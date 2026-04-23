from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OPENAI_MODEL = "openai/gpt-5.4-mini"
DEFAULT_ANTHROPIC_MODEL = "anthropic/claude-haiku-4-5"

from dotenv import load_dotenv

from packages.llm.shared.task_runtime import (
    effective_reasoning_effort,
    model_supports_strict_structured_output,
)
from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.page_notes_stage import (
    PageNotesStageConfig,
    apply_page_notes_run,
    execute_page_notes_run,
    page_notes_analysis,
    write_page_notes_analysis_report,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for canonical page-notes analysis/execution."""
    parser = argparse.ArgumentParser(
        description="Analyze, stage, or apply canonical page-notes generation."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--analyze", action="store_true", help="Analyze page-notes candidates and write a report.")
    mode.add_argument("--dry-run", action="store_true", help="Run page notes into a staged run folder without mutating manifests.")
    mode.add_argument("--apply-run", help="Run id or report path from a prior dry-run to apply into manifests.")

    parser.add_argument("--doc-id", help="Single doc_id target for dry-run mode.")
    parser.add_argument("--random-n", type=int, help="Randomly sample N documents for dry-run mode.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for --random-n.")
    parser.add_argument("--workers", type=int, default=1, help="Doc-level parallel workers for dry-run mode.")
    parser.add_argument("--page-workers", type=int, default=1, help="Page-level parallel workers within each document for dry-run mode.")
    parser.add_argument("--force", action="store_true", help="Include or overwrite already-processed docs.")
    parser.add_argument("--model", default=None, help="LiteLLM model name.")
    parser.add_argument("--anthropic", action="store_true", help="Use the Anthropic default model for this run.")
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        choices=["none", "low", "medium", "high", "xhigh"],
        help="Reasoning effort for supported models. If omitted, no hint is sent.",
    )
    parser.add_argument(
        "--structured-output",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Turn strict structured output on/off for page-notes execution.",
    )
    parser.add_argument("--debug-llm-dump", action="store_true", help="Write per-page LLM request/response dumps during dry-run execution.")
    parser.add_argument(
        "--selection-token-threshold",
        type=int,
        default=20_000,
        help="Target any document at or above this estimated token count.",
    )
    parser.add_argument("--top-n", type=int, default=20, help="Number of top candidate documents to list in analyze mode.")
    parser.add_argument(
        "--report-path",
        default="data/processed/indexes/page_notes_candidate_analysis.json",
        help="Repo-relative or absolute path for analyze-mode report output.",
    )
    return parser.parse_args()


def resolve_path(raw_path: str) -> Path:
    """Resolve a repo-relative or absolute path."""
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


def resolve_run_report_path(apply_run: str) -> Path:
    """Resolve a run id or repo-relative/absolute report path into a report path."""
    path = Path(apply_run)
    if path.suffix == ".json":
        return path if path.is_absolute() else REPO_ROOT / path
    return (
        REPO_ROOT
        / "data"
        / "processed"
        / "page_notes_runs"
        / apply_run
        / "page_notes_run_report.json"
    )


def main() -> None:
    """Analyze, run, or apply canonical page-notes stage."""
    configure_logging()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    args = parse_args()

    model = args.model or (DEFAULT_ANTHROPIC_MODEL if args.anthropic else DEFAULT_OPENAI_MODEL)
    config = PageNotesStageConfig(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        runs_dir=REPO_ROOT / "data" / "processed" / "page_notes_runs",
        indexes_dir=REPO_ROOT / "data" / "processed" / "indexes",
        model=model,
        reasoning_effort=args.reasoning_effort,
        structured_output=args.structured_output,
        workers=args.workers,
        page_workers=args.page_workers,
        selection_token_threshold=args.selection_token_threshold,
    )

    print("Starting canonical page-notes stage.")
    print(
        f"Loaded .env if present. OPENAI_API_KEY set={bool(os.getenv('OPENAI_API_KEY'))} "
        f"ANTHROPIC_API_KEY set={bool(os.getenv('ANTHROPIC_API_KEY'))}"
    )

    if args.analyze:
        print("Mode: analyze")
        print(f"Selection threshold: {config.selection_token_threshold:,} estimated tokens")
        print(
            "Selection basis: best available per page via normalized_document.xml when present, "
            "otherwise repair > markdown > vision_markdown > ocr > text"
        )
        report = page_notes_analysis(config, top_n=args.top_n)
        report_path = resolve_path(args.report_path)
        write_page_notes_analysis_report(report_path, report)
        print(
            "Page-notes candidate analysis complete: "
            f"docs={report['documents_targeted']} | "
            f"pages={report['targeted_pages_total']} | "
            f"chars={report['targeted_chars_total']:,} | "
            f"tokens={report['targeted_tokens_total']:,}"
        )
        print(f"Top {args.top_n} candidate docs:")
        for doc in report["top_documents"]:
            print(
                "  - "
                f"{doc['source_filename']} | "
                f"pages={doc['page_count']} | "
                f"chars={doc['total_chars']:,} | "
                f"tokens={doc['total_tokens']:,} | "
                f"avg_tokens/page={doc['avg_tokens_per_page']} | "
                f"top5_share={doc['top_five_pages_token_share']:.2%} | "
                f"dense_pages={doc['dense_pages_over_400_tokens']}"
            )
        print(f"Report written to {report_path}")
        return

    if args.dry_run:
        effective_effort = effective_reasoning_effort(config.model, config.reasoning_effort)
        print("Mode: dry-run")
        print("This writes staged page-notes artifacts under data/processed/page_notes_runs/.")
        print("It does not update manifests until a separate apply pass.")
        print(f"Model: {config.model}")
        print(f"Reasoning effort: {config.reasoning_effort if config.reasoning_effort is not None else 'not set'}")
        if effective_effort != config.reasoning_effort:
            print("Reasoning effort effective: none (not sent for this provider/model)")
        print(f"Structured output: {config.structured_output}")
        if config.structured_output and not model_supports_strict_structured_output(config.model):
            print("Structured output support: unsupported for this provider/model in current experiment")
        print(f"Workers: {config.workers}")
        print(f"Page workers: {config.page_workers}")
        print(f"Effective max parallel page calls: {config.workers * config.page_workers}")
        print(f"Debug LLM dump: {args.debug_llm_dump}")
        print(f"Selection threshold: {config.selection_token_threshold:,} estimated tokens")
        if args.doc_id:
            print(f"Selection: doc_id={args.doc_id}")
        elif args.random_n is not None:
            print(f"Selection: random_n={args.random_n} seed={args.seed}")
        else:
            print("Selection: all eligible page-notes candidates")

        report, report_path = execute_page_notes_run(
            config=config,
            doc_id=args.doc_id,
            random_n=args.random_n,
            seed=args.seed,
            force=args.force,
            debug_llm_dump=args.debug_llm_dump,
        )
        print(
            "Page-notes dry-run complete: "
            f"selected={report['documents_selected']} | "
            f"succeeded={report['documents_succeeded']} | "
            f"failed={report['documents_failed']}"
        )
        print(f"Report written to {report_path}")
        return

    run_report_path = resolve_run_report_path(args.apply_run)
    print("Mode: apply")
    print("This copies staged page-notes outputs into canonical processed artifacts and updates manifests.")
    print(f"Source run report: {run_report_path}")
    result = apply_page_notes_run(config=config, run_report_path=run_report_path, force=args.force)
    apply_report = result["report"]
    print(
        "Page-notes apply complete: "
        f"seen={apply_report['documents_seen']} | "
        f"applied={apply_report['documents_applied']} | "
        f"skipped={apply_report['documents_skipped']}"
    )
    print(f"Report written to {result['report_path']}")


if __name__ == "__main__":
    main()
