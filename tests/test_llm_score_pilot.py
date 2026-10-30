import json
import sqlite3

import httpx
import pytest

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import llm_score_pilot as pilot


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_LEDGER_PATH", tmp_path / "usage.sqlite3")
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 2_500_000, "large": 1})
    monkeypatch.setattr(config, "OPENAI_BUDGET_FRACTION", 1.)
    monkeypatch.setattr(pilot, "OUT", tmp_path / "scores-v2")
    monkeypatch.setattr(pilot.v1, "OUT", tmp_path / "list-v1")
    monkeypatch.setattr(client, "load_dotenv", lambda path: None)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr(client.httpx, "post", forbidden)


def papers():
    return {f"p{i}": {"title": f"Title{i}", "abstract": "Full abstract.",
                     "authors": [f"Author{j}" for j in range(12)]} for i in range(100)}


@pytest.mark.parametrize("size", [10, 50])
def test_fixed_required_keys_and_exact_same_documents_as_v1(size):
    ps = papers()
    ids = list(ps)[:size]
    old = json.loads(client.encode_payload("query", ids, ps))
    new = json.loads(client.encode_score_payload("query", ids, ps))
    assert new["input"] == old["input"]
    assert new["model"] == old["model"] and new["reasoning"] == {"effort": "none"}
    assert new["max_output_tokens"] == 1024
    schema = new["text"]["format"]["schema"]
    assert schema["type"] == "object" and schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"]) == {f"P{i}" for i in range(1, size + 1)}
    assert all(v == {"type": "integer", "minimum": 0, "maximum": 4}
               for v in schema["properties"].values())
    assert client.request_key(client.encode_payload("query", ids, ps)) != client.request_key(
        client.encode_score_payload("query", ids, ps))


@pytest.mark.parametrize("invalid", [True, 1.0, "1", -1, 5, None])
def test_scores_reject_nonintegers_booleans_and_out_of_range(invalid):
    scores = {f"P{i}": 2 for i in range(1, 11)}
    scores["P1"] = invalid
    with pytest.raises(ValueError):
        client.validate_scores(scores, 10)


def test_missing_extra_and_duplicate_json_keys_are_rejected():
    scores = {f"P{i}": 2 for i in range(1, 11)}
    for bad in ({k: v for k, v in scores.items() if k != "P1"}, {**scores, "P11": 1}):
        with pytest.raises(ValueError):
            client.parse_scores(json.dumps(bad), 10)
    duplicate = json.dumps(scores)[:-1] + ', "P1": 4}'
    with pytest.raises(ValueError, match="Duplicate JSON"):
        client.parse_scores(duplicate, 10)
    assert client.parse_scores(json.dumps(scores), 10) == scores


def test_client_ties_follow_baseline_not_presentation_order_and_tail_is_unchanged():
    base = list(papers())
    presented = list(reversed(base[:50]))
    scores = {f"P{i}": 2 for i in range(1, 51)}
    assert pilot.apply_scores(base, presented, scores) == base
    scores["P1"] = 4
    result = pilot.apply_scores(base, presented, scores)
    assert result[0] == base[49]
    assert result[1:50] == base[:49]
    assert result[50:] == base[50:]
    with pytest.raises(ValueError):
        pilot.apply_scores(base, base[10:20], {f"P{i}": 2 for i in range(1, 11)})


