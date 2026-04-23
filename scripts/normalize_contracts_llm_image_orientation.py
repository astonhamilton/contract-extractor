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
from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.llm_image_orientation import (
    LLMImageOrientationStageConfig,
    apply_llm_image_orientation_run,
    default_llm_orientation_worker_count,
    execute_llm_image_orientation_run,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for canonical LLM image-orientation staging/apply."""
    parser = argparse.ArgumentParser(
        description="Run staged LLM image orientation or apply a staged run into manifests."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Run LLM image orientation into a staged run folder without mutating manifests.",
    )
    mode.add_argument(
        "--apply-run",
        help="Run id or report path from a prior dry-run to apply into manifests.",
    )
    parser.add_argument("--doc-id", help="Single doc_id target for dry-run mode.")
    parser.add_argument("--random-n", type=int, help="Randomly sample N eligible pages for dry-run mode.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for --random-n.")
    parser.add_argument(
        "--reasoning-effort",
        default="none",
        help="Reasoning effort for OpenAI models: none, low, medium, high, xhigh.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers for page-level LLM orientation detection.",
    )
    parser.add_argument(
        "--model",
        default="openai/gpt-5.4-nano",
        help="LiteLLM model name for image-orientation decisions.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Include or overwrite already-validated pages.",
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
        / "llm_image_orientation_runs"
        / apply_run
        / "llm_image_orientation_run_report.json"
    )


def main() -> None:
    """Run or apply canonical LLM image-orientation stage."""
    configure_logging()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    args = parse_args()
    workers = args.workers if args.workers is not None else default_llm_orientation_worker_count()
    config = LLMImageOrientationStageConfig(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        runs_dir=REPO_ROOT / "data" / "processed" / "llm_image_orientation_runs",
        indexes_dir=REPO_ROOT / "data" / "processed" / "indexes",
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        workers=workers,
    )

    print("Starting canonical LLM image orientation stage.")
    print(
        f"Loaded .env if present. OPENAI_API_KEY set={bool(os.getenv('OPENAI_API_KEY'))} "
        f"ANTHROPIC_API_KEY set={bool(os.getenv('ANTHROPIC_API_KEY'))}"
    )
    if args.dry_run:
        print("Mode: dry-run")
        print("This writes staged LLM image-orientation artifacts under data/processed/llm_image_orientation_runs/.")
        print("It does not update manifests until a separate apply pass.")
        print(f"Model: {config.model}")
        print(f"Reasoning effort: {config.reasoning_effort}")
        effective_effort = effective_reasoning_effort(config.model, config.reasoning_effort)
        if effective_effort != config.reasoning_effort:
            print(f"Reasoning effort effective: {effective_effort}")
        print(f"Workers: {config.workers}")
        if args.doc_id:
            print(f"Selection: doc_id={args.doc_id}")
        elif args.random_n is not None:
            print(f"Selection: random_n={args.random_n} pages seed={args.seed}")
        else:
            print("Selection: all eligible pages needing LLM image orientation")

        report, report_path = execute_llm_image_orientation_run(
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
            "LLM image-orientation dry-run complete: "
            f"selected_pages={report['pages_selected']} | "
            f"selected_docs={report['documents_selected']} | "
            f"candidate_pages={report['candidate_pages']} | "
            f"skipped_pages={report['skipped_pages']} | "
            f"succeeded={report['pages_succeeded']} | "
            f"failed={report['pages_failed']} | "
            f"rotated={report['rotated_pages']} | "
            f"manual_review={report['manual_review_pages']} | "
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
    print("This copies staged validated upright images into canonical page folders and updates manifests.")
    print(f"Source run report: {run_report_path}")
    result = apply_llm_image_orientation_run(
        config=config,
        run_report_path=run_report_path,
        force=args.force,
    )
    apply_report = result["report"]
    print(
        "LLM image-orientation apply complete: "
        f"seen={apply_report['pages_seen']} | "
        f"applied={apply_report['pages_applied']} | "
        f"skipped={apply_report['pages_skipped']}"
    )
    print(f"Report written to {result['report_path']}")


if __name__ == "__main__":
    main()
