from __future__ import annotations

from packages.schemas.common import BaseSchema


class AuthLogoutResponse(BaseSchema):
    """Successful logout response."""

    authenticated: bool = False
