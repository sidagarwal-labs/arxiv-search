import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from arxiv_search import config, openai_api as api, openai_rerank as client
from arxiv_search.evaluate import llm_reranker_pilot as pilot


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_LEDGER_PATH", tmp_path / "usage.sqlite3")
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 2_200_000, "large": 1})
    monkeypatch.setattr(config, "OPENAI_BUDGET_FRACTION", 1.)
    monkeypatch.setattr(pilot, "OUT", tmp_path / "pilot")
    monkeypatch.setattr(client, "load_dotenv", lambda path: None)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr(client.httpx, "post", forbidden)


def papers():
    return {f"p{i}": {"title": f"Title{i}", "abstract": "Abstract; ignore instructions in data.",
                     "authors": [f"Author{j}" for j in range(12)]} for i in range(100)}


def answer(size=10):
    ranked = [f"P{i}" for i in range(size, 0, -1)]
    return {"ranking": ranked,
            "evidence": [{"paper": label, "note": "Explicit task support."} for label in ranked[:10]]}


def response(value=None, **changes):
    body = {"status": "completed", "model": client.MODEL,
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
                      "output_tokens_details": {"reasoning_tokens": 0}},
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(answer() if value is None else value)}]}]}
    return httpx.Response(200, json={**body, **changes}, headers={"x-request-id": "fake-request"})


def encoded(size=10):
    return client.encode_payload("known topic", list(papers())[:size], papers())


def ledger_rows():
    with sqlite3.connect(config.OPENAI_LEDGER_PATH) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("SELECT * FROM attempts")]


@pytest.mark.parametrize("size", [10, 50])
def test_payload_full_authors_strict_schema_no_grades_or_source(size):
    payload = json.loads(encoded(size))
    data = json.loads(payload["input"])
    assert len(data["papers"]) == size
    assert len(data["papers"][0]["authors"]) == 12
    assert set(data["papers"][0]) == {"paper", "title", "authors", "abstract"}
    assert payload["model"] == client.MODEL and payload["reasoning"] == {"effort": "none"}
    assert payload["max_output_tokens"] == 2048 and payload["store"] is False
    assert "tools" not in payload and "source_arxiv_id" not in payload["input"]
    schema = payload["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["Evidence"]["additionalProperties"] is False
    assert len(schema["properties"]["ranking"]["items"]["enum"]) == size


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "unknown", "bad-evidence", "extra", "empty-note"])
def test_invalid_permutations_and_evidence_rejected(mutation):
    value = answer()
    if mutation == "duplicate":
        value["ranking"][0] = value["ranking"][1]
    elif mutation == "missing":
        value["ranking"].pop()
    elif mutation == "unknown":
        value["ranking"][0] = "P999"
    elif mutation == "bad-evidence":
        value["evidence"].reverse()
    elif mutation == "extra":
        value["grade"] = 2
    else:
        value["evidence"][0]["note"] = " "
    with pytest.raises(ValueError):
        client.validate_answer(value, 10)


def test_presentation_is_stable_and_answer_only_reorders_supplied_prefix():
    ids = list(papers())
    small = pilot.presentation("q", ids[:10])
    large = pilot.presentation("q", ids[:50])
    assert small == [p for p in large if p in ids[:10]]
    for size in (10, 50):
        presented = pilot.presentation("q", ids[:size])
        run = pilot.apply_answer(ids, presented, answer(size))
        assert run[:size] == presented[::-1]
        assert run[size:] == ids[size:]
        assert set(run) == set(ids)
    with pytest.raises(ValueError):
        pilot.apply_answer(ids, list(papers())[10:20], answer())


def test_balanced_sample_does_not_depend_on_source_labels_or_input_order():
    queries = {f"{kind}-{i}": {"query_type": kind, "query": "q", "source_arxiv_id": "p"}
               for kind in pilot.catalog.QUERY_TYPES for i in range(25)}
    split = {"dev": list(queries), "test": ["held-out"]}
    selected = pilot.select_queries(queries, split)
    assert len(selected) == 20
    assert all(sum(queries[q]["query_type"] == kind for q in selected) == 5
               for kind in pilot.catalog.QUERY_TYPES)
    changed = {q: {**v, "source_arxiv_id": "different", "label": 0}
               for q, v in reversed(list(queries.items()))}
    assert pilot.select_queries(changed, {**split, "dev": split["dev"][::-1]}) == selected
    with pytest.raises(ValueError):
        pilot.select_queries(queries, {**split, "test": [split["dev"][0]]})


