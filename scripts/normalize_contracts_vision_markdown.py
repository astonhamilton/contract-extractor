from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.vision_markdown import (
    VisionMarkdownStageConfig,
    apply_vision_markdown_run,
    default_vision_markdown_worker_count,
    execute_vision_markdown_run,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for staged/apply vision-markdown execution."""
    parser = argparse.ArgumentParser(
        description="Run staged LLM vision markdown or apply a staged run into manifests."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Run LLM vision markdown into a staged run folder without mutating manifests.",
    )
    mode.add_argument(
        "--apply-run",
        help="Run id or report path from a prior dry-run to apply into manifests.",
    )
    parser.add_argument("--doc-id", help="Single doc_id target for dry-run mode.")
    parser.add_argument("--random-n", type=int, help="Randomly sample N eligible pages for dry-run mode.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for --random-n.")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers for page-level LLM vision markdown.",
    )
    parser.add_argument(
        "--model",
        default="openai/gpt-5.4-nano",
        help="LiteLLM model name for vision markdown normalization.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Include or overwrite already-generated vision markdown pages.",
    )
    return parser.parse_args()


def resolve_run_report_path(apply_run: str) -> Path:
    """Resolve a run id or report path into a vision-markdown run report path."""
    path = Path(apply_run)
    if path.suffix == ".json":
        return path if path.is_absolute() else REPO_ROOT / path
    return (
        REPO_ROOT
        / "data"
        / "processed"
        / "vision_markdown_runs"
        / apply_run
        / "vision_markdown_run_report.json"
    )


def main() -> None:
    """Run or apply the staged canonical vision-markdown stage."""
    configure_logging()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    args = parse_args()
    workers = args.workers if args.workers is not None else default_vision_markdown_worker_count()
    config = VisionMarkdownStageConfig(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        runs_dir=REPO_ROOT / "data" / "processed" / "vision_markdown_runs",
        indexes_dir=REPO_ROOT / "data" / "processed" / "indexes",
        model=args.model,
        workers=workers,
    )

    print("Starting canonical LLM vision markdown stage.")
    print(
        f"Loaded .env if present. OPENAI_API_KEY set={bool(os.getenv('OPENAI_API_KEY'))} "
        f"ANTHROPIC_API_KEY set={bool(os.getenv('ANTHROPIC_API_KEY'))}"
    )
    if args.dry_run:
        print("Mode: dry-run")
        print("This writes staged LLM vision-markdown artifacts under data/processed/vision_markdown_runs/.")
        print("It does not update manifests until a separate apply pass.")
        print(f"Model: {config.model}")
        print(f"Workers: {config.workers}")
        if args.doc_id:
            print(f"Selection: doc_id={args.doc_id}")
        elif args.random_n is not None:
            print(f"Selection: random_n={args.random_n} pages seed={args.seed}")
        else:
            print("Selection: all eligible pages needing LLM vision markdown")

        report, report_path = execute_vision_markdown_run(
            config=config,
            doc_id=args.doc_id,
            random_n=args.random_n,
            seed=args.seed,
            force=args.force,
        )
        usage_summary = report.get("usage_summary")
        prompt_tokens = "-"
        completion_tokens = "-"
        reasoning_tokens = "-"
        total_tokens = "-"
        if isinstance(usage_summary, dict):
            totals = usage_summary.get("totals")
            if isinstance(totals, dict):
                prompt_tokens = str(totals.get("prompt_tokens", "-"))
                completion_tokens = str(totals.get("completion_tokens", "-"))
                reasoning_tokens = str(totals.get("reasoning_tokens", "-"))
                total_tokens = str(totals.get("total_tokens", "-"))
        print(
            "LLM vision-markdown dry-run complete: "
            f"selected_pages={report['pages_selected']} | "
            f"selected_docs={report['documents_selected']} | "
            f"succeeded={report['pages_succeeded']} | "
            f"failed={report['pages_failed']} | "
            f"total_tokens={total_tokens}"
        )
        print(
            "Usage totals: "
            f"prompt_tokens={prompt_tokens} | "
            f"completion_tokens={completion_tokens} | "
            f"reasoning_tokens={reasoning_tokens} | "
            f"total_tokens={total_tokens}"
        )
        print(f"Report written to {report_path}")
        return

    run_report_path = resolve_run_report_path(args.apply_run)
    print("Mode: apply")
    print("This copies staged vision markdown into canonical page folders and updates manifests.")
    print(f"Source run report: {run_report_path}")
    result = apply_vision_markdown_run(
        config=config,
        run_report_path=run_report_path,
        force=args.force,
    )
    apply_report = result["report"]
    print(
        "LLM vision-markdown apply complete: "
        f"seen={apply_report['pages_seen']} | "
        f"applied={apply_report['pages_applied']} | "
        f"skipped={apply_report['pages_skipped']}"
    )
    print(f"Report written to {result['report_path']}")


if __name__ == "__main__":
    main()