def test_legacy_ledger_migration_preserves_rows_and_combines_budget(monkeypatch):
    api.Ledger()
    old_request = api.Ledger().reserve(client.MODEL, 10, 20)
    with sqlite3.connect(config.OPENAI_LEDGER_PATH) as db:
        db.execute("CREATE TABLE mini_reranker_pilot_attempts "
                   "(request_key TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL)")
        db.execute("INSERT INTO mini_reranker_pilot_attempts VALUES (?,?)", ("a" * 64, old_request))
    v1 = client.PilotLedger()
    v2 = client.PilotLedger(version=pilot.VERSION)
    assert v1.summary()["requests"] == 1 and v2.summary()["requests"] == 0
    old_cost = 10 * client.INPUT_PRICE + 20 * client.OUTPUT_PRICE
    assert v2.combined_cost_nanodollars() == old_cost
    new_cost = 10 * client.INPUT_PRICE + 1024 * client.OUTPUT_PRICE
    monkeypatch.setattr(client, "TASK_CAP", old_cost + new_cost - 1)
    with pytest.raises(api.BudgetExceeded):
        v2.reserve_request("b" * 64, 10)
    monkeypatch.setattr(client, "TASK_CAP", old_cost + new_cost)
    v2.reserve_request("b" * 64, 10)
    assert v2.summary()["requests"] == 1 and v1.summary()["requests"] == 1
    assert v2.combined_cost_nanodollars() == old_cost + new_cost
    assert v2.summary()["shared_accounted_tokens"] == 30 + 10 + 1024


def test_smoke_then_full_execution_reuses_responses_and_reports_all_queries(monkeypatch):
    pilot.OUT.mkdir()
    ps = papers()
    qs = {f"q{i}": {"query_type": kind, "query": f"query{i}", "source_arxiv_id": "p0"}
          for i, kind in enumerate(pilot.catalog.QUERY_TYPES)}
    qids = sorted(qs)
    base = {q: list(ps) for q in qids}
    snapshot = {"labels": {q: {p: 2 if p == "p0" else 0 for p in list(ps)[:10]}
                           for q in qids}, "query_ids": qids}
    requests = []
    for depth in pilot.v1.DEPTHS:
        for q in qids:
            presented = pilot.v1.presentation(q, base[q][:depth])
            encoded = client.encode_score_payload(qs[q]["query"], presented, ps)
            requests.append({"query_id": q, "depth": depth, "presented_ids": presented,
                             "encoded": encoded, "request_key": client.request_key(encoded)})
    monkeypatch.setattr(pilot, "prepare", lambda: (ps, qs, qids, base, snapshot, requests, {}))
    calls = []

    def post(url, **kwargs):
        payload = json.loads(kwargs["content"])
        data = json.loads(payload["input"])
        calls.append((data["query"], len(data["papers"])))
        scores = {p["paper"]: 2 for p in data["papers"]}
        return httpx.Response(200, json={
            "status": "completed", "model": client.MODEL,
            "usage": {"input_tokens": 100, "output_tokens": 25, "total_tokens": 125,
                      "output_tokens_details": {"reasoning_tokens": 0}},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(scores)}]}]})

    monkeypatch.setattr(client.httpx, "post", post)
    pilot.main(["--run", "--smoke"])
    assert calls == [("query0", 10), ("query0", 50)]
    assert not (pilot.OUT / "report.json").exists()
    pilot.main(["--run"])
    assert len(calls) == 8
    report_bytes = (pilot.OUT / "report.json").read_bytes()
    report = json.loads(report_bytes)
    assert report["primary"]["matched_queries"] == 4
    assert all(not f for f in report["failures"].values())
    for depth in pilot.v1.DEPTHS:
        result = json.loads((pilot.OUT / f"{pilot.system_name(depth)}.run.json").read_text())
        assert result == base
    pilot.main(["--run"])
    assert len(calls) == 8 and (pilot.OUT / "report.json").read_bytes() == report_bytes
    assert client.PilotLedger(version=pilot.VERSION).summary()["accounted_tokens"] == 1000
    assert client.PilotLedger().summary()["requests"] == 0


