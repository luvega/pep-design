from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import harness.engine.signoffs as signoff_engine
from harness.engine.signoffs import SignoffContext, validate_signoff_directory


ROOT = Path(__file__).resolve().parents[1]
VALID_APPROVAL_BINDING = {
    "approval_card_id": "approval_" + "a" * 24,
    "approval_card_digest": "b" * 64,
    "approval_event_id": "approval_event_" + "c" * 24,
}
GOVERNANCE_RATIONALE = (
    "仅批准 contract/registry/migration/validator 的治理完整性；不豁免任何失败 "
    "gate，也不批准 release_checkpoint 或 full_project。"
)
CURRENT_PHASE_RATIONALE = (
    "接受 v0.34 的诚实边界：7 条主运行候选均已解析，其中 6 条通过 QC；"
    "PepGLAD 因混合手性失败；没有 scoring、ranking、frozen target 或 wet-lab 验证。"
)
V033_STALE_RATIONALE = (
    "接受 v0.33 的诚实边界：10 条 method-specific blockers，0 个 "
    "parsed/generated candidates，target/control 尚未冻结，scoring/ranking 尚未启动。"
)


def context(
    *,
    required_roles: tuple[str, ...] = ("governance_owner",),
    contract_id: str = "pep_design_project_acceptance",
    profile_id: str = "governance",
) -> SignoffContext:
    return SignoffContext(
        contract_id=contract_id,
        contract_version="1.0.0",
        contract_digest="sha256:contract",
        profile_id=profile_id,
        evaluation_id="evaluation_abc123",
        evidence_digest="sha256:evidence",
        required_roles=required_roles,
    )


def signoff(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_id": "pep_design_project_acceptance",
        "contract_version": "1.0.0",
        "contract_digest": "sha256:contract",
        "profile_id": "governance",
        "evaluation_id": "evaluation_abc123",
        "evidence_digest": "sha256:evidence",
        "role": "governance_owner",
        "reviewer_id": "reviewer@example.org",
        "decision": "approved",
        "rationale": "Reviewed against the machine evaluation.",
        "reviewed_at": "2026-07-10T12:00:00+08:00",
    }
    value.update(overrides)
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def sanitized_git_environment(root: Path) -> dict[str, str]:
    home = root.parent / f".{root.name}-git-home"
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


def run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    hooks = root.parent / f".{root.name}-git-hooks"
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
        timeout=20,
        env=sanitized_git_environment(root),
    )


@pytest.fixture
def sanitized_git_process_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = sanitized_git_environment(tmp_path)
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        if key.startswith("GIT_") or key in {"HOME", "XDG_CONFIG_HOME"}:
            monkeypatch.setenv(key, value)


def init_git_repository(root: Path) -> Path:
    template = root.parent / f".{root.name}-git-template"
    template.mkdir(parents=True, exist_ok=True)
    run_git(root, "init", "-q", f"--template={template}")
    run_git(root, "config", "--local", "user.name", "Test Reviewer")
    run_git(root, "config", "--local", "user.email", "reviewer@example.test")
    hostile_hook = root / ".git/hooks/pre-commit"
    hostile_hook.parent.mkdir(parents=True, exist_ok=True)
    hostile_hook.write_text(
        "#!/bin/sh\ntouch \"$PWD/hook-executed\"\nexit 97\n",
        encoding="utf-8",
    )
    hostile_hook.chmod(0o755)
    directory = root / "harness/signoffs"
    directory.mkdir(parents=True)
    return directory


def commit_paths(root: Path, message: str, *relative_paths: str) -> None:
    run_git(root, "add", "--", *relative_paths)
    run_git(root, "commit", "-q", "-m", message)
    assert not (root / "hook-executed").exists()


def create_same_commit_signoffs_with_fabricated_parent(
    root: Path, directory: Path
) -> tuple[str, str]:
    write_json(directory / "prior.json", signoff(reviewer_id="reviewer-old"))
    run_git(root, "add", "--", "harness/signoffs/prior.json")
    prior_tree = run_git(root, "write-tree").stdout.decode("ascii").strip()
    fabricated_parent = (
        run_git(root, "commit-tree", prior_tree, "-m", "fabricated prior")
        .stdout.decode("ascii")
        .strip()
    )
    write_json(
        directory / "current.json",
        signoff(reviewer_id="reviewer-new", supersedes="prior.json"),
    )
    run_git(root, "add", "--", "harness/signoffs/current.json")
    same_commit_tree = run_git(root, "write-tree").stdout.decode("ascii").strip()
    same_commit = (
        run_git(root, "commit-tree", same_commit_tree, "-m", "same commit")
        .stdout.decode("ascii")
        .strip()
    )
    run_git(root, "update-ref", "HEAD", same_commit)
    run_git(root, "reset", "-q", "--hard", same_commit)
    return same_commit, fabricated_parent


