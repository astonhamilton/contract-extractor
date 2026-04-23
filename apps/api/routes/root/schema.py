from __future__ import annotations

from packages.schemas.common import BaseSchema


class RootResponse(BaseSchema):
    """Simple root response for bootstrapped API checks."""

    name: str
    status: str
