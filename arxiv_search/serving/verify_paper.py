"""Explicit operator-only Redis checks. Never exported into the public runtime."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import secrets
from threading import Lock
import time
import uuid

from arxiv_search import paper_chat
from arxiv_search.paper_text import abstract_paper, select_context
from arxiv_search.serving.budget import RedisCommands
from arxiv_search.serving.paper_content import RedisContent
from arxiv_search.serving.paper_service import PaperService
from arxiv_search.serving.paper_state import Admission, PaperPolicy, RedisMetadata
from arxiv_search.serving.service import APIError


def verify(redis: RedisCommands) -> dict:
    namespace = "paper:verification:" + uuid.uuid4().hex
    metadata = RedisMetadata(redis, namespace)
    content = RedisContent(redis, namespace)
    context = select_context(
        abstract_paper("2510.12345v1", "Synthetic infrastructure fixture",
                       "This synthetic abstract is only a Redis infrastructure fixture."),
        lambda text: len(text),
    )
    identity = paper_chat.cache_key(context)
    context_key = content.prefix + identity
    policy = PaperPolicy("isolated-verification", 20, 2, 20, 1_000_000, 1_000_000_000)
    keys = [metadata.key, context_key]
    trial_keys = [f"arxiv:trial:arxiv-e2e-2026-11-04-v{n}" for n in (1, 2, 3)]

    def snapshots() -> list[str]:
        values = [redis.command(["HGETALL", key]) for key in trial_keys]
        normalized = []
        for value in values:
            if isinstance(value, list) and len(value) % 2 == 0:
                value = dict(zip(value[::2], value[1::2]))
            if not isinstance(value, dict):
                raise RuntimeError("Search ledger snapshot had an unexpected shape")
            normalized.append(hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest())
        return normalized

    def expect(code, operation):
        try:
            operation()
        except APIError as error:
            if error.code == code:
                return
            raise RuntimeError(f"Expected {code}, received {error.code}") from None
        raise RuntimeError(f"Expected {code} was not raised")

    before = snapshots()
    initial = policy.initial_state()
    if redis.command(["SET", metadata.key, initial, "NX", "EX", 600]) != "OK":
        raise RuntimeError("Isolated verification namespace was not fresh")
    try:
        if redis.command(["SET", metadata.key, initial, "NX", "EX", 600]) is not None:
            raise RuntimeError("Operator provisioning overwrote an existing namespace")
        counters = {"fake_attempts": 0}
        lock = Lock()

        class FakeProvider:
            def post(self, path, payload, *, timeout):
                with lock:
                    counters["fake_attempts"] += 1
                value = {"answer": "Synthetic fixture only. [abstract]", "grounded": True}
                if "suggested_questions" in payload["text"]["format"]["schema"]["properties"]:
                    value["suggested_questions"] = ["What is this?", "Why synthetic?", "What is absent?"]
                return {"model": paper_chat.MODEL, "status": "completed", "output": [{
                    "type": "message", "phase": "final_answer",
                    "content": [{"type": "output_text", "text": json.dumps(value)}],
                }]}

        clock = [time.time()]
        service = PaperService(
            admission=Admission(metadata, policy), content=content, loader=lambda _: context,
            transport=FakeProvider(), count_tokens=lambda text: len(text),
            signing_key=secrets.token_bytes(32), clock=lambda: clock[0],
        )
        prepared = service.prepare({
            "arxiv_id": "2510.12345", "request_id": "verification_prepare_0001",
        })
        if counters["fake_attempts"] != 0 or content.get(identity) != context:
            raise RuntimeError("Prepare failed durable roundtrip or invoked the fake model")
        if not 0 < redis.command(["TTL", metadata.key]) <= 600:
            raise RuntimeError("Compare/exchange dropped temporary namespace expiry")
        opening = {"preparation": prepared["preparation"], "request_id": "verification_open_00001"}

        def open_attempt(_):
            try:
                return service.open(opening)
            except APIError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=4) as pool:
            openings = list(pool.map(open_attempt, range(4)))
        successes = [value for value in openings if isinstance(value, dict)]
        if len(successes) != 1 or counters["fake_attempts"] != 1:
            raise RuntimeError("Concurrent duplicate opening admitted more than one operation")
        result = successes[0]
        overview = result["overview"]
        messages = [{"role": "assistant", "content": overview["text"],
                     "sig": overview["assistant_sig"], "turn_index": 0}]
        request = {"session": result["session"], "request_id": "verification_chat_00001",
                   "messages": messages, "question": "What is this?"}

        def chat_attempt(_):
            try:
                return service.chat(request)
            except APIError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=4) as pool:
            replies = list(pool.map(chat_attempt, range(4)))
        successes = [value for value in replies if isinstance(value, dict)]
        if len(successes) != 1 or counters["fake_attempts"] != 2:
            raise RuntimeError("Concurrent duplicate follow-up admitted more than one operation")
        reply = successes[0]
        if reply["limits"]["turns_left"] != 9:
            raise RuntimeError("Durable turn accounting did not decrement exactly once")
        expect("already_completed", lambda: service.chat(request))
        expect("invalid_history", lambda: service.chat({
            **request, "request_id": "verification_chat_00002",
        }))
        state = metadata.read()
        if overview["text"] in state or request["question"] in state:
            raise RuntimeError("Conversation text leaked into metadata")
        clock[0] += 1801
        expect("session_expired", lambda: service.chat({
            **request, "request_id": "verification_chat_00003",
        }))
        # Actual Redis expiry of prepared content, not a local clock simulation.
        if redis.command(["EXPIRE", context_key, 1]) != 1:
            raise RuntimeError("Content TTL could not be set")
        time.sleep(1.2)
        if content.get(identity) is not None:
            raise RuntimeError("Redis context did not expire")
        if before != snapshots():
            raise RuntimeError("Existing search ledger snapshots changed during verification")
        outcome = {
            "redis": "verified", "content_roundtrip": "passed", "content_expiry": "passed",
            "metadata_ttl_preserved": "passed", "duplicate_open": "blocked",
            "duplicate_followup": "blocked", "turn_accounting": "passed",
            "history_replay": "blocked", "session_expiry": "passed",
            "transcript_in_metadata": False, "fake_provider_attempts": counters["fake_attempts"],
            "real_provider_calls": 0, "search_ledgers_unchanged": True,
        }
    finally:
        redis.command(["DEL", *keys])
        if any(redis.command(["EXISTS", key]) != 0 for key in keys):
            raise RuntimeError("Isolated verification cleanup failed")
    return {**outcome, "temporary_keys_removed": True}
