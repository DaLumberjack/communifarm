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
    conn.close()


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
