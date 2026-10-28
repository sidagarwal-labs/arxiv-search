import pytest

from arxiv_search import config
from arxiv_search.evaluate import judge
from arxiv_search.evaluate.metrics import cohen_kappa


def test_kappa_hand_worked():
    a, b = [0, 1, 2, 2], [0, 1, 2, 1]
    # Unweighted: observed disagreement 1/4, chance 11/16 -> 1 - 4/11.
    assert cohen_kappa(a, b) == pytest.approx(1 - 4 / 11)
    # Quadratic: observed cost 1/4; chance cost .375 + .125 + .75 = 1.25 -> 1 - .2.
    assert cohen_kappa(a, b, weights="quadratic") == pytest.approx(0.8)
    assert cohen_kappa([0, 2, 1], [0, 2, 1]) == 1.0
    assert cohen_kappa([1, 1], [1, 1]) != cohen_kappa([1, 1], [1, 1])  # nan: nothing to agree on


PAPERS = {f"p{i}": {"arxiv_id": f"p{i}", "title": f"Title {i}", "abstract": f"Abstract {i}",
                    "authors": ["A. Author"]} for i in range(5)}
QUERY = {"query_id": "q1", "query": "graph retrieval"}


def fake_call(calls):
    """Grades each paper by its number (p0 -> 0, p1 -> 1, p2+ -> 2), reading the prompt."""
    def call(prompt):
        calls.append(prompt)
        grades = []
        for block in prompt.split("\n\n"):
            if block.startswith("[P"):
                label, number = block[1:block.index("]")], int(block.split("Title ")[1].split("\n")[0])
                grades.append(judge.PaperGrade(paper=label, reason="r", grade=min(number, 2)))
        return judge.Grades(grades=grades), {}
    return call


def test_judge_query_maps_shuffled_labels_back_and_stays_blind():
    calls = []
    rows = judge.judge_query("gemma-31b", QUERY, list(PAPERS.values()), fake_call(calls))
    assert {r["arxiv_id"]: r["grade"] for r in rows} == {"p0": 0, "p1": 1, "p2": 2, "p3": 2, "p4": 2}
    assert "p3" not in calls[0]  # arxiv IDs never shown; papers are labeled P1, P2, ...
    again = judge.judge_query("gemma-31b", QUERY, list(PAPERS.values()), fake_call([]))
    assert [r["position"] for r in rows] == [r["position"] for r in again]  # same shuffle every run


def test_check_answer_rejects_missing_extra_and_bad_grades():
    g = lambda label, grade=1: judge.PaperGrade(paper=label, reason="", grade=grade)
    assert judge.check_answer(judge.Grades(grades=[g("P1"), g("P2")]), ["P1", "P2"]) is None
    assert "missing" in judge.check_answer(judge.Grades(grades=[g("P1")]), ["P1", "P2"])
    assert judge.check_answer(judge.Grades(grades=[g("P1"), g("P1")]), ["P1", "P2"])
    assert judge.check_answer(judge.Grades(grades=[g("P1", 3)]), ["P1"]) == "grade outside 0-2"


def test_bad_answer_is_asked_again():
    answers = [judge.Grades(grades=[]), None]

    def call(prompt):
        if answers[0] is not None:
            bad, answers[0] = answers[0], None
            return bad, {}
        return fake_call([])(prompt)

    rows = judge.judge_query("gemma-31b", QUERY, [PAPERS["p1"]], call)
    assert rows[0]["attempts"] == 2 and rows[0]["grade"] == 1


def test_cache_skips_graded_pairs_and_regrades_changed_text(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JUDGMENTS_DIR", tmp_path)
    queries = {"q1": QUERY}
    pairs = {"q1": ["p0", "p1", "p2"]}
    calls = []
    first = judge.judge_pairs("gemma-31b", pairs, queries, PAPERS, call=fake_call(calls))
    assert first == {"cached": 0, "judged": 3, "calls": 1}
    second = judge.judge_pairs("gemma-31b", pairs, queries, PAPERS, call=fake_call(calls))
    assert second == {"cached": 3, "judged": 0, "calls": 0} and len(calls) == 1
    # A new paper only costs that paper.
    third = judge.judge_pairs("gemma-31b", {"q1": ["p0", "p3"]}, queries, PAPERS, call=fake_call(calls))
    assert third == {"cached": 1, "judged": 1, "calls": 1}
    # Different query wording -> different key -> graded again.
    changed = {"q1": {**QUERY, "query": "graph search"}}
    assert judge.judge_pairs("gemma-31b", pairs, changed, PAPERS, call=fake_call(calls))["judged"] == 3
    assert judge.grades_for("gemma-31b", pairs, queries, PAPERS) == {"q1": {"p0": 0, "p1": 1, "p2": 2}}
    # Each judge has its own cache.
    assert judge.grades_for("qwen2.5-7b", pairs, queries, PAPERS) == {}


def test_max_calls_stops_and_rerun_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JUDGMENTS_DIR", tmp_path)
    queries = {"q1": QUERY, "q2": {"query_id": "q2", "query": "other"}}
    pairs = {"q1": ["p0"], "q2": ["p1"]}
    assert judge.judge_pairs("gemma-31b", pairs, queries, PAPERS, call=fake_call([]), max_calls=1)["calls"] == 1
    assert judge.judge_pairs("gemma-31b", pairs, queries, PAPERS, call=fake_call([])) == \
        {"cached": 1, "judged": 1, "calls": 1}
