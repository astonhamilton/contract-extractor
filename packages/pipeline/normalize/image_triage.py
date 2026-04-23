from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path

from packages.pipeline.normalize.ocr_pages import (
    image_information_profile,
    is_likely_blank_image,
    is_likely_low_information_image,
)


LOGGER = logging.getLogger(__name__)


def relative_symlink(link_path: Path, target_path: Path) -> None:
    """Create or replace a relative symlink."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    relative_target = Path(os.path.relpath(target_path, start=link_path.parent))
    link_path.symlink_to(relative_target)


def sample_paths(paths: list[Path], *, limit: int | None, seed: int) -> list[Path]:
    """Optionally take a deterministic sample of image paths."""
    if limit is None or limit >= len(paths):
        return list(paths)
    rng = random.Random(seed)
    return rng.sample(paths, limit)


def triage_image(path: Path) -> dict[str, object]:
    """Classify one image as kept vs filtered using low-information heuristics."""
    profile = image_information_profile(path)
    likely_blank = is_likely_blank_image(path)
    likely_low_information = is_likely_low_information_image(path)
    keep = not likely_low_information

    return {
        "path": str(path),
        "filename": path.name,
        "keep": keep,
        "likely_blank_image": likely_blank,
        "likely_low_information_image": likely_low_information,
        "profile": profile,
    }


def write_triage_outputs(
    *,
    repo_root: Path,
    output_dir: Path,
    image_results: list[dict[str, object]],
) -> dict[str, object]:
    """Write kept/filtered symlink buckets plus a triage report."""
    kept_dir = output_dir / "kept"
    filtered_dir = output_dir / "filtered"
    output_dir.mkdir(parents=True, exist_ok=True)

    kept_count = 0
    filtered_count = 0
    serialized_items: list[dict[str, object]] = []

    for result in image_results:
        source_path = Path(str(result["path"]))
        bucket_dir = kept_dir if bool(result["keep"]) else filtered_dir
        link_path = bucket_dir / source_path.name
        relative_symlink(link_path, source_path)

        serialized_items.append(
            {
                **result,
                "path": str(source_path.relative_to(repo_root)) if source_path.is_relative_to(repo_root) else str(source_path),
                "link_path": str(link_path.relative_to(repo_root)) if link_path.is_relative_to(repo_root) else str(link_path),
            }
        )
        if result["keep"]:
            kept_count += 1
        else:
            filtered_count += 1

    report = {
        "output_dir": str(output_dir.relative_to(repo_root)) if output_dir.is_relative_to(repo_root) else str(output_dir),
        "kept_count": kept_count,
        "filtered_count": filtered_count,
        "items": serialized_items,
    }
    report_path = output_dir / "triage_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def run_image_folder_triage(
    *,
    repo_root: Path,
    input_dir: Path,
    output_dir: Path,
    limit: int | None = None,
    seed: int = 42,
) -> dict[str, object]:
    """Triage PNGs from a folder into kept vs filtered buckets."""
    image_paths = sorted(input_dir.glob("*.png"))
    selected = sample_paths(image_paths, limit=limit, seed=seed)
    LOGGER.info(
        "Starting image triage | input=%s | selected=%s | limit=%s | seed=%s",
        input_dir,
        len(selected),
        limit if limit is not None else "all",
        seed,
    )

    results: list[dict[str, object]] = []
    for index, path in enumerate(selected, start=1):
        result = triage_image(path)
        results.append(result)
        LOGGER.info(
            "Image triage [%s/%s] %s | keep=%s | blank=%s | low_information=%s",
            index,
            len(selected),
            path.name,
            result["keep"],
            result["likely_blank_image"],
            result["likely_low_information_image"],
        )

    report = write_triage_outputs(
        repo_root=repo_root,
        output_dir=output_dir,
        image_results=results,
    )
    report["input_dir"] = str(input_dir.relative_to(repo_root)) if input_dir.is_relative_to(repo_root) else str(input_dir)
    report["selected_count"] = len(selected)
    report["seed"] = seed
    report["limit"] = limit
    report_path = output_dir / "triage_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    LOGGER.info(
        "Image triage complete | selected=%s | kept=%s | filtered=%s",
        report["selected_count"],
        report["kept_count"],
        report["filtered_count"],
    )
    return report
