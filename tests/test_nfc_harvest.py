"""NFC resolve / check-in + per-container harvest (schema v9) — T0."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_ACQUIRE_CULTURE,
    SERVICE_ADVANCE_PRODUCTION_STAGE,
    SERVICE_CHECK_IN,
    SERVICE_INOCULATE_BATCH,
    SERVICE_RECORD_CONTAINER_HARVEST,
    SERVICE_RESOLVE_NFC,
)
from custom_components.communifarm.dashboard.builder import DashboardBuilder
from custom_components.communifarm.domain.container import (
    apply_container_harvest,
    build_containers_for_inoculate,
    require_confirm,
)
from custom_components.communifarm.domain.culture import (
    FORM_LIQUID_CULTURE,
    SOURCE_PURCHASED,
)
from custom_components.communifarm.domain.nfc import ACTIVITY_HARVEST, OBJECT_CONTAINER
from custom_components.communifarm.domain.production import (
    STAGE_COMPLETE,
    STAGE_FRUITING,
    STAGE_HARVESTING,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.batch_repository import BatchRepository
from custom_components.communifarm.storage.container_repository import ContainerRepository
from custom_components.communifarm.storage.culture_repository import CultureRepository


def test_require_confirm() -> None:
    with pytest.raises(ValidationError, match="confirm=true"):
        require_confirm(False)
    require_confirm(True)


def test_build_containers_for_inoculate() -> None:
    containers = build_containers_for_inoculate(
        batch_id="batch_1",
        container_type="block",
        container_count=3,
        max_flushes=3,
        zone_id="zone_a",
        created_at="2026-09-27T00:00:00+00:00",
    )
    assert len(containers) == 3
    assert containers[0].container_index == 1
    assert containers[2].nfc_uid == containers[2].id
    assert containers[1].zone_id == "zone_a"


def test_apply_container_harvest_returns_to_fruiting() -> None:
    containers = build_containers_for_inoculate(
        batch_id="batch_1",
        container_type="block",
        container_count=1,
        max_flushes=3,
        zone_id=None,
        created_at="t0",
    )
    cont = containers[0]
    cont.lifecycle_phase = STAGE_FRUITING
    updated = apply_container_harvest(
        cont, mass_g=120.0, is_final=False, return_to_fruiting=True
    )
    assert updated.flush_count == 1
    assert updated.lifecycle_phase == STAGE_FRUITING
    assert updated.status == "active"


def test_apply_container_harvest_final_completes() -> None:
    containers = build_containers_for_inoculate(
        batch_id="batch_1",
        container_type="block",
        container_count=1,
        max_flushes=3,
        zone_id=None,
        created_at="t0",
    )
    cont = containers[0]
    cont.lifecycle_phase = STAGE_HARVESTING
    cont.flush_count = 2
    updated = apply_container_harvest(cont, mass_g=50.0, is_final=True)
    assert updated.lifecycle_phase == STAGE_COMPLETE
    assert updated.status == "complete"
    assert updated.flush_count == 3


def test_sqlite_migration_v9_containers(tmp_path: Path) -> None:
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
    assert "production_containers" in tables
    assert "nfc_checkins" in tables
    assert "sale_packs" in tables
    assert "sales" in tables
    harvest_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(harvest_events)").fetchall()
    }
    assert "container_id" in harvest_cols
    conn.close()


def test_dashboard_includes_harvest_tab(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    assert len(config["views"]) == 9
    harvest = next(v for v in config["views"] if v.get("path") == "harvest")
    production = next(v for v in config["views"] if v.get("path") == "production")
    assert harvest["title"] == "Harvest"
    titles = [c.get("title") for c in harvest["cards"]]
    assert "Batch harvest" in titles
    assert "Harvest" in titles
    assert "Fridge / bagging (residential)" in titles
    assert "NFC + confirm" not in titles

    harvest_card = next(c for c in harvest["cards"] if c.get("title") == "Harvest")
    production_card = next(
        c for c in production["cards"] if c.get("title") == "Harvest"
    )
    assert harvest_card["entities"] == production_card["entities"]
    entity_ids = [
        row["entity"] if isinstance(row, dict) else row
        for row in harvest_card["entities"]
    ]
    assert entity_ids == [
        "number.communifarm_harvest_mass_g",
        "button.communifarm_record_harvest",
        "button.communifarm_final_harvest",
    ]


@pytest.mark.asyncio
async def test_nfc_resolve_checkin_container_harvest(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_nfc.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
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

    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": culture_id,
            "container_type": "block",
            "container_count": 2,
            "substrate_g_per_container": 1500.0,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    container_repo: ContainerRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "container_repository"
    ]
    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    containers = await container_repo.async_list_for_batch(state.batch.id)
    assert len(containers) == 2
    target = containers[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADVANCE_PRODUCTION_STAGE,
        {"target_stage": "incubating"},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADVANCE_PRODUCTION_STAGE,
        {"target_stage": "fruiting"},
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RESOLVE_NFC,
        {"nfc_uid": target.nfc_uid},
        blocking=True,
    )
    session = hass.data[DOMAIN][mock_config_entry.entry_id]["nfc_session"]
    assert session["found"] is True
    assert session["object_type"] == OBJECT_CONTAINER
    assert session["object_id"] == target.id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_IN,
        {"activity": ACTIVITY_HARVEST, "nfc_uid": target.nfc_uid},
        blocking=True,
    )
    await hass.async_block_till_done()
    session = hass.data[DOMAIN][mock_config_entry.entry_id]["nfc_session"]
    assert session["activity"] == ACTIVITY_HARVEST
    assert session.get("container_id") == target.id

    with pytest.raises(HomeAssistantError, match="confirm=true"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RECORD_CONTAINER_HARVEST,
            {"mass_g": 88.0, "confirm": False},
            blocking=True,
        )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_CONTAINER_HARVEST,
        {"mass_g": 88.0, "confirm": True, "return_to_fruiting": True},
        blocking=True,
    )
    await hass.async_block_till_done()

    refreshed = await container_repo.async_get(target.id)
    assert refreshed is not None
    assert refreshed.flush_count == 1
    assert refreshed.lifecycle_phase == STAGE_FRUITING

    harvests = await batch_repo.async_list_harvests(state.batch.id)
    assert len(harvests) == 1
    assert harvests[0].container_id == target.id
    assert harvests[0].mass_g == 88.0
