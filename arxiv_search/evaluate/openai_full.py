"""Full-corpus large-3072 embeddings, dev only, with a separate $1.25 lifetime cap.

Default: exact-token, cache-aware dry run. Add --run for approved paid requests.
No automatic retries; unknown outcomes retain their reservation. Pilot files are
read-only. Search timings exclude offline batched query embedding/network time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
import uuid

import httpx
import numpy as np
from dotenv import load_dotenv

from arxiv_search import config
from arxiv_search.search.dense import DenseIndex
from arxiv_search.search.hybrid import fuse
from arxiv_search.search.text import paper_text

MODEL = "text-embedding-3-large"
DIMENSIONS = 3072
PRICE = 130  # integer nanodollars/token, $0.13 per million
CAP = 1_250_000_000
BATCH_SIZE = 64
CACHE = config.EMBEDDINGS_DIR / "openai-full-large"
LEDGER = config.DATA_DIR / "openai" / "embedding-full-large.sqlite3"
DENSE_NAME = "dense-openai-large"
HYBRID_NAME = "hybrid-openai-large+rrf+w=0.5+c=10"
ENDPOINT = "https://api.openai.com/v1/embeddings"
TIMING_SCOPE = "sequential_search_excludes_offline_query_embedding"


def register_systems(registry: dict, system_factory) -> None:
    """Expose saved results without importing experiments or starting paid calls.

    experiments can call register_systems(SYSTEMS, System) after defining them.
    Running these systems uses this module's cache-aware, budget-guarded CLI,
    rather than the generic runner's incompatible online-query timing protocol.
    """
    def build(_corpus):
        raise RuntimeError(
            "Run python -m arxiv_search.evaluate.openai_full for a dry preflight, "
            "then add --run to evaluate (cache-only when embeddings already exist)"
        )

    factors = {"model": "openai-large", "dimensions": DIMENSIONS, "full_corpus": True}
    registry[DENSE_NAME] = system_factory(
        build, "Dense: OpenAI text-embedding-3-large, title + abstract, cosine; "
        "offline query embeddings; latency excludes API", factors)
    registry[HYBRID_NAME] = system_factory(
        build, "Hybrid: best BM25 + OpenAI large, equal RRF c=10; "
        "offline query embeddings; latency excludes API",
        {**factors, "hybrid": True, "method": "rrf", "semantic_weight": 0.5, "c": 10})

    def build_working(_corpus):
        raise RuntimeError(
            "The working baseline is evaluated from cached rankings with "
            "python -m arxiv_search.evaluate.fusion_review; live serving is not deployed"
        )

    registry[config.WORKING_BASELINE_SYSTEM] = system_factory(
        build_working, "Working baseline: best BM25 + OpenAI large, "
        "55% semantic / 45% lexical RRF c=30, depth=100; cached dev review",
        {**factors, "hybrid": True, "method": config.WORKING_BASELINE_METHOD,
         "semantic_weight": config.WORKING_BASELINE_SEMANTIC_WEIGHT,
         "c": config.WORKING_BASELINE_RRF_C, "depth": config.WORKING_BASELINE_DEPTH})


class EmbeddingError(RuntimeError):
    """Sanitized failure; never expose credentials, input text or provider bodies."""


class BudgetExceeded(EmbeddingError):
    pass


def token_counts(texts: list[str]) -> list[int]:
    import tiktoken

    encoder = tiktoken.get_encoding("cl100k_base")
    counts = [len(encoder.encode(t, disallowed_special=())) for t in texts]
    if not counts or any(not 1 <= n <= 8191 for n in counts):
        raise ValueError("Inputs must contain 1..8191 tokens; no truncation")
    return counts


def reservation_tokens(counts: list[int]) -> int:
    return sum(counts) + max(8 * len(counts), math.ceil(sum(counts) * 0.01))


class Ledger:
    """BEGIN IMMEDIATE serializes reservations across concurrent CLI processes."""

    def __init__(self, path: Path = LEDGER):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS calls
                (id TEXT PRIMARY KEY, reserved_tokens INTEGER NOT NULL,
                 accounted_tokens INTEGER NOT NULL, nanodollars INTEGER NOT NULL,
                 status TEXT NOT NULL, seconds REAL)""")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def summary(self) -> dict:
        with self.connect() as db:
            n, cost, seconds = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(nanodollars),0), COALESCE(SUM(seconds),0) FROM calls"
            ).fetchone()
        return {"requests": n, "accounted_usd": cost / 1e9, "api_seconds": seconds}

    def reserve(self, tokens: int) -> str:
        if type(tokens) is not int or tokens <= 0:
            raise ValueError("Positive integer reservation required")
        request_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            used = db.execute("SELECT COALESCE(SUM(nanodollars),0) FROM calls").fetchone()[0]
            if used + tokens * PRICE > CAP:
                raise BudgetExceeded("$1.25 lifetime cap reached; no request sent")
            db.execute("INSERT INTO calls VALUES (?,?,?,?,?,NULL)",
                       (request_id, tokens, tokens, tokens * PRICE, "reserved"))
        return request_id

    def settle(self, request_id: str, tokens: int, seconds: float) -> None:
        if type(tokens) is not int or tokens < 0:
            raise EmbeddingError("Invalid usage; reservation retained")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT reserved_tokens,status FROM calls WHERE id=?", (request_id,)
            ).fetchone()
            if row is None or row[1] != "reserved":
                raise EmbeddingError("Unknown or finalized reservation")
            db.execute("""UPDATE calls SET accounted_tokens=?,nanodollars=?,
                status='complete',seconds=? WHERE id=?""",
                       (tokens, tokens * PRICE, seconds, request_id))
        if tokens > row[0]:
            raise EmbeddingError("Usage exceeded reservation; actual cost recorded, stopping")


