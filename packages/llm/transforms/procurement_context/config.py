from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcurementContextConfig:
    """Static configuration for experimental procurement-context inference."""

    model: str = "openai/gpt-5.4-mini"
    temperature: float = 1.0
    prompt_version: str = "procurement_context_v1"
    max_tokens: int = 3500
