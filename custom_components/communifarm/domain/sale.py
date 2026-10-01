"""Point-of-sale domain models (general tracking — not GAP/accounting compliance)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .container import require_confirm, validate_sale_pack_mass
from .models import new_id
from .validation import ValidationError

PAYMENT_CASH = "cash"
PAYMENT_CHECK = "check"
PAYMENT_VENMO = "venmo"
PAYMENT_DIGITAL = "digital"
PAYMENT_OTHER = "other"

PAYMENT_METHODS = frozenset(
    {
        PAYMENT_CASH,
        PAYMENT_CHECK,
        PAYMENT_VENMO,
        PAYMENT_DIGITAL,
        PAYMENT_OTHER,
    }
)

PACK_STATUS_OPEN = "open"
PACK_STATUS_SOLD = "sold"

DEFAULT_CURRENCY = "USD"

CLEANUP_CLEANED = "cleaned"
CLEANUP_PUT_AWAY = "put_away"
CLEANUP_READY_NEXT = "ready_next"

CLEANUP_CHECKLIST_KEYS = (CLEANUP_CLEANED, CLEANUP_PUT_AWAY, CLEANUP_READY_NEXT)


@dataclass(slots=True)
class Sale:
    """Sale header — venue, buyer, payment after money received."""

    venue_label: str
    buyer_label: str
    payment_method: str
    total_amount: float
    sold_at: str
    created_at: str
    currency: str = DEFAULT_CURRENCY
    notes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("sale")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SaleLineItem:
    """One sold pack / weigh-at-sale line under a sale."""

    sale_id: str
    sale_pack_id: str
    batch_id: str
    harvest_id: str
    product_label: str
    mass_g: float
    line_amount: float
    created_at: str
    unit_price: float | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("sline")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SaleCleanupEvent:
    """Post-sale clean / put-away checklist event."""

    recorded_at: str
    created_at: str
    sale_id: str | None = None
    sale_day: str | None = None
    checklist_json: str = "{}"
    notes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("sclean")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_payment_method(method: str) -> str:
    value = (method or "").strip().lower()
    if value not in PAYMENT_METHODS:
        raise ValidationError(
            f"payment_method must be one of {sorted(PAYMENT_METHODS)}"
        )
    return value


def validate_label(value: str, *, field: str, max_len: int = 120) -> str:
    text = (value or "").strip()
    if not text:
        raise ValidationError(f"{field} is required")
    if len(text) > max_len:
        raise ValidationError(f"{field} must be <= {max_len} characters")
    return text


def validate_money(amount: float, *, field: str = "amount") -> float:
    try:
        value = float(amount)
    except (TypeError, ValueError) as err:
        raise ValidationError(f"{field} must be a number") from err
    if value != value or value in (float("inf"), float("-inf")):
        raise ValidationError(f"{field} must be a finite number")
    if value < 0:
        raise ValidationError(f"{field} must be >= 0")
    if value > 1_000_000:
        raise ValidationError(f"{field} must be <= 1000000")
    return round(value, 2)


def build_cleanup_checklist(
    *,
    cleaned: bool = True,
    put_away: bool = True,
    ready_next: bool = True,
) -> dict[str, bool]:
    return {
        CLEANUP_CLEANED: bool(cleaned),
        CLEANUP_PUT_AWAY: bool(put_away),
        CLEANUP_READY_NEXT: bool(ready_next),
    }


def assert_can_sell_pack(*, status: str, pack_id: str) -> None:
    if status != PACK_STATUS_OPEN:
        raise ValidationError(f"sale_pack {pack_id} is not open (status={status})")


# Re-export for callers that already import confirm/mass from sale domain.
__all__ = [
    "CLEANUP_CHECKLIST_KEYS",
    "CLEANUP_CLEANED",
    "CLEANUP_PUT_AWAY",
    "CLEANUP_READY_NEXT",
    "DEFAULT_CURRENCY",
    "PACK_STATUS_OPEN",
    "PACK_STATUS_SOLD",
    "PAYMENT_METHODS",
    "PAYMENT_CASH",
    "PAYMENT_CHECK",
    "PAYMENT_DIGITAL",
    "PAYMENT_OTHER",
    "PAYMENT_VENMO",
    "Sale",
    "SaleCleanupEvent",
    "SaleLineItem",
    "assert_can_sell_pack",
    "build_cleanup_checklist",
    "require_confirm",
    "validate_label",
    "validate_money",
    "validate_payment_method",
    "validate_sale_pack_mass",
]
