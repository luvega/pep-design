from __future__ import annotations

from dataclasses import dataclass


CARD_SCHEMA_VERSION = "1.0"
APPROVAL_PROFILE_IDS = ("governance", "current_phase")

GOVERNANCE_RATIONALE = (
    "仅批准 contract/registry/migration/validator 的治理完整性；不豁免任何失败 "
    "gate，也不批准 release_checkpoint 或 full_project。"
)
CURRENT_PHASE_RATIONALE = (
    "接受 v0.33 的诚实边界：10 条 method-specific blockers，0 个 "
    "parsed/generated candidates，target/control 尚未冻结，scoring/ranking 尚未启动。"
)
PROFILE_RATIONALES = {
    "governance": GOVERNANCE_RATIONALE,
    "current_phase": CURRENT_PHASE_RATIONALE,
}


class ApprovalError(RuntimeError):
    """Raised when an approval artifact fails a fail-closed validation."""


@dataclass(frozen=True)
class SourceEntry:
    path: str
    status: str
    mode: str | None
    sha256: str | None


@dataclass(frozen=True)
class ProfileApproval:
    profile_id: str
    gate_result_digest: str
    gate_count: int
    rationale: str
    signoff_filename: str
    supersedes: str | None


@dataclass(frozen=True)
class ApprovalCard:
    card_id: str
    card_sha256: str
    schema_version: str
    nonce: str
    created_at: str
    expires_at: str
    contract_id: str
    contract_version: str
    contract_digest: str
    evaluator_version: str
    registry_digest: str
    evaluation_id: str
    evidence_digest: str
    reviewer_id: str
    head_oid: str
    remote_name: str
    remote_url: str
    remote_ref: str
    remote_oid: str
    proposed_tree_oid: str
    diff_stat: str
    ahead_commits: tuple[str, ...]
    source_manifest: tuple[SourceEntry, ...]
    profiles: tuple[ProfileApproval, ...]
