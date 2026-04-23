from __future__ import annotations

import sqlite3

from packages.data_store.contract_intelligence.models import (
    CitationRecord,
    DocumentIndexItem,
    GoverningNotesRecord,
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


def get_governing_notes(connection: sqlite3.Connection, doc_id: str) -> GoverningNotesRecord | None:
    """Return governing notes and citations for one document."""
    row = fetchone(
        connection,
        """
        SELECT *
        FROM ci_governing_notes
        WHERE doc_id = ?
        """,
        (doc_id,),
    )
    if row is None:
        return None
    citations = [
        _citation_from_row(citation_row)
        for citation_row in fetchall(
            connection,
            """
            SELECT *
            FROM ci_citations
            WHERE doc_id = ?
              AND stage = 'governing_domain_notes'
            ORDER BY domain, ordinal, page_number
            """,
            (doc_id,),
        )
    ]
    return GoverningNotesRecord(
        doc_id=str(row["doc_id"]),
        identity_answer=row["identity_answer"],
        parties_answer=row["parties_answer"],
        subject_answer=row["subject_answer"],
        term_answer=row["term_answer"],
        economics_answer=row["economics_answer"],
        controls_answer=row["controls_answer"],
        quality_warnings=[str(item) for item in parse_json_list(row["quality_warnings_json"])],
        confidence=row["confidence"],
        citations=citations,
    )


def find_governing_documents(
    connection: sqlite3.Connection,
    *,
    buyer: str | None = None,
    seller: str | None = None,
    limit: int = 50,
) -> list[DocumentIndexItem]:
    """Return likely governing documents filtered by procurement relationship fields."""
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
            gn.subject_answer AS governing_summary,
            NULL AS change_summary
        FROM ci_documents AS d
        JOIN ci_classification AS c
            ON c.doc_id = d.doc_id
        LEFT JOIN ci_procurement_context AS pc
            ON pc.doc_id = d.doc_id
        LEFT JOIN ci_governing_notes AS gn
            ON gn.doc_id = d.doc_id
        WHERE c.procurement_stage = 'contracting'
          AND c.primary_document_role = 'operative'
    """
    params: list[object] = []
    if buyer:
        sql += " AND pc.buyer = ?"
        params.append(buyer)
    if seller:
        sql += " AND pc.seller = ?"
        params.append(seller)
    sql += " ORDER BY d.source_filename LIMIT ?"
    params.append(limit)
    return [DocumentIndexItem.model_validate(dict(row)) for row in fetchall(connection, sql, params)]
