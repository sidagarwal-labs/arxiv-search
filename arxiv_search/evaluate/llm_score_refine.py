"""Experiment E: a focused second look at the reranked top 20.

Loss analysis (findings 32) showed ordering, not recall, limits the Decision46 reranker:
98 of the 143 fully relevant papers outside its top 10 sit at ranks 11-20, usually below
partly relevant papers. Reordering only the top 20 perfectly would score 0.946 nDCG@10
(vs 0.768), so most of the headroom is inside this short list.

Hypothesis: re-scoring only those 20 papers, with a finer 0-10 scale that separates "the
paper's main contribution is the request" from "related or secondary", promotes the direct
answers the 50-paper 0-4 pass ties with related work.

    1. Take the Decision46 final ranking (unchanged, cached) and its top 20.
    2. Two scoring passes (same model, settings and evidence as Decision46; payload order is
       the fixed hash shuffle used by every earlier reranker), averaged.
    3. Primary: sort the top 20 by the average, ties keep Decision46 order, then RRF c=30 with
       the Decision46 order over those 20 (the same safeguard rule as Decision46). Ranks 21+
       unchanged. Secondary: the refined order without the safeguard (same responses).

Generalization guard: one prompt and one rule for every query; no query IDs, query types,
source papers or labels in ranking; depth 20 and c=30 fixed before any response; the
held-out queries are never touched.

Preflight by default. `--stage pilot --run` sends 40 requests (20 pilot queries x 2);
`--stage full --run` sends the other 160 only if the saved pilot gate passed. No retries.
`--judge` grades unjudged top10 pairs (frozen judge, cache first).
"""

from __future__ import annotations

import argparse
import json
import statistics

import tiktoken

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion
from arxiv_search.evaluate import llm_score_blend as blend, llm_score_dev100 as dev
from arxiv_search.evaluate import llm_score_facets as facets, llm_score_pass2 as pass2
from arxiv_search.evaluate import llm_score_pilot as score, llm_score_safeguard as guard
from arxiv_search.evaluate import results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "llm-score-refine"
DEPTH = client.REFINE_DEPTH
PASSES = (1, 2)
REFERENCE = pass2.AVG_SAFE  # Decision46 reranking baseline
PRIMARY = f"llm-mini-refine20+d={DEPTH}+avg2+rrf-d46+c={guard.C}"  # on top of Decision46
SECONDARY = f"llm-mini-refine20+d={DEPTH}+avg2"  # same responses, no safeguard
SYSTEMS = (PRIMARY, SECONDARY)
LABEL_LAYER = catalog.SHARED_LABELS_D46
JUDGE_TASK_CAP_USD = 0.20
EXPECTED_OUTPUT = 150

PLAN = {
    "version": "refine20-v1", "model": client.MODEL, "reasoning_effort": "none",
    "hypothesis": "A focused 0-10 re-score of the reranked top20 separates direct answers "
                  "from related work better than the 50-paper 0-4 pass.",
    "one_change": f"Second stage over the Decision46 top{DEPTH}: two 0-10 passes averaged; "
                  "sort, ties keep Decision46 order; RRF c=30 with Decision46 order (primary).",
    "primary_system": PRIMARY, "secondary_system": SECONDARY, "reference": REFERENCE,
    "depth": DEPTH, "passes": len(PASSES), "safeguard_rrf_c": guard.C,
    "headroom_offline": "Perfect top20 reorder of Decision46: 0.946 nDCG@10 vs 0.768 "
                        "(98 of 143 buried grade-2 papers are at ranks 11-20).",
    "labels": "shared-labels/labels-d46.json plus a child layer of judge-graded top10 fills "
              "(frozen judge; the 100 reference overrides, legacy name human, preserved).",
    "stages": {"pilot": "20 pilot dev queries: 40 requests.",
               "full": "Other 80 dev queries: 160 requests; only if the pilot gate passed "
                       "and the user approved."},
    "pilot_gate": facets.PLAN["pilot_gate"],
    "qualifies_if": facets.PLAN["qualifies_if"],
    "diagnostics_not_gates": ["nDCG by query type", "grade-0 papers in the top10",
                              "grade-2 papers promoted from ranks 11-20 into the top10",
                              "score distribution and ties"],
    "multiple_comparisons": facets.PLAN["multiple_comparisons"],
    "cost": "Expected ~$0.20 pilot and ~$0.80 full (uncached prices). Judge <= $0.20.",
    "budget_usd": {"refine": client.REFINE_TASK_CAP / 1e9, "judge": JUDGE_TASK_CAP_USD},
    "automatic_retries": False, "held_out_queries_used": False, "automatic_promotion": False,
}


