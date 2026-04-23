from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisionMarkdownNormalizationConfig:
    """Static configuration for vision-first markdown normalization."""

    model: str = "openai/gpt-5.4-nano"
    temperature: float = 1
    prompt_version: str = "vision_markdown_v1"
    max_tokens: int = 4000
