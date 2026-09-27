import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import { getStateViaHass } from "../helpers/ha-api";
import {
  pressMockScaleButton,
  selectMockScaleIngredient,
  setMockScaleCalibratedSensor,
  simulateMockNfcScan,
} from "../helpers/mock-scale";

/**
 * Weigh tab: homepage → login → /communifarm/weigh → NFC select → weigh → record.
 */
test.describe("Mock esp32dev scale (T1)", () => {
  test("NFC select, change weight, record on Weigh dashboard", async ({ page }) => {
    test.skip(getStage() !== "T1", "Scale mock smoke is T1");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );
    test.skip(
      !process.env.TEST_HA_TOKEN,
      "TEST_HA_TOKEN required to drive mock scale services"
    );

    const cf = new CommunifarmPage(page);
    await cf.openWeighStation();
    await expect(page.getByText(/ingredient \(nfc\)|selected ingredient/i).first()).toBeVisible();
    await expect(page.getByText(/current mass|calibrated/i).first()).toBeVisible();

    // Mock NFC scan → hardwood pellets, then tare / add mass / record
    await setMockScaleCalibratedSensor(50);
    await simulateMockNfcScan("nfc-hardwood-pellets");
    await expect
      .poll(async () => getStateViaHass(page, "input_select.esp32dev_selected_ingredient"))
      .toBe("hardwood pellets");

    await pressMockScaleButton("tare");
    await setMockScaleCalibratedSensor(3050);
    await pressMockScaleButton("record_weight");

    await expect
      .poll(async () =>
        Number.parseFloat(await getStateViaHass(page, "sensor.esp32dev_calibrated_g"))
      )
      .toBeCloseTo(3000, 0);

    const recorded = await getStateViaHass(page, "input_text.esp32dev_last_recorded");
    expect(recorded).toMatch(/3000/);
    expect(recorded).toMatch(/hardwood pellets/);

    // Dashboard still shows weigh chrome after the activity
    await expect(page.getByText(/weigh station/i).first()).toBeVisible();
  });

  test("select ingredient dropdown then record weight", async ({ page }) => {
    test.skip(getStage() !== "T1", "Scale mock smoke is T1");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );
    test.skip(
      !process.env.TEST_HA_TOKEN,
      "TEST_HA_TOKEN required to drive mock scale services"
    );

    const cf = new CommunifarmPage(page);
    await cf.openWeighStation();

    await setMockScaleCalibratedSensor(100);
    await selectMockScaleIngredient("gypsum");
    await pressMockScaleButton("tare");
    await setMockScaleCalibratedSensor(300);
    await pressMockScaleButton("record_weight");

    const recorded = await getStateViaHass(page, "input_text.esp32dev_last_recorded");
    expect(recorded).toMatch(/200/);
    expect(recorded).toMatch(/gypsum/);
  });
});
