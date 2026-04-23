from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import json_dumps, stage_status_columns
from packages.schemas import DocumentManifest


def load_documents(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> int:
    """Load manifest-root document and artifact inventory rows."""
    document_rows: list[tuple[object, ...]] = []
    artifact_rows: list[tuple[str, str, str, str | None]] = []

    for manifest in manifests:
        source_pdf_path = repo_root / manifest.source_pdf
        source_pdf_size_bytes = (
            source_pdf_path.stat().st_size if source_pdf_path.exists() else None
        )
        processing = stage_status_columns("processing", manifest.processing_status)
        procurement = stage_status_columns("procurement_context", manifest.procurement_context_status)
        classification = stage_status_columns("classification", manifest.classification_status)
        governing = stage_status_columns("governing_domain_notes", manifest.governing_domain_notes_status)
        change = stage_status_columns("change_extraction", manifest.change_extraction_status)
        page_notes = stage_status_columns("page_notes", manifest.page_notes_status)

        document_rows.append(
            (
                manifest.doc_id,
                manifest.source_filename,
                manifest.source_pdf,
                source_pdf_size_bytes,
                manifest.sha256,
                manifest.page_count,
                int(manifest.has_text_layer) if manifest.has_text_layer is not None else None,
                json_dumps(manifest.quality_flags),
                processing["processing_status"],
                processing["processing_updated_at"],
                processing["processing_version"],
                processing["processing_error"],
                processing["processing_warnings_json"],
                f"data/processed/contracts/{manifest.doc_id}/derived/normalized_document.xml",
                manifest.procurement_context_path,
                procurement["procurement_context_status"],
                procurement["procurement_context_updated_at"],
                manifest.classification_path,
                classification["classification_status"],
                classification["classification_updated_at"],
                manifest.governing_domain_notes_path,
                governing["governing_domain_notes_status"],
                governing["governing_domain_notes_updated_at"],
                manifest.change_extraction_path,
                change["change_extraction_status"],
                change["change_extraction_updated_at"],
                manifest.page_notes_path,
                page_notes["page_notes_status"],
                page_notes["page_notes_updated_at"],
            )
        )

        for artifact in manifest.derived_artifacts:
            artifact_rows.append(
                (
                    manifest.doc_id,
                    str(artifact.kind),
                    artifact.path,
                    artifact.description,
                )
            )

    connection.executemany(
        """
        INSERT INTO ci_documents (
            doc_id, source_filename, source_pdf_path, source_pdf_size_bytes, sha256, page_count,
            has_text_layer, quality_flags_json, processing_status, processing_updated_at,
            processing_version, processing_error, processing_warnings_json, normalized_document_path,
            procurement_context_path, procurement_context_status, procurement_context_updated_at,
            classification_path, classification_status, classification_updated_at,
            governing_domain_notes_path, governing_domain_notes_status, governing_domain_notes_updated_at,
            change_extraction_path, change_extraction_status, change_extraction_updated_at,
            page_notes_path, page_notes_status, page_notes_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(doc_id) DO UPDATE SET
            source_filename = excluded.source_filename,
            source_pdf_path = excluded.source_pdf_path,
            source_pdf_size_bytes = excluded.source_pdf_size_bytes,
            sha256 = excluded.sha256,
            page_count = excluded.page_count,
            has_text_layer = excluded.has_text_layer,
            quality_flags_json = excluded.quality_flags_json,
            processing_status = excluded.processing_status,
            processing_updated_at = excluded.processing_updated_at,
            processing_version = excluded.processing_version,
            processing_error = excluded.processing_error,
            processing_warnings_json = excluded.processing_warnings_json,
            normalized_document_path = excluded.normalized_document_path,
            procurement_context_path = excluded.procurement_context_path,
            procurement_context_status = excluded.procurement_context_status,
            procurement_context_updated_at = excluded.procurement_context_updated_at,
            classification_path = excluded.classification_path,
            classification_status = excluded.classification_status,
            classification_updated_at = excluded.classification_updated_at,
            governing_domain_notes_path = excluded.governing_domain_notes_path,
            governing_domain_notes_status = excluded.governing_domain_notes_status,
            governing_domain_notes_updated_at = excluded.governing_domain_notes_updated_at,
            change_extraction_path = excluded.change_extraction_path,
            change_extraction_status = excluded.change_extraction_status,
            change_extraction_updated_at = excluded.change_extraction_updated_at,
            page_notes_path = excluded.page_notes_path,
            page_notes_status = excluded.page_notes_status,
            page_notes_updated_at = excluded.page_notes_updated_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        document_rows,
    )

    doc_ids = [manifest.doc_id for manifest in manifests]
    if doc_ids:
        connection.executemany(
            "DELETE FROM ci_document_artifacts WHERE doc_id = ?",
            [(doc_id,) for doc_id in doc_ids],
        )
    if artifact_rows:
        connection.executemany(
            """
            INSERT INTO ci_document_artifacts (doc_id, artifact_kind, path, description)
            VALUES (?, ?, ?, ?)
            """,
            artifact_rows,
        )

    return len(document_rows)
