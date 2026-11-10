import copy
from io import BytesIO
import json
from pathlib import Path

import numpy as np
import pytest

from arxiv_search.search.bm25 import BM25
from arxiv_search.search.hybrid import fuse_working_baseline
from arxiv_search.search.text import paper_text, tokenize
from arxiv_search.serving.http import Application, disabled_service
from arxiv_search.serving.lexical import write_index
from arxiv_search.serving.release import EmbeddingSpec, Release, sha256_file
from arxiv_search.serving.service import (
    APIError, Answer, DisabledEmbedder, LocalRetriever, SearchService, dense_scores,
)


@pytest.fixture(params=["float16", "float32"])
def release_dir(tmp_path, request):
    template = Path(__file__).resolve().parents[1] / "serving" / "release-v1.json"
    manifest = json.loads(template.read_text(encoding="utf-8"))
    manifest["embedding"]["dimensions"] = 3
    manifest["vector_storage"] = request.param
    papers = [{
        "arxiv_id": f"2510.{i:05d}", "title": f"Retrieval models {i}",
        "abstract": "Full abstract. " * 30 + ("keyword" if i % 2 else "semantic"),
        "authors": [f"Author {n}" for n in range(12)],
        "primary_category": "cs.IR", "categories": ["cs.IR"], "submitted_month": "2025-10",
    } for i in range(24)]
    (tmp_path / "corpus.jsonl").write_text(
        "".join(json.dumps(p) + "\n" for p in papers), encoding="utf-8",
    )
    rng = np.random.default_rng(42)
    vectors = rng.uniform(0.1, 1, (len(papers), 3)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    np.save(tmp_path / "vectors.npy", vectors.astype(request.param), allow_pickle=False)
    write_index(papers, manifest["retrieval"], tmp_path)
    manifest.update({
        "papers": len(papers), "categories": ["cs.IR"], "fields": "title+abstract",
        "from_month": "2025-10", "to_month": "2025-10", "corpus_note": "Test snapshot.",
        "sha256": {name: sha256_file(tmp_path / name)
                   for name in ("corpus.jsonl", "vectors.npy", "bm25.npz", "terms.json")},
    })
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


@pytest.fixture
def release(release_dir):
    return Release.load(release_dir)


class FakeEmbedder:
    def __init__(self, release):
        self.spec = release.embedding
        self.keys = []

    def embed(self, query, *, cache_key):
        self.keys.append(cache_key)
        return np.array([1, 0.3, 0.1], dtype=np.float32)


class FakeReranker:
    model = "gpt-5.4-mini-2026-03-17"
    prompt_version = "scores-v2"

    def __init__(self):
        self.calls = []

    def scores(self, query, papers, *, pass_index, cache_key):
        self.calls.append((pass_index, cache_key))
        return {p["arxiv_id"]: i % 5 for i, p in enumerate(papers)}


class FakeSummarizer:
    model = "test-summary-model"
    prompt_version = "test-summary-v1"
    answer = Answer("An answer [1, 2].", (1, 2), True)

    def summarize(self, query, papers, *, cache_key):
        return self.answer


def summary_release(release):
    manifest = copy.deepcopy(release.manifest)
    manifest["summary"] = {
        "model": FakeSummarizer.model, "prompt_version": FakeSummarizer.prompt_version,
    }
    return Release(manifest, "summary-release", release.papers, release.vectors,
                   release.embedding, release.directory)


def request(app, method, path, body=None, raw=None, **extra):
    if raw is None:
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
    environ = {
        "PATH_INFO": path, "REQUEST_METHOD": method, "CONTENT_TYPE": "application/json",
        "CONTENT_LENGTH": str(len(raw)), "wsgi.input": BytesIO(raw),
    } | extra
    response = {}

    def start_response(status, headers):
        response.update(status=int(status.split()[0]), headers=dict(headers))

    response["body"] = json.loads(b"".join(app(environ, start_response)))
    return response


def test_search_contract_and_disabled_summary(release):
    service = SearchService(release, FakeEmbedder(release))
    result = service.search({"query": " retrieval ", "k": 20})
    assert result["query"] == "retrieval"
    assert len(result["results"]) == 20
    assert [r["rank"] for r in result["results"]] == list(range(1, 21))
    assert result["meta"]["fallback"] is True
    assert result["meta"]["stage"] == "retrieval"
    first = result["results"][0]
    assert len(first["authors"]) == 10 and first["authors_truncated"]
    assert first["abstract"] == service.papers[first["arxiv_id"]]["abstract"]
    assert first["url"] == f"https://arxiv.org/abs/{first['arxiv_id']}"
    with pytest.raises(APIError, match="disabled"):
        service.summary({"query": "retrieval", "arxiv_ids": [first["arxiv_id"]]})


def test_retrieval_matches_existing_baseline(release):
    retriever = LocalRetriever(release)
    vector = FakeEmbedder(release).embed("keyword", cache_key="unused")
    vector /= np.linalg.norm(vector)
    ids = [p["arxiv_id"] for p in release.papers]
    independent = BM25(
        [tokenize(paper_text(p, authors=True, title_repeats=2), add_stems=True)
         for p in release.papers], ids, k1=0.8, b=0.75,
    )
    lexical = independent.scores(tokenize("keyword", add_stems=True))
    semantic = release.vectors.astype(np.float32) @ vector
    lex = {ids[i]: float(lexical[i]) for i in np.argsort(-lexical, kind="stable")
           if lexical[i] > 0}
    sem = {ids[i]: float(semantic[i]) for i in np.argsort(-semantic, kind="stable")}
    assert retriever.retrieve("keyword", vector, 20) == fuse_working_baseline(lex, sem, k=20)


def test_two_pass_reranking_keys_and_output(release):
    reranker = FakeReranker()
    result = SearchService(release, FakeEmbedder(release), reranker).search({"query": "retrieval"})
    assert len(result["results"]) == 10
    assert result["meta"]["stage"] == "reranked" and not result["meta"]["fallback"]
    assert sorted(p for p, _ in reranker.calls) == [0, 1]
    assert len({key for _, key in reranker.calls}) == 2


def refined_release(release):
    manifest = copy.deepcopy(release.manifest)
    current = json.loads((Path(__file__).resolve().parents[1]
                         / "serving" / "release-v2.json").read_text())
    manifest["refinement"] = current["refinement"]
    manifest["baseline"] = current["baseline"]
    manifest["summary"] = {
        "model": FakeSummarizer.model, "prompt_version": FakeSummarizer.prompt_version,
    }
    return Release(manifest, "refined-release", release.papers, release.vectors,
                   release.embedding, release.directory)


class FakeRefiner(FakeReranker):
    prompt_version = "refine20-v1"

    def scores(self, query, papers, *, pass_index, cache_key):
        self.calls.append((pass_index, cache_key))
        return {p["arxiv_id"]: i * 10 / (len(papers) - 1) for i, p in enumerate(papers)}


def test_refinement_matches_rrf_pin_rule_preserves_tail_and_runs_passes_in_parallel(release):
    from threading import Barrier
    pinned = refined_release(release)
    stage_barrier, refine_barrier = Barrier(2), Barrier(2)

    class ParallelReranker(FakeReranker):
        def scores(self, *args, **kwargs):
            stage_barrier.wait(timeout=5)
            return super().scores(*args, **kwargs)

    class ParallelRefiner(FakeRefiner):
        def scores(self, *args, **kwargs):
            refine_barrier.wait(timeout=5)
            return super().scores(*args, **kwargs)

    service = SearchService(
        pinned, FakeEmbedder(pinned), ParallelReranker(), refiner=ParallelRefiner(),
    )
    ids = list(service.papers)
    d46 = service._score_order("retrieval", ids, service.reranker, "reranking", 4)
    actual = service._score_order("retrieval", d46, service.refiner, "refinement", 10)
    llm_rank = {pid: i for i, pid in enumerate(reversed(d46[:20]), 1)}
    base_rank = {pid: i for i, pid in enumerate(d46[:20], 1)}
    expected = sorted(d46[:20], key=lambda pid: (
        -(1 / (30 + base_rank[pid]) + 1 / (30 + llm_rank[pid])), base_rank[pid],
    )) + d46[20:]
    assert actual == expected
    assert actual[20:] == d46[20:]
    result = service.search({"query": "retrieval", "k": 20})
    baseline = SearchService(pinned, FakeEmbedder(pinned), FakeReranker()).search(
        {"query": "retrieval", "k": 20})
    reference = [p["arxiv_id"] for p in baseline["results"]]
    ranked = service._score_order("retrieval", reference, service.refiner, "refinement", 10)
    assert [p["arxiv_id"] for p in result["results"]] == (
        [reference[0]] + [pid for pid in ranked if pid != reference[0]])
    assert result["meta"]["refined"] is True
    assert result["meta"]["stage"] == "reranked" and not result["meta"]["fallback"]


@pytest.mark.parametrize("code", ["rate_limited", "budget_exhausted", "upstream_unavailable"])
def test_refinement_failure_keeps_decision46_and_does_not_claim_refined(release, code):
    class Failed(FakeRefiner):
        def scores(self, *args, **kwargs):
            raise APIError(code, "Refinement failed")
    pinned = refined_release(release)
    baseline = SearchService(pinned, FakeEmbedder(pinned), FakeReranker()).search(
        {"query": "retrieval", "k": 20})
    result = SearchService(
        pinned, FakeEmbedder(pinned), FakeReranker(), refiner=Failed(),
    ).search({"query": "retrieval", "k": 20})
    assert result["results"] == baseline["results"]
    assert result["meta"]["stage"] == "reranked"
    assert result["meta"]["fallback"] is False and result["meta"]["refined"] is False
    assert "refinement unavailable" in result["meta"]["stage_detail"]


class MemoryTickets:
    def __init__(self):
        self.bindings = {}

    def issue_summary(self, binding):
        from uuid import uuid4
        token = uuid4().hex
        self.bindings[token] = binding
        return token

    def consume_summary(self, token, binding):
        if token not in self.bindings or self.bindings[token] != binding:
            raise APIError("bad_request", "Invalid answer ticket", 400)
        del self.bindings[token]


def test_answer_requires_search_ticket_bound_to_query_release_and_order(release):
    pinned = refined_release(release)
    tickets = MemoryTickets()
    service = SearchService(
        pinned, FakeEmbedder(pinned), FakeReranker(), FakeSummarizer(),
        refiner=FakeRefiner(), tickets=tickets,
    )
    app = Application(lambda: service)
    result = request(app, "POST", "/api/search", {"query": "retrieval", "k": 20})["body"]
    ids = [p["arxiv_id"] for p in result["results"][:10]]
    body = {"query": "retrieval", "arxiv_ids": ids, "search_token": result["search_token"]}
    assert request(app, "POST", "/api/summary", body | {"query": "different"})["status"] == 400
    assert request(app, "POST", "/api/summary", body | {"arxiv_ids": ids[::-1]})["status"] == 400
    assert request(app, "POST", "/api/summary", body | {"search_token": None})["status"] == 400
    response = request(app, "POST", "/api/summary", body)
    assert response["status"] == 200 and response["body"]["cited"] == [1, 2]
    assert request(app, "POST", "/api/summary", body)["status"] == 400


def test_ticket_store_failure_preserves_search_results(release):
    class FailedTickets(MemoryTickets):
        def issue_summary(self, binding):
            raise APIError("upstream_unavailable", "Redis unavailable")
    pinned = refined_release(release)
    result = SearchService(
        pinned, FakeEmbedder(pinned), FakeReranker(), FakeSummarizer(),
        tickets=FailedTickets(),
    ).search({"query": "retrieval"})
    assert len(result["results"]) == 10 and "search_token" not in result
    assert result["meta"]["summary_available"] is False
    assert result["meta"]["summary_unavailable_reason"] == "authorization_unavailable"

def test_safeguard_matches_frozen_formula_including_ties(release):
    class Reverse(FakeReranker):
        def scores(self, query, papers, *, pass_index, cache_key):
            return {p["arxiv_id"]: i * 4 / (len(papers) - 1) for i, p in enumerate(papers)}

    embedder = FakeEmbedder(release)
    baseline = LocalRetriever(release).retrieve(
        "retrieval", embedder.embed("retrieval", cache_key="unused"), 50,
    )
    llm_rank = {pid: i for i, pid in enumerate(reversed(baseline), 1)}
    base_rank = {pid: i for i, pid in enumerate(baseline, 1)}
    expected = sorted(baseline, key=lambda pid: (
        -(1 / (30 + base_rank[pid]) + 1 / (30 + llm_rank[pid])), base_rank[pid],
    ))
    result = SearchService(release, embedder, Reverse()).search({"query": "retrieval", "k": 20})
    assert [p["arxiv_id"] for p in result["results"]] == expected[:20]


@pytest.mark.parametrize("code", ["rate_limited", "budget_exhausted", "upstream_unavailable"])
def test_rerank_failure_retains_exact_retrieval_order(release, code):
    class FailedReranker(FakeReranker):
        def scores(self, *args, **kwargs):
            raise APIError(code, "Unavailable")

    plain = SearchService(release, FakeEmbedder(release)).search({"query": "retrieval"})
    fallback = SearchService(
        release, FakeEmbedder(release), FailedReranker(),
    ).search({"query": "retrieval"})
    assert fallback["results"] == plain["results"]
    assert fallback["meta"]["fallback"]


def test_invalid_reranker_scores_are_explicit_fallback(release, caplog):
    class Invalid(FakeReranker):
        def scores(self, *args, **kwargs):
            return {"unknown": float("nan")}

    result = SearchService(release, FakeEmbedder(release), Invalid()).search({"query": "x"})
    assert result["meta"]["fallback"]
    assert "upstream_unavailable" in caplog.text


@pytest.mark.parametrize("query", [None, "", " ", 3, "a" * 301])
def test_bad_queries(release, query):
    with pytest.raises(APIError) as error:
        SearchService(release, FakeEmbedder(release)).search({"query": query})
    assert error.value.code == "bad_request" and error.value.status == 400


@pytest.mark.parametrize("k", [0, 21, True, 1.0, "10", None])
def test_bad_k(release, k):
    with pytest.raises(APIError):
        SearchService(release, FakeEmbedder(release)).search({"query": "x", "k": k})


def test_embedding_identity_must_match_not_just_dimensions(release):
    embedder = FakeEmbedder(release)
    embedder.spec = EmbeddingSpec("different-provider", "different-model", 3, "title-abstract-v1")
    with pytest.raises(ValueError, match="incompatible"):
        SearchService(release, embedder)


@pytest.mark.parametrize("vector", [[1, 0], [0, 0, 0], [float("nan"), 1, 1]])
def test_bad_query_vectors(release, vector):
    with pytest.raises(ValueError, match="embedding"):
        LocalRetriever(release).retrieve("query", np.array(vector), 10)


def test_model_and_prompt_must_match_release(release):
    adapter = FakeReranker()
    adapter.prompt_version = "new-experiment"
    with pytest.raises(ValueError, match="pinned"):
        SearchService(release, FakeEmbedder(release), adapter)


def test_cache_namespace_changes_with_release_and_order(release):
    key = release.cache_key("summary", {"ids": ["a", "b"], "query": "x"})
    assert key != release.cache_key("summary", {"ids": ["b", "a"], "query": "x"})
    changed = Release(release.manifest, "new-fingerprint", release.papers,
                      release.vectors, release.embedding)
    assert key != changed.cache_key("summary", {"ids": ["a", "b"], "query": "x"})


def test_valid_summary_and_abstention(release):
    release = summary_release(release)
    adapter = FakeSummarizer()
    service = SearchService(release, FakeEmbedder(release), summarizer=adapter)
    body = {"query": "x", "arxiv_ids": [p["arxiv_id"] for p in release.papers[:2]]}
    assert service.summary(body)["cited"] == [1, 2]
    adapter.answer = Answer("No answer found in these abstracts.", (), False)
    assert service.summary(body)["grounded"] is False


def test_contract_b_abstention_can_link_closest_results(release):
    manifest = copy.deepcopy(release.manifest)
    manifest["summary"] = {"model": "gpt-6-luna", "prompt_version": "answer-v2"}
    pinned = Release(manifest, release.fingerprint, release.papers,
                     release.vectors, release.embedding, release.directory)
    adapter = FakeSummarizer()
    adapter.model, adapter.prompt_version = "gpt-6-luna", "answer-v2"
    adapter.answer = Answer("These do not answer the request; closest papers [2, 1].", (2, 1), False)
    service = SearchService(pinned, FakeEmbedder(pinned), summarizer=adapter)
    result = service.summary({"query": "x", "arxiv_ids": [p["arxiv_id"] for p in pinned.papers[:2]]})
    assert result["grounded"] is False and result["cited"] == [2, 1]


@pytest.mark.parametrize("answer", [
    Answer("Out of range [3].", (3,), True),
    Answer("Unlisted citation [2].", (1,), True),
    Answer("No citations.", (), True),
    Answer("No answer [1].", (1,), False),
])
def test_invalid_summary_citations(release, answer):
    release = summary_release(release)
    adapter = FakeSummarizer()
    adapter.answer = answer
    service = SearchService(release, FakeEmbedder(release), summarizer=adapter)
    with pytest.raises(ValueError, match="answer"):
        service.summary({"query": "x", "arxiv_ids": [p["arxiv_id"] for p in release.papers[:2]]})


@pytest.mark.parametrize("ids", [[], ["unknown"], ["2510.00000", "2510.00000"], [True], "id"])
def test_invalid_summary_ids(release, ids):
    with pytest.raises(APIError):
        SearchService(release, FakeEmbedder(release)).summary({"query": "x", "arxiv_ids": ids})


def test_release_corruption_and_dimension_mismatch(release_dir):
    path = release_dir / "manifest.json"
    data = json.loads(path.read_text())
    data["embedding"]["dimensions"] = 4
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="dimensions"):
        Release.load(release_dir)
    with (release_dir / "corpus.jsonl").open("a") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="checksum"):
        Release.load(release_dir)


