from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import delete_by_doc_ids, json_dumps, load_page_notes_model
from packages.schemas import DocumentManifest


def load_page_notes(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> int:
    """Load canonical page-note rows."""
    doc_ids = [manifest.doc_id for manifest in manifests]
    delete_by_doc_ids(connection, table="ci_page_notes", doc_ids=doc_ids)

    rows: list[tuple[object, ...]] = []
    for manifest in manifests:
        document = load_page_notes_model(repo_root, manifest)
        if document is None:
            continue
        for note in document.page_notes:
            rows.append(
                (
                    note.doc_id,
                    note.page_number,
                    str(note.page_role) if note.page_role is not None else None,
                    note.summary or "",
                    json_dumps(note.key_terms),
                    json_dumps([str(tag) for tag in note.relevance_tags]),
                    json_dumps(note.warnings),
                    json_dumps(note.model_dump(mode="json")),
                )
            )

    if rows:
        connection.executemany(
            """
            INSERT INTO ci_page_notes (
                doc_id, page_number, page_role, summary, key_terms_json,
                relevance_tags_json, warnings_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)
