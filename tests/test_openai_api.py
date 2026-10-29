"""Offline tests: every transport and dotenv load is replaced before any call."""

import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from arxiv_search import config, openai_api as api
from arxiv_search.evaluate import judge, judge_pilot


MODEL = "gpt-5.4-nano"
PROMPT = "SEARCH: private search\n\n[P1] Private title\nAbstract: private abstract"


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_LEDGER_PATH", tmp_path / "openai" / "usage.sqlite3")
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 1_500_000, "large": 150_000})
    monkeypatch.setattr(config, "OPENAI_BUDGET_FRACTION", 0.9)
    monkeypatch.setattr(config, "JUDGMENTS_DIR", tmp_path / "judgments")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setattr(api, "load_dotenv", lambda path: None)
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr(api.httpx, "post", forbidden)


def body(**overrides):
    result = {
        "status": "completed",
        "usage": {"input_tokens": 80, "output_tokens": 25, "total_tokens": 105,
                  "output_tokens_details": {"reasoning_tokens": 5}},
        "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(
                {"grades": [{"paper": "P1", "reason": "Matches search", "grade": 2}]})}
        ]}],
    }
    return {**result, **overrides}


def response(data=None, status=200, headers=None):
    return httpx.Response(status, json=body() if data is None else data,
                          headers={"x-request-id": "provider-id", **(headers or {})})


def rows():
    with sqlite3.connect(config.OPENAI_LEDGER_PATH) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("SELECT * FROM attempts ORDER BY rowid")]


def transport(monkeypatch, replies):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        value = replies.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(api.httpx, "post", post)
    return calls


def test_strict_payload_actual_usage_and_no_sensitive_ledger(monkeypatch):
    calls = transport(monkeypatch, [response()])
    answer, usage = api.generate_json(MODEL, PROMPT, "private system")
    assert answer["grades"][0]["grade"] == 2
    url, options = calls[0]
    assert url == "https://api.openai.com/v1/responses"
    assert options["timeout"] == 120 and options["follow_redirects"] is False
    assert options["trust_env"] is False
    assert options["headers"]["Authorization"] == "Bearer fake-test-key"
    payload = json.loads(options["content"])
    assert "fake-test-key" not in options["content"].decode()
    assert payload["model"] == MODEL and payload["store"] is False
    assert payload["reasoning"] == {"effort": "none"}
    assert payload["max_output_tokens"] == 2048
    fmt = payload["text"]["format"]
    assert fmt["strict"] is True and fmt["type"] == "json_schema"
    schema = fmt["schema"]
    for obj in [schema, schema["$defs"]["_PaperGrade"]]:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])
    properties = schema["$defs"]["_PaperGrade"]["properties"]
    assert properties["paper"]["enum"] == ["P1"] and properties["grade"]["enum"] == [0, 1, 2]
    attempt = rows()[0]
    assert attempt["status"] == "completed" and attempt["latency_seconds"] >= 0
    assert attempt["reserved_input"] == len(options["content"]) + 4096
    assert attempt["reserved_output"] == 2048
    assert attempt["accounted_tokens"] == 105  # reasoning isn't added twice
    assert attempt["reasoning_tokens"] == 5
    assert usage["request_id"] == attempt["request_id"]
    assert usage["provider_request_id"] == "provider-id"
    assert usage["attempts"] == 1 and usage["ledger_attempts"] == [attempt]
    assert usage["thinking_tokens"] == 5 and usage["unknown_reserved_tokens"] == 0
    assert usage["input_tokens"] == 80 and usage["output_tokens"] == 25
    serialized = json.dumps(attempt)
    for sensitive in ["fake-test-key", "private search", "Private title", "private system"]:
        assert sensitive not in serialized


def test_reservations_persist_share_mini_tier_and_never_reset(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 100, "large": 150_000})
    monkeypatch.setattr(config, "OPENAI_BUDGET_FRACTION", 1)
    request_id = api.Ledger().reserve(MODEL, 60, 10)
    with sqlite3.connect(config.OPENAI_LEDGER_PATH) as db:
        db.execute("UPDATE attempts SET started_utc = '2000-01-01T00:00:00+00:00'")
    second = api.Ledger()
    with pytest.raises(api.BudgetExceeded):
        second.reserve("gpt-5.4-mini", 21, 10)
    assert rows()[0]["accounted_tokens"] == 70 and rows()[0]["request_id"] == request_id
    assert second.reserve("gpt-5.4-mini", 20, 10)