def test_http_meta_disabled_search_and_retry_header(release):
    service = SearchService(release, DisabledEmbedder(release.embedding))
    app = Application(lambda: service)
    meta = request(app, "GET", "/api/meta")
    assert meta["status"] == 200 and meta["body"]["papers"] == 24
    disabled = request(app, "POST", "/api/search", {"query": "x"})
    assert disabled["status"] == 503
    assert disabled["body"]["error"]["code"] == "budget_exhausted"

    class Limited(FakeEmbedder):
        def embed(self, *args, **kwargs):
            raise APIError("rate_limited", "Wait.", 429, 17)

    app = Application(lambda: SearchService(release, Limited(release)))
    result = request(app, "POST", "/api/search", {"query": "x"})
    assert result["status"] == 429 and result["headers"]["Retry-After"] == "17"


@pytest.mark.parametrize("method,path,raw,extra,status", [
    ("GET", "/missing", b"", {}, 404),
    ("GET", "/api/search", b"", {}, 405),
    ("POST", "/api/search", b"[]", {}, 400),
    ("POST", "/api/search", b"{", {}, 400),
    ("POST", "/api/search", b'{"query":"x"}', {"CONTENT_TYPE": "text/plain"}, 415),
    ("POST", "/api/search", b"x", {"CONTENT_LENGTH": "20000"}, 413),
    ("POST", "/api/search", b"x", {"CONTENT_LENGTH": ""}, 411),
    ("POST", "/api/search", b"x", {"CONTENT_LENGTH": "10"}, 400),
])
def test_http_rejects_bad_requests_without_loading_release(method, path, raw, extra, status):
    def fail():
        pytest.fail("Invalid HTTP input must not load artifacts")

    result = request(Application(fail), method, path, raw=raw, **extra)
    assert result["status"] == status
    assert result["body"]["error"]["code"] == "bad_request"


