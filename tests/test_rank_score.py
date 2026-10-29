import math

import pytest

from arxiv_search.search.hybrid import fuse_rrf_baseline
from arxiv_search.search.rank_score import components, fuse_rank_score, rescore_shortlist
from arxiv_search.search.score_fusion import fuse_scores
from arxiv_search.evaluate import rank_score_experiment as experiment


def test_endpoints_and_theoretical_scaling():
    lexical = {f"p{i}": 200. - i for i in range(150)}
    semantic = {p: v / 200 for p, v in reversed(list(lexical.items()))}
    semantic = dict(sorted(semantic.items(), key=lambda item: -item[1]))
    assert fuse_rank_score(lexical, semantic, score_fraction=0, depth=500) == (
        fuse_rrf_baseline(list(lexical), list(semantic)))
    assert fuse_rank_score(lexical, semantic, score_fraction=1, depth=500) == (
        fuse_scores(lexical, semantic, normalization="max", semantic_weight=.75, depth=500))
    values = components(lexical, semantic, score_fraction=.5, depth=500)
    assert values["p0"]["normalized_rrf"] == pytest.approx(1)
    assert values["p0"]["max_score"] == 1
    assert values["p149"]["normalized_rrf"] == 0
    assert all(0 <= v["combined"] <= 1 for v in values.values())


def test_rank_evidence_can_recover_strong_semantic_only_hit():
    lex = {**{f"lex{i}": 10. - i / 1000 for i in range(149)}, "overlap": 9.}
    sem = {"target": 1., **{f"sem{i}": .99 for i in range(98)}, "overlap": .98}
    magnitude = fuse_rank_score(lex, sem, score_fraction=1, depth=500)
    rank_blend = fuse_rank_score(lex, sem, score_fraction=.25, depth=500)
    assert magnitude.index("target") > rank_blend.index("target")
    assert components(lex, sem, score_fraction=.5, depth=500)["target"]["max_score"] == .75


@pytest.mark.parametrize("options", [
    {"score_fraction": math.nan}, {"score_fraction": -.1}, {"score_fraction": 1.1},
    {"depth": 0}, {"k": -1},
])
def test_invalid_parameters(options):
    with pytest.raises(ValueError):
        fuse_rank_score({"a": 1.}, {}, **{"score_fraction": .5, "depth": 100, **options})


@pytest.mark.parametrize("scores", [{"a": math.inf}, {"a": -1.}, {"a": .1, "b": .2}])
def test_invalid_inputs(scores):
    with pytest.raises(ValueError):
        fuse_rank_score(scores, {}, score_fraction=.5, depth=100)


def test_fixed_plan_has_no_unbounded_grid():
    plan = experiment.plan()
    assert len(plan["settings"]) == 6
    assert {v["score_fraction"] for v in plan["settings"].values()} == {.25, .5, .75}
    assert {v["depth"] for v in plan["settings"].values()} == {100, 500}
    assert plan["automatic_api_calls"] is False
    shortlist = experiment.plan("shortlist")
    assert len(shortlist["settings"]) == 4
    assert {v["score_fraction"] for v in shortlist["settings"].values()} == {.5, 1.}


def test_shortlist_invariance_and_stable_zero_endpoint():
    lexical = {f"p{i}": 300. - i for i in range(150)}
    semantic = {f"p{i}": 300. + i for i in range(149, -1, -1)}
    baseline = fuse_rrf_baseline(list(lexical), list(semantic))
    assert rescore_shortlist(lexical, semantic, score_fraction=0, depth=500) == baseline
    for alpha in (.5, 1.):
        run = rescore_shortlist(lexical, semantic, score_fraction=alpha, depth=500)
        assert set(run[:10]) == set(baseline[:10])
        assert run[10:] == baseline[10:]
        assert set(run[:20]) == set(baseline[:20])
        assert len(run) == len(set(run)) == 100
        assert rescore_shortlist(lexical, semantic, score_fraction=alpha, depth=500, k=5) == run[:5]
