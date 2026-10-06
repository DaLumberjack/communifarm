"""Operator floor plan: SVG, picture-elements, gauges — T0."""

from __future__ import annotations

from custom_components.communifarm.const import CLIMATE_LAYOUT_IMAGE
from custom_components.communifarm.dashboard.builder import DashboardBuilder
from custom_components.communifarm.dashboard.layout_png import png_rgb, render_operator_layout_png
from custom_components.communifarm.domain.climate import (
    KIND_FRUITING,
    KIND_GENERAL_ROOM,
    KIND_HARVEST,
    KIND_OUTDOOR,
    ROLE_AC,
    ROLE_CIRCULATION_FAN,
    ROLE_CONDENSATE_PUMP,
    ROLE_FLOAT,
    ROLE_FRESH_AIR_INTAKE,
    ROLE_HEATER,
    ROLE_HUMIDIFIER,
    ROLE_HUMIDITY,
    ROLE_PRESSURE,
    ROLE_TEMPERATURE,
    ClimateBinding,
    ClimateNode,
)
from custom_components.communifarm.domain.climate_drawing import (
    DOT_KINDS,
    DOT_SLOTS,
    drawing_devices,
    drawing_entity_id,
)
from custom_components.communifarm.domain.climate_layout import (
    overlay_points,
    overlay_prefix,
    percent_left,
    percent_top,
    render_operator_layout_svg,
    sensor_xy,
)
from custom_components.communifarm.domain.climate_units import UNIT_US, gauge_bounds


def _fruiting_points():
    fruit = ClimateNode(
        id="climate_fruit",
        site_id="site_test",
        name="Fruiting",
        kind=KIND_FRUITING,
        enclosure="indoor",
        control_enabled=True,
        temperature_target=20.0,
        humidity_target=90.0,
        temp_deadband=1.0,
        humidity_deadband=5.0,
    )
    room = ClimateNode(
        id="env_test",
        site_id="site_test",
        name="Test Tent",
        kind=KIND_GENERAL_ROOM,
        enclosure="indoor",
        control_enabled=True,
        temperature_target=22.0,
        humidity_target=60.0,
    )
    bindings = [
        ClimateBinding(
            node_id=fruit.id,
            role=ROLE_TEMPERATURE,
            entity_entry_id="reg_t",
            entity_id="sensor.fruiting_temp",
        ),
        ClimateBinding(
            node_id=fruit.id,
            role=ROLE_HUMIDITY,
            entity_entry_id="reg_h",
            entity_id="sensor.fruiting_rh",
        ),
        ClimateBinding(
            node_id=fruit.id,
            role=ROLE_CIRCULATION_FAN,
            entity_entry_id="reg_f",
            entity_id="fan.fruiting_circ",
        ),
        ClimateBinding(
            node_id=fruit.id,
            role=ROLE_HUMIDIFIER,
            entity_entry_id="reg_hum",
            entity_id="switch.fruiting_hum",
        ),
    ]
    return overlay_points([room, fruit], bindings)


def test_svg_names_the_operator_rooms() -> None:
    svg = render_operator_layout_svg()
    assert "Fruiting" in svg
    assert "Outdoors" in svg
    assert "Hard goods" in svg
    assert "Not a scale drawing" in svg


def test_png_matches_the_outdoor_and_fruiting_ink() -> None:
    """Picture-elements needs a raster. The PNG keeps the room colors."""
    data = render_operator_layout_png()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert png_rgb(data, 1000, 30) == (0x5D, 0x7F, 0x9A)
    assert png_rgb(data, 1050, 380) == (0x3D, 0x8F, 0x55)


def test_drawing_devices_are_the_labeled_marks() -> None:
    devices = drawing_devices()
    outdoor = {device.role for device in devices if device.kind == KIND_OUTDOOR}
    general = {device.role for device in devices if device.kind == KIND_GENERAL_ROOM}
    assert outdoor == {ROLE_TEMPERATURE, ROLE_HUMIDITY, ROLE_PRESSURE}
    assert general == {
        ROLE_AC,
        ROLE_HEATER,
        ROLE_FRESH_AIR_INTAKE,
        ROLE_FLOAT,
        ROLE_CONDENSATE_PUMP,
    }
    assert not any(device.kind == KIND_HARVEST for device in devices)
    for kind in DOT_KINDS:
        temps = [
            device
            for device in devices
            if device.kind == kind and device.role == ROLE_TEMPERATURE
        ]
        hums = [
            device
            for device in devices
            if device.kind == kind and device.role == ROLE_HUMIDITY
        ]
        assert len(temps) == DOT_SLOTS
        assert len(hums) == DOT_SLOTS
    assert drawing_entity_id(temps[0]).endswith("_temperature_1")


