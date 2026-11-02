"""Weight / material process events (pure domain, no Home Assistant)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .models import new_id
from .validation import ValidationError

# Communifarm number.communifarm_manual_weigh_g sentinel: ignore → use scale.
MANUAL_WEIGH_OMIT_G = -1.0
MassSource = Literal["manual", "scale"]


@dataclass(slots=True, frozen=True)
class ResolvedWeighMass:
    """Mass used for record_weight — manual number or live scale."""

    mass_g: float
    source: MassSource
    manual_g: float | None
    scale_g: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_weigh_mass_g(
    *,
    manual_g: float | None,
    scale_g: float | None,
) -> ResolvedWeighMass:
    """Prefer manual grams when set (≥ 0); -1 / None omits and uses scale.

    ``0`` is a real value (ingredient not in this recipe / zero pour).
    Scale-only path requires a finite scale reading.
    """
    manual: float | None
    try:
        manual = None if manual_g is None else float(manual_g)
    except (TypeError, ValueError) as err:
        raise ValidationError("manual_weigh_g must be a number") from err

    if manual is not None and manual >= 0.0:
        return ResolvedWeighMass(
            mass_g=manual,
            source="manual",
            manual_g=manual,
            scale_g=_finite_or_none(scale_g),
        )

    scale = _finite_or_none(scale_g)
    if scale is None:
        raise ValidationError(
            "no mass available — set Manual weigh (g) ≥ 0, or fix the scale reading"
        )
    return ResolvedWeighMass(
        mass_g=scale,
        source="scale",
        manual_g=manual,
        scale_g=scale,
    )


def _finite_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:  # NaN
        return None
    return parsed


def ingredient_key_from_label(label: str) -> str:
    """Stable-ish slug for analysis joins (NFC map / recipe lines)."""
    cleaned = label.strip().lower().replace(" ", "_")
    return "".join(ch for ch in cleaned if ch.isalnum() or ch == "_") or "unknown"


@dataclass(slots=True)
class WeightEvent:
    """One recorded weigh-in tied to batch + ingredient."""

    site_id: str
    environment_id: str
    mass_g: float
    recorded_at: str
    batch_id: str | None = None
    ingredient_key: str | None = None
    ingredient_label: str | None = None
    source_entity_id: str | None = None
    nfc_uid: str | None = None
    inventory_lot_id: str | None = None
    unit: str = "g"
    recipe_scale: float | None = None
    target_amount: float | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("wgt")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
