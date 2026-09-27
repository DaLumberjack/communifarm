/** Environment helpers for Communifarm Playwright stages. */

export type Stage = "T1" | "T2" | "T3";

const ALLOWED = new Set([
  "http://127.0.0.1:8123",
  "http://localhost:8123",
  "http://192.168.102.20:8123",
]);

export function getStage(): Stage {
  const stage = (process.env.TEST_HA_STAGE || "T1") as Stage;
  if (!["T1", "T2", "T3"].includes(stage)) {
    throw new Error(`Invalid TEST_HA_STAGE: ${stage}`);
  }
  return stage;
}

export function getHaUrl(): string {
  const url = (process.env.TEST_HA_URL || "http://127.0.0.1:8123").replace(/\/$/, "");
  if (!ALLOWED.has(url)) {
    throw new Error(`Refusing non-allowlisted TEST_HA_URL: ${url}`);
  }
  return url;
}

export function getCredentials(): { username: string; password: string; token?: string } {
  const username = process.env.TEST_HA_USERNAME;
  const password = process.env.TEST_HA_PASSWORD;
  if (!username || !password) {
    throw new Error(
      "TEST_HA_USERNAME/TEST_HA_PASSWORD required (load via scripts/load_openbao_ha_secrets.sh)"
    );
  }
  return {
    username,
    password,
    token: process.env.TEST_HA_TOKEN,
  };
}

export function getOnboardCredentials(): {
  name: string;
  username: string;
  password: string;
} {
  const username = process.env.TEST_HA_ONBOARD_USERNAME || process.env.TEST_HA_USERNAME || "";
  const password = process.env.TEST_HA_ONBOARD_PASSWORD || process.env.TEST_HA_PASSWORD || "";
  const name = process.env.TEST_HA_ONBOARD_NAME || username;
  if (!username || !password || !name) {
    throw new Error(
      "Onboard credentials required: TEST_HA_ONBOARD_NAME/USERNAME/PASSWORD or TEST_HA_USERNAME/PASSWORD"
    );
  }
  return { name, username, password };
}

export function liveActuationEnabled(): boolean {
  return process.env.LIVE_ACTUATION_ENABLED === "true";
}
