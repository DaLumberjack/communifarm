# fixtures

## Purpose

Workspace directory `repos/communifarm/e2e/fixtures`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `fixture`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `communifarm-page.ts` | `e2e` | e2e file `communifarm-page.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `environment.ts` | `e2e` | e2e file `environment.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `ha-auth.ts` | `e2e` | e2e file `ha-auth.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `ha-onboarding-page.ts` | `e2e` | e2e file `ha-onboarding-page.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `ha-session.ts` | `e2e` | e2e file `ha-session.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `ha-test.ts` | `e2e` | e2e file `ha-test.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |
| `README.md` | `e2e` | This directory map (dim1 Map + dim2 Feature index). |
| `timeouts.ts` | `e2e` | e2e file `timeouts.ts`. — UI flow — allowlisted URL only; refresh e2e summary for MR. |

## Feature index

| keywords / features | path |
|---------------------|------|
| communifarm-page, e2e, CommunifarmPage | `communifarm-page.ts` |
| environment, e2e, getStage, getHaUrl, getCredentials, getOnboardCredentials, liveActuationEnabled | `environment.ts` |
| ha-auth, e2e | `ha-auth.ts` |
| ha-onboarding-page, e2e, HaOnboardingPage | `ha-onboarding-page.ts` |
| ha-session, e2e, startHaSession, loginHa | `ha-session.ts` |
| ha-test, e2e | `ha-test.ts` |
| timeouts, e2e | `timeouts.ts` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
