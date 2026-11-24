"""Accès à la base SQLite et migrations versionnées."""
from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path

MIGRATIONS_PKG = "companion.migrations"


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    return conn


def _migration_files() -> list[tuple[int, str, str]]:
    files = []
    for f in resources.files(MIGRATIONS_PKG).iterdir():
        if f.name.endswith(".sql"):
            version = int(f.name.split("_", 1)[0])
            files.append((version, f.name, f.read_text(encoding="utf-8")))
    return sorted(files)


def migrate(conn: sqlite3.Connection) -> int:
    """Applique les migrations manquantes. Retourne la version finale."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, name TEXT)")
    done = {r[0] for r in conn.execute("SELECT version FROM schema_version")}
    for version, name, sql in _migration_files():
        if version in done:
            continue
        with conn:
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_version VALUES (?, ?)", (version, name))
    return conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]
