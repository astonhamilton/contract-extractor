from __future__ import annotations

from packages.schemas.common import BaseSchema


class AppStatsResponse(BaseSchema):
    """Useful startup stats proving the API can see the contract-intelligence DB."""

    name: str
    status: str
    db_available: bool
    db_path: str
    db_size_mb: float | None = None
    document_count: int | None = None
    page_count: int | None = None
    page_note_count: int | None = None
    governing_note_count: int | None = None
    change_note_count: int | None = None
