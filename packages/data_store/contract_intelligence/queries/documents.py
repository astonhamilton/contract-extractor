from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from packages.data_store.contract_intelligence.models import (
    ClassificationRecord,
    DocumentAggregate,
    DocumentRecord,
    PageNoteRecord,
    PageRecord,
    PageVariantRecord,
    ProcurementContextRecord,
)
from packages.data_store.contract_intelligence.queries.common import (
    fetchall,
    fetchone,
    parse_json_list,
    parse_optional_bool,
    where_in_clause,
)


def _document_from_row(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        doc_id=str(row["doc_id"]),
        source_filename=str(row["source_filename"]),
        source_pdf_path=str(row["source_pdf_path"]),
        source_pdf_size_bytes=int(row["source_pdf_size_bytes"])
        if row["source_pdf_size_bytes"] is not None
        else None,
        sha256=row["sha256"],
        page_count=int(row["page_count"]),
        has_text_layer=parse_optional_bool(row["has_text_layer"]),
        quality_flags=[str(item) for item in parse_json_list(row["quality_flags_json"])],
        processing_status=row["processing_status"],
        normalized_document_path=row["normalized_document_path"],
    )


def _procurement_from_row(row: sqlite3.Row | None) -> ProcurementContextRecord | None:
    if row is None:
        return None
    return ProcurementContextRecord(
        doc_id=str(row["doc_id"]),
        is_procurement_related=parse_optional_bool(row["is_procurement_related"]),
        buyer=row["buyer"],
        seller=row["seller"],
        what_is_being_bought=row["what_is_being_bought"],
        procurement_category=row["procurement_category"],
        context_summary=row["context_summary"],
        warnings=[str(item) for item in parse_json_list(row["warnings_json"])],
        confidence=row["confidence"],
    )


def _classification_from_row(row: sqlite3.Row | None) -> ClassificationRecord | None:
    if row is None:
        return None
    return ClassificationRecord(
        doc_id=str(row["doc_id"]),
        procurement_stage=str(row["procurement_stage"]),
        primary_document_role=str(row["primary_document_role"]),
        change_kind=row["change_kind"],
        confidence=float(row["confidence"]),
        rationale=str(row["rationale"] or ""),
        evidence_pages=[int(item) for item in parse_json_list(row["evidence_pages_json"])],
        warnings=[str(item) for item in parse_json_list(row["warnings_json"])],
    )


def _page_from_row(row: sqlite3.Row) -> PageRecord:
    return PageRecord(
        doc_id=str(row["doc_id"]),
        page_number=int(row["page_number"]),
        content=str(row["content"] or ""),
        representation=row["representation"],
        source_path=row["source_path"],
        extraction_method=row["extraction_method"],
        char_count=int(row["char_count"] or 0),
        ocr_char_count=int(row["ocr_char_count"] or 0),
        ocr_confidence=row["ocr_confidence"],
        warnings=[str(item) for item in parse_json_list(row["warnings_json"])],
        quality_flags=[str(item) for item in parse_json_list(row["quality_flags_json"])],
        estimated_tokens=int(row["estimated_tokens"] or 0),
    )


def _page_variant_from_row(row: sqlite3.Row) -> PageVariantRecord:
    return PageVariantRecord(
        **_page_from_row(row).model_dump(),
        priority=int(row["priority"]),
    )


def _page_note_from_row(row: sqlite3.Row) -> PageNoteRecord:
    return PageNoteRecord(
        doc_id=str(row["doc_id"]),
        page_number=int(row["page_number"]),
        page_role=row["page_role"],
        summary=str(row["summary"] or ""),
        key_terms=[str(item) for item in parse_json_list(row["key_terms_json"])],
        relevance_tags=[str(item) for item in parse_json_list(row["relevance_tags_json"])],
        warnings=[str(item) for item in parse_json_list(row["warnings_json"])],
    )


def get_document(connection: sqlite3.Connection, doc_id: str) -> DocumentRecord | None:
    """Return one document metadata record."""
    row = fetchone(
        connection,
        """
        SELECT *
        FROM ci_documents
        WHERE doc_id = ?
        """,
        (doc_id,),
    )
    if row is None:
        return None
    return _document_from_row(row)


def get_document_pages(
    connection: sqlite3.Connection,
    doc_id: str,
    *,
    page_numbers: Sequence[int] | None = None,
) -> list[PageRecord]:
    """Return best-page records for a document, optionally scoped to specific pages."""
    sql = """
        SELECT *
        FROM v_ci_document_pages_best
        WHERE doc_id = ?
    """
    params: list[object] = [doc_id]
    if page_numbers:
        clause, extra = where_in_clause("page_number", [int(value) for value in page_numbers])
        sql += f" AND {clause}"
        params.extend(extra)
    sql += " ORDER BY page_number"
    return [_page_from_row(row) for row in fetchall(connection, sql, params)]


def get_document_page_variants(
    connection: sqlite3.Connection,
    doc_id: str,
    *,
    page_numbers: Sequence[int] | None = None,
) -> list[PageVariantRecord]:
    """Return all normalized page variants for a document."""
    sql = """
        SELECT *
        FROM ci_document_page_variants
        WHERE doc_id = ?
    """
    params: list[object] = [doc_id]
    if page_numbers:
        clause, extra = where_in_clause("page_number", [int(value) for value in page_numbers])
        sql += f" AND {clause}"
        params.extend(extra)
    sql += " ORDER BY page_number, priority, representation"
    return [_page_variant_from_row(row) for row in fetchall(connection, sql, params)]


def get_page_notes(
    connection: sqlite3.Connection,
    doc_id: str,
    *,
    page_numbers: Sequence[int] | None = None,
) -> list[PageNoteRecord]:
    """Return page notes for a document, optionally scoped to specific pages."""
    sql = """
        SELECT *
        FROM ci_page_notes
        WHERE doc_id = ?
    """
    params: list[object] = [doc_id]
    if page_numbers:
        clause, extra = where_in_clause("page_number", [int(value) for value in page_numbers])
        sql += f" AND {clause}"
        params.extend(extra)
    sql += " ORDER BY page_number"
    return [_page_note_from_row(row) for row in fetchall(connection, sql, params)]


def get_document_aggregate(connection: sqlite3.Connection, doc_id: str) -> DocumentAggregate | None:
    """Return the document-centered aggregate used by the assistant/tool layer."""
    document = get_document(connection, doc_id)
    if document is None:
        return None

    procurement_row = fetchone(
        connection,
        "SELECT * FROM ci_procurement_context WHERE doc_id = ?",
        (doc_id,),
    )
    classification_row = fetchone(
        connection,
        "SELECT * FROM ci_classification WHERE doc_id = ?",
        (doc_id,),
    )

    from packages.data_store.contract_intelligence.queries.change import get_change_notes
    from packages.data_store.contract_intelligence.queries.governing import get_governing_notes

    return DocumentAggregate(
        document=document,
        procurement_context=_procurement_from_row(procurement_row),
        classification=_classification_from_row(classification_row),
        governing_notes=get_governing_notes(connection, doc_id),
        change_notes=get_change_notes(connection, doc_id),
        page_notes=get_page_notes(connection, doc_id),
    )