def test_missing_required_signoffs_are_explicit(tmp_path: Path) -> None:
    result = validate_signoff_directory(
        tmp_path,
        context(required_roles=("governance_owner", "scientific_reviewer")),
    )

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner", "scientific_reviewer")
    assert result.stale_signoffs == ()
    assert result.invalid_signoffs == ()
    assert result.is_complete is False


def test_legacy_approved_signoff_without_dialog_binding_is_valid(tmp_path: Path) -> None:
    write_json(tmp_path / "governance.json", signoff())

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ("governance_owner",)
    assert result.missing_roles == ()
    assert result.is_complete is True


def test_full_approval_card_digest_and_event_binding_is_valid(tmp_path: Path) -> None:
    write_json(
        tmp_path / "governance.json",
        signoff(
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            **VALID_APPROVAL_BINDING,
        ),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ("governance_owner",)
    assert result.missing_roles == ()
    assert result.invalid_signoffs == ()


@pytest.mark.parametrize(
    "binding",
    [
        {"approval_card_id": VALID_APPROVAL_BINDING["approval_card_id"]},
        {
            "approval_card_digest": VALID_APPROVAL_BINDING[
                "approval_card_digest"
            ]
        },
        {"approval_event_id": VALID_APPROVAL_BINDING["approval_event_id"]},
        {
            "approval_card_id": VALID_APPROVAL_BINDING["approval_card_id"],
            "approval_card_digest": VALID_APPROVAL_BINDING[
                "approval_card_digest"
            ],
        },
        {
            "approval_card_id": VALID_APPROVAL_BINDING["approval_card_id"],
            "approval_event_id": VALID_APPROVAL_BINDING["approval_event_id"],
        },
        {
            "approval_card_digest": VALID_APPROVAL_BINDING[
                "approval_card_digest"
            ],
            "approval_event_id": VALID_APPROVAL_BINDING["approval_event_id"],
        },
        {
            **VALID_APPROVAL_BINDING,
            "approval_card_id": "approval_not-a-canonical-card-id",
        },
        {
            **VALID_APPROVAL_BINDING,
            "approval_card_digest": "sha256:not-a-bare-canonical-digest",
        },
        {**VALID_APPROVAL_BINDING, "approval_event_id": "   "},
    ],
    ids=(
        "card-id-only",
        "digest-only",
        "event-only",
        "missing-event",
        "missing-digest",
        "missing-card-id",
        "malformed-card-id",
        "malformed-card-digest",
        "blank-event-id",
    ),
)
def test_partial_or_malformed_approval_binding_is_invalid(
    tmp_path: Path, binding: dict[str, str]
) -> None:
    write_json(
        tmp_path / "governance.json",
        signoff(
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            **binding,
        ),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"reviewer_id": "reviewer@example.org"},
        {"rationale": "Generic approval rationale."},
        {"approval_event_id": "approval-event-123"},
    ],
    ids=("wrong-reviewer", "wrong-rationale", "noncanonical-event-id"),
)
def test_dialog_binding_requires_exact_owner_rationale_and_event_id(
    tmp_path: Path, overrides: dict[str, str]
) -> None:
    value = signoff(
        reviewer_id="project_owner",
        rationale=GOVERNANCE_RATIONALE,
        **VALID_APPROVAL_BINDING,
    )
    value.update(overrides)
    write_json(tmp_path / "governance.json", value)

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


def test_current_phase_dialog_binding_requires_its_own_exact_rationale(
    tmp_path: Path,
) -> None:
    write_json(
        tmp_path / "current.json",
        signoff(
            profile_id="current_phase",
            reviewer_id="project_owner",
            rationale=CURRENT_PHASE_RATIONALE,
            **VALID_APPROVAL_BINDING,
        ),
    )

    valid = validate_signoff_directory(tmp_path, context(profile_id="current_phase"))
    assert valid.valid_roles == ("governance_owner",)
    assert valid.invalid_signoffs == ()

    write_json(
        tmp_path / "current.json",
        signoff(
            profile_id="current_phase",
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            **VALID_APPROVAL_BINDING,
        ),
    )
    invalid = validate_signoff_directory(tmp_path, context(profile_id="current_phase"))
    assert invalid.valid_roles == ()
    assert invalid.invalid_signoffs[0].reason_code == (
        "signoff_approval_binding_invalid"
    )


