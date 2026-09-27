"""Domain model unit tests."""

from __future__ import annotations

import pytest

from custom_components.communifarm.domain.models import (
    EnvironmentalProfile,
    ProductionBatch,
    suggest_role_from_entity,
)


def test_profile_validation_rejects_bad_humidity() -> None:
    with pytest.raises(ValueError):
        EnvironmentalProfile(humidity_target=140).validate()


def test_batch_transition_and_events() -> None:
    batch = ProductionBatch(name="B", environment_id="env")
    event = batch.transition("active", "2026-01-01T00:00:00Z")
    assert batch.stage == "active"
    assert event.event_type == "StageChanged"
    assert len(batch.events) == 1
    batch.transition("complete", "2026-01-01T01:00:00Z")
    assert batch.stage == "complete"
    with pytest.raises(ValueError):
        batch.transition("planned", "2026-01-01T02:00:00Z")


def test_suggest_role_from_device_class() -> None:
    assert (
        suggest_role_from_entity("sensor", "temperature", "°C") == "temperature_source"
    )
    assert suggest_role_from_entity("sensor", "humidity", "%") == "humidity_source"
    assert suggest_role_from_entity("fan", None, None) == "fan_actuator"
    assert suggest_role_from_entity("switch", None, None) == "switch_actuator"
    assert suggest_role_from_entity("light", None, None) is None


def test_state_roundtrip(sample_state) -> None:
    restored = type(sample_state).from_dict(sample_state.to_dict())
    assert restored.site.name == sample_state.site.name
    assert restored.batch.id == sample_state.batch.id
    assert len(restored.bindings) == 3
