# Climate rooms and machines

Communifarm can track more than one climate. A room or tent may have its own sensors, borrow the parent room’s reading, or stay unmonitored. Machines run only when a reading says they should, and only if you bound them.

This slice starts **naive**: on/off intents from fresh sensor readings, shipped deadbands, and a short settle rule when the general room exchanges outdoor air. Later versions harden CEA maintenance (timed settle, prefilters, measured CFM, O2) without throwing away the same sensor→actuator path.

Energy estimates and cost of goods are not part of this yet.

## Planned equipment (this site)

| Location | Equipment | Communifarm roles |
| --- | --- | --- |
| Outdoors | Temp / humidity / pressure | `temperature`, `humidity`, `pressure` |
| General room | Outside intake fan, exhaust fan, AC (cool + dehumidify as bound), heater, float + condensate pump | `fresh_air_intake`, `exhaust_fan`, `ac`, `dehumidifier` (if separate), `heater`, `float`, `condensate_pump` |
| Each tent | 5× circulation, 1× intake (from general), 1× exhaust (to general) | five `circulation_fan` bindings + `intake_fan` + `exhaust_fan` |
| Fruiting tent | Humidifier (plus the tent fans above) | `humidifier` |
| Inoculation / incubation | CO2 ppm (O2 not bound yet — high CO2 is the naive proxy for stale air) | `co2_ppm` |

Bind every physical fan/switch you install. Unbound roles never get inventing commands.

## Seed the layout

Setup does this for you. Calling **ensure_climate_layout** again is safe: it keeps the existing nodes and fills any labeled sensor or machine that is not bound yet.

That creates:

| Node | Parent | Control | What it is for |
| --- | --- | --- | --- |
| Outdoors | none | off | Temp, humidity, pressure |
| General room | outdoors | on | Your onboarding environment. AC, heater, fresh-air intake, condensate float and pump |
| Culture prep | general room | on | Tent: circulation, intake, exhaust |
| Inoculation | general room | on | Same, plus a CO2 ppm sensor. The intake fan is the air-exchange fan |
| Incubation | general room | on | Tent plus a fresh-air intake |
| Fruiting | general room | on | Tent, humidifier, dehumidifier if you bind one, lights |
| Harvest | general room | off | Optional sensors |
| Ready to sell | general room | off | Optional sensors |
| Hard goods storage | general room | off | Syringes, towels. No machines |
| Consumable storage | general room | off | Grain, seed. Optional sensors |
| General storage | general room | off | Optional sensors |

The general room keeps the name and id from setup. Calling the service again does not duplicate nodes. It does reset tent and storage targets to the preset below. The general room keeps the temperature and humidity from onboarding. Shelf areas (fruiting tent, inoculation tent, and so on) get a climate link when they do not already have one.

## Preset climates

These are the stand-in readings and the control targets for a standard gourmet (button, blue oyster), not a tropical species. Pink oyster and similar can fruit warmer, up to about 30°C. That is not this preset.

| Room | Temperature | Humidity | Why |
| --- | --- | --- | --- |
| Incubation | 22°C | 75% | Middle of 20–24°C and 70–80% RH. 25°C and above raises mold and bacterial risk during colonization |
| Fruiting | 20°C | 90% | Inside 15–21°C and 85–95% RH for pinning and fruiting |
| Harvest | 15°C | 85% | Humidity in the 80–90% band so fruit stays firm |
| Culture prep, inoculation | 22°C | 50% | Transfer rooms. The colonization humidity above is for incubation, not these benches |

Home Assistant may show those temperatures in °F only when its unit system is US customary. Communifarm stores every shipped target and gauge window in Celsius and in Fahrenheit. The dashboard follows Home Assistant's unit system. It does not keep a second toggle.

Prefer metric. The scratch Playwright onboarding test selects Metric before it leaves Home Assistant setup, including when the country is United States (that country otherwise starts in Fahrenheit). Click **Update** if Home Assistant asks to change sensor units.

Indoor temperature gauges are the target ±4°C (or ±7°F), not 0–40. Outdoor temperature gauges use −15–45°C (5–113°F). Humidity indoors is the target ±12 points. Those pairs live in `domain/climate_units.py`. Change them in git and reload Communifarm to update every install. A custom Celsius target that is not in that table has no Fahrenheit gauge center until a row is added.

## Bind a sensor or machine

