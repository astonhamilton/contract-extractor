from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageOrientationDecisionConfig:
    """Static configuration for LLM image-orientation decisions."""

    model: str = "openai/gpt-5.4-nano"
    temperature: float = 1.0
    prompt_version: str = "image_orientation_v1"
    max_tokens: int = 500
    reasoning_effort: str | None = "none"
