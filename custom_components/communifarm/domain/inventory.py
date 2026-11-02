"""Inventory lots and NDEF identity payloads (stable refs; SQLite is source of truth)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .models import new_id
from .validation import ValidationError, validate_nfc_uid, validate_readable_name
from .weight import ingredient_key_from_label

OBJECT_INVENTORY = "inventory"
OBJECT_EMPLOYEE = "employee"
OBJECT_LOCATION = "location"
OBJECT_CONTAINER = "container"
OBJECT_BATCH = "batch"
OBJECT_CULTURE = "culture"
OBJECT_MACHINE = "machine"

NFC_WRITE_OBJECT_TYPES = frozenset(
    {
        OBJECT_INVENTORY,
        OBJECT_EMPLOYEE,
        OBJECT_LOCATION,
        OBJECT_CONTAINER,
        OBJECT_BATCH,
        OBJECT_CULTURE,
        OBJECT_MACHINE,
    }
)

# Scan mode: when register_production_block, next unresolved UID becomes a bag/bin.
SCAN_MODE_NORMAL = "normal"
SCAN_MODE_REGISTER_BLOCK = "register_production_block"
NFC_SCAN_MODES = frozenset({SCAN_MODE_NORMAL, SCAN_MODE_REGISTER_BLOCK})

# Intake station process chrome (same entities; different visible card groups).
INTAKE_PROCESS_COMBINED = "combined"
INTAKE_PROCESS_MARK_TAGS = "mark_tags"
INTAKE_PROCESS_PURCHASE = "purchase_intake"
INTAKE_PROCESS_MODES = frozenset(
    {
        INTAKE_PROCESS_COMBINED,
        INTAKE_PROCESS_MARK_TAGS,
        INTAKE_PROCESS_PURCHASE,
    }
)

PAYMENT_ACCOUNT = "account"
PAYMENT_CASH = "cash"
INTAKE_PAYMENT_METHODS = frozenset({PAYMENT_ACCOUNT, PAYMENT_CASH})

AMOUNT_UNITS = ("g", "kg", "lb", "qts", "bags", "ea")

# Intake tag-source select: bind pending NDEF to last scan or a known DB UID.
TAG_SOURCE_LAST_SCANNED = "(last scanned)"

# Display labels for water inventory / select; all map to recipe key ``water``.
WATER_KIND_TAP = "tap"
WATER_KIND_FILTERED = "filtered"
WATER_KIND_WARM_TAP = "warm_tap"
WATER_KIND_WARM_FILTERED = "warm_filtered"

WATER_KINDS: dict[str, str] = {
    WATER_KIND_TAP: "water (tap)",
    WATER_KIND_FILTERED: "water (filtered)",
    WATER_KIND_WARM_TAP: "water (warm, tap)",
    WATER_KIND_WARM_FILTERED: "water (warm, filtered)",
}

WATER_KIND_BY_LABEL = {label: kind for kind, label in WATER_KINDS.items()}

STATUS_ACTIVE = "active"
STATUS_RETIRED = "retired"

NDEF_SCHEMA_VERSION = 1


@dataclass(slots=True)
class InventoryLot:
    """One physical bag/bin of an ingredient (unique id; name may duplicate)."""

    site_id: str
    ingredient_key: str
    label: str
    water_kind: str | None = None
    nfc_uid: str | None = None
    ndef_payload: str | None = None
    status: str = STATUS_ACTIVE
    notes: str | None = None
    created_at: str = ""
    id: str = ""
    amount: float | None = None
    amount_unit: str | None = None
    cost: float | None = None
    payment_location: str | None = None
    purchase_location: str | None = None
    tracked: bool | None = None
    receipt_tracked: bool | None = None
    purchase_date: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("inv")
        validate_readable_name(self.label, field_name="inventory.label")
        if self.water_kind and self.water_kind not in WATER_KINDS:
            raise ValidationError(
                f"water_kind must be one of {sorted(WATER_KINDS)}; got {self.water_kind!r}"
            )
        if self.nfc_uid is not None:
            self.nfc_uid = validate_nfc_uid(self.nfc_uid, required=True)
        if self.payment_location and self.payment_location not in INTAKE_PAYMENT_METHODS:
            raise ValidationError(
                f"payment_location must be one of {sorted(INTAKE_PAYMENT_METHODS)}"
            )
        if self.amount_unit and self.amount_unit not in AMOUNT_UNITS:
            raise ValidationError(
                f"amount_unit must be one of {AMOUNT_UNITS}; got {self.amount_unit!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MachineAsset:
    """Tagged machine / equipment (identity only on the chip)."""

    site_id: str
    label: str
    nfc_uid: str | None = None
    ndef_payload: str | None = None
    status: str = STATUS_ACTIVE
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("mach")
        validate_readable_name(self.label, field_name="machine.label")
        if self.nfc_uid is not None:
            self.nfc_uid = validate_nfc_uid(self.nfc_uid, required=True)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EmployeeBadge:
    """Operator badge used to mark mix protocol steps complete."""

    site_id: str
    label: str
    nfc_uid: str | None = None
    ndef_payload: str | None = None
    status: str = STATUS_ACTIVE
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("emp")
        validate_readable_name(self.label, field_name="employee.label")
        if self.nfc_uid is not None:
            self.nfc_uid = validate_nfc_uid(self.nfc_uid, required=True)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NdefIdentity:
    """Typed NDEF text payload written to a tag (identity only, not process state)."""

    object_type: str
    object_id: str
    label: str
    ingredient_key: str | None = None
    water_kind: str | None = None
    zone_id: str | None = None
    v: int = NDEF_SCHEMA_VERSION

    def to_payload(self) -> str:
        if self.object_type not in NFC_WRITE_OBJECT_TYPES:
            raise ValidationError(
                f"NDEF object_type must be one of {sorted(NFC_WRITE_OBJECT_TYPES)}"
            )
        body: dict[str, Any] = {
            "v": self.v,
            "t": self.object_type,
            "id": self.object_id,
            "n": self.label,
        }
        if self.ingredient_key:
            body["k"] = self.ingredient_key
        if self.water_kind:
            body["w"] = self.water_kind
        if self.zone_id:
            body["z"] = self.zone_id
        # Compact stable URI for scanners that prefer a single text record prefix.
        body["uri"] = f"cf://{self.object_type}/{self.object_id}"
        return json.dumps(body, separators=(",", ":"), sort_keys=True)


def parse_ndef_payload(raw: str | None) -> NdefIdentity | None:
    """Parse NDEF JSON written by Communifarm; ignore non-CF payloads."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        if text.startswith("cf://"):
            parts = text.split("/")
            if len(parts) >= 4 and parts[0] == "cf:" and parts[2] in NFC_WRITE_OBJECT_TYPES:
                return NdefIdentity(
                    object_type=parts[2],
                    object_id=parts[3],
                    label=parts[3],
                )
        return None
    if not isinstance(data, dict):
        return None
    ot = str(data.get("t") or "").strip()
    oid = str(data.get("id") or "").strip()
    if ot not in NFC_WRITE_OBJECT_TYPES or not oid:
        return None
    return NdefIdentity(
        object_type=ot,
        object_id=oid,
        label=str(data.get("n") or oid)[:64],
        ingredient_key=data.get("k"),
        water_kind=data.get("w"),
        zone_id=data.get("z"),
        v=int(data.get("v") or NDEF_SCHEMA_VERSION),
    )


