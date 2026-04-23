from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from packages.llm.shared.task_runtime.capabilities import effective_reasoning_effort
from packages.pipeline.change_extraction_stage import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_OPENAI_MODEL,
    ChangeExtractionStageConfig,
    apply_change_extraction_run,
    execute_change_extraction_run,
)
from packages.pipeline.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for canonical change-extraction staging/apply."""
    parser = argparse.ArgumentParser(
        description="Run staged change extraction or apply a staged run into manifests."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Run change extraction into a staged run folder without mutating manifests.",
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
        default=None,
        help="LiteLLM model name, e.g. openai/gpt-5.4-mini or anthropic/claude-haiku-4-5.",
    )
    parser.add_argument(
        "--anthropic",
        action="store_true",
        help="Use the Anthropic default model for this run.",
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
        / "change_extraction_runs"
        / apply_run
        / "change_extraction_run_report.json"
    )


def main() -> None:
    """Run or apply canonical change-extraction stage."""
    configure_logging()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    args = parse_args()
    model = args.model or (DEFAULT_ANTHROPIC_MODEL if args.anthropic else DEFAULT_OPENAI_MODEL)

    config = ChangeExtractionStageConfig(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        runs_dir=REPO_ROOT / "data" / "processed" / "change_extraction_runs",
        indexes_dir=REPO_ROOT / "data" / "processed" / "indexes",
        model=model,
        reasoning_effort=args.reasoning_effort,
        workers=args.workers,
    )

    print("Starting canonical change-extraction stage.")
    print(
        f"Loaded .env if present. OPENAI_API_KEY set={bool(os.getenv('OPENAI_API_KEY'))} "
        f"ANTHROPIC_API_KEY set={bool(os.getenv('ANTHROPIC_API_KEY'))}"
    )

    if args.dry_run:
        print("Mode: dry-run")
        print("This writes staged change-extraction artifacts under data/processed/change_extraction_runs/.")
        print("It does not update manifests until a separate apply pass.")
        print(f"Model: {model}")
        print(f"Reasoning effort: {args.reasoning_effort}")
        effective_effort = effective_reasoning_effort(model, args.reasoning_effort)
        if effective_effort != args.reasoning_effort:
            print(f"Reasoning effort effective: {effective_effort}")
        print(f"Workers: {args.workers}")
        if args.doc_id:
            print(f"Selection: doc_id={args.doc_id}")
        elif args.random_n is not None:
            print(f"Selection: random_n={args.random_n} seed={args.seed}")
        else:
            print("Selection: all eligible change docs without canonical extraction")

        report, report_path = execute_change_extraction_run(
            config=config,
            doc_id=args.doc_id,
            random_n=args.random_n,
            seed=args.seed,
            force=args.force,
        )
        print(
            "Change-extraction dry-run complete: "
            f"selected={report['documents_selected']} | "
            f"succeeded={report['documents_succeeded']} | "
            f"failed={report['documents_failed']}"
        )
        print(f"Report written to {report_path}")
        return

    run_report_path = resolve_run_report_path(args.apply_run)
    print("Mode: apply")
    print("This copies staged change-extraction outputs into canonical derived folders and updates manifests.")
    print(f"Source run report: {run_report_path}")
    result = apply_change_extraction_run(
        config=config,
        run_report_path=run_report_path,
        force=args.force,
    )
    apply_report = result["report"]
    print(
        "Change-extraction apply complete: "
        f"seen={apply_report['documents_seen']} | "
        f"applied={apply_report['documents_applied']} | "
        f"skipped={apply_report['documents_skipped']}"
    )
    print(f"Report written to {result['report_path']}")


if __name__ == "__main__":
    main()
