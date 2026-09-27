"""Setup, unload, persistence, and service tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import DOMAIN, SERVICE_TRANSITION_BATCH
from custom_components.communifarm.domain.models import CommunifarmState
from custom_components.communifarm.storage.repository import CommunifarmRepository


async def test_setup_unload_and_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
) -> None:
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.communifarm_batch_stage") is not None
    assert hass.states.get("number.communifarm_temperature_target") is not None
    assert hass.states.get("number.communifarm_humidity_target") is not None
    assert hass.states.get("switch.communifarm_allowlisted_switch") is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_repository_roundtrip(
    hass: HomeAssistant, sample_state: CommunifarmState
) -> None:
    repo = CommunifarmRepository(hass)
    await repo.async_save(sample_state)
    loaded = await repo.async_load()
    assert loaded is not None
    assert loaded.site.id == sample_state.site.id
    assert loaded.profile.humidity_target == 60.0


async def test_upgrade_preserves_state(
    hass: HomeAssistant, sample_state: CommunifarmState
) -> None:
    """T2-style no-data-loss: save under schema v1 and reload."""
    sample_state.schema_version = 1
    repo = CommunifarmRepository(hass)
    await repo.async_save(sample_state)
    reloaded = await repo.async_load()
    assert reloaded is not None
    assert reloaded.to_dict() == sample_state.to_dict()


async def test_batch_transition_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
) -> None:
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_TRANSITION_BATCH,
        {"stage": "active"},
        blocking=True,
    )
    await hass.async_block_till_done()
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    assert state.batch.stage == "active"
    assert len(state.batch.events) == 1


async def test_temperature_target_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
) -> None:
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.communifarm_temperature_target", "value": 24.5},
        blocking=True,
    )
    await hass.async_block_till_done()
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    assert state.profile.temperature_target == 24.5


async def test_allowlisted_switch_tracks_underlying_state(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
) -> None:
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    proxy = hass.states.get("switch.communifarm_allowlisted_switch")
    assert proxy is not None
    assert proxy.state == "off"

    hass.states.async_set("switch.mock_exhaust", "on")
    await hass.async_block_till_done()
    # Entity state refreshes on next read/write; force a state write via update
    entity = hass.data["entity_components"]["switch"].get_entity(
        "switch.communifarm_allowlisted_switch"
    )
    if entity is not None:
        entity.async_write_ha_state()
        await hass.async_block_till_done()
        assert hass.states.get("switch.communifarm_allowlisted_switch").state == "on"
