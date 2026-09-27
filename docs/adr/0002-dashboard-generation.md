# ADR 0002: Generated Lovelace dashboard model

## Status

Accepted

## Context

Users must see a useful dashboard immediately after setup without editing YAML.

## Decision

Build a pure `DashboardBuilder` that emits built-in Lovelace cards from bindings. Provision best-effort via lovelace APIs; always retain the model under `hass.data["communifarm"]["dashboard_config"]` for tests and fallbacks. Do not overwrite user-owned dashboards.

## Consequences

- No custom cards in MVP.
- Provisioning registers a storage-mode Lovelace dashboard (`url_path`: `communifarm`, `allow_single_word`) via HA's live `DashboardsCollection` (located through the `lovelace/dashboards/create` websocket handler) and saves the generated views with `LovelaceStorage.async_save`.
- DOMAIN `dashboard_config` remains a fallback assertion/diagnostics copy if Lovelace is not ready.
- Day-to-day temperature/humidity target changes happen on the managed dashboard via `number` entities (slider mode); Current settings markdown uses live `states()` templates so values stay accurate without re-provisioning.
