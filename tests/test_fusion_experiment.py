import json
import socket

import pytest

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion


def test_grid_endpoints_dedup_and_short_union():
    settings = fusion.grid()
    assert len(settings) == 38
    lexical = [f"p{i}" for i in range(100)]
    semantic = lexical[::-1]
    for depth in (20, 50, 100):
        subset = [s for s in settings.values() if s["depth"] == depth]
        assert len(subset) == (14 if depth == 100 else 12)
        for weight, ranking in ((0, lexical), (1, semantic)):
            endpoint = [s for s in subset if s["semantic_weight"] == weight]
            assert len(endpoint) == (1 if depth == 100 else 0)
            if endpoint:
                assert fusion.fuse(lexical, semantic, **endpoint[0]) == ranking
    ids = fusion.fuse(lexical, lexical, depth=20, k=100)
    assert len(ids) == len(set(ids)) == 20
    fusion.validate_run("short-union", {"q": ids}, ["q"], dict.fromkeys(lexical))


@pytest.mark.parametrize("run,match", [
    ({}, "exactly"),
    ({"q": ["a"] * 100}, "duplicate"),
    ({"q": [f"unknown{i}" for i in range(100)]}, "unknown"),
    ({"q": ["a"]}, "insufficient"),
    ({"q": ["a", "b"], "test": ["a", "b"]}, "exactly"),
])
def test_source_validation(run, match):
    with pytest.raises(ValueError, match=match):
        fusion.validate_run("source", run, ["q"], {"a": {}, "b": {}}, exact_depth=100)


def test_source_requires_full100():
    ids = [str(i) for i in range(20)]
    with pytest.raises(ValueError, match="depth 100"):
        fusion.validate_run("source", {"q": ids}, ["q"], dict.fromkeys(ids), exact_depth=100)


