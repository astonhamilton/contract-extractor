from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence


def parse_json_text(value: object) -> object:
    """Parse a SQLite JSON-text column into a Python value."""
    if value is None:
        return None
    if isinstance(value, (list, dict, int, float, bool)):
        return value
    text = str(value).strip()
    if not text:
        return None
    return json.loads(text)


def parse_json_list(value: object) -> list[object]:
    """Parse a SQLite JSON-text list column into a Python list."""
    parsed = parse_json_text(value)
    if isinstance(parsed, list):
        return parsed
    return []


def parse_optional_bool(value: object) -> bool | None:
    """Convert SQLite integer/bool-ish values into Python bools."""
    if value is None:
        return None
    return bool(int(value))


def where_in_clause(column: str, values: Sequence[object]) -> tuple[str, list[object]]:
    """Build a parameterized IN clause for a trusted column name."""
    if not values:
        return "1 = 0", []
    placeholders = ", ".join("?" for _ in values)
    return f"{column} IN ({placeholders})", list(values)


def fetchall(connection: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> list[sqlite3.Row]:
    """Execute a SELECT query and return all rows."""
    return list(connection.execute(sql, tuple(params)).fetchall())


def fetchone(connection: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> sqlite3.Row | None:
    """Execute a SELECT query and return one row."""
    return connection.execute(sql, tuple(params)).fetchone()
