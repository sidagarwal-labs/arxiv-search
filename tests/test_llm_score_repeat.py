from arxiv_search.evaluate import llm_score_repeat as repeat


def test_score_agreement_counts_changes():
    a = {"P1": 4, "P2": 2, "P3": 0, "P4": 1}
    b = {"P1": 4, "P2": 3, "P3": 2, "P4": 1}
    out = repeat.score_agreement(a, b)
    assert out == {"pairs": 4, "exact": 2, "changed_by_1": 1, "changed_by_2plus": 1,
                   "mean_abs_change": 0.75, "mean_change": 0.75}


def test_plan_has_no_judge_calls_or_promotion():
    assert repeat.PLAN["judge_api_calls"] == 0 and repeat.PLAN["automatic_promotion"] is False
    assert repeat.PLAN["automatic_retries"] is False
