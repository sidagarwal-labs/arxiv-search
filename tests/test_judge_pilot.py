import json

import pytest
from openpyxl import Workbook

from arxiv_search.evaluate import judge_pilot as jp


def test_human_grade_reader_preserves_labels_and_rejects_fraction(tmp_path, monkeypatch):
    sheet_path = tmp_path / "grades.xlsx"
    pairs_path = tmp_path / "pairs.json"
    monkeypatch.setattr(jp, "SHEET_PATH", sheet_path)
    monkeypatch.setattr(jp, "PAIRS_PATH", pairs_path)
    pairs_path.write_text(json.dumps([{"row": 1, "query_id": "q", "arxiv_id": "p"}]))
    wb = Workbook()
    ws = wb.active
    ws.title = "Grades"
    ws.append(["Row", "Search", "Title", "Authors", "Abstract", "Grade", "Notes"])
    ws.append([1, "q", "t", "a", "abstract", 1])
    wb.save(sheet_path)
    assert jp.read_human_grades() == {("q", "p"): 1}
    ws["F2"] = 1.5
    wb.save(sheet_path)
    with pytest.raises(ValueError, match="grade must be"):
        jp.read_human_grades()
    wb.close()


def test_report_compares_identical_pairs_and_deduplicates_usage(monkeypatch):
    q = {"q": {"source_arxiv_id": "p1", "query_type": "keyword"}}
    human = {("q", "p1"): 2, ("q", "p2"): 0}
    rows = {("q", "p1"): {"grade": 2, "query_id": "q", "call_seconds": 1, "batch_size": 2,
                          "usage": {"request_id": "r1", "input_tokens": 10, "output_tokens": 5}},
            ("q", "p2"): {"grade": 0, "query_id": "q", "call_seconds": 1, "batch_size": 2,
                          "usage": {"request_id": "r1", "input_tokens": 10, "output_tokens": 5}}}
    monkeypatch.setattr(jp, "pilot_pairs", lambda *args: {"q": ["p1", "p2"]})
    monkeypatch.setattr(jp, "judge_rows", lambda key, *args: rows)
    monkeypatch.setattr(jp, "read_human_grades", lambda: human)
    report = jp.build_report(q, {}, {})
    assert "identical 2 human-labeled pairs" in report
    assert "| gemma-31b | 10 | 5 | 0 |" in report
