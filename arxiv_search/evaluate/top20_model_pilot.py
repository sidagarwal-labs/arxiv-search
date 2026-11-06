"""Offline preparation for changing only the top20 refinement model."""

from __future__ import annotations

import hashlib
import json
import argparse
import statistics

import tiktoken

from arxiv_search import config, openai_answer, openai_rerank
from arxiv_search.evaluate import llm_reranker_pilot, top20_compare
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "top20-model-pilot"
MODEL = openai_answer.MODELS["gpt-5.4"]


def payload(query: str, presented: list[str], papers: dict) -> bytes:
    original = json.loads(openai_rerank.encode_refine_payload(query, presented, papers))
    original["model"] = MODEL
    return json.dumps(original, ensure_ascii=False, sort_keys=True).encode("utf-8")


def comparison_diagnostics() -> dict:
    root = top20_compare.OUT
    plan = json.loads((root / "preregistration.json").read_bytes())
    counts = {"forward": {}, "reverse": {}}
    unequal_total = unequal_correct = unequal_agree = decisive = 0
    correct_by_orientation = [0, 0]
    labels = json.loads((config.RESULTS_DIR / "top20-label-completion" / "labels.json")
                        .read_bytes())["labels"]
    run = json.loads((config.RESULTS_DIR / "llm-score-refine-pin" /
                      "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json").read_bytes())
    records = []
    for q in plan["pilot_queries"]:
        replies = [json.loads((root / "responses" / f"{q}-{orientation}.json").read_bytes())
                   ["outcome"] for orientation in ("forward", "reverse")]
        for n, (i, j) in enumerate(top20_compare.pairs(), 1):
            a, b = [reply[f"C{n}"] for reply in replies]
            canonical_b = {"A": "B", "B": "A", "tie": "tie", "insufficient": "insufficient"}[b]
            for orientation, verdict in zip(counts, (a, b)):
                counts[orientation][verdict] = counts[orientation].get(verdict, 0) + 1
            gi, gj = labels[q][run[q][i]], labels[q][run[q][j]]
            if gi == gj:
                continue
            unequal_total += 1
            expected = "A" if gi > gj else "B"
            correct_by_orientation[0] += a == expected
            correct_by_orientation[1] += canonical_b == expected
            unequal_agree += a == canonical_b
            if a in ("A", "B") and canonical_b in ("A", "B") and a == canonical_b:
                decisive += 1
                unequal_correct += a == expected
            records.append({"query_id": q, "comparison": n, "grades": [gi, gj],
                            "forward": a, "reverse_canonical": canonical_b})
    result = {
        "verdict_counts": counts, "unequal_grade_pairs": unequal_total,
        "accuracy_counting_tie_as_wrong": {
            "forward": correct_by_orientation[0] / unequal_total,
            "reverse": correct_by_orientation[1] / unequal_total},
        "unequal_grade_reversal_agreement": unequal_agree / unequal_total,
        "consistent_decisive_pairs": decisive,
        "consistent_decisive_accuracy": unequal_correct / decisive if decisive else None,
        "caution": "Grades are pooled model judgments, not ground truth. Equal-grade comparisons "
                   "may legitimately differ. A/B and evidence-order reversals are confounded. "
                   "This is a post-hoc diagnostic, never a new tuned ranking candidate.",
        "rows": records,
    }
    (root / "comparison-diagnostics.json").write_text(json.dumps(result, indent=2) + "\n",
                                                    encoding="utf-8")
    return result


