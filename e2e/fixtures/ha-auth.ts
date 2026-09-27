import { Page } from "@playwright/test";
import { getCredentials } from "./environment";

/** Log in to Home Assistant UI without writing secrets to traces. */
export async function loginHa(page: Page): Promise<void> {
  const { username, password } = getCredentials();
  await page.goto("/", { waitUntil: "domcontentloaded" });

  // Fresh install onboarding vs login form.
  const userInput = page.locator(
    'input[name="username"], input[type="text"], ha-auth-flow input'
  ).first();
  const passInput = page.locator('input[name="password"], input[type="password"]').first();

  if (await passInput.count()) {
    await userInput.fill(username, { force: true }).catch(async () => {
      await page.getByLabel(/username|name/i).fill(username);
    });
    await passInput.fill(password);
    await page.getByRole("button", { name: /log in|next|create/i }).first().click();
  }

  await page.waitForURL(/\/(lovelace|energy|config|dashboard)?/, { timeout: 60000 }).catch(() => undefined);
}
