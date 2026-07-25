from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.approval.cards import create_approval_card
from harness.approval.git_backend import GitApprovalError, GitExecutionError
from harness.approval.journal import (
    TransactionState,
    create_journal,
    transition_journal,
)
from harness.approval.models import ApprovalCard, ApprovalError
from harness.approval.render import render_approval_card
import harness.approval.service as approval_service
import harness.domains.repository as repository_domain
import harness.engine.bounded_process as bounded_process
from harness.approval.service import (
    ApprovalOutcome,
    PreparedReview,
    VerificationExecutionError,
)
from harness.engine import cli
from harness.engine.bounded_process import BoundedProcessError
from harness.engine.models import (
    EvaluationResult,
    GateResult,
    GateVerdict,
    HarnessStatus,
    ProfileResult,
    ProjectVerdict,
    Severity,
)
from harness.engine.report import _git_workspace_paths


CARD_ID = "approval_" + "a" * 24
CARD_SHA256 = "b" * 64
NOW = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
GOVERNANCE_RATIONALE = (
    "仅批准 contract/registry/migration/validator 的治理完整性；不豁免任何失败 "
    "gate，也不批准 release_checkpoint 或 full_project。"
)
CURRENT_PHASE_RATIONALE = (
    "接受 v0.34 的诚实边界：7 条主运行候选均已解析，其中 6 条通过 QC；"
    "PepGLAD 因混合手性失败；没有 scoring、ranking、frozen target 或 wet-lab 验证。"
)


def deterministic_card() -> ApprovalCard:
    return create_approval_card(
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
            "head_oid": "1" * 40,
            "remote_name": "origin",
            "remote_url": "git@github.com:luvega/pep-design.git",
            "remote_ref": "refs/heads/main",
            "remote_oid": "2" * 40,
            "proposed_tree_oid": "3" * 40,
            "diff_stat": "2 files changed, 8 insertions(+), 1 deletion(-)",
            "ahead_commits": ("4" * 40, "5" * 40),
            "source_manifest": (
                {
                    "path": "README.md",
                    "status": "modified",
                    "mode": "100644",
                    "sha256": "e" * 64,
                },
                {
                    "path": "docs/retired.txt",
                    "status": "deleted",
                    "mode": None,
                    "sha256": None,
                },
            ),
            "profiles": (
                {
                    "profile_id": "governance",
                    "gate_result_digest": "6" * 64,
                    "gate_count": 4,
                    "rationale": GOVERNANCE_RATIONALE,
                    "signoff_filename": "signoff_governance_v2.json",
                    "supersedes": "signoff_governance_v1.json",
                },
                {
                    "profile_id": "current_phase",
                    "gate_result_digest": "7" * 64,
                    "gate_count": 11,
                    "rationale": CURRENT_PHASE_RATIONALE,
                    "signoff_filename": "signoff_current_phase_v1.json",
                    "supersedes": None,
                },
            ),
        },
        now=NOW,
        nonce=b"0" * 16,
    )


def parse(*arguments: str):
    return cli.build_parser().parse_args(arguments)


def assert_parser_error(*arguments: str) -> None:
    with pytest.raises(SystemExit) as caught:
        parse(*arguments)
    assert caught.value.code == 2


def test_prepare_review_parser_accepts_only_exact_bundle_and_push_target() -> None:
    args = parse(
        "prepare-review",
        "--profiles",
        "governance",
        "current_phase",
        "--push-target",
        "origin/main",
    )

    assert tuple(args.profiles) == ("governance", "current_phase")
    assert args.push_target == "origin/main"


@pytest.mark.parametrize(
    "arguments",
    [
        ("--profiles", "governance", "--push-target", "origin/main"),
        (
            "--profiles",
            "current_phase",
            "governance",
            "--push-target",
            "origin/main",
        ),
        (
            "--profiles",
            "governance",
            "release_checkpoint",
            "--push-target",
            "origin/main",
        ),
        (
            "--profiles",
            "governance",
            "full_project",
            "--push-target",
            "origin/main",
        ),
        (
            "--profiles",
            "governance",
            "current_phase",
            "release_checkpoint",
            "--push-target",
            "origin/main",
        ),
        (
            "--profiles",
            "governance",
            "current_phase",
            "--push-target",
            "upstream/main",
        ),
    ],
    ids=(
        "single-profile",
        "reordered",
        "release-profile",
        "full-project-profile",
        "extra-profile",
        "alternate-push-target",
    ),
)
def test_prepare_review_parser_rejects_any_other_scope(
    arguments: tuple[str, ...],
) -> None:
    assert_parser_error("prepare-review", *arguments)


