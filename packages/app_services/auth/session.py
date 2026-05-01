from __future__ import annotations

from pathlib import Path

from packages.app_services.auth.models import AuthSessionState, AuthenticatedUser
from packages.data_store.auth.users import get_auth_user_by_key


def resolve_authenticated_user(
    users_path: Path,
    *,
    user_key: str | None,
) -> AuthenticatedUser | None:
    """Resolve one authenticated user from persisted session identity."""

    if not user_key:
        return None
    record = get_auth_user_by_key(users_path, user_key=user_key)
    if record is None or record.disabled:
        return None
    return AuthenticatedUser(
        user_key=record.user_key,
        email=record.email,
        display_name=record.display_name,
        group_name=record.group_name,
    )


def build_session_state(
    users_path: Path,
    *,
    user_key: str | None,
) -> AuthSessionState:
    """Build current session state from one optional user email."""

    user = resolve_authenticated_user(users_path, user_key=user_key)
    return AuthSessionState(
        authenticated=user is not None,
        user=user,
    )
