import json

import pytest

from arxiv_search import config
from arxiv_search.evaluate import graded


def test_precision_ndcg_and_unjudged_hand_worked():
    rows = graded.score_graded(
        {"q": ["a", "b", "c"], "empty": []},
        {"q": {"a": 0, "b": 2, "c": 1}, "empty": {}},
        {"q": {"query_type": "keyword"}, "empty": {"query_type": "question"}}, k=3)
    assert rows[0]["precision@3"] == pytest.approx(2 / 3)
    assert rows[0]["ndcg@3"] == pytest.approx(0.670, abs=0.001)
    assert rows[0]["judged@3"] == 1
    assert rows[1]["precision@3"] == 0
    assert rows[1]["ndcg@3"] is None
    assert rows[1]["judged@3"] == 0


def test_human_overrides_zero_and_adds_source(monkeypatch):
    monkeypatch.setattr(graded.judge, "grades_for", lambda *args: {"q": {"a": 2}})
    labels, count = graded.merged_labels(
        {"q": ["a"], "q2": ["b"]}, {}, {"a": {}, "source": {}},
        {("q", "a"): 0, ("q", "source"): 2})
    assert labels == {"q": {"a": 0, "source": 2}, "q2": {}}
    assert count == 2


def test_pool_deduplicates_without_losing_zero_labels():
    runs = {"a": {"q": ["p1", "p2"]}, "b": {"q": ["p2", "p3"]}}
    assert graded.pooled_pairs(runs, ["q"], 2) == {"q": ["p1", "p2", "p3"]}


def test_run_validation_rejects_missing_queries_and_duplicate_papers(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(config, "NDCG_K", 2)
    folder = tmp_path / "dev"
    folder.mkdir()
    path = folder / "test.run.json"
    path.write_text(json.dumps({"q": ["p", "p"]}))
    with pytest.raises(ValueError, match="duplicate"):
        graded.load_runs(["test"], ["q"], {"p": {}})
    path.write_text(json.dumps({}))
    with pytest.raises(ValueError, match="query IDs"):
        graded.load_runs(["test"], ["q"], {})


def test_publish_partial_coverage_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(graded, "OUT", tmp_path / "out")
    workbook = tmp_path / "human.xlsx"
    workbook.write_bytes(b"fingerprint")
    monkeypatch.setattr(graded, "SHEET_PATH", workbook)
    report = graded.publish(
        {"s": {"q": ["a", "b"]}}, {"q": {"a": 2}}, {"q": ["a", "b"]},
        {"q": {"query_type": "keyword"}}, 1)
    assert "INCOMPLETE / PROVISIONAL" in report
    assert "50.0%" in report
    snapshot = json.loads((graded.OUT / "labels.json").read_text())
    assert snapshot["pool_judged"] == 1 and snapshot["pool_pairs"] == 2
    assert snapshot["human_overrides"] == 1
    assert snapshot["complete"] is False
    assert snapshot["judge"] == "openai-mini"
    assert "Withheld until" in report


def test_results_register_openai_and_label_cached_query_timing():
    from arxiv_search.evaluate import experiments

    assert set(graded.SYSTEMS) <= experiments.SYSTEMS.keys()
    row = {"query_id": "q", "query_type": "keyword", "specificity": "specific",
           **{key: 1.0 for key in experiments.METRIC_COLUMNS}}
    report = experiments.main_table({
        "dense-openai-large": ([row], {
            "timing_scope": "sequential_search_excludes_offline_query_embedding",
            "build_seconds": 0, "ms_per_query": 5.3})})
    assert "5.3 (cached vector; embedding API excluded)" in report


def test_selected_judge_is_not_mixed_with_gemma(tmp_path, monkeypatch):
    seen = []
    def grades_for(key, *args):
        seen.append(key)
        return {"q": {"a": 1}}
    monkeypatch.setattr(graded.judge, "grades_for", grades_for)
    labels, count = graded.merged_labels(
        {"q": ["a"]}, {}, {"a": {}}, {}, "openai-4.1-mini")
    assert seen == ["openai-4.1-mini"]
    monkeypatch.setattr(graded, "OUT", tmp_path / "out")
    workbook = tmp_path / "human.xlsx"
    workbook.write_bytes(b"fingerprint")
    monkeypatch.setattr(graded, "SHEET_PATH", workbook)
    report = graded.publish({"s": {"q": ["a"]}}, labels, {"q": ["a"]},
                            {"q": {"query_type": "keyword"}}, count, "openai-4.1-mini")
    snapshot = json.loads((graded.OUT / "labels.json").read_text())
    assert snapshot["judge"] == "openai-4.1-mini"
    assert snapshot["model"] == "gpt-4.1-mini"
    assert "gpt-4.1-mini" in report


def test_paired_comparisons_align_queries_and_skip_undefined(monkeypatch):
    monkeypatch.setattr(graded, "COMPARISONS", [("a", "b")])
    a = [{"query_id": "q2", "ndcg@10": None, "precision@10": 0.1},
         {"query_id": "q1", "ndcg@10": 0.2, "precision@10": 0.2}]
    b = [{"query_id": "q1", "ndcg@10": 0.7, "precision@10": 0.4},
         {"query_id": "q2", "ndcg@10": None, "precision@10": 0.3}]
    text = "\n".join(graded.paired_comparisons({"a": a, "b": b}, True))
    assert "ndcg@10 | 1 | +0.500" in text
    assert "precision@10 | 2 | +0.200" in text
    assert "Withheld" in "\n".join(graded.paired_comparisons({"a": a}, False))
    with pytest.raises(ValueError, match="identical query IDs"):
        graded.paired_comparisons({"a": a, "b": b[:1]}, True)
