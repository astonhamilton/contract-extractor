from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import get_agent_runtime_db
from apps.api.routes.thread_detail.schema import ThreadDetailResponse
from packages.app_services.chat_assistant.thread_detail import get_thread_detail
from packages.data_store.connect import SqliteDb


def thread_detail(
    thread_id: str,
    db: SqliteDb = Depends(get_agent_runtime_db),
) -> ThreadDetailResponse:
    """Return the active thread shell."""

    detail = get_thread_detail(db, thread_id=thread_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadDetailResponse(**detail.model_dump())