def test_atomic_concurrent_reservations(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 100, "large": 150_000})
    monkeypatch.setattr(config, "OPENAI_BUDGET_FRACTION", 1)
    api.Ledger()

    def reserve(_):
        try:
            return api.Ledger().reserve(MODEL, 20, 10)
        except api.BudgetExceeded:
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        accepted = list(executor.map(reserve, range(20)))
    assert sum(value is not None for value in accepted) == 3
    assert sum(row["accounted_tokens"] for row in rows()) == 90


def test_quota_preflight_prevents_http(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 100, "large": 100})
    with pytest.raises(api.BudgetExceeded):
        api.generate_json(MODEL, PROMPT, "system")
    assert rows() == []


@pytest.mark.parametrize("model", ["gpt-5.4", "gpt-5.4-pro", "text-embedding-3-small", "other"])
def test_allowlist_rejection_before_any_work(model):
    with pytest.raises(api.OpenAIError, match="allowlisted"):
        api.generate_json(model, PROMPT, "system")
    assert not config.OPENAI_LEDGER_PATH.exists()


@pytest.mark.parametrize("prompt", [
    "No papers", "[P1] a\n[P1] b",
    "\n".join(f"[P{i}] paper" for i in range(1, 12)),
])
def test_batch_validation_before_http(prompt):
    with pytest.raises(api.OpenAIError, match="1-10"):
        api.generate_json(MODEL, prompt, "system")


