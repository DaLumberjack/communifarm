"""NFC resolve / check-in (tag holds stable ID only; SQLite is source of truth)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import new_id
from .validation import ValidationError, validate_nfc_uid

OBJECT_CONTAINER = "container"
OBJECT_BATCH = "batch"
OBJECT_CULTURE = "culture"
OBJECT_MEDIA = "media"
OBJECT_UNKNOWN = "unknown"

NFC_OBJECT_TYPES = frozenset(
    {
        OBJECT_CONTAINER,
        OBJECT_BATCH,
        OBJECT_CULTURE,
        OBJECT_MEDIA,
    }
)

ACTIVITY_HARVEST = "harvest"
ACTIVITY_MOVE = "move"
ACTIVITY_INVENTORY = "inventory"
ACTIVITY_CHECK_IN = "check_in"

NFC_ACTIVITIES = frozenset(
    {
        ACTIVITY_HARVEST,
        ACTIVITY_MOVE,
        ACTIVITY_INVENTORY,
        ACTIVITY_CHECK_IN,
    }
)


@dataclass(slots=True)
class NfcResolution:
    """Result of resolving a physical NFC UID against Communifarm SQLite."""

    nfc_uid: str
    object_type: str
    object_id: str | None = None
    label: str | None = None
    batch_id: str | None = None
    zone_id: str | None = None
    lifecycle_phase: str | None = None
    flush_count: int | None = None
    max_flushes: int | None = None
    found: bool = False
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NfcCheckin:
    """Append-only check-in event when a handheld scan attributes an activity."""

    nfc_uid: str
    object_type: str
    object_id: str
    activity: str
    recorded_at: str
    zone_id: str | None = None
    detail: dict[str, Any] | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("ncin")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_activity(activity: str) -> str:
    value = str(activity or "").strip()
    if value not in NFC_ACTIVITIES:
        raise ValidationError(
            f"activity must be one of {sorted(NFC_ACTIVITIES)}; got {activity!r}"
        )
    return value


def validate_bind_target(object_type: str, object_id: str) -> tuple[str, str]:
    ot = str(object_type or "").strip()
    oid = str(object_id or "").strip()
    if ot not in NFC_OBJECT_TYPES:
        raise ValidationError(
            f"object_type must be one of {sorted(NFC_OBJECT_TYPES)}; got {object_type!r}"
        )
    if not oid:
        raise ValidationError("object_id is required")
    return ot, oid


def parse_nfc_uid(raw: str | None, *, required: bool = True) -> str | None:
    return validate_nfc_uid(raw, required=required)


def format_resolution_markdown(res: NfcResolution) -> str:
    if not res.found:
        return (
            f"| Field | Value |\n| --- | --- |\n"
            f"| NFC | `{res.nfc_uid}` |\n"
            f"| Status | **not found** |"
        )
    lines = [
        "| Field | Value |",
        "| --- | --- |",
        f"| NFC | `{res.nfc_uid}` |",
        f"| Type | **{res.object_type}** |",
        f"| Object | `{res.object_id}` |",
        f"| Label | {res.label or '—'} |",
        f"| Batch | `{res.batch_id or '—'}` |",
        f"| Phase | {res.lifecycle_phase or '—'} |",
        f"| Flushes | {res.flush_count if res.flush_count is not None else '—'} / "
        f"{res.max_flushes if res.max_flushes is not None else '—'} |",
        f"| Zone | `{res.zone_id or '—'}` |",
    ]
    return "\n".join(lines)