def test_approve_parser_requires_full_binding_and_exact_reviewer() -> None:
    args = parse(
        "approve-card",
        "--card-id",
        CARD_ID,
        "--expected-card-sha256",
        CARD_SHA256,
        "--reviewer-id",
        "project_owner",
    )

    assert args.card_id == CARD_ID
    assert args.expected_card_sha256 == CARD_SHA256
    assert args.reviewer_id == "project_owner"


@pytest.mark.parametrize(
    "arguments",
    [
        (
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
        ),
        ("--card-id", CARD_ID, "--reviewer-id", "project_owner"),
        (
            "--card-id",
            "approval_short",
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
        ),
        (
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256[:24],
            "--reviewer-id",
            "project_owner",
        ),
        (
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256.upper(),
            "--reviewer-id",
            "project_owner",
        ),
        (
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "engineering_reviewer",
        ),
    ],
    ids=(
        "missing-card-id",
        "missing-digest",
        "malformed-card-id",
        "truncated-digest",
        "uppercase-digest",
        "alternate-reviewer",
    ),
)
def test_approve_parser_rejects_unbound_or_alternate_approval(
    arguments: tuple[str, ...],
) -> None:
    assert_parser_error("approve-card", *arguments)


@pytest.mark.parametrize("flag", ["--skip-verification", "--force", "--no-verify"])
@pytest.mark.parametrize("command", ["prepare-review", "approve-card", "resume-push"])
def test_dialog_commands_expose_no_verification_or_force_bypass(
    command: str, flag: str
) -> None:
    base = {
        "prepare-review": (
            "--profiles",
            "governance",
            "current_phase",
            "--push-target",
            "origin/main",
        ),
        "approve-card": (
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
        ),
        "resume-push": ("--card-id", CARD_ID),
    }
    assert_parser_error(command, *base[command], flag)


def test_existing_check_and_render_parser_contract_is_retained() -> None:
    for command in ("check", "render"):
        for profile in (
            "governance",
            "current_phase",
            "release_checkpoint",
            "full_project",
        ):
            args = parse(command, "--profile", profile)
            assert args.command == command
            assert args.profile == profile


def test_rendered_approval_card_contains_every_bound_review_fact() -> None:
    card = deterministic_card()
    manifest_path = f"ops/acceptance/dialog_cards/{card.card_id}.json"

    markdown = render_approval_card(card, card_path=manifest_path)

    for exact_value in (
        card.card_id,
        card.card_sha256,
        card.evaluation_id,
        card.evidence_digest,
        card.contract_digest,
        card.registry_digest,
        card.profiles[0].gate_result_digest,
        card.profiles[1].gate_result_digest,
        card.reviewer_id,
        card.expires_at,
        card.remote_url,
        card.remote_oid,
        card.remote_ref,
        card.ahead_commits[0],
        card.ahead_commits[1],
        card.diff_stat,
        manifest_path,
        GOVERNANCE_RATIONALE,
        CURRENT_PHASE_RATIONALE,
        "signoff_governance_v2.json",
        "signoff_governance_v1.json",
        "signoff_current_phase_v1.json",
    ):
        assert exact_value in markdown

    assert re.search(r"governance[^\n]*\b4\b", markdown, re.IGNORECASE)
    assert re.search(r"current_phase[^\n]*\b11\b", markdown, re.IGNORECASE)
    assert re.search(r"(?:source|文件|路径)[^\n]*\b2\b", markdown, re.IGNORECASE)
    assert re.search(
        r"signoff_current_phase_v1\.json[^\n]*(?:无|首次|null|none)",
        markdown,
        re.IGNORECASE,
    )


