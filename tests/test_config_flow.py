"""Config flow tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import DOMAIN


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.mock_temperature",
        "21.5",
        {"device_class": "temperature", "unit_of_measurement": "°C"},
    )
    hass.states.async_set(
        "sensor.mock_humidity",
        "55",
        {"device_class": "humidity", "unit_of_measurement": "%"},
    )
    hass.states.async_set("switch.mock_exhaust", "off")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"site_name": "Lab", "environment_name": "Tent A"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bindings"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "temperature_entity": "sensor.mock_temperature",
            "humidity_entity": "sensor.mock_humidity",
            "switch_entity": "switch.mock_exhaust",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "profile"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "temperature_target": 23.0,
            "humidity_target": 65.0,
            "batch_name": "Spawn 1",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lab / Tent A"
    state = result["data"]["state"]
    assert state["site"]["name"] == "Lab"
    assert state["profile"]["temperature_target"] == 23.0
    assert state["batch"]["name"] == "Spawn 1"
    assert len(state["bindings"]) == 3


async def test_single_instance_abort(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
