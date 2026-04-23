from __future__ import annotations

from packages.schemas.common import BaseSchema


class ThreadItemsThreadResponse(BaseSchema):
    """Thread shell returned with one item page."""

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


class ThreadItemsLastTurnResponse(BaseSchema):
    """Most recent turn detail returned with one item page."""

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


class ThreadItemSummaryResponse(BaseSchema):
    """Compact semantic summary for one thread item."""

    title: str
    detail: str = ""


class ThreadItemRecordResponse(BaseSchema):
    """Normalized runtime item payload for transport."""

    item_id: str
    seq: int | None = None
    item_type: str
    role: str | None = None
    name: str | None = None
    content_text: str | None = None
    arguments: dict[str, object]
    result: dict[str, object]
    provider_item_id: str | None = None
    provider_item_type: str | None = None
    provider_payload: dict[str, object]
    metadata: dict[str, object]
    created_at: str


class ThreadItemResponse(BaseSchema):
    """Display-oriented thread item response."""

    summary: ThreadItemSummaryResponse
    record: ThreadItemRecordResponse


class ThreadItemsResponse(BaseSchema):
    """Paginated thread item timeline response."""

    thread: ThreadItemsThreadResponse
    active_turn: ThreadItemsLastTurnResponse | None = None
    last_turn: ThreadItemsLastTurnResponse | None = None
    items: list[ThreadItemResponse]
    total: int
    page: int
    page_size: int
