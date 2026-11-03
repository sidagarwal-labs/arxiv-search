import pytest

from arxiv_search import config
from arxiv_search.evaluate import judge, llm_score_judge_fill as fill
from tests.test_judge import PAPERS, QUERY, fake_call


def test_missing_pairs_unions_top10_of_every_run_minus_labels():
    runs = {"a": {"q": ["p1", "p2"] + [f"x{i}" for i in range(20)]},
            "b": {"q": ["p3", "p1"]}}
    labels = {"q": {"p1": 2, **{f"x{i}": 0 for i in range(8)}}}
    assert fill.missing_pairs(runs, labels, ["q"]) == {"q": ["p2", "p3"]}  # x8+ are below top10


def test_child_labels_adds_but_never_changes_frozen_grades():
    parent = {"q": {"p1": 2}}
    assert fill.child_labels(parent, {"q": {"p2": 0}}) == {"q": {"p1": 2, "p2": 0}}
    assert parent == {"q": {"p1": 2}}
    assert fill.child_labels(parent, {"q": {"p1": 2}}) == parent
    with pytest.raises(ValueError, match="frozen grade"):
        fill.child_labels(parent, {"q": {"p1": 1}})
    with pytest.raises(ValueError, match="invalid grade"):
        fill.child_labels(parent, {"q": {"p2": 3}})


def test_no_retry_stops_instead_of_reasking_after_invalid_answer():
    calls = []

    def bad(prompt):
        calls.append(prompt)
        return judge.Grades(grades=[judge.PaperGrade(paper="P1", reason="r", grade=0)]), {}

    with pytest.raises(RuntimeError, match="without retry"):
        judge.judge_query("gemma-31b", QUERY, list(PAPERS.values())[:2], fill.no_retry(bad))
    assert len(calls) == 1


def test_batches_match_what_judge_pairs_sends(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "JUDGMENTS_DIR", tmp_path)
    monkeypatch.setattr(config, "OPENAI_JUDGE_MAX_PAPERS_PER_CALL", 2)
    queries = {"q1": QUERY}
    pairs = {"q1": list(PAPERS)}
    planned = judge.batches("openai-mini", pairs, queries, PAPERS, {})
    assert [len(b) for _, b in planned] == [2, 2, 1]
    prompts = []
    judge.judge_pairs("openai-mini", pairs, queries, PAPERS, call=fake_call(prompts))
    assert prompts == [judge.presentation(QUERY, b)[2] for _, b in planned]
    assert judge.batches("openai-mini", pairs, queries, PAPERS, judge.load_judgments("openai-mini")) == []


def test_estimate_counts_calls_papers_and_bounds_cost():
    planned = [("q1", list(PAPERS.values())[:3]), ("q1", list(PAPERS.values())[3:])]
    out = fill.estimate(planned, {"q1": QUERY})
    assert (out["calls"], out["papers"]) == (2, 5)
    assert out["input_token_estimate"] > 0
    assert 0 < out["expected_usd"] < out["worst_case_usd"]
    assert out["max_single_reservation_tokens"] > config.OPENAI_MAX_OUTPUT_TOKENS


def test_run_calls_restores_attempt_limit_and_saves_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "JUDGMENTS_DIR", tmp_path)
    seen = []

    def call(prompt):
        seen.append(config.OPENAI_MAX_ATTEMPTS)
        return fake_call([])(prompt)

    state = {"judge_key": "openai-mini", "queries": {"q1": QUERY},
             "calls": [("q1", list(PAPERS.values())[:2])]}
    before = config.OPENAI_MAX_ATTEMPTS
    sent = fill.run_calls(state, call)
    assert seen == [1] and config.OPENAI_MAX_ATTEMPTS == before
    assert len(sent["rows"]) == 2 and len(judge.load_judgments("openai-mini")) == 2


def test_run_calls_stops_before_a_call_that_could_exceed_the_ceiling(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "JUDGMENTS_DIR", tmp_path)
    prompts = []

    def call(prompt):
        answer, _ = fake_call(prompts)(prompt)
        return answer, {"input_tokens": 1_000, "output_tokens": 100}

    papers = list(PAPERS.values())
    state = {"judge_key": "openai-mini", "queries": {"q1": QUERY},
             "calls": [("q1", papers[:2]), ("q1", papers[2:])]}
    planned = [{"input_token_estimate": 1_000}] * 2
    one_call = fill.call_worst_usd(planned[0])
    with pytest.raises(RuntimeError, match="stopped before sending"):
        fill.run_calls(state, call, planned=planned, cap_usd=one_call + 1e-7)  # first call costs 1.2e-6
    assert len(prompts) == 1 and len(judge.load_judgments("openai-mini")) == 2
