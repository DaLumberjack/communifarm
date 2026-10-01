"""Communifarm SQLite weight_events tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import DOMAIN, SERVICE_RECORD_WEIGHT
from custom_components.communifarm.domain.weight import (
    WeightEvent,
    ingredient_key_from_label,
)
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.batch_repository import BatchRepository
from custom_components.communifarm.storage.weight_repository import WeightEventRepository


def test_ingredient_key_slug() -> None:
    assert ingredient_key_from_label("hardwood pellets") == "hardwood_pellets"


def test_sqlite_migration_creates_weight_events(tmp_path: Path) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='weight_events'"
    ).fetchone()
    assert row is not None
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert str(mode).lower() == "wal"
    conn.close()


def test_db_lock_is_reentrant() -> None:
    with sqlite_db.DB_LOCK:
        with sqlite_db.DB_LOCK:
            assert True


@pytest.mark.asyncio
async def test_weight_repository_roundtrip(hass: HomeAssistant, tmp_path: Path) -> None:
    repo = WeightEventRepository(hass, path=tmp_path / "communifarm.db")
    await repo.async_setup()
    event = WeightEvent(
        site_id="site_a",
        environment_id="env_a",
        batch_id="batch_a",
        mass_g=3000.0,
        ingredient_label="hardwood pellets",
        ingredient_key="hardwood_pellets",
        recorded_at="2026-09-27T12:00:00+00:00",
        source_entity_id="sensor.esp32dev_calibrated_g",
        nfc_uid="nfc-hardwood-pellets",
    )
    await repo.async_insert(event)
    rows = await repo.async_list_for_batch("batch_a")
    assert len(rows) == 1
    assert rows[0].mass_g == 3000.0
    assert rows[0].ingredient_key == "hardwood_pellets"
    await repo.async_close()


@pytest.mark.asyncio
async def test_record_weight_service_persists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    hass.states.async_set("sensor.esp32dev_calibrated_g", "199.5")
    hass.states.async_set("input_select.esp32dev_selected_ingredient", "gypsum")
    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "nfc-gypsum")

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # C5: mark tare before first record so happy path is clean.
    hass.data[DOMAIN][mock_config_entry.entry_id]["weigh_session"]["tare_seen"] = True

    await hass.services.async_call(DOMAIN, SERVICE_RECORD_WEIGHT, {}, blocking=True)
    await hass.async_block_till_done()

    weight_repo: WeightEventRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "weight_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    rows = await weight_repo.async_list_for_batch(state.batch.id)
    assert len(rows) == 1
    assert rows[0].mass_g == 199.5
    assert rows[0].ingredient_label == "gypsum"
    assert rows[0].nfc_uid == "nfc-gypsum"
    assert rows[0].recipe_scale == 1.0
    assert rows[0].target_amount == 200.0  # wood-lover gypsum @ 1×

    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    master = await batch_repo.async_get_batch(state.batch.id)
    assert master is not None
    assert master.recipe_scale == 1.0
    assert master.lifecycle_phase in {"dry_mixing", "planned"}

    # Mixing table columns exist for scale + target
    path = batch_repo._path
    import sqlite3

    conn = sqlite3.connect(path)
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(weight_events)").fetchall()
    }
    assert "recipe_scale" in cols
    assert "target_amount" in cols
    batch_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(batches)").fetchall()
    }
    assert "recipe_scale" in batch_cols
    assert "lifecycle_phase" in batch_cols
    conn.close()

    session = hass.states.get("sensor.communifarm_weigh_session")
    assert session is not None
    assert session.state == "1/9 lines recorded"
    assert "gypsum" in session.attributes["progress_text"]
    assert session.attributes.get("warnings") == []


@pytest.mark.asyncio
async def test_record_weight_rejects_negative_mass(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from homeassistant.exceptions import HomeAssistantError

    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_neg.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError, match="negative"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RECORD_WEIGHT,
            {"mass_g": -5.0, "ingredient": "gypsum", "nfc_uid": "nfc-gypsum"},
            blocking=True,
        )

    weight_repo: WeightEventRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "weight_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    rows = await weight_repo.async_list_for_batch(state.batch.id)
    assert rows == []
    session = hass.states.get("sensor.communifarm_weigh_session")
    assert session is not None
    assert "negative" in (session.attributes.get("last_reject") or "")


@pytest.mark.asyncio
async def test_record_weight_warns_over_capacity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.communifarm.domain.validation import (
        BENCH_CAPACITY_G,
        WARNING_OVER_CAPACITY,
    )

    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_cap.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    hass.data[DOMAIN][mock_config_entry.entry_id]["weigh_session"]["tare_seen"] = True

    mass = BENCH_CAPACITY_G + 500.0
    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_WEIGHT,
        {"mass_g": mass, "ingredient": "gypsum", "nfc_uid": "nfc-gypsum"},
        blocking=True,
    )
    await hass.async_block_till_done()

    weight_repo: WeightEventRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "weight_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    rows = await weight_repo.async_list_for_batch(state.batch.id)
    assert len(rows) == 1
    assert rows[0].mass_g == mass
    session = hass.states.get("sensor.communifarm_weigh_session")
    assert WARNING_OVER_CAPACITY in session.attributes["warnings"]


@pytest.mark.asyncio
async def test_record_weight_warns_missing_nfc(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.communifarm.domain.validation import WARNING_MISSING_NFC

    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_nfc.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    hass.states.async_set("sensor.esp32dev_calibrated_g", "200")
    hass.states.async_set("input_select.esp32dev_selected_ingredient", "gypsum")
    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    hass.data[DOMAIN][mock_config_entry.entry_id]["weigh_session"]["tare_seen"] = True

    await hass.services.async_call(DOMAIN, SERVICE_RECORD_WEIGHT, {}, blocking=True)
    await hass.async_block_till_done()

    session = hass.states.get("sensor.communifarm_weigh_session")
    assert WARNING_MISSING_NFC in session.attributes["warnings"]


@pytest.mark.asyncio
async def test_environment_status_degraded_on_bad_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.communifarm.domain.validation import WARNING_TEMP_OUT_OF_RANGE

    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_env.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    hass.states.async_set("sensor.mock_temperature", "125")
    hass.states.async_set("sensor.mock_humidity", "55")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    status = hass.states.get("sensor.communifarm_environment_status")
    assert status is not None
    assert status.state == "degraded"
    assert WARNING_TEMP_OUT_OF_RANGE in status.attributes["warnings"]

