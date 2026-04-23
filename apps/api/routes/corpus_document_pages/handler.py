from __future__ import annotations

from fastapi import Depends, HTTPException, Query

from apps.api.deps import get_contract_intelligence_db
from apps.api.routes.corpus_document_pages.schema import (
    CorpusDocumentPageResponse,
    CorpusDocumentPagesQuery,
    CorpusDocumentPagesResponse,
)
from packages.app_services.corpus.pages import get_corpus_document_pages
from packages.data_store.connect import SqliteDb


def corpus_document_pages(
    doc_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: SqliteDb = Depends(get_contract_intelligence_db),
) -> CorpusDocumentPagesResponse:
    """Return paginated pages for one corpus document."""

    query = CorpusDocumentPagesQuery(page=page, page_size=page_size)
    pages = get_corpus_document_pages(
        db,
        doc_id=doc_id,
        page=query.page,
        page_size=query.page_size,
    )
    if pages is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return CorpusDocumentPagesResponse(
        items=[CorpusDocumentPageResponse(**item.model_dump()) for item in pages.items],
        total=pages.total,
        page=pages.page,
        page_size=pages.page_size,
    )
