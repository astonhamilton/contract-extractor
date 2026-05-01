from __future__ import annotations

import sqlite3

from packages.data_store.llm_agent_runtime.common import item_from_row
from packages.data_store.llm_agent_runtime.models import ItemRecord


def list_items(connection: sqlite3.Connection, thread_id: str) -> list[ItemRecord]:
    """List persisted thread items in sequence order."""
    rows = connection.execute(
        "SELECT * FROM agent_runtime_items WHERE thread_id = ? ORDER BY seq",
        (thread_id,),
    ).fetchall()
    return [item_from_row(row) for row in rows]


def list_items_page(
    connection: sqlite3.Connection,
    *,
    thread_id: str,
    page: int = 1,
    page_size: int = 50,
    item_type: str | None = None,
) -> tuple[list[ItemRecord], int]:
    """List paginated thread items with optional kind filtering."""
    bounded_page = max(page, 1)
    bounded_page_size = max(1, min(page_size, 100))
    clauses = ["thread_id = ?"]
    params: list[object] = [thread_id]
    if item_type:
        clauses.append("item_type = ?")
        params.append(item_type)
    where_sql = " AND ".join(clauses)
    count_row = connection.execute(
        f"SELECT COUNT(*) AS count FROM agent_runtime_items WHERE {where_sql}",
        tuple(params),
    ).fetchone()
    total = int(count_row["count"] or 0) if count_row is not None else 0
    offset = (bounded_page - 1) * bounded_page_size
    rows = connection.execute(
        f"""
        SELECT *
        FROM agent_runtime_items
        WHERE {where_sql}
        ORDER BY seq DESC
        LIMIT ? OFFSET ?
        """,
        (*params, bounded_page_size, offset),
    ).fetchall()
    return [item_from_row(row) for row in rows], total


def list_items_after(
    connection: sqlite3.Connection,
    thread_id: str,
    *,
    after_seq: int,
) -> list[ItemRecord]:
    """List persisted thread items strictly after one sequence cursor."""

    rows = connection.execute(
        "SELECT * FROM agent_runtime_items WHERE thread_id = ? AND seq > ? ORDER BY seq",
        (thread_id, after_seq),
    ).fetchall()
    return [item_from_row(row) for row in rows]


def max_item_seq(connection: sqlite3.Connection, thread_id: str) -> int:
    """Return the current maximum item sequence for one thread."""

    row = connection.execute(
        "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM agent_runtime_items WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    if row is None:
        return 0
    return int(row["max_seq"] or 0)
