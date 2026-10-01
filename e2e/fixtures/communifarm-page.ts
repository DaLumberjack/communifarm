import { Page, expect } from "@playwright/test";
import { DEFAULT_CF_FLOW } from "../helpers/har-flow-constants";
import { INITIAL_LOAD_MS, STEP_MS } from "./timeouts";

/**
 * Communifarm UI navigation. Call only after startHaSession / ha-test fixture
 * (homepage + login). Methods navigate from the authenticated home shell.
 */
export class CommunifarmPage {
  constructor(private readonly page: Page) {}

  async openIntegrations(): Promise<void> {
    await this.page.goto("/config/integrations", { waitUntil: "domcontentloaded" });
    await expect(this.page).toHaveURL(/\/config\/integrations/, {
      timeout: INITIAL_LOAD_MS,
    });
    // Prefer visible page chrome — broad getByText hits hidden menu items (e.g. show-ignored).
    const heading = this.page.getByRole("heading", { name: /integrations/i }).first();
    const main = this.page.locator("ha-config-integrations, home-assistant-main").first();
    await expect(heading.or(main)).toBeVisible({ timeout: STEP_MS });
  }

  async startCommunifarmFlow(): Promise<void> {
    await this.openIntegrations();
    const add = this.page.getByRole("button", { name: /add integration/i });
    if (await add.count()) {
      await add.click();
    }
    const search = this.page.getByPlaceholder(/search/i).first();
    if (await search.count()) {
      await search.fill("Communifarm");
    }
    await this.page.getByText("Communifarm", { exact: false }).first().click();
  }

  /**
   * Completes Communifarm config flow matching HAR payloads:
   * site → bindings (mock entities) → profile/batch.
   */
  async completeOnboarding(opts?: {
    site?: string;
    environment?: string;
    batch?: string;
    temperatureTarget?: number;
    humidityTarget?: number;
  }): Promise<void> {
    const site = opts?.site ?? DEFAULT_CF_FLOW.site;
    const environment = opts?.environment ?? DEFAULT_CF_FLOW.environment;
    const batch = opts?.batch ?? DEFAULT_CF_FLOW.batch;
    const temperatureTarget =
      opts?.temperatureTarget ?? DEFAULT_CF_FLOW.temperatureTarget;
    const humidityTarget = opts?.humidityTarget ?? DEFAULT_CF_FLOW.humidityTarget;

    await this.fillIfPresent(/site name/i, site);
    await this.fillIfPresent(/environment name/i, environment);
    await this.clickSubmit();

    await this.fillIfPresent(/temperature/i, DEFAULT_CF_FLOW.temperatureEntity);
    await this.fillIfPresent(/humidity/i, DEFAULT_CF_FLOW.humidityEntity);
    await this.fillIfPresent(/fan/i, DEFAULT_CF_FLOW.fanEntity);
    await this.clickSubmit();

    await this.fillIfPresent(/temperature target/i, String(temperatureTarget));
    await this.fillIfPresent(/humidity target/i, String(humidityTarget));
    await this.fillIfPresent(/batch/i, batch);
    await this.clickSubmit();
  }

  /** Navigate to the managed Communifarm dashboard overview. */
  async openCommunifarmDashboard(): Promise<void> {
    const sidebarLink = this.page.locator('a[href*="communifarm"]').first();
    if (await sidebarLink.isVisible().catch(() => false)) {
      await sidebarLink.click();
    } else {
      await this.page.goto("/communifarm/overview", {
        waitUntil: "domcontentloaded",
      });
    }
    await expect(this.page).toHaveURL(/communifarm/, { timeout: INITIAL_LOAD_MS });
  }

  /** Open the Weigh activity tab (scale + NFC select). */
  async openWeighStation(): Promise<void> {
    await this.page.goto("/communifarm/weigh", { waitUntil: "domcontentloaded" });
    await expect(this.page).toHaveURL(/communifarm\/weigh/, {
      timeout: INITIAL_LOAD_MS,
    });
    await expect(
      this.page.getByText(/weigh station|ingredient|current mass/i).first()
    ).toBeVisible({
      timeout: STEP_MS,
    });
  }

  /** Open the Batches tab (list + complete/new + post-weigh milestones). */
  async openBatches(): Promise<void> {
    await this.page.goto("/communifarm/batches", { waitUntil: "domcontentloaded" });
    await expect(this.page).toHaveURL(/communifarm\/batches/, {
      timeout: INITIAL_LOAD_MS,
    });
    await expect(
      this.page.getByText(/batches|complete batch|batch list/i).first()
    ).toBeVisible({
      timeout: STEP_MS,
    });
  }

  private async fillIfPresent(label: RegExp, value: string): Promise<void> {
    const field = this.page.getByLabel(label).first();
    if (await field.count()) {
      await field.fill(value);
    }
  }

  private async clickSubmit(): Promise<void> {
    await this.page
      .getByRole("button", { name: /submit|next|create|finish/i })
      .first()
      .click();
  }
}
