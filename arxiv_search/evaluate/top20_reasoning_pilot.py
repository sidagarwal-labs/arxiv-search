"""Prepare or explicitly run the owner-approved bounded low-reasoning pilot."""

from __future__ import annotations

import hashlib
import json
import argparse
import statistics

import tiktoken

from arxiv_search import config, openai_answer, openai_api, openai_rerank
from arxiv_search.evaluate import top20_model_pilot
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "top20-reasoning-pilot"
MAX_OUTPUT = 4096
MAX_REQUESTS = 40
CAP_NANODOLLARS = 6_600_000_000


def payload(query: str, presented: list[str], papers: dict) -> bytes:
    value = json.loads(top20_model_pilot.payload(query, presented, papers))
    value["reasoning"] = {"effort": "low"}
    value["max_output_tokens"] = MAX_OUTPUT
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def validate_scope(pilot: list[str], requests: list[dict], split: dict) -> None:
    ids = [r["query_id"] for r in requests]
    if (len(pilot) != 20 or len(set(pilot)) != 20 or ids != pilot
            or not set(pilot) <= set(split["dev"]) or set(pilot) & set(split["test"])):
        raise ValueError("Expected the same ordered twenty pilot dev queries only")


def prepare() -> dict:
    source_path = top20_model_pilot.OUT / "preregistration.json"
    source = json.loads(source_path.read_bytes())
    split = json.loads((config.EVAL_DIR / "split.json").read_bytes())
    validate_scope(source["pilot_queries"], source["requests"], split)
    paths = {
        "queries": config.EVAL_DIR / "queries.jsonl",
        "corpus": config.PROJECT_ROOT / "data" / "processed" / "corpus.jsonl",
        "labels": config.RESULTS_DIR / "top20-label-completion" / "labels.json",
        "d46": config.RESULTS_DIR / "llm-score-pass2" /
               "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json",
        "cached_ablations": config.RESULTS_DIR / "top20-ablations" / "report.json",
    }
    raw = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}
    if (hashes["labels"] != source["label_sha256"]
            or hashes["d46"] != source["d46_run_sha256"]):
        raise ValueError("Original pilot evidence changed")
    queries = {q["query_id"]: q for line in raw["queries"].decode("utf-8").splitlines()
               if (q := json.loads(line))}
    papers = {p["arxiv_id"]: p for line in raw["corpus"].decode("utf-8").splitlines()
              if (p := json.loads(line))}
    labels = json.loads(raw["labels"])["labels"]
    base = json.loads(raw["d46"])
    tokenizer = tiktoken.get_encoding("o200k_base")
    requests = []
    for old in source["requests"]:
        q, presented = old["query_id"], old["presented_ids"]
        if (len(presented) != 20 or len(set(presented)) != 20
                or set(presented) != set(base[q][:20])
                or any(p not in labels[q] for p in presented)):
            raise ValueError("Candidate pool changed or is not fully judged")
        original = top20_model_pilot.payload(queries[q]["query"], presented, papers)
        if hashlib.sha256(original).hexdigest() != old["payload_sha256"]:
            raise ValueError("Original payload cannot be reproduced")
        encoded = payload(queries[q]["query"], presented, papers)
        requests.append({
            "query_id": q, "presented_ids": presented,
            "payload_sha256": hashlib.sha256(encoded).hexdigest(),
            "estimated_input": round(len(tokenizer.encode(encoded.decode("utf-8"),
                                                         disallowed_special=())) * 1.1) + 4096,
            "reserved_input": openai_answer.reserved_input(encoded),
        })
    price_in, price_out = openai_answer.PRICES[top20_model_pilot.MODEL]
    worst = sum(2 * (r["reserved_input"] * price_in + MAX_OUTPUT * price_out)
                for r in requests)
    if worst > CAP_NANODOLLARS:
        raise ValueError("Conservative reservation exceeds proposed task cap")
    plan = {
        "version": "top20-low-reasoning-v1", "status": "offline proposal; not approved",
        "model": top20_model_pilot.MODEL, "reasoning_effort": "low",
        "max_output_tokens": MAX_OUTPUT, "pilot_queries": source["pilot_queries"],
        "requests": requests, "max_requests": MAX_REQUESTS,
        "primary": "Two averaged passes, scores_only, stable D46 ties, pin D46 rank1, "
                   "unchanged tail; compare with saved none/512 scores_only average.",
        "secondary": "Equal RRFc30 on both configurations, diagnostic only; no weight sweep "
                     "or choosing the better pass per query.",
        "screen": {"ndcg_delta": ">0.0106 and paired95% lower bound>0 versus "
                                  "saved scores_only/average",
                   "source_mrr_delta": ">=-0.02 versus D47",
                   "complete": "40 valid replies over20 queries;100% judged top10"},
        "stop": "Stop on first invalid, incomplete or unknown outcome; no retries, "
                "fallback, automatic output-cap increase or automatic daily-guard override. "
                "After the first two valid replies, check feasibility before continuing.",
        "cap_usd": CAP_NANODOLLARS / 1e9,
        "cost": {
            "worst_full_byte_reservation_usd": worst / 1e9,
            "scenario_usd_1024_output": sum(
                2 * (r["estimated_input"] * price_in + 1024 * price_out)
                for r in requests) / 1e9,
            "interpretation": "1024 output is a planning scenario, not a usage prediction. "
                              "Output includes hidden reasoning. No cache discount; "
                              "refinement only, excludes common upstream costs.",
        },
        "limitations": "Repeatedly analyzed pilot20, not confirmation. Reasoning and output "
                        "cap both change (none/512 -> low/4096); not a pure reasoning-effect "
                        "estimate.4096 is a deliberate budget constraint, below OpenAI's "
                        "general starting recommendation of25000; truncation is possible. "
                        "No post-hoc relaxation of gates or expansion on a failed screen.",
        "source_plan_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "evidence_sha256": hashes,
        "sources_checked_2026_11_05": [
            "https://developers.openai.com/api/docs/models/gpt-5.4",
            "https://developers.openai.com/api/docs/guides/reasoning",
        ],
        "provider_calls": False, "ledger_writes": False, "remaining80_scoring": False,
        "test_evaluation": False, "automatic_promotion": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", plan)
    return plan


def feasibility() -> dict:
    from arxiv_search.evaluate import answer_eval as ev

    plan = prepare()
    request = plan["requests"][0]
    q = request["query_id"]
    queries = {v["query_id"]: v for line in (config.EVAL_DIR / "queries.jsonl")
               .read_text(encoding="utf-8").splitlines() if (v := json.loads(line))}
    papers = {v["arxiv_id"]: v for line in
              (config.PROJECT_ROOT / "data" / "processed" / "corpus.jsonl")
              .read_text(encoding="utf-8").splitlines() if (v := json.loads(line))}
    encoded = payload(queries[q]["query"], request["presented_ids"], papers)
    if hashlib.sha256(encoded).hexdigest() != request["payload_sha256"]:
        raise ValueError("Feasibility payload differs from frozen plan")
    root = OUT / "feasibility"
    root.mkdir(parents=True, exist_ok=True)
    freeze(root / "approval.json", {
        "date": "2026-11-05", "cap_usd": 0.35, "max_requests": 2,
        "query_id": q, "passes": [1, 2],
        "authority": "Owner approved two-call feasibility check, then explicitly approved "
                     "process-only large daily guard450000. Full pilot not approved.",
        "process_large_daily_guard": 450_000,
        "plan_sha256": hashlib.sha256((OUT / "preregistration.json").read_bytes()).hexdigest(),
    })
    ledger = openai_answer.TaskLedger("top20-low-reasoning-feasibility-v1", 350_000_000, 2)
    previous = config.OPENAI_TOKEN_LIMITS["large"]
    try:
        config.OPENAI_TOKEN_LIMITS["large"] = 450_000
        rows = []
        for n in (1, 2):
            key = openai_rerank.repeat_key(encoded, n)
            path = root / f"{q}-pass{n}.json"
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
                raise openai_api.OpenAIError("Cached failure; stop without retry")
            openai_rerank.validate_refine_scores(
                {k: v for k, v in saved["outcome"].items() if k != "status"})
            rows.append({"query_id": q, "pass": n, "usage": saved["usage"]})
            print(f"Feasibility pass{n} saved; ${ledger.summary()['accounted_usd']:.6f}",
                  flush=True)
        report = {"status": "two valid replies; feasibility only, no quality evaluation",
                  "accounting": ledger.summary(), "rows": rows,
                  "full_pilot_approved": False, "remaining80_scoring": False}
        ev._write(root / "report.json", report)
        return report
    except openai_api.OpenAIError as error:
        ev._write(root / "stopped.json", {"status": "stopped", "detail": str(error),
                                        "accounting": ledger.summary(), "no_retry": True})
        raise
    finally:
        config.OPENAI_TOKEN_LIMITS["large"] = previous


def execute() -> dict:
    from arxiv_search.evaluate import answer_eval as ev, metrics, top20_ablations as ab

    plan = prepare()
    freeze(OUT / "continuation-approval.json", {
        "date": "2026-11-05", "cap_usd": 1.25, "max_new_requests": 38,
        "reuse": "First query's two saved feasibility replies; never resend.",
        "process_large_daily_guard": 750_000,
        "authority": "Owner explicitly approved remaining38 calls with $1.25 cap "
                     "and process-only daily guard750000. No retries or remaining80.",
        "plan_sha256": hashlib.sha256((OUT / "preregistration.json").read_bytes()).hexdigest(),
    })
    queries = {v["query_id"]: v for line in (config.EVAL_DIR / "queries.jsonl")
               .read_text(encoding="utf-8").splitlines() if (v := json.loads(line))}
    papers = {v["arxiv_id"]: v for line in
              (config.PROJECT_ROOT / "data" / "processed" / "corpus.jsonl")
              .read_text(encoding="utf-8").splitlines() if (v := json.loads(line))}
    base = json.loads((config.RESULTS_DIR / "llm-score-pass2" /
                      "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json").read_bytes())
    d47 = json.loads((config.RESULTS_DIR / "llm-score-refine-pin" /
                     "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json").read_bytes())
    labels = json.loads((config.RESULTS_DIR / "top20-label-completion" / "labels.json")
                        .read_bytes())["labels"]
    ledger = openai_answer.TaskLedger("top20-low-reasoning-remaining38-v1", 1_250_000_000, 38)
    previous = config.OPENAI_TOKEN_LIMITS["large"]
    rows = []
    provenance = {}
    try:
        config.OPENAI_TOKEN_LIMITS["large"] = 750_000
        for index, request in enumerate(plan["requests"]):
            q, presented = request["query_id"], request["presented_ids"]
            encoded = payload(queries[q]["query"], presented, papers)
            if hashlib.sha256(encoded).hexdigest() != request["payload_sha256"]:
                raise ValueError("Request differs from frozen plan")
            replies, usages, reference_replies = [], [], []
            for n in (1, 2):
                root = OUT / ("feasibility" if index == 0 else "responses")
                path = root / f"{q}-pass{n}.json"
                key = openai_rerank.repeat_key(encoded, n)
                saved = ev._read(path, encoded)
                if saved is None:
                    if index == 0:
                        raise ValueError("Required feasibility reply missing; never resend")
                    if ledger.attempted(key):
                        raise openai_api.OpenAIError("Attempt without cached outcome; no retry")
                    try:
                        value, usage = openai_answer.call_once(
                            encoded, ledger, validate=openai_rerank.validate_refine_scores,
                            attempt_key=key, failure_path=path.with_suffix(".failure.json"))
                    except openai_answer.InvalidAnswer as error:
                        ev._write(path, {"request_sha256": openai_answer.request_key(encoded),
                                         "outcome": {"status": error.status,
                                                     "detail": error.detail},
                                         "usage": ledger.attempt(key)})
                        raise
                    saved = {"request_sha256": openai_answer.request_key(encoded),
                             "outcome": {"status": "ok", **value}, "usage": usage}
                    ev._write(path, saved)
                if saved["outcome"]["status"] != "ok":
                    raise openai_api.OpenAIError("Saved failure; stop without retry")
                replies.append(openai_rerank.validate_refine_scores(
                    {k: v for k, v in saved["outcome"].items() if k != "status"}))
                usages.append(saved["usage"])
                provenance[str(path.relative_to(OUT))] = hashlib.sha256(path.read_bytes()).hexdigest()
                old_request = top20_model_pilot.payload(queries[q]["query"], presented, papers)
                old_path = top20_model_pilot.OUT / "responses" / f"{q}-pass{n}.json"
                old = ev._read(old_path, old_request)
                if old is None or old["outcome"]["status"] != "ok":
                    raise ValueError("Saved non-reasoning reference missing or failed")
                reference_replies.append({k: v for k, v in old["outcome"].items() if k != "status"})
                provenance[f"reference/{old_path.name}"] = hashlib.sha256(
                    old_path.read_bytes()).hexdigest()
                print(f"{q} pass{n} saved/reused; new task "
                      f"${ledger.summary()['accounted_usd']:.6f}", flush=True)
            source = {queries[q]["source_arxiv_id"]: 2}
            for method in ("scores_only", "equal_rrf"):
                ranked = ab.ranking(base[q], presented, replies, method, "average")
                reference = ab.ranking(base[q], presented, reference_replies, method, "average")
                rows.append({
                    "query_id": q, "query_type": queries[q]["query_type"], "method": method,
                    "candidate": metrics.ndcg_at_k(ranked, labels[q]),
                    "reference": metrics.ndcg_at_k(reference, labels[q]),
                    "d47": metrics.ndcg_at_k(d47[q], labels[q]),
                    "source_delta_vs_d47": metrics.reciprocal_rank(ranked, source)
                                           - metrics.reciprocal_rank(d47[q], source),
                    "fully_judged": metrics.judged_at_k(ranked, labels[q]) == 1,
                    "top20": ranked[:20], "usage": usages,
                })
        summary = {}
        for method in ("scores_only", "equal_rrf"):
            subset = [r for r in rows if r["method"] == method]
            delta, low, high = metrics.paired_diff_ci([r["reference"] for r in subset],
                                                     [r["candidate"] for r in subset])
            diffs = [r["candidate"] - r["reference"] for r in subset]
            mrr = statistics.fmean(r["source_delta_vs_d47"] for r in subset)
            checks = {"ndcg": delta > 0.0106 and low > 0,
                      "source_mrr": mrr >= -0.02,
                      "complete": len(subset) == 20,
                      "fully_judged": all(r["fully_judged"] for r in subset)}
            summary[method] = {
                "candidate_ndcg": statistics.fmean(r["candidate"] for r in subset),
                "reference_ndcg": statistics.fmean(r["reference"] for r in subset),
                "d47_ndcg": statistics.fmean(r["d47"] for r in subset),
                "delta": delta, "ci95": [low, high], "source_mrr_delta_vs_d47": mrr,
                "wins_losses_ties": [sum(d > 1e-12 for d in diffs),
                                     sum(d < -1e-12 for d in diffs),
                                     sum(abs(d) <= 1e-12 for d in diffs)],
                "checks": checks, "screen_pass": all(checks.values()),
                "query_types": {t: statistics.fmean(r["candidate"] - r["reference"]
                                for r in subset if r["query_type"] == t)
                                for t in sorted({r["query_type"] for r in subset})},
            }
        primary = [r for r in rows if r["method"] == "scores_only"]
        usages = [u for r in primary for u in r["usage"]]
        report = {
            "summary": summary, "primary": "scores_only", "accounting": ledger.summary(),
            "total40_cost_usd": sum(openai_answer.cost_nanodollars(
                plan["model"], u["input_tokens"], u["output_tokens"]) for u in usages) / 1e9,
            "mean_max_of_two_api_seconds": statistics.fmean(
                max(u["latency_seconds"] for u in r["usage"]) for r in primary),
            "output_tokens": sum(u["output_tokens"] for u in usages),
            "reasoning_tokens": sum(u["reasoning_tokens"] for u in usages),
            "provenance": provenance, "rows": rows,
            "limitations": "Exploratory repeatedly analyzed pilot20; output cap also changed. "
                            "Sequential calls; max duration is hypothetical parallel latency. "
                            "No remaining80 scoring, test evaluation or promotion.",
        }
        ev._write(OUT / "report.json", report)
        return report
    except (openai_api.OpenAIError, ValueError) as error:
        ev._write(OUT / "continuation-stopped.json", {
            "status": "stopped", "detail": str(error), "accounting": ledger.summary(),
            "completed_query_method_rows": len(rows), "no_retry": True})
        raise
    finally:
        config.OPENAI_TOKEN_LIMITS["large"] = previous


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feasibility", action="store_true",
                        help="Run only the owner-approved two-call $0.35 check")
    parser.add_argument("--run", action="store_true",
                        help="Run only the owner-approved remaining38 calls, $1.25 cap")
    args = parser.parse_args()
    if args.feasibility and args.run:
        parser.error("Choose either feasibility or remaining38, not both")
    if args.run:
        result = execute()
        print(json.dumps({k: v for k, v in result.items()
                          if k not in ("rows", "provenance")}, indent=2))
    elif args.feasibility:
        print(json.dumps(feasibility(), indent=2))
    else:
        result = prepare()
        print(json.dumps({"status": result["status"], "cost": result["cost"],
                          "cap_usd": result["cap_usd"]}, indent=2))
