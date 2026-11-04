"""Experiment E2: Experiment E's top-20 refinement, keeping the Decision46 rank-1 paper in place.

Experiment E (findings 35) raised pilot nDCG@10 by +.042 but failed its frozen source-paper
guard: refinement sometimes demoted the paper Decision46 ranked first. A free check on the
same pilot responses showed that keeping Decision46's rank 1 fixed and applying E's order
below it kept most of the gain (+.030) and passed the guard. That rule was designed after
seeing the pilot, so the pilot cannot test it. E2 tests it on the 80 dev queries E never
scored.

    1. E's primary order: top20 re-scored 0-10 twice (same requests as E), averaged,
       RRF c=30 with the Decision46 order. Ranks 21+ unchanged.
    2. Move Decision46's rank-1 paper back to rank 1; every other paper keeps E's order.

One rule for every query; no query ids, types, source papers or labels in ranking. The
requests for the 80 queries are byte-identical to E's full-stage requests, so responses are
shared with E's cache. Held-out queries are never touched.

    python -m arxiv_search.evaluate.llm_score_refine_pin            # free preflight
    python -m arxiv_search.evaluate.llm_score_refine_pin --run --judge
"""

from __future__ import annotations

import argparse
import json

from arxiv_search import config, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion
from arxiv_search.evaluate import llm_score_blend as blend, llm_score_dev100 as dev
from arxiv_search.evaluate import llm_score_pass2 as pass2, llm_score_pilot as score
from arxiv_search.evaluate import llm_score_refine as refine
from arxiv_search.evaluate import results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "llm-score-refine-pin"
REFERENCE = refine.REFERENCE
SYSTEM = f"{refine.PRIMARY}+pin1-d46"
JUDGE_TASK_CAP_USD = 0.20
MARGIN_SOURCE_MRR = 0.02

PLAN = {
    "version": "refine20-pin1-v1",
    "hypothesis": "Experiment E's gain comes from reordering ranks 2-20; protecting the "
                  "Decision46 rank 1 keeps the gain without demoting looked-up papers.",
    "one_change": "Experiment E primary order, then Decision46's rank-1 paper is moved back to rank 1.",
    "system": SYSTEM, "reference": REFERENCE, "builds_on": refine.PLAN["version"],
    "designed_after": "Experiment E pilot (findings 35): pilot20 informed this rule, so pilot20 "
                      "results are diagnostic only.",
    "evaluation_scope": "new80: the 80 dev queries outside the pilot, never scored by E or E2 "
                        "before this plan was frozen.",
    "qualifies_if": {
        "fully_judged_top10": True,
        "new80_ndcg@10_delta_vs_reference": "> single-pass MDD of the Decision46 safeguard "
                                            "(0.0106) with paired 95% CI lower bound > 0",
        "new80_source_mrr@10": f">= reference - {MARGIN_SOURCE_MRR}",
    },
    "diagnostics_not_gates": ["pilot20 and all100 results", "E primary and secondary on new80",
                              "nDCG by query type", "grade-0 papers in the top10"],
    "requests": "E full-stage requests (160 = 80 queries x 2 passes), shared cache with E",
    "cost": "Expected ~$0.95 (E pilot measured $0.23 per 40 requests). Judge <= $0.20.",
    "automatic_retries": False, "held_out_queries_used": False, "automatic_promotion": False,
}


def pin_first(reference: list[str], ranked: list[str]) -> list[str]:
    """Put the reference's rank-1 paper first; keep every other paper in `ranked` order."""
    top = reference[0]
    if top not in ranked:
        raise ValueError("Reference rank-1 paper missing from the refined ranking")
    return [top] + [p for p in ranked if p != top]


def prepare() -> dict:
    state = refine.prepare()
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", {**PLAN, "new80_query_ids": new80(state)})
    return state


def new80(state: dict) -> list[str]:
    return sorted(q for q in state["qids"] if q not in state["pilot"])


def build(state: dict, qids: list[str]) -> dict:
    runs, _ = refine.build(state, qids)
    runs[SYSTEM] = {q: pin_first(state["d46"][q], runs[refine.PRIMARY][q]) for q in qids}
    fusion.validate_run(SYSTEM, runs[SYSTEM], qids, state["papers"], exact_depth=100)
    return runs


def verdict(results: dict, mdd: float) -> dict:
    new = results["new80"]
    paired = new["summary"][SYSTEM]["all"]["ndcg@10"]["paired_vs_working"]
    mrr = (new["systems"][SYSTEM]["all"]["source_mrr@10"]["mean"]
           - new["systems"][REFERENCE]["all"]["source_mrr@10"]["mean"])
    checks = {"fully_judged_top10": bool(new["systems"][SYSTEM]["top10_fully_judged"]),
              "ndcg_gain_beyond_noise": bool(paired) and paired["difference"] > mdd and paired["ci95"][0] > 0,
              "source_mrr": mrr >= -MARGIN_SOURCE_MRR}
    return {"checks": checks, "qualifies": all(checks.values()),
            "new80_ndcg_delta": paired, "new80_source_mrr_delta": mrr}


