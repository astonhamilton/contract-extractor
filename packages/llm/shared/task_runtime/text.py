from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from pathlib import Path

from litellm import completion

from packages.llm.shared.task_runtime._common import (
    is_empty_text_content_error,
    json_safe,
    parse_text_content,
    response_debug_payload,
    write_debug_json,
)
from packages.llm.shared.task_runtime.capabilities import effective_reasoning_effort


ProgressCallback = Callable[[int], None]


def stream_completion_text(
    *,
    model: str,
    messages: list[dict[str, object]],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> str:
    """Run a streaming LiteLLM completion and collect the final text."""
    reasoning_effort = effective_reasoning_effort(model, reasoning_effort)
    chunks: list[str] = []
    total_chars = 0
    started_at = time.perf_counter()
    request: dict[str, object] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if reasoning_effort is not None:
        request["reasoning_effort"] = reasoning_effort
    response = completion(**request)

    for chunk in response:
        delta = chunk["choices"][0]["delta"]
        content = delta.get("content")
        if isinstance(content, str):
            chunks.append(content)
            total_chars += len(content)
            if progress_callback is not None:
                progress_callback(total_chars)
        elif isinstance(content, Iterable):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
                        total_chars += len(text)
                        if progress_callback is not None:
                            progress_callback(total_chars)

    _ = time.perf_counter() - started_at
    return "".join(chunks).strip()


def completion_text(
    *,
    model: str,
    messages: list[dict[str, object]],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
    debug_dump_dir: str | None = None,
) -> str:
    """Run a non-streaming completion and return plain text content."""
    reasoning_effort = effective_reasoning_effort(model, reasoning_effort)
    started_at = time.perf_counter()
    request: dict[str, object] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if reasoning_effort is not None:
        request["reasoning_effort"] = reasoning_effort
    debug_dir = Path(debug_dump_dir) if debug_dump_dir is not None else None
    if debug_dir is not None:
        write_debug_json(
            debug_dir / "request.json",
            {
                "request": json_safe(request),
            },
        )

    attempts = 2
    last_error: Exception | None = None
    for attempt in range(attempts):
        response = completion(**request)
        if debug_dir is not None:
            write_debug_json(
                debug_dir / f"attempt_{attempt + 1}_response.json",
                response_debug_payload(response),
            )
        choice = response["choices"][0]["message"]
        refusal = choice.get("refusal")
        if refusal:
            raise ValueError(f"Completion refused: {refusal}")
        content = choice.get("content")
        try:
            _ = time.perf_counter() - started_at
            return parse_text_content(content)
        except Exception as error:
            if debug_dir is not None:
                write_debug_json(
                    debug_dir / f"attempt_{attempt + 1}_parse_error.json",
                    {
                        "error": str(error),
                        "content": json_safe(content),
                    },
                )
            if attempt == attempts - 1 or not is_empty_text_content_error(error):
                raise
            last_error = error

    assert last_error is not None
    raise last_error
