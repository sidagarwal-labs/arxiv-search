import json

import pytest

from arxiv_search.evaluate import metrics
from arxiv_search.evaluate.top20_reasoning_diagnostics import disagreements


def test_contributions_reconcile_and_boundary_changes():
    before = [str(i) for i in range(20)]
    after = before.copy()
    after[1], after[10] = after[10], after[1]
    grades = {p: 1 for p in before}
    grades["1"], grades["10"] = 0, 2
    result = disagreements(before, after, grades)
    assert result["delta"] == pytest.approx(
        metrics.ndcg_at_k(after, grades) - metrics.ndcg_at_k(before, grades))
    assert result["entrants"] == ["10"]
    assert result["exits"] == ["1"]
    assert result["entrants_by_grade"] == {"2": 1}
    assert result["exits_by_grade"] == {"0": 1}
    assert json.loads(json.dumps(result)) == result
    assert result["unequal_grade_inversions_corrected"] == 17
    assert result["unequal_grade_inversions_introduced"] == 0
    reverse = disagreements(after, before, grades)
    assert reverse["delta"] == pytest.approx(-result["delta"])
    assert reverse["unequal_grade_inversions_introduced"] == 17


def test_equal_grades_reordering_has_no_gain_or_inversion():
    ids = [str(i) for i in range(20)]
    result = disagreements(ids, list(reversed(ids)), dict.fromkeys(ids, 1))
    assert result["delta"] == pytest.approx(0, abs=1e-12)
    assert result["unequal_grade_inversions_corrected"] == 0
    assert result["unequal_grade_inversions_introduced"] == 0


def test_diagnostic_rejects_missing_or_different_evidence():
    ids = [str(i) for i in range(20)]
    for other in (ids[:-1], ids[:-1] + ["extra"], ids[:-1] + [ids[0]]):
        with pytest.raises(ValueError):
            disagreements(ids, other, dict.fromkeys(ids, 1))
    with pytest.raises(ValueError):
        disagreements(ids, ids, dict.fromkeys(ids[:-1], 1))
    with pytest.raises(ValueError):
        disagreements(ids, ids, dict.fromkeys(ids, 0))
