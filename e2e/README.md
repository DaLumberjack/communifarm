# e2e

## Purpose

Playwright T1–T3 UI flows against allowlisted HA URLs.

## How to use this directory

- Allowlist URLs only (local 8123 or 192.168.102.20). Never production.
- Use Feature index to pick the flow; commit summary.json for MR evidence.

## Map

| path | layer | how / why |
|------|-------|-----------|
| `fixtures/` | `fixture` | Enter for fixture work — read `fixtures/README.md` (Feature index → Map). |
| `flows/` | `dir` | Child map — read `flows/README.md` before exploring. |
| `helpers/` | `dir` | Child map — read `helpers/README.md` before exploring. |
| `load-openbao-secrets.ts` | `e2e` | e2e file `load-openbao-secrets.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `README.md` | `e2e` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| fixtures, fixture | `fixtures/` |
| flows, dir | `flows/` |
| helpers, dir | `helpers/` |
| load-openbao-secrets, e2e, loginCredsLoaded, applyPayload, pickFields, readTokenHelper, parseKvJson, loadViaCli, loadViaHttp, loadOpenBaoHaSecrets | `load-openbao-secrets.ts` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
