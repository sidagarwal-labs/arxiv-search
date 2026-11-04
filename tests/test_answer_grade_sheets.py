from openpyxl import load_workbook
import pytest

from arxiv_search.evaluate import answer_grade_sheets as sheets


def _rows():
    out = []
    for c in ("nano", "luna", "mini", "gpt-5.4"):
        for n in range(6):
            out.append({"candidate": c, "item_id": f"A-q-{n}", "kind": "answerable",
                        "query_type": ("keyword", "question")[n % 2], "request": f"query {n}",
                        "answer_sentences": [{"id": "S1", "text": f"{c} claim [1]."},
                                             {"id": "S2", "text": "Second [1]."}],
                        "cited_papers": [{"label": "[1]", "title": "T", "authors": "A", "month": "2026-01",
                                          "abstract": "Abs."}]})
    return out


def test_sample_is_balanced_per_model_and_type():
    chosen = sheets.sample(_rows(), per_model=4)
    assert len(chosen) == 16
    for c in ("nano", "luna", "mini", "gpt-5.4"):
        mine = [r for r in chosen if r["candidate"] == c]
        assert sorted(r["query_type"] for r in mine) == ["keyword", "keyword", "question", "question"]
    assert chosen == sheets.sample(_rows(), per_model=4)


def test_workbook_is_blinded_and_round_trips(tmp_path):
    rows = sheets.blind(_rows()[:3], "t")
    path = tmp_path / "w.xlsx"
    sheets.write_workbook(rows, path, "GPT-5.4")
    wb = load_workbook(path)
    flat = " ".join(str(c.value) for ws in wb for row in ws.iter_rows() for c in row if c.value)
    assert "A-q-" not in flat and "candidate" not in flat
    key = {r["answer_id"]: {"candidate": r["candidate"], "item_id": r["item_id"],
                            "sentences": [s["text"] for s in r["answer_sentences"]]} for r in rows}
    with pytest.raises(ValueError, match="incomplete"):
        sheets.read_grades(path, key)
    for row in wb["Answers"].iter_rows(min_row=2):
        row[4].value, row[5].value = 2, "No"
    for row in wb["Sentences"].iter_rows(min_row=2):
        row[3].value, row[4].value = "Supported ", "ok"
    wb.save(path)
    grades = sheets.read_grades(path, key)
    assert set(grades) == set(key)
    g = next(iter(grades.values()))
    assert g["answers_request"] == 2 and [s["verdict"] for s in g["sentences"]] == ["supported"] * 2
    assert g["not_direct_answer"] is False
    api_view = {k: v for k, v in g.items() if k != "not_direct_answer"}
    assert sheets.ev.validate_grade(api_view, 2) == api_view
    wb["Sentences"]["C2"].value = "edited"
    wb.save(path)
    with pytest.raises(ValueError, match="changed"):
        sheets.read_grades(path, key)


def test_kappa_and_faithfulness():
    assert sheets._kappa([("a", "a"), ("b", "b")]) == 1
    assert sheets._kappa([("a", "b"), ("b", "a")]) == -1
    g = {"sentences": [{"verdict": "supported"}, {"verdict": "partial"}, {"verdict": "no_claim"}]}
    assert sheets._faithfulness(g) == 0.75
