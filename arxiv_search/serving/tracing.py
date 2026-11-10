"""Optional LangSmith tracing for the serving API.

Tracing is off unless ``LANGSMITH_TRACING=true`` and ``LANGSMITH_API_KEY`` are set and the
``langsmith`` package is importable. The SDK reads ``LANGSMITH_ENDPOINT``,
``LANGSMITH_AGENT_ID`` and ``LANGSMITH_AGENT_ENVIRONMENT`` itself. Tracing must never change a
response: every SDK failure is logged and swallowed, and spans degrade to no-ops.

Runs are batched in the background by the SDK; ``flush`` is called once at the end of each
traced request because serverless functions can be frozen as soon as they respond.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
import contextlib
import contextvars
import logging
import os
from typing import Any

LOG = logging.getLogger(__name__)
FLUSH_TIMEOUT = 3.0
TEXT_LIMIT = 4000

_module: Any = None
_client: Any = None
_loaded = False


def enabled() -> bool:
    return (os.environ.get("LANGSMITH_TRACING", "").strip().lower() == "true"
            and bool(os.environ.get("LANGSMITH_API_KEY", "").strip()))


def configure(module: Any = None, client: Any = None) -> None:
    """Set the SDK module and client explicitly (tests) or reset to lazy loading (None)."""
    global _module, _client, _loaded
    _module, _client, _loaded = module, client, module is not None


def _sdk() -> tuple[Any, Any]:
    global _module, _client, _loaded
    if not _loaded:
        _loaded = True
        if enabled():
            try:
                import langsmith

                _client = langsmith.Client(timeout_ms=(2000, 5000))
                _module = langsmith
            except Exception:
                LOG.warning("LangSmith tracing unavailable; continuing untraced", exc_info=True)
    return _module, _client


class NullRun:
    def end(self, **_: Any) -> None:
        pass

    def add_metadata(self, _: dict) -> None:
        pass


def clip(text: object, limit: int = TEXT_LIMIT) -> object:
    if isinstance(text, str) and len(text) > limit:
        return text[:limit] + f"… [{len(text) - limit} more characters]"
    return text


@contextlib.contextmanager
def span(name: str, run_type: str = "chain", *, inputs: dict | None = None,
         metadata: dict | None = None, tags: list[str] | None = None) -> Iterator[Any]:
    module, client = _sdk()
    manager = None
    if module is not None:
        try:
            manager = module.trace(name, run_type=run_type, inputs=inputs or {},
                                   metadata=metadata or {}, tags=tags, client=client)
            run = manager.__enter__()
        except Exception:
            LOG.warning("Could not start LangSmith span %s", name, exc_info=True)
            manager = None
    if manager is None:
        yield NullRun()
        return
    try:
        yield run
    except BaseException as error:
        with contextlib.suppress(Exception):
            manager.__exit__(type(error), error, error.__traceback__)
        raise
    else:
        with contextlib.suppress(Exception):
            manager.__exit__(None, None, None)


def end(run: Any, **outputs: Any) -> None:
    with contextlib.suppress(Exception):
        run.end(outputs=outputs)


def in_context(function: Callable) -> Callable:
    """Run ``function`` in a copy of the caller's context so worker-thread spans nest."""
    context = contextvars.copy_context()
    return lambda *args, **kwargs: context.copy().run(function, *args, **kwargs)


def flush() -> None:
    if _client is None:
        return
    try:
        _client.flush(timeout=FLUSH_TIMEOUT)
    except Exception:
        LOG.warning("LangSmith flush failed", exc_info=True)


def response_text(reply: object) -> str | None:
    """The final output text of an OpenAI Responses payload, if any."""
    if not isinstance(reply, dict) or not isinstance(reply.get("output"), list):
        return None
    texts = [part.get("text") for item in reply["output"] if isinstance(item, dict)
             for part in item.get("content") or [] if isinstance(part, dict)
             and part.get("type") == "output_text" and isinstance(part.get("text"), str)]
    return texts[-1] if texts else None


def usage(reply: object, *, embedding: bool = False) -> dict | None:
    value = reply.get("usage") if isinstance(reply, dict) else None
    if not isinstance(value, dict):
        return None
    prompt = value.get("prompt_tokens" if embedding else "input_tokens")
    output = 0 if embedding else value.get("output_tokens")
    if type(prompt) is not int or type(output) is not int:
        return None
    return {"input_tokens": prompt, "output_tokens": output, "total_tokens": prompt + output}