@pytest.mark.parametrize(
    ("signoff_profile", "validation_profile", "rationale"),
    [
        ("governance", "current_phase", GOVERNANCE_RATIONALE),
        ("current_phase", "governance", CURRENT_PHASE_RATIONALE),
    ],
)
def test_current_canonical_sibling_dialog_is_stale_when_only_profile_differs(
    tmp_path: Path,
    signoff_profile: str,
    validation_profile: str,
    rationale: str,
) -> None:
    write_json(
        tmp_path / "sibling.json",
        signoff(
            profile_id=signoff_profile,
            reviewer_id="project_owner",
            rationale=rationale,
            **VALID_APPROVAL_BINDING,
        ),
    )

    result = validate_signoff_directory(
        tmp_path, context(profile_id=validation_profile)
    )

    assert result.invalid_signoffs == ()
    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.stale_signoffs] == [
        "signoff_context_mismatch"
    ]
    assert result.stale_signoffs[0].mismatched_fields == ("profile_id",)


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "profile_id": "current_phase",
            "evaluation_id": "evaluation_old",
            "rationale": CURRENT_PHASE_RATIONALE,
        },
        {
            "profile_id": "release_checkpoint",
            "rationale": CURRENT_PHASE_RATIONALE,
        },
        {
            "profile_id": "current_phase",
            "rationale": GOVERNANCE_RATIONALE,
        },
    ],
    ids=("old-context", "fabricated-profile", "wrong-sibling-rationale"),
)
def test_sibling_dialog_stale_exception_rejects_cross_mixes(
    tmp_path: Path,
    overrides: dict[str, str],
) -> None:
    write_json(
        tmp_path / "cross-mix.json",
        signoff(
            reviewer_id="project_owner",
            **VALID_APPROVAL_BINDING,
            **overrides,
        ),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.stale_signoffs == ()
    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


def test_signoff_schema_applies_dialog_constraints_only_with_card_binding() -> None:
    schema = json.loads(
        (ROOT / "harness/signoffs/signoff.schema.json").read_text(encoding="utf-8")
    )

    assert not {
        "approval_card_id",
        "approval_card_digest",
        "approval_event_id",
    } & set(schema["required"])
    assert schema["properties"]["reviewer_id"] == {
        "type": "string",
        "minLength": 1,
    }
    assert "const" not in schema["properties"]["rationale"]
    assert schema["dependentRequired"] == {
        "approval_card_id": ["approval_card_digest", "approval_event_id"],
        "approval_card_digest": ["approval_card_id", "approval_event_id"],
        "approval_event_id": ["approval_card_id", "approval_card_digest"],
    }

    assert {
        "dialog_governance_current",
        "dialog_current_phase_v034",
        "dialog_current_phase_historical_v033",
    } <= set(schema["$defs"])

    validator = Draft202012Validator(schema)
    historical = json.loads(
        (ROOT / "harness/signoffs/signoff_current_phase_v1.json").read_text(
            encoding="utf-8"
        )
    )
    current = signoff(
        contract_digest="a" * 64,
        profile_id="current_phase",
        evaluation_id="evaluation_" + "b" * 24,
        evidence_digest="c" * 64,
        reviewer_id="project_owner",
        rationale=CURRENT_PHASE_RATIONALE,
        **VALID_APPROVAL_BINDING,
    )

    assert list(validator.iter_errors(historical)) == []
    assert list(validator.iter_errors(current)) == []

    historical_near_miss = dict(historical)
    historical_near_miss["evidence_digest"] = "d" * 64
    arbitrary = dict(current)
    arbitrary["rationale"] = "Arbitrary dialog rationale."
    assert list(validator.iter_errors(historical_near_miss))
    assert list(validator.iter_errors(arbitrary))


def test_signoff_readme_documents_v034_rationale_and_preserves_v033_history() -> None:
    readme = (ROOT / "harness/signoffs/README.md").read_text(encoding="utf-8")
    historical = json.loads(
        (ROOT / "harness/signoffs/signoff_current_phase_v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert CURRENT_PHASE_RATIONALE in readme
    assert "signoff_current_phase_v1.json" in readme
    assert "stale" in readme
    assert historical["rationale"] == V033_STALE_RATIONALE
    assert historical["rationale"] != CURRENT_PHASE_RATIONALE


def test_context_mismatch_is_stale_and_role_remains_missing(tmp_path: Path) -> None:
    write_json(
        tmp_path / "old.json",
        signoff(evaluation_id="evaluation_old", evidence_digest="sha256:old"),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.stale_signoffs] == [
        "signoff_context_mismatch"
    ]
    assert result.stale_signoffs[0].mismatched_fields == (
        "evaluation_id",
        "evidence_digest",
    )


def test_historical_dialog_copy_without_production_trust_is_invalid(
    tmp_path: Path,
) -> None:
    historical = json.loads(
        (ROOT / "harness/signoffs/signoff_current_phase_v1.json").read_text(
            encoding="utf-8"
        )
    )
    write_json(
        tmp_path / "old-current.json",
        historical,
    )

    result = validate_signoff_directory(
        tmp_path, context(profile_id="current_phase")
    )

    assert result.stale_signoffs == ()
    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


def test_historical_context_with_current_rationale_is_invalid_not_stale(
    tmp_path: Path,
) -> None:
    historical = json.loads(
        (ROOT / "harness/signoffs/signoff_current_phase_v1.json").read_text(
            encoding="utf-8"
        )
    )
    historical["rationale"] = CURRENT_PHASE_RATIONALE
    write_json(tmp_path / "mixed-context-rationale.json", historical)

    result = validate_signoff_directory(
        tmp_path, context(profile_id="current_phase")
    )

    assert result.stale_signoffs == ()
    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_id", "fabricated_contract"),
        ("contract_version", "1.0.1"),
        ("contract_digest", "0" * 64),
        ("profile_id", "governance"),
        ("evaluation_id", "evaluation_fabricated"),
        ("evidence_digest", "1" * 64),
    ],
)
def test_near_miss_historical_dialog_context_is_invalid_not_stale(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    historical = json.loads(
        (ROOT / "harness/signoffs/signoff_current_phase_v1.json").read_text(
            encoding="utf-8"
        )
    )
    historical[field] = value
    write_json(tmp_path / "near-miss-old-current.json", historical)

    result = validate_signoff_directory(
        tmp_path, context(profile_id="current_phase")
    )

    assert result.stale_signoffs == ()
    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


def test_unknown_historical_dialog_rationale_is_invalid_not_stale(
    tmp_path: Path,
) -> None:
    write_json(
        tmp_path / "unknown-old-current.json",
        signoff(
            profile_id="current_phase",
            evaluation_id="evaluation_old",
            evidence_digest="sha256:old",
            reviewer_id="project_owner",
            rationale="Arbitrary historical approval text.",
            **VALID_APPROVAL_BINDING,
        ),
    )

    result = validate_signoff_directory(
        tmp_path, context(profile_id="current_phase")
    )

    assert result.stale_signoffs == ()
    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


def test_non_string_historical_dialog_rationale_is_invalid_not_an_error(
    tmp_path: Path,
) -> None:
    write_json(
        tmp_path / "malformed-old-current.json",
        signoff(
            profile_id="current_phase",
            evaluation_id="evaluation_old",
            evidence_digest="sha256:old",
            reviewer_id="project_owner",
            rationale=[V033_STALE_RATIONALE],
            **VALID_APPROVAL_BINDING,
        ),
    )

    result = validate_signoff_directory(
        tmp_path, context(profile_id="current_phase")
    )

    assert result.stale_signoffs == ()
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_approval_binding_invalid"
    ]


def test_profile_mismatch_is_stale(tmp_path: Path) -> None:
    write_json(tmp_path / "other-profile.json", signoff(profile_id="current_phase"))

    result = validate_signoff_directory(tmp_path, context())

    assert result.missing_roles == ("governance_owner",)
    assert result.stale_signoffs[0].mismatched_fields == ("profile_id",)


def test_other_profile_role_is_stale_not_a_harness_error(tmp_path: Path) -> None:
    write_json(
        tmp_path / "release-review.json",
        signoff(profile_id="release_checkpoint", role="engineering_reviewer"),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.invalid_signoffs == ()
    assert result.missing_roles == ("governance_owner",)
    assert result.stale_signoffs[0].mismatched_fields == ("profile_id",)


def test_non_approved_decision_is_invalid(tmp_path: Path) -> None:
    write_json(tmp_path / "rejected.json", signoff(decision="rejected"))

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_decision_not_approved"
    ]


def test_reviewer_identity_rationale_and_timezone_timestamp_are_required(
    tmp_path: Path,
) -> None:
    value = signoff()
    value.pop("reviewer_id")
    value["reviewed_at"] = "2026-07-10T12:00:00"
    write_json(tmp_path / "incomplete.json", value)

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].reason_code == "signoff_review_metadata_invalid"


