from __future__ import annotations

from packages.schemas.common import BaseSchema


class ThreadDetailResponse(BaseSchema):
    """Active/admin thread shell response."""

    thread_id: str
    thread_kind: str
    agent_id: str
    title: str
    created_at: str
    updated_at: str
    status: str
    phase: str
    active_turn_id: str | None = None
    last_turn_id: str | None = None
    execution_options: dict[str, object]
    metadata: dict[str, object]
