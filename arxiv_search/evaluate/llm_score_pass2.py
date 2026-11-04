"""Two-pass score averaging for the top50 LLM reranker (100 dev queries).

LLM scores move between identical requests (Decision44: about a third of 0-4 scores
changed). A single pass therefore carries one-off misses, e.g. a source paper scored 0.
Hypothesis: averaging two identical passes per query cancels part of that noise, so
the *same* safeguard rule (RRF c=30 with retrieval order) ranks better and more stably.

One change versus the reranking baseline: the scores (mean of two passes instead of
one). Prompt, model, payload, candidate pool and safeguard rule are unchanged.

Pass A = the cached llm-score-dev100 responses. Pass B = the cached Decision44 repeat
for the 20 pilot queries plus 80 new byte-identical requests. Preflight by default;
--run sends requests (smoke gate on the first, stop on any failure, no retries);
--judge grades unjudged top10 pairs for the two pre-registered systems only.
"""

from __future__ import annotations

import argparse
import json
import statistics

import tiktoken

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, graded
from arxiv_search.evaluate import llm_score_blend as blend, llm_score_dev100 as dev
from arxiv_search.evaluate import llm_score_pilot as score, llm_score_repeat as rep
from arxiv_search.evaluate import llm_score_safeguard as guard, results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "llm-score-pass2"
RUN = 1
AVG = f"{dev.LLM}+avg2"
AVG_SAFE = f"{dev.LLM}+avg2+rrf-baseline+c={guard.C}"
B_LLM, B_SAFE = "passB-top50", "passB-safeguard"  # diagnostics only, never published as runs
REFERENCE = config.DECISION45_RERANK_SYSTEM  # frozen reference for this experiment
JUDGE_TASK_CAP_USD = 0.15

PLAN = {
    "version": client.PASS2_VERSION, "model": client.MODEL,
    "hypothesis": "Averaging two identical LLM passes reduces score noise; the unchanged "
                  "safeguard rule on averaged scores beats the single-pass safeguard.",
    "primary_system": AVG_SAFE, "secondary_system": AVG, "reference": REFERENCE,
    "one_change": "LLM scores = mean of two byte-identical passes; everything else unchanged.",
    "passes": "A = llm-score-dev100 cache; B = llm-score-repeat cache (20 pilot) + 80 new requests.",
    "qualifies_if": {
        "fully_judged_top10": True,
        "ndcg@10_delta_vs_reference": "> reference MDD (0.009) with paired 95% CI lower bound > 0",
        "source_mrr@10": ">= reference - 0.02",
        "consistency": "nDCG delta vs reference > 0 on both pilot20 and new80",
    },
    "also_measured": "100-query run-to-run noise of single-pass top50 and safeguard (A vs B; "
                     "unjudged pass-B-only pairs bounded at 0 and 2, never graded).",
    "cost_note": "Doubles reranker cost and calls per query; latency unchanged if passes run in parallel.",
    "budget_usd": client.PASS2_TASK_CAP / 1e9, "max_requests": client.PASS2_MAX_REQUESTS,
    "automatic_retries": False, "held_out_queries_used": False, "automatic_promotion": False,
}


def prepare() -> dict:
    state = rep.prepare()  # validates the dev100 requests and the 20 pilot repeat keys
    for r in state["requests"]:
        r["repeat_key"] = client.repeat_key(r["encoded"], RUN)
    new = [r for r in state["requests"] if not r["pilot"]]
    if len(new) != client.PASS2_MAX_REQUESTS:
        raise ValueError("Expected 80 non-pilot requests")
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", {**PLAN, "new_request_keys": [r["repeat_key"] for r in new]})
    return {**state, "new": new}


def response_path(r: dict):
    return OUT / "responses" / f"{r['repeat_key']}.json"


def read_new(r: dict) -> dict | None:
    path = response_path(r)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value["request_key"] != r["request_key"] or value["repeat_key"] != r["repeat_key"]
            or value["presented_ids"] != r["presented_ids"]
            or value["answer_sha256"] != fusion.fingerprint(value["answer"])
            or value["usage"]["status"] != "completed"):
        raise ValueError(f"{r['query_id']}: pass-B cache provenance mismatch")
    return client.validate_scores(value["answer"], len(r["presented_ids"]))