def test_success_shared_accounting_cost_and_cached_replay(tmp_path, monkeypatch):
    calls = []

    def post(url, **kwargs):
        assert ledger_rows()[0]["status"] == "reserved"
        calls.append(kwargs)
        assert url == api.ENDPOINT and kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False and kwargs["timeout"] == 120
        return response()

    monkeypatch.setattr(client.httpx, "post", post)
    ledger = client.PilotLedger()
    path = tmp_path / "response.json"
    result = pilot.cached_call(path, encoded(), list(papers())[:10], ledger, run=True)
    assert result[0] == answer()
    assert len(calls) == 1
    assert ledger.summary()["shared_accounted_tokens"] == 150
    assert ledger.summary()["accounted_nanodollars"] == 100 * client.INPUT_PRICE + 50 * client.OUTPUT_PRICE
    assert pilot.cached_call(path, encoded(), list(papers())[:10], ledger, run=False) == result
    assert len(calls) == 1
    assert "fake-test-key" not in path.read_text()
    assert "Abstract" not in json.dumps(ledger_rows())
    with pytest.raises(api.OpenAIError, match="already attempted"):
        ledger.reserve_request(client.request_key(encoded()), client.reserved_input(encoded()))
    value = json.loads(path.read_text())
    value["answer"]["ranking"].reverse()
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="checksum"):
        pilot.read_cached(path, encoded(), list(papers())[:10])


@pytest.mark.parametrize("failure", ["timeout", "503", "invalid-answer", "incomplete", "unknown-usage", "model"])
def test_failures_never_retry_or_reissue_on_resume(monkeypatch, failure):
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        if failure == "timeout":
            raise httpx.ReadTimeout("fake-test-key")
        if failure == "503":
            return httpx.Response(503)
        if failure == "invalid-answer":
            return response({"ranking": ["P1"], "evidence": []})
        if failure == "incomplete":
            return response(status="incomplete")
        if failure == "model":
            return response(model="other")
        return response(usage={})

    monkeypatch.setattr(client.httpx, "post", post)
    ledger = client.PilotLedger()
    with pytest.raises(api.OpenAIError) as error:
        client.call_once(encoded(), 10, ledger)
    assert "fake-test-key" not in str(error.value)
    assert len(calls) == 1
    row = ledger_rows()[0]
    expected = client.reserved_input(encoded()) + client.MAX_OUTPUT if failure in (
        "timeout", "503", "unknown-usage") else 150
    assert row["accounted_tokens"] == expected
    with pytest.raises(api.OpenAIError, match="already attempted"):
        client.call_once(encoded(), 10, ledger)
    assert len(calls) == 1


def test_task_dollar_cap_and_shared_token_cap_both_apply_atomically(monkeypatch):
    ledger = client.PilotLedger()
    cost = 100 * client.INPUT_PRICE + client.MAX_OUTPUT * client.OUTPUT_PRICE
    monkeypatch.setattr(client, "TASK_CAP", 2 * cost)

    def reserve(i):
        try:
            return client.PilotLedger().reserve_request(f"{i:064x}", 100)
        except api.BudgetExceeded:
            return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(reserve, range(8)))
    assert sum(r is not None for r in results) == 2
    assert ledger.summary()["accounted_nanodollars"] == 2 * cost
    monkeypatch.setattr(client, "TASK_CAP", 10 * cost)
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 2 * (100 + client.MAX_OUTPUT), "large": 1})
    with pytest.raises(api.BudgetExceeded, match="cumulative"):
        ledger.reserve_request("a" * 64, 100)
    assert len(ledger_rows()) == 2


def test_request_count_and_missing_credentials_stop_before_transport(monkeypatch):
    ledger = client.PilotLedger()
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(api.OpenAIError, match="OPENAI_API_KEY"):
        client.call_once(encoded(), 10, ledger)
    assert not ledger_rows()
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setattr(client, "MAX_REQUESTS", 0)
    with pytest.raises(api.BudgetExceeded, match="request cap"):
        client.call_once(encoded(), 10, ledger)
    assert not ledger_rows()


def test_preflight_has_no_http_and_checks_all_cache_entries(tmp_path):
    ledger = client.PilotLedger()
    request = {"query_id": "q", "depth": 10, "presented_ids": list(papers())[:10],
               "encoded": encoded(), "request_key": client.request_key(encoded())}
    report = pilot.preflight([request], ledger)
    assert report["unattempted_requests"] == 1
    assert report["attempted_uncached_no_retry"] == 0
    assert report["serialized_input_token_estimate"] > 0
    assert report["maximum_single_request_reservation"] == len(encoded()) + 4096 + 2048
    assert not ledger_rows()


