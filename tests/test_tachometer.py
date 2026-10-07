"""Tests for manual vent tachometer / air-exchange logging."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm import tachometer_actions
from custom_components.communifarm.const import (
    DOMAIN,
    ENTITY_TACHOMETER_STATUS,
    SERVICE_RECORD_TACHOMETER,
    SERVICE_UPSERT_AIR_VENT,
)
from custom_components.communifarm.domain.models import CommunifarmState
from custom_components.communifarm.domain.tachometer import (
    UNIT_CFM,
    UNIT_FPM,
    UNIT_RPM,
    VENT_ROLE_CIRCULATION,
    VENT_ROLE_EXHAUST,
    VENT_ROLE_INTAKE,
    VENT_ROLE_OTHER,
    AirVent,
    TachometerReading,
    normalize_vent_label,
    reading_to_dict,
    validate_tach_unit,
    validate_tach_value,
    validate_vent_role,
    vent_to_dict,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.tachometer_repository import (
    TachometerRepository,
)


@pytest.mark.asyncio
async def test_schema_v13_creates_tachometer_tables(
    tmp_path, hass: HomeAssistant
) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "air_vents" in tables
    assert "tachometer_readings" in tables
    conn.close()


def test_domain_validators_reject_bad_inputs() -> None:
    assert normalize_vent_label("  Fruiting   intake  ") == "Fruiting intake"
    with pytest.raises(ValidationError, match="required"):
        normalize_vent_label("   ")
    with pytest.raises(ValidationError, match="64"):
        normalize_vent_label("x" * 65)

    assert validate_vent_role("INTAKE") == VENT_ROLE_INTAKE
    with pytest.raises(ValidationError, match="vent_role"):
        validate_vent_role("window")

    assert validate_tach_unit("CFM") == UNIT_CFM
    with pytest.raises(ValidationError, match="unit"):
        validate_tach_unit("mph")

    assert validate_tach_value("12.5") == 12.5
    with pytest.raises(ValidationError, match="number"):
        validate_tach_value("nope")
    with pytest.raises(ValidationError, match="negative"):
        validate_tach_value(-0.1)
    with pytest.raises(ValidationError, match="unrealistically"):
        validate_tach_value(1_000_001)


def test_domain_dicts_round_trip_fields() -> None:
    vent = AirVent(
        id="vent_1",
        site_id="site_1",
        label="Exhaust A",
        vent_role=VENT_ROLE_EXHAUST,
        climate_node_id="climate_fruiting",
        notes="left wall",
        created_at="2026-10-05T00:00:00+00:00",
    )
    reading = TachometerReading(
        id="tach_1",
        vent_id=vent.id,
        site_id="site_1",
        value=900,
        unit=UNIT_RPM,
        recorded_at="2026-10-05T12:00:00+00:00",
        notes="laser",
        vent_label=vent.label,
    )
    assert vent_to_dict(vent)["label"] == "Exhaust A"
    assert reading_to_dict(reading)["unit"] == UNIT_RPM
    assert reading_to_dict(reading)["vent_label"] == "Exhaust A"


@pytest.mark.asyncio
async def test_upsert_vent_and_record_reading_with_timestamp(
    tmp_path, hass: HomeAssistant
) -> None:
    repo = TachometerRepository(hass, path=tmp_path / "communifarm.db")
    await repo.async_setup()
    vent = await repo.async_upsert_vent(
        site_id="site_1",
        label="Fruiting intake left",
        vent_role=VENT_ROLE_INTAKE,
        climate_node_id="climate_fruiting",
    )
    assert vent.label == "Fruiting intake left"
    assert vent.vent_role == VENT_ROLE_INTAKE

    reading = await repo.async_record_reading(
        site_id="site_1",
        vent_id=vent.id,
        value=1450,
        unit=UNIT_RPM,
        recorded_at="2026-10-05T18:30:00+00:00",
        notes="handheld laser tach",
    )
    assert reading.value == 1450
    assert reading.unit == UNIT_RPM
    assert reading.recorded_at == "2026-10-05T18:30:00+00:00"
    assert reading.vent_label == "Fruiting intake left"

    snap = await repo.async_snapshot("site_1")
    assert snap["vent_count"] == 1
    assert snap["last_value"] == 1450
    assert snap["last_vent_label"] == "Fruiting intake left"
    await repo.async_close()


@pytest.mark.asyncio
async def test_upsert_updates_existing_vent_by_label_and_id(
    tmp_path, hass: HomeAssistant
) -> None:
    repo = TachometerRepository(hass, path=tmp_path / "communifarm.db")
    await repo.async_setup()
    first = await repo.async_upsert_vent(
        site_id="site_1",
        label="Circ fan top",
        vent_role=VENT_ROLE_CIRCULATION,
        notes="v1",
    )
    second = await repo.async_upsert_vent(
        site_id="site_1",
        label="circ fan top",
        vent_role=VENT_ROLE_CIRCULATION,
        notes="v2",
        climate_node_id="climate_fruiting",
    )
    assert second.id == first.id
    assert second.notes == "v2"
    assert second.climate_node_id == "climate_fruiting"

    third = await repo.async_upsert_vent(
        site_id="site_1",
        label="Circ fan top renamed",
        vent_role=VENT_ROLE_INTAKE,
        vent_id=first.id,
    )
    assert third.id == first.id
    assert third.label == "Circ fan top renamed"
    assert third.vent_role == VENT_ROLE_INTAKE

    with pytest.raises(ValidationError, match="Unknown vent_id"):
        await repo.async_upsert_vent(
            site_id="site_1",
            label="ghost",
            vent_role=VENT_ROLE_OTHER,
            vent_id="vent_missing",
        )
    await repo.async_close()


@pytest.mark.asyncio
async def test_record_by_label_creates_vent(tmp_path, hass: HomeAssistant) -> None:
    repo = TachometerRepository(hass, path=tmp_path / "communifarm.db")
    await repo.async_setup()
    reading = await repo.async_record_reading(
        site_id="site_1",
        vent_label="Fruiting exhaust right",
        vent_role=VENT_ROLE_EXHAUST,
        value=220,
        unit=UNIT_CFM,
    )
    assert reading.unit == UNIT_CFM
    vents = await repo.async_list_vents("site_1")
    assert len(vents) == 1
    assert vents[0].label == "Fruiting exhaust right"
    await repo.async_close()


@pytest.mark.asyncio
async def test_record_requires_vent_identity_and_rejects_bad_ids(
    tmp_path, hass: HomeAssistant
) -> None:
    repo = TachometerRepository(hass, path=tmp_path / "communifarm.db")
    await repo.async_setup()
    with pytest.raises(ValidationError, match="vent_id or vent_label"):
        await repo.async_record_reading(
            site_id="site_1",
            value=10,
            unit=UNIT_FPM,
        )
    with pytest.raises(ValidationError, match="Unknown vent_id"):
        await repo.async_record_reading(
            site_id="site_1",
            vent_id="vent_nope",
            value=10,
            unit=UNIT_FPM,
        )
    await repo.async_close()


@pytest.mark.asyncio
async def test_rejects_negative_value(tmp_path, hass: HomeAssistant) -> None:
    repo = TachometerRepository(hass, path=tmp_path / "communifarm.db")
    await repo.async_setup()
    with pytest.raises(ValidationError, match="negative"):
        await repo.async_record_reading(
            site_id="site_1",
            vent_label="Bad vent",
            value=-1,
            unit=UNIT_RPM,
        )
    await repo.async_close()


@pytest.mark.asyncio
async def test_actions_and_services_record_and_update_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sample_state: CommunifarmState,
) -> None:
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entry_id = mock_config_entry.entry_id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPSERT_AIR_VENT,
        {
            "label": "Inoculation intake",
            "vent_role": "intake",
            "notes": "door side",
        },
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_TACHOMETER,
        {
            "vent_label": "Inoculation intake",
            "vent_role": "intake",
            "value": 1100,
            "unit": "rpm",
            "recorded_at": "2026-10-06T20:00:00+00:00",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    snap = hass.data[DOMAIN][entry_id]["tachometer_snapshot"]
    assert snap["vent_count"] == 1
    assert snap["last_value"] == 1100
    assert snap["last_vent_label"] == "Inoculation intake"

    state = hass.states.get(ENTITY_TACHOMETER_STATUS)
    assert state is not None
    assert "Inoculation intake" in state.state
    assert state.attributes["vent_count"] == 1
    assert state.attributes["last_value"] == 1100

    refreshed = await tachometer_actions.async_refresh_tachometer_snapshot(
        hass, entry_id
    )
    assert refreshed["last_unit"] == "rpm"


@pytest.mark.asyncio
async def test_actions_wrap_validation_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sample_state: CommunifarmState,
) -> None:
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id

    with pytest.raises(HomeAssistantError, match="required"):
        await tachometer_actions.async_upsert_air_vent(
            hass, entry_id, label="  "
        )
    with pytest.raises(HomeAssistantError, match="negative"):
        await tachometer_actions.async_record_tachometer(
            hass,
            entry_id,
            value=-5,
            vent_label="Any vent",
        )

    # Repo slot present but empty -> explicit HA error (not KeyError).
    hass.data[DOMAIN][entry_id]["tachometer_repository"] = None
    with pytest.raises(HomeAssistantError, match="not available"):
        await tachometer_actions.async_upsert_air_vent(
            hass, entry_id, label="x"
        )


def test_mock_package_mentions_services() -> None:
    package = (
        Path(__file__).resolve().parents[1]
        / "devcontainer"
        / "ha_config"
        / "packages"
        / "mock_cf_tachometer.yaml"
    )
    text = package.read_text(encoding="utf-8")
    assert "communifarm.upsert_air_vent" in text
    assert "communifarm.record_tachometer" in text
    assert "cf Tach Vent Label" in text
    assert "cf Tach Timestamp" in text
