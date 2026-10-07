#!/usr/bin/env python3
"""Normalize Playwright JSON into a merge-gate summary and validate it in CI.

Local: run Playwright against the HA container, then summarize.
CI: read committed summary.json — do not spin up HA or Playwright.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REQUIRED_SUITES = ("t1_seeded", "t1_pos")
DEFAULT_SUMMARY = Path("test-results/e2e/summary.json")
DEFAULT_MARKDOWN = Path("test-results/e2e/summary.md")
# Tip commit may only add these after report (git_sha points at tested parent).
SUMMARY_ONLY_PATHS = frozenset(
    {
        "test-results/e2e/summary.json",
        "test-results/e2e/summary.md",
    }
)

@dataclass(frozen=True)
class TestRow:
    id: str
    status: str
    duration_ms: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def git_sha(cwd: Path | None = None) -> str:
    out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        text=True,
    )
    return out.strip()


def git_branch(cwd: Path | None = None) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            text=True,
        )
        return out.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def git_parent(sha: str, cwd: Path | None = None) -> str | None:
    """Return first parent SHA, or None for a root / unknown commit."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", f"{sha}^"],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except subprocess.CalledProcessError:
        return None


def commit_paths(sha: str, cwd: Path | None = None) -> set[str]:
    """Paths changed by a single commit (vs its first parent)."""
    out = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        cwd=cwd,
        text=True,
    )
    return {line.strip() for line in out.splitlines() if line.strip()}


def sha_binding_ok(
    summary_sha: str,
    expected_sha: str,
    *,
    cwd: Path | None = None,
) -> bool:
    """True when summary SHA is the tip, or the parent of a summary-only tip."""
    if not summary_sha or not expected_sha:
        return False
    if summary_sha == expected_sha:
        return True
    parent = git_parent(expected_sha, cwd=cwd)
    if parent != summary_sha:
        return False
    paths = commit_paths(expected_sha, cwd=cwd)
    return bool(paths) and paths <= SUMMARY_ONLY_PATHS


def _walk_specs(node: dict[str, Any], file_prefix: str = "") -> list[TestRow]:
    """Flatten Playwright JSON suites into order-independent test rows."""
    rows: list[TestRow] = []
    file_path = node.get("file") or file_prefix

    for spec in node.get("specs") or []:
        title = spec.get("title") or "untitled"
        spec_file = spec.get("file") or file_path or "unknown"
        for test in spec.get("tests") or []:
            results = test.get("results") or []
            if not results:
                status = "skipped"
                duration_ms = 0
            else:
                # Last attempt wins (retries).
                last = results[-1]
                status = str(last.get("status") or "unknown")
                duration_ms = int(last.get("duration") or 0)
            project = ""
            project_name = test.get("projectName")
            if project_name:
                project = f"[{project_name}] "
            test_id = f"{spec_file}::{project}{title}"
            rows.append(TestRow(id=test_id, status=status, duration_ms=duration_ms))

    for child in node.get("suites") or []:
        rows.extend(_walk_specs(child, file_path))
    return rows


def extract_tests(playwright_report: dict[str, Any]) -> list[TestRow]:
    rows: list[TestRow] = []
    for suite in playwright_report.get("suites") or []:
        rows.extend(_walk_specs(suite))
    # Stable order for humans; CI counts ignore order.
    rows.sort(key=lambda r: r.id)
    return rows


def _bucket(status: str) -> str:
    s = status.lower()
    if s in {"passed", "expected"}:
        return "passed"
    if s == "skipped":
        return "skipped"
    if s in {"failed", "timedout", "interrupted"}:
        return "failed"
    # Unknown / unexpected worker crashes land as errored.
    if s in {"unexpected", "error", "errored"}:
        return "errored"
    return "errored"


