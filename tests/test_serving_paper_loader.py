from email.message import Message
from io import BytesIO
from urllib.error import URLError
from urllib.request import HTTPSHandler, ProxyHandler, addinfourl, build_opener

import pytest

from arxiv_search import paper_text
from arxiv_search.serving import paper_loader as module
from arxiv_search.serving.paper_loader import Download, MAX_METADATA_BYTES, PaperLoader
from arxiv_search.serving.service import APIError


BASE = "2601.12345"
VERSIONED = BASE + "v2"
CORPUS = {BASE: {"title": "A test paper", "abstract": "The corpus abstract."}}
HTML = b"""<article class="ltx_document">
<section class="ltx_section" id="S1"><h2>Method</h2><p>Actual paper prose.</p></section>
</article>"""
METADATA = f'<meta name="citation_arxiv_id" content="{VERSIONED}">'.encode()


class Clock:
    def __init__(self):
        self.now = 10.0

    def __call__(self):
        return self.now


class Transport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, *, deadline, max_bytes):
        self.calls.append((url, deadline, max_bytes))
        value = self.responses.pop(0)
        if callable(value):
            value = value()
        if isinstance(value, Exception):
            raise value
        if isinstance(value, Download):
            return value
        if isinstance(value, int):
            return Download(value, url, b"Unavailable")
        return Download(200, url, value)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("Tests must remain offline")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def loader(transport, clock=None, **kwargs):
    return PaperLoader(CORPUS, lambda s: len(s.split()), transport, clock or Clock(), **kwargs)


def assert_error(code, operation, status=None):
    with pytest.raises(APIError) as error:
        operation()
    assert error.value.code == code
    if status is not None:
        assert error.value.status == status


def test_html_success_resolves_metadata_and_returns_selected_context():
    transport = Transport(METADATA, HTML)
    context = loader(transport).load(BASE)
    assert isinstance(context, paper_text.Context)
    assert context.paper.versioned_id == VERSIONED
    assert context.paper.source == "html"
    assert context.paper.title == CORPUS[BASE]["title"]
    assert context.included[0].href == f"https://arxiv.org/html/{VERSIONED}#S1"
    assert context.paper.warnings == ()
    assert context.paper_tokens > 0
    assert transport.calls == [
        (f"https://arxiv.org/abs/{BASE}", 30.0, MAX_METADATA_BYTES),
        (f"https://arxiv.org/html/{VERSIONED}", 30.0, paper_text.MAX_HTML_BYTES),
    ]


def test_explicit_version_is_checked_against_metadata():
    transport = Transport(METADATA, HTML)
    assert loader(transport).load(VERSIONED).paper.versioned_id == VERSIONED
    assert transport.calls[0][0] == f"https://arxiv.org/abs/{VERSIONED}"
    assert_error("paper_unavailable", lambda: loader(Transport(METADATA)).load(BASE + "v1"), 404)


def test_latest_revision_uses_scoped_arxiv_submission_history():
    metadata = f"""
    <meta name="citation_arxiv_id" content="{BASE}">
    <meta name="citation_pdf_url" content="https://arxiv.org/pdf/{BASE}">
    <p>Unrelated [v999]</p>
    <div class="submission-history">Submission history:
      <strong>[v1]</strong> Earlier
      <div><strong>[v2]</strong> Latest</div>
    </div><p>[v998]</p>""".encode()
    assert loader(Transport(metadata, HTML)).load(BASE).paper.versioned_id == VERSIONED
    assert loader(Transport(metadata, HTML)).load(BASE + "v1").paper.versioned_id == BASE + "v1"
    assert_error("paper_unavailable", lambda: loader(Transport(metadata)).load(BASE + "v3"), 404)


@pytest.mark.parametrize("name,prefix", [
    ("citation_arxiv_id", ""),
    ("citation_pdf_url", "https://arxiv.org/pdf/"),
    ("og:url", "https://arxiv.org/abs/"),
])
def test_versioned_identity_metadata_forms(name, prefix):
    metadata = f'<meta name="{name}" content="{prefix}{VERSIONED}">'.encode()
    assert loader(Transport(metadata, HTML)).load(BASE).paper.versioned_id == VERSIONED