def fingerprint(texts: list[str]) -> str:
    # Match the pilot's exact JSON encoding, not just IDs or token counts.
    return hashlib.sha256(json.dumps([MODEL, DIMENSIONS, texts]).encode()).hexdigest()


def validate_vectors(values, rows: int) -> np.ndarray:
    vectors = np.asarray(values, dtype=np.float32)
    if vectors.shape != (rows, DIMENSIONS) or not np.isfinite(vectors).all():
        raise EmbeddingError("Embedding cache/response shape or values invalid")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 0):
        raise EmbeddingError("Embedding cache/response contains invalid norms")
    return vectors / norms


def read_cache(texts: list[str], cache: Path) -> np.ndarray | None:
    path = cache / f"{fingerprint(texts)}.npy"
    meta = path.with_suffix(".json")
    if not path.exists() and not meta.exists():
        return None
    try:
        info = json.loads(meta.read_text())
        if info != {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "fingerprint": fingerprint(texts)}:
            raise ValueError()
        return validate_vectors(np.load(path, allow_pickle=False), len(texts))
    except Exception:
        raise EmbeddingError("Corrupt full embedding cache; no paid repair attempted") from None


def write_cache(texts: list[str], vectors: np.ndarray, cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{fingerprint(texts)}.npy"
    # Unique staging files avoid concurrent writers sharing an incomplete file.
    staging = path.with_suffix(f".{uuid.uuid4().hex}.pending")
    with staging.open("wb") as file:
        np.save(file, vectors, allow_pickle=False)
    checksum = hashlib.sha256(staging.read_bytes()).hexdigest()
    staging.replace(path)
    meta = path.with_suffix(".json")
    staging_meta = meta.with_suffix(f".{uuid.uuid4().hex}.pending")
    staging_meta.write_text(json.dumps({"sha256": checksum, "fingerprint": fingerprint(texts)}))
    staging_meta.replace(meta)


def pilot_vectors(papers: dict, queries: dict, dev_ids: list[str]) -> dict[str, np.ndarray]:
    """Only reuse pilot arrays if the *whole current text list* matches its hash."""
    manifest_path = config.RESULTS_DIR / "embedding-pilot" / "manifest.json"
    if not manifest_path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text())
    if set(manifest["query_ids"]) != set(dev_ids):
        raise EmbeddingError("Pilot query IDs differ from dev; refusing reuse")
    result = {}
    lists = ([paper_text(papers[a]) for a in manifest["ids"]],
             [queries[q]["query"] for q in manifest["query_ids"]])
    for texts in lists:
        folder = config.EMBEDDINGS_DIR / "openai-pilot" / MODEL / fingerprint(texts)
        if not folder.exists():
            continue  # Changed content is not a cache hit.
        for start in range(0, len(texts), BATCH_SIZE):
            chunk = texts[start:start + BATCH_SIZE]
            path = folder / f"{start}.npy"
            if path.exists():
                try:
                    vectors = validate_vectors(np.load(path, allow_pickle=False), len(chunk))
                except Exception:
                    raise EmbeddingError("Invalid pilot cache; pilot files left untouched") from None
                result.update(zip(chunk, vectors))
    return result


