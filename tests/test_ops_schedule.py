"""T0: ops scheduling projected moves and seed alarms."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from custom_components.communifarm.domain.climate_control import ObservedState
from custom_components.communifarm.domain.location import (
    AREA_FRUITING_TENT,
    AREA_INOCULATION_TENT,
)
from custom_components.communifarm.domain.ops_schedule import (
    BASIS_DWELL,
    BASIS_EXPECTED_CHECK,
    CODE_LIGHT_ON_EXCEEDS_HOURS,
    CODE_MOVE_INCUBATING_TO_FRUITING,
    DEFAULT_INCUBATION_DWELL_HOURS,
    MAX_CONTINUOUS_LIGHT_ON_HOURS,
    PRIORITY_P2,
    PRIORITY_P3,
    OpsSubject,
    evaluate_ops,
    project_next_move,
)
from custom_components.communifarm.domain.production import (
    STAGE_FRUITING,
    STAGE_INCUBATING,
)
from custom_components.communifarm.storage import sqlite_db


def test_project_incubating_to_fruiting_uses_dwell() -> None:
    phase_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    now = phase_at + timedelta(hours=1)
    subject = OpsSubject(
        subject_id="cont_abc",
        lifecycle_phase=STAGE_INCUBATING,
        phase_changed_at=phase_at.isoformat(),
        area_kind=AREA_INOCULATION_TENT,
    )
    move = project_next_move(subject, now=now)
    assert move is not None
    assert move.to_phase == STAGE_FRUITING
    assert move.to_area_kind == AREA_FRUITING_TENT
    assert move.basis == BASIS_DWELL
    due = datetime.fromisoformat(move.due_at)
    assert due == phase_at + timedelta(hours=DEFAULT_INCUBATION_DWELL_HOURS)


def test_project_uses_expected_check_at_when_set() -> None:
    check = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
    subject = OpsSubject(
        subject_id="batch_1",
        lifecycle_phase=STAGE_INCUBATING,
        phase_changed_at=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        expected_check_at=check.isoformat(),
        area_kind=AREA_INOCULATION_TENT,
    )
    move = project_next_move(subject, now=check)
    assert move is not None
    assert move.basis == BASIS_EXPECTED_CHECK
    assert move.due_at == check.isoformat()


def test_p2_when_incubation_due() -> None:
    phase_at = datetime(2026, 1, 1, tzinfo=UTC)
    now = phase_at + timedelta(hours=DEFAULT_INCUBATION_DWELL_HOURS + 1)
    queue = evaluate_ops(
        subjects=[
            OpsSubject(
                subject_id="cont_due",
                lifecycle_phase=STAGE_INCUBATING,
                phase_changed_at=phase_at.isoformat(),
            )
        ],
        now=now,
    )
    assert any(
        a.code == CODE_MOVE_INCUBATING_TO_FRUITING
        and a.priority == PRIORITY_P2
        and a.subject_id == "cont_due"
        for a in queue.alarms
    )


def test_no_p2_before_incubation_due() -> None:
    phase_at = datetime(2026, 1, 1, tzinfo=UTC)
    now = phase_at + timedelta(hours=DEFAULT_INCUBATION_DWELL_HOURS - 1)
    queue = evaluate_ops(
        subjects=[
            OpsSubject(
                subject_id="cont_early",
                lifecycle_phase=STAGE_INCUBATING,
                phase_changed_at=phase_at.isoformat(),
            )
        ],
        now=now,
    )
    assert not any(
        a.code == CODE_MOVE_INCUBATING_TO_FRUITING for a in queue.alarms
    )


def test_p3_when_light_continuous_exceeds_max() -> None:
    now = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    since = now - timedelta(hours=MAX_CONTINUOUS_LIGHT_ON_HOURS + 2)
    queue = evaluate_ops(
        subjects=[],
        light_observations={
            "node_fruiting": ObservedState(light_on=True, light_on_since=since)
        },
        now=now,
    )
    assert any(
        a.code == CODE_LIGHT_ON_EXCEEDS_HOURS
        and a.priority == PRIORITY_P3
        and a.subject_id == "node_fruiting"
        for a in queue.alarms
    )


def test_no_p3_when_light_off_or_recent() -> None:
    now = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    recent = now - timedelta(hours=1)
    queue = evaluate_ops(
        subjects=[],
        light_observations={
            "node_a": ObservedState(light_on=False, light_on_since=recent),
            "node_b": ObservedState(light_on=True, light_on_since=recent),
        },
        now=now,
    )
    assert not any(
        a.code == CODE_LIGHT_ON_EXCEEDS_HOURS for a in queue.alarms
    )


def test_schema_v20_adds_phase_changed_at(tmp_path: Path) -> None:
    path = tmp_path / "communifarm.db"
    conn = sqlite_db.connect(path)
    try:
        version = sqlite_db.apply_migrations(conn)
        assert version == sqlite_db.SCHEMA_VERSION
        assert sqlite_db.SCHEMA_VERSION >= 20
        batch_cols = {row[1] for row in conn.execute("PRAGMA table_info(batches)")}
        cont_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(production_containers)")
        }
        assert "phase_changed_at" in batch_cols
        assert "phase_changed_at" in cont_cols
    finally:
        conn.close()
