from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier

import pytest

import harness.approval.git_backend as git_backend
import harness.approval.journal as approval_journal
from harness.approval.cards import create_approval_card
from harness.approval.git_backend import (
    GitBackend,
    GitApprovalError,
    RemoteSnapshot,
    SourceManifestEntry,
    build_proposed_tree,
    collect_source_manifest,
    commit_signoffs,
    commit_source,
    fetch_remote_snapshot,
    push_exact,
    reject_active_git_customization,
    require_main_with_clean_index,
    require_main_with_clean_or_exact_signoff_index,
    run_git_optional,
    stage_exact_manifest,
    temporary_clean_worktree,
)
from harness.approval.journal import (
    JournalError,
    TransactionState,
    create_journal,
    load_journal,
    transition_journal,
)
from harness.approval.models import PROFILE_RATIONALES
from tests.approval_git_helpers import (
    ApprovalGitFixture,
    advance_remote,
    commit_all,
    git_stdout,
    init_repo_with_bare_remote,
    install_sanitized_git_environment,
    nul_paths,
    run_git,
    sha256_file,
)


CARD_ID = "approval_" + "a" * 24
CARD_SHA256 = "b" * 64
APPROVAL_EVENT_ID = "approval_event_" + "c" * 24
REVIEWED_AT = "2026-07-10T12:00:00+00:00"


@pytest.fixture
def repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> ApprovalGitFixture:
    fixture = init_repo_with_bare_remote(tmp_path)
    install_sanitized_git_environment(monkeypatch, fixture.environment)
    return fixture


def make_manifest_changes(fixture: ApprovalGitFixture) -> None:
    (fixture.work / "README.md").write_text("modified\n", encoding="utf-8")
    (fixture.work / "scripts").mkdir(exist_ok=True)
    executable = fixture.work / "scripts/new-tool.sh"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    (fixture.work / "docs/delete-me.txt").unlink()


def remote_snapshot(fixture: ApprovalGitFixture) -> RemoteSnapshot:
    return fetch_remote_snapshot(
        fixture.work,
        remote_name="origin",
        expected_url=str(fixture.remote),
        ref="refs/heads/main",
    )


@pytest.mark.parametrize(
    "stdout",
    (
        f"{'2' * 40} refs/heads/main\n",
        f"pack\t{'1' * 40}\n{'2' * 40} refs/heads/main\n",
    ),
)
def test_transport_remote_oid_accepts_canonical_fetch_pack_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
) -> None:
    def complete(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert arguments == (
            "fetch-pack",
            "--no-progress",
            "--upload-pack=git-upload-pack",
            "git@github.com:luvega/pep-design.git",
            "refs/heads/main",
        )
        assert kwargs == {"safe_transport": True}
        return subprocess.CompletedProcess(["git"], 0, stdout, "")

    monkeypatch.setattr(git_backend, "run_git", complete)

    assert git_backend._transport_remote_oid(
        tmp_path,
        url="git@github.com:luvega/pep-design.git",
        ref="refs/heads/main",
    ) == "2" * 40


@pytest.mark.parametrize(
    "stdout",
    (
        f"pack\t{'1' * 40}\n{'2' * 40} refs/heads/main\nunexpected\n",
        f"pack\t{'1' * 40}\npack\t{'3' * 40}\n{'2' * 40} refs/heads/main\n",
        f"pack {'1' * 40}\n{'2' * 40} refs/heads/main\n",
        f"pack\t{'A' * 40}\n{'2' * 40} refs/heads/main\n",
        f"pack\t{'1' * 39}\n{'2' * 40} refs/heads/main\n",
        f"{'2' * 40} refs/heads/main\n{'2' * 40} refs/heads/main\n",
        f"{'2' * 40} refs/heads/main\npack\t{'1' * 40}\n",
        f"{'2' * 40} refs/heads/other\n",
        "not-an-oid refs/heads/main\n",
        f"{'2' * 40} refs/heads/main\ntoken=ghp_must_not_be_echoed\n",
    ),
)
def test_transport_remote_oid_rejects_noncanonical_fetch_pack_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
) -> None:
    monkeypatch.setattr(
        git_backend,
        "run_git",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            ["git"], 0, stdout, ""
        ),
    )

    with pytest.raises(GitApprovalError, match="canonical") as error:
        git_backend._transport_remote_oid(
            tmp_path,
            url="git@github.com:luvega/pep-design.git",
            ref="refs/heads/main",
        )

    assert "ghp_must_not_be_echoed" not in str(error.value)


def test_require_main_rejects_a_dirty_index(repository: ApprovalGitFixture) -> None:
    (repository.work / "README.md").write_text("staged\n", encoding="utf-8")
    run_git(
        repository.work,
        "add",
        "--",
        "README.md",
        environment=repository.environment,
    )

    with pytest.raises(GitApprovalError, match="index|staged|cached"):
        require_main_with_clean_index(repository.work)


def test_require_main_accepts_unstaged_changes_but_rejects_other_branch(
    repository: ApprovalGitFixture,
) -> None:
    (repository.work / "README.md").write_text("unstaged\n", encoding="utf-8")
    require_main_with_clean_index(repository.work)

    run_git(
        repository.work,
        "switch",
        "-c",
        "not-main",
        environment=repository.environment,
    )
    with pytest.raises(GitApprovalError, match="main|branch"):
        require_main_with_clean_index(repository.work)


def test_recoverable_signoff_index_rejects_manifest_outside_signoff_namespace(
    repository: ApprovalGitFixture,
) -> None:
    manifest = (
        SourceManifestEntry(
            path="README.md",
            status="modified",
            mode="100644",
            sha256=sha256_file(repository.work / "README.md"),
        ),
    )

    with pytest.raises(GitApprovalError, match="two|signoff|namespace"):
        require_main_with_clean_or_exact_signoff_index(
            repository.work, manifest
        )


def test_manifest_records_modified_untracked_and_deleted_content(
    repository: ApprovalGitFixture,
) -> None:
    make_manifest_changes(repository)

    manifest = collect_source_manifest(repository.work)
    entries = {entry.path: entry for entry in manifest}

    assert tuple(entry.path for entry in manifest) == tuple(sorted(entries))
    assert set(entries) == {
        "README.md",
        "docs/delete-me.txt",
        "scripts/new-tool.sh",
    }
    assert entries["README.md"].status == "modified"
    assert entries["README.md"].mode == "100644"
    assert entries["README.md"].sha256 == sha256_file(
        repository.work / "README.md"
    )
    assert entries["scripts/new-tool.sh"].status == "untracked"
    assert entries["scripts/new-tool.sh"].mode == "100755"
    assert entries["scripts/new-tool.sh"].sha256 == sha256_file(
        repository.work / "scripts/new-tool.sh"
    )
    assert entries["docs/delete-me.txt"].status == "deleted"
    assert entries["docs/delete-me.txt"].mode is None
    assert entries["docs/delete-me.txt"].sha256 is None


def test_proposed_tree_equals_the_tree_from_exact_staging(
    repository: ApprovalGitFixture,
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)

    proposed_tree = build_proposed_tree(repository.work, manifest)
    assert nul_paths(
        repository.work,
        repository.environment,
        "diff",
        "--cached",
        "--name-only",
        "-z",
    ) == ()

    stage_exact_manifest(repository.work, manifest)

    assert set(
        nul_paths(
            repository.work,
            repository.environment,
            "diff",
            "--cached",
            "--name-only",
            "-z",
        )
    ) == {entry.path for entry in manifest}
    assert (
        git_stdout(repository.work, repository.environment, "write-tree")
        == proposed_tree
    )


