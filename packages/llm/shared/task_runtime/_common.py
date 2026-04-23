from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EMPTY_STRUCTURED_CONTENT_MARKER = "returned empty string content"
EMPTY_TEXT_CONTENT_MARKER = "returned empty text content"


def parse_json_content(content: object, *, schema_name: str) -> dict[str, object]:
    """Parse structured model content into a JSON object or raise a useful error."""
    if isinstance(content, dict):
        return content

    if isinstance(content, str):
        text = content.strip()
        if not text:
            raise ValueError(
                f"Structured completion for '{schema_name}' returned empty string content."
            )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            preview = text[:300]
            raise ValueError(
                f"Structured completion for '{schema_name}' returned non-JSON string content: {preview!r}"
            ) from error
        if not isinstance(parsed, dict):
            raise ValueError(
                f"Structured completion for '{schema_name}' returned JSON that was not an object."
            )
        return parsed

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
                elif item.get("type") == "output_text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
        if text_parts:
            return parse_json_content("".join(text_parts), schema_name=schema_name)

    raise ValueError(
        f"Structured completion for '{schema_name}' returned unsupported content type: {type(content).__name__}"
    )


def is_empty_structured_content_error(error: Exception) -> bool:
    """Return True when a structured completion failed only because content was empty."""
    return isinstance(error, ValueError) and EMPTY_STRUCTURED_CONTENT_MARKER in str(error)


def is_empty_text_content_error(error: Exception) -> bool:
    """Return True when a text completion failed only because content was empty."""
    return isinstance(error, ValueError) and EMPTY_TEXT_CONTENT_MARKER in str(error)


def json_safe(value: Any) -> Any:
    """Convert nested values into JSON-serializable debug payloads."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return json_safe(model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return json_safe(value.dict())
    if hasattr(value, "__dict__"):
        return json_safe(vars(value))
    return repr(value)


def extract_response_headers(response: Any) -> dict[str, Any] | None:
    """Best-effort extraction of raw response headers from LiteLLM/OpenAI objects."""
    for attr_name in ("_response_headers", "response_headers", "headers"):
        value = getattr(response, attr_name, None)
        if value:
            return json_safe(value)

    hidden_params = getattr(response, "_hidden_params", None)
    if isinstance(hidden_params, dict):
        for key in ("response_headers", "headers", "additional_headers"):
            value = hidden_params.get(key)
            if value:
                return json_safe(value)
    return None


def write_debug_json(path: Path, payload: dict[str, Any]) -> None:
    """Write one debug payload to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def response_debug_payload(response: Any) -> dict[str, Any]:
    """Build a structured debug payload from a LiteLLM completion response."""
    payload: dict[str, Any] = {
        "response_type": type(response).__name__,
        "response": json_safe(response),
    }
    hidden_params = getattr(response, "_hidden_params", None)
    if hidden_params is not None:
        payload["hidden_params"] = json_safe(hidden_params)
    headers = extract_response_headers(response)
    if headers is not None:
        payload["headers"] = headers
    return payload


def parse_text_content(content: object) -> str:
    """Parse plain model content into one string or raise a useful error."""
    if isinstance(content, str):
        text = content.strip()
        if not text:
            raise ValueError(f"Completion returned {EMPTY_TEXT_CONTENT_MARKER}.")
        return text

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
                elif item.get("type") == "output_text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
        text = "".join(text_parts).strip()
        if not text:
            raise ValueError(f"Completion returned {EMPTY_TEXT_CONTENT_MARKER}.")
        return text

    raise ValueError(f"Completion returned unsupported content type: {type(content).__name__}")
