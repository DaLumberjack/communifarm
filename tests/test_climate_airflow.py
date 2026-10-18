"""OA exchange estimates, smoothed projections, and human escalation — T0."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.communifarm.domain.climate_airflow import (
    CAPABILITY_HUMAN_REQUIRED,
    CAPABILITY_UNDERSIZED,
    CAPABILITY_WAITING,
    EnclosureAirflow,
    ExchangeProgress,
    assess_exchange,
    estimate_ach,
    mixing_tau_minutes,
    project_mixed_value,
)


def test_ach_from_volume_and_cfm() -> None:
    # 10 m³ ≈ 353.15 ft³; 100 CFM → ACH ≈ 100*60/353.15 ≈ 17.0
    ach = estimate_ach(10.0, 100.0)
    assert ach is not None
    assert 16.5 < ach < 17.5
    assert mixing_tau_minutes(ach) is not None
    assert mixing_tau_minutes(ach) == 60.0 / ach


def test_projection_is_smoothed_not_instant() -> None:
    # After a short time, indoor barely moves toward outdoor.
    early = project_mixed_value(30.0, 15.0, ach=6.0, minutes=2.0)
    later = project_mixed_value(30.0, 15.0, ach=6.0, minutes=30.0)
    assert early is not None and later is not None
    assert early > 26.5  # still near 30 after 2 minutes (first-order lag)
    assert later < early
    assert later > 15.0  # not instantly at outdoor


def test_oa_cannot_reach_without_conditioning_requires_human() -> None:
    estimate = assess_exchange(
        airflow=EnclosureAirflow(volume_m3=12.0, intake_cfm=80.0, exhaust_cfm=80.0),
        indoor_temp=28.0,
        indoor_humidity=70.0,
        outdoor_temp=32.0,
        outdoor_humidity=80.0,
        temperature_target=22.0,
        humidity_target=55.0,
        temp_deadband=1.0,
        humidity_deadband=5.0,
        minutes_ahead=15.0,
        progress=None,
        now=datetime(2026, 10, 17, 12, 0, tzinfo=UTC),
        conditioning_bound=False,
        conditioning_on=False,
        exchange_requested=True,
    )
    assert estimate.human_required is True
    assert estimate.capability == CAPABILITY_HUMAN_REQUIRED
    assert estimate.oa_can_reach_temperature is False
    assert "operator" in (estimate.human_reason or "").lower()


def test_undersized_oa_when_progress_lags_estimate() -> None:
    started = datetime(2026, 10, 17, 10, 0, tzinfo=UTC)
    now = started + timedelta(minutes=90)
    airflow = EnclosureAirflow(
        volume_m3=8.0,
        intake_cfm=120.0,
        exhaust_cfm=120.0,
        assess_after_minutes=20.0,
    )
    estimate = assess_exchange(
        airflow=airflow,
        indoor_temp=29.5,  # barely moved from 30
        indoor_humidity=55.0,
        outdoor_temp=15.0,
        outdoor_humidity=50.0,
        temperature_target=22.0,
        humidity_target=55.0,
        temp_deadband=1.0,
        humidity_deadband=5.0,
        minutes_ahead=30.0,
        progress=ExchangeProgress(
            exchange_or_condition_on_since=started,
            temp_when_action_started=30.0,
            outdoor_temp_when_started=15.0,
        ),
        now=now,
        conditioning_bound=False,
        conditioning_on=False,
        exchange_requested=True,
    )
    assert estimate.capability == CAPABILITY_UNDERSIZED
    assert estimate.human_required is True
    assert "undersized" in (estimate.human_reason or "").lower()


def test_conditioning_still_out_of_band_requires_human() -> None:
    started = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
    now = started + timedelta(minutes=60)
    estimate = assess_exchange(
        airflow=EnclosureAirflow(volume_m3=20.0, intake_cfm=50.0, exhaust_cfm=50.0),
        indoor_temp=27.0,
        indoor_humidity=80.0,
        outdoor_temp=30.0,
        outdoor_humidity=85.0,
        temperature_target=22.0,
        humidity_target=55.0,
        temp_deadband=1.0,
        humidity_deadband=5.0,
        minutes_ahead=20.0,
        progress=ExchangeProgress(exchange_or_condition_on_since=started),
        now=now,
        conditioning_bound=True,
        conditioning_on=True,
        exchange_requested=False,
    )
    assert estimate.capability == CAPABILITY_UNDERSIZED
    assert estimate.human_required is True
    assert "ac/dehumidifier" in (estimate.human_reason or "").lower()


def test_waiting_while_smoothed_oa_runs() -> None:
    started = datetime(2026, 10, 17, 11, 0, tzinfo=UTC)
    now = started + timedelta(minutes=5)
    estimate = assess_exchange(
        airflow=EnclosureAirflow(volume_m3=10.0, intake_cfm=100.0, exhaust_cfm=100.0),
        indoor_temp=28.0,
        indoor_humidity=50.0,
        outdoor_temp=15.0,
        outdoor_humidity=45.0,
        temperature_target=22.0,
        humidity_target=55.0,
        temp_deadband=1.0,
        humidity_deadband=5.0,
        minutes_ahead=10.0,
        progress=ExchangeProgress(
            exchange_or_condition_on_since=started,
            temp_when_action_started=28.0,
            outdoor_temp_when_started=15.0,
        ),
        now=now,
        conditioning_bound=False,
        conditioning_on=False,
        exchange_requested=True,
    )
    assert estimate.capability == CAPABILITY_WAITING
    assert estimate.human_required is False
    assert estimate.projected_temp_c is not None
    assert estimate.projected_temp_c < 28.0
