"""Communifarm SQLite database bootstrap and migrations."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

SCHEMA_VERSION = 10

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
    7: """
    CREATE TABLE IF NOT EXISTS placement_areas (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      site_id TEXT NOT NULL,
      name TEXT NOT NULL,
      area_kind TEXT NOT NULL,
      slot_kind TEXT NOT NULL,
      slot_count INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_placement_areas_site
      ON placement_areas (site_id, area_kind);

    CREATE TABLE IF NOT EXISTS zones (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      area_id TEXT NOT NULL,
      site_id TEXT NOT NULL,
      name TEXT NOT NULL,
      slot_kind TEXT NOT NULL,
      slot_index INTEGER NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_zones_area
      ON zones (area_id, slot_index);
    CREATE INDEX IF NOT EXISTS idx_zones_site
      ON zones (site_id, area_id);

    ALTER TABLE batches ADD COLUMN zone_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_batches_zone
      ON batches (zone_id);

    ALTER TABLE harvest_events ADD COLUMN zone_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_harvest_events_zone
      ON harvest_events (zone_id);
    """,
    8: """
    ALTER TABLE culture_lots ADD COLUMN zone_id TEXT;
    ALTER TABLE media_batches ADD COLUMN zone_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_culture_lots_zone
      ON culture_lots (zone_id);
    CREATE INDEX IF NOT EXISTS idx_media_batches_zone
      ON media_batches (zone_id);
    """,
    9: """
    CREATE TABLE IF NOT EXISTS production_containers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      batch_id TEXT NOT NULL,
      container_index INTEGER NOT NULL,
      container_type TEXT NOT NULL,
      nfc_uid TEXT NOT NULL UNIQUE,
      lifecycle_phase TEXT NOT NULL,
      flush_count INTEGER NOT NULL DEFAULT 0,
      max_flushes INTEGER NOT NULL DEFAULT 3,
      zone_id TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL,
      completed_at TEXT,
      notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_production_containers_batch
      ON production_containers (batch_id, container_index);
    CREATE INDEX IF NOT EXISTS idx_production_containers_nfc
      ON production_containers (nfc_uid);
    CREATE INDEX IF NOT EXISTS idx_production_containers_zone
      ON production_containers (zone_id);
    CREATE INDEX IF NOT EXISTS idx_production_containers_status
      ON production_containers (status, lifecycle_phase);

    ALTER TABLE harvest_events ADD COLUMN container_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_harvest_events_container
      ON harvest_events (container_id, recorded_at);

    CREATE TABLE IF NOT EXISTS nfc_checkins (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      nfc_uid TEXT NOT NULL,
      object_type TEXT NOT NULL,
      object_id TEXT NOT NULL,
      activity TEXT NOT NULL,
      zone_id TEXT,
      detail TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_nfc_checkins_nfc_time
      ON nfc_checkins (nfc_uid, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_nfc_checkins_object
      ON nfc_checkins (object_type, object_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_nfc_checkins_activity
      ON nfc_checkins (activity, recorded_at);

    CREATE TABLE IF NOT EXISTS sale_packs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      harvest_id TEXT NOT NULL,
      mass_g REAL NOT NULL,
      size_label TEXT,
      zone_id TEXT,
      status TEXT NOT NULL DEFAULT 'open',
      created_at TEXT NOT NULL,
      notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_sale_packs_harvest
      ON sale_packs (harvest_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_sale_packs_zone
      ON sale_packs (zone_id);
    """,
    10: """
    CREATE TABLE IF NOT EXISTS sales (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      venue_label TEXT NOT NULL,
      buyer_label TEXT NOT NULL,
      payment_method TEXT NOT NULL,
      currency TEXT NOT NULL DEFAULT 'USD',
      total_amount REAL NOT NULL,
      sold_at TEXT NOT NULL,
      notes TEXT,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_sales_sold_at
      ON sales (sold_at);
    CREATE INDEX IF NOT EXISTS idx_sales_payment
      ON sales (payment_method, sold_at);

    CREATE TABLE IF NOT EXISTS sale_line_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      sale_id TEXT NOT NULL,
      sale_pack_id TEXT NOT NULL,
      batch_id TEXT NOT NULL,
      harvest_id TEXT NOT NULL,
      product_label TEXT NOT NULL,
      mass_g REAL NOT NULL,
      unit_price REAL,
      line_amount REAL NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_sale_line_items_sale
      ON sale_line_items (sale_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_sale_line_items_batch
      ON sale_line_items (batch_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_sale_line_items_pack
      ON sale_line_items (sale_pack_id);

    CREATE TABLE IF NOT EXISTS sale_cleanup_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stable_id TEXT NOT NULL UNIQUE,
      sale_id TEXT,
      sale_day TEXT,
      checklist_json TEXT NOT NULL DEFAULT '{}',
      notes TEXT,
      recorded_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_sale_cleanup_sale
      ON sale_cleanup_events (sale_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_sale_cleanup_day
      ON sale_cleanup_events (sale_day, recorded_at);

    ALTER TABLE sale_packs ADD COLUMN sold_sale_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_sale_packs_sold_sale
      ON sale_packs (sold_sale_id);
    CREATE INDEX IF NOT EXISTS idx_sale_packs_status
      ON sale_packs (status, created_at);
    """,
}


def db_path_for_config_dir(config_dir: str | Path) -> Path:
    """Return path to communifarm/communifarm.db under the HA config directory."""
    root = Path(config_dir) / "communifarm"
    root.mkdir(parents=True, exist_ok=True)
    return root / "communifarm.db"


# Serializes all Communifarm SQLite work across repos/threads.
# Multiple connections to one file + HA's executor pool otherwise race into
# ``database is locked`` / ``InterfaceError`` (pysqlite is not multi-thread
# friendly without an external mutex).
DB_LOCK = threading.RLock()


def connect(path: Path) -> sqlite3.Connection:
    """Open Communifarm SQLite with WAL + busy timeout.

    Callers that touch the DB from HA executor jobs must hold :data:`DB_LOCK`
    for the whole sync operation (see repository ``_locked`` helpers).
    """
    conn = sqlite3.connect(
        path,
        check_same_thread=False,
        timeout=30.0,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
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
