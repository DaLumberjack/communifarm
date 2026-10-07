"""NFC resolve / bind / check-in coverage beyond the harvest happy path."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm import nfc_actions
from custom_components.communifarm.const import (
    DOMAIN,
    ENTITY_SCALE_NFC_UID,
    SERVICE_ACQUIRE_CULTURE,
    SERVICE_BIND_NFC,
    SERVICE_CHECK_IN,
    SERVICE_CREATE_MEDIA_BATCH,
    SERVICE_ENSURE_PLACEMENT_LAYOUT,
    SERVICE_INOCULATE_BATCH,
    SERVICE_RESOLVE_NFC,
)
from custom_components.communifarm.domain.culture import (
    FORM_LIQUID_CULTURE,
    SOURCE_PURCHASED,
)
from custom_components.communifarm.domain.location import (
    AREA_INOCULATION_TENT,
    AREA_STILL_AIR_CABINET,
)
from custom_components.communifarm.domain.nfc import (
    ACTIVITY_CHECK_IN,
    ACTIVITY_HARVEST,
    ACTIVITY_INVENTORY,
    ACTIVITY_MOVE,
    OBJECT_BATCH,
    OBJECT_CONTAINER,
    OBJECT_CULTURE,
    OBJECT_MEDIA,
    OBJECT_UNKNOWN,
    NfcCheckin,
    NfcResolution,
    format_resolution_markdown,
    parse_nfc_uid,
    validate_activity,
    validate_bind_target,
)
from custom_components.communifarm.domain.validation import ValidationError
from custom_components.communifarm.storage.batch_repository import BatchRepository
from custom_components.communifarm.storage.container_repository import (
    ContainerRepository,
)
from custom_components.communifarm.storage.culture_repository import CultureRepository
from custom_components.communifarm.storage.location_repository import LocationRepository
from custom_components.communifarm.storage.nfc_repository import NfcRepository


def test_domain_nfc_validators_and_markdown() -> None:
    assert validate_activity("harvest") == ACTIVITY_HARVEST
    with pytest.raises(ValidationError, match="activity must"):
        validate_activity("weigh")

    assert validate_bind_target("batch", " batch_1 ") == (OBJECT_BATCH, "batch_1")
    with pytest.raises(ValidationError, match="object_type"):
        validate_bind_target("fan", "x")
    with pytest.raises(ValidationError, match="object_id"):
        validate_bind_target("batch", "  ")

    assert parse_nfc_uid("04A1B2C3") == "04A1B2C3"
    with pytest.raises(ValidationError):
        parse_nfc_uid(None, required=True)

    missing = NfcResolution(nfc_uid="deadbeef", object_type=OBJECT_UNKNOWN, found=False)
    md_missing = format_resolution_markdown(missing)
    assert "not found" in md_missing
    assert "deadbeef" in md_missing

    found = NfcResolution(
        nfc_uid="aabb",
        object_type=OBJECT_CONTAINER,
        object_id="cont_1",
        label="block #1",
        batch_id="batch_1",
        zone_id="zone_1",
        lifecycle_phase="fruiting",
        flush_count=1,
        max_flushes=3,
        found=True,
    )
    md = format_resolution_markdown(found)
    assert "container" in md
    assert "cont_1" in md
    assert found.to_dict()["found"] is True

    event = NfcCheckin(
        nfc_uid="aabb",
        object_type=OBJECT_CONTAINER,
        object_id="cont_1",
        activity=ACTIVITY_INVENTORY,
        recorded_at="2026-10-06T00:00:00+00:00",
    )
    assert event.id.startswith("ncin_")
    assert event.to_dict()["activity"] == ACTIVITY_INVENTORY


@pytest.mark.asyncio
async def test_resolve_unknown_and_entity_uid(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_nfc_unknown.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RESOLVE_NFC,
        {"nfc_uid": "04DEADBEEF00"},
        blocking=True,
    )
    session = hass.data[DOMAIN][entry_id]["nfc_session"]
    assert session["found"] is False
    assert session["object_type"] == OBJECT_UNKNOWN
    assert "not found" in session["progress_text"]

    with pytest.raises(HomeAssistantError, match="unknown NFC UID"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CHECK_IN,
            {"activity": ACTIVITY_CHECK_IN, "nfc_uid": "04DEADBEEF00"},
            blocking=True,
        )

    with pytest.raises(HomeAssistantError, match="activity must"):
        await nfc_actions.async_check_in(
            hass, entry_id, activity="dance", nfc_uid="04DEADBEEF00"
        )

    # Handheld entity path: empty → validation error; set → resolve.
    with pytest.raises(HomeAssistantError):
        await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=None)

    hass.states.async_set(ENTITY_SCALE_NFC_UID, "04DEADBEEF00")
    resolution = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=None)
    assert resolution.nfc_uid == "04DEADBEEF00"
    assert resolution.found is False


@pytest.mark.asyncio
async def test_resolve_batch_culture_media_and_bind(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_nfc_objects.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Tagged LC",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "container": "jar",
            "nfc_uid": "04CULTURETAG01",
        },
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_MEDIA_BATCH,
        {"name": "Agar tray", "recipe_key": "mea_agar_500"},
        blocking=True,
    )
    await hass.async_block_till_done()

    culture_repo: CultureRepository = hass.data[DOMAIN][entry_id]["culture_repository"]
    cultures = await culture_repo.async_list_cultures()
    culture = cultures[0]
    assert culture.nfc_uid == "04CULTURETAG01"

    media_batches = await culture_repo.async_list_media_batches()
    media = media_batches[0]
    # Seed a distinct media NFC uid (create path may leave None / id).
    if not media.nfc_uid or media.nfc_uid == media.id:
        conn = culture_repo._conn
        assert conn is not None
        conn.execute(
            "UPDATE media_batches SET nfc_uid = ? WHERE stable_id = ?",
            ("04MEDIATAG0001", media.id),
        )
        conn.commit()
        media_uid = "04MEDIATAG0001"
    else:
        media_uid = media.nfc_uid

    await hass.services.async_call(
        DOMAIN, SERVICE_RESOLVE_NFC, {"nfc_uid": "04CULTURETAG01"}, blocking=True
    )
    session = hass.data[DOMAIN][entry_id]["nfc_session"]
    assert session["found"] is True
    assert session["object_type"] == OBJECT_CULTURE
    assert session["object_id"] == culture.id

    await hass.services.async_call(
        DOMAIN, SERVICE_RESOLVE_NFC, {"nfc_uid": media_uid}, blocking=True
    )
    session = hass.data[DOMAIN][entry_id]["nfc_session"]
    assert session["found"] is True
    assert session["object_type"] == OBJECT_MEDIA
    assert session["object_id"] == media.id

    batch_repo: BatchRepository = hass.data[DOMAIN][entry_id]["batch_repository"]
    state = hass.data[DOMAIN][entry_id]["state"]
    await batch_repo.async_ensure_batch(
        batch_id=state.batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=state.batch.name,
        nfc_uid="04BATCHTAG0001",
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_RESOLVE_NFC, {"nfc_uid": "04BATCHTAG0001"}, blocking=True
    )
    session = hass.data[DOMAIN][entry_id]["nfc_session"]
    assert session["found"] is True
    assert session["object_type"] == OBJECT_BATCH
    assert session["object_id"] == state.batch.id

    # Bind a physical UID onto the active batch (overwrites prior tag).
    await hass.services.async_call(
        DOMAIN,
        SERVICE_BIND_NFC,
        {
            "object_type": "batch",
            "object_id": state.batch.id,
            "nfc_uid": "04NEWBATCHTAG1",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    session = hass.data[DOMAIN][entry_id]["nfc_session"]
    assert session["nfc_uid"] == "04NEWBATCHTAG1"
    assert session["object_type"] == OBJECT_BATCH

    with pytest.raises(HomeAssistantError, match="not implemented"):
        await nfc_actions.async_bind_nfc(
            hass,
            entry_id,
            object_type=OBJECT_CULTURE,
            object_id=culture.id,
            nfc_uid="04IGNORED00001",
        )
    with pytest.raises(HomeAssistantError, match="unknown batch_id"):
        await nfc_actions.async_bind_nfc(
            hass,
            entry_id,
            object_type=OBJECT_BATCH,
            object_id="batch_missing",
            nfc_uid="04IGNORED00002",
        )


@pytest.mark.asyncio
async def test_checkin_move_batch_and_container_zone(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_nfc_move.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id

    await hass.services.async_call(
        DOMAIN, SERVICE_ENSURE_PLACEMENT_LAYOUT, {}, blocking=True
    )
    loc_repo: LocationRepository = hass.data[DOMAIN][entry_id]["location_repository"]
    state = hass.data[DOMAIN][entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    inoc = next(a for a in areas if a.area_kind == AREA_INOCULATION_TENT)
    zones = await loc_repo.async_list_zones_for_area(inoc.id)
    zone = zones[0]

    batch_repo: BatchRepository = hass.data[DOMAIN][entry_id]["batch_repository"]
    await batch_repo.async_ensure_batch(
        batch_id=state.batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=state.batch.name,
        nfc_uid="04MOVEBATCH001",
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_IN,
        {
            "activity": ACTIVITY_MOVE,
            "nfc_uid": "04MOVEBATCH001",
            "zone_id": zone.id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    session = hass.data[DOMAIN][entry_id]["nfc_session"]
    assert session["activity"] == ACTIVITY_MOVE
    assert session["zone_id"] == zone.id
    moved = await batch_repo.async_get_batch(state.batch.id)
    assert moved is not None
    assert moved.zone_id == zone.id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Move LC",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "container": "jar",
        },
        blocking=True,
    )
    culture_repo: CultureRepository = hass.data[DOMAIN][entry_id]["culture_repository"]
    culture_id = (await culture_repo.async_list_cultures())[0].id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_INOCULATE_BATCH,
        {
            "culture_id": culture_id,
            "container_type": "block",
            "container_count": 1,
            "substrate_g_per_container": 1000.0,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    container_repo: ContainerRepository = hass.data[DOMAIN][entry_id][
        "container_repository"
    ]
    containers = await container_repo.async_list_for_batch(state.batch.id)
    target = containers[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_BIND_NFC,
        {
            "object_type": "container",
            "object_id": target.id,
            "nfc_uid": "04MOVECONT0001",
        },
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_IN,
        {
            "activity": ACTIVITY_MOVE,
            "nfc_uid": "04MOVECONT0001",
            "zone_id": zone.id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    refreshed = await container_repo.async_get(target.id)
    assert refreshed is not None
    assert refreshed.zone_id == zone.id
    assert refreshed.nfc_uid == "04MOVECONT0001"

    with pytest.raises(HomeAssistantError, match="unknown zone_id"):
        await nfc_actions.async_check_in(
            hass,
            entry_id,
            activity=ACTIVITY_MOVE,
            nfc_uid="04MOVECONT0001",
            zone_id="zone_does_not_exist",
        )
    with pytest.raises(HomeAssistantError, match="unknown container_id"):
        await nfc_actions.async_bind_nfc(
            hass,
            entry_id,
            object_type=OBJECT_CONTAINER,
            object_id="cont_missing",
            nfc_uid="04GHOST0000001",
        )

    # Missing repo surfaces a clear HA error.
    hass.data[DOMAIN][entry_id]["nfc_repository"] = None
    with pytest.raises(HomeAssistantError, match="NFC repository is not available"):
        await nfc_actions.async_resolve_nfc(
            hass, entry_id, nfc_uid="04MOVECONT0001"
        )


@pytest.mark.asyncio
async def test_checkin_move_culture_and_media(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_nfc_culture_media_move.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id

    await hass.services.async_call(
        DOMAIN, SERVICE_ENSURE_PLACEMENT_LAYOUT, {}, blocking=True
    )
    loc_repo: LocationRepository = hass.data[DOMAIN][entry_id]["location_repository"]
    state = hass.data[DOMAIN][entry_id]["state"]
    areas = await loc_repo.async_list_areas(state.site.id)
    sab = next(a for a in areas if a.area_kind == AREA_STILL_AIR_CABINET)
    zones = await loc_repo.async_list_zones_for_area(sab.id)
    zone_a, zone_b = zones[0], zones[1]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ACQUIRE_CULTURE,
        {
            "name": "Moveable LC",
            "source_type": SOURCE_PURCHASED,
            "form": FORM_LIQUID_CULTURE,
            "container": "jar",
            "nfc_uid": "04MOVECULTURE1",
            "zone_id": zone_a.id,
        },
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CREATE_MEDIA_BATCH,
        {
            "name": "Moveable agar",
            "recipe_key": "mea_agar_500",
            "zone_id": zone_a.id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    culture_repo: CultureRepository = hass.data[DOMAIN][entry_id]["culture_repository"]
    culture = (await culture_repo.async_list_cultures())[0]
    media = (await culture_repo.async_list_media_batches())[0]
    conn = culture_repo._conn
    assert conn is not None
    conn.execute(
        "UPDATE media_batches SET nfc_uid = ? WHERE stable_id = ?",
        ("04MOVEMEDIA0001", media.id),
    )
    conn.commit()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_IN,
        {
            "activity": ACTIVITY_MOVE,
            "nfc_uid": "04MOVECULTURE1",
            "zone_id": zone_b.id,
        },
        blocking=True,
    )
    moved_culture = await culture_repo.async_get_culture(culture.id)
    assert moved_culture is not None
    assert moved_culture.zone_id == zone_b.id

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_IN,
        {
            "activity": ACTIVITY_MOVE,
            "nfc_uid": "04MOVEMEDIA0001",
            "zone_id": zone_b.id,
        },
        blocking=True,
    )
    moved_media = await culture_repo.async_get_media_batch(media.id)
    assert moved_media is not None
    assert moved_media.zone_id == zone_b.id


@pytest.mark.asyncio
async def test_nfc_repository_insert_checkin_direct(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    bypass_dashboard,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "communifarm_nfc_insert.db"
    monkeypatch.setattr(
        "custom_components.communifarm.storage.sqlite_repository.sqlite_db.db_path_for_config_dir",
        lambda _config_dir: db_path,
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id
    repo: NfcRepository = hass.data[DOMAIN][entry_id]["nfc_repository"]

    event = NfcCheckin(
        nfc_uid="04DIRECT000001",
        object_type=OBJECT_BATCH,
        object_id="batch_test",
        activity=ACTIVITY_INVENTORY,
        recorded_at="2026-10-06T12:00:00+00:00",
        detail={"label": "direct"},
    )
    saved = await repo.async_insert_checkin(event)
    assert saved.id == event.id
    conn = hass.data[DOMAIN][entry_id]["batch_repository"]._conn
    row = conn.execute(
        "SELECT activity, detail FROM nfc_checkins WHERE stable_id = ?",
        (event.id,),
    ).fetchone()
    assert row["activity"] == ACTIVITY_INVENTORY
    assert "direct" in row["detail"]
