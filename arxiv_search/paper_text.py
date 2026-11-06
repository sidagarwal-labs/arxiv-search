"""Offline extraction of one versioned paper; no network or model calls.

The caller supplies corpus-checked identity and downloaded bytes. Optional dependencies
are loaded only by the relevant extractor, not by the serving answer contract.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

EXTRACTOR_VERSION = "paper-text-v1"
MAX_HTML_BYTES = 8 * 1024 * 1024
MAX_PDF_BYTES = 15 * 1024 * 1024
MAX_PDF_PAGES = 100
_VERSIONED_ID = re.compile(r"\d{4}\.\d{4,5}v[1-9]\d*")
_LOCATOR = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")


@dataclass(frozen=True)
class Section:
    id: str
    label: str
    title: str
    text: str
    href: str
    kind: str = "body"


@dataclass(frozen=True)
class Paper:
    versioned_id: str
    title: str
    source: str
    sections: tuple[Section, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _VERSIONED_ID.fullmatch(self.versioned_id):
            raise ValueError("A resolved modern arXiv ID with an explicit version is required")
        if self.source not in {"html", "pdf", "abstract"} or not self.title.strip():
            raise ValueError("Invalid paper source or title")
        if not self.sections or len({s.id for s in self.sections}) != len(self.sections):
            raise ValueError("Paper must have nonempty, uniquely identified sections")
        for section in self.sections:
            if not _LOCATOR.fullmatch(section.id) or not section.text.strip():
                raise ValueError("Invalid or empty paper section")
            if section.kind not in {"body", "appendix", "references"}:
                raise ValueError("Invalid section kind")
            prefix = f"https://arxiv.org/{'abs' if self.source == 'abstract' else self.source}/"
            target = prefix + self.versioned_id
            if self.source == "html":
                target += "#" + section.id
            elif self.source == "pdf":
                if not re.fullmatch(r"p[1-9]\d*", section.id):
                    raise ValueError("PDF locators must name physical pages")
                target += "#page=" + section.id[1:]
            if section.href != target:
                raise ValueError("Section URL does not match the paper version and locator")

    @property
    def content_sha256(self) -> str:
        import json

        value = [EXTRACTOR_VERSION, self.versioned_id, self.title, self.source,
                 [(s.id, s.label, s.title, s.text, s.kind) for s in self.sections], self.warnings]
        return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Omission:
    id: str
    label: str
    reason: str


@dataclass(frozen=True)
class Context:
    paper: Paper
    included: tuple[Section, ...]
    omitted: tuple[Omission, ...]
    paper_tokens: int

    def coverage(self) -> dict:
        return {
            "source": self.paper.source,
            "included_sections": [
                {"id": s.id, "label": s.label, "title": s.title} for s in self.included
            ],
            "omitted": [
                {"id": s.id, "label": s.label, "reason": s.reason} for s in self.omitted
            ],
            "truncated": any(s.reason == "over_budget" for s in self.omitted),
            "paper_tokens": self.paper_tokens,
            "figures": "captions_only" if self.paper.source == "html" else "not_available",
            "equations": "text_or_latex" if self.paper.source == "html" else "degraded",
            "warnings": list(self.paper.warnings),
        }

    def evidence(self) -> list[dict]:
        return [{"id": s.id, "label": s.label, "title": s.title, "text": s.text}
                for s in self.included]


def _clean(text: str) -> str:
    return " ".join(text.split())


def extract_html(versioned_id: str, title: str, html: bytes) -> Paper:
    """Keep actual arXiv section anchors; flatten nested sections without duplicate text."""
    from bs4 import BeautifulSoup

    if not html or len(html) > MAX_HTML_BYTES:
        raise ValueError("HTML is empty or exceeds the download limit")
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article.ltx_document")
    if article is None:
        raise ValueError("No arXiv HTML document; use an explicit PDF or abstract fallback")
    warnings = []
    if article.select_one(".ltx_ERROR") is not None:
        warnings.append("html_conversion_errors")
    for node in article.select("script, style, nav, .ltx_page_footer, .ltx_authors"):
        node.decompose()
    for math in article.find_all("math"):
        alt = math.get("alttext")
        if isinstance(alt, str) and alt.strip():
            math.replace_with(" " + alt + " ")
        else:
            warnings.append("equations_degraded")
    sections = []
    for node in article.find_all(["section", "div"]):
        classes = set(node.get("class", []))
        if not (classes & {"ltx_abstract", "ltx_section", "ltx_subsection", "ltx_subsubsection",
                           "ltx_appendix", "ltx_bibliography"}):
            continue
        locator = node.get("id")
        if not isinstance(locator, str) or not _LOCATOR.fullmatch(locator):
            raise ValueError("A paper section has no usable source anchor")
        ancestors = [node, *node.parents]
        all_classes = {c for parent in ancestors for c in parent.get("class", [])}
        kind = ("references" if "ltx_bibliography" in all_classes else
                "appendix" if "ltx_appendix" in all_classes else "body")
        heading = node.find(re.compile(r"h[1-6]"), recursive=False)
        name = _clean(heading.get_text(" ", strip=True)) if heading else (
            "Abstract" if "ltx_abstract" in classes else locator)
        # A parent retains only its direct prose; children get their own anchors.
        clone = BeautifulSoup(str(node), "html.parser")
        root = clone.find()
        for child in list(root.find_all(["section", "div"])):
            if child.parent is not None and set(child.get("class", [])) & {
                "ltx_section", "ltx_subsection", "ltx_subsubsection", "ltx_appendix",
                "ltx_bibliography",
            }:
                child.decompose()
        text = _clean(root.get_text(" ", strip=True))
        if text and text != name:
            sections.append(Section(locator, name, name, text,
                                    f"https://arxiv.org/html/{versioned_id}#{locator}", kind))
    if not sections:
        raise ValueError("No extractable anchored text in arXiv HTML")
    return Paper(versioned_id, title, "html", tuple(sections), tuple(sorted(set(warnings))))


def extract_pdf(versioned_id: str, title: str, pdf: bytes) -> Paper:
    """Page locators are physical PDF pages, not inferred section numbers."""
    from io import BytesIO

    from pypdf import PdfReader

    if not pdf or len(pdf) > MAX_PDF_BYTES:
        raise ValueError("PDF is empty or exceeds the download limit")
    reader = PdfReader(BytesIO(pdf))
    if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PDF_PAGES:
        raise ValueError("Encrypted PDF or page limit exceeded")
    texts = [_clean(page.extract_text() or "") for page in reader.pages]
    return from_pdf_pages(versioned_id, title, texts)


def from_pdf_pages(versioned_id: str, title: str, pages: Sequence[str]) -> Paper:
    if not 1 <= len(pages) <= MAX_PDF_PAGES:
        raise ValueError("PDF page limit exceeded")
    sections = []
    warnings = ["pdf_layout_and_equations_may_be_degraded", "pdf_references_not_separated"]
    for n, text in enumerate(pages, 1):
        text = _clean(text)
        if text:
            sections.append(Section(f"p{n}", f"p. {n}", f"Page {n}", text,
                                    f"https://arxiv.org/pdf/{versioned_id}#page={n}"))
        else:
            warnings.append(f"page_{n}_has_no_extractable_text")
    if not sections:
        raise ValueError("PDF has no extractable text; OCR is not supported")
    return Paper(versioned_id, title, "pdf", tuple(sections), tuple(warnings))


def abstract_paper(versioned_id: str, title: str, abstract: str) -> Paper:
    return Paper(versioned_id, title, "abstract", (
        Section("abstract", "Abstract", "Abstract", _clean(abstract),
                f"https://arxiv.org/abs/{versioned_id}"),
    ), ("abstract_only",))


def select_context(paper: Paper, count_tokens: Callable[[str], int], *,
                   max_tokens: int = 24_000) -> Context:
    """Select whole sections: body first, then appendices; never silently slice prose."""
    import json

    if max_tokens <= 0:
        raise ValueError("Paper token budget must be positive")
    included: list[Section] = []
    omitted = []
    for section in sorted(paper.sections, key=lambda s: {"body": 0, "appendix": 1,
                                                       "references": 2}[s.kind]):
        if section.kind == "references":
            omitted.append(Omission(section.id, section.label, "references"))
            continue
        trial = [*included, section]
        evidence = [{"id": s.id, "label": s.label, "title": s.title, "text": s.text} for s in trial]
        tokens = count_tokens(json.dumps(evidence, ensure_ascii=False))
        if tokens <= max_tokens:
            included.append(section)
        else:
            omitted.append(Omission(section.id, section.label, "over_budget"))
    if not included:
        raise ValueError("No complete section fits the context budget")
    evidence = [{"id": s.id, "label": s.label, "title": s.title, "text": s.text} for s in included]
    return Context(paper, tuple(included), tuple(omitted),
                   count_tokens(json.dumps(evidence, ensure_ascii=False)))
