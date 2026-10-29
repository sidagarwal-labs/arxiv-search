import math
import hashlib
import json
import socket

import numpy as np
import pytest

from arxiv_search.search.score_fusion import fuse_scores, fuse_top1_bonus
from arxiv_search.search.hybrid import fuse_rrf_baseline
from arxiv_search.evaluate import score_fusion_experiment as ex


def test_score_fusion_uses_magnitudes_not_just_order():
    options = dict(normalization="minmax", semantic_weight=0.55, depth=3)
    lex = {"a": 100.0, "b": 99.0, "c": 0.0}
    sem = {"b": 1.0, "a": 0.99, "c": 0.0}
    assert fuse_scores(lex, sem, **options)[0] == "b"
    lex["b"] = 1.0
    assert fuse_scores(lex, sem, **options)[0] == "a"


def test_hand_worked_normalization_missing_ties_and_constant():
    opts = dict(semantic_weight=0.5, depth=3)
    assert fuse_scores({"a": 10, "c": 5}, {"b": 1, "c": 0.5},
                       normalization="max", **opts) == ["a", "c", "b"]
    assert fuse_scores({"a": 10, "c": 5}, {"b": 1, "c": 0.5},
                       normalization="minmax", **opts) == ["a", "b", "c"]
    assert fuse_scores({"a": 2, "b": 2}, {}, normalization="minmax", **opts) == ["a", "b"]
    assert fuse_scores({"a": 0, "b": 0}, {}, normalization="minmax", **opts) == ["a", "b"]
    assert fuse_scores({}, {}, normalization="max", **opts) == []
    assert fuse_scores({"a": 1}, {"b": 1}, normalization="max", semantic_weight=1,
                       depth=1, k=1) == ["b"]


@pytest.mark.parametrize("scores", [{"a": math.nan}, {"a": -1}, {"a": 0, "b": 1}])
def test_invalid_scores(scores):
    with pytest.raises(ValueError):
        fuse_scores(scores, {}, normalization="max", semantic_weight=0.5, depth=100)


@pytest.mark.parametrize("options", [
    {"normalization": "bad"}, {"semantic_weight": -0.1}, {"semantic_weight": math.nan},
    {"depth": 0}, {"k": -1},
])
def test_invalid_options(options):
    opts = dict(normalization="max", semantic_weight=0.5, depth=10)
    with pytest.raises(ValueError):
        fuse_scores({"a": 1}, {}, **{**opts, **options})


def test_bonus_zero_reproduces_baseline_and_bounded_boost():
    lex = [f"p{i}" for i in range(120)]
    sem = lex[::-1]
    assert fuse_top1_bonus(lex, sem, bonus=0) == fuse_rrf_baseline(lex, sem)
    with pytest.raises(ValueError):
        fuse_top1_bonus(lex, sem, bonus=math.nan)


def test_top_scores_stable_finite_and_positive_filter():
    assert ex.top_scores(["a", "b", "c"], np.array([0., 1., 1.]),
                         positive_only=True) == {"b": 1., "c": 1.}
    with pytest.raises(ValueError):
        ex.top_scores(["a"], np.array([math.nan]), positive_only=False)


def test_grid_and_provisional_pair_gate():
    scored = {"q": {"lexical": {"a": 10., "b": 5.}, "semantic": {"b": 1., "c": 0.5}}}
    runs, settings = ex.build_runs(scored)
    assert len(settings) == len(runs) == 16
    rows = {"base": [{"query_id": "q", "query_type": "known_item", "judged@10": 1.,
                      "ndcg@10": 1., "source_mrr@10": 1.}],
            "new": [{"query_id": "q", "query_type": "known_item", "judged@10": .9,
                     "ndcg@10": .7, "source_mrr@10": .5}]}
    groups = ex.summarize(rows, "base")["new"]
    assert groups["all"]["ndcg@10"]["paired_vs_working"] is None
    assert groups["all"]["source_mrr@10"]["paired_vs_working"]["difference"] == -.5


