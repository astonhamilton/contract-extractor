from __future__ import annotations

import re
from pathlib import Path

from packages.app_services.corpus.models import CorpusDocumentListItem, CorpusDocumentsPage
from packages.data_store.connect import SqliteDb
from packages.data_store.contract_intelligence.queries.search import list_documents_page


def _humanize_filename(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[_-]+", " ", stem).strip()


def _overview_for_item(
    *,
    change_summary: str | None,
    governing_summary: str | None,
    what_is_being_bought: str | None,
) -> str:
    return (
        (change_summary or "").strip()
        or (governing_summary or "").strip()
        or (what_is_being_bought or "").strip()
    )


def build_corpus_documents_page(
    db: SqliteDb,
    *,
    query: str | None = None,
    sort: str = "name",
    page: int = 1,
    page_size: int = 25,
) -> CorpusDocumentsPage:
    """Build the paginated corpus browser list view."""
    with db.connect() as connection:
        items, total = list_documents_page(
            connection,
            query=query,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return CorpusDocumentsPage(
            items=[
                CorpusDocumentListItem(
                    doc_id=item.doc_id,
                    source_filename=item.source_filename,
                    title=_humanize_filename(item.source_filename),
                    overview=_overview_for_item(
                        change_summary=item.change_summary,
                        governing_summary=item.governing_summary,
                        what_is_being_bought=item.what_is_being_bought,
                    ),
                    page_count=item.page_count,
                    buyer=item.buyer,
                    seller=item.seller,
                    procurement_stage=item.procurement_stage,
                    primary_document_role=item.primary_document_role,
                    document_map_type=item.document_map_type,
                )
                for item in items
            ],
            total=total,
            page=max(page, 1),
            page_size=max(1, min(page_size, 100)),
            sort=sort,
            query=query or "",
        )