@pytest.mark.parametrize("identity", [
    "https://arxiv.org/abs/2601.12345", "../2601.12345", BASE + "/x",
    BASE + "?version=2", BASE + "#x", BASE + "v0", BASE + "v10000",
    BASE + "v02", "2613.12345", "hep-th/9901001", "", None, 12,
    "\n" + BASE, BASE + "\n", "２６０１.12345",
])
def test_invalid_ids_never_reach_transport(identity):
    transport = Transport()
    assert_error("bad_request", lambda: loader(transport).load(identity), 400)
    assert transport.calls == []


def test_noncorpus_id_never_reaches_transport():
    transport = Transport()
    assert_error("not_in_corpus", lambda: loader(transport).load("2601.99999v1"), 404)
    assert not transport.calls


@pytest.mark.parametrize("metadata", [
    b"<html>No metadata</html>",
    f'<meta name="citation_arxiv_id" content="{BASE}">'.encode(),
    b'<meta name="citation_arxiv_id" content="2601.99999v2">',
    METADATA + b'<meta name="citation_arxiv_id" content="2601.12345v1">',
    b"\xff",
])
def test_unresolved_or_conflicting_revision_fails_closed(metadata):
    transport = Transport(metadata)
    assert_error("paper_unavailable", lambda: loader(transport).load(BASE))
    assert len(transport.calls) == 1


@pytest.mark.parametrize("response", [404, 503, OSError("offline"), b""])
def test_metadata_failure_does_not_invent_a_revision(response):
    assert_error("paper_unavailable", lambda: loader(Transport(response)).load(BASE))


@pytest.mark.parametrize("stage", ["abs", "html", "pdf"])
@pytest.mark.parametrize("status,url", [
    (302, None), (200, "https://evil.example/"), (200, "https://arxiv.org/html/2601.12345v3"),
])
def test_redirects_and_changed_final_urls_are_terminal(stage, status, url):
    initial = [] if stage == "abs" else [METADATA]
    if stage == "pdf":
        initial.append(404)
    identity = BASE if stage == "abs" else VERSIONED
    response = Download(status, url or f"https://arxiv.org/{stage}/{identity}", b"x",
                        {"Location": "https://evil.example/"})
    transport = Transport(*initial, response)
    assert_error("paper_unavailable", lambda: loader(transport).load(BASE), 503)
    assert not transport.responses


