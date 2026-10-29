import concurrent.futures
import json

import httpx
import numpy as np
import pytest

from arxiv_search.evaluate import openai_full as full
from arxiv_search.evaluate import experiments as ex
from arxiv_search.search.dense import DenseIndex
from arxiv_search.search.hybrid import fuse


def test_persistent_transactional_lifetime_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(full, "CAP", 1300)
    path = tmp_path / "ledger.sqlite3"
    ledger = full.Ledger(path)

    def reserve():
        try:
            return full.Ledger(path).reserve(6)
        except full.BudgetExceeded:
            return None

    with concurrent.futures.ThreadPoolExecutor(2) as executor:
        reservations = list(executor.map(lambda _: reserve(), range(2)))
    assert sum(r is not None for r in reservations) == 1
    ledger.settle(next(r for r in reservations if r), 2, 0.1)
    full.Ledger(path).reserve(8)
    with pytest.raises(full.BudgetExceeded):
        ledger.reserve(1)
    with pytest.raises(full.EmbeddingError):
        ledger.settle(next(r for r in reservations if r), 0, 0)


def test_unknown_failure_no_paid_retry(tmp_path, monkeypatch):
    ledger = full.Ledger(tmp_path / "ledger.sqlite3")
    calls = []

    def post(self, url, **kwargs):
        calls.append(url)
        raise httpx.ReadTimeout("private provider details")

    monkeypatch.setattr(httpx.Client, "post", post)
    with pytest.raises(full.EmbeddingError, match="no retry"):
        full.request_vectors(["a"], [1], ledger, "not-a-real-key")
    assert calls == [full.ENDPOINT]
    assert ledger.summary()["requests"] == 1
    assert ledger.summary()["accounted_usd"] == 9 * full.PRICE / 1e9


def test_http_failure_never_redirects_or_retries(tmp_path, monkeypatch):
    calls = []

    def post(self, url, **kwargs):
        assert self.follow_redirects is False
        assert kwargs["json"]["model"] == full.MODEL
        calls.append(url)
        return httpx.Response(302, headers={"location": "https://unapproved.invalid"})

    monkeypatch.setattr(httpx.Client, "post", post)
    with pytest.raises(full.EmbeddingError, match="HTTP failure"):
        full.request_vectors(["a"], [1], full.Ledger(tmp_path / "ledger.db"), "fake")
    assert calls == [full.ENDPOINT]


def test_exhausted_budget_prevents_http(tmp_path, monkeypatch):
    monkeypatch.setattr(full, "CAP", 8 * full.PRICE)
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: pytest.fail("Paid call forbidden"))
    ledger = full.Ledger(tmp_path / "ledger.db")
    with pytest.raises(full.BudgetExceeded):
        full.request_vectors(["a"], [1], ledger, "fake")
    assert ledger.summary()["requests"] == 0


def test_valid_response_sorts_indices_and_settles_usage(tmp_path, monkeypatch):
    monkeypatch.setattr(full, "DIMENSIONS", 2)
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: httpx.Response(200, json={
        "usage": {"total_tokens": 2, "prompt_tokens": 2},
        "data": [{"index": 1, "embedding": [0, 3]}, {"index": 0, "embedding": [4, 0]}]}))
    ledger = full.Ledger(tmp_path / "ledger.db")
    actual = full.request_vectors(["a", "b"], [1, 1], ledger, "fake")
    assert actual.dtype == np.float32
    assert np.array_equal(actual, np.eye(2))
    assert ledger.summary()["accounted_usd"] == 2 * full.PRICE / 1e9


@pytest.mark.parametrize("usage", [
    {"total_tokens": True, "prompt_tokens": 1},
    {"total_tokens": 1, "prompt_tokens": True},
    {"total_tokens": 0, "prompt_tokens": 0},
    {"total_tokens": 1, "prompt_tokens": 2},
])
def test_bad_usage_retains_full_reservation(tmp_path, monkeypatch, usage):
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: httpx.Response(
        200, json={"usage": usage, "data": []}))
    ledger = full.Ledger(tmp_path / "ledger.db")
    with pytest.raises(full.EmbeddingError, match="usage"):
        full.request_vectors(["a"], [1], ledger, "fake")
    assert ledger.summary()["accounted_usd"] == 9 * full.PRICE / 1e9


@pytest.mark.parametrize("data", [
    [{"index": 0, "embedding": [1, 0]}, {"index": 0, "embedding": [0, 1]}],
    [{"index": 0, "embedding": [float("nan"), 0]}, {"index": 1, "embedding": [0, 1]}],
    [{"index": 0, "embedding": [0, 0]}, {"index": 1, "embedding": [0, 1]}],
    [{"index": 0, "embedding": [1]}, {"index": 1, "embedding": [0, 1]}],
])
def test_invalid_response_indices_shape_finite(tmp_path, monkeypatch, data):
    monkeypatch.setattr(full, "DIMENSIONS", 2)
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: httpx.Response(
        200, json={"usage": {"total_tokens": 2, "prompt_tokens": 2}, "data": data}))
    with pytest.raises(full.EmbeddingError):
        full.request_vectors(["a", "b"], [1, 1], full.Ledger(tmp_path / "l.db"), "fake")