def test_http_sanitizes_internal_errors(caplog):
    def fail():
        raise ValueError("private-internal-detail")

    result = request(Application(fail), "GET", "/api/meta")
    assert result["status"] == 500
    assert "private-internal-detail" not in json.dumps(result)
    assert "Unhandled serving failure" in caplog.text


def test_paid_environment_flag_cannot_enable_calls(monkeypatch):
    monkeypatch.setenv("ARXIV_ENABLE_PAID_CALLS", "1")
    with pytest.raises(RuntimeError, match="explicitly configured protected trial"):
        disabled_service()


@pytest.mark.parametrize("environment", ["production", "development", ""])
@pytest.mark.parametrize("activation", ["protected-trial-v1", "protected-trial-v2", "protected-trial-v3"])
def test_trial_flag_cannot_enable_calls_outside_vercel_preview(
    monkeypatch, release, environment, activation,
):
    monkeypatch.setenv("ARXIV_ENABLE_PAID_CALLS", activation)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", environment)
    monkeypatch.setattr(Release, "load", lambda directory: release)
    with pytest.raises(RuntimeError, match="restricted to Vercel Preview"):
        disabled_service()


def test_second_trial_requires_the_refinement_and_answer_release(monkeypatch, release):
    monkeypatch.setenv("ARXIV_ENABLE_PAID_CALLS", "protected-trial-v2")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setattr(Release, "load", lambda directory: release)
    with pytest.raises(RuntimeError, match="requires Decision 47 refinement and Decision 48 answers"):
        disabled_service()


