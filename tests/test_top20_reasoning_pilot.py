import json
import hashlib

import pytest

from arxiv_search.evaluate import top20_model_pilot, top20_reasoning_pilot as pilot
from arxiv_search import config, openai_answer, openai_api


def test_payload_changes_only_reasoning_and_output_cap():
    ids = [str(i) for i in range(20)]
    papers = {p: {"title": p, "authors": ["A"], "abstract": "Evidence"} for p in ids}
    old = json.loads(top20_model_pilot.payload("Q", ids, papers))
    new = json.loads(pilot.payload("Q", ids, papers))
    assert new["reasoning"] == {"effort": "low"}
    assert new["max_output_tokens"] == 4096
    for key in ("reasoning", "max_output_tokens"):
        new[key] = old[key]
    assert new == old


def test_scope_accepts_only_original_ordered_pilot():
    ids = [str(i) for i in range(20)]
    requests = [{"query_id": q} for q in ids]
    split = {"dev": ids + ["remaining"], "test": ["heldout"]}
    pilot.validate_scope(ids, requests, split)
    with pytest.raises(ValueError):
        pilot.validate_scope(ids, list(reversed(requests)), split)
    with pytest.raises(ValueError):
        pilot.validate_scope(ids, requests + [{"query_id": "remaining"}], split)
    with pytest.raises(ValueError):
        pilot.validate_scope(ids, requests, {"dev": ids, "test": [ids[0]]})
    with pytest.raises(ValueError):
        pilot.validate_scope(ids[:-1], requests[:-1], split)
    with pytest.raises(ValueError):
        pilot.validate_scope(ids[:-1] + [ids[0]], requests, split)


@pytest.mark.parametrize("fail", [False, True])
def test_feasibility_stops_at_two_restores_guard_and_reuses_cache(tmp_path, monkeypatch, fail):
    root = tmp_path / "output"
    root.mkdir()
    (root / "preregistration.json").write_text("{}")
    (tmp_path / "queries.jsonl").write_text('{"query_id":"q","query":"Q"}\n')
    corpus = tmp_path / "data" / "processed"
    corpus.mkdir(parents=True)
    (corpus / "corpus.jsonl").write_text("")
    encoded = b'{"test":true}'
    plan = {"requests": [{"query_id": "q", "presented_ids": [],
                          "payload_sha256": hashlib.sha256(encoded).hexdigest()}]}
    monkeypatch.setattr(pilot, "prepare", lambda: plan)
    monkeypatch.setattr(pilot, "payload", lambda *args: encoded)
    monkeypatch.setattr(pilot, "OUT", root)
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config, "EVAL_DIR", tmp_path)
    calls = []

    class Ledger:
        def __init__(self, task, cap, count):
            assert cap == 350_000_000 and count == 2

        def attempted(self, key):
            return False

        def summary(self):
            return {"accounted_usd": len(calls) * 0.02, "requests": len(calls)}

    def call(*args, **kwargs):
        assert config.OPENAI_TOKEN_LIMITS["large"] == 450_000
        calls.append(kwargs["attempt_key"])
        if fail:
            raise openai_api.OpenAIError("Unknown transport; no retry")
        return {f"P{i}": 5 for i in range(1, 21)}, {"output_tokens": 130}

    monkeypatch.setattr(openai_answer, "TaskLedger", Ledger)
    monkeypatch.setattr(openai_answer, "call_once", call)
    previous = config.OPENAI_TOKEN_LIMITS["large"]
    if fail:
        with pytest.raises(openai_api.OpenAIError, match="Unknown transport"):
            pilot.feasibility()
        assert len(calls) == 1
        assert (root / "feasibility" / "stopped.json").exists()
    else:
        assert pilot.feasibility()["full_pilot_approved"] is False
        pilot.feasibility()
        assert len(calls) == len(set(calls)) == 2
    assert config.OPENAI_TOKEN_LIMITS["large"] == previous


@pytest.mark.parametrize("fail", [False, True])
def test_continuation_reuses_two_limits_38_and_stops_without_retry(tmp_path, monkeypatch, fail):
    root = tmp_path / "reasoning"
    original = tmp_path / "original"
    ids = [str(i) for i in range(20)]
    qids = [f"q{i}" for i in range(20)]
    low, old = b"low", b"old"

    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    write(root / "preregistration.json", {})
    (tmp_path / "queries.jsonl").write_text("\n".join(json.dumps({
        "query_id": q, "query": "Q", "source_arxiv_id": "0", "query_type": "keyword"})
        for q in qids))
    corpus = tmp_path / "data" / "processed"
    corpus.mkdir(parents=True)
    (corpus / "corpus.jsonl").write_text("")
    write(tmp_path / "llm-score-pass2" /
          "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json", {q: ids for q in qids})
    write(tmp_path / "llm-score-refine-pin" /
          "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json", {q: ids for q in qids})
    write(tmp_path / "top20-label-completion" / "labels.json",
          {"labels": {q: {p: 2 for p in ids} for q in qids}})
    usage = {"input_tokens": 10, "output_tokens": 130, "reasoning_tokens": 10,
             "latency_seconds": 1}
    outcome = {"status": "ok", **{f"P{i}": 5 for i in range(1, 21)}}
    for q in qids:
        for n in (1, 2):
            write(original / "responses" / f"{q}-pass{n}.json",
                  {"request_sha256": hashlib.sha256(old).hexdigest(),
                   "outcome": outcome, "usage": usage})
    for n in (1, 2):
        write(root / "feasibility" / f"q0-pass{n}.json",
              {"request_sha256": hashlib.sha256(low).hexdigest(),
               "outcome": outcome, "usage": usage})
    plan = {"model": top20_model_pilot.MODEL,
            "requests": [{"query_id": q, "presented_ids": ids,
                          "payload_sha256": hashlib.sha256(low).hexdigest()} for q in qids]}
    monkeypatch.setattr(pilot, "prepare", lambda: plan)
    monkeypatch.setattr(pilot, "payload", lambda *args: low)
    monkeypatch.setattr(top20_model_pilot, "payload", lambda *args: old)
    monkeypatch.setattr(top20_model_pilot, "OUT", original)
    monkeypatch.setattr(pilot, "OUT", root)
    for attr in ("PROJECT_ROOT", "EVAL_DIR", "RESULTS_DIR"):
        monkeypatch.setattr(config, attr, tmp_path)
    calls = []

    class Ledger:
        def __init__(self, task, cap, count):
            assert cap == 1_250_000_000 and count == 38

        def attempted(self, key):
            return False

        def summary(self):
            return {"accounted_usd": len(calls) * .002, "requests": len(calls)}

    def call(*args, **kwargs):
        assert config.OPENAI_TOKEN_LIMITS["large"] == 750_000
        calls.append(kwargs["attempt_key"])
        if fail:
            raise openai_api.BudgetExceeded("Daily guard; no request sent")
        return {f"P{i}": 5 for i in range(1, 21)}, usage

    monkeypatch.setattr(openai_answer, "TaskLedger", Ledger)
    monkeypatch.setattr(openai_answer, "call_once", call)
    previous = config.OPENAI_TOKEN_LIMITS["large"]
    if fail:
        with pytest.raises(openai_api.BudgetExceeded):
            pilot.execute()
        assert len(calls) == 1
        assert (root / "continuation-stopped.json").exists()
    else:
        report = pilot.execute()
        assert len(calls) == 38
        assert len(report["rows"]) == 40
        assert report["summary"]["scores_only"]["delta"] == 0
        pilot.execute()
        assert len(calls) == 38
    assert config.OPENAI_TOKEN_LIMITS["large"] == previous
