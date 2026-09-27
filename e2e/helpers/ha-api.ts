import { getCredentials, getHaUrl } from "../fixtures/environment";

/** Minimal HA REST helpers for mock injection and assertions. */
export async function haApi(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const { token } = getCredentials();
  if (!token) {
    throw new Error("TEST_HA_TOKEN required for API helpers (optional OpenBao field)");
  }
  const headers = new Headers(init.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Content-Type", "application/json");
  return fetch(`${getHaUrl()}${path}`, { ...init, headers });
}

export async function setMockTemperature(value: number): Promise<void> {
  const res = await haApi("/api/services/input_number/set_value", {
    method: "POST",
    body: JSON.stringify({
      entity_id: "input_number.mock_temperature",
      value,
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to set mock temperature: ${res.status}`);
  }
}

export async function getState(entityId: string): Promise<{ state: string }> {
  const res = await haApi(`/api/states/${entityId}`);
  if (!res.ok) {
    throw new Error(`Failed to get state ${entityId}: ${res.status}`);
  }
  return res.json() as Promise<{ state: string }>;
}

export async function setNumberValue(entityId: string, value: number): Promise<void> {
  const res = await haApi("/api/services/number/set_value", {
    method: "POST",
    body: JSON.stringify({ entity_id: entityId, value }),
  });
  if (!res.ok) {
    throw new Error(`Failed to set ${entityId} to ${value}: ${res.status}`);
  }
}

/** Read a Communifarm number entity as a float. */
export async function getNumberValue(entityId: string): Promise<number> {
  const body = await getState(entityId);
  const value = Number.parseFloat(body.state);
  if (Number.isNaN(value)) {
    throw new Error(`Expected numeric state for ${entityId}, got ${body.state}`);
  }
  return value;
}
