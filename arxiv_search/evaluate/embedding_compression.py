"""Hosting check: can the paper embeddings be stored smaller without changing Stage 1?

The Decision36 retrieval baseline keeps 23,304 x 3,072 float32 OpenAI vectors (~286 MB),
most of a 500 MB Python function bundle. Two standard ways to shrink them:

    * lower precision: float16 (half the bytes) or int8 with one scale per paper (a quarter);
    * fewer dimensions: text-embedding-3 vectors are trained so a prefix of the numbers is
      itself a usable embedding (keep the first d numbers, then re-normalize).

Only the stored paper vectors change; the query vector is truncated the same way but kept
in float32, as a server would. BM25 scores and every Decision36 setting are frozen. Each
variant rebuilds the Stage 1 run from cached vectors and is compared with a float32
control rebuilt the same way, so only the compression differs.

The rule decides whether a variant is safe to host, not which ranking is better. It is
frozen before any variant is scored, uses only dev queries, and makes no API calls.

    python -m arxiv_search.evaluate.embedding_compression
"""

from __future__ import annotations

import hashlib
import json
import time

import numpy as np

from arxiv_search import config
from arxiv_search.evaluate import experiments as ex, fusion_experiment as fusion
from arxiv_search.evaluate import openai_full as full, results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.search.hybrid import fuse_working_baseline
from arxiv_search.search.text import paper_text

OUT = config.RESULTS_DIR / "embedding-compression"
CONTROL = "f32-3072"
VARIANTS = {  # name: (dimensions kept, storage type)
    CONTROL: (3072, "float32"), "f16-3072": (3072, "float16"), "int8-3072": (3072, "int8"),
    "f32-1536": (1536, "float32"), "f16-1536": (1536, "float16"), "int8-1536": (1536, "int8"),
    "f16-1024": (1024, "float16"), "f16-768": (768, "float16"), "int8-768": (768, "int8"),
    "f16-512": (512, "float16"), "f16-256": (256, "float16"),
}
SCORE_DEPTH = config.WORKING_BASELINE_SCORE_DEPTH
LABEL_LAYER = catalog.SHARED_LABELS_D46

PLAN = {
    "version": "embedding-compression-v1",
    "question": "Smallest stored form of the paper vectors that leaves Stage 1 effectively "
                "unchanged, for hosting.",
    "control": f"{CONTROL}: cached float32 vectors, rebuilt through the same code path",
    "variants": {n: {"dimensions": d, "storage": s} for n, (d, s) in VARIANTS.items()},
    "fixed": "Frozen BM25 top500 scores; Decision36 settings; query vector float32, truncated "
             "and re-normalized like the papers; int8 = symmetric per-paper scale max|x|/127.",
    "labels": "shared-labels/labels-d46.json (no new judging; unjudged top10 pairs count as 0).",
    "equivalent_if": {
        "reranker_input": "mean top50 overlap with the control >= 0.98 (the Decision46 "
                          "reranker sees exactly the Stage 1 top50)",
        "top10": "mean top10 overlap with the control >= 0.95",
        "quality": "nDCG@10 mean difference vs control >= -0.005 and grade2_recall@50 "
                   "difference >= -0.01",
        "coverage": "top10 judged share >= 0.98 (otherwise label gaps hide the effect)",
    },
    "recommendation": "Smallest equivalent variant by bytes; ties prefer float16 (no "
                      "dequantization step).",
    "api_calls": 0, "held_out_queries_used": False, "changes_baseline": False,
}


def load_vectors(texts: list[str]) -> np.ndarray:
    batches = []
    for start in range(0, len(texts), full.BATCH_SIZE):
        vectors = full.read_cache(texts[start:start + full.BATCH_SIZE], full.CACHE)
        if vectors is None:
            raise FileNotFoundError("Embedding cache incomplete; this check never calls the API")
        batches.append(vectors)
    return np.concatenate(batches)


def truncate(vectors: np.ndarray, dims: int) -> np.ndarray:
    """Keep the first `dims` numbers and re-normalize so dot product stays cosine."""
    if not 0 < dims <= vectors.shape[1]:
        raise ValueError("dims must be between 1 and the stored width")
    cut = np.ascontiguousarray(vectors[:, :dims], dtype=np.float32)
    return cut / np.linalg.norm(cut, axis=1, keepdims=True)


