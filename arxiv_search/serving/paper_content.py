"""Private prepared-context storage; deliberately separate from transcript-free metadata."""

from __future__ import annotations

from dataclasses import asdict
import json
import re
from typing import Protocol

from arxiv_search import paper_chat
from arxiv_search.paper_text import Context, Omission, Paper, Section
from arxiv_search.serving.budget import RedisCommands
from arxiv_search.serving.paper_state import canonical
from arxiv_search.serving.service import APIError


class ContentStore(Protocol):
    def put(self, context: Context) -> str: ...
    def get(self, identity: str) -> Context | None: ...


class RedisContent:
    def __init__(self, redis: RedisCommands, namespace: str):
        if not re.fullmatch(r"paper:[A-Za-z0-9:-]{1,100}", namespace):
            raise ValueError("A separate paper-only namespace is required")
        self.redis, self.prefix = redis, "arxiv:" + namespace + ":context:"

    def put(self, context: Context) -> str:
        identity = paper_chat.cache_key(context)
        encoded = canonical(asdict(context))
        if len(encoded.encode("utf-8")) > 2_000_000:
            raise APIError("paper_unavailable", "Prepared paper exceeds the storage limit.", 503)
        # 24 h covers the 10 min consent + 30 min conversation windows.
        result = self.redis.command(["SET", self.prefix + identity, encoded, "EX", 86400])
        if result != "OK":
            raise APIError("paper_unavailable", "Prepared paper storage is unavailable.", 503)
        return identity

    def get(self, identity: str) -> Context | None:
        if not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise APIError("context_changed", "Prepared paper identity is invalid.", 409)
        encoded = self.redis.command(["GET", self.prefix + identity])
        if encoded is None:
            return None
        try:
            value = json.loads(encoded)
            raw_paper = value["paper"]
            paper = Paper(
                raw_paper["versioned_id"], raw_paper["title"], raw_paper["source"],
                tuple(Section(**s) for s in raw_paper["sections"]), tuple(raw_paper["warnings"]),
            )
            context = Context(paper, tuple(Section(**s) for s in value["included"]),
                              tuple(Omission(**s) for s in value["omitted"]), value["paper_tokens"])
            if canonical(asdict(context)) != encoded or paper_chat.cache_key(context) != identity:
                raise ValueError("Prepared context changed")
            return context
        except (ValueError, TypeError, KeyError):
            raise APIError("context_changed", "Prepared paper changed. Prepare it again.", 409) from None
