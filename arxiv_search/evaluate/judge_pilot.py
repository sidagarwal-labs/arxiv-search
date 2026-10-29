"""Decide which LLM judge to trust, by comparing both with a person (Decision 33).

1. pilot_query_ids: 12 dev queries, 3 of each type, chosen at random with a fixed seed.
2. Both judges grade the same pairs: each pilot query's pooled top 10s, plus its source
   paper as a sanity check (the paper the query was written from should usually get 2).
       python -m arxiv_search.evaluate.judge --judge gemma-31b --queries pilot
       python -m arxiv_search.evaluate.judge --judge qwen2.5-7b --queries pilot
3. A person grades 100 of those pairs blind in a spreadsheet (no LLM grades, no ranks,
   no hint which paper is the source):
       python -m arxiv_search.evaluate.judge_pilot sheet
4. Report: agreement of each judge with the person, and with each other:
       python -m arxiv_search.evaluate.judge_pilot report
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter

from arxiv_search import config
from arxiv_search.evaluate import judge
from arxiv_search.evaluate.metrics import cohen_kappa

PILOT_DIR = config.EVAL_DIR / "judge_pilot"
SHEET_PATH = PILOT_DIR / "human_grades.xlsx"
PAIRS_PATH = PILOT_DIR / "human_pairs.json"  # sheet row -> query/paper (kept out of the sheet)
REPORT_PATH = PILOT_DIR / "report.md"
QUERY_TYPES = ("keyword", "question", "paraphrase", "known_item")


def pilot_query_ids(queries: dict, split: dict) -> list[str]:
    rng = random.Random(config.RANDOM_SEED)
    chosen = []
    for query_type in QUERY_TYPES:
        dev = sorted(q for q in split["dev"] if queries[q]["query_type"] == query_type)
        chosen += sorted(rng.sample(dev, config.JUDGE_PILOT_QUERIES_PER_TYPE))
    return chosen


def pilot_pairs(queries: dict, split: dict) -> dict[str, list[str]]:
    """Pooled top 10s plus each query's source paper."""
    pairs = judge.pool(pilot_query_ids(queries, split))
    for qid, ids in pairs.items():
        if queries[qid]["source_arxiv_id"] not in ids:
            ids.append(queries[qid]["source_arxiv_id"])
    return pairs


def human_sample(pairs: dict[str, list[str]], queries: dict) -> list[tuple[str, str]]:
    """25 pairs per query type: every source pair (3) plus 22 others at random.

    Chosen before any LLM grade is looked at, so the sample can't favor either judge.
    Returned grouped by query (read the search once, then its papers) in shuffled order.
    """
    rng = random.Random(config.RANDOM_SEED)
    sample = []
    for query_type in QUERY_TYPES:
        qids = [q for q in pairs if queries[q]["query_type"] == query_type]
        sources = [(q, queries[q]["source_arxiv_id"]) for q in qids]
        others = [(q, a) for q in qids for a in pairs[q] if a != queries[q]["source_arxiv_id"]]
        sample += sources + rng.sample(others, config.JUDGE_PILOT_HUMAN_PAIRS_PER_TYPE - len(sources))
    by_query: dict[str, list[str]] = {}
    for qid, arxiv_id in sample:
        by_query.setdefault(qid, []).append(arxiv_id)
    order = list(by_query)
    rng.shuffle(order)
    out = []
    for qid in order:
        rng.shuffle(by_query[qid])
        out += [(qid, a) for a in by_query[qid]]
    return out


# --- The spreadsheet ----------------------------------------------------------


def write_sheet(sample: list[tuple[str, str]], queries: dict, papers: dict) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    from arxiv_search.evaluate import judge_prompts

    if SHEET_PATH.exists():
        raise SystemExit(f"{SHEET_PATH} exists; delete it first if you really want a fresh sheet")
    font, bold = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")
    wb = Workbook()

    guide = wb.active
    guide.title = "How to grade"
    lines = ["Grade each row's paper for its search: type 0, 1 or 2 in the Grade column.",
             "Use only the title, authors and abstract shown. Don't look papers up.", "",
             *judge_prompts.RUBRIC.splitlines(), "",
             "Rows are grouped by search. Notes are optional (e.g. why it was hard to decide).",
             "Save the file when done (keep the name and the .xlsx format)."]
    for row, text in enumerate(lines, 1):
        guide.cell(row, 1, text).font = bold if row == 1 else font
    guide.column_dimensions["A"].width = 110

    sheet = wb.create_sheet("Grades")
    headers = ["Row", "Search", "Title", "Authors", "Abstract", "Grade (0/1/2)", "Notes"]
    widths = [6, 34, 36, 24, 90, 12, 30]
    for col, (header, width) in enumerate(zip(headers, widths), 1):
        cell = sheet.cell(1, col, header)
        cell.font, cell.alignment = bold, wrap
        cell.fill = PatternFill("solid", start_color="D9E1F2")
        sheet.column_dimensions[cell.column_letter].width = width
    grade_fill = PatternFill("solid", start_color="FFF2CC")
    previous = None
    for row, (qid, arxiv_id) in enumerate(sample, 2):
        paper = papers[arxiv_id]
        values = [row - 1, queries[qid]["query"], paper["title"], ", ".join(paper["authors"][:10]),
                  paper["abstract"], None, None]
        for col, value in enumerate(values, 1):
            cell = sheet.cell(row, col, value)
            cell.font, cell.alignment = font, wrap
        sheet.cell(row, 6).fill = grade_fill
        if qid != previous:
            sheet.cell(row, 2).font = bold
        previous = qid
    rule = DataValidation(type="whole", operator="between", formula1="0", formula2="2",
                          showErrorMessage=True, error="Enter 0, 1 or 2")
    sheet.add_data_validation(rule)
    rule.add(f"F2:F{len(sample) + 1}")
    sheet.freeze_panes = "C2"
    wb.active = 1
    wb.save(SHEET_PATH)
    PAIRS_PATH.write_text(json.dumps([{"row": i, "query_id": q, "arxiv_id": a}
                                      for i, (q, a) in enumerate(sample, 1)], indent=1))


