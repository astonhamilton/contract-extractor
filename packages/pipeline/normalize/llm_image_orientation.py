from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import random
import shutil
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from packages.llm.transforms.image_orientation_decision.config import ImageOrientationDecisionConfig
from packages.llm.transforms.image_orientation_decision.task import (
    build_image_orientation_input,
    run_image_orientation_decision,
)
from packages.llm.shared.task_runtime import usage_summary_from_debug_dir
from packages.pipeline.normalize.image_orientation import (
    merge_page_orientation_results,
    page_needs_orientation_validation,
    reset_page_orientation_fields,
    roll_up_doc_orientation_flags,
    write_upright_image,
)
from packages.pipeline.normalize.llm_selection import is_skipped_image_llm_page
from packages.pipeline.normalize.ocr_pages import (
    is_likely_blank_image,
    is_likely_low_information_image,
)
from packages.pipeline.normalize.pdf_pages import (
    absolute_repo_path,
    iter_manifest_paths,
    load_manifest,
    repo_relative_path,
    write_manifest,
)
from packages.schemas import DocumentManifest, PageArtifact


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMImageOrientationStageConfig:
    """Static configuration for canonical LLM image-orientation execution."""

    repo_root: Path
    processed_contracts_dir: Path
    runs_dir: Path
    indexes_dir: Path
    model: str = "openai/gpt-5.4-nano"
    reasoning_effort: str | None = "none"
    workers: int = 1


def run_timestamp() -> str:
    """Return a stable UTC timestamp for one LLM image-orientation run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def default_llm_orientation_worker_count() -> int:
    """Return a conservative default worker count for LLM image-orientation runs."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1, 8))


def llm_config(config: LLMImageOrientationStageConfig) -> ImageOrientationDecisionConfig:
    """Return the LLM config used for one stage run."""
    return ImageOrientationDecisionConfig(
        model=config.model,
        reasoning_effort=config.reasoning_effort,
    )


def orientation_output_path(base_dir: Path, page_number: int) -> Path:
    """Return the output upright-image path for one page under a base directory."""
    return base_dir / f"{page_number:04d}.llm-upright.png"


def run_output_dir(runs_dir: Path, run_id: str) -> Path:
    """Return the output directory for one staged LLM image-orientation run."""
    return runs_dir / run_id


def doc_run_dir(run_dir: Path, doc_id: str) -> Path:
    """Return the staged subdirectory for one document within a run."""
    return run_dir / doc_id


def total_tokens_from_usage_summary(usage_summary: dict[str, object] | None) -> int | None:
    """Return total tokens from a usage summary when available."""
    if not isinstance(usage_summary, dict):
        return None
    totals = usage_summary.get("totals")
    if not isinstance(totals, dict):
        return None
    total_tokens = totals.get("total_tokens")
    return total_tokens if isinstance(total_tokens, int) else None


def aggregate_usage_summaries(items: list[dict[str, object]]) -> dict[str, object] | None:
    """Aggregate usage summaries across successful runs."""
    summaries = [item.get("usage_summary") for item in items if isinstance(item.get("usage_summary"), dict)]
    if not summaries:
        return None
    totals = {
        "prompt_tokens": sum(
            summary.get("totals", {}).get("prompt_tokens", 0)
            for summary in summaries
            if isinstance(summary.get("totals"), dict)
        ),
        "completion_tokens": sum(
            summary.get("totals", {}).get("completion_tokens", 0)
            for summary in summaries
            if isinstance(summary.get("totals"), dict)
        ),
        "reasoning_tokens": sum(
            summary.get("totals", {}).get("reasoning_tokens", 0)
            for summary in summaries
            if isinstance(summary.get("totals"), dict)
        ),
        "total_tokens": sum(
            summary.get("totals", {}).get("total_tokens", 0)
            for summary in summaries
            if isinstance(summary.get("totals"), dict)
        ),
    }
    return {
        "documents_with_usage": len(summaries),
        "totals": totals,
    }


