# scripts

## Purpose

Lint, local upgrade, OpenBao secrets, deploy, E2E report helpers.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `ops`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `__init__.py` | `config` | Repo helper scripts (importable for T0 tests). — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `bump_version.sh` | `ops` | Bump communifarm manifest version (used on merge-to-main / T2 prep). — Runbooks/scripts — inspect before execute; no secrets in git. |
| `deploy_test_vm.sh` | `ops` | Deploy Communifarm to the HAOS test VM only (192.168.102.20). — Runbooks/scripts — inspect before execute; no secrets in git. |
| `e2e_local_report.py` | `ops` | Normalize Playwright JSON into a merge-gate summary and validate it in CI. Local: run Playwright against the HA container, then summarize. C — Runbooks/scripts — inspect before execute; no secrets in git. |
| `e2e_report.sh` | `ops` | Run merge-blocking local Playwright suites and write committed CI artifacts. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `e2e_validate.sh` | `ops` | Validate committed local E2E summary (used by CI and locally). — Runbooks/scripts — inspect before execute; no secrets in git. |
| `known_hosts.test.example` | `ops` | ops file `known_hosts.test.example`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `lint.sh` | `ops` | Mirror CI Ruff step locally. Fix imports/style, then fail if anything remains. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `load_openbao_ha_secrets.sh` | `ops` | Load HA test credentials from OpenBao into the current shell environment. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `local_upgrade_install.sh` | `ops` | Local T2 helper: copy current component into a local HA config and print next steps. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `openbao_set_playwright_token.sh` | `ops` | Patch OpenBao kv/ha-test with the Playwright long-lived HA token. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| config, init | `__init__.py` |
| bump version, ops | `bump_version.sh` |
| deploy test vm, ops, ssh_cmd, rsync_cmd | `deploy_test_vm.sh` |
| e2e local report, ops, SCHEMA_VERSION, REQUIRED_SUITES, DEFAULT_SUMMARY, DEFAULT_MARKDOWN, SUMMARY_ONLY_PATHS, TestRow, git_sha, git_branch, git_parent, commit_paths | `e2e_local_report.py` |
| e2e report, ops, Playwright | `e2e_report.sh` |
| e2e validate, ops | `e2e_validate.sh` |
| known hosts.test, ops | `known_hosts.test.example` |
| lint, ops | `lint.sh` |
| load openbao ha secrets, ops, OpenBao | `load_openbao_ha_secrets.sh` |
| local upgrade install, ops | `local_upgrade_install.sh` |
| openbao set playwright token, ops, OpenBao, Playwright | `openbao_set_playwright_token.sh` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
