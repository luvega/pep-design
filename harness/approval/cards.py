from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import unicodedata
from dataclasses import asdict, fields, replace
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from harness.engine.models import canonical_json
from harness.engine.path_policy import is_workspace_source_path

from .models import (
    APPROVAL_PROFILE_IDS,
    CARD_SCHEMA_VERSION,
    PROFILE_RATIONALES,
    ApprovalCard,
    ApprovalError,
    ProfileApproval,
    SourceEntry,
)


_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_OID_RE = re.compile(r"[0-9a-f]{40}")
_EVALUATION_RE = re.compile(r"evaluation_[0-9a-f]{24}")
_CARD_ID_RE = re.compile(r"approval_[0-9a-f]{24}")
_NONCE_RE = re.compile(r"[0-9a-f]{32}")
_SOURCE_MODES = frozenset({"100644", "100755"})
_SOURCE_STATUSES = frozenset({"added", "deleted", "modified", "untracked"})
_EXPECTED_REMOTE_URL = "git@github.com:luvega/pep-design.git"
_MAX_CARD_BYTES = 1_000_000
_INPUT_FIELDS = frozenset(
    {
        "schema_version",
        "contract_id",
        "contract_version",
        "contract_digest",
        "evaluator_version",
        "registry_digest",
        "evaluation_id",
        "evidence_digest",
        "reviewer_id",
        "head_oid",
        "remote_name",
        "remote_url",
        "remote_ref",
        "remote_oid",
        "proposed_tree_oid",
        "diff_stat",
        "ahead_commits",
        "source_manifest",
        "profiles",
    }
)
_CARD_FIELDS = frozenset(field.name for field in fields(ApprovalCard))
_SOURCE_FIELDS = frozenset(field.name for field in fields(SourceEntry))
_PROFILE_FIELDS = frozenset(field.name for field in fields(ProfileApproval))


