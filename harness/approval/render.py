from __future__ import annotations

import re
from pathlib import Path

from .models import ApprovalCard, ApprovalError


def _manifest_path(value: str | Path, card: ApprovalCard) -> str:
    raw = str(value)
    expected = f"ops/acceptance/dialog_cards/{card.card_id}.json"
    if raw != expected:
        raise ApprovalError("approval card manifest path is not canonical or mismatched")
    return raw


def _code(value: object) -> str:
    raw = str(value)
    longest = max((len(run) for run in re.findall(r"`+", raw)), default=0)
    fence = "`" * (longest + 1)
    padding = " " if raw.startswith(("`", " ")) or raw.endswith(("`", " ")) else ""
    return f"{fence}{padding}{raw}{padding}{fence}"


def render_approval_card(
    card: ApprovalCard,
    *,
    card_path: str | Path,
) -> str:
    """Render the complete dialog binding without exposing the raw card JSON."""

    if not isinstance(card, ApprovalCard):
        raise ApprovalError("approval card renderer requires an ApprovalCard")
    manifest = _manifest_path(card_path, card)
    lines = [
        "# Pep Design 对话审批卡",
        "",
        f"- Card ID: {_code(card.card_id)}",
        f"- Card SHA-256: {_code(card.card_sha256)}",
        f"- Evaluation ID: {_code(card.evaluation_id)}",
        f"- Evidence digest: {_code(card.evidence_digest)}",
        f"- Contract digest: {_code(card.contract_digest)}",
        f"- Registry digest: {_code(card.registry_digest)}",
        f"- Reviewer: {_code(card.reviewer_id)}",
        f"- 创建时间: {_code(card.created_at)}",
        f"- 过期时间: {_code(card.expires_at)}",
        f"- 初始 HEAD: {_code(card.head_oid)}",
        f"- Proposed tree: {_code(card.proposed_tree_oid)}",
        f"- Remote URL: {_code(card.remote_url)}",
        f"- Remote OID: {_code(card.remote_oid)}",
        f"- Remote ref: {_code(card.remote_ref)}",
        f"- Source 文件数: {_code(len(card.source_manifest))}",
        f"- Diff stat: {_code(card.diff_stat)}",
        f"- Manifest: {_code(manifest)}",
        "",
        "## Profiles 与签核",
        "",
    ]
    for profile in card.profiles:
        supersedes = profile.supersedes or "无（首次签核）"
        lines.extend(
            [
                (
                    f"- {_code(profile.profile_id)}: gate count "
                    f"{_code(profile.gate_count)}; gate digest "
                    f"{_code(profile.gate_result_digest)}"
                ),
                f"  - Rationale: {_code(profile.rationale)}",
                (
                    f"  - Signoff: {_code(profile.signoff_filename)}; "
                    f"supersedes: {_code(supersedes)}"
                ),
            ]
        )
    lines.extend(["", "## 将一并推送的既有 commits", ""])
    if card.ahead_commits:
        lines.extend(f"- {_code(commit)}" for commit in card.ahead_commits)
    else:
        lines.append("- 无")
    lines.extend(
        [
            "",
            "## 授权边界",
            "",
            "本次不批准 release_checkpoint 或 full_project。",
            "本次不表示 Benchmark 完成。",
            "本次不授权 clone/download/GPU/generation/scoring/ranking。",
            "",
            "回复：批准",
        ]
    )
    return "\n".join(lines)


__all__ = ["render_approval_card"]
