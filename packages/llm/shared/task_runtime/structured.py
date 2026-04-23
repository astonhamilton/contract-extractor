from __future__ import annotations

import time
from pathlib import Path

from litellm import completion

from packages.llm.shared.task_runtime._common import (
    is_empty_structured_content_error,
    json_safe,
    parse_json_content,
    response_debug_payload,
    write_debug_json,
)
from packages.llm.shared.task_runtime.capabilities import (
    effective_reasoning_effort,
    model_supports_strict_structured_output,
)


def validate_strict_json_schema(schema: dict[str, object], schema_name: str) -> None:
    """Validate JSON schema compatibility with OpenAI strict structured outputs."""
    violations: list[str] = []

    if schema.get("type") != "object":
        violations.append("Root schema must have type='object'.")
    if "anyOf" in schema:
        violations.append("Root schema must not use anyOf.")

    def _walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                sibling_keys = sorted(key for key in node.keys() if key != "$ref")
                if sibling_keys:
                    violations.append(
                        f"{path}: $ref must not have sibling keywords {sibling_keys}."
                    )
            properties = node.get("properties")
            if isinstance(properties, dict):
                if node.get("additionalProperties") is not False:
                    violations.append(f"{path}: additionalProperties must be false.")
                required = node.get("required")
                if not isinstance(required, list):
                    violations.append(f"{path}: required must be a list.")
                else:
                    property_keys = set(properties.keys())
                    required_keys = set(key for key in required if isinstance(key, str))
                    missing = sorted(property_keys - required_keys)
                    extra = sorted(required_keys - property_keys)
                    if missing:
                        violations.append(f"{path}: required missing keys {missing}.")
                    if extra:
                        violations.append(f"{path}: required has unknown keys {extra}.")

            for key, value in node.items():
                _walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")

    _walk(schema, "root")

    if violations:
        max_items = 10
        details = "; ".join(violations[:max_items])
        if len(violations) > max_items:
            details = f"{details}; ... ({len(violations) - max_items} more)"
        raise ValueError(
            f"Schema '{schema_name}' is not strict-mode compatible: {details}"
        )


def completion_json_schema(
    *,
    model: str,
    messages: list[dict[str, object]],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
    schema_name: str,
    schema: dict[str, object],
    debug_dump_dir: str | None = None,
) -> dict[str, object]:
    """Run a non-streaming completion with JSON-schema constrained output."""
    reasoning_effort = effective_reasoning_effort(model, reasoning_effort)
    if not model_supports_strict_structured_output(model):
        raise ValueError(
            "Strict structured output in this experiment is only enabled for openai/* or anthropic/* models. "
            f"Received model={model!r}."
        )
    validate_strict_json_schema(schema, schema_name)
    started_at = time.perf_counter()
    request: dict[str, object] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "schema": schema,
                "strict": True,
            },
        },
        "stream": False,
    }
    if reasoning_effort is not None:
        request["reasoning_effort"] = reasoning_effort
    debug_dir = Path(debug_dump_dir) if debug_dump_dir is not None else None
    if debug_dir is not None:
        write_debug_json(
            debug_dir / "request.json",
            {
                "schema_name": schema_name,
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
            raise ValueError(f"Structured completion for '{schema_name}' refused: {refusal}")
        content = choice.get("content")
        try:
            _ = time.perf_counter() - started_at
            return parse_json_content(content, schema_name=schema_name)
        except Exception as error:
            if debug_dir is not None:
                write_debug_json(
                    debug_dir / f"attempt_{attempt + 1}_parse_error.json",
                    {
                        "schema_name": schema_name,
                        "error": str(error),
                        "content": json_safe(content),
                    },
                )
            if attempt == attempts - 1 or not is_empty_structured_content_error(error):
                raise
            last_error = error

    assert last_error is not None
    raise last_error
