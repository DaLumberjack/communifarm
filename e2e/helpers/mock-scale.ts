import { Page } from "@playwright/test";
import { getCredentials, getHaUrl } from "../fixtures/environment";
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
 * Prefer this for T1 Playwright against local HA.
 */
export async function weighOneIngredientStepViaHass(
  page: Page,
  line: WoodLoverLine,
  opts?: { containerG?: number; useNfcScan?: boolean }
): Promise<void> {
  const containerG = opts?.containerG ?? MIX_BIN_TARE_G;
  const useNfc = opts?.useNfcScan !== false;

  if (useNfc) {
    await simulateMockNfcScanViaHass(page, line.nfcUid);
  } else {
    await selectMockScaleIngredientViaHass(page, line.label);
  }

  await setMockScaleCalibratedSensorViaHass(page, containerG);
  await pressMockScaleButtonViaHass(page, "tare");
  await setMockScaleCalibratedSensorViaHass(page, containerG + line.amountG);

  // Wait for net mass before record so Communifarm reads the right value.
  const expectedNet = line.amountG;
  for (let attempt = 0; attempt < 20; attempt++) {
    const raw = await getStateViaHass(page, "sensor.esp32dev_calibrated_g");
    if (Math.abs(Number.parseFloat(raw) - expectedNet) < 0.5) {
      break;
    }
    await page.waitForTimeout(250);
  }

  await pressMockScaleButtonViaHass(page, "record_weight");
}
