import json

import pytest

from arxiv_search import paper_chat
from arxiv_search.paper_text import abstract_paper, select_context
from arxiv_search.serving.http import Application
from arxiv_search.serving.paper_live import LivePaperService
from arxiv_search.serving.service import APIError
from tests.test_serving_paper import Content, Transport, count

VISITOR = "a" * 64


class Redis:
    def __init__(self):
        self.data = {}

    def command(self, parts):
        if parts[0] == "GET":
            return self.data.get(parts[1])
        assert parts[0] == "SET" and parts[3:] == ["EX", 86400]
        self.data[parts[1]] = parts[2]
        return "OK"


class Budget:
    def __init__(self):
        self.reserved, self.admitted, self.error = [], [], None

    def reserve(self, attempt_id, *, tokens, nanodollars, starts_search=False):
        if self.error:
            raise self.error
        self.reserved.append((tokens, nanodollars, starts_search))

    def admit_visitor(self, visitor, kind="search"):
        self.admitted.append((visitor, kind))


@pytest.fixture
def live():
    loads = []

    def loader(paper_id):
        loads.append(paper_id)
        return select_context(abstract_paper(f"{paper_id}v2", "Paper title",
                                             "An abstract describing a method."), count)

    budget, transport, content = Budget(), Transport(), Content()
    service = LivePaperService(
        papers={"2510.12345"}, loader=loader, content=content, redis=Redis(),
        namespace="live-test", transport=transport, budget=budget, count_tokens=count,
    )
    return service, budget, transport, loads


def test_context_is_free_cached_and_discloses_coverage(live):
    service, budget, transport, loads = live
    first = service.context({"arxiv_id": "2510.12345"}, visitor=VISITOR)
    second = service.context({"arxiv_id": "2510.12345"}, visitor=VISITOR)
    assert first == second and loads == ["2510.12345"]
    assert first["paper"]["source"] == "abstract" and first["paper"]["version"] == 2
    assert first["paper"]["coverage"]["source"] == "abstract"
    assert not transport.calls and not budget.reserved
    assert budget.admitted == [(VISITOR, "paper_open")] * 2


def test_first_question_starts_conversation_with_one_reserved_call(live):
    service, budget, transport, loads = live
    result = service.ask({"arxiv_id": "2510.12345", "question": " What method? ", "history": []},
                         visitor=VISITOR)
    assert result["grounded"] is True and result["citations"][0]["id"] == "abstract"
    assert result["paper"]["arxiv_id"] == "2510.12345" and result["memory"]["retained_exchanges"] == 0
    assert len(transport.calls) == 1 and len(budget.reserved) == 1
    path, payload, timeout = transport.calls[0]
    assert path == "responses" and payload["model"] == paper_chat.MODEL
    assert json.loads(payload["input"])["question"] == "What method?"
    tokens, nanodollars, starts_search = budget.reserved[0]
    assert tokens > paper_chat.MAX_OUTPUT_TOKENS and nanodollars > 0 and starts_search is False
    assert budget.admitted == [(VISITOR, "paper_ask")]


def test_follow_up_sends_bounded_history(live):
    service, budget, transport, _ = live
    history = [{"user": "What method?", "assistant": "A method. [abstract]"}]
    result = service.ask({"arxiv_id": "2510.12345", "question": "And the data?", "history": history},
                         visitor=VISITOR)
    sent = json.loads(transport.calls[0][1]["input"])["history"]
    assert sent == history and result["memory"]["retained_exchanges"] == 1


@pytest.mark.parametrize("body", [
    {"arxiv_id": "2510.12345", "question": "", "history": []},
    {"arxiv_id": "2510.12345", "question": "x" * 501, "history": []},
    {"arxiv_id": "2510.12345", "question": "q", "history": [{"user": "q"}]},
    {"arxiv_id": "2510.12345", "question": "q", "history": [{"user": "q", "assistant": "a"}] * 11},
    {"arxiv_id": "2510.12345v2", "question": "q", "history": []},
    {"arxiv_id": "2510.12345", "question": "q"},
    {"arxiv_id": "2510.12345", "question": "q", "history": [], "extra": 1},
])
def test_invalid_requests_never_reserve_or_call(live, body):
    service, budget, transport, _ = live
    with pytest.raises(APIError) as error:
        service.ask(body, visitor=VISITOR)
    assert error.value.status == 400 and not budget.reserved and not transport.calls


def test_unknown_paper_is_rejected_before_any_fetch(live):
    service, budget, transport, loads = live
    with pytest.raises(APIError) as error:
        service.context({"arxiv_id": "2510.99999"}, visitor=VISITOR)
    assert error.value.status == 404 and not loads and not budget.admitted


def test_budget_exhaustion_blocks_the_model_call(live):
    service, budget, transport, _ = live
    budget.error = APIError("budget_exhausted", "Today's AI budget has been used.")
    with pytest.raises(APIError, match="budget"):
        service.ask({"arxiv_id": "2510.12345", "question": "q", "history": []}, visitor=VISITOR)
    assert not transport.calls


def test_invalid_model_citation_is_a_clear_error(live):
    service, budget, transport, _ = live
    transport.invalid = True
    with pytest.raises(APIError) as error:
        service.ask({"arxiv_id": "2510.12345", "question": "q", "history": []}, visitor=VISITOR)
    assert error.value.code == "model_invalid_answer" and error.value.status == 502


@pytest.mark.parametrize("model", ["gpt-6-luna-2027-01-01", "gpt-6-luna-mini", None])
def test_unexpected_model_identity_is_reported_separately(live, model, caplog):
    service, budget, transport, _ = live
    post = transport.post
    transport.post = lambda *a, **k: {**post(*a, **k), "model": model}
    with pytest.raises(APIError) as error:
        service.ask({"arxiv_id": "2510.12345", "question": "q", "history": []}, visitor=VISITOR)
    assert error.value.code == "model_identity_mismatch" and error.value.status == 502
    assert "identity mismatch" in caplog.text and len(budget.reserved) == 1


def test_http_routes_live_paper_operations_with_hashed_visitor(live):
    service, budget, _, _ = live

    class Search:
        paper = service

    app = Application(lambda: Search())
    raw = json.dumps({"arxiv_id": "2510.12345"}).encode()
    environ = {"PATH_INFO": "/api/paper/context", "REQUEST_METHOD": "POST",
               "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(raw)),
               "HTTP_X_REAL_IP": "203.0.113.7", "wsgi.input": __import__("io").BytesIO(raw)}
    statuses = []
    body = json.loads(b"".join(app(environ, lambda status, headers: statuses.append(status))))
    assert statuses == ["200 OK"] and body["paper"]["arxiv_id"] == "2510.12345"
    assert budget.admitted[0][0] != "203.0.113.7" and len(budget.admitted[0][0]) == 64

    class NoPaper:
        pass

    disabled = Application(lambda: NoPaper())
    environ["wsgi.input"] = __import__("io").BytesIO(raw)
    body = json.loads(b"".join(disabled(environ, lambda status, headers: statuses.append(status))))
    assert statuses[-1].startswith("503") and body["error"]["code"] == "budget_exhausted"
