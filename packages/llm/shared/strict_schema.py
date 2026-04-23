from __future__ import annotations

from typing import Any


def enforce_openai_strict_required(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize a schema to OpenAI strict-mode object requirements.

    OpenAI strict structured outputs require every object node to list all property keys in
    `required`. They also reject sibling keywords alongside `$ref`.
    """

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_value = node["$ref"]
                node.clear()
                node["$ref"] = ref_value
                return

            properties = node.get("properties")
            if isinstance(properties, dict) and properties:
                node["required"] = list(properties.keys())
                node["additionalProperties"] = False

            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    copied = dict(schema)
    _walk(copied)
    return copied
