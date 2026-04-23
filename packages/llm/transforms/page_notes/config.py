from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageNotesConfig:
    """Static configuration for experimental page-notes generation."""

    model: str = "openai/gpt-5.4-mini"
    temperature: float = 1.0
    reasoning_effort: str | None = None
    structured_output: bool = True
    prompt_version: str = "page_notes_v1"
    max_tokens: int = 2200
