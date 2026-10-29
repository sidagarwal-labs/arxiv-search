from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
from google.genai import errors

from arxiv_search import config, llm
from arxiv_search.evaluate.judge import Grades


def test_client_has_timeout_and_no_nested_retries(monkeypatch):
    options = {}
    monkeypatch.setattr(llm, "_client", None)
    monkeypatch.setattr(llm.genai, "Client", lambda **kwargs: options.update(kwargs) or options)
    llm.client()
    assert options["http_options"].timeout == config.LLM_REQUEST_TIMEOUT_SECONDS * 1000
    assert options["http_options"].retry_options.attempts == 1


def test_retry_delay_honors_provider_and_adds_jitter(monkeypatch):
    monkeypatch.setattr(llm.random, "uniform", lambda a, b: 3)
    error = errors.APIError(429, {"error": {"message": "busy", "retryDelay": "17s"}})
    assert llm._retry_delay(error, 0) == 18
    assert llm._retry_delay(errors.APIError(503, {"error": {"message": "busy"}}), 0) == 13


def test_retry_transient_error_but_stop_on_daily_quota(monkeypatch):
    sleeps = []
    monkeypatch.setattr(llm, "_wait_for_pacing", lambda: None)
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    response = SimpleNamespace(parsed=Grades(grades=[]), usage_metadata=SimpleNamespace(
        prompt_token_count=1, candidates_token_count=2, thoughts_token_count=0))
    answers = [errors.APIError(502, {"error": {"message": "busy"}}), response]

    def generate(**kwargs):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate)))
    usage = llm.generate_json("gemma", "prompt", Grades)[1]
    assert usage["attempts"] == 2
    assert [a["code"] for a in usage["attempt_log"]] == [502, 200]
    assert usage["retry_wait_seconds"] == pytest.approx(sum(sleeps), abs=0.001)
    assert len(sleeps) == 1
    answers.append(errors.APIError(429, {"error": {"message": "PerDay quota"}}))
    with pytest.raises(llm.DailyLimitReached):
        llm.generate_json("gemma", "prompt", Grades)
    assert len(sleeps) == 1


@pytest.mark.parametrize("header, expected", [
    ("42.5", 43.5), ("invalid", 10), ("NaN", 10), ("-1", 10),
])
def test_retry_after_seconds_and_invalid_headers(monkeypatch, header, expected):
    monkeypatch.setattr(llm.random, "uniform", lambda *args: 0)
    error = errors.APIError(503, {"error": {"message": "busy"}},
                            httpx.Response(503, headers={"Retry-After": header}))
    assert llm._retry_delay(error, 0) == expected


def test_retry_after_http_date(monkeypatch):
    monkeypatch.setattr(llm.random, "uniform", lambda *args: 0)
    date = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=60), usegmt=True)
    error = errors.APIError(503, {}, httpx.Response(503, headers={"Retry-After": date}))
    assert 59 <= llm._retry_delay(error, 0) <= 61


def test_fractional_retry_info_and_backoff_floor(monkeypatch):
    monkeypatch.setattr(llm.random, "uniform", lambda *args: 0)
    error = errors.APIError(429, {"error": {"details": [
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "17.75s"}]}})
    assert llm._retry_delay(error, 0) == 18.75
    assert llm._retry_delay(error, 3) == 80


@pytest.mark.parametrize("code,message,expected", [
    (400, "bad request", errors.APIError),
    (403, "forbidden", errors.APIError),
    (429, "requests_per_day exceeded", llm.DailyLimitReached),
    (429, "Daily quota", llm.DailyLimitReached),
])
def test_permanent_and_daily_errors_do_not_retry(monkeypatch, code, message, expected):
    monkeypatch.setattr(llm, "_wait_for_pacing", lambda: None)
    sleeps = []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    def generate(**kwargs):
        raise errors.APIError(code, {"error": {"message": message}})
    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate)))
    with pytest.raises(expected):
        llm.generate_json("gemma", "prompt", Grades)
    assert sleeps == []


def test_exhaustion_remains_bounded_and_logs_no_prompt(monkeypatch, capsys):
    monkeypatch.setattr(llm, "_wait_for_pacing", lambda: None)
    monkeypatch.setattr(config, "LLM_MAX_RETRIES", 1)
    monkeypatch.setattr(llm.time, "sleep", lambda delay: None)
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        raise errors.APIError(500, {"error": {"message": "internal"}})
    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate)))
    with pytest.raises(errors.APIError):
        llm.generate_json("gemma", "PRIVATE_PROMPT_CONTENT", Grades)
    assert len(calls) == 2
    output = capsys.readouterr().out
    assert "HTTP 500" in output and "prompt_chars=22" in output
    assert "PRIVATE_PROMPT_CONTENT" not in output
