# ADR 0002: Generated Lovelace dashboard model

## Status

Accepted

## Context

Users must see a useful dashboard immediately after setup without editing YAML.

## Decision

Build a pure `DashboardBuilder` that emits built-in Lovelace cards from bindings. Provision best-effort via lovelace APIs; always retain the model under `hass.data["communifarm"]["dashboard_config"]` for tests and fallbacks. Do not overwrite user-owned dashboards.

## Consequences

- No custom cards in MVP.
- Provisioning may be partial on some HA versions; DOMAIN data remains the source of truth for assertions.
