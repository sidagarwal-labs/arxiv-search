import pytest

from arxiv_search.search.rerank import rerank_pool, rerank_prefix, score_rank_blend


def test_prefix_preserves_membership_tail_and_ties():
    assert rerank_prefix(["a", "b", "c"], {"a": 0., "b": 1.}, 2) == ["b", "a", "c"]
    assert rerank_prefix(["a", "b", "c"], {"a": 1., "b": 1.}, 2) == ["a", "b", "c"]


@pytest.mark.parametrize("scores,depth", [({"a": 1.}, 2),
                                         ({"a": float("nan")}, 1), ({"a": 1.}, 0)])
def test_prefix_rejects_bad_scores_and_depth(scores, depth):
    with pytest.raises(ValueError):
        rerank_prefix(["a", "b"], scores, depth)


def test_pool_can_promote_beyond_baseline_and_blend_preserves_base_endpoint():
    pool, scores = ["a", "b", "c"], {"a": -3., "b": -2., "c": 2.}
    assert rerank_pool(pool, scores, ["a", "b"], k=2) == ["c", "b"]
    assert rerank_pool(pool, scores, ["a", "b"], cross_weight=0, k=2) == ["a", "b"]
    assert rerank_pool(pool, dict.fromkeys(pool, 1.), ["a", "b"], k=3) == pool


@pytest.mark.parametrize("pool,scores,base,weight,k", [
    (["a", "a"], {"a": 1.}, ["a"], 1., 1),
    (["a"], {"a": 1., "b": 2.}, ["a"], 1., 1),
    (["a"], {"a": float("inf")}, ["a"], 1., 1),
    (["a"], {"a": 1.}, ["b"], 1., 1),
    (["a"], {"a": 1.}, ["a"], float("nan"), 1),
    (["a"], {"a": 1.}, ["a"], 1., 2),
])
def test_pool_rejects_invalid_inputs(pool, scores, base, weight, k):
    with pytest.raises(ValueError):
        rerank_pool(pool, scores, base, cross_weight=weight, k=k)


def test_score_rank_blend_interpolates_between_llm_and_retrieval_order():
    ranking = ["a", "b", "c", "d", "tail"]
    scores = {"a": 0.0, "b": 4.0, "c": 3.0, "d": 3.0}
    # beta=0 is exactly the LLM-score order; equal scores keep retrieval order.
    assert score_rank_blend(ranking, scores, 4, 0, 30) == ["b", "c", "d", "a", "tail"]
    # A small prior cannot overturn a one-point gap but breaks near-ties the same way.
    assert score_rank_blend(ranking, scores, 4, 0.5, 30) == ["b", "c", "d", "a", "tail"]
    # A huge prior reproduces the retrieval order; the tail never moves.
    assert score_rank_blend(ranking, scores, 4, 1000, 30) == ranking
    # a gets 0 + 4 = 4.0; b gets 4 + 4*31/32 = 7.9, so the large LLM gap still wins.
    assert score_rank_blend(ranking, scores, 4, 4, 30)[0] == "b"


def test_score_rank_blend_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        score_rank_blend(["a", "b"], {"a": 1.0, "b": 0.0}, 2, -1, 30)
    with pytest.raises(ValueError):
        score_rank_blend(["a", "b"], {"a": 1.0}, 2, 1, 30)
