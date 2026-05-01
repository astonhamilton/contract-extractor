from __future__ import annotations

import sqlite3
from typing import Literal

from packages.data_store.llm_agent_runtime.common import thread_from_row
from packages.data_store.llm_agent_runtime.models import ThreadRecord


def get_thread(connection: sqlite3.Connection, thread_id: str) -> ThreadRecord | None:
    """Fetch one assistant thread by id."""
    row = connection.execute(
        "SELECT * FROM agent_runtime_threads WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    return None if row is None else thread_from_row(row)


def list_threads(
    connection: sqlite3.Connection,
    *,
    thread_kind: str | None = None,
) -> list[ThreadRecord]:
    """List assistant threads ordered by most recently updated."""
    if thread_kind is None:
        rows = connection.execute(
            "SELECT * FROM agent_runtime_threads ORDER BY updated_at DESC, created_at DESC",
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM agent_runtime_threads ORDER BY updated_at DESC, created_at DESC",
        ).fetchall()
    return [thread_from_row(row) for row in rows]


def list_threads_page(
    connection: sqlite3.Connection,
    *,
    thread_kind: str | None = None,
    status: str | None = None,
    query: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ThreadRecord], int]:
    """List assistant threads with optional filters and pagination."""
    bounded_page = max(page, 1)
    bounded_page_size = max(1, min(page_size, 100))
    clauses: list[str] = []
    params: list[object] = []
    # Newer runtime tables no longer store thread_kind; this backend exposes
    # runtime rows as conversation-compatible threads.
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if query:
        clauses.append("agent_id LIKE ?")
        like = f"%{query.strip()}%"
        params.append(like)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    count_row = connection.execute(
        f"SELECT COUNT(*) AS count FROM agent_runtime_threads {where_sql}",
        tuple(params),
    ).fetchone()
    total = int(count_row["count"] or 0) if count_row is not None else 0
    offset = (bounded_page - 1) * bounded_page_size
    rows = connection.execute(
        f"""
        SELECT *
        FROM agent_runtime_threads
        {where_sql}
        ORDER BY updated_at DESC, created_at DESC
        LIMIT ? OFFSET ?
        """,
        (*params, bounded_page_size, offset),
    ).fetchall()
    return [thread_from_row(row) for row in rows], total