def usage_totals(usage_summary: dict[str, object] | None) -> dict[str, int]:
    """Return normalized integer usage totals from one usage summary."""
    if not isinstance(usage_summary, dict):
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }
    totals = usage_summary.get("totals")
    if not isinstance(totals, dict):
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }
    return {
        "prompt_tokens": int(totals.get("prompt_tokens") or 0),
        "completion_tokens": int(totals.get("completion_tokens") or 0),
        "reasoning_tokens": int(totals.get("reasoning_tokens") or 0),
        "total_tokens": int(totals.get("total_tokens") or 0),
    }


def add_usage_totals(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    """Return summed usage totals."""
    return {
        "prompt_tokens": left["prompt_tokens"] + right["prompt_tokens"],
        "completion_tokens": left["completion_tokens"] + right["completion_tokens"],
        "reasoning_tokens": left["reasoning_tokens"] + right["reasoning_tokens"],
        "total_tokens": left["total_tokens"] + right["total_tokens"],
    }


def page_is_skippable_for_llm_orientation(repo_root: Path, page: PageArtifact) -> bool:
    """Return whether a page should skip LLM orientation work."""
    if is_skipped_image_llm_page(page):
        return True
    if not page.image_path:
        return True
    image_path = absolute_repo_path(repo_root, page.image_path)
    if not image_path.exists():
        return True
    return is_likely_blank_image(image_path) or is_likely_low_information_image(image_path)


def page_needs_llm_orientation_validation(repo_root: Path, page: PageArtifact) -> bool:
    """Return whether a page should run through the canonical LLM orientation stage."""
    return page_needs_orientation_validation(repo_root, page) and not page_is_skippable_for_llm_orientation(repo_root, page)


def iter_eligible_manifest_paths(
    config: LLMImageOrientationStageConfig,
    *,
    include_already_processed: bool,
) -> list[Path]:
    """Return manifest paths eligible for canonical LLM image-orientation."""
    manifest_paths: list[Path] = []
    for manifest_path in iter_manifest_paths(config.processed_contracts_dir):
        manifest = load_manifest(manifest_path)
        if not include_already_processed and not any(
            page_needs_llm_orientation_validation(config.repo_root, page)
            for page in manifest.pages
        ):
            continue
        if include_already_processed:
            has_image_pages = any(page.image_path for page in manifest.pages)
            if not has_image_pages:
                continue
        manifest_paths.append(manifest_path)
    return manifest_paths


def selected_manifest_paths(
    config: LLMImageOrientationStageConfig,
    *,
    doc_id: str | None,
    force: bool,
) -> list[Path]:
    """Resolve target manifest paths from selection options."""
    eligible = iter_eligible_manifest_paths(
        config,
        include_already_processed=force,
    )
    if doc_id is not None:
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        if manifest_path not in eligible and not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found for doc_id={doc_id}")
        return [manifest_path]
    return eligible


def build_orientation_task(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest_path: Path,
    manifest: DocumentManifest,
    page: PageArtifact,
) -> dict[str, object]:
    """Build a serializable staged LLM orientation task for one page."""
    output_dir = doc_run_dir(run_dir, manifest.doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = absolute_repo_path(repo_root, str(page.image_path))
    return {
        "manifest_path": str(manifest_path),
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "page_number": page.page_number,
        "quality_flags": list(page.quality_flags),
        "image_path": str(image_path),
        "validated_output_path": str(orientation_output_path(output_dir, page.page_number)),
        "debug_dir": str(output_dir / f"{page.page_number:04d}.llm_debug"),
    }


def write_staged_page_outputs(
    *,
    repo_root: Path,
    run_dir: Path,
    result: dict[str, object],
    request_payload: dict[str, object],
) -> dict[str, object]:
    """Write staged outputs for one LLM image-orientation page."""
    output_dir = doc_run_dir(run_dir, str(result["doc_id"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    page_number = int(result["page_number"])
    request_path = output_dir / f"{page_number:04d}.orientation_request.json"
    decision_path = output_dir / f"{page_number:04d}.orientation_decision.json"
    source_link_path = output_dir / f"{page_number:04d}.source.png"
    source_image_path = Path(str(result["source_image_path"]))

    request_path.write_text(json.dumps(request_payload, indent=2) + "\n", encoding="utf-8")
    decision_payload = dict(result)
    decision_payload["staged_validated_image_path"] = repo_relative_path(
        Path(str(result["validated_image_path"])),
        repo_root,
    )
    decision_path.write_text(json.dumps(decision_payload, indent=2) + "\n", encoding="utf-8")
    if source_link_path.exists() or source_link_path.is_symlink():
        source_link_path.unlink()
    source_link_path.symlink_to(source_image_path.resolve())

    return {
        "doc_id": result["doc_id"],
        "source_filename": result["source_filename"],
        "page_number": page_number,
        "rotation_degrees": result["rotation_degrees"],
        "is_already_upright": result["is_already_upright"],
        "needs_manual_review": result["needs_manual_review"],
        "confidence": result["confidence"],
        "reason": result["reason"],
        "visual_cues": result["visual_cues"],
        "prompt_version": result["prompt_version"],
        "usage_summary": result["usage_summary"],
        "staged_decision_path": repo_relative_path(decision_path, repo_root),
        "staged_request_path": repo_relative_path(request_path, repo_root),
        "staged_source_image_link": repo_relative_path(source_link_path, repo_root),
        "staged_validated_image_path": repo_relative_path(Path(str(result["validated_image_path"])), repo_root),
        "staged_llm_debug_dir": repo_relative_path(Path(str(result["debug_dir"])), repo_root),
    }


def run_orientation_task(
    task: dict[str, object],
    config: LLMImageOrientationStageConfig,
    run_dir: Path,
) -> dict[str, object]:
    """Run one staged LLM orientation task and write its staged artifacts."""
    image_path = Path(str(task["image_path"]))
    debug_dir = Path(str(task["debug_dir"]))
    validated_output_path = Path(str(task["validated_output_path"]))
    debug_dir.mkdir(parents=True, exist_ok=True)

    request = build_image_orientation_input(
        doc_id=str(task["doc_id"]),
        source_filename=str(task["source_filename"]),
        page_number=int(task["page_number"]),
        model=config.model,
        image_path=image_path,
        quality_flags=list(task.get("quality_flags") or []),
    )
    decision = run_image_orientation_decision(
        request,
        llm_config(config),
        debug_dump_dir=str(debug_dir),
    )
    usage_summary = usage_summary_from_debug_dir(
        debug_dir,
        max_tokens=llm_config(config).max_tokens,
    )

    rotation_degrees = int(decision.rotation_degrees)
    if rotation_degrees == 0:
        validated_image_path = image_path
    else:
        write_upright_image(image_path, validated_output_path, rotation_degrees)
        validated_image_path = validated_output_path

    result = {
        "manifest_path": str(task["manifest_path"]),
        "doc_id": decision.doc_id,
        "source_filename": decision.source_filename,
        "page_number": decision.page_number,
        "rotation_degrees": rotation_degrees,
        "is_already_upright": decision.is_already_upright,
        "needs_manual_review": decision.needs_manual_review,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "visual_cues": decision.visual_cues,
        "prompt_version": decision.prompt_version,
        "source_image_path": str(image_path),
        "validated_image_path": str(validated_image_path),
        "debug_dir": str(debug_dir),
        "usage_summary": usage_summary,
    }
    request_payload = request.model_dump(mode="json")
    request_payload["image_path"] = repo_relative_path(image_path, config.repo_root)
    return write_staged_page_outputs(
        repo_root=config.repo_root,
        run_dir=run_dir,
        result=result,
        request_payload=request_payload,
    )


def execute_llm_image_orientation_run(
    *,
    config: LLMImageOrientationStageConfig,
    doc_id: str | None = None,
    random_n: int | None = None,
    seed: int = 42,
    force: bool = False,
) -> tuple[dict[str, object], Path]:
    """Run a staged LLM image-orientation pass without mutating manifests."""
    selected = selected_manifest_paths(
        config,
        doc_id=doc_id,
        force=force,
    )
    run_id = run_timestamp()
    run_dir = run_output_dir(config.runs_dir, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    candidate_pages: list[tuple[Path, DocumentManifest, PageArtifact]] = []
    skipped_pages = 0
    for manifest_path in selected:
        manifest = load_manifest(manifest_path)
        for page in manifest.pages:
            if page_needs_orientation_validation(config.repo_root, page):
                if page_is_skippable_for_llm_orientation(config.repo_root, page):
                    skipped_pages += 1
                    continue
                candidate_pages.append((manifest_path, manifest, page))

    if random_n is not None:
        if random_n <= 0:
            raise ValueError("--random-n must be >= 1.")
        if random_n > len(candidate_pages):
            raise ValueError(f"--random-n={random_n} exceeds eligible pages={len(candidate_pages)}")
        rng = random.Random(seed)
        candidate_pages = rng.sample(candidate_pages, random_n)

    candidate_pages = sorted(
        candidate_pages,
        key=lambda item: (item[1].doc_id, item[2].page_number),
    )
    tasks = [
        build_orientation_task(
            repo_root=config.repo_root,
            run_dir=run_dir,
            manifest_path=manifest_path,
            manifest=manifest,
            page=page,
        )
        for manifest_path, manifest, page in candidate_pages
    ]

    successes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    cumulative_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }

    if config.workers <= 1:
        for index, task in enumerate(tasks, start=1):
            try:
                result = run_orientation_task(task, config, run_dir)
                successes.append(result)
                page_usage = usage_totals(result.get("usage_summary"))
                cumulative_usage = add_usage_totals(cumulative_usage, page_usage)
                LOGGER.info(
                    "LLM image orientation [%s/%s] %s page %s | rotation=%s | confidence=%.2f | manual_review=%s | usage(prompt=%s completion=%s reasoning=%s total=%s) | cumulative_total=%s",
                    index,
                    len(tasks),
                    result["doc_id"],
                    result["page_number"],
                    result["rotation_degrees"],
                    result["confidence"],
                    result["needs_manual_review"],
                    page_usage["prompt_tokens"],
                    page_usage["completion_tokens"],
                    page_usage["reasoning_tokens"],
                    page_usage["total_tokens"],
                    cumulative_usage["total_tokens"],
                )
            except Exception as error:  # noqa: BLE001
                failures.append(
                    {
                        "doc_id": task["doc_id"],
                        "page_number": task["page_number"],
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    }
                )
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.workers) as executor:
            futures = {
                executor.submit(run_orientation_task, task, config, run_dir): task
                for task in tasks
            }
            for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                task = futures[future]
                try:
                    result = future.result()
                    successes.append(result)
                    page_usage = usage_totals(result.get("usage_summary"))
                    cumulative_usage = add_usage_totals(cumulative_usage, page_usage)
                    LOGGER.info(
                        "LLM image orientation [%s/%s] %s page %s | rotation=%s | confidence=%.2f | manual_review=%s | usage(prompt=%s completion=%s reasoning=%s total=%s) | cumulative_total=%s",
                        index,
                        len(tasks),
                        result["doc_id"],
                        result["page_number"],
                        result["rotation_degrees"],
                        result["confidence"],
                        result["needs_manual_review"],
                        page_usage["prompt_tokens"],
                        page_usage["completion_tokens"],
                        page_usage["reasoning_tokens"],
                        page_usage["total_tokens"],
                        cumulative_usage["total_tokens"],
                    )
                except Exception as error:  # noqa: BLE001
                    failures.append(
                        {
                            "doc_id": task["doc_id"],
                            "page_number": task["page_number"],
                            "error": str(error),
                            "traceback": traceback.format_exc(),
                        }
                    )

    successes = sorted(successes, key=lambda item: (str(item["doc_id"]), int(item["page_number"])))
    failures = sorted(failures, key=lambda item: (str(item["doc_id"]), int(item["page_number"])))
    usage_summary = aggregate_usage_summaries(successes)
    selected_doc_ids = {str(task["doc_id"]) for task in tasks}
    report = {
        "mode": "dry_run",
        "run_id": run_id,
        "model": config.model,
        "prompt_version": llm_config(config).prompt_version,
        "reasoning_effort": config.reasoning_effort,
        "workers": config.workers,
        "random_n": random_n,
        "seed": seed if random_n is not None else None,
        "force": force,
        "documents_scanned": len(selected),
        "documents_selected": len(selected_doc_ids),
        "pages_selected": len(tasks),
        "candidate_pages": len(tasks),
        "skipped_pages": skipped_pages,
        "pages_succeeded": len(successes),
        "pages_failed": len(failures),
        "rotated_pages": sum(1 for item in successes if int(item["rotation_degrees"]) != 0),
        "manual_review_pages": sum(1 for item in successes if bool(item["needs_manual_review"])),
        "usage_summary": usage_summary,
        "results": successes,
        "failures": failures,
    }
    report_path = run_dir / "llm_image_orientation_run_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report, report_path


def apply_llm_image_orientation_run(
    *,
    config: LLMImageOrientationStageConfig,
    run_report_path: Path,
    force: bool = False,
) -> dict[str, object]:
    """Apply a staged LLM image-orientation run into canonical images and manifests."""
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    results = report.get("results", [])
    applied: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for item in results:
        doc_id = item["doc_id"]
        page_number = int(item["page_number"])
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        manifest = load_manifest(manifest_path)
        page = next((page for page in manifest.pages if page.page_number == page_number), None)
        if page is None:
            skipped.append({"doc_id": doc_id, "page_number": page_number, "reason": "page_not_found"})
            continue
        if page.validated_image_path and page.image_rotation_degrees is not None and not force:
            skipped.append({"doc_id": doc_id, "page_number": page_number, "reason": "already_validated"})
            continue

        staged_validated_image_path = config.repo_root / item["staged_validated_image_path"]
        canonical_output_path = orientation_output_path(manifest_path.parent / "pages", page_number)
        if int(item["rotation_degrees"]) == 0:
            validated_image_path = absolute_repo_path(config.repo_root, page.image_path or "")
        else:
            canonical_output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(staged_validated_image_path, canonical_output_path)
            validated_image_path = canonical_output_path

        clean_page = reset_page_orientation_fields(page)
        updated_page = merge_page_orientation_results(
            page=clean_page,
            repo_root=config.repo_root,
            validated_image_path=validated_image_path,
            rotate_clockwise_degrees=int(item["rotation_degrees"]),
            method="llm_image_orientation",
        )
        updated_pages: list[PageArtifact] = []
        for existing_page in manifest.pages:
            updated_pages.append(updated_page if existing_page.page_number == page_number else existing_page)
        manifest.pages = updated_pages
        manifest.quality_flags = roll_up_doc_orientation_flags(updated_pages, manifest.quality_flags)
        write_manifest(manifest_path, manifest)
        applied.append(
            {
                "doc_id": doc_id,
                "page_number": page_number,
                "validated_image_path": updated_page.validated_image_path,
                "rotation_degrees": item["rotation_degrees"],
            }
        )

    apply_report = {
        "mode": "apply",
        "source_run_report": repo_relative_path(run_report_path, config.repo_root),
        "pages_seen": len(results),
        "pages_applied": len(applied),
        "pages_skipped": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }
    output_path = config.indexes_dir / "llm_image_orientation_apply_report.json"
    output_path.write_text(json.dumps(apply_report, indent=2) + "\n", encoding="utf-8")
    return {"report": apply_report, "report_path": output_path}
