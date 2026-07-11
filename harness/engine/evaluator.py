from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from dataclasses import replace
from typing import Any

from .models import (
    GateResult,
    GateVerdict,
    HarnessStatus,
    ProfileResult,
    ProjectVerdict,
    Severity,
)


def resolve_gate_dependencies(
    gates: Sequence[Mapping[str, Any]],
    raw_results: Mapping[str, GateResult],
) -> dict[str, GateResult]:
    """Fail closed when a gate's declared prerequisites have not passed."""
    gate_by_id = {str(gate["gate_id"]): gate for gate in gates}
    resolved: dict[str, GateResult] = {}
    visiting: set[str] = set()

    def resolve(gate_id: str) -> GateResult:
        if gate_id in resolved:
            return resolved[gate_id]
        if gate_id in visiting:
            raise ValueError(f"dependency cycle reached at runtime: {gate_id}")
        visiting.add(gate_id)
        gate = gate_by_id[gate_id]
        dependencies = [resolve(str(item)) for item in gate.get("requires", ())]
        raw = raw_results.get(gate_id)
        if raw is None:
            raw = GateResult(
                gate_id=gate_id,
                domain=str(gate["domain"]),
                severity=Severity(str(gate["severity"])),
                verdict=GateVerdict.ERROR,
                reason_code="missing_gate_result",
                message=f"Evaluator did not return a result for {gate_id}.",
                evidence=(),
            )
        if raw.verdict is GateVerdict.ERROR:
            result = raw
        elif any(item.verdict is GateVerdict.ERROR for item in dependencies):
            result = replace(
                raw,
                verdict=GateVerdict.ERROR,
                reason_code="dependency_error",
                message="A required gate has a harness evaluation error.",
            )
        elif any(item.verdict is not GateVerdict.PASS for item in dependencies):
            failure_status = (
                ProjectVerdict.BLOCKED
                if any(
                    item.failure_status is ProjectVerdict.BLOCKED
                    for item in dependencies
                )
                else ProjectVerdict.NOT_ACCEPTED
            )
            result = replace(
                raw,
                verdict=GateVerdict.PENDING,
                reason_code="dependency_not_satisfied",
                message="One or more required gates have not passed.",
                failure_status=failure_status,
            )
        else:
            result = raw
        visiting.remove(gate_id)
        resolved[gate_id] = result
        return result

    for gate_id in gate_by_id:
        resolve(gate_id)
    return resolved


def roll_up_profile(
    profile: Mapping[str, Any],
    gate_results: Mapping[str, GateResult],
    valid_signoff_roles: Set[str],
) -> ProfileResult:
    profile_id = str(profile["profile_id"])
    if profile.get("applicable", True) is False:
        return ProfileResult(
            profile_id, HarnessStatus.VALID, ProjectVerdict.NOT_APPLICABLE
        )

    required_gate_ids = tuple(str(item) for item in profile.get("required_gate_ids", ()))
    missing_gate_ids = tuple(
        gate_id for gate_id in required_gate_ids if gate_id not in gate_results
    )
    if missing_gate_ids:
        return ProfileResult(
            profile_id,
            HarnessStatus.ERROR,
            ProjectVerdict.NOT_ACCEPTED,
            missing_gate_ids,
        )

    required_results = [gate_results[gate_id] for gate_id in required_gate_ids]
    error_codes = tuple(
        result.reason_code
        for result in required_results
        if result.verdict is GateVerdict.ERROR
    )
    if error_codes:
        return ProfileResult(
            profile_id,
            HarnessStatus.ERROR,
            ProjectVerdict.NOT_ACCEPTED,
            error_codes,
        )

    blocking_results = [
        result
        for result in required_results
        if result.verdict in {GateVerdict.FAIL, GateVerdict.PENDING}
        and result.severity in {Severity.CRITICAL, Severity.MAJOR}
    ]
    if blocking_results:
        reason_codes = tuple(
            dict.fromkeys(result.reason_code for result in blocking_results)
        )
        verdict = (
            ProjectVerdict.BLOCKED
            if any(
                result.failure_status is ProjectVerdict.BLOCKED
                for result in blocking_results
            )
            else ProjectVerdict.NOT_ACCEPTED
        )
        return ProfileResult(
            profile_id, HarnessStatus.VALID, verdict, reason_codes
        )

    required_roles = tuple(
        str(role) for role in profile.get("required_signoff_roles", ())
    )
    missing_roles = tuple(
        role for role in required_roles if role not in valid_signoff_roles
    )
    if missing_roles:
        return ProfileResult(
            profile_id,
            HarnessStatus.VALID,
            ProjectVerdict.PENDING_HUMAN_SIGNOFF,
            missing_signoff_roles=missing_roles,
        )

    return ProfileResult(
        profile_id, HarnessStatus.VALID, ProjectVerdict.ACCEPTED
    )


def exit_code_for(result: ProfileResult) -> int:
    if not isinstance(result, ProfileResult):
        raise ValueError(f"Expected ProfileResult, received: {result!r}")
    if result.harness_status is HarnessStatus.ERROR:
        return 2
    if result.project_status is ProjectVerdict.ACCEPTED:
        return 0
    return 1
