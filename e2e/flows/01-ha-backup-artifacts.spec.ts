import { test, expect } from "@playwright/test";
import { getStage } from "../fixtures/environment";
import path from "path";
import fs from "fs";

/**
 * Documents / lightly verifies intake backup artifacts for restore path.
 * Full UI restore is manual/opt-in; this asserts the preferred backup files exist.
 *
 * Backups: docs/intake/Dev Container Backups/
 * Keys: docs/intake/*emergency_kit*.txt (secrets — do not log contents)
 */
test.describe("HA backup artifacts for restore path", () => {
  test("intake Dev Container Backups contain expected tarballs", async () => {
    test.skip(getStage() === "T3", "Backup catalog is local intake only");

    const backupsDir = path.resolve(
      __dirname,
      "../../../../docs/intake/Dev Container Backups"
    );
    expect(fs.existsSync(backupsDir)).toBeTruthy();

    const expected = [
      "automatic_backup_2026_9_3.tar",
      "dev_container_backup_9_26_26_7_24.tar",
    ];
    for (const name of expected) {
      const full = path.join(backupsDir, name);
      expect(fs.existsSync(full), `missing ${name}`).toBeTruthy();
      expect(fs.statSync(full).size).toBeGreaterThan(1000);
    }
  });
});
