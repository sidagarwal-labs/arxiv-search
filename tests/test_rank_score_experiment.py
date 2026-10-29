import copy
import json
import socket

import pytest

from arxiv_search.evaluate import rank_score_experiment as ex


def test_screen_requires_all_checks_not_just_high_ndcg():
    summary = {"ndcg@10": {"mean": .8}, "source_recall@10": {"mean": .86},
               "source_recall@20": {"mean": .89}}
    base = {"top10_fully_judged": True, "all": copy.deepcopy(summary),
            "by_query_type": {kind: copy.deepcopy(summary) for kind in ex.catalog.QUERY_TYPES}}
    candidate = {**copy.deepcopy(base), "paired_ndcg_vs_working_baseline": {
        "difference": .01, "ci95": [.001, .02]}}
    queries = {q: {"source_arxiv_id": "p0", "query_type": kind}
               for q, kind in zip(("q0", "q1", "q2", "q3"), ex.catalog.QUERY_TYPES)}
    run = {q: ["p0", "p1"] for q in queries}
    labels = {q: {"p0": 2, "p1": 0} for q in queries}
    passed = ex.screen(candidate, base, run, run, queries, labels)
    assert passed["passes"] is True
    unknown = copy.deepcopy(candidate)
    unknown["top10_fully_judged"] = False
    unknown["paired_ndcg_vs_working_baseline"] = None
    assert not ex.screen(unknown, base, run, run, queries, labels)["passes"]
    # Better graded scores do not forgive lost targets or worse known-item ranks.
    lost = copy.deepcopy(run)
    lost["q0"] = ["p1"] * 10 + ["p0"]
    outcome = ex.screen(candidate, base, lost, run, queries, labels)
    assert not outcome["passes"]
    assert outcome["lost_source_top10"] == ["q0"]
    assert not outcome["checks"]["grade0_first_not_increased"]
    known_id = next(q for q in queries if queries[q]["query_type"] == "known_item")
    degraded = copy.deepcopy(run)
    degraded[known_id] = ["p1", "p0"]
    outcome = ex.screen(candidate, base, degraded, run, queries, labels)
    assert outcome["known_item_rank_regressions"] == [known_id]
    assert outcome["known_item_target_rank_changes"][0]["candidate_rank"] == 2
    lower_recall = copy.deepcopy(candidate)
    lower_recall["all"]["source_recall@20"]["mean"] = .88
    assert not ex.screen(lower_recall, base, run, run, queries, labels)["passes"]
    lower_segment = copy.deepcopy(candidate)
    lower_segment["by_query_type"]["keyword"]["ndcg@10"]["mean"] = .79
    assert not ex.screen(lower_segment, base, run, run, queries, labels)["passes"]


def test_cached_cli_preserves_inputs_no_network_and_requires_new_identity_for_changed_plan(
        tmp_path, monkeypatch):
    root = tmp_path / "results"
    monkeypatch.setattr(ex.config, "RESULTS_DIR", root)
    monkeypatch.setattr(ex, "OUT", root / "rank-score-dev")
    papers = {f"p{i}": {"arxiv_id": f"p{i}", "title": f"Paper {i}",
                        "abstract": "Abstract", "authors": []} for i in range(120)}
    queries = {f"q{i}": {"query": kind, "query_type": kind, "source_arxiv_id": "p0"}
               for i, kind in enumerate(ex.catalog.QUERY_TYPES)}
    qids = sorted(queries)
    monkeypatch.setattr(ex.judge, "load_inputs",
                        lambda: (papers, queries, {"dev": qids, "test": ["held-out"]}))

    def forbidden(*args, **kwargs):
        pytest.fail("Offline experiment attempted a network/judge call")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(ex.judge, "judge_pairs", forbidden)
    scores = {q: {family: [[p, 120. - i] for i, p in enumerate(papers)]
                  for family in ("lexical", "semantic")} for q in qids}
    run = {q: list(papers)[:100] for q in qids}
    baseline = ex.config.RRF_BASELINE_SYSTEM
    snapshot = {"labels": {q: {p: 2 if p == "p0" else 0 for p in list(papers)[:10]}
                           for q in qids}, "complete": True, "query_ids": qids}
    report = {
        "snapshot_sha256": ex.fusion.fingerprint(snapshot),
        "provenance": {
            "paper_text_sha256": ex.full.fingerprint([ex.paper_text(p) for p in papers.values()]),
            "query_text_sha256": ex.full.fingerprint([queries[q]["query"] for q in qids]),
            "run_fingerprints": {name: ex.fusion.fingerprint(run)
                                 for name in (baseline, ex.CANDIDATE)},
        },
    }

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    for name in (baseline, ex.CANDIDATE):
        save(root / "score-fusion-dev" / f"{name}.run.json", run)
    for name in (ex.fusion.LEXICAL, ex.fusion.SEMANTIC):
        save(root / "dev" / f"{name}.run.json", run)
    save(root / "score-fusion-dev" / "report.json", report)
    save(root / "score-fusion-dev" / "labels.json", snapshot)
    save(root / "score-fusion-dev" / "input-scores.json", scores)
    original_labels = (root / "score-fusion-dev" / "labels.json").read_bytes()
    for family, folder, count in (("interpolation", "rank-score-dev", 6),
                                  ("shortlist", "shortlist-score-dev", 4)):
        ex.main(["--family", family])
        out = root / folder
        result = json.loads((out / "report.json").read_text())
        assert result["missing_pairs"] == result["api_calls"] == 0
        assert result["promoted"] is False
        assert result["controls_exactly_reproduced"] is True
        assert len(result["screens"]) == count
        before = {p.name: p.read_bytes() for p in out.iterdir()}
        ex.main(["--family", family])
        assert before == {p.name: p.read_bytes() for p in out.iterdir()}
    assert (root / "score-fusion-dev" / "labels.json").read_bytes() == original_labels
    registered = json.loads((ex.OUT / "preregistration.json").read_text())
    registered["hypothesis"] = "post-hoc change"
    save(ex.OUT / "preregistration.json", registered)
    with pytest.raises(ValueError, match="Preregistered"):
        ex.main([])
    save(ex.OUT / "preregistration.json", ex.plan())
    scores["q0"]["lexical"][0][1] += .1
    save(root / "score-fusion-dev" / "input-scores.json", scores)
    with pytest.raises(ValueError, match="Frozen experiment inputs changed"):
        ex.main([])
