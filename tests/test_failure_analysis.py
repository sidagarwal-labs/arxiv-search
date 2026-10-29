import json

import pytest

from arxiv_search.evaluate import failure_analysis as analysis


def test_query_deltas_source_ranks_and_segments():
    queries = {
        "q": {"query": "topic", "query_type": "keyword", "category": "cs.IR",
              "specificity": "broad", "overlap": 0.5, "source_arxiv_id": "a"}}
    rows = analysis.query_rows({
        analysis.DENSE: {"q": ["b", "a"]}, analysis.HYBRID: {"q": ["a", "b"]}},
        {"q": {"a": 2, "b": 0}}, queries)
    row = rows[0]
    assert row["hybrid_minus_dense"] == pytest.approx(1 - 1 / 1.584962500721156)
    assert row["source_ranks"] == {analysis.DENSE: 2, analysis.HYBRID: 1}
    assert row["overlap_band"] == "high (>=0.5)"
    assert "| query_type | keyword | 1/1 |" in "\n".join(analysis.segment_report(rows))


def test_undefined_ndcg_is_explicit():
    queries = {"q": {"query": "topic", "query_type": "question", "category": "cs.CL",
                     "specificity": "broad", "overlap": 0.2, "source_arxiv_id": "missing"}}
    rows = analysis.query_rows({
        analysis.DENSE: {"q": ["a"]}, analysis.HYBRID: {"q": ["a"]}},
        {"q": {"a": 0}}, queries)
    assert rows[0]["hybrid_minus_dense"] is None
    assert rows[0]["source_ranks"][analysis.DENSE] is None
    assert "0/1 | undefined" in "\n".join(analysis.segment_report(rows))


def test_incomplete_snapshot_rejected_before_loading_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(analysis.graded, "OUT", tmp_path)
    (tmp_path / "labels.json").write_text(json.dumps({"complete": False}))
    with pytest.raises(ValueError, match="complete frozen"):
        analysis.main()


def test_changed_rubric_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(analysis.graded, "OUT", tmp_path)
    (tmp_path / "labels.json").write_text(json.dumps({
        "complete": True, "rubric_version": "old"}))
    with pytest.raises(ValueError, match="Rubric changed"):
        analysis.main()
