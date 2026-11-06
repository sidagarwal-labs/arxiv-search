import pytest

from arxiv_search.evaluate import top20_ablations as a, top20_model_pilot


def example():
    base = [str(i) for i in range(100)]
    presented = list(reversed(base[:20]))
    replies = [{f"P{i}": min(10, i // 2) for i in range(1, 21)},
               {f"P{i}": min(10, (21 - i) // 2) for i in range(1, 21)}]
    return base, presented, replies


def test_reference_matches_prior_pipeline():
    base, presented, replies = example()
    assert a.ranking(base, presented, replies, "equal_rrf", "average") == (
        top20_model_pilot.build_ranking(base, presented, replies))


@pytest.mark.parametrize("method", a.METHODS)
@pytest.mark.parametrize("passes", a.PASSES)
def test_all_variants_preserve_pin_pool_and_tail(method, passes):
    base, presented, replies = example()
    ranked = a.ranking(base, presented, replies, method, passes)
    assert ranked[0] == base[0] and set(ranked[:20]) == set(base[:20])
    assert ranked[20:] == base[20:] and len(set(ranked)) == len(ranked)


def test_single_pass_does_not_choose_using_second_pass():
    base, presented, replies = example()
    first = a.ranking(base, presented, replies, "scores_only", "pass1")
    changed = [replies[0], {f"P{i}": 0 for i in range(1, 21)}]
    assert a.ranking(base, presented, changed, "scores_only", "pass1") == first


def test_ties_keep_baseline_order():
    base, presented, _ = example()
    replies = [{f"P{i}": 5 for i in range(1, 21)}] * 2
    for method in a.METHODS:
        assert a.ranking(base, presented, replies, method, "average") == base


def test_bad_inputs_are_rejected():
    base, presented, replies = example()
    with pytest.raises(ValueError):
        a.ranking(base, presented, replies, "undeclared", "average")
    with pytest.raises(ValueError):
        a.ranking(base, presented[:-1], replies, "equal_rrf", "average")
