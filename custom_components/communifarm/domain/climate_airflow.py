"""Outdoor-air exchange estimates and human-escalation capability checks.

Pure domain. No Home Assistant imports.

Estimates use enclosure volume and known intake/exhaust CFM (commissioned or
tachometer-derived). Mixing is modeled as a first-order lag — nothing jumps
instantly. When outdoor air and bound machines cannot close an excursion in a
plausible time, Communifarm raises a human-required notice. Machines do not
resize themselves, invent capacity, or silently rewrite setpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp, log

# ft³ per m³ — ACH = CFM × 60 / volume_ft³
_M3_TO_FT3 = 35.3146667

# After this many time-constants of OA exchange with no useful progress,
# treat the loop as saturated and hand off to a human.
_SATURATION_TAU_MULTIPLIER = 2.0

# Minimum observed progress toward target as a fraction of the first-order
# expectation before we call hardware undersized (accounts for sensor noise).
_MIN_PROGRESS_RATIO = 0.35

CAPABILITY_UNKNOWN = "unknown"
CAPABILITY_SUFFICIENT = "sufficient"
CAPABILITY_WAITING = "waiting_smoothed"
CAPABILITY_UNDERSIZED = "undersized"
CAPABILITY_HUMAN_REQUIRED = "human_required"

CAPABILITY_CODES = frozenset(
    {
        CAPABILITY_UNKNOWN,
        CAPABILITY_SUFFICIENT,
        CAPABILITY_WAITING,
        CAPABILITY_UNDERSIZED,
        CAPABILITY_HUMAN_REQUIRED,
    }
)


@dataclass(frozen=True, slots=True)
class EnclosureAirflow:
    """Commissioned size and fan capacity for one climate volume."""

    volume_m3: float | None = None
    intake_cfm: float | None = None
    exhaust_cfm: float | None = None
    # Minutes of active exchange/conditioning before undersize assessment.
    assess_after_minutes: float = 30.0


@dataclass(frozen=True, slots=True)
class ExchangeEstimate:
    """First-order OA mixing projection for one node at one tick."""

    ach: float | None
    tau_minutes: float | None
    effective_cfm: float | None
    oa_can_reach_temperature: bool | None
    oa_can_reach_humidity: bool | None
    projected_temp_c: float | None
    projected_humidity: float | None
    minutes_ahead: float
    capability: str
    human_required: bool
    human_reason: str | None


@dataclass(frozen=True, slots=True)
class CapabilityNotice:
    """Operator-visible notice. Machines stop here; humans decide the fix."""

    node_id: str
    code: str
    message: str
    ach: float | None = None
    tau_minutes: float | None = None
    projected_temp_c: float | None = None


@dataclass(frozen=True, slots=True)
class ExchangeProgress:
    """Historical hint for smoothed reaction assessment."""

    exchange_or_condition_on_since: datetime | None = None
    temp_when_action_started: float | None = None
    humidity_when_action_started: float | None = None
    outdoor_temp_when_started: float | None = None
    outdoor_humidity_when_started: float | None = None


def effective_exchange_cfm(airflow: EnclosureAirflow) -> float | None:
    """Use the limiting OA path (intake vs exhaust)."""
    values = [
        value
        for value in (airflow.intake_cfm, airflow.exhaust_cfm)
        if value is not None and value > 0
    ]
    if not values:
        return None
    return min(values)


def estimate_ach(volume_m3: float | None, cfm: float | None) -> float | None:
    """Air changes per hour from volume and CFM. None when under-specified."""
    if volume_m3 is None or volume_m3 <= 0 or cfm is None or cfm <= 0:
        return None
    volume_ft3 = volume_m3 * _M3_TO_FT3
    return (cfm * 60.0) / volume_ft3


def mixing_tau_minutes(ach: float | None) -> float | None:
    """First-order time constant in minutes (≈63% of the way to outdoor)."""
    if ach is None or ach <= 0:
        return None
    return (60.0 / ach)


def project_mixed_value(
    indoor: float | None,
    outdoor: float | None,
    ach: float | None,
    minutes: float,
) -> float | None:
    """First-order approach of indoor toward outdoor over ``minutes``."""
    if indoor is None or outdoor is None or ach is None or ach <= 0 or minutes < 0:
        return None
    # indoor' = outdoor + (indoor - outdoor) * e^(-ACH * hours)
    hours = minutes / 60.0
    return outdoor + (indoor - outdoor) * exp(-ach * hours)


def minutes_to_fraction(
    ach: float | None, fraction: float = 1.0 - 1.0 / exp(1)
) -> float | None:
    """Minutes to reach ``fraction`` of the outdoor-indoor gap (default ~63%)."""
    if ach is None or ach <= 0 or not (0.0 < fraction < 1.0):
        return None
    hours = -log(1.0 - fraction) / ach
    return hours * 60.0


def oa_can_reach(
    indoor: float | None,
    outdoor: float | None,
    target: float | None,
    *,
    too_high: bool,
) -> bool | None:
    """Whether outdoor air alone can reach the target for one metric."""
    if indoor is None or outdoor is None or target is None:
        return None
    if too_high:
        return outdoor < indoor and outdoor <= target
    return outdoor > indoor and outdoor >= target


def assess_exchange(
    *,
    airflow: EnclosureAirflow,
    indoor_temp: float | None,
    indoor_humidity: float | None,
    outdoor_temp: float | None,
    outdoor_humidity: float | None,
    temperature_target: float | None,
    humidity_target: float | None,
    temp_deadband: float,
    humidity_deadband: float,
    minutes_ahead: float,
    progress: ExchangeProgress | None,
    now: datetime,
    conditioning_bound: bool,
    conditioning_on: bool,
    exchange_requested: bool,
) -> ExchangeEstimate:
    """Estimate OA effect and whether a human must intervene."""
    cfm = effective_exchange_cfm(airflow)
    ach = estimate_ach(airflow.volume_m3, cfm)
    tau = mixing_tau_minutes(ach)

    too_hot = (
        indoor_temp is not None
        and temperature_target is not None
        and indoor_temp > temperature_target + temp_deadband
    )
    too_cold = (
        indoor_temp is not None
        and temperature_target is not None
        and indoor_temp < temperature_target - temp_deadband
    )
    too_wet = (
        indoor_humidity is not None
        and humidity_target is not None
        and indoor_humidity > humidity_target + humidity_deadband
    )
    too_dry = (
        indoor_humidity is not None
        and humidity_target is not None
        and indoor_humidity < humidity_target - humidity_deadband
    )

    oa_temp = None
    if too_hot or too_cold:
        oa_temp = oa_can_reach(
            indoor_temp, outdoor_temp, temperature_target, too_high=too_hot
        )
    oa_hum = None
    if too_wet or too_dry:
        oa_hum = oa_can_reach(
            indoor_humidity, outdoor_humidity, humidity_target, too_high=too_wet
        )

    projected_temp = project_mixed_value(
        indoor_temp, outdoor_temp, ach, minutes_ahead
    )
    projected_hum = project_mixed_value(
        indoor_humidity, outdoor_humidity, ach, minutes_ahead
    )

    capability = CAPABILITY_UNKNOWN
    human_required = False
    human_reason: str | None = None

    out_of_band = too_hot or too_cold or too_wet or too_dry
    oa_helps_all = True
    if too_hot or too_cold:
        oa_helps_all = oa_helps_all and bool(oa_temp)
    if too_wet or too_dry:
        oa_helps_all = oa_helps_all and bool(oa_hum)
    if not (too_hot or too_cold or too_wet or too_dry):
        oa_helps_all = False

    if not out_of_band:
        capability = CAPABILITY_SUFFICIENT
    elif not oa_helps_all and not conditioning_bound:
        # Machines cannot invent cooling/drying capacity. Human decides.
        human_required = True
        human_reason = (
            "outdoor air cannot reach the target and no AC/dehumidifier "
            "is bound; operator must add capacity, change setpoints, or "
            "intervene manually"
        )
        capability = CAPABILITY_HUMAN_REQUIRED
    elif ach is None:
        # Still automate with on/off intents, but estimates need commissioning.
        capability = CAPABILITY_UNKNOWN
        human_reason = (
            "enclosure volume or fan CFM not commissioned; OA timing estimates "
            "unavailable until the operator records size and tachometer/CFM"
        )
    else:
        if not oa_helps_all and conditioning_bound and conditioning_on:
            capability, human_required, human_reason = _assess_progress(
                airflow=airflow,
                ach=ach,
                tau=tau,
                progress=progress,
                now=now,
                indoor_temp=indoor_temp,
                indoor_humidity=indoor_humidity,
                temperature_target=temperature_target,
                humidity_target=humidity_target,
                too_hot=too_hot,
                too_cold=too_cold,
                too_wet=too_wet,
                too_dry=too_dry,
                mode="conditioning",
            )
        elif oa_helps_all and exchange_requested:
            capability, human_required, human_reason = _assess_progress(
                airflow=airflow,
                ach=ach,
                tau=tau,
                progress=progress,
                now=now,
                indoor_temp=indoor_temp,
                indoor_humidity=indoor_humidity,
                temperature_target=temperature_target,
                humidity_target=humidity_target,
                too_hot=too_hot,
                too_cold=too_cold,
                too_wet=too_wet,
                too_dry=too_dry,
                mode="oa_exchange",
                outdoor_temp=outdoor_temp,
                outdoor_humidity=outdoor_humidity,
            )
        elif oa_helps_all:
            capability = CAPABILITY_WAITING
        else:
            capability = CAPABILITY_WAITING

    return ExchangeEstimate(
        ach=ach,
        tau_minutes=tau,
        effective_cfm=cfm,
        oa_can_reach_temperature=oa_temp,
        oa_can_reach_humidity=oa_hum,
        projected_temp_c=projected_temp,
        projected_humidity=projected_hum,
        minutes_ahead=minutes_ahead,
        capability=capability,
        human_required=human_required,
        human_reason=human_reason,
    )


def _assess_progress(
    *,
    airflow: EnclosureAirflow,
    ach: float | None,
    tau: float | None,
    progress: ExchangeProgress | None,
    now: datetime,
    indoor_temp: float | None,
    indoor_humidity: float | None,
    temperature_target: float | None,
    humidity_target: float | None,
    too_hot: bool,
    too_cold: bool,
    too_wet: bool,
    too_dry: bool,
    mode: str,
    outdoor_temp: float | None = None,
    outdoor_humidity: float | None = None,
) -> tuple[str, bool, str | None]:
    """Compare smoothed expectation to measured progress."""
    if progress is None or progress.exchange_or_condition_on_since is None:
        return CAPABILITY_WAITING, False, None

    elapsed = (now - progress.exchange_or_condition_on_since).total_seconds() / 60.0
    if elapsed < 0:
        return CAPABILITY_WAITING, False, None

    assess_after = max(1.0, float(airflow.assess_after_minutes))
    if tau is not None:
        assess_after = max(assess_after, tau * _SATURATION_TAU_MULTIPLIER)

    if elapsed < assess_after:
        return CAPABILITY_WAITING, False, None

    # Temperature progress vs first-order expectation when OA is the actuator.
    if mode == "oa_exchange" and (too_hot or too_cold):
        start = progress.temp_when_action_started
        outdoor = progress.outdoor_temp_when_started
        if outdoor is None:
            outdoor = outdoor_temp
        if (
            start is not None
            and indoor_temp is not None
            and outdoor is not None
            and ach is not None
        ):
            expected = project_mixed_value(start, outdoor, ach, elapsed)
            if expected is not None:
                expected_delta = abs(expected - start)
                actual_delta = abs(indoor_temp - start)
                if expected_delta > 0.2 and actual_delta < expected_delta * _MIN_PROGRESS_RATIO:
                    reason = (
                        f"OA exchange ran {elapsed:.0f} min; expected ~"
                        f"{expected_delta:.1f}°C move, saw {actual_delta:.1f}°C. "
                        "Fans or ducts may be undersized, blocked, or mislabeled; "
                        "operator must inspect hardware or resize capacity"
                    )
                    return CAPABILITY_UNDERSIZED, True, reason

    if mode == "conditioning" and (too_hot or too_cold or too_wet or too_dry):
        # Conditioning on past the assess window without returning to band.
        stuck: list[str] = []
        if too_hot:
            stuck.append("too hot")
        if too_cold:
            stuck.append("too cold")
        if too_wet:
            stuck.append("too humid")
        if too_dry:
            stuck.append("too dry")
        reason = (
            f"conditioning active {elapsed:.0f} min and still {', '.join(stuck)}. "
            "Bound AC/dehumidifier may be undersized for this enclosure and outdoor "
            "load; operator must intervene (capacity, setpoint, load, or manual vent)"
        )
        return CAPABILITY_UNDERSIZED, True, reason

    if temperature_target is not None and indoor_temp is not None:
        if too_hot or too_cold:
            return CAPABILITY_WAITING, False, None
    if humidity_target is not None and indoor_humidity is not None:
        if too_wet or too_dry:
            return CAPABILITY_WAITING, False, None
    return CAPABILITY_SUFFICIENT, False, None


def notice_from_estimate(node_id: str, estimate: ExchangeEstimate) -> CapabilityNotice | None:
    """Build an operator notice when the estimate needs human attention."""
    if estimate.human_required or estimate.capability in {
        CAPABILITY_UNDERSIZED,
        CAPABILITY_HUMAN_REQUIRED,
    }:
        return CapabilityNotice(
            node_id=node_id,
            code=estimate.capability
            if estimate.capability in CAPABILITY_CODES
            else CAPABILITY_HUMAN_REQUIRED,
            message=estimate.human_reason
            or "operator action required; automation cannot create the needed change",
            ach=estimate.ach,
            tau_minutes=estimate.tau_minutes,
            projected_temp_c=estimate.projected_temp_c,
        )
    if estimate.capability == CAPABILITY_UNKNOWN and estimate.human_reason:
        return CapabilityNotice(
            node_id=node_id,
            code=CAPABILITY_UNKNOWN,
            message=estimate.human_reason,
            ach=estimate.ach,
            tau_minutes=estimate.tau_minutes,
            projected_temp_c=estimate.projected_temp_c,
        )
    if estimate.capability == CAPABILITY_WAITING and estimate.ach is not None:
        tau = estimate.tau_minutes
        tau_txt = f"{tau:.0f} min" if tau is not None else "unknown"
        return CapabilityNotice(
            node_id=node_id,
            code=CAPABILITY_WAITING,
            message=(
                f"OA mix estimate ACH={estimate.ach:.2f}, τ≈{tau_txt}; "
                "response is smoothed — do not expect an instant change"
            ),
            ach=estimate.ach,
            tau_minutes=estimate.tau_minutes,
            projected_temp_c=estimate.projected_temp_c,
        )
    return None
