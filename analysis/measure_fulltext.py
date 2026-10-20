"""Measure how much text a full paper adds over title + abstract.

Fetches a small stratified random sample of papers from arXiv's HTML renderer
(https://arxiv.org/html/<id>), extracts the body text, and counts tokens with
the BGE-small tokenizer (the same kind of tokenizer we would embed with).

Outputs data/analysis/fulltext_sample.json, used by estimate_costs.py.

Usage:
    python analysis/measure_fulltext.py --per-category 15
"""

from __future__ import annotations

import argparse
import json
import random
import time

import requests
from bs4 import BeautifulSoup
from tokenizers import Tokenizer

from arxiv_search import config

TOKENIZER = "BAAI/bge-small-en-v1.5"
CHUNK_TOKENS = 512
CHUNK_OVERLAP = 64

# Parts of the rendered page that are not paper prose.
DROP_SELECTORS = [
    "nav", "header", "footer", "script", "style",
    ".ltx_page_header", ".ltx_page_footer", ".ltx_authors", ".ltx_dates",
    "math", ".ltx_equation", ".ltx_equationgroup",  # equations become noise tokens
]


def extract_sections(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup.body
    if article is None:
        return {"abstract": "", "body": "", "tables": "", "references": ""}

    def pop_text(selector: str) -> str:
        """Return the text of matching elements and remove them from the page."""
        parts = []
        for el in article.select(selector):
            parts.append(el.get_text(" ", strip=True))
            el.decompose()
        return " ".join(parts)

    references = pop_text(".ltx_bibliography")
    for selector in DROP_SELECTORS:
        for el in article.select(selector):
            el.decompose()
    abstract = pop_text(".ltx_abstract")
    tables = pop_text(".ltx_table")
    body = " ".join(article.get_text(" ", strip=True).split())
    return {"abstract": abstract, "body": body, "tables": tables, "references": references}


def num_chunks(n_tokens: int) -> int:
    if n_tokens <= CHUNK_TOKENS:
        return 1
    step = CHUNK_TOKENS - CHUNK_OVERLAP
    return 1 + -(-(n_tokens - CHUNK_TOKENS) // step)  # ceiling division


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-category", type=int, default=15)
    args = parser.parse_args()

    docs = [json.loads(line) for line in open(config.PROCESSED_DIR / "corpus.jsonl", encoding="utf-8")]
    rng = random.Random(config.RANDOM_SEED)
    sample = []
    for category in config.CATEGORIES:
        group = [d for d in docs if d["primary_category"] == category]
        sample += rng.sample(group, args.per_category)

    tok = Tokenizer.from_pretrained(TOKENIZER)
    tok.no_truncation()

    def count(text: str) -> int:
        return len(tok.encode(text).ids) if text else 0

    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    results = []
    for i, doc in enumerate(sample, 1):
        start = time.monotonic()
        response = session.get(f"https://arxiv.org/html/{doc['arxiv_id']}", timeout=60)
        row = {
            "arxiv_id": doc["arxiv_id"],
            "primary_category": doc["primary_category"],
            "license": doc["license"],
            "title_abstract_tokens": count(f"{doc['title']}. {doc['abstract']}"),
            "html_available": response.status_code == 200 and "ltx_document" in response.text,
            "html_bytes": len(response.content),
            "fetch_seconds": round(time.monotonic() - start, 2),
        }
        if row["html_available"]:
            s = extract_sections(response.text)
            row.update(
                body_tokens=count(s["body"]),  # prose incl. section titles + figure captions
                table_tokens=count(s["tables"]),
                reference_tokens=count(s["references"]),
            )
            row["chunks"] = num_chunks(row["body_tokens"])
            abstract_vocab = set(doc["abstract"].lower().split())
            body_vocab = set(s["body"].lower().split())
            row["body_vocab"] = len(body_vocab)
            row["body_vocab_not_in_abstract"] = len(body_vocab - abstract_vocab)
        results.append(row)
        print(f"[{i}/{len(sample)}] {doc['arxiv_id']} html={row['html_available']} "
              f"body_tokens={row.get('body_tokens', '-')}", flush=True)
        time.sleep(config.REQUEST_DELAY_SECONDS)

    out_dir = config.DATA_DIR / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "fulltext_sample.json").write_text(json.dumps(results, indent=2))
    print(f"Saved {len(results)} rows to {out_dir / 'fulltext_sample.json'}")


if __name__ == "__main__":
    main()
