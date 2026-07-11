from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from harness.approval import cards as cards_module
from harness.approval.cards import (
    create_approval_card,
    is_exact_approval_message,
    load_approval_card,
    write_approval_card,
)
from harness.approval.models import ApprovalError
from harness.approval.signoff_payloads import build_signoff_payloads
from harness.engine.models import canonical_json


NOW = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
NONCE = b"0" * 16
EVENT_ID = "approval_event_" + "1" * 24
_UNSET = object()

GOVERNANCE_RATIONALE = (
    "仅批准 contract/registry/migration/validator 的治理完整性；不豁免任何失败 "
    "gate，也不批准 release_checkpoint 或 full_project。"
)
CURRENT_PHASE_RATIONALE = (
    "接受 v0.33 的诚实边界：10 条 method-specific blockers，0 个 "
    "parsed/generated candidates，target/control 尚未冻结，scoring/ranking 尚未启动。"
)


def profile_input(
    profile_id: str,
    *,
    rationale: object = _UNSET,
    signoff_filename: object = _UNSET,
    supersedes: object = _UNSET,
) -> dict[str, object]:
    defaults = {
        "governance": {
            "gate_result_digest": "1" * 64,
            "gate_count": 4,
            "rationale": GOVERNANCE_RATIONALE,
            "signoff_filename": "signoff_governance_v2.json",
            "supersedes": "signoff_governance_v1.json",
        },
        "current_phase": {
            "gate_result_digest": "2" * 64,
            "gate_count": 11,
            "rationale": CURRENT_PHASE_RATIONALE,
            "signoff_filename": "signoff_current_phase_v1.json",
            "supersedes": None,
        },
    }
    selected = defaults.get(
        profile_id,
        {
            "gate_result_digest": "3" * 64,
            "gate_count": 1,
            "rationale": "Unsupported profile rationale.",
            "signoff_filename": f"signoff_{profile_id}_v1.json",
            "supersedes": None,
        },
    )
    return {
        "profile_id": profile_id,
        "gate_result_digest": selected["gate_result_digest"],
        "gate_count": selected["gate_count"],
        "rationale": selected["rationale"] if rationale is _UNSET else rationale,
        "signoff_filename": (
            selected["signoff_filename"]
            if signoff_filename is _UNSET
            else signoff_filename
        ),
        "supersedes": (
            selected["supersedes"] if supersedes is _UNSET else supersedes
        ),
    }


def card_input(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
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
        "diff_stat": "3 files changed, 8 insertions(+), 1 deletion(-)",
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
            profile_input("governance"),
            profile_input("current_phase"),
        ),
    }
    value.update(overrides)
    return value


def binding_payload(card: object) -> dict[str, object]:
    payload = asdict(card)  # type: ignore[arg-type]
    payload.pop("card_id")
    payload.pop("card_sha256")
    return payload


def write_rebound_card(
    root: Path, raw: dict[str, object]
) -> tuple[Path, str]:
    rebound = dict(raw)
    rebound.pop("card_id")
    rebound.pop("card_sha256")
    digest = hashlib.sha256(canonical_json(rebound).encode("utf-8")).hexdigest()
    raw["card_sha256"] = digest
    raw["card_id"] = f"approval_{digest[:24]}"
    path = root / f"approval_{digest[:24]}.json"
    path.write_text(canonical_json(raw) + "\n", encoding="utf-8")
    return path, digest


def set_path_field(
    value: dict[str, object], field: str, path: str
) -> None:
    if field == "source_manifest":
        manifest = copy.deepcopy(list(value["source_manifest"]))
        manifest[0]["path"] = path
        value["source_manifest"] = tuple(manifest)
        return
    profiles = copy.deepcopy(list(value["profiles"]))
    profiles[0][field] = path
    value["profiles"] = tuple(profiles)


