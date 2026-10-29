"""Restricted Responses API relevance judging with durable, fail-closed accounting.

The ledger is a *lifetime* local allowance, not a provider quota service. Its
creation/attempt days use UTC for audit only; midnight never resets usage. Both
allowlisted models share the mini allowance. Other programs, organizational
traffic, pricing changes, and provider tokenization are outside this guard's
control, so it cannot guarantee free organizational usage. Only manually start a
new ledger after verifying the applicable allowance and other clients' usage.

Reserve UTF-8 request bytes (a conservative token upper bound), fixed protocol
headroom, and the entire output cap before EVERY HTTP attempt. Unknown outcomes
keep their full reservation, including process crashes. Never store prompts,
responses, headers, or credentials in the ledger.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, field_validator

from arxiv_search import config

ENDPOINT = "https://api.openai.com/v1/responses"
MODEL_TIERS = {"gpt-5.4-nano": "mini", "gpt-5.4-mini": "mini"}


class OpenAIError(RuntimeError):
    """Sanitized failure: never includes provider bodies, prompts, or secrets."""


class BudgetExceeded(OpenAIError):
    """No HTTP request was made because the durable reservation was denied."""


class _PaperGrade(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    paper: str
    reason: str
    grade: Literal[0, 1, 2]

    @field_validator("grade", mode="before")
    @classmethod
    def integer_grade(cls, value: object) -> object:
        # Literal equality alone accepts True == 1, even in Pydantic strict mode.
        if type(value) is not int:
            raise ValueError("Grade must be a JSON integer")
        return value


class _Grades(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    grades: list[_PaperGrade]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    """Concurrent SQLite reservations; pending/unknown attempts remain charged."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path if path is not None else config.OPENAI_LEDGER_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS attempts (
                request_id TEXT PRIMARY KEY, model TEXT NOT NULL, tier TEXT NOT NULL,
                started_utc TEXT NOT NULL, status TEXT NOT NULL,
                reserved_input INTEGER NOT NULL, reserved_output INTEGER NOT NULL,
                accounted_tokens INTEGER NOT NULL, input_tokens INTEGER,
                output_tokens INTEGER, reasoning_tokens INTEGER,
                provider_request_id TEXT, latency_seconds REAL)""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def reserve(self, model: str, input_tokens: int, output_tokens: int) -> str:
        if model not in MODEL_TIERS:
            raise OpenAIError("Model is not allowlisted for relevance judging")
        if input_tokens <= 0 or output_tokens <= 0:
            raise ValueError("Reservations must be positive")
        tier = MODEL_TIERS[model]
        fraction = config.OPENAI_BUDGET_FRACTION
        if not 0 < fraction <= 1:
            raise ValueError("OPENAI_BUDGET_FRACTION must be in (0, 1]")
        limit = int(config.OPENAI_TOKEN_LIMITS[tier] * fraction)
        total = input_tokens + output_tokens
        request_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            used = db.execute(
                "SELECT COALESCE(SUM(accounted_tokens), 0) FROM attempts WHERE tier = ?", (tier,)
            ).fetchone()[0]
            if used + total > limit:
                raise BudgetExceeded(f"Local {tier} cumulative token budget exhausted; no request sent")
            db.execute("""INSERT INTO attempts
                (request_id, model, tier, started_utc, status, reserved_input,
                 reserved_output, accounted_tokens) VALUES (?, ?, ?, ?, 'reserved', ?, ?, ?)""",
                       (request_id, model, tier, _utc(), input_tokens, output_tokens, total))
        return request_id

    def finish(self, request_id: str, status: str, latency: float,
               usage: dict | None = None, provider_request_id: str | None = None) -> dict:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM attempts WHERE request_id = ?", (request_id,)).fetchone()
            if row is None or row["status"] != "reserved":
                raise OpenAIError("Attempt is missing or already finalized")
            input_tokens = output_tokens = reasoning = None
            accounted = row["accounted_tokens"]
            if usage is not None:
                input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
                reasoning = usage["reasoning_tokens"]
                accounted = input_tokens + output_tokens  # output already includes reasoning
            db.execute("""UPDATE attempts SET status = ?, latency_seconds = ?,
                input_tokens = ?, output_tokens = ?, reasoning_tokens = ?,
                accounted_tokens = ?, provider_request_id = ? WHERE request_id = ?""",
                       (status, latency, input_tokens, output_tokens, reasoning,
                        accounted, provider_request_id, request_id))
            return dict(db.execute("SELECT * FROM attempts WHERE request_id = ?", (request_id,)).fetchone())


def _usage(body: dict) -> dict:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        raise OpenAIError("Response has no trustworthy usage; reservation retained")
    input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
    details = usage.get("output_tokens_details") or {}
    reasoning = details.get("reasoning_tokens", 0) if isinstance(details, dict) else None
    if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens, reasoning)):
        raise OpenAIError("Response has invalid usage; reservation retained")
    if reasoning > output_tokens:
        raise OpenAIError("Response has inconsistent reasoning usage; reservation retained")
    total = usage.get("total_tokens")
    if type(total) is not int or total != input_tokens + output_tokens:
        raise OpenAIError("Response has inconsistent total usage; reservation retained")
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "reasoning_tokens": reasoning}


def _retry_wait(response: httpx.Response | None, attempt: int) -> float:
    value = response.headers.get("retry-after") if response is not None else None
    try:
        wait = float(value) if value is not None else float(2 ** attempt)
    except ValueError:
        try:
            wait = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            raise OpenAIError("Invalid Retry-After; not retrying") from None
    if not 0 <= wait <= config.OPENAI_MAX_RETRY_WAIT_SECONDS:
        raise OpenAIError("Retry-After exceeds bounded retry window; not retrying")
    return wait


