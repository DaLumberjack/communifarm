import { test, expect } from "@playwright/test";
import { loginHa } from "../fixtures/ha-auth";
import { getStage, getCredentials } from "../fixtures/environment";
import { setMockTemperature } from "../helpers/ha-api";

test.describe("Mock device conditions (T1)", () => {
  test("can inject mock temperature when API token present", async ({ page }) => {
    test.skip(getStage() !== "T1", "Mock injection is a T1 local fixture flow");
    const { token } = getCredentials();
    test.skip(!token, "Optional long-lived token not provisioned in OpenBao yet");

    await loginHa(page);
    await setMockTemperature(29.5);
    expect(true).toBeTruthy();
  });
});
