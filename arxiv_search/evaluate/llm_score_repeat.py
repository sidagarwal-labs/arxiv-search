"""Repeatability check: re-send identical top50 reranker requests and measure drift.

The 20 pilot queries' top50 requests are sent again byte-for-byte (same model
snapshot, prompt, payload and presentation order). Run A is the cached v2
response; run B is the new one. We measure how much the LLM scores, the top50
LLM order, the safeguard order and the metrics move between the two runs.

No judge calls: run-B top10 papers without a grade are counted and bounded
(treated as 0 and as 2), never graded. Preflight by default; --run sends
requests (first query is a smoke gate), stops on any failure, no retries.
"""

from __future__ import annotations

import argparse
import json
import statistics

import tiktoken

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, llm_reranker_pilot as v1
from arxiv_search.evaluate import llm_score_dev100 as dev, llm_score_judge_fill as fill
from arxiv_search.evaluate import llm_score_pilot as score, llm_score_safeguard as guard
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "llm-score-repeat"
RUN = 1
SYSTEMS = (dev.LLM, dev.SAFE)

PLAN = {
    "version": client.REPEAT_VERSION, "model": client.MODEL,
    "question": "How much do identical top50 reranker requests vary between runs?",
    "queries": "The 20 pilot dev queries (5 per segment, pre-defined hash sample).",
    "method": "Byte-identical v2 top50 payloads re-sent once; run A = cached v2 response.",
    "measures": ["exact score agreement and mean absolute score change per paper",
                 "top10 overlap and source rank change for top50 LLM and safeguard",
                 "nDCG@10 / source MRR@10 per run and per-query run-to-run differences"],
    "labels": "Full-dev child labels; no new judging. Unjudged run-B pairs bounded at 0 and 2.",
    "stability_guide": {"safeguard_mean_abs_ndcg_change_max": 0.01,
                        "safeguard_median_top10_overlap_min": 8},
    "budget_usd": client.REPEAT_TASK_CAP / 1e9, "max_requests": client.REPEAT_MAX_REQUESTS,
    "automatic_retries": False, "judge_api_calls": 0, "automatic_promotion": False,
}


def prepare() -> dict:
    state = dev.prepare()
    requests = [r for r in state["requests"] if r["pilot"]]
    if len(requests) != 20:
        raise ValueError("Expected the 20 pilot requests")
    for r in requests:
        r["repeat_key"] = client.repeat_key(r["encoded"], RUN)
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", {**PLAN, "query_ids": [r["query_id"] for r in requests],
                                          "request_keys": [r["request_key"] for r in requests]})
    return {**state, "repeat": requests}


def read_repeat(r: dict) -> dict | None:
    path = OUT / "responses" / f"{r['repeat_key']}.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value["request_key"] != r["request_key"] or value["repeat_key"] != r["repeat_key"]
            or value["presented_ids"] != r["presented_ids"]
            or value["answer_sha256"] != fusion.fingerprint(value["answer"])
            or value["usage"]["status"] != "completed"):
        raise ValueError(f"{r['query_id']}: repeat cache provenance mismatch")
    return client.validate_scores(value["answer"], len(r["presented_ids"]))


def call_repeat(r: dict, ledger: client.PilotLedger) -> dict:
    cached = read_repeat(r)
    if cached is not None:
        return cached
    if ledger.attempted(r["repeat_key"]) is not None:
        raise api.OpenAIError("Repeat already attempted without a valid cache; no retry")
    answer, usage = client.call_once(
        r["encoded"], len(r["presented_ids"]), ledger, attempt_key=r["repeat_key"],
        failure_output_path=OUT / "failures" / f"{r['repeat_key']}.json")
    value = {"request_key": r["request_key"], "repeat_key": r["repeat_key"], "model": client.MODEL,
             "presented_ids": r["presented_ids"], "answer": answer, "usage": usage,
             "answer_sha256": fusion.fingerprint(answer)}
    path = OUT / "responses" / f"{r['repeat_key']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".tmp").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    path.with_suffix(".tmp").replace(path)
    return answer


