import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import { getAttributesViaHass, getStateViaHass } from "../helpers/ha-api";
import {
  advanceProductionViaUi,
  getFirstContainerNfcUid,
  mockNfcHarvestCheckIn,
  prepareBatchForInoculate,
  recordContainerHarvestViaUi,
  recordSaleViaUi,
} from "../helpers/production-pos";
import { STEP_MS } from "../fixtures/timeouts";

/**
 * T1: mock handheld NFC (input_text.esp32dev_last_nfc_uid) → container harvest
 * → POS sale. Does not use esp32dev_simulate_nfc_scan (weigh ingredients only).
 */
test.describe("Mock NFC harvest to POS (T1)", () => {
  test("mock container scan, harvest, then sell", async ({ page }) => {
    test.skip(getStage() !== "T1", "Mock NFC harvest is a T1 local flow");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );

    const cf = new CommunifarmPage(page);
    const batchName = `E2E NFC POS ${Date.now()}`;

    await prepareBatchForInoculate(page, batchName);
    await cf.openProduction();
    await advanceProductionViaUi(page);

    const nfcUid = await getFirstContainerNfcUid(page);
    expect(nfcUid.length).toBeGreaterThan(3);

    await mockNfcHarvestCheckIn(page, nfcUid);
    await cf.openHarvest();
    await expect(
      page.getByText(/nfc|check-?in|harvest/i).first()
    ).toBeVisible({ timeout: STEP_MS });

    await recordContainerHarvestViaUi(page, 120);

    const checkin = await getAttributesViaHass(
      page,
      "sensor.communifarm_nfc_checkin"
    );
    expect(String(checkin.object_type || checkin.nfc_uid || "")).toBeTruthy();

    await cf.openPos();
    await recordSaleViaUi(page, { massG: 60, lineAmount: 9 });

    await expect
      .poll(async () => getStateViaHass(page, "sensor.communifarm_sales_status"), {
        timeout: STEP_MS,
      })
      .not.toBe("idle");
  });
});