def test_third_trial_rejects_non_d49_release_before_redis(monkeypatch, release):
    monkeypatch.setenv("ARXIV_ENABLE_PAID_CALLS", "protected-trial-v3")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setattr(Release, "load", lambda directory: release)
    with pytest.raises(RuntimeError, match="third trial requires"):
        disabled_service()


@pytest.mark.parametrize("storage", ["float16", "float32"])
@pytest.mark.parametrize("chunk_size", [1, 7, 256, 1000])
def test_chunked_scores_use_float32_without_changing_stored_vectors(storage, chunk_size):
    rng = np.random.default_rng(16)
    vectors = rng.normal(size=(513, 33)).astype(storage)
    original = vectors.copy()
    query = rng.normal(size=33).astype(np.float32)
    scores = dense_scores(vectors, query, chunk_size=chunk_size)
    assert scores.dtype == np.float32
    np.testing.assert_allclose(scores, vectors.astype(np.float32) @ query, atol=5e-6, rtol=1e-5)
    np.testing.assert_array_equal(vectors, original)


def test_storage_must_match_manifest(release_dir):
    path = release_dir / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["vector_storage"] = (
        "float32" if manifest["vector_storage"] == "float16" else "float16"
    )
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="dimensions"):
        Release.load(release_dir)


def test_unnormalized_vectors_are_rejected(release_dir):
    path = release_dir / "vectors.npy"
    vectors = np.load(path)
    vectors[0] *= 0.9
    np.save(path, vectors, allow_pickle=False)
    manifest_path = release_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["sha256"]["vectors.npy"] = sha256_file(path)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="normalized"):
        Release.load(release_dir)


