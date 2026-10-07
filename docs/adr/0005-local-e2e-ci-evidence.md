# ADR 0005: Local E2E evidence for merge CI

## Status

Accepted

## Context

T1/T2 Playwright needs a Home Assistant container, mock devices, and OpenBao credentials. Running that stack on hosted GitHub Actions is slow and expensive. Hosted runners also cannot reach the private T3 VM.

Pytest (T0) and ESPHome compile jobs stay cheap enough to run in CI.

## Decision

1. Run merge-blocking Playwright suites **locally** before opening or updating a merge request: `t1_seeded` and `t1_pos` via `yarn test:e2e:report`.
2. Normalize Playwright JSON into a committed, order-independent summary:
   - `test-results/e2e/summary.json` (machine)
   - `test-results/e2e/summary.md` (human)
3. Bind the summary to `git_sha` of the **tested tip** at report time (`git rev-parse HEAD` while that tip is checked out).
4. CI job `e2e-local-report` **does not** start HA or Playwright. It only validates the committed summary:
   - `schema_version` supported
   - `git_sha` equals the PR head / push SHA, **or** equals the first parent when the tip commit only adds `test-results/e2e/summary.json` and `summary.md`
   - required suites present
   - each suite has `failed == 0`, `errored == 0`, and at least one `passed`
5. Pytest T0 and ESPHome compile remain live CI jobs.

## Consequences

- Authors run `yarn test:e2e:report` on the code tip, then commit the summary (often as a follow-up commit that only contains the two summary files).
- A green summary can be forged; reviewers treat it as attested local evidence, not cryptographic proof. SHA binding stops stale reports from older feature tips.
- Raw Playwright JSON, HTML, traces stay gitignored.
