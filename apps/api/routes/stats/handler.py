from __future__ import annotations

import sqlite3
from pathlib import Path

from apps.api.routes.stats.schema import AppStatsResponse
from packages.data_store.connect import default_db

REPO_ROOT = Path(__file__).resolve().parents[4]


def _count(connection: sqlite3.Connection, table_or_view: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_or_view}").fetchone()
    return int(row["count"] if row is not None else 0)


def stats() -> AppStatsResponse:
    """Return useful API and contract-intelligence DB stats."""

    db = default_db(REPO_ROOT)
    if not db.exists():
        return AppStatsResponse(
            name="contract-intelligence-app",
            status="bootstrapped",
            db_available=False,
            db_path=str(db.path),
        )

    with db.connect() as connection:
        return AppStatsResponse(
            name="contract-intelligence-app",
            status="ready",
            db_available=True,
            db_path=str(db.path),
            db_size_mb=round(db.path.stat().st_size / (1024 * 1024), 2),
            document_count=_count(connection, "ci_documents"),
            page_count=_count(connection, "v_ci_document_pages_best"),
            page_note_count=_count(connection, "ci_page_notes"),
            governing_note_count=_count(connection, "ci_governing_notes"),
            change_note_count=_count(connection, "ci_change_notes"),
        )
