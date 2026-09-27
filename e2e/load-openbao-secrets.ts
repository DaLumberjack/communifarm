/**
 * Load TEST_HA_* from OpenBao into process.env before Playwright runs.
 * Called from playwright.config.ts so workers inherit the values.
 *
 * Prerequisite: OpenBao running + unsealed + `bao login` (token helper or BAO_TOKEN).
 * See docs/user/openbao.md. Set SKIP_OPENBAO_SECRETS=1 to skip.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

type HaSecretPayload = {
  username?: string;
  password?: string;
  token?: string;
};

function alreadyLoaded(): boolean {
  return Boolean(process.env.TEST_HA_USERNAME && process.env.TEST_HA_PASSWORD);
}

function applyPayload(payload: HaSecretPayload): void {
  if (!payload.username || !payload.password) {
    throw new Error(
      "OpenBao kv/ha-test missing username_dev_container/password_dev_container " +
        "(or username-1/password-1)"
    );
  }
  process.env.TEST_HA_USERNAME = payload.username;
  process.env.TEST_HA_PASSWORD = payload.password;
  if (payload.token && !process.env.TEST_HA_TOKEN) {
    process.env.TEST_HA_TOKEN = payload.token;
  }
}

function pickFields(data: Record<string, unknown>): HaSecretPayload {
  return {
    username:
      (data.username_dev_container as string | undefined) ||
      (data["username-1"] as string | undefined) ||
      (data.username as string | undefined),
    password:
      (data.password_dev_container as string | undefined) ||
      (data["password-1"] as string | undefined) ||
      (data.password as string | undefined),
    token:
      (data.long_lived_token as string | undefined) ||
      (data.token as string | undefined) ||
      (data.ha_token as string | undefined),
  };
}

function readTokenHelper(): string | undefined {
  const fromEnv = process.env.BAO_TOKEN || process.env.VAULT_TOKEN;
  if (fromEnv) {
    return fromEnv;
  }
  for (const name of [".bao-token", ".vault-token"]) {
    const file = path.join(os.homedir(), name);
    try {
      if (fs.existsSync(file)) {
        const value = fs.readFileSync(file, "utf8").trim();
        if (value) {
          return value;
        }
      }
    } catch {
      // ignore
    }
  }
  return undefined;
}

function parseKvJson(raw: string): HaSecretPayload {
  const parsed = JSON.parse(raw) as {
    data?: { data?: Record<string, unknown> } & Record<string, unknown>;
  };
  const outer = parsed.data ?? {};
  const nested = (outer.data ?? outer) as Record<string, unknown>;
  return pickFields(nested);
}

function loadViaCli(): boolean {
  const addr =
    process.env.BAO_ADDR || process.env.VAULT_ADDR || "http://127.0.0.1:8200";
  const namespace =
    process.env.BAO_NAMESPACE || process.env.VAULT_NAMESPACE || "homelab";
  const mount = process.env.OPENBAO_KV_MOUNT || "kv";
  const secretPath = process.env.OPENBAO_HA_PATH || "ha-test";
  const token = readTokenHelper();

  const env: NodeJS.ProcessEnv = {
    ...process.env,
    BAO_ADDR: addr,
    VAULT_ADDR: addr,
    BAO_NAMESPACE: namespace,
    VAULT_NAMESPACE: namespace,
  };
  if (token) {
    env.BAO_TOKEN = token;
    env.VAULT_TOKEN = token;
  }

  for (const bin of ["bao", "vault"]) {
    try {
      const raw = execFileSync(
        bin,
        ["kv", "get", "-format=json", `${mount}/${secretPath}`],
        { encoding: "utf8", env, stdio: ["ignore", "pipe", "pipe"] }
      );
      applyPayload(parseKvJson(raw));
      return true;
    } catch {
      // try next binary
    }
  }
  return false;
}

function loadViaHttp(): boolean {
  const addr = (
    process.env.BAO_ADDR ||
    process.env.VAULT_ADDR ||
    "http://127.0.0.1:8200"
  ).replace(/\/$/, "");
  const namespace =
    process.env.BAO_NAMESPACE || process.env.VAULT_NAMESPACE || "homelab";
  const mount = process.env.OPENBAO_KV_MOUNT || "kv";
  const secretPath = process.env.OPENBAO_HA_PATH || "ha-test";
  const token = readTokenHelper();
  if (!token) {
    return false;
  }

  const url = `${addr}/v1/${mount}/data/${secretPath}`;
  const script = `
    const res = await fetch(${JSON.stringify(url)}, {
      headers: {
        "X-Vault-Token": ${JSON.stringify(token)},
        "X-Vault-Namespace": ${JSON.stringify(namespace)},
      },
    });
    if (!res.ok) {
      console.error("openbao_http_status", res.status);
      process.exit(2);
    }
    const body = await res.json();
    process.stdout.write(JSON.stringify(body));
  `;

  try {
    const out = execFileSync(
      process.execPath,
      ["--input-type=module", "-e", script],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    );
    const body = JSON.parse(out) as { data?: { data?: Record<string, unknown> } };
    applyPayload(pickFields(body.data?.data ?? {}));
    return true;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(
      `OpenBao HTTP read failed for ${mount}/data/${secretPath} (namespace=${namespace}): ${message}`
    );
  }
}

/**
 * Populate TEST_HA_USERNAME / TEST_HA_PASSWORD / optional TEST_HA_TOKEN.
 * Safe to call multiple times. No-op if already set or SKIP_OPENBAO_SECRETS=1.
 */
export function loadOpenBaoHaSecrets(): void {
  if (process.env.SKIP_OPENBAO_SECRETS === "1" || alreadyLoaded()) {
    return;
  }

  if (loadViaCli()) {
    return;
  }

  try {
    if (loadViaHttp()) {
      return;
    }
  } catch (err) {
    throw new Error(
      `${String(err)} Start/unseal OpenBao, run bao login, see docs/user/openbao.md.`
    );
  }

  throw new Error(
    "Could not load HA secrets from OpenBao (missing token helper and bao/vault CLI failed). " +
      "Run `bao login` while OpenBao is unsealed, or set TEST_HA_USERNAME/PASSWORD. " +
      "See docs/user/openbao.md."
  );
}
