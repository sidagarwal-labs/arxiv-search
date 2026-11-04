"""Experiment D: a requirement (facet) checklist for the two-pass LLM reranker.

Loss analysis of the Decision46 reranker (findings section 32) found one dominant failure:
papers that match the query's main topic but miss a distinguishing requirement still get
high scores ("regional language social media" -> a regional *speech* corpus ranked first).
The prompt already says "check the constraints", but one holistic 0-4 score does not
enforce it.

Hypothesis: making the requirements explicit and checking every paper against them ranks
directly relevant papers above partial matches.

    1. One extraction call per query lists 1-4 required facets from the query text only.
    2. Each scoring pass sees that checklist and returns, per paper, the facet IDs its
       title/authors/abstract do not support plus the usual 0-4 score.
    3. Code (not the model) caps a paper with any unsupported facet at CAP=2
       ("useful partial answer"), averages the two passes and applies the unchanged
       safeguard (RRF c=30 with retrieval order).

One change versus the Decision46 reranking baseline: the scoring prompt/schema plus the
cap. Model, candidate pool, presentation order, two passes, averaging and safeguard are
unchanged. The uncapped scores from the same responses form a secondary system that
isolates the prompt from the cap.

Generalization guard: facets come from each query's own text at run time; one prompt and
one cap for every query type; no query IDs, source papers or labels are used in ranking;
CAP was fixed before any response was seen; the held-out queries are never touched.

Staged and approval-gated: preflight by default. `--stage pilot --run` sends the 20 pilot
queries (20 extraction + 40 scoring requests); `--stage full --run` sends the other 80 and
is refused unless the saved pilot gate passed. No retries; stop on the first failure.
`--judge` grades unjudged top10 pairs (judge cache first) before scoring.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics

import tiktoken

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, graded
from arxiv_search.evaluate import llm_score_blend as blend, llm_score_dev100 as dev
from arxiv_search.evaluate import llm_score_pass2 as pass2, llm_score_pilot as score
from arxiv_search.evaluate import llm_score_safeguard as guard, results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "llm-score-facets"
DEPTH = 50
CAP = 2
PASSES = (1, 2)
REFERENCE = pass2.AVG_SAFE  # Decision46 reranking baseline, frozen for this experiment
PRIMARY = f"llm-mini-facet-score+d={DEPTH}+cap={CAP}+avg2+rrf-baseline+c={guard.C}"
SECONDARY = f"llm-mini-facet-score+d={DEPTH}+avg2+rrf-baseline+c={guard.C}"  # same responses, no cap
SYSTEMS = (PRIMARY, SECONDARY)
LABEL_LAYER = catalog.SHARED_LABELS_D46
JUDGE_TASK_CAP_USD = 0.20
EXPECTED_FACET_OUTPUT = 40
EXPECTED_SCORE_OUTPUT = 800  # ~16 tokens per paper entry; plain scores averaged 318

PLAN = {
    "version": "facet-checklist-v1", "model": client.MODEL, "reasoning_effort": "none",
    "hypothesis": "An explicit per-query requirement checklist, with a code-enforced cap for "
                  "papers missing a requirement, ranks direct answers above partial topical "
                  "matches better than one holistic score.",
    "one_change": "Scoring prompt/schema adds the facet checklist and per-paper missing IDs; "
                  f"code caps papers with any missing facet at {CAP}. Everything else as Decision46.",
    "primary_system": PRIMARY, "secondary_system": SECONDARY, "reference": REFERENCE,
    "cap": CAP, "passes": len(PASSES), "depth": DEPTH, "safeguard_rrf_c": guard.C,
    "facets": f"1-{client.MAX_FACETS} per query, extracted once from query text only and "
              "shared by both scoring passes.",
    "labels": "shared-labels/labels-d46.json plus a child layer of judge-graded top10 fills "
              "(frozen judge, human overrides preserved).",
    "stages": {
        "pilot": "20 pilot dev queries: 20 extraction + 40 scoring requests.",
        "full": "Other 80 dev queries: 80 extraction + 160 scoring requests; only if the pilot "
                "gate passed and the user approved.",
    },
    "pilot_gate": {
        "all_responses_valid": True,
        "pilot20_ndcg@10_delta_vs_reference": "> 0 (primary or secondary system)",
        "pilot20_source_mrr@10": ">= reference - 0.02 for the same system",
        "note": "The pilot queries informed earlier designs and the loss analysis saw all 100 "
                "dev queries, so the gate is a sanity screen, not evidence.",
    },
    "qualifies_if": {
        "fully_judged_top10": True,
        "ndcg@10_delta_vs_reference": "> 0.0106 (conservative single-pass MDD of the safeguard; "
                                      "two-pass noise unmeasured) with paired 95% CI lower bound > 0",
        "source_mrr@10": ">= reference - 0.02",
        "consistency": "nDCG delta vs reference > 0 on both pilot20 and new80",
    },
    "diagnostics_not_gates": [
        "nDCG by query type (keyword expected to gain most)",
        "grade-0 papers in the top10",
        "facet count distribution and share of capped papers",
        "source paper flagged as missing a facet (evaluation-only proxy for extraction or "
        "checking errors; never used in ranking)",
    ],
    "multiple_comparisons": "Two systems from the same responses; a secondary-only qualifier is "
                            "reported as such and needs a fresh confirmation before promotion.",
    "cost": "Expected ~$0.80 pilot and ~$3.00 full (uncached prices; both passes of a query are "
            "sent back to back, so real billing may be lower from prompt caching). Judge <= $0.20.",
    "budget_usd": {"facets": client.FACET_TASK_CAP / 1e9,
                   "facet_scores": client.FACET_SCORE_TASK_CAP / 1e9,
                   "judge": JUDGE_TASK_CAP_USD},
    "automatic_retries": False, "held_out_queries_used": False, "automatic_promotion": False,
}


def prompt_hashes() -> dict:
    return {name: hashlib.sha256(text.encode()).hexdigest() for name, text in
            (("facet_system", client.FACET_SYSTEM), ("facet_score_system", client.FACET_SCORE_SYSTEM))}


def prepare() -> dict:
    if config.RERANK_BASELINE_SYSTEM != REFERENCE:
        raise ValueError("Reranking baseline changed; create a new experiment identity")
    state = pass2.prepare()  # validates the Decision46 inputs and cached passes
    for r in state["requests"]:
        r["facet_encoded"] = client.encode_facet_payload(state["queries"][r["query_id"]]["query"])
        r["facet_key"] = client.request_key(r["facet_encoded"])
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", {
        **PLAN, "prompt_sha256": prompt_hashes(),
        "pilot_query_ids": sorted(state["pilot"]),
        "facet_request_keys": {r["query_id"]: r["facet_key"] for r in state["requests"]}})
    return state


def stage_requests(state: dict, stage: str) -> list[dict]:
    if stage not in ("pilot", "full"):
        raise ValueError("Stage must be pilot or full")
    return [r for r in state["requests"] if r["pilot"] == (stage == "pilot")]


def _read(path, key: str, encoded: bytes, meta: dict, validate) -> object | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value.get("attempt_key") != key or value.get("model") != client.MODEL
            or value.get("request_sha256") != client.request_key(encoded)
            or any(value.get(k) != v for k, v in meta.items())
            or value.get("answer_sha256") != fusion.fingerprint(value.get("answer"))
            or value["usage"]["status"] != "completed"):
        raise ValueError(f"{path.name}: cache provenance mismatch")
    return validate(value["answer"])


def _call(path, key: str, encoded: bytes, size: int, ledger: client.PilotLedger, meta: dict,
          failure_dir=None) -> None:
    if ledger.attempted(key) is not None:
        raise api.OpenAIError("Already attempted without a valid cache; no retry")
    answer, usage = client.call_once(encoded, size, ledger, attempt_key=key,
                                     failure_output_path=(failure_dir or OUT / "failures") / f"{key}.json")
    value = {**meta, "attempt_key": key, "request_sha256": client.request_key(encoded),
             "model": client.MODEL, "answer": answer, "usage": usage,
             "answer_sha256": fusion.fingerprint(answer)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".tmp").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    path.with_suffix(".tmp").replace(path)


def facet_path(r: dict):
    return OUT / "facets" / f"{r['facet_key']}.json"


def read_facets(r: dict) -> list[str] | None:
    return _read(facet_path(r), r["facet_key"], r["facet_encoded"], {"query_id": r["query_id"]},
                 client.validate_facets)


def score_request(state: dict, r: dict) -> dict | None:
    """The scoring payload and per-pass ledger keys, once the query's facets exist."""
    facets = read_facets(r)
    if facets is None:
        return None
    encoded = client.encode_facet_score_payload(
        state["queries"][r["query_id"]]["query"], facets, r["presented_ids"], state["papers"])
    return {"encoded": encoded, "facets": facets,
            "keys": {p: client.repeat_key(encoded, p) for p in PASSES}}


