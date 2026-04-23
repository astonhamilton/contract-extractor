from __future__ import annotations

import logging

from packages.data_store.connect import SqliteDb
from packages.data_store.migrations import apply_pending_migrations, current_schema_version


LOGGER = logging.getLogger(__name__)


def ensure_app_db_schema(db: SqliteDb) -> list[str]:
    """Ensure the shared app DB file exists and all pending migrations are applied.

    This is intentionally limited to lightweight schema bootstrapping:
    - create the SQLite file and parent directory if missing
    - apply pending SQL migrations

    It does not load or rebuild corpus data. That remains an explicit operational
    action outside API startup.
    """

    with db.connect() as connection:
        applied = apply_pending_migrations(connection)
        version = current_schema_version(connection)
    if applied:
        LOGGER.info(
            "Applied app DB migrations count=%s current_version=%s",
            len(applied),
            version,
        )
    else:
        LOGGER.info("App DB schema already current version=%s", version)
    return applied
