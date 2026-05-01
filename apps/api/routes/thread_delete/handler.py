from __future__ import annotations

from fastapi import Depends, HTTPException, Response, status

from apps.api.deps import get_agent_runtime_db
from packages.app_services.chat_assistant.delete_thread import delete_thread as delete_thread_service
from packages.data_store.connect import SqliteDb


def thread_delete(
    thread_id: str,
    db: SqliteDb = Depends(get_agent_runtime_db),
) -> Response:
    """Delete one assistant thread."""

    try:
        delete_thread_service(db, thread_id=thread_id)
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Unknown thread:"):
            raise HTTPException(status_code=404, detail="Thread not found") from exc
        if message.startswith("Thread already has active turn:"):
            raise HTTPException(status_code=409, detail="Thread already has an active turn") from exc
        raise HTTPException(status_code=400, detail=message) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
