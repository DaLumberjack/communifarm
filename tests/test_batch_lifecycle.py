"""Batch SQLite milestones + complete/new batch tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_COMPLETE_AND_NEW_BATCH,
    SERVICE_RECORD_BATCH_MILESTONE,
    SERVICE_RECORD_WEIGHT,
)
from custom_components.communifarm.domain.batch_milestones import (
    MILESTONE_DRY_MIXING_STARTED,
    MILESTONE_WATER_ADDED,
)
from custom_components.communifarm.storage.batch_repository import BatchRepository


@pytest.mark.asyncio
async def test_first_weight_auto_starts_dry_mixing(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_batch.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    hass.data[DOMAIN][mock_config_entry.entry_id]["weigh_session"]["tare_seen"] = True

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_WEIGHT,
        {"mass_g": 200.0, "ingredient": "gypsum", "nfc_uid": "nfc-gypsum"},
        blocking=True,
    )
    await hass.async_block_till_done()

    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    assert await batch_repo.async_has_milestone(
        state.batch.id, MILESTONE_DRY_MIXING_STARTED
    )
    record = await batch_repo.async_get_batch(state.batch.id)
    assert record is not None
    assert record.mixing_started_at is not None


@pytest.mark.asyncio
async def test_weigh_milestone_and_complete_new_batch(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_batch2.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    old_id = hass.data[DOMAIN][mock_config_entry.entry_id]["state"].batch.id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_BATCH_MILESTONE,
        {"event_type": MILESTONE_WATER_ADDED},
        blocking=True,
    )
    await hass.async_block_till_done()

    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    assert await batch_repo.async_has_milestone(old_id, MILESTONE_WATER_ADDED)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_COMPLETE_AND_NEW_BATCH,
        {"name": "Batch 2"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    assert state.batch.name == "Batch 2"
    assert state.batch.id != old_id
    old = await batch_repo.async_get_batch(old_id)
    assert old is not None
    assert old.status == "complete"
    new = await batch_repo.async_get_batch(state.batch.id)
    assert new is not None
    assert new.status == "active"

    batches_sensor = hass.states.get("sensor.communifarm_batch_list")
    assert batches_sensor is not None
    assert len(batches_sensor.attributes["batches"]) >= 2