def test_waiver_or_override_keys_are_rejected_even_when_nested_or_false(
    tmp_path: Path,
) -> None:
    write_json(
        tmp_path / "waiver.json",
        signoff(review={"override": False}),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].reason_code == "signoff_override_forbidden"


def test_role_must_be_required_by_the_profile(tmp_path: Path) -> None:
    write_json(tmp_path / "unknown-role.json", signoff(role="release_manager"))

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert result.invalid_signoffs[0].reason_code == "signoff_role_not_required"


def test_duplicate_current_signoffs_invalidate_that_role_deterministically(
    tmp_path: Path,
) -> None:
    write_json(tmp_path / "z-last.json", signoff(reviewer_id="reviewer-z"))
    write_json(tmp_path / "a-first.json", signoff(reviewer_id="reviewer-a"))

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert result.duplicate_roles == ("governance_owner",)
    assert [Path(issue.path).name for issue in result.invalid_signoffs] == [
        "a-first.json",
        "z-last.json",
    ]
    assert {issue.reason_code for issue in result.invalid_signoffs} == {
        "signoff_duplicate_role"
    }


def test_stale_history_does_not_duplicate_a_current_signoff(tmp_path: Path) -> None:
    write_json(tmp_path / "old.json", signoff(evaluation_id="evaluation_old"))
    write_json(tmp_path / "current.json", signoff())

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ("governance_owner",)
    assert result.duplicate_roles == ()
    assert len(result.stale_signoffs) == 1