def pdf_bytes():
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
    })
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 10 100 Td (PDF paper prose.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize("html,warning", [
    (404, "html_unavailable"),
    (b"<html>not a paper</html>", "html_extraction_failed"),
    (OSError("offline"), "html_unavailable"),
])
def test_pdf_fallback_extracts_physical_pages_and_discloses_source(html, warning):
    transport = Transport(METADATA, html, pdf_bytes())
    context = loader(transport).load(BASE)
    assert context.paper.source == "pdf"
    assert warning in context.paper.warnings
    assert "pdf_layout_and_equations_may_be_degraded" in context.paper.warnings
    assert context.included[0].href == f"https://arxiv.org/pdf/{VERSIONED}#page=1"
    assert "PDF paper prose." in context.included[0].text
    assert transport.calls[-1] == (
        f"https://arxiv.org/pdf/{VERSIONED}", 30.0, paper_text.MAX_PDF_BYTES,
    )


def test_abstract_fallback_is_explicit_and_from_allowlisted_corpus():
    context = loader(Transport(METADATA, 404, 404)).load(BASE)
    assert context.paper.source == "abstract"
    assert context.paper.warnings == (
        "abstract_only", "html_unavailable", "pdf_unavailable",
        "corpus_abstract_not_revision_verified",
    )
    assert context.included[0].text == CORPUS[BASE]["abstract"]
    assert context.included[0].href == f"https://arxiv.org/abs/{VERSIONED}"


def test_unextractable_pdf_falls_back_to_abstract():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    context = loader(Transport(METADATA, 404, output.getvalue())).load(BASE)
    assert context.paper.source == "abstract"
    assert "pdf_extraction_failed" in context.paper.warnings


def test_corrupt_pdf_falls_back_to_abstract():
    context = loader(Transport(METADATA, 404, b"not a PDF")).load(BASE)
    assert context.paper.source == "abstract"
    assert "pdf_extraction_failed" in context.paper.warnings


def test_pdf_page_limit_exhaustion_is_terminal_not_abstract_fallback():
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(paper_text.MAX_PDF_PAGES + 1):
        writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    transport = Transport(METADATA, 404, output.getvalue())
    assert_error("paper_unavailable", lambda: loader(transport).load(BASE), 503)
    assert not transport.responses


@pytest.mark.parametrize("stage,limit", [
    ("abs", MAX_METADATA_BYTES),
    ("html", paper_text.MAX_HTML_BYTES),
    ("pdf", paper_text.MAX_PDF_BYTES),
])
@pytest.mark.parametrize("declared_only", [False, True])
def test_download_exhaustion_is_terminal_not_silent_fallback(stage, limit, declared_only):
    initial = [] if stage == "abs" else [METADATA]
    if stage == "pdf":
        initial.append(404)
    identity = BASE if stage == "abs" else VERSIONED
    response = Download(
        200, f"https://arxiv.org/{stage}/{identity}",
        b"x" if declared_only else b"x" * (limit + 1),
        {"Content-Length": str(limit + 1)} if declared_only else {},
    )
    transport = Transport(*initial, response)
    assert_error("paper_unavailable", lambda: loader(transport).load(BASE), 503)
    assert not transport.responses


@pytest.mark.parametrize("headers", [
    {"Content-Length": "-1"}, {"Content-Length": "abc"},
    {"Content-Length": "１２３"}, {"Content-Encoding": "gzip"},
])
def test_invalid_size_and_compression_are_rejected(headers):
    response = Download(200, f"https://arxiv.org/abs/{BASE}", METADATA, headers)
    assert_error("paper_unavailable", lambda: loader(Transport(response)).load(BASE), 503)


def test_huge_declared_content_length_fails_closed_without_integer_conversion():
    response = Download(200, f"https://arxiv.org/abs/{BASE}", METADATA,
                        {"Content-Length": "9" * 5000})
    assert_error("paper_unavailable", lambda: loader(Transport(response)).load(BASE), 503)


def test_error_status_cannot_bypass_download_limit():
    response = Download(404, f"https://arxiv.org/abs/{BASE}", b"x" * (MAX_METADATA_BYTES + 1))
    assert_error("paper_unavailable", lambda: loader(Transport(response)).load(BASE), 503)


def test_unbounded_streaming_response_body_is_not_accepted():
    response = Download(200, f"https://arxiv.org/abs/{BASE}", iter([METADATA]))
    assert_error("paper_unavailable", lambda: loader(Transport(response)).load(BASE), 503)


@pytest.mark.parametrize("stage", ["abs", "html", "pdf"])
def test_one_absolute_deadline_covers_all_downloads_and_fallbacks(stage):
    clock = Clock()

    def slow():
        clock.now = 30.0
        return 404

    initial = [] if stage == "abs" else [METADATA]
    if stage == "pdf":
        initial.append(404)
    transport = Transport(*initial, slow)
    assert_error("upstream_timeout", lambda: loader(transport, clock).load(BASE), 504)
    assert {deadline for _, deadline, _ in transport.calls} == {30.0}


@pytest.mark.parametrize("stage", ["abs", "html", "pdf"])
def test_transport_deadline_failure_is_terminal_even_with_a_fake_clock(stage):
    initial = [] if stage == "abs" else [METADATA]
    if stage == "pdf":
        initial.append(404)
    transport = Transport(*initial, TimeoutError())
    assert_error("upstream_timeout", lambda: loader(transport).load(BASE), 504)
    assert not transport.responses


def test_deadline_is_checked_after_extraction(monkeypatch):
    clock = Clock()
    original = paper_text.extract_html

    def slow(*args, **kwargs):
        result = original(*args, **kwargs)
        clock.now = 30.0
        return result

    monkeypatch.setattr(paper_text, "extract_html", slow)
    transport = Transport(METADATA, HTML)
    assert_error("upstream_timeout", lambda: loader(transport, clock).load(BASE), 504)
    assert len(transport.calls) == 2


def test_extraction_error_after_deadline_is_not_hidden_by_fallback(monkeypatch):
    clock = Clock()

    def slow(*args, **kwargs):
        clock.now = 30.0
        raise ValueError("Malformed HTML")

    monkeypatch.setattr(paper_text, "extract_html", slow)
    transport = Transport(METADATA, HTML)
    assert_error("upstream_timeout", lambda: loader(transport, clock).load(BASE), 504)
    assert len(transport.calls) == 2


def test_tokenizer_error_is_not_treated_as_source_failure():
    failure = APIError("budget_exhausted", "Stop", 429)

    def exhausted(value):
        raise failure

    transport = Transport(METADATA, HTML)
    subject = PaperLoader(CORPUS, exhausted, transport, Clock())
    with pytest.raises(APIError) as error:
        subject.load(BASE)
    assert error.value is failure
    assert len(transport.calls) == 2


def test_tokenizer_deadline_is_not_swallowed_as_fallback():
    clock = Clock()

    def slow(value):
        clock.now = 30.0
        return 1

    transport = Transport(METADATA, HTML)
    subject = PaperLoader(CORPUS, slow, transport, clock)
    assert_error("upstream_timeout", lambda: subject.load(BASE), 504)
    assert len(transport.calls) == 2


def test_context_exhaustion_does_not_downgrade_to_abstract():
    transport = Transport(METADATA, HTML)
    subject = PaperLoader(CORPUS, lambda s: 24_001, transport, Clock())
    assert_error("paper_unavailable", lambda: subject.load(BASE), 503)
    assert len(transport.calls) == 2


@pytest.mark.parametrize("count", [-1, 0, True, 1.5, None])
def test_invalid_token_counts_cannot_bypass_context_budget(count):
    transport = Transport(METADATA, HTML)
    subject = PaperLoader(CORPUS, lambda s: count, transport, Clock())
    assert_error("paper_unavailable", lambda: subject.load(BASE), 503)
    assert len(transport.calls) == 2


def test_programming_and_api_errors_are_not_broadly_swallowed():
    transport = Transport(METADATA, RuntimeError("bug"))
    with pytest.raises(RuntimeError, match="bug"):
        loader(transport).load(BASE)
    failure = APIError("budget_exhausted", "Stop", 429)
    with pytest.raises(APIError) as error:
        loader(Transport(METADATA, failure)).load(BASE)
    assert error.value is failure


@pytest.mark.parametrize("kwargs", [
    {"timeout": 0}, {"timeout": float("inf")}, {"timeout": 61},
    {"max_tokens": 0}, {"max_tokens": 24_001}, {"max_tokens": True},
])
def test_configuration_cannot_remove_hard_limits(kwargs):
    with pytest.raises(ValueError):
        loader(Transport(), **kwargs)

def test_loader_instance_is_the_service_callable():
    subject = loader(Transport(METADATA, HTML))
    assert subject(BASE).paper.versioned_id == VERSIONED


@pytest.mark.parametrize("module,responses,source", [
    ("bs4", [METADATA, HTML], "HTML"),
    ("pypdf", [METADATA, 404, b"%PDF"], "PDF"),
])
def test_missing_extractor_dependency_is_terminal_not_fallback(monkeypatch, module, responses,
                                                                 source):
    import sys

    for name in list(sys.modules):
        if name == module or name.startswith(module + "."):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, module, None)
    transport = Transport(*responses)
    with pytest.raises(APIError) as error:
        loader(transport).load(BASE)
    assert (error.value.code, error.value.status) == ("paper_unavailable", 503)
    assert source in str(error.value)
    assert not transport.responses


