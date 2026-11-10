"""Durable, metadata-only paper admission. No trial is provisioned at runtime."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Callable, Protocol, TypeVar

from arxiv_search.serving.budget import RedisCommands
from arxiv_search.serving.service import APIError

T = TypeVar("T")
MAX_METADATA_BYTES = 48_000
CAS_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[1], ARGV[2], 'KEEPTTL')
return 1
"""


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False)


class MetadataStore(Protocol):
    def read(self) -> str: ...
    def compare_exchange(self, before: str, after: str) -> bool: ...


class RedisMetadata:
    def __init__(self, redis: RedisCommands, namespace: str):
        if not re.fullmatch(r"paper:[A-Za-z0-9:-]{1,100}", namespace):
            raise ValueError("A separate paper-only namespace is required")
        self.redis = redis
        self.key = "arxiv:" + namespace

    def read(self) -> str:
        value = self.redis.command(["GET", self.key])
        if not isinstance(value, str):
            raise APIError("budget_exhausted", "Paper trial is not provisioned.", 503)
        return value

    def compare_exchange(self, before: str, after: str) -> bool:
        result = self.redis.command(["EVAL", CAS_SCRIPT, 1, self.key, before, after])
        if type(result) is not int or result not in (0, 1):
            raise APIError("upstream_unavailable", "Paper accounting is unavailable.", 503)
        return result == 1


@dataclass(frozen=True)
class PaperPolicy:
    """Unapproved limits supplied explicitly by offline callers, not an activation profile."""

    identity: str
    preparations: int
    sessions: int
    calls: int
    tokens: int
    nanodollars: int
    preparation_window_seconds: int = 60
    preparations_per_window: int = 5

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9:-]{1,100}", self.identity):
            raise ValueError("Invalid paper policy identity")
        for value in (self.preparations, self.sessions, self.calls, self.tokens, self.nanodollars,
                      self.preparation_window_seconds, self.preparations_per_window):
            if type(value) is not int or not 0 < value <= 2**40:
                raise ValueError("Paper limits must be positive bounded integers")

    def initial_state(self) -> str:
        """Operator/test provisioning data only; the service never writes an initial state."""
        return canonical({
            "policy": self.__dict__, "usage": {
                "preparations": 0, "sessions": 0, "calls": 0, "tokens": 0, "nanodollars": 0,
            }, "preparations": {}, "sessions": {},
        })

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical(self.__dict__).encode()).hexdigest()


class Admission:
    def __init__(self, store: MetadataStore, policy: PaperPolicy):
        self.store, self.policy = store, policy

    def update(self, change: Callable[[dict], T]) -> T:
        for _ in range(8):
            before = self.store.read()
            try:
                state = json.loads(before)
                if (set(state) != {"policy", "usage", "preparations", "sessions"}
                        or state["policy"] != self.policy.__dict__
                        or not isinstance(state["preparations"], dict)
                        or not isinstance(state["sessions"], dict)):
                    raise ValueError("Policy/state mismatch")
                for key in ("preparations", "sessions", "calls", "tokens", "nanodollars"):
                    value = state["usage"][key]
                    if type(value) is not int or not 0 <= value <= getattr(self.policy, key):
                        raise ValueError("Invalid accounting")
            except (ValueError, KeyError, TypeError):
                raise APIError("upstream_unavailable", "Paper accounting is invalid.", 503) from None
            result = change(state)
            after = canonical(state)
            if after == canonical(json.loads(before)):
                return result
            if len(after.encode("utf-8")) > MAX_METADATA_BYTES:
                raise APIError("budget_exhausted", "Paper metadata capacity was reached.", 503)
            if self.store.compare_exchange(before, after):
                return result
        raise APIError("session_busy", "Paper accounting is busy. Retry the same request.", 409)

    def charge(self, state: dict, **amounts: int) -> None:
        for key, amount in amounts.items():
            if type(amount) is not int or amount < 0:
                raise ValueError("Invalid reservation")
            if state["usage"][key] + amount > getattr(self.policy, key):
                raise APIError("budget_exhausted", "The separate paper trial limit was reached.", 503)
        for key, amount in amounts.items():
            state["usage"][key] += amount
