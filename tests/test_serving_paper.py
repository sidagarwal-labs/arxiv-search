import copy
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from threading import Lock
from threading import Thread
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from arxiv_search import paper_chat
from arxiv_search.paper_text import abstract_paper, select_context
from arxiv_search.serving.http import Application
from arxiv_search.serving.paper_content import RedisContent
from arxiv_search.serving.paper_service import PaperService
from arxiv_search.serving.paper_state import Admission, PaperPolicy, RedisMetadata
from arxiv_search.serving.service import APIError


def count(text):
    return len(text.encode()) // 4 + 1


class Metadata:
    def __init__(self, value):
        self.value = value
        self.lock = Lock()

    def read(self):
        with self.lock:
            return self.value

    def compare_exchange(self, before, after):
        with self.lock:
            if self.value != before:
                return False
            self.value = after
            return True


class Content:
    def __init__(self):
        self.contexts = {}

    def put(self, context):
        identity = paper_chat.cache_key(context)
        self.contexts[identity] = context
        return identity

    def get(self, identity):
        return self.contexts.get(identity)


class Transport:
    def __init__(self):
        self.calls = []
        self.error = None
        self.invalid = False

    def post(self, path, payload, *, timeout):
        self.calls.append((path, payload, timeout))
        if self.error:
            raise self.error
        overview = "suggested_questions" in payload["text"]["format"]["schema"]["properties"]
        value = {"answer": "The abstract describes a method. [abstract]", "grounded": True}
        if overview:
            value["suggested_questions"] = ["What method?", "What evidence?", "What is missing?"]
        if self.invalid:
            value["answer"] = "Unsupported locator [S999]"
        return {"model": paper_chat.MODEL, "status": "completed", "output": [
            {"type": "message", "phase": "commentary", "content": [
                {"type": "output_text", "text": "Draft must not be used."}]},
            {"type": "message", "phase": "final_answer", "content": [
                {"type": "output_text", "text": json.dumps(value)}]},
        ]}


@pytest.fixture
def fixture():
    policy = PaperPolicy("offline-only", 100, 100, 1000, 10_000_000, 10_000_000_000)
    metadata = Metadata(policy.initial_state())
    context = select_context(abstract_paper("2510.12345v2", "Paper title",
                                           "An abstract describing a method."), count)
    content = Content()
    transport = Transport()
    clock = [1000]
    service = PaperService(
        admission=Admission(metadata, policy), content=content, loader=lambda _: context,
        transport=transport, count_tokens=count, signing_key=b"x" * 32, clock=lambda: clock[0],
    )
    return service, metadata, content, transport, clock


def prepare(service, rid="preparation_request_001"):
    return service.prepare({"arxiv_id": "2510.12345", "request_id": rid})


def opened(service):
    prepared = prepare(service)
    return service.open({"preparation": prepared["preparation"], "request_id": "opening_request_0001"})


def history(result):
    overview = result["overview"]
    return [{"role": "assistant", "content": overview["text"], "sig": overview["assistant_sig"],
             "turn_index": overview["turn_index"]}]


def follow(service, result, messages, rid="followup_request_001", question="What method?"):
    return service.chat({"session": result["session"], "request_id": rid,
                         "messages": messages, "question": question})


def usage(metadata):
    return json.loads(metadata.value)["usage"]


def test_prepare_requires_consent_without_model_or_session(fixture):
    service, metadata, _, transport, _ = fixture
    result = prepare(service)
    assert result["consent_required"] is True
    assert result["paper"]["source"] == "abstract"
    assert result["paper"]["version"] == 2
    assert result["paper"]["coverage"]["figures"] == "not_available"
    assert result["limits"] == {"expires_at": 1600}
    assert result["overview_cache"] == "unavailable"
    assert not transport.calls
    assert usage(metadata) == dict(preparations=1, sessions=0, calls=0, tokens=0, nanodollars=0)


