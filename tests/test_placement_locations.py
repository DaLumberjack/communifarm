"""Placement areas / zones (schema v7) — T0 tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_ACQUIRE_CULTURE,
    SERVICE_ENSURE_PLACEMENT_LAYOUT,
    SERVICE_INOCULATE_BATCH,
    SERVICE_RECORD_HARVEST,
    SERVICE_SET_BATCH_LOCATION,
)
from custom_components.communifarm.domain.culture import (
    FORM_LIQUID_CULTURE,
    SOURCE_PURCHASED,
)
from custom_components.communifarm.domain.location import (
    AREA_FRUITING_TENT,
    AREA_HARVEST_FRIDGE,
    AREA_INOCULATION_TENT,
    DEFAULT_LAYOUT,
    build_default_layout,
    suggest_area_kind_for_production_stage,
    validate_zone_index,
)
from custom_components.communifarm.domain.production import (
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INCUBATING,
    STAGE_INOCULATED,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.batch_repository import BatchRepository
from custom_components.communifarm.storage.culture_repository import CultureRepository
from custom_components.communifarm.storage.location_repository import LocationRepository


def test_default_layout_counts() -> None:
    layout = build_default_layout("site_test")
    assert len(layout.areas) == 5
    assert len(layout.zones) == 5 + 5 + 5 + 3 + 6
    assert sum(row[3] for row in DEFAULT_LAYOUT) == 24
    kinds = {a.area_kind for a in layout.areas}
    assert AREA_FRUITING_TENT in kinds
    assert AREA_INOCULATION_TENT in kinds
    assert AREA_HARVEST_FRIDGE in kinds


def test_validate_zone_index() -> None:
    assert validate_zone_index(1, 5) == 1
    assert validate_zone_index(5, 5) == 5
    with pytest.raises(ValidationError, match="between 1 and"):
        validate_zone_index(0, 5)
    with pytest.raises(ValidationError, match="between 1 and"):
        validate_zone_index(6, 5)


def test_suggest_area_kind_for_production_stage() -> None:
    assert (
        suggest_area_kind_for_production_stage(STAGE_INOCULATED)
        == AREA_INOCULATION_TENT
    )
    assert (
        suggest_area_kind_for_production_stage(STAGE_INCUBATING)
        == AREA_INOCULATION_TENT
    )
    assert suggest_area_kind_for_production_stage(STAGE_FRUITING) == AREA_FRUITING_TENT
    assert (
        suggest_area_kind_for_production_stage(STAGE_HARVESTING) == AREA_FRUITING_TENT
    )
    assert suggest_area_kind_for_production_stage("planned") is None


def test_sqlite_migration_v7_placement(tmp_path: Path) -> None:
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
    assert "placement_areas" in tables
    assert "zones" in tables
    batch_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(batches)").fetchall()
    }
    assert "zone_id" in batch_cols
    harvest_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(harvest_events)").fetchall()
    }
    assert "zone_id" in harvest_cols
    conn.close()


@pytest.mark.asyncio
async def test_ensure_default_layout_persists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_layout.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    zones = await loc_repo.async_list_zones(state.site.id)
    assert len(areas) == 5
    assert len(zones) == 24

    await hass.services.async_call(
        DOMAIN, SERVICE_ENSURE_PLACEMENT_LAYOUT, {}, blocking=True
    )
    await hass.async_block_till_done()
    areas2 = await loc_repo.async_list_areas(state.site.id)
    zones2 = await loc_repo.async_list_zones(state.site.id)
    assert len(areas2) == 5
    assert len(zones2) == 24
    assert {a.id for a in areas} == {a.id for a in areas2}


@pytest.mark.asyncio
async def test_set_batch_location_persists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_set_zone.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    inoc = next(a for a in areas if a.area_kind == AREA_INOCULATION_TENT)
    zones = await loc_repo.async_list_zones_for_area(inoc.id)
    zone = zones[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_BATCH_LOCATION,
        {"zone_id": zone.id},
        blocking=True,
    )
    await hass.async_block_till_done()
    batch = await batch_repo.async_get_batch(state.batch.id)
    assert batch is not None
    assert batch.zone_id == zone.id


@pytest.mark.asyncio
async def test_inoculate_with_zone_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_inoc_zone.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Lab LC",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "container": "jar",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    culture_repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    cultures = await culture_repo.async_list_cultures()
    culture_id = cultures[0].id

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    inoc = next(a for a in areas if a.area_kind == AREA_INOCULATION_TENT)
    zone = (await loc_repo.async_list_zones_for_area(inoc.id))[2]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": culture_id,
            "container_type": "bag",
            "container_count": 2,
            "substrate_g_per_container": 1800,
            "zone_id": zone.id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    batch = await batch_repo.async_get_batch(state.batch.id)
    assert batch is not None
    assert batch.lifecycle_phase == STAGE_INOCULATED
    assert batch.zone_id == zone.id


@pytest.mark.asyncio
async def test_harvest_with_zone_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_harv_zone.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Lab LC",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "container": "jar",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    culture_repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    culture_id = (await culture_repo.async_list_cultures())[0].id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": culture_id,
            "container_type": "tub",
            "container_count": 1,
            "substrate_g_per_container": 1500,
        },
        blocking=True,
    )
    from custom_components.communifarm.const import SERVICE_ADVANCE_PRODUCTION_STAGE

    for _ in range(3):
        await hass.services.async_call(
            DOMAIN, SERVICE_ADVANCE_PRODUCTION_STAGE, {}, blocking=True
        )
    await hass.async_block_till_done()

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    fridge = next(a for a in areas if a.area_kind == AREA_HARVEST_FRIDGE)
    shelf = (await loc_repo.async_list_zones_for_area(fridge.id))[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_HARVEST,
        {"mass_g": 88.0, "is_final": True, "zone_id": shelf.id},
        blocking=True,
    )
    await hass.async_block_till_done()

    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    harvests = await batch_repo.async_list_harvests(state.batch.id)
    assert len(harvests) == 1
    assert harvests[0].zone_id == shelf.id
    assert harvests[0].mass_g == 88.0
