import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import { getAttributesViaHass, getStateViaHass } from "../helpers/ha-api";
import {
  advanceProductionViaUi,
  prepareBatchForInoculate,
  recordBatchHarvestViaUi,
  recordSaleViaUi,
} from "../helpers/production-pos";
import { STEP_MS } from "../fixtures/timeouts";

/**
 * T1 UI: planned batch → inoculate → incubating → fruiting → harvesting
 * → batch harvest (no NFC) → POS weigh-at-sale.
 */
test.describe("Production to POS (T1)", () => {
  test("inoculate through harvest then confirm sale on POS tab", async ({
    page,
  }) => {
    test.skip(getStage() !== "T1", "Production→POS is a T1 local flow");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );

    const cf = new CommunifarmPage(page);
    const batchName = `E2E POS ${Date.now()}`;

    await prepareBatchForInoculate(page, batchName);

    await cf.openProduction();
    await advanceProductionViaUi(page);
    await recordBatchHarvestViaUi(page, 250);

    await cf.openPos();
    await expect(
      page.getByText(/point of sale|sales status|confirm sale/i).first()
    ).toBeVisible({ timeout: STEP_MS });

    await recordSaleViaUi(page, { massG: 88, lineAmount: 12.5 });

    await expect
      .poll(async () => getStateViaHass(page, "sensor.communifarm_sales_status"), {
        timeout: STEP_MS,
      })
      .not.toBe("idle");

    const salesAttrs = await getAttributesViaHass(
      page,
      "sensor.communifarm_sales_status"
    );
    const last = salesAttrs.last_sale as
      | { total_amount?: number; venue_label?: string }
      | undefined;
    expect(last?.total_amount).toBe(12.5);
  });
});
