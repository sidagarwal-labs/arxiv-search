"""Cached scored-fusion/depth experiments; never embed or promote.

python -m arxiv_search.evaluate.score_fusion_experiment
python -m arxiv_search.evaluate.score_fusion_experiment --label --max-calls 46
"""

from __future__ import annotations

import hashlib
import json
import argparse

import numpy as np

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, fusion_review as review
from arxiv_search.evaluate import graded, judge, metrics, openai_full as full
from arxiv_search.search.hybrid import fuse, fuse_rrf_baseline
from arxiv_search.search.score_fusion import fuse_scores, fuse_top1_bonus
from arxiv_search.search.text import paper_text

OUT = config.RESULTS_DIR / "score-fusion-dev"
DEPTH = 500


def cached_vectors(texts: list[str]) -> np.ndarray:
    """Read only the exact full-run caches; never call embed or create a ledger."""
    chunks = []
    for start in range(0, len(texts), full.BATCH_SIZE):
        vectors = full.read_cache(texts[start:start + full.BATCH_SIZE], full.CACHE)
        if vectors is None:
            raise ValueError(f"Missing exact embedding cache at batch {start}; no API repair")
        chunks.append(vectors)
    if not chunks:
        raise ValueError("No texts to retrieve")
    return np.concatenate(chunks)


def top_scores(ids: list[str], scores: np.ndarray, *, positive_only: bool) -> dict[str, float]:
    if scores.shape != (len(ids),) or not np.isfinite(scores).all():
        raise ValueError("Invalid retrieval scores")
    order = np.argsort(-scores, kind="stable")[:DEPTH]
    return {ids[i]: float(scores[i]) for i in order if not positive_only or scores[i] > 0}


def build_runs(scored: dict) -> tuple[dict, dict]:
    runs, settings = {}, {}
    for normalization in ("max", "minmax"):
        for weight in (0.35, 0.55, 0.75):
            for depth in (100, 500):
                name = f"score-{normalization}+w={weight:g}+d={depth}"
                options = dict(normalization=normalization, semantic_weight=weight,
                               depth=depth, k=100)
                runs[name] = {q: fuse_scores(s["lexical"], s["semantic"], **options)
                              for q, s in scored.items()}
                settings[name] = options
    for depth in (200, 500):
        name = f"fusion-rrf+w=0.55+d={depth}+c=30"
        runs[name] = {q: fuse(list(s["lexical"]), list(s["semantic"]), semantic_weight=0.55,
                              c=30, depth=depth, k=100) for q, s in scored.items()}
        settings[name] = dict(method="rrf", semantic_weight=0.55, c=30, depth=depth, k=100)
    for bonus in (0.1, 0.25):
        name = f"fusion-top1bonus+b={bonus:g}+w=0.55+d=100+c=30"
        runs[name] = {q: fuse_top1_bonus(list(s["lexical"]), list(s["semantic"]), bonus=bonus)
                      for q, s in scored.items()}
        settings[name] = dict(method="rrf-top1bonus", bonus=bonus, depth=100, k=100)
    return runs, settings


def summarize(rows: dict, baseline: str) -> dict:
    result = {}
    for name, values in rows.items():
        result[name] = {}
        for kind in ("all", *sorted({r["query_type"] for r in values})):
            group = [r for r in values if kind == "all" or r["query_type"] == kind]
            control = [r for r in rows[baseline] if kind == "all" or r["query_type"] == kind]
            complete = all(r["judged@10"] == 1 for r in group + control)
            fields = {}
            for field in values[0]:
                if field in ("query_id", "query_type"):
                    continue
                numbers = [r[field] for r in group if r[field] is not None]
                fields[field] = {
                    "n": len(numbers), "mean": sum(numbers) / len(numbers) if numbers else None,
                    "paired_vs_working": (fusion.paired_rows(control, group, field)
                                          if complete or field.startswith("source_") else None),
                }
            result[name][kind] = fields
    return result