def generate_json(model: str, prompt: str, system_instruction: str) -> tuple[dict, dict]:
    """Judge at most ten labels; no embeddings, redirects, SDK retries, or fallback."""
    if model not in MODEL_TIERS:
        raise OpenAIError("Model is not allowlisted for relevance judging")
    labels = re.findall(r"^\[(P[1-9]\d*)\]", prompt, flags=re.MULTILINE)
    if not 1 <= len(labels) <= 10 or len(labels) != len(set(labels)):
        raise OpenAIError("Relevance requests require 1-10 unique paper labels")
    if not 1024 <= config.OPENAI_MAX_OUTPUT_TOKENS <= 2048:
        raise ValueError("OpenAI relevance output cap must be 1024-2048 tokens")
    if not 1 <= config.OPENAI_MAX_ATTEMPTS <= 3:
        raise ValueError("OpenAI HTTP attempts must be 1-3")
    schema = _Grades.model_json_schema()
    schema["$defs"]["_PaperGrade"]["properties"]["paper"]["enum"] = labels
    payload = {
        "model": model, "instructions": system_instruction, "input": prompt,
        "store": False, "reasoning": {"effort": "none"},
        "max_output_tokens": config.OPENAI_MAX_OUTPUT_TOKENS,
        "text": {"format": {"type": "json_schema", "name": "relevance_grades",
                            "strict": True, "schema": schema}},
    }
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    reserved_input = len(encoded) + config.OPENAI_INPUT_OVERHEAD_TOKENS
    if config.OPENAI_INPUT_OVERHEAD_TOKENS < 4096:
        raise ValueError("OpenAI input overhead must be at least 4096")
    load_dotenv(config.PROJECT_ROOT / ".env")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise OpenAIError("OPENAI_API_KEY is required")
    ledger = Ledger()
    attempts = []
    call_started = time.perf_counter()
    for attempt in range(1, config.OPENAI_MAX_ATTEMPTS + 1):
        request_id = ledger.reserve(model, reserved_input, config.OPENAI_MAX_OUTPUT_TOKENS)
        started = time.perf_counter()
        response = None
        try:
            response = httpx.post(
                ENDPOINT, content=encoded, timeout=120, follow_redirects=False, trust_env=False,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
        except httpx.RequestError:
            attempts.append(ledger.finish(request_id, "unknown_transport", time.perf_counter() - started))
            if attempt == config.OPENAI_MAX_ATTEMPTS:
                raise OpenAIError("OpenAI transport failed; reservations retained") from None
        else:
            elapsed = time.perf_counter() - started
            provider_id = response.headers.get("x-request-id")
            if response.status_code != 200:
                attempts.append(ledger.finish(request_id, f"http_{response.status_code}", elapsed,
                                              provider_request_id=provider_id))
                if (response.status_code != 429 and response.status_code < 500) or \
                        attempt == config.OPENAI_MAX_ATTEMPTS:
                    raise OpenAIError(f"OpenAI HTTP {response.status_code}; reservation retained")
            else:
                try:
                    body = response.json()
                    usage = _usage(body)
                except (ValueError, AttributeError, OpenAIError):
                    ledger.finish(request_id, "unknown_usage", elapsed, provider_request_id=provider_id)
                    raise OpenAIError("Invalid response usage; reservation retained") from None
                status = "completed"
                try:
                    if body.get("status") != "completed":
                        status = "incomplete"
                        raise OpenAIError("OpenAI response incomplete or failed")
                    output = [part for item in body.get("output", [])
                              if item.get("type") == "message" for part in item.get("content", [])]
                    if any(part.get("type") == "refusal" for part in output):
                        status = "refused"
                        raise OpenAIError("OpenAI refused relevance judging")
                    texts = [part["text"] for part in output if part.get("type") == "output_text"]
                    if len(texts) != 1:
                        raise ValueError("Expected one structured answer")
                    answer = _Grades.model_validate_json(texts[0])
                    given = [g.paper for g in answer.grades]
                    if sorted(given) != sorted(labels) or any(type(g.grade) is not int for g in answer.grades):
                        raise ValueError("Invalid paper labels or grades")
                except (ValueError, KeyError, TypeError, AttributeError, OpenAIError):
                    if status == "completed":
                        status = "invalid_answer"
                    ledger.finish(request_id, status, elapsed, usage, provider_id)
                    raise OpenAIError(f"OpenAI {status}; actual usage recorded") from None
                attempts.append(ledger.finish(request_id, status, elapsed, usage, provider_id))
                return answer.model_dump(), {
                    "model": model, "request_id": request_id, "provider_request_id": provider_id,
                    "input_tokens": sum(a["input_tokens"] or 0 for a in attempts),
                    "output_tokens": sum(a["output_tokens"] or 0 for a in attempts),
                    "thinking_tokens": sum(a["reasoning_tokens"] or 0 for a in attempts),
                    "reasoning_tokens": sum(a["reasoning_tokens"] or 0 for a in attempts),
                    "accounted_tokens": sum(a["accounted_tokens"] for a in attempts),
                    "unknown_reserved_tokens": sum(a["accounted_tokens"] for a in attempts
                                                   if a["input_tokens"] is None),
                    "wall_seconds": time.perf_counter() - call_started,
                    "attempts": len(attempts), "ledger_attempts": attempts,
                }
        time.sleep(_retry_wait(response, attempt))
    raise OpenAIError("OpenAI attempt limit reached")
