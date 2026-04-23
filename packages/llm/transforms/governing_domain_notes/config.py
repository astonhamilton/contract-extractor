from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoverningDomainNotesConfig:
    """Static configuration for experimental governing domain-notes extraction."""

    model: str = "openai/gpt-5.4-mini"
    temperature: float = 1.0
    reasoning_effort: str | None = None
    prompt_version: str = "governing_domain_notes_v1"
    max_tokens: int = 4500
