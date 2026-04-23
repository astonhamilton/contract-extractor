from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.image_orientation import (
    build_image_orientation_report,
    normalize_image_orientation_documents,
    write_image_orientation_report,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the canonical orientation-validation stage."""
    parser = argparse.ArgumentParser(description="Validate page-image orientation for processed contract pages.")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for page-level orientation detection.",
    )
    return parser.parse_args()


def main() -> None:
    """Validate page-image orientation for processed contract pages with rendered images."""
    configure_logging()
    args = parse_args()
    print("Starting image orientation validation stage.")
    print("This stage runs after text normalization and before OCR/vision stages.")
    print("It validates page images are upright and writes upright copies only when rotation is needed.")
    print(f"Workers: {args.workers}")

    summary = normalize_image_orientation_documents(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        workers=args.workers,
    )
    report = build_image_orientation_report(summary)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "image_orientation_report.json"
    write_image_orientation_report(report_path, report)

    print(
        "Image orientation validation complete: "
        f"candidate_documents={summary['candidate_documents']} | "
        f"processed_documents={summary['processed_documents']} | "
        f"processed_pages={summary['processed_pages']} | "
        f"rotated_pages={summary['rotated_pages']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
