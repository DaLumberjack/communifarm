import { test, expect } from "../fixtures/ha-test";
import { getStage } from "../fixtures/environment";
import { getStateViaHass } from "../helpers/ha-api";
import {
  pressMockScaleButton,
  selectMockScaleIngredient,
  setMockScaleCalibratedSensor,
} from "../helpers/mock-scale";

/**
 * Smoke: homepage → login → mock esp32dev scale entities respond.
 * Full recipe/NFC human process is deferred (docs/intermediate/weigh-station-process-deferred.md).
 */
test.describe("Mock esp32dev scale (T1)", () => {
  test("tare and record weight with selected ingredient", async ({ page }) => {
    test.skip(getStage() !== "T1", "Scale mock smoke is T1");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing"
    );
    test.skip(
      !process.env.TEST_HA_TOKEN,
      "TEST_HA_TOKEN required to drive mock scale services"
    );

    await setMockScaleCalibratedSensor(100);
    await selectMockScaleIngredient("hardwood pellets");
    await pressMockScaleButton("tare");
    await setMockScaleCalibratedSensor(3100);
    await pressMockScaleButton("record_weight");

    const net = await getStateViaHass(page, "sensor.esp32dev_calibrated_g");
    expect(Number.parseFloat(net)).toBeCloseTo(3000, 0);

    const recorded = await getStateViaHass(
      page,
      "input_text.esp32dev_last_recorded"
    );
    expect(recorded).toMatch(/3000/);
    expect(recorded).toMatch(/hardwood pellets/);
  });
});
