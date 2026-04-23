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

from packages.llm.shared.task_runtime import usage_summary_from_debug_dir
from packages.llm.transforms.vision_markdown_normalization.config import VisionMarkdownNormalizationConfig
from packages.llm.transforms.vision_markdown_normalization.task import (
    build_vision_markdown_input,
    run_vision_markdown_normalization,
)
from packages.pipeline.normalize.llm_selection import is_vision_markdown_candidate
from packages.pipeline.normalize.pdf_pages import (
    iter_manifest_paths,
    load_manifest,
    preferred_page_image_path,
    repo_relative_path,
    write_manifest,
)
from packages.schemas import DocumentManifest, PageArtifact


LOGGER = logging.getLogger(__name__)

PAGE_LLM_FLAGS = {
    "llm_vision_markdown_generated",
}

DOC_LLM_FLAGS = {
    "has_llm_vision_markdown_pages",
}


@dataclass(frozen=True)
class VisionMarkdownStageConfig:
    """Static configuration for staged vision-markdown execution."""

    repo_root: Path
    processed_contracts_dir: Path
    runs_dir: Path
    indexes_dir: Path
    model: str = "openai/gpt-5.4-nano"
    workers: int = 1


def run_timestamp() -> str:
    """Return a stable UTC timestamp for one staged vision-markdown run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def default_vision_markdown_worker_count() -> int:
    """Return a conservative default worker count for vision-markdown runs."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1, 8))


def llm_config(config: VisionMarkdownStageConfig) -> VisionMarkdownNormalizationConfig:
    """Return the LLM config used for one staged run."""
    return VisionMarkdownNormalizationConfig(model=config.model)


