import copy
import json
import socket

import pytest

# Initialize the registry before fixtures temporarily change shared config.
from arxiv_search.evaluate import experiments, results_catalog as catalog


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    papers = {f"p{i}": {"arxiv_id": f"p{i}"} for i in range(25)}
    queries = {
        f"q{i}": {"query_type": kind, "query": kind, "source_arxiv_id": "p0"}
        for i, kind in enumerate(catalog.QUERY_TYPES)
    }
    ids = sorted(queries)
    snapshot = {
        "labels": {q: {f"p{i}": 2 if i == 0 else 1 if i == 1 else 0
                       for i in range(10)} for q in ids},
        "query_ids": ids, "human_overrides": 1,
        "human_workbook_sha256": "frozen-human-workbook",
        "complete": True, "judge": "frozen-judge", "model": "frozen-model",
        "rubric_version": "frozen-rubric",
    }
    run = {q: [f"p{i}" for i in range(20)] for q in ids}
    root = tmp_path / "data" / "results"
    monkeypatch.setattr(catalog.config, "RESULTS_DIR", root)
    monkeypatch.setattr(catalog.config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(catalog.config, "WORKING_BASELINE_SYSTEM", "current-baseline")
    monkeypatch.setattr(catalog.judge, "load_inputs",
                        lambda: (papers, queries, {"dev": ids, "test": ["test-only"]}))
    save(root / "fusion-dev" / "labels.json", snapshot)
    save(root / "fusion-review-dev" / "current-baseline.run.json", run)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network or label refresh")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(catalog.judge, "judge_pairs", forbidden)
    monkeypatch.setattr(catalog.graded, "read_human_grades", forbidden)
    return root, snapshot, papers, queries, ids, run


def test_automatic_discovery_dedup_and_current_baseline(inputs):
    root, _, _, _, _, run = inputs
    for folder, name in (
        ("dev", "legacy"), ("fusion-dev", "legacy"),
        ("fusion-dev", "baseline-original-alias"),
        ("score-fusion-dev", "unregistered-new-score-fusion"),
    ):
        save(root / folder / f"{name}.run.json", run)
    save(root / "dev" / "legacy.info.json", {
        "ms_per_query": 12.5, "timing_scope": "fusion_only", "cost_usd": 0.2})
    save(root / "test" / "must-not-score.run.json", {"test-only": ["p0"]})
    save(root / "embedding-pilot" / "pilot.run.json", {"test-only": ["p0"]})
    text = catalog.write_catalog()
    report = json.loads((root / "catalog-dev" / "report.json").read_text())
    systems = report["systems"]
    assert set(systems) == {
        "current-baseline", "legacy", "baseline-original-alias", "unregistered-new-score-fusion"}
    assert systems["legacy"]["paths"] == [
        "dev/legacy.run.json", "fusion-dev/legacy.run.json"]
    assert systems["legacy"]["metadata"]["dev/legacy.info.json"]["ms_per_query"] == 12.5
    assert systems["unregistered-new-score-fusion"]["metadata"] == {}
    assert "**`current-baseline` (WORKING BASELINE)**" in text
    assert "**`baseline-original-alias` (WORKING BASELINE)**" not in text
    assert systems["legacy"]["paired_ndcg_vs_working_baseline"]["difference"] == 0
    for system in systems.values():
        assert set(system["by_query_type"]) == set(catalog.QUERY_TYPES)
        assert system["known_item_source_mrr@10"] == {"mean": 1.0, "n": 1}
        assert system["all"]["source_recall@20"]["mean"] == 1.0
    assert report["working_baseline"] == "current-baseline"


def test_duplicate_conflict_is_an_explicit_error(inputs):
    root, _, _, _, _, run = inputs
    save(root / "dev" / "current-baseline.run.json", run)
    changed = copy.deepcopy(run)
    changed["q0"] = changed["q0"][::-1]
    save(root / "score-fusion-dev" / "current-baseline.run.json", changed)
    with pytest.raises(ValueError, match="Conflicting duplicate rankings.*current-baseline"):
        catalog.write_catalog()
    assert not (root / "catalog-dev" / "report.json").exists()


def test_one_frozen_denominator_and_human_overrides_not_historical_scores(inputs):
    root, snapshot, _, _, _, run = inputs
    save(root / "dev" / "same-ranking.run.json", run)
    # An incompatible, newer label pool/report must never supply the main scores.
    different = copy.deepcopy(snapshot)
    different["labels"]["q0"]["p1"] = 0
    different["labels"]["q0"]["p20"] = 2
    save(root / "graded-dev" / "labels.json", different)
    save(root / "score-fusion-dev" / "report.json", {"systems": {"same-ranking": {"ndcg": 0}}})
    frozen_bytes = (root / "fusion-dev" / "labels.json").read_bytes()
    catalog.write_catalog()
    report = json.loads((root / "catalog-dev" / "report.json").read_text())
    left = report["systems"]["current-baseline"]
    right = report["systems"]["same-ranking"]
    assert left["all"]["ndcg@10"]["mean"] == right["all"]["ndcg@10"]["mean"] == 1.0
    assert left["all"]["precision@10"]["mean"] == 0.2
    assert report["human_overrides"] == 1
    assert report["human_workbook_sha256"] == "frozen-human-workbook"
    assert (root / "fusion-dev" / "labels.json").read_bytes() == frozen_bytes


def test_unjudged_new_run_is_visible_but_paired_withheld(inputs):
    root, _, _, _, ids, run = inputs
    novel = copy.deepcopy(run)
    for q in ids:
        novel[q][1] = "p20"
    save(root / "score-fusion-dev" / "novel.run.json", novel)
    text = catalog.write_catalog()
    report = json.loads((root / "catalog-dev" / "report.json").read_text())
    result = report["systems"]["novel"]
    assert result["status"] == "PROVISIONAL"
    assert result["all"]["judged@10"]["mean"] == 0.9
    assert result["all"]["source_mrr@10"]["mean"] == 1.0
    assert result["paired_ndcg_vs_working_baseline"] is None
    assert "both runs" in result["paired_withheld_reason"]
    assert "`novel`" in text


def test_incomplete_baseline_blocks_otherwise_complete_comparison(inputs):
    root, _, _, _, _, run = inputs
    save(root / "dev" / "covered.run.json", run)
    short = {q: ranked[:1] for q, ranked in run.items()}
    save(root / "fusion-review-dev" / "current-baseline.run.json", short)
    catalog.write_catalog()
    systems = json.loads((root / "catalog-dev" / "report.json").read_text())["systems"]
    assert systems["current-baseline"]["all"]["judged@10"]["mean"] == 1.0
    assert systems["current-baseline"]["status"] == "PROVISIONAL"
    assert systems["covered"]["status"] == "covered"
    assert systems["covered"]["paired_ndcg_vs_working_baseline"] is None


def test_missing_queries_keep_full_source_denominator_and_all_four_types(inputs):
    root, _, _, _, ids, run = inputs
    save(root / "score-fusion-dev" / "partial.run.json", {ids[0]: run[ids[0]]})
    catalog.write_catalog()
    result = json.loads((root / "catalog-dev" / "report.json").read_text())["systems"]["partial"]
    assert result["queries_present"] == 1
    assert result["queries_expected"] == 4
    assert result["all"]["source_mrr@10"] == {"mean": 0.25, "n": 4}
    assert result["all"]["source_recall@1"] == {"mean": 0.25, "n": 4}
    assert result["by_query_type"]["known_item"]["queries"] == 1
    assert result["by_query_type"]["known_item"]["source_mrr@10"]["mean"] == 0
    assert result["paired_ndcg_vs_working_baseline"] is None


def test_rejects_non_dev_rankings_and_wrong_label_query_denominator(inputs):
    root, snapshot, papers, queries, ids, run = inputs
    bad = {**run, "test-only": ["p0"]}
    save(root / "score-fusion-dev" / "invalid.run.json", bad)
    with pytest.raises(ValueError, match="non-dev query IDs"):
        catalog.write_catalog()
    wrong = copy.deepcopy(snapshot)
    del wrong["labels"][ids[0]]
    with pytest.raises(ValueError, match="exactly the dev queries"):
        catalog.score_catalog({}, wrong, papers, queries, ids, "baseline")


def test_reports_are_deterministic_with_inventory_and_no_central_doc_write(inputs):
    root, _, _, _, _, _ = inputs
    save(root / "dev" / "tuning" / "bm25.json", {"separate": "tuning grid"})
    save(root / "embedding-pilot" / "report.json", {"scope": "reduced corpus"})
    save(root / "score-fusion-dev" / "configs.json", {"new": "configuration"})
    docs = root.parents[1] / "docs"
    docs.mkdir()
    (docs / "05-results.md").write_text("parent will regenerate")
    first = catalog.write_catalog()
    before = {p.name: p.read_bytes() for p in (root / "catalog-dev").iterdir()}
    second = catalog.write_catalog()
    assert first == second
    assert before == {p.name: p.read_bytes() for p in (root / "catalog-dev").iterdir()}
    assert (docs / "05-results.md").read_text() == "parent will regenerate"
    assert "dev/tuning/bm25.json" in first
    assert "embedding-pilot/report.json" in first
    assert "score-fusion-dev/configs.json" in first
    markdown = (root / "catalog-dev" / "report.md").read_text()
    assert "reduced-corpus embedding pilot, separate scope" in markdown
    assert "BM25 tuning, source-paper objective" in markdown
    assert "Every run by query type" in markdown


def test_results_document_puts_catalog_first_and_keeps_historical_reports(inputs, monkeypatch):
    root, _, _, _, _, _ = inputs
    docs = root.parents[1] / "docs"
    docs.mkdir()
    report = root / "score-fusion-dev" / "report.md"
    report.parent.mkdir()
    report.write_text("# New score-fusion report\n\nSaved results.")
    monkeypatch.setattr(experiments, "write_catalog", lambda: "## Unified catalog sentinel")
    monkeypatch.setattr(experiments, "load_results", lambda split: {})
    monkeypatch.setattr(experiments, "hybrid_comparison", lambda results: None)
    monkeypatch.setattr(experiments, "factor_analysis", lambda results: None)
    monkeypatch.setattr(experiments, "tuning_tables", lambda: None)
    monkeypatch.setattr(experiments.config, "EVAL_DIR", root.parents[1] / "eval")
    experiments.write_results_doc()
    text = (docs / "05-results.md").read_text(encoding="utf-8")
    assert text.index("## Unified catalog sentinel") < text.index("## Historical source-paper")
    assert "## Historical dev (100 queries): source-paper experiments" in text
    assert "## Test (300 queries): finalists only" in text
    assert "# New score-fusion report" in text


def test_additive_snapshot_preferred_and_all_systems_share_revised_denominator(inputs):
    root, snapshot, _, _, _, run = inputs
    expanded = copy.deepcopy(snapshot)
    expanded["labels"]["q0"]["p20"] = 2
    # Expanded snapshots need not repeat the optional human override count.
    del expanded["human_overrides"]
    save(root / "score-fusion-dev" / "labels.json", expanded)
    save(root / "dev" / "same-ranking.run.json", run)
    original_bytes = (root / "fusion-dev" / "labels.json").read_bytes()
    expanded_bytes = (root / "score-fusion-dev" / "labels.json").read_bytes()
    text = catalog.write_catalog()
    report = json.loads((root / "catalog-dev" / "report.json").read_text())
    assert report["label_snapshot"] == "score-fusion-dev/labels.json"
    assert report["label_snapshot_provenance"]["added_pairs"] == 1
    assert report["label_snapshot_provenance"]["original_pairs"] == 40
    assert report["label_snapshot_provenance"]["denominator_revised"] is True
    assert report["human_overrides"] == 1
    assert report["model"] == "frozen-model"
    baseline = report["systems"]["current-baseline"]
    other = report["systems"]["same-ranking"]
    assert baseline["all"]["ndcg@10"]["mean"] == other["all"]["ndcg@10"]["mean"] < 1
    assert other["paired_ndcg_vs_working_baseline"]["difference"] == 0
    assert "Revised shared ideal-DCG denominator" in text
    assert "original reports remain unchanged" in text
    assert (root / "fusion-dev" / "labels.json").read_bytes() == original_bytes
    assert (root / "score-fusion-dev" / "labels.json").read_bytes() == expanded_bytes


@pytest.mark.parametrize("change, message", [
    ("grade", "changed or removed original grade"),
    ("remove_grade", "changed or removed original grade"),
    ("judge", "incompatible judge"),
    ("model", "incompatible model"),
    ("rubric_version", "incompatible rubric_version"),
    ("query_ids", "incompatible query_ids"),
    ("human_workbook_sha256", "incompatible human_workbook_sha256"),
    ("human_overrides", "changed human_overrides"),
    ("complete", "boolean complete"),
    ("remove_query", "original query IDs"),
    ("invalid_grade", "Invalid frozen labels"),
    ("no_addition", "strict additive extension"),
])
def test_invalid_expansion_fails_without_fallback(inputs, change, message):
    root, snapshot, _, _, _, _ = inputs
    expanded = copy.deepcopy(snapshot)
    expanded["labels"]["q0"]["p20"] = 2
    if change == "grade":
        expanded["labels"]["q0"]["p0"] = 0
    elif change == "remove_grade":
        del expanded["labels"]["q0"]["p0"]
    elif change == "remove_query":
        del expanded["labels"]["q0"]
    elif change == "invalid_grade":
        expanded["labels"]["q0"]["p20"] = 3
    elif change == "no_addition":
        expanded = copy.deepcopy(snapshot)
    elif change == "query_ids":
        expanded["query_ids"] = ["different"]
    elif change == "human_overrides":
        expanded["human_overrides"] = 0
    else:
        expanded[change] = "changed"
    save(root / "score-fusion-dev" / "labels.json", expanded)
    with pytest.raises(ValueError, match=message):
        catalog.write_catalog()
    assert not (root / "catalog-dev" / "report.json").exists()


def test_malformed_expansion_does_not_fall_back(inputs):
    root, _, _, _, _, _ = inputs
    path = root / "score-fusion-dev" / "labels.json"
    path.parent.mkdir()
    path.write_text("{bad json")
    with pytest.raises(json.JSONDecodeError):
        catalog.write_catalog()


def test_frozen_fallback_records_unchanged_denominator(inputs):
    root, _, _, _, _, _ = inputs
    text = catalog.write_catalog()
    report = json.loads((root / "catalog-dev" / "report.json").read_text())
    assert report["label_snapshot"] == "fusion-dev/labels.json"
    assert report["label_snapshot_provenance"]["denominator_revised"] is False
    assert report["label_snapshot_provenance"]["added_pairs"] == 0
    assert "original frozen fusion-dev denominator is unchanged" in text


def test_refinement_runs_discovered_with_coverage_gate_inventory_and_readme_anchor(inputs):
    root, _, _, _, _, run = inputs
    save(root / "refinement-dev" / "covered-refinement.run.json", run)
    novel = copy.deepcopy(run)
    novel["q0"][0] = "p20"
    save(root / "refinement-dev" / "unjudged-refinement.run.json", novel)
    save(root / "refinement-dev" / "configs.json", {"scope": "finer rank settings"})
    save(root / "refinement-dev" / "report.json", {"scope": "offline"})
    text = catalog.write_catalog()
    report = json.loads((root / "catalog-dev" / "report.json").read_text())
    assert len(report["systems"]) == 3
    assert report["systems"]["covered-refinement"]["status"] == "covered"
    provisional = report["systems"]["unjudged-refinement"]
    assert provisional["status"] == "PROVISIONAL"
    assert provisional["paired_ndcg_vs_working_baseline"] is None
    assert provisional["paths"] == ["refinement-dev/unjudged-refinement.run.json"]
    assert "refinement-dev/configs.json" in report["inventory"]
    assert "refinement-dev/report.json" in report["inventory"]
    assert "refinement-dev/report.json" in text
    assert '<a id="unified-dev-scorecard"></a>' in text
