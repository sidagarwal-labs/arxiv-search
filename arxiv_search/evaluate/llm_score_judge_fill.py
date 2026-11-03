"""Grade the fixed-key v2 pilot's missing top10 pairs with the frozen OpenAI judge.

The v2 top50 arm put 34 never-graded papers into its top10, so its nDCG/P10 were
withheld. This step sends exactly those pairs to the same judge, rubric, prompt,
shuffle and batching behind every existing label, then rescores all three pilot
systems against one child label snapshot.

Safety rules (preflight by default; --run sends requests):
- only the recomputed missing pairs, minus human-graded pairs and cached grades;
- one HTTP attempt per call and no validation retries: any failure stops the run;
- a task dollar ceiling: before each call, spent-so-far plus that call's worst case must fit;
- existing grades, the v2 artifacts and the leaderboard snapshot are never modified.

The judge and the reranker share a model family, so these grades are not an
independent check of the reranker.
"""

from __future__ import annotations

import argparse
import hashlib
import json

import tiktoken

from arxiv_search import config, openai_rerank as client
from arxiv_search.evaluate import fusion_experiment as fusion, judge, judge_prompts
from arxiv_search.evaluate import llm_reranker_pilot as v1, llm_score_pilot as score
from arxiv_search.evaluate import results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.judge_pilot import SHEET_PATH, read_human_grades

OUT = score.OUT / "judge-fill"
VERSION = "judge-fill-v1"
TASK_CAP_USD = 0.05
OUTPUT_TOKENS_PER_PAPER = 50  # largest observed mean per call across 474 earlier judge calls
RETRY_MARKER = "Your previous response failed validation"


def system_names() -> list[str]:
    return [v1.BASELINE, *(score.system_name(d) for d in v1.DEPTHS)]


def missing_pairs(runs: dict, labels: dict, qids: list[str]) -> dict[str, list[str]]:
    """query_id -> sorted top10 papers from any run that have no frozen grade."""
    return {q: sorted({p for run in runs.values() for p in run.get(q, [])[:10]} - set(labels[q]))
            for q in qids}


def child_labels(parent: dict, new: dict) -> dict:
    """Add grades for new pairs; refuse to change any parent grade."""
    out = {q: dict(grades) for q, grades in parent.items()}
    for q, grades in new.items():
        for p, grade in grades.items():
            if grade not in (0, 1, 2):
                raise ValueError(f"{q}/{p}: invalid grade {grade!r}")
            if p in out[q] and out[q][p] != grade:
                raise ValueError(f"{q}/{p}: would change a frozen grade")
            out[q][p] = grade
    return out


def no_retry(call: judge.CallFn) -> judge.CallFn:
    """Stop instead of letting judge_query re-ask after an invalid answer."""
    def guarded(prompt: str):
        if RETRY_MARKER in prompt:
            raise RuntimeError("Judge answer failed validation; stopped without retry")
        return call(prompt)
    return guarded


def estimate(calls: list[tuple[str, list[dict]]], queries: dict) -> dict:
    tokenizer = tiktoken.get_encoding("o200k_base")
    system = len(tokenizer.encode(judge_prompts.SYSTEM_INSTRUCTION))
    rows, worst = [], 0
    for qid, batch in calls:
        _, _, prompt = judge.presentation(queries[qid], batch)
        tokens = system + len(tokenizer.encode(prompt))
        # The client reserves payload bytes (an upper bound on tokens) + overhead + full output
        # cap; the extra 4096 covers the JSON schema and escaping we do not rebuild here.
        reserve = (len((judge_prompts.SYSTEM_INSTRUCTION + prompt).encode("utf-8"))
                   + 4096 + config.OPENAI_INPUT_OVERHEAD_TOKENS + config.OPENAI_MAX_OUTPUT_TOKENS)
        worst = max(worst, reserve)
        rows.append({"query_id": qid, "papers": [p["arxiv_id"] for p in batch],
                     "input_token_estimate": tokens, "max_reservation_tokens": reserve})
    tokens_in = sum(r["input_token_estimate"] for r in rows)
    papers = sum(len(r["papers"]) for r in rows)
    expected_out = papers * OUTPUT_TOKENS_PER_PAPER
    worst_out = len(rows) * config.OPENAI_MAX_OUTPUT_TOKENS
    return {
        "calls": len(rows), "papers": papers, "requests": rows,
        "input_token_estimate": tokens_in,
        "expected_tokens": round(tokens_in * 1.1) + expected_out,
        "expected_usd": (tokens_in * 1.1 * client.INPUT_PRICE + expected_out * client.OUTPUT_PRICE) / 1e9,
        "worst_case_usd": (tokens_in * 1.1 * client.INPUT_PRICE + worst_out * client.OUTPUT_PRICE) / 1e9,
        "max_single_reservation_tokens": worst,
    }


