from __future__ import annotations

from packages.data_store.llm_agent_runtime.models import ThreadRecord
from packages.app_services.chat_assistant.models import ThreadDetail
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.queries.threads import get_thread


def _title_or_default(title: str | None, metadata: dict[str, object] | None = None) -> str:
    metadata_title = None if metadata is None else metadata.get("title")
    candidate = title if title and title.strip() else metadata_title
    return candidate.strip() if isinstance(candidate, str) and candidate.strip() else "Untitled thread"


def thread_detail_from_record(thread: ThreadRecord) -> ThreadDetail:
    """Return the app-service thread detail shape from one thread record."""
    return ThreadDetail(
        thread_id=thread.thread_id,
        conversation_id=thread.thread_id,
        current_thread_id=thread.thread_id,
        thread_kind=thread.thread_kind,
        agent_id=thread.agent_id,
        title=_title_or_default(thread.title, thread.metadata),
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        status=thread.status,
        phase=thread.phase,
        active_turn_id=thread.active_turn_id,
        last_turn_id=thread.last_turn_id,
        execution_options=thread.execution_options.model_dump(mode="json"),
        metadata=thread.metadata,
    )


def get_thread_detail(db: SqliteDb, *, thread_id: str) -> ThreadDetail | None:
    """Return the display-shaped shell for one assistant thread."""
    with db.connect() as connection:
        thread = get_thread(connection, thread_id)
        if thread is None:
            return None
        return thread_detail_from_record(thread)
