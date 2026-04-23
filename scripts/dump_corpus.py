"""Dump the full assistant corpus index to CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.app_services.corpus.assistant_index import get_corpus_index
from packages.data_store.connect import default_db_path, sqlite_db
from packages.data_store.migrations import apply_pending_migrations


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the corpus dump script."""
    parser = argparse.ArgumentParser(
        description="Dump the full assistant corpus index to CSV.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=default_db_path(REPO_ROOT),
        help="SQLite database path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "data" / "sampled" / "corpus_index_dump.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the CSV payload to stdout instead of writing a file.",
    )
    return parser.parse_args()


CSV_COLUMNS = [
    "doc_id",
    "source_filename",
    "page_count",
    "buyer",
    "seller",
    "what_is_being_bought",
    "procurement_category",
    "procurement_stage",
    "primary_document_role",
    "change_kind",
    "document_map_type",
    "has_governing_notes",
    "has_change_notes",
    "has_page_notes",
    "governing_summary",
    "change_summary",
]


def _csv_row(item: object) -> dict[str, object]:
    """Return one flat CSV row for a corpus index item."""
    payload = item.model_dump(mode="json")
    return {
        "doc_id": payload["doc_id"],
        "source_filename": payload["source_filename"],
        "page_count": payload["page_count"],
        "buyer": payload.get("buyer") or "",
        "seller": payload.get("seller") or "",
        "what_is_being_bought": payload.get("what_is_being_bought") or "",
        "procurement_category": payload.get("procurement_category") or "",
        "procurement_stage": payload.get("procurement_stage") or "",
        "primary_document_role": payload.get("primary_document_role") or "",
        "change_kind": payload.get("change_kind") or "",
        "document_map_type": payload.get("document_map_type") or "",
        "has_governing_notes": payload.get("has_governing_notes", False),
        "has_change_notes": payload.get("has_change_notes", False),
        "has_page_notes": payload.get("has_page_notes", False),
        "governing_summary": payload.get("governing_summary") or "",
        "change_summary": payload.get("change_summary") or "",
    }


def main() -> int:
    """Load the full assistant corpus index and dump it to CSV."""
    args = parse_args()
    db = sqlite_db(args.db_path)
    with db.connect() as connection:
        apply_pending_migrations(connection)
        connection.commit()

    items = get_corpus_index(db)
    if args.stdout:
        writer = csv.DictWriter(sys.stdout, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for item in items:
            writer.writerow(_csv_row(item))
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for item in items:
            writer.writerow(_csv_row(item))
    try:
        display_path = str(args.output.relative_to(REPO_ROOT))
    except ValueError:
        display_path = str(args.output)
    print(f"Wrote corpus dump to {display_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