def test_card_id_is_canonical_stable_and_loadable(tmp_path: Path) -> None:
    first = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    second = create_approval_card(card_input(), now=NOW, nonce=NONCE)

    expected_digest = hashlib.sha256(
        canonical_json(binding_payload(first)).encode("utf-8")
    ).hexdigest()
    assert first == second
    assert first.card_sha256 == expected_digest
    assert first.card_id == f"approval_{expected_digest[:24]}"
    assert first.created_at == "2026-07-10T12:00:00+00:00"
    assert first.expires_at == "2026-07-10T13:00:00+00:00"
    assert re.fullmatch(r"[0-9a-f]{32}", first.nonce)
    assert bytes.fromhex(first.nonce) == NONCE

    path = write_approval_card(first, tmp_path)

    assert path == tmp_path / f"{first.card_id}.json"
    assert path.stat().st_mode & 0o777 == 0o600
    serialized = json.loads(path.read_text(encoding="utf-8"))
    assert bytes.fromhex(serialized["nonce"]) == NONCE
    assert load_approval_card(path, first.card_sha256, now=NOW) == first


def test_distinct_injected_nonces_produce_distinct_card_bindings() -> None:
    first = create_approval_card(card_input(), now=NOW, nonce=b"0" * 16)
    second = create_approval_card(card_input(), now=NOW, nonce=b"1" * 16)

    assert bytes.fromhex(first.nonce) == b"0" * 16
    assert bytes.fromhex(second.nonce) == b"1" * 16
    assert first.card_sha256 != second.card_sha256
    assert first.card_id != second.card_id


def test_default_nonce_uses_fresh_cryptographic_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supplied = iter((b"a" * 16, b"b" * 16))
    requested_sizes: list[int] = []

    def fake_token_bytes(size: int) -> bytes:
        requested_sizes.append(size)
        return next(supplied)

    monkeypatch.setattr("secrets.token_bytes", fake_token_bytes)

    first = create_approval_card(card_input(), now=NOW)
    second = create_approval_card(card_input(), now=NOW)

    assert requested_sizes == [16, 16]
    assert first.nonce == (b"a" * 16).hex()
    assert second.nonce == (b"b" * 16).hex()
    assert re.fullmatch(r"[0-9a-f]{32}", first.nonce)
    assert re.fullmatch(r"[0-9a-f]{32}", second.nonce)
    assert first.card_sha256 != second.card_sha256
    assert first.card_id != second.card_id


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("批准", True),
        (" \t批准\n", True),
        ("\u3000批准\u3000", True),
        ("批准。", False),
        ('"批准"', False),
        ("我批准", False),
        ("不批准", False),
        ("批准\n继续", False),
        ("批准 # approval", False),
        ("", False),
    ],
)
def test_only_exact_nfc_and_trim_normalized_approval_message_is_accepted(
    message: str, expected: bool
) -> None:
    assert is_exact_approval_message(message) is expected


def test_load_rejects_an_unexpected_full_digest(tmp_path: Path) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    path = write_approval_card(card, tmp_path)

    with pytest.raises(ApprovalError, match="digest|sha256|integrity"):
        load_approval_card(path, "f" * 64, now=NOW)


