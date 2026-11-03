import pytest

from arxiv_search.evaluate import llm_score_safeguard as guard


def test_fuse_rescues_a_baseline_top_paper_the_llm_buried():
    base = [f"p{i}" for i in range(1, 61)]
    llm = base[1:15] + ["p1"] + base[15:50] + base[50:]  # p1 sinks to LLM rank 15
    fused = guard.fuse(base, llm)
    assert fused.index("p1") == 6  # 1/31+1/45=.0545 trails p7 (1/37+1/36=.0548), beats p8
    assert fused[50:] == base[50:]
    assert sorted(fused[:50]) == sorted(base[:50])


def test_fuse_equal_scores_keep_baseline_order_and_reject_changed_prefix():
    base = ["a", "b", "c"]
    assert guard.fuse(base, ["b", "a", "c"], depth=3) == ["a", "b", "c"]
    with pytest.raises(ValueError, match="same papers"):
        guard.fuse(base, ["a", "b", "x"], depth=3)
