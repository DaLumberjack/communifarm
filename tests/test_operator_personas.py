"""Operator personas: 95% scan-first vs 40% dropdown-then-act (T0).

Oracle: mixing-batch + production-inoculate process docs.
95% — last NFC / scan then press lifecycle button.
40% — Tag source dropdown → Scan NFC → press button.
"""

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
    SERVICE_COMPLETE_MIX_STEP_FROM_BADGE,
    SERVICE_INOCULATE_BATCH,
    SERVICE_RELOCATE_FOR_STERILIZATION,
    SERVICE_SEED_SHIPMENT_NFC_TAGS,
)
from custom_components.communifarm.domain.batch_milestones import (
    MILESTONE_COMPLETELY_MIXED,
    MILESTONE_CONTAINERS_SEPARATED,
    MILESTONE_DRY_WET_MIX_STARTED,
    MILESTONE_DRYS_COMBINED,
    MILESTONE_FIELD_CAPACITY_REACHED,
    MILESTONE_REMAINING_WATER_ADDED,
    MILESTONE_SETTLING_STARTED,
    MILESTONE_WATER_ADDED,
)
from custom_components.communifarm.domain.inventory import OBJECT_EMPLOYEE
from custom_components.communifarm.domain.production import (
    STAGE_INCUBATING,
    STAGE_INOCULATED,
)
from custom_components.communifarm.domain.recipe import WOOD_LOVER_RECIPE
from custom_components.communifarm.domain.weight import WeightEvent


async def _setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    db_name: str,
) -> str:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / db_name,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry.entry_id


async def _inoculate_two_bags(hass: HomeAssistant, entry_id: str) -> tuple[str, str]:
    bucket = hass.data[DOMAIN][entry_id]
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Persona LC",
            "source_type": "purchased",
            "form": "liquid_culture",
            "container": "jar",
        },
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": bucket["active_culture_id"],
            "container_type": "bag",
            "container_count": 2,
            "substrate_g_per_container": 2500,
        },
        blocking=True,
    )
    conts = await bucket["container_repository"].async_list_for_batch(
        bucket["state"].batch.id
    )
    assert len(conts) == 2
    conts[0].nfc_uid = "nfc-persona-bag-a"
    conts[1].nfc_uid = "nfc-persona-bag-b"
    await bucket["container_repository"].async_update(conts[0])
    await bucket["container_repository"].async_update(conts[1])
    return conts[0].id, conts[1].id


@pytest.mark.asyncio
async def test_persona_95_scan_then_press_moves_only_scanned_bag(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """95%: set last-NFC helper (live scan), Tag source = last scanned, press advance."""
    entry_id = await _setup_entry(
        hass, mock_config_entry, tmp_path, monkeypatch, "persona_95.db"
    )
    id_a, id_b = await _inoculate_two_bags(hass, entry_id)
    bucket = hass.data[DOMAIN][entry_id]
    from custom_components.communifarm.domain.inventory import TAG_SOURCE_LAST_SCANNED

    bucket["intake_tag_uid_choice"] = TAG_SOURCE_LAST_SCANNED
    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "nfc-persona-bag-a")

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADVANCE_PRODUCTION_STAGE,
        {"target_stage": STAGE_INCUBATING},
        blocking=True,
    )
    a = await bucket["container_repository"].async_get(id_a)
    b = await bucket["container_repository"].async_get(id_b)
    assert a is not None and a.lifecycle_phase == STAGE_INCUBATING
    assert b is not None and b.lifecycle_phase == STAGE_INOCULATED


@pytest.mark.asyncio
async def test_persona_40_dropdown_scan_then_press_moves_selected_bag(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """40%: Tag source dropdown → Scan NFC → move button (no service nfc_uid)."""
    entry_id = await _setup_entry(
        hass, mock_config_entry, tmp_path, monkeypatch, "persona_40.db"
    )
    id_a, id_b = await _inoculate_two_bags(hass, entry_id)
    bucket = hass.data[DOMAIN][entry_id]
    from custom_components.communifarm import inventory_actions

    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "")
    bucket["intake_tag_uid_choice"] = inventory_actions.format_tag_source_option(
        "nfc-persona-bag-b", "container: bag B"
    )
    await inventory_actions.async_apply_tag_source_scan(hass, entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("input_text.esp32dev_last_nfc_uid").state == "nfc-persona-bag-b"

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADVANCE_PRODUCTION_STAGE,
        {"target_stage": STAGE_INCUBATING},
        blocking=True,
    )
    a = await bucket["container_repository"].async_get(id_a)
    b = await bucket["container_repository"].async_get(id_b)
    assert b is not None and b.lifecycle_phase == STAGE_INCUBATING
    assert a is not None and a.lifecycle_phase == STAGE_INOCULATED


