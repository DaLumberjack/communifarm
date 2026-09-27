/** Constants from docs/intake/initializaion_to_communifarm_setup.har (no secrets). */

export const HA_ONBOARDING_STEPS = [
  "user",
  "core_config",
  "analytics",
  "integration",
] as const;

export const WELCOME_CTA = /Create my smart home/i;

export const DEFAULT_CF_FLOW = {
  site: "Home Site",
  environment: "Main Tent",
  batch: "Batch 1",
  temperatureTarget: 22,
  humidityTarget: 88,
  temperatureEntity: "sensor.mock_temperature",
  humidityEntity: "sensor.mock_humidity",
  fanEntity: "fan.mock_circulation_fan",
} as const;
