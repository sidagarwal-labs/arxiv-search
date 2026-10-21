"""Tests for evaluate/metrics.py. Every expected number can be checked by hand.

Papers are single letters to keep the examples readable.
"""

import math

import pytest

from arxiv_search.evaluate.metrics import (
    bootstrap_ci,
    dcg,
    judged_at_k,
    ndcg_at_k,
    paired_diff_ci,
    reciprocal_rank,
    recall_at_k,
    score_run,
    summarize,
)

RANKED = ["A", "B", "C", "D", "E"]


# --- Recall@k ---------------------------------------------------------------


def test_recall_single_answer_is_hit_or_miss():
    grades = {"C": 2}  # the one right answer is at rank 3
    assert recall_at_k(RANKED, grades, k=1) == 0.0
    assert recall_at_k(RANKED, grades, k=3) == 1.0


def test_recall_multiple_answers_counts_share_found():
    grades = {"B": 2, "D": 1}
    assert recall_at_k(RANKED, grades, k=2) == 0.5  # found B only
    assert recall_at_k(RANKED, grades, k=4) == 1.0  # found B and D


def test_recall_ignores_grade_zero():
    # A was judged "not relevant" (0), so finding it doesn't count.
    assert recall_at_k(RANKED, {"A": 0, "E": 1}, k=1) == 0.0


# --- MRR ----------------------------------------------------------------------


def test_reciprocal_rank():
    assert reciprocal_rank(RANKED, {"A": 2}) == 1.0
    assert reciprocal_rank(RANKED, {"C": 2}) == pytest.approx(1 / 3)
    assert reciprocal_rank(RANKED, {"Z": 2}) == 0.0  # never found


def test_reciprocal_rank_uses_first_relevant_paper():
    assert reciprocal_rank(RANKED, {"B": 1, "D": 2}) == 0.5  # B at rank 2 comes first


def test_reciprocal_rank_cutoff():
    ranked = [f"x{i}" for i in range(10)] + ["hit"]  # right paper at rank 11
    assert reciprocal_rank(ranked, {"hit": 2}, cutoff=10) == 0.0
    assert reciprocal_rank(ranked, {"hit": 2}, cutoff=11) == pytest.approx(1 / 11)


# --- nDCG -----------------------------------------------------------------------


def test_dcg_discounts_by_log2_of_rank_plus_one():
    # rank 1: 2/log2(2) = 2.0;  rank 3: 1/log2(4) = 0.5
    assert dcg([2, 0, 1]) == pytest.approx(2.5)


def test_ndcg_worked_example():
    grades = {"A": 0, "B": 2, "C": 1}
    ours = 0 / 1 + 2 / math.log2(3) + 1 / 2  # 1.762
    ideal = 2 / 1 + 1 / math.log2(3) + 0 / 2  # 2.631 (order B, C, A)
    assert ndcg_at_k(["A", "B", "C"], grades, k=3) == pytest.approx(ours / ideal)
    assert ndcg_at_k(["A", "B", "C"], grades, k=3) == pytest.approx(0.670, abs=0.001)


def test_ndcg_perfect_and_empty():
    grades = {"A": 2, "B": 1}
    assert ndcg_at_k(["A", "B", "C"], grades) == pytest.approx(1.0)
    assert ndcg_at_k(["X", "Y"], grades) == 0.0


def test_ndcg_unjudged_counts_as_zero():
    # Z was never judged, so it earns 0 just like a "not relevant" paper.
    assert ndcg_at_k(["Z", "A"], {"A": 2}, k=2) == ndcg_at_k(["N", "A"], {"A": 2, "N": 0}, k=2)


def test_ndcg_undefined_when_nothing_relevant():
    assert ndcg_at_k(RANKED, {"A": 0, "B": 0}) is None


def test_judged_at_k():
    grades = {"A": 2, "B": 0}  # C, D, E never judged
    assert judged_at_k(RANKED, grades, k=5) == 0.4  # 2 of 5 have a grade


# --- Whole run ------------------------------------------------------------------


def test_score_run_scores_missing_queries_as_zero():
    run = {"q1": ["A", "B"]}  # system returned nothing for q2
    labels = {"q1": {"A": 2}, "q2": {"B": 2}}
    rows = {row["query_id"]: row for row in score_run(run, labels)}
    assert rows["q1"]["recall@1"] == 1.0
    assert rows["q1"]["mrr@10"] == 1.0
    assert rows["q2"]["recall@20"] == 0.0
    assert rows["q2"]["mrr@10"] == 0.0


# --- Uncertainty ----------------------------------------------------------------


def test_bootstrap_identical_values_have_no_spread():
    assert bootstrap_ci([0.5] * 50) == (0.5, 0.5, 0.5)


def test_bootstrap_interval_contains_mean_and_is_repeatable():
    values = [1.0] * 30 + [0.0] * 70  # true mean 0.3
    mean, low, high = bootstrap_ci(values)
    assert mean == pytest.approx(0.3)
    assert low < 0.3 < high
    assert 0.15 < low and high < 0.45  # roughly ±0.09 for 100 yes/no values
    assert bootstrap_ci(values) == (mean, low, high)  # fixed seed -> same answer


def test_paired_diff_detects_consistent_improvement():
    a = [0.0, 0.5, 0.2, 0.0, 1.0] * 20
    b = [x + 0.1 for x in a]  # B is better by exactly 0.1 on every query
    diff, low, high = paired_diff_ci(a, b)
    assert diff == pytest.approx(0.1)
    assert low == pytest.approx(0.1) and high == pytest.approx(0.1)


def test_paired_diff_requires_same_queries():
    with pytest.raises(ValueError):
        paired_diff_ci([1.0, 0.0], [1.0])


def test_summarize_groups():
    rows = [
        {"query_id": "q1", "mrr@10": 1.0, "ndcg@10": None},
        {"query_id": "q2", "mrr@10": 0.5, "ndcg@10": 0.8},
        {"query_id": "q3", "mrr@10": 0.0, "ndcg@10": 0.4},
    ]
    summary = summarize(rows, group_by={"q1": "cs.IR", "q2": "cs.IR", "q3": "cs.CL"})
    assert summary["all"]["n"] == 3
    assert summary["all"]["mrr@10"][0] == pytest.approx(0.5)
    assert summary["cs.IR"]["mrr@10"][0] == pytest.approx(0.75)
    assert summary["all"]["ndcg@10"][0] == pytest.approx(0.6)  # q1's None is skipped
