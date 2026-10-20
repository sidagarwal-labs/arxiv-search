"""Ingestion stage 3 of 3: select, sample, and write the final search corpus.

Pipeline (each step is counted in corpus_stats.json so the write-up can cite it):

    all parsed records
      -> de-duplicate by arxiv_id         (cross-listed papers appear in several sets)
      -> primary category in CATEGORIES   (cs.CV paper cross-listed to cs.IR is dropped)
      -> submitted within WINDOW_DAYS     (month from the arXiv ID; see parse.py)
      -> drop withdrawn / stub abstracts  (fewer than MIN_ABSTRACT_WORDS words)
      -> stratified sample per category   (at most MAX_PER_CATEGORY, fixed seed)
      -> data/processed/corpus.jsonl

Usage:
    python -m arxiv_search.ingest.build_corpus                  # newest snapshot
    python -m arxiv_search.ingest.build_corpus --snapshot 2026-10-20
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from arxiv_search import config
from arxiv_search.ingest.parse import iter_snapshot_records


def deduplicate(records: list[dict]) -> list[dict]:
    """Keep one copy per paper. Copies are identical; we keep the first seen."""
    seen: dict[str, dict] = {}
    for record in records:
        seen.setdefault(record["arxiv_id"], record)
    return list(seen.values())


def is_withdrawn_or_stub(record: dict) -> bool:
    comments = (record.get("comments") or "").lower()
    return "withdrawn" in comments or len(record["abstract"].split()) < config.MIN_ABSTRACT_WORDS


def stratified_sample(records: list[dict], cap: int, seed: int) -> list[dict]:
    """Sample at most `cap` papers per primary category.

    Records are sorted by arxiv_id before sampling so the result depends only on
    the data and the seed, not on file or dict ordering.
    """
    rng = random.Random(seed)
    by_category: dict[str, list[dict]] = {}
    for record in sorted(records, key=lambda r: r["arxiv_id"]):
        by_category.setdefault(record["primary_category"], []).append(record)

    sampled: list[dict] = []
    for category in sorted(by_category):
        group = by_category[category]
        sampled.extend(group if len(group) <= cap else rng.sample(group, cap))
    return sorted(sampled, key=lambda r: r["arxiv_id"])


def build_corpus(records: list[dict], harvest_date: date) -> tuple[list[dict], dict]:
    # Month precision: a 365-day window starting mid-month includes that whole month.
    cutoff = (harvest_date - timedelta(days=config.WINDOW_DAYS)).isoformat()[:7]
    stages: dict[str, dict] = {}

    def count(name: str, rows: list[dict]) -> None:
        stages[name] = {"total": len(rows), **Counter(r["primary_category"] for r in rows)}

    count("parsed", records)
    rows = deduplicate(records)
    count("deduplicated", rows)
    rows = [r for r in rows if r["primary_category"] in config.CATEGORIES]
    count("primary_category_match", rows)
    # "YYYY-MM" strings compare correctly as text.
    rows = [r for r in rows if r["submitted_month"] and r["submitted_month"] >= cutoff]
    count("within_window", rows)
    rows = [r for r in rows if not is_withdrawn_or_stub(r)]
    count("not_withdrawn_or_stub", rows)
    rows = stratified_sample(rows, config.MAX_PER_CATEGORY, config.RANDOM_SEED)
    count("final_sample", rows)

    stats = {
        "harvest_date": harvest_date.isoformat(),
        "submitted_month_cutoff": cutoff,
        "categories": list(config.CATEGORIES),
        "max_per_category": config.MAX_PER_CATEGORY,
        "random_seed": config.RANDOM_SEED,
        "stages": stages,
    }
    return rows, stats


def latest_snapshot() -> Path:
    snapshots = sorted(p for p in config.RAW_DIR.iterdir() if p.is_dir())
    if not snapshots:
        raise SystemExit("No raw snapshots found. Run arxiv_search.ingest.harvest first.")
    return snapshots[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the search corpus from a raw snapshot.")
    parser.add_argument("--snapshot", help="Snapshot folder name under data/raw (default: newest)")
    args = parser.parse_args()

    snapshot_dir = config.RAW_DIR / args.snapshot if args.snapshot else latest_snapshot()
    harvest_date = date.fromisoformat(snapshot_dir.name)

    records = list(iter_snapshot_records(snapshot_dir))
    corpus, stats = build_corpus(records, harvest_date)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    corpus_path = config.PROCESSED_DIR / "corpus.jsonl"
    with corpus_path.open("w", encoding="utf-8") as f:
        for doc in corpus:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    (config.PROCESSED_DIR / "corpus_stats.json").write_text(json.dumps(stats, indent=2))

    print(json.dumps(stats["stages"], indent=2))
    print(f"Wrote {len(corpus):,} documents to {corpus_path}")


if __name__ == "__main__":
    main()
