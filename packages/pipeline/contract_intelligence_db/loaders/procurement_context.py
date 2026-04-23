from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import delete_by_doc_ids, json_dumps, load_procurement_context_model
from packages.schemas import DocumentManifest, TernaryLabel


def load_procurement_context(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> int:
    """Load canonical procurement context rows."""
    doc_ids = [manifest.doc_id for manifest in manifests]
    delete_by_doc_ids(connection, table="ci_procurement_context", doc_ids=doc_ids)

    rows: list[tuple[object, ...]] = []
    for manifest in manifests:
        context = load_procurement_context_model(repo_root, manifest)
        if context is None:
            continue
        is_procurement_related = (
            1 if context.is_procurement_doc == TernaryLabel.YES
            else 0 if context.is_procurement_doc == TernaryLabel.NO
            else None
        )
        rows.append(
            (
                context.doc_id,
                is_procurement_related,
                context.buyer,
                context.seller,
                context.procurement_subject_summary,
                str(context.procurement_category) if context.procurement_category is not None else None,
                context.procurement_subject_summary,
                json_dumps(context.warnings),
                context.confidence,
                json_dumps(context.model_dump(mode="json")),
            )
        )

    if rows:
        connection.executemany(
            """
            INSERT INTO ci_procurement_context (
                doc_id, is_procurement_related, buyer, seller, what_is_being_bought,
                procurement_category, context_summary, warnings_json, confidence, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)
