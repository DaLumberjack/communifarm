import { test, expect } from "@playwright/test";
import { loginHa } from "../fixtures/ha-auth";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage, getCredentials } from "../fixtures/environment";
import { getNumberValue, setNumberValue } from "../helpers/ha-api";

const TEMP_TARGET = "number.communifarm_temperature_target";
const HUM_TARGET = "number.communifarm_humidity_target";

test.describe("Dashboard target controls (T1)", () => {
  test("adjusts temperature ±1°C and humidity ±1% from dashboard entities", async ({
    page,
  }) => {
    test.skip(getStage() !== "T1", "Dashboard target nudge is a T1 local flow");
    const { token } = getCredentials();
    test.skip(!token, "TEST_HA_TOKEN required to drive number.set_value");

    await loginHa(page);
    const cf = new CommunifarmPage(page);
    await cf.openCommunifarmDashboard();
    await expect(page.getByText(/current settings|targets/i).first()).toBeVisible({
      timeout: 30000,
    });

    const baselineTemp = await getNumberValue(TEMP_TARGET);
    const baselineHum = await getNumberValue(HUM_TARGET);

    await setNumberValue(TEMP_TARGET, baselineTemp - 1);
    expect(await getNumberValue(TEMP_TARGET)).toBeCloseTo(baselineTemp - 1, 5);

    await setNumberValue(TEMP_TARGET, baselineTemp - 1 + 1);
    expect(await getNumberValue(TEMP_TARGET)).toBeCloseTo(baselineTemp, 5);

    await setNumberValue(HUM_TARGET, baselineHum - 1);
    expect(await getNumberValue(HUM_TARGET)).toBeCloseTo(baselineHum - 1, 5);

    await setNumberValue(HUM_TARGET, baselineHum - 1 + 1);
    expect(await getNumberValue(HUM_TARGET)).toBeCloseTo(baselineHum, 5);

    await page.reload();
    await expect(page.getByText(/targets/i).first()).toBeVisible({ timeout: 30000 });
    expect(await getNumberValue(TEMP_TARGET)).toBeCloseTo(baselineTemp, 5);
    expect(await getNumberValue(HUM_TARGET)).toBeCloseTo(baselineHum, 5);
  });
});