def test_rendered_card_states_all_exclusions_and_has_one_final_action_line() -> None:
    card = deterministic_card()
    markdown = render_approval_card(
        card,
        card_path=f"ops/acceptance/dialog_cards/{card.card_id}.json",
    )

    assert "不批准 release_checkpoint 或 full_project" in markdown
    assert "不表示 Benchmark 完成" in markdown
    assert "不授权 clone/download/GPU/generation/scoring/ranking" in markdown

    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    assert lines[-1] == "回复：批准"
    assert [line for line in lines if line.startswith("回复：")] == ["回复：批准"]


@pytest.mark.parametrize(
    "manifest_path",
    [
        "./ops/acceptance/dialog_cards/{card_id}.json",
        "other/dialog_cards/{card_id}.json",
        "/tmp/{card_id}.json",
    ],
)
def test_renderer_requires_the_exact_canonical_manifest_path(
    manifest_path: str,
) -> None:
    card = deterministic_card()

    with pytest.raises(ApprovalError, match="manifest path|canonical|mismatch"):
        render_approval_card(
            card,
            card_path=manifest_path.format(card_id=card.card_id),
        )


def test_renderer_uses_a_safe_code_span_for_embedded_backticks() -> None:
    card = replace(
        deterministic_card(),
        diff_stat="changed `inline` value",
    )

    markdown = render_approval_card(
        card,
        card_path=f"ops/acceptance/dialog_cards/{card.card_id}.json",
    )

    assert "``changed `inline` value``" in markdown


def test_service_canonicalizes_root_before_dependency_and_transaction_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_root = tmp_path / "real"
    real_root.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real_root, target_is_directory=True)
    backend = object()
    verifier = object()
    observed: dict[str, object] = {}
    card = deterministic_card()

    def fake_prepare(
        root: Path,
        *,
        backend: object,
        verifier: object,
        now: datetime,
        nonce: bytes | None,
    ) -> SimpleNamespace:
        observed.update(root=root, backend=backend, verifier=verifier)
        return SimpleNamespace(card=card)

    monkeypatch.setattr(approval_service, "prepare_review", fake_prepare)

    approval_service.prepare_dialog_review(
        alias,
        backend=backend,
        verifier=verifier,
        now=NOW,
        nonce=b"0" * 16,
    )

    assert observed == {
        "root": real_root.resolve(strict=True),
        "backend": backend,
        "verifier": verifier,
    }


def test_prepare_cli_calls_injected_service_once_and_prints_card(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[Path] = []
    markdown = "# 审批卡\n\n回复：批准"

    def fake_prepare(root: Path) -> PreparedReview:
        calls.append(root)
        return PreparedReview(
            card_path=f"ops/acceptance/dialog_cards/{CARD_ID}.json",
            card_id=CARD_ID,
            card_sha256=CARD_SHA256,
            markdown=markdown,
        )

    monkeypatch.setattr(cli, "prepare_dialog_review", fake_prepare)

    result = cli.main(
        [
            "prepare-review",
            "--profiles",
            "governance",
            "current_phase",
            "--push-target",
            "origin/main",
            "--root",
            str(tmp_path),
        ]
    )

    assert result == 0
    assert calls == [tmp_path]
    assert capsys.readouterr().out.strip() == markdown


def test_approve_cli_calls_injected_service_once_with_full_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[Path, str, str, str]] = []

    def fake_approve(
        root: Path,
        *,
        card_id: str,
        expected_card_sha256: str,
        reviewer_id: str,
    ) -> ApprovalOutcome:
        calls.append((root, card_id, expected_card_sha256, reviewer_id))
        return ApprovalOutcome(
            card_id=card_id,
            state="pushed",
            source_commit_oid="1" * 40,
            signoff_commit_oid="2" * 40,
            final_commit_oid="2" * 40,
            remote_oid="2" * 40,
        )

    monkeypatch.setattr(cli, "approve_dialog_card", fake_approve)

    result = cli.main(
        [
            "approve-card",
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
            "--root",
            str(tmp_path),
        ]
    )

    assert result == 0
    assert calls == [(tmp_path, CARD_ID, CARD_SHA256, "project_owner")]
    assert json.loads(capsys.readouterr().out) == {
        "card_id": CARD_ID,
        "final_commit_oid": "2" * 40,
        "remote_oid": "2" * 40,
        "signoff_commit_oid": "2" * 40,
        "source_commit_oid": "1" * 40,
        "state": "pushed",
    }