def recipe_ingredient_key(label: str | None) -> str | None:
    """Map UI / NFC labels onto Wood Lover recipe keys (all water kinds → ``water``)."""
    if label is None:
        return None
    cleaned = str(label).strip()
    if not cleaned or cleaned in ("(none)", "unknown", "unavailable"):
        return None
    lower = cleaned.lower()
    if lower in WATER_KIND_BY_LABEL or lower == "water" or lower.startswith("water "):
        return "water"
    return ingredient_key_from_label(cleaned)


def water_kind_from_label(label: str | None) -> str | None:
    if not label:
        return None
    return WATER_KIND_BY_LABEL.get(str(label).strip().lower())


def inventory_write_choices() -> list[str]:
    """Select options for NFC write dashboard (recipe drys + water kinds)."""
    from .recipe import WOOD_LOVER_RECIPE

    choices: list[str] = []
    for line in WOOD_LOVER_RECIPE:
        if line.key == "water":
            continue
        choices.append(line.label)
    choices.extend(WATER_KINDS.values())
    return choices


@dataclass(slots=True)
class PendingNfcWrite:
    """Dashboard / ESPHome handoff for the next NDEF write."""

    object_type: str | None = None
    object_id: str | None = None
    label: str | None = None
    ingredient_key: str | None = None
    water_kind: str | None = None
    zone_id: str | None = None
    nfc_uid: str | None = None
    ndef_payload: str | None = None
    status: str = "idle"
    progress_text: str = "Select a write target, then prepare NDEF."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
