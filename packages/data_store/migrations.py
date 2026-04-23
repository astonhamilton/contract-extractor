from __future__ import annotations

import sqlite3
from pathlib import Path


def data_store_root() -> Path:
    """Return the root directory for data-store packages."""
    return Path(__file__).resolve().parent


def schema_dirs() -> list[Path]:
    """Return schema directories that contribute to the shared SQLite DB."""
    root = data_store_root()
    return [
        root / "contract_intelligence" / "schema",
        root / "llm_agent_runtime" / "schema",
    ]


def migration_paths() -> list[Path]:
    """Return ordered SQL migration files for the shared app DB."""
    paths: list[Path] = []
    for schema_dir in schema_dirs():
        paths.extend(sorted(schema_dir.glob("[0-9][0-9][0-9]_*.sql")))
    return paths


def ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    """Ensure the migration ledger table exists before reading/applying versions."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def migration_version(path: Path) -> str:
    """Return the migration version stored in the ledger."""
    return str(path.relative_to(data_store_root()))


def applied_migration_versions(connection: sqlite3.Connection) -> set[str]:
    """Return the set of migration versions already applied to the database."""
    ensure_schema_migrations_table(connection)
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {str(row["version"]) for row in rows}


def pending_migration_paths(connection: sqlite3.Connection) -> list[Path]:
    """Return migrations that still need to be applied."""
    applied = applied_migration_versions(connection)
    return [path for path in migration_paths() if migration_version(path) not in applied]


def apply_migration(connection: sqlite3.Connection, path: Path) -> str:
    """Apply one SQL migration file and record it in the ledger."""
    ensure_schema_migrations_table(connection)
    version = migration_version(path)
    sql = path.read_text(encoding="utf-8")
    connection.executescript(sql)
    connection.execute(
        "INSERT INTO schema_migrations (version) VALUES (?)",
        (version,),
    )
    return version


def apply_pending_migrations(connection: sqlite3.Connection) -> list[str]:
    """Apply all pending SQL migrations in order and return their versions."""
    applied_versions: list[str] = []
    for path in pending_migration_paths(connection):
        applied_versions.append(apply_migration(connection, path))
    return applied_versions


def current_schema_version(connection: sqlite3.Connection) -> str | None:
    """Return the most recently applied migration version in path order."""
    applied = applied_migration_versions(connection)
    ordered = [migration_version(path) for path in migration_paths() if migration_version(path) in applied]
    return ordered[-1] if ordered else None
