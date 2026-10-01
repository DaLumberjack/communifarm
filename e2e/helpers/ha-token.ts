import fs from "node:fs";
import path from "node:path";
import { Page } from "@playwright/test";
import { INITIAL_LOAD_MS } from "../fixtures/timeouts";

/** Stable HA client_name for the Communifarm Playwright long-lived token. */
export const PLAYWRIGHT_TOKEN_CLIENT_NAME = "communifarm-playwright-dev";

/** HA lifespan in days (~10y). */
export const PLAYWRIGHT_TOKEN_LIFESPAN_DAYS = 3650;

/** OpenBao KV field written by scripts/openbao_set_playwright_token.sh */
export const OPENBAO_PLAYWRIGHT_TOKEN_FIELD =
  "dev_container_playwright_long_lived_access_token";

export const GENERATED_TOKEN_DIR = path.join("e2e", ".generated");
export const GENERATED_TOKEN_ENV = path.join(GENERATED_TOKEN_DIR, "ha-token.env");
export const GENERATED_TOKEN_JSON = path.join(GENERATED_TOKEN_DIR, "ha-token.json");

type RefreshTokenMeta = {
  id: string;
  client_name?: string | null;
  token_type?: string;
};

/**
 * Create (or rotate) a long-lived access token via the logged-in frontend WS.
 * HA never re-shows an existing token string — same client_name is deleted first.
 */
export async function createPlaywrightLongLivedToken(
  page: Page,
  opts?: { clientName?: string; lifespanDays?: number }
): Promise<string> {
  const clientName = opts?.clientName ?? PLAYWRIGHT_TOKEN_CLIENT_NAME;
  const lifespanDays = opts?.lifespanDays ?? PLAYWRIGHT_TOKEN_LIFESPAN_DAYS;

  await page.waitForFunction(() => {
    const el = document.querySelector("home-assistant") as
      | (HTMLElement & { hass?: { callWS?: unknown } })
      | null;
    return Boolean(el?.hass?.callWS);
  }, undefined, { timeout: INITIAL_LOAD_MS });

  const result = await page.evaluate(
    async ({ clientName, lifespanDays }) => {
      const el = document.querySelector("home-assistant") as HTMLElement & {
        hass: {
          callWS: <T>(msg: Record<string, unknown>) => Promise<T>;
        };
      };

      const tokens = await el.hass.callWS<RefreshTokenMeta[]>({
        type: "auth/refresh_tokens",
      });
      for (const tok of tokens || []) {
        if (tok.client_name === clientName) {
          await el.hass.callWS({
            type: "auth/delete_refresh_token",
            refresh_token_id: tok.id,
          });
        }
      }

      const accessToken = await el.hass.callWS<string>({
        type: "auth/long_lived_access_token",
        client_name: clientName,
        lifespan: lifespanDays,
      });
      return accessToken;
    },
    { clientName, lifespanDays }
  );

  if (!result || typeof result !== "string") {
    throw new Error(
      `auth/long_lived_access_token returned unexpected value for ${clientName}`
    );
  }
  return result;
}

/** Write stdout-friendly JSON + gitignored env file for the OpenBao script. */
export function writeGeneratedTokenArtifacts(token: string): {
  envPath: string;
  jsonPath: string;
} {
  fs.mkdirSync(GENERATED_TOKEN_DIR, { recursive: true });

  const payload = {
    TEST_HA_TOKEN: token,
    openbao_field: OPENBAO_PLAYWRIGHT_TOKEN_FIELD,
    client_name: PLAYWRIGHT_TOKEN_CLIENT_NAME,
    lifespan_days: PLAYWRIGHT_TOKEN_LIFESPAN_DAYS,
  };

  fs.writeFileSync(GENERATED_TOKEN_JSON, `${JSON.stringify(payload, null, 2)}\n`, {
    encoding: "utf8",
  });
  fs.writeFileSync(
    GENERATED_TOKEN_ENV,
    `TEST_HA_TOKEN=${JSON.stringify(token)}\n`,
    { encoding: "utf8" }
  );

  // Machine-readable line for piping (also visible in Playwright list reporter).
  console.log(`COMMUNIFARM_HA_TOKEN_JSON=${JSON.stringify(payload)}`);

  return { envPath: GENERATED_TOKEN_ENV, jsonPath: GENERATED_TOKEN_JSON };
}
