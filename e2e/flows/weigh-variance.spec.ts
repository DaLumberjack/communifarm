import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import { STEP_MS } from "../fixtures/timeouts";
import {
  getAttributesViaHass,
  reloadCommunifarmViaHass,
} from "../helpers/ha-api";
import { weighOneIngredientStepViaHass } from "../helpers/mock-scale";
import {
  variedWoodLoverSteps,
  type WeighVarianceMode,
  type WoodLoverLine,
} from "../helpers/wood-lover-recipe";
import {
  assertAmountWithinTolerance,
  expectSessionLineRecorded,
  resetWeighBatch,
} from "../helpers/weigh-session";

async function assertRecipeLinesRecorded(
  page: import("@playwright/test").Page,
  steps: WoodLoverLine[]
): Promise<void> {
  const attrs = await getAttributesViaHass(page, "sensor.communifarm_weigh_session");
  const lines = (attrs.lines as Array<{
    label: string;
    status: string;
    recorded_amount: number | null;
  }>) ?? [];
  expect(lines).toHaveLength(steps.length);
  for (const step of steps) {
    const row = lines.find((l) => l.label === step.label);
    expect(row, `missing ${step.label}`).toBeTruthy();
    expect(row!.status).not.toBe("pending");
    assertAmountWithinTolerance(row!.recorded_amount, step.amountG, step.label);
  }
}

async function runVariedMix(
  page: import("@playwright/test").Page,
  mode: WeighVarianceMode,
  batchName: string
): Promise<void> {
  const cf = new CommunifarmPage(page);
  await cf.openWeighStation();
  await reloadCommunifarmViaHass(page);
  await cf.openWeighStation();

  await resetWeighBatch(page, batchName);

  const steps = variedWoodLoverSteps(mode, () => 0.42);
  for (const line of steps) {
    await weighOneIngredientStepViaHass(page, line);
    await expectSessionLineRecorded(page, line.label, line.amountG);
  }
  await assertRecipeLinesRecorded(page, steps);

  await expect
    .poll(
      async () => {
        const attrs = await getAttributesViaHass(
          page,
          "sensor.communifarm_batch_milestones"
        );
        return (attrs.event_types as string[]) ?? [];
      },
      { timeout: STEP_MS }
    )
    .toContain("dry_mixing_started");
}

test.describe("Weigh variance mixes (T1)", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(() => {
    test.skip(getStage() !== "T1", "Variance mixes are T1");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );
  });

  test("under mix (−5% each ingredient) on a new batch", async ({ page }) => {
    test.setTimeout(240_000);
    await runVariedMix(page, "under", `Mix Under 5 ${Date.now()}`);
  });

  test("over mix (+5% each ingredient) on a new batch", async ({ page }) => {
    test.setTimeout(240_000);
    await runVariedMix(page, "over", `Mix Over 5 ${Date.now()}`);
  });

  test("random mix (±5% each ingredient) on a new batch", async ({ page }) => {
    test.setTimeout(240_000);
    await runVariedMix(page, "random", `Mix Random 5 ${Date.now()}`);
  });
});
