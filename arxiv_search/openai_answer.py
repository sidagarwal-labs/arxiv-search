"""One-shot Responses API calls for answer generation and answer grading.

Same safety rules as the reranker transport: every request is reserved in the shared
daily-token ledger before it is sent, each request key is attempted at most once (no
automatic retries), task dollar ceilings are enforced from the ledger, and prompts,
responses and credentials are never written to the ledger.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from arxiv_search import config, openai_api as api

# Pinned snapshots where OpenAI publishes one. gpt-6-luna has no dated snapshot yet, so its
# responses record the model string the API returns.
MODELS = {
    "nano": "gpt-5.4-nano-2026-03-17",  # deprecated: shuts down 2027-04-01
    "luna": "gpt-6-luna",
    "mini": "gpt-5.4-mini-2026-03-17",
    "gpt-5.4": "gpt-5.4-2026-03-05",
}
# Nanodollars per token, standard (uncached) prices checked 2026-11-04.
PRICES = {
    "gpt-5.4-nano-2026-03-17": (200, 1250),
    "gpt-6-luna": (100, 500),
    "gpt-5.4-mini-2026-03-17": (750, 4500),
    "gpt-5.4-2026-03-05": (2500, 15000),
}
OVERHEAD_TOKENS = 4096


class InvalidAnswer(api.OpenAIError):
    """The model replied but broke the output contract; usage is recorded, nothing retried."""

    def __init__(self, status: str, detail: str):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


def request_key(encoded: bytes) -> str:
    return hashlib.sha256(encoded).hexdigest()


def reserved_input(encoded: bytes) -> int:
    return len(encoded) + OVERHEAD_TOKENS  # UTF-8 bytes bound the token count from above


def cost_nanodollars(model: str, input_tokens: int, output_tokens: int) -> int:
    price_in, price_out = PRICES[model]
    return input_tokens * price_in + output_tokens * price_out


class TaskLedger(api.Ledger):
    """Shared daily-token ledger plus one dollar/request ceiling per named task."""

    def __init__(self, task: str, cap_nanodollars: int, max_requests: int, path: Path | None = None):
        if not task or cap_nanodollars <= 0 or max_requests <= 0:
            raise ValueError("Tasks need a name and positive ceilings")
        self.task, self.cap, self.max_requests = task, cap_nanodollars, max_requests
        super().__init__(path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS answer_task_attempts (
                request_key TEXT NOT NULL, task TEXT NOT NULL, request_id TEXT UNIQUE NOT NULL,
                PRIMARY KEY (request_key, task))""")

    def _rows(self, db) -> list:
        return db.execute("""SELECT a.* FROM attempts a JOIN answer_task_attempts t USING(request_id)
            WHERE t.task=? ORDER BY a.rowid""", (self.task,)).fetchall()

    @staticmethod
    def _cost(row) -> int:
        tokens_in = row["input_tokens"] if row["input_tokens"] is not None else row["reserved_input"]
        tokens_out = row["output_tokens"] if row["output_tokens"] is not None else row["reserved_output"]
        return cost_nanodollars(row["model"], tokens_in, tokens_out)

    def summary(self) -> dict:
        with self._connect() as db:
            rows = self._rows(db)
            shared = {tier: api.used_today(db, tier) for tier in ("mini", "large")}
        by_model: dict[str, dict] = {}
        for r in rows:
            m = by_model.setdefault(r["model"], {"requests": 0, "usd": 0.0, "input_tokens": 0,
                                                 "output_tokens": 0, "api_seconds": 0.0})
            m["requests"] += 1
            m["usd"] += self._cost(r) / 1e9
            m["input_tokens"] += r["input_tokens"] or 0
            m["output_tokens"] += r["output_tokens"] or 0
            m["api_seconds"] += r["latency_seconds"] or 0
        return {"task": self.task, "requests": len(rows),
                "accounted_usd": sum(self._cost(r) for r in rows) / 1e9,
                "cap_usd": self.cap / 1e9, "by_model": by_model,
                "unknown_outcomes": sum(r["input_tokens"] is None for r in rows),
                "shared_accounted_tokens_today": shared}

    def attempted(self, key: str) -> bool:
        with self._connect() as db:
            return db.execute("SELECT 1 FROM answer_task_attempts WHERE request_key=? AND task=?",
                              (key, self.task)).fetchone() is not None

    def attempt(self, key: str) -> dict | None:
        """The ledger row (tokens, latency, status) for this task's attempt at a request key."""
        with self._connect() as db:
            row = db.execute("""SELECT a.* FROM attempts a JOIN answer_task_attempts t USING(request_id)
                WHERE t.request_key=? AND t.task=?""", (key, self.task)).fetchone()
        return dict(row) if row else None

    def reserve_request(self, key: str, model: str, input_tokens: int, output_tokens: int) -> str:
        if model not in PRICES:
            raise api.OpenAIError("Model has no recorded price; no request sent")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM answer_task_attempts WHERE request_key=? AND task=?",
                          (key, self.task)).fetchone():
                raise api.OpenAIError("Request already attempted; no automatic retry")
            rows = self._rows(db)
            spent = sum(self._cost(r) for r in rows)
            if (len(rows) >= self.max_requests
                    or spent + cost_nanodollars(model, input_tokens, output_tokens) > self.cap):
                raise api.BudgetExceeded("Answer task dollar/request ceiling reached; no request sent")
            request_id = self._reserve_in_transaction(db, model, input_tokens, output_tokens)
            db.execute("INSERT INTO answer_task_attempts (request_key, task, request_id) VALUES (?,?,?)",
                       (key, self.task, request_id))
        return request_id


