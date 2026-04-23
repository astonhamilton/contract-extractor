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
from packages.pipeline.run_pipeline import PipelineRunConfig, default_e2e_ocr_workers, run_full_pipeline


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the end-to-end pipeline runner."""
    parser = argparse.ArgumentParser(description="Run the full contract-processing pipeline incrementally.")
    parser.add_argument(
        "--raw-dir",
        default="data/raw/contracts",
        help="Repo-relative or absolute folder containing raw PDFs to inventory.",
    )
    parser.add_argument(
        "--ocr-mode",
        choices=("parallel", "sequential"),
        default="parallel",
        help="OCR execution mode.",
    )
    parser.add_argument(
        "--ocr-workers",
        type=int,
        default=None,
        help="OCR worker count. Defaults to number of CPU cores.",
    )
    parser.add_argument(
        "--markdown-model",
        default="openai/gpt-5.4-mini",
        help="Model for canonical markdown normalization.",
    )
    parser.add_argument(
        "--repair-model",
        default="openai/gpt-5.4-mini",
        help="Model for canonical repair normalization.",
    )
    parser.add_argument(
        "--enable-llm-image-orientation",
        action="store_true",
        help="Enable the canonical LLM image-orientation stage after deterministic orientation.",
    )
    parser.add_argument(
        "--llm-image-orientation-model",
        default="openai/gpt-5.4-nano",
        help="Model for canonical LLM image orientation.",
    )
    parser.add_argument(
        "--llm-image-orientation-reasoning-effort",
        default="none",
        help="Reasoning effort for canonical LLM image orientation.",
    )
    parser.add_argument(
        "--llm-image-orientation-workers",
        type=int,
        default=None,
        help="Worker count for canonical LLM image orientation.",
    )
    parser.add_argument(
        "--enable-vision-markdown",
        action="store_true",
        help="Enable the canonical vision-markdown stage after standard markdown normalization.",
    )
    parser.add_argument(
        "--vision-markdown-model",
        default="openai/gpt-5.4-nano",
        help="Model for canonical vision markdown normalization.",
    )
    parser.add_argument(
        "--vision-markdown-workers",
        type=int,
        default=None,
        help="Worker count for canonical vision markdown normalization.",
    )
    return parser.parse_args()


def resolve_path(raw_path: str) -> Path:
    """Resolve repo-relative or absolute input paths."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def print_stage_update(stage: str, message: str) -> None:
    """Print a readable stage update from the package orchestrator."""
    print(f"[{stage}] {message}")


def main() -> None:
    """Run the full incremental pipeline over the raw corpus."""
    configure_logging()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    args = parse_args()
    raw_dir = resolve_path(args.raw_dir)
    ocr_workers = args.ocr_workers if args.ocr_workers is not None else default_e2e_ocr_workers()

    print("Starting end-to-end pipeline run.")
    print("This inventories raw PDFs, runs the canonical processing stages incrementally, then audits final state.")
    print(f"Loaded .env if present. OPENAI_API_KEY set={bool(os.getenv('OPENAI_API_KEY'))} ANTHROPIC_API_KEY set={bool(os.getenv('ANTHROPIC_API_KEY'))}")
    print(f"Raw dir: {raw_dir}")
    print(f"OCR mode: {args.ocr_mode} | OCR workers: {ocr_workers}")
    print(f"Markdown model: {args.markdown_model}")
    print(f"Repair model: {args.repair_model}")
    print(
        "Optional LLM stages: "
        f"llm_image_orientation={args.enable_llm_image_orientation} | "
        f"vision_markdown={args.enable_vision_markdown}"
    )

    result = run_full_pipeline(
        PipelineRunConfig(
            repo_root=REPO_ROOT,
            raw_contracts_dir=raw_dir,
            processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
            indexes_dir=REPO_ROOT / "data" / "processed" / "indexes",
            ocr_mode=args.ocr_mode,
            ocr_workers=ocr_workers,
            markdown_model=args.markdown_model,
            repair_model=args.repair_model,
            enable_llm_image_orientation=args.enable_llm_image_orientation,
            llm_image_orientation_model=args.llm_image_orientation_model,
            llm_image_orientation_reasoning_effort=args.llm_image_orientation_reasoning_effort,
            llm_image_orientation_workers=args.llm_image_orientation_workers,
            enable_vision_markdown=args.enable_vision_markdown,
            vision_markdown_model=args.vision_markdown_model,
            vision_markdown_workers=args.vision_markdown_workers,
        ),
        stage_callback=print_stage_update,
    )

    print(
        "Pipeline run complete: "
        f"inventory={result['inventory_count']} | "
        f"txt_completed={result['txt_report']['completed_documents']} | "
        f"txt_failed={result['txt_report']['failed_documents']} | "
        f"oriented_pages={result['orientation_report']['processed_pages']} | "
        f"rotated_pages={result['orientation_report']['rotated_pages']} | "
        f"ocr_candidates={result['ocr_report']['total_candidate_documents']} | "
        f"llm_oriented_pages={(result['llm_orientation_report'] or {}).get('pages_succeeded', 0)} | "
        f"markdown_pages={result['markdown_report']['processed_pages']} | "
        f"vision_markdown_pages={(result['vision_markdown_report'] or {}).get('pages_succeeded', 0)} | "
        f"repair_pages={result['repair_report']['processed_pages']} | "
        f"assembled_docs={result['assembled_report']['documents_total']}"
    )
    print(
        "Token inventory: "
        f"best_available_total_tokens={result['token_report']['corpus']['best_available_total_tokens']} | "
        f"by_type={result['token_report']['corpus']['tokens_by_artifact_type']}"
    )
    print(
        "Final state: "
        f"{result['pipeline_report']['state_counts']}"
    )
    print(f"Reports written under {REPO_ROOT / 'data' / 'processed' / 'indexes'}")


if __name__ == "__main__":
    main()
