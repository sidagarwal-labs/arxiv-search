"""Atomic, non-expiring reservations for the explicitly approved preview trial."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import os
import re
import secrets
import time
from typing import Protocol
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler, ProxyHandler, Request, build_opener,
)

from arxiv_search.serving.service import APIError

LOG = logging.getLogger(__name__)
TRIAL_ID = "arxiv-e2e-2026-11-04-v1"

# One atomic hash update; denied/uncertain attempts are never refunded or retried.
# Policy is stored with usage so a redeploy cannot silently change the same budget.
RESERVE_SCRIPT = """
local key = KEYS[1]
local policy = ARGV[1]
local existing = redis.call('HGET', key, 'policy')
if not existing or existing ~= policy then return {'policy_mismatch'} end
local marker = 'attempt:' .. ARGV[2]
if redis.call('HEXISTS', key, marker) == 1 then return {'duplicate'} end
local searches = tonumber(redis.call('HGET', key, 'searches'))
local tokens = tonumber(redis.call('HGET', key, 'tokens'))
local cost = tonumber(redis.call('HGET', key, 'nanodollars'))
local calls = tonumber(redis.call('HGET', key, 'calls'))
for _, value in ipairs({searches, tokens, cost, calls}) do
    if not value or value < 0 or value ~= math.floor(value) then return {'invalid_state'} end
end
if not searches or not tokens or not cost or not calls then return {'invalid_state'} end
local add_searches = tonumber(ARGV[3])
local add_tokens = tonumber(ARGV[4])
local add_cost = tonumber(ARGV[5])
if searches + add_searches > tonumber(ARGV[6])
   or tokens + add_tokens > tonumber(ARGV[7])
   or cost + add_cost > tonumber(ARGV[8])
   or calls + 1 > tonumber(ARGV[9]) then return {'exhausted'} end
redis.call('HSET', key, 'policy', policy, marker, 'reserved',
           'searches', searches + add_searches, 'tokens', tokens + add_tokens,
           'nanodollars', cost + add_cost, 'calls', calls + 1)
return {'reserved', searches + add_searches, tokens + add_tokens, cost + add_cost, calls + 1}
"""

STATUS_SCRIPT = """
local existing = redis.call('HGET', KEYS[1], 'policy')
if not existing or existing ~= ARGV[1] then return {'policy_mismatch'} end
return {'status', redis.call('HGET', KEYS[1], 'searches'),
        redis.call('HGET', KEYS[1], 'tokens'),
        redis.call('HGET', KEYS[1], 'nanodollars'),
        redis.call('HGET', KEYS[1], 'calls')}
"""

PROVISION_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 1 then return {'already_exists'} end
redis.call('HSET', KEYS[1], 'policy', ARGV[1],
           'searches', 0, 'tokens', 0, 'nanodollars', 0, 'calls', 0)
return {'created'}
"""

SUMMARY_TICKET_SCRIPT = """
if redis.call('HGET', KEYS[1], 'policy') ~= ARGV[1] then return {'policy_mismatch'} end
local marker = 'summary:' .. ARGV[2]
if ARGV[4] == 'issue' then
    if redis.call('HSETNX', KEYS[1], marker, ARGV[3]) == 1 then return {'issued'} end
    return {'duplicate'}
end
if redis.call('HGET', KEYS[1], marker) ~= ARGV[3] then return {'invalid_ticket'} end
redis.call('HSET', KEYS[1], marker, 'consumed')
return {'consumed'}
"""


class RedisCommands(Protocol):
    def command(self, parts: list[str | int]) -> object: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise URLError("Redis redirects are forbidden")


