"""Production inoculate domain + SQLite + dashboard tests (T0)."""

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
    SERVICE_INOCULATE_BATCH,
    SERVICE_RECORD_HARVEST,
)
from custom_components.communifarm.dashboard.builder import DashboardBuilder
from custom_components.communifarm.domain.culture import (
    FORM_LIQUID_CULTURE,
    SOURCE_PURCHASED,
)
from custom_components.communifarm.domain.production import (
    DEFAULT_MAX_FLUSHES,
    STAGE_COMPLETE,
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INCUBATING,
    STAGE_INOCULATED,
    STAGE_TRANSITIONS,
    InoculateSpec,
    assert_can_advance,
    assert_can_harvest,
    assert_can_inoculate,
    format_production_markdown,
    validate_inoculate_spec,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.batch_repository import BatchRepository
from custom_components.communifarm.storage.culture_repository import CultureRepository


def test_stage_transitions_locked() -> None:
    assert STAGE_TRANSITIONS[STAGE_INOCULATED] == frozenset({STAGE_INCUBATING})
    assert STAGE_TRANSITIONS[STAGE_INCUBATING] == frozenset({STAGE_FRUITING})
    assert STAGE_TRANSITIONS[STAGE_FRUITING] == frozenset({STAGE_HARVESTING})
    assert STAGE_TRANSITIONS[STAGE_HARVESTING] == frozenset()
    assert DEFAULT_MAX_FLUSHES == 3


def test_gate_rejects_inoculate_during_wet_mix() -> None:
    with pytest.raises(ValidationError, match="finish mix"):
        assert_can_inoculate("wet_mixing")


def test_gate_rejects_inoculate_after_fruiting() -> None:
    with pytest.raises(ValidationError, match="already in production"):
        assert_can_inoculate(STAGE_FRUITING)


def test_gate_allows_inoculate_from_cooling() -> None:
    assert_can_inoculate("cooling")
    assert_can_inoculate("planned")
    assert_can_inoculate(STAGE_INOCULATED)


def test_validate_inoculate_requires_substrate() -> None:
    with pytest.raises(ValidationError, match="substrate_g_per_container"):
        validate_inoculate_spec(
            InoculateSpec(
                culture_id="cult_1",
                container_type="bag",
                container_count=4,
                substrate_g_per_container=0,
            )
        )


def test_advance_gate() -> None:
    assert assert_can_advance(STAGE_INOCULATED) == STAGE_INCUBATING
    with pytest.raises(ValidationError, match="no advance"):
        assert_can_advance(STAGE_HARVESTING)


def test_harvest_gate() -> None:
    with pytest.raises(ValidationError, match="fruiting or harvesting"):
        assert_can_harvest(
            lifecycle_phase=STAGE_INCUBATING,
            flush_count=0,
            max_flushes=3,
            mass_g=100,
            is_final=False,
        )
    assert_can_harvest(
        lifecycle_phase=STAGE_HARVESTING,
        flush_count=0,
        max_flushes=3,
        mass_g=50,
        is_final=False,
    )


def test_format_production_markdown() -> None:
    from custom_components.communifarm.domain.production import ProductionSummary

    text = format_production_markdown(
        ProductionSummary(
            batch_id="batch_a",
            lifecycle_phase=STAGE_INOCULATED,
            culture_id="cult_a",
            container_type="bag",
            container_count=4,
            substrate_g_per_container=2000,
        )
    )
    assert "batch_a" in text
    assert "inoculated" in text


def test_sqlite_migration_v6_adds_production_columns(tmp_path: Path) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    assert version >= 6
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(batches)").fetchall()
    }
    for col in (
        "culture_id",
        "container_type",
        "substrate_g_per_container",
        "inoculum_amount",
        "inoculum_unit",
        "expected_check_at",
        "flush_count",
        "max_flushes",
        "inoculated_at",
        "zone_id",
    ):
        assert col in cols
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "harvest_events" in tables
    ce_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(culture_events)").fetchall()
    }
    assert "batch_id" in ce_cols
    conn.close()


def test_dashboard_includes_production_tab(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    assert len(config["views"]) == 4
    production = next(
        view for view in config["views"] if view.get("path") == "production"
    )
    assert production["title"] == "Production"
    titles = [card.get("title") for card in production["cards"]]
    assert "Inoculate inputs" in titles
    assert "Lifecycle" in titles
    assert "Harvest" in titles
    intro = production["cards"][0]["content"]
    assert "Placement" in intro
    assert "inoculation tent" in intro
    status = next(card for card in production["cards"] if card.get("title") == "Status")
    assert "zone_id" in status["content"]
    assert "area_name" in status["content"]
    inoculate = next(
        card for card in production["cards"] if card.get("title") == "Inoculate inputs"
    )
    ids = [
        row["entity"] if isinstance(row, dict) else row for row in inoculate["entities"]
    ]
    assert "button.communifarm_inoculate_batch" in ids
    assert "select.communifarm_container_type" in ids
    assert "number.communifarm_substrate_g_per_container" in ids


@pytest.mark.asyncio
async def test_happy_path_inoculate_to_final_harvest(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_prod.db"
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
    assert len(cultures) == 1
    culture_id = cultures[0].id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": culture_id,
            "container_type": "bag",
            "container_count": 4,
            "substrate_g_per_container": 2000,
            "inoculum_amount": 10,
            "inoculum_unit": "ml",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    batch_repo: BatchRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "batch_repository"
    ]
    state = hass.data[DOMAIN][mock_config_entry.entry_id]["state"]
    batch = await batch_repo.async_get_batch(state.batch.id)
    assert batch is not None
    assert batch.lifecycle_phase == STAGE_INOCULATED
    assert batch.culture_id == culture_id
    assert batch.container_type == "bag"
    assert batch.substrate_g_per_container == 2000
    assert batch.max_flushes == DEFAULT_MAX_FLUSHES
    assert await batch_repo.async_has_milestone(state.batch.id, "inoculated")

    await hass.services.async_call(
        DOMAIN, SERVICE_ADVANCE_PRODUCTION_STAGE, {}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_ADVANCE_PRODUCTION_STAGE, {}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_ADVANCE_PRODUCTION_STAGE, {}, blocking=True
    )
    await hass.async_block_till_done()
    batch = await batch_repo.async_get_batch(state.batch.id)
    assert batch is not None
    assert batch.lifecycle_phase == STAGE_HARVESTING

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_HARVEST,
        {"mass_g": 120.5, "is_final": True},
        blocking=True,
    )
    await hass.async_block_till_done()
    batch = await batch_repo.async_get_batch(state.batch.id)
    assert batch is not None
    assert batch.lifecycle_phase == STAGE_COMPLETE
    assert batch.status == "complete"
    harvests = await batch_repo.async_list_harvests(state.batch.id)
    assert len(harvests) == 1
    assert harvests[0].mass_g == 120.5
    assert harvests[0].is_final is True
    assert harvests[0].flush_number == 1


@pytest.mark.asyncio
async def test_inoculate_rejects_unknown_culture(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_unknown.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError, match="unknown culture_id"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_INOCULATE_BATCH,
            {
                "culture_id": "cult_missing",
                "container_type": "tub",
                "container_count": 2,
                "substrate_g_per_container": 1500,
            },
            blocking=True,
        )
