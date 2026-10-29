"""Compare paid OpenAI embeddings with cached local models on one fixed small corpus.

Dry run: python -m arxiv_search.evaluate.embedding_pilot
Approved $0.25 lifetime pilot: add --run. No full-corpus embedding calls are made.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sqlite3
import time
import uuid
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

from arxiv_search import config
from arxiv_search.evaluate import metrics
from arxiv_search.evaluate.judge import load_inputs
from arxiv_search.search import dense
from arxiv_search.search.text import paper_text

MODELS = {
    "text-embedding-3-small": {"dimensions": 1536, "nanodollars_per_token": 20},
    "text-embedding-3-large": {"dimensions": 3072, "nanodollars_per_token": 130},
}
BUDGET_NANODOLLARS = 250_000_000  # $0.25 total, including failures with unknown usage
OUT = config.RESULTS_DIR / "embedding-pilot"
CACHE = config.EMBEDDINGS_DIR / "openai-pilot"
LEDGER = config.DATA_DIR / "openai" / "embedding-pilot.sqlite3"


def select_ids(papers: dict, queries: dict, dev_ids: list[str], size: int = 2000) -> list[str]:
    """Keep every dev source, then add seeded distractors; never select using scores."""
    ids = {queries[q]["source_arxiv_id"] for q in dev_ids}
    if size < len(ids) or size > len(papers):
        raise ValueError("pilot size must include all dev sources and fit the corpus")
    remaining = sorted(set(papers) - ids)
    random.Random(config.RANDOM_SEED).shuffle(remaining)
    return sorted(ids | set(remaining[:size - len(ids)]))


def token_counts(texts: list[str]) -> list[int]:
    import tiktoken

    encoder = tiktoken.get_encoding("cl100k_base")
    return [len(encoder.encode(t, disallowed_special=())) for t in texts]


def spending_summary(path: Path = LEDGER) -> dict:
    if not path.exists():
        return {}
    with sqlite3.connect(path) as db:
        rows = db.execute("""SELECT model, COUNT(*), SUM(tokens), SUM(nanodollars),
                             SUM(CASE WHEN status='complete' THEN 1 ELSE 0 END),
                             SUM(seconds) FROM calls GROUP BY model""").fetchall()
    return {model: {"requests": n, "accounted_tokens": tokens,
                    "accounted_usd": dollars / 1e9, "complete_requests": complete,
                    "api_seconds": seconds}
            for model, n, tokens, dollars, complete, seconds in rows}


def reserve(model: str, tokens: int, path: Path = LEDGER) -> str:
    """Atomic lifetime spending cap. Unknown failures retain their full reservation."""
    cost = tokens * MODELS[model]["nanodollars_per_token"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=30) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS calls
                      (id TEXT PRIMARY KEY, model TEXT, tokens INTEGER,
                       nanodollars INTEGER, status TEXT, seconds REAL)""")
        db.execute("BEGIN IMMEDIATE")
        spent = db.execute("SELECT COALESCE(SUM(nanodollars),0) FROM calls").fetchone()[0]
        if spent + cost > BUDGET_NANODOLLARS:
            raise RuntimeError("Embedding pilot $0.25 lifetime cap reached; no request sent")
        request_id = uuid.uuid4().hex
        db.execute("INSERT INTO calls VALUES (?,?,?,?,?,?)",
                   (request_id, model, tokens, cost, "reserved", None))
    return request_id


def settle(request_id: str, model: str, tokens: int, seconds: float,
           path: Path = LEDGER) -> None:
    with sqlite3.connect(path, timeout=30) as db:
        reserved = db.execute("SELECT tokens FROM calls WHERE id=?", (request_id,)).fetchone()
        if reserved is None:
            raise ValueError("Unknown embedding reservation")
        db.execute("UPDATE calls SET tokens=?, nanodollars=?, status='complete', seconds=? WHERE id=?",
                   (tokens, tokens * MODELS[model]["nanodollars_per_token"], seconds, request_id))
    if tokens > reserved[0]:
        raise RuntimeError("Embedding usage exceeded token reservation; recorded actual usage and stopped")