def read_human_grades() -> dict[tuple[str, str], int]:
    """(query_id, arxiv_id) -> the person's grade, for every row filled in so far."""
    from openpyxl import load_workbook

    pairs = {p["row"]: (p["query_id"], p["arxiv_id"]) for p in json.loads(PAIRS_PATH.read_text())}
    grades = {}
    workbook = load_workbook(SHEET_PATH, read_only=True)
    try:
        for row in workbook["Grades"].iter_rows(min_row=2, values_only=True):
            number, grade = row[0], row[5]
            if number is None or grade in (None, ""):
                continue
            if isinstance(grade, bool) or grade not in (0, 1, 2, "0", "1", "2"):
                raise ValueError(f"row {number}: grade must be 0, 1 or 2, not {grade!r}")
            grades[pairs[int(number)]] = int(grade)
    finally:
        workbook.close()
    return grades


# --- The report ---------------------------------------------------------------


def agreement(a: list[int], b: list[int]) -> dict:
    relevant_a, relevant_b = [int(x >= 1) for x in a], [int(x >= 1) for x in b]
    return {
        "n": len(a),
        "exact": sum(x == y for x, y in zip(a, b)) / len(a),
        "kappa_quadratic": cohen_kappa(a, b, weights="quadratic"),
        "relevant_agree": sum(x == y for x, y in zip(relevant_a, relevant_b)) / len(a),
        "relevant_kappa": cohen_kappa(relevant_a, relevant_b, categories=(0, 1)),
        "opposite": sum(abs(x - y) == 2 for x, y in zip(a, b)),  # one said 0, the other 2
    }


def confusion(a: list[int], b: list[int], name_a: str, name_b: str) -> str:
    counts = Counter(zip(a, b))
    lines = [f"| {name_a} ↓ / {name_b} → | 0 | 1 | 2 |", "|---|---|---|---|"]
    lines += [f"| {x} | " + " | ".join(str(counts[(x, y)]) for y in (0, 1, 2)) + " |" for x in (0, 1, 2)]
    return "\n".join(lines)


def judge_rows(judge_key: str, pairs: dict, queries: dict, papers: dict) -> dict[tuple[str, str], dict]:
    cached = judge.load_judgments(judge_key)
    out = {}
    for qid, ids in pairs.items():
        for arxiv_id in ids:
            row = cached.get(judge.pair_key(judge_key, queries[qid]["query"], papers[arxiv_id]))
            if row:
                out[(qid, arxiv_id)] = row
    return out


