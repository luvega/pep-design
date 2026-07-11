from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class Severity(str, Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    ADVISORY = "Advisory"


class GateVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


class HarnessStatus(str, Enum):
    VALID = "valid"
    ERROR = "error"


class ProjectVerdict(str, Enum):
    ACCEPTED = "accepted"
    NOT_ACCEPTED = "not_accepted"
    BLOCKED = "blocked"
    PENDING_HUMAN_SIGNOFF = "pending_human_signoff"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    domain: str
    severity: Severity
    verdict: GateVerdict
    reason_code: str
    message: str
    evidence: tuple[str, ...]
    failure_status: ProjectVerdict = ProjectVerdict.NOT_ACCEPTED
    details: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class ProfileResult:
    profile_id: str
    harness_status: HarnessStatus
    project_status: ProjectVerdict
    reason_codes: tuple[str, ...] = ()
    missing_signoff_roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    evaluation_id: str
    contract_id: str
    contract_version: str
    evaluator_version: str
    profile: ProfileResult
    gate_results: tuple[GateResult, ...]
    contract_digest: str
    registry_digest: str
    evidence_digest: str
    evidence_digests: tuple[tuple[str, str], ...]
    required_signoff_roles: tuple[str, ...] = ()
    valid_signoff_roles: tuple[str, ...] = ()
    stale_signoff_files: tuple[str, ...] = ()
    invalid_signoff_files: tuple[str, ...] = ()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def make_evaluation_id(
    *,
    contract_digest: str,
    registry_digest: str,
    evaluator_version: str,
    evidence_digests: Mapping[str, str],
) -> str:
    digest = canonical_digest(
        {
            "contract_digest": contract_digest,
            "registry_digest": registry_digest,
            "evaluator_version": evaluator_version,
            "evidence_digests": dict(evidence_digests),
        }
    )
    return f"evaluation_{digest[:24]}"
