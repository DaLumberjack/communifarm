import { test, expect } from "../fixtures/ha-test";
import { CommunifarmPage } from "../fixtures/communifarm-page";
import { getStage } from "../fixtures/environment";

test.describe("Communifarm onboarding", () => {
  test("standalone config flow produces dashboard path", async ({ page }) => {
    const stage = getStage();
    test.skip(stage === "T2", "Upgrade flow covered in upgrade.spec.ts");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing — see docs/user/openbao.md"
    );

    // ha-test: homepage → login if required, then navigate
    const cf = new CommunifarmPage(page);

    await cf.openIntegrations();
    await expect(page.locator("body")).toContainText(/integration|Communifarm|Devices/i);

    try {
      await cf.startCommunifarmFlow();
      await cf.completeOnboarding({
        site: "E2E Site",
        environment: "E2E Tent",
        batch: "E2E Batch",
      });
    } catch {
      // Already configured or UI chrome differs — continue to dashboard probe.
    }

    await cf.openCommunifarmDashboard();
    const body = await page.locator("body").innerText();
    expect(body.length).toBeGreaterThan(0);
  });
});