def read_pass(r: dict, req: dict, p: int) -> dict | None:
    key = req["keys"][p]
    return _read(OUT / "responses" / f"{key}.json", key, req["encoded"], pass_meta(r, req, p),
                 lambda a: client.validate_facet_scores(a, len(r["presented_ids"]), len(req["facets"])))


def pass_meta(r: dict, req: dict, p: int) -> dict:
    return {"query_id": r["query_id"], "pass": p, "presented_ids": r["presented_ids"],
            "facets": req["facets"]}


def placeholder_payload(state: dict, r: dict) -> bytes:
    """Worst-case scoring payload before facets exist: the maximum number of long facets."""
    return client.encode_facet_score_payload(
        state["queries"][r["query_id"]]["query"],
        [f"placeholder requirement {i} " + "word " * 10 for i in range(client.MAX_FACETS)],
        r["presented_ids"], state["papers"])


def preflight(state: dict, stage: str, facet_ledger: client.PilotLedger,
              score_ledger: client.PilotLedger) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    facet_todo, score_todo, blocked = [], [], []
    for r in stage_requests(state, stage):
        req = score_request(state, r)
        if req is None:
            (blocked if facet_ledger.attempted(r["facet_key"]) else facet_todo).append(r)
            score_todo += [placeholder_payload(state, r)] * len(PASSES)
            continue
        for p in PASSES:
            if read_pass(r, req, p) is None:
                if score_ledger.attempted(req["keys"][p]):
                    blocked.append(r)
                else:
                    score_todo.append(req["encoded"])
    facet_tokens = sum(len(tokenizer.encode(r["facet_encoded"].decode("utf-8"))) for r in facet_todo)
    score_tokens = sum(len(tokenizer.encode(e.decode("utf-8"))) for e in score_todo)
    usd = lambda tokens, n, out: (tokens * 1.1 * client.INPUT_PRICE + n * out * client.OUTPUT_PRICE) / 1e9
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    largest = max((client.reserved_input(e) for e in score_todo), default=0) + client.FACET_SCORE_MAX_OUTPUT
    return {
        "stage": stage, "facet_requests": len(facet_todo), "score_requests": len(score_todo),
        "attempted_uncached_no_retry": len(blocked),
        "expected_tokens": round((facet_tokens + score_tokens) * 1.1)
                           + len(facet_todo) * EXPECTED_FACET_OUTPUT
                           + len(score_todo) * EXPECTED_SCORE_OUTPUT,
        "expected_usd": usd(facet_tokens, len(facet_todo), EXPECTED_FACET_OUTPUT)
                        + usd(score_tokens, len(score_todo), EXPECTED_SCORE_OUTPUT),
        "worst_case_usd": usd(facet_tokens, len(facet_todo), client.FACET_MAX_OUTPUT)
                          + usd(score_tokens, len(score_todo), client.FACET_SCORE_MAX_OUTPUT),
        "max_single_reservation_tokens": largest,
        "facet_spent_usd": facet_ledger.summary()["accounted_usd"],
        "score_spent_usd": score_ledger.summary()["accounted_usd"],
        "score_cap_usd": client.FACET_SCORE_TASK_CAP / 1e9,
        "facet_cap_usd": client.FACET_TASK_CAP / 1e9,
        "shared_remaining_tokens_today": limit - score_ledger.summary()["shared_accounted_tokens"],
    }