def request_vectors(texts: list[str], counts: list[int], ledger: Ledger,
                    api_key: str) -> np.ndarray:
    request_id = ledger.reserve(reservation_tokens(counts))
    begin = time.perf_counter()
    try:
        # No proxy environment, redirects or transport retries; only this fixed host.
        with httpx.Client(timeout=120, follow_redirects=False, trust_env=False) as client:
            response = client.post(ENDPOINT, headers={"Authorization": f"Bearer {api_key}"},
                                   json={"model": MODEL, "input": texts,
                                         "dimensions": DIMENSIONS, "encoding_format": "float"})
        if response.status_code != 200:
            raise EmbeddingError("Embedding HTTP failure; reservation retained; no retry")
        body = response.json()
        usage = body["usage"]
        tokens = usage["total_tokens"]
        if (type(tokens) is not int or tokens <= 0
                or type(usage.get("prompt_tokens")) is not int
                or usage["prompt_tokens"] != tokens):
            raise EmbeddingError("Untrustworthy embedding usage; reservation retained")
        ledger.settle(request_id, tokens, time.perf_counter() - begin)
        data = body["data"]
        if any(type(r["index"]) is not int for r in data):
            raise EmbeddingError("Invalid embedding indices")
        data = sorted(data, key=lambda row: row["index"])
        if [r["index"] for r in data] != list(range(len(texts))):
            raise EmbeddingError("Missing or duplicate embedding indices")
        return validate_vectors([r["embedding"] for r in data], len(texts))
    except EmbeddingError:
        raise
    except Exception:
        raise EmbeddingError("Embedding request failed; reservation retained; no retry") from None


def planned_tokens(texts: list[str], counts: list[int], reused: dict,
                   cache: Path) -> tuple[int, int]:
    tokens = reused_rows = 0
    for start in range(0, len(texts), BATCH_SIZE):
        chunk = texts[start:start + BATCH_SIZE]
        if read_cache(chunk, cache) is not None:
            reused_rows += len(chunk)
            continue
        missing = [n for t, n in zip(chunk, counts[start:start + BATCH_SIZE]) if t not in reused]
        reused_rows += len(chunk) - len(missing)
        if missing:
            tokens += reservation_tokens(missing)
    return tokens, reused_rows


def embed(texts: list[str], counts: list[int], reused: dict, cache: Path,
          ledger: Ledger, api_key: str) -> np.ndarray:
    batches = []
    for start in range(0, len(texts), BATCH_SIZE):
        chunk = texts[start:start + BATCH_SIZE]
        vectors = read_cache(chunk, cache)
        if vectors is None:
            missing = [i for i, t in enumerate(chunk) if t not in reused]
            vectors = np.empty((len(chunk), DIMENSIONS), dtype=np.float32)
            if missing:
                vectors[missing] = request_vectors(
                    [chunk[i] for i in missing], [counts[start + i] for i in missing], ledger, api_key)
            for i, text in enumerate(chunk):
                if i not in missing:
                    vectors[i] = reused[text]
            vectors = validate_vectors(vectors, len(chunk))
            write_cache(chunk, vectors, cache)
        batches.append(vectors)
        print(f"Cached {min(start + BATCH_SIZE, len(texts))}/{len(texts)}", flush=True)
    return np.concatenate(batches)


def ranked_runs(index: DenseIndex, lexical, qids: list[str], query_texts: list[str],
                qvectors: np.ndarray) -> tuple[dict, dict, dict]:
    """Time sequential single-query matrix search and full BM25+dense+fusion, not batches."""
    semantic, hybrid = {}, {}
    dense_seconds = hybrid_seconds = 0.0
    for qid, text, vector in zip(qids, query_texts, qvectors):
        begin = time.perf_counter()
        semantic[qid] = index.search(vector, config.RUN_DEPTH)
        dense_seconds += time.perf_counter() - begin
        begin = time.perf_counter()
        lexical_ranking = lexical(text)
        dense_ranking = index.search(vector, config.RUN_DEPTH)
        hybrid[qid] = fuse(lexical_ranking, dense_ranking, method="rrf", semantic_weight=0.5,
                           c=10, depth=config.RUN_DEPTH, k=config.RUN_DEPTH)
        hybrid_seconds += time.perf_counter() - begin
    return semantic, hybrid, {"dense_ms": dense_seconds * 1000 / len(qids),
                              "hybrid_ms": hybrid_seconds * 1000 / len(qids)}


