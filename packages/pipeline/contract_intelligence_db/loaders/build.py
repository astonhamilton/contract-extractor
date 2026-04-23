from __future__ import annotations

from collections.abc import Callable
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from packages.pipeline.contract_intelligence_db.loaders.change_notes import load_change_notes
from packages.pipeline.contract_intelligence_db.loaders.classification import load_classification
from packages.pipeline.contract_intelligence_db.loaders.common import load_canonical_manifests
from packages.pipeline.contract_intelligence_db.loaders.documents import load_documents
from packages.pipeline.contract_intelligence_db.loaders.governing_notes import load_governing_notes
from packages.pipeline.contract_intelligence_db.loaders.page_notes import load_page_notes
from packages.pipeline.contract_intelligence_db.loaders.pages import load_document_pages
from packages.pipeline.contract_intelligence_db.loaders.procurement_context import load_procurement_context
from packages.schemas import DocumentManifest


LoaderFn = Callable[[sqlite3.Connection, Path, Sequence[DocumentManifest]], int]


def loader_steps() -> list[tuple[str, LoaderFn]]:
    """Return the ordered loader steps for a full contract-intelligence refresh."""
    return [
        ("documents", load_documents),
        ("document_page_variants", load_document_pages),
        ("procurement_context", load_procurement_context),
        ("classification", load_classification),
        ("governing_notes", load_governing_notes),
        ("change_notes", load_change_notes),
        ("page_notes", load_page_notes),
    ]


def load_contract_intelligence(
    connection: sqlite3.Connection,
    repo_root: Path,
    manifests: Sequence[DocumentManifest],
) -> dict[str, int]:
    """Load all canonical artifact families into the SQLite contract-intelligence DB."""
    counts: dict[str, int] = {}
    for name, loader in loader_steps():
        counts[name] = loader(connection, repo_root, manifests)
    return counts


def load_contract_intelligence_from_repo(
    connection: sqlite3.Connection,
    repo_root: Path,
    *,
    doc_ids: Sequence[str] | None = None,
) -> dict[str, int]:
    """Load canonical manifests from the repo and ingest them into SQLite."""
    manifests = load_canonical_manifests(repo_root, doc_ids=doc_ids)
    return load_contract_intelligence(connection, repo_root, manifests)
