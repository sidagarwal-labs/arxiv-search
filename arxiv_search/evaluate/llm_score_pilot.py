"""Fixed-key mini reranker v2. Preflight by default; --run --smoke before --run."""

from __future__ import annotations

import argparse
import hashlib
import json

import tiktoken

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, llm_reranker_pilot as v1
from arxiv_search.evaluate import results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.score_candidate_review import query_changes
from arxiv_search.evaluate.score_fusion_experiment import summarize
from arxiv_search.search.rerank import rerank_prefix

OUT = config.RESULTS_DIR / "llm-score-pilot"
VERSION = "scores-v2"


def system_name(depth: int) -> str:
    if depth not in v1.DEPTHS:
        raise ValueError("Unexpected fixed-key pilot depth")
    return f"llm-mini-score-pilot+d={depth}"


def plan(qids: list[str]) -> dict:
    return {
        "version": VERSION, "model": client.MODEL, "baseline": v1.BASELINE,
        "query_ids": qids, "depths": list(v1.DEPTHS),
        "hypothesis": "Required fixed paper keys eliminate generated-permutation and note-ID "
                      "errors; bounded usefulness scores enable deterministic client sorting.",
        "scope": "Exactly v1's20 queries, same baseline candidate10/50 and presentation order; "
                 "full public title/authors/abstract. No extra queries, labels or held-out test.",
        "prompt_sha256": hashlib.sha256(client.SCORE_SYSTEM.encode()).hexdigest(),
        "contract": "Flat JSON with every supplied P-label required exactly once, integer0-4, "
                    "no additional keys. Reject duplicate raw JSON keys. No explanations.",
        "ranking": "Descending model score; equal scores retain approved baseline order. "
                   "Rerank only the supplied prefix and preserve the rest of the100 results.",
        "interpretation": "New scoring/tie contract, not an isolated output-format-only ablation. "
                          "Scores are ranking signals, never evaluation grades or probabilities.",
        "budget": {"maximum_combined_v1_v2_usd": client.TASK_CAP / 1e9,
                   "new_requests_maximum": client.MAX_REQUESTS,
                   "max_output_tokens": client.SCORE_MAX_OUTPUT, "reasoning_effort": "none",
                   "input_usd_per_million": client.INPUT_PRICE / 1000,
                   "output_usd_per_million": client.OUTPUT_PRICE / 1000,
                   "ledger": "data/openai/usage.sqlite3", "no_reset": True},
        "execution": "First sorted sample query at each depth is a two-request smoke gate. "
                     "Stop on any invalid smoke response. No retries; cached valid results "
                     "are reused. Subsequent invalid answers are explicit, not fallback ranks.",
        "evaluation": "Paired same20-query baseline comparison when complete; otherwise explicit "
                      "matched-success scope. Withhold incomplete graded comparisons. "
                      "Compare v1 only on identical successfully ranked queries.",
        "automatic_promotion": False, "judge_api_calls": 0, "automatic_retries": False,
    }


def prepare() -> tuple:
    papers, queries, qids, base, snapshot, old_requests, old_provenance = v1.prepare()
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", plan(qids))
    requests = []
    for r in old_requests:
        encoded = client.encode_score_payload(queries[r["query_id"]]["query"], r["presented_ids"], papers)
        requests.append({**r, "encoded": encoded, "request_key": client.request_key(encoded)})
    provenance = {
        "parent_input_provenance_sha256": fusion.fingerprint(old_provenance),
        "full_labels_bytes_sha256": old_provenance["full_labels_bytes_sha256"],
        "subset_labels_sha256": old_provenance["subset_labels_sha256"],
        "baseline_bytes_sha256": old_provenance["baseline_bytes_sha256"],
        "requests": [{k: val for k, val in r.items() if k != "encoded"} for r in requests],
    }
    freeze(OUT / "input-provenance.json", provenance)
    return papers, queries, qids, base, snapshot, requests, provenance