The layout already has stand-in entities for everything labeled on the drawing:

| Where | What gets created |
| --- | --- |
| Outdoors | Temperature, humidity, pressure |
| General room | AC, heater, fresh-air intake, float, condensate pump |
| Culture prep, inoculation, incubation, fruiting | Five temperature probes and five humidity probes, one pair per dot |

Harvest and the storage rooms are names on the drawing only. They are not given machines.

`communifarm.bind_climate_role` adds another entity on that node and role. Use it when a real sensor or machine should replace the stand-in. The stand-in stays until you remove that binding.

Roles: `temperature`, `humidity`, `pressure`, `co2_ppm`, `occupancy`, `culture_activity`, `circulation_fan`, `intake_fan`, `exhaust_fan`, `fresh_air_intake`, `ac`, `heater`, `humidifier`, `dehumidifier`, `light`, `float`, `condensate_pump`.

You can bind several temperature sensors on one tent. One is enough. The decision uses the median and ignores unavailable sensors.

For a DC grow light whose driver heat lands in the general room, set `waste_heat_to_parent` on that light binding.

## What the tick does

Every minute, and when you call `tick_climate`, Communifarm reads those entities and commands the bound ones that are not already in the right state.

| Condition | Command |
| --- | --- |
| Too hot, and parent or outdoor air is cool enough to reach the target | Exhaust and intake on, AC off, heater off |
| Too hot, and that air will not reach the target | AC on if bound. Exchange fans stay off |
| Too cold | Heater on if bound, AC off |
| Too dry | Humidifier on if bound |
| Too humid, dehumidifier bound | Dehumidifier on |
| Too humid, no dehumidifier, outside air is dry enough | Exhaust and intake on |
| Too humid, outside air is not dry enough | Those fans stay off |
| CO2 above the node target | Intake fan on |
| Fresh-air intake | On only when outdoor air helps every out-of-band metric |
| Float sensor on | Condensate pump on |
| Float clear, missing, or no climate reading | Pump, heater, AC, humidifier, and dehumidifier stay off |
| Control off (storage and the like) | No commands, even if you bound a machine |

Shipped deadbands are ±1°C and ±5% RH (about 5% of a 20°C fruiting target for
temperature; humidity uses RH points). Administrators can override them on the
Climate tab; repository defaults still update with each Communifarm version when
no override is stored.

Exchange air (parent or outdoor) must help **every** active excursion at once.
Cool-but-wet outdoor air is not used to “fix” a tent that is both too hot and
too dry.

Fruiting and incubation keep **base circulation** on whenever a climate reading
exists (near-constant interior airflow). Out-of-band or high CO2 adds high-flow
reasons on the same fans. Row fans still use stage/variety duty cycles.

When the general room is exchanging outdoor air (fresh-air intake or helpful
exchange exhaust/intake), tent **intakes settle off** so tents do not pull
unsettled or dirtier room air. Circulation and tent exhaust may stay on. A
duct prefilter / timed settle window is the upgrade path; this slice only
throttles intake while the room exchange is active.

The general-room outside-air intake and exhaust are independent bindings. The
controller commands each entity separately.

Pressure is displayed but is not a default fan trigger. Safe pressure control
needs a calibrated differential-pressure sensor, a commissioned target, and a
known relief path. Two ordinary absolute-pressure sensors are not a cleanroom
controller, no matter how persuasive the dashboard looks.

## Example control flows (naive)

| Sensor story | Expected actions |
| --- | --- |
| Tent CO2 above target | Tent intake + exhaust + circulation on (flush with parent air) |
| Tent temp/RH beyond deadband; general cooler and drier enough to reach targets | Tent intake + exhaust on; AC off; circulation high-flow |
| Tent out of band; general also too hot/wet; outdoor unhelpful | Tent exchange off; general AC and/or dehumidifier on; tent humidifier only if too dry |
| General too hot; outdoor air can reach the room target | General `fresh_air_intake` + exhaust on; tent intakes settle off |
| Fruiting RH below target − deadband | Fruiting humidifier on; base circulation stays on |
| Float wet in general room | Condensate pump on (independent of temp) |

O2 is not a bound metric yet. Treat high CO2 as the stale-air signal until an O2 role exists.

## Activity and occupancy

