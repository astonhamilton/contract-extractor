from __future__ import annotations

import concurrent.futures
import json
import logging
import random
import shutil
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from packages.llm.transforms.procurement_context.config import ProcurementContextConfig
from packages.llm.transforms.procurement_context.task import (
    build_procurement_context_input,
    run_procurement_context,
)
from packages.pipeline.classification_stage import upsert_derived_artifact
from packages.pipeline.normalize.pdf_pages import (
    load_manifest,
    repo_relative_path,
    write_manifest,
)
from packages.schemas import (
    ArtifactKind,
    DocumentManifest,
    ProcurementContext,
    completed_procurement_context_status,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcurementContextStageConfig:
    repo_root: Path
    processed_contracts_dir: Path
    runs_dir: Path
    indexes_dir: Path
    model: str = "openai/gpt-5.4-mini"
    workers: int = 1


def run_timestamp() -> str:
    """Return a stable UTC timestamp for one procurement-context run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def iter_eligible_manifest_paths(
    processed_contracts_dir: Path,
    *,
    include_already_processed: bool,
) -> list[Path]:
    """Return manifest paths eligible for procurement-context execution."""
    manifest_paths: list[Path] = []
    for doc_dir in sorted(processed_contracts_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        manifest_path = doc_dir / "manifest.json"
        normalized_document_path = doc_dir / "derived" / "normalized_document.xml"
        if not manifest_path.exists() or not normalized_document_path.exists():
            continue
        manifest = load_manifest(manifest_path)
        if not include_already_processed and manifest.procurement_context_path:
            continue
        manifest_paths.append(manifest_path)
    return manifest_paths


def selected_manifest_paths(
    config: ProcurementContextStageConfig,
    *,
    doc_id: str | None,
    random_n: int | None,
    seed: int,
    force: bool,
) -> list[Path]:
    """Resolve target manifest paths from selection options."""
    eligible = iter_eligible_manifest_paths(
        config.processed_contracts_dir,
        include_already_processed=force,
    )
    if doc_id is not None:
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        if manifest_path not in eligible and not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found for doc_id={doc_id}")
        return [manifest_path]

    if random_n is None:
        return eligible

    if random_n <= 0:
        raise ValueError("--random-n must be >= 1.")
    if random_n > len(eligible):
        raise ValueError(f"--random-n={random_n} exceeds eligible docs={len(eligible)}")

    rng = random.Random(seed)
    return sorted(rng.sample(eligible, random_n))


def run_output_dir(runs_dir: Path, run_id: str) -> Path:
    """Return the output directory for one staged procurement-context run."""
    return runs_dir / run_id


def doc_run_dir(run_dir: Path, doc_id: str) -> Path:
    """Return the staged subdirectory for one document within a run."""
    return run_dir / doc_id


def write_staged_doc_outputs(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest: DocumentManifest,
    normalized_document_path: Path,
    procurement_context: ProcurementContext,
    request_payload: dict[str, object],
) -> dict[str, object]:
    """Write staged procurement-context outputs for one document."""
    output_dir = doc_run_dir(run_dir, manifest.doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    context_path = output_dir / "procurement_context.json"
    request_path = output_dir / "procurement_context_request.json"
    normalized_link_path = output_dir / "normalized_document.xml"

    context_path.write_text(
        json.dumps(procurement_context.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    request_path.write_text(
        json.dumps(request_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    if normalized_link_path.exists() or normalized_link_path.is_symlink():
        normalized_link_path.unlink()
    normalized_link_path.symlink_to(normalized_document_path.resolve())

    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "is_procurement_doc": procurement_context.is_procurement_doc.value,
        "buyer": procurement_context.buyer,
        "seller": procurement_context.seller,
        "procurement_category": (
            procurement_context.procurement_category.value
            if procurement_context.procurement_category is not None
            else None
        ),
        "confidence": procurement_context.confidence,
        "staged_procurement_context_path": repo_relative_path(context_path, repo_root),
        "staged_request_path": repo_relative_path(request_path, repo_root),
        "staged_normalized_xml_link": repo_relative_path(normalized_link_path, repo_root),
        "normalized_document_path": repo_relative_path(normalized_document_path, repo_root),
    }


def infer_one_manifest(
    manifest_path: Path,
    *,
    config: ProcurementContextStageConfig,
    run_dir: Path,
) -> dict[str, object]:
    """Infer procurement context for one manifest and write staged outputs."""
    manifest = load_manifest(manifest_path)
    normalized_document_path = manifest_path.parent / "derived" / "normalized_document.xml"

    llm_config = ProcurementContextConfig(model=config.model)
    request = build_procurement_context_input(
        doc_id=manifest.doc_id,
        source_filename=manifest.source_filename,
        model=llm_config.model,
        normalized_document_path=normalized_document_path,
    )
    request_payload = request.model_dump()
    request_payload["normalized_document_path"] = repo_relative_path(normalized_document_path, config.repo_root)
    procurement_context = run_procurement_context(request, llm_config)

    return write_staged_doc_outputs(
        repo_root=config.repo_root,
        run_dir=run_dir,
        manifest=manifest,
        normalized_document_path=normalized_document_path,
        procurement_context=procurement_context,
        request_payload=request_payload,
    )


def execute_procurement_context_run(
    *,
    config: ProcurementContextStageConfig,
    doc_id: str | None = None,
    random_n: int | None = None,
    seed: int = 42,
    force: bool = False,
) -> tuple[dict[str, object], Path]:
    """Run a staged procurement-context pass without mutating manifests."""
    selected = selected_manifest_paths(
        config,
        doc_id=doc_id,
        random_n=random_n,
        seed=seed,
        force=force,
    )
    run_id = run_timestamp()
    run_dir = run_output_dir(config.runs_dir, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info(
        "Starting procurement-context dry run | selected=%s | workers=%s",
        len(selected),
        config.workers,
    )

    successes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    if config.workers <= 1:
        for manifest_path in selected:
            try:
                successes.append(infer_one_manifest(manifest_path, config=config, run_dir=run_dir))
            except Exception as error:  # noqa: BLE001
                failures.append(
                    {
                        "doc_id": manifest_path.parent.name,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    }
                )
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.workers) as executor:
            futures = {
                executor.submit(infer_one_manifest, manifest_path, config=config, run_dir=run_dir): manifest_path
                for manifest_path in selected
            }
            for future in concurrent.futures.as_completed(futures):
                manifest_path = futures[future]
                try:
                    successes.append(future.result())
                except Exception as error:  # noqa: BLE001
                    failures.append(
                        {
                            "doc_id": manifest_path.parent.name,
                            "error": str(error),
                            "traceback": traceback.format_exc(),
                        }
                    )

    successes = sorted(successes, key=lambda item: str(item["doc_id"]))
    failures = sorted(failures, key=lambda item: str(item["doc_id"]))
    report = {
        "mode": "dry_run",
        "run_id": run_id,
        "model": config.model,
        "workers": config.workers,
        "random_n": random_n,
        "seed": seed if random_n is not None else None,
        "force": force,
        "documents_selected": len(selected),
        "documents_succeeded": len(successes),
        "documents_failed": len(failures),
        "results": successes,
        "failures": failures,
    }
    report_path = run_dir / "procurement_context_run_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report, report_path


def apply_procurement_context_run(
    *,
    config: ProcurementContextStageConfig,
    run_report_path: Path,
    force: bool = False,
) -> dict[str, object]:
    """Apply a staged procurement-context run into canonical derived outputs and manifests."""
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    results = report.get("results", [])
    applied: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for item in results:
        doc_id = item["doc_id"]
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        manifest = load_manifest(manifest_path)
        if manifest.procurement_context_path and not force:
            skipped.append({"doc_id": doc_id, "reason": "already_processed"})
            continue

        staged_context_path = config.repo_root / item["staged_procurement_context_path"]
        canonical_path = manifest_path.parent / "derived" / "procurement_context.json"
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_context_path, canonical_path)

        manifest.procurement_context_path = repo_relative_path(canonical_path, config.repo_root)
        manifest.procurement_context_status = completed_procurement_context_status()
        upsert_derived_artifact(
            manifest,
            kind=ArtifactKind.JSON,
            path=manifest.procurement_context_path,
            description="Procurement context result",
        )
        write_manifest(manifest_path, manifest)
        applied.append(
            {
                "doc_id": doc_id,
                "procurement_context_path": manifest.procurement_context_path,
            }
        )

    apply_report = {
        "mode": "apply",
        "source_run_report": repo_relative_path(run_report_path, config.repo_root),
        "documents_seen": len(results),
        "documents_applied": len(applied),
        "documents_skipped": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }
    output_path = config.indexes_dir / "procurement_context_apply_report.json"
    output_path.write_text(json.dumps(apply_report, indent=2) + "\n", encoding="utf-8")
    return {"report": apply_report, "report_path": output_path}
