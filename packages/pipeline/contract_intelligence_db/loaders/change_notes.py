from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import delete_by_doc_ids, json_dumps, load_change_notes_model
from packages.schemas import ChangeExtraction, DocumentManifest


def _change_citation_rows(change: ChangeExtraction) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    domains = {
        "target_artifact": change.target_artifact.citations,
        "change": change.change.citations,
        "resulting_state": change.resulting_state.citations,
        "overall": change.citations,
    }
    for domain, citations in domains.items():
        for ordinal, citation in enumerate(citations):
            rows.append((change.doc_id, "change_extraction", domain, citation.page_number, citation.snippet, None, ordinal))
    for clause_ordinal, clause in enumerate(change.key_clauses):
        for citation_ordinal, citation in enumerate(clause.citations):
            rows.append(
                (
                    change.doc_id,
                    "change_extraction",
                    "key_clause",
                    citation.page_number,
                    citation.snippet,
                    clause.label,
                    clause_ordinal * 100 + citation_ordinal,
                )
            )
    return rows


def load_change_notes(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> int:
    """Load canonical change-note rows, key clauses, and citations."""
    doc_ids = [manifest.doc_id for manifest in manifests]
    delete_by_doc_ids(connection, table="ci_change_notes", doc_ids=doc_ids)
    delete_by_doc_ids(connection, table="ci_change_key_clauses", doc_ids=doc_ids)
    delete_by_doc_ids(connection, table="ci_citations", doc_ids=doc_ids, where_sql="doc_id = ? AND stage = 'change_extraction'")

    note_rows: list[tuple[object, ...]] = []
    clause_rows: list[tuple[object, ...]] = []
    citation_rows: list[tuple[object, ...]] = []
    for manifest in manifests:
        change = load_change_notes_model(repo_root, manifest)
        if change is None:
            continue
        note_rows.append(
            (
                change.doc_id,
                change.target_artifact.answer,
                change.change.answer,
                change.resulting_state.answer,
                json_dumps([str(dimension) for dimension in change.change.dimensions]),
                json_dumps(change.quality.warnings),
                change.extraction_confidence,
                json_dumps(change.model_dump(mode="json")),
            )
        )
        for ordinal, clause in enumerate(change.key_clauses):
            clause_rows.append((change.doc_id, clause.label, clause.summary, ordinal))
        citation_rows.extend(_change_citation_rows(change))

    if note_rows:
        connection.executemany(
            """
            INSERT INTO ci_change_notes (
                doc_id, target_artifact_answer, change_answer, resulting_state_answer,
                dimensions_json, quality_warnings_json, confidence, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            note_rows,
        )
    if clause_rows:
        connection.executemany(
            """
            INSERT INTO ci_change_key_clauses (doc_id, label, summary, ordinal)
            VALUES (?, ?, ?, ?)
            """,
            clause_rows,
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
