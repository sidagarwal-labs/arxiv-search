import pytest

from arxiv_search.search.rerank import rerank_pool, rerank_prefix


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
