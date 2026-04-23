from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.common import (
    best_page_content_record,
    load_canonical_manifests,
    load_change_notes_model,
    load_classification_model,
    load_governing_notes_model,
    load_page_notes_model,
    page_variant_records,
    load_procurement_context_model,
)
from packages.schemas import DocumentManifest


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _expected_change_citation_count(doc) -> int:
    return (
        len(doc.target_artifact.citations)
        + len(doc.change.citations)
        + len(doc.resulting_state.citations)
        + len(doc.citations)
        + sum(len(clause.citations) for clause in doc.key_clauses)
    )


def _expected_governing_citation_count(doc) -> int:
    return sum(
        len(note.citations)
        for note in [
            doc.identity.what_this_document_is,
            doc.identity.how_it_identifies_itself,
            doc.identity.linked_documents_or_materials,
            doc.parties.who_the_main_parties_are,
            doc.parties.how_their_roles_are_described,
            doc.parties.other_material_entities,
            doc.subject.what_is_being_bought_or_governed,
            doc.subject.what_scope_or_deliverables_are_described,
            doc.term.when_it_takes_effect_and_how_long_it_runs,
            doc.term.how_renewal_or_extension_works,
            doc.economics.how_pricing_works,
            doc.economics.what_total_fee_or_cap_language_is_explicit,
            doc.economics.how_payment_is_described,
            doc.controls.how_termination_or_exit_works,
            doc.controls.what_insurance_or_risk_requirements_apply,
            doc.controls.what_performance_or_compliance_obligations_matter,
            doc.quality.important_caveats_or_ambiguities,
        ]
    )


def _audit_document_row(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifest: DocumentManifest,
) -> tuple[bool, list[str]]:
    row = connection.execute(
        """
        SELECT doc_id, source_filename, source_pdf_path, source_pdf_size_bytes, page_count
        FROM ci_documents
        WHERE doc_id = ?
        """,
        (manifest.doc_id,),
    ).fetchone()
    if row is None:
        return False, ["missing ci_documents row"]
    mismatches: list[str] = []
    if str(row["source_filename"]) != manifest.source_filename:
        mismatches.append("ci_documents.source_filename mismatch")
    if str(row["source_pdf_path"]) != manifest.source_pdf:
        mismatches.append("ci_documents.source_pdf_path mismatch")
    source_pdf_path = repo_root / manifest.source_pdf
    expected_size_bytes = source_pdf_path.stat().st_size if source_pdf_path.exists() else None
    actual_size_bytes = (
        int(row["source_pdf_size_bytes"])
        if row["source_pdf_size_bytes"] is not None
        else None
    )
    if actual_size_bytes != expected_size_bytes:
        mismatches.append("ci_documents.source_pdf_size_bytes mismatch")
    if int(row["page_count"]) != manifest.page_count:
        mismatches.append("ci_documents.page_count mismatch")
    return not mismatches, mismatches


