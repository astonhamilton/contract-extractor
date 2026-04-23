from __future__ import annotations

from packages.schemas.common import BaseSchema


class ThreadListItem(BaseSchema):
    """Sidebar-ready assistant thread summary."""

    thread_id: str
    thread_kind: str
    agent_id: str
    title: str
    created_at: str
    updated_at: str
    preview_text: str = ""
    status: str
    phase: str


class ThreadList(BaseSchema):
    """Ordered assistant thread list."""

    items: list[ThreadListItem]
    total: int
    page: int
    page_size: int


class ThreadDetail(BaseSchema):
    """Thread shell for the active thread view."""

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


class ThreadInputItem(BaseSchema):
    """One app-service input item posted into a thread."""

    type: str
    data: str


class CreateThreadResult(BaseSchema):
    """Result from creating one thread and optionally enqueueing one turn."""

    thread: ThreadDetail
    turn: EnqueuedTurnSummary | None = None


class EnqueuedTurnSummary(BaseSchema):
    """Minimal enqueued-turn summary returned after posting input."""

    turn_id: str
    status: str
    phase: str


class PostThreadItemsResult(BaseSchema):
    """Result from posting new input items into a thread."""

    thread: ThreadDetail
    turn: EnqueuedTurnSummary


class ThreadItemSummary(BaseSchema):
    """Compact semantic summary for one thread item."""

    title: str
    detail: str = ""


class ThreadItemRecordView(BaseSchema):
    """Transport-safe normalized runtime item payload."""

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


class ThreadItemView(BaseSchema):
    """Display-oriented thread item."""

    summary: ThreadItemSummary
    record: ThreadItemRecordView


class ThreadItemsPage(BaseSchema):
    """Paginated thread item timeline."""

    thread: ThreadDetail
    active_turn: TurnDetail | None = None
    last_turn: TurnDetail | None = None
    items: list[ThreadItemView]
    total: int
    page: int
    page_size: int


class TurnSummary(BaseSchema):
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


class ThreadTurnsPage(BaseSchema):
    """Paginated turn list for one thread."""

    items: list[TurnSummary]
    total: int
    page: int
    page_size: int


class TurnDetail(BaseSchema):
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


class ModelCallSummary(BaseSchema):
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


class ModelCallsPage(BaseSchema):
    """Paginated model-call list for one turn."""

    items: list[ModelCallSummary]
    total: int
    page: int
    page_size: int


class ToolInvocationSummary(BaseSchema):
    """Admin-facing summary of one tool invocation."""

    tool_invocation_id: str
    turn_id: str | None = None
    thread_id: str
    model_call_id: str | None = None
    tool_name: str
    status: str
    started_at: str
    completed_at: str | None = None
    worker_id: str | None = None
    heartbeat_at: str | None = None
    error_text: str | None = None


class ToolInvocationsPage(BaseSchema):
    """Paginated tool-invocation list for one turn."""

    items: list[ToolInvocationSummary]
    total: int
    page: int
    page_size: int