def prepare() -> dict:
    if config.DECISION46_RERANK_SYSTEM != REFERENCE:  # these experiments build on Decision46
        raise ValueError("Reranking baseline changed; create a new experiment identity")
    state = pass2.prepare()
    runs = pass2.build(state, *pass2.pass_scores(state))[0]
    state["d46"] = runs[REFERENCE]
    state["retrieval"] = runs[dev.v1.BASELINE]
    requests = []
    for q in state["qids"]:
        presented = dev.v1.presentation(q, state["d46"][q][:DEPTH])
        encoded = client.encode_refine_payload(state["queries"][q]["query"], presented, state["papers"])
        requests.append({"query_id": q, "presented_ids": presented, "encoded": encoded,
                         "pilot": q in state["pilot"],
                         "keys": {p: client.repeat_key(encoded, p) for p in PASSES}})
    state["refine"] = requests
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", {
        **PLAN, "prompt_sha256": fusion.fingerprint(client.REFINE_SYSTEM),
        "pilot_query_ids": sorted(state["pilot"]),
        "request_keys": {r["query_id"]: r["keys"][1] for r in requests}})
    return state


def stage_requests(state: dict, stage: str) -> list[dict]:
    if stage not in ("pilot", "full"):
        raise ValueError("Stage must be pilot or full")
    return [r for r in state["refine"] if r["pilot"] == (stage == "pilot")]


def response_path(key: str):
    return OUT / "responses" / f"{key}.json"


def pass_meta(r: dict, p: int) -> dict:
    return {"query_id": r["query_id"], "pass": p, "presented_ids": r["presented_ids"]}


def read_pass(r: dict, p: int) -> dict | None:
    key = r["keys"][p]
    return facets._read(response_path(key), key, r["encoded"], pass_meta(r, p),
                        client.validate_refine_scores)


def call_pass(r: dict, p: int, ledger: client.PilotLedger) -> None:
    key = r["keys"][p]
    facets._call(response_path(key), key, r["encoded"], DEPTH, ledger, pass_meta(r, p),
                  failure_dir=OUT / "failures")


def preflight(state: dict, stage: str, ledger: client.PilotLedger) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    todo, blocked = [], 0
    for r in stage_requests(state, stage):
        for p in PASSES:
            if read_pass(r, p) is None:
                if ledger.attempted(r["keys"][p]):
                    blocked += 1
                else:
                    todo.append(r["encoded"])
    tokens = sum(len(tokenizer.encode(e.decode("utf-8"))) for e in todo)
    usd = lambda out: (tokens * 1.1 * client.INPUT_PRICE + len(todo) * out * client.OUTPUT_PRICE) / 1e9
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    summary = ledger.summary()
    return {
        "stage": stage, "requests": len(todo), "attempted_uncached_no_retry": blocked,
        "expected_tokens": round(tokens * 1.1) + len(todo) * EXPECTED_OUTPUT,
        "expected_usd": usd(EXPECTED_OUTPUT), "worst_case_usd": usd(client.REFINE_MAX_OUTPUT),
        "max_single_reservation_tokens": max((client.reserved_input(e) for e in todo), default=0)
                                         + client.REFINE_MAX_OUTPUT,
        "spent_usd": summary["accounted_usd"], "cap_usd": client.REFINE_TASK_CAP / 1e9,
        "shared_remaining_tokens_today": limit - summary["shared_accounted_tokens"],
    }