def _audit_pages(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifest: DocumentManifest,
) -> tuple[dict[str, int], list[str]]:
    expected_variants: dict[tuple[int, str], dict[str, str]] = {}
    expected: dict[int, dict[str, str]] = {}
    for page in manifest.pages:
        for variant in page_variant_records(repo_root, manifest, page_number=page.page_number):
            content = str(variant["content"])
            expected_variants[(page.page_number, str(variant["representation"]))] = {
                "source_path": str(variant["source_path"] or ""),
                "content_sha256": _sha256_text(content),
            }
        record = best_page_content_record(repo_root, manifest, page_number=page.page_number)
        if record is None:
            continue
        content = str(record["content"])
        expected[page.page_number] = {
            "representation": str(record["representation"] or ""),
            "source_path": str(record["source_path"] or ""),
            "content_sha256": _sha256_text(content),
        }

    variant_rows = connection.execute(
        """
        SELECT page_number, representation, source_path, content
        FROM ci_document_page_variants
        WHERE doc_id = ?
        ORDER BY page_number, priority, representation
        """,
        (manifest.doc_id,),
    ).fetchall()
    actual_variants = {
        (int(row["page_number"]), str(row["representation"] or "")): {
            "source_path": str(row["source_path"] or ""),
            "content_sha256": _sha256_text(str(row["content"] or "")),
        }
        for row in variant_rows
    }

    rows = connection.execute(
        """
        SELECT page_number, representation, source_path, content
        FROM v_ci_document_pages_best
        WHERE doc_id = ?
        ORDER BY page_number
        """,
        (manifest.doc_id,),
    ).fetchall()
    actual = {
        int(row["page_number"]): {
            "representation": str(row["representation"] or ""),
            "source_path": str(row["source_path"] or ""),
            "content_sha256": _sha256_text(str(row["content"] or "")),
        }
        for row in rows
    }

    mismatches: list[str] = []
    for variant_key in sorted(set(expected_variants) - set(actual_variants)):
        mismatches.append(
            f"missing ci_document_page_variants row for page {variant_key[0]} variant {variant_key[1]}"
        )
    for variant_key in sorted(set(actual_variants) - set(expected_variants)):
        mismatches.append(
            f"unexpected ci_document_page_variants row for page {variant_key[0]} variant {variant_key[1]}"
        )
    for variant_key in sorted(set(expected_variants) & set(actual_variants)):
        exp = expected_variants[variant_key]
        act = actual_variants[variant_key]
        if exp["source_path"] != act["source_path"]:
            mismatches.append(
                f"page {variant_key[0]} variant {variant_key[1]} source_path mismatch"
            )
        if exp["content_sha256"] != act["content_sha256"]:
            mismatches.append(
                f"page {variant_key[0]} variant {variant_key[1]} content mismatch"
            )
    for page_number in sorted(set(expected) - set(actual)):
        mismatches.append(f"missing v_ci_document_pages_best row for page {page_number}")
    for page_number in sorted(set(actual) - set(expected)):
        mismatches.append(f"unexpected v_ci_document_pages_best row for page {page_number}")
    for page_number in sorted(set(expected) & set(actual)):
        exp = expected[page_number]
        act = actual[page_number]
        if exp["representation"] != act["representation"]:
            mismatches.append(f"page {page_number} representation mismatch")
        if exp["source_path"] != act["source_path"]:
            mismatches.append(f"page {page_number} source_path mismatch")
        if exp["content_sha256"] != act["content_sha256"]:
            mismatches.append(f"page {page_number} content mismatch")
    return {
        "expected_pages": len(expected),
        "loaded_pages": len(actual),
        "expected_variants": len(expected_variants),
        "loaded_variants": len(actual_variants),
    }, mismatches


def _audit_optional_row(
    connection: sqlite3.Connection,
    *,
    table: str,
    doc_id: str,
    expected: bool,
) -> list[str]:
    row = connection.execute(
        f"SELECT 1 FROM {table} WHERE doc_id = ? LIMIT 1",
        (doc_id,),
    ).fetchone()
    exists = row is not None
    if expected and not exists:
        return [f"missing {table} row"]
    if not expected and exists:
        return [f"unexpected {table} row"]
    return []


def _audit_page_notes(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifest: DocumentManifest,
) -> tuple[dict[str, int] | None, list[str]]:
    page_notes = load_page_notes_model(repo_root, manifest)
    expected = page_notes is not None
    rows = connection.execute(
        """
        SELECT page_number, page_role, summary
        FROM ci_page_notes
        WHERE doc_id = ?
        ORDER BY page_number
        """,
        (manifest.doc_id,),
    ).fetchall()
    if not expected:
        return None, ([] if not rows else ["unexpected ci_page_notes rows"])
    assert page_notes is not None
    actual = {int(row["page_number"]): row for row in rows}
    expected_map = {note.page_number: note for note in page_notes.page_notes}
    mismatches: list[str] = []
    for page_number in sorted(set(expected_map) - set(actual)):
        mismatches.append(f"missing page_notes row for page {page_number}")
    for page_number in sorted(set(actual) - set(expected_map)):
        mismatches.append(f"unexpected page_notes row for page {page_number}")
    for page_number in sorted(set(expected_map) & set(actual)):
        note = expected_map[page_number]
        row = actual[page_number]
        if str(row["page_role"] or "") != str(note.page_role or ""):
            mismatches.append(f"page_notes role mismatch on page {page_number}")
        if str(row["summary"] or "") != str(note.summary or ""):
            mismatches.append(f"page_notes summary mismatch on page {page_number}")
    return {
        "expected_page_notes": len(expected_map),
        "loaded_page_notes": len(actual),
    }, mismatches


