from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.ocr_trials import run_ocr_trial


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the experimental OCR runner."""
    parser = argparse.ArgumentParser(description="Run experimental OCR into trial space.")
    parser.add_argument(
        "--mode",
        choices=("sequential", "parallel"),
        default="parallel",
        help="Execution mode for the experimental OCR run.",
    )
    parser.add_argument("--workers", type=int, default=None, help="Worker count for the OCR process pool.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of OCR target pages to sample for this trial.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used when --limit selects a subset of pages.")
    parser.add_argument(
        "--from-report",
        default=None,
        help="Reuse the exact target set from a previous OCR trial report by run id or report.json path.",
    )
    return parser.parse_args()


def main() -> None:
    """Run experimental OCR into sampled trial space without mutating canonical artifacts."""
    configure_logging()
    args = parse_args()

    print("Starting experimental OCR trial.")
    print("This is separate from the trusted sequential OCR stage.")
    print("Outputs are written as real trial artifacts under data/sampled/ocr_trials/.")
    print("This runner does not write manifests and does not use symlinks; it is explicitly experimental for comparison work.")
    print(f"Mode: {args.mode}")
    if args.from_report:
        print(f"Target selection: reusing targets from report {args.from_report}")
    else:
        print(f"Target selection: selector sampling with limit={args.limit if args.limit is not None else 'all'} seed={args.seed}")

    run_dir, report = run_ocr_trial(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        mode=args.mode,
        workers=args.workers,
        limit=args.limit,
        seed=args.seed,
        from_report=args.from_report,
    )
    print(
        "Experimental OCR trial complete: "
        f"mode={report['mode']} | "
        f"available_targets={report['total_available_target_pages']} | "
        f"targets={report['target_page_count']} | "
        f"successes={report['success_count']} | "
        f"failures={report['failure_count']} | "
        f"workers={report['workers']} | "
        f"seed={report['seed']} | "
        f"elapsed={report['elapsed_seconds']}s"
    )
    print(f"Trial written to {run_dir}")


if __name__ == "__main__":
    main()
