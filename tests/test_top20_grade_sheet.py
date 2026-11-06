import pytest
from openpyxl import Workbook, load_workbook

from arxiv_search.evaluate.top20_grade_sheet import validate_review


def files(tmp_path):
    template = tmp_path / "blank.xlsx"
    reviewed = tmp_path / "reviewed.xlsx"
    wb = Workbook()
    wb.active.title = "Instructions"
    for row in [("Rubric", "unchanged"), ("Evaluator model/name", None),
                ("Evaluation date", None), ("Collection method", "Enter method")]:
        wb.active.append(row)
    sheet = wb.create_sheet("Labels")
    sheet.append(["pair_id", "query_id", "arxiv_id", "query", "title", "authors",
                  "abstract", "grade", "reason"])
    sheet.append(["id1", "q1", "2601.12345", "Q", "T", "A", "Abstract", None, None])
    wb.save(template)
    wb["Instructions"]["B2"] = "Unspecified Copilot model"
    wb["Instructions"]["B3"] = "2026-11-05"
    wb["Instructions"]["B4"] = "Owner chat"
    sheet["H2"], sheet["I2"] = 1, "Related but not direct."
    wb.save(reviewed)
    return template, reviewed


def test_review_preserves_provenance_and_accepts_complete_labels(tmp_path):
    template, reviewed = files(tmp_path)
    rows, provenance = validate_review(template, reviewed)
    assert rows[0]["grade"] == 1
    assert provenance["Evaluator model/name"] == "Unspecified Copilot model"


@pytest.mark.parametrize("sheet,cell,value", [
    ("Labels", "H2", 3), ("Labels", "H2", None), ("Labels", "I2", "word " * 21),
    ("Labels", "I2", "=1+1"), ("Labels", "G2", "Altered abstract"),
    ("Instructions", "B1", "Altered rubric"), ("Instructions", "B2", None),
])
def test_review_rejects_bad_grades_evidence_and_metadata(tmp_path, sheet, cell, value):
    template, reviewed = files(tmp_path)
    wb = load_workbook(reviewed)
    wb[sheet][cell] = value
    wb.save(reviewed)
    with pytest.raises(ValueError):
        validate_review(template, reviewed)