def test_resume_cli_requires_card_id_and_calls_service_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert_parser_error("resume-push")
    calls: list[tuple[Path, str]] = []

    def fake_resume(root: Path, *, card_id: str) -> ApprovalOutcome:
        calls.append((root, card_id))
        return ApprovalOutcome(
            card_id=card_id,
            state="pushed",
            source_commit_oid="1" * 40,
            signoff_commit_oid="2" * 40,
            final_commit_oid="2" * 40,
            remote_oid="2" * 40,
        )

    monkeypatch.setattr(cli, "resume_dialog_push", fake_resume)

    result = cli.main(
        ["resume-push", "--card-id", CARD_ID, "--root", str(tmp_path)]
    )

    assert result == 0
    assert calls == [(tmp_path, CARD_ID)]
    assert json.loads(capsys.readouterr().out)["state"] == "pushed"


@pytest.mark.parametrize(
    "message",
    ["approval card is stale", "approval card expired"],
    ids=("stale", "expired"),
)
def test_rejected_card_returns_exit_one_with_one_recovery_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    message: str,
) -> None:
    def reject(*args: object, **kwargs: object) -> ApprovalOutcome:
        raise ApprovalError(message)

    monkeypatch.setattr(cli, "approve_dialog_card", reject)

    result = cli.main(
        [
            "approve-card",
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
            "--root",
            str(tmp_path),
        ]
    )

    assert result == 1
    payload = json.loads(capsys.readouterr().out)
    assert message in payload["message"]
    recovery_fields = {
        key: value
        for key, value in payload.items()
        if "recovery" in key.lower() or "恢复" in key
    }
    assert len(recovery_fields) == 1
    assert all(
        isinstance(value, str) and value.strip()
        for value in recovery_fields.values()
    )


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError(
            "internal failure token=ghp_super_secret_value at "
            "https://reviewer:ghp_super_secret_value@example.test/repo"
        ),
        subprocess.SubprocessError(
            "git push failed; Authorization: Bearer ghp_super_secret_value; "
            "GIT_SSH_COMMAND=ssh-with-ghp_super_secret_value"
        ),
    ],
    ids=("internal", "subprocess"),
)
def test_internal_errors_return_exit_two_as_redacted_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    def fail(*args: object, **kwargs: object) -> ApprovalOutcome:
        raise error

    monkeypatch.setattr(cli, "approve_dialog_card", fail)

    result = cli.main(
        [
            "approve-card",
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
            "--root",
            str(tmp_path),
        ]
    )

    assert result == 2
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert isinstance(payload, dict)
    assert "ghp_super_secret_value" not in output
    assert "reviewer:" not in output
    assert "Bearer " not in output
    assert "ssh-with-" not in output


