from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from packages.pipeline.normalize.pdf_pages import load_manifest
from packages.schemas import DocumentManifest


SLUG_RE = re.compile(r"[^a-z0-9]+")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class InventoryPaths:
    repo_root: Path
    raw_contracts_dir: Path
    processed_contracts_dir: Path
    documents_index_path: Path


def slugify_filename_stem(filename_stem: str) -> str:
    slug = SLUG_RE.sub("_", filename_stem.lower()).strip("_")
    return slug or "document"


def sha256_for_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_doc_id(pdf_path: Path, sha256_hex: str) -> str:
    slug = slugify_filename_stem(pdf_path.stem)
    return f"{slug}__{sha256_hex[:8]}"


def repo_relative_path(path: Path, repo_root: Path) -> str:
    return str(path.relative_to(repo_root))


def build_manifest(
    pdf_path: Path,
    sha256_hex: str,
    doc_id: str,
    repo_root: Path,
) -> DocumentManifest:
    return DocumentManifest(
        doc_id=doc_id,
        source_pdf=repo_relative_path(pdf_path, repo_root),
        source_filename=pdf_path.name,
        sha256=sha256_hex,
    )


def write_manifest(doc_dir: Path, manifest: DocumentManifest) -> None:
    manifest_path = doc_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def index_record(
    manifest: DocumentManifest,
    doc_dir: Path,
    repo_root: Path,
) -> dict[str, str | int | None]:
    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "source_pdf": manifest.source_pdf,
        "sha256": manifest.sha256,
        "page_count": manifest.page_count,
        "manifest_path": repo_relative_path(doc_dir / "manifest.json", repo_root),
        "doc_dir": repo_relative_path(doc_dir, repo_root),
    }


def inventory_contracts(paths: InventoryPaths) -> list[dict[str, str | int | None]]:
    """Inventory raw PDFs, create per-document folders, and write manifests."""
    paths.processed_contracts_dir.mkdir(parents=True, exist_ok=True)
    paths.documents_index_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, str | int | None]] = []
    pdf_paths = sorted(paths.raw_contracts_dir.glob("*.pdf"))

    LOGGER.info("Starting inventory for %s PDF files", len(pdf_paths))

    for index, pdf_path in enumerate(pdf_paths, start=1):
        LOGGER.info("Inventorying [%s/%s] %s", index, len(pdf_paths), pdf_path.name)
        sha256_hex = sha256_for_file(pdf_path)
        doc_id = build_doc_id(pdf_path, sha256_hex)
        doc_dir = paths.processed_contracts_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = doc_dir / "manifest.json"

        if manifest_path.exists():
            manifest = load_manifest(manifest_path)
            LOGGER.info("Reusing existing manifest for %s", doc_id)
        else:
            manifest = build_manifest(pdf_path, sha256_hex, doc_id, paths.repo_root)
            write_manifest(doc_dir, manifest)
            LOGGER.info("Wrote manifest for %s", doc_id)
        records.append(index_record(manifest, doc_dir, paths.repo_root))

    with paths.documents_index_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    LOGGER.info("Wrote documents index to %s", paths.documents_index_path)
    LOGGER.info("Inventory complete: %s documents", len(records))
    return records
