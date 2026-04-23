from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.token_inventory_analysis import (
    build_token_inventory_analysis,
    load_token_inventory_report,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for token inventory analysis."""
    parser = argparse.ArgumentParser(description="Analyze normalized token inventory outputs.")
    parser.add_argument(
        "--report",
        default="data/processed/indexes/token_inventory_report.json",
        help="Repo-relative or absolute path to a token inventory report.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of top documents to show in each ranking.",
    )
    return parser.parse_args()


def resolve_path(raw_path: str) -> Path:
    """Resolve repo-relative or absolute paths."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def print_doc_list(label: str, docs: list[dict[str, object]], *, token_key: str) -> None:
    """Print a short ranked document list."""
    print(f"{label}:")
    if not docs:
        print("  - none")
        return
    for doc in docs:
        if token_key == "best_available_total_tokens":
            tokens = int(doc.get("best_available_total_tokens", 0))
        else:
            tokens = int(doc.get("tokens_by_artifact_type", {}).get(token_key, 0))
        print(
            "  - "
            f"{doc['source_filename']} | "
            f"tokens={tokens} | "
            f"pages={doc['page_count']} | "
            f"best_mix={doc.get('best_available_type_counts', {})}"
        )


def main() -> None:
    """Analyze a token inventory report and print ranked token concentrations."""
    configure_logging()
    args = parse_args()
    report_path = resolve_path(args.report)

    print("Starting token inventory analysis.")
    print("This ranks documents by best-available normalized token footprint and per-artifact totals.")

    report = load_token_inventory_report(report_path)
    analysis = build_token_inventory_analysis(report, limit=args.limit)
    analysis_path = report_path.with_name("token_inventory_analysis.json")
    analysis_path.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")

    print(
        "Token inventory analysis complete: "
        f"docs={analysis['documents_total']} | "
        f"best_available_total_tokens={analysis['best_available_total_tokens']}"
    )
    print(f"Best available type mix: {analysis['best_available_type_counts']}")
    print(f"Tokens by artifact type: {analysis['tokens_by_artifact_type']}")
    print_doc_list(
        f"Top {args.limit} docs by best-available tokens",
        analysis["top_documents_by_best_available_tokens"],
        token_key="best_available_total_tokens",
    )
    print_doc_list(
        f"Top {args.limit} docs by text tokens",
        analysis["top_documents_by_text_tokens"],
        token_key="text",
    )
    print_doc_list(
        f"Top {args.limit} docs by OCR tokens",
        analysis["top_documents_by_ocr_tokens"],
        token_key="ocr_text",
    )
    print_doc_list(
        f"Top {args.limit} docs by markdown tokens",
        analysis["top_documents_by_markdown_tokens"],
        token_key="markdown",
    )
    print_doc_list(
        f"Top {args.limit} docs by repair tokens",
        analysis["top_documents_by_repair_tokens"],
        token_key="repair_markdown",
    )
    print(f"Analysis written to {analysis_path}")


if __name__ == "__main__":
    main()
