from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.pipeline_state import (
    build_pipeline_state_report,
    load_pipeline_manifests,
    write_pipeline_state_report,
)


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
        f"{stage['done']} done of {stage['total_matched']} total matched"
        f"{remaining_suffix}"
    )


def main() -> None:
    """Audit current manifest state and summarize which pipeline step each doc needs next."""
    configure_logging()
    print("Starting pipeline state audit.")
    print("This scans all manifests and derives each document's current state and next pipeline action.")

    manifests = load_pipeline_manifests(REPO_ROOT / "data" / "processed" / "contracts")
    report = build_pipeline_state_report(manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "pipeline_state_report.json"
    write_pipeline_state_report(report_path, report)

    print(
        "Pipeline state audit complete: "
        f"docs={report['total_documents']} | "
        f"states={format_counts(report['state_counts'])}"
    )
    print(format_stage_summary("Stage 1 TXT", report["stages"]["normalize_txt"]))
    print(format_stage_summary("Stage 2 OCR", report["stages"]["normalize_ocr"]))
    print(format_stage_summary("Stage 3 LLM Markdown", report["stages"]["normalize_llm_markdown"]))
    print(format_stage_summary("Stage 4 LLM Repair", report["stages"]["normalize_llm_repair"]))
    print(
        "No stage: "
        f"failed={report['no_stage']['failed']}, "
        f"not_run={report['no_stage']['not_run']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
