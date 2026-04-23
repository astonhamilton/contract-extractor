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

from packages.llm.transforms.page_notes.config import PageNotesConfig
from packages.llm.transforms.page_notes.task import build_page_notes_input, run_page_note
from packages.llm.shared.task_runtime.debug import usage_summary_from_debug_dir
from packages.pipeline.classification_stage import upsert_derived_artifact
from packages.pipeline.normalize.assemble_page_notes_document import normalized_page_notes_xml
from packages.pipeline.normalize.normalized_document_pages import parse_normalized_document_pages
from packages.pipeline.normalize.page_token_analysis import build_page_token_profiles
from packages.pipeline.normalize.pdf_pages import load_manifest, repo_relative_path, write_manifest
from packages.schemas import ArtifactKind, DocumentManifest, PageNote, PageNotesDocument
from packages.schemas.common import ProcessingStatus, StageStatus


LOGGER = logging.getLogger(__name__)

PAGE_NOTES_JSON_DESCRIPTION = "Document-level page notes JSON"
PAGE_NOTES_XML_DESCRIPTION = "Canonical normalized page notes XML assembled from page-level notes."


@dataclass(frozen=True)
class PageNotesStageConfig:
    """Static configuration for canonical page-notes analysis and execution."""

    repo_root: Path
    processed_contracts_dir: Path
    runs_dir: Path
    indexes_dir: Path
    model: str = "openai/gpt-5.4-mini"
    reasoning_effort: str | None = None
    structured_output: bool = True
    workers: int = 1
    page_workers: int = 1
    selection_token_threshold: int = 20_000


def run_timestamp() -> str:
    """Return a stable UTC timestamp for one page-notes run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def completed_page_notes_status() -> StageStatus:
    """Return a completed status block for validated page-notes outputs."""
    return StageStatus(status=ProcessingStatus.COMPLETED)


def candidate_profiles(config: PageNotesStageConfig) -> list[dict[str, object]]:
    """Return page-token profiles for docs selected into the page-notes target set."""
    profiles = build_page_token_profiles(config.repo_root, config.processed_contracts_dir)
    selected = [
        profile
        for profile in profiles
        if int(dict(profile.get("summary", {})).get("total_tokens", 0)) >= config.selection_token_threshold
    ]
    return sorted(
        selected,
        key=lambda profile: (
            -int(dict(profile.get("summary", {})).get("total_tokens", 0)),
            str(profile.get("source_filename", "")),
        ),
    )


def page_notes_analysis(
    config: PageNotesStageConfig,
    *,
    top_n: int = 20,
) -> dict[str, object]:
    """Build an analysis report for the current page-notes candidate set."""
    profiles = candidate_profiles(config)
    targeted_pages_total = sum(int(dict(profile["summary"]).get("page_count", 0)) for profile in profiles)
    targeted_tokens_total = sum(int(dict(profile["summary"]).get("total_tokens", 0)) for profile in profiles)
    targeted_chars_total = sum(int(dict(profile["summary"]).get("total_chars", 0)) for profile in profiles)

    top_documents = []
    for profile in profiles[:top_n]:
        summary = dict(profile["summary"])
        top_documents.append(
            {
                "doc_id": profile["doc_id"],
                "source_filename": profile["source_filename"],
                "page_source": profile["page_source"],
                "normalized_document_path": profile["normalized_document_path"],
                "page_count": summary["page_count"],
                "total_chars": summary["total_chars"],
                "total_tokens": summary["total_tokens"],
                "avg_chars_per_page": summary["avg_chars_per_page"],
                "avg_tokens_per_page": summary["avg_tokens_per_page"],
                "median_tokens_per_page": summary["median_tokens_per_page"],
                "max_page_chars": summary["max_page_chars"],
                "max_page_tokens": summary["max_page_tokens"],
                "top_five_pages_token_share": summary["top_five_pages_token_share"],
                "dense_pages_over_400_tokens": summary["dense_pages_over_400_tokens"],
            }
        )

    return {
        "selection_token_threshold": config.selection_token_threshold,
        "documents_targeted": len(profiles),
        "targeted_pages_total": targeted_pages_total,
        "targeted_tokens_total": targeted_tokens_total,
        "targeted_chars_total": targeted_chars_total,
        "top_n": top_n,
        "top_documents": top_documents,
    }


def write_page_notes_analysis_report(report_path: Path, report: dict[str, object]) -> None:
    """Write a page-notes analysis report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def iter_eligible_manifest_paths(
    config: PageNotesStageConfig,
    *,
    include_already_processed: bool,
) -> list[Path]:
    """Return manifest paths eligible for page-notes execution."""
    manifest_paths: list[Path] = []
    target_doc_ids = {profile["doc_id"] for profile in candidate_profiles(config)}
    for doc_id in sorted(target_doc_ids):
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        normalized_document_path = config.processed_contracts_dir / doc_id / "derived" / "normalized_document.xml"
        if not manifest_path.exists() or not normalized_document_path.exists():
            continue
        manifest = load_manifest(manifest_path)
        if not include_already_processed and manifest.page_notes_path:
            continue
        manifest_paths.append(manifest_path)
    return manifest_paths


