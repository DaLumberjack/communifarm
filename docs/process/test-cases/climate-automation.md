# Climate automation — test cases

Operator doc: `repos/communifarm/docs/user/climate.md`

Quality oracle: `docs/intermediate/cea-quality-process.md`

Evidence: `docs/intermediate/climate-control.md`, `docs/intake/2026-10-06-cea-ventilation-occupancy-controls.md`

## Room and tent ventilation

When you bind room or tent sensors and fans, these tests verify that useful outside/parent air starts ventilation, stale or wrong-direction air does not, and no unbound actuator is invented.

| field | value |
|-------|-------|
| CQA | Environment remains inside its configured profile without harmful blind actuation |
| CPP / gate | Fresh temperature/RH/CO2 reading and helpful source-air direction |
| acceptance | Existing node target plus configured deadband (±1°C / ±5% RH shipped) |
| flaw this case is built to catch | Fan starts from a missing sensor or outside air that worsens the excursion |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_general_room_independently_commands_intake_and_exhaust`; `tests/test_climate.py::test_too_hot_external_air_will_not_help_uses_ac`; `tests/test_climate.py::test_fruiting_hot_uses_cooler_general_before_ac` |
| pass means | Independent bound intake/exhaust entities receive the expected intent from fresh readings |
| pass does not mean | Commissioned CFM, pressure balance, live relay safety, or T3 proof |
| related batches | All active batches in the affected climate node |

## Mixed excursion rejects half-helpful air

When a tent is both too hot and too wet (or similarly mixed), exchange air must help every active excursion before intake/exhaust turn on.

| field | value |
|-------|-------|
| CQA | Parent/outdoor air does not trade one excursion for another |
| CPP / gate | Fresh temp + RH; parent and outdoor samples |
| acceptance | Cool-but-wrong humidity (or reverse) does not open tent exchange; room AC/dehumidifier may run instead |
| flaw this case is built to catch | Humidity-only “help” opens intake while parent is hotter than the tent |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_fruiting_hot_wet_general_triggers_room_ac_and_dehumidify` |
| pass means | Sensor matrix drives room conditioning when exchange air cannot fix all active bands |
| pass does not mean | Optimal energy use or duct balancing |
| related batches | Fruiting batches in the tent |

## CO2 high → increase tent airflow

When tent CO2 exceeds the node target, intake, exhaust, and circulation turn on (naive stale-air flush). O2 is not bound yet.

| field | value |
|-------|-------|
| CQA | Stale high-CO2 air is diluted without inventing unbound fans |
| CPP / gate | Fresh `co2_ppm` above `co2_ppm_target` |
| acceptance | Bound intake + exhaust + circulation receive on intents |
| flaw this case is built to catch | CO2 only toggles one fan or ignores circulation |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_co2_opens_intake_and_fresh_air_checks_outdoor` |
| pass means | High CO2 raises tent airflow on every bound exchange/circulation role |
| pass does not mean | Measured ACH or O2 recovery |
| related batches | Culture/incubation lots in that tent |

## Base circulation and multi-fan tent

Fruiting/incubation keep base circulation while a climate reading exists. Five circulation bindings all receive the same intent.

| field | value |
|-------|-------|
| CQA | Near-constant interior mixing without waiting for an excursion |
| CPP / gate | Fresh temp and/or RH sample on a base-circulation kind |
| acceptance | All bound non-zone circulation entities on; intake stays off while in band |
| flaw this case is built to catch | Only the first fan binding is commanded, or in-band airflow stops |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_fruiting_keeps_base_circulation_while_in_band`; `tests/test_climate.py::test_five_circulation_bindings_all_receive_base_intent`; `tests/test_climate.py::test_tick_turns_fruiting_fan_on_then_off` |
| pass means | Domain + HA tick keep fruiting circulation on through in-band recovery |
| pass does not mean | Crop-height 0.3 m/s proof |
| related batches | Fruiting/incubation batches |

## Parent outdoor exchange settles tent intake

When the general room is exchanging outdoor air, tent intakes turn off (settle) while circulation/exhaust may continue.

| field | value |
|-------|-------|
| CQA | Tents do not inhale unsettled/dirtier general-room air during OA exchange |
| CPP / gate | General fresh-air or helpful exchange on; tent intake bound |
| acceptance | Tent intake off with settle reason; circulation remains available |
| flaw this case is built to catch | Tent intake stays on during room OA flush |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_parent_outdoor_exchange_settles_tent_intake` |
| pass means | Cross-node coordination throttles tent intake |
| pass does not mean | Timed settle after exchange ends, or prefilter hardware |
| related batches | All tent batches under that general room |

## Fruiting humidifier

When fruiting RH falls below target − deadband, the bound humidifier turns on.

| field | value |
|-------|-------|
| CQA | Pinning/fruiting humidity is restored without running exchange when air cannot help |
| CPP / gate | Fresh RH below band; humidifier bound |
| acceptance | Humidifier on; base circulation on |
| flaw this case is built to catch | Dry fruiting only opens fans or ignores the humidifier |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_fruiting_too_dry_turns_humidifier_on` |
| pass means | Sensor→humidifier path works with concurrent circulation |
| pass does not mean | Water quality or droplet size |
| related batches | Fruiting batches |

## Culture activity ventilation

When you conduct culture work, these tests verify the culture-room circulation fan runs only when both the activity signal and occupancy are active.

