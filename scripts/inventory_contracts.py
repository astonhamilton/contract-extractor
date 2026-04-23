from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.ingest.inventory import InventoryPaths, inventory_contracts


def main() -> None:
    """Run the raw PDF inventory stage."""
    configure_logging()
    paths = InventoryPaths(
        repo_root=REPO_ROOT,
        raw_contracts_dir=REPO_ROOT / "data" / "raw" / "contracts",
        processed_contracts_dir=REPO_ROOT / "data" / "processed" / "contracts",
        documents_index_path=REPO_ROOT / "data" / "processed" / "indexes" / "documents.jsonl",
    )

    records = inventory_contracts(paths)
    print(f"Inventory complete: {len(records)} documents")


if __name__ == "__main__":
    main()
