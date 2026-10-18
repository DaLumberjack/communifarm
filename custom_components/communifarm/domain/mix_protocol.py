"""Ordered mix-batch protocol checklist (pure domain)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .batch_milestones import (
    MILESTONE_COMPLETELY_MIXED,
    MILESTONE_CONTAINERS_SEPARATED,
    MILESTONE_DRY_MIXING_STARTED,
    MILESTONE_DRY_WET_MIX_STARTED,
    MILESTONE_DRYS_COMBINED,
    MILESTONE_FIELD_CAPACITY_REACHED,
    MILESTONE_RELOCATED_FOR_STERILIZATION,
    MILESTONE_REMAINING_WATER_ADDED,
    MILESTONE_SETTLING_STARTED,
    MILESTONE_WATER_ADDED,
)
from .recipe import WOOD_LOVER_RECIPE, WeighSessionProgress

# Ordered operator protocol for hardwood bulk substrate (top → bottom).
MIX_PROTOCOL_STEPS: tuple[tuple[str, str, str], ...] = (
    ("weigh_drys", "Weigh dry ingredients", "weigh_session"),
    ("drys_combined", "Mix all drys together", MILESTONE_DRYS_COMBINED),
    ("water_added", "Add water (first pour)", MILESTONE_WATER_ADDED),
    ("incorporate_1", "Incorporate water into drys", MILESTONE_DRY_WET_MIX_STARTED),
    ("remaining_water", "Add remaining water", MILESTONE_REMAINING_WATER_ADDED),
    ("incorporate_2", "Incorporate remaining water", MILESTONE_SETTLING_STARTED),
    ("field_capacity", "Reached field capacity", MILESTONE_FIELD_CAPACITY_REACHED),
    ("completely_mixed", "Completely mixed", MILESTONE_COMPLETELY_MIXED),
    ("bag_bin", "Bag / bin for inoculum type", MILESTONE_CONTAINERS_SEPARATED),
    (
        "relocate_sterile",
        "Relocate to sterilization-ready location",
        MILESTONE_RELOCATED_FOR_STERILIZATION,
    ),
)


@dataclass(slots=True)
class MixProtocolStep:
    key: str
    label: str
    done: bool
    gate: str  # milestone event_type or weigh_session

    def to_attr_dict(self) -> dict[str, str | bool]:
        return asdict(self)


# Steps belonging to the dry section vs wet section vs finish section.
DRY_SECTION_KEYS = frozenset({"weigh_drys", "drys_combined"})
WET_SECTION_KEYS = frozenset(
    {
        "water_added",
        "incorporate_1",
        "remaining_water",
        "incorporate_2",
        "field_capacity",
    }
)
FINISH_SECTION_KEYS = frozenset(
    {"completely_mixed", "bag_bin", "relocate_sterile"}
)


@dataclass(slots=True)
class MixProtocolProgress:
    batch_id: str
    completed: int
    total: int
    next_key: str | None
    next_label: str | None
    last_done_key: str | None
    last_done_label: str | None
    steps: list[MixProtocolStep]
    dry_weigh_done: bool
    field_capacity_ok: bool | None
    focus_hint: str | None = None

    @property
    def summary(self) -> str:
        return f"{self.completed}/{self.total} mix steps"

    @property
    def section(self) -> str:
        if self.next_key is None:
            return "done"
        if self.next_key in DRY_SECTION_KEYS:
            return "drys"
        if self.next_key in WET_SECTION_KEYS:
            return "wets"
        return "finish"

    def focus_text(self) -> str:
        """Operator focus card: current / last done / next."""
        current = self.next_label or "Protocol complete"
        last = self.last_done_label or "—"
        # Peek one step ahead of the current open step.
        ahead = "—"
        if self.next_key is not None:
            found_current = False
            for step in self.steps:
                if found_current and not step.done:
                    ahead = step.label
                    break
                if step.key == self.next_key:
                    found_current = True
        section = {
            "drys": "Dry ingredients",
            "wets": "Water / wet mix",
            "finish": "Bag & relocate",
            "done": "Done",
        }.get(self.section, self.section)
        rows = [
            f"**Section:** {section}",
            "",
            "| | |",
            "| --- | --- |",
            f"| **Now** | {current} |",
            f"| **Last done** | {last} |",
            f"| **Up next** | {ahead} |",
        ]
        if self.focus_hint:
            rows.extend(["", f"_{self.focus_hint}_"])
        if self.field_capacity_ok is False:
            rows.extend(
                [
                    "",
                    "_Field-capacity sensor outside calibrated band "
                    "(salts can skew capacitance — recalibrate for this substrate)._",
                ]
            )
        return "\n".join(rows)

    def progress_text(self) -> str:
        rows = [
            self.focus_text(),
            "",
            f"**Checklist** · `{self.summary}`",
            "",
            "| Done | Step |",
            "| --- | --- |",
        ]
        for step in self.steps:
            mark = "☑" if step.done else "☐"
            rows.append(f"| {mark} | {step.label} |")
        return "\n".join(rows)


def dry_recipe_line_count(recipe=WOOD_LOVER_RECIPE) -> int:
    return sum(1 for line in recipe if line.key != "water")


def build_mix_protocol_progress(
    *,
    batch_id: str,
    milestone_types: set[str] | list[str],
    weigh: WeighSessionProgress | None,
    field_capacity_ok: bool | None = None,
) -> MixProtocolProgress:
    """Build checklist; dry weigh is complete when every non-water line is recorded."""
    done_types = set(milestone_types)
    dry_total = dry_recipe_line_count()
    dry_done = 0
    if weigh is not None:
        dry_done = sum(
            1
            for line in weigh.lines
            if line.key != "water" and line.status != "pending"
        )
    dry_weigh_complete = dry_done >= dry_total and dry_total > 0
    # Auto dry_mixing_started alone is not enough — require recipe dry lines.
    if dry_weigh_complete:
        done_types.add(MILESTONE_DRY_MIXING_STARTED)

    steps: list[MixProtocolStep] = []
    completed = 0
    next_key: str | None = None
    next_label: str | None = None
    last_done_key: str | None = None
    last_done_label: str | None = None
    for key, label, gate in MIX_PROTOCOL_STEPS:
        if gate == "weigh_session":
            is_done = dry_weigh_complete
        else:
            is_done = gate in done_types
        steps.append(MixProtocolStep(key=key, label=label, done=is_done, gate=gate))
        if is_done:
            completed += 1
            last_done_key = key
            last_done_label = label
        elif next_key is None:
            next_key = key
            next_label = label

    focus_hint = None
    if next_key == "weigh_drys" and weigh is not None and weigh.next_label:
        focus_hint = f"Weigh next dry: **{weigh.next_label}**"
    elif next_key in {"water_added", "remaining_water"}:
        focus_hint = (
            "Location tare the mix vessel, add water, then **Record water pour** "
            "(pours sum toward 10200 g)."
        )
    elif next_key == "relocate_sterile":
        focus_hint = (
            "Scan at least one bag/bin NFC tag, then press "
            "**Relocate for sterilization** (documents the whole batch moved)."
        )

    return MixProtocolProgress(
        batch_id=batch_id,
        completed=completed,
        total=len(MIX_PROTOCOL_STEPS),
        next_key=next_key,
        next_label=next_label,
        last_done_key=last_done_key,
        last_done_label=last_done_label,
        steps=steps,
        dry_weigh_done=dry_weigh_complete,
        field_capacity_ok=field_capacity_ok,
        focus_hint=focus_hint,
    )


def next_open_milestone(progress: MixProtocolProgress) -> str | None:
    """Return milestone event_type for the next incomplete step (None if weigh)."""
    for step in progress.steps:
        if step.done:
            continue
        if step.gate == "weigh_session":
            return None
        return step.gate
    return None
