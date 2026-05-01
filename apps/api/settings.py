from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_API_AUTH_SESSION_SECRET = "development-only-change-me"


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


@dataclass
class ApiAuthSettings:
    """Configuration for lightweight application authentication."""

    enabled: bool = False
    session_secret: str = DEFAULT_API_AUTH_SESSION_SECRET
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    session_idle_timeout_seconds: int = 60 * 60 * 24 * 2
    session_refresh_interval_seconds: int = 60 * 15
    cookie_secure: bool = False
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60 * 5

    @classmethod
    def from_env(cls) -> "ApiAuthSettings":
        """Load auth settings from environment variables."""

        session_max_age_raw = os.getenv("API_AUTH_SESSION_MAX_AGE_SECONDS")
        session_idle_timeout_raw = os.getenv("API_AUTH_SESSION_IDLE_TIMEOUT_SECONDS")
        session_refresh_interval_raw = os.getenv("API_AUTH_SESSION_REFRESH_INTERVAL_SECONDS")
        attempts_raw = os.getenv("API_AUTH_LOGIN_RATE_LIMIT_ATTEMPTS")
        window_raw = os.getenv("API_AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS")
        return cls(
            enabled=env_flag("ENABLE_API_AUTH", default=False),
            session_secret=os.getenv("API_AUTH_SESSION_SECRET")
            or DEFAULT_API_AUTH_SESSION_SECRET,
            session_max_age_seconds=(
                60 * 60 * 24 * 7 if session_max_age_raw is None else int(session_max_age_raw)
            ),
            session_idle_timeout_seconds=(
                60 * 60 * 24 * 2
                if session_idle_timeout_raw is None
                else int(session_idle_timeout_raw)
            ),
            session_refresh_interval_seconds=(
                60 * 15
                if session_refresh_interval_raw is None
                else int(session_refresh_interval_raw)
            ),
            cookie_secure=env_flag("API_AUTH_COOKIE_SECURE", default=False),
            login_rate_limit_attempts=5 if attempts_raw is None else int(attempts_raw),
            login_rate_limit_window_seconds=60 * 5 if window_raw is None else int(window_raw),
        )
