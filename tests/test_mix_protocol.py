"""Mix protocol checklist + water over-add + badge checkpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_COMPLETE_MIX_STEP_FROM_BADGE,
    SERVICE_CREATE_EMPLOYEE_BADGE,
    SERVICE_RECORD_WEIGHT,
    SERVICE_RELOCATE_FOR_STERILIZATION,
)
from custom_components.communifarm.domain.batch_milestones import (
    MILESTONE_DRYS_COMBINED,
    MILESTONE_WATER_ADDED,
)
from custom_components.communifarm.domain.mix_protocol import (
    MIX_PROTOCOL_STEPS,
    build_mix_protocol_progress,
    next_open_milestone,
)
from custom_components.communifarm.domain.recipe import (
    WOOD_LOVER_RECIPE,
    build_weigh_session_progress,
)
from custom_components.communifarm.domain.weight import WeightEvent


def test_wood_lover_includes_water_10200() -> None:
    water = next(line for line in WOOD_LOVER_RECIPE if line.key == "water")
    assert water.amount == 10200.0
    assert water.unit == "g"
    assert len(WOOD_LOVER_RECIPE) == 10


def test_water_pours_sum_toward_target() -> None:
    events = [
        WeightEvent(
            site_id="s",
            environment_id="e",
            batch_id="b",
            mass_g=5000.0,
            ingredient_key="water",
            ingredient_label="water (tap)",
            recorded_at="2026-10-17T01:00:00+00:00",
        ),
        WeightEvent(
            site_id="s",
            environment_id="e",
            batch_id="b",
            mass_g=5200.0,
            ingredient_key="water",
            ingredient_label="water (tap)",
            recorded_at="2026-10-17T01:05:00+00:00",
        ),
    ]
    progress = build_weigh_session_progress(
        batch_id="b",
        batch_nfc_uid="batch",
        recipe_scale=1.0,
        events=events,
    )
    water = next(line for line in progress.lines if line.key == "water")
    assert water.recorded_amount == 10200.0
    assert water.status == "close"


def test_mix_protocol_focus_shows_now_last_next() -> None:
    weigh = build_weigh_session_progress(
        batch_id="b",
        batch_nfc_uid="n",
        recipe_scale=1.0,
        events=[],
    )
    progress = build_mix_protocol_progress(
        batch_id="b",
        milestone_types=set(),
        weigh=weigh,
    )
    focus = progress.focus_text()
    assert "**Now**" in focus
    assert "Weigh dry ingredients" in focus
    assert progress.section == "drys"


def test_mix_protocol_requires_dry_weigh_before_milestones() -> None:
    weigh = build_weigh_session_progress(
        batch_id="b",
        batch_nfc_uid="n",
        recipe_scale=1.0,
        events=[],
    )
    progress = build_mix_protocol_progress(
        batch_id="b",
        milestone_types={MILESTONE_DRYS_COMBINED},
        weigh=weigh,
    )
    assert progress.steps[0].done is False
    assert progress.next_key == "weigh_drys"
    assert next_open_milestone(progress) is None
    assert len(MIX_PROTOCOL_STEPS) == 10


@pytest.mark.asyncio
async def test_record_weight_rejects_water_overadd(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_water.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    hass.data[DOMAIN][entry_id]["weigh_session"]["tare_seen"] = True

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_WEIGHT,
        {"mass_g": 8000.0, "ingredient": "water (tap)", "nfc_uid": "nfc-water-tap"},
        blocking=True,
    )
    hass.data[DOMAIN][entry_id]["weigh_session"]["tare_seen"] = True
    with pytest.raises(HomeAssistantError, match="water over-add"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RECORD_WEIGHT,
            {
                "mass_g": 4000.0,
                "ingredient": "water (tap)",
                "nfc_uid": "nfc-water-tap",
            },
            blocking=True,
        )
    weight_repo = hass.data[DOMAIN][entry_id]["weight_repository"]
    batch_id = hass.data[DOMAIN][entry_id]["state"].batch.id
    rows = await weight_repo.async_list_for_batch(batch_id)
    water_rows = [r for r in rows if r.ingredient_key == "water"]
    assert len(water_rows) == 1
    assert water_rows[0].mass_g == 8000.0


@pytest.mark.asyncio
async def test_badge_completes_next_mix_milestone(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_badge.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    state = hass.data[DOMAIN][entry_id]["state"]
    weight_repo = hass.data[DOMAIN][entry_id]["weight_repository"]

    # Seed all dry lines so weigh_drys is done.
    for line in WOOD_LOVER_RECIPE:
        if line.key == "water":
            continue
        await weight_repo.async_insert(
            WeightEvent(
                site_id=state.site.id,
                environment_id=state.environment.id,
                batch_id=state.batch.id,
                mass_g=float(line.amount),
                ingredient_key=line.key,
                ingredient_label=line.label,
                recorded_at="2026-10-17T12:00:00+00:00",
                unit=line.unit,
            )
        )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_EMPLOYEE_BADGE,
        {"label": "Andre"},
        blocking=True,
    )
    inv = hass.data[DOMAIN][entry_id]["inventory_repository"]
    badges = await inv.async_list_employees(state.site.id)
    badge = badges[0]
    badge.nfc_uid = "04EMPLOYEE001"
    await inv.async_update_employee(badge)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_COMPLETE_MIX_STEP_FROM_BADGE,
        {"nfc_uid": "04EMPLOYEE001"},
        blocking=True,
    )
    batch_repo = hass.data[DOMAIN][entry_id]["batch_repository"]
    assert await batch_repo.async_has_milestone(
        state.batch.id, MILESTONE_DRYS_COMBINED
    )

    # Double badge advances to next open step (water_added), not a duplicate dry.
    await hass.services.async_call(
        DOMAIN,
        SERVICE_COMPLETE_MIX_STEP_FROM_BADGE,
        {"nfc_uid": "04EMPLOYEE001"},
        blocking=True,
    )
    assert await batch_repo.async_has_milestone(state.batch.id, MILESTONE_WATER_ADDED)


@pytest.mark.asyncio
async def test_relocate_requires_location_then_allows_batch_nfc(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_relocate.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    bucket = hass.data[DOMAIN][mock_config_entry.entry_id]
    # Zone selects may seed a default — clear so relocate must demand a pick.
    bucket["relocate_zone_label"] = None
    bucket["intake_zone_label"] = None
    # Empty last NFC + no location → clear location error (not nfc_uid is required).
    hass.states.async_set("input_text.esp32dev_last_nfc_uid", "")
    with pytest.raises(HomeAssistantError, match="Storage shelf"):
        await hass.services.async_call(
            DOMAIN, SERVICE_RELOCATE_FOR_STERILIZATION, {}, blocking=True
        )

    from custom_components.communifarm import inventory_actions

    labels = await inventory_actions.async_list_zone_option_labels(
        hass, mock_config_entry.entry_id, area_kind="storage"
    )
    storage = next(label for label in labels if label.startswith("Storage"))
    bucket["relocate_zone_label"] = storage

    # 5A: Storage shelf + active batch NFC → bags land in Storage.
    state = bucket["state"]
    await hass.services.async_call(
        DOMAIN,
        SERVICE_RELOCATE_FOR_STERILIZATION,
        {},
        blocking=True,
    )
    batch_repo = bucket["batch_repository"]
    assert await batch_repo.async_has_milestone(
        state.batch.id, "relocated_for_sterilization"
    )
    batch = await batch_repo.async_get_batch(state.batch.id)
    assert batch is not None and batch.zone_id
    loc = bucket["location_repository"]
    zone = await loc.async_get_zone(batch.zone_id)
    area = await loc.async_get_area(zone.area_id)
    assert area.area_kind == "storage"


@pytest.mark.asyncio
async def test_badge_rejects_when_drys_not_weighed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Isolated DB — shared PHCC testing_config otherwise keeps prior dry weighs.
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_badge_reject.db",
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_EMPLOYEE_BADGE,
        {"label": "Ops"},
        blocking=True,
    )
    inv = hass.data[DOMAIN][entry_id]["inventory_repository"]
    state = hass.data[DOMAIN][entry_id]["state"]
    badge = (await inv.async_list_employees(state.site.id))[0]
    badge.nfc_uid = "04EMPLOYEE002"
    await inv.async_update_employee(badge)
    with pytest.raises(HomeAssistantError, match="dry weighing"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_COMPLETE_MIX_STEP_FROM_BADGE,
            {"nfc_uid": "04EMPLOYEE002"},
            blocking=True,
        )
