"""Estimate the cost of a full-text index vs. the current title + abstract index.

Combines two *measurements* with a few documented *assumptions*:

  measured   data/experiments/fulltext_sample.json  (from measure_fulltext.py)
  measured   embedding throughput of BGE-small on this machine's CPU
  assumed    384-dim float32 vectors, pgvector HNSW index overhead, arXiv 3 s delay

Usage:
    python experiments/estimate_costs.py
"""

from __future__ import annotations

import json
import statistics
import time

from sentence_transformers import SentenceTransformer

from arxiv_search import config

MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
BYTES_PER_VECTOR = DIM * 4  # float32
HNSW_OVERHEAD = 2.0  # pgvector HNSW index is roughly the size of the vectors again
BYTES_PER_TOKEN_TEXT = 4.5  # stored UTF-8 text, roughly 4-5 bytes per token for English
FREE_DB_MB = 500  # Supabase / Neon free-tier database size


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    return values[int(p * (len(values) - 1))]


def measure_throughput(model: SentenceTransformer, n_tokens: int, n_texts: int = 64) -> float:
    """Texts per second for inputs of about n_tokens tokens."""
    text = " ".join(["retrieval"] * n_tokens)  # one token per word for this tokenizer
    texts = [text] * n_texts
    model.encode(texts[:8], batch_size=32)  # warm-up
    start = time.perf_counter()
    model.encode(texts, batch_size=32)
    return n_texts / (time.perf_counter() - start)


def main() -> None:
    rows = json.loads((config.EXPERIMENTS_DIR / "fulltext_sample.json").read_text())
    ok = [r for r in rows if r["html_available"]]
    corpus = [json.loads(l) for l in open(config.PROCESSED_DIR / "corpus.jsonl", encoding="utf-8")]
    n_docs = len(corpus)

    ta = [r["title_abstract_tokens"] for r in ok]
    body = [r["body_tokens"] for r in ok]
    chunks = [r["chunks"] for r in ok]
    ratio = [b / a for a, b in zip(ta, body)]
    novel_vocab = [r["body_vocab_not_in_abstract"] / r["body_vocab"] for r in ok]

    print(f"Sample: {len(rows)} papers, HTML available for {len(ok)} ({len(ok)/len(rows):.0%})\n")
    print("Per paper (BGE tokenizer)        median     p90")
    print(f"  title + abstract tokens      {statistics.median(ta):8.0f} {percentile(ta,.9):7.0f}")
    print(f"  full body tokens             {statistics.median(body):8.0f} {percentile(body,.9):7.0f}")
    print(f"  body / abstract ratio        {statistics.median(ratio):8.1f}x {percentile(ratio,.9):6.1f}x")
    print(f"  512-token chunks per paper   {statistics.median(chunks):8.0f} {percentile(chunks,.9):7.0f}")
    print(f"  table tokens (excluded)      {statistics.median(r['table_tokens'] for r in ok):8.0f}")
    print(f"  reference tokens (excluded)  {statistics.median(r['reference_tokens'] for r in ok):8.0f}")
    print(f"  body words not in abstract   {statistics.median(novel_vocab):8.0%}")

    mean_chunks = statistics.mean(chunks)
    mean_body = statistics.mean(body)
    mean_ta = statistics.mean(ta)
    mean_fetch = statistics.mean(r["fetch_seconds"] for r in rows)

    print("\nMeasuring embedding throughput on this CPU ...")
    model = SentenceTransformer(MODEL, device="cpu")
    tps_abstract = measure_throughput(model, 290)
    tps_chunk = measure_throughput(model, 512)
    print(f"  ~290-token texts: {tps_abstract:.1f}/s    512-token chunks: {tps_chunk:.1f}/s")

    def scenario(name: str, n_papers: int, vectors: float, tokens: float, download_s: float):
        vector_mb = vectors * BYTES_PER_VECTOR * (1 + HNSW_OVERHEAD) / 1e6
        text_mb = tokens * BYTES_PER_TOKEN_TEXT / 1e6
        tps = tps_abstract if vectors == n_papers else tps_chunk
        return {
            "scenario": name,
            "papers": n_papers,
            "vectors": round(vectors),
            "tokens_embedded_M": round(tokens / 1e6, 1),
            "download_hours": round(download_s / 3600, 1),
            "embed_hours_per_model": round(vectors / tps / 3600, 2),
            "db_mb": round(vector_mb + text_mb),
            "fits_free_db": vector_mb + text_mb < FREE_DB_MB,
        }

    per_paper_download = config.REQUEST_DELAY_SECONDS + mean_fetch
    cc_share = sum("creativecommons" in (d["license"] or "") for d in corpus) / n_docs
    ir = [d for d in corpus if d["primary_category"] == "cs.IR"]
    ir_cc = sum("creativecommons" in (d["license"] or "") for d in ir)

    scenarios = [
        scenario("A. title+abstract (current)", n_docs, n_docs, n_docs * mean_ta, 0),
        scenario("B. full text, all papers", n_docs, n_docs * mean_chunks,
                 n_docs * mean_body, n_docs * per_paper_download),
        scenario("C. full text, cs.IR CC-licensed", ir_cc, ir_cc * mean_chunks,
                 ir_cc * mean_body, ir_cc * per_paper_download),
    ]
    print(f"\nCreative Commons share: {cc_share:.0%} of corpus; cs.IR CC papers: {ir_cc}\n")
    header = list(scenarios[0])
    print(" | ".join(header))
    for s in scenarios:
        print(" | ".join(str(s[h]) for h in header))

    out = {
        "sample_size": len(rows),
        "html_available": len(ok),
        "throughput_texts_per_s": {"abstract_290": tps_abstract, "chunk_512": tps_chunk},
        "scenarios": scenarios,
    }
    (config.EXPERIMENTS_DIR / "cost_estimate.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
