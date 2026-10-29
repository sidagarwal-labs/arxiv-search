import json

import numpy as np
import pytest

from arxiv_search.evaluate import openai_field_experiment as fields, openai_full as full


def test_plan_has_same_model_controls_and_explicit_budget():
    plan = fields.plan()
    assert len(plan["settings"]) == 8
    assert plan["dimensions"] == 3072
    assert plan["budget"]["maximum_new_accounted_usd"] == .30
    assert plan["budget"]["shared_lifetime_usd"] == 1.25
    assert plan["automatic_promotion"] is False


def test_field_cosines_and_weight_endpoints():
    q = np.array([1., 0.])
    combined = np.array([[.6, .8], [.8, .6]])
    title = np.eye(2)
    abstract = title[::-1]
    assert np.allclose(fields.field_scores(q, combined, title, abstract, None), [.6, .8])
    assert np.allclose(fields.field_scores(q, combined, title, abstract, .25), [.25, .75])
    assert np.allclose(fields.field_scores(q, combined, title, abstract, 1), [1, 0])
    with pytest.raises(ValueError):
        fields.field_scores(q, combined, title, abstract, float("nan"))


def test_prefix_membership_tail_ties_and_no_source_injection():
    base = {"q": [f"p{i}" for i in range(100)]}
    raw = {"q": {"candidate_ids": base["q"], "concat": list(range(100)),
                 "title": list(reversed(range(100))), "abstract": list(range(100))}}
    runs = fields.build_runs(base, raw, fields.plan()["settings"])
    assert runs["oai-field+text=concat+d=10"]["q"][:10] == list(reversed(base["q"][:10]))
    assert runs["oai-field+text=concat+d=10"]["q"][10:] == base["q"][10:]
    assert all(set(r["q"]) == set(base["q"]) for r in runs.values())
    tied = {"q": {**raw["q"], "concat": [1.] * 100}}
    assert fields.build_runs(base, tied, fields.plan()["settings"])[
        "oai-field+text=concat+d=100"] == base


def test_capped_ledger_reuses_shared_guard_and_no_call_when_task_exceeded(tmp_path, monkeypatch):
    path = tmp_path / "ledger.sqlite3"
    ledger = fields.CappedLedger(path, 0)
    monkeypatch.setattr(fields, "LOCAL_CAP", full.PRICE * 10)
    ledger.reserve(10)
    with pytest.raises(full.BudgetExceeded, match="field experiment cap"):
        ledger.reserve(1)
    assert ledger.summary()["requests"] == 1
    shared = fields.CappedLedger(path, full.PRICE * 10)
    monkeypatch.setattr(full, "CAP", full.PRICE * 10)
    with pytest.raises(full.BudgetExceeded, match="lifetime"):
        shared.reserve(1)


@pytest.mark.parametrize("hybrid", [False, True])
@pytest.mark.parametrize("single_depth", [False, True])
def test_incomplete_grades_are_withheld_with_same_model_controls(tmp_path, hybrid, single_depth):
    from arxiv_search.evaluate import openai_field_hybrid
    from arxiv_search.evaluate.results_catalog import QUERY_TYPES

    papers = {f"p{i}": {"arxiv_id": f"p{i}", "title": str(i), "abstract": "Abstract"}
              for i in range(100)}
    queries = {f"q{i}": {"query_type": kind, "query": kind, "source_arxiv_id": "p0"}
               for i, kind in enumerate(QUERY_TYPES)}
    qids = sorted(queries)
    base = {q: list(papers) for q in qids}
    raw = {q: {"candidate_ids": base[q], "concat": list(range(100)),
               "title": list(range(100)), "abstract": list(range(100))} for q in qids}
    experiment = openai_field_hybrid.plan() if hybrid else fields.plan()
    if single_depth:
        experiment["settings"] = {n: v for n, v in experiment["settings"].items()
                                  if v["depth"] == 10}
    prefix = "oai-field-hybrid" if hybrid else "oai-field"
    runs = fields.build_runs(base, raw, experiment["settings"])
    snapshot = {"labels": {q: {f"p{i}": 2 if i == 0 else 0 for i in range(10)}
                            for q in qids}, "query_ids": qids}
    report = fields.publish(tmp_path, runs, snapshot, papers, queries, qids, experiment, {})
    assert report["systems"][f"{prefix}+text=title25+d=10"]["top10_fully_judged"]
    if not single_depth:
        assert not report["systems"][f"{prefix}+text=title25+d=100"]["top10_fully_judged"]
        assert report["summary"][f"{prefix}+text=title25+d=100"]["all"]["ndcg@10"][
            "paired_vs_working"] is None
    else:
        assert set(report["same_model_concat_comparisons"]) == {"10"}
    same = report["same_model_concat_comparisons"]["10"][f"{prefix}+text=title25+d=10"]
    assert same["all"]["ndcg@10"]["paired_vs_working"]["difference"] == 0
    assert json.loads((tmp_path / "report.json").read_text())["judge_api_calls"] == 0


def test_cached_hybrid_signal_preserves_fixed_weights_and_scale():
    from arxiv_search.evaluate import openai_field_hybrid as hybrid

    assert len(hybrid.plan()["settings"]) == 8
    assert hybrid.plan()["automatic_embedding_calls"] is False
    values = hybrid.hybrid_signal(np.array([2., 1., 0.]), np.array([.5, 1., .2]))
    assert np.allclose(values, [.625, .875, .15])
    assert np.allclose(hybrid.hybrid_signal(np.zeros(2), np.array([.5, 1.])), [.375, .75])
    with pytest.raises(ValueError):
        hybrid.hybrid_signal(np.array([-1.]), np.array([.2]))
