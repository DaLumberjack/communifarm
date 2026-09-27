"""Communifarm SQLite database bootstrap and migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

MIGRATIONS: dict[int, str] = {
    1: """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS weight_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      site_id TEXT NOT NULL,
      environment_id TEXT NOT NULL,
      batch_id TEXT,
      ingredient_key TEXT,
      ingredient_label TEXT,
      mass_g REAL NOT NULL,
      unit TEXT NOT NULL DEFAULT 'g',
      source_entity_id TEXT,
      nfc_uid TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_weight_events_batch_time
      ON weight_events (batch_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_weight_events_env_time
      ON weight_events (environment_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_weight_events_ingredient
      ON weight_events (ingredient_key, recorded_at);
    """
}


def db_path_for_config_dir(config_dir: str | Path) -> Path:
    """Return path to communifarm/communifarm.db under the HA config directory."""
    root = Path(config_dir) / "communifarm"
    root.mkdir(parents=True, exist_ok=True)
    return root / "communifarm.db"


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply pending migrations; return current schema version."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
    current = int(row["v"] if row else 0)
    for version in sorted(MIGRATIONS):
        if version <= current:
            continue
        conn.executescript(MIGRATIONS[version])
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, datetime('now'))",
            (version,),
        )
        conn.commit()
        current = version
    return current
