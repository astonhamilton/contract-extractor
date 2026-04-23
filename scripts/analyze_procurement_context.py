from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.analyze_procurement_context import (
    build_procurement_context_report,
    load_manifests_with_procurement_context,
    report_summary_line,
    write_procurement_context_report,
)
from packages.pipeline.logging_utils import configure_logging


def format_counter_line(counts: dict[str, int], limit: int = 10) -> str:
    """Format a compact top-N counter line for the terminal."""
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if not items:
        return "-"
    return ", ".join(f"{name}={count}" for name, count in items[:limit])


def print_examples(section: dict[str, object], key: str) -> None:
    """Print a few representative examples for one buyer/category grouping."""
    examples = section.get("examples", [])
    if not examples:
        print("  examples: none")
        return

    print("  examples:")
    for item in examples[:3]:
        print(
            "    - "
            f"{item['source_filename']} | "
            f"seller={item['seller']} | "
            f"subject={item['procurement_subject_summary']}"
        )


def main() -> None:
    """Analyze canonical procurement-context outputs and summarize groupings."""
    configure_logging()
    print("Starting procurement-context analysis.")
    print("This scans canonical procurement-context outputs and summarizes buyer/seller/category groupings.")

    manifests = load_manifests_with_procurement_context(REPO_ROOT / "data" / "processed" / "contracts")
    report = build_procurement_context_report(REPO_ROOT, manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "procurement_context_report.json"
    write_procurement_context_report(report_path, report)

    print(f"Procurement-context analysis complete: {report_summary_line(report)}")
    print(f"Missing fields: {format_counter_line(report['missing_field_counts'])}")

    top_buyers = report["top_buyers"]
    print("Top buyers:")
    if not top_buyers:
        print("  - none")
    else:
        for section in top_buyers[:5]:
            print(f"  - {section['buyer']} | count={section['count']}")
            print(f"    top_categories: {format_counter_line({item['name']: item['count'] for item in section['top_categories']})}")
            print_examples(section, "buyer")

    top_categories = report["top_categories"]
    print("Top categories:")
    if not top_categories:
        print("  - none")
    else:
        for section in top_categories[:5]:
            print(f"  - {section['category']} | count={section['count']}")
            print(f"    top_sellers: {format_counter_line({item['name']: item['count'] for item in section['top_sellers']})}")
            print_examples(section, "category")

    print(
        "Top buyer-seller pairs: "
        f"{format_counter_line({item['name']: item['count'] for item in report['top_buyer_seller_pairs']}, limit=10)}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
