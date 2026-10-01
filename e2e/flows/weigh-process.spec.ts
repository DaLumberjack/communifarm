import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import { STEP_MS } from "../fixtures/timeouts";
import {
  getAttributesViaHass,
  getStateViaHass,
} from "../helpers/ha-api";
import { weighOneIngredientStepViaHass } from "../helpers/mock-scale";
import { WOOD_LOVER_WEIGH_STEPS } from "../helpers/wood-lover-recipe";
import {
  assertAmountWithinTolerance,
  expectSessionLineRecorded,
  resetWeighBatch,
} from "../helpers/weigh-session";

type SessionLine = {
  key: string;
  label: string;
  status: string;
  recorded_amount: number | null;
};

/**
 * Full weigh-station process (T1 mocks) — seeded suite.
 * Starts a new batch so prior variance mixes cannot leave stale recorded amounts.
 * Amounts must land within ±5% (domain close band).
 */
test.describe("Weigh process workflow (T1)", () => {
  test("complete Wood Lover recipe on Weigh tab and verify session table", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    test.skip(getStage() !== "T1", "Weigh process is T1 mock UI");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );

    const cf = new CommunifarmPage(page);
    await cf.openWeighStation();

    await expect(
      page.getByText(/weigh station|recipe scale|this session/i).first()
    ).toBeVisible({ timeout: STEP_MS });

    await resetWeighBatch(page, `E2E Exact ${Date.now()}`);

    await expect
      .poll(async () => getStateViaHass(page, "sensor.communifarm_weigh_session"), {
        timeout: STEP_MS,
      })
      .toMatch(/0\/\d+ lines recorded/);

    const total = WOOD_LOVER_WEIGH_STEPS.length;

    for (const line of WOOD_LOVER_WEIGH_STEPS) {
      await weighOneIngredientStepViaHass(page, line);
      await expectSessionLineRecorded(page, line.label, line.amountG);
    }

    const attrs = await getAttributesViaHass(page, "sensor.communifarm_weigh_session");
    expect(Number(attrs.completed)).toBeGreaterThanOrEqual(total);
    expect(Number(attrs.total)).toBe(total);

    const lines = (attrs.lines as SessionLine[]) ?? [];
    expect(lines).toHaveLength(total);
    for (const step of WOOD_LOVER_WEIGH_STEPS) {
      const row = lines.find((l) => l.label === step.label);
      expect(row, `missing session line for ${step.label}`).toBeTruthy();
      expect(row!.status).not.toBe("pending");
      assertAmountWithinTolerance(row!.recorded_amount, step.amountG, step.label);
    }

    const sessionState = await getStateViaHass(page, "sensor.communifarm_weigh_session");
    expect(sessionState).toBe(`${total}/${total} lines recorded`);

    await expect(page.getByText(/weigh station/i).first()).toBeVisible({
      timeout: STEP_MS,
    });
    await expect(page.getByText(/this session|session progress/i).first()).toBeVisible({
      timeout: STEP_MS,
    });
  });
});
