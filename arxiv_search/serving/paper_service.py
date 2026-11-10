"""Offline-wirable paper operations. No environment activation or search-budget reuse."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from collections.abc import Callable
from typing import Protocol

from arxiv_search import paper_chat
from arxiv_search.paper_text import Context
from arxiv_search.serving.paper_content import ContentStore
from arxiv_search.serving.paper_state import Admission, canonical
from arxiv_search.serving.service import APIError


class PaperError(APIError):
    def __init__(self, code: str, message: str, status: int, limits: dict | None = None):
        super().__init__(code, message, status)
        self.limits = limits


class PaperTransport(Protocol):
    def post(self, path: str, payload: dict, *, timeout: float) -> dict: ...


class OverviewCache(Protocol):
    def get(self, identity: str) -> object | None: ...


def request_id(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", value):
        raise PaperError("bad_request", "A valid request_id is required.", 400)
    return hashlib.sha256(value.encode()).hexdigest()


def fields(body: dict, expected: set[str]) -> None:
    if set(body) != expected:
        raise PaperError("bad_request", "Unexpected or missing paper request fields.", 400)


class PaperService:
    def __init__(self, *, admission: Admission, content: ContentStore,
                 loader: Callable[[str], Context], transport: PaperTransport,
                 count_tokens: Callable[[str], int], signing_key: bytes,
                 cache: OverviewCache | None = None, clock: Callable[[], float] = time.time):
        if not isinstance(signing_key, bytes) or len(signing_key) < 32:
            raise ValueError("A separate paper signing key of at least 32 bytes is required")
        self.admission, self.content, self.loader = admission, content, loader
        self.transport, self.count_tokens, self.key = transport, count_tokens, signing_key
        self.cache, self.clock = cache, clock

    def _sign(self, value: object) -> str:
        return hmac.new(self.key, canonical(value).encode(), hashlib.sha256).hexdigest()

    def _token(self, kind: str, identity: str, expires: int) -> str:
        value = canonical({"kind": kind, "id": identity, "exp": expires,
                           "policy": self.admission.policy.digest})
        encoded = base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
        return encoded + "." + self._sign(value)

    def _identity(self, token: object, kind: str) -> str:
        try:
            if not isinstance(token, str) or len(token) > 1024:
                raise ValueError("Invalid token")
            encoded, signature = token.split(".")
            text = base64.b64decode(encoded + "=" * (-len(encoded) % 4),
                                    altchars=b"-_", validate=True).decode()
            if not hmac.compare_digest(signature, self._sign(text)):
                raise ValueError("Invalid signature")
            value = json.loads(text)
            if (set(value) != {"kind", "id", "exp", "policy"} or value["kind"] != kind
                    or value["policy"] != self.admission.policy.digest
                    or not re.fullmatch(r"[0-9a-f]{48}", value["id"])
                    or type(value["exp"]) is not int):
                raise ValueError("Invalid token binding")
            if value["exp"] <= self.clock():
                raise PaperError("preparation_expired" if kind == "prepare" else "session_expired",
                                 "This paper preparation or session expired.", 401)
            return value["id"]
        except (ValueError, TypeError, UnicodeError, KeyError):
            raise PaperError("bad_request", "Invalid paper token.", 400) from None

    @staticmethod
    def paper(context: Context) -> dict:
        paper_id, version = context.paper.versioned_id.rsplit("v", 1)
        return {
            "arxiv_id": paper_id, "version": int(version), "title": context.paper.title,
            "source": context.paper.source, "coverage": context.coverage(),
            "outline": [{"id": s.id, "label": s.label, "title": s.title, "href": s.href}
                        for s in context.included],
        }

    def _context(self, identity: str, *, preparation: bool = False) -> Context:
        value = self.content.get(identity)
        if value is None:
            raise PaperError("preparation_expired" if preparation else "context_changed",
                             "Prepared text is unavailable. Prepare the paper again.", 409)
        if paper_chat.cache_key(value) != identity:
            raise PaperError("context_changed", "Prepared text changed. Prepare it again.", 409)
        return value

    def _cached(self, identity: str, context: Context) -> tuple[str, dict | None]:
        if self.cache is None:
            return "unavailable", None
        value = self.cache.get(identity)
        if value is None:
            return "miss", None
        try:
            return "hit", paper_chat.validate(value, context, overview=True)
        except ValueError:
            raise PaperError("model_invalid_answer", "Cached overview failed validation.", 502) from None

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise PaperError("upstream_timeout", "Paper request deadline exceeded.", 504)
        return remaining

    def prepare(self, body: dict) -> dict:
        fields(body, {"arxiv_id", "request_id"})
        rid = request_id(body["request_id"])
        paper_id = body["arxiv_id"]
        if not isinstance(paper_id, str) or not re.fullmatch(r"\d{4}\.\d{4,5}", paper_id):
            raise PaperError("bad_request", "Use an unversioned corpus paper ID.", 400)
        now = int(self.clock())
        deadline = self.clock() + 45
        pid = secrets.token_hex(24)

        def claim(state: dict) -> None:
            previous = state["preparations"].get(rid)
            if previous:
                if previous["paper"] != paper_id:
                    raise PaperError("bad_request", "request_id was used for another paper.", 400)
                self._duplicate(previous["status"], previous["created"] + 45)
            recent = [p for p in state["preparations"].values()
                      if p["created"] > now - self.admission.policy.preparation_window_seconds]
            if len(recent) >= self.admission.policy.preparations_per_window:
                error = PaperError("rate_limited", "Paper preparation is rate-limited.", 429)
                error.retry_after = self.admission.policy.preparation_window_seconds
                raise error
            self.admission.charge(state, preparations=1)
            state["preparations"][rid] = {
                "id": pid, "paper": paper_id, "status": "pending", "created": now,
                "expires": now + 600,
            }

        self.admission.update(claim)
        try:
            context = self.loader(paper_id)
            self._remaining(deadline)
        except APIError:
            def failed(state: dict) -> None:
                state["preparations"][rid]["status"] = "done"
            self.admission.update(failed)
            raise
        if context.paper.versioned_id.rsplit("v", 1)[0] != paper_id:
            raise PaperError("context_changed", "Resolved paper does not match the request.", 409)
        identity = self.content.put(context)
        cache_status, _ = self._cached(identity, context)

        def finish(state: dict) -> None:
            self._remaining(deadline)
            preparation = state["preparations"][rid]
            if preparation["expires"] <= self.clock():
                raise PaperError("preparation_expired", "Preparation expired. Prepare again.", 401)
            preparation.update(status="ready", context=identity)

        self.admission.update(finish)
        return {"preparation": self._token("prepare", pid, now + 600),
                "paper": self.paper(context), "overview_cache": cache_status,
                "limits": {"expires_at": now + 600}, "consent_required": True}

    def _duplicate(self, status: str, deadline: float = 0) -> None:
        if status == "done":
            raise PaperError("already_completed",
                             "This request completed. Use the original response; no new call was made.", 409)
        if status == "ready":
            raise PaperError("already_completed",
                             "Preparation completed. Use the original preparation or prepare again.", 409)
        if status in ("pending", "pending_open") and deadline > self.clock():
            raise PaperError("session_busy", "This request is still in progress.", 409)
        raise PaperError("outcome_unknown",
                         "This request may still be running or its outcome is unknown. No new call was made.",
                         409)

    def _reserve(self, state: dict, encoded: bytes | None) -> None:
        if encoded is not None:
            reserved = paper_chat.reservation(encoded, self.count_tokens)
            self.admission.charge(state, calls=1, tokens=reserved["total_tokens"],
                                  nanodollars=reserved["nanodollars"])

    def _model(self, context: Context, encoded: bytes, *, overview: bool,
               deadline: float) -> dict:
        # The only payload accepted is produced locally by the separate paper core.
        payload = json.loads(encoded)
        try:
            response = self.transport.post("responses", payload,
                                           timeout=min(25, self._remaining(deadline)))
            self._remaining(deadline)
            return paper_chat.parse_response(response, context, overview=overview)
        except ValueError:
            raise PaperError("model_invalid_answer",
                             "The paper answer failed validation. Its reserved turn remains used.", 502) from None

    def _failed(self, sid: str, rid: str, *, preparation: str | None = None) -> None:
        def finish(state: dict) -> None:
            session = state["sessions"][sid]
            session.update(busy=None)
            session["operations"][rid] = "done"
            if preparation is not None:
                for value in state["preparations"].values():
                    if value["id"] == preparation:
                        value["status"] = "done"
        self.admission.update(finish)

    def _uncertain(self, sid: str, rid: str, *, preparation: str | None = None) -> None:
        def finish(state: dict) -> None:
            state["sessions"][sid]["operations"][rid] = "unknown"
            if preparation is not None:
                for value in state["preparations"].values():
                    if value["id"] == preparation:
                        value["status"] = "unknown"
        self.admission.update(finish)

    def _reply_sig(self, sid: str, index: int, previous: str, user: str, assistant: str) -> str:
        return self._sign({"sid": sid, "turn": index, "previous": previous,
                           "user": user, "assistant": assistant})

    @staticmethod
    def _limits(session: dict) -> dict:
        return {"turns_left": 10 - session["used"], "expires_at": session["expires"]}

    def open(self, body: dict) -> dict:
        deadline = self.clock() + 45
        fields(body, {"preparation", "request_id"})
        rid = request_id(body["request_id"])
        pid = self._identity(body["preparation"], "prepare")
        sid = secrets.token_hex(24)

        def inspect(state: dict) -> dict:
            for value in state["preparations"].values():
                if value["id"] == pid:
                    if value.get("open_request") == rid:
                        self._duplicate(value["status"], value.get("open_deadline", 0))
                    if value["status"] != "ready":
                        raise PaperError("already_completed", "This preparation was already used.", 409)
                    if value["expires"] <= self.clock():
                        raise PaperError("preparation_expired", "Preparation expired.", 401)
                    return value.copy()
            raise PaperError("preparation_expired", "Preparation is unavailable.", 401)

        preparation = self.admission.update(inspect)
        context = self._context(preparation["context"], preparation=True)
        cache_status, cached = self._cached(preparation["context"], context)
        encoded, _ = paper_chat.encode_payload(
            context, paper_chat.OVERVIEW_QUESTION, (), self.count_tokens, overview=True,
        )
        expires = int(self.clock()) + 1800

        def claim(state: dict) -> None:
            self._remaining(deadline)
            current = inspect(state)
            self.admission.charge(state, sessions=1)
            self._reserve(state, encoded if cached is None else None)
            for value in state["preparations"].values():
                if value["id"] == current["id"]:
                    value.update(status="pending_open", open_request=rid, sid=sid,
                                 open_deadline=deadline)
            state["sessions"][sid] = {
                "context": preparation["context"], "expires": expires, "used": 0,
                "head": "0" * 64, "busy": rid, "busy_deadline": deadline,
                "operations": {rid: "pending"},
            }

        self.admission.update(claim)
        try:
            result = cached if cached is not None else self._model(
                context, encoded, overview=True, deadline=deadline,
            )
        except APIError as error:
            if isinstance(error, PaperError) and error.code == "model_invalid_answer":
                self._failed(sid, rid, preparation=pid)
            else:
                self._uncertain(sid, rid, preparation=pid)
            raise
        sig = self._reply_sig(sid, 0, "", "", result["answer"])

        def finish(state: dict) -> dict:
            session = state["sessions"][sid]
            session.update(head=sig, busy=None)
            session["operations"][rid] = "done"
            for value in state["preparations"].values():
                if value["id"] == pid:
                    value["status"] = "done"
            return self._limits(session)

        limits = self.admission.update(finish)
        return {
            "session": self._token("session", sid, expires), "paper": self.paper(context),
            "overview": {"text": result["answer"], "grounded": result["grounded"],
                         "citations": result["citations"],
                         "suggested_questions": result["suggested_questions"],
                         "assistant_sig": sig, "turn_index": 0},
            "limits": limits, "cache": {"overview": cache_status},
        }

    def _history(self, sid: str, session: dict, messages: object) -> tuple[paper_chat.Exchange, ...]:
        if not isinstance(messages, list) or not 1 <= len(messages) <= 21 or len(messages) % 2 != 1:
            raise PaperError("invalid_history", "Supply the complete signed conversation.", 400)
        previous = ""
        last_index = -1
        exchanges = []
        for offset in range(0, len(messages), 2):
            assistant = messages[offset]
            user = "" if offset == 0 else messages[offset - 1]
            if offset and (not isinstance(user, dict) or set(user) != {"role", "content"}
                           or user["role"] != "user" or not isinstance(user["content"], str)
                           or not user["content"].strip()
                           or len(user["content"]) > paper_chat.MAX_QUESTION_CHARS):
                raise PaperError("invalid_history", "Invalid user history.", 400)
            if (not isinstance(assistant, dict)
                    or set(assistant) != {"role", "content", "sig", "turn_index"}
                    or assistant["role"] != "assistant"
                    or not isinstance(assistant["content"], str)
                    or not assistant["content"].strip() or len(assistant["content"]) > 8000
                    or not isinstance(assistant["sig"], str)
                    or type(assistant["turn_index"]) is not int):
                raise PaperError("invalid_history", "Invalid assistant history.", 400)
            index = assistant["turn_index"]
            if (index <= last_index or index > session["used"] or (offset == 0 and index != 0)):
                raise PaperError("invalid_history", "Discontinuous conversation history.", 400)
            text = "" if offset == 0 else user["content"]
            expected = self._reply_sig(sid, index, previous, text, assistant["content"])
            if not hmac.compare_digest(expected, assistant["sig"]):
                raise PaperError("invalid_history", "Conversation signature does not match.", 400)
            previous, last_index = expected, index
            if offset:
                exchanges.append(paper_chat.Exchange(text, assistant["content"]))
        if not hmac.compare_digest(previous, session["head"]):
            raise PaperError("invalid_history", "Conversation history is missing or outdated.", 400)
        return tuple(exchanges)

    def _encode_chat(self, context: Context, question: str,
                     exchanges: tuple[paper_chat.Exchange, ...], baseline: str
                     ) -> tuple[bytes, paper_chat.Memory]:
        # The core has no baseline parameter. Preserve its payload/schema, adding only
        # this authenticated-but-untrusted history field and rebudgeting the whole envelope.
        retained = exchanges
        while True:
            encoded, memory = paper_chat.encode_payload(
                context, question, retained, self.count_tokens,
            )
            payload = json.loads(encoded)
            body = json.loads(payload["input"])
            body["history_baseline"] = baseline
            history = {"baseline": baseline, "exchanges": body["history"]}
            payload["input"] = json.dumps(body, ensure_ascii=False)
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            if (self.count_tokens(json.dumps(history, ensure_ascii=False)) <= 3000
                    and self.count_tokens(encoded.decode()) + paper_chat.FRAMING_TOKENS
                    <= paper_chat.MAX_INPUT_TOKENS):
                return encoded, paper_chat.Memory(
                    memory.exchanges, len(memory.exchanges) != len(exchanges),
                    self.count_tokens(json.dumps(history, ensure_ascii=False)),
                )
            if not memory.exchanges:
                raise PaperError("invalid_history", "Overview exceeds the history budget.", 400)
            retained = memory.exchanges[1:]

    def chat(self, body: dict) -> dict:
        deadline = self.clock() + 45
        fields(body, {"session", "request_id", "messages", "question"})
        rid = request_id(body["request_id"])
        sid = self._identity(body["session"], "session")
        question = body["question"]
        if (not isinstance(question, str) or not question.strip()
                or len(question) > paper_chat.MAX_QUESTION_CHARS):
            raise PaperError("bad_request", "Question must contain 1 to 500 characters.", 400)

        def inspect(state: dict) -> dict:
            session = state["sessions"].get(sid)
            if session is None or session["expires"] <= self.clock():
                raise PaperError("session_expired", "Paper session expired.", 401)
            if rid in session["operations"]:
                self._duplicate(session["operations"][rid], session.get("busy_deadline", 0))
            if session["busy"]:
                raise PaperError("session_busy", "Another request is in progress.", 409,
                                 self._limits(session))
            if session["used"] >= 10:
                raise PaperError("turn_limit", "All ten follow-ups have been used.", 429,
                                 self._limits(session))
            return session.copy()

        session = self.admission.update(inspect)
        exchanges = self._history(sid, session, body["messages"])
        context = self._context(session["context"])
        encoded, memory = self._encode_chat(
            context, question, exchanges, body["messages"][0]["content"],
        )
        index = session["used"] + 1

        def claim(state: dict) -> None:
            self._remaining(deadline)
            current = inspect(state)
            if current["head"] != session["head"] or current["used"] != session["used"]:
                raise PaperError("invalid_history", "Conversation changed. Keep the latest reply.", 400)
            self._reserve(state, encoded)
            state["sessions"][sid].update(used=index, busy=rid, busy_deadline=deadline)
            state["sessions"][sid]["operations"][rid] = "pending"

        self.admission.update(claim)
        try:
            result = self._model(context, encoded, overview=False, deadline=deadline)
        except APIError as error:
            if isinstance(error, PaperError) and error.code == "model_invalid_answer":
                self._failed(sid, rid)
            else:
                self._uncertain(sid, rid)
            error.limits = {"turns_left": 10 - index, "expires_at": session["expires"]}
            raise
        sig = self._reply_sig(sid, index, session["head"], question, result["answer"])

        def finish(state: dict) -> dict:
            current = state["sessions"][sid]
            current.update(head=sig, busy=None)
            current["operations"][rid] = "done"
            return self._limits(current)

        limits = self.admission.update(finish)
        return {**result, "assistant_sig": sig, "turn_index": index,
                "limits": limits, "memory": memory.as_dict()}
