from __future__ import annotations

from apps.api.routes.root.schema import RootResponse


def root() -> RootResponse:
    """Return a minimal bootstrapped response."""

    return RootResponse(name="contract-extractor", status="bootstrapped")
