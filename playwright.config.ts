import { defineConfig, devices } from "@playwright/test";

const url = process.env.TEST_HA_URL || "http://127.0.0.1:8123";
const stage = process.env.TEST_HA_STAGE || "T1";
const allowed = new Set([
  "http://127.0.0.1:8123",
  "http://localhost:8123",
  "http://192.168.102.20:8123",
]);

if (!allowed.has(url.replace(/\/$/, ""))) {
  throw new Error(`TEST_HA_URL not allowlisted for Communifarm E2E: ${url}`);
}

if (stage === "T3" && !url.includes("192.168.102.20")) {
  throw new Error("T3 requires TEST_HA_URL=http://192.168.102.20:8123");
}

export default defineConfig({
  testDir: "./e2e/flows",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/e2e/report.json" }],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  use: {
    baseURL: url,
    headless: process.env.TEST_HEADLESS !== "false",
    launchOptions: {
      slowMo: Number(process.env.TEST_SLOWMO || 0),
    },
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
