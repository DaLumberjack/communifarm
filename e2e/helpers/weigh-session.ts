import { Page, expect } from "@playwright/test";
import {
  callServiceViaHass,
  getAttributesViaHass,
  getStateViaHass,
} from "./ha-api";
import { STEP_MS } from "../fixtures/timeouts";

/** Matches domain CLOSE_BAND_PCT — recorded mass within ±5% of expected. */
export const WEIGH_AMOUNT_TOLERANCE_PCT = 5;

type SessionLine = {
  label: string;
  status: string;
  recorded_amount: number | null;
};

/**
 * Start a fresh production batch and wait until the weigh session is empty
 * (all recipe lines pending) for that batch.
 */
export async function resetWeighBatch(
  page: Page,
  batchName: string
): Promise<void> {
  // Prior tests (mock-scale REST, sensor polls) may still be touching SQLite.
  await page.waitForTimeout(1000);

  await callServiceViaHass(page, "communifarm", "complete_and_new_batch", {
    name: batchName,
  });

  // Let batch/sensor SQLite writers settle before the first weigh (avoids locked races).
  await page.waitForTimeout(1500);

  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_batch_nfc_uid"), {
      timeout: STEP_MS,
    })
    .not.toBe("");

  await expect
    .poll(
      async () => {
        const attrs = await getAttributesViaHass(
          page,
          "sensor.communifarm_weigh_session"
        );
        const lines = (attrs.lines as SessionLine[]) ?? [];
        if (lines.length === 0) {
          return false;
        }
        return lines.every(
          (line) => line.status === "pending" && line.recorded_amount == null
        );
      },
      { timeout: STEP_MS }
    )
    .toBe(true);
}

/** Absolute gram slack for ±pct of expected (min 0.5 g for tiny qts stubs). */
export function amountToleranceG(
  expectedG: number,
  pct: number = WEIGH_AMOUNT_TOLERANCE_PCT
): number {
  return Math.max(0.5, (Math.abs(expectedG) * pct) / 100);
}

export function assertAmountWithinTolerance(
  recorded: number | null | undefined,
  expectedG: number,
  label: string
): void {
  expect(recorded, `${label}: recorded_amount missing`).toEqual(expect.any(Number));
  const slack = amountToleranceG(expectedG);
  expect(
    Math.abs((recorded as number) - expectedG),
    `${label}: recorded ${recorded} not within ±${slack}g of ${expectedG}`
  ).toBeLessThanOrEqual(slack);
}

/** Poll until the session line has a recorded amount within tolerance. */
export async function expectSessionLineRecorded(
  page: Page,
  label: string,
  expectedG: number
): Promise<void> {
  await expect
    .poll(
      async () => {
        const attrs = await getAttributesViaHass(
          page,
          "sensor.communifarm_weigh_session"
        );
        const lines = (attrs.lines as SessionLine[]) ?? [];
        const row = lines.find((r) => r.label === label);
        return row?.recorded_amount ?? null;
      },
      { timeout: STEP_MS }
    )
    .not.toBeNull();

  const attrs = await getAttributesViaHass(page, "sensor.communifarm_weigh_session");
  const lines = (attrs.lines as SessionLine[]) ?? [];
  const row = lines.find((r) => r.label === label);
  assertAmountWithinTolerance(row?.recorded_amount, expectedG, label);
}
