from __future__ import annotations

from fastapi import Depends, HTTPException, Query

from apps.api.deps import get_contract_intelligence_db
from apps.api.routes.corpus_document_page_detail.schema import (
    CorpusDocumentPageDetailContentResponse,
    CorpusDocumentPageDetailPageResponse,
    CorpusDocumentPageDetailResponse,
)
from packages.app_services.corpus.pages import get_corpus_document_page_detail
from packages.data_store.connect import SqliteDb


def corpus_document_page_detail(
    doc_id: str,
    page_number: int,
    include_variants: bool = Query(default=False),
    db: SqliteDb = Depends(get_contract_intelligence_db),
) -> CorpusDocumentPageDetailResponse:
    """Return full detail for one document page."""

    detail = get_corpus_document_page_detail(
        db,
        doc_id=doc_id,
        page_number=page_number,
        include_variants=include_variants,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Document page not found")
    return CorpusDocumentPageDetailResponse(
        page=CorpusDocumentPageDetailPageResponse(**detail.page.model_dump()),
        best_content=CorpusDocumentPageDetailContentResponse(**detail.best_content.model_dump()),
        variants=[
            CorpusDocumentPageDetailContentResponse(**variant.model_dump())
            for variant in detail.variants
        ],
    )
