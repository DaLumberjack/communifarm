"""Varieties catalog + LC/grain vessel states (schema v11) — T0."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_ACQUIRE_CULTURE,
    SERVICE_CREATE_VARIETY,
    SERVICE_RETIRE_VARIETY,
    SERVICE_SET_CULTURE_STATUS,
)
from custom_components.communifarm.dashboard.builder import DashboardBuilder
from custom_components.communifarm.domain.culture import (
    CULTURE_STATUS_DRAWING,
    CULTURE_STATUS_READY,
    FORM_GRAIN_SPAWN,
    FORM_LIQUID_CULTURE,
    SEED_VARIETIES,
    SOURCE_PURCHASED,
)
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.culture_repository import CultureRepository


def test_sqlite_migration_v11_varieties(tmp_path: Path) -> None:
    path = tmp_path / "v11.db"
    conn = sqlite_db.connect(path)
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "varieties" in tables
    cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(culture_lots)").fetchall()
    }
    assert "variety_id" in cols
    conn.close()


def test_dashboard_includes_culture_tab(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    culture = next(v for v in config["views"] if v.get("path") == "culture")
    assert culture["title"] == "Culture"
    titles = [c.get("title") for c in culture["cards"]]
    assert "Variety catalog" in titles
    assert "Acquire vessel" in titles
    assert "Vessel status" in titles


@pytest.mark.asyncio
async def test_seed_varieties_and_custom_crud(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_varieties.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    varieties = await repo.async_list_varieties()
    assert len(varieties) >= len(SEED_VARIETIES)
    names = {v.name for v in varieties}
    assert "Chestnut" in names
    assert "Golden Teacher" in names

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_VARIETY,
        {"name": "Lions Mane"},
        blocking=True,
    )
    await hass.async_block_till_done()
    custom = await repo.async_get_variety_by_name("Lions Mane")
    assert custom is not None
    assert custom.is_seed is False

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RETIRE_VARIETY,
        {"variety_id": custom.id},
        blocking=True,
    )
    await hass.async_block_till_done()
    retired = await repo.async_get_variety(custom.id)
    assert retired is not None
    assert retired.status == "retired"

    seed = await repo.async_get_variety_by_name("Chestnut")
    assert seed is not None
    with pytest.raises(HomeAssistantError, match="seed"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RETIRE_VARIETY,
            {"variety_id": seed.id},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_acquire_lc_and_grain_with_variety_and_status(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_vessels.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    chestnut = await repo.async_get_variety_by_name("Chestnut")
    assert chestnut is not None

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "variety_id": chestnut.id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    lots = await repo.async_list_cultures()
    lc = next(lot for lot in lots if lot.variety_id == chestnut.id)
    assert lc.name == "Chestnut"
    assert lc.status == CULTURE_STATUS_READY
    assert lc.form == FORM_LIQUID_CULTURE
    assert hass.data[DOMAIN][mock_config_entry.entry_id]["active_culture_id"] == lc.id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_CULTURE_STATUS,
        {"status": CULTURE_STATUS_DRAWING, "culture_id": lc.id},
        blocking=True,
    )
    await hass.async_block_till_done()
    updated = await repo.async_get_culture(lc.id)
    assert updated is not None
    assert updated.status == CULTURE_STATUS_DRAWING

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "source_type": SOURCE_PURCHASED,
            "form": FORM_GRAIN_SPAWN,
            "variety_name": "Blue oyster",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    grain = next(
        lot
        for lot in await repo.async_list_cultures()
        if lot.form == FORM_GRAIN_SPAWN
    )
    assert grain.name == "Blue oyster"
    assert grain.status == CULTURE_STATUS_READY

    select_state = hass.states.get("select.communifarm_active_inoculum")
    assert select_state is not None
    assert any("Chestnut" in opt for opt in select_state.attributes.get("options", []))

    inv = hass.states.get("sensor.communifarm_culture_inventory")
    assert inv is not None
    assert "Chestnut" in inv.attributes.get("list_text", "")
