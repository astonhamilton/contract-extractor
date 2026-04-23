from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.analyze_quality import (
    build_quality_report,
    load_all_manifests,
    write_quality_report,
)


def format_reason_counts(reason_counts: dict[str, int], limit: int = 5) -> str:
    """Format the top reason counts into a compact console string."""
    items = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
    if not items:
        return "-"
    return ", ".join(f"{reason}={count}" for reason, count in items[:limit])


def print_candidate_examples(
    label: str,
    candidates: list[dict[str, object]],
    limit: int = 5,
) -> None:
    """Print a few representative candidate pages for quick inspection."""
    print(f"{label} examples:")
    if not candidates:
        print("  - none")
        return

    for candidate in candidates[:limit]:
        flags = ",".join(candidate["quality_flags"]) if candidate["quality_flags"] else "-"
        print(
            "  - "
            f"{candidate['source_filename']} | "
            f"page {candidate['page_number']} | "
            f"method={candidate['extraction_method']} | "
            f"flags={flags}"
        )


def main() -> None:
    """Analyze manifest outputs to summarize extraction confidence and next-step candidates."""
    configure_logging()
    print("Starting normalization quality analysis.")
    print("This scans all document manifests and summarizes confidence, flags, and likely LLM markdown/repair candidates.")

    manifests = load_all_manifests(REPO_ROOT / "data" / "processed" / "contracts")
    report = build_quality_report(manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "normalization_quality_report.json"
    write_quality_report(report_path, report)

    print(
        "Quality analysis complete: "
        f"docs={report['documents']['total']} | "
        f"pages={report['pages']['total']} | "
        f"markdown_candidates={report['llm_candidates']['markdown_page_count']} | "
        f"repair_candidates={report['llm_candidates']['repair_page_count']} | "
        f"skipped_repair_pages={report['llm_candidates']['skipped_repair_page_count']} | "
        f"manual_review_docs={report['manual_review']['document_count']}"
    )
    print(
        "Top markdown reasons: "
        f"{format_reason_counts(report['llm_candidates']['markdown_reason_counts'])}"
    )
    print(
        "Top repair reasons: "
        f"{format_reason_counts(report['llm_candidates']['repair_reason_counts'])}"
    )
    print(
        "Top skipped-repair reasons: "
        f"{format_reason_counts(report['llm_candidates']['skipped_repair_reason_counts'])}"
    )
    print_candidate_examples("Markdown candidate", report["llm_candidates"]["markdown_pages"])
    print_candidate_examples("Repair candidate", report["llm_candidates"]["repair_pages"])
    print_candidate_examples("Skipped repair page", report["llm_candidates"]["skipped_repair_pages"])
    print("Current table detection is heuristic only; no explicit image-layout table analysis is implemented yet.")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
