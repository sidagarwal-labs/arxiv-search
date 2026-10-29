import json
import socket

import pytest

from arxiv_search.evaluate import score_candidate_review as review


def test_recall_losses_are_not_net_counts_or_ndcg_losses():
    queries = {q: {"query": q, "query_type": "keyword", "source_arxiv_id": "target"}
               for q in ("a", "b", "c")}
    runs = {"baseline": {"a": ["target"], "b": ["x"], "c": ["target"]},
            "candidate": {"a": ["x"], "b": ["target"], "c": ["target"]}}
    rows = {name: [{"query_id": q, "ndcg@10": value} for q, value in zip(
        ("a", "b", "c"), (0.5, 0.5, 0.5) if name == "baseline" else (0.6, 0.4, None))]
            for name in runs}
    changes = review.query_changes(runs, rows, queries, "baseline", "candidate")
    assert changes[0]["lost_source_top10"] is True
    assert changes[0]["ndcg_difference"] == pytest.approx(0.1)
    assert changes[1]["gained_source_top10"] is True
    assert changes[1]["ndcg_difference"] == pytest.approx(-0.1)
    assert changes[2]["ndcg_difference"] is None
    with pytest.raises(ValueError, match="identical"):
        review.query_changes(runs, {**rows, "candidate": rows["candidate"][:1]},
                             queries, "baseline", "candidate")


def test_score_components_match_weighted_max_normalization_and_missing_scores():
    inputs = {"lexical": [["a", 10.], ["target", 2.]],
              "semantic": [["b", 0.8], ["target", 0.4]]}
    parts = review.score_components("target", inputs)
    assert parts["lexical"]["rank"] == parts["semantic"]["rank"] == 2
    assert parts["lexical"]["normalized_score"] == 0.2
    assert parts["lexical"]["weighted_contribution"] == 0.05
    assert parts["total"] == pytest.approx(0.425)
    absent = review.score_components("missing", inputs)
    assert absent["lexical"]["raw_score"] is None
    assert absent["total"] == 0
    with pytest.raises(ValueError, match="positive maximum"):
        review.score_components("target", {"lexical": [], "semantic": inputs["semantic"]})


def test_offline_review_validates_frozen_evidence_and_does_not_promote(tmp_path, monkeypatch):
    root = tmp_path / "results"
    out = root / "score-candidate-review-dev"
    monkeypatch.setattr(review.config, "RESULTS_DIR", root)
    monkeypatch.setattr(review, "OUT", out)
    baseline = review.config.RRF_BASELINE_SYSTEM
    papers = {f"p{i}": {"title": f"Paper {i}", "authors": ["Author"], "abstract": "Abstract"}
              for i in range(100)}
    queries = {f"q{i}": {"query": kind, "query_type": kind, "source_arxiv_id": "p0"}
               for i, kind in enumerate(review.results_catalog.QUERY_TYPES)}
    qids = sorted(queries)
    monkeypatch.setattr(review.judge, "load_inputs",
                        lambda: (papers, queries, {"dev": qids, "test": ["held-out"]}))
    monkeypatch.setattr(socket.socket, "connect",
                        lambda *args: pytest.fail("Review attempted a network request"))
    run = {q: list(papers) for q in qids}
    snapshot = {"labels": {q: {p: int(i == 0) * 2 for i, p in enumerate(list(papers)[:10])}
                           for q in qids}, "query_ids": qids, "complete": True,
                "judge": "frozen", "model": "frozen", "rubric_version": "frozen",
                "human_workbook_sha256": "frozen", "human_overrides": 0}

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    save(root / "fusion-dev" / "labels.json", snapshot)
    snapshot["labels"]["q0"]["p10"] = 0
    save(root / "score-fusion-dev" / "labels.json", snapshot)
    folder = root / "score-fusion-dev"
    for name in (baseline, review.CANDIDATE):
        save(folder / f"{name}.run.json", run)
    experiment = {"snapshot_sha256": review.fusion.fingerprint(snapshot),
                  "provenance": {"run_fingerprints": {
                      name: review.fusion.fingerprint(run) for name in (baseline, review.CANDIDATE)}}}
    save(folder / "report.json", experiment)
    save(folder / "input-scores.json", {
        q: {family: [[p, 100. - i] for i, p in enumerate(papers)]
            for family in ("lexical", "semantic")} for q in qids})
    review.main()
    report = json.loads((out / "report.json").read_text())
    assert report["promoted"] is False
    assert report["api_calls"] == 0
    assert report["all_known_item_source_ranks_unchanged"] is True
    assert report["buckets"]["lost_source_top10"] == []
    assert report["paired"]["all"]["ndcg@10"]["difference"] == 0
    assert (out / "report.md").exists()
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    review.main()
    assert before == {p.name: p.read_bytes() for p in out.iterdir()}
    experiment["snapshot_sha256"] = "changed"
    save(folder / "report.json", experiment)
    with pytest.raises(ValueError, match="snapshot changed"):
        review.main()
