from __future__ import annotations

from copy import deepcopy

import pytest

from harness.engine.evaluator import exit_code_for, roll_up_profile
from harness.engine.models import (
    GateResult,
    GateVerdict,
    HarnessStatus,
    ProjectVerdict,
    Severity,
    canonical_digest,
    make_evaluation_id,
)


def gate_result(
    gate_id: str,
    *,
    severity: Severity = Severity.CRITICAL,
    verdict: GateVerdict = GateVerdict.PASS,
    failure_status: ProjectVerdict = ProjectVerdict.NOT_ACCEPTED,
) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        domain="repository_provenance",
        severity=severity,
        verdict=verdict,
        reason_code="test_reason",
        message="test message",
        evidence=(),
        failure_status=failure_status,
    )


def test_canonical_digest_is_independent_of_mapping_order() -> None:
    left = {"b": [2, 1], "a": {"x": True}}
    right = {"a": {"x": True}, "b": [2, 1]}

    assert canonical_digest(left) == canonical_digest(right)


def test_evaluation_id_excludes_render_timestamp_by_interface() -> None:
    first = make_evaluation_id(
        contract_digest="contract",
        registry_digest="registry",
        evaluator_version="1.0.0",
        evidence_digests={"artifact_b": "b", "artifact_a": "a"},
    )
    second = make_evaluation_id(
        contract_digest="contract",
        registry_digest="registry",
        evaluator_version="1.0.0",
        evidence_digests={"artifact_a": "a", "artifact_b": "b"},
    )

    assert first == second


def test_rollup_requires_every_declared_gate() -> None:
    profile = {
        "profile_id": "governance",
        "required_gate_ids": ["gate_a", "gate_b"],
        "required_signoff_roles": [],
    }

    result = roll_up_profile(profile, {"gate_a": gate_result("gate_a")}, set())

    assert result.harness_status is HarnessStatus.ERROR
    assert result.project_status is ProjectVerdict.NOT_ACCEPTED
    assert "gate_b" in result.reason_codes


def test_critical_failure_is_not_accepted() -> None:
    profile = {
        "profile_id": "governance",
        "required_gate_ids": ["gate_a"],
        "required_signoff_roles": [],
    }

    result = roll_up_profile(
        profile,
        {"gate_a": gate_result("gate_a", verdict=GateVerdict.FAIL)},
        set(),
    )

    assert result.project_status is ProjectVerdict.NOT_ACCEPTED
    assert exit_code_for(result) == 1


def test_advisory_failure_does_not_block_acceptance() -> None:
    profile = {
        "profile_id": "governance",
        "required_gate_ids": ["gate_a"],
        "required_signoff_roles": [],
    }

    result = roll_up_profile(
        profile,
        {
            "gate_a": gate_result(
                "gate_a", severity=Severity.ADVISORY, verdict=GateVerdict.FAIL
            )
        },
        set(),
    )

    assert result.project_status is ProjectVerdict.ACCEPTED
    assert exit_code_for(result) == 0


def test_external_blocker_rolls_up_as_blocked() -> None:
    profile = {
        "profile_id": "current_phase",
        "required_gate_ids": ["external_asset"],
        "required_signoff_roles": [],
    }

    result = roll_up_profile(
        profile,
        {
            "external_asset": gate_result(
                "external_asset",
                verdict=GateVerdict.FAIL,
                failure_status=ProjectVerdict.BLOCKED,
            )
        },
        set(),
    )

    assert result.project_status is ProjectVerdict.BLOCKED
    assert exit_code_for(result) == 1


def test_machine_pass_without_required_signoff_is_pending() -> None:
    profile = {
        "profile_id": "governance",
        "required_gate_ids": ["gate_a"],
        "required_signoff_roles": ["governance_owner"],
    }

    result = roll_up_profile(profile, {"gate_a": gate_result("gate_a")}, set())

    assert result.project_status is ProjectVerdict.PENDING_HUMAN_SIGNOFF
    assert result.missing_signoff_roles == ("governance_owner",)
    assert exit_code_for(result) == 1


def test_machine_pass_with_required_signoff_is_accepted() -> None:
    profile = {
        "profile_id": "governance",
        "required_gate_ids": ["gate_a"],
        "required_signoff_roles": ["governance_owner"],
    }

    result = roll_up_profile(
        profile,
        {"gate_a": gate_result("gate_a")},
        {"governance_owner"},
    )

    assert result.harness_status is HarnessStatus.VALID
    assert result.project_status is ProjectVerdict.ACCEPTED
    assert result.missing_signoff_roles == ()
    assert exit_code_for(result) == 0


def test_internal_error_has_exit_code_two() -> None:
    profile = {
        "profile_id": "governance",
        "required_gate_ids": ["missing"],
        "required_signoff_roles": [],
    }
    result = roll_up_profile(profile, {}, set())

    assert result.harness_status is HarnessStatus.ERROR
    assert exit_code_for(result) == 2


def test_only_contract_can_make_profile_not_applicable() -> None:
    profile = {
        "profile_id": "optional",
        "required_gate_ids": ["gate_a"],
        "required_signoff_roles": [],
        "applicable": False,
    }

    result = roll_up_profile(profile, {"gate_a": gate_result("gate_a")}, set())

    assert result.project_status is ProjectVerdict.NOT_APPLICABLE


def test_digest_changes_when_evidence_changes() -> None:
    evidence = {"artifact": {"rows": 10, "parsed": 0}}
    changed = deepcopy(evidence)
    changed["artifact"]["parsed"] = 1

    assert canonical_digest(evidence) != canonical_digest(changed)


def test_unknown_project_verdict_is_not_silently_accepted() -> None:
    with pytest.raises(ValueError):
        exit_code_for("accepted")  # type: ignore[arg-type]
