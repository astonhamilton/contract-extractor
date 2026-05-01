from __future__ import annotations

import json
from pathlib import Path

from packages.data_store.auth.models import AuthUserRecord, AuthUsersFile


def load_auth_users(path: Path) -> list[AuthUserRecord]:
    """Load all configured auth users from disk."""

    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AuthUsersFile.model_validate(payload).users


def get_auth_user_by_email(path: Path, *, email: str) -> AuthUserRecord | None:
    """Return one configured auth user by normalized email."""

    normalized_email = email.strip().lower()
    for user in load_auth_users(path):
        if user.email.strip().lower() == normalized_email:
            return user
    return None


def get_auth_user_by_key(path: Path, *, user_key: str) -> AuthUserRecord | None:
    """Return one configured auth user by opaque user key."""

    for user in load_auth_users(path):
        if user.user_key == user_key:
            return user
    return None