def test_current_signoff_can_append_only_supersede_an_earlier_file(
    tmp_path: Path,
) -> None:
    write_json(tmp_path / "old.json", signoff(reviewer_id="reviewer-old"))
    write_json(
        tmp_path / "corrected.json",
        signoff(reviewer_id="reviewer-new", supersedes="old.json"),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ("governance_owner",)
    assert result.duplicate_roles == ()
    assert result.invalid_signoffs == ()


def test_current_signoff_can_supersede_stale_prior_evaluation(tmp_path: Path) -> None:
    write_json(
        tmp_path / "old.json",
        signoff(evaluation_id="evaluation_old", evidence_digest="sha256:old"),
    )
    write_json(tmp_path / "current.json", signoff(supersedes="old.json"))

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ("governance_owner",)
    assert result.invalid_signoffs == ()
    assert tuple(issue.path for issue in result.stale_signoffs) == ("old.json",)


def test_untrusted_dialog_history_stays_invalid_even_when_superseded(
    tmp_path: Path,
) -> None:
    write_json(
        tmp_path / "prior.json",
        signoff(
            evaluation_id="evaluation_old",
            evidence_digest="sha256:old",
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            **VALID_APPROVAL_BINDING,
        ),
    )
    write_json(
        tmp_path / "current.json",
        signoff(
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            supersedes="prior.json",
            **VALID_APPROVAL_BINDING,
        ),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.stale_signoffs == ()
    assert {
        (issue.path, issue.reason_code) for issue in result.invalid_signoffs
    } == {
        ("current.json", "signoff_supersedes_invalid"),
        ("prior.json", "signoff_approval_binding_invalid"),
    }


@pytest.mark.parametrize(
    "prior_overrides",
    [
        {"profile_id": "current_phase"},
        {"contract_id": "other_acceptance_contract"},
    ],
    ids=("other-profile", "other-contract"),
)
def test_supersedes_rejects_same_role_from_other_profile_or_contract(
    tmp_path: Path, prior_overrides: dict[str, str]
) -> None:
    write_json(tmp_path / "prior.json", signoff(**prior_overrides))
    write_json(tmp_path / "current.json", signoff(supersedes="prior.json"))

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [
        issue.reason_code
        for issue in result.invalid_signoffs
        if issue.path == "current.json"
    ] == ["signoff_supersedes_invalid"]


def test_supersedes_must_reference_an_existing_same_role_signoff(tmp_path: Path) -> None:
    write_json(
        tmp_path / "bad.json",
        signoff(supersedes="missing.json"),
    )

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].reason_code == "signoff_supersedes_invalid"


def test_generated_request_and_schema_files_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "signoff.schema.json").write_text("not-json", encoding="utf-8")
    (tmp_path / "signoff_request_v1.json").write_text("not-json", encoding="utf-8")
    write_json(tmp_path / "governance.json", signoff())

    result = validate_signoff_directory(tmp_path, context())

    assert result.valid_roles == ("governance_owner",)
    assert result.invalid_signoffs == ()
    assert tuple(Path(path).name for path in result.ignored_metadata_files) == (
        "signoff.schema.json",
        "signoff_request_v1.json",
    )


