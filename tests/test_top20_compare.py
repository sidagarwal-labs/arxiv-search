import json
from collections import Counter

import pytest

from arxiv_search.evaluate import top20_compare as experiment


def test_graph_is_regular_and_has_forty_unique_pairs():
    pairs = experiment.pairs()
    assert len(pairs) == len(set(pairs)) == 40
    assert set(Counter(i for pair in pairs for i in pair).values()) == {4}
    assert all(0 <= i < j < 20 for i, j in pairs)


def test_reversal_swaps_same_physical_papers():
    ids = [str(i) for i in range(20)]
    papers = {p: {"title": p, "authors": ["A"], "abstract": "Evidence"} for p in ids}
    inputs = [json.loads(json.loads(experiment.encode("Q", ids, papers, reverse))["input"])
              for reverse in (False, True)]
    maps = [{p["label"]: p["title"] for p in body["papers"]} for body in inputs]
    for k in inputs[0]["comparisons"]:
        a, b = [body["comparisons"][k] for body in inputs]
        assert maps[0][a["A"]] == maps[1][b["B"]]
        assert maps[0][a["B"]] == maps[1][b["A"]]


def test_ranking_ties_preserve_d47_and_pin_is_explicit():
    ids = [str(i) for i in range(20)]
    ties = {f"C{i}": "tie" for i in range(1, 41)}
    assert experiment.rank(ids, [ties, ties]) == ids
    replies = [{}, {}]
    for n, (i, j) in enumerate(experiment.pairs(), 1):
        # A synthetic total preference with larger original index preferred.
        replies[0][f"C{n}"] = "B"
        replies[1][f"C{n}"] = "A"
    result = experiment.rank(ids, replies)
    assert result[0] == ids[0] and set(result) == set(ids)
    with pytest.raises(ValueError):
        experiment.rank(ids, [ties, {}])


def test_response_validation_is_exact():
    valid = {f"C{i}": "tie" for i in range(1, 41)}
    assert experiment.validate(valid) == valid
    for bad in ({}, {**valid, "C1": "unknown"}, {**valid, "extra": "A"}, []):
        with pytest.raises(ValueError):
            experiment.validate(bad)
