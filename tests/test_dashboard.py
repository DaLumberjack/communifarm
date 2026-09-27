"""Dashboard builder tests."""

from __future__ import annotations

from custom_components.communifarm.const import (
    ENTITY_HUMIDITY_TARGET,
    ENTITY_TEMPERATURE_TARGET,
)
from custom_components.communifarm.dashboard.builder import DashboardBuilder


def test_dashboard_includes_bound_sensors_and_batch(sample_state) -> None:
    resolved = {
        "temperature_source": "sensor.mock_temperature",
        "humidity_source": "sensor.mock_humidity",
        "switch_actuator": "switch.mock_exhaust",
    }
    config = DashboardBuilder().build(sample_state, resolved)
    assert config["title"] == "Communifarm"
    cards = config["views"][0]["cards"]
    titles = [card.get("title") for card in cards]
    assert "Current settings" in titles
    assert "Environment" in titles
    assert "Targets" in titles
    assert "Controls" in titles
    assert "Production" in titles


def test_dashboard_current_settings_use_live_entity_templates(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    settings = next(
        card for card in config["views"][0]["cards"] if card.get("title") == "Current settings"
    )
    assert f"states('{ENTITY_TEMPERATURE_TARGET}')" in settings["content"]
    assert f"states('{ENTITY_HUMIDITY_TARGET}')" in settings["content"]


def test_dashboard_targets_card_is_interactive(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    targets = next(
        card for card in config["views"][0]["cards"] if card.get("title") == "Targets"
    )
    entity_ids = [row["entity"] for row in targets["entities"]]
    assert ENTITY_TEMPERATURE_TARGET in entity_ids
    assert ENTITY_HUMIDITY_TARGET in entity_ids
    assert targets.get("show_header_toggle") is False


def test_dashboard_omits_missing_optional_controls(sample_state) -> None:
    sample_state.bindings = [
        b for b in sample_state.bindings if b.role != "switch_actuator"
    ]
    config = DashboardBuilder().build(
        sample_state,
        {"temperature_source": "sensor.mock_temperature"},
    )
    cards = config["views"][0]["cards"]
    assert not any(card.get("title") == "Controls" for card in cards)
