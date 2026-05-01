from __future__ import annotations

from pydantic import Field

from packages.schemas.common import BaseSchema


class ThreadUpdateTitleRequest(BaseSchema):
    """Request payload for updating one thread title."""

    title: str = Field(min_length=1)


class ThreadUpdateTitleResponse(BaseSchema):
    """Updated thread shell returned after renaming one thread."""

    thread_id: str
    conversation_id: str
    current_thread_id: str
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