@pytest.mark.parametrize("origin", [
    "https://arxiv.agarwal-labs.com", "http://localhost:5173", "http://127.0.0.1:8000",
])
def test_cors_preflight_does_not_load_artifacts(origin):
    def fail():
        pytest.fail("Preflight must not load artifacts")

    response = {}
    body = Application(fail)(
        {"HTTP_ORIGIN": origin, "PATH_INFO": "/api/search", "REQUEST_METHOD": "OPTIONS"},
        lambda status, headers: response.update(status=status, headers=dict(headers)),
    )
    assert response["status"] == "204 No Content" and body == [b""]
    assert response["headers"]["Access-Control-Allow-Origin"] == origin
    assert response["headers"]["Access-Control-Expose-Headers"] == "Retry-After"


@pytest.mark.parametrize("origin", [
    "https://evil.example", "http://localhost.evil.example", "null",
    "http://localhost:invalid", "http://user@localhost", "http://localhost/path",
])
def test_unapproved_origins_rejected_before_service_load(origin):
    app = Application(lambda: pytest.fail("Rejected origins must not load service"))
    result = request(app, "POST", "/api/search", {"query": "x"}, HTTP_ORIGIN=origin)
    assert result["status"] == 403
    assert "Access-Control-Allow-Origin" not in result["headers"]


