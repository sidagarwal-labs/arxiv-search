"""Operator-run Redis integration check using isolated non-billable test namespaces."""

from concurrent.futures import ThreadPoolExecutor
import uuid

from arxiv_search.serving.budget import RedisREST, TrialBudget, TrialPolicy, Usage, approved_trial
from arxiv_search.serving.service import APIError


def verify() -> dict:
    redis = RedisREST.from_environment()
    namespace = "verification:" + uuid.uuid4().hex

    def guard(suffix, **limits):
        budget = TrialBudget(redis, trial_id=f"{namespace}:{suffix}", policy=TrialPolicy(**limits))
        budget.provision()
        return budget

    current_policy = approved_trial(redis, "protected-trial-v3").policy
    concurrent = guard("concurrent", **current_policy.__dict__)

    def attempt(index):
        try:
            concurrent.reserve(f"attempt-{index}", tokens=1, nanodollars=1, starts_search=True)
            return "reserved"
        except APIError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(attempt, range(12)))
    if outcomes.count("reserved") != 2 or outcomes.count("budget_exhausted") != 10:
        raise RuntimeError("Concurrent search cap was not enforced")
    if concurrent.status() != Usage(2, 2, 2, 2):
        raise RuntimeError("Concurrent counters differ from successful reservations")
    for suffix, tokens, cost, limits in (
        ("tokens", 200_000, 1, {"max_tokens": 200_000}),
        ("cost", 1, 500_000_000, {}),
        ("calls", 1, 1, {"max_calls": 1}),
    ):
        budget = guard(suffix, **limits)
        budget.reserve("first", tokens=tokens, nanodollars=cost)
        try:
            budget.reserve("overflow", tokens=1, nanodollars=1)
        except APIError as error:
            if error.code != "budget_exhausted":
                raise
        else:
            raise RuntimeError(f"{suffix} limit was not enforced")
    duplicate = guard("duplicate")
    duplicate.reserve("same-attempt", tokens=10, nanodollars=100)
    try:
        duplicate.reserve("same-attempt", tokens=10, nanodollars=100)
    except APIError as error:
        if error.code != "rate_limited":
            raise
    else:
        raise RuntimeError("Duplicate reservation was accepted")
    if duplicate.status() != Usage(0, 10, 100, 1):
        raise RuntimeError("Duplicate changed counters")
    missing = TrialBudget(redis, trial_id=f"{namespace}:missing")
    try:
        missing.reserve("first", tokens=1, nanodollars=1)
    except APIError as error:
        if error.code != "upstream_unavailable":
            raise
    else:
        raise RuntimeError("Missing state must fail closed")
    call_budget = guard("twelve-calls", **current_policy.__dict__)
    for index in range(12):
        call_budget.reserve(f"call-{index}", tokens=1, nanodollars=1)
    try:
        call_budget.reserve("thirteenth", tokens=1, nanodollars=1)
    except APIError as error:
        if error.code != "budget_exhausted":
            raise
    else:
        raise RuntimeError("The second trial's twelve-call cap was not enforced")
    tickets = guard("tickets", **current_policy.__dict__)
    binding = "a" * 64
    token = tickets.issue_summary(binding)
    try:
        tickets.consume_summary(token, "b" * 64)
    except APIError as error:
        if error.code != "bad_request":
            raise
    else:
        raise RuntimeError("A mismatched summary binding was accepted")

    def consume(index):
        try:
            tickets.consume_summary(token, binding)
            return "consumed"
        except APIError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        ticket_outcomes = list(pool.map(consume, range(12)))
    if ticket_outcomes.count("consumed") != 1 or ticket_outcomes.count("bad_request") != 11:
        raise RuntimeError("Summary ticket was not single-use under concurrency")
    if tickets.status() != Usage(0, 0, 0, 0):
        raise RuntimeError("Ticket verification changed model usage counters")
    return {
        "redis": "verified", "concurrent_attempts": 12, "accepted_searches": 2,
        "blocked_searches": 10, "token_cap": "passed", "cost_cap": "passed",
        "call_cap": "passed", "duplicate_attempt": "blocked",
        "missing_state": "blocked", "model_calls": 0, "real_trial_reservations": 0,
        "summary_binding": "verified", "summary_ticket_accepted": 1,
        "summary_ticket_replays_blocked": 11,
        "approved_policy": current_policy.__dict__,
    }