class RedisREST:
    def __init__(self, url: str, token: str, *, max_response_bytes: int = 65_536):
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname
                or not parsed.hostname.endswith(".upstash.io") or parsed.port is not None
                or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or not token or token == "[SENSITIVE]"):
            raise ValueError("A valid Upstash HTTPS endpoint and writable token are required")
        if type(max_response_bytes) is not int or not 65_536 <= max_response_bytes <= 16_000_000:
            raise ValueError("Invalid Redis response limit")
        self.url = url.rstrip("/")
        self.token = token
        self.max_response_bytes = max_response_bytes
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    @classmethod
    def from_environment(cls) -> RedisREST:
        return cls(os.environ.get("KV_REST_API_URL", ""),
                   os.environ.get("KV_REST_API_TOKEN", ""))

    def command(self, parts: list[str | int]) -> object:
        request = Request(
            self.url, data=json.dumps(parts, allow_nan=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=5) as response:
                body = response.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                raise ValueError("Oversized Redis reply")
            value = json.loads(body)
            if not isinstance(value, dict) or set(value) != {"result"}:
                raise ValueError("Redis rejected the command")
            return value["result"]
        except (URLError, TimeoutError, OSError, ValueError):
            # Do not log URLs, tokens, Redis response bodies or request payloads.
            LOG.error("Trial accounting unavailable; model calls blocked")
            raise APIError(
                "upstream_unavailable", "Trial accounting is unavailable; no model call was started.",
            ) from None


@dataclass(frozen=True)
class TrialPolicy:
    max_searches: int = 5
    max_tokens: int = 100_000
    max_nanodollars: int = 500_000_000
    max_calls: int = 20

    def __post_init__(self):
        for value in (self.max_searches, self.max_tokens, self.max_nanodollars, self.max_calls):
            if type(value) is not int or value <= 0 or value > 2**40:
                raise ValueError("Trial limits must be positive bounded integers")

    def encoded(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Usage:
    searches: int
    tokens: int
    nanodollars: int
    calls: int


class TrialBudget:
    def __init__(self, redis: RedisCommands, *, trial_id: str = TRIAL_ID,
                 policy: TrialPolicy = TrialPolicy()):
        if not re.fullmatch(r"[a-zA-Z0-9:-]{1,120}", trial_id):
            raise ValueError("Invalid trial namespace")
        self.redis = redis
        self.policy = policy
        # Deliberately independent of deployment/release identity: redeploys do not reset limits.
        self.key = f"arxiv:trial:{trial_id}"

    def reserve(self, attempt_id: str, *, tokens: int, nanodollars: int,
                starts_search: bool = False) -> Usage:
        if not isinstance(attempt_id, str) or not 1 <= len(attempt_id) <= 256:
            raise ValueError("A unique attempt ID is required")
        if (type(tokens) is not int or not 0 < tokens <= 2**40
                or type(nanodollars) is not int or not 0 < nanodollars <= 2**40
                or type(starts_search) is not bool):
            raise ValueError("Reservations require positive integer tokens and model cost")
        marker = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        result = self.redis.command([
            "EVAL", RESERVE_SCRIPT, 1, self.key, self.policy.encoded(), marker,
            int(starts_search), tokens, nanodollars, self.policy.max_searches,
            self.policy.max_tokens, self.policy.max_nanodollars, self.policy.max_calls,
        ])
        return self._usage(result, "reserved")

    def status(self) -> Usage:
        return self._usage(self.redis.command([
            "EVAL", STATUS_SCRIPT, 1, self.key, self.policy.encoded(),
        ]), "status")

    def issue_summary(self, binding: str) -> str:
        token = secrets.token_hex(32)
        self._summary_ticket(token, binding, "issue")
        return token

    def consume_summary(self, token: object, binding: str) -> None:
        if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{64}", token):
            raise APIError("bad_request", "A valid search token is required for an answer.", 400)
        self._summary_ticket(token, binding, "consume")

    def _summary_ticket(self, token: str, binding: str, operation: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", binding):
            raise ValueError("A release-bound summary fingerprint is required")
        reply = self.redis.command([
            "EVAL", SUMMARY_TICKET_SCRIPT, 1, self.key, self.policy.encoded(),
            hashlib.sha256(token.encode()).hexdigest(), binding, operation,
        ])
        if reply == ["invalid_ticket"]:
            raise APIError(
                "bad_request", "The search token is invalid, already used, or belongs to different papers.",
                400,
            )
        expected = ["issued" if operation == "issue" else "consumed"]
        if reply != expected:
            LOG.error("Summary ticket accounting could not be verified")
            raise APIError("upstream_unavailable", "Answer authorization is unavailable.")

    def provision(self) -> None:
        """One-time operator action only; never run from request-time composition."""
        result = self.redis.command(["EVAL", PROVISION_SCRIPT, 1, self.key, self.policy.encoded()])
        if result != ["created"]:
            raise APIError("upstream_unavailable", "Trial accounting already exists or could not be provisioned.")

    def _usage(self, result: object, expected: str) -> Usage:
        if result == ["exhausted"]:
            raise APIError("budget_exhausted", "The protected trial limit has been reached.")
        if result == ["duplicate"]:
            raise APIError("rate_limited", "This model attempt was already reserved; do not retry.", 429)
        if (not isinstance(result, list) or len(result) != 5 or result[0] != expected):
            LOG.error("Invalid trial accounting state; model calls blocked")
            raise APIError("upstream_unavailable", "Trial accounting could not be verified.")
        values = []
        limits = (self.policy.max_searches, self.policy.max_tokens,
                  self.policy.max_nanodollars, self.policy.max_calls)
        for value, limit in zip(result[1:], limits):
            if type(value) not in (str, int) or not str(value).isascii() or not str(value).isdigit():
                raise APIError("upstream_unavailable", "Trial accounting returned invalid counters.")
            number = int(value)
            if not 0 <= number <= limit:
                raise APIError("upstream_unavailable", "Trial accounting exceeded its limits.")
            values.append(number)
        return Usage(*values)


def approved_trial(redis: RedisCommands, activation: str) -> TrialBudget:
    if activation == "protected-trial-v1":
        return TrialBudget(redis)
    if activation == "protected-trial-v2":
        return TrialBudget(
            redis, trial_id="arxiv-e2e-2026-11-04-v2",
            policy=TrialPolicy(max_searches=2, max_tokens=200_000,
                               max_nanodollars=500_000_000, max_calls=12),
        )
    if activation == "protected-trial-v3":
        return TrialBudget(
            redis, trial_id="arxiv-e2e-2026-11-04-v3",
            policy=TrialPolicy(max_searches=2, max_tokens=200_000,
                               max_nanodollars=500_000_000, max_calls=12),
        )
    raise ValueError("An explicitly approved protected trial is required")

# ---------------------------------------------------------------- production

# Same accounting as the trial, but one counter hash per UTC day that is created on
# first use and expires automatically. The policy digest is part of the key, so a
# redeploy with different limits starts fresh counters instead of failing closed.
DAILY_RESERVE_SCRIPT = RESERVE_SCRIPT.replace(
    "if not existing or existing ~= policy then return {'policy_mismatch'} end",
    "if not existing then\n"
    "    redis.call('HSET', key, 'policy', policy, 'searches', 0, 'tokens', 0,"
    " 'nanodollars', 0, 'calls', 0)\n"
    "    redis.call('EXPIRE', key, tonumber(ARGV[10]))\n"
    "elseif existing ~= policy then return {'policy_mismatch'} end",
)
assert DAILY_RESERVE_SCRIPT != RESERVE_SCRIPT

DAILY_STATUS_SCRIPT = """
local existing = redis.call('HGET', KEYS[1], 'policy')
if not existing then return {'status', 0, 0, 0, 0} end
if existing ~= ARGV[1] then return {'policy_mismatch'} end
return {'status', redis.call('HGET', KEYS[1], 'searches'),
        redis.call('HGET', KEYS[1], 'tokens'),
        redis.call('HGET', KEYS[1], 'nanodollars'),
        redis.call('HGET', KEYS[1], 'calls')}
"""

TICKET_CONSUME_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[1], 'consumed', 'KEEPTTL')
return 1
"""

# Rejected requests are not counted, so a client that waits is admitted again.
VISITOR_SCRIPT = """
local minute = tonumber(redis.call('GET', KEYS[1]) or '0')
local day = tonumber(redis.call('GET', KEYS[2]) or '0')
if minute >= tonumber(ARGV[1]) then return {'minute', redis.call('TTL', KEYS[1])} end
if day >= tonumber(ARGV[2]) then return {'day', redis.call('TTL', KEYS[2])} end
local m = redis.call('INCR', KEYS[1])
if m == 1 then redis.call('EXPIRE', KEYS[1], 60) end
local d = redis.call('INCR', KEYS[2])
if d == 1 then redis.call('EXPIRE', KEYS[2], 86400) end
return {'ok', 0}
"""


# Non-search visitor limits: (per minute, per UTC day, user-facing noun). Kept outside
# DailyPolicy so adding them does not change the policy digest (and today's counters).
VISITOR_LIMITS = {
    "paper_open": (10, 60, "papers opened"),
    "paper_ask": (8, 40, "paper questions"),
}


@dataclass(frozen=True)
class DailyPolicy(TrialPolicy):
    """Per-UTC-day ceiling on reserved (worst-case) model spend for the public site."""

    max_searches: int = 2_000
    max_tokens: int = 50_000_000
    max_nanodollars: int = 5_000_000_000  # $5.00
    max_calls: int = 20_000
    searches_per_minute: int = 10
    searches_per_day: int = 30

    def encoded(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))


class DailyBudget(TrialBudget):
    """Production budget: same reservation/ticket interface as ``TrialBudget``."""

    def __init__(self, redis: RedisCommands, *, namespace: str,
                 policy: DailyPolicy = DailyPolicy(), clock=None):
        if not re.fullmatch(r"[a-z0-9-]{1,40}", namespace):
            raise ValueError("Invalid daily budget namespace")
        self.redis = redis
        self.policy = policy
        self.clock = clock or time.time
        digest = hashlib.sha256(policy.encoded().encode()).hexdigest()[:12]
        self.prefix = f"arxiv:daily:{namespace}:{digest}"

    @property
    def key(self) -> str:  # type: ignore[override]
        return f"{self.prefix}:{time.strftime('%Y-%m-%d', time.gmtime(self.clock()))}"

    def reserve(self, attempt_id: str, *, tokens: int, nanodollars: int,
                starts_search: bool = False) -> Usage:
        if not isinstance(attempt_id, str) or not 1 <= len(attempt_id) <= 256:
            raise ValueError("A unique attempt ID is required")
        if (type(tokens) is not int or not 0 < tokens <= 2**40
                or type(nanodollars) is not int or not 0 < nanodollars <= 2**40
                or type(starts_search) is not bool):
            raise ValueError("Reservations require positive integer tokens and model cost")
        marker = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        result = self.redis.command([
            "EVAL", DAILY_RESERVE_SCRIPT, 1, self.key, self.policy.encoded(), marker,
            int(starts_search), tokens, nanodollars, self.policy.max_searches,
            self.policy.max_tokens, self.policy.max_nanodollars, self.policy.max_calls,
            3 * 86400,
        ])
        return self._usage(result, "reserved")

    def status(self) -> Usage:
        return self._usage(self.redis.command([
            "EVAL", DAILY_STATUS_SCRIPT, 1, self.key, self.policy.encoded(),
        ]), "status")

    def _usage(self, result: object, expected: str) -> Usage:
        if result == ["exhausted"]:
            raise APIError("budget_exhausted",
                           "Today's AI budget has been used. It resets at midnight UTC.")
        return super()._usage(result, expected)

    def _summary_ticket(self, token: str, binding: str, operation: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", binding):
            raise ValueError("A release-bound summary fingerprint is required")
        key = f"{self.prefix}:ticket:{hashlib.sha256(token.encode()).hexdigest()}"
        if operation == "issue":
            reply = self.redis.command(["SET", key, binding, "NX", "EX", 900])
            if reply != "OK":
                LOG.error("Summary ticket accounting could not be verified")
                raise APIError("upstream_unavailable", "Answer authorization is unavailable.")
            return
        reply = self.redis.command(["EVAL", TICKET_CONSUME_SCRIPT, 1, key, binding])
        if reply == 0:
            raise APIError(
                "bad_request", "The search token is invalid, expired, already used, "
                "or belongs to different papers.", 400,
            )
        if reply != 1:
            LOG.error("Summary ticket accounting could not be verified")
            raise APIError("upstream_unavailable", "Answer authorization is unavailable.")

    def admit_visitor(self, visitor: str, kind: str = "search") -> None:
        """Per-visitor limits. ``visitor`` should already be a non-reversible hash."""
        if not re.fullmatch(r"[0-9a-f]{64}", visitor):
            raise ValueError("Visitor identity must be hashed")
        if kind == "search":
            per_minute, per_day = self.policy.searches_per_minute, self.policy.searches_per_day
            scope, noun = f"{self.prefix}:visitor:{visitor}", "searches"
        elif kind in VISITOR_LIMITS:
            per_minute, per_day, noun = VISITOR_LIMITS[kind]
            scope = f"{self.prefix}:visitor:{kind}:{visitor}"
        else:
            raise ValueError("Unknown visitor limit")
        now = self.clock()
        minute = f"{scope}:m:{int(now // 60)}"
        day = f"{scope}:d:{time.strftime('%Y-%m-%d', time.gmtime(now))}"
        reply = self.redis.command(["EVAL", VISITOR_SCRIPT, 2, minute, day, per_minute, per_day])
        if reply == ["ok", 0]:
            return
        if isinstance(reply, list) and len(reply) == 2 and reply[0] in ("minute", "day"):
            wait = reply[1] if type(reply[1]) is int and reply[1] > 0 else 60
            message = (f"Too many {noun} in a minute. Please wait a moment." if reply[0] == "minute"
                       else f"You've reached today's limit for {noun}. Please come back tomorrow.")
            raise APIError("rate_limited", message, 429, retry_after=wait)
        LOG.error("Visitor rate limit could not be verified")
        raise APIError("upstream_unavailable", "Search rate limiting is unavailable.")


def production_budget(redis: RedisCommands, environment: str) -> DailyBudget:
    if environment == "production":
        return DailyBudget(redis, namespace="production")
    if environment == "preview":
        # Preview testing gets its own, smaller daily counters.
        return DailyBudget(redis, namespace="preview",
                           policy=DailyPolicy(max_nanodollars=1_000_000_000))
    raise ValueError("Daily budgets are only configured for Vercel production and preview")