def run_stage(state: dict, stage: str, ledger: client.PilotLedger) -> None:
    for i, r in enumerate(stage_requests(state, stage)):
        try:
            for p in PASSES:  # both passes back to back: identical prefix for prompt caching
                if read_pass(r, p) is None:
                    call_pass(r, p, ledger)
        except api.OpenAIError:
            print(f"STOPPED at {r['query_id']}; investigate before any further requests.", flush=True)
            raise
        if i == 0:
            print(f"Smoke query {r['query_id']} passed ({len(PASSES)} passes).", flush=True)


def refine(d46: list[str], presented: list[str], answers: list[dict]) -> list[str]:
    """Top DEPTH sorted by the average 0-10 score, ties keep Decision46 order; tail unchanged."""
    avg = {pid: statistics.fmean(a[f"P{i}"] for a in answers) for i, pid in enumerate(presented, 1)}
    if set(avg) != set(d46[:DEPTH]):
        raise ValueError("Scored papers differ from the Decision46 top prefix")
    return sorted(d46[:DEPTH], key=lambda p: (-avg[p], d46.index(p))) + d46[DEPTH:]


def build(state: dict, qids: list[str]) -> tuple[dict, dict]:
    runs = {dev.v1.BASELINE: {q: state["retrieval"][q] for q in qids},
            REFERENCE: {q: state["d46"][q] for q in qids}, PRIMARY: {}, SECONDARY: {}}
    scores = {}
    by_q = {r["query_id"]: r for r in state["refine"]}
    for q in qids:
        r = by_q[q]
        answers = [read_pass(r, p) for p in PASSES]
        if any(a is None for a in answers):
            raise ValueError(f"{q}: refinement responses missing; run this stage first")
        scores[q] = {"presented": r["presented_ids"], "passes": answers}
        refined = refine(state["d46"][q], r["presented_ids"], answers)
        runs[SECONDARY][q] = refined
        runs[PRIMARY][q] = guard.fuse(state["d46"][q], refined, depth=DEPTH)
    for n, run in runs.items():
        fusion.validate_run(n, run, qids, state["papers"], exact_depth=100)
    return runs, scores


def diagnostics(state: dict, runs: dict, scores: dict, labels: dict) -> dict:
    qids = sorted(scores)
    values = [a[k] for x in scores.values() for a in x["passes"] for k in a]
    pass_gap = [abs(x["passes"][0][k] - x["passes"][1][k]) for x in scores.values() for k in x["passes"][0]]
    promoted = {n: sum(labels[q].get(p) == 2 and p not in state["d46"][q][:10]
                       for q in qids for p in runs[n][q][:10]) for n in SYSTEMS}
    demoted = {n: sum(labels[q].get(p) == 2 and p not in runs[n][q][:10]
                      for q in qids for p in state["d46"][q][:10]) for n in SYSTEMS}
    return {
        "score_histogram": {str(v): values.count(v) for v in range(11)},
        "pass_agreement": {"exact": sum(g == 0 for g in pass_gap) / len(pass_gap),
                           "mean_abs_gap": statistics.fmean(pass_gap)},
        "grade2_promoted_into_top10": promoted, "grade2_dropped_from_top10": demoted,
        "grade0_in_top10": {n: sum(labels[q].get(p) == 0 for q in qids for p in run[q][:10])
                            for n, run in runs.items()},
    }


def verdicts(results: dict, scopes: tuple[str, ...], mdd: float | None) -> dict:
    """Same frozen gate and qualification checks as Experiment D."""
    return facets.verdicts(results, scopes, mdd, systems=SYSTEMS, reference=REFERENCE)


