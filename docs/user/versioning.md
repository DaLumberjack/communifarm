# Versioning and merge

1. Develop on a feature branch.
2. Run T0 (+ T1; + T2 if persistence touched).
3. Merge to `main` with a standard git merge.
4. Run `./scripts/bump_version.sh` so `manifest.json` (and `const.VERSION`) advance.
5. Run `./scripts/local_upgrade_install.sh` against the local HA config **without wiping `.storage`**.
6. Run Playwright `TEST_HA_STAGE=T2`.
7. Optionally deploy the same version to `192.168.102.20` (T3).