def main(argv: list[str] | None = None) -> None:
    from arxiv_search.evaluate.experiments import BM25_BEST, bm25_index

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", action="store_true", help="explicitly enable incremental judging")
    parser.add_argument("--max-calls", type=int, default=46)
    args = parser.parse_args(argv)
    if args.max_calls < 0:
        parser.error("--max-calls must be nonnegative")
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    if set(qids) & set(split["test"]):
        raise ValueError("Dev/test overlap")
    snapshot_path = fusion.OUT / "labels.json"
    snapshot_raw = snapshot_path.read_bytes()
    snapshot = json.loads(snapshot_raw)
    if not snapshot["complete"] or set(snapshot["labels"]) != set(qids):
        raise ValueError("Expected complete frozen dev snapshot")
    if snapshot["rubric_version"] != judge.RUBRIC_VERSION:
        raise ValueError("Rubric changed since frozen snapshot")
    if snapshot["human_workbook_sha256"] != hashlib.sha256(graded.SHEET_PATH.read_bytes()).hexdigest():
        raise ValueError("Human workbook changed since frozen snapshot")
    corpus = list(papers.values())
    ids = [p["arxiv_id"] for p in corpus]
    texts = [paper_text(p) for p in corpus]
    query_texts = [queries[q]["query"] for q in qids]
    vectors = cached_vectors(texts)
    qvectors = cached_vectors(query_texts)
    index, words = bm25_index(corpus, BM25_BEST)
    frozen_lex = json.loads((config.RESULTS_DIR / "dev" / f"{fusion.LEXICAL}.run.json").read_text())
    frozen_sem = json.loads((config.RESULTS_DIR / "dev" / f"{fusion.SEMANTIC}.run.json").read_text())
    scored = {}
    for qid, vector in zip(qids, qvectors):
        lex = top_scores(ids, index.scores(words(queries[qid]["query"])), positive_only=True)
        sem = top_scores(ids, vectors @ vector, positive_only=False)
        if list(lex)[:100] != frozen_lex[qid] or list(sem)[:100] != frozen_sem[qid]:
            raise ValueError(f"{qid}: recomputed source top100 differs from frozen experiment")
        scored[qid] = {"lexical": lex, "semantic": sem}
    runs, settings = build_runs(scored)
    baseline = config.RRF_BASELINE_SYSTEM
    runs[baseline] = {q: fuse_rrf_baseline(list(s["lexical"]), list(s["semantic"]))
                      for q, s in scored.items()}
    frozen = json.loads((review.OUT / f"{baseline}.run.json").read_text())
    if runs[baseline] != frozen:
        raise ValueError("Working baseline differs from approved rankings")
    for name, run in runs.items():
        fusion.validate_run(name, run, qids, papers, exact_depth=100)
    pairs = graded.pooled_pairs(runs, qids)
    expanded_pairs = {q: list(dict.fromkeys([*snapshot["labels"][q], *pairs[q]])) for q in qids}
    human = graded.read_human_grades()
    if args.label and args.max_calls:
        judge_counts = judge.judge_pairs(
            snapshot["judge"], {q: [p for p in ids if p not in snapshot["labels"][q]
                                   and (q, p) not in human] for q, ids in pairs.items()},
            queries, papers, max_calls=args.max_calls)
    else:
        judge_counts = {"calls": 0, "judged": 0}
    labels = {q: dict(grades) for q, grades in snapshot["labels"].items()}
    cached, _ = graded.merged_labels(expanded_pairs, queries, papers, human, snapshot["judge"])
    for q in qids:
        if any(cached.get(q, {}).get(p) != grade for p, grade in labels[q].items()):
            raise ValueError(f"{q}: frozen grades changed in current cache/human labels")
        labels[q].update(cached[q])
    expanded_snapshot = {
        **snapshot, "labels": labels, "pool": expanded_pairs,
        "complete": all(p in labels[q] for q, ids in expanded_pairs.items() for p in ids),
        "pool_pairs": sum(map(len, expanded_pairs.values())),
        "pool_judged": sum(map(len, labels.values())),
        "parent_snapshot_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
        "run_fingerprints": {**snapshot["run_fingerprints"],
                             **{name: fusion.fingerprint(run) for name, run in runs.items()}},
    }
    expanded_snapshot["provisional"] = not expanded_snapshot["complete"]
    rows = review.score(runs, labels, queries)
    summary = summarize(rows, baseline)
    missing = {q: [p for p in ps if p not in labels[q]] for q, ps in pairs.items()}
    base_rows = {r["query_id"]: r for r in rows[baseline]}
    worst = sorted(qids, key=lambda q: (base_rows[q]["ndcg@10"], q))[:10]
    buckets = {}
    for name in settings:
        differences = summary[name]["all"]["ndcg@10"]["paired_vs_working"]
        if differences is None:
            continue
        deltas = differences["per_query_difference"]
        buckets[name] = {
            "gains": sorted((q for q in deltas if deltas[q] > 1e-12),
                            key=lambda q: (-deltas[q], q))[:3],
            "regressions": sorted((q for q in deltas if deltas[q] < -1e-12),
                                  key=lambda q: (deltas[q], q))[:3],
        }
    failure_ids = sorted(set(worst) | {
        q for q in qids if labels[q][runs[baseline][q][0]] == 0
        or queries[q]["source_arxiv_id"] not in runs[baseline][q][:10]
    } | {q for groups in buckets.values() for qs in groups.values() for q in qs})
    failures = {}
    judgments = judge.load_judgments(snapshot["judge"])
    for q in failure_ids:
        target = queries[q]["source_arxiv_id"]
        details = []
        evidence_ids = list(dict.fromkeys(
            [p for run in runs.values() for p in run[q][:10]] + [target]))
        for pid in evidence_ids:
            paper = papers[pid]
            judgment = judgments.get(judge.pair_key(snapshot["judge"], queries[q]["query"], paper))
            details.append({
                "arxiv_id": pid, "title": paper["title"], "abstract": paper["abstract"],
                "authors": paper["authors"],
                "grade": labels[q].get(pid),
                "provenance": "human" if (q, pid) in human else (
                    snapshot["judge"] if pid in labels[q] else "unjudged"),
                "cached_judge_reason": judgment["reason"] if judgment else None,
                "lexical_score": scored[q]["lexical"].get(pid),
                "cosine_score": scored[q]["semantic"].get(pid),
                "lexical_rank": review.rank(list(scored[q]["lexical"]), pid),
                "semantic_rank": review.rank(list(scored[q]["semantic"]), pid),
                "ranks": {name: review.rank(run[q], pid) for name, run in runs.items()},
            })
        failures[q] = {
            "query": queries[q], "baseline_scores": base_rows[q], "papers": details,
            "source_ranks": {name: review.rank(run[q], target) for name, run in runs.items()},
            "experiment_scores": {name: next(r for r in rs if r["query_id"] == q)
                                  for name, rs in rows.items()},
        }
    report = {
        "baseline": baseline, "judge_calls_this_run": judge_counts["calls"], "promoted": False,
        "parent_snapshot_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
        "snapshot_sha256": fusion.fingerprint(expanded_snapshot),
        "complete": expanded_snapshot["complete"],
        "settings": settings, "source_depth": DEPTH, "summary": summary,
        "missing_pairs": sum(map(len, missing.values())), "missing": missing,
        "query_ids": qids, "worst_baseline_queries": worst,
        "largest_ndcg_changes": buckets,
        "source_ranks_by_depth": {
            q: {family: review.rank(list(scores[family]), queries[q]["source_arxiv_id"])
                for family in ("lexical", "semantic")} for q, scores in scored.items()},
        "provenance": {
            "model": full.MODEL, "dimensions": full.DIMENSIONS,
            "paper_text_sha256": full.fingerprint(texts),
            "query_text_sha256": full.fingerprint(query_texts),
            "source_top100_verified": True,
            "run_fingerprints": {name: fusion.fingerprint(run) for name, run in runs.items()},
        },
    }
    lines = ["# Score-based fusion and deeper retrieval (dev only)", "",
             f"Cached embeddings; no baseline promotion. Judge calls this invocation: "
             f"{judge_counts['calls']}. "
             "All source top100 rankings exactly reproduce the frozen experiment. "
             "Cosine/BM25 scores are recomputed from cached vectors and the same lexical recipe.",
             "max divides each list by its maximum; minmax subtracts its top-depth minimum "
             "then divides by its range. Each input is truncated to depth before normalization. "
             "Missing-list scores are zero. Constant positive lists receive unit scores.",
             "Score weights are not comparable numerically to RRF weights. Top1 bonuses are "
             "fractions of each retriever's weighted rank-one RRF contribution.",
             "**Incomplete graded scores are PROVISIONAL, not winner evidence.** "
             "All graded rows use one additive shared label snapshot; original grades are "
             "preserved and new cached judgments extend the ideal denominator. Unjudged gains count "
             "as zero. Source metrics are complete and remain valid. Label only missing "
             "pairs before comparing provisional graded results. "
             "Exploratory dev results and intervals are not multiple-testing adjusted.",
             "", f"New unjudged query-paper pairs across this grid: {report['missing_pairs']}.", "",
             "| System | nDCG10 (provisional if coverage <100%) | P10 | Judged10 | "
             "Source MRR10 | Known-item MRR | Source R10 | Source R20 |",
             "|---|---|---|---|---|---|---|---|"]
    for name, groups in summary.items():
        all_ = groups["all"]
        columns = [all_[m]["mean"] for m in (
            "ndcg@10", "precision@10", "judged@10", "source_mrr@10")]
        columns += [groups["known_item"]["source_mrr@10"]["mean"]]
        columns += [all_[m]["mean"] for m in ("source_recall@10", "source_recall@20")]
        numbers = " | ".join("undefined" if x is None else f"{x:.4f}" for x in columns)
        lines.append(f"| `{name}` | {numbers} |")
    lines += ["", "## Worst baseline queries and target ranks within top500", "",
              "| Query | nDCG10 | Lexical target rank | Dense target rank | Fused target rank |",
              "|---|---|---|---|---|"]
    for q in worst:
        source = queries[q]["source_arxiv_id"]
        lr = review.rank(list(scored[q]["lexical"]), source)
        sr = review.rank(list(scored[q]["semantic"]), source)
        br = review.rank(runs[baseline][q], source)
        text = queries[q]["query"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {q}: {text} | {base_rows[q]['ndcg@10']:.4f} | {lr} | {sr} | {br} |")
    OUT.mkdir(parents=True, exist_ok=True)
    fusion._write_json(OUT / "input-scores.json", {
        q: {family: list(scores.items()) for family, scores in families.items()}
        for q, families in scored.items()
    })
    fusion._write_json(OUT / "labels.json", expanded_snapshot)
    fusion._write_json(OUT / "configs.json", settings)
    for name, run in runs.items():
        fusion._write_json(OUT / f"{name}.run.json", run)
        (OUT / f"{name}.scores.jsonl").write_text(
            "".join(json.dumps(r, allow_nan=False) + "\n" for r in rows[name]), encoding="utf-8")
    fusion._write_json(OUT / "report.json", report)
    fusion._write_json(OUT / "failures.json", failures)
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {len(settings)} experiments plus working control; "
          f"{report['missing_pairs']} missing pairs. "
          f"{judge_counts['calls']} judge calls this invocation.")


if __name__ == "__main__":
    main()
