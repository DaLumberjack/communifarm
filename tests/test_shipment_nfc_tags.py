"""Shipment NFC tag pool — CF SQLite seed; sandbox mocks live in packages (T0)."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_IMPORT_NFC_FROM_ENTITY,
    SERVICE_SEED_SHIPMENT_NFC_TAGS,
)
from custom_components.communifarm.domain.shipment_tags import DEFAULT_SHIPMENT_TAGS


@pytest.mark.asyncio
async def test_seed_shipment_tags_fills_pool_and_inventory(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_ship.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN, SERVICE_SEED_SHIPMENT_NFC_TAGS, {}, blocking=True
    )
    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    site_id = bucket["state"].site.id
    pool = await bucket["nfc_tag_pool_repository"].async_list(site_id)
    assert len(pool) == len(DEFAULT_SHIPMENT_TAGS)

    inv = bucket["inventory_repository"]
    pellets = await inv.async_get_lot_by_nfc("nfc-hardwood-pellets")
    assert pellets is not None
    assert pellets.label == "hardwood pellets"

    bags = await bucket["nfc_tag_pool_repository"].async_list(
        site_id, intended_type="container", status="available"
    )
    assert len(bags) >= 5
    assert bucket.get("intake_tag_uid_choice", "").startswith("nfc-bag-01")


@pytest.mark.asyncio
async def test_register_production_block_uses_seeded_tag_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_ship_reg.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    # No live scan entity required — seed sets tag-source choice.
    await hass.services.async_call(
        DOMAIN, SERVICE_SEED_SHIPMENT_NFC_TAGS, {}, blocking=True
    )
    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    from custom_components.communifarm import inventory_actions

    cont = await inventory_actions.async_register_production_block(
        hass, mock_config_entry.entry_id
    )
    assert cont.nfc_uid == "nfc-bag-01"
    listed = await bucket["container_repository"].async_list_for_batch(
        bucket["state"].batch.id
    )
    assert len(listed) == 1
    pool_bag = await bucket["nfc_tag_pool_repository"].async_get_by_uid(
        bucket["state"].site.id, "nfc-bag-01"
    )
    assert pool_bag is not None
    assert pool_bag.status == "bound"
    assert pool_bag.bound_object_id == cont.id
    assert pool_bag.bound_object_type == "container"


@pytest.mark.asyncio
async def test_apply_tag_source_scan_and_badge_use_select(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_tag_scan.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, SERVICE_SEED_SHIPMENT_NFC_TAGS, {}, blocking=True
    )
    await hass.async_block_till_done()
    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    from custom_components.communifarm import inventory_actions
    from custom_components.communifarm.const import SERVICE_APPLY_TAG_SOURCE_SCAN
    from custom_components.communifarm.domain.inventory import OBJECT_EMPLOYEE

    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "")
    # Force tag source to employee (not bag).
    bucket["intake_tag_uid_choice"] = inventory_actions.format_tag_source_option(
        "nfc-employee-01", f"{OBJECT_EMPLOYEE}: Operator kit badge"
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_APPLY_TAG_SOURCE_SCAN, {}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_text.esp32dev_last_nfc_uid").state == "nfc-employee-01"


@pytest.mark.asyncio
async def test_import_nfc_requires_existing_entity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_import.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError, match="not present"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_IMPORT_NFC_FROM_ENTITY,
            {"entity_id": "input_text.does_not_exist_nfc"},
            blocking=True,
        )

    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "nfc-imported-99")
    from custom_components.communifarm import inventory_actions

    imported = await inventory_actions.async_import_nfc_from_entity(
        hass, mock_config_entry.entry_id
    )
    assert imported == "nfc-imported-99"
    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    row = await bucket["nfc_tag_pool_repository"].async_get_by_uid(
        bucket["state"].site.id, "nfc-imported-99"
    )
    assert row is not None
    assert row.intended_type == "container"
