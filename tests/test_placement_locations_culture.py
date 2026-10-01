"""Culture / media placement zones (schema v8) — T0 tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_ACQUIRE_CULTURE,
    SERVICE_CREATE_MEDIA_BATCH,
    SERVICE_SET_CULTURE_LOCATION,
    SERVICE_SET_MEDIA_LOCATION,
)
from custom_components.communifarm.domain.culture import (
    FORM_AGAR,
    FORM_LIQUID_CULTURE,
    MEDIA_STATUS_PLANNED,
    MEDIA_STATUS_READY,
    MEDIA_STATUS_WEIGHING,
    SOURCE_PURCHASED,
)
from custom_components.communifarm.domain.location import (
    AREA_CULTURE_FRIDGE,
    AREA_STILL_AIR_CABINET,
    suggest_area_kind_for_culture_form,
    suggest_area_kind_for_media_status,
)
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.culture_repository import CultureRepository
from custom_components.communifarm.storage.location_repository import LocationRepository


def test_suggest_area_kind_for_culture_form() -> None:
    assert suggest_area_kind_for_culture_form(FORM_AGAR) == AREA_CULTURE_FRIDGE
    assert (
        suggest_area_kind_for_culture_form(FORM_LIQUID_CULTURE) == AREA_CULTURE_FRIDGE
    )
    assert suggest_area_kind_for_culture_form("spores") == AREA_CULTURE_FRIDGE
    assert suggest_area_kind_for_culture_form("unknown") is None


def test_suggest_area_kind_for_media_status() -> None:
    assert (
        suggest_area_kind_for_media_status(MEDIA_STATUS_PLANNED)
        == AREA_STILL_AIR_CABINET
    )
    assert (
        suggest_area_kind_for_media_status(MEDIA_STATUS_WEIGHING)
        == AREA_STILL_AIR_CABINET
    )
    assert suggest_area_kind_for_media_status(MEDIA_STATUS_READY) == AREA_CULTURE_FRIDGE
    assert suggest_area_kind_for_media_status("complete") is None


def test_sqlite_migration_v8_culture_media_zones(tmp_path: Path) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    culture_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(culture_lots)").fetchall()
    }
    media_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(media_batches)").fetchall()
    }
    assert "zone_id" in culture_cols
    assert "zone_id" in media_cols
    indexes = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert "idx_culture_lots_zone" in indexes
    assert "idx_media_batches_zone" in indexes
    conn.close()


def _patch_db(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )


@pytest.mark.asyncio
async def test_acquire_culture_with_zone_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_db(monkeypatch, tmp_path / "communifarm_acq_zone.db")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    fridge = next(a for a in areas if a.area_kind == AREA_CULTURE_FRIDGE)
    shelf = (await loc_repo.async_list_zones_for_area(fridge.id))[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Fridge LC",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "container": "jar",
            "zone_id": shelf.id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    culture_repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    lot = (await culture_repo.async_list_cultures())[0]
    assert lot.zone_id == shelf.id


@pytest.mark.asyncio
async def test_set_culture_location_moves_lot(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_db(monkeypatch, tmp_path / "communifarm_set_culture_zone.db")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Move me",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_AGAR,
            "container": "plate",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    culture_repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    lot = (await culture_repo.async_list_cultures())[0]
    assert lot.zone_id is None

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    fridge = next(a for a in areas if a.area_kind == AREA_CULTURE_FRIDGE)
    shelf = (await loc_repo.async_list_zones_for_area(fridge.id))[2]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_CULTURE_LOCATION,
        {"culture_id": lot.id, "zone_id": shelf.id},
        blocking=True,
    )
    await hass.async_block_till_done()

    moved = await culture_repo.async_get_culture(lot.id)
    assert moved is not None
    assert moved.zone_id == shelf.id


@pytest.mark.asyncio
async def test_create_media_batch_with_zone_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_db(monkeypatch, tmp_path / "communifarm_media_zone.db")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    sab = next(a for a in areas if a.area_kind == AREA_STILL_AIR_CABINET)
    shelf = (await loc_repo.async_list_zones_for_area(sab.id))[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_MEDIA_BATCH,
        {"recipe_key": "mea_agar_500", "zone_id": shelf.id},
        blocking=True,
    )
    await hass.async_block_till_done()

    culture_repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    media = (await culture_repo.async_list_media_batches())[0]
    assert media.zone_id == shelf.id


@pytest.mark.asyncio
async def test_set_media_location(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_db(monkeypatch, tmp_path / "communifarm_set_media_zone.db")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN, SERVICE_CREATE_MEDIA_BATCH, {"recipe_key": "honey_lc_500"}, blocking=True
    )
    await hass.async_block_till_done()

    culture_repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    media = (await culture_repo.async_list_media_batches())[0]

    loc_repo: LocationRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "location_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    sab = next(a for a in areas if a.area_kind == AREA_STILL_AIR_CABINET)
    shelf = (await loc_repo.async_list_zones_for_area(sab.id))[1]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_MEDIA_LOCATION,
        {"media_batch_id": media.id, "zone_id": shelf.id},
        blocking=True,
    )
    await hass.async_block_till_done()

    updated = await culture_repo.async_get_media_batch(media.id)
    assert updated is not None
    assert updated.zone_id == shelf.id


@pytest.mark.asyncio
async def test_reject_unknown_zone_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_db(monkeypatch, tmp_path / "communifarm_bad_zone.db")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError, match="unknown zone_id"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ACQUIRE_CULTURE,
            {
                "name": "Bad zone",
                "source_type": SOURCE_PURCHASED,
                "form": FORM_AGAR,
                "zone_id": "zone_does_not_exist",
            },
            blocking=True,
        )
