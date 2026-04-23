from __future__ import annotations

import statistics
from pathlib import Path

from packages.pipeline.normalize.normalized_document_pages import parse_normalized_document_pages
from packages.schemas import ArtifactKind, DocumentManifest


TOKEN_CHARS_PER_TOKEN = 4.0
PAGE_NOTES_TOTAL_TOKEN_THRESHOLD = 40_000
PAGE_NOTES_SPREAD_TOKEN_THRESHOLD = 25_000
PAGE_NOTES_PAGE_COUNT_THRESHOLD = 25
PAGE_NOTES_TOP_FIVE_SHARE_THRESHOLD = 0.45
PAGE_NOTES_DENSE_PAGE_THRESHOLD = 400
PAGE_NOTES_DENSE_PAGE_COUNT_THRESHOLD = 15
TOP_PAGE_DEFAULT_LIMIT = 10


def _absolute_repo_path(repo_root: Path, repo_relative_path: str) -> Path:
    """Resolve a repo-relative path string into an absolute path."""
    return repo_root / repo_relative_path


def _iter_manifest_paths(processed_contracts_dir: Path) -> list[Path]:
    """List manifest paths for processed documents."""
    manifest_paths: list[Path] = []
    for doc_dir in sorted(processed_contracts_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        manifest_path = doc_dir / "manifest.json"
        if manifest_path.exists():
            manifest_paths.append(manifest_path)
    return manifest_paths


def _load_manifest(manifest_path: Path) -> DocumentManifest:
    """Load one manifest from disk without importing heavier normalize modules."""
    return DocumentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def _read_text_if_exists(path: Path | None) -> str | None:
    """Read text if the path exists and contains non-empty content."""
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def estimate_tokens_from_text(text: str) -> int:
    """Estimate tokens from text length using a simple chars-per-token heuristic."""
    if not text:
        return 0
    return max(1, -(-len(text) // int(TOKEN_CHARS_PER_TOKEN)))


def _normalized_document_path(repo_root: Path, manifest: DocumentManifest) -> Path | None:
    """Return canonical normalized document XML path when present."""
    for artifact in manifest.derived_artifacts:
        if artifact.kind != ArtifactKind.XML:
            continue
        if artifact.path.endswith("/derived/normalized_document.xml") or artifact.path.endswith(
            "derived/normalized_document.xml"
        ):
            return _absolute_repo_path(repo_root, artifact.path)
    return None


def _page_artifact_texts(repo_root: Path, page) -> dict[str, str]:
    """Load available normalized text forms for one page."""
    artifacts: dict[str, str] = {}
    candidates = {
        "text": page.text_path,
        "ocr_text": page.ocr_text_path,
        "markdown": page.markdown_path,
        "vision_markdown": page.vision_markdown_path,
        "repair_markdown": page.repair_markdown_path,
    }
    for artifact_type, raw_path in candidates.items():
        if not raw_path:
            continue
        text = _read_text_if_exists(_absolute_repo_path(repo_root, raw_path))
        if text:
            artifacts[artifact_type] = text
    return artifacts


def _safe_int(value: object, default: int = 0) -> int:
    """Convert a value to int when possible."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalized_document_page_records(normalized_xml_path: Path) -> list[dict[str, object]]:
    """Parse page records from canonical normalized document XML."""
    page_records: list[dict[str, object]] = []
    for page in parse_normalized_document_pages(normalized_xml_path):
        page_number = _safe_int(page.get("page_number"))
        representation = str(page.get("representation") or "missing")
        source_path = page.get("source_path")
        quality_flags = list(page.get("quality_flags") or [])
        content = str(page.get("content") or "")
        page_records.append(
            {
                "page_number": page_number,
                "representation": representation,
                "source_path": source_path,
                "quality_flags": quality_flags,
                "char_count": len(content),
                "estimated_tokens": estimate_tokens_from_text(content),
            }
        )
    return page_records


def _fallback_page_records(repo_root: Path, manifest: DocumentManifest) -> list[dict[str, object]]:
    """Build page records directly from page artifacts when canonical XML is unavailable."""
    page_records: list[dict[str, object]] = []
    for page in manifest.pages:
        artifact_text_map = _page_artifact_texts(repo_root, page)
        best_representation = None
        best_text = ""
        for representation in ("repair_markdown", "markdown", "vision_markdown", "ocr_text", "text"):
            if representation in artifact_text_map:
                best_representation = representation
                best_text = artifact_text_map[representation]
                break
        page_records.append(
            {
                "page_number": page.page_number,
                "representation": best_representation or "missing",
                "source_path": None,
                "quality_flags": list(page.quality_flags),
                "char_count": len(best_text),
                "estimated_tokens": estimate_tokens_from_text(best_text),
            }
        )
    return page_records


def page_token_profile(repo_root: Path, manifest: DocumentManifest) -> dict[str, object]:
    """Build a page-level token profile for one document."""
    canonical_path = _normalized_document_path(repo_root, manifest)
    if canonical_path and canonical_path.exists():
        page_records = _normalized_document_page_records(canonical_path)
        page_source = "normalized_document_xml"
    else:
        page_records = _fallback_page_records(repo_root, manifest)
        page_source = "page_artifacts"

    token_values = [int(record["estimated_tokens"]) for record in page_records]
    total_tokens = sum(token_values)
    top_five_tokens = sum(sorted(token_values, reverse=True)[:5])
    dense_page_count = sum(1 for value in token_values if value >= PAGE_NOTES_DENSE_PAGE_THRESHOLD)

    summary = {
        "page_count": len(page_records),
        "total_chars": sum(int(record["char_count"]) for record in page_records),
        "total_tokens": total_tokens,
        "avg_chars_per_page": round(sum(int(record["char_count"]) for record in page_records) / len(page_records), 2)
        if page_records
        else 0.0,
        "avg_tokens_per_page": round(total_tokens / len(page_records), 2) if page_records else 0.0,
        "median_tokens_per_page": statistics.median(token_values) if token_values else 0,
        "max_page_chars": max((int(record["char_count"]) for record in page_records), default=0),
        "max_page_tokens": max(token_values) if token_values else 0,
        "min_page_tokens": min(token_values) if token_values else 0,
        "top_five_pages_token_share": round(top_five_tokens / total_tokens, 4) if total_tokens else 0.0,
        "dense_pages_over_400_tokens": dense_page_count,
    }

    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "normalized_document_path": str(canonical_path) if canonical_path else None,
        "page_source": page_source,
        "summary": summary,
        "pages": sorted(page_records, key=lambda record: int(record["page_number"])),
    }


def top_pages_by_tokens(profile: dict[str, object], *, limit: int = TOP_PAGE_DEFAULT_LIMIT) -> list[dict[str, object]]:
    """Return the top token-heavy pages for one page token profile."""
    pages = list(profile.get("pages", []))
    ranked = sorted(
        pages,
        key=lambda page: (-int(page.get("estimated_tokens", 0)), int(page.get("page_number", 0))),
    )
    return ranked[:limit]


def page_notes_recommendation(profile: dict[str, object]) -> dict[str, object]:
    """Recommend whether a page-notes layer is worth adding for a document."""
    summary = dict(profile.get("summary", {}))
    total_tokens = _safe_int(summary.get("total_tokens"))
    page_count = _safe_int(summary.get("page_count"))
    top_five_share = float(summary.get("top_five_pages_token_share", 0.0) or 0.0)
    dense_page_count = _safe_int(summary.get("dense_pages_over_400_tokens"))

    reasons: list[str] = []
    recommended = False

    if total_tokens >= PAGE_NOTES_TOTAL_TOKEN_THRESHOLD:
        recommended = True
        reasons.append(f"total token load is very large ({total_tokens:,})")
    if (
        total_tokens >= PAGE_NOTES_SPREAD_TOKEN_THRESHOLD
        and page_count >= PAGE_NOTES_PAGE_COUNT_THRESHOLD
        and top_five_share <= PAGE_NOTES_TOP_FIVE_SHARE_THRESHOLD
    ):
        recommended = True
        reasons.append("token load is spread across many pages, not concentrated in only a few")
    if total_tokens >= PAGE_NOTES_SPREAD_TOKEN_THRESHOLD and dense_page_count >= PAGE_NOTES_DENSE_PAGE_COUNT_THRESHOLD:
        recommended = True
        reasons.append(f"many pages are individually dense ({dense_page_count} pages over 400 tokens)")

    if recommended:
        verdict = "recommended"
        reason = "; ".join(reasons)
    elif total_tokens <= 12_000:
        verdict = "not_needed"
        reason = f"document is small enough to pass directly ({total_tokens:,} estimated tokens)"
    else:
        verdict = "borderline"
        reason = "document is moderately large, but current token spread does not clearly justify page notes yet"

    return {
        "page_notes_recommended": recommended,
        "verdict": verdict,
        "reason": reason,
        "signals": {
            "total_tokens": total_tokens,
            "page_count": page_count,
            "top_five_pages_token_share": top_five_share,
            "dense_pages_over_400_tokens": dense_page_count,
        },
        "thresholds": {
            "large_doc_total_tokens": PAGE_NOTES_TOTAL_TOKEN_THRESHOLD,
            "spread_doc_total_tokens": PAGE_NOTES_SPREAD_TOKEN_THRESHOLD,
            "spread_doc_page_count": PAGE_NOTES_PAGE_COUNT_THRESHOLD,
            "spread_doc_top_five_share_max": PAGE_NOTES_TOP_FIVE_SHARE_THRESHOLD,
            "dense_page_threshold": PAGE_NOTES_DENSE_PAGE_THRESHOLD,
            "dense_page_count_threshold": PAGE_NOTES_DENSE_PAGE_COUNT_THRESHOLD,
        },
    }


def load_manifest_by_doc_id(processed_contracts_dir: Path, doc_id: str) -> DocumentManifest:
    """Load one document manifest by doc_id."""
    manifest_path = processed_contracts_dir / doc_id / "manifest.json"
    return _load_manifest(manifest_path)


def build_page_token_profiles(repo_root: Path, processed_contracts_dir: Path) -> list[dict[str, object]]:
    """Build page token profiles for all manifests in the processed contracts directory."""
    profiles: list[dict[str, object]] = []
    for manifest_path in _iter_manifest_paths(processed_contracts_dir):
        manifest = _load_manifest(manifest_path)
        profiles.append(page_token_profile(repo_root, manifest))
    return profiles


def build_page_notes_candidates(
    repo_root: Path,
    processed_contracts_dir: Path,
    *,
    min_total_tokens: int = PAGE_NOTES_TOTAL_TOKEN_THRESHOLD,
) -> list[dict[str, object]]:
    """Return large-document page token profiles sorted by total tokens."""
    profiles = build_page_token_profiles(repo_root, processed_contracts_dir)
    ranked = sorted(
        profiles,
        key=lambda profile: (
            -_safe_int(dict(profile.get("summary", {})).get("total_tokens")),
            str(profile.get("source_filename", "")),
        ),
    )
    return [
        profile
        for profile in ranked
        if _safe_int(dict(profile.get("summary", {})).get("total_tokens")) >= min_total_tokens
    ]
