import { Page, expect } from "@playwright/test";
import { getCredentials } from "./environment";

/**
 * Standard entry for Communifarm E2E against a configured HA instance:
 * 1. Open the instance homepage (`/`)
 * 2. Log in if the auth form is shown (usual case)
 * 3. Wait until the main UI is ready
 *
 * Callers then navigate to their test endpoints (dashboard, integrations, …).
 * Do not use for scratch onboarding (`00-ha-scratch-to-communifarm`) — that starts at onboarding.html.
 */
export async function startHaSession(page: Page): Promise<void> {
  const { username, password } = getCredentials();

  await page.goto("/", { waitUntil: "domcontentloaded" });

  if (page.url().includes("onboarding")) {
    throw new Error(
      "HA is still on onboarding.html. Finish Create my smart home, restore a backup, " +
        "or run e2e/flows/00-ha-scratch-to-communifarm.spec.ts instead."
    );
  }

  const passwordField = page
    .locator('input[name="password"], input[type="password"]')
    .first();
  const homeChrome = page
    .locator("home-assistant, home-assistant-main, ha-sidebar")
    .first();

  // Either auth form or already-authenticated shell should appear.
  await Promise.race([
    passwordField.waitFor({ state: "visible", timeout: 20000 }),
    homeChrome.waitFor({ state: "visible", timeout: 20000 }),
  ]).catch(() => undefined);

  if (await passwordField.isVisible().catch(() => false)) {
    const userField = page
      .locator('input[name="username"], input[type="text"], ha-auth-flow input')
      .first();
    await userField.fill(username, { force: true }).catch(async () => {
      await page.getByLabel(/username|name/i).fill(username);
    });
    await passwordField.fill(password);
    await page.getByRole("button", { name: /log in|next|sign in/i }).first().click();
  }

  await expect(homeChrome).toBeVisible({ timeout: 60000 });
  await expect(page).not.toHaveURL(/\/auth\//);
}

/** @deprecated Prefer startHaSession — same homepage → login-if-needed contract. */
export async function loginHa(page: Page): Promise<void> {
  await startHaSession(page);
}
