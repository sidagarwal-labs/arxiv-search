import json
from io import BytesIO
from urllib.error import URLError

import pytest

from arxiv_search.serving.budget import (
    RedisREST, RESERVE_SCRIPT, TrialBudget, TrialPolicy, Usage, approved_trial,
)
from arxiv_search.serving.service import APIError


def test_large_paper_redis_reply_requires_explicit_bounded_connection():
    encoded = json.dumps({"result": "x" * 100_000}).encode()

    class Opener:
        def open(self, request, *, timeout):
            return BytesIO(encoded)

    original = RedisREST("https://example.upstash.io", "private-token")
    original.opener = Opener()
    with pytest.raises(APIError):
        original.command(["GET", "fixture"])
    paper = RedisREST("https://example.upstash.io", "private-token", max_response_bytes=200_000)
    paper.opener = Opener()
    assert paper.command(["GET", "fixture"]) == "x" * 100_000
    with pytest.raises(ValueError):
        RedisREST("https://example.upstash.io", "private-token", max_response_bytes=16_000_001)


class RedisStub:
    def __init__(self, result):
        self.result = result
        self.commands = []

    def command(self, parts):
        self.commands.append(parts)
        return self.result


def test_trial_policy_matches_approval():
    policy = TrialPolicy()
    assert (policy.max_searches, policy.max_tokens, policy.max_nanodollars) == (
        5, 100_000, 500_000_000,
    )


def test_reservations_hash_ids_and_use_one_atomic_command():
    redis = RedisStub(["reserved", 1, 2000, 3_000_000, 1])
    guard = TrialBudget(redis)
    usage = guard.reserve("private-query-not-for-storage", tokens=2000,
                          nanodollars=3_000_000, starts_search=True)
    assert usage == Usage(1, 2000, 3_000_000, 1)
    assert len(redis.commands) == 1
    command = redis.commands[0]
    assert command[:3] == ["EVAL", RESERVE_SCRIPT, 1]
    assert "private-query-not-for-storage" not in json.dumps(command)
    assert command[6:] == [1, 2000, 3_000_000, 5, 100_000, 500_000_000, 20]
    assert "EXPIRE" not in RESERVE_SCRIPT and "DEL" not in RESERVE_SCRIPT


def test_deployments_share_trial_key():
    a = TrialBudget(RedisStub(None))
    b = TrialBudget(RedisStub(None))
    assert a.key == b.key == "arxiv:trial:arxiv-e2e-2026-11-04-v1"


def test_second_trial_uses_separately_approved_limits_without_provisioning():
    redis = RedisStub(["reserved", 1, 2000, 3_000_000, 1])
    original = approved_trial(redis, "protected-trial-v1")
    current = approved_trial(redis, "protected-trial-v2")
    assert redis.commands == []
    assert original.key == TrialBudget(redis).key
    assert current.key == "arxiv:trial:arxiv-e2e-2026-11-04-v2"
    assert current.key != original.key
    assert current.policy == TrialPolicy(2, 200_000, 500_000_000, 12)
    assert original.policy == TrialPolicy()
    current.reserve("new-trial-attempt", tokens=2000, nanodollars=3_000_000, starts_search=True)
    assert len(redis.commands) == 1
    assert redis.commands[0][3] == current.key
    assert redis.commands[0][6:] == [1, 2000, 3_000_000, 2, 200_000, 500_000_000, 12]
    assert approved_trial(redis, "protected-trial-v2").key == current.key


def test_third_trial_is_separate_and_never_automatically_provisioned():
    redis = RedisStub(None)
    budgets = [approved_trial(redis, f"protected-trial-v{n}") for n in (1, 2, 3)]
    assert len({b.key for b in budgets}) == 3
    assert budgets[2].key == "arxiv:trial:arxiv-e2e-2026-11-04-v3"
    assert budgets[2].policy == TrialPolicy(2, 200_000, 500_000_000, 12)
    assert redis.commands == []


@pytest.mark.parametrize("activation", ["", "0", "1", "protected-trial-v4"])
def test_unapproved_trial_profile_never_contacts_redis(activation):
    redis = RedisStub(None)
    with pytest.raises(ValueError, match="explicitly approved"):
        approved_trial(redis, activation)
    assert redis.commands == []


@pytest.mark.parametrize("reply,code", [
    (["exhausted"], "budget_exhausted"),
    (["duplicate"], "rate_limited"),
    (["policy_mismatch"], "upstream_unavailable"),
    (None, "upstream_unavailable"),
    (["reserved", True, 0, 0, 0], "upstream_unavailable"),
    (["reserved", 0, "nan", 0, 0], "upstream_unavailable"),
    (["reserved", 0, 100_001, 0, 0], "upstream_unavailable"),
    (["reserved", 0, 1, 500_000_001, 0], "upstream_unavailable"),
    (["reserved", 6, 1, 1, 1], "upstream_unavailable"),
])
def test_failure_replies_never_authorize_calls(reply, code):
    redis = RedisStub(reply)
    with pytest.raises(APIError) as error:
        TrialBudget(redis).reserve("attempt", tokens=1, nanodollars=1)
    assert error.value.code == code
    assert len(redis.commands) == 1


