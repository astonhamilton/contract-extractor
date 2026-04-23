from __future__ import annotations

from packages.data_store.connect import SqliteDb
from packages.data_store.contract_intelligence.models import DocumentIndexItem
from packages.data_store.contract_intelligence.queries.search import list_document_index


def get_corpus_index(
    db: SqliteDb,
) -> list[DocumentIndexItem]:
    """Return the full lightweight corpus index for assistant navigation."""
    with db.connect() as connection:
        return list_document_index(
            connection,
            limit=1_000_000,
            offset=0,
        )
