"""Build a small local sample of the corpus for the UI's mock mode.

Run from the arxiv-search folder:
    .\\.venv\\Scripts\\python.exe web\\scripts\\make_mock_data.py

Writes web/mock/papers.json (git-ignored). Read-only on the corpus.
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "processed" / "corpus.jsonl"
OUT = ROOT / "web" / "mock" / "papers.json"
SAMPLE_SIZE = 1500
FIELDS = ("arxiv_id", "title", "abstract", "authors", "primary_category", "categories", "submitted_month", "url")


def main() -> None:
    papers = [json.loads(line) for line in CORPUS.open(encoding="utf-8")]
    rng = random.Random(6188)
    sample = rng.sample(papers, min(SAMPLE_SIZE, len(papers)))
    months = sorted(p["submitted_month"] for p in papers)
    payload = {
        "meta": {
            "papers": len(papers),
            "categories": sorted({p["primary_category"] for p in papers}),
            "from_month": months[0],
            "to_month": months[-1],
            "fields": "title+abstract",
        },
        "papers": [{k: p[k] for k in FIELDS} for p in sample],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(sample)} papers to {OUT}")


if __name__ == "__main__":
    main()
