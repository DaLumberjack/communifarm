"""T0 tests for local E2E summary normalize + CI validate gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.e2e_local_report import (
    SCHEMA_VERSION,
    build_summary,
    extract_tests,
    render_markdown,
    sha_binding_ok,
    validate_summary,
)


def _pw_report(*specs: tuple[str, str, str]) -> dict:
    """Build a minimal Playwright JSON report.

    Each spec: (file, title, status).
    """
    return {
        "suites": [
            {
                "title": "e2e/flows",
                "file": "",
                "specs": [],
                "suites": [
                    {
                        "title": file,
                        "file": file,
                        "specs": [
                            {
                                "title": title,
                                "file": file,
                                "tests": [
                                    {
                                        "projectName": "chromium",
                                        "results": [
                                            {"status": status, "duration": 10}
                                        ],
                                    }
                                ],
                            }
                        ],
                        "suites": [],
                    }
                    for file, title, status in specs
                ],
            }
        ]
    }


def test_extract_tests_is_order_independent(tmp_path: Path) -> None:
    a = _pw_report(
        ("b.spec.ts", "second", "passed"),
        ("a.spec.ts", "first", "failed"),
    )
    b = _pw_report(
        ("a.spec.ts", "first", "failed"),
        ("b.spec.ts", "second", "passed"),
    )
    ids_a = [r.id for r in extract_tests(a)]
    ids_b = [r.id for r in extract_tests(b)]
    assert ids_a == ids_b
    assert ids_a[0].startswith("a.spec.ts::")


def test_build_summary_and_validate_green(tmp_path: Path) -> None:
    seeded = tmp_path / "seeded.json"
    pos = tmp_path / "pos.json"
    seeded.write_text(
        json.dumps(
            _pw_report(
                ("mock-conditions.spec.ts", "inject", "passed"),
                ("weigh-process.spec.ts", "weigh", "passed"),
            )
        ),
        encoding="utf-8",
    )
    pos.write_text(
        json.dumps(
            _pw_report(("production-to-pos.spec.ts", "pos path", "passed"))
        ),
        encoding="utf-8",
    )
    summary = build_summary(
        [("t1_seeded", seeded), ("t1_pos", pos)],
        sha="abc123",
        branch="feature/x",
        generated_at="2026-10-06T00:00:00Z",
    )
    assert summary["schema_version"] == SCHEMA_VERSION
    assert summary["totals"]["failed"] == 0
    assert summary["totals"]["errored"] == 0
    result = validate_summary(summary, expected_sha="abc123")
    assert result.ok, result.errors
    md = render_markdown(summary)
    assert "abc123" in md
    assert "`t1_seeded`" in md


def test_validate_rejects_sha_mismatch_and_failures(tmp_path: Path) -> None:
    seeded = tmp_path / "seeded.json"
    pos = tmp_path / "pos.json"
    seeded.write_text(
        json.dumps(
            _pw_report(("mock-conditions.spec.ts", "inject", "failed"))
        ),
        encoding="utf-8",
    )
    pos.write_text(
        json.dumps(
            _pw_report(("production-to-pos.spec.ts", "pos path", "passed"))
        ),
        encoding="utf-8",
    )
    summary = build_summary(
        [("t1_seeded", seeded), ("t1_pos", pos)],
        sha="deadbeef",
        branch="feature/x",
    )
    result = validate_summary(summary, expected_sha="cafebabe")
    assert not result.ok
    joined = " ".join(result.errors)
    assert "git_sha mismatch" in joined
    assert "t1_seeded" in joined


def test_validate_rejects_missing_required_suite(tmp_path: Path) -> None:
    seeded = tmp_path / "seeded.json"
    seeded.write_text(
        json.dumps(_pw_report(("mock-conditions.spec.ts", "inject", "passed"))),
        encoding="utf-8",
    )
    summary = build_summary(
        [("t1_seeded", seeded)],
        sha="abc123",
        branch="feature/x",
    )
    result = validate_summary(summary, expected_sha="abc123")
    assert not result.ok
    assert any("t1_pos" in e for e in result.errors)


def test_validate_rejects_empty_suite(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"suites": []}), encoding="utf-8")
    pos = tmp_path / "pos.json"
    pos.write_text(
        json.dumps(
            _pw_report(("production-to-pos.spec.ts", "pos path", "passed"))
        ),
        encoding="utf-8",
    )
    summary = build_summary(
        [("t1_seeded", empty), ("t1_pos", pos)],
        sha="abc123",
        branch="feature/x",
    )
    result = validate_summary(summary, expected_sha="abc123")
    assert not result.ok
    assert any("passed=0" in e for e in result.errors)


def test_sha_binding_allows_summary_only_child_tip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import e2e_local_report as mod

    monkeypatch.setattr(mod, "git_parent", lambda sha, cwd=None: "parentsha")
    monkeypatch.setattr(
        mod,
        "commit_paths",
        lambda sha, cwd=None: {
            "test-results/e2e/summary.json",
            "test-results/e2e/summary.md",
        },
    )
    assert sha_binding_ok("parentsha", "childsha")
    monkeypatch.setattr(
        mod,
        "commit_paths",
        lambda sha, cwd=None: {
            "test-results/e2e/summary.json",
            "scripts/e2e_local_report.py",
        },
    )
    assert not sha_binding_ok("parentsha", "childsha")


def test_cli_summarize_and_validate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import e2e_local_report as mod

    seeded = tmp_path / "seeded.json"
    pos = tmp_path / "pos.json"
    seeded.write_text(
        json.dumps(_pw_report(("a.spec.ts", "ok", "passed"))), encoding="utf-8"
    )
    pos.write_text(
        json.dumps(_pw_report(("b.spec.ts", "ok", "passed"))), encoding="utf-8"
    )
    out = tmp_path / "summary.json"
    md = tmp_path / "summary.md"
    monkeypatch.setattr(mod, "git_sha", lambda cwd=None: "sha1")
    monkeypatch.setattr(mod, "git_branch", lambda cwd=None: "main")
    rc = mod.main(
        [
            "summarize",
            f"--suite=t1_seeded:{seeded}",
            f"--suite=t1_pos:{pos}",
            f"--output={out}",
            f"--markdown={md}",
            "--git-sha=sha1",
        ]
    )
    assert rc == 0
    assert out.is_file()
    assert md.is_file()
    assert mod.main(["validate", f"--summary={out}", "--expected-sha=sha1"]) == 0
    assert mod.main(["validate", f"--summary={out}", "--expected-sha=other"]) == 1