def vision_markdown_output_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical vision-markdown output path for one page."""
    return doc_dir / "pages" / f"{page_number:04d}.vision.md"


def staged_output_path(base_dir: Path, page_number: int) -> Path:
    """Return the staged markdown output path for one page."""
    return base_dir / f"{page_number:04d}.vision.md"


def run_output_dir(runs_dir: Path, run_id: str) -> Path:
    """Return the output directory for one staged run."""
    return runs_dir / run_id


def doc_run_dir(run_dir: Path, doc_id: str) -> Path:
    """Return the staged subdirectory for one document within a run."""
    return run_dir / doc_id


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


def reset_page_llm_fields(page: PageArtifact) -> PageArtifact:
    """Return a page artifact with vision-markdown-only fields cleared for reruns."""
    base_flags = [flag for flag in page.quality_flags if flag not in PAGE_LLM_FLAGS]
    base_warnings = [warning for warning in page.warnings if not warning.startswith("LLM vision markdown: ")]
    return page.model_copy(update={"quality_flags": base_flags, "warnings": base_warnings})


def roll_up_doc_llm_flags(pages: list[PageArtifact], base_flags: list[str]) -> list[str]:
    """Recompute document-level vision-markdown flags after generation."""
    flags = [flag for flag in base_flags if flag not in DOC_LLM_FLAGS]
    if any("llm_vision_markdown_generated" in page.quality_flags for page in pages):
        flags.append("has_llm_vision_markdown_pages")
    return list(dict.fromkeys(flags))


def iter_candidate_manifest_paths(
    processed_contracts_dir: Path,
    *,
    include_already_processed: bool,
) -> list[Path]:
    """Return manifest paths that contain at least one candidate page."""
    manifest_paths: list[Path] = []
    for manifest_path in iter_manifest_paths(processed_contracts_dir):
        manifest = load_manifest(manifest_path)
        if include_already_processed:
            has_image_page = any(page.image_path for page in manifest.pages)
            if has_image_page:
                manifest_paths.append(manifest_path)
            continue
        if any(is_vision_markdown_candidate(page) for page in manifest.pages):
            manifest_paths.append(manifest_path)
    return manifest_paths


def selected_manifest_paths(
    config: VisionMarkdownStageConfig,
    *,
    doc_id: str | None,
    force: bool,
) -> list[Path]:
    """Resolve target manifest paths from selection options."""
    eligible = iter_candidate_manifest_paths(
        config.processed_contracts_dir,
        include_already_processed=force,
    )
    if doc_id is not None:
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        if manifest_path not in eligible and not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found for doc_id={doc_id}")
        return [manifest_path]
    return eligible


def build_task(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest_path: Path,
    manifest: DocumentManifest,
    page: PageArtifact,
) -> dict[str, object]:
    """Build a serializable staged vision-markdown task for one page."""
    output_dir = doc_run_dir(run_dir, manifest.doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_page = reset_page_llm_fields(page)
    image_path = preferred_page_image_path(repo_root, clean_page)
    if image_path is None:
        raise FileNotFoundError(f"No image path available for doc={manifest.doc_id} page={page.page_number}")
    page_stem = f"{page.page_number:04d}"
    doc_dir = manifest_path.parent
    return {
        "manifest_path": str(manifest_path),
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "page_number": page.page_number,
        "quality_flags": list(clean_page.quality_flags),
        "image_path": str(image_path),
        "pdf_text_path": str(doc_dir / "pages" / f"{page_stem}.txt"),
        "ocr_text_path": str(doc_dir / "pages" / f"{page_stem}.ocr.txt"),
        "output_path": str(staged_output_path(output_dir, page.page_number)),
        "debug_dir": str(output_dir / f"{page.page_number:04d}.llm_debug"),
    }


def write_staged_outputs(
    *,
    repo_root: Path,
    run_dir: Path,
    result: dict[str, object],
    request_payload: dict[str, object],
) -> dict[str, object]:
    """Write staged request/decision outputs for one page."""
    output_dir = doc_run_dir(run_dir, str(result["doc_id"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    page_number = int(result["page_number"])
    request_path = output_dir / f"{page_number:04d}.vision_request.json"
    result_path = output_dir / f"{page_number:04d}.vision_result.json"
    request_path.write_text(json.dumps(request_payload, indent=2) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {
        "doc_id": result["doc_id"],
        "source_filename": result["source_filename"],
        "page_number": page_number,
        "prompt_version": result["prompt_version"],
        "usage_summary": result["usage_summary"],
        "staged_markdown_path": repo_relative_path(Path(str(result["staged_markdown_path"])), repo_root),
        "staged_request_path": repo_relative_path(request_path, repo_root),
        "staged_result_path": repo_relative_path(result_path, repo_root),
        "staged_llm_debug_dir": repo_relative_path(Path(str(result["debug_dir"])), repo_root),
    }


def run_task(
    task: dict[str, object],
    config: VisionMarkdownStageConfig,
    run_dir: Path,
) -> dict[str, object]:
    """Run one staged vision-markdown task and write staged artifacts."""
    debug_dir = Path(str(task["debug_dir"]))
    debug_dir.mkdir(parents=True, exist_ok=True)
    request = build_vision_markdown_input(
        doc_id=str(task["doc_id"]),
        source_filename=str(task["source_filename"]),
        page_number=int(task["page_number"]),
        model=config.model,
        quality_flags=list(task.get("quality_flags") or []),
        image_path=Path(str(task["image_path"])),
        pdf_text_path=Path(str(task["pdf_text_path"])),
        ocr_text_path=Path(str(task["ocr_text_path"])),
    )
    result = run_vision_markdown_normalization(
        request,
        llm_config(config),
        debug_dump_dir=str(debug_dir),
    )
    output_path = Path(str(task["output_path"]))
    output_path.write_text((result.output_markdown or "") + ("\n" if result.output_markdown else ""), encoding="utf-8")
    usage_summary = usage_summary_from_debug_dir(debug_dir, max_tokens=llm_config(config).max_tokens)
    request_payload = request.model_dump(mode="json")
    request_payload["image_path"] = repo_relative_path(Path(str(task["image_path"])), config.repo_root)
    if request.pdf_text_path:
        request_payload["pdf_text_path"] = repo_relative_path(Path(str(task["pdf_text_path"])), config.repo_root)
    if request.ocr_text_path:
        request_payload["ocr_text_path"] = repo_relative_path(Path(str(task["ocr_text_path"])), config.repo_root)
    result_payload = {
        "doc_id": result.doc_id,
        "source_filename": result.source_filename,
        "page_number": result.page_number,
        "prompt_version": result.prompt_version,
        "usage_summary": usage_summary,
        "staged_markdown_path": str(output_path),
        "debug_dir": str(debug_dir),
    }
    return write_staged_outputs(
        repo_root=config.repo_root,
        run_dir=run_dir,
        result=result_payload,
        request_payload=request_payload,
    )


def execute_vision_markdown_run(
    *,
    config: VisionMarkdownStageConfig,
    doc_id: str | None = None,
    random_n: int | None = None,
    seed: int = 42,
    force: bool = False,
) -> tuple[dict[str, object], Path]:
    """Run a staged vision-markdown pass without mutating manifests."""
    selected = selected_manifest_paths(config, doc_id=doc_id, force=force)
    run_id = run_timestamp()
    run_dir = run_output_dir(config.runs_dir, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    candidate_pages: list[tuple[Path, DocumentManifest, PageArtifact]] = []
    for manifest_path in selected:
        manifest = load_manifest(manifest_path)
        for page in manifest.pages:
            if force:
                if page.image_path:
                    candidate_pages.append((manifest_path, manifest, page))
            elif is_vision_markdown_candidate(page):
                candidate_pages.append((manifest_path, manifest, page))

    if random_n is not None:
        if random_n <= 0:
            raise ValueError("--random-n must be >= 1.")
        if random_n > len(candidate_pages):
            raise ValueError(f"--random-n={random_n} exceeds eligible pages={len(candidate_pages)}")
        rng = random.Random(seed)
        candidate_pages = rng.sample(candidate_pages, random_n)

    candidate_pages = sorted(candidate_pages, key=lambda item: (item[1].doc_id, item[2].page_number))
    tasks = [
        build_task(
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
                result = run_task(task, config, run_dir)
                successes.append(result)
                page_usage = usage_totals(result.get("usage_summary"))
                cumulative_usage = add_usage_totals(cumulative_usage, page_usage)
                LOGGER.info(
                    "Vision markdown [%s/%s] %s page %s | usage(prompt=%s completion=%s reasoning=%s total=%s) | cumulative_total=%s",
                    index,
                    len(tasks),
                    result["doc_id"],
                    result["page_number"],
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
            futures = {executor.submit(run_task, task, config, run_dir): task for task in tasks}
            for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                task = futures[future]
                try:
                    result = future.result()
                    successes.append(result)
                    page_usage = usage_totals(result.get("usage_summary"))
                    cumulative_usage = add_usage_totals(cumulative_usage, page_usage)
                    LOGGER.info(
                        "Vision markdown [%s/%s] %s page %s | usage(prompt=%s completion=%s reasoning=%s total=%s) | cumulative_total=%s",
                        index,
                        len(tasks),
                        result["doc_id"],
                        result["page_number"],
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
    selected_doc_ids = {str(task["doc_id"]) for task in tasks}
    report = {
        "mode": "dry_run",
        "run_id": run_id,
        "model": config.model,
        "prompt_version": llm_config(config).prompt_version,
        "workers": config.workers,
        "random_n": random_n,
        "seed": seed if random_n is not None else None,
        "force": force,
        "documents_scanned": len(selected),
        "documents_selected": len(selected_doc_ids),
        "pages_selected": len(tasks),
        "candidate_pages": len(tasks),
        "pages_succeeded": len(successes),
        "pages_failed": len(failures),
        "usage_summary": aggregate_usage_summaries(successes),
        "results": successes,
        "failures": failures,
    }
    report_path = run_dir / "vision_markdown_run_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report, report_path


def apply_vision_markdown_run(
    *,
    config: VisionMarkdownStageConfig,
    run_report_path: Path,
    force: bool = False,
) -> dict[str, object]:
    """Apply a staged vision-markdown run into canonical markdown artifacts and manifests."""
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    results = report.get("results", [])
    applied: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for item in results:
        doc_id = str(item["doc_id"])
        page_number = int(item["page_number"])
        manifest_path = config.processed_contracts_dir / doc_id / "manifest.json"
        manifest = load_manifest(manifest_path)
        page = next((page for page in manifest.pages if page.page_number == page_number), None)
        if page is None:
            skipped.append({"doc_id": doc_id, "page_number": page_number, "reason": "page_not_found"})
            continue
        if page.vision_markdown_path and not force:
            skipped.append({"doc_id": doc_id, "page_number": page_number, "reason": "already_generated"})
            continue

        staged_markdown_path = config.repo_root / str(item["staged_markdown_path"])
        canonical_output_path = vision_markdown_output_path(manifest_path.parent, page_number)
        canonical_output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_markdown_path, canonical_output_path)

        clean_page = reset_page_llm_fields(page)
        merged_flags = list(dict.fromkeys(clean_page.quality_flags + ["llm_vision_markdown_generated"]))
        merged_warnings = list(
            dict.fromkeys(clean_page.warnings + [f"LLM vision markdown: {config.model} | {report['prompt_version']}"])
        )
        updated_page = clean_page.model_copy(
            update={
                "vision_markdown_path": repo_relative_path(canonical_output_path, config.repo_root),
                "quality_flags": merged_flags,
                "warnings": merged_warnings,
            }
        )

        updated_pages = [
            updated_page if existing_page.page_number == page_number else existing_page
            for existing_page in manifest.pages
        ]
        manifest.pages = updated_pages
        manifest.quality_flags = roll_up_doc_llm_flags(updated_pages, manifest.quality_flags)
        write_manifest(manifest_path, manifest)
        applied.append(
            {
                "doc_id": doc_id,
                "page_number": page_number,
                "vision_markdown_path": updated_page.vision_markdown_path,
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
    output_path = config.indexes_dir / "vision_markdown_apply_report.json"
    output_path.write_text(json.dumps(apply_report, indent=2) + "\n", encoding="utf-8")
    return {"report": apply_report, "report_path": output_path}
