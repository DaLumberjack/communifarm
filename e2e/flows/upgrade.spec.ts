import { test, expect } from "../fixtures/ha-test";
import { getStage } from "../fixtures/environment";
import { getNumberValueViaHass, getStateViaHass } from "../helpers/ha-api";

test.describe("Local upgrade no-data-loss (T2)", () => {
  test("seeded communifarm entities survive after version install", async ({
    page,
  }) => {
    test.skip(
      getStage() !== "T2",
      "Set TEST_HA_STAGE=T2 after scripts/local_upgrade_install.sh"
    );
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing — see docs/user/openbao.md"
    );

    // ha-test: homepage → login if required; assert via logged-in hass session
    const stage = await getStateViaHass(page, "sensor.communifarm_batch_stage");
    expect(stage).toBeTruthy();
    const temp = await getNumberValueViaHass(
      page,
      "number.communifarm_temperature_target"
    );
    expect(temp).toBeGreaterThan(-40);
  });
});