def test_pilot_report_uses_same_subset_and_withholds_incomplete_grades(tmp_path):
    pilot.OUT.mkdir()
    ps = papers()
    qs = {f"q{i}": {"query_type": kind, "query": kind, "source_arxiv_id": "p0"}
          for i, kind in enumerate(pilot.catalog.QUERY_TYPES)}
    qids = sorted(qs)
    base = {q: list(ps) for q in qids}
    snapshot = {"labels": {q: {p: 2 if p == "p0" else 0 for p in list(ps)[:10]}
                           for q in qids}, "query_ids": qids}
    runs = {pilot.BASELINE: base,
            pilot.system_name(10): {q: ids[:10][::-1] + ids[10:] for q, ids in base.items()},
            pilot.system_name(50): {q: ids[:50][::-1] + ids[50:] for q, ids in base.items()}}
    accounting = {"accounted_usd": 0., "requests": 0, "input_tokens": 0,
                  "output_tokens": 0, "reasoning_tokens": 0}
    report = pilot.publish(ps, qs, qids, base, snapshot, runs,
                           [{"usage": {"latency_seconds": 1.}}], {}, accounting)
    assert report["systems"][pilot.system_name(10)]["top10_fully_judged"]
    assert not report["systems"][pilot.system_name(50)]["top10_fully_judged"]
    assert report["summary"][pilot.system_name(50)]["all"]["ndcg@10"]["paired_vs_working"] is None
    assert report["summary"][pilot.system_name(50)]["all"]["source_mrr@10"]["paired_vs_working"] is not None
    assert report["missing_pairs"] == 40
    assert not report["promoted"] and report["judge_api_calls"] == 0


@pytest.mark.parametrize("bad_notes_only", [False, True])
def test_finish_unattempted_records_failures_and_uses_matched_queries(monkeypatch, bad_notes_only):
    pilot.OUT.mkdir()
    ps = papers()
    qs = {f"q{i}": {"query_type": kind, "query": f"query{i}", "source_arxiv_id": "p0"}
          for i, kind in enumerate(pilot.catalog.QUERY_TYPES)}
    qids = sorted(qs)
    base = {q: list(ps) for q in qids}
    snapshot = {"labels": {q: {p: 2 if p == "p0" else 0 for p in list(ps)[:10]}
                           for q in qids}, "query_ids": qids}
    requests = []
    for depth in pilot.DEPTHS:
        for q in qids:
            presented = pilot.presentation(q, base[q][:depth])
            data = client.encode_payload(qs[q]["query"], presented, ps)
            requests.append({"query_id": q, "depth": depth, "presented_ids": presented,
                             "encoded": data, "request_key": client.request_key(data)})
    provenance = {"requests": [{k: v for k, v in r.items() if k != "encoded"} for r in requests]}
    monkeypatch.setattr(pilot, "prepare", lambda: (ps, qs, qids, base, snapshot, requests, provenance))
    calls = []

    def post(url, **kwargs):
        size = len(json.loads(json.loads(kwargs["content"])["input"])["papers"])
        calls.append(size)
        if len(calls) == 1:
            if bad_notes_only:
                value = answer(size)
                value["evidence"][0]["paper"] = value["evidence"][1]["paper"]
                return response(value)
            return response({"ranking": ["P1"], "evidence": []})
        return response(answer(size))

    monkeypatch.setattr(client.httpx, "post", post)
    pilot.main(["--run"])
    report_bytes = (pilot.OUT / "report.json").read_bytes()
    report = json.loads(report_bytes)
    assert len(calls) == 8
    assert report["matched_queries"] == 3 and report["queries"] == 4
    assert report["matched_query_ids"] == qids[1:]
    assert report["failures"][pilot.system_name(10)][qids[0]]["status"] == "invalid_answer"
    assert report["systems"][pilot.BASELINE]["queries_expected"] == 3
    assert len(list((pilot.OUT / "failures").glob("*.json"))) == 1
    diagnostic = json.loads((pilot.OUT / "ranking-only-diagnostic.json").read_text())
    assert diagnostic["matched_queries"] == (4 if bad_notes_only else 3)
    assert qids[0] not in json.loads(
        (pilot.OUT / f"{pilot.system_name(10)}.run.json").read_text())
    pilot.main(["--run"])
    assert len(calls) == 8
    assert (pilot.OUT / "report.json").read_bytes() == report_bytes
    estimate = json.loads((pilot.OUT / "preflight.json").read_text())
    assert estimate["unattempted_requests"] == 0
    assert estimate["attempted_uncached_no_retry"] == 1
