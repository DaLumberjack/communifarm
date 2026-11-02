# helpers

## Purpose

Workspace directory `repos/communifarm/e2e/helpers`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `dir`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `ha-api.ts` | `e2e` | e2e file `ha-api.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `ha-token.ts` | `e2e` | e2e file `ha-token.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `har-flow-constants.ts` | `e2e` | e2e file `har-flow-constants.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `mock-scale.ts` | `e2e` | e2e file `mock-scale.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `production-pos.ts` | `e2e` | e2e file `production-pos.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `README.md` | `e2e` | This directory map (dim1 Map + dim2 Feature index). |
| `weigh-session.ts` | `e2e` | e2e file `weigh-session.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `wood-lover-recipe.ts` | `e2e` | e2e file `wood-lover-recipe.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |

## Feature index

| keywords / features | path |
|---------------------|------|
| ha-api, e2e, haApi, setMockTemperature, getState, setNumberValue, getNumberValue, callServiceViaHass, getStateViaHass, getAttributesViaHass | `ha-api.ts` |
| ha-token, e2e, createPlaywrightLongLivedToken, writeGeneratedTokenArtifacts | `ha-token.ts` |
| har-flow-constants, e2e | `har-flow-constants.ts` |
| mock-scale, e2e, haApi, setMockScaleCalibratedSensor, setMockScaleCalibratedSensorViaHass, selectMockScaleIngredient, selectMockScaleIngredientViaHass, simulateMockNfcScan, simulateMockNfcScanViaHass, pressMockScaleButton | `mock-scale.ts` |
| production-pos, e2e, pressCommunifarmButton, acquireCulture, ensureActiveCulture, selectInoculumFromMockNfc, selectInoculumByLabel, prepareBatchForInoculate, advanceProductionViaUi, recordBatchHarvestViaUi | `production-pos.ts` |
| weigh-session, e2e, sessionLineMatches, resetWeighBatch, amountToleranceG, assertAmountWithinTolerance, expectSessionLineRecorded | `weigh-session.ts` |
| wood-lover-recipe, e2e, variedWoodLoverSteps | `wood-lover-recipe.ts` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
