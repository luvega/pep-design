from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from harness.domains.project_state import evaluate_gate
from harness.engine.evaluator import exit_code_for, resolve_gate_dependencies, roll_up_profile
from harness.engine.loader import ContractError
from harness.engine.models import (
    EvaluationResult,
    GateResult,
    GateVerdict,
    HarnessStatus,
    ProjectVerdict,
    Severity,
)
from harness.engine.report import (
    collect_evidence_digests,
    evaluate_project,
    workspace_source_digest,
)


ROOT = Path(__file__).resolve().parents[1]
CURRENT_PHASE_LIFECYCLE = {
    ProjectVerdict.NOT_ACCEPTED: ((), (), 1),
    ProjectVerdict.PENDING_HUMAN_SIGNOFF: ((), ("governance_owner",), 1),
    ProjectVerdict.ACCEPTED: (("governance_owner",), (), 0),
}


def sanitized_git_environment(home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("GIT_"):
            environment.pop(key, None)
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / "xdg"),
        }
    )
    return environment


def run_git(
    root: Path,
    environment: dict[str, str],
    hooks: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[bytes]:
    hooks.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "git",
            "-c",
            f"core.hooksPath={hooks}",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "tag.gpgSign=false",
            *arguments,
        ],
        cwd=root,
        check=True,
        capture_output=True,
        timeout=30,
        env=environment,
    )


