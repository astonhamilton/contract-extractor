from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import get_contract_intelligence_db
from apps.api.routes.corpus_document_notes.schema import CorpusDocumentNotesResponse
from packages.app_services.corpus.notes import get_corpus_document_notes
from packages.data_store.connect import SqliteDb


def corpus_document_notes(
    doc_id: str,
    db: SqliteDb = Depends(get_contract_intelligence_db),
) -> CorpusDocumentNotesResponse:
    """Return unified notes for one corpus document."""

    notes = get_corpus_document_notes(db, doc_id=doc_id)
    if notes is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return CorpusDocumentNotesResponse(**notes.model_dump())