| field | value |
|-------|-------|
| CQA | Culture work receives intended circulation without treating mere room presence as an aseptic-process record |
| CPP / gate | Fresh culture-activity signal AND current/recent occupancy |
| acceptance | Both gates true |
| flaw this case is built to catch | Fan runs for an empty room or for occupancy with no culture task |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_culture_fan_requires_activity_and_occupancy` |
| pass means | The pure controller requires both signals |
| pass does not mean | HEPA integrity, cleanroom classification, or measured pressure direction |
| related batches | Culture/media lots being handled during the active task |

## Occupancy lighting

When a person enters a controlled location, these tests verify its bound light overrides the clock and remains on for no more than the documented 20-minute vacancy hold.

| field | value |
|-------|-------|
| CQA | Safe task visibility while preserving the configured biological schedule after vacancy |
| CPP / gate | Fresh occupancy signal or last confirmed occupancy less than 20 minutes ago |
| acceptance | On while occupied/held; schedule resumes at 20 minutes |
| flaw this case is built to catch | Sensor flicker immediately darkens the room, or stale presence leaves lights on forever |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_occupancy_overrides_dark_schedule_then_expires` |
| pass means | Occupancy override and deterministic expiry work in domain logic |
| pass does not mean | Camera inference quality or live luminaire behavior |
| related batches | Any batch whose photoperiod shares the location |

## Row fan policy

When you assign a batch to a row with a bound row circulation fan, these tests verify the fan policy uses both lifecycle stage and the culture variety.

| field | value |
|-------|-------|
| CQA | Row air movement matches the assigned crop context instead of a whole-tent guess |
| CPP / gate | Active batch has zone, lifecycle stage, culture, and optional variety identity |
| acceptance | Fruiting/harvesting only; oyster profile 15 min on/5 min off, generic profile 10/10 until commissioned |
| flaw this case is built to catch | Incubating batch starts a fruiting fan or the final row binding is skipped |
| loop | `control` and `iteration` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_row_fan_uses_assigned_batch_stage_and_variety` |
| pass means | Per-zone intents differ by stage and supported variety profile |
| pass does not mean | The duty cycle produces a measured 0.3 m/s at the crop; verify airflow physically |
| related batches | Every active batch assigned to that zone |

## UI override and reset

When you change a room or row automation setting on the Climate dashboard,
these tests verify an administrator's override persists separately from the
repository default, drives the effective control value, survives preset
refresh, and can be reset without freezing an old default.

| field | value |
|-------|-------|
| CQA | Effective control limits are attributable and future default changes are not masked accidentally |
| CPP / gate | Authenticated HA administrator; selected node/row; setting inside its documented range |
| acceptance | Override wins while present; reset reveals current repository default |
| flaw this case is built to catch | UI changes only transient state, repo refresh destroys an override, or reset stores a stale copy |
| loop | `control` |
| stage | T0 + T1 |
| pytest or spec | `tests/test_climate.py::test_climate_setting_overrides_survive_repo_default_refresh_and_reset`; `tests/test_climate.py::test_climate_setting_changes_require_admin` |
| pass means | SQLite precedence, authorization boundary, and native entity state agree |
| pass does not mean | Future operator-role implementation or live actuator commissioning |
| related batches | Batches assigned to the selected room/row |

## OA ACH estimate and smoothed projection

When enclosure volume and fan CFM are commissioned, these tests verify ACH/τ math and that indoor projections approach outdoor gradually (not instantly).

| field | value |
|-------|-------|
| CQA | Operators see a credible time scale for OA exchange |
| CPP / gate | volume_m³ > 0; intake/exhaust CFM > 0 |
| acceptance | ACH = CFM×60/(volume_ft³); early projection still near indoor |
| flaw this case is built to catch | Treating a fan-on tick as a completed air change |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate_airflow.py::test_ach_from_volume_and_cfm`; `tests/test_climate_airflow.py::test_projection_is_smoothed_not_instant` |
| pass means | Domain math matches the commissioned size/CFM model |
| pass does not mean | Live duct CFM equals the nameplate |
| related batches | Batches in the commissioned enclosure |

## Human-required when machines cannot close the gap

When outdoor air cannot reach the target and no AC/dehumidifier is bound, or when progress lags the ACH expectation past the assess window, these tests verify a human-required / undersized notice.

| field | value |
|-------|-------|
| CQA | Excursions that hardware cannot fix are visible deviations, not silent green |
| CPP / gate | Outdoor vs target; optional conditioning bound; elapsed action time |
| acceptance | `human_required` or `undersized` notice; futile OA exchange stops when no conditioning path |
| flaw this case is built to catch | Automation keeps thrashing fans forever or pretends capacity appeared |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_climate_airflow.py::test_oa_cannot_reach_without_conditioning_requires_human`; `tests/test_climate_airflow.py::test_undersized_oa_when_progress_lags_estimate`; `tests/test_climate.py::test_oa_estimate_notice_and_human_required_when_outdoor_cannot_help` |
| pass means | Domain escalates to the operator; setpoints are not silently rewritten |
| pass does not mean | The operator’s physical fix is automated |
| related batches | All active batches in the affected node |

## Sources

- `docs/intake/2026-10-06-cea-ventilation-occupancy-controls.md` (V1–V8)
- `docs/intermediate/climate-control.md`
- `docs/intermediate/air-exchange-measurement.md`
- Operator equipment plan: per-tent 5× circulation + intake/exhaust; general OA + AC/dehumidifier; fruiting humidifier