def test_exact_staging_rejects_manifest_drift_without_staging(
    repository: ApprovalGitFixture,
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    (repository.work / "README.md").write_text(
        "changed after review\n", encoding="utf-8"
    )

    with pytest.raises(GitApprovalError, match="manifest|changed|drift|sha"):
        stage_exact_manifest(repository.work, manifest)

    assert nul_paths(
        repository.work,
        repository.environment,
        "diff",
        "--cached",
        "--name-only",
        "-z",
    ) == ()


def test_untracked_crlf_manifest_binds_git_clean_blob_and_clean_checkout(
    repository: ApprovalGitFixture,
) -> None:
    attributes = repository.work / ".gitattributes"
    (repository.work / "benchmark").mkdir()
    csv = repository.work / "benchmark" / "data.csv"
    attributes.write_text("benchmark/*.csv text eol=lf\n", encoding="utf-8")
    csv.write_bytes(b"name,value\r\nalpha,1\r\n")

    manifest = collect_source_manifest(repository.work)
    entries = {entry.path: entry for entry in manifest}
    clean_bytes = b"name,value\nalpha,1\n"

    assert entries["benchmark/data.csv"].status == "untracked"
    assert entries["benchmark/data.csv"].mode == "100644"
    assert entries["benchmark/data.csv"].sha256 == hashlib.sha256(clean_bytes).hexdigest()
    proposed_tree = build_proposed_tree(repository.work, manifest)
    stage_exact_manifest(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work,
        repository.environment,
        "rev-parse",
        "HEAD",
    )
    commit_oid = commit_source(
        repository.work,
        manifest,
        CARD_ID,
        expected_parent_oid=expected_parent,
    )

    assert git_stdout(
        repository.work,
        repository.environment,
        "show",
        "-s",
        "--format=%T",
        commit_oid,
    ) == proposed_tree
    committed_blob = run_git(
        repository.work,
        "show",
        f"{commit_oid}:benchmark/data.csv",
        environment=repository.environment,
    ).stdout
    assert committed_blob == clean_bytes
    assert entries["benchmark/data.csv"].sha256 == hashlib.sha256(committed_blob).hexdigest()

    def inspect_checkout(clean_root: Path) -> None:
        assert (clean_root / "benchmark" / "data.csv").read_bytes() == clean_bytes

    temporary_clean_worktree(repository.work, commit_oid, inspect_checkout)


def test_tracked_crlf_manifest_ignores_raw_line_ending_only_drift(
    repository: ApprovalGitFixture,
) -> None:
    (repository.work / "benchmark").mkdir()
    (repository.work / ".gitattributes").write_text(
        "benchmark/*.csv text eol=lf\n",
        encoding="utf-8",
    )
    csv = repository.work / "benchmark" / "tracked.csv"
    csv.write_bytes(b"name,value\nbase,0\n")
    commit_all(
        repository,
        repository.work,
        "tracked normalized csv",
        [".gitattributes", "benchmark/tracked.csv"],
    )
    csv.write_bytes(b"name,value\r\nchanged,1\r\n")

    manifest = collect_source_manifest(repository.work)
    csv_entry = next(
        entry for entry in manifest if entry.path == "benchmark/tracked.csv"
    )
    canonical_bytes = b"name,value\nchanged,1\n"
    assert csv_entry.status == "modified"
    assert csv_entry.sha256 == hashlib.sha256(canonical_bytes).hexdigest()

    csv.write_bytes(canonical_bytes)

    assert collect_source_manifest(repository.work) == manifest
    build_proposed_tree(repository.work, manifest)
    stage_exact_manifest(repository.work, manifest)


def test_binary_manifest_hashes_exact_blob_bytes_without_newline_translation(
    repository: ApprovalGitFixture,
) -> None:
    (repository.work / "benchmark").mkdir()
    payload = b"\x00binary\r\ncontent\xff\r\n"
    binary = repository.work / "benchmark" / "payload.bin"
    binary.write_bytes(payload)

    manifest = collect_source_manifest(repository.work)
    entry = next(
        value for value in manifest if value.path == "benchmark/payload.bin"
    )

    assert entry.sha256 == hashlib.sha256(payload).hexdigest()
    build_proposed_tree(repository.work, manifest)
    stage_exact_manifest(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work,
        repository.environment,
        "rev-parse",
        "HEAD",
    )
    commit_oid = commit_source(
        repository.work,
        manifest,
        CARD_ID,
        expected_parent_oid=expected_parent,
    )
    committed = run_git(
        repository.work,
        "show",
        f"{commit_oid}:benchmark/payload.bin",
        environment=repository.environment,
    ).stdout

    assert committed == payload
    assert entry.sha256 == hashlib.sha256(committed).hexdigest()


@pytest.mark.parametrize("filter_key", ["clean", "process"])
def test_executable_clean_filter_configuration_is_rejected_before_staging(
    repository: ApprovalGitFixture,
    filter_key: str,
) -> None:
    marker = repository.work.parent / f"{filter_key}-filter-ran"
    run_git(
        repository.work,
        "config",
        "--local",
        f"filter.hostile.{filter_key}",
        f"sh -c 'touch {marker}; cat'",
        environment=repository.environment,
    )
    (repository.work / "benchmark").mkdir()
    (repository.work / ".gitattributes").write_text(
        "benchmark/*.payload filter=hostile\n",
        encoding="utf-8",
    )
    (repository.work / "benchmark" / "input.payload").write_text(
        "payload\n", encoding="utf-8"
    )

    with pytest.raises(GitApprovalError, match="filter|clean|process|config"):
        collect_source_manifest(repository.work)

    assert not marker.exists()


def test_clean_filter_added_at_git_add_boundary_cannot_execute(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = repository.work.parent / "late-clean-filter-ran"
    (repository.work / "benchmark").mkdir()
    (repository.work / ".gitattributes").write_text(
        "benchmark/*.payload filter=hostile\n",
        encoding="utf-8",
    )
    (repository.work / "benchmark" / "input.payload").write_text(
        "payload\n",
        encoding="utf-8",
    )
    manifest = collect_source_manifest(repository.work)
    real_run_git = git_backend.run_git
    mutated: list[bool] = []

    def mutate_at_add(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments and arguments[0] == "add" and not mutated:
            run_git(
                repository.work,
                "config",
                "--local",
                "filter.hostile.clean",
                f"sh -c 'touch {marker}; cat'",
                environment=repository.environment,
            )
            mutated.append(True)
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", mutate_at_add)

    with pytest.raises(GitApprovalError, match="filter|clean|config"):
        stage_exact_manifest(repository.work, manifest)

    assert mutated == [True]
    assert not marker.exists()
    assert nul_paths(
        repository.work,
        repository.environment,
        "diff",
        "--cached",
        "--name-only",
        "-z",
    ) == ()


def test_clean_filter_added_at_manifest_diff_boundary_cannot_execute(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = repository.work.parent / "discovery-clean-filter-ran"
    (repository.work / "benchmark").mkdir()
    (repository.work / ".gitattributes").write_text(
        "benchmark/*.payload filter=hostile\n",
        encoding="utf-8",
    )
    payload = repository.work / "benchmark" / "input.payload"
    payload.write_text("base\n", encoding="utf-8")
    commit_all(
        repository,
        repository.work,
        "tracked filtered payload",
        [".gitattributes", "benchmark/input.payload"],
    )
    payload.write_text("changed\n", encoding="utf-8")
    real_run_git = git_backend.run_git
    mutated: list[bool] = []

    def mutate_at_diff(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if (
            arguments
            and arguments[0] == "diff"
            and "--name-only" in arguments
            and not mutated
        ):
            run_git(
                repository.work,
                "config",
                "--local",
                "filter.hostile.clean",
                f"sh -c 'touch {marker}; cat'",
                environment=repository.environment,
            )
            mutated.append(True)
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", mutate_at_diff)

    with pytest.raises(GitApprovalError, match="filter|clean|config"):
        collect_source_manifest(repository.work)

    assert mutated == [True]
    assert not marker.exists()


def test_fsmonitor_added_at_manifest_diff_boundary_cannot_execute(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = repository.work.parent / "fsmonitor-ran"
    monitor = repository.work.parent / "hostile-fsmonitor"
    monitor.write_text(
        f"#!/bin/sh\nprintf ran > {marker}\nprintf '0'\n",
        encoding="utf-8",
    )
    monitor.chmod(0o755)
    (repository.work / "README.md").write_text("changed\n", encoding="utf-8")
    real_run_git = git_backend.run_git
    mutated: list[bool] = []

    def mutate_at_diff(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if (
            arguments
            and arguments[0] == "diff"
            and "--name-only" in arguments
            and not mutated
        ):
            run_git(
                repository.work,
                "config",
                "--local",
                "core.fsmonitor",
                str(monitor),
                environment=repository.environment,
            )
            mutated.append(True)
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", mutate_at_diff)

    manifest = collect_source_manifest(repository.work)

    assert mutated == [True]
    assert tuple(entry.path for entry in manifest) == ("README.md",)
    assert not marker.exists()


def test_isolated_diff_check_ignores_late_filter_and_reports_whitespace(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (repository.work / "benchmark").mkdir()
    (repository.work / ".gitattributes").write_text(
        "benchmark/*.payload filter=hostile\n",
        encoding="utf-8",
    )
    payload = repository.work / "benchmark" / "diff-check.payload"
    payload.write_text("base\n", encoding="utf-8")
    commit_all(
        repository,
        repository.work,
        "tracked diff-check payload",
        [".gitattributes", "benchmark/diff-check.payload"],
    )
    payload.write_text("changed\n", encoding="utf-8")
    marker = repository.work.parent / "diff-check-filter-ran"
    real_run_git = git_backend.run_git
    mutated: list[bool] = []

    def mutate_at_diff_check(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if (
            arguments
            and arguments[0] == "diff"
            and "--check" in arguments
            and not mutated
        ):
            run_git(
                repository.work,
                "config",
                "--local",
                "filter.hostile.clean",
                f"sh -c 'touch {marker}; cat'",
                environment=repository.environment,
            )
            mutated.append(True)
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", mutate_at_diff_check)

    git_backend.check_worktree_diff(repository.work)

    assert mutated == [True]
    assert not marker.exists()
    payload.write_text("trailing whitespace \n", encoding="utf-8")
    with pytest.raises(GitApprovalError, match="trailing whitespace|diff"):
        git_backend.check_worktree_diff(repository.work)
    assert not marker.exists()


def test_literal_wildcard_filename_is_staged_as_one_exact_path(
    repository: ApprovalGitFixture,
) -> None:
    relative_path = "docs/literal[abc]*?.txt"
    (repository.work / relative_path).write_text("literal path\n", encoding="utf-8")
    manifest = collect_source_manifest(repository.work)

    assert tuple(entry.path for entry in manifest) == (relative_path,)
    proposed_tree = build_proposed_tree(repository.work, manifest)
    stage_exact_manifest(repository.work, manifest)

    assert nul_paths(
        repository.work,
        repository.environment,
        "diff",
        "--cached",
        "--name-only",
        "-z",
    ) == (relative_path,)
    assert git_stdout(repository.work, repository.environment, "write-tree") == proposed_tree


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("core.hooksPath", "custom-hooks"),
        ("core.sshCommand", "ssh -F hostile-config"),
        ("core.fsmonitor", "/tmp/hostile-fsmonitor"),
        ("core.attributesFile", "/tmp/hostile-attributes"),
        ("diff.external", "/tmp/hostile-diff"),
        ("diff.hostile.textconv", "/tmp/hostile-textconv"),
        ("url.https://mirror.example/.insteadOf", "git@github.com:"),
        ("url.https://mirror.example/.pushInsteadOf", "git@github.com:"),
    ],
)
def test_active_git_configuration_is_rejected(
    repository: ApprovalGitFixture, key: str, value: str
) -> None:
    run_git(
        repository.work,
        "config",
        "--local",
        key,
        value,
        environment=repository.environment,
    )

    with pytest.raises(GitApprovalError, match="config|hook|ssh|instead"):
        reject_active_git_customization(repository.work)


@pytest.mark.parametrize(
    "hook_name",
    [
        "pre-commit",
        "commit-msg",
        "pre-push",
        "reference-transaction",
        "post-checkout",
        "organization-specific-hook",
    ],
)
def test_active_commit_or_push_hook_is_rejected(
    repository: ApprovalGitFixture, hook_name: str
) -> None:
    hook = repository.work / ".git" / "hooks" / hook_name
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)

    with pytest.raises(GitApprovalError, match="hook"):
        reject_active_git_customization(repository.work)


def test_executable_sample_hook_is_not_treated_as_active(
    repository: ApprovalGitFixture,
) -> None:
    hook = repository.work / ".git" / "hooks" / "pre-commit.sample"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
    hook.chmod(0o755)

    reject_active_git_customization(repository.work)


def test_remote_snapshot_uses_fetch_url_when_pushurl_is_absent_and_lists_ahead(
    repository: ApprovalGitFixture,
) -> None:
    (repository.work / "local.txt").write_text("local\n", encoding="utf-8")
    local_oid = commit_all(repository, repository.work, "local", ["local.txt"])

    snapshot = remote_snapshot(repository)

    assert snapshot.name == "origin"
    assert snapshot.fetch_url == str(repository.remote)
    assert snapshot.push_url == str(repository.remote)
    assert snapshot.ref == "refs/heads/main"
    assert snapshot.head_oid == local_oid
    assert snapshot.oid == git_stdout(
        repository.remote,
        repository.environment,
        "rev-parse",
        "refs/heads/main",
    )
    assert snapshot.oid != snapshot.head_oid
    assert snapshot.ahead_commits == (local_oid,)


def test_remote_snapshot_rejects_a_different_explicit_push_url(
    repository: ApprovalGitFixture,
) -> None:
    run_git(
        repository.work,
        "config",
        "--local",
        "remote.origin.pushurl",
        str(repository.remote.parent / "other.git"),
        environment=repository.environment,
    )

    with pytest.raises(GitApprovalError, match="push.*url|remote"):
        remote_snapshot(repository)


def test_remote_snapshot_rejects_duplicate_fetch_urls_even_when_equal(
    repository: ApprovalGitFixture,
) -> None:
    run_git(
        repository.work,
        "config",
        "--local",
        "--add",
        "remote.origin.url",
        str(repository.remote),
        environment=repository.environment,
    )

    with pytest.raises(GitApprovalError, match="fetch.*url|exactly one|multiple"):
        remote_snapshot(repository)


def test_remote_snapshot_rejects_duplicate_push_urls_even_when_equal(
    repository: ApprovalGitFixture,
) -> None:
    for _ in range(2):
        run_git(
            repository.work,
            "config",
            "--local",
            "--add",
            "remote.origin.pushurl",
            str(repository.remote),
            environment=repository.environment,
        )

    with pytest.raises(GitApprovalError, match="push.*url|exactly one|multiple"):
        remote_snapshot(repository)


def test_remote_snapshot_rejects_a_mismatched_fetch_url(
    repository: ApprovalGitFixture,
) -> None:
    unexpected = repository.remote.parent / "unexpected.git"

    with pytest.raises(GitApprovalError, match="fetch.*url|remote|expected"):
        fetch_remote_snapshot(
            repository.work,
            remote_name="origin",
            expected_url=str(unexpected),
            ref="refs/heads/main",
        )


def test_remote_snapshot_rejects_local_head_behind_origin_main(
    repository: ApprovalGitFixture,
) -> None:
    advance_remote(repository)

    with pytest.raises(
        GitApprovalError, match="behind|ancestor|fast.forward|origin/main|remote"
    ):
        remote_snapshot(repository)


def test_remote_snapshot_rejects_diverged_local_and_origin_main(
    repository: ApprovalGitFixture,
) -> None:
    (repository.work / "local.txt").write_text("local\n", encoding="utf-8")
    commit_all(repository, repository.work, "local", ["local.txt"])
    advance_remote(repository)

    with pytest.raises(
        GitApprovalError, match="diverg|ancestor|fast.forward|origin/main|remote"
    ):
        remote_snapshot(repository)


def test_source_commit_has_exact_tree_and_approval_trailer(
    repository: ApprovalGitFixture,
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    proposed_tree = build_proposed_tree(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )
    stage_exact_manifest(repository.work, manifest)

    commit_oid = commit_source(
        repository.work,
        manifest,
        CARD_ID,
        expected_parent_oid=expected_parent,
    )

    assert git_stdout(
        repository.work, repository.environment, "show", "-s", "--format=%T", commit_oid
    ) == proposed_tree
    message = git_stdout(
        repository.work, repository.environment, "show", "-s", "--format=%B", commit_oid
    )
    assert git_stdout(
        repository.work,
        repository.environment,
        "show",
        "-s",
        "--format=%P",
        commit_oid,
    ) == expected_parent
    assert f"Approval-Card: {CARD_ID}" in message


@pytest.mark.parametrize("drift_kind", ["blob", "mode"])
def test_source_commit_rejects_staged_blob_or_mode_drift(
    repository: ApprovalGitFixture, drift_kind: str
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    stage_exact_manifest(repository.work, manifest)
    original_head = git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )
    if drift_kind == "blob":
        replacement = repository.work / "replacement-content.txt"
        replacement.write_text("not reviewed\n", encoding="utf-8")
        replacement_oid = git_stdout(
            repository.work,
            repository.environment,
            "hash-object",
            "-w",
            "--",
            str(replacement),
        )
        run_git(
            repository.work,
            "update-index",
            "--cacheinfo",
            f"100644,{replacement_oid},README.md",
            environment=repository.environment,
        )
    else:
        run_git(
            repository.work,
            "update-index",
            "--chmod=+x",
            "--",
            "README.md",
            environment=repository.environment,
        )

    with pytest.raises(GitApprovalError, match="staged|index|blob|mode|sha|manifest"):
        commit_source(repository.work, manifest, CARD_ID)

    assert git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    ) == original_head


@pytest.mark.parametrize("toctou_kind", ["extra-path", "blob-replacement"])
def test_commit_object_validation_rejects_index_toctou_before_ref_update(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
    toctou_kind: str,
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    stage_exact_manifest(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )
    payload = repository.work.parent / f"{toctou_kind}-payload.txt"
    payload.write_text("not reviewed by the card\n", encoding="utf-8")
    replacement_oid = git_stdout(
        repository.work,
        repository.environment,
        "hash-object",
        "-w",
        "--",
        str(payload),
    )
    real_run_git = git_backend.run_git
    injected: list[str] = []

    def mutate_index_before_tree(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments and arguments[0] == "write-tree" and not injected:
            path = "docs/toctou-extra.txt" if toctou_kind == "extra-path" else "README.md"
            add_flag = ("--add",) if toctou_kind == "extra-path" else ()
            run_git(
                repository.work,
                "update-index",
                *add_flag,
                "--cacheinfo",
                f"100644,{replacement_oid},{path}",
                environment=repository.environment,
            )
            injected.append(path)
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", mutate_index_before_tree)

    with pytest.raises(GitApprovalError, match="commit|path|blob|sha|manifest"):
        commit_source(
            repository.work,
            manifest,
            CARD_ID,
            expected_parent_oid=expected_parent,
        )

    assert len(injected) == 1
    assert git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    ) == expected_parent


def test_reconcile_rejects_graft_spoofed_exact_parent(
    repository: ApprovalGitFixture,
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    proposed_tree = build_proposed_tree(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work,
        repository.environment,
        "rev-parse",
        "HEAD",
    )
    parent_tree = git_stdout(
        repository.work,
        repository.environment,
        "show",
        "-s",
        "--format=%T",
        expected_parent,
    )
    wrong_parent = git_stdout(
        repository.work,
        repository.environment,
        "commit-tree",
        parent_tree,
        "-m",
        "unrelated parent",
    )
    malicious_commit = git_stdout(
        repository.work,
        repository.environment,
        "commit-tree",
        proposed_tree,
        "-p",
        wrong_parent,
        "-m",
        "chore: checkpoint dialog approval source",
        "-m",
        f"Approval-Card: {CARD_ID}",
    )
    run_git(
        repository.work,
        "update-ref",
        "refs/heads/main",
        malicious_commit,
        expected_parent,
        environment=repository.environment,
    )
    grafts = repository.work / ".git" / "info" / "grafts"
    grafts.parent.mkdir(parents=True, exist_ok=True)
    grafts.write_text(
        f"{malicious_commit} {expected_parent}\n",
        encoding="ascii",
    )
    spoofed_parents = git_stdout(
        repository.work,
        repository.environment,
        "rev-list",
        "--parents",
        "-n",
        "1",
        malicious_commit,
    ).split()
    assert spoofed_parents == [malicious_commit, expected_parent]

    with pytest.raises(GitApprovalError, match="parent|child|card commit"):
        git_backend.reconcile_card_commit(
            repository.work,
            expected_parent,
            CARD_ID,
            tuple(entry.path for entry in manifest),
            expected_tree_oid=proposed_tree,
            expected_manifest=manifest,
        )


def test_source_commit_ref_update_rejects_parent_race(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    stage_exact_manifest(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )
    parent_tree = git_stdout(
        repository.work,
        repository.environment,
        "show",
        "-s",
        "--format=%T",
        expected_parent,
    )
    real_status = git_backend._run_git_status
    raced: list[str] = []

    def race_before_update(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments and arguments[0] == "update-ref" and not raced:
            race_oid = git_stdout(
                repository.work,
                repository.environment,
                "commit-tree",
                parent_tree,
                "-p",
                expected_parent,
                "-m",
                "independent race",
            )
            run_git(
                repository.work,
                "update-ref",
                "refs/heads/main",
                race_oid,
                expected_parent,
                environment=repository.environment,
            )
            raced.append(race_oid)
        return real_status(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "_run_git_status", race_before_update)

    with pytest.raises(GitApprovalError, match="parent|race|trailer|card|ref"):
        commit_source(
            repository.work,
            manifest,
            CARD_ID,
            expected_parent_oid=expected_parent,
        )

    assert len(raced) == 1
    assert git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    ) == raced[0]


def test_reference_transaction_hook_added_at_ref_update_cannot_execute(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    stage_exact_manifest(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work,
        repository.environment,
        "rev-parse",
        "HEAD",
    )
    marker = repository.work.parent / "reference-transaction-ran"
    real_status = git_backend._run_git_status
    installed: list[bool] = []

    def install_hook_before_update(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments and arguments[0] == "update-ref" and not installed:
            hook = repository.work / ".git" / "hooks" / "reference-transaction"
            hook.parent.mkdir(parents=True, exist_ok=True)
            hook.write_text(
                f"#!/bin/sh\nprintf ran > {marker}\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)
            installed.append(True)
        return real_status(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "_run_git_status", install_hook_before_update)

    commit_oid = commit_source(
        repository.work,
        manifest,
        CARD_ID,
        expected_parent_oid=expected_parent,
    )

    assert installed == [True]
    assert commit_oid == git_stdout(
        repository.work,
        repository.environment,
        "rev-parse",
        "HEAD",
    )
    assert not marker.exists()


def test_source_commit_recovers_ambiguous_post_update_ref_error(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_manifest_changes(repository)
    manifest = collect_source_manifest(repository.work)
    proposed_tree = build_proposed_tree(repository.work, manifest)
    stage_exact_manifest(repository.work, manifest)
    expected_parent = git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )
    real_status = git_backend._run_git_status
    injected: list[int] = []

    def ambiguous_after_update(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        completed = real_status(root, *arguments, **kwargs)
        if arguments and arguments[0] == "update-ref" and not injected:
            assert completed.returncode == 0
            injected.append(1)
            return subprocess.CompletedProcess(
                completed.args,
                1,
                completed.stdout,
                "simulated lost update-ref acknowledgement",
            )
        return completed

    monkeypatch.setattr(git_backend, "_run_git_status", ambiguous_after_update)

    commit_oid = commit_source(
        repository.work,
        manifest,
        CARD_ID,
        expected_parent_oid=expected_parent,
    )

    assert injected == [1]
    assert commit_oid == git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )
    assert git_backend.reconcile_card_commit(
        repository.work,
        expected_parent,
        CARD_ID,
        tuple(entry.path for entry in manifest),
        expected_tree_oid=proposed_tree,
        expected_manifest=manifest,
    ) == commit_oid


def test_signoff_commit_stages_only_the_two_declared_paths(
    repository: ApprovalGitFixture,
) -> None:
    signoff_root = repository.work / "harness" / "signoffs"
    signoff_root.mkdir(parents=True)
    paths = (
        "harness/signoffs/signoff_governance_v2.json",
        "harness/signoffs/signoff_current_phase_v1.json",
    )
    for path in paths:
        (repository.work / path).write_text("{}\n", encoding="utf-8")
    (repository.work / "unrelated.txt").write_text("do not stage\n", encoding="utf-8")
    expected_parent = git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )

    commit_oid = commit_signoffs(repository.work, paths, CARD_ID)

    assert set(
        git_stdout(
            repository.work,
            repository.environment,
            "show",
            "--pretty=format:",
            "--name-only",
            commit_oid,
        ).splitlines()
    ) == set(paths)
    assert git_stdout(
        repository.work,
        repository.environment,
        "show",
        "-s",
        "--format=%P",
        commit_oid,
    ) == expected_parent
    assert (repository.work / "unrelated.txt").exists()
    assert "unrelated.txt" in nul_paths(
        repository.work,
        repository.environment,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )


def test_signoff_commit_rejects_content_replaced_after_transaction_manifest(
    repository: ApprovalGitFixture,
) -> None:
    signoff_root = repository.work / "harness" / "signoffs"
    signoff_root.mkdir(parents=True)
    paths = tuple(
        sorted(
            (
                "harness/signoffs/signoff_governance_v2.json",
                "harness/signoffs/signoff_current_phase_v1.json",
            )
        )
    )
    for relative in paths:
        (repository.work / relative).write_text(
            json.dumps({"reviewed": relative}) + "\n", encoding="utf-8"
        )
    expected_manifest = tuple(
        SourceManifestEntry(
            path=relative,
            status="untracked",
            mode="100644",
            sha256=sha256_file(repository.work / relative),
        )
        for relative in paths
    )
    expected_parent = git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    )
    (repository.work / paths[0]).write_text(
        '{"reviewed":"replacement"}\n', encoding="utf-8"
    )

    with pytest.raises(GitApprovalError, match="signoff|staged|blob|sha|manifest"):
        commit_signoffs(
            repository.work,
            paths,
            CARD_ID,
            expected_parent_oid=expected_parent,
            expected_manifest=expected_manifest,
        )

    assert git_stdout(
        repository.work, repository.environment, "rev-parse", "HEAD"
    ) == expected_parent


def test_clean_worktree_runs_callback_and_removes_only_its_worktree(
    repository: ApprovalGitFixture,
) -> None:
    source_oid = git_stdout(repository.work, repository.environment, "rev-parse", "HEAD")
    before = git_stdout(
        repository.work, repository.environment, "worktree", "list", "--porcelain"
    )
    observed: list[Path] = []

    def verify(clean_root: Path) -> str:
        observed.append(clean_root)
        assert clean_root != repository.work
        assert git_stdout(clean_root, repository.environment, "rev-parse", "HEAD") == source_oid
        assert git_stdout(clean_root, repository.environment, "status", "--porcelain") == ""
        return "verified"

    result = temporary_clean_worktree(repository.work, source_oid, verify)

    assert result == "verified"
    assert len(observed) == 1
    assert not observed[0].exists()
    assert git_stdout(
        repository.work, repository.environment, "worktree", "list", "--porcelain"
    ) == before


def test_clean_worktree_is_removed_when_callback_fails(
    repository: ApprovalGitFixture,
) -> None:
    source_oid = git_stdout(repository.work, repository.environment, "rev-parse", "HEAD")
    observed: list[Path] = []

    def fail(clean_root: Path) -> None:
        observed.append(clean_root)
        raise RuntimeError("verification failed")

    with pytest.raises(RuntimeError, match="verification failed"):
        temporary_clean_worktree(repository.work, source_oid, fail)

    assert len(observed) == 1
    assert not observed[0].exists()
    assert str(observed[0]) not in git_stdout(
        repository.work, repository.environment, "worktree", "list", "--porcelain"
    )


def test_post_checkout_hook_added_at_worktree_boundary_cannot_execute(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_oid = git_stdout(repository.work, repository.environment, "rev-parse", "HEAD")
    marker = repository.work.parent / "post-checkout-ran"
    real_run_git = git_backend.run_git
    installed: list[bool] = []

    def install_hook_before_worktree_add(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments[:2] == ("worktree", "add") and not installed:
            hook = repository.work / ".git" / "hooks" / "post-checkout"
            hook.parent.mkdir(parents=True, exist_ok=True)
            hook.write_text(
                f"#!/bin/sh\nprintf ran > {marker}\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)
            installed.append(True)
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", install_hook_before_worktree_add)

    result = temporary_clean_worktree(
        repository.work,
        source_oid,
        lambda clean_root: clean_root.name,
    )

    assert result == "checkout"
    assert installed == [True]
    assert not marker.exists()


@pytest.mark.parametrize("filter_key", ["smudge", "process"])
def test_filter_added_at_worktree_boundary_cannot_execute_during_materialization(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
    filter_key: str,
) -> None:
    (repository.work / "benchmark").mkdir()
    (repository.work / ".gitattributes").write_text(
        "benchmark/*.payload filter=hostile\n",
        encoding="utf-8",
    )
    payload = repository.work / "benchmark" / "checkout.payload"
    payload.write_bytes(b"exact committed payload\n")
    source_oid = commit_all(
        repository,
        repository.work,
        "tracked checkout payload",
        [".gitattributes", "benchmark/checkout.payload"],
    )
    marker = repository.work.parent / f"late-{filter_key}-ran"
    command = (
        f"sh -c 'touch {marker}; cat'"
        if filter_key == "smudge"
        else f"sh -c 'touch {marker}; exit 1'"
    )
    real_run_git = git_backend.run_git
    installed: list[bool] = []
    observed: list[Path] = []

    def install_filter_before_worktree_add(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments[:2] == ("worktree", "add") and not installed:
            run_git(
                repository.work,
                "config",
                "--local",
                f"filter.hostile.{filter_key}",
                command,
                environment=repository.environment,
            )
            installed.append(True)
        return real_run_git(root, *arguments, **kwargs)

    def inspect_checkout(clean_root: Path) -> bytes:
        observed.append(clean_root)
        assert (clean_root / ".git").is_file()
        return (clean_root / "benchmark" / "checkout.payload").read_bytes()

    monkeypatch.setattr(
        git_backend,
        "run_git",
        install_filter_before_worktree_add,
    )

    result = temporary_clean_worktree(
        repository.work,
        source_oid,
        inspect_checkout,
    )

    assert result == b"exact committed payload\n"
    assert installed == [True]
    assert len(observed) == 1
    assert not observed[0].exists()
    assert not marker.exists()


def test_git_backend_facade_exposes_the_transaction_contract(
    repository: ApprovalGitFixture,
) -> None:
    backend = GitBackend(repository.work)

    assert backend.root == repository.work
    for method_name in (
        "require_main_with_clean_index",
        "reject_active_git_customization",
        "fetch_remote_snapshot",
        "collect_source_manifest",
        "build_proposed_tree",
        "diff_stat",
        "check_worktree_diff",
        "latest_committed_signoffs",
        "stage_exact_manifest",
        "commit_source",
        "commit_tree_oid",
        "current_head_oid",
        "reconcile_card_commit",
        "temporary_clean_worktree",
        "commit_signoffs",
        "push_exact",
    ):
        assert callable(getattr(backend, method_name))


def test_git_backend_facade_delegates_clean_worktree_with_callback(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = GitBackend(repository.work)
    source_oid = "1" * 40
    sentinel = object()
    calls: list[tuple[Path, str, object]] = []

    def callback(clean_root: Path) -> str:
        return clean_root.name

    def fake_temporary_clean_worktree(
        root: Path, commit_oid: str, verifier: object
    ) -> object:
        calls.append((root, commit_oid, verifier))
        return sentinel

    monkeypatch.setattr(
        git_backend, "temporary_clean_worktree", fake_temporary_clean_worktree
    )

    result = backend.temporary_clean_worktree(source_oid, callback)

    assert result is sentinel
    assert calls == [(repository.work, source_oid, callback)]


def test_git_backend_facade_delegates_transaction_support_methods(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = GitBackend(repository.work)
    manifest = collect_source_manifest(repository.work)
    commit_oid = "1" * 40
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def fake_diff_stat(
        root: Path, source_manifest: tuple[object, ...]
    ) -> str:
        calls.append(("diff_stat", (root, source_manifest), {}))
        return "reviewed diff stat"

    def fake_latest_committed_signoffs(
        root: Path,
        *,
        contract_id: str,
        contract_version: str,
        contract_digest: str,
        profile_id: str,
        evaluation_id: str,
        evidence_digest: str,
        role: str,
    ) -> tuple[str, ...]:
        calls.append(
            (
                "latest_committed_signoffs",
                (root,),
                {
                    "contract_id": contract_id,
                    "contract_version": contract_version,
                    "contract_digest": contract_digest,
                    "profile_id": profile_id,
                    "evaluation_id": evaluation_id,
                    "evidence_digest": evidence_digest,
                    "role": role,
                },
            )
        )
        return ("signoff_governance_v2.json",)

    def fake_commit_tree_oid(root: Path, source_commit_oid: str) -> str:
        calls.append(("commit_tree_oid", (root, source_commit_oid), {}))
        return "2" * 40

    monkeypatch.setattr(git_backend, "diff_stat", fake_diff_stat)
    monkeypatch.setattr(
        git_backend,
        "latest_committed_signoffs",
        fake_latest_committed_signoffs,
    )
    monkeypatch.setattr(git_backend, "commit_tree_oid", fake_commit_tree_oid)

    assert backend.diff_stat(manifest) == "reviewed diff stat"
    assert backend.latest_committed_signoffs(
        contract_id="pep_design_project_acceptance",
        contract_version="1.0.0",
        contract_digest="a" * 64,
        profile_id="governance",
        evaluation_id="evaluation_" + "c" * 24,
        evidence_digest="d" * 64,
        role="governance_owner",
    ) == ("signoff_governance_v2.json",)
    assert backend.commit_tree_oid(commit_oid) == "2" * 40
    assert calls == [
        ("diff_stat", (repository.work, manifest), {}),
        (
            "latest_committed_signoffs",
            (repository.work,),
            {
                "contract_id": "pep_design_project_acceptance",
                "contract_version": "1.0.0",
                "contract_digest": "a" * 64,
                "profile_id": "governance",
                "evaluation_id": "evaluation_" + "c" * 24,
                "evidence_digest": "d" * 64,
                "role": "governance_owner",
            },
        ),
        ("commit_tree_oid", (repository.work, commit_oid), {}),
    ]


def test_git_backend_facade_delegates_head_and_card_reconciliation(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = GitBackend(repository.work)
    parent_oid = "1" * 40
    commit_oid = "2" * 40
    tree_oid = "3" * 40
    paths = ("README.md",)
    manifest = (
        SourceManifestEntry(
            path="README.md",
            status="modified",
            mode="100644",
            sha256="4" * 64,
        ),
    )
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def fake_current_head_oid(root: Path) -> str:
        calls.append(("current_head_oid", (root,), {}))
        return parent_oid

    def fake_reconcile_card_commit(
        root: Path,
        expected_parent_oid: str,
        card_id: str,
        expected_paths: tuple[str, ...],
        *,
        expected_tree_oid: str | None = None,
        expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
    ) -> str | None:
        calls.append(
            (
                "reconcile_card_commit",
                (root, expected_parent_oid, card_id, expected_paths),
                {
                    "expected_tree_oid": expected_tree_oid,
                    "expected_manifest": expected_manifest,
                },
            )
        )
        return commit_oid

    monkeypatch.setattr(git_backend, "current_head_oid", fake_current_head_oid)
    monkeypatch.setattr(
        git_backend, "reconcile_card_commit", fake_reconcile_card_commit
    )

    assert backend.current_head_oid() == parent_oid
    assert backend.reconcile_card_commit(
        parent_oid,
        CARD_ID,
        paths,
        expected_tree_oid=tree_oid,
        expected_manifest=manifest,
    ) == commit_oid
    assert calls == [
        ("current_head_oid", (repository.work,), {}),
        (
            "reconcile_card_commit",
            (repository.work, parent_oid, CARD_ID, paths),
            {
                "expected_tree_oid": tree_oid,
                "expected_manifest": manifest,
            },
        ),
    ]


def test_git_backend_facade_support_methods_return_real_repository_results(
    repository: ApprovalGitFixture,
) -> None:
    make_manifest_changes(repository)
    backend = GitBackend(repository.work)
    manifest = backend.collect_source_manifest()

    stat_summary = backend.diff_stat(manifest)

    assert stat_summary == "files=3;insertions=3;deletions=2;binaries=0"
    assert "\n" not in stat_summary
    head_oid = git_stdout(repository.work, repository.environment, "rev-parse", "HEAD")
    assert backend.commit_tree_oid(head_oid) == git_stdout(
        repository.work,
        repository.environment,
        "show",
        "-s",
        "--format=%T",
        head_oid,
    )
    card = create_approval_card(
        {
            "schema_version": "1.0",
            "contract_id": "pep_design_project_acceptance",
            "contract_version": "1.0.0",
            "contract_digest": "a" * 64,
            "evaluator_version": "1.0.0",
            "registry_digest": "b" * 64,
            "evaluation_id": "evaluation_" + "c" * 24,
            "evidence_digest": "d" * 64,
            "reviewer_id": "project_owner",
            "head_oid": head_oid,
            "remote_name": "origin",
            "remote_url": "git@github.com:luvega/pep-design.git",
            "remote_ref": "refs/heads/main",
            "remote_oid": "2" * 40,
            "proposed_tree_oid": backend.build_proposed_tree(manifest),
            "diff_stat": stat_summary,
            "ahead_commits": (),
            "source_manifest": tuple(asdict(entry) for entry in manifest),
            "profiles": (
                {
                    "profile_id": "governance",
                    "gate_result_digest": "6" * 64,
                    "gate_count": 4,
                    "rationale": PROFILE_RATIONALES["governance"],
                    "signoff_filename": "signoff_governance_v1.json",
                    "supersedes": None,
                },
                {
                    "profile_id": "current_phase",
                    "gate_result_digest": "7" * 64,
                    "gate_count": 11,
                    "rationale": PROFILE_RATIONALES["current_phase"],
                    "signoff_filename": "signoff_current_phase_v1.json",
                    "supersedes": None,
                },
            ),
        },
        now=datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc),
        nonce=b"0" * 16,
    )
    assert card.diff_stat == stat_summary


def test_latest_committed_signoffs_prefers_current_context_over_newer_stale(
    repository: ApprovalGitFixture,
) -> None:
    backend = GitBackend(repository.work)
    signoff_root = repository.work / "harness" / "signoffs"
    signoff_root.mkdir(parents=True)

    def write_signoff(filename: str, **overrides: str) -> None:
        payload = {
            "contract_id": "pep_design_project_acceptance",
            "contract_version": "1.0.0",
            "contract_digest": "a" * 64,
            "profile_id": "governance",
            "evaluation_id": "evaluation_" + "c" * 24,
            "evidence_digest": "d" * 64,
            "role": "governance_owner",
        }
        payload.update(overrides)
        (signoff_root / filename).write_text(
            json.dumps(payload) + "\n",
            encoding="utf-8",
        )

    first = "harness/signoffs/signoff_governance_v1.json"
    second = "harness/signoffs/signoff_governance_v2.json"
    wrong_context = "harness/signoffs/signoff_governance_v8.json"
    uncommitted = "harness/signoffs/signoff_governance_v3.json"
    write_signoff(Path(first).name)
    commit_all(repository, repository.work, "first signoff", [first])
    write_signoff(
        Path(second).name,
        evaluation_id="evaluation_" + "e" * 24,
        evidence_digest="f" * 64,
    )
    commit_all(repository, repository.work, "second signoff", [second])
    write_signoff(Path(wrong_context).name, contract_id="other_contract")
    commit_all(repository, repository.work, "wrong context", [wrong_context])
    write_signoff(Path(uncommitted).name)

    assert backend.latest_committed_signoffs(
        contract_id="pep_design_project_acceptance",
        contract_version="1.0.0",
        contract_digest="a" * 64,
        profile_id="governance",
        evaluation_id="evaluation_" + "c" * 24,
        evidence_digest="d" * 64,
        role="governance_owner",
    ) == (
        "signoff_governance_v1.json",
        "signoff_governance_v2.json",
    )


def test_latest_committed_signoffs_falls_back_to_newest_stale_context(
    repository: ApprovalGitFixture,
) -> None:
    signoff_root = repository.work / "harness" / "signoffs"
    signoff_root.mkdir(parents=True)
    for version, evaluation_suffix in ((1, "1"), (2, "2")):
        relative = f"harness/signoffs/signoff_current_phase_v{version}.json"
        (repository.work / relative).write_text(
            json.dumps(
                {
                    "contract_id": "pep_design_project_acceptance",
                    "contract_version": "1.0.0",
                    "contract_digest": "a" * 64,
                    "profile_id": "current_phase",
                    "evaluation_id": "evaluation_" + evaluation_suffix * 24,
                    "evidence_digest": evaluation_suffix * 64,
                    "role": "governance_owner",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        commit_all(repository, repository.work, f"stale signoff {version}", [relative])

    assert GitBackend(repository.work).latest_committed_signoffs(
        contract_id="pep_design_project_acceptance",
        contract_version="1.0.0",
        contract_digest="b" * 64,
        profile_id="current_phase",
        evaluation_id="evaluation_" + "c" * 24,
        evidence_digest="d" * 64,
        role="governance_owner",
    ) == (
        "signoff_current_phase_v2.json",
        "signoff_current_phase_v1.json",
    )


def test_latest_committed_signoffs_keeps_malformed_candidate_fail_closed(
    repository: ApprovalGitFixture,
) -> None:
    relative = "harness/signoffs/signoff_current_phase_v1.json"
    path = repository.work / relative
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")
    commit_all(repository, repository.work, "malformed signoff", [relative])

    with pytest.raises(GitApprovalError, match="valid JSON|signoff"):
        GitBackend(repository.work).latest_committed_signoffs(
            contract_id="pep_design_project_acceptance",
            contract_version="1.0.0",
            contract_digest="a" * 64,
            profile_id="current_phase",
            evaluation_id="evaluation_" + "c" * 24,
            evidence_digest="d" * 64,
            role="governance_owner",
        )


def test_push_uses_one_explicit_refspec_exact_lease_and_confirms_remote(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = remote_snapshot(repository)
    (repository.work / "local.txt").write_text("push me\n", encoding="utf-8")
    final_oid = commit_all(repository, repository.work, "local", ["local.txt"])
    calls: list[tuple[str, ...]] = []
    real_run_git = git_backend.run_git

    def recording_run_git(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(arguments))
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", recording_run_git)

    pushed_oid = push_exact(repository.work, final_oid, snapshot)

    assert pushed_oid == final_oid
    send_call = (
        "send-pack",
        "--receive-pack=git-receive-pack",
        f"--force-with-lease=refs/heads/main:{snapshot.oid}",
        str(repository.remote),
        f"{final_oid}:refs/heads/main",
    )
    confirmation_call = (
        "fetch-pack",
        "--no-progress",
        "--upload-pack=git-upload-pack",
        str(repository.remote),
        "refs/heads/main",
    )
    assert send_call in calls
    assert calls.count(confirmation_call) == 2
    assert calls.index(send_call) < max(
        index for index, call in enumerate(calls) if call == confirmation_call
    )
    assert all(argument != "--force" for call in calls for argument in call)
    assert not send_call[-1].startswith("+")
    assert git_stdout(
        repository.remote, repository.environment, "rev-parse", "refs/heads/main"
    ) == final_oid


def test_fetch_uses_reviewed_url_when_remote_config_mutates_after_validation(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moved_oid = advance_remote(repository)
    run_git(
        repository.work,
        "fetch",
        str(repository.remote),
        "refs/heads/main",
        environment=repository.environment,
    )
    run_git(
        repository.work,
        "update-ref",
        "refs/heads/main",
        moved_oid,
        environment=repository.environment,
    )
    redirected_remote = repository.remote.parent / "redirected-fetch.git"
    run_git(
        repository.remote.parent,
        "init",
        "--bare",
        "--initial-branch=main",
        f"--template={repository.template}",
        "--",
        str(redirected_remote),
        environment=repository.environment,
    )
    real_require_urls = git_backend._require_expected_remote_urls
    mutated: list[bool] = []

    def mutate_after_validation(
        root: Path, *, remote_name: str, expected_url: str
    ) -> tuple[str, str]:
        urls = real_require_urls(
            root,
            remote_name=remote_name,
            expected_url=expected_url,
        )
        if not mutated:
            run_git(
                repository.work,
                "config",
                "--local",
                "remote.origin.url",
                str(redirected_remote),
                environment=repository.environment,
            )
            run_git(
                repository.work,
                "config",
                "--local",
                f"url.{redirected_remote}.insteadOf",
                str(repository.remote),
                environment=repository.environment,
            )
            mutated.append(True)
        return urls

    monkeypatch.setattr(
        git_backend,
        "_require_expected_remote_urls",
        mutate_after_validation,
    )

    snapshot = fetch_remote_snapshot(
        repository.work,
        remote_name="origin",
        expected_url=str(repository.remote),
        ref="refs/heads/main",
    )

    assert mutated == [True]
    assert snapshot.fetch_url == str(repository.remote)
    assert snapshot.push_url == str(repository.remote)
    assert snapshot.oid == moved_oid
    assert git_stdout(
        repository.work,
        repository.environment,
        "rev-parse",
        "refs/remotes/origin/main",
    ) == moved_oid


def test_push_uses_receive_time_lease_when_remote_moves_into_final_ancestry(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = remote_snapshot(repository)
    (repository.work / "race.txt").write_text("race\n", encoding="utf-8")
    raced_oid = commit_all(repository, repository.work, "race", ["race.txt"])
    run_git(
        repository.work,
        "push",
        str(repository.remote),
        f"{raced_oid}:refs/heads/race-staging",
        environment=repository.environment,
    )
    (repository.work / "final.txt").write_text("final\n", encoding="utf-8")
    final_oid = commit_all(repository, repository.work, "final", ["final.txt"])
    real_run_git = git_backend.run_git
    raced: list[bool] = []

    def move_remote_at_transport(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments and arguments[0] in {"push", "send-pack"} and not raced:
            run_git(
                repository.remote,
                "update-ref",
                "refs/heads/main",
                raced_oid,
                snapshot.oid,
                environment=repository.environment,
            )
            run_git(
                repository.remote,
                "update-ref",
                "-d",
                "refs/heads/race-staging",
                raced_oid,
                environment=repository.environment,
            )
            raced.append(True)
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", move_remote_at_transport)

    with pytest.raises(GitApprovalError, match="lease|remote|moved|stale|reject"):
        push_exact(repository.work, final_oid, snapshot)

    assert raced == [True]
    assert git_stdout(
        repository.remote,
        repository.environment,
        "rev-parse",
        "refs/heads/main",
    ) == raced_oid
    assert git_stdout(
        repository.work,
        repository.environment,
        "rev-parse",
        "HEAD",
    ) == final_oid


def test_push_bypasses_hook_and_redirect_config_added_after_last_fetch(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = remote_snapshot(repository)
    (repository.work / "local.txt").write_text("push me safely\n", encoding="utf-8")
    final_oid = commit_all(repository, repository.work, "local", ["local.txt"])
    redirected_remote = repository.remote.parent / "redirected-push.git"
    run_git(
        repository.remote.parent,
        "init",
        "--bare",
        "--initial-branch=main",
        f"--template={repository.template}",
        "--",
        str(redirected_remote),
        environment=repository.environment,
    )
    hook_marker = repository.remote.parent / "pre-push-ran"
    real_run_git = git_backend.run_git
    mutated: list[bool] = []

    def mutate_after_fetch(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        completed = real_run_git(root, *arguments, **kwargs)
        if arguments and arguments[0] in {"fetch", "fetch-pack"} and not mutated:
            hook = repository.work / ".git" / "hooks" / "pre-push"
            hook.parent.mkdir(parents=True, exist_ok=True)
            hook.write_text(
                f"#!/bin/sh\nprintf ran > {hook_marker}\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)
            run_git(
                repository.work,
                "config",
                "--local",
                "remote.origin.pushurl",
                str(redirected_remote),
                environment=repository.environment,
            )
            run_git(
                repository.work,
                "config",
                "--local",
                f"url.{redirected_remote}.pushInsteadOf",
                str(repository.remote),
                environment=repository.environment,
            )
            run_git(
                repository.work,
                "config",
                "--local",
                "core.sshCommand",
                "false malicious-ssh-command",
                environment=repository.environment,
            )
            mutated.append(True)
        return completed

    monkeypatch.setattr(git_backend, "run_git", mutate_after_fetch)

    pushed_oid = push_exact(repository.work, final_oid, snapshot)

    assert pushed_oid == final_oid
    assert mutated == [True]
    assert not hook_marker.exists()
    assert git_stdout(
        repository.remote,
        repository.environment,
        "rev-parse",
        "refs/heads/main",
    ) == final_oid
    redirected_ref = run_git(
        redirected_remote,
        "rev-parse",
        "--verify",
        "refs/heads/main",
        environment=repository.environment,
        check=False,
    )
    assert redirected_ref.returncode != 0


def test_remote_movement_fails_before_push_and_preserves_local_commit(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = remote_snapshot(repository)
    (repository.work / "local.txt").write_text("local\n", encoding="utf-8")
    local_oid = commit_all(repository, repository.work, "local", ["local.txt"])
    moved_oid = advance_remote(repository)
    calls: list[tuple[str, ...]] = []
    real_run_git = git_backend.run_git

    def recording_run_git(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(arguments))
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", recording_run_git)

    with pytest.raises(GitApprovalError, match="remote|moved|changed|oid"):
        push_exact(repository.work, local_oid, snapshot)

    assert not any(call and call[0] == "push" for call in calls)
    assert git_stdout(repository.work, repository.environment, "rev-parse", "HEAD") == local_oid
    assert git_stdout(
        repository.remote, repository.environment, "rev-parse", "refs/heads/main"
    ) == moved_oid


def test_non_fast_forward_push_fails_without_changing_remote_or_local_history(
    repository: ApprovalGitFixture,
) -> None:
    snapshot = remote_snapshot(repository)
    (repository.work / "local.txt").write_text("local\n", encoding="utf-8")
    local_oid = commit_all(repository, repository.work, "local", ["local.txt"])
    moved_oid = advance_remote(repository)
    current_remote = replace(snapshot, oid=moved_oid)

    with pytest.raises(
        GitApprovalError, match="fast.forward|non.fast|ancestor|rejected|fetch first"
    ):
        push_exact(repository.work, local_oid, current_remote)

    assert git_stdout(repository.work, repository.environment, "rev-parse", "HEAD") == local_oid
    assert git_stdout(
        repository.remote, repository.environment, "rev-parse", "refs/heads/main"
    ) == moved_oid


@pytest.mark.parametrize("spoof_kind", ["replace", "graft"])
def test_local_history_spoof_cannot_turn_unrelated_push_into_fast_forward(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
    spoof_kind: str,
) -> None:
    snapshot = remote_snapshot(repository)
    tree_oid = git_stdout(
        repository.work,
        repository.environment,
        "show",
        "-s",
        "--format=%T",
        "HEAD",
    )
    unrelated_oid = git_stdout(
        repository.work,
        repository.environment,
        "commit-tree",
        tree_oid,
        "-m",
        "unrelated root",
    )
    run_git(
        repository.work,
        "update-ref",
        "refs/heads/main",
        unrelated_oid,
        snapshot.head_oid,
        environment=repository.environment,
    )
    if spoof_kind == "replace":
        fake_descendant_oid = git_stdout(
            repository.work,
            repository.environment,
            "commit-tree",
            tree_oid,
            "-p",
            snapshot.oid,
            "-m",
            "replacement descendant",
        )
        run_git(
            repository.work,
            "replace",
            unrelated_oid,
            fake_descendant_oid,
            environment=repository.environment,
        )
    else:
        grafts = repository.work / ".git" / "info" / "grafts"
        grafts.parent.mkdir(parents=True, exist_ok=True)
        grafts.write_text(
            f"{unrelated_oid} {snapshot.oid}\n",
            encoding="ascii",
        )

    spoofed = run_git(
        repository.work,
        "merge-base",
        "--is-ancestor",
        snapshot.oid,
        unrelated_oid,
        environment=repository.environment,
        check=False,
    )
    assert spoofed.returncode == 0
    calls: list[tuple[str, ...]] = []
    real_run_git = git_backend.run_git

    def recording_run_git(
        root: Path, *arguments: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(arguments))
        return real_run_git(root, *arguments, **kwargs)

    monkeypatch.setattr(git_backend, "run_git", recording_run_git)

    with pytest.raises(GitApprovalError, match="ancestor|diverg|fast.forward|remote"):
        push_exact(repository.work, unrelated_oid, snapshot)

    assert not any(call and call[0] == "send-pack" for call in calls)
    assert git_stdout(
        repository.remote,
        repository.environment,
        "rev-parse",
        "refs/heads/main",
    ) == snapshot.oid


def test_git_errors_are_redacted_before_they_are_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "ghp_super_secret_value"

    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["git"],
            returncode=128,
            stdout="",
            stderr=(
                f"fatal: https://reviewer:{secret}@example.test/repo token={secret} "
                f"GIT_SSH_COMMAND=ssh-with-{secret}"
            ),
        )

    monkeypatch.setattr(git_backend.subprocess, "run", fail)

    with pytest.raises(GitApprovalError) as captured:
        git_backend.run_git(tmp_path, "status")

    message = str(captured.value)
    assert secret not in message
    assert "reviewer:" not in message


@pytest.mark.parametrize(
    ("raw", "secret"),
    [
        ("fatal: Authorization: Bearer bearer-secret-value", "bearer-secret-value"),
        ("fatal: Authorization: Basic dXNlcjpzdXBlcnNlY3JldA==", "dXNlcjpzdXBlcnNlY3JldA=="),
        ("fatal: access_token='access-secret-value'", "access-secret-value"),
        ('fatal: oauth="oauth-secret-value"', "oauth-secret-value"),
        ("fatal: password=password-secret-value", "password-secret-value"),
        ("fatal: token=token-secret-value", "token-secret-value"),
        (
            "GIT_SSH_COMMAND='ssh -i /private/secret-key -o BatchMode=yes'",
            "/private/secret-key",
        ),
        ("GIT_ASKPASS=/private/askpass-secret --prompt", "/private/askpass-secret"),
        ("SSH_ASKPASS=\"/private/ssh askpass secret\"", "/private/ssh askpass secret"),
    ],
)
def test_git_error_redaction_covers_auth_and_complete_git_command_values(
    raw: str, secret: str
) -> None:
    redacted = git_backend.redact_git_error(raw)

    assert secret not in redacted
    assert "[REDACTED]" in redacted


def test_runner_removes_ambient_git_environment_and_fixes_safe_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hostile = {
        "GIT_DIR": "/hostile/git-dir",
        "GIT_WORK_TREE": "/hostile/work-tree",
        "GIT_SSH_COMMAND": "ssh -i /hostile/key",
        "GIT_ASKPASS": "/hostile/askpass",
        "SSH_ASKPASS": "/hostile/ssh-askpass",
        "GIT_CONFIG_GLOBAL": "/hostile/global-config",
        "GIT_INDEX_FILE": "/hostile/index",
        "GIT_NO_REPLACE_OBJECTS": "0",
    }
    for key, value in hostile.items():
        monkeypatch.setenv(key, value)
    captured: dict[str, object] = {}

    def complete(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(git_backend.subprocess, "run", complete)
    reviewed_index = tmp_path / "reviewed-index"

    git_backend.run_git(
        tmp_path,
        "status",
        env={"GIT_INDEX_FILE": str(reviewed_index)},
    )

    environment = captured["env"]
    assert isinstance(environment, dict)
    assert captured["argv"] == [
        "git",
        "--no-replace-objects",
        "-c",
        "commit.gpgSign=false",
        "-c",
        "tag.gpgSign=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.attributesFile=/dev/null",
        "status",
    ]
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_ATTR_NOSYSTEM"] == "1"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_LITERAL_PATHSPECS"] == "1"
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["GIT_INDEX_FILE"] == str(reviewed_index)
    for key in hostile:
        if key not in {
            "GIT_INDEX_FILE",
            "GIT_CONFIG_GLOBAL",
            "GIT_NO_REPLACE_OBJECTS",
        }:
            assert key not in environment


def test_runner_rejects_every_environment_override_except_index(
    tmp_path: Path,
) -> None:
    with pytest.raises(GitApprovalError, match="environment|GIT_INDEX_FILE"):
        git_backend.run_git(
            tmp_path,
            "status",
            env={"GIT_WORK_TREE": str(tmp_path)},
        )


def test_transport_runs_with_an_ephemeral_git_dir_and_real_object_store(
    repository: ApprovalGitFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_git(
        repository.work,
        "config",
        "--local",
        "transport.auditMarker",
        "must-not-be-loaded",
        environment=repository.environment,
    )
    real_subprocess_run = git_backend.subprocess.run
    observed: list[Path] = []
    actual_objects = Path(
        git_stdout(
            repository.work,
            repository.environment,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "objects",
        )
    ).resolve()

    def inspect_transport(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if "fetch-pack" in argv or "send-pack" in argv:
            environment = kwargs["env"]
            assert isinstance(environment, dict)
            transport_git_dir = Path(environment["GIT_DIR"])
            assert transport_git_dir.is_dir()
            assert transport_git_dir != repository.work / ".git"
            assert (transport_git_dir / "objects").resolve() == actual_objects
            config = (transport_git_dir / "config").read_text(encoding="utf-8")
            assert "auditMarker" not in config
            assert "must-not-be-loaded" not in config
            observed.append(transport_git_dir)
        return real_subprocess_run(argv, **kwargs)

    monkeypatch.setattr(git_backend.subprocess, "run", inspect_transport)

    snapshot = remote_snapshot(repository)

    assert snapshot.oid == git_stdout(
        repository.remote,
        repository.environment,
        "rev-parse",
        "refs/heads/main",
    )
    assert len(observed) == 1
    assert not observed[0].exists()


def test_ambient_git_dir_and_work_tree_cannot_redirect_real_git_command(
    repository: ApprovalGitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_DIR", str(repository.remote))
    monkeypatch.setenv("GIT_WORK_TREE", str(repository.peer))
    monkeypatch.setenv("GIT_SSH_COMMAND", "false ambient-ssh-must-not-run")
    monkeypatch.setenv("GIT_ASKPASS", "/ambient/askpass-must-not-run")
    monkeypatch.setenv("SSH_ASKPASS", "/ambient/ssh-askpass-must-not-run")

    assert git_backend.run_git(
        repository.work, "rev-parse", "--show-toplevel"
    ).stdout.strip() == str(repository.work)


def test_optional_config_only_treats_exit_one_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = iter(
        (
            subprocess.CompletedProcess(["git"], 1, "", ""),
            subprocess.CompletedProcess(["git"], 2, "", "fatal: corrupt config"),
        )
    )

    def complete(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return next(results)

    monkeypatch.setattr(git_backend.subprocess, "run", complete)

    assert run_git_optional(tmp_path, "config", "--get", "missing.key") is None
    with pytest.raises(GitApprovalError, match="corrupt config"):
        run_git_optional(tmp_path, "config", "--get", "broken.key")


def test_journal_transitions_persist_identity_and_are_byte_idempotent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "dialog_transactions" / f"{CARD_ID}.json"
    prepared = create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    assert prepared.state is TransactionState.PREPARED

    approved = transition_journal(
        path,
        expected_state=TransactionState.PREPARED,
        new_state=TransactionState.APPROVED,
        reviewed_at=REVIEWED_AT,
        approval_event_id=APPROVAL_EVENT_ID,
    )
    assert approved.reviewed_at == REVIEWED_AT
    assert approved.approval_event_id == APPROVAL_EVENT_ID

    source_oid = "1" * 40
    committed = transition_journal(
        path,
        expected_state=TransactionState.APPROVED,
        new_state=TransactionState.SOURCE_COMMITTED,
        source_commit_oid=source_oid,
    )
    first_bytes = path.read_bytes()
    repeated = transition_journal(
        path,
        expected_state=TransactionState.APPROVED,
        new_state=TransactionState.SOURCE_COMMITTED,
        source_commit_oid=source_oid,
    )

    assert repeated == committed
    assert path.read_bytes() == first_bytes
    loaded = load_journal(path)
    assert loaded.card_id == CARD_ID
    assert loaded.card_sha256 == CARD_SHA256
    assert loaded.approval_event_id == APPROVAL_EVENT_ID
    assert loaded.source_commit_oid == source_oid


def test_journal_transition_fsyncs_a_same_directory_temp_before_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "dialog_transactions" / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    events: list[tuple[str, object, object]] = []
    real_fsync = approval_journal.os.fsync
    real_flock = approval_journal.fcntl.flock
    real_replace = approval_journal.os.replace

    def spy_fsync(file_descriptor: int) -> None:
        is_regular_file = stat.S_ISREG(os.fstat(file_descriptor).st_mode)
        events.append(("fsync", file_descriptor, is_regular_file))
        real_fsync(file_descriptor)

    def spy_flock(file_descriptor: int, operation: int) -> None:
        events.append(("flock", file_descriptor, operation))
        real_flock(file_descriptor, operation)

    def spy_replace(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert src_dir_fd is not None
        assert dst_dir_fd is not None
        assert os.fstat(src_dir_fd) == os.fstat(dst_dir_fd)
        source_path = path.parent / Path(source)
        target_path = path.parent / Path(target)
        assert source_path.parent == path.parent
        assert target_path == path
        assert source_path != path
        assert source_path.is_file()
        json.loads(source_path.read_text(encoding="utf-8"))
        events.append(("replace", source_path, target_path))
        real_replace(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(approval_journal.os, "fsync", spy_fsync)
    monkeypatch.setattr(approval_journal.fcntl, "flock", spy_flock)
    monkeypatch.setattr(approval_journal.os, "replace", spy_replace)

    transition_journal(
        path,
        expected_state=TransactionState.PREPARED,
        new_state=TransactionState.APPROVED,
        reviewed_at=REVIEWED_AT,
        approval_event_id=APPROVAL_EVENT_ID,
    )

    replace_index = next(
        index for index, event in enumerate(events) if event[0] == "replace"
    )
    assert any(
        event[0] == "fsync" and event[2] is True
        for event in events[:replace_index]
    )
    lock_index = next(
        index
        for index, event in enumerate(events)
        if event[0] == "flock" and event[2] == approval_journal.fcntl.LOCK_EX
    )
    unlock_index = next(
        index
        for index, event in enumerate(events)
        if event[0] == "flock" and event[2] == approval_journal.fcntl.LOCK_UN
    )
    assert lock_index < replace_index < unlock_index
    assert set(path.parent.iterdir()) == {path}


def test_journal_replace_failure_preserves_prior_json_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "dialog_transactions" / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    original = path.read_bytes()
    replace_sources: list[Path] = []

    def fail_replace(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert src_dir_fd is not None
        assert dst_dir_fd is not None
        assert os.fstat(src_dir_fd) == os.fstat(dst_dir_fd)
        source_path = path.parent / Path(source)
        assert source_path.parent == path.parent
        assert path.parent / Path(target) == path
        replace_sources.append(source_path)
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(approval_journal.os, "replace", fail_replace)

    with pytest.raises((JournalError, OSError), match="replace|atomic|simulated"):
        transition_journal(
            path,
            expected_state=TransactionState.PREPARED,
            new_state=TransactionState.APPROVED,
            reviewed_at=REVIEWED_AT,
            approval_event_id=APPROVAL_EVENT_ID,
        )

    assert len(replace_sources) == 1
    assert path.read_bytes() == original
    assert json.loads(path.read_text(encoding="utf-8"))["state"] == "prepared"
    assert set(path.parent.iterdir()) == {path}


def test_journal_rejects_skipped_or_conflicting_transitions(tmp_path: Path) -> None:
    path = tmp_path / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)

    with pytest.raises(JournalError, match="transition|state"):
        transition_journal(
            path,
            expected_state=TransactionState.PREPARED,
            new_state=TransactionState.VERIFIED,
        )

    transition_journal(
        path,
        expected_state=TransactionState.PREPARED,
        new_state=TransactionState.APPROVED,
        reviewed_at=REVIEWED_AT,
        approval_event_id=APPROVAL_EVENT_ID,
    )
    transition_journal(
        path,
        expected_state=TransactionState.APPROVED,
        new_state=TransactionState.SOURCE_COMMITTED,
        source_commit_oid="1" * 40,
    )
    with pytest.raises(JournalError, match="conflict|state|oid"):
        transition_journal(
            path,
            expected_state=TransactionState.APPROVED,
            new_state=TransactionState.SOURCE_COMMITTED,
            source_commit_oid="2" * 40,
        )


def test_journal_failure_state_keeps_final_oid_for_push_resume(tmp_path: Path) -> None:
    path = tmp_path / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    transition_journal(
        path,
        expected_state=TransactionState.PREPARED,
        new_state=TransactionState.APPROVED,
        reviewed_at=REVIEWED_AT,
        approval_event_id=APPROVAL_EVENT_ID,
    )
    transition_journal(
        path,
        expected_state=TransactionState.APPROVED,
        new_state=TransactionState.SOURCE_COMMITTED,
        source_commit_oid="1" * 40,
    )
    transition_journal(
        path,
        expected_state=TransactionState.SOURCE_COMMITTED,
        new_state=TransactionState.SIGNOFFS_COMMITTED,
        signoff_commit_oid="2" * 40,
        final_commit_oid="2" * 40,
    )
    failed = transition_journal(
        path,
        expected_state=TransactionState.SIGNOFFS_COMMITTED,
        new_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        failure_code="remote_moved",
    )

    assert failed.final_commit_oid == "2" * 40
    assert failed.signoff_commit_oid == "2" * 40
    assert failed.failure_code == "remote_moved"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["state"] == "local_committed_push_failed"
    assert raw["final_commit_oid"] == "2" * 40


@pytest.mark.parametrize("with_final_oid", [False, True])
def test_journal_recovery_clears_failure_code_explicitly(
    tmp_path: Path, with_final_oid: bool
) -> None:
    path = tmp_path / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    transition_journal(
        path,
        expected_state=TransactionState.PREPARED,
        new_state=TransactionState.APPROVED,
        reviewed_at=REVIEWED_AT,
        approval_event_id=APPROVAL_EVENT_ID,
    )
    transition_journal(
        path,
        expected_state=TransactionState.APPROVED,
        new_state=TransactionState.SOURCE_COMMITTED,
        source_commit_oid="1" * 40,
    )
    if with_final_oid:
        transition_journal(
            path,
            expected_state=TransactionState.SOURCE_COMMITTED,
            new_state=TransactionState.SIGNOFFS_COMMITTED,
            signoff_commit_oid="2" * 40,
            final_commit_oid="2" * 40,
        )
        failed_from = TransactionState.SIGNOFFS_COMMITTED
    else:
        failed_from = TransactionState.SOURCE_COMMITTED
    transition_journal(
        path,
        expected_state=failed_from,
        new_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        failure_code="injected_failure",
    )

    recovered = transition_journal(
        path,
        expected_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        new_state=(
            TransactionState.SIGNOFFS_COMMITTED
            if with_final_oid
            else TransactionState.SOURCE_COMMITTED
        ),
        signoff_commit_oid="2" * 40 if with_final_oid else None,
        final_commit_oid="2" * 40 if with_final_oid else None,
        failure_code=None,
    )

    assert recovered.failure_code is None
    assert load_journal(path).failure_code is None


def test_concurrent_journal_create_publishes_once_without_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "dialog_transactions" / f"{CARD_ID}.json"
    barrier = Barrier(2)
    replace_barrier = Barrier(2)
    real_replace = approval_journal.os.replace

    def synchronize_unsafe_replace(*args: object, **kwargs: object) -> None:
        replace_barrier.wait(timeout=5)
        real_replace(*args, **kwargs)

    monkeypatch.setattr(approval_journal.os, "replace", synchronize_unsafe_replace)

    def create() -> object:
        barrier.wait(timeout=5)
        return create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create) for _ in range(2)]
        outcomes: list[object] = []
        errors: list[BaseException] = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=10))
            except BaseException as exc:
                errors.append(exc)

    assert len(outcomes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], JournalError)
    assert "exist" in str(errors[0]).lower()
    assert load_journal(path) == outcomes[0]
    assert set(path.parent.iterdir()) == {path}


def test_concurrent_distinct_approval_transitions_have_one_cas_winner(
    tmp_path: Path,
) -> None:
    path = tmp_path / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    barrier = Barrier(2)
    identities = (
        ("2026-07-10T12:00:00+00:00", "approval_event_" + "1" * 24),
        ("2026-07-10T12:00:01+00:00", "approval_event_" + "2" * 24),
    )

    def approve(identity: tuple[str, str]) -> object:
        barrier.wait(timeout=5)
        return transition_journal(
            path,
            expected_state=TransactionState.PREPARED,
            new_state=TransactionState.APPROVED,
            reviewed_at=identity[0],
            approval_event_id=identity[1],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(approve, identity) for identity in identities]
        outcomes: list[object] = []
        errors: list[BaseException] = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=10))
            except BaseException as exc:
                errors.append(exc)

    assert len(outcomes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], JournalError)
    assert "conflict" in str(errors[0]).lower()
    assert load_journal(path) == outcomes[0]


def test_journal_load_rejects_symlink_without_following_it(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    path = tmp_path / f"{CARD_ID}.json"
    path.symlink_to(target)

    with pytest.raises(JournalError, match="symlink|regular|nofollow|load"):
        load_journal(path)


def test_journal_load_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    path = tmp_path / f"{CARD_ID}.json"
    os.mkfifo(path)

    with pytest.raises(JournalError, match="regular|journal"):
        load_journal(path)


def test_journal_load_rejects_oversize_content(tmp_path: Path) -> None:
    path = tmp_path / f"{CARD_ID}.json"
    path.write_bytes(b"{" + b" " * (1024 * 1024) + b"}")

    with pytest.raises(JournalError, match="large|size|bytes"):
        load_journal(path)


def test_journal_load_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    raw = path.read_text(encoding="utf-8")
    path.write_text(
        raw.replace('"state":"prepared"', '"state":"prepared","state":"prepared"'),
        encoding="utf-8",
    )

    with pytest.raises(JournalError, match="duplicate|state|JSON"):
        load_journal(path)
