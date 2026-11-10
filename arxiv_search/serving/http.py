"""Small WSGI boundary; paper operations require an explicit injected offline adapter."""

from __future__ import annotations

from contextlib import nullcontext
from http import HTTPStatus
import hashlib
import json
import logging
import os
from pathlib import Path
from threading import Lock
import time
from typing import Callable, Protocol
from urllib.parse import urlsplit
from wsgiref.simple_server import make_server

from arxiv_search.serving import tracing
from arxiv_search.serving.release import Release
from arxiv_search.serving.service import APIError, DisabledEmbedder, SearchService


class PaperOperations(Protocol):
    def prepare(self, body: dict) -> dict: ...
    def open(self, body: dict) -> dict: ...
    def chat(self, body: dict) -> dict: ...

LOG = logging.getLogger(__name__)
MAX_BODY = 16_384
# Public site: $5/day reserved-spend cap plus per-visitor search limits (budget.DailyPolicy).
PRODUCTION_ACTIVATION = "production-daily-v1"


def allowed_origin(origin: str) -> bool:
    if origin == "https://arxiv.agarwal-labs.com":
        return True
    # Trust platform configuration, not the client-supplied Host/Forwarded headers.
    deployment_host = os.environ.get("VERCEL_URL", "")
    if (os.environ.get("VERCEL") == "1" and deployment_host
            and origin == f"https://{deployment_host}"):
        return True
    try:
        url = urlsplit(origin)
        port = url.port
    except ValueError:
        return False
    return (
        url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1")
        and url.username is None and url.password is None
        and not url.path and not url.query and not url.fragment
        and (port is None or 1 <= port <= 65535)
    )


def visitor_id(environ: dict) -> str:
    """Hashed client address. On Vercel the platform sets these headers, not the client."""
    address = (environ.get("HTTP_X_REAL_IP")
               or environ.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]
               or environ.get("REMOTE_ADDR") or "unknown").strip()[:64]
    return hashlib.sha256(("arxiv-visitor-v1:" + address).encode("utf-8")).hexdigest()


