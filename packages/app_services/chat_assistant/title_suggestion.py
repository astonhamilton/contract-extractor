from __future__ import annotations

from packages.schemas.common import BaseSchema
from packages.app_services.chat_assistant.thread_titles import generate_thread_title
from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService


class ThreadTitleSuggestion(BaseSchema):
    """Best-effort title suggestion for one user message."""

    title: str


def suggest_thread_title(
    db: SqliteDb,
    *,
    service: EmbeddedAgentRuntimeService,
    message: str,
) -> ThreadTitleSuggestion:
    """Return one best-effort generated thread title for a user message."""

    cleaned = " ".join(message.split()).strip()
    if not cleaned:
        raise ValueError("Message cannot be empty.")
    title = generate_thread_title(
        db=db,
        service=service,
        source_text=cleaned,
    )
    if title is None:
        raise ValueError("Unable to generate thread title.")
    return ThreadTitleSuggestion(title=title)
