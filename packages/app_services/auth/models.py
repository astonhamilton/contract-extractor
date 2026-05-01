from __future__ import annotations

from packages.schemas.common import BaseSchema


class AuthenticatedUser(BaseSchema):
    """Authenticated application user available to handlers and services."""

    user_key: str
    email: str
    display_name: str
    group_name: str


class AuthLoginResult(BaseSchema):
    """Successful login result."""

    user: AuthenticatedUser


class AuthSessionState(BaseSchema):
    """Current browser session state."""

    authenticated: bool
    user: AuthenticatedUser | None = None
