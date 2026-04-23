from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from packages.data_store.contract_intelligence.models import DocumentIndexItem
from packages.data_store.contract_intelligence.queries.common import fetchall, fetchone
from packages.data_store.contract_intelligence.queries.common import parse_optional_bool


def _base_document_index_select() -> str:
    return """
        SELECT
            d.doc_id,
            d.source_filename,
            d.page_count,
            pc.buyer,
            pc.seller,
            pc.what_is_being_bought,
            pc.procurement_category,
            c.procurement_stage,
            c.primary_document_role,
            c.change_kind,
            CASE
                WHEN gn.doc_id IS NOT NULL THEN 'governing'
                WHEN cn.doc_id IS NOT NULL THEN 'change'
                ELSE NULL
            END AS document_map_type,
            gn.subject_answer AS governing_summary,
            cn.change_answer AS change_summary,
            CASE WHEN gn.doc_id IS NOT NULL THEN 1 ELSE 0 END AS has_governing_notes,
            CASE WHEN cn.doc_id IS NOT NULL THEN 1 ELSE 0 END AS has_change_notes,
            CASE WHEN pn.doc_id IS NOT NULL THEN 1 ELSE 0 END AS has_page_notes
        FROM ci_documents AS d
        LEFT JOIN ci_procurement_context AS pc
            ON pc.doc_id = d.doc_id
        LEFT JOIN ci_classification AS c
            ON c.doc_id = d.doc_id
        LEFT JOIN ci_governing_notes AS gn
            ON gn.doc_id = d.doc_id
        LEFT JOIN ci_change_notes AS cn
            ON cn.doc_id = d.doc_id
        LEFT JOIN (
            SELECT DISTINCT doc_id
            FROM ci_page_notes
        ) AS pn
            ON pn.doc_id = d.doc_id
    """


def _document_search_where(query: str | None) -> tuple[str, list[object]]:
    sql = " WHERE 1 = 1"
    params: list[object] = []
    if query:
        sql += """
            AND (
                d.source_filename LIKE ?
                OR pc.buyer LIKE ?
                OR pc.seller LIKE ?
                OR pc.what_is_being_bought LIKE ?
                OR gn.subject_answer LIKE ?
                OR cn.change_answer LIKE ?
            )
        """
        like_query = f"%{query}%"
        params.extend([like_query, like_query, like_query, like_query, like_query, like_query])
    return sql, params


def _document_index_item_from_row(row: sqlite3.Row) -> DocumentIndexItem:
    payload = dict(row)
    payload["has_governing_notes"] = parse_optional_bool(payload.get("has_governing_notes")) or False
    payload["has_change_notes"] = parse_optional_bool(payload.get("has_change_notes")) or False
    payload["has_page_notes"] = parse_optional_bool(payload.get("has_page_notes")) or False
    return DocumentIndexItem.model_validate(payload)


def _sort_sql(sort: str) -> str:
    lifecycle_order = """
        CASE COALESCE(c.procurement_stage, 'unclear')
            WHEN 'sourcing' THEN 1
            WHEN 'award' THEN 2
            WHEN 'contracting' THEN 3
            WHEN 'active_change' THEN 4
            WHEN 'compliance' THEN 5
            ELSE 6
        END
    """
    role_order = """
        CASE COALESCE(c.primary_document_role, 'context')
            WHEN 'operative' THEN 1
            WHEN 'delta' THEN 2
            WHEN 'context' THEN 3
            ELSE 4
        END
    """
    order_map = {
        "name": (
            "ORDER BY LOWER(d.source_filename), "
            f"{lifecycle_order}, {role_order}, d.doc_id"
        ),
        "page_count": (
            "ORDER BY d.page_count DESC, "
            f"{lifecycle_order}, {role_order}, LOWER(d.source_filename), d.doc_id"
        ),
        "seller": (
            "ORDER BY LOWER(COALESCE(pc.seller, '')), "
            f"{lifecycle_order}, {role_order}, LOWER(d.source_filename), d.doc_id"
        ),
        "buyer": (
            "ORDER BY LOWER(COALESCE(pc.buyer, '')), "
            f"{lifecycle_order}, {role_order}, LOWER(d.source_filename), d.doc_id"
        ),
    }
    return order_map.get(sort, order_map["name"])


def list_document_index(
    connection: sqlite3.Connection,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[DocumentIndexItem]:
    """Return a lightweight corpus index view over documents and their doc maps."""
    rows = fetchall(
        connection,
        f"""
        {_base_document_index_select()}
        ORDER BY LOWER(d.source_filename), d.doc_id
        LIMIT ?
        OFFSET ?
        """,
        (limit, offset),
    )
    return [_document_index_item_from_row(row) for row in rows]


def find_documents(
    connection: sqlite3.Connection,
    *,
    buyer: str | None = None,
    seller: str | None = None,
    query: str | None = None,
    procurement_stage: str | None = None,
    primary_document_role: str | None = None,
    change_kind: str | None = None,
    limit: int = 100,
) -> list[DocumentIndexItem]:
    """Return lightweight document search results for assistant/tool discovery."""
    sql = _base_document_index_select() + "\n WHERE 1 = 1"
    params: list[object] = []
    if buyer:
        sql += " AND pc.buyer = ?"
        params.append(buyer)
    if seller:
        sql += " AND pc.seller = ?"
        params.append(seller)
    if procurement_stage:
        sql += " AND c.procurement_stage = ?"
        params.append(procurement_stage)
    if primary_document_role:
        sql += " AND c.primary_document_role = ?"
        params.append(primary_document_role)
    if change_kind:
        sql += " AND c.change_kind = ?"
        params.append(change_kind)
    if query:
        sql += """
            AND (
                d.source_filename LIKE ?
                OR pc.buyer LIKE ?
                OR pc.seller LIKE ?
                OR pc.what_is_being_bought LIKE ?
                OR gn.subject_answer LIKE ?
                OR cn.change_answer LIKE ?
            )
        """
        like_query = f"%{query}%"
        params.extend([like_query, like_query, like_query, like_query, like_query, like_query])
    sql += " ORDER BY d.source_filename LIMIT ?"
    params.append(limit)
    return [_document_index_item_from_row(row) for row in fetchall(connection, sql, params)]


def list_documents_page(
    connection: sqlite3.Connection,
    *,
    query: str | None = None,
    sort: str = "name",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[DocumentIndexItem], int]:
    """Return one paginated/sorted corpus document page plus total match count."""

    bounded_page = max(page, 1)
    bounded_page_size = max(1, min(page_size, 100))
    offset = (bounded_page - 1) * bounded_page_size

    where_sql, params = _document_search_where(query)
    rows = fetchall(
        connection,
        f"""
        {_base_document_index_select()}
        {where_sql}
        {_sort_sql(sort)}
        LIMIT ?
        OFFSET ?
        """,
        [*params, bounded_page_size, offset],
    )
    total_row = fetchone(
        connection,
        f"""
        SELECT COUNT(*) AS count
        FROM ci_documents AS d
        LEFT JOIN ci_procurement_context AS pc
            ON pc.doc_id = d.doc_id
        LEFT JOIN ci_governing_notes AS gn
            ON gn.doc_id = d.doc_id
        LEFT JOIN ci_change_notes AS cn
            ON cn.doc_id = d.doc_id
        {where_sql}
        """,
        params,
    )
    total = int(total_row["count"] if total_row is not None else 0)
    return ([_document_index_item_from_row(row) for row in rows], total)
