from __future__ import annotations

from packages.schemas.common import BaseSchema


class ModelCallSummaryResponse(BaseSchema):
    """Admin-facing summary of one model call."""

    model_call_id: str
    turn_id: str
    thread_id: str
    ordinal: int
    provider: str | None = None
    model: str | None = None
    status: str
    started_at: str
    completed_at: str | None = None
    worker_id: str | None = None
    heartbeat_at: str | None = None


class TurnModelCallsResponse(BaseSchema):
    """Paginated model-call list for one turn."""

    items: list[ModelCallSummaryResponse]
    total: int
    page: int
    page_size: int
