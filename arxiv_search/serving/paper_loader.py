"""Corpus-allowlisted paper preparation with no implicit network or model calls.

``PaperLoader(corpus, count_tokens, transport, clock).load(arxiv_id)`` returns a
selected ``Context``. Transports must enforce the supplied absolute monotonic
deadline and byte limit while reading, disable redirects, and return ``Download``.
The loader also validates every response before parsing it. A transport is
required deliberately; ``ArxivTransport`` is the bounded production option, and
constructing either class or importing this module performs no I/O.

Serving errors use ``bad_request`` (400), ``not_in_corpus`` (404),
``paper_unavailable`` (503; unknown revisions 404), and ``upstream_timeout`` (504).
Missing optional extractors and exhausted limits fail explicitly, not as fallbacks.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from http.client import HTTPResponse
import math
import re
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from arxiv_search import paper_text
from arxiv_search.paper_text import Context
from arxiv_search.serving.service import APIError

MAX_METADATA_BYTES = 512 * 1024
MAX_OPERATION_TIMEOUT = 5.0
_CHUNK_BYTES = 64 * 1024
_ID = re.compile(r"([0-9]{2}(?:0[1-9]|1[0-2])\.[0-9]{4,5})(?:v([1-9][0-9]{0,3}))?")
_VERSION = re.compile(r"\[v([1-9][0-9]{0,3})\]")
_URL = re.compile(
    r"https://arxiv\.org/(?:abs/[0-9]{4}\.[0-9]{4,5}(?:v[1-9][0-9]{0,3})?"
    r"|(?:html|pdf)/[0-9]{4}\.[0-9]{4,5}v[1-9][0-9]{0,3})"
)


@dataclass(frozen=True)
class Download:
    status: int
    url: str
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


class PaperTransport(Protocol):
    def get(self, url: str, *, deadline: float, max_bytes: int) -> Download:
        """Bound reads to max_bytes and deadline; do not follow redirects."""
        ...


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # urllib then raises HTTPError carrying the 3xx status.


class ArxivTransport:
    """Fixed-host urllib transport: no proxies, redirects, compression or unbounded reads.

    Each socket operation is limited to ``min(remaining, MAX_OPERATION_TIMEOUT)``.
    The socket timeout is reduced before each bounded read as the absolute
    deadline approaches. Calling ``get`` is the only network action.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic, opener=None, *,
                 user_agent: str = "arxiv-search-paper-chat/1 (bounded paper preparation)") -> None:
        if (not isinstance(user_agent, str) or not 1 <= len(user_agent) <= 200
                or not user_agent.isascii() or any(ord(c) < 32 or ord(c) == 127
                                                 for c in user_agent)):
            raise ValueError("A printable, nonsecret paper user agent is required")
        self.clock = clock
        self.user_agent = user_agent
        self.opener = opener or build_opener(ProxyHandler({}), _RejectRedirect())

    def _timeout(self, deadline: float) -> float:
        remaining = deadline - self.clock()
        if not math.isfinite(remaining) or remaining <= 0:
            raise TimeoutError("Paper download deadline elapsed")
        return min(remaining, MAX_OPERATION_TIMEOUT)

    def get(self, url: str, *, deadline: float, max_bytes: int) -> Download:
        if not isinstance(url, str) or not _URL.fullmatch(url):
            raise ValueError("Only fixed arXiv paper URLs are allowed")
        if type(max_bytes) is not int or not 0 < max_bytes <= paper_text.MAX_PDF_BYTES:
            raise ValueError("Invalid paper download limit")
        request = Request(url, headers={
            "Accept-Encoding": "identity", "User-Agent": self.user_agent,
        })
        try:
            response: HTTPResponse = self.opener.open(request, timeout=self._timeout(deadline))
        except HTTPError as error:
            headers = dict(error.headers.items()) if error.headers else {}
            error.close()
            self._timeout(deadline)
            return Download(error.code, url, b"", headers)
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise TimeoutError("Paper download timed out") from None
            raise
        with response:
            headers = dict(response.headers.items())
            final = response.geturl()
            length = {k.lower(): v for k, v in headers.items()}.get("content-length")
            if final != url or response.status != 200 or (
                    length is not None and length.isascii() and length.isdecimal()
                    and (len(length) > 10 or int(length) > max_bytes)):
                return Download(response.status, final, b"", headers)
            chunks, size = [], 0
            while size <= max_bytes:
                remaining_timeout = self._timeout(deadline)
                if isinstance(response, HTTPResponse) and response.fp is not None:
                    # urllib's HTTPResponse uses a SocketIO-backed buffered reader.
                    # Retune its live socket rather than resetting the wall deadline.
                    response.fp.raw._sock.settimeout(remaining_timeout)
                chunk = response.read1(min(_CHUNK_BYTES, max_bytes + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            self._timeout(deadline)
            return Download(response.status, final, b"".join(chunks), headers)


class _Metadata(HTMLParser):
    """Read identity metadata and the bounded, scoped submission-history block."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.identities: list[str] = []
        self.history: list[str] = []
        self.history_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta":
            name = (values.get("name") or values.get("property") or "").lower()
            content = values.get("content") or ""
            if name == "citation_arxiv_id":
                self.identities.append(content)
            elif name in {"citation_pdf_url", "og:url"}:
                for prefix in ("https://arxiv.org/abs/", "https://arxiv.org/pdf/"):
                    if content.startswith(prefix):
                        self.identities.append(content[len(prefix):])
                        break
        if tag == "div":
            if self.history_depth:
                self.history_depth += 1
            elif "submission-history" in (values.get("class") or "").split():
                self.history_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.history_depth:
            self.history_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.history_depth:
            self.history.append(data)


class _Unavailable(Exception):
    """An expected source failure; eligible for a disclosed fallback."""


class PaperLoader:
    def __init__(
        self,
        corpus: Mapping[str, Mapping[str, str]],
        count_tokens: Callable[[str], int],
        transport: PaperTransport,
        clock: Callable[[], float] = time.monotonic,
        *,
        timeout: float = 20.0,
        max_tokens: int = 24_000,
    ) -> None:
        if not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("Paper preparation timeout must be in (0, 60] seconds")
        if type(max_tokens) is not int or not 0 < max_tokens <= 24_000:
            raise ValueError("Paper context budget must be in [1, 24000]")
        self.corpus: dict[str, dict[str, str]] = {}
        for identity, entry in corpus.items():
            match = _ID.fullmatch(identity)
            if match is None:
                raise ValueError("Corpus paper IDs must be modern arXiv IDs")
            value = {"title": entry["title"], "abstract": entry["abstract"]}
            if not all(isinstance(s, str) and s.strip() for s in value.values()):
                raise ValueError("Corpus title and abstract must be nonempty strings")
            base = match[1]
            if base in self.corpus and self.corpus[base] != value:
                raise ValueError("Conflicting corpus revisions")
            self.corpus[base] = value
        self.count_tokens = count_tokens
        self.transport = transport
        self.clock = clock
        self.timeout = timeout
        self.max_tokens = max_tokens

    def __call__(self, arxiv_id: str) -> Context:
        return self.load(arxiv_id)

    def _check_deadline(self, deadline: float) -> None:
        if self.clock() >= deadline:
            raise APIError("upstream_timeout", "Paper preparation exceeded its deadline.", 504)

    def _download(self, url: str, limit: int, deadline: float) -> bytes:
        self._check_deadline(deadline)
        try:
            response = self.transport.get(url, deadline=deadline, max_bytes=limit)
        except TimeoutError:
            raise APIError(
                "upstream_timeout", "Paper download exceeded its deadline.", 504,
            ) from None
        except (URLError, OSError):
            self._check_deadline(deadline)
            raise _Unavailable("download_failed") from None
        self._check_deadline(deadline)
        if response.url != url or 300 <= response.status < 400:
            raise APIError("paper_unavailable", "Paper source attempted a redirect.", 503)
        if not isinstance(response.body, bytes):
            raise APIError("paper_unavailable", "Paper source returned an invalid body.", 503)
        headers = {key.lower(): value for key, value in response.headers.items()}
        length = headers.get("content-length")
        if length is not None and (not length.isascii() or not length.isdecimal()):
            raise APIError("paper_unavailable", "Paper source returned an invalid size.", 503)
        if len(response.body) > limit or (
                length is not None and (len(length) > 10 or int(length) > limit)):
            raise APIError("paper_unavailable", "Paper source exceeds the download limit.", 503)
        if headers.get("content-encoding", "identity").lower() not in {"identity", ""}:
            raise APIError("paper_unavailable", "Compressed paper downloads are not supported.", 503)
        if response.status != 200:
            raise _Unavailable("http_error")
        if not response.body:
            raise _Unavailable("empty_download")
        return response.body

    def _resolve(self, identity: str, base: str, requested: str | None,
                 deadline: float) -> str:
        try:
            body = self._download(f"https://arxiv.org/abs/{identity}", MAX_METADATA_BYTES, deadline)
        except _Unavailable:
            raise APIError("paper_unavailable", "Paper revision metadata is unavailable.", 503) from None
        metadata = _Metadata()
        try:
            metadata.feed(body.decode("utf-8"))
            metadata.close()
        except UnicodeError:
            raise APIError("paper_unavailable", "Paper revision metadata is invalid.", 503) from None
        self._check_deadline(deadline)
        versions: set[int] = set()
        for candidate in metadata.identities:
            match = _ID.fullmatch(candidate)
            if match is None or match[1] != base:
                raise APIError("paper_unavailable", "Paper revision identity does not match.", 503)
            if match[2]:
                versions.add(int(match[2]))
        if not metadata.identities or len(versions) > 1:
            raise APIError("paper_unavailable", "Paper revision metadata is ambiguous.", 503)
        history = {int(v) for v in _VERSION.findall(" ".join(metadata.history))}
        if requested:
            revision = int(requested)
            if (versions and versions != {revision}) or (
                    not versions and revision not in history):
                raise APIError("paper_unavailable", "The requested paper revision is unavailable.", 404)
        elif versions:
            revision = next(iter(versions))
        elif history:
            revision = max(history)
        else:
            raise APIError("paper_unavailable", "No explicit paper revision could be resolved.", 503)
        return f"{base}v{revision}"

    def load(self, arxiv_id: str) -> Context:
        """Resolve only a corpus paper, then prepare HTML → PDF → abstract evidence.

        Unsafe responses, exhausted byte/context budgets and elapsed deadlines
        fail closed. Only ordinary unavailable/unextractable sources fall back;
        fallback provenance is retained in ``Context.paper.warnings``. Corpus
        abstract text is not claimed to have been verified against the revision.
        """
        match = _ID.fullmatch(arxiv_id) if isinstance(arxiv_id, str) else None
        if match is None:
            raise APIError("bad_request", "A modern arXiv paper ID is required.", 400)
        base, requested = match.groups()
        entry = self.corpus.get(base)
        if entry is None:
            raise APIError("not_in_corpus", "Paper is not in this corpus.", 404)
        deadline = self.clock() + self.timeout
        versioned = self._resolve(arxiv_id, base, requested, deadline)
        warnings: list[str] = []
        paper = None
        for source, limit, extract in (
            ("html", paper_text.MAX_HTML_BYTES, paper_text.extract_html),
            ("pdf", paper_text.MAX_PDF_BYTES, paper_text.extract_pdf),
        ):
            try:
                body = self._download(f"https://arxiv.org/{source}/{versioned}", limit, deadline)
            except _Unavailable:
                warnings.append(f"{source}_unavailable")
                continue
            parse_errors: tuple[type[Exception], ...] = (ValueError,)
            try:
                if source == "pdf":
                    from pypdf.errors import PdfReadError

                    parse_errors += (PdfReadError,)
                paper = extract(versioned, entry["title"], body)
            except ImportError:
                # A missing extractor is a deployment fault, never a reason to downgrade.
                raise APIError(
                    "paper_unavailable",
                    f"The {source.upper()} paper extractor is not installed.", 503,
                ) from None
            except parse_errors as error:
                self._check_deadline(deadline)
                # The core currently combines encryption and the page ceiling
                # in one ValueError; neither is safe to disguise as a fallback.
                if str(error) in {
                    "Encrypted PDF or page limit exceeded", "PDF page limit exceeded",
                }:
                    raise APIError(
                        "paper_unavailable", "Paper extraction exceeds its safe limits.", 503,
                    ) from None
                warnings.append(f"{source}_extraction_failed")
                continue
            self._check_deadline(deadline)
            break
        if paper is None:
            self._check_deadline(deadline)
            paper = paper_text.abstract_paper(versioned, entry["title"], entry["abstract"])
            warnings.append("corpus_abstract_not_revision_verified")
        paper = replace(paper, warnings=(*paper.warnings, *warnings))
        self._check_deadline(deadline)

        def count(value: str) -> int:
            self._check_deadline(deadline)
            result = self.count_tokens(value)
            self._check_deadline(deadline)
            if type(result) is not int or result <= 0:
                raise APIError(
                    "paper_unavailable", "The paper tokenizer returned an invalid token count.", 503,
                )
            return result

        try:
            context = paper_text.select_context(paper, count, max_tokens=self.max_tokens)
        except ValueError:
            self._check_deadline(deadline)
            raise APIError(
                "paper_unavailable", "No complete paper section fits the context budget.", 503,
            ) from None
        self._check_deadline(deadline)
        return context
