import json

import pytest

from arxiv_search.evaluate import cross_encoder_experiment as ce


def test_plan_pins_model_and_does_not_promote_or_pay(monkeypatch):
    assert len(ce.plan()["settings"]) == 5
    assert len(ce.plan()["revision"]) == 40
    assert ce.plan()["paid_calls"] is False
    assert ce.plan()["automatic_promotion"] is False
    monkeypatch.setattr(ce.config, "WORKING_BASELINE_SYSTEM", "future-baseline")
    assert ce.plan()["baseline"] == "fusion-shortlist+a=1+d=500"


def test_frozen_plan_rejects_changed_settings(tmp_path):
    path = tmp_path / "plan.json"
    ce.freeze(path, ce.plan())
    ce.freeze(path, ce.plan())
    with pytest.raises(ValueError, match="frozen"):
        ce.freeze(path, {"changed": True})


def test_pool_never_injects_source_and_has_stable_deduplication():
    base = [str(i) for i in range(100)]
    pool = ce.candidate_pool(base, base[20:] + [f"x{i}" for i in range(20)], base)
    assert pool == base + [f"x{i}" for i in range(20)]
    with pytest.raises(ValueError):
        ce.candidate_pool(base[:99], base, base)


def test_score_cache_fails_closed_on_text_revision_or_membership_changes(tmp_path):
    path = tmp_path / "cache.json"
    papers = {"a": {"title": "Title", "abstract": "Abstract"}}
    key = ce.cache_key("query", ["a"], papers)
    assert ce.read_scores(path, key, ["a"]) is None
    path.write_text(json.dumps({"input_sha256": key, "scores": {"a": 1.}, "pairs": 1}))
    assert ce.read_scores(path, key, ["a"])["scores"] == {"a": 1.}
    papers["a"]["abstract"] = "Changed"
    with pytest.raises(ValueError, match="inputs changed"):
        ce.read_scores(path, ce.cache_key("query", ["a"], papers), ["a"])
    with pytest.raises(ValueError, match="invalid or incomplete"):
        ce.read_scores(path, key, ["b"])


def test_build_runs_changes_prefix_only_and_preserves_100_results():
    base = {"q": [str(i) for i in range(100)]}
    pool = {"q": base["q"] + ["new"]}
    scores = {"q": {p: float(i) for i, p in enumerate(pool["q"])}}
    runs = ce.build_runs(base, pool, scores)
    assert len(runs) == 5
    assert runs["cross-minilm-l6+pool=baseline+d=10"]["q"][:10] == list(reversed(base["q"][:10]))
    assert runs["cross-minilm-l6+pool=baseline+d=10"]["q"][10:] == base["q"][10:]
    assert runs["cross-minilm-l6+pool=union100+w=1"]["q"][0] == "new"
    assert all(len(r["q"]) == 100 for r in runs.values())


def test_score_cache_accepts_sorted_json_keys_but_preserves_declared_pool_ties(tmp_path):
    from arxiv_search.evaluate.fusion_experiment import _write_json
    from arxiv_search.search.rerank import rerank_pool

    path = tmp_path / "cache.json"
    pool = ["z", "a"]
    _write_json(path, {"input_sha256": "key", "scores": dict.fromkeys(pool, 1.), "pairs": 2})
    cached = ce.read_scores(path, "key", pool)
    assert rerank_pool(pool, cached["scores"], pool, k=2) == pool


def test_incomplete_report_withholds_graded_comparisons_but_keeps_source_metrics(tmp_path):
    from arxiv_search.evaluate.results_catalog import QUERY_TYPES

    papers = {f"p{i}": {"arxiv_id": f"p{i}", "title": f"Title {i}", "abstract": "Abstract"}
              for i in range(101)}
    queries = {f"q{i}": {"query_type": kind, "query": kind, "source_arxiv_id": "p0"}
               for i, kind in enumerate(QUERY_TYPES)}
    qids = sorted(queries)
    baseline = {q: [f"p{i}" for i in range(100)] for q in qids}
    candidate = {q: ["p100"] + baseline[q][:99] for q in qids}
    snapshot = {"labels": {q: {f"p{i}": 2 if i == 0 else 0 for i in range(10)}
                            for q in qids}, "query_ids": qids}
    report = ce.report_runs(tmp_path, {"base": baseline, "candidate": candidate}, snapshot,
                            papers, queries, qids, "base",
                            {"pairs": 404, "seconds": 0., "truncated_documents": 0})
    assert report["missing_pairs"] == 4
    result = report["systems"]["candidate"]
    assert result["paired_ndcg_vs_working_baseline"] is None
    assert result["all"]["source_mrr@10"]["mean"] == .5
    assert report["summary"]["candidate"]["all"]["ndcg@10"]["paired_vs_working"] is None
    assert report["summary"]["candidate"]["all"]["source_mrr@10"]["paired_vs_working"]
    assert report["screens"]["candidate"]["passes"] is False
    assert "PROVISIONAL" in (tmp_path / "report.md").read_text()
