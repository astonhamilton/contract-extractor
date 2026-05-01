from __future__ import annotations

from typing import Literal

from packages.schemas.common import BaseSchema


class ThreadListItemResponse(BaseSchema):
    """Sidebar/admin thread summary response."""

    thread_id: str
    conversation_id: str
    current_thread_id: str
    thread_kind: str
    agent_id: str
    title: str
    created_at: str
    updated_at: str
    preview_text: str = ""
    status: str
    phase: str


class ThreadsResponse(BaseSchema):
    """Paginated assistant thread list response."""

    items: list[ThreadListItemResponse]
    total: int
    page: int
    page_size: int


class ThreadsQuery(BaseSchema):
    """Validated query params for listing threads."""

    thread_kind: Literal["conversation", "task", "all"] = "conversation"
    status: str | None = None
    query: str | None = None
    page: int = 1
    page_size: int = 50