def test_open_and_chat_use_isolated_admission_and_signed_baseline(fixture):
    service, metadata, _, transport, _ = fixture
    result = opened(service)
    assert result["limits"]["turns_left"] == 10
    response = follow(service, result, history(result))
    assert response["turn_index"] == 1
    assert response["limits"]["turns_left"] == 9
    assert response["memory"] == {"truncated": False, "retained_exchanges": 0}
    assert usage(metadata)["calls"] == 2
    payload = transport.calls[-1][1]
    assert payload["model"] == "gpt-6-luna"
    assert payload["instructions"] == paper_chat.SYSTEM
    assert payload["max_output_tokens"] == 1200
    assert json.loads(payload["input"])["history_baseline"] == result["overview"]["text"]
    assert payload["text"]["format"]["name"] == "paper_chat"
    assert "abstract describes" not in metadata.value
    assert "What method?" not in metadata.value


@pytest.mark.parametrize("operation", ["prepare", "open", "chat"])
def test_duplicate_completed_never_reexecutes(fixture, operation):
    service, metadata, _, transport, _ = fixture
    if operation == "prepare":
        prepare(service)
        call = lambda: prepare(service)
    else:
        p = prepare(service)
        request = {"preparation": p["preparation"], "request_id": "opening_request_0001"}
        result = service.open(request)
        if operation == "open":
            call = lambda: service.open(request)
        else:
            follow(service, result, history(result))
            call = lambda: follow(service, result, history(result))
    before = metadata.value
    calls = len(transport.calls)
    with pytest.raises(APIError) as error:
        call()
    assert error.value.code == "already_completed"
    assert len(transport.calls) == calls
    assert metadata.value == before


def test_preparation_one_session_even_with_new_request_id(fixture):
    service, _, _, transport, _ = fixture
    p = prepare(service)
    service.open({"preparation": p["preparation"], "request_id": "opening_request_0001"})
    with pytest.raises(APIError, match="already used"):
        service.open({"preparation": p["preparation"], "request_id": "opening_request_0002"})
    assert len(transport.calls) == 1


def test_missing_context_does_not_refetch_or_debit_open(fixture):
    service, metadata, content, transport, _ = fixture
    p = prepare(service)
    content.contexts.clear()
    with pytest.raises(APIError) as error:
        service.open({"preparation": p["preparation"], "request_id": "opening_request_0001"})
    assert error.value.code == "preparation_expired"
    assert usage(metadata)["sessions"] == 0
    assert not transport.calls


@pytest.mark.parametrize("mutation", ["content", "signature", "missing", "user", "index", "fork"])
def test_history_tampering_never_debits(fixture, mutation):
    service, metadata, _, transport, _ = fixture
    result = opened(service)
    messages = history(result)
    response = follow(service, result, messages)
    full = messages + [{"role": "user", "content": "What method?"},
                       {"role": "assistant", "content": response["answer"],
                        "sig": response["assistant_sig"], "turn_index": response["turn_index"]}]
    if mutation == "content":
        full[-1]["content"] = "Changed answer"
    elif mutation == "signature":
        full[-1]["sig"] = "0" * 64
    elif mutation == "missing":
        full = full[2:]
    elif mutation == "user":
        full[1]["content"] = "A different question"
    elif mutation == "index":
        full[-1]["turn_index"] = 0
    else:
        full = messages
    before = metadata.value
    with pytest.raises(APIError) as error:
        follow(service, result, full, rid="followup_request_002")
    assert error.value.code == "invalid_history"
    assert metadata.value == before
    assert len(transport.calls) == 2


def test_unknown_provider_outcome_is_sticky_and_never_retried(fixture):
    service, metadata, _, transport, clock = fixture
    result = opened(service)
    transport.error = APIError("upstream_timeout", "Unknown outcome.", 504)
    with pytest.raises(APIError):
        follow(service, result, history(result))
    assert usage(metadata)["calls"] == 2
    for advance in (0, 100):
        clock[0] += advance
        with pytest.raises(APIError) as error:
            follow(service, result, history(result))
        assert error.value.code == "outcome_unknown"
        with pytest.raises(APIError) as error:
            follow(service, result, history(result), rid="followup_request_002")
        assert error.value.code == "session_busy"
    assert len(transport.calls) == 2