def preflight(requests: list[dict], ledger: client.PilotLedger) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    missing, tasks = [], []
    blocked = 0
    for r in requests:
        cached = v1.read_cached(OUT / "responses" / f"{r['request_key']}.json",
                                r["encoded"], r["presented_ids"], version=VERSION)
        previous = ledger.attempted(r["request_key"]) if cached is None else None
        row = {
            "query_id": r["query_id"], "depth": r["depth"], "request_key": r["request_key"],
            "serialized_token_estimate": len(tokenizer.encode(r["encoded"].decode("utf-8"))),
            "reserved_input_tokens": client.reserved_input(r["encoded"]), "cached": cached is not None,
            "attempt_status": previous["status"] if previous is not None else None,
        }
        tasks.append(row)
        if previous is not None:
            blocked += 1
        elif cached is None:
            missing.append(row)
    accounting = ledger.summary()
    estimate = sum(r["serialized_token_estimate"] for r in missing)
    combined = ledger.combined_cost_nanodollars() / 1e9
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    return {
        "unattempted_requests": len(missing), "cached_requests": len(requests) - len(missing) - blocked,
        "attempted_uncached_no_retry": blocked, "request_preflight": tasks,
        "serialized_input_token_estimate": estimate,
        "expected_tokens_with_10pct_input_headroom_and_max_output": estimate * 1.1 + len(missing) * ledger.output_cap,
        "expected_incremental_usd_with_10pct_input_headroom_and_max_output": (
            estimate * 1.1 * client.INPUT_PRICE + len(missing) * ledger.output_cap * client.OUTPUT_PRICE) / 1e9,
        "max_single_request_reservation": max(
            (r["reserved_input_tokens"] + ledger.output_cap for r in missing), default=0),
        "shared_token_limit": limit, "shared_remaining_tokens": limit - accounting["shared_accounted_tokens"],
        "combined_v1_v2_accounted_usd": combined, "combined_v1_v2_ceiling_usd": client.TASK_CAP / 1e9,
        "accounting": accounting,
        "caution": "Estimates exclude provider tokenization differences; actual per-call reservations "
                   "use UTF8 payload bytes+4096+full output cap and settle usage. No resets or retries.",
    }


def apply_scores(base: list[str], presented: list[str], scores: dict) -> list[str]:
    scores = client.validate_scores(scores, len(presented))
    if set(presented) != set(base[:len(presented)]):
        raise ValueError("Candidate prefix changed")
    values = {pid: float(scores[f"P{i}"]) for i, pid in enumerate(presented, 1)}
    return rerank_prefix(base, values, len(presented))


def compare(runs: dict, reference: str, snapshot: dict, papers: dict, queries: dict,
            qids: list[str]) -> dict:
    matched = sorted(set(qids).intersection(*(set(r) for r in runs.values())))
    subset = {"query_ids": matched, "labels": {q: snapshot["labels"][q] for q in matched}}
    reduced = {n: {q: run[q] for q in matched} for n, run in runs.items()}
    systems = catalog.score_catalog(
        {n: {"run": r, "paths": [], "metadata": {"scope": "fixed-key20-query pilot"}}
         for n, r in reduced.items()}, subset, papers, queries, matched, reference) if matched else {}
    rows = {n: r["per_query"] for n, r in systems.items()}
    return {
        "reference": reference, "matched_query_ids": matched, "matched_queries": len(matched),
        "systems": systems, "summary": summarize(rows, reference) if matched else {},
        "changes": {n: query_changes(reduced, rows, queries, reference, n)
                    for n in runs if n != reference} if matched else {},
    }


