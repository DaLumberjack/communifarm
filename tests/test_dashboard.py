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


def test_dashboard_includes_mix_and_intake_tabs(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    mix = next(view for view in config["views"] if view.get("path") == "mix")
    assert mix["title"] == "Mix"
    mix_titles = [card.get("title") for card in mix["cards"]]
    assert "Focus — now / last / next" in mix_titles
    assert "NFC / badge (sandbox)" in mix_titles
    assert "Dry progress" in mix_titles
    assert "Water progress" in mix_titles
    assert "Scale (drys)" in mix_titles
    assert "Scale (water pours)" in mix_titles
    assert "Finish checkpoints" in mix_titles
    nfc_card = next(
        card for card in mix["cards"] if card.get("title") == "NFC / badge (sandbox)"
    )
    nfc_ids = [row["entity"] for row in nfc_card["entities"]]
    assert "select.communifarm_intake_tag_uid" in nfc_ids
    assert "button.communifarm_apply_tag_source_scan" in nfc_ids
    assert "button.communifarm_mix_step_from_badge" in nfc_ids
    finish = next(
        card for card in mix["cards"] if card.get("title") == "Finish checkpoints"
    )
    finish_ids = [row["entity"] for row in finish["entities"]]
    assert "button.communifarm_relocate_for_sterilization" in finish_ids
    assert "select.communifarm_relocate_zone" in finish_ids
    water = next(
        card for card in mix["cards"] if card.get("title") == "Scale (water pours)"
    )
    water_ids = [row["entity"] for row in water["entities"]]
    assert "button.communifarm_record_water_pour" in water_ids
    assert "button.esp32dev_location_tare" in water_ids
    assert "number.communifarm_manual_weigh_g" in water_ids
    dry_scale = next(
        card for card in mix["cards"] if card.get("title") == "Scale (drys)"
    )
    dry_ids = [row["entity"] for row in dry_scale["entities"]]
    assert "number.communifarm_manual_weigh_g" in dry_ids

    intake = next(view for view in config["views"] if view.get("path") == "intake")
    assert intake["title"] == "Intake"

    def _intake_inner_cards() -> list[dict]:
        out: list[dict] = []
        for card in intake["cards"]:
            if card.get("type") == "conditional":
                out.append(card["card"])
            else:
                out.append(card)
        return out

    inner = _intake_inner_cards()
    intake_titles = [card.get("title") for card in inner]
    assert "Process" in intake_titles
    assert "Shipment / tag pool" in intake_titles
    assert "Scanner mode" in intake_titles
    assert "Asset purchase" in intake_titles
    assert "Location write" in intake_titles
    assert "Bag / bin write" in intake_titles
    assert "Write actions" in intake_titles

    process = next(card for card in inner if card.get("title") == "Process")
    process_ids = [row["entity"] for row in process["entities"]]
    assert "select.communifarm_intake_process_mode" in process_ids

    conditionals = [
        card for card in intake["cards"] if card.get("type") == "conditional"
    ]
    assert conditionals, "Intake should gate sections with conditional cards"
    mark_gated = [
        c
        for c in conditionals
        if c["card"].get("title") == "Shipment / tag pool"
    ]
    assert mark_gated
    mark_cond = mark_gated[0]["conditions"][0]
    assert mark_cond["condition"] == "or"
    mark_states = {x["state"] for x in mark_cond["conditions"]}
    assert mark_states == {"combined", "mark_tags"}
    purchase_gated = [
        c for c in conditionals if c["card"].get("title") == "Asset purchase"
    ]
    assert purchase_gated
    purchase_states = {
        x["state"] for x in purchase_gated[0]["conditions"][0]["conditions"]
    }
    assert purchase_states == {"combined", "purchase_intake"}

    shipment = next(card for card in inner if card.get("title") == "Shipment / tag pool")
    ship_ids = [row["entity"] for row in shipment["entities"]]
    assert "button.communifarm_seed_shipment_nfc_tags" in ship_ids
    assert "select.communifarm_intake_tag_uid" in ship_ids


def test_dashboard_production_has_placement_sections(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    prod = next(view for view in config["views"] if view.get("path") == "production")
    titles = [card.get("title") for card in prod["cards"]]
    assert "Ops queue" in titles
    assert "Storage" in titles
    assert "Cold storage" in titles
    assert "Fruiting tent" in titles
    assert "Inoculation tent" in titles
    ops = next(card for card in prod["cards"] if card.get("title") == "Ops queue")
    assert "sensor.communifarm_ops_queue" in ops["content"]
    storage = next(card for card in prod["cards"] if card.get("title") == "Storage")
    assert "sensor.communifarm_placement_storage" in storage["content"]
    lifecycle = next(
        card for card in prod["cards"] if card.get("title") == "Lifecycle"
    )
    ids = [row["entity"] for row in lifecycle["entities"]]
    assert "button.communifarm_move_to_incubation" in ids


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
