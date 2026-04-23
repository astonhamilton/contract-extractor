from __future__ import annotations

import os
from dataclasses import dataclass


def env_flag(name: str, *, default: bool) -> bool:
    """Parse one boolean environment flag."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class EmbeddedAgentRuntimeSettings:
    """Configuration for the embedded API worker."""

    enabled: bool = True
    poll_interval_seconds: float = 0.5
    max_turns: int = 25
    max_steps: int = 200
    event_pretty: bool = True
    event_jsonl: bool = True
    default_provider: str | None = None
    default_model: str | None = None

    @classmethod
    def from_env(cls) -> "EmbeddedAgentRuntimeSettings":
        """Load embedded-worker settings from environment variables."""
        poll_interval_raw = os.getenv("EMBEDDED_AGENT_WORKER_POLL_INTERVAL_SECONDS")
        max_turns_raw = os.getenv("EMBEDDED_AGENT_WORKER_MAX_TURNS")
        max_steps_raw = os.getenv("EMBEDDED_AGENT_WORKER_MAX_STEPS")
        return cls(
            enabled=env_flag("ENABLE_EMBEDDED_AGENT_WORKER", default=True),
            poll_interval_seconds=0.5 if poll_interval_raw is None else float(poll_interval_raw),
            max_turns=25 if max_turns_raw is None else int(max_turns_raw),
            max_steps=200 if max_steps_raw is None else int(max_steps_raw),
            event_pretty=env_flag("ENABLE_EMBEDDED_AGENT_WORKER_EVENT_PRETTY", default=True),
            event_jsonl=env_flag("ENABLE_EMBEDDED_AGENT_WORKER_EVENT_JSONL", default=True),
            default_provider=os.getenv("EMBEDDED_AGENT_WORKER_PROVIDER") or None,
            default_model=os.getenv("EMBEDDED_AGENT_WORKER_MODEL") or None,
        )


@dataclass
class ApiSettings:
    """Configuration for API-only development helpers."""

    enable_debug_delay: bool = True
    max_debug_delay_ms: int = 5000

    @classmethod
    def from_env(cls) -> "ApiSettings":
        """Load API settings from environment variables."""

        max_debug_delay_raw = os.getenv("API_MAX_DEBUG_DELAY_MS")
        return cls(
            enable_debug_delay=env_flag("ENABLE_API_DEBUG_DELAY", default=True),
            max_debug_delay_ms=(
                5000 if max_debug_delay_raw is None else int(max_debug_delay_raw)
            ),
        )
