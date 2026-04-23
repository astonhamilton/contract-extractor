from __future__ import annotations

from fastapi import Depends, HTTPException, Query

from apps.api.deps import get_agent_runtime_db
from apps.api.routes.thread_turns.schema import ThreadTurnsResponse, TurnSummaryResponse
from packages.app_services.chat_assistant.turns import get_thread_turns
from packages.data_store.connect import SqliteDb


def thread_turns(
    thread_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: SqliteDb = Depends(get_agent_runtime_db),
) -> ThreadTurnsResponse:
    """Return paginated admin-facing turns for one thread."""

    turns = get_thread_turns(
        db,
        thread_id=thread_id,
        page=page,
        page_size=page_size,
    )
    if turns is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadTurnsResponse(
        items=[TurnSummaryResponse(**item.model_dump()) for item in turns.items],
        total=turns.total,
        page=turns.page,
        page_size=turns.page_size,
    )
