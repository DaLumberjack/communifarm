import { Page, expect } from "@playwright/test";
import {
  callServiceViaHass,
  getAttributesViaHass,
  getStateViaHass,
  setNumberValueViaHass,
} from "./ha-api";
import { resetWeighBatch } from "./weigh-session";
import { STEP_MS } from "../fixtures/timeouts";

const PHASE_MS = STEP_MS * 2;

async function pressCommunifarmButton(
  page: Page,
  entityId: string
): Promise<void> {
  await callServiceViaHass(page, "button", "press", { entity_id: entityId });
}

/** Acquire a culture lot; returns stable culture id (sensor.communifarm_active_culture_id). */
export async function acquireCulture(
  page: Page,
  opts: { name: string; nfcUid?: string }
): Promise<string> {
  await callServiceViaHass(page, "communifarm", "acquire_culture", {
    name: opts.name,
    source_type: "purchased",
    form: "liquid_culture",
    container: "jar",
    ...(opts.nfcUid ? { nfc_uid: opts.nfcUid } : {}),
  });
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_active_culture_id"), {
      timeout: STEP_MS,
    })
    .not.toBe("none");
  return getStateViaHass(page, "sensor.communifarm_active_culture_id");
}

/** @deprecated use acquireCulture */
export async function ensureActiveCulture(
  page: Page,
  name = "E2E LC"
): Promise<void> {
  await acquireCulture(page, { name });
}

/** Mock handheld scan → Production "Select inoculum from NFC scan". */
export async function selectInoculumFromMockNfc(
  page: Page,
  nfcUid: string
): Promise<void> {
  await callServiceViaHass(page, "input_text", "set_value", {
    entity_id: "input_text.esp32dev_last_nfc_uid",
    value: nfcUid,
  });
  await pressCommunifarmButton(
    page,
    "button.communifarm_select_inoculum_from_nfc"
  );
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_active_culture_id"), {
      timeout: STEP_MS,
    })
    .not.toBe("none");
}

/** Pick inoculum from the Production dropdown (select option label). */
export async function selectInoculumByLabel(
  page: Page,
  optionLabel: string
): Promise<void> {
  await callServiceViaHass(page, "select", "select_option", {
    entity_id: "select.communifarm_active_inoculum",
    option: optionLabel,
  });
}

/**
 * Fresh planned batch + culture ready for Production UI inoculate.
 * Mix is not required — inoculate is allowed from `planned`.
 */
export async function prepareBatchForInoculate(
  page: Page,
  batchName: string
): Promise<void> {
  await resetWeighBatch(page, batchName);
  await ensureActiveCulture(page, `E2E LC ${batchName}`);
  await setNumberValueViaHass(page, "number.communifarm_container_count", 1);
  await setNumberValueViaHass(
    page,
    "number.communifarm_substrate_g_per_container",
    1500
  );
}

/** Drive Production tab buttons: inoculate → incubating → fruiting → harvesting. */
export async function advanceProductionViaUi(page: Page): Promise<void> {
  await pressCommunifarmButton(page, "button.communifarm_inoculate_batch");
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_production_status"), {
      timeout: PHASE_MS,
    })
    .toBe("inoculated");

  await pressCommunifarmButton(page, "button.communifarm_move_to_incubation");
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_production_status"), {
      timeout: PHASE_MS,
    })
    .toBe("incubating");

  await pressCommunifarmButton(page, "button.communifarm_move_to_fruiting");
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_production_status"), {
      timeout: PHASE_MS,
    })
    .toBe("fruiting");

  await pressCommunifarmButton(page, "button.communifarm_move_to_harvest");
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_production_status"), {
      timeout: PHASE_MS,
    })
    .toBe("harvesting");
}

/** Batch-level harvest (no NFC) via Production dashboard controls. */
export async function recordBatchHarvestViaUi(
  page: Page,
  massG: number
): Promise<void> {
  await setNumberValueViaHass(page, "number.communifarm_harvest_mass_g", massG);
  await pressCommunifarmButton(page, "button.communifarm_record_harvest");
  await expect
    .poll(
      async () => {
        const attrs = await getAttributesViaHass(
          page,
          "sensor.communifarm_production_status"
        );
        return Number(attrs.total_harvest_g ?? 0);
      },
      { timeout: PHASE_MS }
    )
    .toBeGreaterThanOrEqual(massG - 0.5);
}

/** POS weigh-at-sale via dashboard draft numbers + Confirm sale. */
export async function recordSaleViaUi(
  page: Page,
  opts: { massG: number; lineAmount: number }
): Promise<void> {
  await setNumberValueViaHass(page, "number.communifarm_sale_mass_g", opts.massG);
  await setNumberValueViaHass(
    page,
    "number.communifarm_sale_line_amount",
    opts.lineAmount
  );
  await pressCommunifarmButton(page, "button.communifarm_record_sale");
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_sales_status"), {
      timeout: PHASE_MS,
    })
    .not.toBe("idle");
}

type Milestone = {
  event_type?: string;
  detail?: { container_nfc_uids?: string[]; container_ids?: string[] };
};

/** First container NFC UID spawned at inoculate (defaults to cont_* stable id). */
export async function getFirstContainerNfcUid(page: Page): Promise<string> {
  const attrs = await getAttributesViaHass(
    page,
    "sensor.communifarm_batch_milestones"
  );
  const milestones = (attrs.milestones as Milestone[]) ?? [];
  for (let i = milestones.length - 1; i >= 0; i--) {
    const m = milestones[i];
    if (m.event_type !== "inoculated") {
      continue;
    }
    const uids = m.detail?.container_nfc_uids ?? [];
    if (uids[0]) {
      return uids[0];
    }
    const ids = m.detail?.container_ids ?? [];
    if (ids[0]) {
      return ids[0];
    }
  }
  throw new Error("No inoculated milestone with container NFC UIDs yet");
}

/**
 * Mock handheld scan: set last NFC UID then Communifarm harvest check-in.
 * Does not use esp32dev_simulate_nfc_scan (that path is weigh ingredients only).
 */
export async function mockNfcHarvestCheckIn(
  page: Page,
  nfcUid: string
): Promise<void> {
  await callServiceViaHass(page, "input_text", "set_value", {
    entity_id: "input_text.esp32dev_last_nfc_uid",
    value: nfcUid,
  });
  await callServiceViaHass(page, "communifarm", "check_in", {
    activity: "harvest",
    nfc_uid: nfcUid,
  });
  await expect
    .poll(async () => getStateViaHass(page, "sensor.communifarm_nfc_checkin"), {
      timeout: PHASE_MS,
    })
    .not.toBe("idle");
}

/** Per-container harvest after mock NFC check-in (Harvest tab confirm). */
export async function recordContainerHarvestViaUi(
  page: Page,
  massG: number
): Promise<void> {
  await setNumberValueViaHass(page, "number.communifarm_harvest_mass_g", massG);
  await pressCommunifarmButton(
    page,
    "button.communifarm_confirm_container_harvest"
  );
  await expect
    .poll(
      async () => {
        const attrs = await getAttributesViaHass(
          page,
          "sensor.communifarm_production_status"
        );
        return Number(attrs.total_harvest_g ?? 0);
      },
      { timeout: PHASE_MS }
    )
    .toBeGreaterThan(0);
}
