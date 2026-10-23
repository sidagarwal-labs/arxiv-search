import pytest

from arxiv_search.search.hybrid import fuse


def test_rrf_rewards_agreement():
    # C gets 1/12 from each list, beating A's 1/11 from just one.
    assert fuse(["A", "C"], ["B", "C"], c=10) == ["C", "A", "B"]


def test_linear_hand_worked():
    # A = .5*1, C = .5*.5 + .5*.5, B = .5*1; stable ties.
    assert fuse(["A", "C"], ["B", "C"], method="linear", depth=2) == ["A", "C", "B"]


@pytest.mark.parametrize("method", ["rrf", "linear"])
def test_endpoint_weights_and_cutoffs(method):
    assert fuse(["A", "B"], ["C", "D"], method=method, semantic_weight=0) == ["A", "B"]
    assert fuse(["A", "B"], ["C", "D"], method=method, semantic_weight=1) == ["C", "D"]
    assert fuse(["A", "B"], ["C", "D"], method=method, depth=1, k=1) == ["A"]
    assert fuse([], [], method=method) == []
    assert fuse(["A"], ["B"], method=method, k=0) == []


@pytest.mark.parametrize("options", [
    {"method": "bad"}, {"semantic_weight": -0.1}, {"semantic_weight": float("nan")},
    {"c": -1}, {"depth": 0}, {"k": -1},
])
def test_invalid_settings(options):
    with pytest.raises(ValueError):
        fuse(["A"], ["B"], **options)


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        fuse(["A", "A"], ["B"])


def test_live_hybrid_uses_same_fusion_as_offline(monkeypatch):
    from arxiv_search.evaluate import experiments as e

    lexical, semantic = ["A", "C"], ["B", "C"]
    monkeypatch.setattr(e, "bm25_system", lambda _: e.System(lambda corpus: lambda q: lexical, "fake"))
    monkeypatch.setattr(e, "dense_system", lambda _: e.System(
        lambda corpus: (lambda q: semantic, {"build_seconds": 0}), "fake"))
    for settings in e.HYBRID_GRID.values():
        search = e.hybrid_system(settings).build([])
        assert search("query") == fuse(
            lexical, semantic, method=settings["method"],
            semantic_weight=settings["semantic_weight"], c=settings["c"])


def test_grid_requires_complete_dev_candidates(tmp_path, monkeypatch):
    import json
    from arxiv_search.evaluate import experiments as e

    monkeypatch.setattr(e.config, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(e, "load_eval", lambda: ([], {}, {}, {"dev": ["q1"]}))
    (tmp_path / "dev").mkdir()
    path = tmp_path / "dev" / f"{e.bm25_name(e.BM25_BEST)}.run.json"
    path.write_text(json.dumps({"q1": ["A"]}))
    with pytest.raises(ValueError, match="100 candidates"):
        e.run_hybrid_grid()
