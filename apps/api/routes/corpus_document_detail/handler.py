from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import get_contract_intelligence_db
from apps.api.routes.corpus_document_detail.schema import CorpusDocumentDetailResponse
from packages.app_services.corpus.document_detail import get_corpus_document_detail
from packages.data_store.connect import SqliteDb


def corpus_document_detail(
    doc_id: str,
    db: SqliteDb = Depends(get_contract_intelligence_db),
) -> CorpusDocumentDetailResponse:
    """Return the initial selected-document detail for one corpus document."""
    detail = get_corpus_document_detail(db, doc_id=doc_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return CorpusDocumentDetailResponse(**detail.model_dump())
