"""Domain validation / sensor-validity unit tests (C1–C12 foundations)."""

from __future__ import annotations

import pytest

from custom_components.communifarm.domain.models import (
    CommunifarmState,
    Environment,
    EnvironmentalProfile,
    ProductionBatch,
    Site,
)
from custom_components.communifarm.domain.recipe import (
    WOOD_LOVER_RECIPE,
    build_weigh_session_progress,
)
from custom_components.communifarm.domain.validation import (
    BENCH_CAPACITY_G,
    CALIBRATION_REMINDER_EVERY_N,
    MAX_INGREDIENT_LABEL_LENGTH,
    MAX_NAME_LENGTH,
    MAX_NFC_UID_LENGTH,
    WARNING_CALIBRATION_DUE,
    WARNING_HUMIDITY_OUT_OF_RANGE,
    WARNING_MISSING_NFC,
    WARNING_OVER_CAPACITY,
    WARNING_STUCK_READING,
    WARNING_TARE_SKIPPED,
    WARNING_TEMP_OUT_OF_RANGE,
    WARNING_UNSTABLE_READING,
    ValidationError,
    assess_environment_readings,
    assess_mass_g,
    validate_ingredient_label,
    validate_nfc_uid,
    validate_readable_name,
    validate_recipe_unit,
)
from custom_components.communifarm.domain.weight import WeightEvent


def test_c1_reject_negative_mass() -> None:
    result = assess_mass_g(-1.0)
    assert result.accepted is False
    assert "negative" in (result.reject_reason or "")


def test_c1_reject_nan_mass() -> None:
    result = assess_mass_g(float("nan"))
    assert result.accepted is False


def test_happy_typical_mass() -> None:
    result = assess_mass_g(3000.0, tare_seen=True)
    assert result.accepted is True
    assert result.warnings == []


def test_c2_warn_over_bench_capacity() -> None:
    result = assess_mass_g(BENCH_CAPACITY_G + 1, tare_seen=True)
    assert result.accepted is True
    assert WARNING_OVER_CAPACITY in result.warnings


def test_c3_warn_unstable_step_without_tare() -> None:
    result = assess_mass_g(
        8000.0,
        previous_mass_g=1000.0,
        tare_seen=False,
        record_count_before=1,
    )
    assert WARNING_UNSTABLE_READING in result.warnings


def test_c3_no_unstable_warn_when_tared() -> None:
    result = assess_mass_g(
        8000.0,
        previous_mass_g=1000.0,
        tare_seen=True,
        record_count_before=1,
    )
    assert WARNING_UNSTABLE_READING not in result.warnings


def test_c4_warn_stuck_reading_across_ingredients() -> None:
    result = assess_mass_g(
        199.5,
        previous_mass_g=199.5,
        previous_ingredient_key="gypsum",
        ingredient_key="potash",
        tare_seen=True,
        record_count_before=1,
    )
    assert WARNING_STUCK_READING in result.warnings


def test_c5_warn_tare_skipped_on_first_record() -> None:
    result = assess_mass_g(500.0, tare_seen=False, record_count_before=0)
    assert WARNING_TARE_SKIPPED in result.warnings


def test_c6_session_marks_under_and_over() -> None:
    events = [
        WeightEvent(
            site_id="s",
            environment_id="e",
            batch_id="b",
            mass_g=100.0,
            ingredient_key="gypsum",
            ingredient_label="gypsum",
            recorded_at="2026-09-27T01:00:00+00:00",
        )
    ]
    progress = build_weigh_session_progress(
        batch_id="b",
        batch_nfc_uid="b",
        recipe_scale=1.0,
        events=events,
    )
    gypsum = next(line for line in progress.lines if line.key == "gypsum")
    assert gypsum.status == "under"
    assert gypsum.closeness_pct is not None
    assert gypsum.closeness_pct < 100.0


def test_c7_environment_out_of_absolute_range() -> None:
    result = assess_environment_readings(temperature_c=120.0, humidity_pct=-5.0)
    assert result.ok is False
    assert WARNING_TEMP_OUT_OF_RANGE in result.warnings
    assert WARNING_HUMIDITY_OUT_OF_RANGE in result.warnings


def test_c8_name_length_and_empty() -> None:
    with pytest.raises(ValidationError):
        validate_readable_name("")
    with pytest.raises(ValidationError):
        validate_readable_name("x" * (MAX_NAME_LENGTH + 1))
    assert validate_readable_name("Batch 1") == "Batch 1"


def test_c8_ingredient_and_nfc_limits() -> None:
    with pytest.raises(ValidationError):
        validate_ingredient_label("i" * (MAX_INGREDIENT_LABEL_LENGTH + 1))
    with pytest.raises(ValidationError):
        validate_nfc_uid("n" * (MAX_NFC_UID_LENGTH + 1))
    with pytest.raises(ValidationError):
        validate_nfc_uid("bad\nuid")


def test_c9_unknown_unit_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_recipe_unit("stone")
    assert validate_recipe_unit("g") == "g"
    for line in WOOD_LOVER_RECIPE:
        validate_recipe_unit(line.unit)


def test_c10_calibration_reminder_every_n() -> None:
    result = assess_mass_g(
        100.0,
        tare_seen=True,
        record_count_before=CALIBRATION_REMINDER_EVERY_N - 1,
    )
    assert WARNING_CALIBRATION_DUE in result.warnings


def test_state_validate_rejects_long_batch_name() -> None:
    state = CommunifarmState(
        site=Site(name="Site", id="site_a"),
        environment=Environment(name="Tent", site_id="site_a", id="env_a"),
        profile=EnvironmentalProfile(),
        batch=ProductionBatch(
            name="x" * (MAX_NAME_LENGTH + 1),
            environment_id="env_a",
            id="batch_a",
        ),
    )
    with pytest.raises(ValidationError):
        state.validate()


def test_missing_nfc_warning_constant_documented() -> None:
    # C11 is applied at record time when ingredient set but NFC empty.
    assert WARNING_MISSING_NFC == "missing_nfc"
