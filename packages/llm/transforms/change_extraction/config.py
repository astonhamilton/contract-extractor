from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChangeExtractionConfig:
    """Static configuration for experimental change extraction."""

    model: str = "openai/gpt-5.4-mini"
    temperature: float = 1.0
    reasoning_effort: str | None = None
    structured_output: bool = True
    prompt_version: str = "change_extraction_v1"
    max_tokens: int = 4500
