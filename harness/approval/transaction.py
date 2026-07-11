from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from harness.engine.models import canonical_json

from .cards import create_approval_card, load_approval_card, write_approval_card
from .git_backend import (
    EXPECTED_REMOTE_NAME,
    EXPECTED_REMOTE_REF,
    EXPECTED_REMOTE_URL,
    GitBackend,
    RemoteSnapshot,
    SourceManifestEntry,
)
from .journal import (
    TransactionJournal,
    TransactionState,
    create_journal,
    load_journal,
    transition_journal,
)
from .models import (
    APPROVAL_PROFILE_IDS,
    CARD_SCHEMA_VERSION,
    PROFILE_RATIONALES,
    ApprovalCard,
    ApprovalError,
)
from .signoff_payloads import build_signoff_payloads


_SIGNOFF_VERSION_RE = re.compile(
    r"signoff_(governance|current_phase)_v([0-9]+)\.json"
)
_CARD_ID_RE = re.compile(r"approval_[0-9a-f]{24}")


@dataclass(frozen=True)
class VerificationSnapshot:
    evaluation_id: str
    evidence_digest: str
    contract_digest: str
    registry_digest: str
    profile_gate_digests: tuple[tuple[str, str], ...]


class VerificationRunner(Protocol):
    def prepare(self, root: Path) -> VerificationSnapshot: ...

    def clean_checkout(self, root: Path) -> VerificationSnapshot: ...

    def accepted(self, root: Path) -> VerificationSnapshot: ...

    def render_current_phase(self, root: Path) -> None: ...


@dataclass(frozen=True)
class TransactionResult:
    card_id: str
    state: TransactionState
    source_commit_oid: str | None
    signoff_commit_oid: str | None
    final_commit_oid: str | None


@dataclass(frozen=True)
class PreparedTransaction:
    card: ApprovalCard


