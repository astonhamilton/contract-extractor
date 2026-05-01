from __future__ import annotations

from packages.schemas.common import BaseSchema


class AuthUserRecord(BaseSchema):
    """One configured application user loaded from the JSON user store."""

    user_key: str
    email: str
    password_hash: str
    hashed: bool = True
    display_name: str
    group_name: str
    disabled: bool = False


class AuthUsersFile(BaseSchema):
    """JSON file shape for the application user store."""

    users: list[AuthUserRecord]
