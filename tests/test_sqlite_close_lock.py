"""SQLite close must hold DB_LOCK — concurrent close+query segfaults (CI 139)."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant

from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.batch_repository import BatchRepository


@pytest.mark.asyncio
async def test_close_serializes_against_in_flight_query(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """Close under lock: overlapping query + close must not crash the interpreter."""
    path = tmp_path / "communifarm_close_lock.db"
    repo = BatchRepository(hass, path)
    await repo.async_setup()
    assert repo._conn is not None

    hold = threading.Event()
    release = threading.Event()
    errors: list[BaseException] = []

    def slow_query() -> None:
        try:

            def _query() -> None:
                hold.set()
                release.wait(timeout=5)
                assert repo._conn is not None
                repo._conn.execute("SELECT COUNT(*) FROM batches").fetchone()

            repo._locked(_query)
        except BaseException as err:  # noqa: BLE001 — capture for main thread
            errors.append(err)

    with ThreadPoolExecutor(max_workers=2) as pool:
        query_fut = pool.submit(slow_query)
        assert hold.wait(timeout=5)
        close_fut = pool.submit(repo._locked, repo._close_sync)
        release.set()
        query_fut.result(timeout=10)
        close_fut.result(timeout=10)

    assert errors == []
    assert repo._conn is None


def test_migration_v18_to_v19_adds_scan_events_without_data_loss(tmp_path: Path) -> None:
    """Upgrade path: pool rows survive; scan_events + bound_object_type appear."""
    path = tmp_path / "communifarm_v18_upgrade.db"
    conn = sqlite_db.connect(path)
    for version in sorted(v for v in sqlite_db.MIGRATIONS if v <= 18):
        conn.executescript(sqlite_db.MIGRATIONS[version])
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) "
            "VALUES (?, datetime('now'))",
            (version,),
        )
    conn.commit()
    conn.execute(
        """
        INSERT INTO nfc_tag_pool (
          stable_id, site_id, nfc_uid, intended_type, label,
          status, created_at
        ) VALUES (
          'ntag_keep', 'site_test', 'nfc-keep-uid', 'inventory', 'keep me',
          'available', '2026-01-01T00:00:00+00:00'
        )
        """
    )
    conn.commit()
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    assert version >= 19
    row = conn.execute(
        "SELECT nfc_uid, label, bound_object_type FROM nfc_tag_pool "
        "WHERE stable_id = ?",
        ("ntag_keep",),
    ).fetchone()
    assert row["nfc_uid"] == "nfc-keep-uid"
    assert row["label"] == "keep me"
    assert row["bound_object_type"] is None
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "nfc_scan_events" in tables
    conn.close()