def call_new(r: dict, ledger: client.PilotLedger) -> None:
    if read_new(r) is not None:
        return
    if ledger.attempted(r["repeat_key"]) is not None:
        raise api.OpenAIError("Already attempted without a valid cache; no retry")
    answer, usage = client.call_once(
        r["encoded"], len(r["presented_ids"]), ledger, attempt_key=r["repeat_key"],
        failure_output_path=OUT / "failures" / f"{r['repeat_key']}.json")
    value = {"request_key": r["request_key"], "repeat_key": r["repeat_key"], "model": client.MODEL,
             "presented_ids": r["presented_ids"], "answer": answer, "usage": usage,
             "answer_sha256": fusion.fingerprint(answer)}
    path = response_path(r)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".tmp").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    path.with_suffix(".tmp").replace(path)


def preflight(state: dict, ledger: client.PilotLedger) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    todo = [r for r in state["new"] if read_new(r) is None]
    blocked = [r for r in todo if ledger.attempted(r["repeat_key"])]
    tokens = sum(len(tokenizer.encode(r["encoded"].decode("utf-8"))) for r in todo)
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    summary = ledger.summary()
    expected_out = 350
    return {"new_requests": len(todo), "attempted_uncached_no_retry": len(blocked),
            "serialized_input_token_estimate": tokens,
            "expected_tokens": round(tokens * 1.1) + len(todo) * expected_out,
            "expected_usd": (tokens * 1.1 * client.INPUT_PRICE
                             + len(todo) * expected_out * client.OUTPUT_PRICE) / 1e9,
            "worst_case_usd": (tokens * 1.1 * client.INPUT_PRICE
                               + len(todo) * ledger.output_cap * client.OUTPUT_PRICE) / 1e9,
            "max_single_reservation_tokens": max(
                (client.reserved_input(r["encoded"]) + ledger.output_cap for r in todo), default=0),
            "pass2_spent_usd": summary["accounted_usd"], "pass2_cap_usd": client.PASS2_TASK_CAP / 1e9,
            "shared_remaining_tokens_today": limit - summary["shared_accounted_tokens"]}


def pass_scores(state: dict) -> tuple[dict, dict]:
    a, b = {}, {}
    for r in state["requests"]:
        q, pres = r["query_id"], r["presented_ids"]
        sa = client.validate_scores(dev.cached(r, score.VERSION if r["pilot"] else client.DEV100_VERSION)[0], 50)
        sb = rep.read_repeat({**r, "repeat_key": client.repeat_key(r["encoded"], rep.RUN)}) \
            if r["pilot"] else read_new(r)
        if sb is None:
            raise ValueError(f"{q}: pass-B response missing; run --run first")
        a[q] = {p: float(sa[f"P{i}"]) for i, p in enumerate(pres, 1)}
        b[q] = {p: float(sb[f"P{i}"]) for i, p in enumerate(pres, 1)}
    return a, b


def build(state: dict, a: dict, b: dict) -> tuple[dict, dict]:
    runs = dev.build_runs(state)
    diag = {B_LLM: {}, B_SAFE: {}}
    for q in state["qids"]:
        base = state["base"][q]
        avg = {p: (a[q][p] + b[q][p]) / 2 for p in a[q]}
        runs.setdefault(AVG, {})[q] = score.rerank_prefix(base, avg, 50)
        runs.setdefault(AVG_SAFE, {})[q] = guard.fuse(base, runs[AVG][q])
        diag[B_LLM][q] = score.rerank_prefix(base, b[q], 50)
        diag[B_SAFE][q] = guard.fuse(base, diag[B_LLM][q])
    for n, run in {**runs, **diag}.items():
        fusion.validate_run(n, run, state["qids"], state["papers"], exact_depth=100)
    return runs, diag


