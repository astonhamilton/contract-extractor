from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.failed_pdf_render import (
    build_failed_pdf_render_report,
    write_failed_pdf_render_report,
)


def main() -> None:
    """Check whether failed PDFs can still be rendered to preview PNGs."""
    configure_logging()
    print("Starting failed PDF render check.")
    print("This tries to render page 1 of each failed PDF into sampled preview space.")
    print("If rendering works, the file is likely salvageable via image-first repair.")

    report = build_failed_pdf_render_report(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
    )
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "failed_pdf_render_report.json"
    write_failed_pdf_render_report(report_path, report)

    print(
        "Failed PDF render check complete: "
        f"failed_docs={report['failed_document_count']} | "
        f"renderable={report['renderable_count']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
