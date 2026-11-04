"""Experiment L: can a citation-discipline prompt make GPT-6 Luna a qualifying AI-summary model?

Decision 48 chose GPT-5.4 mini (answer-v1). Luna is about 8x cheaper per answer but failed two
checks. Free diagnostics on the saved v1 answers (2026-11-04) found two causes, neither about
invented facts:
    * Format: 9 of Luna's 13 failures were a parser bug. GPT-6 models send a commentary-phase
      draft before the final_answer message, and the client expected exactly one message.
      Fixed in openai_answer (read the final_answer phase); 3 more ran out of output tokens.
    * Faithfulness: 81 of Luna's 82 unsupported sentences had no [n] of their own (the label
      sat in another sentence). The same pattern explains most unsupported sentences for every
      model (gpt-5.4 70/72, mini 56/63).

answer-v2 (arxiv_search.answer.SYSTEM_V2) asks for a label in every sentence about a paper,
cites the closest papers inside a not-a-direct-answer caveat, and allows 1,200 output tokens.
Luna and mini both run it on the same 125 answer-dev-v1 items and the same Decision46 top10,
so a gain can be attributed to the prompt rather than the model. The yardstick stays the
GPT-5.4 answer-v1 answers already graded by GPT-6.1 Terra.

Grading: the owner grades a blinded workbook (terra-v2.xlsx) with GPT-6.1 Terra in a chat
session. It mixes in ANCHORS answer-v1 answers Terra already graded, so the report can measure
whether the new session grades differently (drift).

    python -m arxiv_search.evaluate.answer_eval_v2                 # free: preflight
    python -m arxiv_search.evaluate.answer_eval_v2 --run           # paid: generate (approval)
    python -m arxiv_search.evaluate.answer_eval_v2 --export        # free: blinded workbook
    python -m arxiv_search.evaluate.answer_eval_v2 --import <filled.xlsx>
    python -m arxiv_search.evaluate.answer_eval_v2 --report
    python -m arxiv_search.evaluate.answer_eval_v2 --recheck       # free: contract B, provisional
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import tiktoken

from arxiv_search import answer, config, openai_answer as client, openai_api as api
from arxiv_search.evaluate import answer_eval as ev, answer_grade_sheets as sheets
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "answer-eval-v2"
CANDIDATES = ("luna", "mini")
REFERENCE = "gpt-5.4"  # best answer-v1 faithfulness: the fixed yardstick
INCUMBENT = "mini"  # Decision 48, answer-v1
CHALLENGER = "luna"
TASK, CAP_USD, MAX_REQUESTS = "answer-generate-v2", 1.50, 280  # 15 responses resent (lost locally)
ANCHORS_PER_MODEL = 20  # answer-v1 answers from REFERENCE and INCUMBENT re-graded blind
SHEET = sheets.SHEETS_DIR / "terra-v2.xlsx"
KEY_PATH = OUT / "grading-key.json"
SALT = "answer-v2"
DRIFT_LIMIT = 0.05

PLAN = {
    "version": "answer-eval-l1", "date": "2026-11-04",
    "question": "Does answer-v2 make GPT-6 Luna qualify under Decision 48's rule, so it can replace "
                "GPT-5.4 mini as the cheaper AI-summary model?",
    "prompt": answer.VERSION_V2, "candidates": {k: client.MODELS[k] for k in CANDIDATES},
    "reasoning_effort": "none", "evaluation_set": "answer-dev-v1, full stage (125 items), same "
                                                  "Decision46 top10 evidence as Decision 48",
    "parser": "final_answer phase only when a reply has phased messages (bug fix, model-general)",
    "yardstick": f"{REFERENCE} answer-v1 answers and their GPT-6.1 Terra grades (unchanged)",
    "grader": "GPT-6.1 Terra via the owner's chat session (terra-v2.xlsx), same rubric and caveat "
              f"column; {ANCHORS_PER_MODEL} answer-v1 answers each from {REFERENCE} and {INCUMBENT} "
              "mixed in blind to measure drift",
    "decision_rule": {
        "qualifies_if": "the answer-eval-v2 rule unchanged: faithfulness and citation precision "
                        "95% CI lower bound of (candidate - yardstick) >= -0.05; abstain accuracy "
                        "(v2) >= 0.80; false abstain (v2) <= 0.10; format valid >= 0.95",
        "replace": f"{CHALLENGER} with answer-v2 replaces {INCUMBENT} answer-v1 if it qualifies and "
                   "costs less per answer",
        "drift_guard": f"if the anchors' mean faithfulness moves by more than {DRIFT_LIMIT} between "
                       "Terra sessions, report only (no replacement)",
        "mini_v2": "diagnostic only: whether the prompt helps a model that already qualifies; "
                   "switching mini's prompt would need its own decision",
    },
    "caveats": "Prompt written after reading answer-v1 failures on these dev items; the rules are "
               "general (cite every sentence) but a pass is optimistic until confirmed on "
               "held-out queries.",
    "retries": "none", "held_out_queries_used": False, "budget_usd": CAP_USD,
}

# Free, post-hoc recheck (approved 2026-11-04). All 15 answer-v2 format failures were abstain
# items that said "none of these answer it; the closest are [n]" with grounded=false, which
# contract A rejects. Contract B keeps the saved answers and changes only the rule.
RECHECK = {
    "version": "answer-eval-l-recheck1", "date": "2026-11-04",
    "change": "answer contract B: grounded=false means the supplied papers do not answer the "
              "request and the answer may cite the closest papers (shown as closest results); "
              "grounded answers must still cite",
    "method": "free: re-validate the saved raw replies of invalid_answer failures under contract B; "
              "no new requests, no new grades, decision rule and drift guard unchanged",
    "status": "post hoc: the rule changed after seeing the failures, so a pass is provisional; "
              "serving Luna needs a confirmation run on held-out queries (separate approval)",
}


def recheck_reply(reply: dict | None, item: dict, candidate: str) -> dict | None:
    """The saved reply re-validated under contract B; other failures and successes unchanged."""
    if reply is None or reply["outcome"]["status"] != "invalid_answer":
        return reply
    failure = response_path(candidate, item).with_suffix(".failure.json")
    if not failure.exists():
        return reply
    raw = json.loads(failure.read_text(encoding="utf-8"))
    try:
        value = json.loads(client.structured_text(client.final_parts(raw["output"] or [])))
        result = answer.validate(value, len(item["paper_ids"]), ungrounded_may_cite=True)
    except (ValueError, TypeError, KeyError, AttributeError):
        return reply
    return {**reply, "outcome": {"status": "ok", **result, "contract": "B"}}


def generation_payload(state: dict, item: dict, candidate: str) -> bytes:
    return answer.encode_payload(client.MODELS[candidate], state["queries"][item["query_id"]]["query"],
                                 [state["papers"][p] for p in item["paper_ids"]],
                                 version=answer.VERSION_V2)


def response_path(candidate: str, item: dict) -> Path:
    return OUT / "responses" / candidate / f"{item['item_id']}.json"


def grade_path(candidate: str, item: dict) -> Path:
    """candidate is a v2 writer (luna, mini) or an anchor (v1-gpt-5.4, v1-mini)."""
    return OUT / "sheet-grades" / "terra" / candidate / f"{item['item_id']}.json"


def ledger() -> client.TaskLedger:
    return client.TaskLedger(TASK, int(CAP_USD * 1e9), MAX_REQUESTS)


def reply_for(state: dict, item: dict, candidate: str) -> dict | None:
    return ev._read(response_path(candidate, item), generation_payload(state, item, candidate))


def todo(state: dict) -> list[tuple[str, dict, bytes]]:
    return [(c, item, generation_payload(state, item, c)) for c in CANDIDATES
            for item in ev.stage_items(state, "full") if reply_for(state, item, c) is None]


def preflight(state: dict, task: client.TaskLedger) -> dict:
    tokenizer, expected_out = tiktoken.get_encoding("o200k_base"), 300
    by_model: dict[str, dict] = {}
    for _, _, encoded in todo(state):
        model = json.loads(encoded)["model"]
        m = by_model.setdefault(model, {"requests": 0, "input_tokens": 0, "expected_usd": 0.0,
                                        "tier": api.MODEL_TIERS[model]})
        tokens = round(len(tokenizer.encode(encoded.decode("utf-8"))) * 1.1)
        m["requests"] += 1
        m["input_tokens"] += tokens
        m["expected_usd"] += client.cost_nanodollars(model, tokens, expected_out) / 1e9
    summary = task.summary()
    return {"requests": sum(m["requests"] for m in by_model.values()), "by_model": by_model,
            "expected_usd": sum(m["expected_usd"] for m in by_model.values()),
            "spent_usd": summary["accounted_usd"], "cap_usd": summary["cap_usd"]}


def run(state: dict, task: client.TaskLedger) -> None:
    for n, (candidate, item, encoded) in enumerate(todo(state)):
        ev._send(response_path(candidate, item), encoded, task,
                 lambda v, k=len(item["paper_ids"]): answer.validate(v, k),
                 {"item_id": item["item_id"], "candidate": candidate, "prompt": answer.VERSION_V2})
        if n == 0:
            print(f"Smoke request {candidate}/{item['item_id']} done.", flush=True)


# --- Blinded workbook ------------------------------------------------------------------

def _row(state: dict, item: dict, candidate: str, reply: dict) -> dict:
    body = json.loads(json.loads(ev.grade_payload(state, item, reply["outcome"]))["input"])
    return {"candidate": candidate, "item_id": item["item_id"], "kind": item["kind"],
            "query_type": state["queries"][item["query_id"]]["query_type"], **body}


def anchors(state: dict) -> list[dict]:
    """Answer-v1 answers Terra already graded, picked by query type in a fixed hash order."""
    rows = []
    for model in (REFERENCE, INCUMBENT):
        graded = [_row(state, item, f"v1-{model}", reply) for item in ev.stage_items(state, "full")
                  if ev.gradable(reply := ev._read(ev.response_path(model, item),
                                                   ev.generation_payload(state, item, model)))
                  and ev.sheet_grade_path(model, item).exists()]
        types = sorted({r["query_type"] for r in graded})
        queues = {t: sorted((r for r in graded if r["query_type"] == t),
                            key=lambda r: sheets._hash(f"{SALT}-anchor:{r['item_id']}")) for t in types}
        picked: list[dict] = []
        while len(picked) < ANCHORS_PER_MODEL and any(queues.values()):
            for t in types:
                if queues[t] and len(picked) < ANCHORS_PER_MODEL:
                    picked.append(queues[t].pop(0))
        rows += picked
    return rows


def export(state: dict) -> int:
    rows = [_row(state, item, c, reply) for c in CANDIDATES for item in ev.stage_items(state, "full")
            if ev.gradable(reply := reply_for(state, item, c))]
    if not rows:
        raise SystemExit("No answer-v2 answers to grade yet; run generation first")
    chosen = sheets.blind(rows + anchors(state), SALT)
    sheets.write_workbook(chosen, SHEET, "GPT-6.1 Terra")
    ev._write(KEY_PATH, {r["answer_id"]: {"candidate": r["candidate"], "item_id": r["item_id"],
                                          "sentences": [s["text"] for s in r["answer_sentences"]]}
                         for r in chosen})
    return len(chosen)


def import_sheet(path: Path) -> int:
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    grades = sheets.read_grades(path, key)
    for aid, grade in grades.items():
        meta = key[aid]
        ev._write(grade_path(meta["candidate"], {"item_id": meta["item_id"]}),
                  {"answer_id": aid, "candidate": meta["candidate"], "item_id": meta["item_id"],
                   "grader": "GPT-6.1 Terra", "provenance": f"GPT-6.1 Terra via owner chat session "
                                                             f"from {path.name} (not the API)",
                   "outcome": {"status": "ok", **grade}})
    return len(grades)


# --- Report -----------------------------------------------------------------------------

def drift(state: dict) -> dict:
    """Same answer-v1 answers, Terra session 1 (Decision 48) vs session 2 (this workbook)."""
    pairs, gaps = [], []
    for model in (REFERENCE, INCUMBENT):
        for item in ev.stage_items(state, "full"):
            new, old = grade_path(f"v1-{model}", item), ev.sheet_grade_path(model, item)
            if not (new.exists() and old.exists()):
                continue
            a, b = (json.loads(p.read_text(encoding="utf-8"))["outcome"] for p in (old, new))
            pairs += [(x["verdict"], y["verdict"]) for x, y in zip(a["sentences"], b["sentences"])]
            fa, fb = sheets._faithfulness(a), sheets._faithfulness(b)
            if fa is not None and fb is not None:
                gaps.append(fb - fa)
    shift = sheets._mean(gaps)
    return {"answers": len(gaps), "sentences": len(pairs),
            "sentence_agreement": sheets._mean([a == b for a, b in pairs]),
            "sentence_kappa": sheets._kappa(pairs), "faithfulness_shift_new_minus_old": shift,
            "within_limit": shift is not None and abs(shift) <= DRIFT_LIMIT}


def summarize(state: dict, recheck: bool = False) -> dict:
    items = ev.stage_items(state, "full")
    task = ledger()
    rows, table = {}, {}
    for c in CANDIDATES:
        rows[c], spent = [], []
        for item in items:
            reply = reply_for(state, item, c)
            if recheck:
                reply = recheck_reply(reply, item, c)
            path = grade_path(c, item)
            grade = (json.loads(path.read_text(encoding="utf-8"))
                     if ev.gradable(reply) and path.exists() else None)
            rows[c].append(ev.item_metrics(state, item, reply, grade))
            u = (reply or {}).get("usage", {})
            if reply and "input_tokens" not in u:
                u = task.attempt(reply["request_sha256"]) or {}
            if u.get("input_tokens") is not None:
                spent.append(u)
        table[c] = _table(rows[c], ev.cost_profile(c, spent))
    v1 = ev.summarize(state, "full")
    return {"rows": rows, "table": table, "v1_rows": v1["rows"], "v1_table": v1["table"]}


def _table(r: list[dict], cost: dict) -> dict:
    answerable = [x for x in r if x["kind"] == "answerable"]
    abstain = [x for x in r if x["kind"] == "abstain"]
    return {"items": len(r), "format_valid": ev._mean(r, "format_valid"),
            "false_abstain_v2": ev._mean(answerable, "false_abstain_v2"),
            "abstain_accuracy_v2": ev._mean(abstain, "abstained_v2"),
            **{k: ev._mean(answerable, k) for k in ("citation_precision", "grade2_coverage",
                                                     "source_cited", "faithfulness", "fully_faithful",
                                                     "answers_request", "words", "n_cited")},
            "graded_answers": sum(x.get("faithfulness") is not None for x in answerable), **cost}


def checks(rows: list[dict], t: dict, reference_rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["kind"] == "answerable"]
    ref = [r for r in reference_rows if r["kind"] == "answerable"]
    out = {}
    for key in ("faithfulness", "citation_precision"):
        p = ev.paired(answerable, ref, key)
        out[f"{key}_vs_yardstick"] = p
        out[key] = p is not None and p["ci95"][0] >= -ev.MARGIN
    out["abstain_accuracy"] = (t["abstain_accuracy_v2"] or 0) >= 0.80
    out["false_abstain"] = t["false_abstain_v2"] is not None and t["false_abstain_v2"] <= 0.10
    out["format_valid"] = (t["format_valid"] or 0) >= 0.95
    out["qualifies"] = all(out[k] for k in ("faithfulness", "citation_precision", "abstain_accuracy",
                                             "false_abstain", "format_valid"))
    return out


def decide(summary: dict, grader_drift: dict) -> dict:
    reference = summary["v1_rows"][REFERENCE]
    result = {c: checks(summary["rows"][c], summary["table"][c], reference) for c in CANDIDATES}
    challenger = result[CHALLENGER]["qualifies"]
    cheaper = ((summary["table"][CHALLENGER]["usd_per_answer"] or 1)
               < (summary["v1_table"][INCUMBENT]["usd_per_answer"] or 0))
    replace = challenger and cheaper and grader_drift["within_limit"]
    return {"checks": result, "replace_incumbent": replace,
            "serving_model": f"{CHALLENGER} ({answer.VERSION_V2})" if replace
            else f"{INCUMBENT} ({answer.VERSION})",
            "why": ("qualifies, cheaper, grader drift within limit" if replace else
                    "grader drift exceeds the limit (report only)" if challenger and cheaper
                    else "challenger does not qualify")}


def report(state: dict, recheck: bool = False) -> dict:
    summary = summarize(state, recheck)
    value = {"plan": PLAN, "drift": drift(state), "table": summary["table"],
             "v1_table": {k: summary["v1_table"][k] for k in (REFERENCE, INCUMBENT, CHALLENGER)}}
    value["decision"] = decide(summary, value["drift"])
    name = "report"
    if recheck:
        value["recheck"] = RECHECK
        value["rechecked_answers"] = {c: sum(r.get("format_valid", False) for r in summary["rows"][c])
                                      - sum(r.get("format_valid", False) for r in summarize(state)["rows"][c])
                                      for c in CANDIDATES}
        name = "report-recheck"
    ev._write(OUT / f"{name}.json", value)
    write_markdown(value, OUT / f"{name}.md")
    return value


def _f(x, digits: int = 3) -> str:
    return "—" if x is None else f"{x:.{digits}f}"


def write_markdown(value: dict, path: Path) -> None:
    lines = ["# Experiment L: citation-discipline prompt (answer-v2) for the AI summary", "",
             f"Same 125 answer-dev-v1 items and Decision46 top10 as Decision 48. Yardstick: {REFERENCE} "
             "answer-v1, graded by GPT-6.1 Terra in session 1; answer-v2 graded by Terra in session 2.", ""]
    if "recheck" in value:
        r = value["recheck"]
        lines[0] = "# Experiment L recheck: answer-v2 under answer contract B (provisional)"
        lines += [f"Change: {r['change']}.", "", f"Method: {r['method']}. Answers rescored from format "
                  f"failures to valid: {value['rechecked_answers']}.", "", f"**Status: {r['status']}.**", ""]
    lines += ["| Model (prompt) | Format valid | False abstain | Abstain acc. | Citation precision | "
              "Faithfulness | Fully faithful | Answers request | Words | $ per 1k | p50 s |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    rows = [(f"{m} (answer-v1)", value["v1_table"][m]) for m in (REFERENCE, INCUMBENT, CHALLENGER)]
    rows += [(f"**{m} (answer-v2)**", value["table"][m]) for m in CANDIDATES]
    for name, t in rows:
        lines.append(f"| {name} | {_f(t['format_valid'])} | {_f(t.get('false_abstain_v2'))} | "
                     f"{_f(t.get('abstain_accuracy_v2'))} | {_f(t['citation_precision'])} | "
                     f"{_f(t['faithfulness'])} | {_f(t['fully_faithful'])} | {_f(t['answers_request'], 2)} | "
                     f"{_f(t['words'], 0)} | ${_f(t.get('usd_per_1000'), 2)} | {_f(t.get('seconds_p50'), 1)} |")
    lines += ["", f"| answer-v2 model | Faithfulness Δ vs {REFERENCE} v1 [95% CI] | Citation precision Δ [95% CI] | Qualifies |",
              "|---|---|---|---|"]
    for m, c in value["decision"]["checks"].items():
        cells = []
        for key in ("faithfulness", "citation_precision"):
            p = c[f"{key}_vs_yardstick"]
            cells.append("—" if p is None else
                         f"{p['difference']:+.3f} [{p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f}] (n={p['n']})")
        failed = [k for k in ("faithfulness", "citation_precision", "abstain_accuracy", "false_abstain",
                              "format_valid") if not c[k]]
        lines.append(f"| {m} | {cells[0]} | {cells[1]} | {'yes' if c['qualifies'] else 'no (' + ', '.join(failed) + ')'} |")
    d = value["drift"]
    decision = (f"**Decision:** serve {value['decision']['serving_model']}: {value['decision']['why']}."
                if "recheck" not in value else
                f"**Provisional result:** {value['decision']['why']} "
                f"({value['decision']['serving_model']} under contract B). Nothing changes in serving "
                "until a held-out confirmation run passes.")
    lines += ["", f"Grader drift (same answer-v1 answers, Terra session 2 minus session 1): "
                  f"{d['answers']} answers, sentence agreement {_f(d['sentence_agreement'])}, kappa "
                  f"{_f(d['sentence_kappa'])}, faithfulness shift {_f(d['faithfulness_shift_new_minus_old'])} "
                  f"(limit ±{DRIFT_LIMIT}).", "", decision, "",
              f"Cautions: {PLAN['caveats']} Graders are models, not people."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="send generation requests (paid)")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--import", dest="import_", metavar="PATH")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--recheck", action="store_true", help="free: report under contract B")
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", PLAN)
    state = ev.load_state()
    task = ledger()
    if not (args.export or args.import_ or args.report or args.recheck):
        pre = preflight(state, task)
        print(json.dumps(pre, indent=2), flush=True)
        if args.run and pre["requests"]:
            if pre["expected_usd"] > pre["cap_usd"] - pre["spent_usd"]:
                raise api.BudgetExceeded("Expected cost exceeds the remaining ceiling; nothing sent")
            run(state, task)
    if args.export:
        print(f"{export(state)} answers written to {SHEET}")
    if args.import_:
        print(f"{import_sheet(Path(args.import_))} graded answers imported")
    if args.report:
        value = report(state)
        print(json.dumps({"drift": value["drift"], "decision": value["decision"]["serving_model"]}, default=str))
    if args.recheck:
        freeze(OUT / "recheck-plan.json", RECHECK)
        value = report(state, recheck=True)
        print(json.dumps({"rechecked": value["rechecked_answers"], "why": value["decision"]["why"]}))


if __name__ == "__main__":
    main()
