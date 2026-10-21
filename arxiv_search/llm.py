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
import time

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
        _client = genai.Client()
    return _client


def _wait_for_pacing() -> None:
    global _last_call_at
    wait = config.LLM_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def _retry_delay(error: errors.APIError, attempt: int) -> float:
    """Google sometimes says how long to wait ("retryDelay": "37s"); otherwise back off."""
    match = re.search(r"retryDelay'?\"?:\s*'?\"?(\d+)", str(error))
    if match:
        return int(match.group(1)) + 1
    return min(10 * 2**attempt, 300)


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
    model: str, prompt: str, schema: type[BaseModel], system_instruction: str | None = None
) -> tuple[BaseModel, dict]:
    """Call the model and return (parsed answer, usage info).

    `schema` is a pydantic class describing the JSON we want back; the model is told to
    answer in exactly that shape. If it still returns broken JSON, we ask again.
    """
    request_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=schema,
    )
    for attempt in range(config.LLM_MAX_RETRIES + 1):
        _wait_for_pacing()
        try:
            response = client().models.generate_content(
                model=model, contents=prompt, config=request_config
            )
        except errors.APIError as error:
            if error.code == 429 and "PerDay" in str(error):
                raise DailyLimitReached(f"{model}: daily free-tier quota used up.\n{error}") from error
            if error.code not in (429, 500, 503) or attempt == config.LLM_MAX_RETRIES:
                raise
            delay = _retry_delay(error, attempt)
            print(f"  {model} returned {error.code}; waiting {delay:.0f}s (retry {attempt + 1})")
            time.sleep(delay)
            continue
        except httpx.TransportError as error:  # Wi-Fi dropped, laptop slept, connection reset
            if attempt == config.LLM_MAX_RETRIES:
                raise
            delay = min(10 * 2**attempt, 300)
            print(f"  network error ({type(error).__name__}); waiting {delay}s (retry {attempt + 1})")
            time.sleep(delay)
            continue
        parsed = _parse(response, schema)
        if parsed is None:
            if attempt == config.LLM_MAX_RETRIES:
                raise ValueError(f"Model returned no parseable JSON: {response.text!r}")
            print(f"  {model} returned broken JSON; asking again (retry {attempt + 1})")
            continue
        usage = response.usage_metadata
        return parsed, {
            "model": model,
            "input_tokens": usage.prompt_token_count,
            "output_tokens": usage.candidates_token_count,
            "thinking_tokens": usage.thoughts_token_count,
            "attempts": attempt + 1,
        }
    raise AssertionError("unreachable")