def noise(state: dict, runs: dict, diag: dict, labels: dict, a: dict, b: dict) -> dict:
    """Pass A vs pass B per-query nDCG change, unjudged pairs bounded at 0 and 2."""
    out = {}
    for name, a_name, b_name in (("top50", dev.LLM, B_LLM), ("safeguard", REFERENCE, B_SAFE)):
        worst = None
        for grade in (0, 2):
            diffs = []
            for q in state["qids"]:
                ra, rb = runs[a_name][q], diag[b_name][q]
                lab = {q: {**{p: grade for p in ra[:10] + rb[:10]}, **labels[q]}}
                na = graded.score_graded({q: ra}, lab, state["queries"])[0]["ndcg@10"]
                nb = graded.score_graded({q: rb}, lab, state["queries"])[0]["ndcg@10"]
                diffs.append(nb - na)
            sd = statistics.pstdev(diffs)
            row = {"assumed_unjudged_grade": grade, "mean_change": statistics.fmean(diffs),
                   "mean_abs_change": statistics.fmean(map(abs, diffs)), "sd_per_query_change": sd,
                   "est_sd_of_100q_mean": sd / 2 ** 0.5 / 10}
            if worst is None or sd > worst["sd_per_query_change"]:
                worst = row
        unjudged = sum(p not in labels[q] for q in state["qids"] for p in diag[b_name][q][:10])
        out[name] = {**worst, "unjudged_passB_top10_pairs": unjudged,
                     "single_pass_mdd": 1.96 * 2 ** 0.5 * worst["est_sd_of_100q_mean"],
                     "avg2_mdd_if_independent": 1.96 * worst["est_sd_of_100q_mean"]}
    agree = [b[q][p] - a[q][p] for q in state["qids"] for p in a[q]]
    out["score_agreement"] = {"pairs": len(agree), "exact": sum(d == 0 for d in agree),
                              "changed_by_2plus": sum(abs(d) >= 2 for d in agree),
                              "mean_abs_change": statistics.fmean(map(abs, agree))}
    return out


def publish(state: dict, runs: dict, diag: dict, shared: dict, labels: dict,
            judge_usage: dict, ledger: client.PilotLedger, a: dict, b: dict) -> dict:
    qids, queries, papers = state["qids"], state["queries"], state["papers"]
    snapshot = {**shared, "labels": labels}
    scopes = {"all100": qids, "new80": [q for q in qids if q not in state["pilot"]],
              "pilot20": sorted(state["pilot"])}
    results = {s: score.compare(runs, REFERENCE, {**snapshot, "labels": {q: labels[q] for q in ids}},
                                papers, queries, ids) for s, ids in scopes.items()}
    ref_mdd = 1.96 * 2 ** 0.5 * json.loads(
        (config.RESULTS_DIR / config.RERANK_BASELINE_NOISE_DIR / "report.json")
        .read_text(encoding="utf-8"))["systems"][REFERENCE]["est_sd_of_100q_mean"]
    verdicts = {}
    for n in (AVG_SAFE, AVG):
        full = results["all100"]
        mine, ref = full["systems"][n], full["systems"][REFERENCE]
        paired = full["summary"][n]["all"]["ndcg@10"]["paired_vs_working"]
        sub = {s: (results[s]["summary"][n]["all"]["ndcg@10"]["paired_vs_working"] or {})
               .get("difference") for s in ("pilot20", "new80")}
        checks = {
            "fully_judged_top10": mine["top10_fully_judged"],
            "ndcg_gain_beyond_noise": bool(paired) and paired["difference"] > ref_mdd
                                      and paired["ci95"][0] > 0,
            "source_mrr": mine["all"]["source_mrr@10"]["mean"]
                          >= ref["all"]["source_mrr@10"]["mean"] - 0.02,
            "consistent_subsets": all(v is not None and v > 0 for v in sub.values()),
        }
        verdicts[n] = {"checks": checks, "qualifies": all(checks.values()),
                       "ndcg_delta": paired, "subset_deltas": sub}
    for n in (AVG, AVG_SAFE):
        fusion._write_json(OUT / f"{n}.run.json", runs[n])
    report = {"plan": json.loads((OUT / "preregistration.json").read_text(encoding="utf-8")),
              "reference_mdd": ref_mdd, "results": results, "verdicts": verdicts,
              "noise": noise(state, runs, diag, labels, a, b),
              "reranker_accounting": ledger.summary(),
              "cost_per_query_usd": 2 * (json.loads((dev.OUT / "report.json").read_text(
                  encoding="utf-8"))["reranker_accounting"]["accounted_usd"] / 80),
              "judge_accounting": judge_usage, "promoted": False}
    fusion._write_json(OUT / "report.json", report)
    write_markdown(report)
    return report


