import numpy as np
import pytest

from arxiv_search.evaluate import embedding_pilot as ep


def test_subset_keeps_sources_and_is_deterministic():
    papers = {str(i): {} for i in range(10)}
    queries = {"q1": {"source_arxiv_id": "1"}, "q2": {"source_arxiv_id": "2"}}
    ids = ep.select_ids(papers, queries, list(queries), size=5)
    assert len(ids) == 5 and {"1", "2"} <= set(ids)
    assert ids == ep.select_ids(dict(reversed(list(papers.items()))), queries, list(queries), size=5)
    with pytest.raises(ValueError):
        ep.select_ids(papers, queries, list(queries), size=1)


def test_paid_reservations_persist_and_unknown_failures_consume_cap(tmp_path, monkeypatch):
    path = tmp_path / "ledger.db"
    monkeypatch.setattr(ep, "BUDGET_NANODOLLARS", 400)
    request = ep.reserve("text-embedding-3-small", 10, path)
    ep.reserve("text-embedding-3-small", 10, path)
    with pytest.raises(RuntimeError, match="cap reached"):
        ep.reserve("text-embedding-3-small", 1, path)
    ep.settle(request, "text-embedding-3-small", 5, 1.5, path)
    ep.reserve("text-embedding-3-small", 5, path)
    summary = ep.spending_summary(path)["text-embedding-3-small"]
    assert summary["accounted_usd"] == 400 / 1e9
    assert summary["complete_requests"] == 1


def test_paid_vectors_validate_cache_and_response(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "CACHE", tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setattr(ep, "reserve", lambda model, count: "request")
    settled = []
    monkeypatch.setattr(ep, "settle", lambda *args: settled.append(args))
    monkeypatch.setitem(ep.MODELS, "test-model", {"dimensions": 2, "nanodollars_per_token": 1})
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"usage": {"total_tokens": 2}, "data": [
                {"index": 1, "embedding": [0, 3]}, {"index": 0, "embedding": [4, 0]}]}

    def post(*args, **kwargs):
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr(ep.requests, "post", post)
    actual = ep.paid_vectors("test-model", ["a", "b"], [1, 1], "papers")
    assert np.array_equal(actual, [[1, 0], [0, 1]])
    assert len(settled) == 1
    assert np.array_equal(ep.paid_vectors("test-model", ["a", "b"], [1, 1], "papers"), actual)
    assert len(calls) == 1


def test_subset_evaluation_uses_source_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "OUT", tmp_path)
    queries = {"q": {"source_arxiv_id": "p1", "query_type": "keyword"}}
    ep.evaluate("test", np.eye(2), ["p0", "p1"], np.array([[0, 1]]), ["q"], queries, 1)
    assert "| test | 2 | 2 | 1.000" in ep.report_table()
