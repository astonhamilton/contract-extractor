from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkdownNormalizationConfig:
    """Static configuration for markdown normalization trial runs."""

    model: str = "openai/gpt-5.4-mini"
    temperature: float = 1.0
    prompt_version: str = "markdown_v1"
    max_tokens: int = 4000