@pytest.mark.parametrize("tokens,cost", [(0, 1), (-1, 1), (True, 1), (1, 0), (1, 1.1)])
def test_invalid_reservations_do_not_touch_redis(tokens, cost):
    redis = RedisStub(None)
    with pytest.raises(ValueError):
        TrialBudget(redis).reserve("id", tokens=tokens, nanodollars=cost)
    assert not redis.commands


def test_status_is_read_only():
    redis = RedisStub(["status", "1", "200", "1000", "4"])
    assert TrialBudget(redis).status() == Usage(1, 200, 1000, 4)
    assert "HSET" not in redis.commands[0][1]


def test_provision_is_explicit_and_never_resets_existing_state():
    redis = RedisStub(["created"])
    guard = TrialBudget(redis)
    guard.provision()
    redis.result = ["already_exists"]
    with pytest.raises(APIError):
        guard.provision()
    assert "EXISTS" in redis.commands[0][1]


def test_missing_state_blocks_reservation_without_automatic_provision():
    redis = RedisStub(["policy_mismatch"])
    with pytest.raises(APIError):
        TrialBudget(redis).reserve("attempt", tokens=1, nanodollars=1)
    assert len(redis.commands) == 1
    assert "if not existing" in redis.commands[0][1]


def test_summary_tickets_are_random_hashed_release_bound_and_single_use():
    from arxiv_search.serving.budget import SUMMARY_TICKET_SCRIPT
    redis = RedisStub(["issued"])
    budget = TrialBudget(redis)
    binding = "a" * 64
    token = budget.issue_summary(binding)
    assert len(token) == 64
    issue = redis.commands[0]
    assert token not in json.dumps(issue)
    assert issue[:4] == ["EVAL", SUMMARY_TICKET_SCRIPT, 1, budget.key]
    assert issue[-2:] == [binding, "issue"]
    redis.result = ["consumed"]
    budget.consume_summary(token, binding)
    assert redis.commands[1][-3:] == [issue[-3], binding, "consume"]
    assert "HSETNX" in SUMMARY_TICKET_SCRIPT
    assert "'consumed'" in SUMMARY_TICKET_SCRIPT
    redis.result = ["invalid_ticket"]
    with pytest.raises(APIError, match="already used"):
        budget.consume_summary(token, binding)
    assert len(redis.commands) == 3


@pytest.mark.parametrize("token", [None, "", "a" * 63, "Z" * 64, {}, 123])
def test_invalid_summary_token_never_contacts_redis(token):
    redis = RedisStub(None)
    with pytest.raises(APIError):
        TrialBudget(redis).consume_summary(token, "b" * 64)
    assert redis.commands == []


def test_summary_ticket_missing_policy_fails_closed():
    redis = RedisStub(["policy_mismatch"])
    with pytest.raises(APIError, match="authorization"):
        TrialBudget(redis).issue_summary("c" * 64)


@pytest.mark.parametrize("url", [
    "http://example.upstash.io", "https://evil.example",
    "https://foo.upstash.io.evil.example", "https://user@foo.upstash.io",
    "https://foo.upstash.io/path", "https://foo.upstash.io:443",
])
def test_transport_does_not_send_credentials_to_unapproved_endpoint(url):
    with pytest.raises(ValueError):
        RedisREST(url, "secret")


def test_rest_timeout_is_sanitized_and_not_retried(caplog):
    class Failed:
        calls = 0

        def open(self, request, timeout):
            self.calls += 1
            raise URLError("secret-detail")

    redis = RedisREST("https://example.upstash.io", "private-token")
    redis.opener = Failed()
    with pytest.raises(APIError) as error:
        redis.command(["PING"])
    assert redis.opener.calls == 1
    assert error.value.code == "upstream_unavailable"
    assert "secret-detail" not in str(error.value)
    assert "private-token" not in caplog.text


