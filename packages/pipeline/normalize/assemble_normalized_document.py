from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.normalize.pdf_pages import absolute_repo_path, iter_manifest_paths, load_manifest, repo_relative_path, write_manifest
from packages.schemas import ArtifactKind, DerivedArtifact, DocumentManifest, PageArtifact


BEST_AVAILABLE_PRIORITY = (
    ("repair_markdown", "repair_markdown_path"),
    ("markdown", "markdown_path"),
    ("vision_markdown", "vision_markdown_path"),
    ("ocr_text", "ocr_text_path"),
    ("text", "text_path"),
)

DERIVED_DESCRIPTION = "Canonical normalized document assembled from the best available page representation."


def xml_escape_attr(value: str) -> str:
    """Escape XML attribute content."""
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def cdata_wrap(text: str) -> str:
    """Wrap text in CDATA safely for XML output."""
    return f"<![CDATA[{text.replace(']]>', ']]]]><![CDATA[>')}]]>"


def normalized_document_output_path(doc_dir: Path) -> Path:
    """Return the canonical output path for the assembled normalized document."""
    derived_dir = doc_dir / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)
    return derived_dir / "normalized_document.xml"


def best_available_page_representation(page: PageArtifact) -> tuple[str | None, str | None]:
    """Return the best available representation type and repo-relative source path for a page."""
    for representation, field_name in BEST_AVAILABLE_PRIORITY:
        value = getattr(page, field_name)
        if value:
            return representation, value
    return None, None


def read_page_content(repo_root: Path, raw_path: str | None) -> str | None:
    """Read page content from a repo-relative path if present."""
    if not raw_path:
        return None
    path = absolute_repo_path(repo_root, raw_path)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def page_xml(repo_root: Path, page: PageArtifact) -> str:
    """Build one page XML block from the best available representation."""
    representation, source_path = best_available_page_representation(page)
    content = read_page_content(repo_root, source_path)
    source_attr = xml_escape_attr(source_path or "")
    representation_attr = xml_escape_attr(representation or "missing")

    lines = [
        f'    <page number="{page.page_number}" representation="{representation_attr}" source_path="{source_attr}">',
        f"      <quality_flags>{xml_escape_attr(','.join(page.quality_flags) if page.quality_flags else '')}</quality_flags>",
    ]
    if content is not None:
        lines.append(f"      <content>{cdata_wrap(content)}</content>")
    else:
        lines.append("      <content><![CDATA[]]></content>")
    lines.append("    </page>")
    return "\n".join(lines)


def normalized_document_xml(repo_root: Path, manifest: DocumentManifest) -> str:
    """Build the assembled normalized document XML for one manifest."""
    page_blocks = "\n".join(page_xml(repo_root, page) for page in manifest.pages)
    lines = [
        f'<document doc_id="{xml_escape_attr(manifest.doc_id)}">',
        "  <metadata>",
        f"    <source_filename>{xml_escape_attr(manifest.source_filename)}</source_filename>",
        f"    <source_pdf>{xml_escape_attr(manifest.source_pdf)}</source_pdf>",
        f"    <page_count>{manifest.page_count}</page_count>",
        "  </metadata>",
        "  <pages>",
        page_blocks,
        "  </pages>",
        "</document>",
    ]
    return "\n".join(lines) + "\n"


def upsert_normalized_document_artifact(manifest: DocumentManifest, artifact_path: str) -> DocumentManifest:
    """Insert or update the normalized document derived artifact in the manifest."""
    filtered = [
        artifact
        for artifact in manifest.derived_artifacts
        if not (artifact.kind == ArtifactKind.XML and artifact.description == DERIVED_DESCRIPTION)
    ]
    filtered.append(
        DerivedArtifact(
            kind=ArtifactKind.XML,
            path=artifact_path,
            description=DERIVED_DESCRIPTION,
        )
    )
    return manifest.model_copy(update={"derived_artifacts": filtered})


def assemble_normalized_document(
    *,
    repo_root: Path,
    manifest_path: Path,
) -> DocumentManifest:
    """Assemble one canonical normalized document and update its manifest."""
    manifest = load_manifest(manifest_path)
    doc_dir = manifest_path.parent
    output_path = normalized_document_output_path(doc_dir)
    output_path.write_text(normalized_document_xml(repo_root, manifest), encoding="utf-8")

    updated_manifest = upsert_normalized_document_artifact(
        manifest,
        repo_relative_path(output_path, repo_root),
    )
    write_manifest(manifest_path, updated_manifest)
    return updated_manifest


def assemble_all_normalized_documents(
    *,
    repo_root: Path,
    processed_contracts_dir: Path,
) -> list[DocumentManifest]:
    """Assemble canonical normalized documents for every processed manifest."""
    manifests: list[DocumentManifest] = []
    for manifest_path in iter_manifest_paths(processed_contracts_dir):
        manifests.append(assemble_normalized_document(repo_root=repo_root, manifest_path=manifest_path))
    return manifests


def build_assembled_documents_report(manifests: list[DocumentManifest]) -> dict[str, object]:
    """Build a compact report for assembled normalized documents."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "documents_total": len(manifests),
        "assembled_documents": [
            {
                "doc_id": manifest.doc_id,
                "source_filename": manifest.source_filename,
                "normalized_document_path": next(
                    (
                        artifact.path
                        for artifact in manifest.derived_artifacts
                        if artifact.kind == ArtifactKind.XML and artifact.description == DERIVED_DESCRIPTION
                    ),
                    None,
                ),
            }
            for manifest in manifests
        ],
    }


def write_assembled_documents_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the assembled-documents report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
