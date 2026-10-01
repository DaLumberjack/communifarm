"""Point of sale / sales tracking (schema v10) — T0."""

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
    SERVICE_RECORD_SALE,
    SERVICE_RECORD_SALE_CLEANUP,
)
from custom_components.communifarm.dashboard.builder import DashboardBuilder
from custom_components.communifarm.domain.container import SalePack
from custom_components.communifarm.domain.culture import (
    FORM_LIQUID_CULTURE,
    SOURCE_PURCHASED,
)
from custom_components.communifarm.domain.sale import (
    PAYMENT_CASH,
    PAYMENT_VENMO,
    validate_payment_method,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.batch_repository import BatchRepository
from custom_components.communifarm.storage.container_repository import (
    ContainerRepository,
)
from custom_components.communifarm.storage.culture_repository import CultureRepository
from custom_components.communifarm.storage.sale_repository import SaleRepository


def test_validate_payment_method() -> None:
    assert validate_payment_method("Cash") == PAYMENT_CASH
    with pytest.raises(ValidationError):
        validate_payment_method("bitcoin")


def test_sqlite_migration_v10_sales(tmp_path: Path) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    version = sqlite_db.apply_migrations(conn)
    assert version == 10
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "sales" in tables
    assert "sale_line_items" in tables
    assert "sale_cleanup_events" in tables
    pack_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(sale_packs)").fetchall()
    }
    assert "sold_sale_id" in pack_cols
    conn.close()


def test_dashboard_includes_pos_tab(sample_state) -> None:
    config = DashboardBuilder().build(sample_state, {})
    assert len(config["views"]) == 6
    pos = next(v for v in config["views"] if v.get("path") == "pos")
    assert pos["title"] == "POS"
    titles = [c.get("title") for c in pos["cards"]]
    assert "Point of sale" in titles
    assert "Sale draft" in titles
    assert "Submit" in titles
    overview = config["views"][0]["cards"][0]["content"]
    assert "POS" in overview


async def _seed_harvest(
    hass: HomeAssistant,
    entry_id: str,
) -> tuple[str, str]:
    """Inoculate → fruiting → harvest; return (culture unused, harvest_id)."""
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "POS LC",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "container": "jar",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    culture_repo: CultureRepository = hass.data[DOMAIN][entry_id]["culture_repository"]
    culture_id = (await culture_repo.async_list_cultures())[0].id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": culture_id,
            "container_type": "block",
            "container_count": 1,
            "substrate_g_per_container": 1500.0,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    for stage in ("incubating", "fruiting", "harvesting"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ADVANCE_PRODUCTION_STAGE,
            {"target_stage": stage},
            blocking=True,
        )
        await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_HARVEST,
        {"mass_g": 250.0, "is_final": False},
        blocking=True,
    )
    await hass.async_block_till_done()
    batch_repo: BatchRepository = hass.data[DOMAIN][entry_id]["batch_repository"]
    state = hass.data[DOMAIN][entry_id]["state"]
    harvests = await batch_repo.async_list_harvests(state.batch.id)
    assert harvests
    return culture_id, harvests[-1].id


