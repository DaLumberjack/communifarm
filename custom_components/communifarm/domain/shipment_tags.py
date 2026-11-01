"""All-in-one shipment NFC pack — known chip UIDs Communifarm ships with.

These are stable physical-tag identities (not HA entity IDs). Seeding writes
them into Communifarm SQLite.

Sandbox: ``devcontainer`` packages expose fake last-NFC sensors / kit picker
that mirror these UIDs. Production: integration only updates helpers that
already exist (real ESPHome); it never creates mock entities.
"""

from __future__ import annotations

from dataclasses import dataclass

from .inventory import OBJECT_CONTAINER, OBJECT_EMPLOYEE, OBJECT_INVENTORY, OBJECT_LOCATION

STATUS_AVAILABLE = "available"
STATUS_BOUND = "bound"
STATUS_RESERVED = "reserved"

DEFAULT_SHIPMENT_ID = "cf-kit-wood-lover-v1"


@dataclass(frozen=True, slots=True)
class ShipmentTagSpec:
    """One chip in the shipped kit."""

    nfc_uid: str
    intended_type: str
    label: str
    ingredient_key: str | None = None


# UIDs align with local mock scale NFC→ingredient automations where applicable.
DEFAULT_SHIPMENT_TAGS: tuple[ShipmentTagSpec, ...] = (
    ShipmentTagSpec(
        "nfc-hardwood-pellets",
        OBJECT_INVENTORY,
        "hardwood pellets",
        "hardwood_pellets",
    ),
    ShipmentTagSpec(
        "nfc-hardwood-shavings",
        OBJECT_INVENTORY,
        "hardwood shavings",
        "hardwood_shavings",
    ),
    ShipmentTagSpec(
        "nfc-wheat-straw",
        OBJECT_INVENTORY,
        "shredded organic wheat straw",
        "shredded_organic_wheat_straw",
    ),
    ShipmentTagSpec(
        "nfc-worm-castings",
        OBJECT_INVENTORY,
        "organic worm castings",
        "organic_worm_castings",
    ),
    ShipmentTagSpec("nfc-wheat-bran", OBJECT_INVENTORY, "organic wheat bran", "organic_wheat_bran"),
    ShipmentTagSpec("nfc-vermiculite", OBJECT_INVENTORY, "vermiculite", "vermiculite"),
    ShipmentTagSpec("nfc-coco-coir", OBJECT_INVENTORY, "coco coir", "coco_coir"),
    ShipmentTagSpec("nfc-gypsum", OBJECT_INVENTORY, "gypsum", "gypsum"),
    ShipmentTagSpec("nfc-potash", OBJECT_INVENTORY, "potash", "potash"),
    ShipmentTagSpec("nfc-water-tap", OBJECT_INVENTORY, "water (tap)", "water"),
    # Production-block / bag chips (available until bound to a container).
    ShipmentTagSpec("nfc-bag-01", OBJECT_CONTAINER, "bag / block 01"),
    ShipmentTagSpec("nfc-bag-02", OBJECT_CONTAINER, "bag / block 02"),
    ShipmentTagSpec("nfc-bag-03", OBJECT_CONTAINER, "bag / block 03"),
    ShipmentTagSpec("nfc-bag-04", OBJECT_CONTAINER, "bag / block 04"),
    ShipmentTagSpec("nfc-bag-05", OBJECT_CONTAINER, "bag / block 05"),
    ShipmentTagSpec("nfc-employee-01", OBJECT_EMPLOYEE, "Operator kit badge"),
    ShipmentTagSpec("nfc-loc-cold-01", OBJECT_LOCATION, "Cold storage shelf 1"),
    ShipmentTagSpec("nfc-loc-sterile-01", OBJECT_LOCATION, "Sterilization staging"),
)
