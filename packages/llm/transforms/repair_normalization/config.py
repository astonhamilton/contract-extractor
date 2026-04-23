from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairNormalizationConfig:
    """Static configuration for repair normalization trial runs."""

    model: str = "openai/gpt-5.4-mini"
    temperature: float = 1.0
    prompt_version: str = "repair_v2"
    max_tokens: int = 3000