def _count_rows(connection: sqlite3.Connection, *, table: str, doc_id: str, extra_where: str = "") -> int:
    sql = f"SELECT COUNT(*) AS count FROM {table} WHERE doc_id = ?"
    if extra_where:
        sql += f" AND {extra_where}"
    row = connection.execute(sql, (doc_id,)).fetchone()
    return int(row["count"])


def audit_sqlite_load(
    connection: sqlite3.Connection,
    repo_root: Path,
    *,
    doc_ids: list[str] | None = None,
) -> dict[str, object]:
    """Audit doc-by-doc SQLite load completeness against canonical repo artifacts."""
    manifests = load_canonical_manifests(repo_root, doc_ids=doc_ids)
    document_results: list[dict[str, object]] = []
    docs_ok = 0

    for manifest in manifests:
        mismatches: list[str] = []
        document_ok, document_mismatches = _audit_document_row(connection, repo_root, manifest)
        mismatches.extend(document_mismatches)

        page_summary, page_mismatches = _audit_pages(connection, repo_root, manifest)
        mismatches.extend(page_mismatches)

        procurement_expected = load_procurement_context_model(repo_root, manifest) is not None
        classification = load_classification_model(repo_root, manifest)
        classification_expected = classification is not None
        governing = load_governing_notes_model(repo_root, manifest)
        change = load_change_notes_model(repo_root, manifest)

        mismatches.extend(
            _audit_optional_row(
                connection,
                table="ci_procurement_context",
                doc_id=manifest.doc_id,
                expected=procurement_expected,
            )
        )
        mismatches.extend(
            _audit_optional_row(
                connection,
                table="ci_classification",
                doc_id=manifest.doc_id,
                expected=classification_expected,
            )
        )
        mismatches.extend(
            _audit_optional_row(
                connection,
                table="ci_governing_notes",
                doc_id=manifest.doc_id,
                expected=governing is not None,
            )
        )
        mismatches.extend(
            _audit_optional_row(
                connection,
                table="ci_change_notes",
                doc_id=manifest.doc_id,
                expected=change is not None,
            )
        )

        page_note_summary, page_note_mismatches = _audit_page_notes(connection, repo_root, manifest)
        mismatches.extend(page_note_mismatches)

        governing_citations_expected = _expected_governing_citation_count(governing) if governing is not None else 0
        change_citations_expected = _expected_change_citation_count(change) if change is not None else 0
        change_key_clauses_expected = len(change.key_clauses) if change is not None else 0

        governing_citations_loaded = _count_rows(
            connection,
            table="ci_citations",
            doc_id=manifest.doc_id,
            extra_where="stage = 'governing_domain_notes'",
        )
        change_citations_loaded = _count_rows(
            connection,
            table="ci_citations",
            doc_id=manifest.doc_id,
            extra_where="stage = 'change_extraction'",
        )
        change_key_clauses_loaded = _count_rows(
            connection,
            table="ci_change_key_clauses",
            doc_id=manifest.doc_id,
        )

        if governing_citations_loaded != governing_citations_expected:
            mismatches.append("governing citations count mismatch")
        if change_citations_loaded != change_citations_expected:
            mismatches.append("change citations count mismatch")
        if change_key_clauses_loaded != change_key_clauses_expected:
            mismatches.append("change_key_clauses count mismatch")

        ok = document_ok and not mismatches
        if ok:
            docs_ok += 1

        document_results.append(
            {
                "doc_id": manifest.doc_id,
                "source_filename": manifest.source_filename,
                "ok": ok,
                "page_summary": page_summary,
                "page_notes_summary": page_note_summary,
                "expected": {
                    "procurement_context": procurement_expected,
                    "classification": classification_expected,
                    "governing_notes": governing is not None,
                    "change_notes": change is not None,
                    "governing_citations": governing_citations_expected,
                    "change_citations": change_citations_expected,
                    "change_key_clauses": change_key_clauses_expected,
                },
                "loaded": {
                    "governing_citations": governing_citations_loaded,
                    "change_citations": change_citations_loaded,
                    "change_key_clauses": change_key_clauses_loaded,
                },
                "mismatches": mismatches,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "documents_audited": len(document_results),
        "documents_ok": docs_ok,
        "documents_with_issues": len(document_results) - docs_ok,
        "documents": document_results,
    }


def write_sqlite_audit_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the SQLite load audit report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