def test_score_client_records_duplicate_key_failure_without_retry(monkeypatch, tmp_path):
    ps = papers()
    encoded = client.encode_score_payload("query", list(ps)[:10], ps)
    ledger = client.PilotLedger(version=pilot.VERSION)
    text = json.dumps({f"P{i}": 2 for i in range(1, 11)})[:-1] + ', "P1": 4}'
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        return httpx.Response(200, json={
            "status": "completed", "model": client.MODEL,
            "usage": {"input_tokens": 100, "output_tokens": 25, "total_tokens": 125},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]})

    monkeypatch.setattr(client.httpx, "post", post)
    path = tmp_path / "failure.json"
    with pytest.raises(api.OpenAIError, match="invalid_answer"):
        client.call_once(encoded, 10, ledger, failure_output_path=path)
    assert ledger.summary()["accounted_tokens"] == 125
    assert "Duplicate JSON" in json.loads(path.read_text())["validation_error"]
    with pytest.raises(api.OpenAIError, match="already attempted"):
        client.call_once(encoded, 10, ledger)
    assert len(calls) == 1


@pytest.mark.parametrize("fail_at", [1, 3])
def test_any_failure_stops_and_resume_cannot_send_more_requests(monkeypatch, fail_at):
    pilot.OUT.mkdir()
    ps = papers()
    qids = ["q0", "q1"]
    qs = {q: {"query": q, "query_type": "question", "source_arxiv_id": "p0"} for q in qids}
    base = {q: list(ps) for q in qids}
    snapshot = {"labels": {q: {"p0": 2} for q in qids}, "query_ids": qids}
    requests = []
    for depth in pilot.v1.DEPTHS:
        for q in qids:
            ids = base[q][:depth]
            encoded = client.encode_score_payload(q, ids, ps)
            requests.append({"query_id": q, "depth": depth, "presented_ids": ids,
                             "encoded": encoded, "request_key": client.request_key(encoded)})
    monkeypatch.setattr(pilot, "prepare", lambda: (ps, qs, qids, base, snapshot, requests, {}))
    calls = []

    def post(url, **kwargs):
        data = json.loads(json.loads(kwargs["content"])["input"])
        calls.append(data["query"])
        scores = {p["paper"]: 2 for p in data["papers"]}
        if len(calls) == fail_at:
            scores.pop("P1")
        return httpx.Response(200, json={
            "status": "completed", "model": client.MODEL,
            "usage": {"input_tokens": 100, "output_tokens": 25, "total_tokens": 125},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(scores)}]}]})

    monkeypatch.setattr(client.httpx, "post", post)
    with pytest.raises(api.OpenAIError, match="invalid_answer"):
        pilot.main(["--run"])
    assert len(calls) == fail_at
    assert (pilot.OUT / "failed-requests.json").exists()
    assert not (pilot.OUT / "report.json").exists()
    with pytest.raises(api.OpenAIError, match="investigate"):
        pilot.main(["--run"])
    assert len(calls) == fail_at
    assert client.PilotLedger(version=pilot.VERSION).summary()["accounted_tokens"] == fail_at * 125


def test_comparison_gates_incomplete_labels_and_pairs_v1_only_on_same_queries():
    ps = papers()
    qs = {f"q{i}": {"query_type": kind, "query": kind, "source_arxiv_id": "p0"}
          for i, kind in enumerate(pilot.catalog.QUERY_TYPES)}
    qids = sorted(qs)
    base = {q: list(ps) for q in qids}
    old = {q: base[q] for q in qids[:3]}
    new = {q: base[q][:50][::-1] + base[q][50:] for q in qids}
    snapshot = {"labels": {q: {p: 2 if p == "p0" else 0 for p in list(ps)[:10]}
                           for q in qids}, "query_ids": qids}
    result = pilot.compare({"old": old, "new": new}, "old", snapshot, ps, qs, qids)
    assert result["matched_query_ids"] == qids[:3]
    assert result["systems"]["old"]["queries_expected"] == 3
    assert not result["systems"]["new"]["top10_fully_judged"]
    assert result["summary"]["new"]["all"]["ndcg@10"]["paired_vs_working"] is None
    assert result["summary"]["new"]["all"]["source_mrr@10"]["paired_vs_working"] is not None
