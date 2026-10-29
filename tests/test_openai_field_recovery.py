import numpy as np
import pytest

from arxiv_search.evaluate import openai_field_recovery as recovery


def test_plan_is_bounded_global_and_top10_only():
    plan = recovery.plan()
    assert len(plan["settings"]) == 6
    assert {v["depth"] for v in plan["settings"].values()} == {10}
    assert not plan["automatic_embedding_calls"]
    assert not plan["automatic_promotion"]
    name = "oai-field-recovery+text=title25+anchor=0.5+d=10"
    description = recovery.catalog.describe_system(name)
    assert "50% combined-text anchor" in description["ranker"]
    assert "25% title / 75% abstract" in description["ranker"]


def test_semantic_ablation_and_anchor_formula():
    row = {"concat": [.4, .8], "title": [.8, .2], "abstract": [.2, .6]}
    assert np.allclose(recovery.semantic_signal(row, None, 1), row["concat"])
    assert np.allclose(recovery.semantic_signal(row, 0, 0), row["abstract"])
    assert np.allclose(recovery.semantic_signal(row, .1, 0), [.26, .56])
    field = .25 * np.array(row["title"]) + .75 * np.array(row["abstract"])
    assert np.allclose(recovery.semantic_signal(row, .25, .5),
                       .5 * np.array(row["concat"]) + .5 * field)
    for weight, anchor in ((None, 0), (.1, 2), (-1, 0), (.1, float("nan"))):
        with pytest.raises(ValueError):
            recovery.semantic_signal(row, weight, anchor)
    with pytest.raises(ValueError):
        recovery.semantic_signal({**row, "abstract": [1.]}, .1, 0)


def test_recovery_requires_other_segments_to_retain_challenger_gains():
    def groups(value):
        return {k: {"ndcg@10": {"mean": value}, "source_mrr@10": {"mean": .8}}
                for k in recovery.catalog.QUERY_TYPES}
    summary = {recovery.fields.BASELINE: groups(.7), recovery.CHALLENGER: groups(.72),
               "candidate": groups(.72)}
    assert recovery.recovery_checks(summary, "candidate")["passes"]
    summary["candidate"]["keyword"]["ndcg@10"]["mean"] = .71
    assert not recovery.recovery_checks(summary, "candidate")["passes"]
    summary["candidate"] = groups(.72)
    summary["candidate"]["paraphrase"]["source_mrr@10"]["mean"] = .79
    assert not recovery.recovery_checks(summary, "candidate")["passes"]
