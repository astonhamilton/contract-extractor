from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentClassificationConfig:
    """Static configuration for experimental document classification."""

    model: str = "openai/gpt-5.4-mini"
    temperature: float = 1.0
    reasoning_effort: str = "medium"
    prompt_version: str = "document_classification_v1"
    max_tokens: int = 2500