def evaluate(state: dict, run_judge: bool) -> dict | None:
    qids = state["qids"]
    runs = build(state, qids)
    _, _, shared, _ = catalog.load_shared_labels(config.RESULTS_DIR, refine.LABEL_LAYER)
    usage_path = OUT / "judge-accounting.json"
    prior = dev.judge_accounting(json.loads(usage_path.read_text(encoding="utf-8"))["rows"]) \
        if usage_path.exists() else {"usd": 0.0}
    labels, rows = blend.fill_top10({**state, "qids": qids}, runs, shared, OUT,
                                    JUDGE_TASK_CAP_USD - prior["usd"], run_judge,
                                    parent=refine.LABEL_LAYER.as_posix())
    if labels is None:
        return None
    snapshot = {**shared, "labels": labels}
    pilot = sorted(state["pilot"])
    scopes = {"new80": new80(state), "pilot20": pilot, "all100": qids}
    results = {s: score.compare(runs, REFERENCE, {**snapshot, "labels": {q: labels[q] for q in ids}},
                                state["papers"], state["queries"], ids) for s, ids in scopes.items()}
    mdd = json.loads((pass2.OUT / "report.json").read_text(encoding="utf-8"))["noise"]["safeguard"]["single_pass_mdd"]
    report = {"plan": json.loads((OUT / "preregistration.json").read_text(encoding="utf-8")),
              "mdd": mdd, "results": results, "verdict": verdict(results, mdd),
              "accounting": {"refine": client.PilotLedger(version=client.REFINE_VERSION).summary(),
                             "judge": dev.judge_accounting(rows) if rows else {}},
              "promoted": False}
    fusion._write_json(OUT / f"{SYSTEM}.run.json", runs[SYSTEM])
    fusion._write_json(OUT / "report.json", report)
    write_markdown(report, OUT / "report.md")
    return report


def write_markdown(report: dict, path) -> None:
    v = report["verdict"]
    systems = (dev.v1.BASELINE, REFERENCE, refine.PRIMARY, refine.SECONDARY, SYSTEM)
    lines = ["# Experiment E2: top20 refinement keeping the Decision46 rank 1", "",
             f"System `{SYSTEM}` vs `{REFERENCE}` (Decision46). Decision scope: new80 (queries "
             f"never scored before the plan was frozen). Noise threshold (MDD): {report['mdd']:.4f}.", "",
             f"**Qualifies: {'yes' if v['qualifies'] else 'no'}** "
             f"({', '.join(f'{k}: {ok}' for k, ok in v['checks'].items())}). Not promoted.", ""]
    for scope in ("new80", "pilot20", "all100"):
        res = report["results"][scope]
        lines += [f"## {scope}" + (" (decision)" if scope == "new80" else " (diagnostic)"), "",
                  "| System | nDCG@10 | Δ vs D46 [95% CI] | Source MRR@10 | R@1 | P@10 |",
                  "|---|---|---|---|---|---|"]
        for n in systems:
            s = res["systems"][n]["all"]
            d = res["summary"][n]["all"]["ndcg@10"]["paired_vs_working"]
            lines.append(f"| `{n}` | {s['ndcg@10']['mean']:.4f} | "
                         + ("—" if n == REFERENCE or not d else
                            f"{d['difference']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]")
                         + f" | {s['source_mrr@10']['mean']:.4f} | {s['source_recall@1']['mean']:.0%} | "
                         f"{s['precision@10']['mean']:.3f} |")
        lines.append("")
    a = report["accounting"]
    lines += ["## Cost", "", f"- Refinement ledger (E and E2 share it): ${a['refine']['accounted_usd']:.4f}.",
              f"- Judge: ${(a['judge'] or {}).get('usd', 0):.4f}.", "",
              "## Cautions", "", "- Dev only; the judge and reranker share a model family.",
              "- The pin rule was designed on pilot20 after seeing E's pilot; only new80 decides.",
              "- Not promoted; promotion needs the owner's approval."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="send the 160 new80 requests")
    parser.add_argument("--judge", action="store_true", help="grade unjudged top10 pairs")
    args = parser.parse_args(argv)
    state = prepare()
    ledger = client.PilotLedger(version=client.REFINE_VERSION)
    pre = refine.preflight(state, "full", ledger)
    print(json.dumps(pre, indent=2), flush=True)
    if not args.run:
        return
    refine.run_stage(state, "full", ledger)
    report = evaluate(state, args.judge)
    if report:
        print(json.dumps(report["verdict"], indent=2, default=str))


if __name__ == "__main__":
    main()
