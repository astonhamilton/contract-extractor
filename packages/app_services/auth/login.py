from __future__ import annotations

from pathlib import Path

from packages.app_services.auth.models import AuthLoginResult, AuthenticatedUser
from packages.app_services.auth.passwords import verify_password
from packages.data_store.auth.users import get_auth_user_by_email


def authenticate_user(
    users_path: Path,
    *,
    email: str,
    password: str,
) -> AuthLoginResult:
    """Authenticate one configured user against the JSON user store."""

    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        raise ValueError("Email and password are required.")
    record = get_auth_user_by_email(users_path, email=normalized_email)
    if record is None or record.disabled:
        raise ValueError("Invalid email or password.")
    if not verify_password(password, record.password_hash):
        raise ValueError("Invalid email or password.")
    return AuthLoginResult(
        user=AuthenticatedUser(
            user_key=record.user_key,
            email=record.email,
            display_name=record.display_name,
            group_name=record.group_name,
        )
    )
