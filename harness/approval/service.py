from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from harness.engine.models import (
    GateVerdict,
    HarnessStatus,
    ProjectVerdict,
    canonical_digest,
)
from harness.engine.bounded_process import (
    BoundedProcessError,
    run_bounded_process,
)
from harness.engine.report import (
    evaluate_project,
    gate_result_dict,
    render_outputs,
)

from .git_backend import GitApprovalError, GitBackend, check_worktree_diff
from .models import ApprovalError
from .render import render_approval_card
from .transaction import (
    TransactionResult,
    VerificationRunner,
    VerificationSnapshot,
    approve_card,
    prepare_review,
    resume_push,
)


_PROFILES = ("governance", "current_phase")
_TRUSTED_PATH = os.defpath
_GIT_CONFIG_ARGUMENTS = (
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.attributesFile=/dev/null",
)


@dataclass(frozen=True)
class PreparedReview:
    card_path: str
    card_id: str
    card_sha256: str
    markdown: str


@dataclass(frozen=True)
class ApprovalOutcome:
    card_id: str
    state: str
    source_commit_oid: str | None
    signoff_commit_oid: str | None
    final_commit_oid: str | None
    remote_oid: str | None


class VerificationExecutionError(RuntimeError):
    """Raised for bounded subprocess failures rather than approval rejection."""

    def __init__(self, code: str, label: str, *, returncode: int | None = None):
        self.code = code
        self.label = label
        self.returncode = returncode
        suffix = "" if returncode is None else f" (exit {returncode})"
        super().__init__(f"{label}: {code}{suffix}")


