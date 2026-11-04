import pytest

from arxiv_search.evaluate import llm_score_refine_pin as e2


def test_pin_first_restores_reference_rank1_and_keeps_other_order():
    assert e2.pin_first(["a", "b", "c", "d"], ["c", "a", "d", "b"]) == ["a", "c", "d", "b"]
    assert e2.pin_first(["a", "b"], ["a", "b"]) == ["a", "b"]
    with pytest.raises(ValueError):
        e2.pin_first(["z", "b"], ["a", "b"])


def test_plan_decides_on_unseen_queries_only():
    assert "new80" in e2.PLAN["evaluation_scope"] and e2.PLAN["held_out_queries_used"] is False
    assert e2.SYSTEM.endswith("+pin1-d46") and e2.PLAN["automatic_promotion"] is False