def run_stage(state: dict, stage: str, facet_ledger: client.PilotLedger,
              score_ledger: client.PilotLedger) -> None:
    """Per query: extraction, then both passes back to back (shared prompt prefix)."""
    for i, r in enumerate(stage_requests(state, stage)):
        try:
            if read_facets(r) is None:
                _call(facet_path(r), r["facet_key"], r["facet_encoded"], 0, facet_ledger,
                      {"query_id": r["query_id"]})
            req = score_request(state, r)
            for p in PASSES:
                if read_pass(r, req, p) is None:
                    _call(OUT / "responses" / f"{req['keys'][p]}.json", req["keys"][p],
                          req["encoded"], len(r["presented_ids"]), score_ledger,
                          pass_meta(r, req, p))
        except api.OpenAIError:
            print(f"STOPPED at {r['query_id']}; investigate before any further requests.", flush=True)
            raise
        if i == 0:
            print(f"Smoke query {r['query_id']} passed (extraction + {len(PASSES)} passes).", flush=True)


def adjusted(entry: dict, cap: int | None) -> float:
    return float(min(entry["score"], cap) if cap is not None and entry["missing"] else entry["score"])


def build(state: dict, qids: list[str]) -> tuple[dict, dict]:
    """Reference runs (cached Decision46 passes) plus both facet systems for `qids`."""
    reference = pass2.build(state, *pass2.pass_scores(state))[0]
    runs = {n: {q: reference[n][q] for q in qids} for n in (dev.v1.BASELINE, REFERENCE)}
    responses = {}
    for r in state["requests"]:
        q = r["query_id"]
        if q not in qids:
            continue
        req = score_request(state, r)
        answers = [read_pass(r, req, p) if req else None for p in PASSES]
        if any(a is None for a in answers):
            raise ValueError(f"{q}: facet responses missing; run this stage first")
        responses[q] = {"facets": req["facets"], "passes": answers, "presented": r["presented_ids"]}
        base = state["base"][q]
        for name, cap in ((PRIMARY, CAP), (SECONDARY, None)):
            avg = {pid: statistics.fmean(adjusted(a[f"P{i}"], cap) for a in answers)
                   for i, pid in enumerate(r["presented_ids"], 1)}
            runs.setdefault(name, {})[q] = guard.fuse(base, score.rerank_prefix(base, avg, DEPTH))
    for n, run in runs.items():
        fusion.validate_run(n, run, qids, state["papers"], exact_depth=100)
    return runs, responses