def git_visible_paths(
    root: Path, environment: dict[str, str], hooks: Path
) -> tuple[str, ...]:
    completed = run_git(
        root,
        environment,
        hooks,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    values = completed.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return tuple(sorted(value for value in values if value))


def test_tracked_csv_worktree_bytes_follow_lf_policy(tmp_path: Path) -> None:
    auxiliary = tmp_path / "git-environment"
    environment = sanitized_git_environment(auxiliary / "home")
    hooks = auxiliary / "hooks"
    completed = run_git(
        ROOT,
        environment,
        hooks,
        "ls-files",
        "-z",
        "--",
        "*.csv",
    )
    relative_paths = tuple(
        value
        for value in completed.stdout.decode(
            "utf-8", errors="surrogateescape"
        ).split("\0")
        if value
    )

    violations: list[str] = []
    for relative_path in relative_paths:
        path = ROOT / relative_path
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            violations.append(f"{relative_path} (missing)")
            continue
        if stat.S_ISLNK(metadata.st_mode):
            violations.append(f"{relative_path} (symlink)")
            continue
        if not stat.S_ISREG(metadata.st_mode):
            violations.append(f"{relative_path} (not a regular file)")
            continue
        if b"\r" in path.read_bytes():
            violations.append(f"{relative_path} (contains CR byte)")

    assert not violations, (
        "tracked CSV worktree files must be regular LF-only files:\n"
        + "\n".join(violations)
    )


def make_isolated_repository(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    auxiliary = tmp_path / "git-environment"
    environment = sanitized_git_environment(auxiliary / "home")
    hooks = auxiliary / "hooks"
    template = auxiliary / "template"
    template.mkdir(parents=True)
    paths = git_visible_paths(ROOT, environment, hooks)
    repository = tmp_path / "workspace"
    run_git(
        tmp_path,
        environment,
        hooks,
        "clone",
        "--local",
        "--no-hardlinks",
        "--no-checkout",
        "--quiet",
        f"--template={template}",
        "--",
        str(ROOT),
        str(repository),
    )
    run_git(repository, environment, hooks, "remote", "remove", "origin")
    run_git(repository, environment, hooks, "read-tree", "HEAD")

    assert run_git(
        repository, environment, hooks, "rev-parse", "HEAD"
    ).stdout == run_git(ROOT, environment, hooks, "rev-parse", "HEAD").stdout
    assert run_git(
        repository,
        environment,
        hooks,
        "log",
        "--format=%H",
        "--",
        "harness/signoffs",
    ).stdout == run_git(
        ROOT,
        environment,
        hooks,
        "log",
        "--format=%H",
        "--",
        "harness/signoffs",
    ).stdout

    for relative_path in paths:
        source = ROOT / relative_path
        target = repository / relative_path
        if not source.exists():
            continue
        metadata = source.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise AssertionError(
                f"Git-visible test fixture must be a regular file: {relative_path}"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return repository, environment


def lifecycle_state(
    evaluation: EvaluationResult,
) -> tuple[
    HarnessStatus,
    ProjectVerdict,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    int,
]:
    return (
        evaluation.profile.harness_status,
        evaluation.profile.project_status,
        evaluation.valid_signoff_roles,
        evaluation.profile.missing_signoff_roles,
        evaluation.invalid_signoff_files,
        exit_code_for(evaluation.profile),
    )


def repository_snapshot(root: Path) -> dict[str, tuple[int, int, int, int, str]]:
    snapshot: dict[str, tuple[int, int, int, int, str]] = {}
    for path in (root, *sorted(root.rglob("*"))):
        metadata = path.lstat()
        relative_path = "." if path == root else path.relative_to(root).as_posix()
        file_type = stat.S_IFMT(metadata.st_mode)
        payload = ""
        if stat.S_ISREG(metadata.st_mode):
            payload = hashlib.sha256(path.read_bytes()).hexdigest()
        elif stat.S_ISLNK(metadata.st_mode):
            payload = os.readlink(path)
        snapshot[relative_path] = (
            file_type,
            stat.S_IMODE(metadata.st_mode),
            metadata.st_mtime_ns,
            metadata.st_size,
            payload,
        )
    return snapshot


def gate_result(
    gate_id: str,
    verdict: GateVerdict,
    *,
    failure_status: ProjectVerdict = ProjectVerdict.NOT_ACCEPTED,
) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        domain="repository_provenance",
        severity=Severity.CRITICAL,
        verdict=verdict,
        reason_code=f"{gate_id}_{verdict.value}",
        message="test",
        evidence=(),
        failure_status=failure_status,
    )


def test_dependency_failure_prevents_dependent_pass() -> None:
    gates = [
        {"gate_id": "source", "requires": []},
        {"gate_id": "dependent", "requires": ["source"]},
    ]
    resolved = resolve_gate_dependencies(
        gates,
        {
            "source": gate_result("source", GateVerdict.FAIL),
            "dependent": gate_result("dependent", GateVerdict.PASS),
        },
    )

    assert resolved["dependent"].verdict is GateVerdict.PENDING
    assert resolved["dependent"].reason_code == "dependency_not_satisfied"


def test_engine_error_is_separate_from_project_status() -> None:
    profile = {
        "profile_id": "governance",
        "required_gate_ids": ["gate"],
        "required_signoff_roles": [],
    }
    result = roll_up_profile(
        profile,
        {"gate": gate_result("gate", GateVerdict.ERROR)},
        set(),
    )

    assert result.harness_status is HarnessStatus.ERROR
    assert result.project_status is ProjectVerdict.NOT_ACCEPTED
    assert exit_code_for(result) == 2


def test_evidence_digest_excludes_generated_external_and_signoff_artifacts(
    tmp_path: Path,
) -> None:
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("evidence", encoding="utf-8")
    generated = tmp_path / "report.json"
    generated.write_text("rendered", encoding="utf-8")
    signoff = tmp_path / "signoff.json"
    signoff.write_text("approved", encoding="utf-8")
    registry = {
        "artifacts": [
            {
                "artifact_id": "tracked",
                "path": "tracked.txt",
                "verification_scope": "tracked",
                "include_in_evidence_digest": True,
            },
            {
                "artifact_id": "report",
                "path": "report.json",
                "verification_scope": "generated",
                "include_in_evidence_digest": False,
            },
            {
                "artifact_id": "signoff",
                "path": "signoff.json",
                "verification_scope": "generated",
                "include_in_evidence_digest": False,
            },
            {
                "artifact_id": "external",
                "path": "/external/source.txt",
                "verification_scope": "external_pointer",
                "include_in_evidence_digest": False,
            },
        ]
    }

    assert set(collect_evidence_digests(tmp_path, registry)) == {"tracked"}


def test_evidence_digest_rejects_path_escape_before_reading(tmp_path: Path) -> None:
    registry = {
        "artifacts": [
            {
                "artifact_id": "escape",
                "path": "../outside.txt",
                "verification_scope": "tracked",
                "include_in_evidence_digest": True,
            }
        ]
    }

    with pytest.raises(ContractError, match="must stay inside project root"):
        collect_evidence_digests(tmp_path, registry)


def test_optional_tracked_evidence_enters_digest_only_after_creation(
    tmp_path: Path,
) -> None:
    artifact = {
        "artifact_id": "future_evidence",
        "path": "results/future.json",
        "format": "json",
        "verification_scope": "tracked",
        "include_in_evidence_digest": True,
        "required_for_profiles": [],
    }
    registry = {"artifacts": [artifact]}
    evidence_path = tmp_path / artifact["path"]

    missing_digests = collect_evidence_digests(tmp_path, registry)
    assert artifact["artifact_id"] not in missing_digests

    payload = b"future conditional evidence\n"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_bytes(payload)
    present_digests = collect_evidence_digests(tmp_path, registry)

    assert present_digests[artifact["artifact_id"]] == hashlib.sha256(
        payload
    ).hexdigest()


def test_optional_tracked_evidence_rejects_dangling_symlink(
    tmp_path: Path,
) -> None:
    artifact = {
        "artifact_id": "future_evidence",
        "path": "results/future.json",
        "format": "json",
        "verification_scope": "tracked",
        "include_in_evidence_digest": True,
        "required_for_profiles": [],
    }
    registry = {"artifacts": [artifact]}
    evidence_path = tmp_path / artifact["path"]
    evidence_path.parent.mkdir(parents=True)
    evidence_path.symlink_to("missing.json")

    with pytest.raises(ContractError):
        collect_evidence_digests(tmp_path, registry)


def test_current_phase_missing_conditional_bundle_returns_gate_failure(
    tmp_path: Path,
) -> None:
    repository, _ = make_isolated_repository(tmp_path)
    registry_path = repository / "harness/registry/artifacts_v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    artifact = next(
        row
        for row in registry["artifacts"]
        if row["artifact_id"] == "v035_pepglad_connectivity_bundle"
    )
    artifact["required_for_profiles"] = []
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    evidence_path = repository / artifact["path"]
    evidence_path.unlink(missing_ok=True)

    contract = json.loads(
        (repository / "harness/contracts/project_acceptance_v1.json").read_text(
            encoding="utf-8"
        )
    )
    gate_contract = next(
        row
        for row in contract["gates"]
        if row["gate_id"] == "current.v035_bounded_connectivity"
    )
    artifact_index = {
        row["artifact_id"]: row for row in registry["artifacts"]
    }
    raw_gate = evaluate_gate(repository, gate_contract, artifact_index)

    assert raw_gate.verdict is GateVerdict.FAIL
    assert raw_gate.reason_code == "v035_bounded_connectivity_incomplete"

    evaluation = evaluate_project(
        repository,
        "current_phase",
        require_fresh_generated=False,
    )
    gate = next(
        row
        for row in evaluation.gate_results
        if row.gate_id == "current.v035_bounded_connectivity"
    )
    assert evaluation.profile.harness_status is HarnessStatus.VALID
    assert gate.verdict in {GateVerdict.FAIL, GateVerdict.PENDING}
    assert gate.verdict is not GateVerdict.ERROR


def test_workspace_digest_tracks_evaluator_code_but_excludes_reports_and_signoffs(
    tmp_path: Path,
) -> None:
    code = tmp_path / "harness/engine/evaluator.py"
    report = tmp_path / "ops/acceptance/project_acceptance_report.json"
    signoff = tmp_path / "harness/signoffs/approval.json"
    for path, content in ((code, "v1"), (report, "report-v1"), (signoff, "sign-v1")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    paths = [
        "harness/engine/evaluator.py",
        "ops/acceptance/project_acceptance_report.json",
        "harness/signoffs/approval.json",
    ]
    first = workspace_source_digest(tmp_path, paths)

    report.write_text("report-v2", encoding="utf-8")
    signoff.write_text("sign-v2", encoding="utf-8")
    assert workspace_source_digest(tmp_path, paths) == first

    code.write_text("v2", encoding="utf-8")
    assert workspace_source_digest(tmp_path, paths) != first


def test_actual_current_phase_has_exact_production_lifecycle_state() -> None:
    evaluation = evaluate_project(ROOT, "current_phase")

    assert evaluation.profile.harness_status is HarnessStatus.VALID
    expected_valid, expected_missing, expected_exit = CURRENT_PHASE_LIFECYCLE[
        evaluation.profile.project_status
    ]
    assert evaluation.valid_signoff_roles == expected_valid
    assert evaluation.profile.missing_signoff_roles == expected_missing
    assert evaluation.invalid_signoff_files == ()
    assert exit_code_for(evaluation.profile) == expected_exit
    assert "workspace_acceptance_surface" in dict(evaluation.evidence_digests)


def test_check_is_byte_for_byte_read_only_and_matches_production_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, environment = make_isolated_repository(tmp_path)
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        if key.startswith("GIT_") or key in {"HOME", "XDG_CONFIG_HOME"}:
            monkeypatch.setenv(key, value)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    evaluation = evaluate_project(repository, "current_phase")
    expected_valid, expected_missing, expected_exit = CURRENT_PHASE_LIFECYCLE[
        evaluation.profile.project_status
    ]
    expected_lifecycle = (
        HarnessStatus.VALID,
        evaluation.profile.project_status,
        expected_valid,
        expected_missing,
        (),
        expected_exit,
    )
    assert lifecycle_state(evaluation) == expected_lifecycle
    before = repository_snapshot(repository)

    completed = subprocess.run(
        [
            sys.executable,
            str(repository / "scripts/run_project_acceptance.py"),
            "check",
            "--profile",
            "current_phase",
            "--root",
            str(repository),
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=environment,
    )

    assert completed.returncode == expected_exit
    payload = json.loads(completed.stdout)
    assert payload["harness_status"] == "valid"
    assert payload["project_status"] == evaluation.profile.project_status.value
    assert tuple(payload["valid_signoff_roles"]) == expected_valid
    assert tuple(payload["missing_signoff_roles"]) == expected_missing
    assert payload["invalid_signoff_files"] == []
    assert repository_snapshot(repository) == before
