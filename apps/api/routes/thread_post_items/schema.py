from __future__ import annotations

from typing import Literal

from pydantic import Field

from packages.schemas.common import BaseSchema


class ThreadPostItemRequest(BaseSchema):
    """One posted thread item."""

    type: Literal["message"]
    data: str = Field(min_length=1)


class ThreadPostItemsRequest(BaseSchema):
    """Request payload for posting new items into a thread."""

    items: list[ThreadPostItemRequest] = Field(min_length=1, max_length=1)


class ThreadPostItemsThreadResponse(BaseSchema):
    """Updated thread shell returned after posting input."""

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


class ThreadPostItemsTurnResponse(BaseSchema):
    """Enqueued-turn summary returned after posting input."""

    turn_id: str
    status: str
    phase: str


class ThreadPostItemsResponse(BaseSchema):
    """Response payload for accepted thread input."""

    thread: ThreadPostItemsThreadResponse
    turn: ThreadPostItemsTurnResponse
