import contextvars
from dataclasses import dataclass, field

import pytest

from arxiv_search.serving import tracing
from arxiv_search.serving.http import Application
from arxiv_search.serving.service import APIError, SearchService
from tests.test_serving import FakeEmbedder, FakeReranker, release, release_dir, request  # noqa: F401
from tests.test_serving_paper_live import VISITOR, live  # noqa: F401


@dataclass
class Run:
    name: str
    run_type: str
    inputs: dict
    metadata: dict
    parent: "Run | None"
    outputs: dict = field(default_factory=dict)
    error: str | None = None

    def end(self, *, outputs=None, **_):
        self.outputs = outputs or {}


class FakeLangSmith:
    def __init__(self, fail=False):
        self.runs, self.fail = [], fail
        self.stack = contextvars.ContextVar("stack", default=())

    def trace(self, name, *, run_type, inputs, metadata, tags, client):
        if self.fail:
            raise RuntimeError("LangSmith is down")
        sdk = self

        class Manager:
            def __enter__(self):
                stack = sdk.stack.get()
                self.run = Run(name, run_type, inputs, metadata, stack[-1] if stack else None)
                sdk.runs.append(self.run)
                self.token = sdk.stack.set(stack + (self.run,))
                return self.run

            def __exit__(self, kind, error, _):
                sdk.stack.reset(self.token)
                self.run.error = repr(error) if error else None

        return Manager()

    def named(self, name):
        return [run for run in self.runs if run.name == name]


class Client:
    def __init__(self):
        self.flushes = 0

    def flush(self, timeout):
        assert timeout == tracing.FLUSH_TIMEOUT
        self.flushes += 1


@pytest.fixture
def sdk():
    fake, client = FakeLangSmith(), Client()
    tracing.configure(fake, client)
    yield fake, client
    tracing.configure()


class SpanReranker(FakeReranker):
    def scores(self, query, papers, *, pass_index, cache_key):
        with tracing.span("score-pass", "llm", inputs={"pass": pass_index}):
            return super().scores(query, papers, pass_index=pass_index, cache_key=cache_key)


def test_search_request_is_one_trace_with_nested_stages_and_one_flush(release, sdk):
    fake, client = sdk
    app = Application(lambda: SearchService(release, FakeEmbedder(release), SpanReranker()))
    response = request(app, "POST", "/api/search", {"query": "retrieval", "k": 5})
    assert response["status"] == 200
    root, = fake.named("search")
    assert root.parent is None and root.inputs == {"query": "retrieval", "k": 5}
    assert root.outputs["meta"]["stage"] == "reranked" and len(root.outputs["results"]) == 5
    assert "abstract" not in str(root.outputs)
    assert "visitor" not in root.metadata and root.metadata["vercel_env"] == "local"
    retrieve, = fake.named("retrieve")
    rerank, = fake.named("rerank")
    assert retrieve.parent is root and rerank.parent is root
    passes = fake.named("score-pass")
    # Reranking passes run on worker threads but still nest under the rerank span.
    assert len(passes) == 2 and all(run.parent is rerank for run in passes)
    assert client.flushes == 1


def test_meta_is_not_traced_and_errors_are_recorded(release, sdk):
    fake, client = sdk
    app = Application(lambda: SearchService(release, FakeEmbedder(release)))
    assert request(app, "GET", "/api/meta")["status"] == 200
    assert not fake.runs and client.flushes == 0
    response = request(app, "POST", "/api/summary", {"query": "q", "arxiv_ids": [release.papers[0]["arxiv_id"]]})
    assert response["status"] == 503
    root, = fake.named("summary")
    assert "disabled" in root.error and client.flushes == 1


def test_tracing_failures_never_change_responses(release):
    tracing.configure(FakeLangSmith(fail=True), Client())
    try:
        app = Application(lambda: SearchService(release, FakeEmbedder(release), SpanReranker()))
        traced = request(app, "POST", "/api/search", {"query": "retrieval"})
    finally:
        tracing.configure()
    plain = request(Application(lambda: SearchService(release, FakeEmbedder(release), FakeReranker())),
                    "POST", "/api/search", {"query": "retrieval"})
    assert traced["status"] == 200
    assert [r["arxiv_id"] for r in traced["body"]["results"]] == [
        r["arxiv_id"] for r in plain["body"]["results"]]


def test_disabled_without_key_or_flag(monkeypatch):
    tracing.configure()
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    assert not tracing.enabled()
    with tracing.span("x") as run:
        assert isinstance(run, tracing.NullRun)
    monkeypatch.setenv("LANGSMITH_API_KEY", "key")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    assert not tracing.enabled()
    tracing.configure()


def test_paper_ask_records_paper_load_and_model_usage(live, sdk):  # noqa: F811
    fake, _ = sdk
    service, budget, transport, _ = live
    service.ask({"arxiv_id": "2510.12345", "question": "What method?", "history": []},
                visitor=VISITOR)
    load, = fake.named("load-paper")
    assert load.outputs["cached"] is False and load.outputs["source"] == "abstract"
    answer, = fake.named("paper-answer")
    assert answer.run_type == "llm" and answer.inputs["question"] == "What method?"
    assert answer.metadata["ls_model_name"] == "gpt-6-luna" and answer.metadata["reserved_usd"] > 0
    assert "[abstract]" in answer.outputs["output"]
    service.ask({"arxiv_id": "2510.12345", "question": "Again?", "history": []}, visitor=VISITOR)
    assert fake.named("load-paper")[1].outputs["cached"] is True


def test_usage_and_text_helpers():
    reply = {"usage": {"input_tokens": 10, "output_tokens": 3}, "output": [
        {"content": [{"type": "output_text", "text": "draft"}]},
        {"content": [{"type": "output_text", "text": "final"}]}]}
    assert tracing.usage(reply) == {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}
    assert tracing.usage({"usage": {"prompt_tokens": 7}}, embedding=True)["total_tokens"] == 7
    assert tracing.usage({}) is None and tracing.response_text(reply) == "final"
    assert tracing.clip("x" * 5, 3) == "xxx… [2 more characters]"


def test_provider_calls_are_llm_spans_with_reservation_usage_and_output(sdk):
    from tests.test_serving_provider import (
        Budget, Counter, Transport, embedding_payload, model_reply,
    )
    from arxiv_search import answer
    from arxiv_search.serving.provider import ANSWER_MODEL, BudgetedProvider, OpenAISummarizer
    fake, _ = sdk
    budget = Budget()
    transport = Transport(budget)
    provider = BudgetedProvider(transport, budget, Counter())
    provider.call("embeddings", embedding_payload(), embedding=True)
    papers = tuple({"arxiv_id": f"2510.{i:05d}", "title": f"Paper {i}", "authors": ["A"],
                    "abstract": "An abstract.", "submitted_month": "2026-10"} for i in range(3))
    transport.response = model_reply({"grounded": True, "answer": "A claim [1]."}, ANSWER_MODEL)
    OpenAISummarizer(provider, model=ANSWER_MODEL, prompt_version=answer.VERSION_V2).summarize(
        "question", papers, cache_key="key")
    embed, answer_run = fake.named("embed-query")[0], fake.named("answer")[0]
    assert embed.run_type == "embedding" and embed.inputs["input"] == "test"
    assert embed.outputs["usage_metadata"]["input_tokens"] == 10
    assert answer_run.run_type == "llm" and answer_run.metadata["ls_model_name"] == ANSWER_MODEL
    assert "A claim [1]." in answer_run.outputs["output"]
    assert answer_run.metadata["reserved_tokens"] == budget.calls[1][1]["tokens"]
