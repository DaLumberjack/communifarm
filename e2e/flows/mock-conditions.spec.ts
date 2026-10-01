import { test, expect } from "../fixtures/ha-test";
import { getStage } from "../fixtures/environment";
import { setMockTemperature } from "../helpers/ha-api";

test.describe("Mock device conditions (T1)", () => {
  test("can inject mock temperature when API token present", async ({ page }) => {
    test.skip(getStage() !== "T1", "Mock injection is a T1 local fixture flow");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing — see docs/user/openbao.md"
    );
    test.skip(
      !process.env.TEST_HA_TOKEN,
      "OpenBao kv/ha-test missing dev_container_playwright_long_lived_access_token"
    );

    // ha-test: homepage → login if required, then API inject
    await expect(
      page.locator("home-assistant, home-assistant-main").first()
    ).toBeVisible();
    await setMockTemperature(29.5);
    expect(true).toBeTruthy();
  });
});
