import { test, expect } from "../fixtures/ha-test";
import { getStage } from "../fixtures/environment";
import { getStateViaHass, setNumberValueViaHass } from "../helpers/ha-api";
import {
  acquireCulture,
  selectInoculumFromMockNfc,
} from "../helpers/production-pos";
import { resetWeighBatch } from "../helpers/weigh-session";
import { STEP_MS } from "../fixtures/timeouts";

test.describe("Inoculum selection (T1)", () => {
  test("mock NFC scan selects culture for inoculate", async ({ page }) => {
    test.skip(getStage() !== "T1", "Inoculum mock is T1");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );

    const tag = `nfc-mock-lc-${Date.now()}`;
    const batchName = `E2E inoc NFC ${Date.now()}`;

    await resetWeighBatch(page, batchName);
    await setNumberValueViaHass(page, "number.communifarm_container_count", 1);
    await setNumberValueViaHass(
      page,
      "number.communifarm_substrate_g_per_container",
      1500
    );
    const firstId = await acquireCulture(page, {
      name: "First LC (should not stay active)",
      nfcUid: `other-${tag}`,
    });

    const targetId = await acquireCulture(page, {
      name: "Target LC for NFC",
      nfcUid: tag,
    });
    expect(targetId).not.toBe(firstId);

    await selectInoculumFromMockNfc(page, tag);
    await expect
      .poll(async () => getStateViaHass(page, "sensor.communifarm_active_culture_id"), {
        timeout: STEP_MS,
      })
      .toBe(targetId);
  });
});