def preflight(state: dict, ledger: client.PilotLedger) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    todo = [r for r in state["repeat"] if read_repeat(r) is None]
    blocked = [r for r in todo if ledger.attempted(r["repeat_key"])]
    tokens = sum(len(tokenizer.encode(r["encoded"].decode("utf-8"))) for r in todo)
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    summary = ledger.summary()
    return {"new_requests": len(todo), "attempted_uncached_no_retry": len(blocked),
            "serialized_input_token_estimate": tokens,
            "expected_usd": (tokens * 1.1 * client.INPUT_PRICE + len(todo) * 350 * client.OUTPUT_PRICE) / 1e9,
            "worst_case_usd": (tokens * 1.1 * client.INPUT_PRICE
                               + len(todo) * ledger.output_cap * client.OUTPUT_PRICE) / 1e9,
            "repeat_spent_usd": summary["accounted_usd"], "repeat_cap_usd": client.REPEAT_TASK_CAP / 1e9,
            "shared_remaining_tokens_today": limit - summary["shared_accounted_tokens"]}


def score_agreement(a: dict, b: dict) -> dict:
    diffs = [b[k] - a[k] for k in a]
    return {"pairs": len(diffs), "exact": sum(d == 0 for d in diffs),
            "changed_by_1": sum(abs(d) == 1 for d in diffs),
            "changed_by_2plus": sum(abs(d) >= 2 for d in diffs),
            "mean_abs_change": sum(map(abs, diffs)) / len(diffs), "mean_change": sum(diffs) / len(diffs)}


def per_query_metrics(result: dict, name: str) -> dict:
    return {row["query_id"]: row for row in result["systems"][name]["per_query"]}


