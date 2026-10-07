"""Climate tree, inheritance, control decisions, schema v12 — T0/T2."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    ENTITY_CLIMATE_STATUS,
    SERVICE_BIND_CLIMATE_ROLE,
    SERVICE_ENSURE_CLIMATE_LAYOUT,
    SERVICE_TICK_CLIMATE,
)
from custom_components.communifarm.dashboard.builder import DashboardBuilder
from custom_components.communifarm.domain.climate import (
    KIND_FRUITING,
    KIND_GENERAL_ROOM,
    KIND_HARVEST,
    KIND_INCUBATION,
    KIND_INOCULATION,
    KIND_OUTDOOR,
    KIND_SPECS,
    KIND_STORAGE_HARD_GOODS,
    PHOTOPERIOD_DARK,
    PHOTOPERIOD_GREENS,
    ROLE_AC,
    ROLE_CIRCULATION_FAN,
    ROLE_CO2_PPM,
    ROLE_CONDENSATE_PUMP,
    ROLE_DEHUMIDIFIER,
    ROLE_EXHAUST_FAN,
    ROLE_FLOAT,
    ROLE_FRESH_AIR_INTAKE,
    ROLE_HEATER,
    ROLE_HUMIDIFIER,
    ROLE_HUMIDITY,
    ROLE_INTAKE_FAN,
    ROLE_LIGHT,
    ROLE_PRESSURE,
    ROLE_TEMPERATURE,
    SOURCE_INHERITED,
    SOURCE_LOCAL,
    SOURCE_NONE,
    ClimateBinding,
    SensorSample,
    build_operator_layout,
    resolve_effective_readings,
    validate_climate_node,
)
from custom_components.communifarm.domain.climate_control import (
    ObservedState,
    decide_control,
)
from custom_components.communifarm.domain.location import AREA_FRUITING_TENT
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db

NOW_DARK = datetime(2026, 10, 1, 18, 0, tzinfo=UTC)
NOW_LIGHT = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
NOW_GREEN_ON = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)
NOW_GREEN_OFF = datetime(2026, 10, 1, 20, 0, tzinfo=UTC)


def _layout():
    return build_operator_layout(
        "site_test",
        general_room_id="env_test",
        general_room_name="Test Tent",
        general_temperature_target=22.0,
        general_humidity_target=60.0,
    )


def _by_kind(nodes):
    return {node.kind: node for node in nodes}


def _bind(node_id: str, role: str, entity: str, *, waste: bool = False) -> ClimateBinding:
    return ClimateBinding(
        node_id=node_id,
        role=role,
        entity_entry_id=f"reg_{role}_{node_id}",
        entity_id=entity,
        waste_heat_to_parent=waste,
    )


def _decide(samples, bindings, observed=None, now=None, nodes=None):
    tree = nodes if nodes is not None else _layout()
    samples_by: dict = {}
    for node_id, node_samples in samples.items():
        samples_by[node_id] = node_samples
    bindings_by: dict = {}
    for binding in bindings:
        bindings_by.setdefault(binding.node_id, []).append(binding)
    decision = decide_control(
        tree,
        samples_by,
        bindings_by,
        observed or {},
        now or NOW_DARK,
    )
    return decision, _by_kind(tree)


def _ons(decision, node_id: str) -> set[str]:
    return {
        intent.role
        for intent in decision.intents
        if intent.node_id == node_id and intent.turn_on
    }


def _reason(decision, node_id: str, role: str) -> str:
    matches = [
        intent.reason
        for intent in decision.intents
        if intent.node_id == node_id and intent.role == role
    ]
    assert matches, f"no intent for {role}"
    return matches[0]


def test_operator_layout_parents_and_control_flags() -> None:
    nodes = _layout()
    by = _by_kind(nodes)
    assert len(nodes) == 11
    assert by[KIND_GENERAL_ROOM].id == "env_test"
    assert by[KIND_GENERAL_ROOM].name == "Test Tent"
    assert by[KIND_GENERAL_ROOM].parent_id == by[KIND_OUTDOOR].id
    assert by[KIND_FRUITING].parent_id == by[KIND_GENERAL_ROOM].id
    assert by[KIND_FRUITING].control_enabled is True
    assert ROLE_HUMIDIFIER in KIND_SPECS[KIND_FRUITING].expected_roles
    assert by[KIND_STORAGE_HARD_GOODS].control_enabled is False
    assert by[KIND_OUTDOOR].enclosure == "outdoor"
    assert by[KIND_OUTDOOR].parent_id is None


def test_reject_temperature_target_out_of_range() -> None:
    node = _by_kind(_layout())[KIND_FRUITING]
    node.temperature_target = 140
    with pytest.raises(ValidationError, match="temperature_target"):
        validate_climate_node(node)


def test_local_median_ignores_stale_and_one_sensor_is_enough() -> None:
    nodes = _layout()
    by = _by_kind(nodes)
    fruit = by[KIND_FRUITING]
    readings = resolve_effective_readings(
        nodes,
        {
            fruit.id: [
                SensorSample(ROLE_TEMPERATURE, 10, stale=True),
                SensorSample(ROLE_TEMPERATURE, 28),
                SensorSample(ROLE_TEMPERATURE, 30),
                SensorSample(ROLE_TEMPERATURE, 32),
            ]
        },
    )
    local = readings[fruit.id][ROLE_TEMPERATURE]
    assert local.source == SOURCE_LOCAL
    assert local.value == 30
    assert local.sample_count == 3

    readings = resolve_effective_readings(
        nodes, {fruit.id: [SensorSample(ROLE_TEMPERATURE, 21)]}
    )
    assert readings[fruit.id][ROLE_TEMPERATURE].value == 21
    assert readings[fruit.id][ROLE_TEMPERATURE].sample_count == 1


def test_indoor_inherits_parent_outdoor_does_not() -> None:
    nodes = _layout()
    by = _by_kind(nodes)
    outdoor = by[KIND_OUTDOOR]
    general = by[KIND_GENERAL_ROOM]
    hard = by[KIND_STORAGE_HARD_GOODS]
    readings = resolve_effective_readings(
        nodes,
        {
            outdoor.id: [
                SensorSample(ROLE_TEMPERATURE, 10),
                SensorSample(ROLE_HUMIDITY, 40),
            ]
        },
    )
    assert readings[general.id][ROLE_TEMPERATURE].source == SOURCE_INHERITED
    assert readings[general.id][ROLE_TEMPERATURE].value == 10
    assert readings[hard.id][ROLE_TEMPERATURE].source == SOURCE_INHERITED
    assert readings[hard.id][ROLE_TEMPERATURE].value == 10
    assert readings[outdoor.id][ROLE_PRESSURE].source == SOURCE_NONE


def test_too_hot_uses_cooler_parent_air_before_ac() -> None:
    nodes = _layout()
    by = _by_kind(nodes)
    fruit = by[KIND_FRUITING]
    general = by[KIND_GENERAL_ROOM]
    decision, _ = _decide(
        {
            fruit.id: [SensorSample(ROLE_TEMPERATURE, 30)],
            general.id: [SensorSample(ROLE_TEMPERATURE, 18)],
        },
        [
            _bind(fruit.id, ROLE_EXHAUST_FAN, "fan.exhaust"),
            _bind(fruit.id, ROLE_AC, "switch.ac"),
            _bind(fruit.id, ROLE_HEATER, "switch.heater"),
            _bind(fruit.id, ROLE_CIRCULATION_FAN, "fan.circ"),
        ],
        nodes=nodes,
    )
    ons = _ons(decision, fruit.id)
    assert ROLE_EXHAUST_FAN in ons
    assert ROLE_CIRCULATION_FAN in ons
    assert ROLE_AC not in ons
    assert ROLE_HEATER not in ons


def test_too_hot_external_air_will_not_help_uses_ac() -> None:
    nodes = _layout()
    fruit = _by_kind(nodes)[KIND_FRUITING]
    general = _by_kind(nodes)[KIND_GENERAL_ROOM]
    decision, _ = _decide(
        {
            fruit.id: [SensorSample(ROLE_TEMPERATURE, 30)],
            general.id: [SensorSample(ROLE_TEMPERATURE, 25)],
        },
        [
            _bind(fruit.id, ROLE_EXHAUST_FAN, "fan.exhaust"),
            _bind(fruit.id, ROLE_AC, "switch.ac"),
        ],
        nodes=nodes,
    )
    ons = _ons(decision, fruit.id)
    assert ROLE_AC in ons
    assert ROLE_EXHAUST_FAN not in ons
    assert "will not help" in _reason(decision, fruit.id, ROLE_EXHAUST_FAN)


def test_missing_ac_binding_produces_no_ac_intent() -> None:
    nodes = _layout()
    fruit = _by_kind(nodes)[KIND_FRUITING]
    general = _by_kind(nodes)[KIND_GENERAL_ROOM]
    decision, _ = _decide(
        {
            fruit.id: [SensorSample(ROLE_TEMPERATURE, 30)],
            general.id: [SensorSample(ROLE_TEMPERATURE, 25)],
        },
        [_bind(fruit.id, ROLE_EXHAUST_FAN, "fan.exhaust")],
        nodes=nodes,
    )
    assert ROLE_AC not in {intent.role for intent in decision.intents if intent.node_id == fruit.id}


def test_too_cold_heater_on_ac_off() -> None:
    nodes = _layout()
    fruit = _by_kind(nodes)[KIND_FRUITING]
    decision, _ = _decide(
        {fruit.id: [SensorSample(ROLE_TEMPERATURE, 10)]},
        [
            _bind(fruit.id, ROLE_HEATER, "switch.heater"),
            _bind(fruit.id, ROLE_AC, "switch.ac"),
        ],
        nodes=nodes,
    )
    ons = _ons(decision, fruit.id)
    assert ROLE_HEATER in ons
    assert ROLE_AC not in ons
    paired = {
        intent.role
        for intent in decision.intents
        if intent.node_id == fruit.id and intent.turn_on and intent.role in {ROLE_HEATER, ROLE_AC}
    }
    assert paired != {ROLE_HEATER, ROLE_AC}


def test_humidity_dehumidifier_and_external_air() -> None:
    nodes = _layout()
    fruit = _by_kind(nodes)[KIND_FRUITING]
    general = _by_kind(nodes)[KIND_GENERAL_ROOM]
    dry, _ = _decide(
        {fruit.id: [SensorSample(ROLE_HUMIDITY, 70)]},
        [_bind(fruit.id, ROLE_HUMIDIFIER, "switch.hum")],
        nodes=nodes,
    )
    assert ROLE_HUMIDIFIER in _ons(dry, fruit.id)

    unbound, _ = _decide(
        {fruit.id: [SensorSample(ROLE_HUMIDITY, 70)]},
        [],
        nodes=nodes,
    )
    assert all(intent.role != ROLE_HUMIDIFIER for intent in unbound.intents)

    wet_air, _ = _decide(
        {
            fruit.id: [SensorSample(ROLE_HUMIDITY, 98)],
            general.id: [SensorSample(ROLE_HUMIDITY, 80)],
        },
        [_bind(fruit.id, ROLE_EXHAUST_FAN, "fan.exhaust")],
        nodes=nodes,
    )
    assert ROLE_EXHAUST_FAN in _ons(wet_air, fruit.id)

    wet_blocked, _ = _decide(
        {
            fruit.id: [SensorSample(ROLE_HUMIDITY, 98)],
            general.id: [SensorSample(ROLE_HUMIDITY, 96)],
        },
        [_bind(fruit.id, ROLE_EXHAUST_FAN, "fan.exhaust")],
        nodes=nodes,
    )
    assert ROLE_EXHAUST_FAN not in _ons(wet_blocked, fruit.id)
    assert "will not help" in _reason(wet_blocked, fruit.id, ROLE_EXHAUST_FAN)

    dehum, _ = _decide(
        {fruit.id: [SensorSample(ROLE_HUMIDITY, 98)]},
        [_bind(fruit.id, ROLE_DEHUMIDIFIER, "switch.dehum")],
        nodes=nodes,
    )
    assert ROLE_DEHUMIDIFIER in _ons(dehum, fruit.id)


def test_light_grace_holds_humidifier_then_releases() -> None:
    nodes = _layout()
    fruit = _by_kind(nodes)[KIND_FRUITING]
    now = NOW_DARK
    held, _ = _decide(
        {fruit.id: [SensorSample(ROLE_HUMIDITY, 70)]},
        [_bind(fruit.id, ROLE_HUMIDIFIER, "switch.hum")],
        observed={
            fruit.id: ObservedState(
                light_on=True, light_on_since=now - timedelta(minutes=10)
            )
        },
        now=now,
        nodes=nodes,
    )
    assert ROLE_HUMIDIFIER not in _ons(held, fruit.id)
    assert "grace" in _reason(held, fruit.id, ROLE_HUMIDIFIER)

    released, _ = _decide(
        {fruit.id: [SensorSample(ROLE_HUMIDITY, 70)]},
        [_bind(fruit.id, ROLE_HUMIDIFIER, "switch.hum")],
        observed={
            fruit.id: ObservedState(
                light_on=True, light_on_since=now - timedelta(minutes=16)
            )
        },
        now=now,
        nodes=nodes,
    )
    assert ROLE_HUMIDIFIER in _ons(released, fruit.id)


def test_lights_suppress_heater_but_not_cooling() -> None:
    nodes = _layout()
    fruit = _by_kind(nodes)[KIND_FRUITING]
    general = _by_kind(nodes)[KIND_GENERAL_ROOM]
    cold, _ = _decide(
        {fruit.id: [SensorSample(ROLE_TEMPERATURE, 10)]},
        [
            _bind(fruit.id, ROLE_HEATER, "switch.heater"),
            _bind(fruit.id, ROLE_LIGHT, "light.fruit"),
        ],
        observed={fruit.id: ObservedState(light_on=True, light_on_since=NOW_DARK)},
        now=NOW_DARK,
        nodes=nodes,
    )
    assert ROLE_HEATER not in _ons(cold, fruit.id)
    assert "suppressed" in _reason(cold, fruit.id, ROLE_HEATER)

    hot, _ = _decide(
        {
            fruit.id: [SensorSample(ROLE_TEMPERATURE, 30)],
            general.id: [SensorSample(ROLE_TEMPERATURE, 28)],
        },
        [
            _bind(fruit.id, ROLE_AC, "switch.ac"),
            _bind(fruit.id, ROLE_CIRCULATION_FAN, "fan.circ"),
            _bind(fruit.id, ROLE_HEATER, "switch.heater"),
            _bind(fruit.id, ROLE_LIGHT, "light.fruit"),
        ],
        observed={fruit.id: ObservedState(light_on=True, light_on_since=NOW_LIGHT)},
        now=NOW_LIGHT,
        nodes=nodes,
    )
    ons = _ons(hot, fruit.id)
    assert ROLE_AC in ons
    assert ROLE_CIRCULATION_FAN in ons
    assert ROLE_HEATER not in ons


def test_child_light_waste_heat_suppresses_parent_heater() -> None:
    nodes = _layout()
    by = _by_kind(nodes)
    general = by[KIND_GENERAL_ROOM]
    fruit = by[KIND_FRUITING]
    decision, _ = _decide(
        {general.id: [SensorSample(ROLE_TEMPERATURE, 10)]},
        [
            _bind(general.id, ROLE_HEATER, "switch.room_heat"),
            _bind(fruit.id, ROLE_LIGHT, "light.fruit", waste=True),
        ],
        now=NOW_LIGHT,
        nodes=nodes,
    )
    assert ROLE_HEATER not in _ons(decision, general.id)
    assert "suppressed" in _reason(decision, general.id, ROLE_HEATER)


def test_photoperiod_fruiting_greens_and_dark() -> None:
    nodes = _layout()
    fruit = _by_kind(nodes)[KIND_FRUITING]
    culture = _by_kind(nodes)[KIND_INOCULATION]
    day, _ = _decide(
        {},
        [_bind(fruit.id, ROLE_LIGHT, "light.fruit")],
        now=NOW_LIGHT,
        nodes=nodes,
    )
    assert ROLE_LIGHT in _ons(day, fruit.id)
    night, _ = _decide(
        {},
        [_bind(fruit.id, ROLE_LIGHT, "light.fruit")],
        now=NOW_DARK,
        nodes=nodes,
    )
    assert ROLE_LIGHT not in _ons(night, fruit.id)

    fruit.photoperiod_preset = PHOTOPERIOD_GREENS
    fruit.light_hours_on = 16
    fruit.light_hours_off = 8
    greens_on, _ = _decide(
        {},
        [_bind(fruit.id, ROLE_LIGHT, "light.greens")],
        now=NOW_GREEN_ON,
        nodes=nodes,
    )
    assert ROLE_LIGHT in _ons(greens_on, fruit.id)
    greens_off, _ = _decide(
        {},
        [_bind(fruit.id, ROLE_LIGHT, "light.greens")],
        now=NOW_GREEN_OFF,
        nodes=nodes,
    )
    assert ROLE_LIGHT not in _ons(greens_off, fruit.id)

    assert culture.photoperiod_preset == PHOTOPERIOD_DARK
    dark, _ = _decide(
        {},
        [_bind(culture.id, ROLE_LIGHT, "light.culture")],
        now=NOW_LIGHT,
        nodes=nodes,
    )
    assert ROLE_LIGHT not in _ons(dark, culture.id)


def test_co2_opens_intake_and_fresh_air_checks_outdoor() -> None:
    nodes = _layout()
    by = _by_kind(nodes)
    inoc = by[KIND_INOCULATION]
    general = by[KIND_GENERAL_ROOM]
    outdoor = by[KIND_OUTDOOR]
    ppm, _ = _decide(
        {inoc.id: [SensorSample(ROLE_CO2_PPM, 1500)]},
        [_bind(inoc.id, ROLE_INTAKE_FAN, "fan.inoc")],
        nodes=nodes,
    )
    assert ROLE_INTAKE_FAN in _ons(ppm, inoc.id)

    helpful, _ = _decide(
        {
            general.id: [SensorSample(ROLE_TEMPERATURE, 30)],
            outdoor.id: [SensorSample(ROLE_TEMPERATURE, 15)],
        },
        [_bind(general.id, ROLE_FRESH_AIR_INTAKE, "fan.fresh")],
        nodes=nodes,
    )
    assert ROLE_FRESH_AIR_INTAKE in _ons(helpful, general.id)

    useless, _ = _decide(
        {
            general.id: [SensorSample(ROLE_TEMPERATURE, 30)],
            outdoor.id: [SensorSample(ROLE_TEMPERATURE, 40)],
        },
        [_bind(general.id, ROLE_FRESH_AIR_INTAKE, "fan.fresh")],
        nodes=nodes,
    )
    assert ROLE_FRESH_AIR_INTAKE not in _ons(useless, general.id)
    assert "will not help" in _reason(useless, general.id, ROLE_FRESH_AIR_INTAKE)


def test_float_pump_is_independent_and_missing_float_stays_off() -> None:
    nodes = _layout()
    general = _by_kind(nodes)[KIND_GENERAL_ROOM]
    active, _ = _decide(
        {general.id: [SensorSample(ROLE_FLOAT, 1)]},
        [
            _bind(general.id, ROLE_CONDENSATE_PUMP, "switch.pump"),
            _bind(general.id, ROLE_HEATER, "switch.heat"),
        ],
        nodes=nodes,
    )
    assert ROLE_CONDENSATE_PUMP in _ons(active, general.id)
    assert ROLE_HEATER not in _ons(active, general.id)

    missing, _ = _decide(
        {},
        [_bind(general.id, ROLE_CONDENSATE_PUMP, "switch.pump")],
        nodes=nodes,
    )
    assert ROLE_CONDENSATE_PUMP not in _ons(missing, general.id)

    clear, _ = _decide(
        {general.id: [SensorSample(ROLE_FLOAT, 0)]},
        [_bind(general.id, ROLE_CONDENSATE_PUMP, "switch.pump")],
        nodes=nodes,
    )
    assert ROLE_CONDENSATE_PUMP not in _ons(clear, general.id)


def test_uncontrolled_storage_does_not_actuate() -> None:
    nodes = _layout()
    hard = _by_kind(nodes)[KIND_STORAGE_HARD_GOODS]
    decision, _ = _decide(
        {hard.id: [SensorSample(ROLE_TEMPERATURE, 40)]},
        [_bind(hard.id, ROLE_HEATER, "switch.heat")],
        nodes=nodes,
    )
    assert all(intent.node_id != hard.id for intent in decision.intents)
    assert decision.readings[hard.id][ROLE_TEMPERATURE].source == SOURCE_LOCAL


def test_dashboard_includes_climate_card(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    titles = [card.get("title") for card in config["views"][0]["cards"]]
    assert "Climate" in titles


def test_schema_v13_upgrade_preserves_v11(tmp_path: Path) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    for version in range(1, 12):
        conn.executescript(sqlite_db.MIGRATIONS[version])
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, datetime('now'))",
            (version,),
        )
    conn.execute(
        """
        INSERT INTO batches (
          stable_id, site_id, environment_id, name, nfc_uid, status, created_at
        ) VALUES (
          'batch_keep', 'site_test', 'env_test', 'Keep me', 'batch_keep',
          'active', '2026-01-01T00:00:00+00:00'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO placement_areas (
          stable_id, site_id, name, area_kind, slot_kind, slot_count, created_at
        ) VALUES (
          'area_keep', 'site_test', 'Fruiting tent', 'fruiting_tent', 'level', 5,
          '2026-01-01T00:00:00+00:00'
        )
        """
    )
    conn.commit()
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    assert version == 13
    batch = conn.execute(
        "SELECT name, environment_id FROM batches WHERE stable_id = 'batch_keep'"
    ).fetchone()
    assert batch["name"] == "Keep me"
    assert batch["environment_id"] == "env_test"
    area = conn.execute(
        "SELECT name, climate_id FROM placement_areas WHERE stable_id = 'area_keep'"
    ).fetchone()
    assert area["name"] == "Fruiting tent"
    assert area["climate_id"] is None
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert "climate_nodes" in tables
    assert "climate_bindings" in tables
    assert "climate_intents" in tables
    assert "air_vents" in tables
    assert "tachometer_readings" in tables
    conn.close()


@pytest.mark.asyncio
async def test_tick_turns_fruiting_fan_on_then_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
) -> None:
    """Mocked ESPHome-shaped states: high temp starts the fan, target stops it."""

    async def _turn_on(call: ServiceCall) -> None:
        hass.states.async_set(call.data["entity_id"], "on")

    async def _turn_off(call: ServiceCall) -> None:
        hass.states.async_set(call.data["entity_id"], "off")

    hass.services.async_register("fan", "turn_on", _turn_on)
    hass.services.async_register("fan", "turn_off", _turn_off)
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    seeded = hass.states.get(ENTITY_CLIMATE_STATUS)
    assert seeded is not None
    assert seeded.state == "11 nodes"
    outdoor = hass.states.get("sensor.communifarm_outdoor_temperature")
    assert outdoor is not None
    assert float(outdoor.state) == 12.0
    assert hass.states.get("switch.communifarm_general_room_ac").state == "off"
    png = Path(hass.config.path("www/communifarm/cea-layout.png"))
    assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    await hass.services.async_call(
        DOMAIN, SERVICE_ENSURE_CLIMATE_LAYOUT, {}, blocking=True
    )
    await hass.async_block_till_done()
    repo = hass.data[DOMAIN][mock_config_entry.entry_id]["climate_repository"]
    nodes = await repo.async_list_nodes("site_test")
    fruit = next(node for node in nodes if node.kind == KIND_FRUITING)
    assert fruit.parent_id
    incub = next(node for node in nodes if node.kind == KIND_INCUBATION)
    assert incub.temperature_target == 22.0
    assert incub.humidity_target == 75.0
    harvest = next(node for node in nodes if node.kind == KIND_HARVEST)
    assert harvest.humidity_target == 85.0
    general = next(node for node in nodes if node.id == "env_test")
    assert general.kind == KIND_GENERAL_ROOM

    loc = hass.data[DOMAIN][mock_config_entry.entry_id]["location_repository"]
    areas = await loc.async_list_areas("site_test")
    tent = next(area for area in areas if area.area_kind == AREA_FRUITING_TENT)
    assert tent.climate_id == fruit.id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_BIND_CLIMATE_ROLE,
        {
            "node_id": fruit.id,
            "role": ROLE_TEMPERATURE,
            "entity_id": "sensor.fruiting_temp",
        },
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_BIND_CLIMATE_ROLE,
        {
            "node_id": fruit.id,
            "role": ROLE_CIRCULATION_FAN,
            "entity_id": "fan.fruiting_circ",
        },
        blocking=True,
    )
    hass.states.async_set("sensor.fruiting_temp", "30")
    hass.states.async_set("fan.fruiting_circ", "off")
    fruit_temps = [
        binding.entity_id
        for binding in await repo.async_list_bindings("site_test")
        if binding.node_id == fruit.id
        and binding.role == ROLE_TEMPERATURE
        and binding.entity_id
    ]
    for entity_id in fruit_temps:
        hass.states.async_set(entity_id, "30")
    assert len(fruit_temps) == 6
    await hass.services.async_call(DOMAIN, SERVICE_TICK_CLIMATE, {}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("fan.fruiting_circ").state == "on"
    status = hass.states.get(ENTITY_CLIMATE_STATUS)
    assert status is not None
    assert status.state == "11 nodes"
    assert "**Fruiting**" in status.attributes["summary"]
    assert status.attributes["summary"].startswith("- **")
    recent = await repo.async_list_recent_intents()
    assert any(row["entity_id"] == "fan.fruiting_circ" and row["turn_on"] for row in recent)

    for entity_id in fruit_temps:
        hass.states.async_set(entity_id, "20")
    await hass.services.async_call(DOMAIN, SERVICE_TICK_CLIMATE, {}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("fan.fruiting_circ").state == "off"

    again = await repo.async_list_nodes("site_test")
    assert [node.id for node in again] == [node.id for node in nodes]

    def _store_old_incubation() -> None:
        assert repo._conn is not None
        repo._conn.execute(
            """
            UPDATE climate_nodes
            SET temperature_target = 25, humidity_target = 70
            WHERE kind = ?
            """,
            (KIND_INCUBATION,),
        )
        repo._conn.commit()

    await hass.async_add_executor_job(repo._locked, _store_old_incubation)
    await hass.services.async_call(
        DOMAIN, SERVICE_ENSURE_CLIMATE_LAYOUT, {}, blocking=True
    )
    refreshed = await repo.async_list_nodes("site_test")
    incub = next(node for node in refreshed if node.kind == KIND_INCUBATION)
    assert incub.temperature_target == 22.0
    assert incub.humidity_target == 75.0
    general = next(node for node in refreshed if node.kind == KIND_GENERAL_ROOM)
    assert general.humidity_target == 60.0
