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

from packages.llm.transforms.governing_domain_notes.config import GoverningDomainNotesConfig
from packages.llm.transforms.governing_domain_notes.task import (
    build_governing_domain_notes_input,
    run_governing_domain_notes_adaptive,
)
from packages.llm.shared.task_runtime.debug import usage_summary_from_debug_dir
from packages.pipeline.classification_stage import upsert_derived_artifact
from packages.pipeline.normalize.pdf_pages import load_manifest, repo_relative_path, write_manifest
from packages.schemas import (
    ArtifactKind,
    DocumentClassification,
    DocumentManifest,
    GoverningDomainNotes,
    completed_governing_domain_notes_status,
)
from packages.llm.transforms.document_classification.coerce import coerce_document_classification_payload


LOGGER = logging.getLogger(__name__)

GOVERNING_DOMAIN_NOTES_JSON_DESCRIPTION = "Governing contract domain notes JSON"


@dataclass(frozen=True)
class GoverningDomainNotesStageConfig:
    """Static configuration for canonical governing-domain-notes execution."""

    repo_root: Path
    processed_contracts_dir: Path
    runs_dir: Path
    indexes_dir: Path
    model: str = "openai/gpt-5.4-mini"
    reasoning_effort: str | None = None
    workers: int = 1


def run_timestamp() -> str:
    """Return a stable UTC timestamp for one governing-domain-notes run."""
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
    """Return manifest paths eligible for governing-domain-notes execution."""
    manifest_paths: list[Path] = []
    for doc_dir in sorted(processed_contracts_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        manifest_path = doc_dir / "manifest.json"
        normalized_document_path = doc_dir / "derived" / "normalized_document.xml"
        if not manifest_path.exists() or not normalized_document_path.exists():
            continue
        manifest = load_manifest(manifest_path)
        if not include_already_processed and manifest.governing_domain_notes_path:
            continue
        classification = load_classification(doc_dir)
        if classification and classification.routes_to_governing_domain_notes:
            manifest_paths.append(manifest_path)
    return manifest_paths


def selected_manifest_paths(
    config: GoverningDomainNotesStageConfig,
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
    """Return the output directory for one staged governing-domain-notes run."""
    return runs_dir / run_id


def doc_run_dir(run_dir: Path, doc_id: str) -> Path:
    """Return the staged subdirectory for one document within a run."""
    return run_dir / doc_id


def aggregate_usage_summaries(items: list[dict[str, object]]) -> dict[str, object] | None:
    """Aggregate usage summaries across successful governing-domain-notes runs."""
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
    notes: GoverningDomainNotes,
    request_payload: dict[str, object],
    usage_summary: dict[str, object],
    attempted_domain_groups: list[list[str]],
    used_adaptive_split: bool,
) -> dict[str, object]:
    """Write staged governing-domain-notes outputs for one document."""
    output_dir = doc_run_dir(run_dir, manifest.doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    notes_path = output_dir / "governing_domain_notes.json"
    request_path = output_dir / "governing_domain_notes_request.json"
    normalized_link_path = output_dir / "normalized_document.xml"

    notes_path.write_text(
        json.dumps(notes.model_dump(mode="json"), indent=2) + "\n",
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
        "usage_summary": usage_summary,
        "adaptive_execution": {
            "used_adaptive_split": used_adaptive_split,
            "attempted_domain_groups": attempted_domain_groups,
        },
        "staged_governing_domain_notes_path": repo_relative_path(notes_path, repo_root),
        "staged_request_path": repo_relative_path(request_path, repo_root),
        "staged_normalized_xml_link": repo_relative_path(normalized_link_path, repo_root),
        "normalized_document_path": repo_relative_path(normalized_document_path, repo_root),
    }


def infer_one_manifest(
    manifest_path: Path,
    *,
    config: GoverningDomainNotesStageConfig,
    run_dir: Path,
) -> dict[str, object]:
    """Infer governing-domain notes for one manifest and write staged outputs."""
    manifest = load_manifest(manifest_path)
    normalized_document_path = manifest_path.parent / "derived" / "normalized_document.xml"
    llm_config = GoverningDomainNotesConfig(
        model=config.model,
        reasoning_effort=config.reasoning_effort,
    )
    request = build_governing_domain_notes_input(
        doc_id=manifest.doc_id,
        source_filename=manifest.source_filename,
        model=llm_config.model,
        normalized_document_path=normalized_document_path,
    )
    debug_dir = doc_run_dir(run_dir, manifest.doc_id) / "llm_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    notes, adaptive_result = run_governing_domain_notes_adaptive(
        request,
        llm_config,
        debug_dump_dir=debug_dir,
    )
    usage_summary = usage_summary_from_debug_dir(debug_dir, max_tokens=llm_config.max_tokens)
    request_payload = request.model_dump()
    request_payload["normalized_document_path"] = repo_relative_path(normalized_document_path, config.repo_root)
    return write_staged_doc_outputs(
        repo_root=config.repo_root,
        run_dir=run_dir,
        manifest=manifest,
        normalized_document_path=normalized_document_path,
        notes=notes,
        request_payload=request_payload,
        usage_summary=usage_summary,
        attempted_domain_groups=[list(group) for group in adaptive_result.attempted_domain_groups],
        used_adaptive_split=adaptive_result.used_adaptive_split,
    )


def execute_governing_domain_notes_run(
    *,
    config: GoverningDomainNotesStageConfig,
    doc_id: str | None = None,
    random_n: int | None = None,
    seed: int = 42,
    force: bool = False,
) -> tuple[dict[str, object], Path]:
    """Run a staged governing-domain-notes pass without mutating manifests."""
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
        "Starting governing-domain-notes dry run | selected=%s | workers=%s",
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
                        debug_dir, max_tokens=config_reasoning_max_tokens(config)
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
                            debug_dir, max_tokens=config_reasoning_max_tokens(config)
                        )
                    failures.append(failure_payload)

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
        "usage_summary": aggregate_usage_summaries(successes),
    }
    report_path = run_dir / "governing_domain_notes_run_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report, report_path