def analyse(state: dict) -> dict:
    labels = json.loads((dev.OUT / "labels.json").read_text(encoding="utf-8"))
    qids = [r["query_id"] for r in state["repeat"]]
    base = {q: state["base"][q] for q in qids}
    runs = {"A": {}, "B": {}}
    agreement, pair_rows = [], []
    for r in state["repeat"]:
        q = r["query_id"]
        a = dev.cached(r, score.VERSION)[0]
        b = read_repeat(r)
        if b is None:
            raise ValueError(f"{q}: repeat response missing; run --run first")
        stats = score_agreement(a, b)
        agreement.append(stats)
        pair_rows.append({"query_id": q, **stats})
        for tag, answer in (("A", a), ("B", b)):
            llm = score.apply_scores(base[q], r["presented_ids"], answer)
            runs[tag].setdefault(dev.LLM, {})[q] = llm
            runs[tag].setdefault(dev.SAFE, {})[q] = guard.fuse(base[q], llm)
    published = json.loads((dev.OUT / f"{dev.SAFE}.run.json").read_text(encoding="utf-8"))
    if any(runs["A"][dev.SAFE][q] != published[q] for q in qids):
        raise ValueError("Run A does not reproduce the published safeguard ranking")
    totals = {k: sum(x[k] for x in agreement) for k in ("pairs", "exact", "changed_by_1", "changed_by_2plus")}
    totals["mean_abs_change"] = sum(x["mean_abs_change"] * x["pairs"] for x in agreement) / totals["pairs"]
    totals["mean_change"] = sum(x["mean_change"] * x["pairs"] for x in agreement) / totals["pairs"]

    flat = {f"{n}@{tag}": runs[tag][n] for tag in runs for n in SYSTEMS}
    flat[v1.BASELINE] = base
    missing = fill.missing_pairs(flat, labels["labels"], qids)
    bounds = {}
    for assumed in (None, 0, 2):
        graded = labels["labels"] if assumed is None else {
            q: {**labels["labels"][q], **{p: assumed for p in missing[q]}} for q in qids}
        result = score.compare(flat, v1.BASELINE, {**labels, "labels": graded},
                               state["papers"], state["queries"], qids)
        bounds["as_labelled" if assumed is None else f"unjudged={assumed}"] = result
    result = bounds["unjudged=0"]

    systems = {}
    for n in SYSTEMS:
        overlap, source_moves, ndcg_diffs, mrr_diffs = [], [], {}, []
        for q in qids:
            ra, rb = runs["A"][n][q], runs["B"][n][q]
            overlap.append(len(set(ra[:10]) & set(rb[:10])))
            src = state["queries"][q]["source_arxiv_id"]
            pa, pb = (ra.index(src) + 1 if src in ra else 101), (rb.index(src) + 1 if src in rb else 101)
            source_moves.append({"query_id": q, "A": pa, "B": pb})
        for tag, other in (("unjudged=0", 0), ("unjudged=2", 2)):
            pa = per_query_metrics(bounds[tag], f"{n}@A")
            pb = per_query_metrics(bounds[tag], f"{n}@B")
            ndcg_diffs[tag] = {q: pb[q]["ndcg@10"] - pa[q]["ndcg@10"] for q in qids}
        pa = per_query_metrics(result, f"{n}@A")
        pb = per_query_metrics(result, f"{n}@B")
        mrr_diffs = [pb[q]["source_mrr@10"] - pa[q]["source_mrr@10"] for q in qids]
        means = {tag: {run: bounds[tag]["systems"][f"{n}@{run}"]["all"]["ndcg@10"]["mean"]
                       for run in "AB"} for tag in ("unjudged=0", "unjudged=2")}
        d = list(ndcg_diffs["unjudged=0"].values())
        systems[n] = {
            "top10_overlap": {"mean": statistics.mean(overlap), "median": statistics.median(overlap),
                              "min": min(overlap), "identical_top10_queries": sum(o == 10 for o in overlap)},
            "identical_full_order_queries": sum(runs["A"][n][q] == runs["B"][n][q] for q in qids),
            "source_rank_changed": [m for m in source_moves if m["A"] != m["B"]],
            "ndcg@10_means": means,
            "mean_abs_query_ndcg_change": {t: statistics.mean(map(abs, v.values()))
                                           for t, v in ndcg_diffs.items()},
            "sd_query_ndcg_change": statistics.stdev(d),
            # Run-to-run SD of a 100-query mean, assuming per-query differences scale like these 20.
            "est_sd_of_100q_mean": statistics.stdev(d) / (2 * 100) ** 0.5,
            "source_mrr@10": {run: result["systems"][f"{n}@{run}"]["all"]["source_mrr@10"]["mean"]
                              for run in "AB"},
            "mean_abs_query_source_mrr_change": statistics.mean(map(abs, mrr_diffs)),
            "per_query_ndcg_change": ndcg_diffs,
        }
    guide = PLAN["stability_guide"]
    safe = systems[dev.SAFE]
    worst = max(abs(safe["ndcg@10_means"][t]["B"] - safe["ndcg@10_means"][t]["A"])
                for t in ("unjudged=0", "unjudged=2"))
    verdict = {"safeguard_mean_ndcg_change_worst_bound": worst,
               "passes_ndcg_guide": worst <= guide["safeguard_mean_abs_ndcg_change_max"],
               "passes_overlap_guide": safe["top10_overlap"]["median"] >= guide["safeguard_median_top10_overlap_min"]}
    return {"query_ids": qids, "score_agreement": totals, "per_query_agreement": pair_rows,
            "unjudged_run_pairs": sum(map(len, missing.values())), "missing": missing,
            "systems": systems, "verdict": verdict}


