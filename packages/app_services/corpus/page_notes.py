from __future__ import annotations

from packages.app_services.corpus.models import CorpusDocumentPageNotesPage, CorpusPageNoteItem
from packages.data_store.connect import SqliteDb
from packages.data_store.contract_intelligence.queries.documents import get_page_notes


def get_corpus_document_page_notes(
    db: SqliteDb,
    *,
    doc_id: str,
    page: int = 1,
    page_size: int = 10,
) -> CorpusDocumentPageNotesPage:
    """Return one paginated page-notes slice for a corpus document."""
    bounded_page = max(page, 1)
    bounded_page_size = max(1, min(page_size, 100))
    with db.connect() as connection:
        all_notes = get_page_notes(connection, doc_id)
        total = len(all_notes)
        start = (bounded_page - 1) * bounded_page_size
        end = start + bounded_page_size
        notes = all_notes[start:end]
        return CorpusDocumentPageNotesPage(
            items=[
                CorpusPageNoteItem(
                    page_number=note.page_number,
                    page_role=note.page_role,
                    summary=note.summary,
                    key_terms=note.key_terms,
                    relevance_tags=note.relevance_tags,
                    warnings=note.warnings,
                )
                for note in notes
            ],
            total=total,
            page=bounded_page,
            page_size=bounded_page_size,
        )
