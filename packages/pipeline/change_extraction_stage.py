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

from packages.llm.transforms.change_extraction.config import ChangeExtractionConfig
from packages.llm.transforms.change_extraction.task import build_change_extraction_input, run_change_extraction
from packages.llm.transforms.document_classification.coerce import coerce_document_classification_payload
from packages.llm.shared.task_runtime.capabilities import effective_reasoning_effort
from packages.llm.shared.task_runtime.debug import usage_summary_from_debug_dir
from packages.pipeline.classification_stage import upsert_derived_artifact
from packages.pipeline.normalize.pdf_pages import load_manifest, repo_relative_path, write_manifest
from packages.schemas import (
    ArtifactKind,
    ChangeExtraction,
    DocumentClassification,
    DocumentManifest,
    completed_change_extraction_status,
)


LOGGER = logging.getLogger(__name__)

CHANGE_EXTRACTION_JSON_DESCRIPTION = "Change extraction JSON"
DEFAULT_OPENAI_MODEL = "openai/gpt-5.4-mini"
DEFAULT_ANTHROPIC_MODEL = "anthropic/claude-haiku-4-5"


@dataclass(frozen=True)
class ChangeExtractionStageConfig:
    """Static configuration for canonical change-extraction execution."""

    repo_root: Path
    processed_contracts_dir: Path
    runs_dir: Path
    indexes_dir: Path
    model: str = DEFAULT_OPENAI_MODEL
    reasoning_effort: str | None = None
    workers: int = 1


