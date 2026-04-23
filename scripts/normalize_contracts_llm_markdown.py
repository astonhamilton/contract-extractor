from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from packages.llm.transforms.markdown_normalization.config import MarkdownNormalizationConfig
from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.llm_markdown import (
    build_llm_markdown_report,
    normalize_llm_markdown_documents,
    write_llm_markdown_report,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for canonical markdown normalization."""
    parser = argparse.ArgumentParser(description="Run canonical LLM markdown normalization for selected pages.")
    parser.add_argument(
        "--model",
        default="openai/gpt-5.4-mini",
        help="LiteLLM model name for markdown normalization.",
    )
    return parser.parse_args()


def main() -> None:
    """Run canonical markdown normalization and write .md paths back into manifests."""
    configure_logging()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    args = parse_args()
    config = MarkdownNormalizationConfig(model=args.model)

    print("Starting canonical LLM markdown normalization stage.")
    print("This stage targets the selector-defined markdown candidate pages only.")
    print("It writes .md artifacts into processed page folders and updates manifests in place.")
    print(f"Loaded .env if present. OPENAI_API_KEY set={bool(os.getenv('OPENAI_API_KEY'))} ANTHROPIC_API_KEY set={bool(os.getenv('ANTHROPIC_API_KEY'))}")
    print(f"Model: {config.model}")

    summary = normalize_llm_markdown_documents(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        config=config,
    )
    report = build_llm_markdown_report(config=config, summary=summary)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "llm_markdown_report.json"
    write_llm_markdown_report(report_path, report)

    print(
        "Canonical LLM markdown normalization complete: "
        f"candidate_documents={summary['candidate_documents']} | "
        f"processed_documents={summary['processed_documents']} | "
        f"processed_pages={summary['processed_pages']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