def test_crash_marker_changes_from_inflight_to_unknown_without_readmission(fixture):
    service, metadata, _, transport, clock = fixture
    result = opened(service)
    transport.error = RuntimeError("Simulated worker crash")
    with pytest.raises(RuntimeError):
        follow(service, result, history(result))
    with pytest.raises(APIError) as error:
        follow(service, result, history(result))
    assert error.value.code == "session_busy"
    clock[0] += 46
    with pytest.raises(APIError) as error:
        follow(service, result, history(result))
    assert error.value.code == "outcome_unknown"
    with pytest.raises(APIError) as error:
        follow(service, result, history(result), rid="followup_request_002")
    assert error.value.code == "session_busy"
    assert usage(metadata)["calls"] == 2
    assert len(transport.calls) == 2


def test_shared_open_deadline_exhausted_before_admission_never_debits(fixture):
    service, metadata, content, transport, clock = fixture
    p = prepare(service)
    original = content.get

    def slow_get(identity):
        clock[0] += 46
        return original(identity)

    content.get = slow_get
    with pytest.raises(APIError) as error:
        service.open({"preparation": p["preparation"], "request_id": "opening_request_0001"})
    assert error.value.code == "upstream_timeout"
    assert usage(metadata)["calls"] == 0
    assert usage(metadata)["sessions"] == 0
    assert not transport.calls


def test_invalid_answer_consumes_turn_but_allows_next_explicit_question(fixture):
    service, metadata, _, transport, _ = fixture
    result = opened(service)
    transport.invalid = True
    with pytest.raises(APIError) as error:
        follow(service, result, history(result))
    assert error.value.code == "model_invalid_answer"
    assert error.value.limits["turns_left"] == 9
    transport.invalid = False
    response = follow(service, result, history(result), rid="followup_request_002")
    assert response["turn_index"] == 2
    assert response["limits"]["turns_left"] == 8
    assert usage(metadata)["calls"] == 3


def test_ten_followups_and_whole_history_verification_before_memory_selection(fixture):
    service, metadata, _, transport, _ = fixture
    result = opened(service)
    messages = history(result)
    for index in range(1, 11):
        reply = follow(service, result, messages, rid=f"followup_request_{index:03}")
        assert reply["limits"]["turns_left"] == 10 - index
        messages.extend([{"role": "user", "content": "What method?"},
                         {"role": "assistant", "content": reply["answer"],
                          "sig": reply["assistant_sig"], "turn_index": reply["turn_index"]}])
    assert reply["memory"] == {"truncated": True, "retained_exchanges": 6}
    with pytest.raises(APIError) as error:
        follow(service, result, messages, rid="followup_request_011")
    assert error.value.code == "turn_limit"
    assert len(transport.calls) == 11
    assert usage(metadata)["calls"] == 11


@pytest.mark.parametrize("question", ["", " " * 3, "a" * 501, None, 123])
def test_invalid_questions_do_not_admit(fixture, question):
    service, metadata, _, _, _ = fixture
    result = opened(service)
    before = metadata.value
    with pytest.raises(APIError):
        follow(service, result, history(result), question=question)
    assert metadata.value == before


def test_expiry_and_token_tampering(fixture):
    service, _, _, _, clock = fixture
    result = opened(service)
    changed = copy.deepcopy(result)
    changed["session"] = result["session"][:-1] + ("0" if result["session"][-1] != "0" else "1")
    with pytest.raises(APIError) as error:
        follow(service, changed, history(result))
    assert error.value.code == "bad_request"
    clock[0] += 1801
    with pytest.raises(APIError) as error:
        follow(service, result, history(result))
    assert error.value.code == "session_expired"


def test_concurrent_chats_only_one_provider_attempt(fixture):
    service, metadata, _, transport, _ = fixture
    result = opened(service)
    messages = history(result)

    def attempt(index):
        try:
            return follow(service, result, messages, rid=f"followup_request_{index:03}")["turn_index"]
        except APIError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(attempt, range(8)))
    assert responses.count(1) == 1
    assert set(responses) <= {1, "session_busy", "invalid_history"}
    assert len(transport.calls) == 2
    assert usage(metadata)["calls"] == 2


def test_budget_denial_is_atomic_before_session_or_provider(fixture):
    service, metadata, _, transport, _ = fixture
    p = prepare(service)
    state = json.loads(metadata.value)
    state["usage"]["calls"] = service.admission.policy.calls
    metadata.value = json.dumps(state)
    before = metadata.value
    with pytest.raises(APIError) as error:
        service.open({"preparation": p["preparation"], "request_id": "opening_request_0001"})
    assert error.value.code == "budget_exhausted"
    assert metadata.value == before
    assert not transport.calls


