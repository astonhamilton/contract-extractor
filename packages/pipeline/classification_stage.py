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

from packages.llm.transforms.document_classification.config import DocumentClassificationConfig
from packages.llm.transforms.document_classification.task import build_classification_input, run_document_classification
from packages.pipeline.normalize.pdf_pages import (
    load_manifest,
    repo_relative_path,
    write_manifest,
)
from packages.schemas import (
    ArtifactKind,
    DerivedArtifact,
    DocumentClassification,
    DocumentManifest,
    ProcessingStatus,
    StageStatus,
    completed_classification_status,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassificationStageConfig:
    repo_root: Path
    processed_contracts_dir: Path
    runs_dir: Path
    indexes_dir: Path
    model: str = "openai/gpt-5.4-mini"
    reasoning_effort: str = "medium"
    workers: int = 1


def run_timestamp() -> str:
    """Return a stable UTC timestamp for one classification run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def iter_eligible_manifest_paths(
    processed_contracts_dir: Path,
    *,
    include_already_classified: bool,
) -> list[Path]:
    """Return manifest paths eligible for classification execution."""
    manifest_paths: list[Path] = []
    for doc_dir in sorted(processed_contracts_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        manifest_path = doc_dir / "manifest.json"
        normalized_document_path = doc_dir / "derived" / "normalized_document.xml"
        if not manifest_path.exists() or not normalized_document_path.exists():
            continue
        manifest = load_manifest(manifest_path)
        if not include_already_classified and manifest.classification_path:
            continue
        manifest_paths.append(manifest_path)
    return manifest_paths


def selected_manifest_paths(
    config: ClassificationStageConfig,
    *,
    doc_id: str | None,
    random_n: int | None,
    seed: int,
    force: bool,
) -> list[Path]:
    """Resolve target manifest paths from selection options."""
    eligible = iter_eligible_manifest_paths(
        config.processed_contracts_dir,
        include_already_classified=force,
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
    """Return the output directory for one staged classification run."""
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
    classification: DocumentClassification,
    request_payload: dict[str, object],
) -> dict[str, object]:
    """Write staged classification outputs for one document."""
    output_dir = doc_run_dir(run_dir, manifest.doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    classification_path = output_dir / "classification.json"
    request_path = output_dir / "classification_request.json"
    normalized_link_path = output_dir / "normalized_document.xml"

    classification_path.write_text(
        json.dumps(classification.model_dump(mode="json"), indent=2) + "\n",
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
        "procurement_stage": classification.procurement_stage.value,
        "primary_document_role": classification.primary_document_role.value,
        "change_kind": classification.change_kind.value if classification.change_kind else None,
        "confidence": classification.confidence,
        "staged_classification_path": repo_relative_path(classification_path, repo_root),
        "staged_request_path": repo_relative_path(request_path, repo_root),
        "staged_normalized_xml_link": repo_relative_path(normalized_link_path, repo_root),
        "normalized_document_path": repo_relative_path(normalized_document_path, repo_root),
    }


def classify_one_manifest(
    manifest_path: Path,
    *,
    config: ClassificationStageConfig,
    run_dir: Path,
) -> dict[str, object]:
    """Classify one manifest and write staged outputs."""
    manifest = load_manifest(manifest_path)
    normalized_document_path = manifest_path.parent / "derived" / "normalized_document.xml"

    llm_config = DocumentClassificationConfig(
        model=config.model,
        reasoning_effort=config.reasoning_effort,
    )
    request = build_classification_input(
        doc_id=manifest.doc_id,
        source_filename=manifest.source_filename,
        model=llm_config.model,
        normalized_document_path=normalized_document_path,
    )
    request_payload = request.model_dump()
    request_payload["normalized_document_path"] = repo_relative_path(normalized_document_path, config.repo_root)
    classification = run_document_classification(request, llm_config)

    return write_staged_doc_outputs(
        repo_root=config.repo_root,
        run_dir=run_dir,
        manifest=manifest,
        normalized_document_path=normalized_document_path,
        classification=classification,
        request_payload=request_payload,
    )


def execute_classification_run(
    *,
    config: ClassificationStageConfig,
    doc_id: str | None = None,
    random_n: int | None = None,
    seed: int = 42,
    force: bool = False,
) -> tuple[dict[str, object], Path]:
    """Run a staged classification pass without mutating manifests."""
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
        "Starting classification dry run | selected=%s | workers=%s",
        len(selected),
        config.workers,
    )

    successes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    if config.workers <= 1:
        for manifest_path in selected:
            try:
                successes.append(classify_one_manifest(manifest_path, config=config, run_dir=run_dir))
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
                executor.submit(classify_one_manifest, manifest_path, config=config, run_dir=run_dir): manifest_path
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
        "reasoning_effort": config.reasoning_effort,
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
    report_path = run_dir / "classification_run_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report, report_path


def upsert_derived_artifact(
    manifest: DocumentManifest,
    *,
    kind: ArtifactKind,
    path: str,
    description: str,
) -> None:
    """Insert or update one derived artifact entry on a manifest."""
    updated = False
    for artifact in manifest.derived_artifacts:
        if artifact.path == path or artifact.description == description:
            artifact.kind = kind
            artifact.path = path
            artifact.description = description
            updated = True
            break
    if not updated:
        manifest.derived_artifacts.append(
            DerivedArtifact(kind=kind, path=path, description=description)
        )


def apply_classification_run(
    *,
    config: ClassificationStageConfig,
    run_report_path: Path,
    force: bool = False,
) -> dict[str, object]:
    """Apply a staged classification run into canonical derived outputs and manifests."""
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    results = report.get("results", [])
    applied: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for item in results:
        doc_id = item["doc_id"]
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        manifest = load_manifest(manifest_path)
        if manifest.classification_path and not force:
            skipped.append({"doc_id": doc_id, "reason": "already_classified"})
            continue

        staged_classification_path = config.repo_root / item["staged_classification_path"]
        canonical_path = manifest_path.parent / "derived" / "classification.json"
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_classification_path, canonical_path)

        manifest.classification_path = repo_relative_path(canonical_path, config.repo_root)
        manifest.classification_status = completed_classification_status()
        upsert_derived_artifact(
            manifest,
            kind=ArtifactKind.JSON,
            path=manifest.classification_path,
            description="Document classification result",
        )
        write_manifest(manifest_path, manifest)
        applied.append(
            {
                "doc_id": doc_id,
                "classification_path": manifest.classification_path,
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
    output_path = config.indexes_dir / "classification_apply_report.json"
    output_path.write_text(json.dumps(apply_report, indent=2) + "\n", encoding="utf-8")
    return {"report": apply_report, "report_path": output_path}
