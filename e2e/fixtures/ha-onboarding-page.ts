import { Page, expect } from "@playwright/test";

/**
 * Home Assistant scratch onboarding UI.
 * Step order from docs/intake/initializaion_to_communifarm_setup.har:
 * user → core_config → analytics → integration
 */
export class HaOnboardingPage {
  constructor(private readonly page: Page) {}

  async openWelcome(): Promise<void> {
    await this.page.goto("/onboarding.html", { waitUntil: "domcontentloaded" });
    await expect(this.page.getByText(/Welcome!/i)).toBeVisible({ timeout: 60000 });
  }

  async startCreateSmartHome(): Promise<void> {
    await this.page.getByRole("button", { name: /Create my smart home/i }).click();
  }

  async completeUserStep(opts: {
    name: string;
    username: string;
    password: string;
  }): Promise<void> {
    // HA onboarding user form labels vary slightly by version; use flexible locators.
    const nameField = this.page.getByLabel(/^name$/i).or(this.page.locator('input[name="name"]')).first();
    const userField = this.page
      .getByLabel(/username/i)
      .or(this.page.locator('input[name="username"]'))
      .first();
    const passField = this.page
      .getByLabel(/^password$/i)
      .or(this.page.locator('input[name="password"]'))
      .first();
    const confirmField = this.page
      .getByLabel(/confirm/i)
      .or(this.page.locator('input[name="password_confirm"]'))
      .first();

    await nameField.fill(opts.name);
    await userField.fill(opts.username);
    await passField.fill(opts.password);
    if (await confirmField.count()) {
      await confirmField.fill(opts.password);
    }
    await this.clickPrimary();
  }

  async completeCoreConfigIfPresent(): Promise<void> {
    // Location / unit system — often a Next/Create button is enough.
    if (await this.page.getByText(/location|unit system|home location/i).count()) {
      await this.clickPrimary();
    }
  }

  async completeAnalyticsIfPresent(): Promise<void> {
    if (await this.page.getByText(/analytics|share/i).count()) {
      // Prefer skip / next without enabling share when both exist.
      const skip = this.page.getByRole("button", { name: /next|skip|finish|create/i }).first();
      await skip.click();
    }
  }

  async completeIntegrationIfPresent(): Promise<void> {
    if (await this.page.getByText(/integrate|devices|finish/i).count()) {
      await this.clickPrimary();
    }
  }

  async expectPastOnboarding(): Promise<void> {
    await this.page.waitForURL((url) => !url.pathname.includes("onboarding"), {
      timeout: 120000,
    });
    await expect(this.page.locator("home-assistant, home-assistant-main, ha-sidebar").first()).toBeVisible({
      timeout: 120000,
    });
  }

  private async clickPrimary(): Promise<void> {
    await this.page
      .getByRole("button", { name: /create|next|finish|continue|submit/i })
      .first()
      .click();
  }
}