def diagnostics(state: dict, runs: dict, responses: dict, labels: dict) -> dict:
    qids = sorted(responses)
    entries = [(q, pid, a[f"P{i}"]) for q, x in responses.items() for a in x["passes"]
               for i, pid in enumerate(x["presented"], 1)]
    source_flags = [bool(e["missing"]) for q, pid, e in entries
                    if pid == state["queries"][q]["source_arxiv_id"]]
    return {
        "facet_counts": dict(collections.Counter(len(x["facets"]) for x in responses.values())),
        "facets": {q: responses[q]["facets"] for q in qids},
        "paper_passes": len(entries),
        "missing_any_share": sum(bool(e["missing"]) for *_, e in entries) / len(entries),
        "capped_share": sum(bool(e["missing"]) and e["score"] > CAP for *_, e in entries) / len(entries),
        "source_flagged_missing": {"flagged": sum(source_flags), "source_paper_passes": len(source_flags)},
        "grade0_in_top10": {n: sum(labels[q].get(p) == 0 for q in qids for p in run[q][:10])
                            for n, run in runs.items()},
    }


def verdicts(results: dict, scopes: tuple[str, ...], mdd: float | None,
             systems: tuple[str, ...] = SYSTEMS, reference: str = REFERENCE) -> dict:
    out = {}
    for n in systems:
        sub = {s: (results[s]["summary"][n]["all"]["ndcg@10"]["paired_vs_working"] or {}).get("difference")
               for s in scopes}
        mrr = {s: results[s]["systems"][n]["all"]["source_mrr@10"]["mean"]
               - results[s]["systems"][reference]["all"]["source_mrr@10"]["mean"] for s in scopes}
        if mdd is None:  # pilot gate
            checks = {"pilot20_ndcg_gain": (sub["pilot20"] or 0) > 0,
                      "pilot20_source_mrr": mrr["pilot20"] >= -0.02}
        else:
            full = results["all100"]
            paired = full["summary"][n]["all"]["ndcg@10"]["paired_vs_working"]
            checks = {
                "fully_judged_top10": full["systems"][n]["top10_fully_judged"],
                "ndcg_gain_beyond_noise": bool(paired) and paired["difference"] > mdd
                                          and paired["ci95"][0] > 0,
                "source_mrr": mrr["all100"] >= -0.02,
                "consistent_subsets": all((sub[s] or 0) > 0 for s in ("pilot20", "new80")),
            }
        out[n] = {"checks": checks, "passes": all(checks.values()), "ndcg_deltas": sub,
                  "source_mrr_deltas": mrr}
    return out


