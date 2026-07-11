from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.engine.path_policy import is_acceptance_state_path, is_workspace_source_path
from harness.engine.report import workspace_source_digest
from scripts import validate_benchmark_kb


STATE_PATHS = (
    "ops/acceptance/project_acceptance_report.json",
    "ops/acceptance/dialog_cards/approval_abc.json",
    "ops/acceptance/dialog_transactions/approval_abc.json",
    "harness/PROJECT_ACCEPTANCE.md",
    "harness/signoffs/signoff_request_v1.json",
    "harness/signoffs/signoff_governance_v2.json",
    "harness/signoffs/signoff_current_phase_v1.json",
)

SOURCE_PATHS = (
    ".gitattributes",
    "harness/signoffs/signoff.schema.json",
    "harness/signoffs/README.md",
    "ops/validation/wiki_validation_report.md",
    "harness/engine/report.py",
)


def write_file(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_workspace(root: Path) -> tuple[str, ...]:
    for relative_path in STATE_PATHS:
        write_file(root, relative_path, f"state:{relative_path}:v1")
    for relative_path in SOURCE_PATHS:
        write_file(root, relative_path, f"source:{relative_path}:v1")
    return STATE_PATHS + SOURCE_PATHS


@pytest.mark.parametrize(
    ("path", "excluded"),
    [
        ("ops/acceptance/project_acceptance_report.json", True),
        ("ops/acceptance/dialog_cards/approval_abc.json", True),
        ("ops/acceptance/dialog_transactions/approval_abc.json", True),
        ("harness/PROJECT_ACCEPTANCE.md", True),
        ("harness/signoffs/signoff_request_v1.json", True),
        ("harness/signoffs/signoff_governance_v2.json", True),
        ("harness/signoffs/signoff_current_phase_v1.json", True),
        ("harness/signoffs/nested/policy.json", False),
        ("harness/signoffs/signoff.schema.json", False),
        ("harness/signoffs/README.md", False),
        ("ops/validation/wiki_validation_report.md", False),
        ("harness/engine/report.py", False),
        # Only safe project-relative paths are classified; near-misses and
        # traversal/absolute inputs remain outside the acceptance-state boundary.
        ("ops/acceptance_notes.md", False),
        ("ops/acceptance-backup/report.json", False),
        ("harness/PROJECT_ACCEPTANCE.md.bak", False),
        ("/ops/acceptance/project_acceptance_report.json", False),
        ("../ops/acceptance/project_acceptance_report.json", False),
        ("harness/signoffs/../signoffs/approval.json", False),
    ],
)
def test_acceptance_state_path_policy_is_exact(path: str, excluded: bool) -> None:
    assert is_acceptance_state_path(path) is excluded


def test_workspace_source_digest_ignores_all_acceptance_state_paths(
    tmp_path: Path,
) -> None:
    paths = write_workspace(tmp_path)
    original = workspace_source_digest(tmp_path, paths)

    for relative_path in STATE_PATHS:
        write_file(tmp_path, relative_path, f"state:{relative_path}:v2")

    assert workspace_source_digest(tmp_path, paths) == original


@pytest.mark.parametrize(
    "relative_path",
    [
        ".gitattributes",
        "harness/signoffs/signoff.schema.json",
        "harness/engine/report.py",
    ],
)
def test_workspace_source_digest_tracks_governed_schema_and_source(
    tmp_path: Path, relative_path: str
) -> None:
    paths = write_workspace(tmp_path)
    original = workspace_source_digest(tmp_path, paths)

    write_file(tmp_path, relative_path, f"source:{relative_path}:v2")

    assert workspace_source_digest(tmp_path, paths) != original


def test_gitattributes_is_a_governed_workspace_source_path() -> None:
    assert is_workspace_source_path(".gitattributes") is True


def test_legacy_tracked_file_count_ignores_acceptance_state_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = write_workspace(tmp_path)
    completed = subprocess.CompletedProcess(
        args=["git", "ls-files"],
        returncode=0,
        stdout="\n".join(paths) + "\n",
        stderr="",
    )
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    monkeypatch.setattr(
        validate_benchmark_kb.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )
    errors: list[str] = []

    checked = validate_benchmark_kb.check_tracked_large_or_forbidden_files(errors)

    assert checked == len(SOURCE_PATHS)
    assert errors == []


def test_legacy_tracked_file_scan_disables_repository_fsmonitor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=main"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    (repository / "visible.txt").write_text("visible\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "--", "visible.txt"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    marker = tmp_path / "validator-fsmonitor-executed"
    fsmonitor = tmp_path / "validator-fsmonitor.sh"
    fsmonitor.write_text(
        f"#!/bin/sh\ntouch '{marker}'\nprintf '\\n'\n",
        encoding="utf-8",
    )
    fsmonitor.chmod(0o755)
    subprocess.run(
        ["git", "config", "core.fsmonitor", str(fsmonitor)],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", repository)
    errors: list[str] = []

    checked = validate_benchmark_kb.check_tracked_large_or_forbidden_files(errors)

    assert checked == 1
    assert errors == []
    assert not marker.exists()


def test_legacy_link_scan_ignores_acceptance_state_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    excluded_markdown = (
        "harness/PROJECT_ACCEPTANCE.md",
        "ops/acceptance/project_acceptance_report.md",
        "ops/acceptance/dialog_cards/approval_abc.md",
    )
    governed_markdown = (
        "harness/signoffs/README.md",
        "ops/validation/wiki_validation_report.md",
        "harness/engine/source_contract.md",
    )
    for relative_path in excluded_markdown + governed_markdown:
        write_file(tmp_path, relative_path, "[broken](missing.md)\n")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    checked = validate_benchmark_kb.check_markdown_links(errors)

    assert checked == len(governed_markdown)
    assert set(errors) == {
        f"{relative_path}: broken link -> missing.md"
        for relative_path in governed_markdown
    }
