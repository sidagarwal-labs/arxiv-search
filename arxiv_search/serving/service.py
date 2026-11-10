"""Stable serving operations with replaceable, explicitly identified model adapters."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import logging
import math
import re
from threading import Lock
import time
from typing import Protocol

import numpy as np

from arxiv_search.serving import tracing
from arxiv_search.search.hybrid import fuse
from arxiv_search.search.rank_score import rescore_shortlist
from arxiv_search.search.rerank import rerank_prefix
from arxiv_search.search.text import tokenize
from arxiv_search.serving.lexical import PackedBM25
from arxiv_search.serving.release import EmbeddingSpec, Release

LOG = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, code: str, message: str, status: int = 503,
                 retry_after: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.retry_after = retry_after
        self.limits: dict | None = None


class Embedder(Protocol):
    spec: EmbeddingSpec

    def embed(self, query: str, *, cache_key: str) -> np.ndarray: ...


class Reranker(Protocol):
    model: str
    prompt_version: str

    def scores(self, query: str, papers: tuple[dict, ...], *, pass_index: int,
               cache_key: str) -> dict[str, float]: ...


@dataclass(frozen=True)
class Answer:
    summary: str
    cited: tuple[int, ...]
    grounded: bool


class Summarizer(Protocol):
    model: str
    prompt_version: str

    def summarize(self, query: str, papers: tuple[dict, ...], *,
                  cache_key: str) -> Answer: ...


class SummaryTickets(Protocol):
    def issue_summary(self, binding: str) -> str: ...

    def consume_summary(self, token: object, binding: str) -> None: ...


class VisitorLimiter(Protocol):
    def admit_visitor(self, visitor: str) -> None: ...


class DisabledEmbedder:
    def __init__(self, spec: EmbeddingSpec):
        self.spec = spec

    def embed(self, query: str, *, cache_key: str) -> np.ndarray:
        raise APIError(
            "budget_exhausted",
            "Live query embeddings are disabled pending model-usage approval.",
        )


def dense_scores(vectors: np.ndarray, query: np.ndarray, *, chunk_size: int = 256) -> np.ndarray:
    """Keep float16 storage compact while accumulating every dot product in float32."""
    if type(chunk_size) is not int or chunk_size <= 0:
        raise ValueError("Dense score chunk size must be a positive integer")
    query = np.asarray(query, dtype=np.float32)
    if vectors.ndim != 2 or query.shape != (vectors.shape[1],):
        raise ValueError("Dense score dimensions do not match")
    scores = np.empty(len(vectors), dtype=np.float32)
    for start in range(0, len(vectors), chunk_size):
        block = vectors[start:start + chunk_size].astype(np.float32, copy=False)
        scores[start:start + len(block)] = block @ query
    return scores


class LocalRetriever:
    def __init__(self, release: Release):
        self.release = release
        self.ids = [paper["arxiv_id"] for paper in release.papers]
        settings = release.manifest["retrieval"]
        if settings["adapter"] != "shortlist-v1":
            raise ValueError("Unsupported retrieval adapter")
        self.settings = settings
        if release.directory is None:
            raise ValueError("Retrieval requires a loaded release directory")
        self.lexical = PackedBM25(release.directory, self.ids, settings)

    def retrieve_lexical(self, query: str, k: int) -> list[str]:
        """Keyword-only order, used when query embeddings are unavailable."""
        lexical = self.lexical.scores(tokenize(query, add_stems=True))
        order = np.argsort(-lexical, kind="stable")[:k]
        return [self.ids[i] for i in order if lexical[i] > 0]

    def retrieve(self, query: str, vector: np.ndarray, k: int) -> list[str]:
        vector = np.asarray(vector, dtype=np.float32)
        if vector.shape != (self.release.embedding.dimensions,) or not np.isfinite(vector).all():
            raise ValueError("Query embedding shape or values invalid")
        norm = float(np.linalg.norm(vector))
        if norm <= 0 or not math.isfinite(norm):
            raise ValueError("Query embedding norm invalid")
        lexical = self.lexical.scores(tokenize(query, add_stems=True))
        semantic = dense_scores(self.release.vectors, vector / norm)
        depth = self.settings["score_depth"]
        lex_order = np.argsort(-lexical, kind="stable")[:depth]
        sem_order = np.argsort(-semantic, kind="stable")[:depth]
        # Match the evaluation adapter: only the lexical list omits zero scores.
        lex = {self.ids[i]: float(lexical[i]) for i in lex_order if lexical[i] > 0}
        sem = {self.ids[i]: float(semantic[i]) for i in sem_order}
        return rescore_shortlist(
            lex, sem, score_fraction=1, depth=depth, k=k,
            score_semantic_weight=self.settings["score_semantic_weight"],
            shortlist_size=self.settings["shortlist_size"],
        )


def validate_query(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 300:
        raise APIError("bad_request", "Query must contain 1 to 300 characters.", 400)
    return value.strip()


class SearchService:
    def __init__(self, release: Release, embedder: Embedder,
                 reranker: Reranker | None = None, summarizer: Summarizer | None = None, *,
                 refiner: Reranker | None = None, tickets: SummaryTickets | None = None,
                 visitors: VisitorLimiter | None = None, lexical_fallback: bool = False):
        if embedder.spec != release.embedding:
            raise ValueError("Query embedder is incompatible with this release's document vectors")
        for adapter, name in ((reranker, "reranking"), (summarizer, "summary"),
                              (refiner, "refinement")):
            if adapter is not None:
                pinned = release.manifest[name]
                if (adapter.model, adapter.prompt_version) != (
                    pinned["model"], pinned["prompt_version"]
                ):
                    raise ValueError(f"{name} adapter does not match the pinned release")
        self.release = release
        self.embedder = embedder
        self.reranker = reranker
        self.summarizer = summarizer
        self.refiner = refiner
        self.tickets = tickets
        self.visitors = visitors
        self.lexical_fallback = lexical_fallback
        self._retriever: LocalRetriever | None = None
        self._retriever_lock = Lock()
        self.papers = {p["arxiv_id"]: p for p in release.papers}

    def retriever(self) -> LocalRetriever:
        with self._retriever_lock:
            if self._retriever is None:
                self._retriever = LocalRetriever(self.release)
        return self._retriever

    def warm(self) -> None:
        """Do one-time loading before the first search instead of during it."""
        retriever = self.retriever()
        probe = np.zeros(self.release.embedding.dimensions, dtype=np.float32)
        probe[0] = 1.0
        retriever.retrieve("retrieval", probe, 1)
        transport = getattr(getattr(self.embedder, "provider", None), "transport", None)
        if hasattr(transport, "warm"):
            transport.warm()

    def _score_order(self, query: str, ids: list[str], adapter: Reranker,
                     operation: str, maximum: int) -> list[str]:
        settings = self.release.manifest[operation]
        candidates = tuple(self.papers[pid] for pid in ids[:settings["depth"]])
        expected = {p["arxiv_id"] for p in candidates}

        def score(pass_index: int) -> dict[str, float]:
            scores = adapter.scores(
                query, candidates, pass_index=pass_index,
                cache_key=self.release.cache_key(operation, {
                    "query": query, "ids": [p["arxiv_id"] for p in candidates],
                    "pass": pass_index,
                }),
            )
            if (not isinstance(scores, dict) or set(scores) != expected or any(
                type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= maximum
                for v in scores.values()
            )):
                raise APIError("upstream_unavailable", "Scoring returned invalid scores.")
            return scores

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(tracing.in_context(score), n) for n in range(settings["passes"])]
            passes = [future.result() for future in futures]
        mean = {pid: sum(p[pid] for p in passes) / len(passes) for pid in expected}
        llm = rerank_prefix(ids, mean, len(candidates))
        if settings["rrf_c"] is None:
            # Decision 50: order by averaged scores alone; stable sort keeps prior order on ties.
            return llm
        prefix = fuse(
            ids[:len(candidates)], llm[:len(candidates)], semantic_weight=0.5,
            c=settings["rrf_c"], depth=len(candidates), k=len(candidates),
        )
        return prefix + ids[len(candidates):]

    def search(self, body: dict, *, visitor: str | None = None) -> dict:
        query = validate_query(body.get("query"))
        k = body.get("k", 10)
        if type(k) is not int or not 1 <= k <= 20:
            raise APIError("bad_request", "k must be an integer from 1 to 20.", 400)
        if self.visitors is not None:
            if visitor is None:
                raise APIError("bad_request", "Visitor identity is required.", 400)
            self.visitors.admit_visitor(visitor)
        begin = time.perf_counter()
        unavailable: str | None = None
        try:
            vector = self.embedder.embed(
                query, cache_key=self.release.cache_key("embedding", {"query": query}),
            )
        except APIError as error:
            if not self.lexical_fallback or error.code not in (
                "rate_limited", "budget_exhausted", "upstream_unavailable",
            ):
                raise
            LOG.warning("Query embedding unavailable; keyword results only: %s", error.code)
            vector = None
            unavailable = "daily_budget" if error.code == "budget_exhausted" else "model_unavailable"
        retriever = self.retriever()
        settings = self.release.manifest["reranking"]
        if vector is None:
            return {
                "query": query,
                "results": [self._result(pid, rank) for rank, pid in
                            enumerate(retriever.retrieve_lexical(query, k), 1)],
                "meta": {
                    "stage": "lexical", "fallback": True, "refined": False,
                    "stage_detail": "bm25 keyword match (AI ranking unavailable)",
                    "latency_ms": round((time.perf_counter() - begin) * 1000),
                    "release": self.release.fingerprint,
                    "summary_available": False, "summary_unavailable_reason": unavailable,
                },
            }
        with tracing.span("retrieve", "retriever", inputs={"query": query}) as run:
            ids = retriever.retrieve(query, vector, max(k, settings["depth"]))
            tracing.end(run, candidates=len(ids), top_ids=ids[:10])
        fallback = True
        refined = False
        if self.reranker is not None and ids:
            try:
                with tracing.span("rerank", inputs={"candidates": len(ids)}) as run:
                    ids = self._score_order(query, ids, self.reranker, "reranking", 4)
                    tracing.end(run, top_ids=ids[:10])
                fallback = False
            except APIError as error:
                if error.code not in ("rate_limited", "budget_exhausted", "upstream_unavailable"):
                    raise
                LOG.warning("Reranker unavailable; retrieval order retained: %s", error.code)
        if not fallback and self.refiner is not None:
            try:
                with tracing.span("refine", inputs={"candidates": len(ids)}) as run:
                    updated = self._score_order(query, ids, self.refiner, "refinement", 10)
                    tracing.end(run, top_ids=updated[:10])
                if self.release.manifest["refinement"]["pin_first"]:
                    updated = [ids[0]] + [pid for pid in updated if pid != ids[0]]
                ids = updated
                refined = True
            except APIError as error:
                if error.code not in ("rate_limited", "budget_exhausted", "upstream_unavailable"):
                    raise
                LOG.warning("Refinement unavailable; Decision 46 order retained: %s", error.code)
        detail = self.release.manifest["baseline"]["retrieval"]
        if fallback:
            detail += " (reranking disabled or unavailable)"
        elif self.refiner is not None and not refined:
            detail += " -> llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30 (refinement unavailable)"
        else:
            detail += " -> " + self.release.manifest["baseline"]["reranking"]
        result = {
            "query": query,
            "results": [self._result(pid, rank) for rank, pid in enumerate(ids[:k], 1)],
            "meta": {
                "stage": "retrieval" if fallback else "reranked", "fallback": fallback,
                "refined": refined, "stage_detail": detail,
                "latency_ms": round((time.perf_counter() - begin) * 1000),
                "release": self.release.fingerprint,
                "summary_available": self.summarizer is not None,
            },
        }
        if self.tickets is not None and self.summarizer is not None and result["results"]:
            binding = self.release.cache_key("summary", {"query": query, "ids": ids[:min(k, 10)]})
            try:
                result["search_token"] = self.tickets.issue_summary(binding)
            except APIError as error:
                LOG.warning("Summary authorization unavailable: %s", error.code)
                result["meta"]["summary_available"] = False
                result["meta"]["summary_unavailable_reason"] = "authorization_unavailable"
        return result

    def _result(self, pid: str, rank: int) -> dict:
        paper = self.papers[pid]
        return {
            key: paper[key] for key in
            ("arxiv_id", "title", "abstract", "primary_category", "categories", "submitted_month")
        } | {
            "rank": rank, "authors": paper["authors"][:10],
            "authors_truncated": len(paper["authors"]) > 10,
            "url": f"https://arxiv.org/abs/{pid}",
        }

    def summary(self, body: dict) -> dict:
        query = validate_query(body.get("query"))
        ids = body.get("arxiv_ids")
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 10
                or any(not isinstance(pid, str) or pid not in self.papers for pid in ids)
                or len(set(ids)) != len(ids)):
            raise APIError("bad_request", "Provide 1 to 10 unique IDs from the corpus.", 400)
        if self.summarizer is None:
            raise APIError("budget_exhausted", "Live summaries are disabled pending approval.")
        binding = self.release.cache_key("summary", {"query": query, "ids": ids})
        if self.tickets is not None:
            self.tickets.consume_summary(body.get("search_token"), binding)
        begin = time.perf_counter()
        answer = self.summarizer.summarize(
            query, tuple(self.papers[pid] for pid in ids),
            cache_key=binding,
        )
        if (type(answer.grounded) is not bool or not isinstance(answer.summary, str)
                or not answer.summary.strip() or len(set(answer.cited)) != len(answer.cited)
                or any(type(n) is not int or not 1 <= n <= len(ids) for n in answer.cited)):
            raise ValueError("Summary adapter returned an invalid answer")
        markers = {
            int(n) for group in re.findall(r"\[([0-9]+(?:\s*,\s*[0-9]+)*)\]", answer.summary)
            for n in group.split(",")
        }
        contract_b = self.release.manifest["summary"] == {
            "model": "gpt-6-luna", "prompt_version": "answer-v2",
        }
        if (markers != set(answer.cited) or (not contract_b and not answer.grounded and answer.cited)
                or (answer.grounded and not answer.cited)):
            raise ValueError("Summary citations do not match its grounded answer")
        return {
            "summary": answer.summary, "cited": list(answer.cited), "grounded": answer.grounded,
            "model": self.summarizer.model,
            "latency_ms": round((time.perf_counter() - begin) * 1000),
        }