def test_verifier_child_environment_drops_ambient_python_git_and_plugin_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    poisoned = {
        "PATH": "/tmp/hostile-path",
        "HOME": "/tmp/hostile-home",
        "GIT_DIR": "/tmp/hostile-git-dir",
        "GIT_WORK_TREE": "/tmp/hostile-work-tree",
        "GIT_SSH_COMMAND": "ssh hostile",
        "PYTEST_ADDOPTS": "--pdb",
        "PYTEST_PLUGINS": "hostile_plugin",
        "PYTHONPATH": "/tmp/hostile-pythonpath",
        "UNRELATED_SECRET": "must-not-cross-boundary",
    }
    for key, value in poisoned.items():
        monkeypatch.setenv(key, value)

    completed = approval_service._run_checked(
        tmp_path,
        (
            sys.executable,
            "-c",
            "import json, os; print(json.dumps(dict(os.environ), sort_keys=True))",
        ),
        label="environment probe",
        timeout=5,
    )
    child = json.loads(completed.stdout)

    assert all(
        key not in child
        for key in poisoned
        if key not in {"PATH", "HOME"}
    )
    assert child["PATH"] == os.defpath
    assert child["HOME"] != poisoned["HOME"]
    assert child["HOME"].startswith("/tmp/approval-command-")
    assert child["XDG_CONFIG_HOME"].startswith("/tmp/approval-command-")
    assert child["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert child["PYTHONUTF8"] == "1"
    assert child["PYTHONNOUSERSITE"] == "1"
    assert child["PYTHONSAFEPATH"] == "1"
    assert child["GIT_CONFIG_NOSYSTEM"] == "1"
    assert child["GIT_CONFIG_GLOBAL"] == os.devnull
    assert child["GIT_ATTR_NOSYSTEM"] == "1"
    assert child["GIT_LITERAL_PATHSPECS"] == "1"
    assert child["GIT_TERMINAL_PROMPT"] == "0"
    assert child["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert child["GIT_OPTIONAL_LOCKS"] == "0"


def test_verifier_git_diff_disables_repository_fsmonitor_and_external_diff(
    tmp_path: Path,
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
    subprocess.run(
        ["git", "config", "user.name", "Verifier Test"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    subprocess.run(
        ["git", "config", "user.email", "verifier@example.test"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    tracked = repository / "tracked.txt"
    attributes = repository / ".gitattributes"
    tracked.write_text("before\n", encoding="utf-8")
    attributes.write_text("*.txt diff=hostile\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "--", ".gitattributes", "tracked.txt"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "base"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )

    fsmonitor_marker = tmp_path / "fsmonitor-executed"
    fsmonitor = tmp_path / "fsmonitor.sh"
    fsmonitor.write_text(
        f"#!/bin/sh\ntouch '{fsmonitor_marker}'\nprintf '\\n'\n",
        encoding="utf-8",
    )
    fsmonitor.chmod(0o755)
    diff_marker = tmp_path / "external-diff-executed"
    external_diff = tmp_path / "external-diff.sh"
    external_diff.write_text(
        f"#!/bin/sh\ntouch '{diff_marker}'\nexit 0\n",
        encoding="utf-8",
    )
    external_diff.chmod(0o755)
    subprocess.run(
        ["git", "config", "core.fsmonitor", str(fsmonitor)],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    subprocess.run(
        ["git", "config", "diff.hostile.command", str(external_diff)],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    tracked.write_text("after\n", encoding="utf-8")

    approval_service._run_checked(
        repository,
        ("git", "diff", "HEAD", "--", "tracked.txt"),
        label="adversarial git diff",
        timeout=10,
    )

    assert not fsmonitor_marker.exists()
    assert not diff_marker.exists()


def _init_verifier_diff_repository(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "diff-repository"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=main"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    for key, value in (
        ("user.name", "Verifier Test"),
        ("user.email", "verifier@example.test"),
    ):
        subprocess.run(
            ["git", "config", key, value],
            cwd=repository,
            check=True,
            capture_output=True,
            timeout=10,
        )
    payload = repository / "tracked.payload"
    payload.write_text("base\n", encoding="utf-8")
    (repository / ".gitattributes").write_text(
        "*.payload filter=hostile\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", "--", ".gitattributes", "tracked.payload"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "base"],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    report = repository / "ops/validation/wiki_validation_report.md"
    report.parent.mkdir(parents=True)
    report.write_text("stable report\n", encoding="utf-8")
    return repository, payload


def _stub_non_git_verifier_steps(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> object:
    real_run_checked = approval_service._run_checked

    def selective_run_checked(
        root: Path,
        arguments: tuple[str, ...],
        *,
        label: str,
        timeout: int | float,
    ) -> subprocess.CompletedProcess[str]:
        if arguments and arguments[0] == "git":
            return real_run_checked(
                root,
                arguments,
                label=label,
                timeout=timeout,
            )
        return subprocess.CompletedProcess(arguments, 0, "stable\n", "")

    snapshot = object()
    monkeypatch.setattr(approval_service, "_run_checked", selective_run_checked)
    monkeypatch.setattr(
        approval_service,
        "_profile_snapshot",
        lambda root, *, accepted: snapshot,
    )
    assert (repository / "ops/validation/wiki_validation_report.md").is_file()
    return snapshot


@pytest.mark.parametrize("filter_mode", ["clean", "process"])
def test_project_verifier_diff_check_never_executes_local_content_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filter_mode: str,
) -> None:
    repository, payload = _init_verifier_diff_repository(tmp_path)
    marker = tmp_path / f"{filter_mode}-filter-executed"
    filter_program = tmp_path / f"{filter_mode}-filter.sh"
    body = "cat\n" if filter_mode == "clean" else "exit 1\n"
    filter_program.write_text(
        f"#!/bin/sh\ntouch '{marker}'\n{body}",
        encoding="utf-8",
    )
    filter_program.chmod(0o755)
    subprocess.run(
        [
            "git",
            "config",
            f"filter.hostile.{filter_mode}",
            str(filter_program),
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        timeout=10,
    )
    payload.write_text("changed\n", encoding="utf-8")
    expected = _stub_non_git_verifier_steps(repository, monkeypatch)

    observed = approval_service.ProjectVerificationRunner().prepare(repository)

    assert observed is expected
    assert not marker.exists()


def test_project_verifier_diff_check_still_rejects_trailing_whitespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payload = _init_verifier_diff_repository(tmp_path)
    payload.write_text("trailing whitespace \n", encoding="utf-8")
    _stub_non_git_verifier_steps(repository, monkeypatch)

    with pytest.raises(VerificationExecutionError) as captured:
        approval_service.ProjectVerificationRunner().prepare(repository)

    assert captured.value.code == "nonzero_exit"
    assert captured.value.label == "git diff check"


def test_verifier_process_group_times_out_with_a_stable_code(tmp_path: Path) -> None:
    with pytest.raises(VerificationExecutionError) as captured:
        approval_service._run_checked(
            tmp_path,
            (
                sys.executable,
                "-c",
                "import os, time; os.write(1, b'x'); time.sleep(30)",
            ),
            label="timeout probe",
            timeout=0.1,
        )

    assert captured.value.code == "timeout"
    assert "time.sleep" not in str(captured.value)


def test_verifier_process_group_rejects_output_overflow(tmp_path: Path) -> None:
    with pytest.raises(VerificationExecutionError) as captured:
        approval_service._run_checked(
            tmp_path,
            (
                sys.executable,
                "-c",
                "import os; os.write(1, b'x' * (1024 * 1024 + 1))",
            ),
            label="overflow probe",
            timeout=5,
        )

    assert captured.value.code == "output_limit_exceeded"
    assert len(str(captured.value)) < 200


def test_verifier_kills_process_group_when_pipe_read_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processes: list[subprocess.Popen[bytes]] = []
    real_popen = bounded_process.subprocess.Popen
    real_read = bounded_process.os.read
    armed = False

    def recording_popen(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
        nonlocal armed
        process = real_popen(*args, **kwargs)
        processes.append(process)
        armed = True
        return process

    def fail_read(*args: object, **kwargs: object) -> bytes:
        if armed:
            raise RuntimeError("injected pipe read failure")
        return real_read(*args, **kwargs)

    monkeypatch.setattr(bounded_process.subprocess, "Popen", recording_popen)
    monkeypatch.setattr(bounded_process.os, "read", fail_read)

    with pytest.raises(RuntimeError, match="injected pipe read failure"):
        approval_service._run_checked(
            tmp_path,
            (
                sys.executable,
                "-c",
                "import os, time; os.write(1, b'x'); time.sleep(30)",
            ),
            label="read failure probe",
            timeout=5,
        )

    assert len(processes) == 1
    assert processes[0].poll() is not None


def test_successful_command_cannot_leave_background_group_child(
    tmp_path: Path,
) -> None:
    completed = approval_service._run_checked(
        tmp_path,
        (
            sys.executable,
            "-c",
            (
                "import subprocess, sys; "
                "child=subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(30)']); "
                "print(child.pid, flush=True)"
            ),
        ),
        label="background child probe",
        timeout=5,
    )
    child_pid = int(completed.stdout.strip())

    deadline = time.monotonic() + 2
    state = ""
    while time.monotonic() < deadline:
        status = Path(f"/proc/{child_pid}/stat")
        if not status.exists():
            state = "gone"
            break
        state = status.read_text(encoding="utf-8").split()[2]
        if state == "Z":
            break
        time.sleep(0.02)
    assert state in {"gone", "Z"}


def test_legacy_validator_maps_shared_output_cap_to_stable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def overflow(*args: object, **kwargs: object) -> object:
        raise BoundedProcessError(
            "output_limit_exceeded",
            "legacy validator",
        )

    monkeypatch.setattr(repository_domain, "run_bounded_process", overflow)

    with pytest.raises(
        RuntimeError,
        match="legacy validator subprocess output_limit_exceeded",
    ):
        repository_domain.run_legacy_validator(tmp_path)


def test_report_git_enumeration_ignores_ambient_git_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=main", str(repository)],
        check=True,
        capture_output=True,
        timeout=10,
    )
    (repository / "visible.txt").write_text("visible\n", encoding="utf-8")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "hostile.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "hostile-work-tree"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "hostile-config"))

    assert "visible.txt" in _git_workspace_paths(repository)


def test_report_git_enumeration_disables_repository_fsmonitor(
    tmp_path: Path,
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
    marker = tmp_path / "report-fsmonitor-executed"
    fsmonitor = tmp_path / "report-fsmonitor.sh"
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

    assert "visible.txt" in _git_workspace_paths(repository)
    assert not marker.exists()


def test_profile_snapshot_ignores_ambient_git_python_and_pytest_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def passing_evaluation(
        root: Path,
        profile_id: str,
        *,
        require_fresh_generated: bool,
    ) -> EvaluationResult:
        assert root == tmp_path
        assert require_fresh_generated is False
        return EvaluationResult(
            evaluation_id="evaluation_" + "a" * 24,
            contract_id="pep_design_project_acceptance",
            contract_version="1.0.0",
            evaluator_version="1.0.0",
            profile=ProfileResult(
                profile_id=profile_id,
                harness_status=HarnessStatus.VALID,
                project_status=ProjectVerdict.PENDING_HUMAN_SIGNOFF,
                missing_signoff_roles=("governance_owner",),
            ),
            gate_results=(
                GateResult(
                    gate_id=f"{profile_id}.test_gate",
                    domain="test",
                    severity=Severity.CRITICAL,
                    verdict=GateVerdict.PASS,
                    reason_code="test_gate_passed",
                    message="Deterministic passing evaluation.",
                    evidence=(),
                ),
            ),
            contract_digest="b" * 64,
            registry_digest="c" * 64,
            evidence_digest="d" * 64,
            evidence_digests=(("test_source", "e" * 64),),
            required_signoff_roles=("governance_owner",),
        )

    monkeypatch.setattr(approval_service, "evaluate_project", passing_evaluation)
    baseline = approval_service._profile_snapshot(tmp_path, accepted=False)
    monkeypatch.setenv("GIT_DIR", "/tmp/hostile-git-dir")
    monkeypatch.setenv("GIT_WORK_TREE", "/tmp/hostile-work-tree")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/hostile-git-config")
    monkeypatch.setenv("PYTHONPATH", "/tmp/hostile-pythonpath")
    monkeypatch.setenv("PYTEST_ADDOPTS", "--pdb")
    monkeypatch.setenv("PYTEST_PLUGINS", "hostile_plugin")

    assert approval_service._profile_snapshot(tmp_path, accepted=False) == baseline


def _write_durable_journal(root: Path, state: TransactionState) -> None:
    path = root / "ops/acceptance/dialog_transactions" / f"{CARD_ID}.json"
    create_journal(path, card_id=CARD_ID, card_sha256=CARD_SHA256)
    transition_journal(
        path,
        expected_state=TransactionState.PREPARED,
        new_state=TransactionState.APPROVED,
        reviewed_at=NOW.isoformat(),
        approval_event_id="approval_event_" + "c" * 24,
    )
    transition_journal(
        path,
        expected_state=TransactionState.APPROVED,
        new_state=TransactionState.SOURCE_COMMITTED,
        source_commit_oid="1" * 40,
    )
    if state is TransactionState.LOCAL_COMMITTED_PUSH_FAILED:
        transition_journal(
            path,
            expected_state=TransactionState.SOURCE_COMMITTED,
            new_state=state,
            failure_code="push_failed",
        )
        return
    transition_journal(
        path,
        expected_state=TransactionState.SOURCE_COMMITTED,
        new_state=TransactionState.SIGNOFFS_COMMITTED,
        signoff_commit_oid="2" * 40,
        final_commit_oid="2" * 40,
    )
    transition_journal(
        path,
        expected_state=TransactionState.SIGNOFFS_COMMITTED,
        new_state=TransactionState.VERIFIED,
    )


@pytest.mark.parametrize(
    "state",
    [
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        TransactionState.VERIFIED,
    ],
)
def test_operational_error_uses_resume_recovery_for_durable_local_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    state: TransactionState,
) -> None:
    _write_durable_journal(tmp_path, state)

    def fail(*args: object, **kwargs: object) -> ApprovalOutcome:
        raise GitExecutionError("secret-bearing arbitrary git diagnostic")

    monkeypatch.setattr(cli, "approve_dialog_card", fail)

    result = cli.main(
        [
            "approve-card",
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
            "--root",
            str(tmp_path),
        ]
    )

    assert result == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["reason_code"] == "git_operation_failed"
    assert "resume-push" in payload["recovery_action"]
    assert CARD_ID in payload["recovery_action"]
    assert "prepare-review" not in payload["recovery_action"]
    assert "arbitrary git diagnostic" not in json.dumps(payload)


@pytest.mark.parametrize(
    ("error", "expected_exit", "expected_code"),
    [
        (GitApprovalError("approval requires branch main"), 1, "approval_rejected"),
        (GitExecutionError("Git command failed"), 2, "git_operation_failed"),
    ],
    ids=("git-state-rejection", "git-execution-failure"),
)
def test_git_state_and_execution_errors_have_distinct_cli_classes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    expected_exit: int,
    expected_code: str,
) -> None:
    def fail(*args: object, **kwargs: object) -> ApprovalOutcome:
        raise error

    monkeypatch.setattr(cli, "approve_dialog_card", fail)

    result = cli.main(
        [
            "approve-card",
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
            "--root",
            str(tmp_path),
        ]
    )

    assert result == expected_exit
    payload = json.loads(capsys.readouterr().out)
    assert payload["reason_code"] == expected_code
    assert "prepare-review" in payload["recovery_action"]


def test_approval_error_after_local_commit_is_exit_two_and_resume_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_durable_journal(
        tmp_path,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    )

    def fail(*args: object, **kwargs: object) -> ApprovalOutcome:
        raise ApprovalError("accepted profile check failed")

    monkeypatch.setattr(cli, "approve_dialog_card", fail)

    result = cli.main(
        [
            "approve-card",
            "--card-id",
            CARD_ID,
            "--expected-card-sha256",
            CARD_SHA256,
            "--reviewer-id",
            "project_owner",
            "--root",
            str(tmp_path),
        ]
    )

    assert result == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["reason_code"] == "durable_transaction_requires_resume"
    assert payload["message"] == "durable_transaction_requires_resume"
    assert "resume-push" in payload["recovery_action"]
    assert CARD_ID in payload["recovery_action"]
    assert "prepare-review" not in payload["recovery_action"]


def test_check_error_output_does_not_echo_internal_exception_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError("secret internal evaluator diagnostic")

    monkeypatch.setattr(cli, "evaluate_project", fail)

    result = cli.main(
        ["check", "--profile", "governance", "--root", str(tmp_path)]
    )

    assert result == 2
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["reason_codes"] == ["harness_evaluation_error"]
    assert payload["message"] == "harness_evaluation_error"
    assert "secret internal evaluator diagnostic" not in output
