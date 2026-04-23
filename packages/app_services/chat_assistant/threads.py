from __future__ import annotations

import sqlite3

from packages.app_services.chat_assistant.models import ThreadList, ThreadListItem
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.queries.items import list_items
from packages.data_store.llm_agent_runtime.queries.threads import list_threads_page


def _title_or_default(title: str | None) -> str:
    return title.strip() if title and title.strip() else "Untitled thread"


def _preview_text(connection: sqlite3.Connection, thread_id: str) -> str:
    for item in reversed(list_items(connection, thread_id)):
        if item.content_text and item.content_text.strip():
            return item.content_text.strip()
    return ""


def get_threads(
    db: SqliteDb,
    *,
    thread_kind: str | None = "conversation",
    status: str | None = None,
    query: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> ThreadList:
    """Return assistant thread summaries for sidebar/admin views."""
    with db.connect() as connection:
        threads, total = list_threads_page(
            connection,
            thread_kind=thread_kind,
            status=status,
            query=query,
            page=page,
            page_size=page_size,
        )
        return ThreadList(
            items=[
                ThreadListItem(
                    thread_id=thread.thread_id,
                    thread_kind=thread.thread_kind,
                    agent_id=thread.agent_id,
                    title=_title_or_default(thread.title),
                    created_at=thread.created_at.isoformat(),
                    updated_at=thread.updated_at.isoformat(),
                    preview_text=_preview_text(connection, thread.thread_id),
                    status=thread.status,
                    phase=thread.phase,
                )
                for thread in threads
            ],
            total=total,
            page=max(page, 1),
            page_size=max(1, min(page_size, 100)),
        )
