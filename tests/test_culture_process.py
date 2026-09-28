"""Culture process + media SQLite tests (T0)."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm.const import (
    DOMAIN,
    SERVICE_ACQUIRE_CULTURE,
    SERVICE_CREATE_MEDIA_BATCH,
    SERVICE_INTRODUCE_CULTURE,
    SERVICE_RECORD_MEDIA_MILESTONE,
    SERVICE_RECORD_MEDIA_WEIGHT,
)
from custom_components.communifarm.domain.culture import (
    CONTAINER_SYRINGE,
    DEFAULT_AGAR_RECIPE_KEY,
    EVENT_CULTURE_INTRODUCED,
    FORM_SPORES,
    MEDIA_MILESTONES,
    MEDIA_RECIPE_META,
    MEDIA_STATUS_IN_USE,
    MEDIA_STATUS_PLANNED,
    MEDIA_STATUS_READY,
    MILESTONE_LC_STIR_STARTED,
    MILESTONE_LC_STIR_STOPPED,
    MILESTONE_MEDIA_PORTIONED,
    MILESTONE_MEDIA_READY,
    MILESTONE_MEDIA_STERILIZED,
    MILESTONE_TO_MEDIA_STATUS,
    RECIPE_HONEY_LC_500,
    SOURCE_PURCHASED,
    CultureLot,
    assert_media_accepts_culture,
    build_media_batch_from_recipe,
    child_culture_from_parent,
    media_recipe_lines,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage import sqlite_db
from custom_components.communifarm.storage.culture_repository import CultureRepository


def test_lc_recipe_expects_mason_ports_and_stir_bar() -> None:
    meta = MEDIA_RECIPE_META[RECIPE_HONEY_LC_500]
    assert meta["vessel_type"] == "jar"
    assert "syringe_port" in meta["vessel_notes"]
    assert "breathability_port" in meta["vessel_notes"]
    assert "stir_bar" in meta["vessel_notes"]
    assert MILESTONE_LC_STIR_STARTED in MEDIA_MILESTONES
    assert MILESTONE_LC_STIR_STARTED not in MILESTONE_TO_MEDIA_STATUS


@pytest.mark.asyncio
async def test_lc_stir_milestone_keeps_media_ready(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    repo = CultureRepository(hass, path=tmp_path / "lc_stir.db")
    await repo.async_setup()
    media = build_media_batch_from_recipe(
        site_id="site_a",
        environment_id="env_a",
        recipe_key=RECIPE_HONEY_LC_500,
    )
    await repo.async_create_media_batch(media)
    when = "2026-09-27T21:00:00+00:00"
    await repo.async_insert_media_milestone(
        media_batch_id=media.id,
        event_type=MILESTONE_MEDIA_READY,
        recorded_at=when,
    )
    await repo.async_insert_media_milestone(
        media_batch_id=media.id,
        event_type=MILESTONE_LC_STIR_STARTED,
        recorded_at=when,
    )
    after = await repo.async_get_media_batch(media.id)
    assert after is not None
    assert after.status == MEDIA_STATUS_READY
    await repo.async_close()


@pytest.mark.asyncio
async def test_bound_stir_plate_records_cf_milestone(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_stir_bind.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    hass.states.async_set("switch.mock_lc_stir_plate", "off")

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    async def _on(call) -> None:
        target = call.data["entity_id"]
        if isinstance(target, list):
            target = target[0]
        hass.states.async_set(target, "on")

    async def _off(call) -> None:
        target = call.data["entity_id"]
        if isinstance(target, list):
            target = target[0]
        hass.states.async_set(target, "off")

    if hass.services.has_service("switch", "turn_on"):
        hass.services.async_remove("switch", "turn_on")
    if hass.services.has_service("switch", "turn_off"):
        hass.services.async_remove("switch", "turn_off")
    hass.services.async_register("switch", "turn_on", _on)
    hass.services.async_register("switch", "turn_off", _off)

    proxy = hass.states.get("switch.communifarm_lc_stir_plate")
    assert proxy is not None
    assert proxy.state == "off"

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_MEDIA_BATCH,
        {"recipe_key": RECIPE_HONEY_LC_500},
        blocking=True,
    )
    repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    media_id = (await repo.async_list_media_batches())[0].id
    assert (
        hass.data[DOMAIN][mock_config_entry.entry_id]["active_media_batch_id"]
        == media_id
    )

    entity = hass.data["entity_components"]["switch"].get_entity(
        "switch.communifarm_lc_stir_plate"
    )
    assert entity is not None

    await entity.async_turn_on()
    await hass.async_block_till_done()
    assert await repo.async_has_media_milestone(media_id, MILESTONE_LC_STIR_STARTED)
    assert hass.states.get("switch.mock_lc_stir_plate").state == "on"

    await entity.async_turn_off()
    await hass.async_block_till_done()
    assert await repo.async_has_media_milestone(media_id, MILESTONE_LC_STIR_STOPPED)


def test_mea_recipe_lines() -> None:
    lines = media_recipe_lines(DEFAULT_AGAR_RECIPE_KEY)
    assert len(lines) == 3
    assert lines[0].unit == "ml"
    assert lines[1].amount == 10.0
    assert lines[2].label == "light malt extract"


def test_gate_rejects_planned_media() -> None:
    with pytest.raises(ValidationError, match="media_ready"):
        assert_media_accepts_culture(MEDIA_STATUS_PLANNED)


def test_gate_allows_ready_and_in_use() -> None:
    assert_media_accepts_culture(MEDIA_STATUS_READY)
    assert_media_accepts_culture(MEDIA_STATUS_IN_USE)


def test_child_lot_is_new_identity() -> None:
    parent = CultureLot(
        site_id="site_a",
        environment_id="env_a",
        name="Vendor LC",
        source_type=SOURCE_PURCHASED,
        form="liquid_culture",
        container="jar",
        strain_label="oyster",
    )
    child = child_culture_from_parent(parent, name="Plate A", form="agar")
    assert child.id != parent.id
    assert child.parent_culture_id == parent.id
    assert child.form == "agar"
    assert child.strain_label == "oyster"


def test_sqlite_migration_v5_creates_culture_tables(tmp_path: Path) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    version = sqlite_db.apply_migrations(conn)
    assert version == sqlite_db.SCHEMA_VERSION
    assert version == 5
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    for name in (
        "culture_lots",
        "media_batches",
        "media_weight_events",
        "media_milestones",
        "culture_events",
        "batches",
        "weight_events",
    ):
        assert name in tables
    conn.close()


@pytest.mark.asyncio
async def test_introduce_rejects_before_media_ready(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    repo = CultureRepository(hass, path=tmp_path / "culture.db")
    await repo.async_setup()
    media = build_media_batch_from_recipe(
        site_id="site_a",
        environment_id="env_a",
        recipe_key=DEFAULT_AGAR_RECIPE_KEY,
    )
    await repo.async_create_media_batch(media)
    parent = CultureLot(
        site_id="site_a",
        environment_id="env_a",
        name="Spore syringe",
        source_type=SOURCE_PURCHASED,
        form=FORM_SPORES,
        container=CONTAINER_SYRINGE,
    )
    await repo.async_acquire_culture(parent)

    with pytest.raises(ValidationError, match="media_ready"):
        await repo.async_introduce_culture(
            parent_culture_id=parent.id,
            media_batch_id=media.id,
        )
    await repo.async_close()


@pytest.mark.asyncio
async def test_introduce_creates_child_after_media_ready(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    repo = CultureRepository(hass, path=tmp_path / "culture_ok.db")
    await repo.async_setup()
    media = build_media_batch_from_recipe(
        site_id="site_a",
        environment_id="env_a",
        recipe_key=DEFAULT_AGAR_RECIPE_KEY,
        vessel_count=10,
    )
    await repo.async_create_media_batch(media)
    when = "2026-09-27T20:00:00+00:00"
    await repo.async_insert_media_milestone(
        media_batch_id=media.id,
        event_type=MILESTONE_MEDIA_PORTIONED,
        recorded_at=when,
    )
    await repo.async_insert_media_milestone(
        media_batch_id=media.id,
        event_type=MILESTONE_MEDIA_STERILIZED,
        recorded_at=when,
    )
    await repo.async_insert_media_milestone(
        media_batch_id=media.id,
        event_type=MILESTONE_MEDIA_READY,
        recorded_at=when,
    )
    ready = await repo.async_get_media_batch(media.id)
    assert ready is not None
    assert ready.status == MEDIA_STATUS_READY
    assert ready.ready_at == when

    parent = CultureLot(
        site_id="site_a",
        environment_id="env_a",
        name="Wild tissue",
        source_type="wild",
        form="agar",
        container="plate",
        strain_label="local",
    )
    await repo.async_acquire_culture(parent)

    child, event = await repo.async_introduce_culture(
        parent_culture_id=parent.id,
        media_batch_id=media.id,
        child_name="Isolate A1",
    )
    assert child.parent_culture_id == parent.id
    assert child.id != parent.id
    assert child.name == "Isolate A1"
    assert event.event_type == EVENT_CULTURE_INTRODUCED
    assert event.child_culture_id == child.id

    after = await repo.async_get_media_batch(media.id)
    assert after is not None
    assert after.status == MEDIA_STATUS_IN_USE

    events = await repo.async_list_culture_events_for_media(media.id)
    types = {e.event_type for e in events}
    assert EVENT_CULTURE_INTRODUCED in types
    await repo.async_close()


@pytest.mark.asyncio
async def test_culture_services_happy_path(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_culture_svc.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_MEDIA_BATCH,
        {"recipe_key": DEFAULT_AGAR_RECIPE_KEY, "vessel_count": 8},
        blocking=True,
    )
    await hass.async_block_till_done()
    media_batches = await repo.async_list_media_batches()
    assert len(media_batches) == 1
    media_id = media_batches[0].id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_MEDIA_WEIGHT,
        {
            "media_batch_id": media_id,
            "amount": 500,
            "unit": "ml",
            "ingredient": "distilled water",
        },
        blocking=True,
    )
    weights = await repo.async_list_media_weights(media_id)
    assert len(weights) == 1
    assert weights[0].target_amount == 500.0

    for milestone in (
        MILESTONE_MEDIA_PORTIONED,
        MILESTONE_MEDIA_STERILIZED,
        MILESTONE_MEDIA_READY,
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RECORD_MEDIA_MILESTONE,
            {"media_batch_id": media_id, "event_type": milestone},
            blocking=True,
        )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Shop spores",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_SPORES,
            "container": CONTAINER_SYRINGE,
            "strain_label": "blue oyster",
        },
        blocking=True,
    )
    cultures = await repo.async_list_cultures()
    parents = [c for c in cultures if c.parent_culture_id is None]
    assert len(parents) == 1
    parent_id = parents[0].id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_INTRODUCE_CULTURE,
        {
            "culture_id": parent_id,
            "media_batch_id": media_id,
            "child_name": "Plate set 1",
        },
        blocking=True,
    )
    cultures = await repo.async_list_cultures()
    children = [c for c in cultures if c.parent_culture_id == parent_id]
    assert len(children) == 1
    assert children[0].name == "Plate set 1"


@pytest.mark.asyncio
async def test_introduce_service_rejects_unready_media(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "custom_components.communifarm.storage.weight_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: tmp_path / "communifarm_culture_reject.db",
    )
    hass.states.async_set("switch.mock_exhaust", "off")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    repo: CultureRepository = hass.data[DOMAIN][mock_config_entry.entry_id][
        "culture_repository"
    ]
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_MEDIA_BATCH,
        {"recipe_key": RECIPE_HONEY_LC_500},
        blocking=True,
    )
    media_id = (await repo.async_list_media_batches())[0].id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Friend LC",
            "source_type": "acquaintance",
            "form": "liquid_culture",
        },
        blocking=True,
    )
    parent_id = [c for c in await repo.async_list_cultures()][0].id

    with pytest.raises(HomeAssistantError, match="media_ready"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_INTRODUCE_CULTURE,
            {"culture_id": parent_id, "media_batch_id": media_id},
            blocking=True,
        )
