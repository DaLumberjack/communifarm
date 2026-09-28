"""Communifarm SQLite database bootstrap and migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 6

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
    """,
    2: """
    ALTER TABLE weight_events ADD COLUMN recipe_scale REAL;
    ALTER TABLE weight_events ADD COLUMN target_amount REAL;
    """,
    3: """
    CREATE TABLE IF NOT EXISTS batches (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      site_id TEXT NOT NULL,
      environment_id TEXT NOT NULL,
      name TEXT NOT NULL,
      nfc_uid TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      completed_at TEXT,
      mixing_started_at TEXT,
      mixing_finished_at TEXT,
      container_count INTEGER,
      notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_batches_status_created
      ON batches (status, created_at);

    CREATE TABLE IF NOT EXISTS batch_milestones (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      batch_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      detail TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_batch_milestones_batch_time
      ON batch_milestones (batch_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_batch_milestones_type
      ON batch_milestones (event_type, recorded_at);
    """,
    4: """
    ALTER TABLE batches ADD COLUMN recipe_scale REAL DEFAULT 1.0;
    ALTER TABLE batches ADD COLUMN lifecycle_phase TEXT DEFAULT 'planned';
    ALTER TABLE batches ADD COLUMN recipe_key TEXT DEFAULT 'wood_lover';

    CREATE INDEX IF NOT EXISTS idx_batches_lifecycle_phase
      ON batches (lifecycle_phase, created_at);
    CREATE INDEX IF NOT EXISTS idx_weight_events_batch_ingredient
      ON weight_events (batch_id, ingredient_key, recorded_at);
    """,
    5: """
    CREATE TABLE IF NOT EXISTS culture_lots (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      site_id TEXT NOT NULL,
      environment_id TEXT NOT NULL,
      name TEXT NOT NULL,
      source_type TEXT NOT NULL,
      form TEXT NOT NULL,
      container TEXT NOT NULL,
      strain_label TEXT,
      parent_culture_id TEXT,
      status TEXT NOT NULL,
      acquired_at TEXT,
      created_at TEXT NOT NULL,
      nfc_uid TEXT,
      notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_culture_lots_status
      ON culture_lots (status, created_at);
    CREATE INDEX IF NOT EXISTS idx_culture_lots_parent
      ON culture_lots (parent_culture_id);

    CREATE TABLE IF NOT EXISTS media_batches (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      site_id TEXT NOT NULL,
      environment_id TEXT NOT NULL,
      name TEXT NOT NULL,
      recipe_key TEXT NOT NULL,
      media_form TEXT NOT NULL,
      vessel_type TEXT NOT NULL,
      recipe_scale REAL NOT NULL DEFAULT 1.0,
      status TEXT NOT NULL,
      vessel_count INTEGER,
      sterilized_at TEXT,
      ready_at TEXT,
      created_at TEXT NOT NULL,
      nfc_uid TEXT,
      notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_media_batches_status
      ON media_batches (status, created_at);
    CREATE INDEX IF NOT EXISTS idx_media_batches_recipe
      ON media_batches (recipe_key, created_at);

    CREATE TABLE IF NOT EXISTS media_weight_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      site_id TEXT NOT NULL,
      environment_id TEXT NOT NULL,
      media_batch_id TEXT NOT NULL,
      ingredient_key TEXT,
      ingredient_label TEXT,
      amount REAL NOT NULL,
      unit TEXT NOT NULL,
      recipe_scale REAL,
      target_amount REAL,
      source_entity_id TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_media_weight_batch_time
      ON media_weight_events (media_batch_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_media_weight_ingredient
      ON media_weight_events (ingredient_key, recorded_at);

    CREATE TABLE IF NOT EXISTS media_milestones (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      media_batch_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      detail TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_media_milestones_batch_time
      ON media_milestones (media_batch_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_media_milestones_type
      ON media_milestones (event_type, recorded_at);

    CREATE TABLE IF NOT EXISTS culture_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      event_type TEXT NOT NULL,
      culture_id TEXT,
      child_culture_id TEXT,
      media_batch_id TEXT,
      detail TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_culture_events_culture_time
      ON culture_events (culture_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_culture_events_media_time
      ON culture_events (media_batch_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_culture_events_type
      ON culture_events (event_type, recorded_at);
    """,
    6: """
    ALTER TABLE batches ADD COLUMN culture_id TEXT;
    ALTER TABLE batches ADD COLUMN container_type TEXT;
    ALTER TABLE batches ADD COLUMN substrate_g_per_container REAL;
    ALTER TABLE batches ADD COLUMN inoculum_amount REAL;
    ALTER TABLE batches ADD COLUMN inoculum_unit TEXT;
    ALTER TABLE batches ADD COLUMN expected_check_at TEXT;
    ALTER TABLE batches ADD COLUMN flush_count INTEGER DEFAULT 0;
    ALTER TABLE batches ADD COLUMN max_flushes INTEGER DEFAULT 3;
    ALTER TABLE batches ADD COLUMN inoculated_at TEXT;

    CREATE INDEX IF NOT EXISTS idx_batches_culture
      ON batches (culture_id, inoculated_at);

    CREATE TABLE IF NOT EXISTS harvest_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      batch_id TEXT NOT NULL,
      flush_number INTEGER NOT NULL,
      mass_g REAL NOT NULL,
      is_final INTEGER NOT NULL DEFAULT 0,
      notes TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_harvest_events_batch_time
      ON harvest_events (batch_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_harvest_events_flush
      ON harvest_events (batch_id, flush_number);

    ALTER TABLE culture_events ADD COLUMN batch_id TEXT;

    CREATE INDEX IF NOT EXISTS idx_culture_events_batch_time
      ON culture_events (batch_id, recorded_at);
    """,
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