def test_malformed_or_non_object_json_is_reported_as_invalid(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    write_json(tmp_path / "list.json", [])

    result = validate_signoff_directory(tmp_path, context())

    assert result.missing_roles == ("governance_owner",)
    assert [issue.path for issue in result.invalid_signoffs] == [
        "broken.json",
        "list.json",
    ]
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_json_invalid",
        "signoff_not_object",
    ]


def test_symlinked_signoff_cannot_grant_approval(tmp_path: Path) -> None:
    target = tmp_path / "outside.json"
    write_json(target, signoff())
    directory = tmp_path / "signoffs"
    directory.mkdir()
    (directory / "approval.json").symlink_to(target)

    result = validate_signoff_directory(directory, context())

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].reason_code == "signoff_file_untrusted"


def test_directory_named_like_signoff_is_untrusted(tmp_path: Path) -> None:
    directory = tmp_path / "signoffs"
    directory.mkdir()
    (directory / "approval.json").mkdir()

    result = validate_signoff_directory(directory, context())

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].path == "approval.json"
    assert result.invalid_signoffs[0].reason_code == "signoff_file_untrusted"


def test_fifo_signoff_is_rejected_before_git_or_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path / "signoffs"
    directory.mkdir()
    fifo = directory / "approval.json"
    os.mkfifo(fifo)
    real_read_text = Path.read_text

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path == fifo:
            raise AssertionError("FIFO must not be read")
        return real_read_text(path, *args, **kwargs)

    def reject_git_open(path: Path) -> object:
        raise AssertionError("Git must not run for a non-regular signoff")

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(signoff_engine, "_open_raw_git_repository", reject_git_open)

    result = validate_signoff_directory(
        directory,
        replace(context(), repository_root=str(tmp_path)),
    )

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].path == "approval.json"
    assert result.invalid_signoffs[0].reason_code == "signoff_file_untrusted"


def test_uncommitted_signoff_cannot_grant_production_approval(
    tmp_path: Path, sanitized_git_process_environment: None
) -> None:
    directory = init_git_repository(tmp_path)
    write_json(directory / "approval.json", signoff())
    base = context()
    production_context = SignoffContext(
        contract_id=base.contract_id,
        contract_version=base.contract_version,
        contract_digest=base.contract_digest,
        profile_id=base.profile_id,
        evaluation_id=base.evaluation_id,
        evidence_digest=base.evidence_digest,
        required_roles=base.required_roles,
        repository_root=str(tmp_path),
    )

    result = validate_signoff_directory(directory, production_context)

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].reason_code == "signoff_file_untrusted"


def test_production_validation_parses_bytes_captured_before_path_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sanitized_git_process_environment: None,
) -> None:
    directory = init_git_repository(tmp_path)
    approval = directory / "approval.json"
    write_json(approval, signoff(decision="rejected"))
    commit_paths(tmp_path, "add rejected decision", "harness/signoffs/approval.json")
    real_trust_check = signoff_engine._git_signoff_is_committed_clean

    def replace_after_trust_check(*args: object) -> bool:
        trusted = real_trust_check(*args)
        write_json(approval, signoff())
        return trusted

    monkeypatch.setattr(
        signoff_engine,
        "_git_signoff_is_committed_clean",
        replace_after_trust_check,
    )

    result = validate_signoff_directory(
        directory, replace(context(), repository_root=str(tmp_path))
    )

    assert result.valid_roles == ()
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_decision_not_approved"
    ]


def test_production_supersedes_rejects_target_added_in_same_commit(
    tmp_path: Path, sanitized_git_process_environment: None
) -> None:
    directory = init_git_repository(tmp_path)
    write_json(directory / "prior.json", signoff(reviewer_id="reviewer-old"))
    write_json(
        directory / "current.json",
        signoff(reviewer_id="reviewer-new", supersedes="prior.json"),
    )
    commit_paths(
        tmp_path,
        "add same-commit signoffs",
        "harness/signoffs/prior.json",
        "harness/signoffs/current.json",
    )
    production_context = replace(context(), repository_root=str(tmp_path))

    result = validate_signoff_directory(directory, production_context)

    assert [
        issue.reason_code
        for issue in result.invalid_signoffs
        if issue.path == "current.json"
    ] == ["signoff_supersedes_invalid"]