def test_numbered_probe_lands_on_the_center_dot() -> None:
    fruit = ClimateNode(
        id="climate_fruit",
        site_id="site_test",
        name="Fruiting",
        kind=KIND_FRUITING,
        enclosure="indoor",
        control_enabled=True,
        temperature_target=20.0,
        humidity_target=90.0,
    )
    bindings = [
        ClimateBinding(
            node_id=fruit.id,
            role=ROLE_TEMPERATURE,
            entity_entry_id=f"reg_{slot}",
            entity_id=f"sensor.communifarm_fruiting_temperature_{slot}",
        )
        for slot in (3, 1, 2)
    ]
    points = overlay_points([fruit], bindings)
    center = next(point for point in points if point.entity_id.endswith("_1"))
    xy = sensor_xy(KIND_FRUITING, 0)
    assert xy is not None
    assert center.left == percent_left(xy[0])
    assert center.top == percent_top(xy[1])
    assert overlay_prefix(center) == ""


def test_sensor_overlay_uses_the_same_point_as_the_svg_slots() -> None:
    xy = sensor_xy(KIND_FRUITING, 0)
    assert xy is not None
    points = _fruiting_points()
    temp = next(point for point in points if point.role == ROLE_TEMPERATURE)
    assert temp.left == percent_left(xy[0])
    assert temp.top == percent_top(xy[1])
    assert ROLE_HUMIDIFIER in {point.role for point in points}


def test_layout_and_status_tabs_without_bindings(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    paths = [view["path"] for view in config["views"]]
    assert paths[:3] == ["overview", "climate-layout", "climate-status"]
    layout = config["views"][1]
    assert layout["panel"] is True
    stack = layout["cards"][0]
    assert stack["type"] == "vertical-stack"
    picture = next(card for card in stack["cards"] if card["type"] == "picture-elements")
    assert picture["image"] == CLIMATE_LAYOUT_IMAGE
    assert picture["elements"][0]["entity"] == "sensor.communifarm_climate_status"
    note = next(card for card in stack["cards"] if card["type"] == "markdown")
    assert "later" in note["content"]
    assert "phone" in note["content"]
    status = config["views"][2]
    assert all(card.get("type") != "gauge" for card in status["cards"])
    assert any(card.get("title") == "Nothing bound yet" for card in status["cards"])


def test_bound_fan_and_gauges(sample_state) -> None:
    points = _fruiting_points()
    config = DashboardBuilder().build(sample_state, {}, points)
    layout = config["views"][1]
    stack = layout["cards"][0]["cards"]
    picture = next(card for card in stack if card["type"] == "picture-elements")
    fan = next(el for el in picture["elements"] if el["entity"] == "fan.fruiting_circ")
    assert fan["type"] == "state-icon"
    temp = next(el for el in picture["elements"] if el["entity"] == "sensor.fruiting_temp")
    assert temp["type"] == "state-label"
    temp_point = next(point for point in points if point.entity_id == "sensor.fruiting_temp")
    assert temp["style"]["left"] == temp_point.left

    status = config["views"][2]
    history = next(card for card in status["cards"] if card["type"] == "history-graph")
    assert "sensor.fruiting_temp" in history["entities"]
    assert history["hours_to_show"] == 24
    gauges = [
        card
        for card in status["cards"]
        if card.get("type") == "gauge"
        or card.get("type") == "horizontal-stack"
    ]
    flat = []
    for card in gauges:
        if card["type"] == "horizontal-stack":
            flat.extend(card["cards"])
        else:
            flat.append(card)
    temp_gauge = next(card for card in flat if card["entity"] == "sensor.fruiting_temp")
    assert temp_gauge["min"] == 16.0
    assert temp_gauge["max"] == 24.0
    assert temp_gauge["severity"]["green"] == 16.0
    assert temp_gauge["severity"]["yellow"] == 21.0
    assert temp_gauge["severity"]["red"] > temp_gauge["severity"]["yellow"]
    assert "unit" not in temp_gauge
    machines = next(card for card in status["cards"] if card.get("title") == "Machines")
    assert machines["state_color"] is True
    names = [row["entity"] for row in machines["entities"]]
    assert "fan.fruiting_circ" in names
    assert "switch.fruiting_hum" in names


def test_indoor_gauge_is_tight_and_outdoor_is_wide() -> None:
    indoor = gauge_bounds(
        kind=KIND_FRUITING,
        role=ROLE_TEMPERATURE,
        temperature_target=20.0,
        humidity_target=90.0,
        co2_ppm_target=None,
        system="metric",
    )
    assert indoor is not None
    assert indoor[0] == 16.0
    assert indoor[1] == 24.0
    outdoor = gauge_bounds(
        kind=KIND_OUTDOOR,
        role=ROLE_TEMPERATURE,
        temperature_target=None,
        humidity_target=None,
        co2_ppm_target=None,
        system="metric",
    )
    assert outdoor is not None
    assert outdoor[0] == -15.0
    assert outdoor[1] == 45.0
    imperial = gauge_bounds(
        kind=KIND_FRUITING,
        role=ROLE_TEMPERATURE,
        temperature_target=20.0,
        humidity_target=90.0,
        co2_ppm_target=None,
        system=UNIT_US,
    )
    assert imperial is not None
    assert imperial[0] == 61.0
    assert imperial[2] == 68.0
    assert imperial[1] == 75.0