def build_report(queries: dict, papers: dict, split: dict) -> str:
    pairs = pilot_pairs(queries, split)
    total = sum(map(len, pairs.values()))
    graded = {k: judge_rows(k, pairs, queries, papers) for k in config.JUDGES}
    human = read_human_grades() if SHEET_PATH.exists() else {}
    out = [f"# Judge pilot (rubric {judge.RUBRIC_VERSION})", "",
           f"{len(pairs)} dev queries, {total} query-paper pairs. Human grades so far: {len(human)}.", "",
           "Preliminary calibration on one person's pilot labels, not held-out validation. "
           "Models with different coverage must be compared on the same pair subset. "
           "OpenAI's human-only run intentionally grades 100 pairs, not all 266 pooled pairs.", "",
           "| Judge | Pairs graded | Calls | Mean s/call | Source papers graded 2 | Grade 0/1/2 shares |",
           "|---|---|---|---|---|---|"]
    for key, rows in graded.items():
        if not rows:
            out.append(f"| {key} | 0 / {total} | — | — | — | — |")
            continue
        calls = {r.get("usage", {}).get("request_id") or
                 (r["query_id"], r["call_seconds"], r["batch_size"]): r["call_seconds"]
                 for r in rows.values()}
        sources = [r["grade"] for (q, a), r in rows.items() if a == queries[q]["source_arxiv_id"]]
        shares = Counter(r["grade"] for r in rows.values())
        out.append(f"| {key} | {len(rows)} / {total} | {len(calls)} | {statistics.mean(calls.values()):.0f} | "
                   f"{sources.count(2)} / {len(sources)} | "
                   + " / ".join(f"{shares[g] / len(rows):.0%}" for g in (0, 1, 2)) + " |")

    comparisons = [(k, "human", graded[k], human) for k in config.JUDGES]
    keys = list(config.JUDGES)
    comparisons.append((keys[0], keys[1], graded[keys[0]], graded[keys[1]]))
    out += ["", "**Exact** = same grade. **κ** = Cohen's kappa (1 perfect, 0 chance; quadratic: "
            "0-vs-2 costs most). **Relevant** = agree on 0 vs 1-or-2. **Opposite** = one said 0, the "
            "other 2.", "",
            "| Comparison | Pairs | Exact | κ (quadratic) | Relevant agree | κ (relevant) | Opposite |",
            "|---|---|---|---|---|---|---|"]
    tables = []
    for name_a, name_b, a_rows, b_rows in comparisons:
        common = sorted(set(a_rows) & set(b_rows))
        if not common:
            out.append(f"| {name_a} vs {name_b} | 0 | — | — | — | — | — |")
            continue
        grade = lambda rows, k: rows[k] if isinstance(rows[k], int) else rows[k]["grade"]
        a = [grade(a_rows, k) for k in common]
        b = [grade(b_rows, k) for k in common]
        s = agreement(a, b)
        out.append(f"| {name_a} vs {name_b} | {s['n']} | {s['exact']:.0%} | {s['kappa_quadratic']:.2f} | "
                   f"{s['relevant_agree']:.0%} | {s['relevant_kappa']:.2f} | {s['opposite']} |")
        by_type = []
        for t in QUERY_TYPES:
            idx = [i for i, (q, _) in enumerate(common) if queries[q]["query_type"] == t]
            if idx:
                by_type.append(f"{t} {sum(a[i] == b[i] for i in idx) / len(idx):.0%} (n={len(idx)})")
        tables.append(f"**{name_a} vs {name_b}**: exact agreement by type: {', '.join(by_type)}\n\n"
                      + confusion(a, b, name_a, name_b))
    active = {k: v for k, v in graded.items() if set(v) & set(human)}
    if len(active) > 1:
        common = sorted(set(human).intersection(*(set(rows) for rows in active.values())))
        out += ["", f"## Fair comparison: identical {len(common)} human-labeled pairs", "",
                "| Judge | Exact | Quadratic kappa | Relevant agreement | 0-vs-2 errors |",
                "|---|---|---|---|---|"]
        if common:
            for name, rows in active.items():
                s = agreement([human[k] for k in common], [rows[k]["grade"] for k in common])
                out.append(f"| {name} | {s['exact']:.1%} | {s['kappa_quadratic']:.3f} | "
                           f"{s['relevant_agree']:.1%} | {s['opposite']} |")
        else:
            out.append("No common pairs yet.")
    out += ["", "## API usage (successful cached responses)", "",
            "Tokens are deduplicated by request ID where available. Older cache entries have "
            "no request IDs; their calls are estimated from query, batch size and duration. "
            "Gemma usage may omit failed API attempts; OpenAI's ledger separately accounts "
            "for unknown attempts conservatively. Wall time includes retries.",
            "", "| Judge | Input tokens | Output tokens | Thinking tokens (included where applicable) |",
            "|---|---|---|---|"]
    for name, rows in graded.items():
        if not rows:
            continue
        usage_by_call = {}
        for row in rows.values():
            usage = row.get("usage", {})
            call_id = usage.get("request_id") or (row["query_id"], row["call_seconds"], row["batch_size"])
            usage_by_call[call_id] = usage
        totals = [sum(u.get(field) or 0 for u in usage_by_call.values())
                  for field in ("input_tokens", "output_tokens", "thinking_tokens")]
        out.append(f"| {name} | {totals[0]:,} | {totals[1]:,} | {totals[2]:,} |")
    return "\n".join(out + [""] + ["\n\n".join(tables)]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["sheet", "report"])
    args = parser.parse_args()
    papers, queries, split = judge.load_inputs()
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    if args.action == "sheet":
        sample = human_sample(pilot_pairs(queries, split), queries)
        write_sheet(sample, queries, papers)
        print(f"Wrote {SHEET_PATH} ({len(sample)} rows)")
    else:
        report = build_report(queries, papers, split)
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(report)


if __name__ == "__main__":
    main()
