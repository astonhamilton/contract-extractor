from __future__ import annotations

from packages.schemas.common import BaseSchema


class AuthSessionUserResponse(BaseSchema):
    """Transport-safe authenticated user payload."""

    email: str
    display_name: str
    group_name: str


class AuthSessionResponse(BaseSchema):
    """Current auth session state."""

    enabled: bool
    authenticated: bool
    user: AuthSessionUserResponse | None = None