Bind a binary presence entity as `occupancy`. `on` may come from a camera
presence integration, HC-SR04 occupancy helper, or another HA binary entity.
Presence turns the bound room light on even outside its normal schedule. After
the last confirmed presence, the light stays on for 20 minutes and then returns
to the biological schedule.

For Culture prep or Inoculation, also bind a binary task signal as
`culture_activity`. The circulation fan runs only when culture activity and
occupancy are both active (including the vacancy hold). Presence alone does not
claim that culture work happened.

## Row-specific circulation

Bind a row fan with `communifarm.bind_climate_role`, role
`circulation_fan`, and that row's `zone_id`. Communifarm resolves the active
batch assigned to the zone, follows its lifecycle stage, then resolves its
culture variety.

| crop context | initial fan policy |
| --- | --- |
| Blue/white oyster in fruiting or harvesting | 15 minutes on / 5 minutes off |
| Other/unknown variety in fruiting or harvesting | 10 minutes on / 10 minutes off |
| Inoculated/incubating, complete, or no active batch | off |

These are commissioning defaults, not proof of airflow. Measure at crop height;
the Pleurotus study cited below reported its best tested result at 0.3 m/s.
Room geometry, fan position, and obstructions decide whether an on/off command
actually produces that.

## Change automation settings in the UI

Open **Communifarm → Climate**. The settings cards use ordinary Home Assistant
select, number, and button entities:

1. Choose a room/tent or row.
2. Change the target, deadband, light timing, occupancy hold, or row fan cycle.
3. The next climate tick uses the saved override.
4. Press **Reset selected climate … defaults** to remove every override for
   that selected room or row.

Each number entity has a `value_source` attribute:

| value | meaning |
| --- | --- |
| `repo default` | The value comes from the version-controlled Communifarm preset. A future merged default change applies automatically. |
| `user override` | The local SQLite override wins until an administrator resets it. |

Overrides are per room/tent or row and survive restarts/upgrades. Changing one
room does not rewrite the global preset or another room. A CO2 target of `0`
disables CO2-triggered ventilation for the selected node.

Only authenticated Home Assistant administrators may select/edit/reset these
settings today. A dedicated Communifarm operator role is planned; it is not
silently approximated by granting every dashboard user control.

## Lights

On/off only. There is no spectrum control.

| Preset | Schedule | Where it starts |
| --- | --- | --- |
| fruiting | 12 h on / 12 h off from midnight | Fruiting |
| dark | always off | Culture prep, inoculation, incubation |
| greens | 16 h on / 8 h off | Only if you set that preset on a node that has a grow light |

Sources for the defaults: Paul Stamets, *Growing Gourmet and Medicinal Mushrooms* (12 h fruiting photoperiod; colonization does not need a fruiting light cycle). Toyoki Kozai, *Plant Factory* (16 h vegetative photoperiod for leafy greens). Species differ. Change `light_hours_on` / `light_hours_off` on the node if you need a different clock.

While a bound light is on, the heater in that room stays off. If the light is flagged `waste_heat_to_parent`, the general-room heater stays off too. A real overheating still starts the fan or AC immediately. The humidifier waits 15 minutes after the light turns on before treating a humidity drop as “too dry.”

## If a sensor is missing

An indoor room with no working sensor shows the parent reading and marks it inherited. Outdoors never borrows a parent. Storage can show an inherited value and still will not turn machines on.

The overview **Climate** card reads `sensor.communifarm_climate_status`.

## Manual vent tachometer (air exchange)

For semi-frequent air-exchange checks, label each vent and log a timestamped reading:

| Service | Purpose |
| --- | --- |
| `communifarm.upsert_air_vent` | Create/update a vent label + role |
| `communifarm.record_tachometer` | Store value (`rpm` / `cfm` / `fpm`) + timestamp |

Status: `sensor.communifarm_tachometer_status`. Operator helpers and detail: [air-exchange-tachometer.md](../hardware/air-exchange-tachometer.md). ACH math from CFM × room volume is later.

## Layout and Climate tabs

Two more tabs show the same preset.

| Tab | What you see |
| --- | --- |
| Layout | Schematic of outdoors, the general room, the four tents, and storage. Sensor numbers and fan icons sit on the room they belong to. A fan icon is highlighted while that fan is on. |
| Climate | 24-hour history, gauges that go yellow then red above the target, and a machine list with on/off color. |

