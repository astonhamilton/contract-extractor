from __future__ import annotations

from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.commands.threads import delete_thread as delete_thread_row
from packages.data_store.llm_agent_runtime.queries.threads import get_thread


def delete_thread(db: SqliteDb, *, thread_id: str) -> None:
    """Delete one assistant thread when it is not actively running."""

    with db.connect() as connection:
        thread = get_thread(connection, thread_id)
        if thread is None:
            raise ValueError(f"Unknown thread: {thread_id}")
        if thread.active_turn_id:
            raise ValueError(f"Thread already has active turn: {thread_id}")
        delete_thread_row(connection, thread_id)
        connection.commit()
