"""Score-aware blend of the cached top50 LLM scores with retrieval rank. No reranker calls.

The safeguard (Decision42/45) fuses two *ranks*. Converting 0-4 LLM scores to ranks
throws away how big a gap is: a 4-vs-0 gap and a 3-vs-2 gap count the same. On
question queries the safeguard gave back 0.058 of the LLM's nDCG gain.

Hypothesis: keep the LLM score itself and add a smooth retrieval-rank prior,
    blended(p) = LLM score(p) + beta * (c+1)/(c+retrieval rank(p)),   c = 30,
so large LLM gaps decide the order while near-ties fall back to retrieval evidence.
The prior is worth beta points at rank 1 and 0.39*beta at rank 50.

Generalization guard: one formula for every query (no query-type, query-ID or label
inputs), c is the approved baseline's constant, and the beta grid was fixed before any
score was computed. beta < 1/0.61 cannot overturn a one-point LLM gap anywhere in
the top 50, so it would just reproduce the raw top50 order; the grid therefore
starts at 2.
"""

from __future__ import annotations

import argparse
import json

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, judge
from arxiv_search.evaluate import llm_score_dev100 as dev, llm_score_judge_fill as fill
from arxiv_search.evaluate import llm_score_pilot as score, results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.judge_pilot import read_human_grades
from arxiv_search.search.rerank import score_rank_blend

OUT = config.RESULTS_DIR / "llm-score-blend"
DEPTH = 50
C = config.RERANK_BASELINE_RRF_C
BETAS = (2, 3, 4)
JUDGE_TASK_CAP_USD = 0.10
REFERENCE = config.RERANK_BASELINE_SYSTEM


def system_name(beta: float) -> str:
    return f"{dev.LLM}+blend-rank-prior+b={beta:g}+c={C}"


PLAN = {
    "version": "score-blend-v1",
    "hypothesis": "Keeping the 0-4 LLM score and adding a smooth retrieval-rank prior "
                  "keeps more of the top50 gain than rank-only RRF while protecting "
                  "strong retrieval matches.",
    "rule": "blended = LLM score + beta*(c+1)/(c+retrieval rank) over the top50; ties keep "
            "retrieval order; ranks 51-100 unchanged.",
    "c": C, "depth": DEPTH, "betas": list(BETAS),
    "inputs": "Cached llm-score-dev100 responses (one pass, 100 dev queries); no reranker calls.",
    "labels": "shared-labels/labels.json; unjudged top10 pairs graded by the frozen judge "
              "(human overrides preserved) before scoring.",
    "reference": REFERENCE,
    "qualifies_if": {
        "fully_judged_top10": True,
        "ndcg@10_delta_vs_reference": "> the reference's run-to-run MDD (0.009) with paired "
                                      "95% CI lower bound > 0",
        "source_mrr@10": ">= reference - 0.02",
        "consistency": "nDCG delta vs reference > 0 on both the pilot20 and new80 subsets",
    },
    "selection": "Among qualifiers, highest all-100 nDCG@10; 3 configs on dev, so the winner's "
                 "gain is optimistic. Report all configs.",
    "generalization_guard": "Same formula for all queries; no query-type/ID/label inputs; grid fixed "
                            "a priori; held-out queries never touched.",
    "held_out_queries_used": False, "automatic_promotion": False,
}


def build(state: dict) -> dict:
    runs = dev.build_runs(state)
    for r in state["requests"]:
        answer = dev.cached(r, score.VERSION if r["pilot"] else client.DEV100_VERSION)
        scores = client.validate_scores(answer[0], len(r["presented_ids"]))
        llm = {p: float(scores[f"P{i}"]) for i, p in enumerate(r["presented_ids"], 1)}
        q = r["query_id"]
        for beta in BETAS:
            runs.setdefault(system_name(beta), {})[q] = score_rank_blend(
                state["base"][q], llm, DEPTH, beta, C)
    for n, run in runs.items():
        fusion.validate_run(n, run, state["qids"], state["papers"], exact_depth=100)
    return runs


def shared_snapshot() -> dict:
    _, _, shared, _ = catalog.load_shared_labels(config.RESULTS_DIR)
    return shared


def labels_with_child(shared: dict, out=None) -> dict:
    path = (out or OUT) / "labels.json"
    labels = shared["labels"]
    if path.exists():
        labels = fill.child_labels(labels, json.loads(path.read_text(encoding="utf-8"))["labels"])
    return labels