The Layout tab is one full-width card for a desktop browser. A phone layout is later. Climate gauges follow Home Assistant's unit system and use the metric or Fahrenheit window stored with the integration. Indoor gauges sit close to the target. Outdoor gauges use a wider window.

The drawing is this site's preset. It will not line up with every shelf you add. It is close enough to see the rooms and the machines. Moving a tent on the drawing later means changing the layout table, not redrawing Home Assistant by hand. That editor is not built yet.

The image the layout tab shows is `config/www/communifarm/cea-layout.png` (`/local/communifarm/cea-layout.png`). A matching SVG is written next to it. The card uses the PNG because a picture-elements card will not display that SVG. Reload Communifarm after an update so the card points at the PNG.

## Failure behavior

If a sensor is unavailable and there is no parent value, climate machines are not turned on. A missing float turns the condensate pump off. Commands go only to entities you bound. This slice does not add an ESP32 program that keeps running if Home Assistant is down.

## Purchase Checklist

| have | item | level | why | lower-cost substitute | upgrade path |
| --- | --- | --- | --- | --- | --- |
| [ ] | General outside intake + exhaust fans | basic | Exchange outdoor air when it helps | One reversible fan | Separate OA intake + exhaust with dampers |
| [ ] | Per-tent intake + exhaust | basic | Move air vs general room | Shared duct with dampers | Dedicated fans per tent |
| [ ] | Five circulation fans per tent | reliable home | Near-constant interior mixing | 2–3 clip fans | Row-zoned fans + tach logging |
| [ ] | Fruiting humidifier | basic | Hold high RH for pinning | Hand mist (higher variance) | Humidistat-linked ultrasonic + RO water |
| [ ] | General AC / dehumidifier | reliable home | Condition parent air when outdoor will not help | AC only; watch RH | Separate dehumidifier + AC |
| [ ] | Tent CO2 sensor (inoc/incubate first) | reliable home | Stale-air / exchange trigger | Periodic manual meter | Multi-tent CO2 + future O2 |
| [ ] | Intake prefilter on general OA | advanced clean | Dirtier outdoor air before tents pull | Settle-only throttle (software today) | MERV/HEPA + timed settle |

## Minimal Process Upgrades

| current setup | smallest upgrade | failure mode reduced | why this first | source |
| --- | --- | --- | --- | --- |
| Fans guesswork | Bind sensors; let tick drive on/off | Blind actuation | Readings before more hardware | Operator layout |
| Tent pulls during room OA exchange | Keep settle throttle (shipped) | Contaminated/unsettled intake | Software before duct rebuild | This doc |
| Settling only | Add OA prefilter | Dust/spore load on exchange | Filter when exchange is routine | SARE culture-lab notes (V6) |
| On/off only | Log CFM/RPM per vent | Unproven airflow claims | Measurement before PWM | [air-exchange-tachometer.md](../hardware/air-exchange-tachometer.md) |
| CO2 proxy only | Add O2 role later | Ambiguous stale-air signal | CO2 evidence first | Zhang et al. 2022 |

## Sources

| Claim | Source |
| --- | --- |
| Incubation 20–24°C, fruiting 15–21°C for standard gourmet, tropical fruiting up to about 30°C, colonization 70–80% RH, pinning and fruiting 85–95% RH, harvest 80–90% RH | Operator note, 2026-10-01, captured in `docs/intake/2026-10-01-operator-growing-conditions.md` |
| Fruiting 12 h on / 12 h off; colonization does not need a fruiting light cycle | Paul Stamets, *Growing Gourmet and Medicinal Mushrooms* |
| 16 h vegetative photoperiod for leafy greens | Toyoki Kozai, *Plant Factory* |
| Stage/species-aware ventilation; Agaricus pinning/cropping 1,000–2,500 ppm | Penn State Extension, *Basic Procedures for Agaricus Mushroom Growing* |
| Fruiting Pleurotus sensitivity to excessive CO2 | Zhang et al., 2022, PMCID PMC9321156 |
| Tested Pleurotus air-velocity result of 0.3 m/s | Oh et al., *Journal of Mushrooms*, 2019 |
| 20-minute vacancy timeout used as the occupancy-light default | 2021 IECC occupancy-control summary |
| Culture labs separated/cleanable; HEPA when advancing | SARE *Specialty Mushroom Farm Book* (intake V6) |

Operator-facing verification: [climate automation test cases](../process/test-cases/climate-automation.md).
