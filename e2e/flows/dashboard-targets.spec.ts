import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";
import {
  getNumberValueViaHass,
  setNumberValueViaHass,
} from "../helpers/ha-api";

const TEMP_TARGET = "number.communifarm_temperature_target";
const HUM_TARGET = "number.communifarm_humidity_target";

test.describe("Dashboard target controls (T1)", () => {
  test("adjusts temperature ±1°C and humidity ±1% from dashboard entities", async ({
    page,
  }) => {
    test.skip(getStage() !== "T1", "Dashboard target nudge is a T1 local flow");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing — start/unseal OpenBao, bao login, see docs/user/openbao.md"
    );

    // ha-test fixture already: homepage → login if required
    const cf = new CommunifarmPage(page);
    await cf.openCommunifarmDashboard();
    await expect(page.getByText(/current settings|targets/i).first()).toBeVisible({
      timeout: 30000,
    });

    const baselineTemp = await getNumberValueViaHass(page, TEMP_TARGET);
    const baselineHum = await getNumberValueViaHass(page, HUM_TARGET);

    await setNumberValueViaHass(page, TEMP_TARGET, baselineTemp - 1);
    expect(await getNumberValueViaHass(page, TEMP_TARGET)).toBeCloseTo(
      baselineTemp - 1,
      5
    );

    await setNumberValueViaHass(page, TEMP_TARGET, baselineTemp - 1 + 1);
    expect(await getNumberValueViaHass(page, TEMP_TARGET)).toBeCloseTo(
      baselineTemp,
      5
    );

    await setNumberValueViaHass(page, HUM_TARGET, baselineHum - 1);
    expect(await getNumberValueViaHass(page, HUM_TARGET)).toBeCloseTo(
      baselineHum - 1,
      5
    );

    await setNumberValueViaHass(page, HUM_TARGET, baselineHum - 1 + 1);
    expect(await getNumberValueViaHass(page, HUM_TARGET)).toBeCloseTo(
      baselineHum,
      5
    );

    await page.reload();
    await expect(page.getByText(/targets/i).first()).toBeVisible({ timeout: 30000 });
    expect(await getNumberValueViaHass(page, TEMP_TARGET)).toBeCloseTo(
      baselineTemp,
      5
    );
    expect(await getNumberValueViaHass(page, HUM_TARGET)).toBeCloseTo(
      baselineHum,
      5
    );
  });
});