def test_historical_refinement_grid_includes_approved_profile():
    from arxiv_search.evaluate.fusion_refinement import grid

    settings = grid()
    assert len(settings) == 24
    assert settings[ex.config.RRF_BASELINE_SYSTEM] == {
        "semantic_weight": 0.55, "c": 30, "depth": 100, "k": 100}


def test_missing_cache_cannot_trigger_embedding(monkeypatch):
    monkeypatch.setattr(ex.full, "read_cache", lambda *args: None)
    monkeypatch.setattr(ex.full, "embed", lambda *args: pytest.fail("Embedding forbidden"))
    with pytest.raises(ValueError, match="no API repair"):
        ex.cached_vectors(["missing"])


def test_offline_cli_shared_snapshot_and_no_network(tmp_path, monkeypatch):
    from arxiv_search.evaluate import experiments

    ids = [f"p{i}" for i in range(100)]
    papers = {p: {"arxiv_id": p, "title": p, "abstract": "abstract", "authors": []}
              for p in ids}
    queries = {"q": {"query": "paper", "source_arxiv_id": "p0", "query_type": "known_item"}}
    monkeypatch.setattr(ex.judge, "load_inputs", lambda: (papers, queries, {"dev": ["q"], "test": ["t"]}))
    monkeypatch.setattr(ex.config, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(ex, "OUT", tmp_path / "out")
    monkeypatch.setattr(ex.fusion, "OUT", tmp_path / "frozen")
    monkeypatch.setattr(ex.review, "OUT", tmp_path / "review")
    sheet = tmp_path / "human.xlsx"
    sheet.write_bytes(b"frozen")
    monkeypatch.setattr(ex.graded, "SHEET_PATH", sheet)
    monkeypatch.setattr(ex.graded, "read_human_grades", lambda: {})
    monkeypatch.setattr(ex.judge, "load_judgments", lambda *args: {})
    monkeypatch.setattr(ex.graded, "merged_labels", lambda *args: ({"q": dict.fromkeys(ids, 1)}, 0))
    for folder in ("dev", "frozen", "review"):
        (tmp_path / folder).mkdir()
    run = {"q": ids}
    for name in (ex.fusion.LEXICAL, ex.fusion.SEMANTIC):
        (tmp_path / "dev" / f"{name}.run.json").write_text(json.dumps(run))
    (tmp_path / "review" / f"{ex.config.RRF_BASELINE_SYSTEM}.run.json").write_text(json.dumps(run))
    snapshot = {
        "complete": True, "labels": {"q": dict.fromkeys(ids, 1)}, "query_ids": ["q"],
        "human_workbook_sha256": hashlib.sha256(sheet.read_bytes()).hexdigest(),
        "rubric_version": ex.judge.RUBRIC_VERSION, "judge": "openai-mini",
        "model": "gpt-5.4-mini", "run_fingerprints": {},
    }
    frozen_path = tmp_path / "frozen" / "labels.json"
    frozen_path.write_text(json.dumps(snapshot))
    original = frozen_path.read_bytes()
    values = np.arange(100, 0, -1, dtype=float)
    monkeypatch.setattr(ex, "cached_vectors", lambda texts: (
        values.reshape(-1, 1) if len(texts) == 100 else np.ones((1, 1))))
    class Index:
        def scores(self, tokens):
            return values
    monkeypatch.setattr(experiments, "bm25_index", lambda *args: (Index(), lambda text: [text]))
    def forbidden(*args, **kwargs):
        raise AssertionError("Network/labeling forbidden")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(ex.judge, "judge_pairs", forbidden)
    ex.main([])
    report = json.loads((ex.OUT / "report.json").read_text())
    assert len(report["settings"]) == 16
    assert report["complete"] is True
    assert report["missing_pairs"] == report["judge_calls_this_run"] == 0
    saved_scores = json.loads((ex.OUT / "input-scores.json").read_text())
    assert saved_scores["q"]["lexical"][:2] == [["p0", 100.0], ["p1", 99.0]]
    assert frozen_path.read_bytes() == original
    assert json.loads((ex.OUT / "labels.json").read_text())["labels"] == snapshot["labels"]