def shared_remaining() -> int:
    ledger = client.PilotLedger(version=score.VERSION)
    limit = int(config.OPENAI_TOKEN_LIMITS["mini"] * config.OPENAI_BUDGET_FRACTION)
    return limit - ledger.summary()["shared_accounted_tokens"]


def prepare() -> dict:
    papers, queries, split = judge.load_inputs()
    v2 = json.loads((score.OUT / "report.json").read_text(encoding="utf-8"))
    qids = v2["query_ids"]
    if set(qids) - set(split["dev"]):
        raise ValueError("Pilot queries must all be dev queries")
    runs = {n: json.loads((score.OUT / f"{n}.run.json").read_text(encoding="utf-8"))
            for n in system_names()}
    _, label_bytes, full, _ = catalog.load_snapshot(config.RESULTS_DIR)
    provenance = json.loads((score.OUT / "input-provenance.json").read_text(encoding="utf-8"))
    if hashlib.sha256(label_bytes).hexdigest() != provenance["full_labels_bytes_sha256"]:
        raise ValueError("Parent label snapshot changed since the v2 pilot")
    if full["rubric_version"] != judge.RUBRIC_VERSION:
        raise ValueError("Judge rubric changed since the frozen snapshot")
    if full["human_workbook_sha256"] != hashlib.sha256(SHEET_PATH.read_bytes()).hexdigest():
        raise ValueError("Human workbook changed since the frozen snapshot")
    parent = {q: full["labels"][q] for q in qids}
    missing = missing_pairs(runs, parent, qids)
    if missing != v2["missing"]:
        raise ValueError("Recomputed missing pairs differ from the published v2 report")
    human = read_human_grades()
    to_judge = {q: [p for p in ps if (q, p) not in human] for q, ps in missing.items() if ps}
    judge_key = full["judge"]
    calls = judge.batches(judge_key, to_judge, queries, papers, judge.load_judgments(judge_key))
    plan = {
        "version": VERSION, "judge": judge_key, "judge_model": config.JUDGES[judge_key]["model"],
        "rubric_version": judge.RUBRIC_VERSION, "query_ids": qids,
        "parent_labels_bytes_sha256": provenance["full_labels_bytes_sha256"],
        "missing_pairs": sum(map(len, missing.values())), "missing": missing,
        "human_graded_pairs": sum(1 for q, ps in missing.items() for p in ps if (q, p) in human),
        "scope": "Only the v2 pilot's missing top10 pairs; 20 dev queries; no held-out queries.",
        "execution": "Same judge prompt, shuffle and batching as all frozen labels. One HTTP "
                     "attempt per call, no validation retries, stop on the first failure.",
        "evaluation": "Rescore baseline, top10 and top50 against one child snapshot; IDCG may change.",
        "task_cap_usd": TASK_CAP_USD, "automatic_promotion": False,
    }
    return {"papers": papers, "queries": queries, "qids": qids, "runs": runs, "full": full,
            "parent": parent, "missing": missing, "human": human, "judge_key": judge_key,
            "calls": calls, "plan": plan}


def call_worst_usd(request: dict) -> float:
    return (request["input_token_estimate"] * 1.1 * client.INPUT_PRICE
            + config.OPENAI_MAX_OUTPUT_TOKENS * client.OUTPUT_PRICE) / 1e9


def run_calls(state: dict, call: judge.CallFn | None = None, planned: list[dict] | None = None,
              cap_usd: float = TASK_CAP_USD) -> dict:
    """Send the planned calls with HTTP and validation retries disabled.

    Before each call, spent-so-far plus that call's worst case must fit the task ceiling.
    """
    previous = config.OPENAI_MAX_ATTEMPTS
    config.OPENAI_MAX_ATTEMPTS = 1
    try:
        guarded = no_retry(call or judge.default_call(state["judge_key"]))
        path = judge.cache_path(state["judge_key"])
        rows, spent = [], 0.0
        for i, (qid, batch) in enumerate(state["calls"]):
            if planned is not None and spent + call_worst_usd(planned[i]) > cap_usd:
                raise RuntimeError(f"Next call could exceed ${cap_usd:.2f}; stopped before sending")
            print(f"  {qid}: judging {len(batch)} papers", flush=True)
            new = judge.judge_query(state["judge_key"], state["queries"][qid], batch, guarded)
            for row in new:
                judge.append_jsonl(path, row)  # saved immediately, like judge_pairs
            rows += new
            usage = new[0]["usage"] or {}
            spent += (usage.get("input_tokens", 0) * client.INPUT_PRICE
                      + usage.get("output_tokens", 0) * client.OUTPUT_PRICE) / 1e9
        return {"calls": len(state["calls"]), "rows": rows, "usd": spent}
    finally:
        config.OPENAI_MAX_ATTEMPTS = previous


