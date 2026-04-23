from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.token_inventory import (
    build_token_inventory_report,
    load_token_inventory_manifests,
    write_token_inventory_report,
)


def main() -> None:
    """Estimate token usage across normalized document artifacts."""
    configure_logging()
    print("Starting normalized token inventory.")
    print("This estimates tokens for text, OCR text, markdown, and repair markdown artifacts.")
    print("It also computes a best-available total using: repair_markdown > markdown > vision_markdown > ocr_text > text.")

    manifests = load_token_inventory_manifests(REPO_ROOT / "data" / "processed" / "contracts")
    report = build_token_inventory_report(REPO_ROOT, manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "token_inventory_report.json"
    write_token_inventory_report(report_path, report)

    corpus = report["corpus"]
    print(
        "Token inventory complete: "
        f"docs={report['documents_total']} | "
        f"best_available_total_tokens={corpus['best_available_total_tokens']}"
    )
    print(
        "By artifact type: "
        f"{corpus['tokens_by_artifact_type']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
