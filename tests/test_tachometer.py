"""Tests for manual vent tachometer / air-exchange logging."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant

from custom_components.communifarm.domain.tachometer import (
    UNIT_CFM,
    UNIT_RPM,
    VENT_ROLE_EXHAUST,
    VENT_ROLE_INTAKE,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.tachometer_repository import (
    TachometerRepository,
)


@pytest.mark.asyncio
async def test_schema_v13_creates_tachometer_tables(tmp_path, hass: HomeAssistant) -> None:
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
