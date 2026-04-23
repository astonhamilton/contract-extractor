from __future__ import annotations

from packages.schemas.common import BaseSchema


class ToolInvocationSummaryResponse(BaseSchema):
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


class TurnToolInvocationsResponse(BaseSchema):
    """Paginated tool-invocation list for one turn."""

    items: list[ToolInvocationSummaryResponse]
    total: int
    page: int
    page_size: int
