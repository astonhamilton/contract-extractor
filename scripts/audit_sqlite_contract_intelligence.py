from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.data_store import default_db_path, sqlite_connection
from packages.pipeline.contract_intelligence_db.audit import (
    audit_sqlite_load,
    write_sqlite_audit_report,
)
from packages.pipeline.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for auditing the SQLite contract-intelligence DB."""
    parser = argparse.ArgumentParser(
        description="Audit a loaded SQLite contract-intelligence DB against canonical repo artifacts."
    )
    parser.add_argument(
        "--db-path",
        default=str(default_db_path(REPO_ROOT)),
        help="SQLite DB path to audit. Defaults to data/app/app.db.",
    )
    parser.add_argument(
        "--doc-id",
        action="append",
        dest="doc_ids",
        help="Limit the audit to one or more doc ids. Can be provided multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    """Audit SQLite load completeness against canonical manifests and derived artifacts."""
    configure_logging()
    args = parse_args()
    db_path = Path(args.db_path)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "sqlite_contract_intelligence_audit_report.json"

    print("Starting SQLite contract-intelligence audit.")
    print(f"DB path: {db_path}")
    if args.doc_ids:
        print(f"Selection: {len(args.doc_ids)} doc ids")
    else:
        print("Selection: all canonical manifests")

    with sqlite_connection(db_path) as connection:
        report = audit_sqlite_load(
            connection,
            REPO_ROOT,
            doc_ids=args.doc_ids,
        )

    write_sqlite_audit_report(report_path, report)
    print(
        "SQLite audit complete: "
        f"audited={report['documents_audited']} | "
        f"ok={report['documents_ok']} | "
        f"issues={report['documents_with_issues']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
