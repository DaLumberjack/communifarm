"""Ops scheduling: projected next moves and priority alarms (pure domain)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .climate_control import ObservedState
from .location import STAGE_SUGGESTED_AREA_KIND
from .production import (
    STAGE_FRUITING,
    STAGE_INCUBATING,
    STAGE_TRANSITIONS,
)

PRIORITY_P1 = "p1"
PRIORITY_P2 = "p2"
PRIORITY_P3 = "p3"
PRIORITIES = frozenset({PRIORITY_P1, PRIORITY_P2, PRIORITY_P3})

CODE_MOVE_INCUBATING_TO_FRUITING = "move_incubating_to_fruiting"
CODE_LIGHT_ON_EXCEEDS_HOURS = "light_on_exceeds_hours"

# Provisional until process-evidence locks colonization dwell (hours).
DEFAULT_INCUBATION_DWELL_HOURS = 14 * 24
# Continuous on-time before P3 advisory (ROLE_LIGHT / UV overrun class).
MAX_CONTINUOUS_LIGHT_ON_HOURS = 16.0

BASIS_EXPECTED_CHECK = "expected_check_at"
BASIS_DWELL = "phase_dwell"


@dataclass(slots=True)
class OpsSubject:
    """One batch or container fact set for evaluation."""

    subject_id: str
    lifecycle_phase: str
    phase_changed_at: str | None = None
    created_at: str | None = None
    expected_check_at: str | None = None
    area_kind: str | None = None
    zone_id: str | None = None


@dataclass(slots=True)
class AlarmEvent:
    """Priority ops alarm — architecture core model."""

    priority: str
    code: str
    subject_id: str
    message: str
    due_at: str | None = None
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"{self.code}:{self.subject_id}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProjectedMove:
    """Next lifecycle move projected from phase + location + timing."""

    subject_id: str
    from_phase: str
    to_phase: str
    from_area_kind: str | None
    to_area_kind: str | None
    due_at: str
    basis: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpsQueue:
    """Snapshot for the ops-queue sensor and notifications."""

    alarms: list[AlarmEvent] = field(default_factory=list)
    projected_moves: list[ProjectedMove] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alarm_count": len(self.alarms),
            "alarms": [a.to_dict() for a in self.alarms],
            "projected_moves": [m.to_dict() for m in self.projected_moves],
            "summary": self.summary,
        }


def parse_iso(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def resolve_phase_anchor(subject: OpsSubject) -> datetime | None:
    """Prefer phase_changed_at; fall back to created_at."""
    return parse_iso(subject.phase_changed_at) or parse_iso(subject.created_at)


def incubation_due_at(subject: OpsSubject) -> tuple[datetime | None, str]:
    """Return (due_at, basis) for incubating → fruiting."""
    expected = parse_iso(subject.expected_check_at)
    if expected is not None:
        return expected, BASIS_EXPECTED_CHECK
    anchor = resolve_phase_anchor(subject)
    if anchor is None:
        return None, BASIS_DWELL
    return (
        anchor + timedelta(hours=DEFAULT_INCUBATION_DWELL_HOURS),
        BASIS_DWELL,
    )


def project_next_move(subject: OpsSubject, *, now: datetime) -> ProjectedMove | None:
    """Project the next stage move from transitions + suggested area."""
    allowed = STAGE_TRANSITIONS.get(subject.lifecycle_phase, frozenset())
    if not allowed:
        return None
    # Deterministic: prefer fruiting when incubating; else first sorted.
    if STAGE_FRUITING in allowed:
        to_phase = STAGE_FRUITING
    else:
        to_phase = sorted(allowed)[0]

    due: datetime | None = None
    basis = BASIS_DWELL
    if subject.lifecycle_phase == STAGE_INCUBATING:
        due, basis = incubation_due_at(subject)
    else:
        anchor = resolve_phase_anchor(subject)
        due = anchor or now

    if due is None:
        due = now

    return ProjectedMove(
        subject_id=subject.subject_id,
        from_phase=subject.lifecycle_phase,
        to_phase=to_phase,
        from_area_kind=subject.area_kind,
        to_area_kind=STAGE_SUGGESTED_AREA_KIND.get(to_phase),
        due_at=due.isoformat(),
        basis=basis,
    )


def _alarm_move_incubating(
    subject: OpsSubject, *, now: datetime
) -> AlarmEvent | None:
    if subject.lifecycle_phase != STAGE_INCUBATING:
        return None
    due, _basis = incubation_due_at(subject)
    if due is None or now < due:
        return None
    return AlarmEvent(
        priority=PRIORITY_P2,
        code=CODE_MOVE_INCUBATING_TO_FRUITING,
        subject_id=subject.subject_id,
        message=(
            f"Move `{subject.subject_id}` from incubation to fruiting "
            f"(due {due.isoformat()})."
        ),
        due_at=due.isoformat(),
        created_at=now.isoformat(),
        id=f"{CODE_MOVE_INCUBATING_TO_FRUITING}:{subject.subject_id}",
    )


def _alarm_light_overrun(
    node_id: str,
    observed: ObservedState,
    *,
    now: datetime,
    max_hours: float = MAX_CONTINUOUS_LIGHT_ON_HOURS,
) -> AlarmEvent | None:
    if not observed.light_on or observed.light_on_since is None:
        return None
    since = observed.light_on_since
    if since.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=since.tzinfo)
    elif since.tzinfo is None and now.tzinfo is not None:
        since = since.replace(tzinfo=now.tzinfo)
    hours_on = (now - since).total_seconds() / 3600.0
    if hours_on <= max_hours:
        return None
    due = since + timedelta(hours=max_hours)
    return AlarmEvent(
        priority=PRIORITY_P3,
        code=CODE_LIGHT_ON_EXCEEDS_HOURS,
        subject_id=node_id,
        message=(
            f"Light/UV on `{node_id}` continuous {hours_on:.1f} h "
            f"(max {max_hours:g} h)."
        ),
        due_at=due.isoformat(),
        created_at=now.isoformat(),
        id=f"{CODE_LIGHT_ON_EXCEEDS_HOURS}:{node_id}",
    )


_PRIORITY_ORDER = {PRIORITY_P1: 0, PRIORITY_P2: 1, PRIORITY_P3: 2}


def evaluate_ops(
    *,
    subjects: list[OpsSubject],
    light_observations: dict[str, ObservedState] | None = None,
    now: datetime,
    max_continuous_light_hours: float = MAX_CONTINUOUS_LIGHT_ON_HOURS,
) -> OpsQueue:
    """Evaluate projected moves and seed alarms from current facts."""
    alarms: list[AlarmEvent] = []
    moves: list[ProjectedMove] = []

    for subject in subjects:
        move = project_next_move(subject, now=now)
        if move is not None:
            moves.append(move)
        alarm = _alarm_move_incubating(subject, now=now)
        if alarm is not None:
            alarms.append(alarm)

    for node_id, observed in (light_observations or {}).items():
        light_alarm = _alarm_light_overrun(
            node_id,
            observed,
            now=now,
            max_hours=max_continuous_light_hours,
        )
        if light_alarm is not None:
            alarms.append(light_alarm)

    alarms.sort(
        key=lambda a: (_PRIORITY_ORDER.get(a.priority, 9), a.due_at or "", a.id)
    )
    moves.sort(key=lambda m: (m.due_at, m.subject_id))

    p2 = sum(1 for a in alarms if a.priority == PRIORITY_P2)
    p3 = sum(1 for a in alarms if a.priority == PRIORITY_P3)
    summary = (
        f"{len(alarms)} open ({p2} P2, {p3} P3); "
        f"{len(moves)} projected moves"
    )
    return OpsQueue(alarms=alarms, projected_moves=moves, summary=summary)


__all__ = [
    "AlarmEvent",
    "BASIS_DWELL",
    "BASIS_EXPECTED_CHECK",
    "CODE_LIGHT_ON_EXCEEDS_HOURS",
    "CODE_MOVE_INCUBATING_TO_FRUITING",
    "DEFAULT_INCUBATION_DWELL_HOURS",
    "MAX_CONTINUOUS_LIGHT_ON_HOURS",
    "OpsQueue",
    "OpsSubject",
    "PRIORITY_P1",
    "PRIORITY_P2",
    "PRIORITY_P3",
    "ProjectedMove",
    "evaluate_ops",
    "incubation_due_at",
    "parse_iso",
    "project_next_move",
    "resolve_phase_anchor",
]