def selected_manifest_paths(
    config: PageNotesStageConfig,
    *,
    doc_id: str | None,
    random_n: int | None,
    seed: int,
    force: bool,
) -> list[Path]:
    """Resolve target manifest paths from selection options."""
    eligible = iter_eligible_manifest_paths(config, include_already_processed=force)
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
    """Return the output directory for one staged page-notes run."""
    return runs_dir / run_id


def doc_run_dir(run_dir: Path, doc_id: str) -> Path:
    """Return the staged subdirectory for one document within a run."""
    return run_dir / doc_id


def _page_output_paths(doc_output_dir: Path, page_number: int) -> tuple[Path, Path]:
    """Return staged page-note and debug paths for one page."""
    pages_dir = doc_output_dir / "pages" / "page_notes"
    debug_dir = doc_output_dir / "llm_debug" / f"{page_number:04d}"
    return pages_dir / f"{page_number:04d}.json", debug_dir


def _canonical_page_note_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical per-page note path for one page."""
    return doc_dir / "pages" / "page_notes" / f"{page_number:04d}.json"


def _load_existing_page_note(
    *,
    path: Path,
    expected_doc_id: str,
    expected_source_filename: str,
    expected_page_number: int,
) -> PageNote | None:
    """Return a validated existing page note when it matches the expected envelope."""
    if not path.exists():
        return None
    try:
        note = PageNote.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if (
        note.doc_id != expected_doc_id
        or note.source_filename != expected_source_filename
        or note.page_number != expected_page_number
    ):
        return None
    return note


def aggregate_usage_summaries(items: list[dict[str, object]]) -> dict[str, object] | None:
    """Aggregate usage summaries across successful page-notes runs."""
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


def _run_one_page(
    *,
    manifest: DocumentManifest,
    normalized_document_path: Path,
    page: dict[str, object],
    llm_config: PageNotesConfig,
    debug_llm_dump: bool,
    doc_output_dir: Path,
    repo_root: Path,
):
    page_number = int(page["page_number"])
    request = build_page_notes_input(
        doc_id=manifest.doc_id,
        source_filename=manifest.source_filename,
        model=llm_config.model,
        normalized_document_path=repo_relative_path(normalized_document_path, repo_root),
        page_number=page_number,
        page_text=str(page.get("content") or ""),
        page_representation=str(page.get("representation") or "missing"),
        page_quality_flags=list(page.get("quality_flags") or []),
    )
    page_output_path, debug_dir = _page_output_paths(doc_output_dir, page_number)
    page_output_path.parent.mkdir(parents=True, exist_ok=True)
    if debug_llm_dump:
        debug_dir.mkdir(parents=True, exist_ok=True)
    note = run_page_note(
        request,
        llm_config,
        debug_dump_dir=str(debug_dir) if debug_llm_dump else None,
    )
    page_output_path.write_text(
        json.dumps(note.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return note


def write_staged_doc_outputs(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest: DocumentManifest,
    normalized_document_path: Path,
    request_payload: dict[str, object],
    page_notes_document: PageNotesDocument,
) -> dict[str, object]:
    """Write staged page-notes outputs for one document."""
    output_dir = doc_run_dir(run_dir, manifest.doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_notes_json_path = output_dir / "page_notes.json"
    page_notes_xml_path = output_dir / "normalized_page_notes.xml"
    request_path = output_dir / "page_notes_request.json"
    normalized_link_path = output_dir / "normalized_document.xml"

    page_notes_json_path.write_text(
        json.dumps(page_notes_document.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    page_notes_xml_path.write_text(
        normalized_page_notes_xml(page_notes_document),
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
        "page_count_processed": len(page_notes_document.page_notes),
        "staged_page_notes_json_path": repo_relative_path(page_notes_json_path, repo_root),
        "staged_page_notes_xml_path": repo_relative_path(page_notes_xml_path, repo_root),
        "staged_request_path": repo_relative_path(request_path, repo_root),
        "staged_normalized_xml_link": repo_relative_path(normalized_link_path, repo_root),
        "normalized_document_path": repo_relative_path(normalized_document_path, repo_root),
    }


def generate_one_manifest(
    manifest_path: Path,
    *,
    config: PageNotesStageConfig,
    run_dir: Path,
    debug_llm_dump: bool,
    force: bool = False,
) -> dict[str, object]:
    """Generate page notes for one manifest and write staged outputs."""
    manifest = load_manifest(manifest_path)
    doc_dir = manifest_path.parent
    normalized_document_path = manifest_path.parent / "derived" / "normalized_document.xml"
    page_payloads = parse_normalized_document_pages(normalized_document_path)
    llm_config = PageNotesConfig(
        model=config.model,
        reasoning_effort=config.reasoning_effort,
        structured_output=config.structured_output,
    )
    doc_output_dir = doc_run_dir(run_dir, manifest.doc_id)
    doc_output_dir.mkdir(parents=True, exist_ok=True)
    reused_notes: list[PageNote] = []
    pages_to_generate: list[dict[str, object]] = []
    for page in page_payloads:
        page_number = int(page["page_number"])
        existing_note = None if force else _load_existing_page_note(
            path=_canonical_page_note_path(doc_dir, page_number),
            expected_doc_id=manifest.doc_id,
            expected_source_filename=manifest.source_filename,
            expected_page_number=page_number,
        )
        if existing_note is None:
            pages_to_generate.append(page)
            continue
        reused_notes.append(existing_note)
        page_output_path, _ = _page_output_paths(doc_output_dir, page_number)
        page_output_path.parent.mkdir(parents=True, exist_ok=True)
        page_output_path.write_text(
            json.dumps(existing_note.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )

    generated_notes: list[PageNote]
    if not pages_to_generate:
        generated_notes = []
    elif config.page_workers <= 1:
        generated_notes = [
            _run_one_page(
                manifest=manifest,
                normalized_document_path=normalized_document_path,
                page=page,
                llm_config=llm_config,
                debug_llm_dump=debug_llm_dump,
                doc_output_dir=doc_output_dir,
                repo_root=config.repo_root,
            )
            for page in pages_to_generate
        ]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.page_workers) as executor:
            futures = [
                executor.submit(
                    _run_one_page,
                    manifest=manifest,
                    normalized_document_path=normalized_document_path,
                    page=page,
                    llm_config=llm_config,
                    debug_llm_dump=debug_llm_dump,
                    doc_output_dir=doc_output_dir,
                    repo_root=config.repo_root,
                )
                for page in pages_to_generate
            ]
            generated_notes = [future.result() for future in concurrent.futures.as_completed(futures)]

    notes = sorted([*reused_notes, *generated_notes], key=lambda note: note.page_number)

    page_notes_document = PageNotesDocument(
        doc_id=manifest.doc_id,
        source_filename=manifest.source_filename,
        page_notes=notes,
        status=completed_page_notes_status(),
    )
    request_payload = {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "structured_output": config.structured_output,
        "workers": config.workers,
        "page_workers": config.page_workers,
        "normalized_document_path": repo_relative_path(normalized_document_path, config.repo_root),
        "pages_selected": len(page_payloads),
    }
    result = write_staged_doc_outputs(
        repo_root=config.repo_root,
        run_dir=run_dir,
        manifest=manifest,
        normalized_document_path=normalized_document_path,
        request_payload=request_payload,
        page_notes_document=page_notes_document,
    )
    result["usage_summary"] = (
        usage_summary_from_debug_dir(doc_output_dir / "llm_debug", max_tokens=llm_config.max_tokens)
        if debug_llm_dump
        else None
    )
    result["page_count_reused"] = len(reused_notes)
    result["page_count_generated"] = len(generated_notes)
    return result


def execute_page_notes_run(
    *,
    config: PageNotesStageConfig,
    doc_id: str | None = None,
    random_n: int | None = None,
    seed: int = 42,
    force: bool = False,
    debug_llm_dump: bool = False,
) -> tuple[dict[str, object], Path]:
    """Run a staged page-notes pass without mutating manifests."""
    selected = selected_manifest_paths(config, doc_id=doc_id, random_n=random_n, seed=seed, force=force)
    run_id = run_timestamp()
    run_dir = run_output_dir(config.runs_dir, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    successes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    if config.workers <= 1:
        for manifest_path in selected:
            try:
                successes.append(
                    generate_one_manifest(
                        manifest_path,
                        config=config,
                        run_dir=run_dir,
                        debug_llm_dump=debug_llm_dump,
                        force=force,
                    )
                )
            except Exception as error:  # noqa: BLE001
                failures.append({"doc_id": manifest_path.parent.name, "error": str(error), "traceback": traceback.format_exc()})
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.workers) as executor:
            futures = {
                executor.submit(
                    generate_one_manifest,
                    manifest_path,
                    config=config,
                    run_dir=run_dir,
                    debug_llm_dump=debug_llm_dump,
                    force=force,
                ): manifest_path
                for manifest_path in selected
            }
            for future in concurrent.futures.as_completed(futures):
                manifest_path = futures[future]
                try:
                    successes.append(future.result())
                except Exception as error:  # noqa: BLE001
                    failures.append({"doc_id": manifest_path.parent.name, "error": str(error), "traceback": traceback.format_exc()})

    successes = sorted(successes, key=lambda item: str(item["doc_id"]))
    failures = sorted(failures, key=lambda item: str(item["doc_id"]))
    report = {
        "mode": "dry_run",
        "run_id": run_id,
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "structured_output": config.structured_output,
        "workers": config.workers,
        "page_workers": config.page_workers,
        "random_n": random_n,
        "seed": seed if random_n is not None else None,
        "force": force,
        "selection_token_threshold": config.selection_token_threshold,
        "documents_selected": len(selected),
        "documents_succeeded": len(successes),
        "documents_failed": len(failures),
        "results": successes,
        "failures": failures,
        "usage_summary": aggregate_usage_summaries(successes),
    }
    report_path = run_dir / "page_notes_run_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report, report_path


def apply_page_notes_run(
    *,
    config: PageNotesStageConfig,
    run_report_path: Path,
    force: bool = False,
) -> dict[str, object]:
    """Apply a staged page-notes run into canonical derived outputs and manifests."""
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    results = report.get("results", [])
    applied: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for item in results:
        doc_id = item["doc_id"]
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        manifest = load_manifest(manifest_path)
        if manifest.page_notes_path and not force:
            skipped.append({"doc_id": doc_id, "reason": "already_processed"})
            continue

        doc_dir = manifest_path.parent
        canonical_pages_dir = doc_dir / "pages" / "page_notes"
        canonical_pages_dir.mkdir(parents=True, exist_ok=True)
        staged_pages_dir = config.repo_root / Path(item["staged_page_notes_json_path"]).parent / "pages" / "page_notes"
        if staged_pages_dir.exists():
            if canonical_pages_dir.exists():
                shutil.rmtree(canonical_pages_dir)
                canonical_pages_dir.mkdir(parents=True, exist_ok=True)
            for staged_page_path in sorted(staged_pages_dir.glob("*.json")):
                shutil.copyfile(staged_page_path, canonical_pages_dir / staged_page_path.name)

        staged_json_path = config.repo_root / item["staged_page_notes_json_path"]
        staged_xml_path = config.repo_root / item["staged_page_notes_xml_path"]
        canonical_json_path = doc_dir / "derived" / "page_notes.json"
        canonical_xml_path = doc_dir / "derived" / "normalized_page_notes.xml"
        canonical_json_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_json_path, canonical_json_path)
        shutil.copyfile(staged_xml_path, canonical_xml_path)

        manifest.page_notes_path = repo_relative_path(canonical_xml_path, config.repo_root)
        manifest.page_notes_status = completed_page_notes_status()
        upsert_derived_artifact(
            manifest,
            kind=ArtifactKind.JSON,
            path=repo_relative_path(canonical_json_path, config.repo_root),
            description=PAGE_NOTES_JSON_DESCRIPTION,
        )
        upsert_derived_artifact(
            manifest,
            kind=ArtifactKind.XML,
            path=manifest.page_notes_path,
            description=PAGE_NOTES_XML_DESCRIPTION,
        )
        write_manifest(manifest_path, manifest)
        applied.append({"doc_id": doc_id, "page_notes_path": manifest.page_notes_path})

    apply_report = {
        "mode": "apply",
        "source_run_report": repo_relative_path(run_report_path, config.repo_root),
        "documents_seen": len(results),
        "documents_applied": len(applied),
        "documents_skipped": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }
    output_path = config.indexes_dir / "page_notes_apply_report.json"
    output_path.write_text(json.dumps(apply_report, indent=2) + "\n", encoding="utf-8")
    return {"report": apply_report, "report_path": output_path}
