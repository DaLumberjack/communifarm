# Fixed / mock fixtures

## Local mocks (T1/T2)

| Fixture | Docs |
| --- | --- |
| Env sensors / fan / exhaust | `devcontainer/ha_config/configuration.yaml` |
| Scale `esp32dev_*` + NFC select stub | `packages/mock_esp32dev_scale.yaml`, [mock-scale.md](../user/mock-scale.md) |

Controllable via `input_number` / `input_select` / `button.press`. Prefer mocks for code-flow tests.

## Live test VM (T3)

Record the fixed ESPHome device registry id, entity ids, and safe actuator allowlist in the workspace intermediate contract (`docs/intermediate/test-ha-contract.md`). Do not invent pin mappings.

Dedicated lab scale/NFC hardware (not floor production gear) should be used when testing human process flows — see workspace `docs/intermediate/weigh-station-process-deferred.md`.