def write_markdown(report: dict) -> None:
    s, sa = report["score_agreement"], report["accounting"]
    lines = ["# Repeatability: identical top50 reranker requests sent twice", "",
             "The 20 pilot queries' v2 top50 payloads were re-sent byte-for-byte. Run A is the "
             "cached v2 response, run B the repeat. No judge calls; run-B top10 papers without "
             f"a grade (**{report['unjudged_run_pairs']}**) are bounded as grade 0 and grade 2.", "",
             "## LLM score agreement (20 queries x 50 papers)", "",
             f"- Identical score: **{s['exact']}/{s['pairs']}** ({s['exact'] / s['pairs']:.1%}); "
             f"changed by 1: {s['changed_by_1']}; by 2+: {s['changed_by_2plus']}.",
             f"- Mean absolute change {s['mean_abs_change']:.3f} points (0-4 scale); "
             f"mean signed change {s['mean_change']:+.3f}.", "",
             "## Ranking and metric stability", "",
             "| System | Median top10 overlap | Min | Identical top10 | Identical order | "
             "nDCG10 A -> B (unjudged=0) | (unjudged=2) | Mean abs query nDCG change | "
             "Source MRR A -> B | Source ranks changed |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for n, x in report["systems"].items():
        m = x["ndcg@10_means"]
        lines.append(
            f"| `{n}` | {x['top10_overlap']['median']:.0f}/10 | {x['top10_overlap']['min']} | "
            f"{x['top10_overlap']['identical_top10_queries']}/20 | {x['identical_full_order_queries']}/20 | "
            f"{m['unjudged=0']['A']:.4f} -> {m['unjudged=0']['B']:.4f} | "
            f"{m['unjudged=2']['A']:.4f} -> {m['unjudged=2']['B']:.4f} | "
            f"{x['mean_abs_query_ndcg_change']['unjudged=0']:.4f} | "
            f"{x['source_mrr@10']['A']:.4f} -> {x['source_mrr@10']['B']:.4f} | "
            f"{len(x['source_rank_changed'])} |")
    lines += ["", "| System | SD of per-query nDCG change | Estimated run-to-run SD of a 100-query mean |",
              "|---|---|---|"]
    for n, x in report["systems"].items():
        lines.append(f"| `{n}` | {x['sd_query_ndcg_change']:.4f} | {x['est_sd_of_100q_mean']:.4f} |")
    lines += ["", "## Source rank changes", "", "| System | Query | Run A | Run B |", "|---|---|---|---|"]
    for n, x in report["systems"].items():
        for m in x["source_rank_changed"]:
            lines.append(f"| `{n}` | {m['query_id']} | {m['A']} | {m['B']} |")
    v = report["verdict"]
    lines += ["", "## Pre-registered stability guide", "",
              f"- Safeguard mean nDCG@10 change (worst bound) {v['safeguard_mean_ndcg_change_worst_bound']:.4f} "
              f"vs <= 0.01: **{'pass' if v['passes_ndcg_guide'] else 'fail'}**.",
              f"- Safeguard median top10 overlap >= 8/10: **{'pass' if v['passes_overlap_guide'] else 'fail'}**.",
              "", "## Accounting", "",
              f"- {sa['requests']} requests; input/output tokens {sa['input_tokens']:,}/{sa['output_tokens']:,}; "
              f"${sa['accounted_usd']:.4f}.", "",
              "## Cautions", "",
              "- One repeat of 20 queries; the 100-query noise estimate is an extrapolation.",
              "- Run A was sent on an earlier day; provider-side changes cannot be ruled out.",
              "- Same-family judge caveat unchanged; no promotion."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="send the repeat requests")
    args = parser.parse_args(argv)
    state = prepare()
    ledger = client.PilotLedger(version=client.REPEAT_VERSION)
    pre = preflight(state, ledger)
    print(json.dumps(pre, indent=2), flush=True)
    if pre["attempted_uncached_no_retry"]:
        raise api.OpenAIError("A prior repeat has no valid cache; investigate before continuing")
    if pre["new_requests"]:
        fusion._write_json(OUT / "preflight.json", pre)
        if not args.run:
            return
        if pre["expected_usd"] > pre["repeat_cap_usd"] - pre["repeat_spent_usd"]:
            raise api.BudgetExceeded("Expected cost exceeds the approved repeat ceiling; no request sent")
        for i, r in enumerate(state["repeat"]):
            try:
                call_repeat(r, ledger)
            except api.OpenAIError:
                print(f"STOPPED at {r['query_id']}; investigate before any further requests.", flush=True)
                raise
            if i == 0:
                print(f"Smoke request {r['query_id']} passed.", flush=True)
    report = {**analyse(state), "accounting": ledger.summary(), "promoted": False}
    fusion._write_json(OUT / "report.json", report)
    write_markdown(report)
    print(json.dumps(report["verdict"], indent=2))


if __name__ == "__main__":
    main()
