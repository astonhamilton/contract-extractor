from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.ocr_pages import (
    build_ocr_report,
    normalize_ocr_documents,
    write_ocr_report,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the canonical OCR normalization stage."""
    parser = argparse.ArgumentParser(description="Run OCR fallback for processed documents.")
    parser.add_argument(
        "--mode",
        choices=("parallel", "sequential"),
        default="parallel",
        help="Execution mode for canonical OCR normalization.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Worker count for parallel OCR. Ignored in sequential mode.",
    )
    return parser.parse_args()


def main() -> None:
    """Run OCR fallback for documents flagged during text normalization."""
    configure_logging()
    args = parse_args()
    print("Starting OCR fallback normalization stage.")
    print("This stage is expected to run after the text normalization pass.")
    print("It only targets pages flagged as likely needing OCR; if no pages were flagged, nothing will run.")
    print(f"Mode: {args.mode}")

    manifests = normalize_ocr_documents(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        mode=args.mode,
        workers=args.workers,
    )
    report = build_ocr_report(manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "ocr_report.json"
    write_ocr_report(report_path, report)

    print(
        "OCR normalization complete: "
        f"{report['total_candidate_documents']} candidates | "
        f"ocr_attempted={report['ocr_attempted_documents']} | "
        f"llm_recommended={report['llm_recommended_documents']} | "
        f"mode={args.mode}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
