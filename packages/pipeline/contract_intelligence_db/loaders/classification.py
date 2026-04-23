from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import delete_by_doc_ids, json_dumps, load_classification_model
from packages.schemas import DocumentManifest


def load_classification(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> int:
    """Load canonical classification rows."""
    doc_ids = [manifest.doc_id for manifest in manifests]
    delete_by_doc_ids(connection, table="ci_classification", doc_ids=doc_ids)

    rows: list[tuple[object, ...]] = []
    for manifest in manifests:
        classification = load_classification_model(repo_root, manifest)
        if classification is None:
            continue
        rows.append(
            (
                classification.doc_id,
                str(classification.procurement_stage),
                str(classification.primary_document_role),
                str(classification.change_kind) if classification.change_kind is not None else None,
                classification.confidence,
                classification.rationale,
                json_dumps(classification.evidence_pages),
                json_dumps(classification.warnings),
                json_dumps(classification.model_dump(mode="json")),
            )
        )

    if rows:
        connection.executemany(
            """
            INSERT INTO ci_classification (
                doc_id, procurement_stage, primary_document_role, change_kind, confidence,
                rationale, evidence_pages_json, warnings_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)
