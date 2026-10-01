import { test, expect } from "../fixtures/ha-test";
import { getStage } from "../fixtures/environment";
import {
  createPlaywrightLongLivedToken,
  writeGeneratedTokenArtifacts,
  PLAYWRIGHT_TOKEN_CLIENT_NAME,
  OPENBAO_PLAYWRIGHT_TOKEN_FIELD,
} from "../helpers/ha-token";

/**
 * One-shot T1 setup: mint a long-lived HA token for REST helpers and write
 * artifacts for scripts/openbao_set_playwright_token.sh.
 *
 * Not part of the seeded regression suite.
 */
test.describe("Provision Playwright HA token (T1 setup)", () => {
  test("create long-lived token and write OpenBao-ready artifacts", async ({
    page,
  }) => {
    test.skip(getStage() !== "T1", "Token provision is a local T1 setup flow");
    test.skip(
      !process.env.TEST_HA_USERNAME || !process.env.TEST_HA_PASSWORD,
      "OpenBao secrets missing — see docs/user/openbao.md"
    );

    await expect(
      page.locator("home-assistant, home-assistant-main").first()
    ).toBeVisible();

    const token = await createPlaywrightLongLivedToken(page);
    expect(token.length).toBeGreaterThan(20);

    const { envPath, jsonPath } = writeGeneratedTokenArtifacts(token);

    // Sanity: token works against HA REST before we tell OpenBao about it.
    const res = await fetch(
      `${(process.env.TEST_HA_URL || "http://127.0.0.1:8123").replace(/\/$/, "")}/api/`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(res.ok, `HA /api/ rejected new token (${res.status})`).toBeTruthy();

    console.log(
      [
        `Created HA long-lived token client_name=${PLAYWRIGHT_TOKEN_CLIENT_NAME}`,
        `Wrote ${jsonPath}`,
        `Wrote ${envPath}`,
        `Next: ./scripts/openbao_set_playwright_token.sh`,
        `  (patches kv/ha-test field ${OPENBAO_PLAYWRIGHT_TOKEN_FIELD})`,
      ].join("\n")
    );
  });
});
