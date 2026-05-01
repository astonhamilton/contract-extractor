from __future__ import annotations

from fastapi import Depends

from apps.api.deps import get_authenticated_user_optional
from apps.api.routes.auth_session.schema import AuthSessionResponse
from apps.api.routes.auth_session.schema import AuthSessionUserResponse
from apps.api.settings import ApiAuthSettings
from packages.app_services.auth.models import AuthenticatedUser


def auth_session(
    user: AuthenticatedUser | None = Depends(get_authenticated_user_optional),
) -> AuthSessionResponse:
    """Return current session state for the browser client."""

    settings = ApiAuthSettings.from_env()
    return AuthSessionResponse(
        enabled=settings.enabled,
        authenticated=user is not None,
        user=None
        if user is None
        else AuthSessionUserResponse(
            email=user.email,
            display_name=user.display_name,
            group_name=user.group_name,
        ),
    )
