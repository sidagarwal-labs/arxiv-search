"""Public paper chat: the first question starts the conversation, no consent round-trips.

Two operations, both corpus-allowlisted and limited per hashed visitor:

- ``context {arxiv_id}``: no model call. Resolves HTML → PDF → abstract evidence with the
  paper core's ``PaperLoader`` and returns source/coverage, so the UI can disclose
  abstract-only coverage before anything is asked. Prepared context is cached 24 h.
- ``ask {arxiv_id, question, history}``: one ``paper_chat`` model call, reserved against the
  same daily budget as search before it is sent.

History is browser-held and unsigned: it is untrusted conversational context, not authenticated
transcript, and ``SYSTEM`` instructions do not make it injection-proof. Unlike the old
signed-session design there is no verified transcript, session expiry or per-session allowance.
This service's guarantees come from its own bounds instead: the shared daily budget, per-visitor
limits, exact request/history/token limits, the corpus allowlist, model-identity checks and
``paper_chat`` citation validation. Altered history can only affect the sender's own answer.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import logging
import re
from typing import Protocol
from uuid import uuid4

from arxiv_search import paper_chat
from arxiv_search.paper_text import Context
from arxiv_search.serving import tracing
from arxiv_search.serving.budget import RedisCommands
from arxiv_search.serving.paper_content import ContentStore
from arxiv_search.serving.paper_service import PaperError, PaperService, PaperTransport
from arxiv_search.serving.service import APIError

LOG = logging.getLogger(__name__)
MAX_HISTORY = 10
MODEL_TIMEOUT = 60


class PaperBudget(Protocol):
    def reserve(self, attempt_id: str, *, tokens: int, nanodollars: int,
                starts_search: bool = False) -> object: ...
    def admit_visitor(self, visitor: str, kind: str = "search") -> None: ...


class LivePaperService:
    def __init__(self, *, papers: set[str], loader: Callable[[str], Context],
                 content: ContentStore, redis: RedisCommands, namespace: str,
                 transport: PaperTransport, budget: PaperBudget,
                 count_tokens: Callable[[str], int]):
        if not re.fullmatch(r"[a-z0-9-]{1,40}", namespace):
            raise ValueError("Invalid paper namespace")
        self.papers, self.loader, self.content = papers, loader, content
        self.redis, self.transport, self.budget = redis, transport, budget
        self.count_tokens = count_tokens
        self.pointer = f"arxiv:paper:{namespace}:latest:"

    def _paper_id(self, body: dict, expected: set[str]) -> str:
        if set(body) != expected:
            raise PaperError("bad_request", "Unexpected or missing paper request fields.", 400)
        paper_id = body["arxiv_id"]
        if not isinstance(paper_id, str) or not re.fullmatch(r"\d{4}\.\d{4,5}", paper_id):
            raise PaperError("bad_request", "Use an unversioned arXiv ID.", 400)
        if paper_id not in self.papers:
            raise PaperError("not_in_corpus", "This paper is not in the search index.", 404)
        return paper_id

    def _load(self, paper_id: str) -> Context:
        with tracing.span("load-paper", "retriever", inputs={"arxiv_id": paper_id}) as run:
            context, cached = self._load_context(paper_id)
            coverage = context.coverage()
            tracing.end(run, cached=cached, source=coverage.get("source"),
                        version=context.paper.versioned_id,
                        paper_tokens=coverage.get("paper_tokens"))
        return context

    def _load_context(self, paper_id: str) -> tuple[Context, bool]:
        identity = self.redis.command(["GET", self.pointer + paper_id])
        if isinstance(identity, str) and re.fullmatch(r"[0-9a-f]{64}", identity):
            try:
                cached = self.content.get(identity)
            except APIError:
                cached = None  # Stale or changed entry: prepare it again below.
            if cached is not None:
                return cached, True
        context = self.loader(paper_id)
        if context.paper.versioned_id.rsplit("v", 1)[0] != paper_id:
            raise PaperError("context_changed", "Resolved paper does not match the request.", 409)
        identity = self.content.put(context)
        self.redis.command(["SET", self.pointer + paper_id, identity, "EX", 86400])
        return context, False

    def context(self, body: dict, *, visitor: str) -> dict:
        paper_id = self._paper_id(body, {"arxiv_id"})
        self.budget.admit_visitor(visitor, "paper_open")
        return {"paper": PaperService.paper(self._load(paper_id))}

    @staticmethod
    def _history(value: object) -> tuple[paper_chat.Exchange, ...]:
        if not isinstance(value, list) or len(value) > MAX_HISTORY:
            raise PaperError("bad_request",
                             f"History must be a list of at most {MAX_HISTORY} exchanges.", 400)
        exchanges = []
        for item in value:
            if (not isinstance(item, dict) or set(item) != {"user", "assistant"}
                    or not all(isinstance(item[k], str) and item[k].strip() for k in item)):
                raise PaperError("bad_request", "Each history item needs user and assistant text.", 400)
            exchanges.append(paper_chat.Exchange(item["user"].strip(), item["assistant"].strip()))
        return tuple(exchanges)

    def ask(self, body: dict, *, visitor: str) -> dict:
        paper_id = self._paper_id(body, {"arxiv_id", "question", "history"})
        question = body["question"]
        if (not isinstance(question, str) or not question.strip()
                or len(question.strip()) > paper_chat.MAX_QUESTION_CHARS):
            raise PaperError("bad_request", "Questions must be 1 to 500 characters.", 400)
        exchanges = self._history(body["history"])
        self.budget.admit_visitor(visitor, "paper_ask")
        context = self._load(paper_id)
        try:
            encoded, memory = paper_chat.encode_payload(
                context, question.strip(), exchanges, self.count_tokens,
            )
            reserved = paper_chat.reservation(encoded, self.count_tokens)
        except ValueError:
            raise PaperError("bad_request", "The question or conversation history is invalid.", 400) from None
        self.budget.reserve(uuid4().hex, tokens=reserved["total_tokens"],
                            nanodollars=reserved["nanodollars"])
        with tracing.span(
            "paper-answer", "llm",
            inputs={"model": paper_chat.MODEL, "question": question.strip(),
                    "history_turns": len(exchanges)},
            metadata={"ls_provider": "openai", "ls_model_name": paper_chat.MODEL,
                      "reserved_tokens": reserved["total_tokens"],
                      "reserved_usd": round(reserved["nanodollars"] / 1e9, 6)},
        ) as run:
            response = self.transport.post("responses", json.loads(encoded), timeout=MODEL_TIMEOUT)
            tracing.end(run, usage_metadata=tracing.usage(response),
                        output=tracing.clip(tracing.response_text(response)))
        # Exact identity stays enforced by parse_response; this only reports a mismatch distinctly.
        returned = response.get("model") if isinstance(response, dict) else None
        if returned != paper_chat.MODEL:
            LOG.warning("Paper chat model identity mismatch: expected %s, got %r",
                        paper_chat.MODEL, str(returned)[:80])
            raise PaperError("model_identity_mismatch",
                             "The AI service answered with an unexpected model. Please try again later.",
                             502)
        try:
            result = paper_chat.parse_response(response, context)
        except ValueError:
            raise PaperError("model_invalid_answer",
                             "The answer didn't pass citation checks. Try rephrasing.", 502) from None
        return {**result, "paper": PaperService.paper(context), "memory": memory.as_dict()}