def write_markdown(report: dict) -> None:
    full = report["results"]["all100"]
    order = [dev.v1.BASELINE, dev.LLM, REFERENCE, AVG, AVG_SAFE]
    lines = ["# Two-pass score averaging (100 dev queries)", "",
             "One change vs the reranking baseline: LLM scores are the mean of two byte-identical "
             f"passes. Reference: `{REFERENCE}`; its noise threshold (MDD) is "
             f"{report['reference_mdd']:.4f}.", "",
             "| System | nDCG@10 | Δ vs reference [95% CI] | pilot20 Δ | new80 Δ | Source MRR@10 | "
             "R@1 | Qualifies |", "|---|---|---|---|---|---|---|---|"]
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
            + ("—" if v is None else ("**yes**" if v["qualifies"] else
                                      "no (" + ", ".join(k for k, ok in v["checks"].items() if not ok) + ")"))
            + " |")
    lines += ["", "## nDCG@10 by query type (diagnostic only)", "",
              "| System | " + " | ".join(catalog.QUERY_TYPES) + " |",
              "|---|" + "---|" * len(catalog.QUERY_TYPES)]
    for n in order:
        t = full["systems"][n]["by_query_type"]
        lines.append(f"| `{n}` | " + " | ".join(f"{t[k]['ndcg@10']['mean']:.4f}"
                                                 for k in catalog.QUERY_TYPES) + " |")
    nz = report["noise"]
    ag = nz["score_agreement"]
    lines += ["", "## Run-to-run noise, 100 queries (pass A vs pass B, single pass)", "",
              f"- LLM scores identical in {ag['exact']}/{ag['pairs']} pairs "
              f"({ag['exact'] / ag['pairs']:.1%}); changed by 2+: {ag['changed_by_2plus']}; "
              f"mean absolute change {ag['mean_abs_change']:.3f}.", "",
              "| System | Mean abs per-query nDCG change | Est. SD of 100-q mean | Single-pass MDD | "
              "Avg-of-2 MDD (if passes independent) | Unjudged pass-B pairs |",
              "|---|---|---|---|---|---|"]
    for k in ("top50", "safeguard"):
        x = nz[k]
        lines.append(f"| {k} | {x['mean_abs_change']:.4f} | {x['est_sd_of_100q_mean']:.4f} | "
                     f"{x['single_pass_mdd']:.4f} | {x['avg2_mdd_if_independent']:.4f} | "
                     f"{x['unjudged_passB_top10_pairs']} |")
    acc = report["reranker_accounting"]
    lines += ["", "## Cost", "",
              f"- New pass-B requests: {acc['requests']}; ${acc['accounted_usd']:.4f}.",
              f"- Two passes cost ≈ ${report['cost_per_query_usd']:.4f} per uncached query (2x).",
              f"- Judge: ${report['judge_accounting'].get('usd', 0):.4f}.", "",
              "## Cautions", "",
              "- Dev only; judge and reranker share a model family.",
              "- Pass A for the pilot queries was sent on an earlier day than pass B.",
              "- Not promoted."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="send the 80 pass-B requests")
    parser.add_argument("--judge", action="store_true", help="grade unjudged top10 pairs")
    args = parser.parse_args(argv)
    state = prepare()
    ledger = client.PilotLedger(version=client.PASS2_VERSION)
    pre = preflight(state, ledger)
    print(json.dumps(pre, indent=2), flush=True)
    if pre["attempted_uncached_no_retry"]:
        raise api.OpenAIError("A prior request has no valid cache; investigate before continuing")
    if pre["new_requests"]:
        fusion._write_json(OUT / "preflight.json", pre)
        if not args.run:
            return
        # The ledger also enforces the hard cap per request before anything is sent.
        if pre["expected_usd"] > pre["pass2_cap_usd"] - pre["pass2_spent_usd"]:
            raise api.BudgetExceeded("Expected cost exceeds the approved pass-2 ceiling; no request sent")
        if pre["expected_tokens"] + pre["max_single_reservation_tokens"] > pre["shared_remaining_tokens_today"]:
            raise api.BudgetExceeded("Expected usage exceeds today's shared token allowance; no request sent")
        for i, r in enumerate(state["new"]):
            try:
                call_new(r, ledger)
            except api.OpenAIError:
                print(f"STOPPED at {r['query_id']}; investigate before any further requests.", flush=True)
                raise
            if i == 0:
                print(f"Smoke request {r['query_id']} passed.", flush=True)
    a, b = pass_scores(state)
    runs, diag = build(state, a, b)
    shared = blend.shared_snapshot()
    labels, rows = blend.fill_top10(state, runs, shared, OUT, JUDGE_TASK_CAP_USD, args.judge)
    if labels is None:
        return
    report = publish(state, runs, diag, shared, labels,
                     dev.judge_accounting(rows) if rows else {}, ledger, a, b)
    print(json.dumps({n: v["qualifies"] for n, v in report["verdicts"].items()}))


if __name__ == "__main__":
    main()
