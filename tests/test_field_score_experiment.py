import json
import socket

import numpy as np
import pytest

from arxiv_search.evaluate import field_score_experiment as ex


def test_prespecified_seven_settings_and_frozen_baseline():
    plan = ex.plan()
    assert len(plan["settings"]) == 7
    assert plan["baseline"] == "fusion-shortlist+a=1+d=500"
    assert "field-gte-concat" in plan["settings"]
    assert plan["no_paid_calls"] and plan["no_test_evaluation"]
    assert {s["title_weight"] for s in plan["settings"].values()
            if "title_weight" in s} == {.25, .5, .75}


def test_weighting_author_preservation_and_concat_control():
    raw = {"lexical_title": np.array([4., 0.]),
           "lexical_abstract": np.array([0., 8.]),
           "lexical_authors": np.array([0., 3.]),
           "semantic_title": np.array([1., 0.]),
           "semantic_abstract": np.array([0., 1.]),
           "semantic_concat": np.array([.2, .4])}
    assert ex.field_signal(raw, {"family": "lexical", "title_weight": .25}) == pytest.approx(
        [.225, .775])
    assert ex.field_signal(raw, {"family": "lexical", "title_weight": .75}) == pytest.approx(
        [.675, .325])
    assert ex.field_signal(raw, {"family": "semantic-concat"}) == pytest.approx([.6, .7])
    assert ex.field_signal(raw, {"family": "semantic-separate",
                                 "title_weight": .25}) == pytest.approx([.625, .875])
    assert ex.max_normalize(np.zeros(2)).tolist() == [0, 0]
    with pytest.raises(ValueError):
        ex.max_normalize(np.array([np.nan]))
    with pytest.raises(ValueError):
        ex.field_signal(raw, {"family": "unexpected"})


def test_stable_ties_and_fixed_tail_membership():
    ids = ["c", "a", "b"]
    assert ex.reorder(ids, np.ones(3), base_fraction=0) == ids
    assert ex.reorder(ids, np.array([0., 1., 0.]), base_fraction=0) == ["a", "c", "b"]
    assert ex.reorder(ids, np.zeros(3)) == ids
    with pytest.raises(ValueError):
        ex.reorder(ids, np.array([0.]))


def test_pure_signal_followup_only_orders_fixed_top10():
    ids = [f"p{i}" for i in range(100)]
    signal = np.arange(100, dtype=float)
    ordered = ex.order_shortlist(ids, signal)
    assert ordered[:10] == list(reversed(ids[:10]))
    assert ordered[10:] == ids[10:]
    assert ex.order_shortlist(ids, np.ones(100)) == ids
    assert len(ex.signal_plan()["settings"]) == 4
    assert ex.signal_plan()["exploratory"]
    with pytest.raises(ValueError):
        ex.order_shortlist(ids, np.array([float("nan")] * 100))


def test_cache_identity_invalidates_text_ids_field_and_revision(tmp_path):
    path = tmp_path / "vectors.npz"
    vectors = np.zeros((2, 384), dtype=np.float32)
    vectors[:, 0] = 1
    identity = ex.cache_identity(["a", "b"], ["one", "two"], "title")
    np.savez(path, vectors=vectors, identity=json.dumps(identity))
    assert np.array_equal(ex.read_cache(path, identity), vectors)
    for changed in (
        ex.cache_identity(["b", "a"], ["one", "two"], "title"),
        ex.cache_identity(["a", "b"], ["ONE", "two"], "title"),
        ex.cache_identity(["a", "b"], ["one", "two"], "abstract"),
        ex.cache_identity(["a", "b"], ["one", "two"], "title", revision="different"),
    ):
        assert ex.read_cache(path, changed) is None
    np.savez(path, vectors=vectors * 2, identity=json.dumps(identity))
    with pytest.raises(ValueError, match="normalized"):
        ex.read_cache(path, identity)


