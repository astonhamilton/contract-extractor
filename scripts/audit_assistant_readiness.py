from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.assistant_readiness import (
    build_assistant_readiness_report,
    load_manifests,
    write_assistant_readiness_report,
)
from packages.pipeline.logging_utils import configure_logging


def format_counts(counts: dict[str, int]) -> str:
    """Format compact state/count output for terminal summaries."""
    if not counts:
        return "-"
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name}={count}" for name, count in items)


def format_stage_summary(stage_name: str, stage: dict[str, int]) -> str:
    """Format one stage summary line for terminal output."""
    remaining_suffix = "" if stage["remaining"] == 0 else f" | remaining={stage['remaining']}"
    return (
        f"{stage_name}: "
        f"{stage['done']} done of {stage['total_required']} required"
        f"{remaining_suffix}"
    )


def main() -> None:
    """Audit corpus readiness for SQLite load / assistant backend ingestion."""
    configure_logging()
    print("Starting assistant-readiness audit.")
    print("This scans canonical manifests and derived artifacts to show what is still missing before DB load.")

    manifests = load_manifests(REPO_ROOT / "data" / "processed" / "contracts")
    report = build_assistant_readiness_report(REPO_ROOT, manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "assistant_readiness_report.json"
    write_assistant_readiness_report(report_path, report)

    print(
        "Assistant-readiness audit complete: "
        f"docs={report['total_documents']} | "
        f"states={format_counts(report['state_counts'])}"
    )
    print(format_stage_summary("Normalized", report["stages"]["normalized_document"]))
    print(format_stage_summary("Procurement Context", report["stages"]["procurement_context"]))
    print(format_stage_summary("Classification", report["stages"]["classification"]))
    print(format_stage_summary("Governing Domain Notes", report["stages"]["governing_domain_notes"]))
    print(format_stage_summary("Change Extraction", report["stages"]["change_extraction"]))
    print(
        "Loader readiness: "
        f"ready={report['loader_readiness']['ready']} | "
        f"remaining={report['loader_readiness']['remaining']}"
    )
    print(f"Next actions: {format_counts(report['next_action_counts'])}")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
