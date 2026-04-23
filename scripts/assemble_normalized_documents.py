from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.assemble_normalized_document import (
    assemble_all_normalized_documents,
    build_assembled_documents_report,
    write_assembled_documents_report,
)


def main() -> None:
    """Assemble canonical normalized documents from best available page representations."""
    configure_logging()
    print("Starting normalized document assembly stage.")
    print("This writes one canonical normalized XML document per manifest using the best available page representation.")

    manifests = assemble_all_normalized_documents(
        repo_root=REPO_ROOT,
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
    )
    report = build_assembled_documents_report(manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "assembled_documents_report.json"
    write_assembled_documents_report(report_path, report)

    print(
        "Normalized document assembly complete: "
        f"docs={report['documents_total']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