def store(vectors: np.ndarray, storage: str) -> tuple[np.ndarray, np.ndarray | None]:
    """Return (stored matrix, per-paper scale or None) exactly as a server would keep them."""
    if storage == "float32":
        return vectors.astype(np.float32), None
    if storage == "float16":
        return vectors.astype(np.float16), None
    if storage == "int8":
        scale = np.abs(vectors).max(axis=1, keepdims=True) / 127.0
        return np.clip(np.rint(vectors / scale), -127, 127).astype(np.int8), scale.astype(np.float32)
    raise ValueError(f"Unknown storage type: {storage}")


def stored_bytes(matrix: np.ndarray, scale: np.ndarray | None) -> int:
    return matrix.nbytes + (0 if scale is None else scale.nbytes)


def similarities(matrix: np.ndarray, scale: np.ndarray | None, queries: np.ndarray) -> np.ndarray:
    """Query x paper cosine scores computed in float32 from the stored form."""
    scores = queries.astype(np.float32) @ matrix.astype(np.float32).T
    return scores if scale is None else scores * scale[:, 0][None, :]


def top_scores(row: np.ndarray, ids: list[str], depth: int) -> dict[str, float]:
    order = np.argsort(-row, kind="stable")[:depth]
    return {ids[i]: float(row[i]) for i in order}


def overlap(a: list[str], b: list[str], k: int) -> float:
    return len(set(a[:k]) & set(b[:k])) / k


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", PLAN)
    corpus, queries, _, splits = ex.load_eval()
    papers = {p["arxiv_id"]: p for p in corpus}
    ids = list(papers)
    qids = sorted(splits["dev"])
    if set(qids) & set(splits["test"]):
        raise ValueError("Dev/test overlap")
    paper_vectors = load_vectors([paper_text(p) for p in corpus])
    query_vectors = load_vectors([queries[q]["query"] for q in qids])
    inputs_path = config.RESULTS_DIR / "score-fusion-dev" / "input-scores.json"
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    lexical = {q: dict(inputs[q]["lexical"]) for q in qids}
    _, label_raw, shared, _ = catalog.load_shared_labels(config.RESULTS_DIR, LABEL_LAYER)

    runs, info = {}, {}
    for name, (dims, storage) in VARIANTS.items():
        matrix, scale = store(truncate(paper_vectors, dims), storage)
        begin = time.perf_counter()
        scores = similarities(matrix, scale, truncate(query_vectors, dims))
        seconds = time.perf_counter() - begin
        runs[name] = {q: fuse_working_baseline(lexical[q], top_scores(scores[i], ids, SCORE_DEPTH),
                                               k=config.RUN_DEPTH) for i, q in enumerate(qids)}
        fusion.validate_run(name, runs[name], qids, papers, exact_depth=config.RUN_DEPTH)
        info[name] = {"dimensions": dims, "storage": storage,
                      "megabytes": stored_bytes(matrix, scale) / 1e6,
                      "batched_similarity_ms_per_query": seconds * 1000 / len(qids)}
    frozen_path = config.RESULTS_DIR / "shortlist-score-dev" / f"{config.WORKING_BASELINE_SYSTEM}.run.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    control_check = {"top10_identical_queries": sum(runs[CONTROL][q][:10] == frozen[q][:10] for q in qids),
                     "top50_overlap_mean": float(np.mean([overlap(runs[CONTROL][q], frozen[q], 50)
                                                          for q in qids]))}

    entries = {n: {"run": run, "paths": [], "metadata": info[n]} for n, run in runs.items()}
    scored = catalog.score_catalog(entries, shared, papers, queries, qids, CONTROL)
    control = scored[CONTROL]
    rows = {}
    for name in VARIANTS:
        s = scored[name]
        per = {r["query_id"]: r for r in s["per_query"]}
        base = {r["query_id"]: r for r in control["per_query"]}
        diff = [per[q]["ndcg@10"] - base[q]["ndcg@10"] for q in qids]
        g2 = [per[q]["grade2_recall@50"] - base[q]["grade2_recall@50"] for q in qids
              if base[q]["grade2_recall@50"] is not None]
        rows[name] = {
            **info[name],
            "ndcg@10": s["all"]["ndcg@10"]["mean"],
            "ndcg@10_diff_vs_control": float(np.mean(diff)),
            "queries_ndcg_changed": sum(abs(d) > 1e-12 for d in diff),
            "source_mrr@10": s["all"]["source_mrr@10"]["mean"],
            "grade2_recall@50": s["all"]["grade2_recall@50"]["mean"],
            "grade2_recall@50_diff_vs_control": float(np.mean(g2)),
            "top10_overlap": float(np.mean([overlap(runs[name][q], runs[CONTROL][q], 10) for q in qids])),
            "top50_overlap": float(np.mean([overlap(runs[name][q], runs[CONTROL][q], 50) for q in qids])),
            "top50_set_identical_queries": sum(set(runs[name][q][:50]) == set(runs[CONTROL][q][:50])
                                               for q in qids),
            "top10_judged_share": float(np.mean([r["judged@10"] for r in s["per_query"]])),
        }
        r = rows[name]
        r["checks"] = {
            "reranker_input": r["top50_overlap"] >= 0.98, "top10": r["top10_overlap"] >= 0.95,
            "quality": r["ndcg@10_diff_vs_control"] >= -0.005
                       and r["grade2_recall@50_diff_vs_control"] >= -0.01,
            "coverage": r["top10_judged_share"] >= 0.98,
        }
        r["equivalent"] = all(r["checks"].values())
    ok = [n for n in VARIANTS if rows[n]["equivalent"]]
    pick = min(ok, key=lambda n: (rows[n]["megabytes"], VARIANTS[n][1] != "float16")) if ok else None
    report = {
        "plan": PLAN, "control_vs_frozen_baseline": control_check, "variants": rows,
        "recommended": pick, "api_calls": 0, "promoted": False,
        "inputs": {"lexical_scores_sha256": hashlib.sha256(inputs_path.read_bytes()).hexdigest(),
                   "labels_sha256": hashlib.sha256(label_raw).hexdigest(),
                   "frozen_baseline_run": frozen_path.relative_to(config.RESULTS_DIR).as_posix()},
    }
    fusion._write_json(OUT / "report.json", report)
    write_markdown(report, OUT / "report.md")
    print(json.dumps({"recommended": pick, "control_check": control_check}, indent=2))