def publish(papers: dict, queries: dict, qids: list[str], base: dict, snapshot: dict,
            runs: dict, failures: dict, provenance: dict, accounting: dict,
            combined_cost: float, ties: dict) -> dict:
    primary = compare(runs, v1.BASELINE, snapshot, papers, queries, qids)
    previous = {}
    for depth in v1.DEPTHS:
        path = v1.OUT / f"{v1.system_name(depth)}.run.json"
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            previous[str(depth)] = compare(
                {v1.system_name(depth): old, system_name(depth): runs[system_name(depth)]},
                v1.system_name(depth), snapshot, papers, queries, qids)
    missing = {q: sorted({p for run in runs.values() for p in run.get(q, [])[:10]}
                          - set(snapshot["labels"][q])) for q in qids}
    known_changes = {n: [v for v in rows if v["query_type"] == "known_item"
                         and v["baseline_source_rank"] != v["candidate_source_rank"]]
                     for n, rows in primary["changes"].items()}
    report = {
        "model": client.MODEL, "version": VERSION, "query_ids": qids,
        "completed_queries": {n: len(r) for n, r in runs.items()}, "failures": failures,
        "primary": primary, "same_query_comparisons_vs_v1": previous,
        "missing": missing, "missing_pairs": sum(map(len, missing.values())),
        "known_item_source_changes": known_changes, "score_ties": ties,
        "accounting": accounting, "combined_v1_v2_accounted_usd": combined_cost,
        "provenance": provenance, "judge_api_calls": 0, "promoted": False,
        "cautions": [
            "20 previously examined dev queries; five per segment; exploratory only.",
            "Evaluation judge and reranker share a model family; no independent validation.",
            "Missing selected-result grades withhold comparable nDCG/P10; scores are not grades.",
            "Fixed0-4 usefulness scores and baseline tie-breaking change scoring as well as output format.",
            "v1 comparisons use only its successful queries; this is a selected subset, not a fresh test.",
        ],
    }
    cases = {}
    for q in qids:
        ids = list(dict.fromkeys([p for run in runs.values() for p in run.get(q, [])[:10]]
                                + [queries[q]["source_arxiv_id"]]))
        cases[q] = {"query": queries[q], "papers": [
            {"arxiv_id": pid, "title": papers[pid]["title"], "authors": papers[pid]["authors"],
             "abstract": papers[pid]["abstract"], "grade": snapshot["labels"][q].get(pid),
             "ranks": {n: r[q].index(pid) + 1 if pid in r.get(q, []) else None for n, r in runs.items()}}
            for pid in ids]}
    fusion._write_json(OUT / "report.json", report)
    fusion._write_json(OUT / "cases.json", cases)
    lines = [
        "# Fixed-key mini reranker v2: same20-query pilot", "",
        f"Model `{client.MODEL}`; reasoning disabled; all title/authors/abstract text preserved. "
        "One required integer0-4 per candidate ID, no generated permutations or explanations. "
        "Descending score with approved-baseline order for ties. No retries, new labels or promotion.",
        f"Matched queries: **{primary['matched_queries']}/{len(qids)}**. "
        "Failures, if any, are excluded identically from both arms and baseline, never replaced "
        "with fallback rankings. This is separate from the100-query leaderboard.", "",
        "| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |",
        "|---|---|---|---|---|---|---|"]
    for n, result in primary["systems"].items():
        vals = [("withheld" if field in ("ndcg@10", "precision@10") and not result["top10_fully_judged"]
                 else f"{result['all'][field]['mean']:.4f}")
                for field in ("ndcg@10", "precision@10", "judged@10", "source_mrr@10",
                              "source_recall@10", "source_recall@20")]
        lines.append(f"| `{n}` | " + " | ".join(vals) + " |")
    lines += ["", f"Missing new top10 judgments: **{report['missing_pairs']}**. "
              "Incomplete JSON scores are diagnostic only, not bounds on future nDCG; paired "
              "graded comparisons are withheld. Rejudging can change IDCG.", "",
              "## Paired versus baseline", "",
              "| Arm | nDCG delta [95% CI] | Source MRR delta [95% CI] |", "|---|---|---|"]
    for depth in v1.DEPTHS:
        vals = []
        for field in ("ndcg@10", "source_mrr@10"):
            paired = primary["summary"].get(system_name(depth), {}).get("all", {}).get(field, {}).get("paired_vs_working")
            vals.append("withheld" if paired is None else
                        f"{paired['difference']:+.4f} [{paired['ci95'][0]:+.4f},{paired['ci95'][1]:+.4f}]")
        lines.append(f"| top{depth} | " + " | ".join(vals) + " |")
    lines += ["", "## Segment results", "",
              "| System | Segment | Queries | nDCG10 | Source MRR10 | R10 | R20 |",
              "|---|---|---|---|---|---|---|"]
    for n, result in primary["systems"].items():
        for kind in catalog.QUERY_TYPES:
            rows = [r for r in result["per_query"] if r["query_type"] == kind]
            if not rows:
                continue
            group = result["by_query_type"][kind]
            complete = all(r["judged@10"] == 1 for r in rows)
            vals = [("withheld" if field == "ndcg@10" and not complete else f"{group[field]['mean']:.4f}")
                    for field in ("ndcg@10", "source_mrr@10", "source_recall@10", "source_recall@20")]
            lines.append(f"| `{n}` | {kind} | {len(rows)} | " + " | ".join(vals) + " |")
    lines += ["", "## Accounting and reliability", "",
              f"- New v2 requests: {accounting['requests']}; completed: "
              f"`{json.dumps(report['completed_queries'], sort_keys=True)}`.",
              f"- New input/output/reasoning tokens: {accounting['input_tokens']:,}/"
              f"{accounting['output_tokens']:,}/{accounting['reasoning_tokens']:,}.",
              f"- New local cost: ${accounting['accounted_usd']:.6f}; combined v1+v2 "
              f"${combined_cost:.6f} against the same${client.TASK_CAP / 1e9:.2f} ceiling.",
              f"- Shared accounted tokens at completion: {accounting['shared_accounted_tokens']:,}. "
              f"Sequential API-time sum: {accounting['api_seconds']:.1f}s.",
              "- No reset, retry, silent paid cache repair or reranker-generated evaluation labels.",
              "", "## Known-item source changes", "",
              "| Arm | Query | Source rank before -> after |", "|---|---|---|"]
    for n, changes in known_changes.items():
        for change in changes:
            lines.append(f"| `{n}` | {change['query_id']} | "
                         f"{change['baseline_source_rank']} -> {change['candidate_source_rank']} |")
    lines += ["", "## Explicit failures", "", json.dumps(failures, sort_keys=True),
              "", "## Interpretation", "", *[f"- {s}" for s in report["cautions"]],
              "- Exact paired v1 comparisons and score-tie counts are in `report.json`; "
              "v1's primary artifacts remain unchanged."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Only the first query at both depths")
    args = parser.parse_args(argv)
    if args.smoke and not args.run:
        parser.error("--smoke requires --run")
    papers, queries, qids, base, snapshot, requests, provenance = prepare()
    freeze(OUT / "execution-policy.json", {
        "stop_on_any_failure": True, "automatic_retries": False,
        "resume_after_failure": "Investigate before any more paid requests; no automatic continuation.",
        "scope": "User amendment before the first v2 request; applies beyond the smoke gate too.",
    })
    ledger = client.PilotLedger(version=VERSION)
    estimate = preflight(requests, ledger)
    fusion._write_json(OUT / "preflight.json", estimate)
    print(json.dumps({k: v for k, v in estimate.items() if k != "request_preflight"}, indent=2), flush=True)
    if not args.run:
        return
    if estimate["attempted_uncached_no_retry"]:
        raise api.OpenAIError(
            "Prior v2 attempt has no valid cache; investigate before any further paid requests")
    smoke = [r for r in requests if r["query_id"] == qids[0]]
    ordered = smoke + [r for r in requests if r["query_id"] != qids[0]]
    runs = {v1.BASELINE: base, **{system_name(d): {} for d in v1.DEPTHS}}
    failures = {system_name(d): {} for d in v1.DEPTHS}
    ties = {system_name(d): {} for d in v1.DEPTHS}
    for r in (smoke if args.smoke else ordered):
        try:
            scores, _ = v1.cached_call(
                OUT / "responses" / f"{r['request_key']}.json",
                r["encoded"], r["presented_ids"], ledger, run=True,
                failure_output_path=OUT / "failures" / f"{r['request_key']}.json")
        except api.OpenAIError:
            attempt = ledger.attempted(r["request_key"])
            failures[system_name(r["depth"])][r["query_id"]] = (
                {"status": attempt["status"], "request_key": r["request_key"],
                 "accounted_tokens": attempt["accounted_tokens"]} if attempt else
                {"status": "blocked_before_request", "request_key": r["request_key"],
                 "accounted_tokens": 0})
            fusion._write_json(OUT / "failed-requests.json", failures)
            print(f"STOPPED top{r['depth']} {r['query_id']}; investigate before further requests. "
                  "No retry or fallback.", flush=True)
            raise
        name, q = system_name(r["depth"]), r["query_id"]
        runs[name][q] = apply_scores(base[q], r["presented_ids"], scores)
        ties[name][q] = {"candidates": len(scores), "distinct_scores": len(set(scores.values()))}
        print(f"Completed top{r['depth']} {q}; new v2 cost ${ledger.summary()['accounted_usd']:.4f}", flush=True)
    if args.smoke:
        print("Both smoke requests passed. Cached results will be reused; no other requests sent.")
        return
    for n, run in runs.items():
        fusion.validate_run(n, run, sorted(run), papers, exact_depth=100)
        fusion._write_json(OUT / f"{n}.run.json", run)
    accounting_path = OUT / "accounting.json"
    if accounting_path.exists():
        saved = json.loads(accounting_path.read_text(encoding="utf-8"))
        if ledger.summary()["requests"] != saved["v2"]["requests"]:
            raise ValueError("Completed v2 request count changed")
    else:
        saved = {"v2": ledger.summary(), "combined_v1_v2_usd": ledger.combined_cost_nanodollars() / 1e9}
        freeze(accounting_path, saved)
    report = publish(papers, queries, qids, base, snapshot, runs, failures, provenance,
                     saved["v2"], saved["combined_v1_v2_usd"], ties)
    print(f"V2 complete: {report['completed_queries']}; missing judgments "
          f"{report['missing_pairs']}; no promotion.")


if __name__ == "__main__":
    main()
