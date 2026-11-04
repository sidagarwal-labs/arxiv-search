"""Blinded grading workbooks for the answer-model comparison (graded outside the API).

The owner grades AI-summary answers with chat models instead of paid API calls:
    * astra-sample.xlsx: a stratified sample (SAMPLE_PER_MODEL answers per candidate),
      graded with GPT-6 ASTRA to measure agreement with the Terra grader.
    * terra-full.xlsx: every gradable answer (valid and grounded), graded with GPT-6.1 Terra
      (owner's choice, 2026-11-04, before any grading; Terra is not a candidate, so the
      full-set grader has no self-preference).

Both workbooks carry exactly what the API grader would see (answer_eval.grade_payload): the
request, the answer split into sentences S1..Sk, and only the cited papers' evidence cards,
plus the same rubric (answer_eval.GRADE_SYSTEM) and a not-a-direct-answer caveat check. Rows are shuffled and carry opaque ids; the
writer of each answer is stored only in a key file that is never part of a workbook.

    python -m arxiv_search.evaluate.answer_grade_sheets --export
    python -m arxiv_search.evaluate.answer_grade_sheets --import astra  <filled.xlsx>
    python -m arxiv_search.evaluate.answer_grade_sheets --import terra   <filled.xlsx>
    python -m arxiv_search.evaluate.answer_grade_sheets --agreement
    python -m arxiv_search.evaluate.answer_eval --stage full --report
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from arxiv_search import answer
from arxiv_search.evaluate import answer_eval as ev

SHEETS_DIR = ev.SET_PATH.parent / "grading"
KEY_PATH = ev.OUT / "grading-key.json"
IMPORT_DIR = ev.OUT / "sheet-grades"
SAMPLE_PER_MODEL = 10
VERDICTS = ("supported", "partial", "unsupported", "no_claim")
SHEETS = {"astra": ("astra-sample.xlsx", "GPT-6 ASTRA"), "terra": ("terra-full.xlsx", "GPT-6.1 Terra")}
FULL = "terra"
SALTS = {"astra": "astra", "terra": "gpt54"}  # salt kept from the first export so answer ids are stable
FONT = "Arial"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gradable_answers(state: dict) -> list[dict]:
    """Every valid, grounded full-stage answer with what the grader may see."""
    out = []
    for candidate in ev.CANDIDATES:
        for item in ev.stage_items(state, "full"):
            reply = ev._read(ev.response_path(candidate, item), ev.generation_payload(state, item, candidate))
            if not ev.gradable(reply):
                continue
            body = json.loads(json.loads(ev.grade_payload(state, item, reply["outcome"]))["input"])
            out.append({"candidate": candidate, "item_id": item["item_id"], "kind": item["kind"],
                        "query_type": state["queries"][item["query_id"]]["query_type"], **body})
    return out


def sample(rows: list[dict], per_model: int = SAMPLE_PER_MODEL) -> list[dict]:
    """Per candidate: round-robin over query types, each type in a fixed hash order."""
    chosen = []
    for candidate in ev.CANDIDATES:
        mine = [r for r in rows if r["candidate"] == candidate]
        types = sorted({r["query_type"] for r in mine})
        queues = {t: sorted((r for r in mine if r["query_type"] == t),
                            key=lambda r: _hash(f"astra-sample:{r['item_id']}")) for t in types}
        picked = []
        while len(picked) < per_model and any(queues.values()):
            for t in types:
                if queues[t] and len(picked) < per_model:
                    picked.append(queues[t].pop(0))
        chosen += picked
    return chosen


def blind(rows: list[dict], salt: str) -> list[dict]:
    """Shuffle deterministically and assign opaque answer ids (A001...)."""
    ordered = sorted(rows, key=lambda r: _hash(f"{salt}:{r['candidate']}:{r['item_id']}"))
    return [{**r, "answer_id": f"A{n:03d}"} for n, r in enumerate(ordered, 1)]


def evidence_text(cards: list[dict]) -> str:
    return "\n\n".join(f"{c['label']} {c['title']} ({c['authors']}; {c['month']})\n{c['abstract']}"
                       for c in cards)


def write_workbook(rows: list[dict], path: Path, grader: str) -> None:
    wb = Workbook()
    bold, wrap = Font(name=FONT, bold=True), Alignment(wrap_text=True, vertical="top")
    fill = PatternFill("solid", start_color="FFFF00")
    info = wb.active
    info.title = "Instructions"
    notes = [f"Grader: {grader}. Fill the yellow cells only; do not edit ids or text.",
             "Answers sheet: answers_request = 0, 1 or 2 for each answer.",
             "Answers sheet: not_direct_answer = yes if the answer clearly tells the reader that "
             "the supplied papers do NOT directly answer the request (for example 'none of the "
             "papers directly address X; the closest are...'); otherwise no.",
             "Sentences sheet: verdict = supported / partial / unsupported / no_claim for each "
             "sentence; reason = under 25 words.",
             "Judge each sentence only against the cited papers shown for its answer_id.",
             "", "Rubric (identical to the API grader):", ev.GRADE_SYSTEM]
    for n, text in enumerate(notes, 1):
        info.cell(n, 1, text).font = Font(name=FONT, bold=n == 1)
        info.cell(n, 1).alignment = wrap
    info.column_dimensions["A"].width = 120

    ans = wb.create_sheet("Answers")
    ans.append(["answer_id", "request", "answer", "cited_papers", "answers_request", "not_direct_answer"])
    for r in rows:
        ans.append([r["answer_id"], r["request"], " ".join(s["text"] for s in r["answer_sentences"]),
                    evidence_text(r["cited_papers"]), None, None])
    sent = wb.create_sheet("Sentences")
    sent.append(["answer_id", "sentence_id", "sentence", "verdict", "reason"])
    for r in rows:
        for s in r["answer_sentences"]:
            sent.append([r["answer_id"], s["id"], s["text"], None, None])

    for ws, widths, inputs in ((ans, (11, 40, 70, 90, 16, 18), ("E", "F")), (sent, (11, 12, 80, 16, 50), ("D", "E"))):
        for cell in ws[1]:
            cell.font = bold
        for col, width in zip("ABCDEF", widths):
            ws.column_dimensions[col].width = width
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment, cell.font = wrap, Font(name=FONT)
        for col in inputs:
            for (cell,) in ws[f"{col}2:{col}{ws.max_row}"]:
                cell.fill = fill
        ws.freeze_panes = "B2"
    check = DataValidation(type="list", formula1='"0,1,2"', allow_blank=True)
    ans.add_data_validation(check)
    check.add(f"E2:E{ans.max_row}")
    yes_no = DataValidation(type="list", formula1='"yes,no"', allow_blank=True)
    ans.add_data_validation(yes_no)
    yes_no.add(f"F2:F{ans.max_row}")
    verdict = DataValidation(type="list", formula1='"' + ",".join(VERDICTS) + '"', allow_blank=True)
    sent.add_data_validation(verdict)
    verdict.add(f"D2:D{sent.max_row}")
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def export(state: dict) -> dict:
    rows = gradable_answers(state)
    sets = {"astra": blind(sample(rows), SALTS["astra"]), FULL: blind(rows, SALTS[FULL])}
    key = {}
    for name, chosen in sets.items():
        filename, grader = SHEETS[name]
        write_workbook(chosen, SHEETS_DIR / filename, grader)
        key[name] = {r["answer_id"]: {"candidate": r["candidate"], "item_id": r["item_id"],
                                      "sentences": [s["text"] for s in r["answer_sentences"]]}
                     for r in chosen}
    ev._write(KEY_PATH, key)
    return {name: len(chosen) for name, chosen in sets.items()}


def read_grades(path: Path, key: dict) -> dict:
    """Validate a filled workbook against the key; return {answer_id: grade} in API format."""
    wb = load_workbook(path, data_only=True)
    requests = {r[0]: r[4] for r in wb["Answers"].iter_rows(min_row=2, values_only=True) if r[0]}
    caveats = {r[0]: str(r[5] or "").strip().lower() for r in wb["Answers"].iter_rows(min_row=2, values_only=True)
               if r[0]}
    sentences: dict[str, list] = {}
    for aid, sid, text, verdict, reason in wb["Sentences"].iter_rows(min_row=2, max_col=5, values_only=True):
        if aid:
            sentences.setdefault(aid, []).append((sid, text, verdict, reason))
    if set(requests) != set(key) or set(sentences) != set(key):
        raise ValueError("Workbook answer ids do not match the grading key")
    problems, grades = [], {}
    for aid, meta in key.items():
        rows = sentences[aid]
        verdicts = [str(v).strip().lower() if v is not None else None for _, _, v, _ in rows]
        score = requests[aid]
        if [t for _, t, _, _ in rows] != meta["sentences"]:
            problems.append(f"{aid}: sentence text or order changed")
        if any(v not in VERDICTS for v in verdicts):
            problems.append(f"{aid}: missing or invalid verdict")
        if caveats[aid] not in ("yes", "no"):
            problems.append(f"{aid}: not_direct_answer must be yes or no")
        if score is None or str(score).strip() not in ("0", "1", "2"):
            problems.append(f"{aid}: answers_request must be 0, 1 or 2")
            continue
        grades[aid] = {"sentences": [{"id": sid, "verdict": v, "reason": str(r or "")}
                                     for (sid, _, _, r), v in zip(rows, verdicts)],
                       "answers_request": int(str(score).strip()),
                       "not_direct_answer": caveats[aid] == "yes"}
    if problems:
        raise ValueError("Workbook incomplete:\n" + "\n".join(problems[:30]))
    return grades


def import_sheet(name: str, path: Path) -> int:
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))[name]
    grades = read_grades(path, key)
    _, grader = SHEETS[name]
    for aid, grade in grades.items():
        meta = key[aid]
        ev._write(IMPORT_DIR / name / meta["candidate"] / f"{meta['item_id']}.json",
                  {"answer_id": aid, "candidate": meta["candidate"], "item_id": meta["item_id"],
                   "grader": grader, "provenance": f"{grader} via owner chat session from {path.name} "
                                                   "(not the API)", "outcome": {"status": "ok", **grade}})
    return len(grades)


def _faithfulness(grade: dict) -> float | None:
    values = [ev.VERDICT_VALUE[s["verdict"]] for s in grade["sentences"] if s["verdict"] in ev.VERDICT_VALUE]
    return sum(values) / len(values) if values else None


def _kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    labels = sorted({x for p in pairs for x in p})
    observed = sum(a == b for a, b in pairs) / len(pairs)
    expected = sum((sum(a == l for a, _ in pairs) / len(pairs)) * (sum(b == l for _, b in pairs) / len(pairs))
                   for l in labels)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def _mean(xs: list) -> float | None:
    return sum(xs) / len(xs) if xs else None


def agreement() -> dict:
    """ASTRA vs Terra on the sample answers both graded, overall and by answer-writing model."""
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))["astra"]
    sentence_pairs, request_pairs, caveat_pairs, gaps = [], [], [], {}
    for meta in key.values():
        paths = [IMPORT_DIR / s / meta["candidate"] / f"{meta['item_id']}.json" for s in ("astra", FULL)]
        if not all(p.exists() for p in paths):
            continue
        astra, terra = (json.loads(p.read_text(encoding="utf-8"))["outcome"] for p in paths)
        sentence_pairs += [(a["verdict"], t["verdict"]) for a, t in zip(astra["sentences"], terra["sentences"])]
        request_pairs.append((astra["answers_request"], terra["answers_request"]))
        caveat_pairs.append((astra["not_direct_answer"], terra["not_direct_answer"]))
        fa, fg = _faithfulness(astra), _faithfulness(terra)
        if fa is not None and fg is not None:
            gaps.setdefault(meta["candidate"], []).append(fg - fa)
    value = {"answers": len(request_pairs), "sentences": len(sentence_pairs),
             "sentence_verdict_agreement": _mean([a == b for a, b in sentence_pairs]),
             "sentence_verdict_kappa": _kappa(sentence_pairs),
             "answers_request_agreement": _mean([a == b for a, b in request_pairs]),
             "caveat_agreement": _mean([a == b for a, b in caveat_pairs]),
             "faithfulness_gap_terra_minus_astra": {c: _mean(xs) for c, xs in gaps.items()},
             "note": "A gap that differs by answer-writing model would mean the full-set grader "
                     "favours some models; neither grader wrote any answer."}
    ev._write(ev.OUT / "grader-agreement.json", value)
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--import", dest="import_", nargs=2, metavar=("SHEET", "PATH"))
    parser.add_argument("--agreement", action="store_true", help="ASTRA vs Terra on the sample")
    args = parser.parse_args(argv)
    if args.export:
        print(json.dumps(export(ev.load_state())))
    if args.import_:
        name, path = args.import_
        if name not in SHEETS:
            raise SystemExit(f"SHEET must be one of {sorted(SHEETS)}")
        print(f"{import_sheet(name, Path(path))} graded answers imported for {name}")
    if args.agreement:
        print(json.dumps(agreement(), indent=2))


if __name__ == "__main__":
    main()