@pytest.mark.parametrize(
    "expected_digest_kind",
    ["correct-prefix", "algorithm-prefix", "too-short", "uppercase", "non-hex"],
)
def test_load_requires_a_full_canonical_expected_digest(
    tmp_path: Path, expected_digest_kind: str
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    path = write_approval_card(card, tmp_path)
    values = {
        "correct-prefix": card.card_sha256[:24],
        "algorithm-prefix": f"sha256:{card.card_sha256}",
        "too-short": card.card_sha256[:-1],
        "uppercase": card.card_sha256.upper(),
        "non-hex": "z" * 64,
    }

    with pytest.raises(ApprovalError, match="expected|digest|sha256|canonical"):
        load_approval_card(path, values[expected_digest_kind], now=NOW)


@pytest.mark.parametrize(
    ("field", "corrupted_value"),
    [
        ("card_id", "approval_" + "f" * 24),
        ("card_sha256", "f" * 64),
    ],
)
def test_load_rejects_corrupted_embedded_card_identifiers(
    tmp_path: Path, field: str, corrupted_value: str
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    raw = asdict(card)
    raw[field] = corrupted_value
    path = tmp_path / f"{card.card_id}.json"
    path.write_text(canonical_json(raw) + "\n", encoding="utf-8")

    with pytest.raises(ApprovalError, match="card|id|digest|sha256|integrity"):
        load_approval_card(path, card.card_sha256, now=NOW)


def test_load_rejects_tampered_card_bytes(tmp_path: Path) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    path = write_approval_card(card, tmp_path)
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["diff_stat"] = "no changes"
    path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ApprovalError, match="digest|sha256|integrity"):
        load_approval_card(path, card.card_sha256, now=NOW)


def test_strict_load_rejects_unknown_fields_even_with_a_matching_digest(
    tmp_path: Path,
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    raw = asdict(card)
    raw["unexpected"] = "not part of the card schema"
    path, digest = write_rebound_card(tmp_path, raw)

    with pytest.raises(ApprovalError, match="field|schema|unexpected"):
        load_approval_card(path, digest, now=NOW)


@pytest.mark.parametrize(
    ("scope", "field"),
    [
        ("top-level", "schema_version"),
        ("top-level", "reviewer_id"),
        ("top-level", "remote_oid"),
        ("source_manifest", "path"),
        ("source_manifest", "status"),
        ("source_manifest", "mode"),
        ("source_manifest", "sha256"),
        ("profiles", "profile_id"),
        ("profiles", "gate_result_digest"),
        ("profiles", "gate_count"),
        ("profiles", "rationale"),
        ("profiles", "signoff_filename"),
        ("profiles", "supersedes"),
    ],
)
def test_strict_load_rejects_redigested_cards_missing_required_fields(
    tmp_path: Path, scope: str, field: str
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    raw = asdict(card)
    if scope == "top-level":
        raw.pop(field)
    elif scope == "source_manifest":
        raw["source_manifest"][0].pop(field)
    else:
        raw["profiles"][0].pop(field)
    path, digest = write_rebound_card(tmp_path, raw)

    with pytest.raises(ApprovalError, match="field|schema|required|missing"):
        load_approval_card(path, digest, now=NOW)


@pytest.mark.parametrize(
    ("field", "malicious_path"),
    [
        ("source_manifest", "../README.md"),
        ("source_manifest", "/tmp/README.md"),
        ("source_manifest", "retired.txt"),
        (
            "source_manifest",
            "ops/acceptance/dialog_cards/approval_bad.json",
        ),
        ("signoff_filename", "../signoff_governance_v2.json"),
        ("signoff_filename", "/tmp/signoff_governance_v2.json"),
        ("supersedes", "../signoff_governance_v1.json"),
        ("supersedes", "/tmp/signoff_governance_v1.json"),
    ],
)
def test_strict_load_rejects_redigested_cards_with_unsafe_paths(
    tmp_path: Path, field: str, malicious_path: str
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    raw = asdict(card)
    set_path_field(raw, field, malicious_path)
    path, digest = write_rebound_card(tmp_path, raw)

    with pytest.raises(
        ApprovalError,
        match="path|filename|supersedes|unsafe|absolute|traversal",
    ):
        load_approval_card(path, digest, now=NOW)


@pytest.mark.parametrize(
    ("field", "malicious_path"),
    [
        ("source_manifest", "../README.md"),
        ("source_manifest", "/tmp/README.md"),
        ("source_manifest", "retired.txt"),
        (
            "source_manifest",
            "harness/signoffs/signoff_governance_v2.json",
        ),
        ("signoff_filename", "../signoff_governance_v2.json"),
        ("signoff_filename", "/tmp/signoff_governance_v2.json"),
        ("supersedes", "../signoff_governance_v1.json"),
        ("supersedes", "/tmp/signoff_governance_v1.json"),
    ],
)
def test_create_rejects_unsafe_paths(field: str, malicious_path: str) -> None:
    value = card_input()
    set_path_field(value, field, malicious_path)

    with pytest.raises(
        ApprovalError,
        match="path|filename|supersedes|unsafe|absolute|traversal",
    ):
        create_approval_card(value, now=NOW, nonce=NONCE)


@pytest.mark.parametrize("mode", ["100600", "120000", "160000", None])
def test_create_rejects_non_regular_source_modes(mode: str | None) -> None:
    value = card_input()
    manifest = copy.deepcopy(list(value["source_manifest"]))
    manifest[0]["mode"] = mode
    value["source_manifest"] = tuple(manifest)

    with pytest.raises(ApprovalError, match="mode|100644|100755"):
        create_approval_card(value, now=NOW, nonce=NONCE)


@pytest.mark.parametrize(
    "remote_url",
    [
        "https://github.com/luvega/pep-design.git",
        "git@github.com:luvega/other.git",
        "/tmp/remote.git",
    ],
)
def test_create_rejects_any_other_remote_url(remote_url: str) -> None:
    with pytest.raises(ApprovalError, match="remote_url|pep-design"):
        create_approval_card(
            card_input(remote_url=remote_url),
            now=NOW,
            nonce=NONCE,
        )


def test_card_expires_after_sixty_minutes(tmp_path: Path) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    path = write_approval_card(card, tmp_path)

    assert (
        load_approval_card(
            path,
            card.card_sha256,
            now=NOW + timedelta(minutes=59, seconds=59),
        )
        == card
    )
    with pytest.raises(ApprovalError, match="expired"):
        load_approval_card(
            path,
            card.card_sha256,
            now=NOW + timedelta(hours=1),
        )


@pytest.mark.parametrize(
    "profile_ids",
    [
        ("governance",),
        ("current_phase", "governance"),
        ("governance", "release_checkpoint"),
        ("governance", "full_project"),
        ("governance", "governance"),
        ("governance", "current_phase", "release_checkpoint"),
        ("governance", "current_phase", "full_project"),
    ],
)
def test_card_requires_the_exact_ordered_bundled_profile_set(
    profile_ids: tuple[str, ...],
) -> None:
    profiles = tuple(profile_input(profile_id) for profile_id in profile_ids)

    with pytest.raises(ApprovalError, match="profile"):
        create_approval_card(card_input(profiles=profiles), now=NOW, nonce=NONCE)


@pytest.mark.parametrize(
    ("profile_index", "filename"),
    [
        (0, "signoff_current_phase_v2.json"),
        (1, "signoff_governance_v2.json"),
        (0, "governance.json"),
        (1, "../signoff_current_phase_v1.json"),
    ],
)
def test_profile_identity_must_match_its_safe_versioned_signoff_filename(
    profile_index: int, filename: str
) -> None:
    value = card_input()
    profiles = copy.deepcopy(list(value["profiles"]))
    profiles[profile_index]["signoff_filename"] = filename
    value["profiles"] = tuple(profiles)

    with pytest.raises(ApprovalError, match="filename|profile|path"):
        create_approval_card(value, now=NOW, nonce=NONCE)


@pytest.mark.parametrize("nonce", [b"", b"x" * 15, b"x" * 17])
def test_nonce_must_be_exactly_128_bits(nonce: bytes) -> None:
    with pytest.raises(ApprovalError, match="nonce|128"):
        create_approval_card(card_input(), now=NOW, nonce=nonce)


def test_immutable_card_write_rejects_overwrite_without_changing_bytes(
    tmp_path: Path,
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    path = write_approval_card(card, tmp_path)
    original = path.read_bytes()

    with pytest.raises(ApprovalError, match="exists|overwrite|immutable"):
        write_approval_card(card, tmp_path)

    assert path.read_bytes() == original


def test_card_load_rejects_a_symlink_even_when_target_is_valid(tmp_path: Path) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    target = write_approval_card(card, tmp_path / "target")
    link_root = tmp_path / "links"
    link_root.mkdir()
    link = link_root / target.name
    link.symlink_to(target)

    with pytest.raises(ApprovalError, match="open|safe|regular|symlink"):
        load_approval_card(link, card.card_sha256, now=NOW)


def test_card_load_reads_only_the_inode_opened_before_a_path_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    path = write_approval_card(card, tmp_path)
    replacement = tmp_path / "replacement.json"
    replacement.write_text("{}\n", encoding="utf-8")
    real_open = os.open
    swapped = False

    def swapping_open(
        value: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        descriptor = real_open(value, flags, mode, dir_fd=dir_fd)
        is_read = not flags & (os.O_WRONLY | os.O_RDWR)
        if not swapped and is_read and Path(value) == path:
            swapped = True
            os.replace(replacement, path)
        return descriptor

    monkeypatch.setattr(cards_module.os, "open", swapping_open)

    assert load_approval_card(path, card.card_sha256, now=NOW) == card
    assert swapped is True
    assert path.read_text(encoding="utf-8") == "{}\n"


def test_card_write_rejects_symlinked_directory_and_destination(
    tmp_path: Path,
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(real_directory, target_is_directory=True)

    with pytest.raises(ApprovalError, match="directory|unsafe|symlink"):
        write_approval_card(card, linked_directory)

    outside = tmp_path / "outside.json"
    outside.write_text("unchanged", encoding="utf-8")
    destination = real_directory / f"{card.card_id}.json"
    destination.symlink_to(outside)
    with pytest.raises(ApprovalError, match="exists|immutable|safe"):
        write_approval_card(card, real_directory)
    assert outside.read_text(encoding="utf-8") == "unchanged"


def test_directory_fsync_failure_removes_new_card_and_allows_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    directory = tmp_path / "cards"
    expected_path = directory / f"{card.card_id}.json"
    real_fsync = os.fsync

    def fail_directory_fsync(descriptor: int) -> None:
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError("injected directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(cards_module.os, "fsync", fail_directory_fsync)

    with pytest.raises(ApprovalError, match="directory sync failed|removed"):
        write_approval_card(card, directory)
    assert not expected_path.exists()

    monkeypatch.setattr(cards_module.os, "fsync", real_fsync)
    assert write_approval_card(card, directory) == expected_path
    with pytest.raises(ApprovalError, match="exists|immutable"):
        write_approval_card(card, directory)


def test_both_approval_profiles_may_supersede_their_own_prior_signoff() -> None:
    valid = create_approval_card(card_input(), now=NOW, nonce=NONCE)
    assert valid.profiles[0].supersedes == "signoff_governance_v1.json"
    assert valid.profiles[1].supersedes is None

    value = card_input()
    profiles = copy.deepcopy(list(value["profiles"]))
    profiles[1]["signoff_filename"] = "signoff_current_phase_v2.json"
    profiles[1]["supersedes"] = "signoff_current_phase_v1.json"
    value["profiles"] = tuple(profiles)

    resigned = create_approval_card(value, now=NOW, nonce=NONCE)

    assert resigned.profiles[1].supersedes == "signoff_current_phase_v1.json"


def test_governance_supersedes_must_name_a_governance_signoff() -> None:
    value = card_input()
    profiles = copy.deepcopy(list(value["profiles"]))
    profiles[0]["supersedes"] = "signoff_current_phase_v1.json"
    value["profiles"] = tuple(profiles)

    with pytest.raises(ApprovalError, match="supersedes|governance"):
        create_approval_card(value, now=NOW, nonce=NONCE)


def test_current_phase_supersedes_must_name_a_current_phase_signoff() -> None:
    value = card_input()
    profiles = copy.deepcopy(list(value["profiles"]))
    profiles[1]["signoff_filename"] = "signoff_current_phase_v2.json"
    profiles[1]["supersedes"] = "signoff_governance_v1.json"
    value["profiles"] = tuple(profiles)

    with pytest.raises(ApprovalError, match="supersedes|current_phase"):
        create_approval_card(value, now=NOW, nonce=NONCE)


def test_signoff_payloads_use_per_profile_filenames_and_fixed_rationales() -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)

    payloads = build_signoff_payloads(
        card,
        reviewed_at="2026-07-10T20:05:00+08:00",
        approval_event_id=EVENT_ID,
    )

    common = {
        "contract_id": card.contract_id,
        "contract_version": card.contract_version,
        "contract_digest": card.contract_digest,
        "evaluation_id": card.evaluation_id,
        "evidence_digest": card.evidence_digest,
        "role": "governance_owner",
        "reviewer_id": "project_owner",
        "decision": "approved",
        "reviewed_at": "2026-07-10T20:05:00+08:00",
        "approval_card_id": card.card_id,
        "approval_card_digest": card.card_sha256,
        "approval_event_id": EVENT_ID,
    }
    assert payloads == {
        "signoff_governance_v2.json": {
            **common,
            "profile_id": "governance",
            "rationale": GOVERNANCE_RATIONALE,
            "supersedes": "signoff_governance_v1.json",
        },
        "signoff_current_phase_v1.json": {
            **common,
            "profile_id": "current_phase",
            "rationale": CURRENT_PHASE_RATIONALE,
            "supersedes": None,
        },
    }


@pytest.mark.parametrize(
    "approval_event_id",
    [
        "approval-event-001",
        "approval_event_short",
        "approval_event_" + "A" * 24,
        " approval_event_" + "1" * 24,
    ],
)
def test_signoff_payloads_reject_noncanonical_approval_event_ids(
    approval_event_id: str,
) -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=NONCE)

    with pytest.raises(ApprovalError, match="approval_event_id|canonical"):
        build_signoff_payloads(
            card,
            reviewed_at="2026-07-10T20:05:00+08:00",
            approval_event_id=approval_event_id,
        )
