"""Weight / material process events (pure domain, no Home Assistant)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import new_id


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
    unit: str = "g"
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("wgt")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
