from __future__ import annotations

from fastapi import Depends

from apps.api.deps import get_contract_intelligence_db
from apps.api.routes.corpus_summary.schema import CorpusSummaryResponse
from packages.app_services.corpus.summary import build_corpus_summary
from packages.data_store.connect import SqliteDb


def corpus_summary(
    db: SqliteDb = Depends(get_contract_intelligence_db),
) -> CorpusSummaryResponse:
    """Return product-facing corpus summary information."""
    summary = build_corpus_summary(db)
    return CorpusSummaryResponse(**summary.model_dump())
