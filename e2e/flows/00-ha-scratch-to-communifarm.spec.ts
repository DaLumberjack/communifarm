import { test, expect } from "@playwright/test";
import { HaOnboardingPage } from "../fixtures/ha-onboarding-page";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage, getOnboardCredentials } from "../fixtures/environment";
import { DEFAULT_CF_FLOW } from "../helpers/har-flow-constants";

/**
 * First T1 bootstrap regression (scratch suite only).
 * Source: docs/intake/initializaion_to_communifarm_setup.har
 * Requires an empty/onboarding HA instance (prefer wiping .storage for this run only).
 *
 * Credentials: TEST_HA_ONBOARD_* or OpenBao-backed TEST_HA_USERNAME/PASSWORD.
 * Never hardcode values from the intake HAR.
 *
 * Do not run against seeded devcontainer HA — use yarn test:e2e:t1:seeded instead.
 */
test.describe("00 HA scratch onboarding to Communifarm", () => {
  test.describe.configure({ mode: "serial" });

  test("Create my smart home then complete Communifarm config flow", async ({ page }) => {
    test.skip(getStage() === "T3", "Scratch Docker onboarding is a local T1 flow");
    test.setTimeout(300000);

    let creds: ReturnType<typeof getOnboardCredentials>;
    try {
      creds = getOnboardCredentials();
    } catch {
      test.skip(true, "Set TEST_HA_ONBOARD_* or TEST_HA_USERNAME/PASSWORD via OpenBao");
      return;
    }

    const onboarding = new HaOnboardingPage(page);
    const onEmptyHa = await onboarding.tryOpenWelcome();
    test.skip(
      !onEmptyHa,
      "HA already past onboarding (no Welcome!). Wipe ha_config onboarding state for scratch, or run yarn test:e2e:t1:seeded."
    );

    await onboarding.startCreateSmartHome();
    await onboarding.completeUserStep(creds);
    await onboarding.completeCoreConfigIfPresent();
    await onboarding.completeAnalyticsIfPresent();
    await onboarding.completeIntegrationIfPresent();
    await onboarding.expectPastOnboarding();
    const unitSystem = await page.evaluate(() => {
      const root = document.querySelector("home-assistant") as
        | (HTMLElement & { hass?: { config?: { unit_system?: string } } })
        | null;
      return root?.hass?.config?.unit_system ?? "";
    });
    expect(unitSystem).toBe("metric");

    // Now on homepage shell — navigate to Communifarm setup endpoints
    const cf = new CommunifarmPage(page);
    await cf.startCommunifarmFlow();
    await cf.completeOnboarding({
      site: process.env.TEST_CF_SITE_NAME || DEFAULT_CF_FLOW.site,
      environment: process.env.TEST_CF_ENV_NAME || DEFAULT_CF_FLOW.environment,
      batch: process.env.TEST_CF_BATCH_NAME || DEFAULT_CF_FLOW.batch,
      temperatureTarget: DEFAULT_CF_FLOW.temperatureTarget,
      humidityTarget: DEFAULT_CF_FLOW.humidityTarget,
    });

    await cf.openCommunifarmDashboard();
    const body = await page.locator("body").innerText();
    expect(body.length).toBeGreaterThan(0);
  });
});
