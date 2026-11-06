"""Free D47 loss decomposition on frozen dev evidence; never sends model requests."""

from __future__ import annotations

import hashlib
import json
import statistics

from arxiv_search import config
from arxiv_search.evaluate import metrics, results_catalog as catalog

OUT = config.RESULTS_DIR / "rerank-loss-d47"
STAGES = ("actual", "oracle10", "oracle20", "oracle50", "ideal")
COMPONENTS = ("ordering_top10", "selection_11_20", "screening_21_50", "outside_top50")


def decompose(ranked: list[str], candidates: list[str], grades: dict[str, int]) -> dict:
    if len(ranked) < 50 or len(set(ranked)) != len(ranked):
        raise ValueError("D47 needs at least 50 unique ranked candidates")
    if len(candidates) < 50 or set(ranked[:50]) != set(candidates[:50]):
        raise ValueError("D47 and retrieval top50 candidate sets differ")
    if any(p not in grades for p in ranked[:10]):
        raise ValueError("D47 top10 must be fully judged")
    if any(type(g) is not int or g not in (0, 1, 2) for g in grades.values()):
        raise ValueError("Grades must be integers 0/1/2")
    scores = {"actual": metrics.ndcg_at_k(ranked, grades)}
    for depth in (10, 20, 50):
        ordered = sorted(ranked[:depth], key=lambda p: -grades.get(p, 0))
        scores[f"oracle{depth}"] = metrics.ndcg_at_k(ordered, grades)
    if scores["actual"] is None:
        raise ValueError("Query has no positive labels")
    scores["ideal"] = 1.0
    losses = {name: scores[b] - scores[a]
              for name, a, b in zip(COMPONENTS, STAGES, STAGES[1:])}
    fixed_first = [ranked[0]] + sorted(ranked[1:20], key=lambda p: -grades.get(p, 0))
    grade_counts = {}
    for name, pool in (("top10", ranked[:10]), ("ranks11_20", ranked[10:20]),
                       ("ranks21_50", ranked[20:50])):
        grade_counts[name] = {str(g): sum(grades.get(p) == g for p in pool) for g in (0, 1, 2)}
        grade_counts[name]["unjudged"] = sum(p not in grades for p in pool)
    # Pairwise opportunities, not a count of independent rank errors or label disagreements.
    opportunities = []
    for rank, paper in enumerate(ranked[:10], 1):
        better = [(n, p) for n, p in enumerate(ranked[10:50], 11)
                  if grades.get(p, 0) > grades[paper]]
        if better:
            opportunities.append({"rank": rank, "paper_id": paper, "grade": grades[paper],
                                  "better_candidates": [
                                      {"rank": n, "paper_id": p, "grade": grades[p]}
                                      for n, p in better]})
    return {
        "scores": scores, "loss": losses, "grade_counts": grade_counts,
        "pin1_top20_oracle_penalty": scores["oracle20"] - metrics.ndcg_at_k(fixed_first, grades),
        "opportunities": opportunities,
    }


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Cannot aggregate an empty query scope")
    means = {k: statistics.fmean(r["scores"][k] for r in rows) for k in STAGES}
    gap = means["oracle50"] - means["actual"]
    losses = {}
    for k in COMPONENTS:
        values = [r["loss"][k] for r in rows]
        mean, low, high = metrics.bootstrap_ci(values)
        losses[k] = {"mean": mean, "ci95": [low, high],
                     "queries_affected": sum(v > 1e-12 for v in values),
                     "share_of_top50_gap": mean / gap if gap > 0 and k != "outside_top50" else None}
    return {"queries": len(rows), "scores": means, "loss": losses,
            "pin1_top20_oracle_penalty": statistics.fmean(r["pin1_top20_oracle_penalty"]
                                                        for r in rows),
            "unjudged_top50": sum(sum(v["unjudged"] for v in r["grade_counts"].values())
                                 for r in rows),
            "grade_counts": {
                band: {grade: sum(r["grade_counts"][band][grade] for r in rows)
                       for grade in ("0", "1", "2", "unjudged")}
                for band in ("top10", "ranks11_20", "ranks21_50")
            }}


