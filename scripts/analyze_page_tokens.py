from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.page_token_analysis import (
    build_page_notes_candidates,
    top_pages_by_tokens,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for page token analysis."""
    parser = argparse.ArgumentParser(description="Analyze page-level token spread for large documents.")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of large documents to show.",
    )
    parser.add_argument(
        "--min-total-tokens",
        type=int,
        default=40000,
        help="Only include docs at or above this estimated token total.",
    )
    parser.add_argument(
        "--top-pages",
        type=int,
        default=5,
        help="Number of top token-heavy pages to show per doc.",
    )
    return parser.parse_args()


def main() -> None:
    """Print a page-level token spread view for large documents."""
    configure_logging()
    args = parse_args()
    processed_contracts_dir = REPO_ROOT / "data" / "processed" / "contracts"

    print("Starting page token analysis.")
    candidates = build_page_notes_candidates(
        REPO_ROOT,
        processed_contracts_dir,
        min_total_tokens=args.min_total_tokens,
    )
    output = {
        "min_total_tokens": args.min_total_tokens,
        "documents_matching_threshold": len(candidates),
        "documents": candidates[: args.limit],
    }
    output_path = REPO_ROOT / "data" / "processed" / "indexes" / "page_token_analysis.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print(
        f"Found {len(candidates)} docs at or above {args.min_total_tokens:,} estimated tokens. "
        f"Showing top {min(len(candidates), args.limit)}."
    )
    for profile in candidates[: args.limit]:
        summary = dict(profile["summary"])
        print(
            f"- {profile['doc_id']} | {profile['source_filename']} | "
            f"tokens={summary['total_tokens']:,} | pages={summary['page_count']} | "
            f"top5_share={summary['top_five_pages_token_share']:.2%} | "
            f"dense_pages={summary['dense_pages_over_400_tokens']}"
        )
        for page in top_pages_by_tokens(profile, limit=args.top_pages):
            print(
                f"    p.{page['page_number']} | tokens={int(page['estimated_tokens']):,} | "
                f"repr={page['representation']}"
            )

    print(f"Analysis written to {output_path}")


if __name__ == "__main__":
    main()
