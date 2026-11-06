import math

import pytest

from arxiv_search.evaluate.rerank_loss import COMPONENTS, aggregate, decompose


def test_loss_components_telescope_with_a_single_denominator():
    ranked = [f"p{i}" for i in range(50)]
    grades = {p: 0 for p in ranked}
    grades.update(p1=1, p15=2, p30=2, outside=2)
    row = decompose(ranked, ranked, grades)
    scores = list(row["scores"].values())
    assert scores == sorted(scores)
    assert all(row["loss"][k] > 0 for k in COMPONENTS)
    assert math.isclose(sum(row["loss"].values()), 1 - row["scores"]["actual"])
    assert row["pin1_top20_oracle_penalty"] > 0
    assert row["grade_counts"]["ranks11_20"]["2"] == 1
    summary = aggregate([row])
    assert math.isclose(sum(v["share_of_top50_gap"] or 0
                            for v in summary["loss"].values()), 1)


def test_perfect_top10_has_no_artificial_loss_and_unknown_is_reported():
    ranked = [f"p{i}" for i in range(50)]
    row = decompose(ranked, ranked, {p: 2 for p in ranked[:10]})
    assert row["scores"]["actual"] == 1
    assert sum(row["loss"].values()) == 0
    assert aggregate([row])["unjudged_top50"] == 40
    assert aggregate([row])["grade_counts"]["top10"]["2"] == 10
    assert aggregate([row])["grade_counts"]["ranks11_20"]["unjudged"] == 10
    assert all(v["share_of_top50_gap"] is None for v in aggregate([row])["loss"].values())


def test_scope_and_judgment_guards():
    ranked = [f"p{i}" for i in range(50)]
    grades = {p: 1 for p in ranked}
    for run, pool, labels in [
        (ranked[:-1], ranked, grades),
        ([ranked[0]] * 50, ranked, grades),
        (ranked, [*ranked[:-1], "different"], grades),
        (ranked, ranked, {}),
        (ranked, ranked, {**grades, "p0": 3}),
    ]:
        with pytest.raises(ValueError):
            decompose(run, pool, labels)
    with pytest.raises(ValueError):
        aggregate([])
