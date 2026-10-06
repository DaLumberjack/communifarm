# Climate layout — test cases

Operator doc: `repos/communifarm/docs/user/climate.md`

Quality oracle: `docs/intermediate/cea-quality-process.md`

## layout-image — the floor plan is visible

When you open the Layout tab, these tests verify the schematic is a PNG the card can load, and the labeled marks have entities.

| field | value |
|-------|-------|
| CQA | operator can see the rooms and the live values on the marks |
| CPP / gate | setup has seeded the climate tree |
| acceptance | PNG header, outdoor and fruiting ink colors, labeled roles bound |
| flaw this case is built to catch | SVG URL that the card will not paint, or a seeded tree with no bindings |
| loop | none |
| stage | T0 |
| pytest or spec | `tests/test_climate_layout.py::test_png_matches_the_outdoor_and_fruiting_ink`, `tests/test_climate.py::test_tick_turns_fruiting_fan_on_then_off` |
| pass means | the file is a PNG, the layout view is a desktop panel, and setup binds the drawing |
| pass does not mean | a phone layout, the browser painted it, or live hardware is attached |

### Expected record

| object | field | expected |
|--------|-------|----------|
| `sensor.communifarm_climate_status` | state | `11 nodes` |
| `sensor.communifarm_outdoor_temperature` | state | `12` |
| `www/communifarm/cea-layout.png` | header | PNG signature |
