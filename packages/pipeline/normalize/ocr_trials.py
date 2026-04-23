from __future__ import annotations

import json
import logging
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.normalize.ocr_pages import ensure_tesseract_available, process_page_ocr_trial
from packages.pipeline.normalize.ocr_selection import target_page_numbers
from packages.pipeline.normalize.pdf_pages import absolute_repo_path, iter_manifest_paths, load_manifest, repo_relative_path


LOGGER = logging.getLogger(__name__)


def trial_run_id() -> str:
    """Return a timestamped OCR trial run identifier."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def default_worker_count() -> int:
    """Return a conservative default worker count for parallel OCR."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1, 4))


def build_trial_doc_dir(run_dir: Path, doc_id: str) -> Path:
    """Return the output folder for one document inside an OCR trial run."""
    return run_dir / doc_id


def write_trial_report(report_path: Path, report: dict[str, object]) -> None:
    """Write an OCR trial report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def serialize_target(repo_root: Path, manifest_path: Path, page_number: int) -> dict[str, object]:
    """Serialize one OCR target for durable storage in a trial report."""
    return {
        "manifest_path": repo_relative_path(manifest_path, repo_root),
        "page_number": page_number,
    }


def deserialize_target(repo_root: Path, target: dict[str, object]) -> tuple[Path, int]:
    """Deserialize one OCR target from a trial report."""
    return repo_root / str(target["manifest_path"]), int(target["page_number"])


def load_trial_report(repo_root: Path, report_ref: str) -> tuple[Path, dict[str, object]]:
    """Load a trial report from either a run id or a direct report path."""
    candidate_path = Path(report_ref)
    if candidate_path.exists():
        report_path = candidate_path
        run_dir = report_path.parent
    else:
        run_dir = repo_root / "data" / "sampled" / "ocr_trials" / report_ref
        report_path = run_dir / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return run_dir, report


def select_trial_targets(
    targets: list[tuple[Path, int]],
    *,
    limit: int | None,
    seed: int,
) -> list[tuple[Path, int]]:
    """Select a deterministic subset of OCR targets for an experimental trial run."""
    if limit is None or limit >= len(targets):
        return list(targets)
    rng = random.Random(seed)
    return rng.sample(targets, limit)


def process_trial_target(
    *,
    repo_root: Path,
    manifest_path: Path,
    page_number: int,
    run_dir: Path,
) -> dict[str, object]:
    """Run OCR for one manifest page into the trial directory."""
    started_at = time.perf_counter()
    manifest = load_manifest(manifest_path)
    source_pdf_path = absolute_repo_path(repo_root, manifest.source_pdf)
    page = next(page for page in manifest.pages if page.page_number == page_number)
    output_doc_dir = build_trial_doc_dir(run_dir, manifest.doc_id)
    result = process_page_ocr_trial(
        repo_root=repo_root,
        source_pdf_path=source_pdf_path,
        source_filename=manifest.source_filename,
        page=page,
        output_doc_dir=output_doc_dir,
    )
    result["doc_id"] = manifest.doc_id
    result["elapsed_seconds"] = round(time.perf_counter() - started_at, 4)
    return result


def collect_ocr_targets(processed_contracts_dir: Path) -> list[tuple[Path, int]]:
    """Collect all manifest/page pairs currently selected for OCR."""
    targets: list[tuple[Path, int]] = []
    for manifest_path in iter_manifest_paths(processed_contracts_dir):
        manifest = load_manifest(manifest_path)
        for page_number in target_page_numbers(manifest):
            targets.append((manifest_path, page_number))
    return targets


def targets_from_report(repo_root: Path, report_ref: str) -> tuple[list[tuple[Path, int]], dict[str, object]]:
    """Load a previously selected OCR target set from a prior trial report."""
    _, report = load_trial_report(repo_root, report_ref)
    targets = [deserialize_target(repo_root, target) for target in report.get("targets", [])]
    return targets, report


def run_ocr_trial(
    *,
    repo_root: Path,
    processed_contracts_dir: Path,
    mode: str,
    workers: int | None = None,
    limit: int | None = None,
    seed: int = 42,
    from_report: str | None = None,
) -> tuple[Path, dict[str, object]]:
    """Run experimental OCR into trial space without mutating canonical artifacts."""
    ensure_tesseract_available()
    started_at = time.perf_counter()
    run_dir = repo_root / "data" / "sampled" / "ocr_trials" / trial_run_id()
    run_dir.mkdir(parents=True, exist_ok=True)

    if from_report:
        targets, source_report = targets_from_report(repo_root, from_report)
        all_targets = list(targets)
        target_source = {
            "kind": "report_reuse",
            "report_ref": from_report,
            "report_run_dir": source_report.get("run_dir"),
        }
    else:
        all_targets = collect_ocr_targets(processed_contracts_dir)
        targets = select_trial_targets(all_targets, limit=limit, seed=seed)
        target_source = {
            "kind": "selector_sampling",
            "report_ref": None,
        }

    worker_count = workers or default_worker_count()
    LOGGER.info(
        "Starting OCR trial | mode=%s | available_targets=%s | selected_targets=%s | workers=%s | seed=%s | from_report=%s",
        mode,
        len(all_targets),
        len(targets),
        worker_count,
        seed,
        from_report or "-",
    )

    successes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    if mode == "parallel":
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    process_trial_target,
                    repo_root=repo_root,
                    manifest_path=manifest_path,
                    page_number=page_number,
                    run_dir=run_dir,
                ): (manifest_path, page_number)
                for manifest_path, page_number in targets
            }
            completed = 0
            for future in as_completed(futures):
                manifest_path, page_number = futures[future]
                completed += 1
                try:
                    successes.append(future.result())
                    LOGGER.info(
                        "OCR trial progress [%s/%s] %s page %s | status=ok",
                        completed,
                        len(targets),
                        manifest_path.parent.name,
                        page_number,
                    )
                except Exception as error:
                    failures.append(
                        {
                            "manifest_path": repo_relative_path(manifest_path, repo_root),
                            "page_number": page_number,
                            "error": str(error),
                        }
                    )
                    LOGGER.error(
                        "OCR trial progress [%s/%s] %s page %s | status=failed | error=%s",
                        completed,
                        len(targets),
                        manifest_path.parent.name,
                        page_number,
                        error,
                    )
    else:
        for index, (manifest_path, page_number) in enumerate(targets, start=1):
            try:
                successes.append(
                    process_trial_target(
                        repo_root=repo_root,
                        manifest_path=manifest_path,
                        page_number=page_number,
                        run_dir=run_dir,
                    )
                )
                LOGGER.info(
                    "OCR trial progress [%s/%s] %s page %s | status=ok",
                    index,
                    len(targets),
                    manifest_path.parent.name,
                    page_number,
                )
            except Exception as error:
                failures.append(
                    {
                        "manifest_path": repo_relative_path(manifest_path, repo_root),
                        "page_number": page_number,
                        "error": str(error),
                    }
                )
                LOGGER.error(
                    "OCR trial progress [%s/%s] %s page %s | status=failed | error=%s",
                    index,
                    len(targets),
                    manifest_path.parent.name,
                    page_number,
                    error,
                )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_dir": repo_relative_path(run_dir, repo_root),
        "mode": f"{mode}_trial",
        "workers": worker_count,
        "seed": seed,
        "limit": limit,
        "target_source": target_source,
        "total_available_target_pages": len(all_targets),
        "target_page_count": len(targets),
        "success_count": len(successes),
        "failure_count": len(failures),
        "elapsed_seconds": round(time.perf_counter() - started_at, 4),
        "targets": [
            serialize_target(repo_root, manifest_path, page_number)
            for manifest_path, page_number in targets
        ],
        "results": sorted(successes, key=lambda item: (str(item["doc_id"]), int(item["page_number"]))),
        "failures": failures,
    }
    write_trial_report(run_dir / "report.json", report)
    LOGGER.info(
        "OCR trial complete | mode=%s | selected_targets=%s | successes=%s | failures=%s | elapsed=%.4fs",
        mode,
        len(targets),
        len(successes),
        len(failures),
        report["elapsed_seconds"],
    )
    return run_dir, report


def run_single_page_ocr_trial(
    *,
    repo_root: Path,
    manifest_path: Path,
    page_number: int,
) -> tuple[Path, dict[str, object]]:
    """Run OCR for one page into a single-page trial area under data/sampled/ocr_trials/."""
    ensure_tesseract_available()
    run_dir = repo_root / "data" / "sampled" / "ocr_trials" / trial_run_id()
    run_dir.mkdir(parents=True, exist_ok=True)
    result = process_trial_target(
        repo_root=repo_root,
        manifest_path=manifest_path,
        page_number=page_number,
        run_dir=run_dir,
    )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_dir": repo_relative_path(run_dir, repo_root),
        "mode": "single_page_trial",
        "target_page_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "results": [result],
        "failures": [],
    }
    write_trial_report(run_dir / "report.json", report)
    return run_dir, report
