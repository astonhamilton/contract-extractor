from __future__ import annotations

import argparse
from time import perf_counter
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.data_store import default_db_path, sqlite_connection, sqlite_transaction
from packages.data_store.migrations import (
    apply_pending_migrations,
    current_schema_version,
    pending_migration_paths,
)
from packages.pipeline.contract_intelligence_db.loaders import (
    load_canonical_manifests,
    loader_steps,
)
from packages.pipeline.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for building the SQLite contract-intelligence DB."""
    parser = argparse.ArgumentParser(
        description="Create/update the SQLite contract-intelligence DB from canonical manifests and derived artifacts."
    )
    parser.add_argument(
        "--db-path",
        default=str(default_db_path(REPO_ROOT)),
        help="SQLite DB output path. Defaults to data/app/app.db.",
    )
    parser.add_argument(
        "--init-only",
        action="store_true",
        help="Create the DB and apply pending migrations, but do not load any data.",
    )
    parser.add_argument(
        "--doc-id",
        action="append",
        dest="doc_ids",
        help="Limit loading to one or more doc ids. Can be provided multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    """Create/update the SQLite DB, apply pending migrations, and load canonical artifacts."""
    configure_logging()
    args = parse_args()
    db_path = Path(args.db_path)
    started_at = perf_counter()

    print("Starting SQLite contract-intelligence load.")
    print(f"DB path: {db_path}")
    if args.init_only:
        print("Mode: init-only")
    elif args.doc_ids:
        print(f"Selection: {len(args.doc_ids)} doc ids")
    else:
        print("Selection: all canonical manifests")

    with sqlite_connection(db_path) as connection:
        pending_before = [path.name for path in pending_migration_paths(connection)]
        with sqlite_transaction(connection):
            applied = apply_pending_migrations(connection)
        print(
            "Migrations: "
            f"pending_before={len(pending_before)} | "
            f"applied={len(applied)} | "
            f"current={current_schema_version(connection)}"
        )

        if args.init_only:
            print("Schema init complete.")
            return

        manifests = load_canonical_manifests(REPO_ROOT, doc_ids=args.doc_ids)
        print(f"Manifests selected: {len(manifests)}")

        counts: dict[str, int] = {}
        with sqlite_transaction(connection):
            for name, loader in loader_steps():
                loader_started_at = perf_counter()
                print(f"{name}: start")
                counts[name] = loader(connection, REPO_ROOT, manifests)
                elapsed = perf_counter() - loader_started_at
                print(f"{name}: loaded={counts[name]} | elapsed={elapsed:.2f}s")

    formatted_counts = " | ".join(f"{name}={count}" for name, count in counts.items())
    total_elapsed = perf_counter() - started_at
    print(f"Load complete: {formatted_counts} | elapsed={total_elapsed:.2f}s")


if __name__ == "__main__":
    main()