def apply_governing_domain_notes_run(
    *,
    config: GoverningDomainNotesStageConfig,
    run_report_path: Path,
    force: bool = False,
) -> dict[str, object]:
    """Apply a staged governing-domain-notes run into canonical derived outputs and manifests."""
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    results = report.get("results", [])
    applied: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for item in results:
        doc_id = item["doc_id"]
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        manifest = load_manifest(manifest_path)
        if manifest.governing_domain_notes_path and not force:
            skipped.append({"doc_id": doc_id, "reason": "already_processed"})
            continue

        staged_notes_path = config.repo_root / item["staged_governing_domain_notes_path"]
        canonical_notes_path = manifest_path.parent / "derived" / "governing_domain_notes.json"
        canonical_notes_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_notes_path, canonical_notes_path)

        manifest.governing_domain_notes_path = repo_relative_path(canonical_notes_path, config.repo_root)
        manifest.governing_domain_notes_status = completed_governing_domain_notes_status()
        upsert_derived_artifact(
            manifest,
            kind=ArtifactKind.JSON,
            path=manifest.governing_domain_notes_path,
            description=GOVERNING_DOMAIN_NOTES_JSON_DESCRIPTION,
        )
        write_manifest(manifest_path, manifest)
        applied.append(
            {
                "doc_id": doc_id,
                "governing_domain_notes_path": manifest.governing_domain_notes_path,
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
    output_path = config.indexes_dir / "governing_domain_notes_apply_report.json"
    output_path.write_text(json.dumps(apply_report, indent=2) + "\n", encoding="utf-8")
    return {"report": apply_report, "report_path": output_path}


def config_reasoning_max_tokens(config: GoverningDomainNotesStageConfig) -> int:
    """Return the configured max token budget for governing-domain-notes runs."""
    return GoverningDomainNotesConfig(
        model=config.model,
        reasoning_effort=config.reasoning_effort,
    ).max_tokens