def final_parts(output: list) -> list[dict]:
    """Content parts of the reply's messages; GPT-6 drafts in a commentary phase first."""
    messages = [item for item in output if item.get("type") == "message"]
    if any(item.get("phase") for item in messages):
        messages = [item for item in messages if item.get("phase") == "final_answer"]
    return [part for item in messages for part in item.get("content", [])]


def structured_text(parts: list[dict]) -> str:
    texts = [part["text"] for part in parts if part.get("type") == "output_text"]
    if len(texts) != 1:
        raise ValueError("Expected one structured response")
    return texts[0]


def call_once(encoded: bytes, ledger: TaskLedger, *, validate, attempt_key: str | None = None,
              failure_path: Path | None = None) -> tuple[object, dict]:
    """Send one structured-output request; validate; record usage. Never retries."""
    payload = json.loads(encoded)
    model = payload["model"]
    if (model not in PRICES or payload.get("store") is not False or "tools" in payload
            or payload["text"]["format"].get("strict") is not True):
        raise ValueError("Unexpected answer request configuration")
    load_dotenv(config.PROJECT_ROOT / ".env")
    secret = os.environ.get("OPENAI_API_KEY")
    if not secret:
        raise api.OpenAIError("OPENAI_API_KEY is required for new requests")
    key = attempt_key or request_key(encoded)
    request_id = ledger.reserve_request(key, model, reserved_input(encoded), payload["max_output_tokens"])
    start = time.perf_counter()
    try:
        response = httpx.post(api.ENDPOINT, content=encoded, timeout=180, follow_redirects=False,
                              trust_env=False, headers={"Authorization": f"Bearer {secret}",
                                                        "Content-Type": "application/json"})
    except httpx.RequestError:
        ledger.finish(request_id, "unknown_transport", time.perf_counter() - start)
        raise api.OpenAIError("Transport failed; reservation retained; no retry") from None
    elapsed = time.perf_counter() - start
    provider_id = response.headers.get("x-request-id")
    if response.status_code != 200:
        ledger.finish(request_id, f"http_{response.status_code}", elapsed, provider_request_id=provider_id)
        try:
            error = response.json().get("error") or {}
            reason = f" {error.get('type')}/{error.get('code')}"
        except (ValueError, AttributeError):
            reason = ""
        raise api.OpenAIError(f"HTTP {response.status_code}{reason}; reservation retained; no retry")
    try:
        body = response.json()
        usage = api._usage(body)
    except (ValueError, AttributeError, api.OpenAIError):
        ledger.finish(request_id, "unknown_usage", elapsed, provider_request_id=provider_id)
        raise api.OpenAIError("Invalid usage; reservation retained") from None
    status = "completed"
    try:
        if body.get("status") != "completed":
            status = "incomplete"
            raise ValueError("Incomplete response")
        if not str(body.get("model", "")).startswith(model):
            raise ValueError("Response came from a different model")
        parts = final_parts(body.get("output", []))
        if any(part.get("type") == "refusal" for part in parts):
            status = "refused"
            raise ValueError("Refused response")
        answer = validate(json.loads(structured_text(parts)))
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        if status == "completed":
            status = "invalid_answer"
        ledger.finish(request_id, status, elapsed, usage, provider_id)
        if failure_path is not None:
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            failure_path.write_text(json.dumps({
                "request_key": request_key(encoded), "status": status, "validation_error": str(error),
                "model": body.get("model"), "output": body.get("output"), "usage": usage,
            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise InvalidAnswer(status, str(error)) from None
    attempt = ledger.finish(request_id, status, elapsed, usage, provider_id)
    return answer, {**attempt, "response_model": body.get("model")}
