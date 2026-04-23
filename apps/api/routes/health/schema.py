from __future__ import annotations

from packages.schemas.common import BaseSchema


class HealthResponse(BaseSchema):
    """Basic liveness response for the API process."""

    status: str
