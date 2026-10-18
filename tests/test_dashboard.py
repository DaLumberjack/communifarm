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
    assert len(config["views"]) == 11
    cards = config["views"][0]["cards"]
    titles = [card.get("title") for card in cards]
    assert "Current settings" in titles
    assert "Environment" in titles
    assert "Targets" in titles
    assert "Controls" in titles
    assert "Production" in titles


def test_dashboard_weigh_tab_redirects_to_mix(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    weigh = next(view for view in config["views"] if view.get("path") == "weigh")
    assert weigh["title"] == "Weigh"
    assert any(
        "Moved to **Mix**" in (card.get("content") or "") for card in weigh["cards"]
    )


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


def test_dashboard_includes_mix_and_nfc_write_tabs(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    mix = next(view for view in config["views"] if view.get("path") == "mix")
    assert mix["title"] == "Mix"
    mix_titles = [card.get("title") for card in mix["cards"]]
    assert "Focus — now / last / next" in mix_titles
    assert "Dry progress" in mix_titles
    assert "Water progress" in mix_titles
    assert "Scale (drys)" in mix_titles
    assert "Scale (water pours)" in mix_titles
    assert "Finish checkpoints" in mix_titles
    finish = next(
        card for card in mix["cards"] if card.get("title") == "Finish checkpoints"
    )
    finish_ids = [row["entity"] for row in finish["entities"]]
    assert "button.communifarm_relocate_for_sterilization" in finish_ids
    water = next(
        card for card in mix["cards"] if card.get("title") == "Scale (water pours)"
    )
    water_ids = [row["entity"] for row in water["entities"]]
    assert "button.communifarm_record_water_pour" in water_ids
    assert "button.esp32dev_location_tare" in water_ids

    nfc = next(view for view in config["views"] if view.get("path") == "nfc-write")
    assert nfc["title"] == "NFC Write"
    nfc_titles = [card.get("title") for card in nfc["cards"]]
    assert "Write target" in nfc_titles


def test_dashboard_includes_batches_tab(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    batches = next(view for view in config["views"] if view.get("path") == "batches")
    assert batches["title"] == "Batches"
    titles = [card.get("title") for card in batches["cards"]]
    assert "Batch list" in titles
    assert "Post-weigh process" in titles
    active = next(card for card in batches["cards"] if card.get("title") == "Active batch")
    ids = [
        row["entity"] if isinstance(row, dict) else row for row in active["entities"]
    ]
    assert "button.communifarm_complete_and_new_batch" in ids


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