def test_preview_browser_post_reaches_disabled_model_guard(release, monkeypatch):
    host = "arxiv-serving-preview-example-stealthymonkeys-projects.vercel.app"
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_URL", host)
    app = Application(lambda: SearchService(release, DisabledEmbedder(release.embedding)))
    result = request(app, "POST", "/api/search", {"query": "retrieval"},
                     HTTP_ORIGIN=f"https://{host}")
    assert result["status"] == 503
    assert result["body"]["error"]["code"] == "budget_exhausted"
    assert result["headers"]["Access-Control-Allow-Origin"] == f"https://{host}"


@pytest.mark.parametrize("origin", [
    "https://another-project.vercel.app",
    "https://preview.vercel.app.evil.example",
    "http://preview.vercel.app",
])
def test_preview_allowlist_is_exact(release, monkeypatch, origin):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_URL", "preview.vercel.app")
    app = Application(lambda: pytest.fail("Foreign origins must be rejected"))
    result = request(app, "POST", "/api/search", {"query": "x"},
                     HTTP_ORIGIN=origin, HTTP_HOST=origin.split("://")[1])
    assert result["status"] == 403

@pytest.mark.parametrize("code,reason", [
    ("budget_exhausted", "daily_budget"), ("rate_limited", "model_unavailable"),
    ("upstream_unavailable", "model_unavailable"),
])
def test_production_embedding_failure_falls_back_to_keyword_results(release, code, reason):
    class FailedEmbedder(FakeEmbedder):
        def embed(self, query, *, cache_key):
            raise APIError(code, "Unavailable")

    strict = SearchService(release, FailedEmbedder(release))
    with pytest.raises(APIError):
        strict.search({"query": "keyword"})
    tickets = MemoryTickets()
    service = SearchService(release, FailedEmbedder(release), lexical_fallback=True,
                            tickets=tickets)
    result = service.search({"query": "keyword", "k": 5})
    assert [r["rank"] for r in result["results"]] == [1, 2, 3, 4, 5]
    assert all(int(r["arxiv_id"][-1]) % 2 for r in result["results"])
    assert result["meta"]["stage"] == "lexical" and result["meta"]["fallback"] is True
    assert result["meta"]["summary_available"] is False
    assert result["meta"]["summary_unavailable_reason"] == reason
    assert "search_token" not in result and not tickets.bindings
    assert service.search({"query": "zzzunmatched"})["results"] == []


