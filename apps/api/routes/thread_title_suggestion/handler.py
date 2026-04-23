from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import (
    get_agent_runtime_db,
    get_embedded_agent_runtime_service,
)
from apps.api.routes.thread_title_suggestion.schema import (
    ThreadTitleSuggestionRequest,
    ThreadTitleSuggestionResponse,
)
from packages.app_services.chat_assistant.title_suggestion import suggest_thread_title
from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService


def thread_title_suggestion(
    request: ThreadTitleSuggestionRequest,
    db: SqliteDb = Depends(get_agent_runtime_db),
    service: EmbeddedAgentRuntimeService = Depends(get_embedded_agent_runtime_service),
) -> ThreadTitleSuggestionResponse:
    """Return one best-effort generated title for a user message."""

    try:
        result = suggest_thread_title(
            db,
            service=service,
            message=request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ThreadTitleSuggestionResponse(**result.model_dump())
