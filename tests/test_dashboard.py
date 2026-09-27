"""Dashboard builder tests."""

from __future__ import annotations

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
    assert any(card.get("title") == "Environment" for card in cards)
    assert any(card.get("title") == "Targets" for card in cards)
    assert any(card.get("title") == "Controls" for card in cards)
    assert any(card.get("title") == "Production" for card in cards)


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
