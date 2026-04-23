from __future__ import annotations

from packages.schemas.common import BaseSchema


class TurnSummaryResponse(BaseSchema):
    """Admin-facing summary of one assistant turn."""

    turn_id: str
    thread_id: str
    agent_id: str
    status: str
    phase: str
    queued_at: str
    started_at: str
    completed_at: str | None = None
    provider: str | None = None
    model: str | None = None
    claim_worker_id: str | None = None
    heartbeat_at: str | None = None


class ThreadTurnsResponse(BaseSchema):
    """Paginated assistant-turn list for one thread."""

    items: list[TurnSummaryResponse]
    total: int
    page: int
    page_size: int
