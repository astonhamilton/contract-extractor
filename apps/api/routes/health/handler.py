from __future__ import annotations

from apps.api.routes.health.schema import HealthResponse


def health() -> HealthResponse:
    """Return a minimal liveness signal."""

    return HealthResponse(status="ok")