def test_cache_content_invalidation_and_corruption(tmp_path, monkeypatch):
    monkeypatch.setattr(full, "DIMENSIONS", 2)
    vectors = np.eye(2, dtype=np.float32)
    full.write_cache(["a", "b"], vectors, tmp_path)
    assert np.array_equal(full.read_cache(["a", "b"], tmp_path), vectors)
    assert full.read_cache(["changed", "b"], tmp_path) is None
    path = tmp_path / f"{full.fingerprint(['a', 'b'])}.npy"
    path.write_bytes(b"corruption")
    with pytest.raises(full.EmbeddingError, match="Corrupt"):
        full.read_cache(["a", "b"], tmp_path)
    monkeypatch.setattr(full, "request_vectors", lambda *a: pytest.fail("Paid repair forbidden"))
    with pytest.raises(full.EmbeddingError, match="Corrupt"):
        full.embed(["a", "b"], [1, 1], {}, tmp_path, None, "fake")


def test_resume_reuses_rows_and_normalizes(tmp_path, monkeypatch):
    monkeypatch.setattr(full, "DIMENSIONS", 2)
    calls = []

    def request(texts, counts, ledger, key):
        calls.append(texts)
        return np.array([[0, 3]], dtype=np.float32)

    monkeypatch.setattr(full, "request_vectors", request)
    reused = {"a": np.array([4, 0], dtype=np.float32)}
    assert full.planned_tokens(["a", "b"], [1, 2], reused, tmp_path) == (10, 1)
    actual = full.embed(["a", "b"], [1, 2], reused, tmp_path, None, "fake")
    assert actual.dtype == np.float32
    assert np.array_equal(actual, np.eye(2))
    assert np.array_equal(full.embed(["a", "b"], [1, 2], reused, tmp_path, None, ""), actual)
    assert calls == [["b"]]


def test_pilot_reuse_requires_exact_whole_text_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(full, "DIMENSIONS", 2)
    monkeypatch.setattr(full.config, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(full.config, "EMBEDDINGS_DIR", tmp_path / "embeddings")
    manifest = full.config.RESULTS_DIR / "embedding-pilot" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"ids": ["p"], "query_ids": ["q"]}))
    papers = {"p": {"title": "Title", "abstract": "Abstract"}}
    queries = {"q": {"query": "hello"}}
    for texts in (["Title Abstract"], ["hello"]):
        folder = full.config.EMBEDDINGS_DIR / "openai-pilot" / full.MODEL / full.fingerprint(texts)
        folder.mkdir(parents=True)
        np.save(folder / "0.npy", np.array([[3, 0]], dtype=np.float32))
    assert set(full.pilot_vectors(papers, queries, ["q"])) == {"Title Abstract", "hello"}
    papers["p"]["abstract"] = "Changed"
    assert set(full.pilot_vectors(papers, queries, ["q"])) == {"hello"}


def test_dense_and_live_hybrid_rankings(monkeypatch):
    monkeypatch.setattr(full.config, "RUN_DEPTH", 3)
    index = DenseIndex(np.array([[1, 0], [0, 1], [-1, 0]], dtype=np.float32), ["a", "b", "c"])
    lexical_calls = []

    def lexical(text):
        lexical_calls.append(text)
        return ["c", "a", "b"]

    semantic, hybrid, timing = full.ranked_runs(
        index, lexical, ["q"], ["term"], np.array([[1, 0]], dtype=np.float32))
    assert semantic == {"q": ["a", "b", "c"]}
    assert hybrid["q"] == fuse(["c", "a", "b"], semantic["q"], method="rrf",
                               semantic_weight=0.5, c=10, depth=3, k=3)
    assert lexical_calls == ["term"]
    assert timing["hybrid_ms"] >= 0 and timing["dense_ms"] >= 0


def test_preflight_margin_and_invalid_tokens():
    assert full.reservation_tokens([10000]) == 10100
    with pytest.raises(ValueError):
        full.token_counts([""])


def test_dry_run_never_embeds_test_queries_or_creates_ledger(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(full, "LEDGER", tmp_path / "new-ledger.db")
    monkeypatch.setattr(full, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(full, "pilot_vectors", lambda *args: {})
    monkeypatch.setattr(ex, "load_eval", lambda: (
        [{"arxiv_id": "p", "title": "Title", "abstract": "Abstract"}],
        {"dev": {"query": "dev query"}, "test": {"query": "test query must not embed"}},
        {}, {"dev": ["dev"], "test": ["test"]}))
    counts_seen = []

    def counts(texts):
        counts_seen.extend(texts)
        return [1 for _ in texts]

    monkeypatch.setattr(full, "token_counts", counts)
    monkeypatch.setattr("sys.argv", ["openai_full"])
    full.main()
    assert counts_seen == ["Title Abstract", "dev query"]
    assert not full.LEDGER.exists()
    assert not full.CACHE.exists()
    assert '"dev_queries": 1' in capsys.readouterr().out


def test_registration_is_metadata_only_and_explicit_about_offline_timing():
    registry = {}
    full.register_systems(registry, ex.System)
    assert set(registry) == {full.DENSE_NAME, full.HYBRID_NAME}
    for system in registry.values():
        assert "latency excludes API" in system.description
        assert system.factors["dimensions"] == 3072
        with pytest.raises(RuntimeError, match="dry preflight"):
            system.build([])
    assert registry[full.HYBRID_NAME].factors["semantic_weight"] == 0.5
    assert full.TIMING_SCOPE == "sequential_search_excludes_offline_query_embedding"