def main() -> None:
    from arxiv_search.evaluate import experiments as ex

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    corpus, queries, _, splits = ex.load_eval()
    ids = [p["arxiv_id"] for p in corpus]
    qids = sorted(splits["dev"])  # Never embed test queries.
    texts = [paper_text(p) for p in corpus]
    query_texts = [queries[q]["query"] for q in qids]
    counts, qcounts = token_counts(texts), token_counts(query_texts)
    reused = pilot_vectors(dict(zip(ids, corpus)), queries, qids)
    planned, paper_hits = planned_tokens(texts, counts, reused, CACHE)
    qplanned, query_hits = planned_tokens(query_texts, qcounts, reused, CACHE)
    # Dry runs do not create or alter any ledger.
    spent = Ledger(LEDGER).summary() if LEDGER.exists() else {"accounted_usd": 0}
    preflight = {"papers": len(ids), "dev_queries": len(qids),
                 "paper_tokens": sum(counts), "dev_query_tokens": sum(qcounts),
                 "cached_papers": paper_hits, "cached_queries": query_hits,
                 "reserved_remaining_usd": (planned + qplanned) * PRICE / 1e9,
                 "accounted_usd": spent["accounted_usd"], "lifetime_cap_usd": CAP / 1e9,
                 "price_usd_per_million": 0.13}
    print(json.dumps(preflight, indent=2), flush=True)
    if spent["accounted_usd"] + preflight["reserved_remaining_usd"] > CAP / 1e9:
        raise BudgetExceeded("Preflight exceeds remaining $1.25 cap; no calls made")
    if not args.run:
        return
    load_dotenv(config.PROJECT_ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and planned + qplanned:
        raise EmbeddingError("OPENAI_API_KEY missing from local environment")
    ledger = Ledger(LEDGER)
    begin = time.perf_counter()
    vectors = embed(texts, counts, reused, CACHE, ledger, api_key or "")
    paper_seconds = time.perf_counter() - begin
    begin = time.perf_counter()
    qvectors = embed(query_texts, qcounts, reused, CACHE, ledger, api_key or "")
    query_seconds = time.perf_counter() - begin
    begin = time.perf_counter()
    index = DenseIndex(vectors, ids)
    dense_init = time.perf_counter() - begin
    begin = time.perf_counter()
    lexical = ex.bm25_system(ex.BM25_BEST).build(corpus)
    bm25_init = time.perf_counter() - begin
    if isinstance(lexical, tuple):
        lexical = lexical[0]
    semantic, hybrid, timing = ranked_runs(index, lexical, qids, query_texts, qvectors)
    query_lookup = dict(zip(query_texts, qvectors))

    def offline_dense(query: str) -> list[str]:
        return index.search(query_lookup[query], config.RUN_DEPTH)

    def offline_hybrid(query: str) -> list[str]:
        return fuse(lexical(query), offline_dense(query), method="rrf", semantic_weight=0.5,
                    c=10, depth=config.RUN_DEPTH, k=config.RUN_DEPTH)

    factors = {"model": "openai-large", "dimensions": DIMENSIONS, "full_corpus": True}
    ex.SYSTEMS[DENSE_NAME] = ex.System(
        lambda _: offline_dense, "Dense: OpenAI text-embedding-3-large, title + abstract, cosine; "
        "offline query embeddings; latency excludes API", factors)
    ex.SYSTEMS[HYBRID_NAME] = ex.System(
        lambda _: offline_hybrid, "Hybrid: best BM25 + OpenAI large, equal RRF c=10; "
        "offline query embeddings; latency excludes API",
        {**factors, "hybrid": True, "method": "rrf", "semantic_weight": 0.5, "c": 10})
    extra = {"timing_scope": TIMING_SCOPE,
             "papers": len(ids), "dimensions": DIMENSIONS, "vector_bytes": vectors.nbytes,
             "paper_embedding_and_cache_seconds": paper_seconds,
             "offline_batched_query_embedding_and_cache_seconds": query_seconds,
             "dense_index_initialization_seconds": dense_init,
             "bm25_initialization_seconds": bm25_init,
             "preflight": preflight, "embedding_ledger": ledger.summary()}
    for name, run, initialization, ms in (
        (DENSE_NAME, semantic, dense_init, timing["dense_ms"]),
        (HYBRID_NAME, hybrid, bm25_init + dense_init, timing["hybrid_ms"]),
    ):
        info = ex.save_run(name, "dev", run, initialization, ms, extra)
        print(json.dumps(info, indent=2), flush=True)


if __name__ == "__main__":
    main()