def fill_top10(state: dict, runs: dict, shared: dict, out, cap_usd: float,
               run_judge: bool) -> tuple[dict | None, list]:
    """Grade unjudged top10 pairs into `out`/labels.json (child of the shared layer).

    Returns (labels, usage rows); labels is None when grading is needed but not enabled.
    """
    labels = labels_with_child(shared, out)
    missing = fill.missing_pairs(runs, labels, state["qids"])
    human = read_human_grades()
    to_judge = {q: [p for p in ps if (q, p) not in human] for q, ps in missing.items() if ps}
    calls = judge.batches(shared["judge"], to_judge, state["queries"], state["papers"],
                          judge.load_judgments(shared["judge"]))
    usage_path = out / "judge-accounting.json"
    rows = json.loads(usage_path.read_text(encoding="utf-8"))["rows"] if usage_path.exists() else []
    print(json.dumps({"missing_pairs": sum(map(len, missing.values())), "judge_calls": len(calls)}))
    if not any(missing.values()):
        return labels, rows
    estimate = fill.estimate(calls, state["queries"])
    print(json.dumps({k: v for k, v in estimate.items() if k != "requests"}, indent=2))
    if calls:
        if not run_judge:
            fusion._write_json(out / "judge-preflight.json", estimate)
            return None, rows
        if estimate["expected_usd"] > cap_usd:
            raise api.BudgetExceeded("Judge estimate exceeds its ceiling; no request sent")
        if estimate["expected_tokens"] + estimate["max_single_reservation_tokens"] > fill.shared_remaining():
            raise api.BudgetExceeded("Judge estimate exceeds the shared token allowance")
        sent = fill.run_calls({"judge_key": shared["judge"], "queries": state["queries"],
                               "calls": calls}, planned=estimate["requests"], cap_usd=cap_usd)
        rows += [{k: r[k] for k in ("query_id", "arxiv_id", "usage")} for r in sent["rows"]]
        fusion._write_json(usage_path, {"rows": rows})
    pairs = {q: ps for q, ps in missing.items() if ps}
    new = judge.grades_for(shared["judge"], pairs, state["queries"], state["papers"])
    for (q, p), grade in human.items():
        if p in pairs.get(q, []):
            new.setdefault(q, {})[p] = grade
    child = fill.child_labels(labels, new)
    fusion._write_json(out / "labels.json", {
        "judge": shared["judge"], "rubric_version": shared["rubric_version"],
        "parent": "shared-labels/labels.json",
        "labels": {q: {p: g for p, g in child[q].items() if p not in shared["labels"][q]}
                   for q in state["qids"]}})
    labels = labels_with_child(shared, out)
    if any(fill.missing_pairs(runs, labels, state["qids"]).values()):
        raise ValueError("Top10 pairs still unjudged after judging")
    return labels, rows


def publish(state: dict, runs: dict, shared: dict, labels: dict, judge_usage: dict) -> dict:
    qids, queries, papers = state["qids"], state["queries"], state["papers"]
    snapshot = {**shared, "labels": labels}
    scopes = {"all100": qids, "new80": [q for q in qids if q not in state["pilot"]],
              "pilot20": sorted(state["pilot"])}
    results = {s: score.compare(runs, REFERENCE, {**snapshot, "labels": {q: labels[q] for q in ids}},
                                papers, queries, ids) for s, ids in scopes.items()}
    mdd = 1.96 * 2 ** 0.5 * json.loads(
        (config.RESULTS_DIR / config.RERANK_BASELINE_NOISE_DIR / "report.json")
        .read_text(encoding="utf-8"))["systems"][REFERENCE]["est_sd_of_100q_mean"]
    verdicts = {}
    for beta in BETAS:
        n = system_name(beta)
        full = results["all100"]
        mine, ref = full["systems"][n], full["systems"][REFERENCE]
        paired = full["summary"][n]["all"]["ndcg@10"]["paired_vs_working"]
        sub = {s: (results[s]["summary"][n]["all"]["ndcg@10"]["paired_vs_working"] or {})
               .get("difference") for s in ("pilot20", "new80")}
        checks = {
            "fully_judged_top10": mine["top10_fully_judged"],
            "ndcg_gain_beyond_noise": bool(paired) and paired["difference"] > mdd
                                      and paired["ci95"][0] > 0,
            "source_mrr": mine["all"]["source_mrr@10"]["mean"]
                          >= ref["all"]["source_mrr@10"]["mean"] - 0.02,
            "consistent_subsets": all(v is not None and v > 0 for v in sub.values()),
        }
        verdicts[n] = {"checks": checks, "qualifies": all(checks.values()),
                       "ndcg_delta": paired, "subset_deltas": sub}
    qualifiers = [n for n, v in verdicts.items() if v["qualifies"]]
    winner = max(qualifiers, key=lambda n: results["all100"]["systems"][n]["all"]["ndcg@10"]["mean"],
                 default=None)
    for n in [system_name(b) for b in BETAS]:
        fusion._write_json(OUT / f"{n}.run.json", runs[n])
    report = {"plan": json.loads((OUT / "preregistration.json").read_text(encoding="utf-8")),
              "reference_mdd": mdd, "results": results, "verdicts": verdicts,
              "selected": winner, "judge_accounting": judge_usage, "promoted": False}
    fusion._write_json(OUT / "report.json", report)
    write_markdown(report, runs)
    return report


