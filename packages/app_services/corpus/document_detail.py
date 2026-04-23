from __future__ import annotations

import re
from pathlib import Path

from packages.app_services.corpus.models import CorpusDocumentDetail
from packages.data_store.connect import SqliteDb
from packages.data_store.contract_intelligence.queries.documents import get_document_aggregate


def _humanize_filename(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[_-]+", " ", stem).strip()


def _overview(
    *,
    change_answer: str | None,
    governing_subject_answer: str | None,
    what_is_being_bought: str | None,
) -> str:
    return (
        (change_answer or "").strip()
        or (governing_subject_answer or "").strip()
        or (what_is_being_bought or "").strip()
    )


def _document_map_type(
    *,
    has_governing_notes: bool,
    has_change_notes: bool,
) -> str | None:
    if has_governing_notes:
        return "governing"
    if has_change_notes:
        return "change"
    return None


def get_corpus_document_detail(
    db: SqliteDb,
    *,
    doc_id: str,
) -> CorpusDocumentDetail | None:
    """Return the initial selected-document detail for the corpus browser."""
    with db.connect() as connection:
        aggregate = get_document_aggregate(connection, doc_id)
        if aggregate is None:
            return None

        document = aggregate.document
        procurement = aggregate.procurement_context
        classification = aggregate.classification
        governing_notes = aggregate.governing_notes
        change_notes = aggregate.change_notes

        return CorpusDocumentDetail(
            document={
                "doc_id": document.doc_id,
                "title": _humanize_filename(document.source_filename),
                "source_filename": document.source_filename,
                "page_count": document.page_count,
            },
            overview={
                "summary": _overview(
                    change_answer=change_notes.change_answer if change_notes else None,
                    governing_subject_answer=governing_notes.subject_answer if governing_notes else None,
                    what_is_being_bought=procurement.what_is_being_bought if procurement else None,
                ),
                "document_map_type": _document_map_type(
                    has_governing_notes=governing_notes is not None,
                    has_change_notes=change_notes is not None,
                ),
                "supports_page_notes": len(aggregate.page_notes) > 0,
            },
            procurement_context={
                "buyer": procurement.buyer if procurement else None,
                "seller": procurement.seller if procurement else None,
                "what_is_being_bought": procurement.what_is_being_bought if procurement else None,
                "procurement_category": procurement.procurement_category if procurement else None,
            },
            classification={
                "procurement_stage": classification.procurement_stage if classification else None,
                "primary_document_role": classification.primary_document_role if classification else None,
                "change_kind": classification.change_kind if classification else None,
            },
        )
