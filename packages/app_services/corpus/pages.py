from __future__ import annotations

from packages.app_services.corpus.models import (
    CorpusDocumentPageDetail,
    CorpusDocumentPagesPage,
    CorpusPageContent,
    CorpusPageListItem,
    CorpusPageNoteItem,
)
from packages.data_store.connect import SqliteDb
from packages.data_store.contract_intelligence.queries.documents import (
    get_document,
    get_document_page_variants,
    get_document_pages,
    get_page_notes,
)


def _preview(content: str, limit: int = 360) -> str:
    compact = " ".join(content.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def get_corpus_document_pages(
    db: SqliteDb,
    *,
    doc_id: str,
    page: int = 1,
    page_size: int = 10,
) -> CorpusDocumentPagesPage | None:
    """Return a paginated page index for one document."""
    with db.connect() as connection:
        document = get_document(connection, doc_id)
        if document is None:
            return None

        bounded_page = max(page, 1)
        bounded_page_size = max(1, min(page_size, 100))

        best_pages = get_document_pages(connection, doc_id)
        variants = get_document_page_variants(connection, doc_id)
        page_notes = get_page_notes(connection, doc_id)

        variant_map: dict[int, list[str]] = {}
        for variant in variants:
            representation = variant.representation or ""
            if not representation:
                continue
            bucket = variant_map.setdefault(variant.page_number, [])
            if representation not in bucket:
                bucket.append(representation)

        page_note_numbers = {note.page_number for note in page_notes}

        total = len(best_pages)
        start = (bounded_page - 1) * bounded_page_size
        end = start + bounded_page_size
        page_slice = best_pages[start:end]

        return CorpusDocumentPagesPage(
            items=[
                CorpusPageListItem(
                    page_number=page_record.page_number,
                    best_representation=page_record.representation,
                    available_representations=[
                        *variant_map.get(page_record.page_number, []),
                        *(["page_notes"] if page_record.page_number in page_note_numbers else []),
                    ],
                    estimated_tokens=page_record.estimated_tokens,
                    preview=_preview(page_record.content),
                    page_note_available=page_record.page_number in page_note_numbers,
                )
                for page_record in page_slice
            ],
            total=total,
            page=bounded_page,
            page_size=bounded_page_size,
        )


def _page_content_from_best(page_record) -> CorpusPageContent:
    return CorpusPageContent(
        representation=page_record.representation,
        source_path=page_record.source_path,
        content=page_record.content,
        extraction_method=page_record.extraction_method,
        char_count=page_record.char_count,
        ocr_confidence=page_record.ocr_confidence,
        warnings=page_record.warnings,
        quality_flags=page_record.quality_flags,
        estimated_tokens=page_record.estimated_tokens,
        priority=None,
        page_role=None,
        key_terms=[],
        relevance_tags=[],
    )


def _page_content_from_variant(page_record) -> CorpusPageContent:
    return CorpusPageContent(
        representation=page_record.representation,
        source_path=page_record.source_path,
        content=page_record.content,
        extraction_method=page_record.extraction_method,
        char_count=page_record.char_count,
        ocr_confidence=page_record.ocr_confidence,
        warnings=page_record.warnings,
        quality_flags=page_record.quality_flags,
        estimated_tokens=page_record.estimated_tokens,
        priority=page_record.priority,
        page_role=None,
        key_terms=[],
        relevance_tags=[],
    )


def _page_content_from_note(page_note: CorpusPageNoteItem) -> CorpusPageContent:
    return CorpusPageContent(
        representation="page_notes",
        source_path=None,
        content=page_note.summary,
        extraction_method="page_notes",
        char_count=len(page_note.summary),
        ocr_confidence=None,
        warnings=page_note.warnings,
        quality_flags=[],
        estimated_tokens=0,
        priority=None,
        page_role=page_note.page_role,
        key_terms=page_note.key_terms,
        relevance_tags=page_note.relevance_tags,
    )


def get_corpus_document_page_detail(
    db: SqliteDb,
    *,
    doc_id: str,
    page_number: int,
    include_variants: bool = False,
) -> CorpusDocumentPageDetail | None:
    """Return the full detail for one document page."""
    with db.connect() as connection:
        document = get_document(connection, doc_id)
        if document is None:
            return None

        best_pages = get_document_pages(connection, doc_id, page_numbers=[page_number])
        if not best_pages:
            return None
        best_page = best_pages[0]

        page_note_rows = get_page_notes(connection, doc_id, page_numbers=[page_number])
        page_note = None
        if page_note_rows:
            note = page_note_rows[0]
            page_note = CorpusPageNoteItem(
                page_number=note.page_number,
                page_role=note.page_role,
                summary=note.summary,
                key_terms=note.key_terms,
                relevance_tags=note.relevance_tags,
                warnings=note.warnings,
            )

        variant_rows = get_document_page_variants(connection, doc_id, page_numbers=[page_number])
        available_representations: list[str] = []
        for variant in variant_rows:
            representation = variant.representation or ""
            if representation and representation not in available_representations:
                available_representations.append(representation)
        if page_note is not None and "page_notes" not in available_representations:
            available_representations.append("page_notes")

        return CorpusDocumentPageDetail(
            page=CorpusPageListItem(
                page_number=best_page.page_number,
                best_representation=best_page.representation,
                available_representations=available_representations,
                estimated_tokens=best_page.estimated_tokens,
                preview=_preview(best_page.content),
                page_note_available=page_note is not None,
            ),
            best_content=_page_content_from_best(best_page),
            variants=(
                [
                    _page_content_from_variant(variant)
                    for variant in variant_rows
                    if variant.representation != best_page.representation
                ]
                + ([_page_content_from_note(page_note)] if page_note is not None else [])
            )
            if include_variants
            else [],
        )