def test_prepare_retains_frozen_original_and_shared_pool(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(fusion.graded, "SYSTEMS", [fusion.ORIGINAL, "old"])
    ids = [str(i) for i in range(110)]
    folder = tmp_path / "dev"
    folder.mkdir()
    for name in (fusion.LEXICAL, fusion.SEMANTIC, fusion.ORIGINAL, "old"):
        ranked = ids[10:] if name == "old" else ids[:100]
        (folder / f"{name}.run.json").write_text(json.dumps({"q": ranked}))
    runs, configs, provenance = fusion.prepare(dict.fromkeys(ids), ["q"])
    assert runs[fusion.BASELINE] == runs[fusion.ORIGINAL]
    assert configs[fusion.BASELINE]["frozen_from"] == fusion.ORIGINAL
    assert len(configs) == 41
    assert provenance[fusion.LEXICAL]["ranking_sha256"] == fusion.fingerprint({"q": ids[:100]})
    pool = fusion.graded.pooled_pairs(runs, ["q"])["q"]
    assert len(pool) == len(set(pool))
    assert set(ids[10:20]) <= set(pool)
    for bad in ([], ["q", "q"]):
        with pytest.raises(ValueError, match="dev query IDs"):
            fusion.prepare(dict.fromkeys(ids), bad)


def test_paired_alignment_regressions_and_undefined(monkeypatch):
    monkeypatch.setattr(config, "BOOTSTRAP_SAMPLES", 10)
    left = [{"query_id": "b", "m": None}, {"query_id": "a", "m": 0.4},
            {"query_id": "c", "m": 0.8}]
    right = [{"query_id": "c", "m": 0.3}, {"query_id": "a", "m": 0.7},
             {"query_id": "b", "m": None}]
    paired = fusion.paired_rows(left, right, "m")
    assert paired["difference"] == pytest.approx(-0.1)
    assert paired["wins"] == paired["regressions"] == 1
    assert paired["n"] == 2
    assert paired["per_query_difference"]["c"] == pytest.approx(-0.5)
    with pytest.raises(ValueError, match="identical query IDs"):
        fusion.paired_rows(left, right[:1], "m")
    with pytest.raises(ValueError, match="unique"):
        fusion.paired_rows(left + left[:1], right, "m")


def publish_fixture(tmp_path, monkeypatch, *, complete):
    monkeypatch.setattr(config, "NDCG_K", 2)
    monkeypatch.setattr(fusion.graded, "SHEET_PATH", tmp_path / "absent.xlsx")
    queries = {"q": {"query_type": "keyword"}}
    runs = {fusion.BASELINE: {"q": ["a", "b"]}, "new": {"q": ["a", "c"]},
            "old": {"q": ["d", "b"]}}
    pairs = fusion.graded.pooled_pairs(runs, ["q"], 2)
    labels = {"q": {"a": 1, "b": 0, "d": 2}}
    if complete:
        labels["q"]["c"] = 0
    text = fusion.publish(runs, {}, {}, labels, pairs, queries, {"q": {"a": 2}},
                          1, config.DEFAULT_JUDGE, tmp_path / "out")
    return text, json.loads((tmp_path / "out" / "report.json").read_text())


def test_common_denominator_preserves_prior_pool_and_human(tmp_path, monkeypatch):
    text, report = publish_fixture(tmp_path, monkeypatch, complete=True)
    snapshot = json.loads((tmp_path / "out" / "labels.json").read_text())
    assert snapshot["complete"] is True
    assert snapshot["pool_pairs"] == snapshot["pool_judged"] == 4
    assert snapshot["human_overrides"] == 1
    scores = report["graded"]
    expected = fusion.metrics.ndcg_at_k(["a", "b"], snapshot["labels"]["q"], 2)
    assert scores[fusion.BASELINE]["all"]["ndcg@2"]["mean"] == expected
    assert scores["new"]["all"]["ndcg@2"]["mean"] == expected
    assert expected < 0.5  # old system's d=2 remains in every ideal denominator
    assert "COMPLETE" in text
    assert (tmp_path / "out" / "new.source.scores.jsonl").exists()
    assert (tmp_path / "out" / "new.graded.scores.jsonl").exists()
    assert scores["new"]["keyword"]["precision@2"]["paired_vs_baseline"]["ties"] == 1


def test_provisional_withholds_all_comparisons_and_is_deterministic(tmp_path, monkeypatch):
    text, report = publish_fixture(tmp_path, monkeypatch, complete=False)
    assert "INCOMPLETE / PROVISIONAL" in text
    assert report["provisional"] is True
    for family in ("graded", "source"):
        for groups in report[family].values():
            for fields in groups.values():
                assert all(s["paired_vs_baseline"] is None for s in fields.values())
    before = {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()}
    publish_fixture(tmp_path, monkeypatch, complete=False)
    assert before == {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()}


@pytest.fixture
def cli_inputs(tmp_path, monkeypatch):
    ids = [f"p{i}" for i in range(10)]
    papers = dict.fromkeys(ids, {})
    queries = {"q": {"query_type": "keyword"}}
    runs = {fusion.BASELINE: {"q": ids}, "new": {"q": ids[::-1]}}
    monkeypatch.setattr(fusion.judge, "load_inputs", lambda: (papers, queries, {"dev": ["q"]}))
    monkeypatch.setattr(fusion, "prepare", lambda *args: (runs, {}, {}))
    monkeypatch.setattr(config, "EVAL_DIR", tmp_path)
    monkeypatch.setattr(fusion.graded, "SHEET_PATH", tmp_path / "absent.xlsx")
    (tmp_path / "labels.json").write_text(json.dumps({"q": {"p0": 2}}))
    monkeypatch.setattr(fusion.graded, "read_human_grades", lambda: {("q", "p0"): 0})
    monkeypatch.setattr(fusion.judge, "grades_for", lambda *args: {"q": {"p0": 2}})
    return tmp_path / "out"


def test_default_cli_never_calls_network_and_human_overrides(cli_inputs, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network or labeling call")
    monkeypatch.setattr(fusion.judge, "judge_pairs", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    fusion.main(["--output-dir", str(cli_inputs)])
    assert "Shared pool: 10 pairs; 1 cached/human covered; 9 missing before labeling." in capsys.readouterr().out
    snapshot = json.loads((cli_inputs / "labels.json").read_text())
    assert snapshot["labels"]["q"]["p0"] == 0
    assert snapshot["judge"] == config.DEFAULT_JUDGE
    assert snapshot["provisional"] is True


def test_label_error_publishes_partial_and_propagates(cli_inputs, monkeypatch):
    seen = []
    def fail(key, pairs, queries, papers, *, max_calls):
        seen.append((key, pairs, max_calls))
        raise RuntimeError("judge failed")
    monkeypatch.setattr(fusion.judge, "judge_pairs", fail)
    with pytest.raises(RuntimeError, match="judge failed"):
        fusion.main(["--label", "--max-calls", "3", "--judge", "openai-4.1-mini",
                     "--output-dir", str(cli_inputs)])
    assert seen[0][0] == "openai-4.1-mini" and seen[0][2] == 3
    assert "p0" not in seen[0][1]["q"]
    assert json.loads((cli_inputs / "labels.json").read_text())["provisional"] is True
    assert (cli_inputs / "report.md").exists()


def test_zero_budget_never_calls_judge(cli_inputs, monkeypatch):
    monkeypatch.setattr(fusion.judge, "judge_pairs", lambda *a, **k: pytest.fail("No budget"))
    fusion.main(["--label", "--max-calls", "0", "--output-dir", str(cli_inputs)])
    with pytest.raises(SystemExit):
        fusion.main(["--max-calls", "-1"])