@pytest.mark.asyncio
async def test_record_sale_weigh_at_sale_updates_db_and_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_pos.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    _, harvest_id = await _seed_harvest(hass, mock_config_entry.entry_id)

    sensor = hass.states.get("sensor.communifarm_sales_status")
    assert sensor is not None
    assert sensor.state == "idle"

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_SALE,
        {
            "venue_label": "Farmers market",
            "buyer_label": "Walk-up",
            "payment_method": PAYMENT_VENMO,
            "line_amount": 12.5,
            "confirm": True,
            "harvest_id": harvest_id,
            "mass_g": 88.0,
            "product_label": "Blue oyster",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    sale_repo: SaleRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "sale_repository"
    ]
    sales = await sale_repo.async_list_sales()
    assert len(sales) == 1
    assert sales[0].venue_label == "Farmers market"
    assert sales[0].buyer_label == "Walk-up"
    assert sales[0].payment_method == PAYMENT_VENMO
    assert sales[0].total_amount == 12.5

    lines = await sale_repo.async_list_lines_for_sale(sales[0].id)
    assert len(lines) == 1
    assert lines[0].mass_g == 88.0
    assert lines[0].harvest_id == harvest_id
    assert lines[0].product_label == "Blue oyster"

    container_repo: ContainerRepository = hass.data[DOMAIN][
        mock_config_entry.entry_id
    ]["container_repository"]
    pack = await container_repo.async_get_sale_pack(lines[0].sale_pack_id)
    assert pack is not None
    assert pack.status == "sold"
    assert pack.sold_sale_id == sales[0].id

    sensor = hass.states.get("sensor.communifarm_sales_status")
    assert sensor is not None
    assert sensor.state == sales[0].id
    assert "Farmers market" in sensor.attributes["progress_text"]
    assert sensor.attributes["sale_count"] == 1


@pytest.mark.asyncio
async def test_record_sale_prepacked_pack(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_pos_pack.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    _, harvest_id = await _seed_harvest(hass, mock_config_entry.entry_id)
    container_repo: ContainerRepository = hass.data[DOMAIN][
        mock_config_entry.entry_id
    ]["container_repository"]
    pack = SalePack(
        harvest_id=harvest_id,
        mass_g=120.0,
        size_label="pint",
        status="open",
        created_at="2026-09-30T00:00:00+00:00",
    )
    await container_repo.async_insert_sale_pack(pack)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_SALE,
        {
            "venue_label": "Farm stand",
            "buyer_label": "CSA member",
            "payment_method": PAYMENT_CASH,
            "line_amount": 8.0,
            "confirm": True,
            "sale_pack_id": pack.id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    sold = await container_repo.async_get_sale_pack(pack.id)
    assert sold is not None
    assert sold.status == "sold"

    with pytest.raises(HomeAssistantError, match="not open"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RECORD_SALE,
            {
                "venue_label": "Farm stand",
                "buyer_label": "CSA member",
                "payment_method": PAYMENT_CASH,
                "line_amount": 8.0,
                "confirm": True,
                "sale_pack_id": pack.id,
            },
            blocking=True,
        )


@pytest.mark.asyncio
async def test_record_sale_requires_confirm(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_pos_confirm.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    _, harvest_id = await _seed_harvest(hass, mock_config_entry.entry_id)

    with pytest.raises(HomeAssistantError, match="confirm=true"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RECORD_SALE,
            {
                "venue_label": "Farmers market",
                "buyer_label": "Walk-up",
                "payment_method": PAYMENT_CASH,
                "line_amount": 5.0,
                "confirm": False,
                "harvest_id": harvest_id,
                "mass_g": 50.0,
            },
            blocking=True,
        )


@pytest.mark.asyncio
async def test_record_sale_cleanup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_pos_cleanup.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    _, harvest_id = await _seed_harvest(hass, mock_config_entry.entry_id)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_SALE,
        {
            "venue_label": "Farmers market",
            "buyer_label": "Walk-up",
            "payment_method": PAYMENT_CASH,
            "line_amount": 9.0,
            "confirm": True,
            "harvest_id": harvest_id,
            "mass_g": 40.0,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_SALE_CLEANUP,
        {"cleaned": True, "put_away": True, "ready_next": True},
        blocking=True,
    )
    await hass.async_block_till_done()

    sale_repo: SaleRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "sale_repository"
    ]
    cleanups = await sale_repo.async_list_cleanups()
    assert len(cleanups) == 1
    assert "cleaned" in cleanups[0].checklist_json

    sensor = hass.states.get("sensor.communifarm_sales_status")
    assert sensor is not None
    assert "cleanup" in sensor.attributes["progress_text"].lower()
