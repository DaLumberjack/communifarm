import { test, expect } from "../fixtures/ha-test";
import { getStage } from "../fixtures/environment";
import { callServiceViaHass, getStateViaHass } from "../helpers/ha-api";

test.describe("Climate control (T1)", () => {
  test("seeded layout exposes a climate status sensor", async ({ page }) => {
    test.skip(getStage() !== "T1", "Climate UI check is a T1 local flow");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing — see docs/user/openbao.md"
    );

    await expect(
      page.locator("home-assistant, home-assistant-main").first()
    ).toBeVisible();
    await callServiceViaHass(page, "communifarm", "ensure_climate_layout", {});
    await callServiceViaHass(page, "communifarm", "tick_climate", {});
    const status = await getStateViaHass(
      page,
      "sensor.communifarm_climate_status"
    );
    expect(status).toBe("11 nodes");

    const targetEntity = "number.communifarm_climate_temperature_target";
    const original = Number.parseFloat(await getStateViaHass(page, targetEntity));
    expect(Number.isFinite(original)).toBeTruthy();
    await callServiceViaHass(page, "number", "set_value", {
      entity_id: targetEntity,
      value: 23.5,
    });
    expect(Number.parseFloat(await getStateViaHass(page, targetEntity))).toBe(23.5);

    await callServiceViaHass(page, "button", "press", {
      entity_id: "button.communifarm_climate_reset_node",
    });
    expect(Number.parseFloat(await getStateViaHass(page, targetEntity))).toBe(original);
  });
});