def test_cache_hit_revalidated_admits_session_without_model_cost(fixture):
    service, metadata, _, transport, _ = fixture

    class Cache:
        def get(self, identity):
            return {"answer": "Cached overview [abstract]", "grounded": True,
                    "suggested_questions": ["A?", "B?", "C?"]}

    service.cache = Cache()
    result = opened(service)
    assert result["cache"]["overview"] == "hit"
    assert usage(metadata)["sessions"] == 1
    assert usage(metadata)["calls"] == 0
    assert not transport.calls


def test_invalid_cached_overview_never_creates_session(fixture):
    service, metadata, _, transport, _ = fixture

    class Cache:
        def get(self, identity):
            return {"answer": "Invalid [S999]", "grounded": True,
                    "suggested_questions": ["A?", "B?", "C?"]}

    p = prepare(service)
    service.cache = Cache()
    before = metadata.value
    with pytest.raises(APIError) as error:
        service.open({"preparation": p["preparation"], "request_id": "opening_request_0001"})
    assert error.value.code == "model_invalid_answer"
    assert before == metadata.value
    assert not transport.calls


def test_preparation_rate_limit_is_separate_from_provider_and_session_quota(fixture):
    service, metadata, _, transport, clock = fixture
    for index in range(5):
        prepare(service, rid=f"preparation_request_{index:03}")
    before = metadata.value
    with pytest.raises(APIError) as error:
        prepare(service, rid="preparation_request_006")
    assert error.value.code == "rate_limited"
    assert error.value.retry_after == 60
    assert metadata.value == before
    assert not transport.calls
    clock[0] += 60
    prepare(service, rid="preparation_request_006")
    assert usage(metadata)["preparations"] == 6


def test_known_prepare_failure_is_terminal_and_new_prepare_is_explicit(fixture):
    service, metadata, _, transport, _ = fixture
    original = service.loader

    def failed(_):
        raise APIError("upstream_timeout", "Paper preparation timed out.", 504)

    service.loader = failed
    with pytest.raises(APIError) as error:
        prepare(service)
    assert error.value.code == "upstream_timeout"
    with pytest.raises(APIError) as error:
        prepare(service)
    assert error.value.code == "already_completed"
    service.loader = original
    result = prepare(service, rid="preparation_request_002")
    assert result["consent_required"] is True
    assert usage(metadata)["preparations"] == 2
    assert usage(metadata)["sessions"] == 0
    assert not transport.calls


def test_metadata_capacity_fails_before_provider_or_partial_charge(fixture):
    service, metadata, _, transport, _ = fixture
    p = prepare(service)
    state = json.loads(metadata.value)
    state["preparations"]["padding"] = {"created": 0, "id": "0" * 48,
                                        "padding": "x" * 48_000}
    metadata.value = json.dumps(state)
    before = metadata.value
    with pytest.raises(APIError) as error:
        service.open({"preparation": p["preparation"], "request_id": "opening_request_0001"})
    assert error.value.code == "budget_exhausted"
    assert metadata.value == before
    assert not transport.calls


def test_real_o200k_payload_and_full_output_reservation_are_accounted(fixture):
    import tiktoken

    service, metadata, _, transport, _ = fixture
    encoding = tiktoken.get_encoding("o200k_base")
    service.count_tokens = lambda text: len(encoding.encode(text, disallowed_special=()))
    result = opened(service)
    follow(service, result, history(result))
    expected_tokens = 0
    expected_cost = 0
    for _, payload, _ in transport.calls:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        reserved = paper_chat.reservation(encoded, service.count_tokens)
        input_count = service.count_tokens(encoded.decode()) + 4096
        assert reserved["input_tokens"] == input_count <= 32000
        assert reserved["output_tokens"] == 1200
        assert reserved["total_tokens"] == input_count + 1200 <= 33200
        assert reserved["nanodollars"] == input_count * 100 + 1200 * 500
        expected_tokens += reserved["total_tokens"]
        expected_cost += reserved["nanodollars"]
    assert usage(metadata)["tokens"] == expected_tokens
    assert usage(metadata)["nanodollars"] == expected_cost