def test_no_heldout_or_changed_candidates():
    papers = {"a": {}, "b": {}}
    ex.validate_scope({"dev": ["a", "b"]}, ["dev"], ["heldout"], papers, depth=2)
    with pytest.raises(ValueError, match="disjoint"):
        ex.validate_scope({"heldout": ["a", "b"]}, ["dev"], ["heldout"], papers, depth=2)
    with pytest.raises(ValueError, match="disjoint"):
        ex.validate_scope({"dev": ["a", "b"]}, ["dev"], ["dev"], papers, depth=2)
    with pytest.raises(ValueError, match="candidates"):
        ex.validate_scope({"dev": ["a", "a"]}, ["dev"], [], papers, depth=2)


def test_target_changes_are_source_based_not_inferred_grades():
    ids = [f"p{i}" for i in range(20)]
    base = {"lost": ids, "gained": list(reversed(ids))}
    run = {"lost": ids[1:11] + [ids[0]] + ids[11:], "gained": ids}
    queries = {q: {"source_arxiv_id": "p0", "query_type": "known_item"} for q in base}
    result = ex.changes(run, base, queries)
    assert result["lost_source_top10"] == ["lost"]
    assert result["gained_source_top10"] == ["gained"]
    assert result["known_item_target_rank_changes"] == [
        {"query_id": "lost", "baseline_rank": 1, "candidate_rank": 11},
        {"query_id": "gained", "baseline_rank": 20, "candidate_rank": 1}]


def test_budget_and_resume_cache_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "CACHE", tmp_path)
    progress = {"encoded_texts": 0, "cached_texts": 0}

    class Model:
        def encode(self, texts, **kwargs):
            vectors = np.zeros((len(texts), 384), dtype=np.float32)
            vectors[:, 0] = 1
            return vectors

    with pytest.raises(ex.SemanticBudgetExceeded):
        ex.encode_cached(Model(), ["a"], ["text"], "title", -1, progress)
    first = ex.encode_cached(Model(), ["a"], ["text"], "title", float("inf"), progress)
    second = ex.encode_cached(None, ["a"], ["text"], "title", -1, progress)
    assert np.array_equal(first, second)
    assert progress == {"encoded_texts": 1, "cached_texts": 1}


def test_fixture_publish_provisional_metrics_preserves_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "OUT", tmp_path)
    papers = {f"p{i}": {} for i in range(100)}
    base = {"q": list(papers)}
    queries = {"q": {"query_type": "known_item", "source_arxiv_id": "p0"}}
    snapshot = {"labels": {"q": {"p0": 2}}, "query_ids": ["q"],
                "human_overrides": {"q/p0": 2}}
    original = json.dumps(snapshot, sort_keys=True)
    raw = {"q": {f"lexical_{f}": np.arange(100, dtype=float) for f in ex.FIELDS}}
    report = ex.publish(raw, base, snapshot, papers, queries, ex.plan(), {}, {})
    assert report["missing_pairs"] > 0
    assert report["incomplete_settings"] == [
        "field-gte-concat", "field-gte-separate+t=0.25",
        "field-gte-separate+t=0.5", "field-gte-separate+t=0.75"]
    for result in report["systems"].values():
        assert result["status"] == "PROVISIONAL"
        assert result["paired_ndcg_vs_working_baseline"] is None
    for result in report["summary"].values():
        assert result["all"]["ndcg@10"]["paired_vs_working"] is None
        assert result["all"]["source_recall@10"]["paired_vs_working"] is not None
    assert json.dumps(snapshot, sort_keys=True) == original
    for path in tmp_path.glob("*.run.json"):
        run = json.loads(path.read_text())
        assert set(run) == {"q"} and set(run["q"]) == set(papers)