def run_timestamp() -> str:
    """Return a stable UTC timestamp for one change-extraction run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def load_classification(doc_dir: Path) -> DocumentClassification | None:
    """Load canonical classification for one document when present."""
    path = doc_dir / "derived" / "classification.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = coerce_document_classification_payload(payload)
    return DocumentClassification.model_validate(payload)


def iter_eligible_manifest_paths(
    processed_contracts_dir: Path,
    *,
    include_already_processed: bool,
) -> list[Path]:
    """Return manifest paths eligible for canonical change extraction."""
    manifest_paths: list[Path] = []
    for doc_dir in sorted(processed_contracts_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        manifest_path = doc_dir / "manifest.json"
        normalized_document_path = doc_dir / "derived" / "normalized_document.xml"
        if not manifest_path.exists() or not normalized_document_path.exists():
            continue
        manifest = load_manifest(manifest_path)
        if not include_already_processed and manifest.change_extraction_path:
            continue
        classification = load_classification(doc_dir)
        if classification and classification.routes_to_change_extraction:
            manifest_paths.append(manifest_path)
    return manifest_paths


def selected_manifest_paths(
    config: ChangeExtractionStageConfig,
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
    """Return the output directory for one staged change-extraction run."""
    return runs_dir / run_id


def doc_run_dir(run_dir: Path, doc_id: str) -> Path:
    """Return the staged subdirectory for one document within a run."""
    return run_dir / doc_id


def aggregate_usage_summaries(items: list[dict[str, object]]) -> dict[str, object] | None:
    """Aggregate usage summaries across successful change-extraction runs."""
    summaries = [item.get("usage_summary") for item in items if isinstance(item.get("usage_summary"), dict)]
    if not summaries:
        return None
    attempts_total = 0
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }
    reasoning_exhausted = False
    for summary in summaries:
        attempts = summary.get("attempts")
        if isinstance(attempts, list):
            attempts_total += len(attempts)
        summary_totals = summary.get("totals")
        if isinstance(summary_totals, dict):
            for key in totals:
                value = summary_totals.get(key)
                if isinstance(value, int):
                    totals[key] += value
        heuristics = summary.get("heuristics")
        if isinstance(heuristics, dict) and heuristics.get("likely_output_budget_exhausted_by_reasoning"):
            reasoning_exhausted = True
    return {
        "documents_with_usage": len(summaries),
        "attempts_total": attempts_total,
        "totals": totals,
        "heuristics": {
            "any_output_budget_exhausted_by_reasoning": reasoning_exhausted,
        },
    }


def write_staged_doc_outputs(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest: DocumentManifest,
    normalized_document_path: Path,
    classification_path: Path,
    extraction: ChangeExtraction,
    request_payload: dict[str, object],
    usage_summary: dict[str, object],
) -> dict[str, object]:
    """Write staged change-extraction outputs for one document."""
    output_dir = doc_run_dir(run_dir, manifest.doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    extraction_path = output_dir / "change_extraction.json"
    request_path = output_dir / "change_extraction_request.json"
    normalized_link_path = output_dir / "normalized_document.xml"
    classification_link_path = output_dir / "classification.json"

    extraction_path.write_text(
        json.dumps(extraction.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    request_path.write_text(
        json.dumps(request_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    for link_path, source_path in (
        (normalized_link_path, normalized_document_path),
        (classification_link_path, classification_path),
    ):
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(source_path.resolve())

    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "classified_change_kind": request_payload["classified_change_kind"],
        "target_artifact_answer": extraction.target_artifact.answer,
        "change_answer": extraction.change.answer,
        "change_dimensions": [dimension.value for dimension in extraction.change.dimensions],
        "resulting_state_answer": extraction.resulting_state.answer,
        "extraction_confidence": extraction.extraction_confidence,
        "usage_summary": usage_summary,
        "staged_change_extraction_path": repo_relative_path(extraction_path, repo_root),
        "staged_request_path": repo_relative_path(request_path, repo_root),
        "staged_normalized_xml_link": repo_relative_path(normalized_link_path, repo_root),
        "staged_classification_link": repo_relative_path(classification_link_path, repo_root),
        "staged_llm_debug_dir": repo_relative_path(output_dir / "llm_debug", repo_root),
        "normalized_document_path": repo_relative_path(normalized_document_path, repo_root),
    }


def infer_one_manifest(
    manifest_path: Path,
    *,
    config: ChangeExtractionStageConfig,
    run_dir: Path,
) -> dict[str, object]:
    """Infer change extraction for one manifest and write staged outputs."""
    manifest = load_manifest(manifest_path)
    doc_dir = manifest_path.parent
    normalized_document_path = doc_dir / "derived" / "normalized_document.xml"
    classification_path = doc_dir / "derived" / "classification.json"
    classification = load_classification(doc_dir)
    if classification is None:
        raise FileNotFoundError(f"Classification not found for change extraction: {classification_path}")
    if not classification.routes_to_change_extraction:
        raise ValueError(
            "Document does not route to change extraction: "
            f"{classification.procurement_stage.value}/{classification.primary_document_role.value} | {manifest.doc_id}"
        )
    if classification.change_kind is None:
        raise ValueError(f"Change document missing classified change_kind: {manifest.doc_id}")

    llm_config = ChangeExtractionConfig(
        model=config.model,
        reasoning_effort=config.reasoning_effort,
    )
    request = build_change_extraction_input(
        doc_id=manifest.doc_id,
        source_filename=manifest.source_filename,
        model=llm_config.model,
        normalized_document_path=normalized_document_path,
        classified_change_kind=classification.change_kind,
    )
    debug_dir = doc_run_dir(run_dir, manifest.doc_id) / "llm_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    extraction = run_change_extraction(
        request,
        llm_config,
        debug_dump_dir=debug_dir,
    )
    usage_summary = usage_summary_from_debug_dir(debug_dir, max_tokens=llm_config.max_tokens)
    request_payload = request.model_dump(mode="json")
    request_payload["normalized_document_path"] = repo_relative_path(normalized_document_path, config.repo_root)
    request_payload["classification_path"] = repo_relative_path(classification_path, config.repo_root)
    return write_staged_doc_outputs(
        repo_root=config.repo_root,
        run_dir=run_dir,
        manifest=manifest,
        normalized_document_path=normalized_document_path,
        classification_path=classification_path,
        extraction=extraction,
        request_payload=request_payload,
        usage_summary=usage_summary,
    )


def config_reasoning_max_tokens(config: ChangeExtractionStageConfig) -> int:
    """Return the configured max token budget for change-extraction runs."""
    return ChangeExtractionConfig(
        model=config.model,
        reasoning_effort=config.reasoning_effort,
    ).max_tokens


def execute_change_extraction_run(
    *,
    config: ChangeExtractionStageConfig,
    doc_id: str | None = None,
    random_n: int | None = None,
    seed: int = 42,
    force: bool = False,
) -> tuple[dict[str, object], Path]:
    """Run a staged change-extraction pass without mutating manifests."""
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
        "Starting change-extraction dry run | selected=%s | workers=%s",
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
                failure_payload = {
                    "doc_id": manifest_path.parent.name,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
                debug_dir = doc_run_dir(run_dir, manifest_path.parent.name) / "llm_debug"
                if debug_dir.exists():
                    failure_payload["usage_summary"] = usage_summary_from_debug_dir(
                        debug_dir,
                        max_tokens=config_reasoning_max_tokens(config),
                    )
                failures.append(failure_payload)
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
                    failure_payload = {
                        "doc_id": manifest_path.parent.name,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    }
                    debug_dir = doc_run_dir(run_dir, manifest_path.parent.name) / "llm_debug"
                    if debug_dir.exists():
                        failure_payload["usage_summary"] = usage_summary_from_debug_dir(
                            debug_dir,
                            max_tokens=config_reasoning_max_tokens(config),
                        )
                    failures.append(failure_payload)

    successes = sorted(successes, key=lambda item: str(item["doc_id"]))
    failures = sorted(failures, key=lambda item: str(item["doc_id"]))
    report = {
        "mode": "dry_run",
        "run_id": run_id,
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "effective_reasoning_effort": effective_reasoning_effort(config.model, config.reasoning_effort),
        "workers": config.workers,
        "random_n": random_n,
        "seed": seed if random_n is not None else None,
        "force": force,
        "documents_selected": len(selected),
        "documents_succeeded": len(successes),
        "documents_failed": len(failures),
        "results": successes,
        "failures": failures,
        "usage_summary": aggregate_usage_summaries(successes),
    }
    report_path = run_dir / "change_extraction_run_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report, report_path


def apply_change_extraction_run(
    *,
    config: ChangeExtractionStageConfig,
    run_report_path: Path,
    force: bool = False,
) -> dict[str, object]:
    """Apply a staged change-extraction run into canonical derived outputs and manifests."""
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    results = report.get("results", [])
    applied: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for item in results:
        doc_id = item["doc_id"]
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        manifest = load_manifest(manifest_path)
        if manifest.change_extraction_path and not force:
            skipped.append({"doc_id": doc_id, "reason": "already_processed"})
            continue

        staged_extraction_path = config.repo_root / item["staged_change_extraction_path"]
        canonical_extraction_path = manifest_path.parent / "derived" / "change_extraction.json"
        canonical_extraction_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_extraction_path, canonical_extraction_path)

        manifest.change_extraction_path = repo_relative_path(canonical_extraction_path, config.repo_root)
        manifest.change_extraction_status = completed_change_extraction_status()
        upsert_derived_artifact(
            manifest,
            kind=ArtifactKind.JSON,
            path=manifest.change_extraction_path,
            description=CHANGE_EXTRACTION_JSON_DESCRIPTION,
        )
        write_manifest(manifest_path, manifest)
        applied.append(
            {
                "doc_id": doc_id,
                "change_extraction_path": manifest.change_extraction_path,
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
    output_path = config.indexes_dir / "change_extraction_apply_report.json"
    output_path.write_text(json.dumps(apply_report, indent=2) + "\n", encoding="utf-8")
    return {"report": apply_report, "report_path": output_path}
