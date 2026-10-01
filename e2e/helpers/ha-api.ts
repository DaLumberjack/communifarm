import { Page } from "@playwright/test";
import { getCredentials, getHaUrl } from "../fixtures/environment";
import { INITIAL_LOAD_MS, STEP_MS } from "../fixtures/timeouts";

/** Minimal HA REST helpers for mock injection and assertions. */
export async function haApi(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const { token } = getCredentials();
  if (!token) {
    throw new Error("TEST_HA_TOKEN required for API helpers (optional OpenBao field)");
  }
  const headers = new Headers(init.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Content-Type", "application/json");
  return fetch(`${getHaUrl()}${path}`, { ...init, headers });
}

export async function setMockTemperature(value: number): Promise<void> {
  const res = await haApi("/api/services/input_number/set_value", {
    method: "POST",
    body: JSON.stringify({
      entity_id: "input_number.mock_temperature",
      value,
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to set mock temperature: ${res.status}`);
  }
}

export async function getState(entityId: string): Promise<{ state: string }> {
  const res = await haApi(`/api/states/${entityId}`);
  if (!res.ok) {
    throw new Error(`Failed to get state ${entityId}: ${res.status}`);
  }
  return res.json() as Promise<{ state: string }>;
}

export async function setNumberValue(entityId: string, value: number): Promise<void> {
  const res = await haApi("/api/services/number/set_value", {
    method: "POST",
    body: JSON.stringify({ entity_id: entityId, value }),
  });
  if (!res.ok) {
    throw new Error(`Failed to set ${entityId} to ${value}: ${res.status}`);
  }
}

/** Read a Communifarm number entity as a float (requires TEST_HA_TOKEN). */
export async function getNumberValue(entityId: string): Promise<number> {
  const body = await getState(entityId);
  const value = Number.parseFloat(body.state);
  if (Number.isNaN(value)) {
    throw new Error(`Expected numeric state for ${entityId}, got ${body.state}`);
  }
  return value;
}

/**
 * Call an HA service through the logged-in frontend `hass` object.
 * Prefer this for T1 when OpenBao has no long-lived token yet.
 */
export async function callServiceViaHass(
  page: Page,
  domain: string,
  service: string,
  data: Record<string, unknown>,
  opts?: { retries?: number }
): Promise<void> {
  await page.waitForFunction(() => {
    const el = document.querySelector("home-assistant") as
      | (HTMLElement & { hass?: { callService?: unknown } })
      | null;
    return Boolean(el?.hass?.callService);
  }, undefined, { timeout: INITIAL_LOAD_MS });

  const retries = opts?.retries ?? 6;
  let lastMessage = "unknown";

  for (let attempt = 0; attempt < retries; attempt++) {
    // Catch inside the page: HA rejects with plain objects ({code, message}),
    // which Playwright otherwise reports only as "page.evaluate: Object".
    const result = await page.evaluate(
      async ({ domain, service, data }) => {
        const el = document.querySelector("home-assistant") as HTMLElement & {
          hass: {
            callService: (
              d: string,
              s: string,
              payload: Record<string, unknown>
            ) => Promise<unknown>;
          };
        };
        try {
          await el.hass.callService(domain, service, data);
          return { ok: true as const };
        } catch (err: unknown) {
          const anyErr = err as {
            message?: string;
            code?: string;
            error?: { message?: string; code?: string };
          };
          return {
            ok: false as const,
            message:
              anyErr?.message ||
              anyErr?.error?.message ||
              (typeof err === "string" ? err : JSON.stringify(err)),
            code: anyErr?.code || anyErr?.error?.code,
          };
        }
      },
      { domain, service, data }
    );

    if (result.ok) {
      return;
    }

    lastMessage = result.message;
    const locked = /database is locked/i.test(result.message);
    if (!locked || attempt === retries - 1) {
      throw new Error(
        `hass.callService(${domain}.${service}) failed` +
          (result.code ? ` [${result.code}]` : "") +
          `: ${result.message}`
      );
    }
    // Communifarm SQLite busy — wait for the other writer/reader to finish (2–5s budget).
    await page.waitForTimeout(1000 * Math.min(attempt + 1, 3));
  }

  throw new Error(
    `hass.callService(${domain}.${service}) failed after retries: ${lastMessage}`
  );
}

/** Read entity state via the logged-in frontend session (no TEST_HA_TOKEN). */
export async function getStateViaHass(
  page: Page,
  entityId: string
): Promise<string> {
  await page.waitForFunction(
    (id) => {
      const el = document.querySelector("home-assistant") as
        | (HTMLElement & { hass?: { states?: Record<string, { state: string }> } })
        | null;
      return Boolean(el?.hass?.states?.[id]);
    },
    entityId,
    { timeout: STEP_MS }
  );

  const state = await page.evaluate((id) => {
    const el = document.querySelector("home-assistant") as HTMLElement & {
      hass: { states: Record<string, { state: string }> };
    };
    return el.hass.states[id]?.state;
  }, entityId);

  if (state == null) {
    throw new Error(`No state for ${entityId} via hass`);
  }
  return state;
}

/** Read entity attributes via the logged-in frontend session. */
export async function getAttributesViaHass(
  page: Page,
  entityId: string
): Promise<Record<string, unknown>> {
  await page.waitForFunction(
    (id) => {
      const el = document.querySelector("home-assistant") as
        | (HTMLElement & {
            hass?: { states?: Record<string, { attributes?: Record<string, unknown> }> };
          })
        | null;
      return Boolean(el?.hass?.states?.[id]);
    },
    entityId,
    { timeout: STEP_MS }
  );

  const attrs = await page.evaluate((id) => {
    const el = document.querySelector("home-assistant") as HTMLElement & {
      hass: {
        states: Record<string, { attributes?: Record<string, unknown> }>;
      };
    };
    return el.hass.states[id]?.attributes ?? {};
  }, entityId);

  return attrs;
}

export async function getNumberValueViaHass(
  page: Page,
  entityId: string
): Promise<number> {
  const raw = await getStateViaHass(page, entityId);
  const value = Number.parseFloat(raw);
  if (Number.isNaN(value)) {
    throw new Error(`Expected numeric state for ${entityId}, got ${raw}`);
  }
  return value;
}

export async function setNumberValueViaHass(
  page: Page,
  entityId: string,
  value: number
): Promise<void> {
  await callServiceViaHass(page, "number", "set_value", {
    entity_id: entityId,
    value,
  });
  await page.waitForFunction(
    ({ id, expected }) => {
      const el = document.querySelector("home-assistant") as
        | (HTMLElement & { hass?: { states?: Record<string, { state: string }> } })
        | null;
      const raw = el?.hass?.states?.[id]?.state;
      return raw != null && Math.abs(Number.parseFloat(raw) - expected) < 0.01;
    },
    { id: entityId, expected: value },
    { timeout: STEP_MS }
  );
}

/** Reload the Communifarm config entry so new platforms/dashboard views appear. */
export async function reloadCommunifarmViaHass(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const el = document.querySelector("home-assistant") as
      | (HTMLElement & {
          hass?: {
            callWS?: (msg: Record<string, unknown>) => Promise<unknown>;
            callService?: unknown;
          };
        })
      | null;
    return Boolean(el?.hass?.callWS && el?.hass?.callService);
  }, undefined, { timeout: INITIAL_LOAD_MS });

  await page.evaluate(async () => {
    const el = document.querySelector("home-assistant") as HTMLElement & {
      hass: {
        callWS: (msg: Record<string, unknown>) => Promise<
          Array<{ entry_id: string; domain: string }>
        >;
        callService: (
          d: string,
          s: string,
          payload: Record<string, unknown>
        ) => Promise<unknown>;
      };
    };
    const entries = await el.hass.callWS({ type: "config_entries/get" });
    const entry = entries.find((e) => e.domain === "communifarm");
    if (!entry) {
      throw new Error("Communifarm config entry not found");
    }
    await el.hass.callService("homeassistant", "reload_config_entry", {
      entry_id: entry.entry_id,
    });
  });
  // Give platforms + Lovelace provision time to settle.
  await page.waitForTimeout(STEP_MS);
}