def test_lexical_cli_offline_never_scores_heldout_and_freezes_inputs(tmp_path, monkeypatch):
    results = tmp_path / "results"
    out = results / "field-score-dev"
    monkeypatch.setattr(ex, "OUT", out)
    monkeypatch.setattr(ex.config, "RESULTS_DIR", results)
    monkeypatch.setattr(ex.config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ex.config, "WORKING_BASELINE_SYSTEM", "future-promoted-baseline")
    papers = {f"p{i}": {"title": f"Retrieval paper {i}",
                        "abstract": f"An abstract about learning and retrieval {i}",
                        "authors": ["Author Example"]} for i in range(100)}
    base = {"dev": list(papers)}
    # A heldout object that cannot be used as a query proves only dev is accessed.
    queries = {"dev": {"query": "retrieval learning", "source_arxiv_id": "p0",
                        "query_type": "keyword"}, "heldout": None}
    monkeypatch.setattr(ex.judge, "load_inputs",
                        lambda: (papers, queries, {"dev": ["dev"], "test": ["heldout"]}))
    source = results / "shortlist-score-dev"
    source.mkdir(parents=True)
    ex.write_json(source / f"{ex.BASELINE}.run.json", base)
    label_path = results / "score-fusion-dev" / "labels.json"
    label_path.parent.mkdir()
    snapshot = {"labels": {"dev": {p: 2 if p == "p0" else 0 for p in papers}},
                "query_ids": ["dev"], "human_overrides": ["preserved"]}
    ex.write_json(label_path, snapshot)
    original_labels = label_path.read_bytes()
    monkeypatch.setattr(ex.catalog, "load_snapshot",
                        lambda root: (label_path, original_labels, snapshot, {}))

    def forbidden(*args, **kwargs):
        pytest.fail("Offline field experiment attempted network or judging")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(ex.judge, "judge_pairs", forbidden)
    ex.main(["--lexical-only"])
    report = json.loads((out / "report.json").read_text())
    assert len(report["completed_settings"]) == 3
    assert len(report["incomplete_settings"]) == 4
    assert report["api_calls"] == report["missing_pairs"] == 0
    first_runtime = report["runtime"]
    assert first_runtime["cumulative_total_seconds"] == first_runtime["total_seconds"]
    ex.main(["--lexical-only"])
    rerun = json.loads((out / "report.json").read_text())["runtime"]
    assert rerun["prior_invocations"] == 1
    assert rerun["prior_total_seconds"] == first_runtime["total_seconds"]
    assert rerun["cumulative_total_seconds"] == pytest.approx(
        rerun["total_seconds"] + first_runtime["total_seconds"], abs=.001)
    assert len(json.loads((out / "runtime-history.json").read_text())) == 2
    assert label_path.read_bytes() == original_labels
    assert all(set(json.loads(path.read_text())) == {"dev"} for path in out.glob("*.run.json"))
    papers["p0"]["title"] = "Changed input"
    with pytest.raises(ValueError, match="Frozen experiment input changed"):
        ex.main(["--lexical-only"])


def test_sorted_json_mapping_keys_do_not_change_candidate_tie_order(tmp_path):
    base = {"z-query": ["z-paper", "a-paper"], "a-query": ["a-paper", "z-paper"]}
    path = tmp_path / "run.json"
    ex.write_json(path, base)
    restored = json.loads(path.read_text())
    assert list(restored) != list(base)
    ex.validate_scope(restored, list(base), [], {"z-paper": {}, "a-paper": {}}, depth=2)
    for qid, candidates in restored.items():
        assert ex.reorder(candidates, np.zeros(2), base_fraction=0) == base[qid]


def test_partial_semantic_concat_does_not_claim_separate_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "OUT", tmp_path)
    papers = {f"p{i}": {} for i in range(100)}
    base = {"q": list(papers)}
    queries = {"q": {"query_type": "keyword", "source_arxiv_id": "p0"}}
    snapshot = {"labels": {"q": {p: 0 for p in papers}}, "query_ids": ["q"]}
    raw = {"q": {**{f"lexical_{f}": np.zeros(100) for f in ex.FIELDS},
                 "semantic_concat": np.zeros(100), "semantic_title": np.zeros(100)}}
    result = ex.publish(raw, base, snapshot, papers, queries, ex.plan(), {}, {})
    assert "field-gte-concat" in result["completed_settings"]
    assert len(result["incomplete_settings"]) == 3
