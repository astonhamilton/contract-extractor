from __future__ import annotations

from packages.schemas.common import BaseSchema


class TurnDetailResponse(BaseSchema):
    """Admin-facing detailed turn record."""

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
    provider_response_id: str | None = None
    provider_conversation_id: str | None = None
    usage: dict[str, object]
    error: dict[str, object]
    metadata: dict[str, object]
    execution_options: dict[str, object]
