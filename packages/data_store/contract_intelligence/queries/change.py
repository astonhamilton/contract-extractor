from __future__ import annotations

import sqlite3

from packages.data_store.contract_intelligence.models import (
    ChangeKeyClauseRecord,
    ChangeNotesRecord,
    CitationRecord,
    DocumentIndexItem,
)
from packages.data_store.contract_intelligence.queries.common import fetchall, fetchone, parse_json_list


def _citation_from_row(row: sqlite3.Row) -> CitationRecord:
    return CitationRecord(
        page_number=int(row["page_number"]),
        snippet=str(row["snippet"] or ""),
        stage=str(row["stage"]),
        domain=str(row["domain"]),
        clause_label=row["clause_label"],
        ordinal=int(row["ordinal"] or 0),
    )


def get_change_notes(connection: sqlite3.Connection, doc_id: str) -> ChangeNotesRecord | None:
    """Return change notes, key clauses, and citations for one document."""
    row = fetchone(
        connection,
        """
        SELECT *
        FROM ci_change_notes
        WHERE doc_id = ?
        """,
        (doc_id,),
    )
    if row is None:
        return None
    key_clause_rows = fetchall(
        connection,
        """
        SELECT label, summary, ordinal
        FROM ci_change_key_clauses
        WHERE doc_id = ?
        ORDER BY ordinal
        """,
        (doc_id,),
    )
    citation_rows = fetchall(
        connection,
        """
        SELECT *
        FROM ci_citations
        WHERE doc_id = ?
          AND stage = 'change_extraction'
        ORDER BY domain, ordinal, page_number
        """,
        (doc_id,),
    )
    return ChangeNotesRecord(
        doc_id=str(row["doc_id"]),
        target_artifact_answer=row["target_artifact_answer"],
        change_answer=row["change_answer"],
        resulting_state_answer=row["resulting_state_answer"],
        dimensions=[str(item) for item in parse_json_list(row["dimensions_json"])],
        quality_warnings=[str(item) for item in parse_json_list(row["quality_warnings_json"])],
        confidence=row["confidence"],
        key_clauses=[
            ChangeKeyClauseRecord(
                label=str(clause_row["label"]),
                summary=str(clause_row["summary"]),
                ordinal=int(clause_row["ordinal"] or 0),
            )
            for clause_row in key_clause_rows
        ],
        citations=[_citation_from_row(citation_row) for citation_row in citation_rows],
    )


def find_change_documents(
    connection: sqlite3.Connection,
    *,
    buyer: str | None = None,
    seller: str | None = None,
    dimension: str | None = None,
    limit: int = 50,
) -> list[DocumentIndexItem]:
    """Return likely change documents filtered by relationship fields and optional change dimension."""
    sql = """
        SELECT
            d.doc_id,
            d.source_filename,
            pc.buyer,
            pc.seller,
            pc.what_is_being_bought,
            pc.procurement_category,
            c.procurement_stage,
            c.primary_document_role,
            c.change_kind,
            NULL AS governing_summary,
            cn.change_answer AS change_summary
        FROM ci_documents AS d
        JOIN ci_classification AS c
            ON c.doc_id = d.doc_id
        LEFT JOIN ci_procurement_context AS pc
            ON pc.doc_id = d.doc_id
        LEFT JOIN ci_change_notes AS cn
            ON cn.doc_id = d.doc_id
        WHERE c.procurement_stage = 'active_change'
          AND c.primary_document_role = 'delta'
    """
    params: list[object] = []
    if buyer:
        sql += " AND pc.buyer = ?"
        params.append(buyer)
    if seller:
        sql += " AND pc.seller = ?"
        params.append(seller)
    if dimension:
        sql += " AND cn.dimensions_json LIKE ?"
        params.append(f'%"{dimension}"%')
    sql += " ORDER BY d.source_filename LIMIT ?"
    params.append(limit)
    return [DocumentIndexItem.model_validate(dict(row)) for row in fetchall(connection, sql, params)]