def evaluate(state: dict, stage: str, run_judge: bool) -> dict | None:
    pilot = sorted(state["pilot"])
    qids = pilot if stage == "pilot" else state["qids"]
    runs, responses = build(state, qids)
    _, _, shared, _ = catalog.load_shared_labels(config.RESULTS_DIR, LABEL_LAYER)
    scoped = {**state, "qids": qids}
    usage_path = OUT / "judge-accounting.json"
    prior = dev.judge_accounting(json.loads(usage_path.read_text(encoding="utf-8"))["rows"]) \
        if usage_path.exists() else {"usd": 0.0}
    remaining = JUDGE_TASK_CAP_USD - prior["usd"]  # one ceiling across both stages and restarts
    labels, rows = blend.fill_top10(scoped, runs, shared, OUT, remaining, run_judge,
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
    facet_ledger = client.PilotLedger(version=client.FACET_VERSION)
    score_ledger = client.PilotLedger(version=client.FACET_SCORE_VERSION)
    report = {
        "stage": stage, "plan": json.loads((OUT / "preregistration.json").read_text(encoding="utf-8")),
        "mdd": mdd, "results": results, "verdicts": verdicts(results, tuple(scopes), mdd),
        "diagnostics": diagnostics(state, runs, responses, labels),
        "accounting": {"facets": facet_ledger.summary(), "facet_scores": score_ledger.summary(),
                       "judge": dev.judge_accounting(rows) if rows else {}},
        "promoted": False,
    }
    name = "pilot-report" if stage == "pilot" else "report"
    if stage == "full":
        report["cost_per_query_usd"] = (report["accounting"]["facets"]["accounted_usd"]
                                        + report["accounting"]["facet_scores"]["accounted_usd"]) / len(qids)
        for n in SYSTEMS:  # full-dev runs only, so the leaderboard never sees a partial run
            fusion._write_json(OUT / f"{n}.run.json", runs[n])
    fusion._write_json(OUT / f"{name}.json", report)
    write_markdown(report, OUT / f"{name}.md")
    return report


def write_markdown(report: dict, path) -> None:
    stage, scopes = report["stage"], list(report["results"])
    main = "pilot20" if report["stage"] == "pilot" else "all100"
    full = report["results"][main]
    lines = [f"# Experiment D: requirement checklist reranker ({stage} stage)", "",
             f"Reference: `{REFERENCE}` (Decision46). Primary: cap {CAP} for papers missing a "
             "required facet; secondary: same responses, no cap."
             + (f" Noise threshold (MDD): {report['mdd']:.4f}." if report["mdd"] else
                " Pilot gate only: a sanity screen, not evidence."), "",
             "| System | nDCG@10 | " + " | ".join(f"{s} Δ" for s in scopes)
             + " | Source MRR@10 | R@1 | P@10 | Passes |", "|---|---|" + "---|" * len(scopes) + "---|---|---|---|"]
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
    src = d["source_flagged_missing"]
    lines += ["", "## Checklist diagnostics", "",
              f"- Facets per query: {dict(sorted(d['facet_counts'].items()))}.",
              f"- Paper-passes with any missing facet: {d['missing_any_share']:.1%}; capped "
              f"(score above {CAP} and a missing facet): {d['capped_share']:.1%}.",
              f"- Source paper flagged as missing a facet: {src['flagged']}/{src['source_paper_passes']} "
              "paper-passes (evaluation-only error proxy; the source should meet every requirement).",
              "- Grade-0 papers in the top10: " + ", ".join(
                  f"`{n}` {c}" for n, c in d["grade0_in_top10"].items()) + ".", "",
              "<details><summary>Extracted facets per query</summary>", "",
              *(f"- `{q}`: " + "; ".join(f) for q, f in d["facets"].items()), "", "</details>", ""]
    acc = report["accounting"]
    lines += ["## Cost", "",
              f"- Extraction: {acc['facets']['requests']} requests, ${acc['facets']['accounted_usd']:.4f}.",
              f"- Scoring: {acc['facet_scores']['requests']} requests, "
              f"${acc['facet_scores']['accounted_usd']:.4f} (uncached prices; caching may lower the bill).",
              f"- Judge: ${acc['judge'].get('usd', 0):.4f}.", "",
              "## Cautions", "",
              "- Dev only; the judge and reranker share a model family.",
              f"- Label overrides called \"human\" in the frozen plan are {config.REFERENCE_LABELER} "
              "reference grades (owner declaration, 2026-11-03); no labels here are human.",
              "- The loss analysis that motivated this experiment read dev queries.",
              "- Not promoted."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("pilot", "full"), required=True)
    parser.add_argument("--run", action="store_true", help="send this stage's requests")
    parser.add_argument("--judge", action="store_true", help="grade unjudged top10 pairs")
    args = parser.parse_args(argv)
    state = prepare()
    facet_ledger = client.PilotLedger(version=client.FACET_VERSION)
    score_ledger = client.PilotLedger(version=client.FACET_SCORE_VERSION)
    if args.stage == "full":
        gate = OUT / "pilot-report.json"
        if not gate.exists() or not any(v["passes"] for v in json.loads(
                gate.read_text(encoding="utf-8"))["verdicts"].values()):
            raise ValueError("The full stage requires a passed, saved pilot gate")
    pre = preflight(state, args.stage, facet_ledger, score_ledger)
    print(json.dumps(pre, indent=2), flush=True)
    if pre["attempted_uncached_no_retry"]:
        raise api.OpenAIError("A prior request has no valid cache; investigate before continuing")
    if pre["facet_requests"] or pre["score_requests"]:
        fusion._write_json(OUT / f"preflight-{args.stage}.json", pre)
        if not args.run:
            return
        if (pre["expected_usd"] > pre["score_cap_usd"] - pre["score_spent_usd"]
                or pre["facet_requests"] * 0.001 > pre["facet_cap_usd"] - pre["facet_spent_usd"]):
            raise api.BudgetExceeded("Expected cost exceeds the approved ceiling; no request sent")
        if pre["expected_tokens"] + pre["max_single_reservation_tokens"] > pre["shared_remaining_tokens_today"]:
            raise api.BudgetExceeded("Expected usage exceeds today's shared token allowance; no request sent")
        run_stage(state, args.stage, facet_ledger, score_ledger)
    report = evaluate(state, args.stage, args.judge)
    if report is not None:
        print(json.dumps({n: v["passes"] for n, v in report["verdicts"].items()}))


if __name__ == "__main__":
    main()
