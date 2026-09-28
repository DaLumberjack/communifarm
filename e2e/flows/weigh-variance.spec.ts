import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import {
  callServiceViaHass,
  getAttributesViaHass,
  getStateViaHass,
  reloadCommunifarmViaHass,
} from "../helpers/ha-api";
import { weighOneIngredientStepViaHass } from "../helpers/mock-scale";
import {
  variedWoodLoverSteps,
  type WeighVarianceMode,
  type WoodLoverLine,
} from "../helpers/wood-lover-recipe";

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
    expect(row!.recorded_amount).toBeCloseTo(step.amountG, 0);
  }
}

async function runVariedMix(
  page: import("@playwright/test").Page,
  mode: WeighVarianceMode,
  batchName: string
): Promise<void> {
  const cf = new CommunifarmPage(page);
  // Reload picks up new services / Batches dashboard after a code pull.
  await cf.openWeighStation();
  await reloadCommunifarmViaHass(page);
  await cf.openWeighStation();

  await callServiceViaHass(page, "communifarm", "complete_and_new_batch", {
    name: batchName,
  });
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_batch_nfc_uid"), {
      timeout: 30000,
    })
    .not.toBe("");

  const steps = variedWoodLoverSteps(mode, () => 0.42);
  for (const line of steps) {
    await weighOneIngredientStepViaHass(page, line);
    await expect
      .poll(async () => {
        const rows =
          ((await getAttributesViaHass(page, "sensor.communifarm_weigh_session"))
            .lines as Array<{ label: string; recorded_amount: number | null }>) ?? [];
        return rows.find((r) => r.label === line.label)?.recorded_amount ?? null;
      })
      .toBeCloseTo(line.amountG, 0);
  }
  await assertRecipeLinesRecorded(page, steps);

  await expect
    .poll(async () => {
      const attrs = await getAttributesViaHass(
        page,
        "sensor.communifarm_batch_milestones"
      );
      return (attrs.event_types as string[]) ?? [];
    })
    .toContain("dry_mixing_started");
}

test.describe("Weigh variance mixes (T1)", () => {
  test.beforeEach(() => {
    test.skip(getStage() !== "T1", "Variance mixes are T1");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );
  });

  test("under mix (−5% each ingredient) on a new batch", async ({ page }) => {
    test.setTimeout(240_000);
    await runVariedMix(page, "under", "Mix Under 5");
  });

  test("over mix (+5% each ingredient) on a new batch", async ({ page }) => {
    test.setTimeout(240_000);
    await runVariedMix(page, "over", "Mix Over 5");
  });

  test("random mix (±5% each ingredient) on a new batch", async ({ page }) => {
    test.setTimeout(240_000);
    await runVariedMix(page, "random", "Mix Random 5");
  });
});
