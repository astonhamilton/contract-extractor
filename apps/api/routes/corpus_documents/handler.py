from __future__ import annotations

from fastapi import Depends, Query

from apps.api.deps import get_contract_intelligence_db
from apps.api.routes.corpus_documents.schema import (
    CorpusDocumentListItemResponse,
    CorpusDocumentsQuery,
    CorpusDocumentsResponse,
)
from packages.app_services.corpus.documents import build_corpus_documents_page
from packages.data_store.connect import SqliteDb


def corpus_documents(
    q: str = Query(default=""),
    sort: str = Query(default="name"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: SqliteDb = Depends(get_contract_intelligence_db),
) -> CorpusDocumentsResponse:
    """Return the paginated corpus browser list."""
    query = CorpusDocumentsQuery(q=q, sort=sort, page=page, page_size=page_size)
    documents_page = build_corpus_documents_page(
        db,
        query=query.q or None,
        sort=query.sort,
        page=query.page,
        page_size=query.page_size,
    )
    return CorpusDocumentsResponse(
        items=[
            CorpusDocumentListItemResponse(**item.model_dump())
            for item in documents_page.items
        ],
        total=documents_page.total,
        page=documents_page.page,
        page_size=documents_page.page_size,
    )
