"""Twenty-query mini reranker pilot: preflight by default, --run for approved calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import tiktoken

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, judge, results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.score_candidate_review import query_changes
from arxiv_search.evaluate.score_fusion_experiment import summarize
from arxiv_search.search.rerank import rerank_prefix

OUT = config.RESULTS_DIR / "llm-reranker-pilot"
BASELINE = "fusion-shortlist+a=1+d=500"
SAMPLE_SEED = "mini-pilot-proposal-v1"
ORDER_SEED = "mini-reranker-order-v1"
DEPTHS = (10, 50)


def system_name(depth: int) -> str:
    if depth not in DEPTHS:
        raise ValueError("Unexpected pilot depth")
    return f"llm-mini-pilot+d={depth}"


def select_queries(queries: dict, split: dict) -> list[str]:
    dev = split["dev"]
    if len(dev) != 100 or len(set(dev)) != 100 or set(dev) & set(split["test"]):
        raise ValueError("Expected100 distinct dev queries disjoint from held-out")
    selected = []
    for kind in catalog.QUERY_TYPES:
        group = [q for q in dev if queries[q]["query_type"] == kind]
        if len(group) != 25:
            raise ValueError("Expected25 dev queries per segment")
        selected.extend(sorted(group, key=lambda q: hashlib.sha256(
            f"{SAMPLE_SEED}:{q}".encode()).hexdigest())[:5])
    return sorted(selected)


def presentation(qid: str, candidates: list[str]) -> list[str]:
    if len(candidates) != len(set(candidates)):
        raise ValueError("Duplicate candidate IDs")
    return sorted(candidates, key=lambda p: hashlib.sha256(
        f"{ORDER_SEED}:{qid}:{p}".encode()).hexdigest())


def plan(qids: list[str]) -> dict:
    return {
        "hypothesis": "Joint query-paper reading better distinguishes direct task/constraint "
                      "satisfaction from topic overlap; deeper selection can replace weak top10s.",
        "model": client.MODEL, "reasoning_effort": "none", "baseline": BASELINE,
        "query_ids": qids, "sample": "Lowest five SHA256 hashes per dev type using " + SAMPLE_SEED,
        "depths": list(DEPTHS), "max_requests": client.MAX_REQUESTS,
        "prompt_sha256": hashlib.sha256(client.SYSTEM.encode()).hexdigest(),
        "presentation": ORDER_SEED + ":qid:paper SHA256 order; rank/source labels withheld",
        "inputs": "Full title, all authors, full abstract; no tools, browsing or source flags.",
        "output": "Exact candidate permutation and ten brief evidence notes, never evaluation labels.",
        "max_output_tokens": client.MAX_OUTPUT,
        "budget": {"maximum_new_accounted_usd": client.TASK_CAP / 1e9,
                   "input_usd_per_million": client.INPUT_PRICE / 1000,
                   "output_usd_per_million": client.OUTPUT_PRICE / 1000,
                   "ledger": "data/openai/usage.sqlite3", "no_reset": True,
                   "reservation": "UTF8 payload bytes +4096 overhead +full output cap",
                   "automatic_retries": False, "unknown_outcomes_keep_reservations": True},
        "evaluation": "Same20 queries for both arms and baseline. Frozen labels plus human "
                      "overrides; no new judging. Withhold incomplete graded comparisons. "
                      "Separate pilot table, never rank against100-query leaderboard.",
        "success_screen": "Exploratory practical target +.02 nDCG on complete labels; inspect "
                          "P10/source recall/known-item ranks, per-query changes and cost/latency. "
                          "Only five queries per segment, no promotion or generalized claim.",
        "automatic_promotion": False, "judge_api_calls": 0, "held_out_queries": 0,
        "judge_bias": "GPT-5.4 mini also made most labels: shared-family self-preference risk. "
                      "Independent blind human/other-judge validation still required.",
    }


def read_cached(path: Path, encoded: bytes, presented: list[str]) -> tuple[dict, dict] | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value.get("request_key") != client.request_key(encoded)
            or value.get("presented_ids") != presented or value.get("model") != client.MODEL
            or value.get("answer_sha256") != fusion.fingerprint(value.get("answer"))):
        raise ValueError("Reranker cache provenance/checksum mismatch")
    answer = client.validate_answer(value["answer"], len(presented)).model_dump()
    usage = value["usage"]
    if usage["status"] != "completed" or usage["model"] != client.MODEL:
        raise ValueError("Reranker cache has no successful accounted request")
    return answer, usage


def cached_call(path: Path, encoded: bytes, presented: list[str], ledger: client.PilotLedger,
                *, run: bool) -> tuple[dict, dict]:
    cached = read_cached(path, encoded, presented)
    if cached is not None:
        return cached
    if not run:
        raise api.OpenAIError("Reranker response missing; --run and approved budget required")
    if ledger.attempted(client.request_key(encoded)) is not None:
        raise api.OpenAIError("Request already attempted; no retry or paid cache repair")
    answer, usage = client.call_once(
        encoded, len(presented), ledger,
        failure_output_path=OUT / "failures" / f"{client.request_key(encoded)}.json")
    value = {"request_key": client.request_key(encoded), "model": client.MODEL,
             "presented_ids": presented, "answer": answer, "usage": usage,
             "answer_sha256": fusion.fingerprint(answer)}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return answer, usage


def apply_answer(base: list[str], presented: list[str], answer: dict) -> list[str]:
    parsed = client.validate_answer(answer, len(presented))
    if set(presented) != set(base[:len(presented)]):
        raise ValueError("Reranker candidate prefix changed")
    ranked = [presented[int(label[1:]) - 1] for label in parsed.ranking]
    return rerank_prefix(base, {pid: float(-i) for i, pid in enumerate(ranked)}, len(ranked))


def prepare() -> tuple:
    papers, queries, split = judge.load_inputs()
    qids = select_queries(queries, split)
    baseline_path = config.RESULTS_DIR / "shortlist-score-dev" / f"{BASELINE}.run.json"
    baseline_bytes = baseline_path.read_bytes()
    all_base = json.loads(baseline_bytes)
    fusion.validate_run(BASELINE, all_base, split["dev"], papers, exact_depth=100)
    if config.WORKING_BASELINE_SYSTEM != BASELINE:
        raise ValueError("Approved baseline changed; create a new pilot identity")
    base = {q: all_base[q] for q in qids}
    _, label_bytes, snapshot, _ = catalog.load_snapshot(config.RESULTS_DIR)
    if not snapshot["complete"] or set(snapshot["labels"]) != set(split["dev"]):
        raise ValueError("Expected complete frozen parent labels")
    subset = {"labels": {q: snapshot["labels"][q] for q in qids}, "query_ids": qids}
    if any(p not in subset["labels"][q] for q in qids for p in base[q][:10]):
        raise ValueError("Baseline pilot top10 must be fully judged")
    experiment = plan(qids)
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", experiment)
    requests = []
    for depth in DEPTHS:
        for q in qids:
            presented = presentation(q, base[q][:depth])
            encoded = client.encode_payload(queries[q]["query"], presented, papers)
            requests.append({"query_id": q, "depth": depth, "presented_ids": presented,
                             "encoded": encoded, "request_key": client.request_key(encoded)})
    provenance = {
        "baseline_bytes_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "full_labels_bytes_sha256": hashlib.sha256(label_bytes).hexdigest(),
        "subset_labels_sha256": fusion.fingerprint(subset),
        "human_workbook_sha256": snapshot["human_workbook_sha256"],
        "model": client.MODEL, "query_ids": qids,
        "requests": [{k: v for k, v in r.items() if k != "encoded"} for r in requests],
    }
    freeze(OUT / "input-provenance.json", provenance)
    return papers, queries, qids, base, subset, requests, provenance


def preflight(requests: list[dict], ledger: client.PilotLedger) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    tasks, missing, blocked = [], [], []
    for r in requests:
        row = {
            "query_id": r["query_id"], "depth": r["depth"], "request_key": r["request_key"],
            "serialized_token_estimate": len(tokenizer.encode(r["encoded"].decode("utf-8"))),
            "reserved_input_tokens": client.reserved_input(r["encoded"]),
        }
        cached = read_cached(OUT / "responses" / f"{r['request_key']}.json",
                             r["encoded"], r["presented_ids"])
        row["cached"] = cached is not None
        previous = ledger.attempted(r["request_key"]) if cached is None else None
        row["attempt_status"] = previous["status"] if previous is not None else None
        tasks.append(row)
        if previous is not None:
            blocked.append(row)
        elif not row["cached"]:
            missing.append(row)
    accounting = ledger.summary()
    estimates = sum(r["serialized_token_estimate"] for r in missing)
    expected_high = estimates * 1.1 + len(missing) * client.MAX_OUTPUT
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    return {
        "total_requests": len(requests), "unattempted_requests": len(missing),
        "attempted_uncached_no_retry": len(blocked),
        "cached_requests": len(requests) - len(missing) - len(blocked), "request_preflight": tasks,
        "serialized_input_token_estimate": estimates,
        "expected_tokens_with_10pct_input_headroom_and_max_output": expected_high,
        "maximum_single_request_reservation": max(
            (r["reserved_input_tokens"] + client.MAX_OUTPUT for r in missing), default=0),
        "all_requests_conservative_reservations": sum(
            r["reserved_input_tokens"] + client.MAX_OUTPUT for r in missing),
        "expected_cost_usd_output_400_to_2048": [
            (estimates * 1.1 * client.INPUT_PRICE + len(missing) * out * client.OUTPUT_PRICE) / 1e9
            for out in (400, client.MAX_OUTPUT)],
        "task_ceiling_usd": client.TASK_CAP / 1e9,
        "shared_token_limit": limit, "shared_remaining_tokens": limit - accounting["shared_accounted_tokens"],
        "accounting": accounting,
        "caution": "Tokenizer/10% estimates are not provider usage or a reservation. Actual "
                   "per-call reservation uses UTF8 bytes plus protocol/output caps. Sequential "
                   "settlement frees headroom; any cap stops before the next request. No retries.",
    }


def ranking_only_diagnostic(runs: dict, provenance: dict, papers: dict,
                            queries: dict, qids: list[str], snapshot: dict) -> dict:
    recovered = {n: {q: ids[:] for q, ids in run.items()} for n, run in runs.items()}
    categories = {}
    for r in provenance.get("requests", []):
        n, q, size = system_name(r["depth"]), r["query_id"], r["depth"]
        if q in recovered[n]:
            continue
        path = OUT / "failures" / f"{r['request_key']}.json"
        category = "output_not_retained"
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved["request_key"] != r["request_key"] or saved["model"] != client.MODEL:
                raise ValueError("Failure diagnostic provenance mismatch")
            texts = [part["text"] for item in saved["output"] if item.get("type") == "message"
                     for part in item.get("content", []) if part.get("type") == "output_text"]
            if len(texts) != 1:
                category = "no_single_structured_answer"
            else:
                try:
                    value = client.Ranking.model_validate_json(texts[0])
                except ValueError:
                    category = "schema_invalid"
                else:
                    expected = {f"P{i}" for i in range(1, size + 1)}
                    if len(value.ranking) != size or set(value.ranking) != expected:
                        category = "invalid_permutation"
                    else:
                        category = "valid_permutation_rejected_evidence"
                        ids = [r["presented_ids"][int(label[1:]) - 1] for label in value.ranking]
                        recovered[n][q] = rerank_prefix(
                            runs[BASELINE][q], {p: float(-i) for i, p in enumerate(ids)}, size)
        categories.setdefault(n, {})[q] = category
    matched = sorted(set(qids).intersection(*(set(r) for r in recovered.values())))
    subset = {"query_ids": matched, "labels": {q: snapshot["labels"][q] for q in matched}}
    results = catalog.score_catalog(
        {n: {"run": {q: run[q] for q in matched}, "paths": [], "metadata": {}}
         for n, run in recovered.items()}, subset, papers, queries, matched, BASELINE) if matched else {}
    rows = {n: r["per_query"] for n, r in results.items()}
    return {
        "scope": "Post-hoc ranking-only diagnostic, NOT the strict primary pilot. "
                 "Use only exact full permutations; ignore rejected evidence notes. "
                 "Never repair missing/duplicate IDs, generate labels or change strict run files. "
                 "Still success-selected; no promotion or generalized quality claim.",
        "failure_categories": categories, "matched_query_ids": matched,
        "matched_queries": len(matched),
        "available_rankings": {n: len(r) for n, r in recovered.items()},
        "systems": results, "summary": summarize(rows, BASELINE) if matched else {},
        "api_calls": 0,
    }


def publish(papers: dict, queries: dict, qids: list[str], base: dict, snapshot: dict,
            runs: dict, responses: list[dict], provenance: dict,
            accounting: dict, failures: dict | None = None) -> dict:
    failures = failures or {}
    matched = sorted(set(qids).intersection(*(set(r) for r in runs.values())))
    matched_runs = {n: {q: r[q] for q in matched} for n, r in runs.items()}
    matched_snapshot = {"labels": {q: snapshot["labels"][q] for q in matched}, "query_ids": matched}
    results = catalog.score_catalog(
        {n: {"run": r, "paths": [], "metadata": {"scope": "matched pilot queries only"}}
         for n, r in matched_runs.items()},
        matched_snapshot, papers, queries, matched, BASELINE) if matched else {}
    rows = {n: r["per_query"] for n, r in results.items()}
    summary = summarize(rows, BASELINE) if matched else {}
    diagnostic = ranking_only_diagnostic(runs, provenance, papers, queries, qids, snapshot)
    fusion._write_json(OUT / "ranking-only-diagnostic.json", diagnostic)
    missing = {q: sorted({p for run in runs.values() for p in run.get(q, [])[:10]}
                          - set(snapshot["labels"][q])) for q in qids}
    differences = {n: query_changes(matched_runs, rows, queries, BASELINE, n)
                   for n in runs if n != BASELINE} if matched else {}
    known_changes = {
        n: [v for v in values if v["query_type"] == "known_item"
            and v["baseline_source_rank"] != v["candidate_source_rank"]]
        for n, values in differences.items()}
    cases = {}
    for q in qids:
        ids = list(dict.fromkeys([p for r in runs.values() for p in r.get(q, [])[:10]]
                                + [queries[q]["source_arxiv_id"]]))
        cases[q] = {
            "query": queries[q],
            "papers": [{"arxiv_id": p, "title": papers[p]["title"], "authors": papers[p]["authors"],
                        "abstract": papers[p]["abstract"], "grade": snapshot["labels"][q].get(p),
                        "ranks": {n: run[q].index(p) + 1 if p in run.get(q, []) else None
                                  for n, run in runs.items()}} for p in ids],
        }
    latencies = [r["usage"]["latency_seconds"] for r in responses]
    report = {
        "model": client.MODEL, "baseline": BASELINE, "query_ids": qids, "queries": len(qids),
        "matched_query_ids": matched, "matched_queries": len(matched), "failures": failures,
        "completed_queries_per_system": {n: len(r) for n, r in runs.items()},
        "failure_categories": diagnostic["failure_categories"],
        "systems": results, "summary": summary, "changes": differences,
        "known_item_target_changes": known_changes, "missing": missing,
        "missing_pairs": sum(map(len, missing.values())), "accounting": accounting,
        "latency_seconds": {"total_successful": sum(latencies),
                            "mean_successful": statistics.mean(latencies) if latencies else None,
                            "median_successful": statistics.median(latencies) if latencies else None,
                            "max_successful": max(latencies) if latencies else None},
        "provenance": provenance, "judge_api_calls": 0, "promoted": False,
        "independent_validation": False,
        "cautions": ["Only20 already-examined dev queries; five per segment; exploratory.",
                     "Failures are explicit, not replaced with baseline results. Matched successful "
                     "queries are complete-case diagnostics, susceptible to failure-selection bias.",
                     "Most evaluation labels use the same model family as the reranker.",
                     "One frozen presentation order; no order-sensitivity or repeat runs.",
                     "Unjudged new top10s require independent labels before comparable nDCG/P10.",
                     "Reranker notes are not labels. Not a100-query leaderboard entry."],
    }
    fusion._write_json(OUT / "report.json", report)
    fusion._write_json(OUT / "cases.json", cases)
    lines = [
        "# Mini LLM reranker pilot:20 queries, top10 versus top50", "",
        "Separate pilot benchmark, not comparable to the100-query leaderboard. "
        "Planned20 frozen queries for baseline and both arms; five per segment. "
        f"**Matched successful queries used below: {len(matched)}/{len(qids)}.** "
        "Failed queries are excluded identically from both arms and baseline, with no silent fallback.",
        f"Completed queries per system: `{json.dumps(report['completed_queries_per_system'], sort_keys=True)}`.",
        f"Model `{client.MODEL}`; full title/authors/abstract; reasoning disabled; "
        "hash-shuffled candidates, no tools, no retries. No promotion or new judging.", "",
        "| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |",
        "|---|---|---|---|---|---|---|"]
    for n, result in results.items():
        complete = result["top10_fully_judged"]
        values = [("withheld" if not complete and f in ("ndcg@10", "precision@10")
                   else f"{result['all'][f]['mean']:.4f}")
                  for f in ("ndcg@10", "precision@10", "judged@10", "source_mrr@10",
                            "source_recall@10", "source_recall@20")]
        lines.append(f"| `{n}` | " + " | ".join(values) + " |")
    lines += ["", f"Missing new top10 judgments: **{report['missing_pairs']}**. "
              "Incomplete graded scores in JSON are diagnostic only; paired intervals withheld. "
              "Adding labels may revise IDCG, so these are not bounds on final nDCG.",
              "", "## Paired candidate minus pilot baseline", "",
              "| Arm | nDCG delta [95% CI] | Source MRR delta [95% CI] |",
              "|---|---|---|"]
    for depth in DEPTHS:
        n = system_name(depth)
        cells = []
        for field in ("ndcg@10", "source_mrr@10"):
            paired = summary[n]["all"][field]["paired_vs_working"] if matched else None
            cells.append("withheld" if paired is None else
                         f"{paired['difference']:+.4f} [{paired['ci95'][0]:+.4f},{paired['ci95'][1]:+.4f}]")
        lines.append(f"| top{depth} | " + " | ".join(cells) + " |")
    lines += ["", "## Segment results (matched successful queries)", "",
              "| System | Segment | Queries | nDCG10 | Source MRR10 | R10 | R20 |",
              "|---|---|---|---|---|---|---|"]
    for n in runs:
        for kind in catalog.QUERY_TYPES:
            count = sum(queries[q]["query_type"] == kind for q in matched)
            if not count:
                lines.append(f"| `{n}` | {kind} | 0 | withheld | withheld | withheld | withheld |")
                continue
            group = summary[n][kind]
            complete = all(r["judged@10"] == 1 for r in rows[n] if r["query_type"] == kind)
            vals = [("withheld" if field == "ndcg@10" and not complete else
                     f"{group[field]['mean']:.4f}")
                    for field in ("ndcg@10", "source_mrr@10", "source_recall@10", "source_recall@20")]
            lines.append(f"| `{n}` | {kind} | {count} | " + " | ".join(vals) + " |")
    lines += ["", "## Accounting and reproducibility", "",
              f"- New locally accounted cost: ${accounting['accounted_usd']:.6f}; "
              f"task cap ${client.TASK_CAP / 1e9:.2f}. Standard uncached rates; not provider billing.",
              f"- Requests: {accounting['requests']}; input/output tokens: "
              f"{accounting['input_tokens']:,}/{accounting['output_tokens']:,}; "
              f"reasoning tokens: {accounting['reasoning_tokens']}.",
              f"- Successful-response latency: `{json.dumps(report['latency_seconds'], sort_keys=True)}`. "
              "Accounting retains failed-attempt latency too. Not production end-to-end search latency.",
              "- Plans, input hashes, presentation order, response cache and usage are persisted. "
              "Replay must validate cached answers and make zero new calls.",
              "- Frozen parent label bytes/human overrides preserved. No held-out queries sent.",
              "", "## Known-item target changes", "",
              "| Arm | Query | Source rank before -> after |", "|---|---|---|"]
    for n, changes in known_changes.items():
        for change in changes:
            lines.append(f"| `{n}` | {change['query_id']} | "
                         f"{change['baseline_source_rank']} -> {change['candidate_source_rank']} |")
    lines += ["", "## Explicit failures (no retries)", "",
              "| Arm | Query | Failure category |", "|---|---|---|"]
    for n, values in failures.items():
        for q in values:
            category = diagnostic["failure_categories"].get(n, {}).get(q, "invalid_answer")
            lines.append(f"| `{n}` | {q} | {category} |")
    lines += ["", "## Post-hoc ranking-only diagnostic", "", diagnostic["scope"], "",
              f"Additional cached exact permutations yield **{diagnostic['matched_queries']}** "
              "matched queries for this secondary comparison. Strict acceptance/failure counts "
              "above do not change; details in `ranking-only-diagnostic.json`.", "",
              "| System | Queries | nDCG10 | Source MRR10 | R10 | Judged10 |",
              "|---|---|---|---|---|---|"]
    for n, result in diagnostic["systems"].items():
        cells = [("withheld" if field == "ndcg@10" and not result["top10_fully_judged"]
                  else f"{result['all'][field]['mean']:.4f}")
                 for field in ("ndcg@10", "source_mrr@10", "source_recall@10", "judged@10")]
        lines.append(f"| `{n}` | {diagnostic['matched_queries']} | " + " | ".join(cells) + " |")
    lines += ["",
              "## Interpretation limits", "",
              *[f"- {text}" for text in report["cautions"]]]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Enable only missing approved reranker calls")
    args = parser.parse_args(argv)
    papers, queries, qids, base, snapshot, requests, provenance = prepare()
    ledger = client.PilotLedger()
    estimate = preflight(requests, ledger)
    fusion._write_json(OUT / "preflight.json", estimate)
    print(json.dumps({k: v for k, v in estimate.items() if k != "request_preflight"}, indent=2), flush=True)
    if not args.run:
        return
    runs = {BASELINE: base, **{system_name(d): {} for d in DEPTHS}}
    responses = []
    failures = {system_name(d): {} for d in DEPTHS}
    for index, r in enumerate(requests, 1):
        try:
            answer, usage = cached_call(
                OUT / "responses" / f"{r['request_key']}.json", r["encoded"],
                r["presented_ids"], ledger, run=True)
        except api.OpenAIError:
            attempt = ledger.attempted(r["request_key"])
            if attempt is None or attempt["status"] != "invalid_answer":
                raise
            failures[system_name(r["depth"])][r["query_id"]] = {
                "request_key": r["request_key"], "request_id": attempt["request_id"],
                "status": attempt["status"], "accounted_tokens": attempt["accounted_tokens"],
            }
            fusion._write_json(OUT / "failed-requests.json", failures)
            print(f"FAILED {index}/40: top{r['depth']} {r['query_id']}; invalid_answer; "
                  "recorded, no retry or fallback; continuing unattempted requests.", flush=True)
            continue
        depth, q = r["depth"], r["query_id"]
        ranking = apply_answer(base[q], r["presented_ids"], answer)
        runs.setdefault(system_name(depth), {})[q] = ranking
        responses.append({"query_id": q, "depth": depth, "usage": usage})
        print(f"Completed {index}/40: top{depth} {q}; "
              f"accounted ${ledger.summary()['accounted_usd']:.4f}", flush=True)
    for n, run in runs.items():
        fusion.validate_run(n, run, sorted(run), papers, exact_depth=100)
        fusion._write_json(OUT / f"{n}.run.json", run)
    accounting_path = OUT / "accounting.json"
    if accounting_path.exists():
        accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
        if ledger.summary()["requests"] != accounting["requests"]:
            raise ValueError("Completed pilot request count changed")
    else:
        accounting = ledger.summary()
        freeze(accounting_path, accounting)
    report = publish(papers, queries, qids, base, snapshot, runs, responses, provenance, accounting, failures)
    print(f"Pilot complete:20 planned queries,{len(responses)} cached successful requests, "
          f"{report['matched_queries']} matched queries, {report['missing_pairs']} missing "
          "top10 judgments; no promotion.", flush=True)


if __name__ == "__main__":
    main()
