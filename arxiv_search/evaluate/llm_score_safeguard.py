"""Offline safeguard replay for the fixed-key v2 top50 reranker. No API calls.

Top50 LLM reranking raised graded quality but buried strong baseline matches
(q-keyword-079's source fell from rank 1 to 15). Hypothesis: fusing the LLM order
with the baseline order keeps most of the gain while stopping one LLM score from
burying a strong lexical/semantic match.

One rule, frozen before any result was computed (no sweep):
    score = 1/(C + baseline rank) + 1/(C + LLM rank), over the top 50 only,
    with C = 30, the RRF constant the approved baseline already uses.
Ties keep baseline order; ranks 51-100 are unchanged.

Inputs are the cached v2 runs and the judge-fill child labels for the same 20
pilot queries. Pairs without a grade withhold nDCG/P10 instead of counting as 0.
"""

from __future__ import annotations

import json

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion
from arxiv_search.evaluate import llm_reranker_pilot as v1, llm_score_judge_fill as fill
from arxiv_search.evaluate import llm_score_pilot as score
from arxiv_search.evaluate import results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.judge import load_inputs

OUT = score.OUT / "safeguard"
DEPTH = 50
C = config.WORKING_BASELINE_RRF_C
NAME = f"llm-mini-score-pilot+d=50+rrf-baseline+c={C}"
LLM = score.system_name(DEPTH)

PLAN = {
    "version": "safeguard-v1", "system": NAME, "depth": DEPTH, "rrf_c": C,
    "rule": "1/(c+baseline rank)+1/(c+LLM rank) over the top50; ties keep baseline order; "
            "ranks 51-100 unchanged. Equal weights; c is the approved baseline's RRF constant.",
    "inputs": "Cached v2 baseline and top50 runs; judge-fill child labels; 20 pilot queries.",
    "success_criteria": {
        "source_mrr@10_min": "baseline source MRR@10 - 0.02",
        "ndcg@10_min": "baseline nDCG@10 + half of the top50 arm's nDCG@10 gain",
        "requires_fully_judged_top10": True,
    },
    "api_calls": 0, "sweep": False, "automatic_promotion": False,
}