class Application:
    def __init__(self, factory: Callable[[], SearchService], *,
                 paper_service: PaperOperations | None = None):
        self.factory = factory
        # No environment flag wires paper calls: deployment/activation is a separate milestone.
        self.paper_service = paper_service
        self._service: SearchService | None = None
        self._lock = Lock()

    def service(self) -> SearchService:
        with self._lock:
            if self._service is None:
                self._service = self.factory()
        return self._service

    def warm(self) -> None:
        """Load the release and index at cold start so the first search doesn't pay for it."""
        begin = time.perf_counter()
        try:
            self.service().warm()
        except Exception:
            LOG.warning("Warm-up failed; loading lazily on the first request", exc_info=True)
            return
        LOG.info("Warm-up finished in %d ms", (time.perf_counter() - begin) * 1000)

    def __call__(self, environ: dict, start_response: Callable) -> list[bytes]:
        headers = [("Content-Type", "application/json; charset=utf-8"),
                   ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")]
        try:
            origin = environ.get("HTTP_ORIGIN")
            if origin:
                headers.append(("Vary", "Origin"))
                if not allowed_origin(origin):
                    raise APIError("bad_request", "Origin is not allowed.", 403)
                headers.extend([
                    ("Access-Control-Allow-Origin", origin),
                    ("Access-Control-Expose-Headers", "Retry-After"),
                ])
            path = environ.get("PATH_INFO", "")
            method = environ.get("REQUEST_METHOD", "")
            expected = {"/api/meta": "GET", "/api/search": "POST", "/api/summary": "POST",
                        "/api/paper/prepare": "POST", "/api/paper/open": "POST",
                        "/api/paper/chat": "POST", "/api/paper/context": "POST",
                        "/api/paper/ask": "POST"}
            paper_path = path.startswith("/api/paper/")
            if path not in expected:
                raise APIError("bad_request", "Unknown API endpoint.", 404)
            if method == "OPTIONS" and origin:
                headers.extend([
                    ("Access-Control-Allow-Methods", expected[path] + ", OPTIONS"),
                    ("Access-Control-Allow-Headers", "Content-Type"),
                    ("Content-Length", "0"),
                ])
                start_response("204 No Content", headers)
                return [b""]
            if method != expected[path]:
                headers.append(("Allow", expected[path]))
                raise APIError("bad_request", "Method not allowed.", 405)
            body = {}
            if method == "POST":
                if environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower() != "application/json":
                    raise APIError("bad_request", "Content-Type must be application/json.", 415)
                try:
                    length = int(environ.get("CONTENT_LENGTH", ""))
                except (TypeError, ValueError):
                    raise APIError("bad_request", "Content-Length is required.", 411) from None
                max_body = 524_288 if paper_path else MAX_BODY
                if not 0 < length <= max_body:
                    raise APIError("bad_request", f"Request body must be 1 to {max_body} bytes.", 413)
                raw = environ["wsgi.input"].read(length)
                if len(raw) != length:
                    raise APIError("bad_request", "Incomplete request body.", 400)
                try:
                    body = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise APIError("bad_request", "Request body must be valid JSON.", 400) from None
                if not isinstance(body, dict):
                    raise APIError("bad_request", "Request body must be a JSON object.", 400)
                # Reject malformed input before loading the corpus.
                if not paper_path:
                    from arxiv_search.serving.service import validate_query
                    validate_query(body.get("query"))
            traced = TRACED.get(path)
            request_span = tracing.span(
                traced, inputs=trace_inputs(path, body), metadata=trace_metadata(environ),
            ) if traced else nullcontext(tracing.NullRun())
            with request_span as run:
                if paper_path:
                    operation = path.rsplit("/", 1)[1]
                    if operation in ("context", "ask"):
                        live = getattr(self.service(), "paper", None)
                        if live is None:
                            raise APIError("budget_exhausted", "Paper chat is not enabled here.", 503)
                        result = getattr(live, operation)(body, visitor=visitor_id(environ))
                    elif self.paper_service is None:
                        raise APIError("budget_exhausted",
                                       "Live paper chat is disabled pending separate approval.", 503)
                    else:
                        result = getattr(self.paper_service, operation)(body)
                elif path == "/api/meta":
                    service = self.service()
                    result = service.release.metadata()
                elif path == "/api/search":
                    service = self.service()
                    result = service.search(body, visitor=visitor_id(environ))
                else:
                    service = self.service()
                    result = service.summary(body)
                if traced:
                    tracing.end(run, **trace_outputs(path, result))
            status = 200
        except APIError as error:
            status = error.status
            result = {"error": {"code": error.code, "message": str(error)}}
            if getattr(error, "limits", None) is not None:
                result["limits"] = error.limits
            if error.retry_after is not None:
                headers.append(("Retry-After", str(error.retry_after)))
        except Exception:
            # The HTTP boundary must never expose stack traces or provider payloads.
            LOG.error("Unhandled serving failure", exc_info=True)
            status = 500
            result = {"error": {"code": "internal", "message": (
                "Paper service failed." if environ.get("PATH_INFO", "").startswith("/api/paper/")
                else "Search service failed."
            )}}
        if TRACED.get(environ.get("PATH_INFO", "")) and environ.get("REQUEST_METHOD") == "POST":
            tracing.flush()
        data = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
        headers.append(("Content-Length", str(len(data))))
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [data]


TRACED = {"/api/search": "search", "/api/summary": "summary",
          "/api/paper/context": "paper-context", "/api/paper/ask": "paper-ask"}


def trace_inputs(path: str, body: dict) -> dict:
    if path == "/api/search":
        return {"query": body.get("query"), "k": body.get("k", 10)}
    if path == "/api/summary":
        return {"query": body.get("query"), "arxiv_ids": body.get("arxiv_ids")}
    if path == "/api/paper/ask":
        history = body.get("history")
        return {"arxiv_id": body.get("arxiv_id"), "question": body.get("question"),
                "history_turns": len(history) if isinstance(history, list) else None}
    return {"arxiv_id": body.get("arxiv_id")}


def trace_outputs(path: str, result: dict) -> dict:
    try:
        return _trace_outputs(path, result)
    except Exception:
        LOG.warning("Could not summarize %s for tracing", path, exc_info=True)
        return {}


def _trace_outputs(path: str, result: dict) -> dict:
    if path == "/api/search":
        return {"meta": result.get("meta"),
                "results": [f"{r['rank']}. {r['arxiv_id']} {r['title']}" for r in result["results"]]}
    if path == "/api/summary":
        return {key: result.get(key) for key in ("summary", "grounded", "cited", "meta")}
    if path == "/api/paper/ask":
        return {"answer": result.get("answer"), "grounded": result.get("grounded"),
                "citations": [c.get("id") for c in result.get("citations", [])],
                "memory": result.get("memory")}
    paper = result.get("paper") or {}
    return {"source": paper.get("source"), "version": paper.get("version"),
            "paper_tokens": (paper.get("coverage") or {}).get("paper_tokens")}


def trace_metadata(environ: dict) -> dict:
    return {"vercel_env": os.environ.get("VERCEL_ENV", "local"),
            "deployment": os.environ.get("VERCEL_DEPLOYMENT_ID", "local")}


def disabled_service() -> SearchService:
    enabled = os.environ.get("ARXIV_ENABLE_PAID_CALLS", "0")
    if enabled not in ("0", "protected-trial-v1", "protected-trial-v2", "protected-trial-v3",
                       PRODUCTION_ACTIVATION):
        raise RuntimeError(
            "Paid serving requires the explicitly configured protected trial"
        )
    directory = Path(os.environ.get(
        "ARXIV_RELEASE_DIR", str(Path(__file__).resolve().parents[2] / "artifacts"),
    ))
    release = Release.load(directory)
    if enabled != "0":
        production = enabled == PRODUCTION_ACTIVATION
        if os.environ.get("VERCEL") != "1" or os.environ.get("VERCEL_ENV") not in (
            ("production", "preview") if production else ("preview",)
        ):
            raise RuntimeError("The approved model trial is restricted to Vercel Preview")
        if (release.manifest["reranking"] != {
            "model": "gpt-5.4-mini-2026-03-17", "prompt_version": "scores-v2",
            "depth": 50, "passes": 2, "rrf_c": 30,
        }):
            raise RuntimeError("The trial requires the pinned Decision 46 reranker")
        from arxiv_search.serving.budget import RedisREST, approved_trial
        from arxiv_search.serving.provider import (
            BudgetedProvider, OpenAIEmbedder, OpenAIReranker, OpenAIRefiner,
            OpenAISummarizer, OpenAITransport, TokenCounter,
        )
        refinement = release.manifest.get("refinement")
        summary = release.manifest["summary"]
        if refinement is not None and refinement not in ({
            "model": "gpt-5.4-mini-2026-03-17", "prompt_version": "refine20-v1",
            "depth": 20, "passes": 2, "rrf_c": 30, "pin_first": True,
        }, {
            "model": "gpt-5.4-2026-03-05", "prompt_version": "refine20-v1",
            "depth": 20, "passes": 2, "rrf_c": None, "pin_first": True,
        }):
            raise RuntimeError("The trial requires the pinned Decision 47 or Decision 50 refinement")
        if summary not in (
            {"model": None, "prompt_version": None},
            {"model": "gpt-5.4-mini-2026-03-17", "prompt_version": "answer-v1"},
            {"model": "gpt-6-luna", "prompt_version": "answer-v2"},
        ):
            raise RuntimeError("The trial requires a pinned Decision 48 or Decision 49 answer model")
        if enabled == "protected-trial-v2" and (
            refinement is None or summary["model"] is None
        ):
            raise RuntimeError("The second trial requires Decision 47 refinement and Decision 48 answers")
        if enabled in ("protected-trial-v3", PRODUCTION_ACTIVATION) and (
            refinement is None or summary != {"model": "gpt-6-luna", "prompt_version": "answer-v2"}
        ):
            raise RuntimeError("The third trial requires Decision 47 refinement and Decision 49 answers")
        from arxiv_search.serving.budget import production_budget
        redis = RedisREST.from_environment()
        budget = (production_budget(redis, os.environ["VERCEL_ENV"]) if production
                  else approved_trial(redis, enabled))
        budget.status()
        name = release.manifest["tokenizer_file"]
        if name != "tokenizers.json":
            raise ValueError("Unsupported tokenizer artifact")
        counter = TokenCounter(directory / name, release.manifest["sha256"][name])
        transport = OpenAITransport(os.environ.get("OPENAI_API_KEY", ""))
        provider = BudgetedProvider(transport, budget, counter)
        service = SearchService(
            release, OpenAIEmbedder(release.embedding, provider), OpenAIReranker(provider),
            OpenAISummarizer(provider, **summary) if summary["model"] is not None else None,
            refiner=(OpenAIRefiner(provider, model=refinement["model"])
                     if refinement is not None else None),
            tickets=budget if summary["model"] is not None else None,
            visitors=budget if production else None, lexical_fallback=production,
        )
        # Kill switch: ARXIV_PAPER_CHAT=off disables paper chat without touching search.
        if production and os.environ.get("ARXIV_PAPER_CHAT", "on") != "off":
            service.paper = live_paper(release, counter, transport, budget,
                                       os.environ["VERCEL_ENV"])
        return service
    return SearchService(release, DisabledEmbedder(release.embedding))


def live_paper(release: Release, counter, transport, budget, environment: str):
    from arxiv_search.serving.budget import RedisREST
    from arxiv_search.serving.paper_content import RedisContent
    from arxiv_search.serving.paper_live import LivePaperService
    from arxiv_search.serving.paper_loader import ArxivTransport, PaperLoader

    namespace = "live-production" if environment == "production" else "live-preview"
    # Prepared papers can be large; this client is only used for paper context storage.
    redis = RedisREST(os.environ.get("KV_REST_API_URL", ""),
                      os.environ.get("KV_REST_API_TOKEN", ""), max_response_bytes=12_000_100)
    corpus = {p["arxiv_id"]: p for p in release.papers}
    loader = PaperLoader(corpus, counter.count_paper, ArxivTransport(), timeout=20)
    return LivePaperService(
        papers=set(corpus), loader=loader.load, content=RedisContent(redis, "paper:" + namespace),
        redis=redis, namespace=namespace, transport=transport, budget=budget,
        count_tokens=counter.count_paper,
    )


app = Application(disabled_service)
if os.environ.get("VERCEL") == "1":
    app.warm()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with make_server("127.0.0.1", 8000, app) as server:
        LOG.info("Serving local API at http://127.0.0.1:8000 (paid calls disabled)")
        server.serve_forever()


if __name__ == "__main__":
    main()
