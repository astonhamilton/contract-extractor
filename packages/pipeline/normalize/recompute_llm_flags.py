from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.normalize.llm_selection import recompute_manifest_llm_flags
from packages.pipeline.normalize.pdf_pages import iter_manifest_paths, load_manifest, write_manifest
from packages.schemas import DocumentManifest


LOGGER = logging.getLogger(__name__)


def recompute_all_manifest_llm_flags(processed_contracts_dir: Path) -> list[DocumentManifest]:
    """Recompute split LLM recommendation flags for every manifest in place."""
    manifest_paths = list(iter_manifest_paths(processed_contracts_dir))
    LOGGER.info("Recomputing LLM flags for %s manifests", len(manifest_paths))
    manifests: list[DocumentManifest] = []

    for index, manifest_path in enumerate(manifest_paths, start=1):
        manifest = load_manifest(manifest_path)
        updated_manifest = recompute_manifest_llm_flags(manifest)
        write_manifest(manifest_path, updated_manifest)
        manifests.append(updated_manifest)
        LOGGER.info("LLM flag recompute [%s/%s] %s", index, len(manifest_paths), manifest_path.parent.name)

    LOGGER.info("LLM flag recompute complete: %s manifests", len(manifests))
    return manifests


def build_recompute_llm_flags_report(manifests: Iterable[DocumentManifest]) -> dict[str, object]:
    """Build a compact report for manifest-level LLM flag recomputation."""
    manifest_list = list(manifests)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_documents": len(manifest_list),
        "llm_markdown_recommended_documents": sum(
            1 for manifest in manifest_list if "llm_markdown_recommended" in manifest.quality_flags
        ),
        "llm_repair_recommended_documents": sum(
            1 for manifest in manifest_list if "llm_repair_recommended" in manifest.quality_flags
        ),
        "legacy_llm_normalization_recommended_documents": sum(
            1 for manifest in manifest_list if "llm_normalization_recommended" in manifest.quality_flags
        ),
    }


def write_recompute_llm_flags_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the LLM flag recomputation report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
