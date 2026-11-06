"""One-shot remaining80 dev confirmation of GPT-5.4 two-pass scores-only refinement.

The candidate was chosen on the 20 pilot dev queries. This module scores it once on the
other 80 dev queries, which no top20 experiment has looked at. The 300 test queries are
never read. `prepare()` is free; `execute()` spends money and needs owner approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics

import tiktoken

from arxiv_search import config, openai_answer, openai_api, openai_rerank
from arxiv_search.evaluate import llm_reranker_pilot, top20_ablations, top20_model_pilot
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "top20-confirm"
MODEL = top20_model_pilot.MODEL
TASK = "top20-confirm-remaining80-v1"
D46 = config.RESULTS_DIR / "llm-score-pass2" / "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json"
D47 = (config.RESULTS_DIR / "llm-score-refine-pin" /
       "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json")
LABELS = config.RESULTS_DIR / "top20-label-completion" / "labels.json"
MIN_GAIN = 0.0106


def remaining80() -> list[str]:
    split = json.loads((config.EVAL_DIR / "split.json").read_bytes())
    pilot = set(json.loads((top20_model_pilot.OUT / "preregistration.json")
                           .read_bytes())["pilot_queries"])
    rest = [q for q in split["dev"] if q not in pilot]
    if len(rest) != 80 or set(rest) & set(split["test"]) or len(pilot) != 20:
        raise ValueError("Expected exactly the 80 non-pilot dev queries")
    return rest


def _inputs():
    queries = {q["query_id"]: q for line in (config.EVAL_DIR / "queries.jsonl")
               .read_text(encoding="utf-8").splitlines() if (q := json.loads(line))}
    papers = {p["arxiv_id"]: p for line in (config.PROJECT_ROOT / "data" / "processed" /
                                           "corpus.jsonl").read_text(encoding="utf-8").splitlines()
              if (p := json.loads(line))}
    return (queries, papers, json.loads(D46.read_bytes()), json.loads(D47.read_bytes()),
            json.loads(LABELS.read_bytes())["labels"])


def prepare() -> dict:
    qids = remaining80()
    queries, papers, d46, d47, labels = _inputs()
    count = tiktoken.get_encoding("o200k_base")
    requests = []
    for q in qids:
        presented = llm_reranker_pilot.presentation(q, d46[q][:20])
        if any(p not in labels[q] for p in presented) or set(presented) != set(d47[q][:20]):
            raise ValueError("Top20 must be fully judged and identical to D47's candidate pool")
        encoded = top20_model_pilot.payload(queries[q]["query"], presented, papers)
        requests.append({
            "query_id": q, "presented_ids": presented,
            "payload_sha256": hashlib.sha256(encoded).hexdigest(),
            "estimated_input": len(count.encode(encoded.decode(), disallowed_special=())),
            "reserved_input": openai_answer.reserved_input(encoded),
        })
    price_in, price_out = openai_answer.PRICES[MODEL]
    pilot = json.loads((top20_model_pilot.OUT / "report.json").read_bytes())["accounting"]
    pilot_out = pilot["by_model"][MODEL]["output_tokens"] / pilot["requests"]
    cost = {
        "pilot_mean_output_tokens": pilot_out,
        "requests": 2 * len(requests),
        "estimated_usd": sum(2 * (r["estimated_input"] * price_in + pilot_out * price_out)
                             for r in requests) / 1e9,
        "worst_case_reservation_usd": sum(
            2 * (r["reserved_input"] * price_in + openai_rerank.REFINE_MAX_OUTPUT * price_out)
            for r in requests) / 1e9,
        "worst_case_reserved_tokens": sum(
            2 * (r["reserved_input"] + openai_rerank.REFINE_MAX_OUTPUT) for r in requests),
    }
    plan = {
        "version": "top20-confirm-v1",
        "status": "frozen before any remaining80 GPT-5.4 call; paid run requires owner approval",
        "scope": "80 dev queries not in pilot20. Test split never read.",
        "candidate": "GPT-5.4 (reasoning none), refine20-v1 prompt, same presentation and "
                     "512-token output cap, two identical passes, average scores, sort by score "
                     "with D46 order as tie-break, pin D46 rank1, tail unchanged",
        "baseline": "Saved D47 production ranking, scored on completed top20 labels",
        "model": MODEL, "selected_on": "pilot20 (top20-ablations scores_only/average)",
        "query_ids": qids, "requests": requests,
        "primary_gate": {"ndcg_delta_vs_d47": f">{MIN_GAIN} and paired95% CI lower bound>0",
                         "source_mrr_delta_vs_d47": ">=-0.02",
                         "complete": "160 valid replies", "judged_top10": "100%"},
        "diagnostics_not_gates": ["one-pass scores-only (pass1)", "equal RRF averaged",
                                  "query-type deltas", "all-100 dev combined (pilot-contaminated)"],
        "failure_policy": "No retries, no resends, no prompt or model changes. Any failed reply "
                          "stops the run and is reported as incomplete.",
        "cost": cost,
        "fingerprints": {"d46": hashlib.sha256(D46.read_bytes()).hexdigest(),
                         "d47": hashlib.sha256(D47.read_bytes()).hexdigest(),
                         "labels": hashlib.sha256(LABELS.read_bytes()).hexdigest()},
        "automatic_promotion": False, "test_evaluation": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", plan)
    return plan

def execute(cap_usd: float, large_daily_guard: int, authority: str) -> dict:
    from arxiv_search.evaluate import answer_eval as ev, metrics

    plan = prepare()
    freeze(OUT / "run-approval.json", {
        "cap_usd": cap_usd, "max_requests": 160, "process_large_daily_guard": large_daily_guard,
        "authority": authority,
        "plan_sha256": hashlib.sha256((OUT / "preregistration.json").read_bytes()).hexdigest(),
    })
    queries, papers, d46, d47, labels = _inputs()
    ledger = openai_answer.TaskLedger(TASK, round(cap_usd * 1e9), 160)
    previous = config.OPENAI_TOKEN_LIMITS["large"]
    rows = []
    try:
        config.OPENAI_TOKEN_LIMITS["large"] = large_daily_guard
        for request in plan["requests"]:
            q, presented = request["query_id"], request["presented_ids"]
            encoded = top20_model_pilot.payload(queries[q]["query"], presented, papers)
            if hashlib.sha256(encoded).hexdigest() != request["payload_sha256"]:
                raise ValueError("Request differs from frozen plan")
            replies, usages = [], []
            for n in (1, 2):
                path = OUT / "responses" / f"{q}-pass{n}.json"
                key = openai_rerank.repeat_key(encoded, n)
                saved = ev._read(path, encoded)
                if saved is None:
                    if ledger.attempted(key):
                        raise openai_api.OpenAIError("Attempt without cached outcome; no retry")
                    try:
                        value, usage = openai_answer.call_once(
                            encoded, ledger, validate=openai_rerank.validate_refine_scores,
                            attempt_key=key, failure_path=path.with_suffix(".failure.json"))
                    except openai_answer.InvalidAnswer as error:
                        ev._write(path, {"request_sha256": openai_answer.request_key(encoded),
                                         "outcome": {"status": error.status, "detail": error.detail},
                                         "usage": ledger.attempt(key)})
                        raise
                    saved = {"request_sha256": openai_answer.request_key(encoded),
                             "outcome": {"status": "ok", **value}, "usage": usage}
                    ev._write(path, saved)
                if saved["outcome"]["status"] != "ok":
                    raise openai_api.OpenAIError("Saved failure; stop without retry")
                replies.append({k: v for k, v in saved["outcome"].items() if k != "status"})
                usages.append(saved["usage"])
            print(f"{q} saved; task ${ledger.summary()['accounted_usd']:.4f}", flush=True)
            source = {queries[q]["source_arxiv_id"]: 2}
            row = {"query_id": q, "query_type": queries[q]["query_type"],
                   "d47": metrics.ndcg_at_k(d47[q], labels[q]), "usage": usages}
            for name, method, passes in (("candidate", "scores_only", "average"),
                                         ("one_pass", "scores_only", "pass1"),
                                         ("equal_rrf", "equal_rrf", "average")):
                ranked = top20_ablations.ranking(d46[q], presented, replies, method, passes)
                row[name] = metrics.ndcg_at_k(ranked, labels[q])
                row[f"{name}_source_delta"] = (metrics.reciprocal_rank(ranked, source)
                                               - metrics.reciprocal_rank(d47[q], source))
                row[f"{name}_fully_judged"] = metrics.judged_at_k(ranked, labels[q]) == 1
                row[f"{name}_top20"] = ranked[:20]
            rows.append(row)
    finally:
        config.OPENAI_TOKEN_LIMITS["large"] = previous
    report = summarize(rows, ledger.summary())
    ev._write(OUT / "report.json", report)
    (OUT / "report.md").write_text(markdown(report), encoding="utf-8")
    return report


def summarize(rows: list[dict], accounting: dict) -> dict:
    from arxiv_search.evaluate import metrics

    variants = {}
    for name in ("candidate", "one_pass", "equal_rrf"):
        delta, low, high = metrics.paired_diff_ci([r["d47"] for r in rows], [r[name] for r in rows])
        diffs = [r[name] - r["d47"] for r in rows]
        mrr = statistics.fmean(r[f"{name}_source_delta"] for r in rows)
        variants[name] = {
            "ndcg": statistics.fmean(r[name] for r in rows), "delta_vs_d47": delta,
            "ci95": [low, high], "source_mrr_delta_vs_d47": mrr,
            "wins_losses_ties": [sum(d > 1e-12 for d in diffs), sum(d < -1e-12 for d in diffs),
                                 sum(abs(d) <= 1e-12 for d in diffs)],
            "fully_judged": all(r[f"{name}_fully_judged"] for r in rows),
            "by_query_type": {t: statistics.fmean(r[name] - r["d47"] for r in rows
                                                  if r["query_type"] == t)
                              for t in sorted({r["query_type"] for r in rows})},
        }
    c = variants["candidate"]
    checks = {"ndcg": c["delta_vs_d47"] > MIN_GAIN and c["ci95"][0] > 0,
              "source_mrr": c["source_mrr_delta_vs_d47"] >= -0.02,
              "complete": len(rows) == 80 and accounting["requests"] == 160
                          and accounting["unknown_outcomes"] == 0,
              "fully_judged": c["fully_judged"]}
    seconds = sorted(max(u["latency_seconds"] for u in r["usage"]) for r in rows)
    first = [r["usage"][0]["latency_seconds"] for r in rows]
    return {
        "d47_ndcg": statistics.fmean(r["d47"] for r in rows), "variants": variants,
        "checks": checks, "confirmed": all(checks.values()),
        "latency_seconds": {"two_pass_max_of_two_mean": statistics.fmean(seconds),
                            "two_pass_max_of_two_p95": seconds[int(0.95 * (len(seconds) - 1))],
                            "one_pass_mean": statistics.fmean(first)},
        "usd_per_query": {"two_pass": accounting["accounted_usd"] / len(rows),
                          "one_pass": sum(openai_answer.cost_nanodollars(
                              MODEL, r["usage"][0]["input_tokens"], r["usage"][0]["output_tokens"])
                              for r in rows) / 1e9 / len(rows)},
        "accounting": accounting,
        "caution": "Latency is max of two sequential provider calls, not measured serving "
                   "latency. Labels are pooled AI judgments. One-pass and equal-RRF are "
                   "diagnostics from the same replies, not gated candidates.",
        "rows": rows,
    }


def markdown(report: dict) -> str:
    lines = ["# Remaining80 dev confirmation: GPT-5.4 two-pass scores-only", "",
             f"D47 nDCG@10: {report['d47_ndcg']:.4f}. Confirmed: **{report['confirmed']}** "
             f"({', '.join(f'{k}={v}' for k, v in report['checks'].items())}).", "",
             "| Variant | nDCG@10 | Delta vs D47 [95% CI] | W/L/T | Source MRR delta |",
             "|---|---:|---:|---:|---:|"]
    for name, v in report["variants"].items():
        lines.append(f"| {name} | {v['ndcg']:.4f} | {v['delta_vs_d47']:+.4f} "
                     f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | "
                     f"{'/'.join(map(str, v['wins_losses_ties']))} | "
                     f"{v['source_mrr_delta_vs_d47']:+.4f} |")
    lat, usd = report["latency_seconds"], report["usd_per_query"]
    lines += ["", f"Refinement cost/query: two-pass ${usd['two_pass']:.4f}, one-pass "
              f"${usd['one_pass']:.4f}. Total ${report['accounting']['accounted_usd']:.4f}.", "",
              f"API seconds: two-pass max-of-two mean {lat['two_pass_max_of_two_mean']:.2f} "
              f"(p95 {lat['two_pass_max_of_two_p95']:.2f}); one-pass mean {lat['one_pass_mean']:.2f}.",
              "", report["caution"], "", "Per-query rows: [report.json](report.json)."]
    return "\n".join(lines) + "\n"


RUN_ID = "llm-gpt54-refine20+d=20+avg2+scores+pin1-d46"


def combined_run() -> dict:
    """Decision 50 dev100 run from saved replies: pilot20 ablation + remaining80 confirmation."""
    from arxiv_search.evaluate import metrics

    queries, _, d46, d47, labels = _inputs()
    pilot = json.loads((top20_ablations.OUT / "report.json").read_bytes())["rows"]["scores_only/average"]
    confirm = json.loads((OUT / "report.json").read_bytes())["rows"]
    top = {r["query_id"]: r["top20"] for r in pilot} | {r["query_id"]: r["candidate_top20"]
                                                       for r in confirm}
    if len(top) != 100:
        raise ValueError("Expected all 100 dev queries")
    run = {q: top[q] + d46[q][20:] for q in d46}
    if any(set(run[q][:20]) != set(d46[q][:20]) or run[q][0] != d46[q][0] for q in run):
        raise ValueError("Pool or rank-one pin changed")
    freeze(OUT / f"{RUN_ID}.run.json", run)

    def score(ranked: dict) -> dict:
        src = {q: queries[q]["source_arxiv_id"] for q in ranked}
        return {"ndcg@10": statistics.fmean(metrics.ndcg_at_k(ranked[q], labels[q]) for q in ranked),
                "source_mrr@10": statistics.fmean(metrics.reciprocal_rank(ranked[q], {src[q]: 2})
                                                  for q in ranked),
                "source_recall@10": statistics.fmean(src[q] in ranked[q][:10] for q in ranked)}
    delta, low, high = metrics.paired_diff_ci(
        [metrics.ndcg_at_k(d47[q], labels[q]) for q in run],
        [metrics.ndcg_at_k(run[q], labels[q]) for q in run])
    summary = {"labels": "completed top20 labels", "d47": score(d47), "d50": score(run),
               "ndcg_delta": delta, "ci95": [low, high],
               "caution": "Pilot20 selected the variant; only the remaining80 half is confirmation."}
    freeze(OUT / "dev100-summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--cap-usd", type=float)
    parser.add_argument("--large-daily-guard", type=int)
    parser.add_argument("--authority")
    parser.add_argument("--combine", action="store_true", help="write the free dev100 run")
    args = parser.parse_args(argv)
    if args.combine:
        print(json.dumps(combined_run(), indent=2))
    elif args.run:
        if not (args.cap_usd and args.large_daily_guard and args.authority):
            raise SystemExit("--run needs --cap-usd, --large-daily-guard and --authority")
        report = execute(args.cap_usd, args.large_daily_guard, args.authority)
        print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    else:
        print(json.dumps(prepare()["cost"], indent=2))


if __name__ == "__main__":
    main()