def _require_exact_fields(
    value: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    actual = set(value)
    missing = expected - actual
    unexpected = actual - expected
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append("missing required fields: " + ", ".join(sorted(missing)))
        if unexpected:
            details.append(
                "unexpected fields: " + ", ".join(sorted(str(item) for item in unexpected))
            )
        raise ApprovalError(f"{label} field schema invalid: {'; '.join(details)}")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise ApprovalError(f"{label} schema must be a JSON object")
    return value


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ApprovalError(f"{label} must be an array")
    return value


def _require_string(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ApprovalError(f"{label} must be a non-empty string")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ApprovalError(f"{label} contains unsafe control characters")
    return value


def _require_pattern(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ApprovalError(f"{label} has a non-canonical format")
    return value


def _require_safe_path(value: Any, label: str, *, filename: bool = False) -> str:
    path_value = _require_string(value, label)
    if "\\" in path_value or re.match(r"^[A-Za-z]:", path_value):
        raise ApprovalError(f"{label} is an unsafe path")
    path = PurePosixPath(path_value)
    if path.is_absolute():
        raise ApprovalError(f"{label} must not be an absolute path")
    if ".." in path.parts:
        raise ApprovalError(f"{label} contains path traversal")
    if path.as_posix() != path_value or path_value in {"", "."}:
        raise ApprovalError(f"{label} must be a canonical relative path")
    if filename and len(path.parts) != 1:
        raise ApprovalError(f"{label} must be a filename, not a path")
    return path_value


def _require_datetime(value: Any, label: str) -> datetime:
    raw = _require_string(value, label)
    try:
        timestamp = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ApprovalError(f"{label} must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ApprovalError(f"{label} must include a timezone")
    if timestamp.isoformat() != raw:
        raise ApprovalError(f"{label} must use canonical ISO-8601 encoding")
    return timestamp


def _parse_source_entry(value: Any, index: int) -> SourceEntry:
    label = f"source_manifest[{index}]"
    mapping = _require_mapping(value, label)
    _require_exact_fields(mapping, _SOURCE_FIELDS, label)
    path = _require_safe_path(mapping["path"], f"{label} path")
    if not is_workspace_source_path(path):
        raise ApprovalError(f"{label} path is outside the workspace source surface")
    status_value = _require_string(mapping["status"], f"{label} status")
    if status_value not in _SOURCE_STATUSES:
        raise ApprovalError(f"{label} status is unsupported")

    mode_value = mapping["mode"]
    digest_value = mapping["sha256"]
    if status_value == "deleted":
        if mode_value is not None or digest_value is not None:
            raise ApprovalError(f"{label} deletion marker must omit mode and sha256")
        mode = None
        digest = None
    else:
        if not isinstance(mode_value, str) or mode_value not in _SOURCE_MODES:
            raise ApprovalError(f"{label} mode must be 100644 or 100755")
        mode = mode_value
        digest = _require_pattern(digest_value, _DIGEST_RE, f"{label} sha256")
    return SourceEntry(path=path, status=status_value, mode=mode, sha256=digest)


def _profile_filename(profile_id: str, value: Any, label: str) -> str:
    filename = _require_safe_path(value, label, filename=True)
    pattern = re.compile(rf"signoff_{re.escape(profile_id)}_v[1-9][0-9]*\.json")
    if pattern.fullmatch(filename) is None:
        raise ApprovalError(f"{label} does not match profile {profile_id}")
    return filename


def _parse_profile(value: Any, index: int) -> ProfileApproval:
    label = f"profiles[{index}]"
    mapping = _require_mapping(value, label)
    _require_exact_fields(mapping, _PROFILE_FIELDS, label)
    profile_id = _require_string(mapping["profile_id"], f"{label} profile_id")
    gate_digest = _require_pattern(
        mapping["gate_result_digest"], _DIGEST_RE, f"{label} gate_result_digest"
    )
    gate_count = mapping["gate_count"]
    if isinstance(gate_count, bool) or not isinstance(gate_count, int) or gate_count < 0:
        raise ApprovalError(f"{label} gate_count must be a non-negative integer")
    rationale = _require_string(mapping["rationale"], f"{label} rationale")
    expected_rationale = PROFILE_RATIONALES.get(profile_id)
    if expected_rationale is None or rationale != expected_rationale:
        raise ApprovalError(f"{label} rationale is not the fixed profile rationale")
    filename = _profile_filename(
        profile_id, mapping["signoff_filename"], f"{label} signoff filename"
    )

    raw_supersedes = mapping["supersedes"]
    if raw_supersedes is None:
        supersedes = None
    else:
        supersedes = _profile_filename(
            profile_id, raw_supersedes, f"{profile_id} supersedes"
        )
        if supersedes == filename:
            raise ApprovalError(
                f"{profile_id} supersedes cannot name the new signoff"
            )

    return ProfileApproval(
        profile_id=profile_id,
        gate_result_digest=gate_digest,
        gate_count=gate_count,
        rationale=rationale,
        signoff_filename=filename,
        supersedes=supersedes,
    )


def _parse_common(
    value: Mapping[str, Any], *, nonce: str, created_at: str, expires_at: str
) -> dict[str, Any]:
    if value["schema_version"] != CARD_SCHEMA_VERSION:
        raise ApprovalError("card schema_version is unsupported")
    created = _require_datetime(created_at, "created_at")
    expires = _require_datetime(expires_at, "expires_at")
    if expires - created != timedelta(minutes=60):
        raise ApprovalError("approval card expiry must be exactly 60 minutes")

    nonce_value = _require_pattern(nonce, _NONCE_RE, "nonce")
    contract_id = _require_string(value["contract_id"], "contract_id")
    contract_version = _require_string(value["contract_version"], "contract_version")
    contract_digest = _require_pattern(
        value["contract_digest"], _DIGEST_RE, "contract_digest"
    )
    evaluator_version = _require_string(
        value["evaluator_version"], "evaluator_version"
    )
    registry_digest = _require_pattern(
        value["registry_digest"], _DIGEST_RE, "registry_digest"
    )
    evaluation_id = _require_pattern(
        value["evaluation_id"], _EVALUATION_RE, "evaluation_id"
    )
    evidence_digest = _require_pattern(
        value["evidence_digest"], _DIGEST_RE, "evidence_digest"
    )
    reviewer_id = _require_string(value["reviewer_id"], "reviewer_id")
    if reviewer_id != "project_owner":
        raise ApprovalError("reviewer_id must be project_owner")

    head_oid = _require_pattern(value["head_oid"], _OID_RE, "head_oid")
    remote_name = _require_string(value["remote_name"], "remote_name")
    if remote_name != "origin":
        raise ApprovalError("remote_name must be origin")
    remote_url = _require_string(value["remote_url"], "remote_url")
    if remote_url != _EXPECTED_REMOTE_URL:
        raise ApprovalError(f"remote_url must be {_EXPECTED_REMOTE_URL}")
    remote_ref = _require_string(value["remote_ref"], "remote_ref")
    if remote_ref != "refs/heads/main":
        raise ApprovalError("remote_ref must be refs/heads/main")
    remote_oid = _require_pattern(value["remote_oid"], _OID_RE, "remote_oid")
    proposed_tree_oid = _require_pattern(
        value["proposed_tree_oid"], _OID_RE, "proposed_tree_oid"
    )
    diff_stat = _require_string(value["diff_stat"], "diff_stat", allow_empty=True)

    ahead_values = _require_sequence(value["ahead_commits"], "ahead_commits")
    ahead_commits = tuple(
        _require_pattern(item, _OID_RE, f"ahead_commits[{index}]")
        for index, item in enumerate(ahead_values)
    )
    if len(ahead_commits) != len(set(ahead_commits)):
        raise ApprovalError("ahead_commits must not contain duplicates")

    source_values = _require_sequence(value["source_manifest"], "source_manifest")
    source_manifest = tuple(
        _parse_source_entry(item, index) for index, item in enumerate(source_values)
    )
    source_paths = tuple(entry.path for entry in source_manifest)
    if len(source_paths) != len(set(source_paths)):
        raise ApprovalError("source_manifest paths must be unique")

    profile_values = _require_sequence(value["profiles"], "profiles")
    profiles = tuple(
        _parse_profile(item, index) for index, item in enumerate(profile_values)
    )
    profile_ids = tuple(profile.profile_id for profile in profiles)
    if profile_ids != APPROVAL_PROFILE_IDS:
        raise ApprovalError(
            "profiles must be exactly ordered as governance,current_phase"
        )
    filenames = tuple(profile.signoff_filename for profile in profiles)
    if len(filenames) != len(set(filenames)):
        raise ApprovalError("profile signoff filenames must be unique")

    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "nonce": nonce_value,
        "created_at": created_at,
        "expires_at": expires_at,
        "contract_id": contract_id,
        "contract_version": contract_version,
        "contract_digest": contract_digest,
        "evaluator_version": evaluator_version,
        "registry_digest": registry_digest,
        "evaluation_id": evaluation_id,
        "evidence_digest": evidence_digest,
        "reviewer_id": reviewer_id,
        "head_oid": head_oid,
        "remote_name": remote_name,
        "remote_url": remote_url,
        "remote_ref": remote_ref,
        "remote_oid": remote_oid,
        "proposed_tree_oid": proposed_tree_oid,
        "diff_stat": diff_stat,
        "ahead_commits": ahead_commits,
        "source_manifest": source_manifest,
        "profiles": profiles,
    }


def _binding_digest(card: ApprovalCard) -> str:
    payload = asdict(card)
    payload.pop("card_id")
    payload.pop("card_sha256")
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def create_approval_card(
    value: Mapping[str, Any],
    *,
    now: datetime,
    nonce: bytes | None = None,
) -> ApprovalCard:
    """Create a deterministic card when time and nonce are injected."""

    mapping = _require_mapping(value, "approval card input")
    _require_exact_fields(mapping, _INPUT_FIELDS, "approval card input")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ApprovalError("now must include a timezone")
    nonce_bytes = secrets.token_bytes(16) if nonce is None else nonce
    if not isinstance(nonce_bytes, bytes) or len(nonce_bytes) != 16:
        raise ApprovalError("nonce must be exactly 128 bits")
    created_at = now.isoformat()
    expires_at = (now + timedelta(minutes=60)).isoformat()
    common = _parse_common(
        mapping,
        nonce=nonce_bytes.hex(),
        created_at=created_at,
        expires_at=expires_at,
    )
    provisional = ApprovalCard(card_id="", card_sha256="", **common)
    digest = _binding_digest(provisional)
    return replace(
        provisional,
        card_id=f"approval_{digest[:24]}",
        card_sha256=digest,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ApprovalError(f"card JSON contains duplicate field: {key}")
        value[key] = item
    return value


def _card_from_mapping(
    raw: Mapping[str, Any],
    *,
    expected_sha256: str,
    now: datetime | None,
    expected_filename: str | None,
) -> ApprovalCard:
    _require_exact_fields(raw, _CARD_FIELDS, "approval card")
    card_id = _require_pattern(raw["card_id"], _CARD_ID_RE, "card_id")
    embedded_digest = _require_pattern(
        raw["card_sha256"], _DIGEST_RE, "card_sha256"
    )
    common = _parse_common(
        raw,
        nonce=raw["nonce"],
        created_at=raw["created_at"],
        expires_at=raw["expires_at"],
    )
    card = ApprovalCard(
        card_id=card_id,
        card_sha256=embedded_digest,
        **common,
    )
    calculated = _binding_digest(card)
    if not hmac.compare_digest(embedded_digest, calculated):
        raise ApprovalError("approval card integrity digest does not match its payload")
    if not hmac.compare_digest(expected_sha256, calculated):
        raise ApprovalError("approval card digest does not match expected sha256")
    expected_id = f"approval_{calculated[:24]}"
    if card_id != expected_id:
        raise ApprovalError("card_id does not match the approval card digest")
    if expected_filename is not None and expected_filename != f"{card_id}.json":
        raise ApprovalError("approval card filename does not match card_id")

    if now is not None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ApprovalError("now must include a timezone")
        created = _require_datetime(card.created_at, "created_at")
        expires = _require_datetime(card.expires_at, "expires_at")
        if now < created:
            raise ApprovalError("approval card was created in the future")
        if now >= expires:
            raise ApprovalError("approval card has expired")
    return card


def write_approval_card(card: ApprovalCard, directory: str | Path) -> Path:
    """Create one immutable card file with owner-only permissions."""

    if not isinstance(card, ApprovalCard):
        raise ApprovalError("approval card must use the frozen ApprovalCard model")
    _card_from_mapping(
        asdict(card),
        expected_sha256=card.card_sha256,
        now=None,
        expected_filename=None,
    )
    root = Path(directory)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ApprovalError(f"approval card directory could not be created: {exc}") from exc
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_only = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_only is None:
        raise ApprovalError("platform lacks no-follow directory file operations")
    try:
        directory_descriptor = os.open(
            root,
            os.O_RDONLY | directory_only | nofollow,
        )
    except OSError as exc:
        raise ApprovalError(f"approval card directory is unsafe: {exc}") from exc

    filename = f"{card.card_id}.json"
    path = root / filename
    try:
        directory_metadata = os.fstat(directory_descriptor)
        if not stat.S_ISDIR(directory_metadata.st_mode):
            raise ApprovalError("approval card directory descriptor is not a directory")
        try:
            descriptor = os.open(
                filename,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | nofollow,
                0o600,
                dir_fd=directory_descriptor,
            )
        except FileExistsError as exc:
            raise ApprovalError("immutable approval card already exists") from exc
        except OSError as exc:
            raise ApprovalError(f"approval card could not be created safely: {exc}") from exc
        created = True
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ApprovalError("approval card descriptor is not a regular file")
            os.fchmod(descriptor, 0o600)
            payload = (canonical_json(asdict(card)) + "\n").encode("utf-8")
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise ApprovalError("approval card write made no progress")
                offset += written
            os.fsync(descriptor)
        except (OSError, ApprovalError) as exc:
            if created:
                try:
                    os.unlink(filename, dir_fd=directory_descriptor)
                except OSError:
                    pass
            if isinstance(exc, ApprovalError):
                raise
            raise ApprovalError(f"approval card could not be written safely: {exc}") from exc
        finally:
            os.close(descriptor)
        try:
            os.fsync(directory_descriptor)
        except OSError as exc:
            cleanup_error: OSError | None = None
            try:
                os.unlink(filename, dir_fd=directory_descriptor)
            except OSError as unlink_exc:
                cleanup_error = unlink_exc
            else:
                try:
                    os.fsync(directory_descriptor)
                except OSError:
                    pass
            if cleanup_error is not None:
                raise ApprovalError(
                    "approval card directory sync failed and cleanup could not "
                    "remove the newly created card"
                ) from exc
            raise ApprovalError(
                "approval card directory sync failed; newly created card was removed"
            ) from exc
    finally:
        os.close(directory_descriptor)
    return path


def load_approval_card(
    path: str | Path,
    expected_sha256: str,
    *,
    now: datetime,
) -> ApprovalCard:
    """Load a card only when schema, binding, path, and expiry all remain valid."""

    expected = _require_pattern(
        expected_sha256, _DIGEST_RE, "expected card digest"
    )
    card_path = Path(path)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise ApprovalError("platform lacks no-follow card file operations")
    try:
        descriptor = os.open(card_path, os.O_RDONLY | nofollow)
    except OSError as exc:
        raise ApprovalError(f"approval card could not be opened safely: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ApprovalError("approval card descriptor must be a regular file")
        if metadata.st_size > _MAX_CARD_BYTES:
            raise ApprovalError("approval card exceeds the bounded size limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, _MAX_CARD_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_CARD_BYTES:
                raise ApprovalError("approval card exceeds the bounded size limit")
        payload = b"".join(chunks)
    except OSError as exc:
        raise ApprovalError(f"approval card could not be read safely: {exc}") from exc
    finally:
        os.close(descriptor)
    try:
        raw = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except ApprovalError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ApprovalError(f"approval card JSON could not be read: {exc}") from exc
    mapping = _require_mapping(raw, "approval card")
    return _card_from_mapping(
        mapping,
        expected_sha256=expected,
        now=now,
        expected_filename=card_path.name,
    )


def is_exact_approval_message(value: str) -> bool:
    return (
        isinstance(value, str)
        and unicodedata.normalize("NFC", value).strip() == "批准"
    )