def test_unknown_failure_reserves_before_http_and_keeps_all_tokens(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_MAX_ATTEMPTS", 1)

    def timeout(url, **kwargs):
        assert rows()[0]["status"] == "reserved"
        raise httpx.ReadTimeout("fake-test-key must never appear in raised exception")

    monkeypatch.setattr(api.httpx, "post", timeout)
    with pytest.raises(api.OpenAIError, match="transport failed") as error:
        api.generate_json(MODEL, PROMPT, "system")
    assert "fake-test-key" not in str(error.value)
    row = rows()[0]
    assert row["status"] == "unknown_transport"
    assert row["accounted_tokens"] == row["reserved_input"] + row["reserved_output"]
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": row["accounted_tokens"], "large": 1})
    with pytest.raises(api.BudgetExceeded):
        api.generate_json(MODEL, PROMPT, "system")
    assert len(rows()) == 1


def test_retry_after_and_each_http_attempt_accounted(monkeypatch):
    waits = []
    monkeypatch.setattr(api.time, "sleep", waits.append)
    calls = transport(monkeypatch, [
        response(status=429, headers={"retry-after": "3"}), response(),
    ])
    _, usage = api.generate_json(MODEL, PROMPT, "system")
    attempts = rows()
    assert waits == [3] and len(calls) == 2
    assert len({a["request_id"] for a in attempts}) == 2
    assert attempts[0]["status"] == "http_429"
    assert attempts[0]["accounted_tokens"] == attempts[0]["reserved_input"] + 2048
    assert attempts[1]["accounted_tokens"] == 105
    assert usage["attempts"] == 2 and usage["ledger_attempts"] == attempts
    assert usage["input_tokens"] == 80 and usage["output_tokens"] == 25
    assert usage["thinking_tokens"] == 5
    assert usage["unknown_reserved_tokens"] == attempts[0]["accounted_tokens"]
    assert usage["accounted_tokens"] == sum(a["accounted_tokens"] for a in attempts)


def test_http_retry_limit(monkeypatch):
    calls = transport(monkeypatch, [response(status=503) for _ in range(3)])
    with pytest.raises(api.OpenAIError, match="HTTP 503"):
        api.generate_json(MODEL, PROMPT, "system")
    assert len(calls) == len(rows()) == 3
    assert all(r["accounted_tokens"] == r["reserved_input"] + r["reserved_output"] for r in rows())


@pytest.mark.parametrize("status", [301, 400, 401, 403, 404])
def test_permanent_error_never_retries_or_redirects(monkeypatch, status):
    calls = transport(monkeypatch, [response(status=status)])
    with pytest.raises(api.OpenAIError, match=f"HTTP {status}"):
        api.generate_json(MODEL, PROMPT, "system")
    assert len(calls) == len(rows()) == 1


@pytest.mark.parametrize("retry_after", ["9999", "NaN", "invalid-date"])
def test_unbounded_or_invalid_retry_after_fails_closed(monkeypatch, retry_after):
    calls = transport(monkeypatch, [response(status=429, headers={"retry-after": retry_after})])
    with pytest.raises(api.OpenAIError, match="Retry-After"):
        api.generate_json(MODEL, PROMPT, "system")
    assert len(calls) == 1 and rows()[0]["status"] == "http_429"


@pytest.mark.parametrize("usage", [
    None, {}, {"input_tokens": True, "output_tokens": 1},
    {"input_tokens": 1, "output_tokens": -1},
    {"input_tokens": 1, "output_tokens": 1, "output_tokens_details": {"reasoning_tokens": 2}},
    {"input_tokens": 1, "output_tokens": 1, "total_tokens": 3},
    {"input_tokens": 1, "output_tokens": 1, "total_tokens": True},
])
def test_untrustworthy_usage_keeps_reservation(monkeypatch, usage):
    transport(monkeypatch, [response(body(usage=usage))])
    with pytest.raises(api.OpenAIError, match="usage"):
        api.generate_json(MODEL, PROMPT, "system")
    row = rows()[0]
    assert row["status"] == "unknown_usage" and row["input_tokens"] is None
    assert row["accounted_tokens"] == row["reserved_input"] + 2048


@pytest.mark.parametrize("data,status", [
    (body(status="incomplete"), "incomplete"),
    (body(output=[{"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}]), "refused"),
    (body(output=[]), "invalid_answer"),
])
def test_incomplete_refused_or_missing_output_explicit_actual_usage(monkeypatch, data, status):
    transport(monkeypatch, [response(data)])
    with pytest.raises(api.OpenAIError, match=status):
        api.generate_json(MODEL, PROMPT, "system")
    assert rows()[0]["status"] == status and rows()[0]["accounted_tokens"] == 105


@pytest.mark.parametrize("answer", [
    "not-json",
    {"grades": [{"paper": "P2", "reason": "r", "grade": 1}]},
    {"grades": [{"paper": "P1", "reason": "r", "grade": 3}]},
    {"grades": [{"paper": "P1", "reason": "r", "grade": "1"}]},
    {"grades": [{"paper": "P1", "reason": "r", "grade": True}]},
    {"grades": [{"paper": "P1", "grade": 1}]},
    {"grades": [{"paper": "P1", "reason": "r", "grade": 1, "extra": 1}]},
    {"grades": []},
    {"grades": [{"paper": "P1", "reason": "r", "grade": 1}] * 2},
])
def test_strict_answer_rejection_records_actual_usage(monkeypatch, answer):
    data = body()
    data["output"][0]["content"][0]["text"] = answer if isinstance(answer, str) else json.dumps(answer)
    transport(monkeypatch, [response(data)])
    with pytest.raises(api.OpenAIError, match="invalid_answer"):
        api.generate_json(MODEL, PROMPT, "system")
    assert rows()[0]["status"] == "invalid_answer" and rows()[0]["accounted_tokens"] == 105


def test_missing_key_and_dotenv_path(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    paths = []
    monkeypatch.setattr(api, "load_dotenv", paths.append)
    with pytest.raises(api.OpenAIError, match="OPENAI_API_KEY"):
        api.generate_json(MODEL, PROMPT, "system")
    assert paths == [config.PROJECT_ROOT / ".env"]
    assert not config.OPENAI_LEDGER_PATH.exists()


def test_reconciliation_can_exceed_reservation_but_stops_future_calls(monkeypatch):
    api.Ledger().reserve(MODEL, 1, 1)
    request_id = api.Ledger().reserve(MODEL, 10, 10)
    finished = api.Ledger().finish(request_id, "completed", 0.1,
                                   {"input_tokens": 2_000_000, "output_tokens": 1, "reasoning_tokens": 0})
    assert finished["accounted_tokens"] == 2_000_001
    with pytest.raises(api.BudgetExceeded):
        api.generate_json(MODEL, PROMPT, "system")
    with pytest.raises(api.OpenAIError, match="finalized"):
        api.Ledger().finish(request_id, "completed", 0.1)


def test_human_selection_intersects_sheet_mapping_without_grades_or_notes(tmp_path, monkeypatch):
    path = tmp_path / "human_pairs.json"
    path.write_text(json.dumps([
        {"row": 1, "query_id": "q1", "arxiv_id": "p1"},
        {"row": 2, "query_id": "q1", "arxiv_id": "p2"},
        {"row": 3, "query_id": "q2", "arxiv_id": "p3"},
    ]))
    monkeypatch.setattr(judge_pilot, "PAIRS_PATH", path)
    monkeypatch.setattr(judge_pilot, "read_human_grades",
                        lambda: {("q1", "p1"): 0, ("q2", "p3"): 2, ("outside", "p4"): 1})
    assert judge.human_pairs() == {"q1": ["p1"], "q2": ["p3"]}


@pytest.mark.parametrize("key", ["openai-nano", "openai-mini"])
def test_openai_batches_cache_dedup_and_blind_prompt(monkeypatch, key):
    papers = {f"p{i}": {"arxiv_id": f"p{i}", "title": f"Title {i}",
                        "abstract": f"Abstract {i}", "authors": ["Author"]} for i in range(25)}
    queries = {"q1": {"query_id": "q1", "query": "search", "human_grade": 0, "notes": "HUMAN NOTES"}}
    pairs = {"q1": list(papers)}
    calls = []

    def post(url, **kwargs):
        payload = json.loads(kwargs["content"])
        calls.append(payload)
        labels = payload["text"]["format"]["schema"]["$defs"]["_PaperGrade"]["properties"]["paper"]["enum"]
        answer = {"grades": [{"paper": label, "reason": "matches", "grade": 1} for label in labels]}
        data = body()
        data["output"][0]["content"][0]["text"] = json.dumps(answer)
        return response(data)

    monkeypatch.setattr(api.httpx, "post", post)
    monkeypatch.setattr(config, "OPENAI_JUDGE_MAX_PAPERS_PER_CALL", 100)
    assert judge.judge_pairs(key, pairs, queries, papers, max_calls=1) == {
        "cached": 0, "judged": 10, "calls": 1}
    assert judge.judge_pairs(key, pairs, queries, papers) == {
        "cached": 10, "judged": 15, "calls": 2}
    assert judge.judge_pairs(key, pairs, queries, papers) == {
        "cached": 25, "judged": 0, "calls": 0}
    cached = list(judge.load_judgments(key).values())
    assert sorted({row["batch_size"] for row in cached}) == [5, 10]
    assert len({row["usage"]["request_id"] for row in cached}) == 3
    assert sum(u["accounted_tokens"] for u in {
        row["usage"]["request_id"]: row["usage"] for row in cached}.values()) == 315
    for call in calls:
        assert "human_grade" not in call["input"] and "HUMAN NOTES" not in call["input"]
        assert "arxiv_id" not in call["input"]
        assert call["instructions"] == judge.judge_prompts.SYSTEM_INSTRUCTION
        assert judge.judge_prompts.RUBRIC in call["input"]
        assert call["model"] == config.JUDGES[key]["model"]


def test_cli_restricts_openai_to_human(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["judge", "--judge", "openai-nano", "--queries", "dev"])
    with pytest.raises(SystemExit) as error:
        judge.main()
    assert error.value.code == 2


def test_cli_human_passes_only_selected_pairs(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["judge", "--judge", "openai-mini", "--queries", "human"])
    monkeypatch.setattr(judge, "load_inputs", lambda: ({}, {}, {}))
    monkeypatch.setattr(judge, "human_pairs", lambda: {"q1": ["p1"]})
    received = []

    def run(key, pairs, queries, papers, **kwargs):
        received.append((key, pairs))
        return {"cached": 1, "judged": 0, "calls": 0}

    monkeypatch.setattr(judge, "judge_pairs", run)
    judge.main()
    assert received == [("openai-mini", {"q1": ["p1"]})]


def test_human_selection_rejects_more_than_100_sheet_rows(tmp_path, monkeypatch):
    path = tmp_path / "human_pairs.json"
    path.write_text(json.dumps([{"row": i, "query_id": "q1", "arxiv_id": f"p{i}"}
                                for i in range(101)]))
    monkeypatch.setattr(judge_pilot, "PAIRS_PATH", path)
    monkeypatch.setattr(judge_pilot, "read_human_grades", lambda: {})
    with pytest.raises(ValueError, match="100-pair"):
        judge.human_pairs()
