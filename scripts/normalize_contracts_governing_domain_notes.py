from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from packages.pipeline.governing_domain_notes_stage import (
    GoverningDomainNotesStageConfig,
    apply_governing_domain_notes_run,
    execute_governing_domain_notes_run,
)
from packages.pipeline.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for canonical governing-domain-notes staging/apply."""
    parser = argparse.ArgumentParser(
        description="Run staged governing domain notes or apply a staged run into manifests."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Run governing-domain-notes into a staged run folder without mutating manifests.",
    )
    mode.add_argument(
        "--apply-run",
        help="Run id or report path from a prior dry-run to apply into manifests.",
    )
    parser.add_argument("--doc-id", help="Single doc_id target for dry-run mode.")
    parser.add_argument("--random-n", type=int, help="Randomly sample N documents for dry-run mode.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for --random-n.")
    parser.add_argument("--workers", type=int, default=1, help="Doc-level parallel workers for dry-run mode.")
    parser.add_argument("--force", action="store_true", help="Include or overwrite already-processed docs.")
    parser.add_argument(
        "--model",
        default="openai/gpt-5.4-mini",
        help="LiteLLM model name for governing domain notes.",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help="Optional reasoning effort hint. If omitted, no reasoning hint is sent.",
    )
    return parser.parse_args()


def resolve_run_report_path(apply_run: str) -> Path:
    """Resolve a run id or repo-relative/absolute report path into a report path."""
    path = Path(apply_run)
    if path.suffix == ".json":
        return path if path.is_absolute() else REPO_ROOT / path
    return (
        REPO_ROOT
        / "data"
        / "processed"
        / "governing_domain_notes_runs"
        / apply_run
        / "governing_domain_notes_run_report.json"
    )


def main() -> None:
    """Run or apply canonical governing-domain-notes stage."""
    configure_logging()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    args = parse_args()

    config = GoverningDomainNotesStageConfig(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        runs_dir=REPO_ROOT / "data" / "processed" / "governing_domain_notes_runs",
        indexes_dir=REPO_ROOT / "data" / "processed" / "indexes",
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        workers=args.workers,
    )

    print("Starting canonical governing-domain-notes stage.")
    print(
        f"Loaded .env if present. OPENAI_API_KEY set={bool(os.getenv('OPENAI_API_KEY'))} "
        f"ANTHROPIC_API_KEY set={bool(os.getenv('ANTHROPIC_API_KEY'))}"
    )

    if args.dry_run:
        print("Mode: dry-run")
        print("This writes staged governing-domain-notes artifacts under data/processed/governing_domain_notes_runs/.")
        print("It does not update manifests until a separate apply pass.")
        print(f"Model: {args.model}")
        print(f"Reasoning effort: {args.reasoning_effort}")
        print(f"Workers: {args.workers}")
        if args.doc_id:
            print(f"Selection: doc_id={args.doc_id}")
        elif args.random_n is not None:
            print(f"Selection: random_n={args.random_n} seed={args.seed}")
        else:
            print("Selection: all eligible governing docs without canonical notes")

        report, report_path = execute_governing_domain_notes_run(
            config=config,
            doc_id=args.doc_id,
            random_n=args.random_n,
            seed=args.seed,
            force=args.force,
        )
        print(
            "Governing-domain-notes dry-run complete: "
            f"selected={report['documents_selected']} | "
            f"succeeded={report['documents_succeeded']} | "
            f"failed={report['documents_failed']}"
        )
        print(f"Report written to {report_path}")
        return

    run_report_path = resolve_run_report_path(args.apply_run)
    print("Mode: apply")
    print("This copies staged governing-domain-notes outputs into canonical derived folders and updates manifests.")
    print(f"Source run report: {run_report_path}")
    result = apply_governing_domain_notes_run(
        config=config,
        run_report_path=run_report_path,
        force=args.force,
    )
    apply_report = result["report"]
    print(
        "Governing-domain-notes apply complete: "
        f"seen={apply_report['documents_seen']} | "
        f"applied={apply_report['documents_applied']} | "
        f"skipped={apply_report['documents_skipped']}"
    )
    print(f"Report written to {result['report_path']}")


if __name__ == "__main__":
    main()
