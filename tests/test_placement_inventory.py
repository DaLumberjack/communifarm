"""Production placement inventory + NFC-scoped lifecycle moves (T0)."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_ACQUIRE_CULTURE,
    SERVICE_ADVANCE_PRODUCTION_STAGE,
    SERVICE_INOCULATE_BATCH,
    SERVICE_RELOCATE_FOR_STERILIZATION,
)
from custom_components.communifarm.domain.placement_inventory import (
    PlacementContainerRow,
    format_placement_inventory_markdown,
)
from custom_components.communifarm.domain.production import STAGE_INCUBATING


def test_format_placement_empty() -> None:
    assert "No bags" in format_placement_inventory_markdown("Storage", [])


def test_format_placement_table() -> None:
    md = format_placement_inventory_markdown(
        "Storage",
        [
            PlacementContainerRow(
                area_kind="storage",
                area_name="Storage",
                zone_name="Shelf 1",
                zone_id="zone_1",
                batch_id="batch_1",
                batch_name="Mix A",
                container_index=2,
                container_type="bag",
                lifecycle_phase="inoculated",
                nfc_uid="nfc-bag-01",
                container_id="cont_1",
            )
        ],
    )
    assert "Shelf 1" in md
    assert "Mix A" in md
    assert "bag #2" in md
    assert "inoculated" in md


@pytest.mark.asyncio
async def test_relocate_lands_containers_in_storage_section(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_place_store.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    bucket = hass.data[DOMAIN][entry_id]

    from custom_components.communifarm import inventory_actions, production_actions

    cont = await inventory_actions.async_register_production_block(
        hass, entry_id, nfc_uid="nfc-bag-place-01"
    )
    labels = await inventory_actions.async_list_zone_option_labels(
        hass, entry_id, area_kind="storage"
    )
    bucket["relocate_zone_label"] = labels[0]
    await hass.services.async_call(
        DOMAIN, SERVICE_RELOCATE_FOR_STERILIZATION, {}, blocking=True
    )
    await hass.async_block_till_done()

    updated = await bucket["container_repository"].async_get(cont.id)
    assert updated is not None and updated.zone_id
    value, markdown, rows = await production_actions.async_placement_section(
        hass, entry_id, "storage", "Storage"
    )
    assert value == "1 units"
    assert any(r["container_id"] == cont.id for r in rows)
    assert "nfc-bag-place-01" in markdown
    cold_val, _, cold_rows = await production_actions.async_placement_section(
        hass, entry_id, "cold_storage", "Cold storage"
    )
    assert cold_val == "0 units"
    assert cold_rows == []


@pytest.mark.asyncio
async def test_advance_with_bag_nfc_moves_only_that_container(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_place_move.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    bucket = hass.data[DOMAIN][entry_id]
    state = bucket["state"]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "LC place",
            "source_type": "purchased",
            "form": "liquid_culture",
            "container": "jar",
        },
        blocking=True,
    )
    culture_id = bucket["active_culture_id"]
    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": culture_id,
            "container_type": "bag",
            "container_count": 2,
            "substrate_g_per_container": 2500,
        },
        blocking=True,
    )
    conts = await bucket["container_repository"].async_list_for_batch(state.batch.id)
    assert len(conts) == 2
    conts[0].nfc_uid = "nfc-bag-move-a"
    conts[1].nfc_uid = "nfc-bag-move-b"
    await bucket["container_repository"].async_update(conts[0])
    await bucket["container_repository"].async_update(conts[1])

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADVANCE_PRODUCTION_STAGE,
        {"target_stage": STAGE_INCUBATING, "nfc_uid": "nfc-bag-move-a"},
        blocking=True,
    )
    a = await bucket["container_repository"].async_get(conts[0].id)
    b = await bucket["container_repository"].async_get(conts[1].id)
    assert a is not None and a.lifecycle_phase == STAGE_INCUBATING
    assert b is not None and b.lifecycle_phase != STAGE_INCUBATING
    assert a.zone_id and a.zone_id != b.zone_id