def suite_rollup(suite_id: str, rows: list[TestRow]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[_bucket(row.status)] += 1
    failed = int(counts.get("failed", 0))
    errored = int(counts.get("errored", 0))
    passed = int(counts.get("passed", 0))
    skipped = int(counts.get("skipped", 0))
    if failed or errored:
        status = "failed"
    elif passed == 0:
        status = "empty"
    else:
        status = "passed"
    return {
        "id": suite_id,
        "status": status,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "skipped": skipped,
        "tests": [
            {"id": r.id, "status": _bucket(r.status), "duration_ms": r.duration_ms}
            for r in rows
        ],
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def build_summary(
    suite_inputs: list[tuple[str, Path]],
    *,
    sha: str,
    branch: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    suites: dict[str, Any] = {}
    for suite_id, report_path in suite_inputs:
        report = load_json(report_path)
        rows = extract_tests(report)
        suites[suite_id] = suite_rollup(suite_id, rows)

    totals = Counter()
    for suite in suites.values():
        for key in ("passed", "failed", "errored", "skipped"):
            totals[key] += int(suite[key])

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now(),
        "git_sha": sha,
        "branch": branch,
        "required_suites": list(REQUIRED_SUITES),
        "suites": suites,
        "totals": {
            "passed": int(totals["passed"]),
            "failed": int(totals["failed"]),
            "errored": int(totals["errored"]),
            "skipped": int(totals["skipped"]),
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Communifarm local E2E summary",
        "",
        f"- Generated: {summary.get('generated_at')}",
        f"- Git SHA: `{summary.get('git_sha')}`",
        f"- Branch: `{summary.get('branch')}`",
        "",
        "## Totals",
        "",
        "| passed | failed | errored | skipped |",
        "|------:|-------:|--------:|--------:|",
        (
            f"| {summary['totals']['passed']} "
            f"| {summary['totals']['failed']} "
            f"| {summary['totals']['errored']} "
            f"| {summary['totals']['skipped']} |"
        ),
        "",
        "## Suites",
        "",
        "| suite | status | passed | failed | errored | skipped |",
        "|-------|--------|-------:|-------:|--------:|--------:|",
    ]
    for suite_id in sorted(summary.get("suites") or {}):
        suite = summary["suites"][suite_id]
        lines.append(
            f"| `{suite_id}` | {suite['status']} | {suite['passed']} | "
            f"{suite['failed']} | {suite['errored']} | {suite['skipped']} |"
        )
    lines.extend(["", "## Failures", ""])
    failures: list[str] = []
    for suite_id, suite in sorted((summary.get("suites") or {}).items()):
        for test in suite.get("tests") or []:
            if test.get("status") in {"failed", "errored"}:
                failures.append(f"- `{suite_id}`: {test['id']} ({test['status']})")
    if failures:
        lines.extend(failures)
    else:
        lines.append("_None._")
    lines.append("")
    return "\n".join(lines)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]


def validate_summary(
    summary: dict[str, Any],
    *,
    expected_sha: str,
    required_suites: tuple[str, ...] = REQUIRED_SUITES,
    cwd: Path | None = None,
) -> ValidationResult:
    errors: list[str] = []

    if int(summary.get("schema_version") or 0) != SCHEMA_VERSION:
        errors.append(
            f"unsupported schema_version={summary.get('schema_version')!r}; "
            f"want {SCHEMA_VERSION}"
        )

    got_sha = str(summary.get("git_sha") or "")
    if not got_sha:
        errors.append("missing git_sha")
    elif not sha_binding_ok(got_sha, expected_sha, cwd=cwd):
        errors.append(
            f"git_sha mismatch: summary={got_sha} expected={expected_sha} "
            "(re-run local E2E on the tested tip; summary tip may only add "
            "test-results/e2e/summary.json|.md)"
        )

    suites = summary.get("suites")
    if not isinstance(suites, dict) or not suites:
        errors.append("suites missing or empty")
        return ValidationResult(ok=False, errors=tuple(errors))

    for suite_id in required_suites:
        if suite_id not in suites:
            errors.append(f"required suite missing: {suite_id}")
            continue
        suite = suites[suite_id]
        if not isinstance(suite, dict):
            errors.append(f"suite {suite_id}: not an object")
            continue
        failed = int(suite.get("failed") or 0)
        errored = int(suite.get("errored") or 0)
        passed = int(suite.get("passed") or 0)
        if failed or errored:
            errors.append(
                f"suite {suite_id}: failed={failed} errored={errored} (must be 0)"
            )
        if passed < 1:
            errors.append(f"suite {suite_id}: passed={passed} (need at least 1)")
        if suite.get("status") != "passed":
            errors.append(
                f"suite {suite_id}: status={suite.get('status')!r} (want 'passed')"
            )

    totals = summary.get("totals") or {}
    if int(totals.get("failed") or 0) or int(totals.get("errored") or 0):
        errors.append(
            f"totals not clean: failed={totals.get('failed')} "
            f"errored={totals.get('errored')}"
        )

    return ValidationResult(ok=not errors, errors=tuple(errors))


def cmd_summarize(args: argparse.Namespace) -> int:
    pairs: list[tuple[str, Path]] = []
    for item in args.suite:
        if ":" not in item:
            print(f"bad --suite value {item!r}; use suite_id:path", file=sys.stderr)
            return 2
        suite_id, path_str = item.split(":", 1)
        pairs.append((suite_id, Path(path_str)))

    sha = args.git_sha or git_sha()
    branch = args.branch or git_branch()
    summary = build_summary(pairs, sha=sha, branch=branch)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    md_path = Path(args.markdown) if args.markdown else out.with_suffix(".md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(summary), encoding="utf-8")

    print(f"wrote {out}")
    print(f"wrote {md_path}")
    # Local summarize still exits non-zero if the report itself is dirty so
    # yarn chains fail before you commit a red summary by accident.
    result = validate_summary(summary, expected_sha=sha)
    if not result.ok:
        for err in result.errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.summary)
    if not path.is_file():
        print(
            f"ERROR: missing {path}. Run `yarn test:e2e:report` locally, "
            "commit test-results/e2e/summary.json (+ .md), then push.",
            file=sys.stderr,
        )
        return 1
    summary = load_json(path)
    expected = args.expected_sha or git_sha()
    result = validate_summary(summary, expected_sha=expected)
    if result.ok:
        print(f"OK: {path} matches SHA {expected} with zero failed/errored tests")
        return 0
    for err in result.errors:
        print(f"ERROR: {err}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    summarize = sub.add_parser("summarize", help="Build summary from Playwright JSON")
    summarize.add_argument(
        "--suite",
        action="append",
        required=True,
        help="suite_id:path/to/playwright-report.json (repeatable)",
    )
    summarize.add_argument("--output", default=str(DEFAULT_SUMMARY))
    summarize.add_argument("--markdown", default=str(DEFAULT_MARKDOWN))
    summarize.add_argument("--git-sha", default=None)
    summarize.add_argument("--branch", default=None)
    summarize.set_defaults(func=cmd_summarize)

    validate = sub.add_parser("validate", help="Validate committed summary for CI")
    validate.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    validate.add_argument(
        "--expected-sha",
        default=None,
        help="PR head / commit SHA the summary must match",
    )
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