def test_production_supersedes_accepts_target_from_prior_commit(
    tmp_path: Path, sanitized_git_process_environment: None
) -> None:
    directory = init_git_repository(tmp_path)
    write_json(directory / "prior.json", signoff(reviewer_id="reviewer-old"))
    commit_paths(
        tmp_path,
        "add prior signoff",
        "harness/signoffs/prior.json",
    )
    write_json(
        directory / "current.json",
        signoff(reviewer_id="reviewer-new", supersedes="prior.json"),
    )
    commit_paths(
        tmp_path,
        "supersede prior signoff",
        "harness/signoffs/current.json",
    )
    production_context = replace(context(), repository_root=str(tmp_path))

    result = validate_signoff_directory(directory, production_context)

    assert result.valid_roles == ("governance_owner",)
    assert result.missing_roles == ()
    assert result.duplicate_roles == ()
    assert result.invalid_signoffs == ()


def test_production_supersedes_rejects_rewritten_prior_path(
    tmp_path: Path, sanitized_git_process_environment: None
) -> None:
    directory = init_git_repository(tmp_path)
    write_json(directory / "prior.json", signoff(reviewer_id="reviewer-old"))
    commit_paths(tmp_path, "add prior signoff", "harness/signoffs/prior.json")
    write_json(directory / "prior.json", signoff(reviewer_id="rewritten"))
    write_json(
        directory / "current.json",
        signoff(reviewer_id="reviewer-new", supersedes="prior.json"),
    )
    commit_paths(
        tmp_path,
        "rewrite and supersede prior",
        "harness/signoffs/prior.json",
        "harness/signoffs/current.json",
    )

    result = validate_signoff_directory(
        directory, replace(context(), repository_root=str(tmp_path))
    )

    assert result.valid_roles == ()
    assert {
        (issue.path, issue.reason_code) for issue in result.invalid_signoffs
    } == {
        ("current.json", "signoff_supersedes_invalid"),
        ("prior.json", "signoff_file_untrusted"),
    }


def test_production_signoff_rejects_rewrite_then_restore_history(
    tmp_path: Path, sanitized_git_process_environment: None
) -> None:
    directory = init_git_repository(tmp_path)
    original = signoff(reviewer_id="reviewer-original")
    write_json(directory / "approval.json", original)
    commit_paths(tmp_path, "add approval", "harness/signoffs/approval.json")
    write_json(
        directory / "approval.json",
        signoff(reviewer_id="reviewer-rewritten"),
    )
    commit_paths(tmp_path, "rewrite approval", "harness/signoffs/approval.json")
    write_json(directory / "approval.json", original)
    commit_paths(tmp_path, "restore approval", "harness/signoffs/approval.json")

    result = validate_signoff_directory(
        directory, replace(context(), repository_root=str(tmp_path))
    )

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert [issue.reason_code for issue in result.invalid_signoffs] == [
        "signoff_file_untrusted"
    ]


def test_production_supersedes_accepts_prior_dialog_from_changed_evaluation(
    tmp_path: Path, sanitized_git_process_environment: None
) -> None:
    directory = init_git_repository(tmp_path)
    write_json(
        directory / "prior.json",
        signoff(
            evaluation_id="evaluation_old",
            evidence_digest="sha256:old",
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            **VALID_APPROVAL_BINDING,
        ),
    )
    commit_paths(tmp_path, "add prior dialog", "harness/signoffs/prior.json")
    write_json(
        directory / "current.json",
        signoff(
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            supersedes="prior.json",
            **VALID_APPROVAL_BINDING,
        ),
    )
    commit_paths(
        tmp_path,
        "supersede prior dialog",
        "harness/signoffs/current.json",
    )

    result = validate_signoff_directory(
        directory, replace(context(), repository_root=str(tmp_path))
    )

    assert result.valid_roles == ("governance_owner",)
    assert result.missing_roles == ()
    assert result.invalid_signoffs == ()
    assert tuple(issue.path for issue in result.stale_signoffs) == ("prior.json",)


def test_production_prior_dialog_is_stale_but_cannot_grant_current_approval(
    tmp_path: Path, sanitized_git_process_environment: None
) -> None:
    directory = init_git_repository(tmp_path)
    write_json(
        directory / "prior.json",
        signoff(
            evaluation_id="evaluation_old",
            evidence_digest="sha256:old",
            reviewer_id="project_owner",
            rationale=GOVERNANCE_RATIONALE,
            **VALID_APPROVAL_BINDING,
        ),
    )
    commit_paths(tmp_path, "add prior dialog", "harness/signoffs/prior.json")

    result = validate_signoff_directory(
        directory, replace(context(), repository_root=str(tmp_path))
    )

    assert result.valid_roles == ()
    assert result.missing_roles == ("governance_owner",)
    assert result.invalid_signoffs == ()
    assert tuple(issue.path for issue in result.stale_signoffs) == ("prior.json",)