def evaluate(state: dict, stage: str, run_judge: bool) -> dict | None:
    pilot = sorted(state["pilot"])
    qids = pilot if stage == "pilot" else state["qids"]
    runs, scores = build(state, qids)
    _, _, shared, _ = catalog.load_shared_labels(config.RESULTS_DIR, LABEL_LAYER)
    usage_path = OUT / "judge-accounting.json"
    prior = dev.judge_accounting(json.loads(usage_path.read_text(encoding="utf-8"))["rows"]) \
        if usage_path.exists() else {"usd": 0.0}
    labels, rows = blend.fill_top10({**state, "qids": qids}, runs, shared, OUT,
                                    JUDGE_TASK_CAP_USD - prior["usd"], run_judge,
                                    parent=LABEL_LAYER.as_posix())
    if labels is None:
        return None
    snapshot = {**shared, "labels": labels}
    scopes = {"pilot20": pilot} if stage == "pilot" else {
        "all100": qids, "pilot20": pilot, "new80": [q for q in qids if q not in pilot]}
    results = {s: score.compare(runs, REFERENCE, {**snapshot, "labels": {q: labels[q] for q in ids}},
                                state["papers"], state["queries"], ids) for s, ids in scopes.items()}
    mdd = None if stage == "pilot" else json.loads(
        (pass2.OUT / "report.json").read_text(encoding="utf-8"))["noise"]["safeguard"]["single_pass_mdd"]
    ledger = client.PilotLedger(version=client.REFINE_VERSION)
    report = {
        "stage": stage, "plan": json.loads((OUT / "preregistration.json").read_text(encoding="utf-8")),
        "mdd": mdd, "results": results, "verdicts": verdicts(results, tuple(scopes), mdd),
        "diagnostics": diagnostics(state, runs, scores, labels),
        "accounting": {"refine": ledger.summary(),
                       "judge": dev.judge_accounting(rows) if rows else {}},
        "promoted": False,
    }
    name = "pilot-report" if stage == "pilot" else "report"
    if stage == "full":
        report["refine_cost_per_query_usd"] = report["accounting"]["refine"]["accounted_usd"] / len(qids)
        for n in SYSTEMS:
            fusion._write_json(OUT / f"{n}.run.json", runs[n])
    fusion._write_json(OUT / f"{name}.json", report)
    write_markdown(report, OUT / f"{name}.md")
    return report


