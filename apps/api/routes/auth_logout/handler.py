from __future__ import annotations

from fastapi import Request

from apps.api.auth import clear_authenticated_user
from apps.api.routes.auth_logout.schema import AuthLogoutResponse


def auth_logout(request: Request) -> AuthLogoutResponse:
    """Clear the signed session cookie state for the current user."""

    clear_authenticated_user(request.session)
    return AuthLogoutResponse()