@pytest.mark.parametrize("spoof", ["replace", "graft"])
def test_production_supersedes_ignores_replacement_history_spoofing(
    tmp_path: Path,
    sanitized_git_process_environment: None,
    spoof: str,
) -> None:
    directory = init_git_repository(tmp_path)
    same_commit, fabricated_parent = create_same_commit_signoffs_with_fabricated_parent(
        tmp_path, directory
    )
    if spoof == "replace":
        run_git(tmp_path, "replace", "--graft", same_commit, fabricated_parent)
    else:
        grafts = tmp_path / ".git/info/grafts"
        grafts.parent.mkdir(parents=True, exist_ok=True)
        grafts.write_text(
            f"{same_commit} {fabricated_parent}\n",
            encoding="ascii",
        )

    result = validate_signoff_directory(
        directory,
        replace(context(), repository_root=str(tmp_path)),
    )

    assert [
        issue.reason_code
        for issue in result.invalid_signoffs
        if issue.path == "current.json"
    ] == ["signoff_supersedes_invalid"]


def test_production_signoff_validation_disables_repository_fsmonitor(
    tmp_path: Path,
    sanitized_git_process_environment: None,
) -> None:
    directory = init_git_repository(tmp_path)
    write_json(directory / "approval.json", signoff())
    commit_paths(tmp_path, "approve", "harness/signoffs/approval.json")
    marker = tmp_path.parent / f".{tmp_path.name}-fsmonitor-executed"
    fsmonitor = tmp_path.parent / f".{tmp_path.name}-fsmonitor.sh"
    fsmonitor.write_text(
        f"#!/bin/sh\ntouch '{marker}'\nprintf '\\n'\n",
        encoding="utf-8",
    )
    fsmonitor.chmod(0o755)
    run_git(tmp_path, "config", "core.fsmonitor", str(fsmonitor))

    result = validate_signoff_directory(
        directory,
        replace(context(), repository_root=str(tmp_path)),
    )

    assert result.valid_roles == ("governance_owner",)
    assert result.invalid_signoffs == ()
    assert not marker.exists()


def test_ambient_git_repository_cannot_trust_an_uncommitted_signoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sanitized_git_process_environment: None,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    trusted_directory = init_git_repository(trusted)
    write_json(trusted_directory / "approval.json", signoff())
    commit_paths(trusted, "trusted approval", "harness/signoffs/approval.json")

    victim = tmp_path / "victim"
    victim.mkdir()
    victim_directory = init_git_repository(victim)
    write_json(victim_directory / "approval.json", signoff())
    monkeypatch.setenv("GIT_DIR", str(trusted / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(trusted))

    result = validate_signoff_directory(
        victim_directory,
        replace(context(), repository_root=str(victim)),
    )

    assert result.valid_roles == ()
    assert result.invalid_signoffs[0].reason_code == "signoff_file_untrusted"


def test_ambient_git_repository_cannot_hide_same_commit_supersession(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sanitized_git_process_environment: None,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    trusted_directory = init_git_repository(trusted)
    write_json(trusted_directory / "prior.json", signoff(reviewer_id="old"))
    commit_paths(trusted, "trusted prior", "harness/signoffs/prior.json")
    write_json(
        trusted_directory / "current.json",
        signoff(reviewer_id="new", supersedes="prior.json"),
    )
    commit_paths(trusted, "trusted current", "harness/signoffs/current.json")

    victim = tmp_path / "victim"
    victim.mkdir()
    victim_directory = init_git_repository(victim)
    write_json(victim_directory / "prior.json", signoff(reviewer_id="old"))
    write_json(
        victim_directory / "current.json",
        signoff(reviewer_id="new", supersedes="prior.json"),
    )
    commit_paths(
        victim,
        "victim same commit",
        "harness/signoffs/prior.json",
        "harness/signoffs/current.json",
    )
    monkeypatch.setenv("GIT_DIR", str(trusted / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(trusted))

    result = validate_signoff_directory(
        victim_directory,
        replace(context(), repository_root=str(victim)),
    )

    assert [
        issue.reason_code
        for issue in result.invalid_signoffs
        if issue.path == "current.json"
    ] == ["signoff_supersedes_invalid"]
