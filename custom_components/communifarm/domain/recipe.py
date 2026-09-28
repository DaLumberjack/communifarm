"""Default recipes and weigh-session progress (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass

from .weight import WeightEvent, ingredient_key_from_label

DEFAULT_RECIPE_SCALE_MIN = 0.1
DEFAULT_RECIPE_SCALE_MAX = 10.0
DEFAULT_RECIPE_SCALE = 1.0


@dataclass(frozen=True, slots=True)
class RecipeLine:
    """One line of a substrate recipe."""

    label: str
    amount: float
    unit: str  # g | qts | ...

    @property
    def key(self) -> str:
        return ingredient_key_from_label(self.label)


# Simpler Wood Lover (Fungaia Life) — intake docs/intake/mushroom data/recipe.md
WOOD_LOVER_RECIPE: tuple[RecipeLine, ...] = (
    RecipeLine("hardwood pellets", 3000.0, "g"),
    RecipeLine("hardwood shavings", 200.0, "g"),
    RecipeLine("shredded organic wheat straw", 500.0, "g"),
    RecipeLine("organic worm castings", 250.0, "g"),
    RecipeLine("organic wheat bran", 200.0, "g"),
    RecipeLine("vermiculite", 2.0, "qts"),
    RecipeLine("coco coir", 2.0, "qts"),
    RecipeLine("gypsum", 200.0, "g"),
    RecipeLine("potash", 50.0, "g"),
)


@dataclass(slots=True)
class LineProgress:
    """One recipe line vs recorded weigh-ins for the active batch."""

    key: str
    label: str
    unit: str
    base_amount: float
    target_amount: float
    recorded_amount: float | None
    status: str  # pending | recorded | close | over | under
    closeness_pct: float | None

    def to_attr_dict(self) -> dict[str, str | float | None]:
        return {
            "key": self.key,
            "label": self.label,
            "unit": self.unit,
            "base_amount": self.base_amount,
            "target_amount": self.target_amount,
            "recorded_amount": self.recorded_amount,
            "status": self.status,
            "closeness_pct": self.closeness_pct,
        }


@dataclass(slots=True)
class WeighSessionProgress:
    """Session snapshot for the Weigh dashboard (not full history dump)."""

    recipe_name: str
    recipe_scale: float
    batch_id: str
    batch_nfc_uid: str
    completed: int
    total: int
    next_label: str | None
    lines: list[LineProgress]

    @property
    def summary(self) -> str:
        return f"{self.completed}/{self.total} lines recorded"

    def progress_text(self) -> str:
        """Markdown-friendly table for HA sensors / Lovelace."""
        rows = [
            f"Scale **×{self.recipe_scale:g}** · Batch NFC `{self.batch_nfc_uid}`",
            "",
            "| Status | Ingredient | Target | Recorded | Close |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for line in self.lines:
            rec = (
                f"{line.recorded_amount:g} {line.unit}"
                if line.recorded_amount is not None
                else "—"
            )
            pct = (
                f"{line.closeness_pct:.0f}%"
                if line.closeness_pct is not None
                else "—"
            )
            mark = {
                "pending": "○",
                "recorded": "●",
                "close": "✓",
                "under": "↓",
                "over": "↑",
            }.get(line.status, "?")
            rows.append(
                f"| {mark} {line.status} | {line.label} | "
                f"{line.target_amount:g} {line.unit} | {rec} | {pct} |"
            )
        if self.next_label:
            rows.append("")
            rows.append(f"**Next:** {self.next_label}")
        return "\n".join(rows)


def clamp_recipe_scale(value: float) -> float:
    return max(DEFAULT_RECIPE_SCALE_MIN, min(DEFAULT_RECIPE_SCALE_MAX, float(value)))


def build_weigh_session_progress(
    *,
    batch_id: str,
    batch_nfc_uid: str,
    recipe_scale: float,
    events: list[WeightEvent],
    recipe: tuple[RecipeLine, ...] = WOOD_LOVER_RECIPE,
    recipe_name: str = "Simpler Wood Lover",
    close_band_pct: float = 5.0,
) -> WeighSessionProgress:
    """Map latest weight_events per ingredient onto scaled recipe targets."""
    scale = clamp_recipe_scale(recipe_scale)
    latest: dict[str, WeightEvent] = {}
    for event in events:
        if not event.ingredient_key:
            continue
        latest[event.ingredient_key] = event

    lines: list[LineProgress] = []
    completed = 0
    next_label: str | None = None
    for line in recipe:
        target = line.amount * scale
        event = latest.get(line.key)
        recorded = float(event.mass_g) if event is not None else None
        # Volumetric lines may later use a different measure; for now record mass_g as amount.
        if recorded is None:
            status = "pending"
            closeness = None
            if next_label is None:
                next_label = line.label
        else:
            completed += 1
            if target == 0:
                closeness = 100.0
                status = "recorded"
            else:
                closeness = 100.0 * (1.0 - abs(recorded - target) / target)
                closeness = max(0.0, min(100.0, closeness))
                delta_pct = abs(recorded - target) / target * 100.0
                if delta_pct <= close_band_pct:
                    status = "close"
                elif recorded < target:
                    status = "under"
                else:
                    status = "over"
        lines.append(
            LineProgress(
                key=line.key,
                label=line.label,
                unit=line.unit,
                base_amount=line.amount,
                target_amount=target,
                recorded_amount=recorded,
                status=status,
                closeness_pct=closeness,
            )
        )

    return WeighSessionProgress(
        recipe_name=recipe_name,
        recipe_scale=scale,
        batch_id=batch_id,
        batch_nfc_uid=batch_nfc_uid,
        completed=completed,
        total=len(recipe),
        next_label=next_label,
        lines=lines,
    )
