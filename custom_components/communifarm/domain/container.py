"""Per-container production units (blocks/tubs/bags) under a batch."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import new_id
from .production import (
    DEFAULT_MAX_FLUSHES,
    PRODUCTION_CONTAINERS,
    STAGE_COMPLETE,
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INOCULATED,
    assert_can_harvest,
)
from .validation import ValidationError, validate_nfc_uid

CONTAINER_STATUS_ACTIVE = "active"
CONTAINER_STATUS_COMPLETE = "complete"


@dataclass(slots=True)
class ProductionContainer:
    """One physical production container with its own NFC + placement + flush count."""

    batch_id: str
    container_index: int
    container_type: str
    nfc_uid: str
    lifecycle_phase: str = STAGE_INOCULATED
    flush_count: int = 0
    max_flushes: int = DEFAULT_MAX_FLUSHES
    zone_id: str | None = None
    status: str = CONTAINER_STATUS_ACTIVE
    created_at: str = ""
    completed_at: str | None = None
    notes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("cont")
        if not self.nfc_uid:
            self.nfc_uid = self.id

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SalePack:
    """Bagged harvest portion linked to a harvest_event (buyer lives on sales)."""

    harvest_id: str
    mass_g: float
    created_at: str
    size_label: str | None = None
    zone_id: str | None = None
    status: str = "open"
    sold_sale_id: str | None = None
    notes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("pack")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_containers_for_inoculate(
    *,
    batch_id: str,
    container_type: str,
    container_count: int,
    max_flushes: int,
    zone_id: str | None,
    created_at: str,
) -> list[ProductionContainer]:
    if container_type not in PRODUCTION_CONTAINERS:
        raise ValidationError(
            f"container_type must be one of {sorted(PRODUCTION_CONTAINERS)}"
        )
    try:
        count = int(container_count)
    except (TypeError, ValueError) as err:
        raise ValidationError("container_count must be an integer") from err
    if count < 1 or count > 500:
        raise ValidationError("container_count must be between 1 and 500")
    containers: list[ProductionContainer] = []
    for index in range(1, count + 1):
        cont = ProductionContainer(
            batch_id=batch_id,
            container_index=index,
            container_type=container_type,
            nfc_uid="",  # filled in __post_init__ from id
            lifecycle_phase=STAGE_INOCULATED,
            flush_count=0,
            max_flushes=max_flushes,
            zone_id=zone_id,
            created_at=created_at,
        )
        containers.append(cont)
    return containers


def apply_container_harvest(
    container: ProductionContainer,
    *,
    mass_g: float,
    is_final: bool,
    return_to_fruiting: bool = True,
) -> ProductionContainer:
    """Mutate flush/phase rules for one container after a confirmed harvest."""
    if container.status != CONTAINER_STATUS_ACTIVE:
        raise ValidationError(f"container {container.id} is already complete")
    assert_can_harvest(
        lifecycle_phase=container.lifecycle_phase,
        flush_count=container.flush_count,
        max_flushes=container.max_flushes,
        mass_g=mass_g,
        is_final=is_final,
    )
    new_flush = int(container.flush_count) + 1
    if is_final or new_flush >= container.max_flushes:
        return ProductionContainer(
            id=container.id,
            batch_id=container.batch_id,
            container_index=container.container_index,
            container_type=container.container_type,
            nfc_uid=container.nfc_uid,
            lifecycle_phase=STAGE_COMPLETE,
            flush_count=new_flush,
            max_flushes=container.max_flushes,
            zone_id=container.zone_id,
            status=CONTAINER_STATUS_COMPLETE,
            created_at=container.created_at,
            completed_at=container.completed_at,
            notes=container.notes,
        )
    next_phase = STAGE_FRUITING if return_to_fruiting else STAGE_HARVESTING
    return ProductionContainer(
        id=container.id,
        batch_id=container.batch_id,
        container_index=container.container_index,
        container_type=container.container_type,
        nfc_uid=container.nfc_uid,
        lifecycle_phase=next_phase,
        flush_count=new_flush,
        max_flushes=container.max_flushes,
        zone_id=container.zone_id,
        status=CONTAINER_STATUS_ACTIVE,
        created_at=container.created_at,
        completed_at=None,
        notes=container.notes,
    )


def require_confirm(confirm: bool) -> None:
    if not confirm:
        raise ValidationError(
            "confirm=true is required for production-affecting harvest / inventory actions"
        )


def validate_sale_pack_mass(mass_g: float) -> float:
    try:
        mass = float(mass_g)
    except (TypeError, ValueError) as err:
        raise ValidationError("mass_g must be a number") from err
    if mass != mass or mass in (float("inf"), float("-inf")):
        raise ValidationError("mass_g must be a finite number")
    if mass <= 0:
        raise ValidationError("mass_g must be > 0")
    if mass > 50_000:
        raise ValidationError("mass_g must be <= 50000 (human-usable pack size)")
    return mass


def rebind_container_nfc(
    container: ProductionContainer, nfc_uid: str
) -> ProductionContainer:
    uid = validate_nfc_uid(nfc_uid, required=True)
    assert uid is not None
    return ProductionContainer(
        id=container.id,
        batch_id=container.batch_id,
        container_index=container.container_index,
        container_type=container.container_type,
        nfc_uid=uid,
        lifecycle_phase=container.lifecycle_phase,
        flush_count=container.flush_count,
        max_flushes=container.max_flushes,
        zone_id=container.zone_id,
        status=container.status,
        created_at=container.created_at,
        completed_at=container.completed_at,
        notes=container.notes,
    )
