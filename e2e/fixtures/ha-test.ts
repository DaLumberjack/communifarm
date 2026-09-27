import { test as base } from "@playwright/test";
import { startHaSession } from "./ha-session";

/**
 * Playwright test that always opens the HA homepage and logs in if required
 * before the test body runs. Use for all flows against a configured instance.
 *
 * Scratch onboarding (`00-…`) and filesystem-only specs should keep
 * `@playwright/test` instead.
 */
export const test = base.extend<{ haSession: void }>({
  haSession: [
    async ({ page }, use) => {
      await startHaSession(page);
      await use();
    },
    { auto: true },
  ],
});

export { expect } from "@playwright/test";
