from __future__ import annotations

from packages.app_services.corpus.models import CorpusSummary
from packages.data_store.connect import SqliteDb
from packages.data_store.contract_intelligence.queries.summary import (
    get_document_count,
    get_raw_corpus_size_bytes,
)


def build_corpus_summary(db: SqliteDb) -> CorpusSummary:
    """Build the lightweight corpus summary used by the browser shell."""
    with db.connect() as connection:
        return CorpusSummary(
            document_count=get_document_count(connection),
            db_size_mb=round(db.path.stat().st_size / (1024 * 1024), 2),
            raw_corpus_size_mb=round(get_raw_corpus_size_bytes(connection) / (1024 * 1024), 2),
        )