def write_markdown(report: dict, runs: dict) -> None:
    full = report["results"]["all100"]
    order = [dev.v1.BASELINE, dev.LLM, REFERENCE, *(system_name(b) for b in BETAS)]
    lines = ["# Score-aware blend: LLM score + retrieval-rank prior (no reranker calls)", "",
             f"Rule: `LLM score + beta*({C}+1)/({C}+retrieval rank)` over the top {DEPTH}; ties keep "
             f"retrieval order; betas {list(BETAS)} fixed before scoring. Reference: `{REFERENCE}` "
             f"(reranking baseline). Noise threshold (MDD): {report['reference_mdd']:.4f}.", "",
             "| System | nDCG@10 | Δ vs reference [95% CI] | pilot20 Δ | new80 Δ | Source MRR@10 | "
             "R@1 | judged@10 | Qualifies |", "|---|---|---|---|---|---|---|---|---|"]
    for n in order:
        s = full["systems"][n]["all"]
        p = full["summary"][n]["all"]["ndcg@10"]["paired_vs_working"]
        subs = [report["results"][k]["summary"][n]["all"]["ndcg@10"]["paired_vs_working"]
                for k in ("pilot20", "new80")]
        v = report["verdicts"].get(n)
        lines.append(
            f"| `{n}` | {s['ndcg@10']['mean']:.4f} | "
            + ("—" if n == REFERENCE or not p else
               f"{p['difference']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}]")
            + " | " + " | ".join("—" if n == REFERENCE or not x else f"{x['difference']:+.4f}"
                                 for x in subs)
            + f" | {s['source_mrr@10']['mean']:.4f} | {s['source_recall@1']['mean']:.0%} | "
            f"{s['judged@10']['mean']:.3f} | "
            + ("—" if v is None else ("**yes**" if v["qualifies"] else
                                      "no (" + ", ".join(k for k, ok in v["checks"].items() if not ok) + ")"))
            + " |")
    lines += ["", "## nDCG@10 by query type (diagnostic only; the rule has no type input)", "",
              "| System | " + " | ".join(catalog.QUERY_TYPES) + " |",
              "|---|" + "---|" * len(catalog.QUERY_TYPES)]
    for n in order:
        t = full["systems"][n]["by_query_type"]
        lines.append(f"| `{n}` | " + " | ".join(f"{t[k]['ndcg@10']['mean']:.4f}"
                                                 for k in catalog.QUERY_TYPES) + " |")
    lines += ["", f"Selected: **{report['selected'] or 'none qualified'}**. Not promoted.", "",
              "## Cautions", "",
              "- Three configs chosen on the same 100 dev queries; the winner's gain is optimistic.",
              "- One cached LLM pass; run-to-run noise applies to every blend.",
              "- Judge and reranker share a model family.",
              f"- Judge spend: ${report['judge_accounting'].get('usd', 0):.4f}."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true", help="grade unjudged top10 pairs")
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", PLAN)
    state = dev.prepare()
    runs = build(state)
    shared = shared_snapshot()
    labels, rows = fill_top10(state, runs, shared, OUT, JUDGE_TASK_CAP_USD, args.judge)
    if labels is None:
        return
    report = publish(state, runs, shared, labels, dev.judge_accounting(rows) if rows else {})
    print(json.dumps({n: v["qualifies"] for n, v in report["verdicts"].items()}),
          "selected:", report["selected"])


if __name__ == "__main__":
    main()