def paid_vectors(model: str, texts: list[str], counts: list[int], key: str) -> np.ndarray:
    """Cache by exact text and model, save each batch; do not retry failed paid requests."""
    if model not in MODELS:
        raise ValueError("embedding model is not approved")
    dimensions = MODELS[model]["dimensions"]
    fingerprint = hashlib.sha256(json.dumps([model, dimensions, texts]).encode()).hexdigest()
    folder = CACHE / model / fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    load_dotenv(config.PROJECT_ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in the local .env")
    batches = []
    for start in range(0, len(texts), 64):
        chunk = texts[start:start + 64]
        path = folder / f"{start}.npy"
        if path.exists():
            vectors = np.load(path, allow_pickle=False)
            if vectors.shape != (len(chunk), dimensions) or not np.isfinite(vectors).all():
                raise ValueError(f"Invalid cached embedding batch: {path}")
        else:
            count = sum(counts[start:start + 64]) + 8 * len(chunk)
            request_id = reserve(model, count)
            begin = time.perf_counter()
            response = requests.post("https://api.openai.com/v1/embeddings", timeout=120,
                                     headers={"Authorization": f"Bearer {api_key}"},
                                     json={"model": model, "input": chunk,
                                           "dimensions": dimensions, "encoding_format": "float"})
            if response.status_code != 200:
                raise RuntimeError(f"{model}: HTTP {response.status_code}; reservation retained. "
                                   "No automatic paid retry; resume later.")
            body = response.json()
            usage = body["usage"]["total_tokens"]
            if type(usage) is not int or usage < 0:
                raise ValueError("Invalid embedding usage; reservation retained")
            settle(request_id, model, usage, time.perf_counter() - begin)
            data = sorted(body["data"], key=lambda row: row["index"])
            if [r["index"] for r in data] != list(range(len(chunk))):
                raise ValueError("Embedding response has missing or duplicate indices")
            vectors = np.asarray([r["embedding"] for r in data], dtype=np.float32)
            if vectors.shape != (len(chunk), dimensions) or not np.isfinite(vectors).all():
                raise ValueError("Embedding response has invalid shape or non-finite values")
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            if np.any(norms == 0):
                raise ValueError("Embedding response has zero-length vectors")
            vectors /= norms
            temp = path.with_suffix(".tmp")
            with temp.open("wb") as file:
                np.save(file, vectors)
            temp.replace(path)
            print(f"{model} {key}: {min(start + 64, len(texts))}/{len(texts)} saved", flush=True)
        batches.append(vectors)
    return np.concatenate(batches)


def evaluate(name: str, vectors: np.ndarray, ids: list[str], query_vectors: np.ndarray,
             query_ids: list[str], queries: dict, build_seconds: float) -> None:
    index = dense.DenseIndex(vectors, ids)
    begin = time.perf_counter()
    run = {q: index.search(v, config.RUN_DEPTH) for q, v in zip(query_ids, query_vectors)}
    search_ms = 1000 * (time.perf_counter() - begin) / len(query_ids)
    labels = {q: {queries[q]["source_arxiv_id"]: 2} for q in query_ids}
    rows = metrics.score_run(run, labels)
    for row in rows:
        row["query_type"] = queries[row["query_id"]]["query_type"]
    info = {"system": name, "papers": len(ids), "queries": len(query_ids),
            "dimensions": vectors.shape[1], "vector_bytes": vectors.nbytes,
            "setup_seconds": round(build_seconds, 2), "search_only_ms": round(search_ms, 2),
            "query_latency_note": "search_only_ms excludes query embedding; setup includes it"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.run.json").write_text(json.dumps(run), encoding="utf-8")
    (OUT / f"{name}.scores.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (OUT / f"{name}.info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")


def report_table() -> str:
    files = sorted(OUT.glob("*.scores.jsonl"))
    if not files:
        return "No embedding pilot scores yet."
    lines = ["Reduced-corpus screening only: easier than the 23,304-paper benchmark; "
             "**do not compare its scores directly with the main table**.",
             "All models use the identical saved subset and 100 dev queries. "
             "MRR/recall credit only the source paper; graded nDCG is not yet available. "
             "All inputs use title + abstract; local models retain their 512-token truncation "
             "while OpenAI receives the full input (up to 8,191 tokens).",
             "", "| Model | Papers | Dimensions | MRR@10 [95% CI] | R@10 | R@20 | Vector MB |",
             "|---|---|---|---|---|---|---|"]
    runs = {}
    for path in files:
        name = path.name.removesuffix(".scores.jsonl")
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        runs[name] = {r["query_id"]: r for r in rows}
        info = json.loads((OUT / f"{name}.info.json").read_text())
        mean, low, high = metrics.bootstrap_ci([r["mrr@10"] for r in rows])
        r10 = np.mean([r["recall@10"] for r in rows])
        r20 = np.mean([r["recall@20"] for r in rows])
        lines.append(f"| {name} | {info['papers']} | {info['dimensions']} | "
                     f"{mean:.3f} [{low:.3f}, {high:.3f}] | {r10:.3f} | {r20:.3f} | "
                     f"{info['vector_bytes'] / 1e6:.1f} |")
    if "gte-small" in runs:
        lines += ["", "| Model vs. GTE-small | Paired MRR difference [95% CI] |",
                  "|---|---|"]
        for name, run in runs.items():
            if name == "gte-small":
                continue
            qids = sorted(runs["gte-small"])
            if set(qids) != set(run):
                raise ValueError("Pilot score files have different query sets")
            delta, low, high = metrics.paired_diff_ci(
                [runs["gte-small"][q]["mrr@10"] for q in qids],
                [run[q]["mrr@10"] for q in qids])
            lines.append(f"| {name} | {delta:+.3f} [{low:+.3f}, {high:+.3f}] |")
    if set(MODELS) <= set(runs):
        qids = sorted(runs["text-embedding-3-small"])
        delta, low, high = metrics.paired_diff_ci(
            [runs["text-embedding-3-small"][q]["mrr@10"] for q in qids],
            [runs["text-embedding-3-large"][q]["mrr@10"] for q in qids])
        lines += ["", f"Large minus small: **{delta:+.3f} [{low:+.3f}, {high:+.3f}]** "
                  "(paired 95% interval). These are dev screening comparisons, not held-out wins."]
    cost_path = OUT / "usage.json"
    if cost_path.exists():
        lines += ["", "| Paid model | Requests | Accounted tokens | Accounted USD | API seconds |",
                  "|---|---|---|---|---|"]
        for model, usage in json.loads(cost_path.read_text()).items():
            lines.append(f"| {model} | {usage['requests']} | {usage['accounted_tokens']:,} | "
                         f"${usage['accounted_usd']:.4f} | {usage['api_seconds'] or 0:.1f} |")
        lines += ["", "Accounted cost includes conservative reservations for failed/unknown "
                  "requests and is not a provider invoice. $0.25 lifetime cap; no automatic retries."]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="make calls within approved $0.25 cap")
    args = parser.parse_args()
    papers, queries, split = load_inputs()
    qids = sorted(split["dev"])
    ids = select_ids(papers, queries, qids)
    texts = [paper_text(papers[a]) for a in ids]
    query_texts = [queries[q]["query"] for q in qids]
    counts, qcounts = token_counts(texts), token_counts(query_texts)
    fullcounts = token_counts([paper_text(p) for p in papers.values()])
    if max(counts + qcounts) > 8191 or min(counts + qcounts) == 0:
        raise ValueError("Embedding input must contain 1..8191 tokens; no silent truncation")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = {"ids": ids, "query_ids": qids, "paper_tokens": sum(counts),
                "query_tokens": sum(qcounts), "full_corpus_tokens": sum(fullcounts),
                "pricing_usd_per_million": {k: v["nanodollars_per_token"] / 1000
                                          for k, v in MODELS.items()},
                "approved_lifetime_usd": 0.25}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old != manifest:
            raise ValueError("Pilot corpus or price changed; preserve old run and review first")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Pilot tokens: {sum(counts) + sum(qcounts):,}; full corpus: {sum(fullcounts):,}")
    planned = 0.0
    for model, settings in MODELS.items():
        price = settings["nanodollars_per_token"] / 1e9
        cost = (sum(counts) + sum(qcounts)) * price
        planned += cost
        print(f"{model}: pilot ${cost:.4f}; full corpus estimate ${sum(fullcounts) * price:.4f}")
    if not args.run:
        return
    if planned > BUDGET_NANODOLLARS / 1e9:
        raise RuntimeError("Estimated combined pilot exceeds approved cap; no calls made")
    for model in MODELS:
        begin = time.perf_counter()
        try:
            vectors = paid_vectors(model, texts, counts, "papers")
            qvectors = paid_vectors(model, query_texts, qcounts, "queries")
        finally:
            (OUT / "usage.json").write_text(json.dumps(spending_summary(), indent=2), encoding="utf-8")
        evaluate(model, vectors, ids, qvectors, qids, queries, time.perf_counter() - begin)
    for model in ("gte-small", "bge-small"):
        begin = time.perf_counter()
        info = json.loads((config.EMBEDDINGS_DIR / f"{model}.json").read_text())
        offsets = {a: i for i, a in enumerate(info["ids"])}
        vectors = np.load(config.EMBEDDINGS_DIR / f"{model}.npy", mmap_mode="r")[
            [offsets[a] for a in ids]]
        qvectors = dense.embed_queries(model, query_texts)
        evaluate(model, vectors, ids, qvectors, qids, queries, time.perf_counter() - begin)
    (OUT / "report.md").write_text(report_table() + "\n", encoding="utf-8")
    print(report_table())


if __name__ == "__main__":
    main()
