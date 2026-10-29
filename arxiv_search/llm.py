"""One small wrapper around the Gemini API, shared by every step that calls an LLM.

Free-tier rules it handles, so the rest of the code doesn't have to:

1. Pace calls: wait at least LLM_SECONDS_BETWEEN_CALLS between requests (stays under
   per-minute limits).
2. Retry when Google is busy (500/503), we're going too fast (429), or the network drops,
   waiting longer each time (10 s, 20 s, 40 s, ...), or exactly as long as Google asks if it says.
3. Stop cleanly on the DAILY limit, because retrying won't help until tomorrow. Callers save
   progress as they go, so rerunning the next day resumes.
"""

from __future__ import annotations

import re
import random
import time
import math
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from arxiv_search import config


class DailyLimitReached(RuntimeError):
    """The free-tier daily quota for this model is used up. Rerun tomorrow to resume."""


_client: genai.Client | None = None
_last_call_at = 0.0


def client() -> genai.Client:
    global _client
    if _client is None:
        load_dotenv(config.PROJECT_ROOT / ".env")  # reads GEMINI_API_KEY
        _client = genai.Client(http_options=types.HttpOptions(
            timeout=config.LLM_REQUEST_TIMEOUT_SECONDS * 1000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ))
    return _client


def _wait_for_pacing() -> None:
    global _last_call_at
    wait = config.LLM_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def _retry_delay(error: errors.APIError, attempt: int) -> float:
    """Respect provider delays without shortening exponential backoff."""
    delays = [min(10 * 2**attempt, 300) + random.uniform(0, 5)]
    match = re.search(r"""retryDelay['"]?:\s*['"]?(\d+(?:\.\d+)?)s""", str(error))
    if match:
        delays.append(float(match.group(1)) + 1)
    if error.response is not None:
        header = error.response.headers.get("Retry-After")
        if header is not None:
            try:
                seconds = float(header)
            except ValueError:
                try:
                    seconds = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    print("  ignoring invalid Retry-After header; using backoff", flush=True)
                    return max(delays)
            if math.isfinite(seconds) and seconds >= 0:
                delays.append(seconds + 1)
    return max(delays)


def _parse(response: types.GenerateContentResponse, schema: type[BaseModel]) -> BaseModel | None:
    """The parsed answer, or None if the text isn't valid JSON for `schema`.

    Gemma sometimes wraps its JSON in ``` fences, which the SDK won't parse, so we strip them.
    """
    if response.parsed is not None:
        return response.parsed
    text = re.sub(r"^\s*```(?:json)?|```\s*$", "", response.text or "").strip()
    try:
        return schema.model_validate_json(text)
    except ValueError:
        return None


def generate_json(
    model: str, prompt: str, schema: type[BaseModel], system_instruction: str | None = None,
    temperature: float | None = None,
) -> tuple[BaseModel, dict]:
    """Call the model and return (parsed answer, usage info).

    `schema` is a pydantic class describing the JSON we want back; the model is told to
    answer in exactly that shape. If it still returns broken JSON, we ask again.
    temperature=0 makes answers as repeatable as the API allows (used by the judge).
    """
    request_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature,
    )
    request_id = uuid.uuid4().hex[:12]
    attempt_log = []
    retry_wait_seconds = 0.0
    started = time.perf_counter()
    for attempt in range(config.LLM_MAX_RETRIES + 1):
        _wait_for_pacing()
        attempt_start = time.perf_counter()
        print(f"  {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
              f"{model} request={request_id} attempt={attempt + 1} "
              f"prompt_chars={len(prompt)}", flush=True)
        try:
            response = client().models.generate_content(
                model=model, contents=prompt, config=request_config
            )
        except errors.APIError as error:
            elapsed = time.perf_counter() - attempt_start
            attempt_log.append({"attempt": attempt + 1, "code": error.code,
                                "seconds": round(elapsed, 3)})
            print(f"  request={request_id} HTTP {error.code} status={error.status} "
                  f"after {elapsed:.1f}s", flush=True)
            if error.code == 429 and re.search(r"per[_ -]?day|daily", str(error), re.IGNORECASE):
                raise DailyLimitReached(f"{model}: daily free-tier quota used up.\n{error}") from error
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == config.LLM_MAX_RETRIES:
                raise
            delay = _retry_delay(error, attempt)
            print(f"  {model} returned {error.code}; waiting {delay:.1f}s (retry {attempt + 1})",
                  flush=True)
            retry_wait_seconds += delay
            time.sleep(delay)
            continue
        except httpx.TransportError as error:  # Wi-Fi dropped, laptop slept, connection reset
            elapsed = time.perf_counter() - attempt_start
            attempt_log.append({"attempt": attempt + 1, "error": type(error).__name__,
                                "seconds": round(elapsed, 3)})
            print(f"  request={request_id} {type(error).__name__} after {elapsed:.1f}s", flush=True)
            if attempt == config.LLM_MAX_RETRIES:
                raise
            delay = min(10 * 2**attempt, 300)
            print(f"  network error ({type(error).__name__}); waiting {delay}s (retry {attempt + 1})",
                  flush=True)
            retry_wait_seconds += delay
            time.sleep(delay)
            continue
        parsed = _parse(response, schema)
        elapsed = time.perf_counter() - attempt_start
        attempt_log.append({"attempt": attempt + 1, "code": 200,
                            "parsed": parsed is not None, "seconds": round(elapsed, 3)})
        if parsed is None:
            if attempt == config.LLM_MAX_RETRIES:
                raise ValueError(f"Model returned no parseable JSON: {response.text!r}")
            print(f"  request={request_id} returned broken JSON after {elapsed:.1f}s; "
                  f"asking again (retry {attempt + 1})", flush=True)
            continue
        usage = response.usage_metadata
        print(f"  request={request_id} succeeded after {elapsed:.1f}s; "
              f"input_tokens={usage.prompt_token_count} output_tokens={usage.candidates_token_count}",
              flush=True)
        return parsed, {
            "model": model,
            "input_tokens": usage.prompt_token_count,
            "output_tokens": usage.candidates_token_count,
            "thinking_tokens": usage.thoughts_token_count,
            "attempts": attempt + 1,
            "request_id": request_id,
            "wall_seconds": round(time.perf_counter() - started, 3),
            "retry_wait_seconds": round(retry_wait_seconds, 3),
            "attempt_log": attempt_log,
        }
    raise AssertionError("unreachable")