def test_visitor_limit_runs_before_any_model_call(release):
    class Limiter:
        def __init__(self):
            self.seen = []

        def admit_visitor(self, visitor):
            self.seen.append(visitor)
            if len(self.seen) > 1:
                raise APIError("rate_limited", "Slow down", 429, retry_after=7)

    embedder = FakeEmbedder(release)
    limiter = Limiter()
    app = Application(lambda: SearchService(release, embedder, visitors=limiter))
    env = {"HTTP_X_FORWARDED_FOR": "203.0.113.9, 10.0.0.1"}
    assert request(app, "POST", "/api/search", {"query": "retrieval"}, **env)["status"] == 200
    limited = request(app, "POST", "/api/search", {"query": "retrieval"}, **env)
    assert limited["status"] == 429 and limited["headers"]["Retry-After"] == "7"
    assert len(embedder.keys) == 1
    assert limiter.seen[0] == limiter.seen[1] and "203.0.113.9" not in limiter.seen[0]
    with pytest.raises(APIError, match="Visitor identity"):
        SearchService(release, embedder, visitors=limiter).search({"query": "retrieval"})


def test_visitor_id_prefers_vercel_real_ip_and_is_hashed():
    from arxiv_search.serving.http import visitor_id
    a = visitor_id({"HTTP_X_REAL_IP": "198.51.100.4", "HTTP_X_FORWARDED_FOR": "1.1.1.1"})
    assert a == visitor_id({"HTTP_X_FORWARDED_FOR": "198.51.100.4, 10.0.0.2"})
    assert a == visitor_id({"REMOTE_ADDR": "198.51.100.4"})
    assert a != visitor_id({"REMOTE_ADDR": "198.51.100.5"})
    assert len(a) == 64 and "198.51" not in a


@pytest.mark.parametrize("environment", ["development", ""])
def test_production_activation_requires_vercel_production_or_preview(
    monkeypatch, release, environment,
):
    monkeypatch.setenv("ARXIV_ENABLE_PAID_CALLS", "production-daily-v1")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", environment)
    monkeypatch.setattr(Release, "load", lambda directory: release)
    with pytest.raises(RuntimeError, match="restricted"):
        disabled_service()


@pytest.mark.parametrize("environment", ["production", "preview"])
def test_production_activation_still_requires_pinned_release(monkeypatch, release, environment):
    monkeypatch.setenv("ARXIV_ENABLE_PAID_CALLS", "production-daily-v1")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", environment)
    monkeypatch.setattr(Release, "load", lambda directory: release)
    with pytest.raises(RuntimeError, match="requires"):
        disabled_service()
