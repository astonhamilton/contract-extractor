from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import (
    delete_by_doc_ids,
    join_answers,
    json_dumps,
    load_governing_notes_model,
)
from packages.schemas import Citation, DocumentManifest, GoverningDomainNotes


def _governing_citation_rows(notes: GoverningDomainNotes) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    domains = {
        "identity.what_this_document_is": notes.identity.what_this_document_is.citations,
        "identity.how_it_identifies_itself": notes.identity.how_it_identifies_itself.citations,
        "identity.linked_documents_or_materials": notes.identity.linked_documents_or_materials.citations,
        "parties.who_the_main_parties_are": notes.parties.who_the_main_parties_are.citations,
        "parties.how_their_roles_are_described": notes.parties.how_their_roles_are_described.citations,
        "parties.other_material_entities": notes.parties.other_material_entities.citations,
        "subject.what_is_being_bought_or_governed": notes.subject.what_is_being_bought_or_governed.citations,
        "subject.what_scope_or_deliverables_are_described": notes.subject.what_scope_or_deliverables_are_described.citations,
        "term.when_it_takes_effect_and_how_long_it_runs": notes.term.when_it_takes_effect_and_how_long_it_runs.citations,
        "term.how_renewal_or_extension_works": notes.term.how_renewal_or_extension_works.citations,
        "economics.how_pricing_works": notes.economics.how_pricing_works.citations,
        "economics.what_total_fee_or_cap_language_is_explicit": notes.economics.what_total_fee_or_cap_language_is_explicit.citations,
        "economics.how_payment_is_described": notes.economics.how_payment_is_described.citations,
        "controls.how_termination_or_exit_works": notes.controls.how_termination_or_exit_works.citations,
        "controls.what_insurance_or_risk_requirements_apply": notes.controls.what_insurance_or_risk_requirements_apply.citations,
        "controls.what_performance_or_compliance_obligations_matter": notes.controls.what_performance_or_compliance_obligations_matter.citations,
        "quality.important_caveats_or_ambiguities": notes.quality.important_caveats_or_ambiguities.citations,
    }
    for domain, citations in domains.items():
        for ordinal, citation in enumerate(citations):
            rows.append((notes.doc_id, "governing_domain_notes", domain, citation.page_number, citation.snippet, None, ordinal))
    return rows


def load_governing_notes(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> int:
    """Load canonical governing-domain-note rows and citations."""
    doc_ids = [manifest.doc_id for manifest in manifests]
    delete_by_doc_ids(connection, table="ci_governing_notes", doc_ids=doc_ids)
    delete_by_doc_ids(connection, table="ci_citations", doc_ids=doc_ids, where_sql="doc_id = ? AND stage = 'governing_domain_notes'")

    note_rows: list[tuple[object, ...]] = []
    citation_rows: list[tuple[object, ...]] = []
    for manifest in manifests:
        notes = load_governing_notes_model(repo_root, manifest)
        if notes is None:
            continue
        note_rows.append(
            (
                notes.doc_id,
                join_answers(
                    [
                        ("What this document is", notes.identity.what_this_document_is.answer),
                        ("How it identifies itself", notes.identity.how_it_identifies_itself.answer),
                        ("Linked documents or materials", notes.identity.linked_documents_or_materials.answer),
                    ]
                ),
                join_answers(
                    [
                        ("Who the main parties are", notes.parties.who_the_main_parties_are.answer),
                        ("How their roles are described", notes.parties.how_their_roles_are_described.answer),
                        ("Other material entities", notes.parties.other_material_entities.answer),
                    ]
                ),
                join_answers(
                    [
                        ("What is being bought or governed", notes.subject.what_is_being_bought_or_governed.answer),
                        ("What scope or deliverables are described", notes.subject.what_scope_or_deliverables_are_described.answer),
                    ]
                ),
                join_answers(
                    [
                        ("When it takes effect and how long it runs", notes.term.when_it_takes_effect_and_how_long_it_runs.answer),
                        ("How renewal or extension works", notes.term.how_renewal_or_extension_works.answer),
                    ]
                ),
                join_answers(
                    [
                        ("How pricing works", notes.economics.how_pricing_works.answer),
                        ("What total fee or cap language is explicit", notes.economics.what_total_fee_or_cap_language_is_explicit.answer),
                        ("How payment is described", notes.economics.how_payment_is_described.answer),
                    ]
                ),
                join_answers(
                    [
                        ("How termination or exit works", notes.controls.how_termination_or_exit_works.answer),
                        ("What insurance or risk requirements apply", notes.controls.what_insurance_or_risk_requirements_apply.answer),
                        ("What performance or compliance obligations matter", notes.controls.what_performance_or_compliance_obligations_matter.answer),
                    ]
                ),
                json_dumps(
                    [
                        value
                        for value in [notes.quality.important_caveats_or_ambiguities.answer]
                        if value
                    ]
                ),
                None,
                json_dumps(notes.model_dump(mode="json")),
            )
        )
        citation_rows.extend(_governing_citation_rows(notes))

    if note_rows:
        connection.executemany(
            """
            INSERT INTO ci_governing_notes (
                doc_id, identity_answer, parties_answer, subject_answer, term_answer,
                economics_answer, controls_answer, quality_warnings_json, confidence, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            note_rows,
        )
    if citation_rows:
        connection.executemany(
            """
            INSERT INTO ci_citations (
                doc_id, stage, domain, page_number, snippet, clause_label, ordinal
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            citation_rows,
        )
    return len(note_rows)