def write_markdown(report: dict, path) -> None:
    scopes = list(report["results"])
    main = "pilot20" if report["stage"] == "pilot" else "all100"
    full = report["results"][main]
    lines = [f"# Experiment E: top{DEPTH} refinement ({report['stage']} stage)", "",
             f"Reference: `{REFERENCE}` (Decision46). Primary re-scores its top{DEPTH} 0-10 "
             f"(two passes averaged) and applies RRF c={guard.C} with the Decision46 order; "
             "secondary: same responses, no RRF."
             + (f" Noise threshold (MDD): {report['mdd']:.4f}." if report["mdd"] else
                " Pilot gate only: a sanity screen, not evidence."), "",
             "| System | nDCG@10 | " + " | ".join(f"{s} Δ" for s in scopes)
             + " | Source MRR@10 | R@1 | P@10 | Passes |",
             "|---|---|" + "---|" * len(scopes) + "---|---|---|---|"]
    for n in (dev.v1.BASELINE, REFERENCE, *SYSTEMS):
        s = full["systems"][n]["all"]
        deltas = [report["results"][k]["summary"][n]["all"]["ndcg@10"]["paired_vs_working"] for k in scopes]
        v = report["verdicts"].get(n)
        lines.append(
            f"| `{n}` | {s['ndcg@10']['mean']:.4f} | "
            + " | ".join("—" if n == REFERENCE or not d else
                         f"{d['difference']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]"
                         for d in deltas)
            + f" | {s['source_mrr@10']['mean']:.4f} | {s['source_recall@1']['mean']:.0%} | "
            f"{s['precision@10']['mean']:.3f} | "
            + ("—" if v is None else "**yes**" if v["passes"] else
               "no (" + ", ".join(k for k, ok in v["checks"].items() if not ok) + ")") + " |")
    lines += ["", "## nDCG@10 by query type (diagnostic only)", "",
              "| System | " + " | ".join(catalog.QUERY_TYPES) + " |",
              "|---|" + "---|" * len(catalog.QUERY_TYPES)]
    for n in (dev.v1.BASELINE, REFERENCE, *SYSTEMS):
        t = full["systems"][n]["by_query_type"]
        lines.append(f"| `{n}` | " + " | ".join(
            "—" if t[k]["ndcg@10"]["mean"] is None else f"{t[k]['ndcg@10']['mean']:.4f}"
            for k in catalog.QUERY_TYPES) + " |")
    d = report["diagnostics"]
    lines += ["", "## Diagnostics", "",
              f"- 0-10 score histogram (all paper-passes): {d['score_histogram']}.",
              f"- Pass agreement: {d['pass_agreement']['exact']:.0%} identical; mean gap "
              f"{d['pass_agreement']['mean_abs_gap']:.2f} points.",
              "- Grade-2 papers promoted into the top10 / dropped from it: " + "; ".join(
                  f"`{n}` +{d['grade2_promoted_into_top10'][n]} / -{d['grade2_dropped_from_top10'][n]}"
                  for n in SYSTEMS) + ".",
              "- Grade-0 papers in the top10: " + ", ".join(
                  f"`{n}` {c}" for n, c in d["grade0_in_top10"].items()) + ".", ""]
    acc = report["accounting"]
    lines += ["## Cost", "",
              f"- Refinement: {acc['refine']['requests']} requests, "
              f"${acc['refine']['accounted_usd']:.4f} (uncached prices).",
              f"- Judge: ${acc['judge'].get('usd', 0):.4f}.", "",
              "## Cautions", "",
              "- Dev only; the judge and reranker share a model family.",
              "- The loss analysis that motivated this experiment read dev queries.",
              f"- Label overrides called \"human\" in older files are {config.REFERENCE_LABELER} "
              "reference grades; no labels here are human.",
              "- Not promoted."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("pilot", "full"), required=True)
    parser.add_argument("--run", action="store_true", help="send this stage's requests")
    parser.add_argument("--judge", action="store_true", help="grade unjudged top10 pairs")
    args = parser.parse_args(argv)
    state = prepare()
    ledger = client.PilotLedger(version=client.REFINE_VERSION)
    if args.stage == "full":
        gate = OUT / "pilot-report.json"
        if not gate.exists() or not any(v["passes"] for v in json.loads(
                gate.read_text(encoding="utf-8"))["verdicts"].values()):
            raise ValueError("The full stage requires a passed, saved pilot gate")
    pre = preflight(state, args.stage, ledger)
    print(json.dumps(pre, indent=2), flush=True)
    if pre["attempted_uncached_no_retry"]:
        raise api.OpenAIError("A prior request has no valid cache; investigate before continuing")
    if pre["requests"]:
        fusion._write_json(OUT / f"preflight-{args.stage}.json", pre)
        if not args.run:
            return
        if pre["worst_case_usd"] > pre["cap_usd"] - pre["spent_usd"]:
            raise api.BudgetExceeded("Worst-case cost exceeds the approved ceiling; no request sent")
        if pre["expected_tokens"] + pre["max_single_reservation_tokens"] > pre["shared_remaining_tokens_today"]:
            raise api.BudgetExceeded("Expected usage exceeds today's shared token allowance; no request sent")
        run_stage(state, args.stage, ledger)
    report = evaluate(state, args.stage, args.judge)
    if report is not None:
        print(json.dumps({n: v["passes"] for n, v in report["verdicts"].items()}))


if __name__ == "__main__":
    main()
