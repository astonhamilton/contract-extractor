from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import (
    delete_by_doc_ids,
    json_dumps,
    page_variant_records,
)
from packages.schemas import DocumentManifest


def load_document_pages(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> int:
    """Load all canonical normalized page variants."""
    doc_ids = [manifest.doc_id for manifest in manifests]
    delete_by_doc_ids(connection, table="ci_document_page_variants", doc_ids=doc_ids)

    variant_rows: list[tuple[object, ...]] = []
    for manifest in manifests:
        for artifact in manifest.pages:
            for variant in page_variant_records(
                repo_root,
                manifest,
                page_number=artifact.page_number,
            ):
                content = str(variant["content"])
                variant_rows.append(
                    (
                        manifest.doc_id,
                        artifact.page_number,
                        variant["representation"],
                        int(variant["priority"]),
                        variant["source_path"],
                        content,
                        str(artifact.extraction_method) or None,
                        int(artifact.char_count),
                        int(artifact.ocr_char_count),
                        float(artifact.ocr_confidence) if artifact.ocr_confidence is not None else None,
                        json_dumps(list(artifact.warnings)),
                        json_dumps(list(artifact.quality_flags)),
                        max(1, round(len(content) / 4)) if content else 0,
                    )
                )

    if variant_rows:
        connection.executemany(
            """
            INSERT INTO ci_document_page_variants (
                doc_id, page_number, representation, priority, source_path, content,
                extraction_method, char_count, ocr_char_count, ocr_confidence,
                warnings_json, quality_flags_json, estimated_tokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            variant_rows,
        )
    return len(variant_rows)
