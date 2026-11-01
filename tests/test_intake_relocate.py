"""Intake scan mode + purchase fields + relocate location select (T0)."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_CREATE_INVENTORY_LOT,
    SERVICE_RESOLVE_NFC,
)


@pytest.mark.asyncio
async def test_create_inventory_lot_persists_purchase_fields(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_intake.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    bucket["intake_amount"] = 25.0
    bucket["intake_amount_unit"] = "kg"
    bucket["intake_cost"] = 42.5
    bucket["intake_payment_location"] = "account"
    bucket["intake_purchase_location"] = "Feed store"
    bucket["intake_tracked"] = "yes"
    bucket["intake_receipt_tracked"] = "yes"
    bucket["intake_purchase_date"] = "2026-10-18"

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_INVENTORY_LOT,
        {"label": "hardwood pellets"},
        blocking=True,
    )
    inv = bucket["inventory_repository"]
    lots = await inv.async_list_lots(bucket["state"].site.id)
    assert len(lots) >= 1
    lot = next(item for item in lots if item.label == "hardwood pellets")
    assert lot.amount == 25.0
    assert lot.amount_unit == "kg"
    assert lot.cost == 42.5
    assert lot.payment_location == "account"
    assert lot.purchase_location == "Feed store"
    assert lot.tracked is True
    assert lot.receipt_tracked is True
    assert lot.purchase_date == "2026-10-18"


@pytest.mark.asyncio
async def test_scan_mode_registers_production_block(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_block.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    bucket["nfc_scan_mode"] = "register_production_block"
    uid = "04PRODBLOCK0001"
    hass.states.async_set("input_text.esp32dev_last_nfc_uid", uid)

    await hass.services.async_call(DOMAIN, SERVICE_RESOLVE_NFC, {}, blocking=True)
    conts = await bucket["container_repository"].async_list_for_batch(
        bucket["state"].batch.id
    )
    assert len(conts) == 1
    assert conts[0].nfc_uid == uid
    assert bucket["nfc_scan_mode"] == "normal"


@pytest.mark.asyncio
async def test_badge_rejects_empty_nfc_clearly(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.communifarm.const import SERVICE_COMPLETE_MIX_STEP_FROM_BADGE

    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_badge_empty.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "")
    # Empty weigh → dry weighing gate before NFC is even consulted.
    with pytest.raises(HomeAssistantError, match="dry weighing"):
        await hass.services.async_call(
            DOMAIN, SERVICE_COMPLETE_MIX_STEP_FROM_BADGE, {}, blocking=True
        )
