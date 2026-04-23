from __future__ import annotations

from packages.schemas.common import BaseSchema


class CorpusSummaryResponse(BaseSchema):
    """Top-level corpus summary used by the corpus browser shell."""

    document_count: int
    db_size_mb: float
    raw_corpus_size_mb: float
