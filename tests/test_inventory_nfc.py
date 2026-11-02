"""Inventory NFC write / dual-lot UUID / water mapping coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_CONFIRM_NFC_WRITE,
    SERVICE_CREATE_INVENTORY_LOT,
    SERVICE_PREPARE_NFC_WRITE,
    SERVICE_RESOLVE_NFC,
)
from custom_components.communifarm.domain.inventory import (
    OBJECT_INVENTORY,
    NdefIdentity,
    recipe_ingredient_key,
    water_kind_from_label,
)


def test_water_labels_map_to_recipe_key() -> None:
    assert recipe_ingredient_key("water (tap)") == "water"
    assert recipe_ingredient_key("water (warm, filtered)") == "water"
    assert recipe_ingredient_key("hardwood pellets") == "hardwood_pellets"
    assert water_kind_from_label("water (filtered)") == "filtered"


def test_ndef_identity_roundtrip_stable_ref() -> None:
    payload = NdefIdentity(
        object_type=OBJECT_INVENTORY,
        object_id="inv_abc123",
        label="hardwood pellets",
        ingredient_key="hardwood_pellets",
    ).to_payload()
    data = json.loads(payload)
    assert data["t"] == "inventory"
    assert data["id"] == "inv_abc123"
    assert data["uri"] == "cf://inventory/inv_abc123"
    assert "hardwood pellets" in data["n"]


@pytest.fixture
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "communifarm_inventory.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: path,
    )
    return path


@pytest.mark.asyncio
async def test_create_inventory_lot_new_uuid_same_name(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, isolated_db: Path
) -> None:
    """Two oak-pellet bags share a name but get distinct Communifarm UUIDs."""
    del isolated_db
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_INVENTORY_LOT,
        {"label": "hardwood pellets"},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_INVENTORY_LOT,
        {"label": "hardwood pellets"},
        blocking=True,
    )
    inv = hass.data[DOMAIN][mock_config_entry.entry_id]["inventory_repository"]
    lots = await inv.async_list_lots(
        hass.data[DOMAIN][mock_config_entry.entry_id]["state"].site.id,
        ingredient_key="hardwood_pellets",
    )
    assert len(lots) >= 2
    assert lots[0].label == lots[1].label == "hardwood pellets"
    assert lots[0].id != lots[1].id
    assert lots[0].ndef_payload and "cf://inventory/" in lots[0].ndef_payload


@pytest.mark.asyncio
async def test_prepare_and_confirm_nfc_write_binds_chip(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, isolated_db: Path
) -> None:
    del isolated_db
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_INVENTORY_LOT,
        {"label": "hardwood pellets"},
        blocking=True,
    )
    inv = hass.data[DOMAIN][mock_config_entry.entry_id]["inventory_repository"]
    site_id = hass.data[DOMAIN][mock_config_entry.entry_id]["state"].site.id
    lots = await inv.async_list_lots(site_id, ingredient_key="hardwood_pellets")
    lot = lots[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_PREPARE_NFC_WRITE,
        {
            "object_type": "inventory",
            "object_id": lot.id,
        },
        blocking=True,
    )
    pending = hass.data[DOMAIN][mock_config_entry.entry_id]["pending_nfc_write"]
    assert pending["status"] == "ready"
    assert pending["ndef_payload"]

    hass.states.async_set("sensor.cf_lab_nfc_write01_last_nfc_uid", "04OAKBAG00001")
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CONFIRM_NFC_WRITE,
        {},
        blocking=True,
    )
    updated = await inv.async_get_lot(lot.id)
    assert updated is not None
    assert updated.nfc_uid == "04OAKBAG00001"

    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    pool_row = await bucket["nfc_tag_pool_repository"].async_get_by_uid(
        site_id, "04OAKBAG00001"
    )
    assert pool_row is not None
    assert pool_row.status == "bound"
    assert pool_row.bound_object_id == lot.id
    assert pool_row.bound_object_type == "inventory"

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RESOLVE_NFC,
        {"nfc_uid": "04OAKBAG00001"},
        blocking=True,
    )
    session = bucket["nfc_session"]
    assert session["found"] is True
    assert session["object_type"] == "inventory"
    assert session["object_id"] == lot.id
    assert session.get("scan_event_id")


@pytest.mark.asyncio
async def test_confirm_nfc_write_rejects_without_prepare(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, isolated_db: Path
) -> None:
    del isolated_db
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError, match="prepare_nfc_write"):
        await hass.services.async_call(
            DOMAIN, SERVICE_CONFIRM_NFC_WRITE, {}, blocking=True
        )