def fuse(base: list[str], llm: list[str], depth: int = DEPTH, c: int = C) -> list[str]:
    """Re-order the shared top-`depth` prefix by RRF of the two orders; keep the tail."""
    prefix = base[:depth]
    if set(prefix) != set(llm[:depth]):
        raise ValueError("Baseline and LLM top prefixes must hold the same papers")
    llm_rank = {p: i for i, p in enumerate(llm[:depth], 1)}
    fused = sorted(prefix, key=lambda p: (-(1 / (c + prefix.index(p) + 1) + 1 / (c + llm_rank[p])),
                                          prefix.index(p)))
    return fused + base[depth:]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", PLAN)
    papers, queries, _ = load_inputs()
    snapshot = json.loads((fill.OUT / "labels.json").read_text(encoding="utf-8"))
    qids = snapshot["query_ids"]
    runs = {n: json.loads((score.OUT / f"{n}.run.json").read_text(encoding="utf-8"))
            for n in (v1.BASELINE, score.system_name(10), LLM)}
    runs[NAME] = {q: fuse(runs[v1.BASELINE][q], runs[LLM][q]) for q in qids}
    fusion.validate_run(NAME, runs[NAME], qids, papers, exact_depth=100)
    fusion._write_json(OUT / f"{NAME}.run.json", runs[NAME])
    missing = fill.missing_pairs(runs, snapshot["labels"], qids)
    result = score.compare(runs, v1.BASELINE, snapshot, papers, queries, qids)
    systems = result["systems"]
    base, top50 = systems[v1.BASELINE]["all"], systems[LLM]["all"]
    mine = systems[NAME]
    judged = mine["top10_fully_judged"]
    thresholds = {
        "source_mrr@10": base["source_mrr@10"]["mean"] - 0.02,
        "ndcg@10": base["ndcg@10"]["mean"] + (top50["ndcg@10"]["mean"] - base["ndcg@10"]["mean"]) / 2,
    }
    passed = {k: (mine["all"][k]["mean"] >= v if judged or k == "source_mrr@10" else None)
              for k, v in thresholds.items()}
    source = {q: {n: (r[q].index(queries[q]["source_arxiv_id"]) + 1
                      if queries[q]["source_arxiv_id"] in r[q] else None) for n, r in runs.items()}
              for q in qids}
    report = {**PLAN, "missing": missing, "missing_pairs": sum(map(len, missing.values())),
              "thresholds": thresholds, "passed": passed, "source_ranks": source,
              "primary": result, "promoted": False}
    sensitivity = {}
    if report["missing_pairs"]:
        for grade in (0, 1, 2):
            labels = {q: {**snapshot["labels"][q], **{p: grade for p in missing[q]}} for q in qids}
            r = score.compare(runs, v1.BASELINE, {**snapshot, "labels": labels}, papers, queries, qids)
            means = {n: r["systems"][n]["all"]["ndcg@10"]["mean"] for n in runs}
            paired = r["summary"][NAME]["all"]["ndcg@10"]["paired_vs_working"]
            threshold = means[v1.BASELINE] + (means[LLM] - means[v1.BASELINE]) / 2
            sensitivity[grade] = {"ndcg@10": means, "threshold": threshold,
                                  "passes": means[NAME] >= threshold,
                                  "delta": paired["difference"], "ci95": paired["ci95"]}
    report["missing_grade_sensitivity"] = sensitivity
    fusion._write_json(OUT / "report.json", report)

    lines = ["# Offline safeguard replay: top50 LLM order fused with baseline order", "",
             f"Rule (frozen before computing): `1/({C}+baseline rank) + 1/({C}+LLM rank)` over the "
             "top 50; ties keep baseline order; ranks 51-100 unchanged. No API calls, no sweep.", "",
             f"Missing top10 grades: **{report['missing_pairs']}**.", "",
             "| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |",
             "|---|---|---|---|---|---|---|"]
    for n, r in systems.items():
        vals = [("withheld" if f in ("ndcg@10", "precision@10") and not r["top10_fully_judged"]
                 else f"{r['all'][f]['mean']:.4f}")
                for f in ("ndcg@10", "precision@10", "judged@10", "source_mrr@10",
                          "source_recall@10", "source_recall@20")]
        lines.append(f"| `{n}` | " + " | ".join(vals) + " |")
    lines += ["", "## Pre-registered criteria", "", "| Criterion | Threshold | Result |", "|---|---|---|"]
    for k, v in thresholds.items():
        verdict = {True: "pass", False: "fail", None: "withheld"}[passed[k]]
        lines.append(f"| {k} | >= {v:.4f} | {mine['all'][k]['mean']:.4f} ({verdict}) |"
                     if passed[k] is not None else f"| {k} | >= {v:.4f} | withheld |")
    lines += ["", "## Paired versus baseline", "",
              "| System | nDCG10 delta [95% CI] | Source MRR10 delta [95% CI] |", "|---|---|---|"]
    for n in (LLM, NAME):
        cells = []
        for f in ("ndcg@10", "source_mrr@10"):
            p = result["summary"].get(n, {}).get("all", {}).get(f, {}).get("paired_vs_working")
            cells.append("withheld" if p is None else
                         f"{p['difference']:+.4f} [{p['ci95'][0]:+.4f},{p['ci95'][1]:+.4f}]")
        lines.append(f"| `{n}` | " + " | ".join(cells) + " |")
    lines += ["", "## Segment nDCG10", "", "| System | " + " | ".join(catalog.QUERY_TYPES) + " |",
              "|---|" + "---|" * len(catalog.QUERY_TYPES)]
    for n, r in systems.items():
        cells = []
        for kind in catalog.QUERY_TYPES:
            rows = [x for x in r["per_query"] if x["query_type"] == kind]
            ok = all(x["judged@10"] == 1 for x in rows)
            cells.append(f"{r['by_query_type'][kind]['ndcg@10']['mean']:.4f}" if ok else "withheld")
        lines.append(f"| `{n}` | " + " | ".join(cells) + " |")
    if sensitivity:
        lines += ["", "## Missing-grade sensitivity (diagnostic, not a label)", "",
                  "Every unjudged top10 pair set to the same assumed grade; all systems rescored.", "",
                  "| Assumed grade | Baseline | Top50 LLM | Safeguard | Threshold | Delta [95% CI] | Passes |",
                  "|---|---|---|---|---|---|---|"]
        for grade, x in sensitivity.items():
            m = x["ndcg@10"]
            lines.append(f"| {grade} | {m[v1.BASELINE]:.4f} | {m[LLM]:.4f} | {m[NAME]:.4f} | "
                         f"{x['threshold']:.4f} | {x['delta']:+.4f} [{x['ci95'][0]:+.4f},"
                         f"{x['ci95'][1]:+.4f}] | {'yes' if x['passes'] else 'no'} |")
    lines += ["", "## Source ranks that differ from baseline", "",
              "| Query | Baseline | Top50 LLM | Safeguard |", "|---|---|---|---|"]
    for q in qids:
        s = source[q]
        if len({s[v1.BASELINE], s[LLM], s[NAME]}) > 1:
            lines.append(f"| {q} | {s[v1.BASELINE]} | {s[LLM]} | {s[NAME]} |")
    lines += ["", "## Cautions", "",
              "- 20 previously examined dev queries; the rule was motivated by these same losses.",
              "- Judge and reranker share a model family; no independent validation.",
              "- No promotion."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{NAME}: missing {report['missing_pairs']}; passed {passed}")


if __name__ == "__main__":
    main()
