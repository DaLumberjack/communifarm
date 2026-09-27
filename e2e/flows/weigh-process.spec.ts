import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import {
  getAttributesViaHass,
  getStateViaHass,
} from "../helpers/ha-api";
import { weighOneIngredientStepViaHass } from "../helpers/mock-scale";
import { WOOD_LOVER_WEIGH_STEPS } from "../helpers/wood-lover-recipe";

type SessionLine = {
  key: string;
  label: string;
  status: string;
  recorded_amount: number | null;
};

async function sessionLines(page: import("@playwright/test").Page): Promise<SessionLine[]> {
  const attrs = await getAttributesViaHass(page, "sensor.communifarm_weigh_session");
  return (attrs.lines as SessionLine[]) ?? [];
}

/**
 * Full weigh-station process (T1 mocks):
 * bulk bin → NFC scan → tare mix container → weigh → record → repeat → verify session.
 *
 * Stateful HA may already have prior weigh-ins; we overwrite each recipe line and
 * assert the batch session table (latest per ingredient), not absolute counters from zero.
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
    ).toBeVisible({ timeout: 30000 });

    await expect
      .poll(async () => getStateViaHass(page, "sensor.communifarm_weigh_session"), {
        timeout: 30000,
      })
      .toMatch(/\d+\/\d+ lines recorded/);

    const total = WOOD_LOVER_WEIGH_STEPS.length;

    for (const line of WOOD_LOVER_WEIGH_STEPS) {
      // 1) Operator gets the bulk bin (implicit).
      // 2) Scan NFC → 3) tare mix container → 4) weigh → 5) record.
      await weighOneIngredientStepViaHass(page, line);

      await expect
        .poll(
          async () => getStateViaHass(page, "input_select.esp32dev_selected_ingredient"),
          { timeout: 15000 }
        )
        .toBe(line.label);

      await expect
        .poll(
          async () => {
            const raw = await getStateViaHass(page, "sensor.esp32dev_calibrated_g");
            return Number.parseFloat(raw);
          },
          { timeout: 15000 }
        )
        .toBeCloseTo(line.amountG, 0);

      await expect
        .poll(
          async () => {
            const rows = await sessionLines(page);
            const row = rows.find((r) => r.label === line.label);
            return row?.recorded_amount ?? null;
          },
          { timeout: 30000 }
        )
        .toBeCloseTo(line.amountG, 0);

      await expect
        .poll(async () => {
          const attrs = await getAttributesViaHass(
            page,
            "sensor.communifarm_weigh_session"
          );
          return String(attrs.progress_text ?? "");
        })
        .toContain(line.label);
    }

    // 7) Verify batch session table: every recipe ingredient recorded.
    const attrs = await getAttributesViaHass(page, "sensor.communifarm_weigh_session");
    expect(Number(attrs.completed)).toBeGreaterThanOrEqual(total);
    expect(Number(attrs.total)).toBe(total);

    const lines = (attrs.lines as SessionLine[]) ?? [];
    expect(lines).toHaveLength(total);
    for (const step of WOOD_LOVER_WEIGH_STEPS) {
      const row = lines.find((l) => l.label === step.label);
      expect(row, `missing session line for ${step.label}`).toBeTruthy();
      expect(row!.status).not.toBe("pending");
      expect(row!.recorded_amount).toBeCloseTo(step.amountG, 0);
    }

    const sessionState = await getStateViaHass(page, "sensor.communifarm_weigh_session");
    expect(sessionState).toBe(`${total}/${total} lines recorded`);

    await expect(page.getByText(/weigh station/i).first()).toBeVisible();
    await expect(page.getByText(/this session|session progress/i).first()).toBeVisible();
  });
});
