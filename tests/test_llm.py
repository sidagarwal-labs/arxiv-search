from types import SimpleNamespace

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
    assert llm.generate_json("gemma", "prompt", Grades)[1]["attempts"] == 2
    assert len(sleeps) == 1
    answers.append(errors.APIError(429, {"error": {"message": "PerDay quota"}}))
    with pytest.raises(llm.DailyLimitReached):
        llm.generate_json("gemma", "prompt", Grades)
    assert len(sleeps) == 1