def test_signed_overview_and_history_share_three_thousand_token_memory_budget(fixture):
    service, _, _, _, _ = fixture
    context = service.loader("2510.12345")
    exchanges = tuple(paper_chat.Exchange("q" * 500, "word " * 100) for _ in range(6))
    baseline = ("b" * 30 + " ") * 250
    encoded, memory = service._encode_chat(context, "Explain the overview", exchanges, baseline)
    body = json.loads(json.loads(encoded)["input"])
    combined = {"baseline": body["history_baseline"], "exchanges": body["history"]}
    assert service.count_tokens(json.dumps(combined, ensure_ascii=False)) <= 3000
    assert 0 < len(memory.exchanges) < 6
    assert memory.truncated is True
    assert body["history_baseline"] == baseline
    assert service.count_tokens(encoded.decode()) + 4096 <= 32000


class Redis:
    def __init__(self):
        self.values = {}
        self.commands = []

    def command(self, parts):
        self.commands.append(parts)
        if parts[0] == "GET":
            return self.values.get(parts[1])
        if parts[0] == "SET":
            self.values[parts[1]] = parts[2]
            return "OK"
        raise AssertionError(parts[0])


def test_durable_content_roundtrip_and_context_change(fixture):
    service, _, _, _, _ = fixture
    context = service.loader("2510.12345")
    redis = Redis()
    content = RedisContent(redis, "paper:offline-fixture")
    identity = content.put(context)
    assert content.get(identity) == context
    assert redis.commands[0][-2:] == ["EX", 86400]
    key = redis.commands[0][1]
    redis.values[key] = redis.values[key].replace("An abstract", "Changed abstract")
    with pytest.raises(APIError) as error:
        content.get(identity)
    assert error.value.code == "context_changed"


def test_missing_metadata_never_provisions_or_uses_search_namespace():
    redis = Redis()
    metadata = RedisMetadata(redis, "paper:offline-fixture")
    with pytest.raises(APIError):
        metadata.read()
    assert redis.commands == [["GET", "arxiv:paper:offline-fixture"]]
    with pytest.raises(ValueError):
        RedisMetadata(redis, "arxiv-e2e-2026-11-04-v3")


def http_call(app, path, body):
    encoded = json.dumps(body).encode()
    status = []
    data = app({"PATH_INFO": path, "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(encoded)),
                "wsgi.input": io.BytesIO(encoded)}, lambda value, _: status.append(value))
    return status[0], json.loads(b"".join(data))


def test_http_disabled_by_default_does_not_load_search_service():
    def forbidden():
        raise AssertionError("Search factory must not run")

    app = Application(forbidden)
    for operation in ("prepare", "open", "chat"):
        status, result = http_call(app, "/api/paper/" + operation, {})
        assert status.startswith("503")
        assert result["error"]["code"] == "budget_exhausted"


def test_http_injected_offline_adapter_and_error_limits(fixture):
    service, _, _, _, _ = fixture
    app = Application(lambda: None, paper_service=service)
    status, result = http_call(app, "/api/paper/prepare", {
        "arxiv_id": "2510.12345", "request_id": "preparation_request_001",
    })
    assert status.startswith("200")
    assert result["consent_required"] is True
    assert result["paper"]["source"] == "abstract"


def test_frontend_controller_against_actual_local_wsgi_contract(fixture):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the frontend/server contract test")
    service, metadata, _, transport, clock = fixture
    # Use current epoch seconds, matching browser expiry checks.
    import time
    clock[0] = time.time()
    app = Application(lambda: None, paper_service=service)

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            pass

    server = make_server("127.0.0.1", 0, app, handler_class=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = dict(os.environ, PAPER_TEST_BASE_URL=f"http://127.0.0.1:{server.server_port}")
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [node, "--experimental-default-type=module", "--test",
             str(root / "web" / "paper-integration.test.mjs")],
            cwd=root, env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert usage(metadata)["preparations"] == 1
        assert usage(metadata)["sessions"] == 1
        assert usage(metadata)["calls"] == 3
        assert len(transport.calls) == 3
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
