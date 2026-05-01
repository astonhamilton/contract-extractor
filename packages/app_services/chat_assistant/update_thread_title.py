from __future__ import annotations

from packages.app_services.chat_assistant.models import ThreadDetail
from packages.app_services.chat_assistant.thread_detail import thread_detail_from_record
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.commands import update_thread
from packages.data_store.llm_agent_runtime.queries.threads import get_thread


def _normalized_title(title: str) -> str:
    """Return one validated thread title."""

    cleaned = " ".join(title.split()).strip()
    if not cleaned:
        raise ValueError("Thread title cannot be empty.")
    return cleaned


def update_thread_title(
    db: SqliteDb,
    *,
    thread_id: str,
    title: str,
) -> ThreadDetail:
    """Update one thread title and return the refreshed thread shell."""

    normalized_title = _normalized_title(title)
    with db.connect() as connection:
        thread = get_thread(connection, thread_id)
        if thread is None:
            raise ValueError(f"Unknown thread: {thread_id}")
        metadata = dict(thread.metadata)
        metadata["title"] = normalized_title
        updated_thread = update_thread(
            connection,
            thread.model_copy(update={"title": normalized_title, "metadata": metadata}),
        )
        connection.commit()
        return thread_detail_from_record(updated_thread)
