from __future__ import annotations

from fastapi import Depends, Query

from apps.api.deps import get_contract_intelligence_db
from apps.api.routes.corpus_document_page_notes.schema import (
    CorpusDocumentPageNoteResponse,
    CorpusDocumentPageNotesQuery,
    CorpusDocumentPageNotesResponse,
)
from packages.app_services.corpus.page_notes import get_corpus_document_page_notes
from packages.data_store.connect import SqliteDb


def corpus_document_page_notes(
    doc_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: SqliteDb = Depends(get_contract_intelligence_db),
) -> CorpusDocumentPageNotesResponse:
    """Return paginated page notes for one corpus document."""

    query = CorpusDocumentPageNotesQuery(page=page, page_size=page_size)
    notes_page = get_corpus_document_page_notes(
        db,
        doc_id=doc_id,
        page=query.page,
        page_size=query.page_size,
    )
    return CorpusDocumentPageNotesResponse(
        items=[CorpusDocumentPageNoteResponse(**item.model_dump()) for item in notes_page.items],
        total=notes_page.total,
        page=notes_page.page,
        page_size=notes_page.page_size,
    )
