import { getCredentials, getHaUrl } from "../fixtures/environment";

const INJECT_G = "input_number.esp32dev_inject_calibrated_sensor";
const SELECT = "input_select.esp32dev_selected_ingredient";
const NFC_UID = "input_text.esp32dev_last_nfc_uid";
const NFC_SCAN = "input_button.esp32dev_simulate_nfc_scan";

async function haApi(path: string, init: RequestInit = {}): Promise<Response> {
  const { token } = getCredentials();
  if (!token) {
    throw new Error("TEST_HA_TOKEN required for mock-scale REST helpers");
  }
  const headers = new Headers(init.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Content-Type", "application/json");
  return fetch(`${getHaUrl()}${path}`, { ...init, headers });
}

/** Set gross calibrated mass (grams) on the mock scale. */
export async function setMockScaleCalibratedSensor(grams: number): Promise<void> {
  const res = await haApi("/api/services/input_number/set_value", {
    method: "POST",
    body: JSON.stringify({ entity_id: INJECT_G, value: grams }),
  });
  if (!res.ok) {
    throw new Error(`setMockScaleCalibratedSensor failed: ${res.status}`);
  }
}

/** Select recipe ingredient (simulates NFC dropdown result). */
export async function selectMockScaleIngredient(option: string): Promise<void> {
  const res = await haApi("/api/services/input_select/select_option", {
    method: "POST",
    body: JSON.stringify({ entity_id: SELECT, option }),
  });
  if (!res.ok) {
    throw new Error(`selectMockScaleIngredient failed: ${res.status}`);
  }
}

/** Set mock NFC UID then press Simulate NFC Scan. */
export async function simulateMockNfcScan(uid: string): Promise<void> {
  const textRes = await haApi("/api/services/input_text/set_value", {
    method: "POST",
    body: JSON.stringify({ entity_id: NFC_UID, value: uid }),
  });
  if (!textRes.ok) {
    throw new Error(`set NFC UID failed: ${textRes.status}`);
  }
  const pressRes = await haApi("/api/services/input_button/press", {
    method: "POST",
    body: JSON.stringify({ entity_id: NFC_SCAN }),
  });
  if (!pressRes.ok) {
    throw new Error(`simulate NFC scan failed: ${pressRes.status}`);
  }
}

export async function pressMockScaleButton(
  which: "tare" | "location_tare" | "record_weight"
): Promise<void> {
  const entityId = `button.esp32dev_${which}`;
  const res = await haApi("/api/services/button/press", {
    method: "POST",
    body: JSON.stringify({ entity_id: entityId }),
  });
  if (!res.ok) {
    throw new Error(`press ${entityId} failed: ${res.status}`);
  }
}
