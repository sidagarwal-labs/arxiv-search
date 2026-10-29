import hashlib
import json
import socket

import pytest

from arxiv_search.evaluate import fusion_review as review


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    ids = [f"p{i}" for i in range(100)]
    queries = {"q": {"query": "paper", "query_type": "known_item", "source_arxiv_id": "p0"}}
    papers = {p: {"title": p, "authors": [], "abstract": "abstract"} for p in ids}
    runs = {name: {"q": ids[:]} for name in (
        review.fusion.BASELINE, review.PREVIOUS, review.fusion.LEXICAL, review.fusion.SEMANTIC)}
    sheet = tmp_path / "human.xlsx"
    sheet.write_bytes(b"frozen")
    monkeypatch.setattr(review.graded, "SHEET_PATH", sheet)
    snapshot = {
        "complete": True, "rubric_version": review.judge.RUBRIC_VERSION,
        "human_workbook_sha256": hashlib.sha256(sheet.read_bytes()).hexdigest(),
        "query_ids": ["q"], "labels": {"q": {p: 2 if p == "p0" else 0 for p in ids}},
        "run_fingerprints": {n: review.fusion.fingerprint(r) for n, r in runs.items()},
        "judge": "openai-mini",
    }
    return runs, snapshot, queries, papers


def test_snapshot_guards(inputs):
    runs, snapshot, _, _ = inputs
    review.validate_snapshot(snapshot, runs, ["q"])
    for field, value, message in (
        ("complete", False, "complete"),
        ("rubric_version", "changed", "Rubric"),
        ("human_workbook_sha256", "changed", "workbook"),
        ("query_ids", ["test"], "dev queries"),
    ):
        with pytest.raises(ValueError, match=message):
            review.validate_snapshot({**snapshot, field: value}, runs, ["q"])
    changed = {**runs, review.PREVIOUS: {"q": runs[review.PREVIOUS]["q"][::-1]}}
    with pytest.raises(ValueError, match="ranking changed"):
        review.validate_snapshot(snapshot, changed, ["q"])
    del snapshot["labels"]["q"]["p5"]
    with pytest.raises(ValueError, match="unjudged"):
        review.validate_snapshot(snapshot, runs, ["q"])


def test_source_and_graded_objectives_stay_separate(inputs):
    runs, snapshot, queries, _ = inputs
    ids = runs[review.PREVIOUS]["q"][:]
    ids[0], ids[1] = ids[1], ids[0]
    labels = snapshot["labels"]
    labels["q"]["p1"] = 2
    runs[review.CANDIDATE] = {"q": ids}
    runs[review.ALTERNATIVE] = runs[review.PREVIOUS]
    rows = review.score(runs, labels, queries)
    paired = review.comparisons(rows)[review.PREVIOUS]["known_item"]
    assert paired["ndcg@10"]["difference"] == 0
    assert paired["source_mrr@10"]["difference"] == -0.5
    assert paired["source_recall@1"]["regressions"] == 1
    assert paired["source_recall@10"]["difference"] == 0
    assert review.rank(ids, "missing") is None


def test_offline_review_deterministic_and_does_not_promote(inputs, tmp_path, monkeypatch):
    runs, snapshot, queries, papers = inputs
    monkeypatch.setattr(review.fusion, "OUT", tmp_path)
    monkeypatch.setattr(review, "OUT", tmp_path / "review")
    (tmp_path / "labels.json").write_text(json.dumps(snapshot))
    monkeypatch.setattr(review.judge, "load_inputs", lambda: (papers, queries, {"dev": ["q"], "test": ["t"]}))
    monkeypatch.setattr(review.fusion, "prepare", lambda *args: (runs, {}, {}))
    monkeypatch.setattr(review.judge, "load_judgments", lambda *args: {})
    monkeypatch.setattr(review.graded, "read_human_grades", lambda: {})
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected labeling/network/promotion")
    monkeypatch.setattr(review.judge, "judge_pairs", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    frozen_bytes = (tmp_path / "labels.json").read_bytes()
    review.main()
    output = review.OUT
    report = json.loads((output / "report.json").read_text())
    assert report["promoted"] is False
    assert report["api_calls"] == 0
    assert report["summary"][review.CANDIDATE]["all"]["judged@10"]["mean"] == 1
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    review.main()
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    assert (tmp_path / "labels.json").read_bytes() == frozen_bytes
