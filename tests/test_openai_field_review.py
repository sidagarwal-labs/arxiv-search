import numpy as np
import pytest

from arxiv_search.evaluate import openai_field_review as review


def test_concentration_removes_actual_largest_gains():
    values = {str(i): float(i) for i in range(6)}
    result = review.concentration(values)
    assert result["excluding_largest_gains"]["3"]["excluded"] == ["5", "4", "3"]
    assert result["excluding_largest_gains"]["3"]["mean_delta"] == 1
    assert result["leave_one_out_mean_range"] == [2., 3.]
    with pytest.raises(ValueError):
        review.concentration({})


def test_weighted_evidence_reconstructs_hybrid_and_alignment_is_required():
    ids = ["a", "b"]
    row = {"candidate_ids": ids, "title": [.8, .2], "abstract": [.4, .6],
           "concat": [.5, .5]}
    parts = review.evidence(ids, row, {"a": 2})
    assert np.isclose(parts["a"]["lexical"], .25)
    assert parts["b"]["lexical"] == 0
    assert np.isclose(sum(parts["a"][f] for f in ("lexical", "title", "abstract")),
                      parts["a"]["total"])
    with pytest.raises(ValueError):
        review.evidence(ids[::-1], row, {})


def test_harmful_inversion_and_title_decisive_margin():
    ids = [str(i) for i in range(10)]
    parts = {p: {"lexical": 0., "title": 0., "abstract": .5, "total": .5} for p in ids}
    parts["1"] = {"lexical": 0., "title": .2, "abstract": .4, "total": .6}
    after = [ids[1], ids[0], *ids[2:]]
    grades = {p: 0 for p in ids}
    grades["0"] = 2
    flips = review.inversions(ids, after, grades, parts)
    assert len(flips) == 1
    assert flips[0]["grade_difference"] == -2
    assert flips[0]["title_decisive_at_fixed_normalizer"]
    with pytest.raises(ValueError):
        review.inversions(ids, ids[:-1], grades, parts)


def test_label_sensitivity_recomputes_both_ideals_without_mutation():
    grades = {"a": 2, "b": 1, "c": 2}
    original = grades.copy()
    result = review.label_sensitivity(["b", "a"], ["a", "b"], grades)
    assert result["change_to_query_delta"] < 0
    assert abs(result["from"] - result["to"]) == 1
    assert grades == original
