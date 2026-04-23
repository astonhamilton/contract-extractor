from __future__ import annotations

import sqlite3

from packages.data_store.contract_intelligence.queries.common import fetchone


def get_document_count(connection: sqlite3.Connection) -> int:
    """Return the total number of documents in the contract-intelligence DB."""

    row = fetchone(
        connection,
        """
        SELECT COUNT(*) AS count
        FROM ci_documents
        """,
    )
    return int(row["count"] if row is not None else 0)


def get_raw_corpus_size_bytes(connection: sqlite3.Connection) -> int:
    """Return the total raw PDF size across the source corpus."""

    row = fetchone(
        connection,
        """
        SELECT COALESCE(SUM(source_pdf_size_bytes), 0) AS total_bytes
        FROM ci_documents
        """,
    )
    return int(row["total_bytes"] if row is not None else 0)
