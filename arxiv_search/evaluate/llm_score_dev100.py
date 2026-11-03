"""Full-dev evaluation of the top50 fixed-key LLM reranker and its baseline safeguard.

Extends the v2 pilot's exact top50 method (same model, prompt, payload encoding and
presentation order) from its 20 pilot queries to all 100 dev queries, then applies
the Decision42 safeguard rule unchanged. The 20 pilot responses are reused from the
v2 cache; only the other 80 queries are new requests.

Steps (preflight by default):
    --run      send the 80 reranker requests (first query is a one-request smoke gate)
    --judge    grade the new top10 pairs with the frozen judge, then publish
Both stop on the first failure; no retries. Held-out queries are never touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json

import tiktoken

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, judge
from arxiv_search.evaluate import llm_reranker_pilot as v1, llm_score_judge_fill as fill
from arxiv_search.evaluate import llm_score_pilot as score, llm_score_safeguard as guard
from arxiv_search.evaluate import results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.judge_pilot import SHEET_PATH, read_human_grades

OUT = config.RESULTS_DIR / "llm-score-dev100"
DEPTH = 50
LLM = score.system_name(DEPTH)
SAFE = guard.NAME
JUDGE_TASK_CAP_USD = 0.25


def plan(qids: list[str], pilot: list[str]) -> dict:
    return {
        "version": client.DEV100_VERSION, "model": client.MODEL, "baseline": v1.BASELINE,
        "systems": [LLM, SAFE], "query_ids": qids, "pilot_query_ids": pilot,
        "hypothesis": "The Decision42 safeguard keeps a meaningful nDCG gain over the baseline "
                      "on all 100 dev queries without losing source MRR.",
        "method": "Identical to the v2 top50 arm: same prompt, payload encoding, presentation "
                  "order, reasoning none and tie rule. Safeguard rule unchanged from Decision42.",
        "reuse": "The 20 pilot queries reuse cached v2 responses; 80 new requests at most.",
        "success_criteria": guard.PLAN["success_criteria"],
        "primary_scope": "All 100 dev queries; the 80 non-pilot queries are reported separately "
                         "as the out-of-sample check because the rule was designed on the 20.",
        "execution": "Stop on the first failure, no retries; smoke gate on the first new query.",
        "judging": "Frozen openai-mini judge for new top10 pairs, one attempt per call, no "
                   "retries; human labels take priority and are never sent to the judge.",
        "automatic_promotion": False, "held_out_queries_used": False,
    }


def prepare() -> dict:
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    if len(qids) != 100 or set(qids) & set(split["test"]):
        raise ValueError("Expected 100 dev queries disjoint from held-out")
    base_path = config.RESULTS_DIR / "shortlist-score-dev" / f"{v1.BASELINE}.run.json"
    base_bytes = base_path.read_bytes()
    base = json.loads(base_bytes)
    fusion.validate_run(v1.BASELINE, base, qids, papers, exact_depth=100)
    if config.WORKING_BASELINE_SYSTEM != v1.BASELINE:
        raise ValueError("Approved baseline changed; create a new identity")
    pilot = json.loads((score.OUT / "report.json").read_text(encoding="utf-8"))["query_ids"]
    pilot_keys = {(r["query_id"], r["depth"]): r["request_key"] for r in json.loads(
        (score.OUT / "input-provenance.json").read_text(encoding="utf-8"))["requests"]}
    requests = []
    for q in qids:
        presented = v1.presentation(q, base[q][:DEPTH])
        encoded = client.encode_score_payload(queries[q]["query"], presented, papers)
        key = client.request_key(encoded)
        is_pilot = q in pilot
        if is_pilot and pilot_keys[(q, DEPTH)] != key:
            raise ValueError(f"{q}: request differs from the v2 pilot; method changed")
        requests.append({"query_id": q, "presented_ids": presented, "encoded": encoded,
                         "request_key": key, "pilot": is_pilot})
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", plan(qids, pilot))
    freeze(OUT / "input-provenance.json", {
        "baseline_bytes_sha256": hashlib.sha256(base_bytes).hexdigest(),
        "requests": [{k: v for k, v in r.items() if k != "encoded"} for r in requests]})
    return {"papers": papers, "queries": queries, "qids": qids, "base": base,
            "pilot": pilot, "requests": requests}


def cache_path(r: dict):
    folder = score.OUT if r["pilot"] else OUT
    return folder / "responses" / f"{r['request_key']}.json"


def cached(r: dict, version: str):
    return v1.read_cached(cache_path(r), r["encoded"], r["presented_ids"], version=version)


def preflight(state: dict, ledger: client.PilotLedger) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    todo, blocked = [], []
    for r in state["requests"]:
        if cached(r, score.VERSION if r["pilot"] else client.DEV100_VERSION) is not None:
            continue
        if r["pilot"]:
            raise ValueError(f"{r['query_id']}: pilot response missing from the v2 cache")
        (blocked if ledger.attempted(r["request_key"]) else todo).append(r)
    tokens = [len(tokenizer.encode(r["encoded"].decode("utf-8"))) for r in todo]
    out_cap = ledger.output_cap
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    shared = ledger.summary()["shared_accounted_tokens"]
    expected_out = 350  # observed v2 top50 output was 318 tokens per request on average
    return {
        "new_requests": len(todo), "attempted_uncached_no_retry": len(blocked),
        "serialized_input_token_estimate": sum(tokens),
        "expected_tokens": round(sum(tokens) * 1.1) + len(todo) * expected_out,
        "expected_usd": (sum(tokens) * 1.1 * client.INPUT_PRICE
                         + len(todo) * expected_out * client.OUTPUT_PRICE) / 1e9,
        "worst_case_usd": (sum(tokens) * 1.1 * client.INPUT_PRICE
                           + len(todo) * out_cap * client.OUTPUT_PRICE) / 1e9,
        "max_single_reservation_tokens": max(
            (client.reserved_input(r["encoded"]) + out_cap for r in todo), default=0),
        "dev100_spent_usd": ledger.summary()["accounted_usd"],
        "dev100_cap_usd": client.DEV100_TASK_CAP / 1e9,
        "shared_token_limit": limit, "shared_accounted_tokens": shared,
        "shared_remaining_tokens": limit - shared,
    }


def run_reranker(state: dict, ledger: client.PilotLedger) -> None:
    new = [r for r in state["requests"] if not r["pilot"]]
    for i, r in enumerate(new):
        try:
            v1.cached_call(cache_path(r), r["encoded"], r["presented_ids"], ledger, run=True,
                           failure_output_path=OUT / "failures" / f"{r['request_key']}.json")
        except api.OpenAIError:
            print(f"STOPPED at {r['query_id']}; investigate before any further requests.", flush=True)
            raise
        if i == 0:
            print(f"Smoke request {r['query_id']} passed.", flush=True)
    print(f"Reranker complete; dev100 cost ${ledger.summary()['accounted_usd']:.4f}", flush=True)


def build_runs(state: dict) -> dict:
    runs = {v1.BASELINE: {q: state["base"][q] for q in state["qids"]}, LLM: {}, SAFE: {}}
    for r in state["requests"]:
        answer = cached(r, score.VERSION if r["pilot"] else client.DEV100_VERSION)
        if answer is None:
            raise ValueError(f"{r['query_id']}: reranker response missing; run --run first")
        q = r["query_id"]
        runs[LLM][q] = score.apply_scores(state["base"][q], r["presented_ids"], answer[0])
        runs[SAFE][q] = guard.fuse(state["base"][q], runs[LLM][q])
    for n, run in runs.items():
        fusion.validate_run(n, run, state["qids"], state["papers"], exact_depth=100)
    pilot_runs = {n: json.loads((score.OUT / f"{n}.run.json").read_text(encoding="utf-8"))
                  for n in (LLM,)}
    pilot_runs[SAFE] = json.loads((guard.OUT / f"{SAFE}.run.json").read_text(encoding="utf-8"))
    for n, run in pilot_runs.items():
        if any(runs[n][q] != run[q] for q in state["pilot"]):
            raise ValueError(f"{n}: rebuilt pilot rankings differ from published pilot")
    return runs


def parent_labels(state: dict) -> tuple[dict, dict]:
    _, label_bytes, full, _ = catalog.load_snapshot(config.RESULTS_DIR)
    if full["rubric_version"] != judge.RUBRIC_VERSION:
        raise ValueError("Judge rubric changed since the frozen snapshot")
    if full["human_workbook_sha256"] != hashlib.sha256(SHEET_PATH.read_bytes()).hexdigest():
        raise ValueError("Human workbook changed since the frozen snapshot")
    pilot = json.loads((fill.OUT / "labels.json").read_text(encoding="utf-8"))
    labels = fill.child_labels({q: full["labels"][q] for q in state["qids"]}, pilot["labels"])
    meta = {"judge": full["judge"], "parent_labels_bytes_sha256": hashlib.sha256(label_bytes).hexdigest(),
            "pilot_child_labels_sha256": fusion.fingerprint(pilot)}
    return labels, meta


def judge_plan(state: dict, runs: dict, labels: dict, judge_key: str) -> tuple[dict, list, dict]:
    missing = fill.missing_pairs(runs, labels, state["qids"])
    human = read_human_grades()
    to_judge = {q: [p for p in ps if (q, p) not in human] for q, ps in missing.items() if ps}
    calls = judge.batches(judge_key, to_judge, state["queries"], state["papers"],
                          judge.load_judgments(judge_key))
    return missing, calls, human


def publish(state: dict, runs: dict, labels: dict, meta: dict, missing: dict, human: dict,
            judge_usage: dict) -> dict:
    qids, queries, papers = state["qids"], state["queries"], state["papers"]
    pairs = {q: ps for q, ps in missing.items() if ps}
    new = judge.grades_for(meta["judge"], pairs, queries, papers)
    for (q, p), grade in human.items():
        if p in pairs.get(q, []):
            new.setdefault(q, {})[p] = grade
    labels = fill.child_labels(labels, new)
    still = fill.missing_pairs(runs, labels, qids)
    snapshot = {**meta, "rubric_version": judge.RUBRIC_VERSION, "query_ids": qids,
                "labels": labels, "added_pairs": sum(map(len, new.values())),
                "complete_for_top10": not any(still.values())}
    fusion._write_json(OUT / "labels.json", snapshot)
    for n, run in runs.items():
        fusion._write_json(OUT / f"{n}.run.json", run)
    scopes = {"all100": qids, "new80": [q for q in qids if q not in state["pilot"]],
              "pilot20": state["pilot"]}
    results = {s: score.compare(runs, v1.BASELINE, {**snapshot, "labels": {q: labels[q] for q in ids}},
                                papers, queries, ids) for s, ids in scopes.items()}
    verdicts = {}
    for s, result in results.items():
        systems = result["systems"]
        b, t = systems[v1.BASELINE]["all"], systems[LLM]["all"]
        mine = systems[SAFE]
        ok = mine["top10_fully_judged"] and t and systems[LLM]["top10_fully_judged"]
        thresholds = {
            "source_mrr@10": b["source_mrr@10"]["mean"] - 0.02,
            "ndcg@10": b["ndcg@10"]["mean"] + (t["ndcg@10"]["mean"] - b["ndcg@10"]["mean"]) / 2,
        }
        verdicts[s] = {k: {"threshold": v, "value": mine["all"][k]["mean"],
                           "passes": (mine["all"][k]["mean"] >= v) if (ok or k == "source_mrr@10") else None}
                       for k, v in thresholds.items()}
    source = {q: {n: (r[q].index(queries[q]["source_arxiv_id"]) + 1
                      if queries[q]["source_arxiv_id"] in r[q] else None) for n, r in runs.items()}
              for q in qids}
    report = {"plan": json.loads((OUT / "preregistration.json").read_text(encoding="utf-8")),
              "missing_before_judging": sum(map(len, missing.values())),
              "added_pairs": snapshot["added_pairs"], "still_missing": still,
              "results": results, "verdicts": verdicts, "source_ranks": source,
              "reranker_accounting": client.PilotLedger(version=client.DEV100_VERSION).summary(),
              "judge_accounting": judge_usage, "promoted": False}
    fusion._write_json(OUT / "report.json", report)
    write_markdown(report, queries)
    return report


def write_markdown(report: dict, queries: dict) -> None:
    fields = ("ndcg@10", "precision@10", "judged@10", "source_mrr@10", "source_recall@10",
              "source_recall@20")
    lines = ["# Full-dev evaluation: top50 LLM reranker and baseline safeguard", "",
             "Same method as the v2 top50 pilot arm and the Decision42 safeguard rule, on all 100 "
             "dev queries. The 20 pilot queries reuse cached responses; `new80` is the out-of-sample "
             "check because the safeguard was designed on the 20. Held-out queries untouched.", "",
             f"New top10 pairs graded: **{report['added_pairs']}** of "
             f"{report['missing_before_judging']}; still missing: "
             f"**{sum(map(len, report['still_missing'].values()))}**."]
    for scope, result in report["results"].items():
        lines += ["", f"## {scope} ({result['matched_queries']} queries)", "",
                  "| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |",
                  "|---|---|---|---|---|---|---|"]
        for n, r in result["systems"].items():
            vals = [("withheld" if f in ("ndcg@10", "precision@10") and not r["top10_fully_judged"]
                     else f"{r['all'][f]['mean']:.4f}") for f in fields]
            lines.append(f"| `{n}` | " + " | ".join(vals) + " |")
        lines += ["", "| Arm vs baseline | nDCG10 delta [95% CI] | P10 delta [95% CI] | "
                  "Source MRR10 delta [95% CI] | nDCG W/L/T |", "|---|---|---|---|---|"]
        for n in (LLM, SAFE):
            cells = []
            for f in ("ndcg@10", "precision@10", "source_mrr@10"):
                p = result["summary"].get(n, {}).get("all", {}).get(f, {}).get("paired_vs_working")
                cells.append("withheld" if p is None else
                             f"{p['difference']:+.4f} [{p['ci95'][0]:+.4f},{p['ci95'][1]:+.4f}]")
            p = result["summary"].get(n, {}).get("all", {}).get("ndcg@10", {}).get("paired_vs_working")
            if p is None:
                cells.append("withheld")
            else:
                d = p["per_query_difference"].values()
                cells.append(f"{sum(x > 1e-12 for x in d)}/{sum(x < -1e-12 for x in d)}/"
                             f"{sum(abs(x) <= 1e-12 for x in d)}")
            lines.append(f"| `{n}` | " + " | ".join(cells) + " |")
        v = report["verdicts"][scope]
        lines += ["", "Pre-registered safeguard criteria: " + "; ".join(
            f"{k} {x['value']:.4f} vs >= {x['threshold']:.4f} "
            f"({ {True: 'pass', False: 'fail', None: 'withheld'}[x['passes']] })" for k, x in v.items())]
        lines += ["", "| Segment | " + " | ".join(f"`{n}`" for n in result["systems"]) + " |",
                  "|---|" + "---|" * len(result["systems"])]
        for kind in catalog.QUERY_TYPES:
            cells = []
            for n, r in result["systems"].items():
                rows = [x for x in r["per_query"] if x["query_type"] == kind]
                ok = rows and all(x["judged@10"] == 1 for x in rows)
                cells.append(f"{r['by_query_type'][kind]['ndcg@10']['mean']:.4f} / "
                             f"{r['by_query_type'][kind]['source_mrr@10']['mean']:.3f}"
                             if ok else "withheld")
            lines.append(f"| {kind} (nDCG / MRR) | " + " | ".join(cells) + " |")
    lines += ["", "## Largest source-rank drops (safeguard vs baseline)", "",
              "| Query | Type | Baseline | Top50 LLM | Safeguard |", "|---|---|---|---|---|"]
    def drop(s):
        b, g = s[v1.BASELINE] or 101, s[SAFE] or 101
        return g - b
    worst = sorted(((q, s) for q, s in report["source_ranks"].items() if drop(s) > 0),
                   key=lambda x: -drop(x[1]))[:12]
    for q, s in worst:
        lines.append(f"| {q} | {queries[q]['query_type']} | {s[v1.BASELINE]} | {s[LLM]} | {s[SAFE]} |")
    ra, ja = report["reranker_accounting"], report["judge_accounting"]
    lines += ["", "## Accounting", "",
              f"- Reranker (new80): {ra['requests']} requests, input/output/reasoning "
              f"{ra['input_tokens']:,}/{ra['output_tokens']:,}/{ra['reasoning_tokens']:,}, "
              f"${ra['accounted_usd']:.4f}.",
              f"- Judge: {ja.get('calls', 0)} calls, {ja.get('accounted_tokens', 0):,} tokens, "
              f"${ja.get('usd', 0):.4f}.", "",
              "## Cautions", "",
              "- Dev queries only; settings were developed on dev, so scores are optimistic.",
              "- Judge and reranker share a model family; possible same-family preference.",
              "- No promotion without explicit approval."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def judge_accounting(rows: list[dict]) -> dict:
    usage = {r["usage"]["request_id"]: r["usage"] for r in rows}
    out = {"calls": len(usage), **{k: sum(u[k] for u in usage.values())
                                   for k in ("input_tokens", "output_tokens", "reasoning_tokens",
                                             "accounted_tokens")}}
    out["usd"] = (out["input_tokens"] * client.INPUT_PRICE + out["output_tokens"] * client.OUTPUT_PRICE) / 1e9
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="send the new reranker requests")
    parser.add_argument("--judge", action="store_true", help="grade new top10 pairs and publish")
    args = parser.parse_args(argv)
    state = prepare()
    ledger = client.PilotLedger(version=client.DEV100_VERSION)
    pre = preflight(state, ledger)
    print(json.dumps(pre, indent=2), flush=True)
    if pre["attempted_uncached_no_retry"]:
        raise api.OpenAIError("A prior request has no valid cache; investigate before continuing")
    if pre["new_requests"]:
        fusion._write_json(OUT / "preflight.json", pre)
        if not args.run:
            return
        if pre["expected_usd"] > pre["dev100_cap_usd"] - pre["dev100_spent_usd"]:
            raise api.BudgetExceeded("Expected cost exceeds the approved dev100 ceiling; no request sent")
        if pre["expected_tokens"] + pre["max_single_reservation_tokens"] > pre["shared_remaining_tokens"]:
            raise api.BudgetExceeded("Expected usage exceeds the shared token allowance; no request sent")
        run_reranker(state, ledger)
    runs = build_runs(state)
    labels, meta = parent_labels(state)
    missing, calls, human = judge_plan(state, runs, labels, meta["judge"])
    estimate = fill.estimate(calls, state["queries"])
    print(json.dumps({k: v for k, v in estimate.items() if k != "requests"}, indent=2), flush=True)
    usage_path = OUT / "judge-accounting.json"
    rows = json.loads(usage_path.read_text(encoding="utf-8"))["rows"] if usage_path.exists() else []
    if calls:
        fusion._write_json(OUT / "judge-preflight.json", estimate)
        if not args.judge:
            return
        if estimate["expected_usd"] > JUDGE_TASK_CAP_USD:
            raise api.BudgetExceeded("Judge estimate exceeds its ceiling; no request sent")
        remaining = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION) \
            - ledger.summary()["shared_accounted_tokens"]
        if estimate["expected_tokens"] + estimate["max_single_reservation_tokens"] > remaining:
            raise api.BudgetExceeded("Judge estimate exceeds the shared token allowance")
        sent = fill.run_calls({"judge_key": meta["judge"], "queries": state["queries"], "calls": calls},
                              planned=estimate["requests"], cap_usd=JUDGE_TASK_CAP_USD)
        rows += [{k: r[k] for k in ("query_id", "arxiv_id", "usage")} for r in sent["rows"]]
        fusion._write_json(usage_path, {"rows": rows})
    report = publish(state, runs, labels, meta, missing, human, judge_accounting(rows))
    print(json.dumps({s: {k: x["passes"] for k, x in v.items()} for s, v in report["verdicts"].items()}))


if __name__ == "__main__":
    main()
