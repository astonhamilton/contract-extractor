from __future__ import annotations

from fastapi import Depends, HTTPException, Query

from apps.api.deps import get_agent_runtime_db
from apps.api.routes.thread_items.schema import (
    ThreadItemRecordResponse,
    ThreadItemResponse,
    ThreadItemsLastTurnResponse,
    ThreadItemSummaryResponse,
    ThreadItemsThreadResponse,
    ThreadItemsResponse,
)
from packages.app_services.chat_assistant.items import get_thread_items
from packages.data_store.connect import SqliteDb


def thread_items(
    thread_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    item_type: str | None = Query(default=None, max_length=100),
    db: SqliteDb = Depends(get_agent_runtime_db),
) -> ThreadItemsResponse:
    """Return the display-oriented item timeline for one thread."""

    items = get_thread_items(
        db,
        thread_id=thread_id,
        page=page,
        page_size=page_size,
        item_type=item_type,
    )
    if items is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadItemsResponse(
        thread=ThreadItemsThreadResponse(**items.thread.model_dump()),
        active_turn=(
            None
            if items.active_turn is None
            else ThreadItemsLastTurnResponse(**items.active_turn.model_dump())
        ),
        last_turn=(
            None
            if items.last_turn is None
            else ThreadItemsLastTurnResponse(**items.last_turn.model_dump())
        ),
        items=[
            ThreadItemResponse(
                summary=ThreadItemSummaryResponse(**item.summary.model_dump()),
                record=ThreadItemRecordResponse(**item.record.model_dump()),
            )
            for item in items.items
        ],
        total=items.total,
        page=items.page,
        page_size=items.page_size,
    )
