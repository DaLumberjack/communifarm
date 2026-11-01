"""Manual weigh Communifarm number → record_weight mass source (T0)."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    ENTITY_MANUAL_WEIGH_G,
    MANUAL_WEIGH_OMIT_G,
    SERVICE_RECORD_WEIGHT,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.domain.weight import resolve_weigh_mass_g


def test_resolve_manual_omit_uses_scale() -> None:
    r = resolve_weigh_mass_g(manual_g=MANUAL_WEIGH_OMIT_G, scale_g=1234.5)
    assert r.source == "scale"
    assert r.mass_g == 1234.5


def test_resolve_manual_ge_zero_wins_including_zero() -> None:
    r = resolve_weigh_mass_g(manual_g=0.0, scale_g=999.0)
    assert r.source == "manual"
    assert r.mass_g == 0.0
    r2 = resolve_weigh_mass_g(manual_g=500.0, scale_g=0.0)
    assert r2.source == "manual"
    assert r2.mass_g == 500.0


def test_resolve_rejects_when_neither_available() -> None:
    with pytest.raises(ValidationError, match="no mass available"):
        resolve_weigh_mass_g(manual_g=-1, scale_g=None)


@pytest.mark.asyncio
async def test_record_weight_uses_manual_when_scale_zero_after_tare(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_manual_weigh.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    bucket = hass.data[DOMAIN][entry_id]
    bucket["weigh_session"]["tare_seen"] = True

    # Scale stuck at 0 (post-tare); operator types grams into Communifarm number.
    hass.states.async_set("sensor.esp32dev_calibrated_g", "0")
    hass.states.async_set(
        "input_select.esp32dev_selected_ingredient", "hardwood pellets"
    )
    bucket["manual_weigh_g"] = 3000.0

    await hass.services.async_call(
        DOMAIN, SERVICE_RECORD_WEIGHT, {}, blocking=True
    )
    rows = await bucket["weight_repository"].async_list_for_batch(
        bucket["state"].batch.id
    )
    assert len(rows) == 1
    assert rows[0].mass_g == 3000.0
    assert rows[0].source_entity_id == ENTITY_MANUAL_WEIGH_G
    assert bucket["manual_weigh_g"] == MANUAL_WEIGH_OMIT_G
    assert bucket["weigh_session"]["last_mass_source"] == "manual"


@pytest.mark.asyncio
async def test_record_weight_manual_zero_is_not_in_recipe(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_manual_zero.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    bucket = hass.data[DOMAIN][entry_id]
    bucket["weigh_session"]["tare_seen"] = True
    hass.states.async_set("sensor.esp32dev_calibrated_g", "500")
    hass.states.async_set(
        "input_select.esp32dev_selected_ingredient", "hardwood pellets"
    )
    bucket["manual_weigh_g"] = 0.0

    await hass.services.async_call(
        DOMAIN, SERVICE_RECORD_WEIGHT, {}, blocking=True
    )
    rows = await bucket["weight_repository"].async_list_for_batch(
        bucket["state"].batch.id
    )
    assert rows[0].mass_g == 0.0
    assert rows[0].source_entity_id == ENTITY_MANUAL_WEIGH_G


@pytest.mark.asyncio
async def test_record_weight_rejects_when_scale_dead_and_manual_omit(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_manual_dead.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    hass.data[DOMAIN][entry_id]["weigh_session"]["tare_seen"] = True
    hass.data[DOMAIN][entry_id]["manual_weigh_g"] = MANUAL_WEIGH_OMIT_G
    # No scale entity → must fail closed with a clear message.
    with pytest.raises(HomeAssistantError, match="Manual weigh"):
        await hass.services.async_call(
            DOMAIN, SERVICE_RECORD_WEIGHT, {}, blocking=True
        )
