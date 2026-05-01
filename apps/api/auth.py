from __future__ import annotations

import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from apps.api.settings import ApiAuthSettings
from packages.app_services.auth.models import AuthenticatedUser


SESSION_USER_KEY = "auth_user_key"
SESSION_ISSUED_AT_KEY = "auth_issued_at"
SESSION_LAST_ACTIVE_AT_KEY = "auth_last_active_at"


class LoginRateLimiter:
    """Small in-memory login rate limiter keyed by client IP."""

    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Return whether another login attempt is currently allowed."""

        now = time.time()
        with self._lock:
            bucket = self._attempts.setdefault(key, deque())
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            return len(bucket) < self.max_attempts

    def record_failure(self, key: str) -> None:
        """Record one failed login attempt for an IP key."""

        with self._lock:
            self._attempts.setdefault(key, deque()).append(time.time())

    def reset(self, key: str) -> None:
        """Clear recorded failures for one IP key after successful login."""

        with self._lock:
            self._attempts.pop(key, None)


def auth_users_path(repo_root: Path) -> Path:
    """Return the runtime JSON user-store path."""

    return repo_root / "data" / "private" / "auth_users.json"


def build_login_rate_limiter(settings: ApiAuthSettings) -> LoginRateLimiter:
    """Return the API-owned login rate limiter."""

    return LoginRateLimiter(
        max_attempts=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )


def install_session_middleware(app, settings: ApiAuthSettings) -> None:
    """Install signed cookie session support onto the FastAPI app."""

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=settings.cookie_secure,
        max_age=settings.session_max_age_seconds,
        session_cookie="ci_session",
    )


def is_exempt_auth_path(path: str) -> bool:
    """Return whether a path is public and should bypass auth checks."""

    return (
        path == "/api/health"
        or path.startswith("/api/auth/")
        or path == "/docs"
        or path == "/openapi.json"
        or path.startswith("/redoc")
    )


def is_api_path(path: str) -> bool:
    """Return whether a path should receive JSON auth failures."""

    return (
        path == "/api"
        or path.startswith("/api/")
        or path == "/stats"
        or path.startswith("/threads")
        or path.startswith("/turns")
        or path.startswith("/corpus/")
    )


def is_protected_path(path: str) -> bool:
    """Return whether a path requires authentication."""

    if is_exempt_auth_path(path):
        return False
    return is_api_path(path)


def _utc_now() -> datetime:
    """Return the current UTC time."""

    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    """Return one UTC timestamp as ISO-8601 text."""

    return value.isoformat()


def _parse_session_time(raw_value: object) -> datetime | None:
    """Parse one stored ISO session timestamp."""

    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def store_authenticated_user(session: dict, user: AuthenticatedUser) -> None:
    """Persist minimal authenticated user state into the signed session."""

    now = _utc_now()
    session[SESSION_USER_KEY] = user.user_key
    session[SESSION_ISSUED_AT_KEY] = _isoformat(now)
    session[SESSION_LAST_ACTIVE_AT_KEY] = _isoformat(now)


def refresh_authenticated_session(session: dict) -> None:
    """Advance the signed-session last-active timestamp."""

    session[SESSION_LAST_ACTIVE_AT_KEY] = _isoformat(_utc_now())


def clear_authenticated_user(session: dict) -> None:
    """Remove authenticated user state from the signed session."""

    session.pop(SESSION_USER_KEY, None)
    session.pop(SESSION_ISSUED_AT_KEY, None)
    session.pop(SESSION_LAST_ACTIVE_AT_KEY, None)


def session_user_key(session: dict) -> str | None:
    """Return the opaque authenticated user key from one session."""

    raw_value = session.get(SESSION_USER_KEY)
    return raw_value if isinstance(raw_value, str) and raw_value else None


def session_is_valid(session: dict, settings: ApiAuthSettings) -> bool:
    """Return whether one signed session satisfies absolute and idle limits."""

    issued_at = _parse_session_time(session.get(SESSION_ISSUED_AT_KEY))
    last_active_at = _parse_session_time(session.get(SESSION_LAST_ACTIVE_AT_KEY))
    if issued_at is None or last_active_at is None:
        return False
    now = _utc_now()
    if (now - issued_at).total_seconds() > settings.session_max_age_seconds:
        return False
    if (now - last_active_at).total_seconds() > settings.session_idle_timeout_seconds:
        return False
    return True


def should_refresh_session(session: dict, settings: ApiAuthSettings) -> bool:
    """Return whether the signed session should be reissued on this request."""

    last_active_at = _parse_session_time(session.get(SESSION_LAST_ACTIVE_AT_KEY))
    if last_active_at is None:
        return False
    return (
        _utc_now() - last_active_at
    ).total_seconds() >= settings.session_refresh_interval_seconds


def unauthenticated_api_response() -> JSONResponse:
    """Return the standard JSON response for unauthenticated API access."""

    return JSONResponse(status_code=401, content={"detail": "Authentication required."})


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Backend-enforced auth middleware that expects `SessionMiddleware` upstream."""

    async def dispatch(self, request, call_next):
        from apps.api.deps import get_auth_users_path
        from packages.app_services.auth.session import resolve_authenticated_user

        settings = ApiAuthSettings.from_env()
        if not settings.enabled:
            return await call_next(request)

        path = request.url.path
        if not is_protected_path(path):
            return await call_next(request)

        if "session" not in request.scope:
            raise RuntimeError(
                "AuthenticationMiddleware requires SessionMiddleware to run first."
            )

        if not session_is_valid(request.session, settings):
            clear_authenticated_user(request.session)
            return unauthenticated_api_response()

        users_path = get_auth_users_path()
        user = resolve_authenticated_user(
            users_path,
            user_key=session_user_key(request.session),
        )
        request.state.authenticated_user = user
        if user is None:
            clear_authenticated_user(request.session)
            return unauthenticated_api_response()

        if should_refresh_session(request.session, settings):
            refresh_authenticated_session(request.session)
        return await call_next(request)
