from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from sqlite3 import Connection


class SqliteDb:
    """Thin application-facing handle for one SQLite database."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> Iterator[Connection]:
        """Yield a fresh configured SQLite connection."""
        return sqlite_connection(self.path)

    def exists(self) -> bool:
        """Return whether the backing SQLite file exists."""
        return self.path.exists()


def default_db_path(repo_root: Path) -> Path:
    """Return the default SQLite path for the app DB."""
    return repo_root / "data" / "app" / "app.db"


def sqlite_db(db_path: Path) -> SqliteDb:
    """Return a thin DB handle for one SQLite path."""
    return SqliteDb(db_path)


def default_db(repo_root: Path) -> SqliteDb:
    """Return the default app DB handle."""
    return sqlite_db(default_db_path(repo_root))


def ensure_db_parent_dir(db_path: Path) -> None:
    """Create the parent directory for a SQLite database path when needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with the repo's default connection settings."""
    ensure_db_parent_dir(db_path)
    connection = sqlite3.connect(db_path, check_same_thread=False, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA busy_timeout = 5000;")
    connection.execute("PRAGMA synchronous = NORMAL;")
    connection.execute("PRAGMA temp_store = MEMORY;")
    return connection


def sqlite_database_path(connection: sqlite3.Connection) -> Path:
    """Return the filesystem path backing the main SQLite database connection."""
    row = connection.execute("PRAGMA database_list;").fetchone()
    if row is None:
        raise ValueError("Unable to determine SQLite database path.")
    return Path(str(row["file"]))


@contextmanager
def sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection and close it on exit."""
    connection = connect_sqlite(db_path)
    try:
        yield connection
    finally:
        connection.close()

@contextmanager
def sqlite_transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block inside a transaction, using a savepoint when already in one."""
    if connection.in_transaction:
        savepoint_name = "sp_runtime_txn"
        try:
            connection.execute(f"SAVEPOINT {savepoint_name}")
            yield connection
        except Exception:
            connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            connection.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            raise
        else:
            connection.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        return

    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