def _child_environment(control_root: Path) -> dict[str, str]:
    home = control_root / "home"
    xdg = control_root / "xdg"
    temporary = control_root / "tmp"
    for directory in (home, xdg, temporary):
        directory.mkdir(parents=True, exist_ok=True)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key == "LANG" or key.startswith("LC_")
    }
    environment.update(
        {
            "PATH": _TRUSTED_PATH,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(xdg),
            "TMPDIR": str(temporary),
            "TMP": str(temporary),
            "TEMP": str(temporary),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONUTF8": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _harden_git_arguments(arguments: Sequence[str]) -> tuple[str, ...]:
    values = tuple(arguments)
    if not values or values[0] != "git":
        return values
    if len(values) < 2:
        raise VerificationExecutionError("invalid_git_command", "git")
    command = ("git", *_GIT_CONFIG_ARGUMENTS, values[1])
    if values[1] == "diff":
        command += ("--no-ext-diff", "--no-textconv")
    return (*command, *values[2:])


def _run_checked(
    root: Path,
    arguments: Sequence[str],
    *,
    label: str,
    timeout: int | float,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(
        prefix="approval-command-",
        dir="/tmp",
    ) as temporary:
        try:
            completed = run_bounded_process(
                root,
                _harden_git_arguments(arguments),
                label=label,
                timeout=timeout,
                environment=_child_environment(Path(temporary)),
            )
        except BoundedProcessError as exc:
            raise VerificationExecutionError(
                exc.code,
                label,
                returncode=exc.returncode,
            ) from exc
    if completed.returncode != 0:
        raise VerificationExecutionError(
            "nonzero_exit",
            label,
            returncode=completed.returncode,
        )
    return completed


def _run_worktree_diff_check(root: Path, *, label: str) -> None:
    try:
        check_worktree_diff(root)
    except GitApprovalError as exc:
        raise VerificationExecutionError(
            "nonzero_exit",
            label,
            returncode=1,
        ) from exc


def _profile_snapshot(root: Path, *, accepted: bool) -> VerificationSnapshot:
    evaluations = tuple(
        evaluate_project(root, profile_id, require_fresh_generated=False)
        for profile_id in _PROFILES
    )
    first = evaluations[0]
    identity = (
        first.evaluation_id,
        first.evidence_digest,
        first.contract_digest,
        first.registry_digest,
    )
    gate_digests: list[tuple[str, str]] = []
    for profile_id, evaluation in zip(_PROFILES, evaluations, strict=True):
        current_identity = (
            evaluation.evaluation_id,
            evaluation.evidence_digest,
            evaluation.contract_digest,
            evaluation.registry_digest,
        )
        if current_identity != identity:
            raise ApprovalError("approval profiles do not share one evaluation identity")
        if evaluation.profile.harness_status is not HarnessStatus.VALID:
            raise ApprovalError(f"{profile_id} harness evaluation is not valid")
        if evaluation.invalid_signoff_files:
            raise ApprovalError(f"{profile_id} contains invalid signoffs")
        if any(gate.verdict is not GateVerdict.PASS for gate in evaluation.gate_results):
            raise ApprovalError(f"{profile_id} machine gates are not all pass")
        if accepted:
            if evaluation.profile.project_status is not ProjectVerdict.ACCEPTED:
                raise ApprovalError(f"{profile_id} is not accepted")
        elif evaluation.profile.project_status not in {
            ProjectVerdict.PENDING_HUMAN_SIGNOFF,
            ProjectVerdict.ACCEPTED,
        }:
            raise ApprovalError(f"{profile_id} is not ready for governance review")
        gate_digests.append(
            (
                profile_id,
                canonical_digest(
                    [gate_result_dict(gate) for gate in evaluation.gate_results]
                ),
            )
        )
    return VerificationSnapshot(
        evaluation_id=identity[0],
        evidence_digest=identity[1],
        contract_digest=identity[2],
        registry_digest=identity[3],
        profile_gate_digests=tuple(gate_digests),
    )


@dataclass(frozen=True)
class ProjectVerificationRunner(VerificationRunner):
    pytest_timeout: int = 300
    validator_timeout: int = 120

    def prepare(self, root: Path) -> VerificationSnapshot:
        _run_checked(
            root,
            (sys.executable, "-m", "pytest", "-q"),
            label="pytest",
            timeout=self.pytest_timeout,
        )
        validator = (sys.executable, "scripts/validate_benchmark_kb.py")
        first = _run_checked(
            root,
            validator,
            label="project validator first pass",
            timeout=self.validator_timeout,
        )
        report = root / "ops/validation/wiki_validation_report.md"
        try:
            first_report = report.read_bytes()
        except OSError as exc:
            raise VerificationExecutionError(
                "report_read_failed",
                "project validator first pass",
            ) from exc
        second = _run_checked(
            root,
            validator,
            label="project validator second pass",
            timeout=self.validator_timeout,
        )
        try:
            second_report = report.read_bytes()
        except OSError as exc:
            raise VerificationExecutionError(
                "report_read_failed",
                "project validator second pass",
            ) from exc
        if (
            first.stdout != second.stdout
            or first.stderr != second.stderr
            or first_report != second_report
        ):
            raise ApprovalError("project validator output is not deterministic")
        _run_worktree_diff_check(root, label="git diff check")
        return _profile_snapshot(root, accepted=False)

    def clean_checkout(self, root: Path) -> VerificationSnapshot:
        _run_checked(
            root,
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_harness_path_policy.py",
                "tests/test_harness_signoffs.py",
            ),
            label="clean checkout focused pytest",
            timeout=self.pytest_timeout,
        )
        _run_checked(
            root,
            (
                sys.executable,
                "scripts/validate_benchmark_kb.py",
                "--no-write-report",
            ),
            label="clean checkout validator",
            timeout=self.validator_timeout,
        )
        _run_worktree_diff_check(root, label="clean checkout diff check")
        return _profile_snapshot(root, accepted=False)

    def accepted(self, root: Path) -> VerificationSnapshot:
        return _profile_snapshot(root, accepted=True)

    def render_current_phase(self, root: Path) -> None:
        result = evaluate_project(
            root,
            "current_phase",
            require_fresh_generated=False,
        )
        if (
            result.profile.harness_status is not HarnessStatus.VALID
            or result.profile.project_status is not ProjectVerdict.ACCEPTED
            or result.invalid_signoff_files
        ):
            raise ApprovalError("current_phase cannot be rendered before acceptance")
        render_outputs(root, result)


def _production_dependencies(
    root: Path,
) -> tuple[GitBackend, ProjectVerificationRunner]:
    return GitBackend(root), ProjectVerificationRunner()


def _canonical_root(root: str | Path) -> Path:
    try:
        canonical = Path(root).resolve(strict=True)
    except OSError as exc:
        raise ApprovalError("project root does not exist or cannot be resolved") from exc
    if not canonical.is_dir():
        raise ApprovalError("project root must be a directory")
    return canonical


def _dependencies(
    root: Path,
    backend: GitBackend | None,
    verifier: VerificationRunner | None,
) -> tuple[GitBackend, VerificationRunner]:
    if backend is None and verifier is None:
        return _production_dependencies(root)
    if backend is None or verifier is None:
        raise ApprovalError("backend and verifier must be injected together")
    return backend, verifier


def _outcome(result: TransactionResult) -> ApprovalOutcome:
    state = getattr(result.state, "value", result.state)
    remote_oid = result.final_commit_oid if state == "pushed" else None
    return ApprovalOutcome(
        card_id=result.card_id,
        state=str(state),
        source_commit_oid=result.source_commit_oid,
        signoff_commit_oid=result.signoff_commit_oid,
        final_commit_oid=result.final_commit_oid,
        remote_oid=remote_oid,
    )


def prepare_dialog_review(
    root: str | Path,
    *,
    backend: GitBackend | None = None,
    verifier: VerificationRunner | None = None,
    now: datetime | None = None,
    nonce: bytes | None = None,
) -> PreparedReview:
    workspace = _canonical_root(root)
    selected_backend, selected_verifier = _dependencies(
        workspace, backend, verifier
    )
    prepared_at = datetime.now(timezone.utc) if now is None else now
    result = prepare_review(
        workspace,
        backend=selected_backend,
        verifier=selected_verifier,
        now=prepared_at,
        nonce=nonce,
    )
    card = result.card
    relative_path = f"ops/acceptance/dialog_cards/{card.card_id}.json"
    return PreparedReview(
        card_path=relative_path,
        card_id=card.card_id,
        card_sha256=card.card_sha256,
        markdown=render_approval_card(card, card_path=relative_path),
    )


def approve_dialog_card(
    root: str | Path,
    *,
    card_id: str,
    expected_card_sha256: str,
    reviewer_id: str,
    backend: GitBackend | None = None,
    verifier: VerificationRunner | None = None,
    now: datetime | None = None,
) -> ApprovalOutcome:
    workspace = _canonical_root(root)
    selected_backend, selected_verifier = _dependencies(
        workspace, backend, verifier
    )
    reviewed_at = datetime.now(timezone.utc) if now is None else now
    return _outcome(
        approve_card(
            workspace,
            card_id=card_id,
            expected_card_sha256=expected_card_sha256,
            reviewer_id=reviewer_id,
            backend=selected_backend,
            verifier=selected_verifier,
            now=reviewed_at,
        )
    )


def resume_dialog_push(
    root: str | Path,
    *,
    card_id: str,
    backend: GitBackend | None = None,
    verifier: VerificationRunner | None = None,
) -> ApprovalOutcome:
    workspace = _canonical_root(root)
    selected_backend, selected_verifier = _dependencies(
        workspace, backend, verifier
    )
    return _outcome(
        resume_push(
            workspace,
            card_id=card_id,
            backend=selected_backend,
            verifier=selected_verifier,
        )
    )


__all__ = [
    "ApprovalOutcome",
    "PreparedReview",
    "ProjectVerificationRunner",
    "approve_dialog_card",
    "prepare_dialog_review",
    "resume_dialog_push",
]
