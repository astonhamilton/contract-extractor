from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.pdf_pages import (
    build_normalization_report,
    normalize_all_documents,
    write_normalization_report,
)


def main() -> None:
    """Normalize all inventoried PDFs into page-level text artifacts."""
    configure_logging()
    print("Starting text normalization stage.")
    print("This is the first normalization pass over inventoried PDFs.")
    print("It extracts page-level text, writes page .txt artifacts, and sets quality flags for later fallback stages.")

    manifests = normalize_all_documents(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
    )
    report = build_normalization_report(manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "normalization_report.json"
    write_normalization_report(report_path, report)

    print(
        "Normalization complete: "
        f"{report['total_documents']} documents | "
        f"completed={report['completed_documents']} | "
        f"failed={report['failed_documents']} | "
        f"ocr_recommended={report['ocr_recommended_documents']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