def run() -> dict:
    root = config.RESULTS_DIR
    paths = {
        "retrieval": root / "shortlist-score-dev" / f"{config.WORKING_BASELINE_SYSTEM}.run.json",
        "d47": root / "llm-score-refine-pin" /
               "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json",
        "split": config.EVAL_DIR / "split.json", "queries": config.EVAL_DIR / "queries.jsonl",
    }
    label_path, label_raw, shared, _ = catalog.load_shared_labels(root, catalog.SHARED_LABELS_D47)
    labels = shared["labels"]
    raw = {name: path.read_bytes() for name, path in paths.items()}
    split = json.loads(raw["split"])
    qids = sorted(split["dev"])
    if set(qids) & set(split["test"]):
        raise ValueError("Dev/test overlap")
    if set(qids) != set(shared["query_ids"]):
        raise ValueError("Pinned label snapshot does not match the dev scope")
    queries = {q["query_id"]: q for line in raw["queries"].decode("utf-8").splitlines()
               if (q := json.loads(line))["query_id"] in qids}
    retrieval, d47 = json.loads(raw["retrieval"]), json.loads(raw["d47"])
    rows = []
    for qid in qids:
        rows.append({"query_id": qid, "query": queries[qid]["query"],
                     "query_type": queries[qid]["query_type"],
                     **decompose(d47[qid], retrieval[qid], labels[qid])})
    result = {
        "scope": "D47, 100 dev queries, frozen D47 pooled labels; no provider calls or test scoring",
        "method": "Sequential perfect reordering of the D47 top10, top20, top50; same global "
                  "pooled-label ideal denominator and linear gains. Components telescope to "
                  "1 - actual. Unjudged candidates count as zero, not confirmed irrelevant.",
        "cautions": [
            "Oracle bounds are label-informed diagnostics, not achievable system predictions.",
            "Partially judged top50 and pooled labels make the ceiling optimistic/incomplete.",
            "Bootstrap intervals describe dev-query variation, not unbiased generalization.",
            "Candidate inversions are not proof of label noise; no independent label audit performed.",
            "Pin penalty is an idealized bound, not a recommendation to remove the safeguard.",
            "Allocation is sequential/order-dependent: top10 ordering is credited first, then "
            "selection from top20, then top50. Selection increments include optimal new ordering.",
        ],
        "provenance": {name: {"path": str(paths[name].relative_to(config.PROJECT_ROOT)),
                              "sha256": hashlib.sha256(value).hexdigest()}
                       for name, value in raw.items()},
        "all": aggregate(rows),
        "by_query_type": {t: aggregate([r for r in rows if r["query_type"] == t])
                          for t in sorted({r["query_type"] for r in rows})},
        "rows": rows,
    }
    result["provenance"]["labels"] = {
        "path": str(label_path.relative_to(config.PROJECT_ROOT)),
        "sha256": hashlib.sha256(label_raw).hexdigest(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_markdown(result)
    return result


def write_markdown(result: dict) -> None:
    all_ = result["all"]
    lines = ["# D47: where the remaining ranking loss sits", "", result["scope"], "",
             result["method"], "", "| Ordering | Mean nDCG@10 |", "|---|---:|"]
    lines += [f"| {k} | {all_['scores'][k]:.4f} |" for k in STAGES]
    lines += ["", "| Loss component | Mean [95% bootstrap CI] | Queries affected | Share of top50 gap |",
              "|---|---:|---:|---:|"]
    for k, v in all_["loss"].items():
        share = v["share_of_top50_gap"]
        lines.append(f"| {k} | {v['mean']:.4f} [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}] | "
                     f"{v['queries_affected']} | {'—' if share is None else f'{share:.1%}'} |")
    lines += ["", f"Unjudged query-paper pairs in the top50: **{all_['unjudged_top50']}**.",
              f"Keeping D47 rank 1 fixed reduces the top20 oracle by "
              f"**{all_['pin1_top20_oracle_penalty']:.4f}** on average.", "",
              "| D47 rank band | Grade 0 | Grade 1 | Grade 2 | Unjudged |",
              "|---|---:|---:|---:|---:|"]
    for band, counts in all_["grade_counts"].items():
        lines.append(f"| {band} | " + " | ".join(str(counts[g])
                                                for g in ("0", "1", "2", "unjudged")) + " |")
    lines += ["",
              "## By query type", "",
              "| Type | Actual | Ordering top10 | Selection 11–20 | Screening 21–50 | Outside top50 |",
              "|---|---:|---:|---:|---:|---:|"]
    for t, v in result["by_query_type"].items():
        lines.append(f"| {t} | {v['scores']['actual']:.4f} | " +
                     " | ".join(f"{v['loss'][k]['mean']:.4f}" for k in COMPONENTS) + " |")
    lines += ["", "## Largest known gaps", "",
              "| Query | Type | Actual | Top50 oracle | Largest component |",
              "|---|---|---:|---:|---|"]
    for r in sorted(result["rows"], key=lambda r: r["scores"]["oracle50"] - r["scores"]["actual"],
                    reverse=True)[:15]:
        query = r["query"].replace("|", "\\|").replace("\n", " ")
        component = max(COMPONENTS[:3], key=lambda k: r["loss"][k])
        lines.append(f"| {query} | {r['query_type']} | {r['scores']['actual']:.4f} | "
                     f"{r['scores']['oracle50']:.4f} | {component} |")
    lines += ["", "## Limits", ""] + [f"- {c}" for c in result["cautions"]]
    lines += ["", "Per-query counts, candidate inversions and input hashes: [report.json](report.json)."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run()["all"], indent=2))
