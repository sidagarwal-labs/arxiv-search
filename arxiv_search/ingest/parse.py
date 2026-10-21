"""Step 2a (clean up): turn raw OAI-PMH XML pages into plain Python dicts.

This module only *translates* XML into dicts and normalizes whitespace. It
makes no decisions about which papers belong in the corpus; that is the job of
clean.py. Keeping translation and selection separate makes each easier
to test and explain.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "arxiv": "http://arxiv.org/OAI/arXiv/",
}


def clean_text(text: str | None) -> str:
    """Collapse the hard line-wraps and indentation arXiv puts in titles/abstracts."""
    return " ".join((text or "").split())


def submitted_month_from_id(arxiv_id: str) -> str | None:
    """'2308.09419' -> '2023-08'. The YYMM prefix is the month of FIRST submission.

    We use this instead of the <created> field because, in practice, <created>
    can hold the date of the latest revision (e.g. 2308.09419 shows 2026-10-03,
    its v3 date). Old-style IDs like 'cs/0101001' predate our window -> None.
    """
    prefix = arxiv_id.split(".")[0]
    if "/" in arxiv_id or len(prefix) != 4 or not prefix.isdigit():
        return None
    return f"20{prefix[:2]}-{prefix[2:]}"


def _field(meta: ET.Element, name: str) -> str:
    return clean_text(meta.findtext(f"arxiv:{name}", default="", namespaces=NS))


def parse_record(record: ET.Element) -> dict | None:
    """Convert one <record> element to a dict, or None for deleted records."""
    header = record.find("oai:header", NS)
    if header is not None and header.get("status") == "deleted":
        return None
    meta = record.find("oai:metadata/arxiv:arXiv", NS)
    if meta is None:
        return None

    categories = _field(meta, "categories").split()
    authors = [
        clean_text(f"{a.findtext('arxiv:forenames', '', NS)} {a.findtext('arxiv:keyname', '', NS)}")
        for a in meta.findall("arxiv:authors/arxiv:author", NS)
    ]
    arxiv_id = _field(meta, "id")
    return {
        "arxiv_id": arxiv_id,
        "title": _field(meta, "title"),
        "abstract": _field(meta, "abstract"),
        "authors": authors,
        # arXiv lists the primary category first; the rest are cross-lists.
        "primary_category": categories[0] if categories else "",
        "categories": categories,
        "submitted_month": submitted_month_from_id(arxiv_id),  # reliable v1 month
        "created": _field(meta, "created"),  # NOT reliably v1; kept for reference only
        "updated": _field(meta, "updated") or None,
        "comments": _field(meta, "comments") or None,
        "license": _field(meta, "license") or None,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
    }


def parse_page(xml_text: str) -> Iterator[dict]:
    root = ET.fromstring(xml_text)
    for record in root.iterfind(".//oai:ListRecords/oai:record", NS):
        parsed = parse_record(record)
        if parsed is not None:
            yield parsed


def iter_snapshot_records(snapshot_dir: Path) -> Iterator[dict]:
    """Yield every record from every saved page in a raw snapshot folder.

    The same paper can appear under several categories (cross-listing), so
    callers should de-duplicate by arxiv_id.
    """
    for page_path in sorted(snapshot_dir.glob("*/page_*.xml")):
        yield from parse_page(page_path.read_text(encoding="utf-8"))
