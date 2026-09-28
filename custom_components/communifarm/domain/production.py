"""Production inoculate / incubate / fruit / harvest (pure domain)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import new_id
from .validation import ValidationError

CONTAINER_BLOCK = "block"
CONTAINER_TUB = "tub"
CONTAINER_BAG = "bag"
CONTAINER_JAR = "jar"
CONTAINER_OTHER = "other"
PRODUCTION_CONTAINERS = frozenset(
    {
        CONTAINER_BLOCK,
        CONTAINER_TUB,
        CONTAINER_BAG,
        CONTAINER_JAR,
        CONTAINER_OTHER,
    }
)

DEFAULT_MAX_FLUSHES = 3

STAGE_INOCULATED = "inoculated"
STAGE_INCUBATING = "incubating"
STAGE_FRUITING = "fruiting"
STAGE_HARVESTING = "harvesting"
STAGE_COMPLETE = "complete"

PRODUCTION_STAGES = frozenset(
    {
        STAGE_INOCULATED,
        STAGE_INCUBATING,
        STAGE_FRUITING,
        STAGE_HARVESTING,
        STAGE_COMPLETE,
    }
)

# advance_production_stage only — complete comes from final harvest.
STAGE_TRANSITIONS: dict[str, frozenset[str]] = {
    STAGE_INOCULATED: frozenset({STAGE_INCUBATING}),
    STAGE_INCUBATING: frozenset({STAGE_FRUITING}),
    STAGE_FRUITING: frozenset({STAGE_HARVESTING}),
    STAGE_HARVESTING: frozenset(),
    STAGE_COMPLETE: frozenset(),
}

STAGE_ADVANCE_ORDER = (
    STAGE_INOCULATED,
    STAGE_INCUBATING,
    STAGE_FRUITING,
    STAGE_HARVESTING,
)

INOCULUM_UNITS = frozenset({"ml", "g", "cc", "wedge", "other"})


@dataclass(slots=True)
class InoculateSpec:
    """Inputs required to link a culture lot into a substrate batch."""

    culture_id: str
    container_type: str
    container_count: int
    substrate_g_per_container: float
    inoculum_amount: float | None = None
    inoculum_unit: str | None = None
    max_flushes: int = DEFAULT_MAX_FLUSHES
    expected_check_at: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HarvestEvent:
    """One flush harvest mass for a production batch."""

    batch_id: str
    mass_g: float
    recorded_at: str
    flush_number: int
    is_final: bool = False
    notes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("harv")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProductionSummary:
    """Operator-facing snapshot for the Production dashboard sensor."""

    batch_id: str
    lifecycle_phase: str
    culture_id: str | None = None
    container_type: str | None = None
    container_count: int | None = None
    substrate_g_per_container: float | None = None
    inoculum_amount: float | None = None
    inoculum_unit: str | None = None
    flush_count: int = 0
    max_flushes: int = DEFAULT_MAX_FLUSHES
    expected_check_at: str | None = None
    inoculated_at: str | None = None
    total_harvest_g: float = 0.0
    harvests: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_inoculate_spec(spec: InoculateSpec) -> InoculateSpec:
    if not spec.culture_id or not str(spec.culture_id).strip():
        raise ValidationError("culture_id is required")
    if spec.container_type not in PRODUCTION_CONTAINERS:
        raise ValidationError(
            f"container_type must be one of {sorted(PRODUCTION_CONTAINERS)}"
        )
    try:
        count = int(spec.container_count)
    except (TypeError, ValueError) as err:
        raise ValidationError("container_count must be an integer") from err
    if count < 1 or count > 500:
        raise ValidationError("container_count must be between 1 and 500")
    try:
        substrate = float(spec.substrate_g_per_container)
    except (TypeError, ValueError) as err:
        raise ValidationError("substrate_g_per_container must be a number") from err
    if substrate != substrate or substrate in (float("inf"), float("-inf")):
        raise ValidationError("substrate_g_per_container must be a finite number")
    if substrate <= 0:
        raise ValidationError("substrate_g_per_container must be > 0")

    inoculum_amount = spec.inoculum_amount
    inoculum_unit = spec.inoculum_unit
    if inoculum_amount is not None:
        try:
            inoculum_amount = float(inoculum_amount)
        except (TypeError, ValueError) as err:
            raise ValidationError("inoculum_amount must be a number") from err
        if inoculum_amount != inoculum_amount or inoculum_amount in (
            float("inf"),
            float("-inf"),
        ):
            raise ValidationError("inoculum_amount must be a finite number")
        if inoculum_amount < 0:
            raise ValidationError("inoculum_amount must be >= 0")
        if not inoculum_unit:
            raise ValidationError("inoculum_unit is required when inoculum_amount is set")
        if inoculum_unit not in INOCULUM_UNITS:
            raise ValidationError(
                f"inoculum_unit must be one of {sorted(INOCULUM_UNITS)}"
            )
    elif inoculum_unit:
        raise ValidationError("inoculum_amount is required when inoculum_unit is set")

    try:
        max_flushes = int(spec.max_flushes)
    except (TypeError, ValueError) as err:
        raise ValidationError("max_flushes must be an integer") from err
    if max_flushes < 1 or max_flushes > 20:
        raise ValidationError("max_flushes must be between 1 and 20")

    return InoculateSpec(
        culture_id=str(spec.culture_id).strip(),
        container_type=spec.container_type,
        container_count=count,
        substrate_g_per_container=substrate,
        inoculum_amount=inoculum_amount,
        inoculum_unit=inoculum_unit,
        max_flushes=max_flushes,
        expected_check_at=spec.expected_check_at,
        notes=spec.notes,
    )


def assert_can_inoculate(lifecycle_phase: str) -> None:
    """Allow inoculate after mix cool-down (or re-apply while still inoculated)."""
    blocked_early = {
        "dry_mixing",
        "wet_mixing",
        "settling",
        "field_capacity",
    }
    blocked_late = PRODUCTION_STAGES - {STAGE_INOCULATED}
    if lifecycle_phase in blocked_early:
        raise ValidationError(
            "finish mix / cooling before inoculating substrate containers"
        )
    if lifecycle_phase in blocked_late:
        raise ValidationError(
            f"cannot inoculate while batch is already in production phase {lifecycle_phase}"
        )


def next_production_stage(current: str) -> str:
    allowed = STAGE_TRANSITIONS.get(current, frozenset())
    if not allowed:
        raise ValidationError(
            f"no advance from phase {current}; use record_harvest(is_final=true) to complete"
        )
    # Deterministic single successor.
    for stage in STAGE_ADVANCE_ORDER:
        if stage in allowed:
            return stage
    return sorted(allowed)[0]


def assert_can_advance(current: str, target: str | None = None) -> str:
    resolved = target or next_production_stage(current)
    allowed = STAGE_TRANSITIONS.get(current, frozenset())
    if resolved not in allowed:
        raise ValidationError(
            f"cannot advance from {current} to {resolved}; allowed={sorted(allowed) or 'none'}"
        )
    return resolved


def assert_can_harvest(
    *,
    lifecycle_phase: str,
    flush_count: int,
    max_flushes: int,
    mass_g: float,
    is_final: bool,
) -> None:
    if lifecycle_phase not in {STAGE_HARVESTING, STAGE_FRUITING}:
        raise ValidationError(
            "batch must be fruiting or harvesting before recording harvest"
        )
    try:
        mass = float(mass_g)
    except (TypeError, ValueError) as err:
        raise ValidationError("mass_g must be a number") from err
    if mass != mass or mass in (float("inf"), float("-inf")):
        raise ValidationError("mass_g must be a finite number")
    if mass <= 0:
        raise ValidationError("mass_g must be > 0")
    if flush_count >= max_flushes and not is_final:
        raise ValidationError(
            f"flush_count {flush_count} already at max_flushes {max_flushes}; "
            "set is_final=true to complete"
        )


def format_production_markdown(summary: ProductionSummary) -> str:
    """Human-readable Production tab summary."""
    containers = (
        summary.container_count if summary.container_count is not None else "—"
    )
    substrate = (
        summary.substrate_g_per_container
        if summary.substrate_g_per_container is not None
        else "—"
    )
    inoculum = (
        summary.inoculum_amount if summary.inoculum_amount is not None else "—"
    )
    inoculum_unit = f" {summary.inoculum_unit}" if summary.inoculum_unit else ""
    lines = [
        "| Field | Value |",
        "| --- | --- |",
        f"| Batch | `{summary.batch_id}` |",
        f"| Phase | **{summary.lifecycle_phase}** |",
        f"| Culture | `{summary.culture_id or '—'}` |",
        f"| Containers | {containers} × {summary.container_type or '—'} |",
        f"| Substrate g/container | {substrate} |",
        f"| Inoculum | {inoculum}{inoculum_unit} |",
        f"| Flushes | {summary.flush_count} / {summary.max_flushes} |",
        f"| Total harvest (g) | {summary.total_harvest_g:g} |",
        f"| Next check | {summary.expected_check_at or '—'} |",
        f"| Inoculated at | {summary.inoculated_at or '—'} |",
    ]
    if summary.harvests:
        lines.extend(
            [
                "",
                "| Flush | Mass (g) | Final | When |",
                "| ---: | ---: | --- | --- |",
            ]
        )
        for h in summary.harvests:
            lines.append(
                f"| {h.get('flush_number')} | {h.get('mass_g')} | "
                f"{'yes' if h.get('is_final') else 'no'} | {h.get('recorded_at')} |"
            )
    return "\n".join(lines)