def _contract(root: Path) -> dict[str, object]:
    path = root / "harness/contracts/project_acceptance_v1.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ApprovalError(f"approval contract could not be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise ApprovalError("approval contract must be a JSON object")
    for field in ("contract_id", "contract_version", "evaluator_version"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise ApprovalError(f"approval contract is missing {field}")
    return value


def _profile_gate_counts(contract: dict[str, object]) -> dict[str, int]:
    # The fallback keeps isolated transaction tests independent of the full contract.
    counts = {"governance": 4, "current_phase": 11}
    profiles = contract.get("profiles")
    if not isinstance(profiles, list):
        return counts
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        profile_id = profile.get("profile_id")
        gate_ids = profile.get("required_gate_ids")
        if profile_id in APPROVAL_PROFILE_IDS and isinstance(gate_ids, list):
            counts[str(profile_id)] = len(gate_ids)
    return counts


def _next_signoff_versions(root: Path) -> dict[str, int]:
    versions = {profile_id: 0 for profile_id in APPROVAL_PROFILE_IDS}
    signoff_root = root / "harness/signoffs"
    if not signoff_root.is_dir():
        return {key: 1 for key in versions}
    for path in signoff_root.iterdir():
        match = _SIGNOFF_VERSION_RE.fullmatch(path.name)
        if match is not None:
            profile_id, raw_version = match.groups()
            versions[profile_id] = max(versions[profile_id], int(raw_version))
    return {key: version + 1 for key, version in versions.items()}


def _expected_remote(card: ApprovalCard) -> RemoteSnapshot:
    return RemoteSnapshot(
        name=card.remote_name,
        fetch_url=card.remote_url,
        push_url=card.remote_url,
        ref=card.remote_ref,
        oid=card.remote_oid,
        head_oid=card.head_oid,
        ahead_commits=card.ahead_commits,
    )


def _require_initial_remote(current: RemoteSnapshot, card: ApprovalCard) -> None:
    if current.name != card.remote_name:
        raise ApprovalError("remote name drifted from the approval card")
    if current.fetch_url != card.remote_url or current.push_url != card.remote_url:
        raise ApprovalError("remote URL drifted from the approval card")
    if current.ref != card.remote_ref:
        raise ApprovalError("remote ref drifted from the approval card")
    if current.oid != card.remote_oid:
        raise ApprovalError("remote OID moved after the approval card was prepared")
    if current.head_oid != card.head_oid:
        raise ApprovalError("HEAD drifted from the approval card")
    if current.ahead_commits != card.ahead_commits:
        raise ApprovalError("ahead commit list drifted from the approval card")


def _require_remote_baseline(current: RemoteSnapshot, card: ApprovalCard) -> None:
    if current.name != card.remote_name:
        raise ApprovalError("remote name drifted from the approval card")
    if current.fetch_url != card.remote_url or current.push_url != card.remote_url:
        raise ApprovalError("remote URL drifted from the approval card")
    if current.ref != card.remote_ref:
        raise ApprovalError("remote ref drifted from the approval card")
    if current.oid != card.remote_oid:
        raise ApprovalError("remote OID moved after the approval card was prepared")


def _require_remote_metadata(current: RemoteSnapshot, card: ApprovalCard) -> None:
    if current.name != card.remote_name:
        raise ApprovalError("remote name drifted from the approval card")
    if current.fetch_url != card.remote_url or current.push_url != card.remote_url:
        raise ApprovalError("remote URL drifted from the approval card")
    if current.ref != card.remote_ref:
        raise ApprovalError("remote ref drifted from the approval card")


def _require_verification(
    snapshot: VerificationSnapshot, card: ApprovalCard, *, phase: str
) -> None:
    expected_scalars = (
        ("evaluation identity", snapshot.evaluation_id, card.evaluation_id),
        ("evidence digest", snapshot.evidence_digest, card.evidence_digest),
        ("contract digest", snapshot.contract_digest, card.contract_digest),
        ("registry digest", snapshot.registry_digest, card.registry_digest),
    )
    for label, actual, expected in expected_scalars:
        if actual != expected:
            raise ApprovalError(f"{phase} {label} drifted from the approval card")
    expected_gates = tuple(
        (profile.profile_id, profile.gate_result_digest)
        for profile in card.profiles
    )
    if snapshot.profile_gate_digests != expected_gates:
        raise ApprovalError(
            f"{phase} profile gate identity drifted from the approval card"
        )


def _card_path(root: Path, card_id: str) -> Path:
    _require_card_id(card_id)
    return root / "ops/acceptance/dialog_cards" / f"{card_id}.json"


def _journal_path(root: Path, card_id: str) -> Path:
    _require_card_id(card_id)
    return root / "ops/acceptance/dialog_transactions" / f"{card_id}.json"


def _require_card_id(card_id: str) -> None:
    if not isinstance(card_id, str) or _CARD_ID_RE.fullmatch(card_id) is None:
        raise ApprovalError("approval card ID is not canonical")


def _journal_matches_card(
    journal: TransactionJournal, card: ApprovalCard, requested_card_id: str
) -> None:
    if (
        requested_card_id != journal.card_id
        or requested_card_id != card.card_id
        or journal.card_sha256 != card.card_sha256
    ):
        raise ApprovalError("approval card and journal identity do not match")


def _result(
    journal: TransactionJournal, *, source_was_committed: bool
) -> TransactionResult:
    return TransactionResult(
        card_id=journal.card_id,
        state=journal.state,
        source_commit_oid=(
            journal.source_commit_oid if source_was_committed else None
        ),
        signoff_commit_oid=journal.signoff_commit_oid,
        final_commit_oid=journal.final_commit_oid,
    )


def prepare_review(
    root: str | Path,
    *,
    backend: GitBackend,
    verifier: VerificationRunner,
    now: datetime,
    nonce: bytes | None = None,
) -> PreparedTransaction:
    workspace = Path(root)
    backend.require_main_with_clean_index()
    backend.reject_active_git_customization()
    remote = backend.fetch_remote_snapshot(
        remote_name=EXPECTED_REMOTE_NAME,
        expected_url=EXPECTED_REMOTE_URL,
        ref=EXPECTED_REMOTE_REF,
    )
    snapshot = verifier.prepare(workspace)
    manifest = backend.collect_source_manifest()
    proposed_tree_oid = backend.build_proposed_tree(manifest)
    diff_stat = backend.diff_stat(manifest)

    contract = _contract(workspace)
    gate_counts = _profile_gate_counts(contract)
    gate_digests = dict(snapshot.profile_gate_digests)
    if tuple(gate_digests) != APPROVAL_PROFILE_IDS:
        raise ApprovalError(
            "verification must contain exactly governance,current_phase gate digests"
        )
    versions = _next_signoff_versions(workspace)
    profiles: list[dict[str, object]] = []
    for profile_id in APPROVAL_PROFILE_IDS:
        committed = backend.latest_committed_signoffs(
            contract_id=str(contract["contract_id"]),
            contract_version=str(contract["contract_version"]),
            contract_digest=snapshot.contract_digest,
            profile_id=profile_id,
            evaluation_id=snapshot.evaluation_id,
            evidence_digest=snapshot.evidence_digest,
            role="governance_owner",
        )
        profiles.append(
            {
                "profile_id": profile_id,
                "gate_result_digest": gate_digests[profile_id],
                "gate_count": gate_counts[profile_id],
                "rationale": PROFILE_RATIONALES[profile_id],
                "signoff_filename": (
                    f"signoff_{profile_id}_v{versions[profile_id]}.json"
                ),
                "supersedes": committed[0] if committed else None,
            }
        )

    card = create_approval_card(
        {
            "schema_version": CARD_SCHEMA_VERSION,
            "contract_id": contract["contract_id"],
            "contract_version": contract["contract_version"],
            "contract_digest": snapshot.contract_digest,
            "evaluator_version": contract["evaluator_version"],
            "registry_digest": snapshot.registry_digest,
            "evaluation_id": snapshot.evaluation_id,
            "evidence_digest": snapshot.evidence_digest,
            "reviewer_id": "project_owner",
            "head_oid": remote.head_oid,
            "remote_name": remote.name,
            "remote_url": remote.fetch_url,
            "remote_ref": remote.ref,
            "remote_oid": remote.oid,
            "proposed_tree_oid": proposed_tree_oid,
            "diff_stat": diff_stat,
            "ahead_commits": remote.ahead_commits,
            "source_manifest": tuple(asdict(entry) for entry in manifest),
            "profiles": tuple(profiles),
        },
        now=now,
        nonce=nonce,
    )
    write_approval_card(card, workspace / "ops/acceptance/dialog_cards")
    create_journal(
        _journal_path(workspace, card.card_id),
        card_id=card.card_id,
        card_sha256=card.card_sha256,
    )
    return PreparedTransaction(card=card)


def _invalidate_before_commit(path: Path, state: TransactionState, code: str) -> None:
    if state in {TransactionState.PREPARED, TransactionState.APPROVED}:
        _transition_reconciled(
            path,
            expected_state=state,
            new_state=TransactionState.INVALIDATED,
            failure_code=code,
        )


def _record_local_failure(
    path: Path, state: TransactionState, code: str
) -> None:
    if state in {
        TransactionState.SOURCE_COMMITTED,
        TransactionState.SIGNOFFS_COMMITTED,
        TransactionState.VERIFIED,
    }:
        _transition_reconciled(
            path,
            expected_state=state,
            new_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
            failure_code=code,
        )


def _transition_reconciled(
    path: Path,
    *,
    expected_state: TransactionState,
    new_state: TransactionState,
    **updates: object,
) -> TransactionJournal:
    def exact_new_state(value: TransactionJournal) -> bool:
        return value.state is new_state and all(
            getattr(value, key) == update for key, update in updates.items()
        )

    try:
        return transition_journal(
            path,
            expected_state=expected_state,
            new_state=new_state,
            **updates,
        )
    except ApprovalError as first_error:
        current = load_journal(path)
        if exact_new_state(current):
            return current
        if current.state is not expected_state:
            raise ApprovalError(
                "journal transition failed and current state cannot be reconciled"
            ) from first_error
        try:
            return transition_journal(
                path,
                expected_state=expected_state,
                new_state=new_state,
                **updates,
            )
        except ApprovalError as second_error:
            current = load_journal(path)
            if exact_new_state(current):
                return current
            raise ApprovalError(
                "journal transition could not be persisted after retry"
            ) from second_error


def _transition_after_commit(
    path: Path,
    *,
    expected_state: TransactionState,
    new_state: TransactionState,
    failure_code: str,
    **updates: object,
) -> TransactionJournal:
    """Reconcile an atomic journal error after an irreversible local commit."""

    try:
        return _transition_reconciled(
            path,
            expected_state=expected_state,
            new_state=new_state,
            **updates,
        )
    except ApprovalError as first_error:
        current = load_journal(path)
        if current.state is new_state and all(
            getattr(current, key) == value for key, value in updates.items()
        ):
            return current
        recovery_updates = dict(updates)
        recovery_updates["failure_code"] = failure_code
        if current.state is expected_state:
            try:
                recovered = _transition_reconciled(
                    path,
                    expected_state=expected_state,
                    new_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
                    **recovery_updates,
                )
            except ApprovalError:
                recovered = load_journal(path)
            if recovered.state is TransactionState.LOCAL_COMMITTED_PUSH_FAILED:
                raise ApprovalError(
                    "local commit succeeded but journal continuation requires resume"
                ) from first_error
        raise ApprovalError(
            "local commit succeeded but its journal state could not be reconciled"
        ) from first_error


def _require_local_head(remote: RemoteSnapshot, expected_oid: str, phase: str) -> None:
    if remote.head_oid != expected_oid:
        raise ApprovalError(f"HEAD changed before {phase}")


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise ApprovalError("signoff write made no progress")
        view = view[written:]


def _publish_signoff(
    directory: int, filename: str, payload: bytes
) -> None:
    create_flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    temporary_name = f".{filename}.{secrets.token_hex(12)}.tmp"
    descriptor = -1
    linked = False
    try:
        descriptor = os.open(
            temporary_name, create_flags, 0o600, dir_fd=directory
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ApprovalError("temporary signoff is not a regular file")
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(
            temporary_name,
            filename,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        linked = True
        os.fsync(directory)
    except FileExistsError as exc:
        raise ApprovalError(f"signoff appeared concurrently: {filename}") from exc
    except ApprovalError:
        raise
    except OSError as exc:
        raise ApprovalError(f"signoff publication failed: {filename}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_name, dir_fd=directory)
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise ApprovalError(
                f"temporary signoff cleanup failed: {filename}: {exc}"
            ) from exc
        else:
            os.fsync(directory)
    if not linked:
        raise ApprovalError(f"signoff was not published: {filename}")


def _canonical_signoff_bytes(
    card: ApprovalCard, *, reviewed_at: str, event_id: str
) -> dict[str, bytes]:
    payloads = build_signoff_payloads(
        card,
        reviewed_at=reviewed_at,
        approval_event_id=event_id,
    )
    return {
        filename: (canonical_json(payload) + "\n").encode("utf-8")
        for filename, payload in payloads.items()
    }


def _expected_signoff_manifest(
    card: ApprovalCard, *, reviewed_at: str, event_id: str
) -> tuple[SourceManifestEntry, ...]:
    payloads = _canonical_signoff_bytes(
        card, reviewed_at=reviewed_at, event_id=event_id
    )
    return tuple(
        SourceManifestEntry(
            path=f"harness/signoffs/{filename}",
            status="untracked",
            mode="100644",
            sha256=hashlib.sha256(payload).hexdigest(),
        )
        for filename, payload in sorted(payloads.items())
    )


def _write_signoffs(
    root: Path,
    card: ApprovalCard,
    *,
    reviewed_at: str,
    event_id: str,
    allow_create: bool = True,
) -> tuple[str, ...]:
    payloads = _canonical_signoff_bytes(
        card, reviewed_at=reviewed_at, event_id=event_id
    )
    signoff_root = root / "harness/signoffs"
    signoff_root.mkdir(parents=True, exist_ok=True)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        directory = os.open(signoff_root, directory_flags)
    except OSError as exc:
        raise ApprovalError(f"signoff directory could not be opened safely: {exc}") from exc
    relative_paths: list[str] = []
    try:
        if not stat.S_ISDIR(os.fstat(directory).st_mode):
            raise ApprovalError("signoff parent must be a directory")
        fcntl.flock(directory, fcntl.LOCK_EX)
        try:
            for profile in card.profiles:
                filename = profile.signoff_filename
                if _SIGNOFF_VERSION_RE.fullmatch(filename) is None:
                    raise ApprovalError("signoff filename is not canonical")
                expected = payloads[filename]
                read_flags = (
                    os.O_RDONLY
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_NONBLOCK", 0)
                )
                try:
                    existing = os.open(filename, read_flags, dir_fd=directory)
                except FileNotFoundError:
                    existing = -1
                except OSError as exc:
                    raise ApprovalError(
                        f"existing signoff could not be opened safely: {filename}: {exc}"
                    ) from exc
                if existing >= 0:
                    try:
                        metadata = os.fstat(existing)
                        if not stat.S_ISREG(metadata.st_mode):
                            raise ApprovalError(
                                f"existing signoff is not a regular file: {filename}"
                            )
                        chunks: list[bytes] = []
                        while True:
                            chunk = os.read(existing, 65_536)
                            if not chunk:
                                break
                            chunks.append(chunk)
                            if sum(map(len, chunks)) > len(expected):
                                break
                        if b"".join(chunks) != expected:
                            raise ApprovalError(
                                f"existing signoff bytes conflict with approval: {filename}"
                            )
                    finally:
                        os.close(existing)
                else:
                    if not allow_create:
                        raise ApprovalError(
                            f"committed signoff is missing during resume: {filename}"
                        )
                    _publish_signoff(directory, filename, expected)
                relative_paths.append(
                    (signoff_root / filename).relative_to(root).as_posix()
                )
        finally:
            fcntl.flock(directory, fcntl.LOCK_UN)
    finally:
        os.close(directory)
    return tuple(relative_paths)


def approve_card(
    root: str | Path,
    *,
    card_id: str,
    expected_card_sha256: str,
    reviewer_id: str,
    backend: GitBackend,
    verifier: VerificationRunner,
    now: datetime,
    event_id_factory: Callable[[], str] | None = None,
) -> TransactionResult:
    workspace = Path(root)
    _require_card_id(card_id)
    try:
        card = load_approval_card(
            _card_path(workspace, card_id),
            expected_card_sha256,
            now=now,
        )
    except ApprovalError as exc:
        raise ApprovalError(f"approval card validation failed: {exc}") from exc
    if card.card_id != card_id:
        raise ApprovalError("loaded approval card ID does not match the request")
    if reviewer_id != card.reviewer_id:
        raise ApprovalError("reviewer does not match the approval card")
    path = _journal_path(workspace, card_id)
    journal = load_journal(path)
    _journal_matches_card(journal, card, card_id)
    if journal.state is not TransactionState.PREPARED:
        raise ApprovalError(
            f"approval card cannot run from journal state {journal.state.value}"
        )

    try:
        backend.require_main_with_clean_index()
        backend.reject_active_git_customization()
        remote = backend.fetch_remote_snapshot(
            remote_name=card.remote_name,
            expected_url=card.remote_url,
            ref=card.remote_ref,
        )
        _require_initial_remote(remote, card)
        _require_verification(verifier.prepare(workspace), card, phase="prepare")
        manifest = backend.collect_source_manifest()
        if manifest != card.source_manifest:
            raise ApprovalError("source manifest drifted from the approval card")
        if backend.build_proposed_tree(manifest) != card.proposed_tree_oid:
            raise ApprovalError("proposed source tree drifted from the approval card")
    except Exception:
        _invalidate_before_commit(
            path, TransactionState.PREPARED, "precommit_recheck_failed"
        )
        raise

    event_factory = event_id_factory or (
        lambda: "approval_event_" + secrets.token_hex(12)
    )
    reviewed_at = now.isoformat()
    event_id = event_factory()
    journal = _transition_reconciled(
        path,
        expected_state=TransactionState.PREPARED,
        new_state=TransactionState.APPROVED,
        reviewed_at=reviewed_at,
        approval_event_id=event_id,
    )
    source_was_committed = bool(manifest)
    effective_source_oid = card.head_oid
    if manifest:
        try:
            backend.stage_exact_manifest(manifest)
        except Exception:
            _invalidate_before_commit(
                path, TransactionState.APPROVED, "source_stage_failed"
            )
            raise
        if backend.current_head_oid() != card.head_oid:
            _invalidate_before_commit(
                path, TransactionState.APPROVED, "source_parent_moved"
            )
            raise ApprovalError("HEAD moved before source commit")
        try:
            effective_source_oid = backend.commit_source(
                manifest,
                card.card_id,
                expected_parent_oid=card.head_oid,
            )
        except Exception as commit_error:
            try:
                effective_source_oid = backend.reconcile_card_commit(
                    card.head_oid,
                    card.card_id,
                    tuple(entry.path for entry in manifest),
                    expected_tree_oid=card.proposed_tree_oid,
                    expected_manifest=manifest,
                )
            except Exception as reconcile_error:
                observed_oid = backend.current_head_oid()
                if observed_oid == card.head_oid:
                    _invalidate_before_commit(
                        path, TransactionState.APPROVED, "source_commit_failed"
                    )
                else:
                    _transition_reconciled(
                        path,
                        expected_state=TransactionState.APPROVED,
                        new_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
                        source_commit_oid=observed_oid,
                        failure_code="source_commit_ambiguous",
                    )
                raise ApprovalError(
                    "source commit result is ambiguous and requires exact reconciliation"
                ) from reconcile_error
            if effective_source_oid is None:
                _invalidate_before_commit(
                    path, TransactionState.APPROVED, "source_commit_failed"
                )
                raise commit_error
        journal = _transition_after_commit(
            path,
            expected_state=TransactionState.APPROVED,
            new_state=TransactionState.SOURCE_COMMITTED,
            failure_code="source_journal_failed",
            source_commit_oid=effective_source_oid,
        )
    else:
        journal = _transition_reconciled(
            path,
            expected_state=TransactionState.APPROVED,
            new_state=TransactionState.SOURCE_COMMITTED,
            source_commit_oid=effective_source_oid,
        )

    try:
        if backend.commit_tree_oid(effective_source_oid) != card.proposed_tree_oid:
            raise ApprovalError("source commit tree differs from the proposed tree")
        _require_verification(
            verifier.prepare(workspace), card, phase="post-source"
        )

        def verify_clean(clean_root: Path) -> VerificationSnapshot:
            clean = verifier.clean_checkout(clean_root)
            _require_verification(clean, card, phase="clean checkout")
            return clean

        backend.temporary_clean_worktree(effective_source_oid, verify_clean)
        pre_signoff_remote = backend.fetch_remote_snapshot(
            remote_name=card.remote_name,
            expected_url=card.remote_url,
            ref=card.remote_ref,
        )
        _require_remote_baseline(pre_signoff_remote, card)
        _require_local_head(
            pre_signoff_remote, effective_source_oid, "signoff creation"
        )
        signoff_paths = _write_signoffs(
            workspace,
            card,
            reviewed_at=journal.reviewed_at or reviewed_at,
            event_id=journal.approval_event_id or event_id,
        )
        signoff_manifest = _expected_signoff_manifest(
            card,
            reviewed_at=journal.reviewed_at or reviewed_at,
            event_id=journal.approval_event_id or event_id,
        )
        if backend.current_head_oid() != effective_source_oid:
            raise ApprovalError("HEAD moved before signoff commit")
        try:
            signoff_oid = backend.commit_signoffs(
                signoff_paths,
                card.card_id,
                expected_parent_oid=effective_source_oid,
                expected_manifest=signoff_manifest,
            )
        except Exception as commit_error:
            try:
                reconciled_signoff = backend.reconcile_card_commit(
                    effective_source_oid,
                    card.card_id,
                    signoff_paths,
                    expected_manifest=signoff_manifest,
                )
            except Exception as reconcile_error:
                observed_oid = backend.current_head_oid()
                if observed_oid == effective_source_oid:
                    _record_local_failure(
                        path,
                        TransactionState.SOURCE_COMMITTED,
                        "signoff_commit_failed",
                    )
                else:
                    _transition_reconciled(
                        path,
                        expected_state=TransactionState.SOURCE_COMMITTED,
                        new_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
                        signoff_commit_oid=observed_oid,
                        final_commit_oid=observed_oid,
                        failure_code="signoff_commit_ambiguous",
                    )
                raise ApprovalError(
                    "signoff commit result is ambiguous and requires exact reconciliation"
                ) from reconcile_error
            if reconciled_signoff is None:
                _record_local_failure(
                    path, TransactionState.SOURCE_COMMITTED, "signoff_commit_failed"
                )
                raise commit_error
            signoff_oid = reconciled_signoff
        journal = _transition_after_commit(
            path,
            expected_state=TransactionState.SOURCE_COMMITTED,
            new_state=TransactionState.SIGNOFFS_COMMITTED,
            failure_code="signoff_journal_failed",
            signoff_commit_oid=signoff_oid,
            final_commit_oid=signoff_oid,
        )
        _require_verification(verifier.accepted(workspace), card, phase="accepted")
        verifier.render_current_phase(workspace)
        current_remote = backend.fetch_remote_snapshot(
            remote_name=card.remote_name,
            expected_url=card.remote_url,
            ref=card.remote_ref,
        )
        _require_remote_baseline(current_remote, card)
        _require_local_head(current_remote, signoff_oid, "push")
        if backend.current_head_oid() != signoff_oid:
            raise ApprovalError("HEAD moved before push")
        journal = _transition_reconciled(
            path,
            expected_state=TransactionState.SIGNOFFS_COMMITTED,
            new_state=TransactionState.VERIFIED,
        )
    except Exception:
        current = load_journal(path)
        _record_local_failure(path, current.state, "transaction_failed")
        raise

    try:
        backend.push_exact(signoff_oid, _expected_remote(card))
    except Exception:
        _record_local_failure(path, TransactionState.VERIFIED, "push_failed")
        raise
    try:
        journal = _transition_reconciled(
            path,
            expected_state=TransactionState.VERIFIED,
            new_state=TransactionState.PUSHED,
        )
    except Exception:
        current = load_journal(path)
        if current.state is TransactionState.PUSHED:
            journal = current
        else:
            # The remote may already contain final_commit_oid; VERIFIED is resumable.
            raise
    return _result(journal, source_was_committed=source_was_committed)


def resume_push(
    root: str | Path,
    *,
    card_id: str,
    backend: GitBackend,
    verifier: VerificationRunner,
    now: datetime | None = None,
) -> TransactionResult:
    workspace = Path(root)
    _require_card_id(card_id)
    path = _journal_path(workspace, card_id)
    journal = load_journal(path)
    if journal.card_id != card_id:
        raise ApprovalError("requested card ID does not match the journal")
    if journal.state not in {
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        TransactionState.VERIFIED,
    }:
        raise ApprovalError(
            "resume requires local_committed_push_failed or verified state, "
            f"found {journal.state.value}"
        )
    # Expiry gates the initial approval, not recovery of an already consumed card.
    # Reuse the persisted review instant to run the strict integrity loader.
    timestamp = (
        datetime.fromisoformat(journal.reviewed_at)
        if journal.reviewed_at is not None
        else (datetime.now(timezone.utc) if now is None else now)
    )
    card = load_approval_card(
        _card_path(workspace, card_id), journal.card_sha256, now=timestamp
    )
    _journal_matches_card(journal, card, card_id)
    source_only_recovery = (
        journal.state is TransactionState.LOCAL_COMMITTED_PUSH_FAILED
        and journal.final_commit_oid is None
    )
    recovery_exact_prestaged = False
    if not source_only_recovery:
        backend.require_main_with_clean_index()
    backend.reject_active_git_customization()

    if source_only_recovery:
        source_oid = journal.source_commit_oid
        if source_oid is None:
            raise ApprovalError("source-only recovery is missing its source commit OID")
        if card.source_manifest:
            reconciled_source = backend.reconcile_card_commit(
                card.head_oid,
                card.card_id,
                tuple(entry.path for entry in card.source_manifest),
                expected_tree_oid=card.proposed_tree_oid,
                expected_manifest=card.source_manifest,
            )
            if reconciled_source != source_oid:
                raise ApprovalError(
                    "recoverable source OID does not match the exact card commit"
                )
        elif source_oid != card.head_oid:
            raise ApprovalError("empty-manifest recovery has an unexpected source OID")
        if backend.current_head_oid() != source_oid:
            raise ApprovalError("HEAD moved from the recoverable source commit")
        if journal.reviewed_at is None or journal.approval_event_id is None:
            raise ApprovalError("source-only recovery is missing approval identity")
        signoff_manifest = _expected_signoff_manifest(
            card,
            reviewed_at=journal.reviewed_at,
            event_id=journal.approval_event_id,
        )
        recovery_exact_prestaged = (
            backend.require_main_with_clean_or_exact_signoff_index(
                signoff_manifest
            )
        )
        journal = _transition_reconciled(
            path,
            expected_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
            new_state=TransactionState.SOURCE_COMMITTED,
            failure_code=None,
        )
        try:
            if backend.commit_tree_oid(source_oid) != card.proposed_tree_oid:
                raise ApprovalError("source recovery tree differs from the proposed tree")

            def verify_clean(clean_root: Path) -> VerificationSnapshot:
                prepared = verifier.prepare(clean_root)
                _require_verification(
                    prepared, card, phase="post-source recovery"
                )
                clean = verifier.clean_checkout(clean_root)
                _require_verification(clean, card, phase="clean checkout recovery")
                return clean

            backend.temporary_clean_worktree(source_oid, verify_clean)
            pre_signoff_remote = backend.fetch_remote_snapshot(
                remote_name=card.remote_name,
                expected_url=card.remote_url,
                ref=card.remote_ref,
            )
            _require_remote_baseline(pre_signoff_remote, card)
            _require_local_head(
                pre_signoff_remote, source_oid, "recovered signoff creation"
            )
            signoff_paths = _write_signoffs(
                workspace,
                card,
                reviewed_at=journal.reviewed_at or "",
                event_id=journal.approval_event_id or "",
            )
            if backend.current_head_oid() != source_oid:
                raise ApprovalError("HEAD moved before recovered signoff commit")
            try:
                if recovery_exact_prestaged:
                    signoff_oid = backend.commit_signoffs(
                        signoff_paths,
                        card.card_id,
                        expected_parent_oid=source_oid,
                        expected_manifest=signoff_manifest,
                        allow_exact_prestaged=True,
                    )
                else:
                    signoff_oid = backend.commit_signoffs(
                        signoff_paths,
                        card.card_id,
                        expected_parent_oid=source_oid,
                        expected_manifest=signoff_manifest,
                    )
            except Exception as commit_error:
                reconciled_signoff = backend.reconcile_card_commit(
                    source_oid,
                    card.card_id,
                    signoff_paths,
                    expected_manifest=signoff_manifest,
                )
                if reconciled_signoff is None:
                    raise commit_error
                signoff_oid = reconciled_signoff
            journal = _transition_after_commit(
                path,
                expected_state=TransactionState.SOURCE_COMMITTED,
                new_state=TransactionState.SIGNOFFS_COMMITTED,
                failure_code="signoff_journal_failed",
                signoff_commit_oid=signoff_oid,
                final_commit_oid=signoff_oid,
            )
        except Exception:
            current = load_journal(path)
            _record_local_failure(path, current.state, "resume_source_failed")
            raise
    elif (
        journal.state is TransactionState.LOCAL_COMMITTED_PUSH_FAILED
        and journal.final_commit_oid is not None
    ):
        # Re-enter the last durable pre-verification state without recreating commits.
        source_oid = journal.source_commit_oid
        if source_oid is None:
            raise ApprovalError("signoff recovery is missing its source parent OID")
        signoff_paths = tuple(
            f"harness/signoffs/{profile.signoff_filename}"
            for profile in card.profiles
        )
        signoff_manifest = _expected_signoff_manifest(
            card,
            reviewed_at=journal.reviewed_at or "",
            event_id=journal.approval_event_id or "",
        )
        reconciled_signoff = backend.reconcile_card_commit(
            source_oid,
            card.card_id,
            signoff_paths,
            expected_manifest=signoff_manifest,
        )
        if reconciled_signoff != journal.final_commit_oid:
            raise ApprovalError(
                "recoverable final OID does not match the exact signoff commit"
            )
        recovery_remote = backend.fetch_remote_snapshot(
            remote_name=card.remote_name,
            expected_url=card.remote_url,
            ref=card.remote_ref,
        )
        _require_remote_metadata(recovery_remote, card)
        _require_local_head(
            recovery_remote, journal.final_commit_oid, "signoff recovery"
        )
        if recovery_remote.oid not in {card.remote_oid, journal.final_commit_oid}:
            raise ApprovalError("remote OID moved outside the reviewed push")
        if backend.current_head_oid() != journal.final_commit_oid:
            raise ApprovalError("HEAD moved from the recoverable signoff commit")
        _write_signoffs(
            workspace,
            card,
            reviewed_at=journal.reviewed_at or "",
            event_id=journal.approval_event_id or "",
            allow_create=False,
        )
        journal = _transition_reconciled(
            path,
            expected_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
            new_state=TransactionState.SIGNOFFS_COMMITTED,
            signoff_commit_oid=journal.signoff_commit_oid,
            final_commit_oid=journal.final_commit_oid,
            failure_code=None,
        )

    final_oid = journal.final_commit_oid
    if final_oid is None:
        raise ApprovalError("resume requires an existing final signoff commit OID")
    if journal.state is TransactionState.SIGNOFFS_COMMITTED:
        try:
            _require_verification(verifier.accepted(workspace), card, phase="accepted")
            verifier.render_current_phase(workspace)
            current_remote = backend.fetch_remote_snapshot(
                remote_name=card.remote_name,
                expected_url=card.remote_url,
                ref=card.remote_ref,
            )
            _require_remote_metadata(current_remote, card)
            _require_local_head(current_remote, final_oid, "resumed push")
            if backend.current_head_oid() != final_oid:
                raise ApprovalError("HEAD moved before resumed push")
            if current_remote.oid not in {card.remote_oid, final_oid}:
                raise ApprovalError("remote OID moved outside the reviewed push")
            journal = _transition_reconciled(
                path,
                expected_state=TransactionState.SIGNOFFS_COMMITTED,
                new_state=TransactionState.VERIFIED,
                failure_code=None,
            )
        except Exception:
            current = load_journal(path)
            _record_local_failure(path, current.state, "resume_verification_failed")
            raise
    else:
        _require_verification(verifier.accepted(workspace), card, phase="accepted")
        verifier.render_current_phase(workspace)
        current_remote = backend.fetch_remote_snapshot(
            remote_name=card.remote_name,
            expected_url=card.remote_url,
            ref=card.remote_ref,
        )
        _require_remote_metadata(current_remote, card)
        _require_local_head(current_remote, final_oid, "resumed push")
        if backend.current_head_oid() != final_oid:
            raise ApprovalError("HEAD moved before resumed push")
        if current_remote.oid not in {card.remote_oid, final_oid}:
            raise ApprovalError("remote OID moved outside the reviewed push")

    if current_remote.oid == final_oid:
        journal = _transition_reconciled(
            path,
            expected_state=TransactionState.VERIFIED,
            new_state=TransactionState.PUSHED,
        )
        return _result(journal, source_was_committed=bool(card.source_manifest))
    try:
        backend.push_exact(final_oid, _expected_remote(card))
    except Exception:
        _transition_reconciled(
            path,
            expected_state=TransactionState.VERIFIED,
            new_state=TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
            failure_code=journal.failure_code or "resume_push_failed",
        )
        raise
    try:
        journal = _transition_reconciled(
            path,
            expected_state=TransactionState.VERIFIED,
            new_state=TransactionState.PUSHED,
        )
    except Exception:
        current = load_journal(path)
        if current.state is TransactionState.PUSHED:
            journal = current
        else:
            raise
    return _result(journal, source_was_committed=bool(card.source_manifest))


__all__ = [
    "TransactionResult",
    "PreparedTransaction",
    "VerificationRunner",
    "VerificationSnapshot",
    "approve_card",
    "prepare_review",
    "resume_push",
]
