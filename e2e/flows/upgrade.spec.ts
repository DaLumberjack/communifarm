import { test, expect } from "@playwright/test";
import { loginHa } from "../fixtures/ha-auth";
import { getStage } from "../fixtures/environment";
import { getState } from "../helpers/ha-api";

test.describe("Local upgrade no-data-loss (T2)", () => {
  test("seeded communifarm entities survive after version install", async ({ page }) => {
    test.skip(getStage() !== "T2", "Set TEST_HA_STAGE=T2 after scripts/local_upgrade_install.sh");
    const token = process.env.TEST_HA_TOKEN;
    test.skip(!token, "TEST_HA_TOKEN required to assert entity state after upgrade");

    await loginHa(page);
    const stage = (await getState("sensor.communifarm_batch_stage")) as {
      state?: string;
    };
    expect(stage.state).toBeTruthy();
    const temp = (await getState("number.communifarm_temperature_target")) as {
      state?: string;
    };
    expect(Number(temp.state)).toBeGreaterThan(-40);
  });
});
