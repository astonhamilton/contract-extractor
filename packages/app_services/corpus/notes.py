from __future__ import annotations

from packages.app_services.corpus.models import (
    CorpusAnswerNote,
    CorpusChangeNotes,
    CorpusChangeSection,
    CorpusChangeKeyClause,
    CorpusCitationItem,
    CorpusDocumentNotes,
    CorpusGoverningNotes,
    CorpusQualitySection,
)
from packages.data_store.connect import SqliteDb
from packages.data_store.contract_intelligence.queries.documents import get_document
from packages.data_store.contract_intelligence.queries.change import get_change_notes
from packages.data_store.contract_intelligence.queries.governing import get_governing_notes


def _citations_for_domain(citations, domain: str) -> list[CorpusCitationItem]:
    return [
        CorpusCitationItem(
            page_number=citation.page_number,
            snippet=citation.snippet,
            clause_label=citation.clause_label,
        )
        for citation in citations
        if citation.domain == domain or str(citation.domain).startswith(f"{domain}.")
    ]


def get_corpus_document_notes(
    db: SqliteDb,
    *,
    doc_id: str,
) -> CorpusDocumentNotes | None:
    """Return unified document-map notes for one document."""
    with db.connect() as connection:
        document = get_document(connection, doc_id)
        if document is None:
            return None

        governing_notes = get_governing_notes(connection, doc_id)
        if governing_notes is not None:
            return CorpusDocumentNotes(
                document_map_type="governing",
                governing_notes=CorpusGoverningNotes(
                    identity=CorpusAnswerNote(
                        answer=governing_notes.identity_answer,
                        citations=_citations_for_domain(governing_notes.citations, "identity"),
                    ),
                    parties=CorpusAnswerNote(
                        answer=governing_notes.parties_answer,
                        citations=_citations_for_domain(governing_notes.citations, "parties"),
                    ),
                    subject=CorpusAnswerNote(
                        answer=governing_notes.subject_answer,
                        citations=_citations_for_domain(governing_notes.citations, "subject"),
                    ),
                    term=CorpusAnswerNote(
                        answer=governing_notes.term_answer,
                        citations=_citations_for_domain(governing_notes.citations, "term"),
                    ),
                    economics=CorpusAnswerNote(
                        answer=governing_notes.economics_answer,
                        citations=_citations_for_domain(governing_notes.citations, "economics"),
                    ),
                    controls=CorpusAnswerNote(
                        answer=governing_notes.controls_answer,
                        citations=_citations_for_domain(governing_notes.citations, "controls"),
                    ),
                    quality=CorpusAnswerNote(
                        answer=(
                            "\n".join(governing_notes.quality_warnings)
                            if governing_notes.quality_warnings
                            else None
                        ),
                        citations=_citations_for_domain(governing_notes.citations, "quality"),
                    ),
                ),
                change_notes=None,
            )

        change_notes = get_change_notes(connection, doc_id)
        if change_notes is not None:
            return CorpusDocumentNotes(
                document_map_type="change",
                governing_notes=None,
                change_notes=CorpusChangeNotes(
                    target_artifact=CorpusAnswerNote(
                        answer=change_notes.target_artifact_answer,
                        citations=_citations_for_domain(change_notes.citations, "target_artifact"),
                    ),
                    change=CorpusChangeSection(
                        answer=change_notes.change_answer,
                        dimensions=change_notes.dimensions,
                        citations=_citations_for_domain(change_notes.citations, "change"),
                    ),
                    resulting_state=CorpusAnswerNote(
                        answer=change_notes.resulting_state_answer,
                        citations=_citations_for_domain(change_notes.citations, "resulting_state"),
                    ),
                    quality=CorpusQualitySection(
                        warnings=change_notes.quality_warnings,
                        citations=_citations_for_domain(change_notes.citations, "quality"),
                    ),
                    key_clauses=[
                        CorpusChangeKeyClause(label=clause.label, summary=clause.summary)
                        for clause in change_notes.key_clauses
                    ],
                ),
            )

        return CorpusDocumentNotes(
            document_map_type=None,
            governing_notes=None,
            change_notes=None,
        )
