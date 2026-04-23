from __future__ import annotations

import json
import os
import random
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.normalize.analyze_quality import (
    build_quality_report,
    load_all_manifests,
)
from packages.pipeline.normalize.llm_selection import markdown_candidates, repair_candidates


def run_id() -> str:
    """Return a timestamped sampling run identifier."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def candidate_slug(candidate: dict[str, object]) -> str:
    """Build a stable slug for a candidate page."""
    return f"{candidate['doc_id']}__page_{int(candidate['page_number']):04d}"


def relative_symlink(link_path: Path, target_path: Path) -> None:
    """Create or replace a relative symlink."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    relative_target = Path(os.path.relpath(target_path, start=link_path.parent))
    link_path.symlink_to(relative_target)


def safe_relative_path(path: Path, root: Path) -> str:
    """Convert a path into a root-relative string for report serialization."""
    return str(path.relative_to(root))


def candidate_source_paths(repo_root: Path, candidate: dict[str, object]) -> dict[str, Path]:
    """Resolve source artifact paths for a candidate page."""
    doc_id = str(candidate["doc_id"])
    page_number = int(candidate["page_number"])
    doc_dir = repo_root / "data" / "processed" / "contracts" / doc_id
    page_stem = f"{page_number:04d}"

    return {
        "doc_dir": doc_dir,
        "manifest": doc_dir / "manifest.json",
        "text": doc_dir / "pages" / f"{page_stem}.txt",
        "ocr_text": doc_dir / "pages" / f"{page_stem}.ocr.txt",
        "image": doc_dir / "pages" / f"{page_stem}.png",
    }


def write_candidate_pack(
    repo_root: Path,
    base_dir: Path,
    candidate_type: str,
    candidate: dict[str, object],
) -> dict[str, object]:
    """Create a symlink-based review pack for a single candidate page."""
    pack_dir = base_dir / candidate_type / candidate_slug(candidate)
    pack_dir.mkdir(parents=True, exist_ok=True)

    source_paths = candidate_source_paths(repo_root, candidate)
    symlink_paths: dict[str, str] = {}

    for label, source_path in source_paths.items():
        if not source_path.exists():
            continue
        suffix = source_path.suffix or ".link"
        link_path = pack_dir / f"{label}{suffix}"
        relative_symlink(link_path, source_path)
        symlink_paths[label] = safe_relative_path(link_path, repo_root)

    metadata_path = pack_dir / "candidate.json"
    metadata = {
        "candidate_type": candidate_type,
        **candidate,
        "linked_artifacts": symlink_paths,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return {
        **candidate,
        "candidate_type": candidate_type,
        "pack_dir": safe_relative_path(pack_dir, repo_root),
        "candidate_json": safe_relative_path(metadata_path, repo_root),
        "linked_artifacts": symlink_paths,
    }


def sample_partition(items: list[dict[str, object]], size: int, seed: int) -> list[dict[str, object]]:
    """Return a deterministic random sample of items."""
    if len(items) <= size:
        return list(items)
    rng = random.Random(seed)
    return rng.sample(items, size)


def edge_case_candidates(
    markdown_candidates: list[dict[str, object]],
    repair_candidates: list[dict[str, object]],
    limit: int = 10,
) -> list[dict[str, object]]:
    """Return a small edge-case set spanning different difficult candidate types."""
    ranked = sorted(
        markdown_candidates + repair_candidates,
        key=lambda item: (
            item.get("ocr_confidence") is None,
            item.get("ocr_confidence") if item.get("ocr_confidence") is not None else -1,
            -len(item.get("quality_flags", [])),
        ),
    )
    seen: set[tuple[str, int, str]] = set()
    selected: list[dict[str, object]] = []
    for item in ranked:
        key = (str(item["doc_id"]), int(item["page_number"]), str(item["source_filename"]))
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def build_sampling_report(
    repo_root: Path,
    run_dir: Path,
    full_set_records: list[dict[str, object]],
    sample_groups: dict[str, list[dict[str, object]]],
    quality_report: dict[str, object],
) -> dict[str, object]:
    """Build the top-level sampling run report."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_dir": safe_relative_path(run_dir, repo_root),
        "quality_report_snapshot": {
            "markdown_page_count": quality_report["llm_candidates"]["markdown_page_count"],
            "repair_page_count": quality_report["llm_candidates"]["repair_page_count"],
            "manual_review_document_count": quality_report["manual_review"]["document_count"],
        },
        "full_set_count": len(full_set_records),
        "sample_group_counts": {name: len(records) for name, records in sample_groups.items()},
        "full_set": full_set_records,
        "samples": sample_groups,
    }


def write_sampling_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the sampling run report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def build_llm_sampling_run(repo_root: Path, seed: int = 42) -> tuple[Path, dict[str, object]]:
    """Create a timestamped LLM-candidate sampling run with symlink review packs."""
    manifests = load_all_manifests(repo_root / "data" / "processed" / "contracts")
    quality_report = build_quality_report(manifests)
    markdown_candidate_pages = markdown_candidates(manifests)
    repair_candidate_pages = repair_candidates(manifests)

    root = repo_root / "data" / "sampled" / "llm_candidates" / run_id()
    full_set_dir = root / "full_set"
    samples_dir = root / "samples"
    full_set_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)

    full_set_records: list[dict[str, object]] = []
    for candidate in markdown_candidate_pages:
        full_set_records.append(write_candidate_pack(repo_root, full_set_dir, "markdown", candidate))
    for candidate in repair_candidate_pages:
        full_set_records.append(write_candidate_pack(repo_root, full_set_dir, "repair", candidate))

    random_pool = markdown_candidate_pages + repair_candidate_pages
    sample_specs = {
        "random_25": sample_partition(random_pool, 25, seed),
        "markdown_10": sample_partition(markdown_candidate_pages, 10, seed + 1),
        "repair_10": sample_partition(repair_candidate_pages, 10, seed + 2),
        "edge_cases_10": edge_case_candidates(markdown_candidate_pages, repair_candidate_pages, 10),
    }

    sample_group_records: dict[str, list[dict[str, object]]] = {}
    for group_name, candidates in sample_specs.items():
        group_records: list[dict[str, object]] = []
        for candidate in candidates:
            candidate_type = "markdown" if candidate in markdown_candidate_pages else "repair"
            group_records.append(write_candidate_pack(repo_root, samples_dir / group_name, candidate_type, candidate))
        sample_group_records[group_name] = group_records

    report = build_sampling_report(
        repo_root=repo_root,
        run_dir=root,
        full_set_records=full_set_records,
        sample_groups=sample_group_records,
        quality_report=quality_report,
    )
    write_sampling_report(root / "report.json", report)
    return root, report