class Reader(BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.reads = []

    def read1(self, size=-1):
        self.reads.append(size)
        return super().read1(size)


class FakeHTTPS(HTTPSHandler):
    def __init__(self, *responses):
        super().__init__()
        self.responses = list(responses)
        self.requests = []

    def https_open(self, request):
        self.requests.append((request, request.timeout))
        code, body, headers = self.responses.pop(0)
        message = Message()
        for key, value in headers.items():
            message[key] = value
        response = addinfourl(body if isinstance(body, Reader) else Reader(body), message,
                              request.full_url, code)
        response.msg = "OK" if code == 200 else "Redirect"
        return response


def fake_transport(*responses, clock=None):
    handler = FakeHTTPS(*responses)
    opener = build_opener(ProxyHandler({}), module._RejectRedirect(), handler)
    return module.ArxivTransport(clock or Clock(), opener), handler


def test_default_transport_construction_is_bounded_and_does_no_io():
    transport = module.ArxivTransport()
    from urllib.request import HTTPRedirectHandler

    handlers = transport.opener.handlers
    # An empty ProxyHandler suppresses environment proxies and registers no proxy route.
    assert not any(isinstance(h, ProxyHandler) for h in handlers)
    assert [type(h) for h in handlers if isinstance(h, HTTPRedirectHandler)] == [
        module._RejectRedirect,
    ]


def test_default_transport_reads_identity_body_with_bounded_operation_timeout():
    transport, handler = fake_transport((200, METADATA, {"Content-Length": str(len(METADATA))}))
    url = f"https://arxiv.org/abs/{BASE}"
    response = transport.get(url, deadline=100.0, max_bytes=MAX_METADATA_BYTES)
    assert response == module.Download(200, url, METADATA, {"Content-Length": str(len(METADATA))})
    request, timeout = handler.requests[0]
    assert timeout == module.MAX_OPERATION_TIMEOUT
    assert request.get_header("Accept-encoding") == "identity"


def test_default_transport_uses_remaining_time_when_below_operation_cap():
    transport, handler = fake_transport((200, b"x", {}))
    transport.get(f"https://arxiv.org/html/{VERSIONED}", deadline=11.5, max_bytes=10)
    assert handler.requests[0][1] == 1.5


def test_default_transport_stops_after_limit_plus_one_byte():
    body = Reader(b"x" * 1000)
    transport, _ = fake_transport((200, body, {}))
    response = transport.get(f"https://arxiv.org/html/{VERSIONED}", deadline=100.0, max_bytes=10)
    assert response.body == b"x" * 11 and body.reads == [11]
    assert_error("paper_unavailable",
                 lambda: loader(fake_transport((200, b"x" * (MAX_METADATA_BYTES + 5), {}))[0])
                 .load(BASE), 503)


def test_default_transport_does_not_read_declared_oversize_body():
    body = Reader(b"x")
    transport, _ = fake_transport((200, body, {"Content-Length": "11"}))
    response = transport.get(f"https://arxiv.org/pdf/{VERSIONED}", deadline=100.0, max_bytes=10)
    assert response.body == b"" and body.reads == []


def test_default_transport_rejects_redirect_without_following():
    transport, handler = fake_transport((302, b"", {"Location": "https://evil.example/"}))
    response = transport.get(f"https://arxiv.org/abs/{BASE}", deadline=100.0,
                             max_bytes=MAX_METADATA_BYTES)
    assert response.status == 302 and len(handler.requests) == 1
    transport, handler = fake_transport((302, b"", {"Location": "https://evil.example/"}))
    assert_error("paper_unavailable", lambda: loader(transport).load(BASE), 503)
    assert len(handler.requests) == 1


@pytest.mark.parametrize("url", [
    "http://arxiv.org/abs/2601.12345", "https://arxiv.org.evil/abs/2601.12345",
    "https://evil.example/abs/2601.12345", "https://arxiv.org/html/2601.12345",
    "https://arxiv.org/abs/2601.12345?x=1", "https://user@arxiv.org/abs/2601.12345",
    "https://arxiv.org/src/2601.12345v1", "https://arxiv.org/abs/2601.12345\n",
])
def test_default_transport_rejects_arbitrary_urls_before_io(url):
    transport, handler = fake_transport()
    with pytest.raises(ValueError, match="fixed arXiv"):
        transport.get(url, deadline=100.0, max_bytes=10)
    assert not handler.requests


@pytest.mark.parametrize("limit", [0, -1, True, paper_text.MAX_PDF_BYTES + 1])
def test_default_transport_requires_bounded_limit(limit):
    transport, handler = fake_transport()
    with pytest.raises(ValueError, match="limit"):
        transport.get(f"https://arxiv.org/abs/{BASE}", deadline=100.0, max_bytes=limit)
    assert not handler.requests


def test_default_transport_deadline_and_timeout_errors():
    transport, handler = fake_transport()
    with pytest.raises(TimeoutError):
        transport.get(f"https://arxiv.org/abs/{BASE}", deadline=10.0, max_bytes=10)
    assert not handler.requests

    class Timeout:
        def open(self, request, timeout):
            raise URLError(TimeoutError("slow"))

    transport = module.ArxivTransport(Clock(), Timeout())
    with pytest.raises(TimeoutError):
        transport.get(f"https://arxiv.org/abs/{BASE}", deadline=100.0, max_bytes=10)
    assert_error("upstream_timeout", lambda: loader(transport).load(BASE), 504)


def test_real_response_socket_timeout_shrinks_with_absolute_deadline():
    from http.client import HTTPResponse
    from types import SimpleNamespace

    clock = Clock()
    timeouts = []

    class Response(HTTPResponse):
        def __init__(self):
            self.fp = SimpleNamespace(raw=SimpleNamespace(
                _sock=SimpleNamespace(settimeout=timeouts.append)))
            self.headers = Message()
            self.status = 200
            self.calls = 0

        def geturl(self):
            return f"https://arxiv.org/abs/{BASE}"

        def read1(self, size):
            self.calls += 1
            clock.now += 2.0
            return b"x"

        def close(self):
            self.fp = None

    response = Response()

    class Opener:
        def open(self, request, timeout):
            assert timeout == 3.0
            return response

    transport = module.ArxivTransport(clock, Opener())
    with pytest.raises(TimeoutError):
        transport.get(f"https://arxiv.org/abs/{BASE}", deadline=13.0, max_bytes=10)
    assert timeouts == [3.0, 1.0]
    assert response.calls == 2 and response.fp is None


@pytest.mark.parametrize("user_agent", ["", "x\ny", "x\ry", "x\x00y", "x\x7fy", "x" * 201])
def test_transport_rejects_invalid_user_agent_without_io(user_agent):
    with pytest.raises(ValueError, match="user agent"):
        module.ArxivTransport(user_agent=user_agent)


def test_transport_uses_configured_nonsecret_user_agent():
    transport, handler = fake_transport((200, b"x", {}))
    subject = module.ArxivTransport(Clock(), transport.opener,
                                  user_agent="CollegePaperReader/1 (offline-tested)")
    subject.get(f"https://arxiv.org/abs/{BASE}", deadline=100.0, max_bytes=10)
    assert handler.requests[0][0].get_header("User-agent") == (
        "CollegePaperReader/1 (offline-tested)")


@pytest.mark.parametrize("deadline", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_deadline_cannot_disable_transport_time_limit(deadline):
    transport, handler = fake_transport()
    with pytest.raises(TimeoutError):
        transport.get(f"https://arxiv.org/abs/{BASE}", deadline=deadline, max_bytes=10)
    assert not handler.requests