@pytest.mark.asyncio
async def test_persona_95_no_scan_press_moves_entire_batch(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4B: no bag context → whole-batch advance (both bags incubating)."""
    entry_id = await _setup_entry(
        hass, mock_config_entry, tmp_path, monkeypatch, "persona_batch.db"
    )
    id_a, id_b = await _inoculate_two_bags(hass, entry_id)
    bucket = hass.data[DOMAIN][entry_id]
    from custom_components.communifarm.domain.inventory import TAG_SOURCE_LAST_SCANNED

    bucket["intake_tag_uid_choice"] = TAG_SOURCE_LAST_SCANNED
    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "")

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADVANCE_PRODUCTION_STAGE,
        {"target_stage": STAGE_INCUBATING},
        blocking=True,
    )
    a = await bucket["container_repository"].async_get(id_a)
    b = await bucket["container_repository"].async_get(id_b)
    assert a is not None and a.lifecycle_phase == STAGE_INCUBATING
    assert b is not None and b.lifecycle_phase == STAGE_INCUBATING


@pytest.mark.asyncio
async def test_persona_40_non_container_tag_does_not_scope_to_one_bag(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flaw: dropdown on employee badge must not look like a bag move — whole batch."""
    entry_id = await _setup_entry(
        hass, mock_config_entry, tmp_path, monkeypatch, "persona_emp.db"
    )
    id_a, id_b = await _inoculate_two_bags(hass, entry_id)
    bucket = hass.data[DOMAIN][entry_id]
    from custom_components.communifarm import inventory_actions

    await hass.services.async_call(
        DOMAIN, SERVICE_SEED_SHIPMENT_NFC_TAGS, {}, blocking=True
    )
    bucket["intake_tag_uid_choice"] = inventory_actions.format_tag_source_option(
        "nfc-employee-01", f"{OBJECT_EMPLOYEE}: kit"
    )
    await inventory_actions.async_apply_tag_source_scan(hass, entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADVANCE_PRODUCTION_STAGE,
        {"target_stage": STAGE_INCUBATING},
        blocking=True,
    )
    a = await bucket["container_repository"].async_get(id_a)
    b = await bucket["container_repository"].async_get(id_b)
    assert a is not None and a.lifecycle_phase == STAGE_INCUBATING
    assert b is not None and b.lifecycle_phase == STAGE_INCUBATING


@pytest.mark.asyncio
async def test_persona_badge_rejects_when_checkpoints_done_use_relocate(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Process gate: at relocate step, badge cannot finish — Storage relocate required."""
    entry_id = await _setup_entry(
        hass, mock_config_entry, tmp_path, monkeypatch, "persona_relocate.db"
    )
    bucket = hass.data[DOMAIN][entry_id]
    state = bucket["state"]
    from custom_components.communifarm import batch_actions, inventory_actions

    for line in WOOD_LOVER_RECIPE:
        if line.key == "water":
            continue
        await bucket["weight_repository"].async_insert(
            WeightEvent(
                site_id=state.site.id,
                environment_id=state.environment.id,
                batch_id=state.batch.id,
                mass_g=float(line.amount),
                ingredient_key=line.key,
                ingredient_label=line.label,
                recorded_at="2026-10-18T12:00:00+00:00",
                unit=line.unit,
            )
        )
    for milestone in (
        MILESTONE_DRYS_COMBINED,
        MILESTONE_WATER_ADDED,
        MILESTONE_DRY_WET_MIX_STARTED,
        MILESTONE_REMAINING_WATER_ADDED,
        MILESTONE_SETTLING_STARTED,
        MILESTONE_FIELD_CAPACITY_REACHED,
        MILESTONE_COMPLETELY_MIXED,
        MILESTONE_CONTAINERS_SEPARATED,
    ):
        await batch_actions.async_record_milestone(hass, entry_id, milestone)

    await hass.services.async_call(
        DOMAIN, SERVICE_SEED_SHIPMENT_NFC_TAGS, {}, blocking=True
    )
    bucket["intake_tag_uid_choice"] = inventory_actions.format_tag_source_option(
        "nfc-employee-01", f"{OBJECT_EMPLOYEE}: kit"
    )
    with pytest.raises(HomeAssistantError, match="Relocate"):
        await hass.services.async_call(
            DOMAIN, SERVICE_COMPLETE_MIX_STEP_FROM_BADGE, {}, blocking=True
        )

    labels = await inventory_actions.async_list_zone_option_labels(
        hass, entry_id, area_kind="storage"
    )
    bucket["relocate_zone_label"] = labels[0]
    await hass.services.async_call(
        DOMAIN, SERVICE_RELOCATE_FOR_STERILIZATION, {}, blocking=True
    )
    assert await bucket["batch_repository"].async_has_milestone(
        state.batch.id, "relocated_for_sterilization"
    )