def prepare() -> dict:
    prior = json.loads((top20_compare.OUT / "preregistration.json").read_bytes())
    pilot = prior["pilot_queries"]
    split = json.loads((config.EVAL_DIR / "split.json").read_bytes())
    if not set(pilot) <= set(split["dev"]) or set(pilot) & set(split["test"]):
        raise ValueError("Pilot is not dev-only")
    run_path = config.RESULTS_DIR / "llm-score-pass2" / (
        "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json")
    run = json.loads(run_path.read_bytes())
    labels_path = config.RESULTS_DIR / "top20-label-completion" / "labels.json"
    labels = json.loads(labels_path.read_bytes())["labels"]
    queries = {q["query_id"]: q for line in (config.EVAL_DIR / "queries.jsonl")
               .read_text(encoding="utf-8").splitlines() if (q := json.loads(line))}
    papers = {p["arxiv_id"]: p for line in (config.PROJECT_ROOT / "data" / "processed" /
                                           "corpus.jsonl").read_text(encoding="utf-8").splitlines()
              if (p := json.loads(line))}
    count = tiktoken.get_encoding("o200k_base")
    requests = []
    for q in pilot:
        presented = llm_reranker_pilot.presentation(q, run[q][:20])
        if any(p not in labels[q] for p in presented):
            raise ValueError("Unjudged candidate in replacement refinement")
        encoded = payload(queries[q]["query"], presented, papers)
        requests.append({
            "query_id": q, "presented_ids": presented,
            "payload_sha256": hashlib.sha256(encoded).hexdigest(),
            "estimated_input": round(len(count.encode(encoded.decode(),
                                                    disallowed_special=())) * 1.1) + 4096,
            "reserved_input": openai_answer.reserved_input(encoded),
        })
    price_in, price_out = openai_answer.PRICES[MODEL]
    cost = {
        "requests": 40,
        "estimated_usd_150_output": sum(2 * (r["estimated_input"] * price_in +
                                            150 * price_out) for r in requests) / 1e9,
        "worst_full_byte_reservation_usd": sum(
            2 * (r["reserved_input"] * price_in + openai_rerank.REFINE_MAX_OUTPUT * price_out)
            for r in requests) / 1e9,
    }
    plan = {
        "version": "top20-model-v1", "status": "offline proposal; new paid cap requires approval",
        "model": MODEL, "reasoning_effort": "none",
        "one_change": "Replace GPT-5.4 mini with GPT-5.4 in existing D47 refinement. Use the "
                      "same D46 top20, same deterministic presentation, same refine20-v1 prompt, "
                      "same512-output cap, two averaged scores, RRFc30 and pin D46 rank1. "
                      "This replaces refinement rather than adding a post-D47 stage.",
        "reference": "Saved D47 mini refinement, rescored on completed top20 labels",
        "pilot_queries": pilot, "requests": requests,
        "primary_gate": {"ndcg_gain": ">0.0106 and paired95% CI lower bound>0",
                         "source_mrr_delta": ">=-0.02", "complete": "40 valid replies",
                         "judged_top10": "100%"},
        "cost": cost,
        "cost_interpretation": "Estimate uses tokenizer+10%+4096. Worst case uses actual transport "
                               "UTF8-byte input reservation and full512 output for every call. "
                               "No cache discounts. No retries. Shared daily guard stays active.",
        "label_sha256": hashlib.sha256(labels_path.read_bytes()).hexdigest(),
        "d46_run_sha256": hashlib.sha256(run_path.read_bytes()).hexdigest(),
        "scope": "20 previously analyzed dev queries, diagnostic only; not held-out evidence",
        "automatic_promotion": False, "test_evaluation": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", plan)
    return plan


def build_ranking(base: list[str], presented: list[str], replies: list[dict]) -> list[str]:
    from arxiv_search.evaluate import llm_score_refine as refine
    from arxiv_search.evaluate import llm_score_safeguard as guard
    from arxiv_search.evaluate.llm_score_refine_pin import pin_first

    scores = [openai_rerank.validate_refine_scores(reply) for reply in replies]
    if len(scores) != 2:
        raise ValueError("Both refinement passes required")
    return pin_first(base, guard.fuse(base, refine.refine(base, presented, scores), depth=20))


def execute(plan: dict) -> dict:
    from arxiv_search.evaluate import answer_eval as ev, metrics

    ledger = openai_answer.TaskLedger("top20-model-v1", 4_500_000_000, 40)
    freeze(OUT / "run-approval.json", {
        "date": "2026-11-05", "cap_usd": 4.5, "max_requests": 40,
        "authority": "Owner approved GPT-5.4 pilot estimated $1.32 hard cap $4.50",
        "plan_sha256": hashlib.sha256((OUT / "preregistration.json").read_bytes()).hexdigest(),
    })
    base = json.loads((config.RESULTS_DIR / "llm-score-pass2" /
                      "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json").read_bytes())
    d47 = json.loads((config.RESULTS_DIR / "llm-score-refine-pin" /
                     "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json").read_bytes())
    labels = json.loads((config.RESULTS_DIR / "top20-label-completion" / "labels.json")
                        .read_bytes())["labels"]
    queries = {q["query_id"]: q for line in (config.EVAL_DIR / "queries.jsonl")
               .read_text(encoding="utf-8").splitlines() if (q := json.loads(line))}
    papers = {p["arxiv_id"]: p for line in (config.PROJECT_ROOT / "data" / "processed" /
                                           "corpus.jsonl").read_text(encoding="utf-8").splitlines()
              if (p := json.loads(line))}
    rows = []
    for request in plan["requests"]:
        q = request["query_id"]
        encoded = payload(queries[q]["query"], request["presented_ids"], papers)
        if hashlib.sha256(encoded).hexdigest() != request["payload_sha256"]:
            raise ValueError("Payload differs from frozen plan")
        replies, durations = [], []
        for n in (1, 2):
            # Intentionally identical passes have separate ledger keys, not altered prompts.
            key = openai_rerank.repeat_key(encoded, n)
            path = OUT / "responses" / f"{q}-pass{n}.json"
            if not path.exists():
                if ledger.attempted(key):
                    raise ValueError("Attempt without cached outcome; no retry")
                try:
                    value, usage = openai_answer.call_once(
                        encoded, ledger, validate=openai_rerank.validate_refine_scores,
                        attempt_key=key, failure_path=path.with_suffix(".failure.json"))
                except openai_answer.InvalidAnswer as error:
                    ev._write(path, {"request_sha256": openai_answer.request_key(encoded),
                                     "outcome": {"status": error.status, "detail": error.detail},
                                     "usage": ledger.attempt(key)})
                    raise
                ev._write(path, {"request_sha256": openai_answer.request_key(encoded),
                                 "outcome": {"status": "ok", **value}, "usage": usage})
            saved = ev._read(path, encoded)
            if saved["outcome"]["status"] != "ok":
                raise ValueError("Saved refinement failure; no retry")
            replies.append({k: v for k, v in saved["outcome"].items() if k != "status"})
            durations.append(saved["usage"]["latency_seconds"])
            print(f"{q} pass{n} saved; ${ledger.summary()['accounted_usd']:.4f}", flush=True)
        ranked = build_ranking(base[q], request["presented_ids"], replies)
        if set(ranked[:20]) != set(d47[q][:20]) or ranked[20:] != base[q][20:]:
            raise ValueError("Candidate pool or tail changed")
        grades = labels[q]
        source = {queries[q]["source_arxiv_id"]: 2}
        rows.append({
            "query_id": q, "baseline": metrics.ndcg_at_k(d47[q], grades),
            "candidate": metrics.ndcg_at_k(ranked, grades),
            "source_delta": metrics.reciprocal_rank(ranked, source) -
                            metrics.reciprocal_rank(d47[q], source),
            "fully_judged": metrics.judged_at_k(ranked, grades) == 1,
            "parallel_api_seconds": max(durations), "top20": ranked[:20],
        })
    delta, low, high = metrics.paired_diff_ci([r["baseline"] for r in rows],
                                             [r["candidate"] for r in rows])
    mrr = statistics.fmean(r["source_delta"] for r in rows)
    checks = {"ndcg": delta > 0.0106 and low > 0, "source_mrr": mrr >= -0.02,
              "complete": len(rows) == 20 and ledger.summary()["requests"] == 40,
              "fully_judged": all(r["fully_judged"] for r in rows)}
    report = {
        "baseline_ndcg": statistics.fmean(r["baseline"] for r in rows),
        "candidate_ndcg": statistics.fmean(r["candidate"] for r in rows),
        "delta": delta, "ci95": [low, high], "source_mrr_delta": mrr,
        "checks": checks, "pilot_pass": all(checks.values()),
        "mean_parallel_api_seconds": statistics.fmean(r["parallel_api_seconds"] for r in rows),
        "accounting": ledger.summary(), "rows": rows,
    }
    ev._write(OUT / "report.json", report)
    (OUT / "report.md").write_text(
        "# GPT-5.4 top20 model-only pilot\n\n"
        f"D47: {report['baseline_ndcg']:.4f}; candidate: {report['candidate_ndcg']:.4f}.\n\n"
        f"Delta: {delta:+.4f} [{low:+.4f}, {high:+.4f}].\n\n"
        f"Source MRR delta: {mrr:+.4f}. Pilot pass: {report['pilot_pass']}.\n\n"
        f"Cost: ${report['accounting']['accounted_usd']:.4f}.\n\n"
        "Only the refinement model changed. Twenty previously analyzed dev queries, completed "
        "top20 labels (owner-attributed GPT 6 Terra additions). No test evaluation or promotion. "
        "Passes executed sequentially; max-of-two API duration is not measured parallel serving "
        "latency. See report.json for checks, query rows and resource usage.\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    plan = prepare()
    if args.run:
        report = execute(plan)
        print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    else:
        diagnostics = comparison_diagnostics()
        print(json.dumps({k: v for k, v in diagnostics.items() if k != "rows"}, indent=2))
        print(json.dumps(plan["cost"], indent=2))


if __name__ == "__main__":
    main()
