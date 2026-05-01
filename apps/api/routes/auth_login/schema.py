from __future__ import annotations

from pydantic import Field

from packages.schemas.common import BaseSchema


class AuthLoginRequest(BaseSchema):
    """Request payload for logging into the application."""

    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class AuthenticatedUserResponse(BaseSchema):
    """Transport-safe authenticated user payload."""

    email: str
    display_name: str
    group_name: str


class AuthLoginResponse(BaseSchema):
    """Successful login response."""

    authenticated: bool
    user: AuthenticatedUserResponse
