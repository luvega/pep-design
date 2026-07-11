from __future__ import annotations

import re
from datetime import datetime

from .models import ApprovalCard, ApprovalError


def _require_review_timestamp(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ApprovalError("reviewed_at is required")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalError("reviewed_at must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ApprovalError("reviewed_at must include a timezone")


def build_signoff_payloads(
    card: ApprovalCard,
    *,
    reviewed_at: str,
    approval_event_id: str,
) -> dict[str, dict[str, object]]:
    """Build the two profile-bound decisions without mutable overrides."""

    _require_review_timestamp(reviewed_at)
    if not isinstance(approval_event_id, str) or re.fullmatch(
        r"approval_event_[0-9a-f]{24}", approval_event_id
    ) is None:
        raise ApprovalError("approval_event_id must use its canonical format")

    return {
        profile.signoff_filename: {
            "contract_id": card.contract_id,
            "contract_version": card.contract_version,
            "contract_digest": card.contract_digest,
            "profile_id": profile.profile_id,
            "evaluation_id": card.evaluation_id,
            "evidence_digest": card.evidence_digest,
            "role": "governance_owner",
            "reviewer_id": card.reviewer_id,
            "decision": "approved",
            "rationale": profile.rationale,
            "reviewed_at": reviewed_at,
            "supersedes": profile.supersedes,
            "approval_card_id": card.card_id,
            "approval_card_digest": card.card_sha256,
            "approval_event_id": approval_event_id,
        }
        for profile in card.profiles
    }
