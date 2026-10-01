import { Page, expect } from "@playwright/test";
import { getCredentials, getHaUrl } from "../fixtures/environment";
import { STEP_MS } from "../fixtures/timeouts";
import { callServiceViaHass, getStateViaHass } from "./ha-api";
import { MIX_BIN_TARE_G, type WoodLoverLine } from "./wood-lover-recipe";

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

export async function setMockScaleCalibratedSensorViaHass(
  page: Page,
  grams: number
): Promise<void> {
  await callServiceViaHass(page, "input_number", "set_value", {
    entity_id: INJECT_G,
    value: grams,
  });
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

export async function selectMockScaleIngredientViaHass(
  page: Page,
  option: string
): Promise<void> {
  await callServiceViaHass(page, "input_select", "select_option", {
    entity_id: SELECT,
    option,
  });
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

export async function simulateMockNfcScanViaHass(
  page: Page,
  uid: string
): Promise<void> {
  await callServiceViaHass(page, "input_text", "set_value", {
    entity_id: NFC_UID,
    value: uid,
  });
  await callServiceViaHass(page, "input_button", "press", {
    entity_id: NFC_SCAN,
  });
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

export async function pressMockScaleButtonViaHass(
  page: Page,
  which: "tare" | "location_tare" | "record_weight"
): Promise<void> {
  const entityId = `button.esp32dev_${which}`;
  await callServiceViaHass(page, "button", "press", { entity_id: entityId });
}

/**
 * One human weigh step (REST token): NFC → tare mix bin → add mass → record.
 */
export async function weighOneIngredientStep(
  line: WoodLoverLine,
  opts?: { containerG?: number; useNfcScan?: boolean }
): Promise<void> {
  const containerG = opts?.containerG ?? MIX_BIN_TARE_G;
  const useNfc = opts?.useNfcScan !== false;

  if (useNfc) {
    await simulateMockNfcScan(line.nfcUid);
  } else {
    await selectMockScaleIngredient(line.label);
  }

  await setMockScaleCalibratedSensor(containerG);
  await pressMockScaleButton("tare");
  await setMockScaleCalibratedSensor(containerG + line.amountG);
  await pressMockScaleButton("record_weight");
}

/**
 * One human weigh step via logged-in hass (no long-lived token).
 *
 * Sets mock scale + tare, then persists with `communifarm.record_weight` only.
 * Do **not** also press `button.esp32dev_record_weight` — that fires the same
 * persist path via EVENT_CALL_SERVICE and races SQLite (Playwright then sees
 * opaque `page.evaluate: Object` from hass.callService).
 */
export async function weighOneIngredientStepViaHass(
  page: Page,
  line: WoodLoverLine,
  opts?: { containerG?: number; useNfcScan?: boolean }
): Promise<void> {
  // Unique bin mass per line so consecutive equal nets (e.g. under-mix bran/gypsum)
  // still change the gross reading before tare.
  const containerG =
    opts?.containerG ?? MIX_BIN_TARE_G + (Math.abs(hashLabel(line.label)) % 50);
  const useNfc = opts?.useNfcScan !== false;

  if (useNfc) {
    await simulateMockNfcScanViaHass(page, line.nfcUid);
  } else {
    await selectMockScaleIngredientViaHass(page, line.label);
  }

  await expect
    .poll(
      async () => getStateViaHass(page, "input_select.esp32dev_selected_ingredient"),
      { timeout: STEP_MS }
    )
    .toBe(line.label);

  await setMockScaleCalibratedSensorViaHass(page, containerG);
  await pressMockScaleButtonViaHass(page, "tare");
  await setMockScaleCalibratedSensorViaHass(page, containerG + line.amountG);

  const expectedNet = line.amountG;
  await expect
    .poll(
      async () =>
        Number.parseFloat(
          await getStateViaHass(page, "sensor.esp32dev_calibrated_g")
        ),
      { timeout: STEP_MS }
    )
    .toBeCloseTo(expectedNet, 0);

  // Authoritative Communifarm write (single path — no mock Record button).
  await callServiceViaHass(page, "communifarm", "record_weight", {
    mass_g: expectedNet,
    ingredient: line.label,
    nfc_uid: line.nfcUid,
  });
}

function hashLabel(label: string): number {
  let h = 0;
  for (let i = 0; i < label.length; i++) {
    h = (h * 31 + label.charCodeAt(i)) | 0;
  }
  return h;
}