def publish(state: dict, sent: dict | None) -> dict:
    qids, queries, papers, runs = state["qids"], state["queries"], state["papers"], state["runs"]
    pairs = {q: ps for q, ps in state["missing"].items() if ps}
    new = judge.grades_for(state["judge_key"], pairs, queries, papers)
    for (q, p), grade in state["human"].items():
        if p in pairs.get(q, []):
            new.setdefault(q, {})[p] = grade
    labels = child_labels(state["parent"], new)
    still_missing = missing_pairs(runs, labels, qids)
    snapshot = {
        "parent_labels_bytes_sha256": state["plan"]["parent_labels_bytes_sha256"],
        "judge": state["judge_key"], "rubric_version": judge.RUBRIC_VERSION,
        "query_ids": qids, "labels": labels,
        "added_pairs": sum(map(len, new.values())),
        "complete_for_pilot_top10": not any(still_missing.values()),
    }
    result = score.compare(runs, v1.BASELINE, snapshot, papers, queries, qids)
    cached = judge.load_judgments(state["judge_key"])
    details = []
    for q, ps in pairs.items():
        for p in ps:
            row = cached.get(judge.pair_key(state["judge_key"], queries[q]["query"], papers[p]))
            details.append({
                "query_id": q, "query_type": queries[q]["query_type"], "query": queries[q]["query"],
                "arxiv_id": p, "title": papers[p]["title"], "grade": labels[q].get(p),
                "source": "human" if (q, p) in state["human"] else ("judge" if row else "missing"),
                "reason": row["reason"] if row else None,
                "ranks": {n: (r[q].index(p) + 1 if p in r[q] else None) for n, r in runs.items()},
            })
    usage = {}
    for row in (sent or {}).get("rows", []):
        usage[row["usage"]["request_id"]] = row["usage"]
    accounting = {
        "calls": len(usage),
        "input_tokens": sum(u["input_tokens"] for u in usage.values()),
        "output_tokens": sum(u["output_tokens"] for u in usage.values()),
        "reasoning_tokens": sum(u["reasoning_tokens"] for u in usage.values()),
        "accounted_tokens": sum(u["accounted_tokens"] for u in usage.values()),
    }
    accounting["usd"] = (accounting["input_tokens"] * client.INPUT_PRICE
                         + accounting["output_tokens"] * client.OUTPUT_PRICE) / 1e9
    report = {
        **{k: state["plan"][k] for k in ("version", "judge", "judge_model", "rubric_version",
                                         "query_ids", "missing_pairs", "human_graded_pairs")},
        "added_pairs": snapshot["added_pairs"], "still_missing": still_missing,
        "grade_counts": {g: sum(d["grade"] == g for d in details) for g in (0, 1, 2)},
        "primary": result, "pairs": details, "accounting": accounting, "promoted": False,
    }
    fusion._write_json(OUT / "labels.json", snapshot)
    fusion._write_json(OUT / "report.json", report)
    write_markdown(report)
    return report


