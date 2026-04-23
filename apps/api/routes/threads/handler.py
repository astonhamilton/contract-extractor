from __future__ import annotations

from fastapi import Depends, Query

from apps.api.deps import get_agent_runtime_db
from apps.api.routes.threads.schema import (
    ThreadListItemResponse,
    ThreadsQuery,
    ThreadsResponse,
)
from packages.app_services.chat_assistant.threads import get_threads
from packages.data_store.connect import SqliteDb


def threads(
    thread_kind: str = Query(default="conversation", pattern="^(conversation|task|all)$"),
    status: str | None = Query(default=None),
    query: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: SqliteDb = Depends(get_agent_runtime_db),
) -> ThreadsResponse:
    """Return assistant thread summaries."""

    params = ThreadsQuery(
        thread_kind=thread_kind,
        status=status,
        query=query,
        page=page,
        page_size=page_size,
    )
    thread_list = get_threads(
        db,
        thread_kind=None if params.thread_kind == "all" else params.thread_kind,
        status=params.status,
        query=params.query,
        page=params.page,
        page_size=params.page_size,
    )
    return ThreadsResponse(
        items=[ThreadListItemResponse(**item.model_dump()) for item in thread_list.items],
        total=thread_list.total,
        page=thread_list.page,
        page_size=thread_list.page_size,
    )