class DailyRedis:
    """In-memory emulation of the daily scripts (Lua verified separately against Redis)."""

    def __init__(self):
        from arxiv_search.serving import budget
        self.budget = budget
        self.data = {}
        self.ttl = {}

    def command(self, parts):
        b = self.budget
        if parts[0] == "SET":
            _, key, value, nx, ex, seconds = parts
            if key in self.data:
                return None
            self.data[key], self.ttl[key] = value, seconds
            return "OK"
        script, keys, args = parts[1], parts[3:3 + parts[2]], parts[3 + parts[2]:]
        if script == b.TICKET_CONSUME_SCRIPT:
            if self.data.get(keys[0]) != args[0]:
                return 0
            self.data[keys[0]] = "consumed"
            return 1
        if script == b.VISITOR_SCRIPT:
            minute, day = (self.data.get(k, 0) for k in keys)
            if minute >= args[0]:
                return ["minute", 42]
            if day >= args[1]:
                return ["day", 3600]
            for key, ttl in zip(keys, (60, 86400)):
                self.data[key] = self.data.get(key, 0) + 1
                self.ttl.setdefault(key, ttl)
            return ["ok", 0]
        state = self.data.get(keys[0])
        if script == b.DAILY_STATUS_SCRIPT:
            if state is None:
                return ["status", 0, 0, 0, 0]
            return ["status", *(state[f] for f in ("searches", "tokens", "nanodollars", "calls"))]
        assert script == b.DAILY_RESERVE_SCRIPT
        if state is None:
            state = self.data[keys[0]] = {"policy": args[0], "searches": 0, "tokens": 0,
                                          "nanodollars": 0, "calls": 0}
            self.ttl[keys[0]] = args[9]
        if state["policy"] != args[0]:
            return ["policy_mismatch"]
        if args[1] in state:
            return ["duplicate"]
        new = (state["searches"] + args[2], state["tokens"] + args[3],
               state["nanodollars"] + args[4], state["calls"] + 1)
        if any(v > limit for v, limit in zip(new, args[5:9])):
            return ["exhausted"]
        state.update(dict(zip(("searches", "tokens", "nanodollars", "calls"), new)), **{args[1]: 1})
        return ["reserved", *new]


def test_daily_budget_creates_counters_caps_spend_and_rolls_over_at_utc_midnight():
    from arxiv_search.serving.budget import DailyBudget, production_budget
    redis = DailyRedis()
    now = [1_793_000_000.0]
    guard = DailyBudget(redis, namespace="production", clock=lambda: now[0])
    assert guard.policy.max_nanodollars == 5_000_000_000
    assert guard.status() == Usage(0, 0, 0, 0)
    assert guard.reserve("a", tokens=10, nanodollars=4_000_000_000, starts_search=True) == Usage(
        1, 10, 4_000_000_000, 1,
    )
    assert redis.ttl[guard.key] == 3 * 86400
    with pytest.raises(APIError, match="resets at midnight UTC") as error:
        guard.reserve("b", tokens=10, nanodollars=1_000_000_001)
    assert error.value.code == "budget_exhausted"
    with pytest.raises(APIError) as error:
        guard.reserve("a", tokens=1, nanodollars=1)
    assert error.value.code == "rate_limited"
    first_key = guard.key
    now[0] += 86400
    assert guard.key != first_key and guard.status() == Usage(0, 0, 0, 0)
    guard.reserve("b", tokens=10, nanodollars=1_000_000_001)
    preview = production_budget(redis, "preview")
    assert preview.policy.max_nanodollars == 1_000_000_000
    assert preview.prefix.startswith("arxiv:daily:preview:") and "production" in guard.prefix
    assert not any(k.startswith("arxiv:trial:") for k in redis.data)
    with pytest.raises(ValueError):
        production_budget(redis, "development")


def test_daily_budget_tickets_are_single_use_and_bound():
    from arxiv_search.serving.budget import DailyBudget
    redis = DailyRedis()
    guard = DailyBudget(redis, namespace="production")
    binding = "a" * 64
    token = guard.issue_summary(binding)
    stored = [k for k in redis.data if ":ticket:" in k]
    assert len(stored) == 1 and token not in stored[0] and redis.ttl[stored[0]] == 900
    with pytest.raises(APIError, match="invalid"):
        guard.consume_summary(token, "b" * 64)
    guard.consume_summary(token, binding)
    with pytest.raises(APIError, match="already used"):
        guard.consume_summary(token, binding)


def test_daily_budget_visitor_limits_and_retry_after():
    from arxiv_search.serving.budget import DailyBudget, DailyPolicy
    redis = DailyRedis()
    guard = DailyBudget(redis, namespace="production",
                        policy=DailyPolicy(searches_per_minute=2, searches_per_day=3),
                        clock=lambda: 1_793_000_000.0)
    visitor = "c" * 64
    guard.admit_visitor(visitor)
    guard.admit_visitor(visitor)
    with pytest.raises(APIError) as error:
        guard.admit_visitor(visitor)
    assert (error.value.code, error.value.status, error.value.retry_after) == ("rate_limited", 429, 42)
    guard.admit_visitor("d" * 64)
    with pytest.raises(ValueError):
        guard.admit_visitor("203.0.113.9")
    with pytest.raises(APIError) as error:
        DailyBudget(RedisStub(["weird"]), namespace="production").admit_visitor(visitor)
    assert error.value.code == "upstream_unavailable"


def test_paper_visitor_limits_are_separate_from_search():
    from arxiv_search.serving.budget import DailyBudget, VISITOR_LIMITS
    redis = DailyRedis()
    guard = DailyBudget(redis, namespace="production", clock=lambda: 1_793_000_000.0)
    visitor = "e" * 64
    for _ in range(VISITOR_LIMITS["paper_ask"][0]):
        guard.admit_visitor(visitor, "paper_ask")
    with pytest.raises(APIError, match="paper questions"):
        guard.admit_visitor(visitor, "paper_ask")
    guard.admit_visitor(visitor)
    guard.admit_visitor(visitor, "paper_open")
    with pytest.raises(ValueError):
        guard.admit_visitor(visitor, "other")