def write_markdown(report: dict) -> None:
    primary = report["primary"]
    lines = [
        "# Fixed-key v2 pilot: missing judgments filled", "",
        f"Judge `{report['judge']}` (`{report['judge_model']}`), rubric `{report['rubric_version']}`; "
        "same prompt, shuffle and batching as all frozen labels. One HTTP attempt per call, no "
        "validation retries. Existing grades unchanged; leaderboard snapshot untouched.", "",
        f"Missing pairs: **{report['missing_pairs']}** (human-graded: {report['human_graded_pairs']}); "
        f"grades added: **{report['added_pairs']}**; grade counts 0/1/2: "
        + "/".join(str(report["grade_counts"][g]) for g in (0, 1, 2)) + ".", "",
        "| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |",
        "|---|---|---|---|---|---|---|"]
    for n, result in primary["systems"].items():
        vals = [("withheld" if f in ("ndcg@10", "precision@10") and not result["top10_fully_judged"]
                 else f"{result['all'][f]['mean']:.4f}")
                for f in ("ndcg@10", "precision@10", "judged@10", "source_mrr@10",
                          "source_recall@10", "source_recall@20")]
        lines.append(f"| `{n}` | " + " | ".join(vals) + " |")
    lines += ["", "## Paired versus baseline (same 20 queries, same child labels)", "",
              "| Arm | nDCG10 delta [95% CI] | P10 delta [95% CI] | Wins/losses/ties |", "|---|---|---|---|"]
    for depth in v1.DEPTHS:
        name = score.system_name(depth)
        vals = []
        for field in ("ndcg@10", "precision@10"):
            paired = primary["summary"].get(name, {}).get("all", {}).get(field, {}).get("paired_vs_working")
            vals.append("withheld" if paired is None else
                        f"{paired['difference']:+.4f} [{paired['ci95'][0]:+.4f},{paired['ci95'][1]:+.4f}]")
        paired = primary["summary"].get(name, {}).get("all", {}).get("ndcg@10", {}).get("paired_vs_working")
        if paired is None:
            record = "withheld"
        else:
            diffs = paired["per_query_difference"].values()
            record = (f"{sum(d > 1e-12 for d in diffs)}/{sum(d < -1e-12 for d in diffs)}/"
                      f"{sum(abs(d) <= 1e-12 for d in diffs)}")
        lines.append(f"| top{depth} | " + " | ".join(vals) + f" | {record} |")
    lines += ["", "## Segment nDCG10", "", "| System | " + " | ".join(catalog.QUERY_TYPES) + " |",
              "|---|" + "---|" * len(catalog.QUERY_TYPES)]
    for n, result in primary["systems"].items():
        cells = []
        for kind in catalog.QUERY_TYPES:
            group = result["by_query_type"].get(kind)
            cells.append("n/a" if group is None else f"{group['ndcg@10']['mean']:.4f}")
        lines.append(f"| `{n}` | " + " | ".join(cells) + " |")
    lines += ["", "## New grades", "",
              "| Query | Type | Paper | Grade | Rank in top10 arm | Rank in top50 arm |",
              "|---|---|---|---|---|---|"]
    for d in sorted(report["pairs"], key=lambda d: (d["query_id"], d["arxiv_id"])):
        ranks = [d["ranks"].get(score.system_name(k)) for k in v1.DEPTHS]
        lines.append(f"| {d['query_id']} | {d['query_type']} | {d['title'][:70]} | {d['grade']} | "
                     + " | ".join("-" if r is None else str(r) for r in ranks) + " |")
    a = report["accounting"]
    lines += ["", "## Accounting", "",
              f"- Paid judge calls: {a['calls']}; input/output/reasoning tokens "
              f"{a['input_tokens']:,}/{a['output_tokens']:,}/{a['reasoning_tokens']:,}; "
              f"ledger-accounted {a['accounted_tokens']:,}; cost ${a['usd']:.6f} "
              f"(task ceiling ${TASK_CAP_USD:.2f}).", "",
              "## Cautions", "",
              "- 20 previously examined dev queries; exploratory CIs; no promotion.",
              "- The judge and the reranker share a model family: possible same-family preference "
              "is not ruled out by these grades.",
              "- Adding grades can raise a query's ideal DCG, so baseline numbers can move too."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="send the planned judge calls")
    args = parser.parse_args(argv)
    state = prepare()
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", state["plan"])
    pre = {**estimate(state["calls"], state["queries"]), "shared_remaining_tokens": shared_remaining(),
           "task_cap_usd": TASK_CAP_USD}
    preflight_path = OUT / "preflight.json"
    if pre["calls"] or not preflight_path.exists():  # keep the record of the paid run's plan
        fusion._write_json(preflight_path, pre)
    print(json.dumps({k: v for k, v in pre.items() if k != "requests"}, indent=2), flush=True)
    if not args.run:
        return
    if pre["expected_usd"] > TASK_CAP_USD:
        raise ValueError("Expected cost exceeds the task ceiling; no request sent")
    # Calls are sequential and each reservation settles to actual usage before the next one.
    if pre["expected_tokens"] + pre["max_single_reservation_tokens"] > pre["shared_remaining_tokens"]:
        raise ValueError("Expected usage plus one peak reservation exceeds the shared allowance; "
                         "no request sent")
    sent = (run_calls(state, planned=pre["requests"]) if state["calls"]
            else {"calls": 0, "rows": []})
    usage_path = OUT / "accounting.json"
    if sent["rows"]:
        freeze(usage_path, {"rows": [{k: r[k] for k in ("query_id", "arxiv_id", "usage")}
                                     for r in sent["rows"]]})
    elif usage_path.exists():
        sent = {"rows": json.loads(usage_path.read_text(encoding="utf-8"))["rows"]}
    report = publish(state, sent)
    print(f"Added {report['added_pairs']} grades; still missing "
          f"{sum(map(len, report['still_missing'].values()))}; no promotion.")


if __name__ == "__main__":
    main()