def write_markdown(report: dict, path) -> None:
    c = report["control_vs_frozen_baseline"]
    lines = [
        "# Embedding compression check (hosting)", "",
        "Stage 1 (Decision36) rebuilt from cached OpenAI vectors stored in smaller forms. Only "
        "the stored paper vectors change; BM25 scores and every setting are frozen. Dev queries "
        "only, existing labels, zero API calls. Differences are against the float32 control "
        "rebuilt the same way.", "",
        f"Control sanity: top10 identical to the frozen Decision36 run on "
        f"{c['top10_identical_queries']}/100 queries; top50 overlap {c['top50_overlap_mean']:.4f} "
        "(the cached scores differ only by float rounding).", "",
        "| Variant | MB | nDCG@10 | Δ vs control | Queries changed | Grade-2 R@50 Δ | Top10 overlap "
        "| Top50 overlap | Identical top50 sets | Judged@10 | Equivalent |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, r in report["variants"].items():
        failed = [k for k, v in r["checks"].items() if not v]
        lines.append(
            f"| `{name}` | {r['megabytes']:.0f} | {r['ndcg@10']:.4f} | {r['ndcg@10_diff_vs_control']:+.4f} | "
            f"{r['queries_ndcg_changed']} | {r['grade2_recall@50_diff_vs_control']:+.4f} | "
            f"{r['top10_overlap']:.3f} | {r['top50_overlap']:.3f} | {r['top50_set_identical_queries']}/100 | "
            f"{r['top10_judged_share']:.3f} | " + ("**yes**" if r["equivalent"] else
                                                 "no (" + ", ".join(failed) + ")") + " |")
    lines += ["", f"Recommended (smallest equivalent): `{report['recommended']}`.", "",
              "Rule (frozen before scoring): " + "; ".join(
                  f"{k}: {v}" for k, v in report["plan"]["equivalent_if"].items()) + ".", "",
              "Cautions: dev queries only; unjudged top10 papers count as not relevant, so a "
              "variant that surfaces new papers can look slightly worse than it is. This "
              "decides storage for hosting only; it does not change any baseline."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
