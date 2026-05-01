from __future__ import annotations

from pathlib import Path

from fastapi import Depends, HTTPException, Request

from apps.api.auth import store_authenticated_user
from apps.api.deps import get_auth_users_path
from apps.api.routes.auth_login.schema import AuthLoginRequest, AuthLoginResponse
from apps.api.settings import ApiAuthSettings
from apps.api.routes.auth_login.schema import AuthenticatedUserResponse
from packages.app_services.auth.login import authenticate_user


def auth_login(
    request: Request,
    payload: AuthLoginRequest,
    users_path: Path = Depends(get_auth_users_path),
) -> AuthLoginResponse:
    """Authenticate one user and persist their signed session cookie."""

    settings = ApiAuthSettings.from_env()
    if not settings.enabled:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    client_host = request.client.host if request.client else "unknown"
    limiter = request.app.state.login_rate_limiter
    if not limiter.allow(client_host):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    try:
        result = authenticate_user(
            users_path,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as exc:
        limiter.record_failure(client_host)
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    limiter.reset(client_host)
    store_authenticated_user(request.session, result.user)
    return AuthLoginResponse(
        authenticated=True,
        user=AuthenticatedUserResponse(
            email=result.user.email,
            display_name=result.user.display_name,
            group_name=result.user.group_name,
        ),
    )
