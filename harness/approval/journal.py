from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from harness.engine.models import canonical_json

from .models import ApprovalError


_CARD_ID_RE = re.compile(r"approval_[0-9a-f]{24}")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_EVENT_ID_RE = re.compile(r"approval_event_[0-9a-f]{24}")
_OID_RE = re.compile(r"[0-9a-f]{40}")
_FAILURE_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_MAX_JOURNAL_BYTES = 64 * 1024
_UNSET = object()


class JournalError(ApprovalError):
    """Raised when an approval transaction journal is invalid or conflicts."""


class TransactionState(str, Enum):
    PREPARED = "prepared"
    APPROVED = "approved"
    SOURCE_COMMITTED = "source_committed"
    SIGNOFFS_COMMITTED = "signoffs_committed"
    VERIFIED = "verified"
    PUSHED = "pushed"
    INVALIDATED = "invalidated"
    LOCAL_COMMITTED_PUSH_FAILED = "local_committed_push_failed"


@dataclass(frozen=True)
class TransactionJournal:
    card_id: str
    card_sha256: str
    state: TransactionState
    reviewed_at: str | None = None
    approval_event_id: str | None = None
    source_commit_oid: str | None = None
    signoff_commit_oid: str | None = None
    final_commit_oid: str | None = None
    failure_code: str | None = None


_JOURNAL_FIELDS = frozenset(TransactionJournal.__dataclass_fields__)
_LEGAL_TRANSITIONS = frozenset(
    {
        (TransactionState.PREPARED, TransactionState.APPROVED),
        (TransactionState.PREPARED, TransactionState.INVALIDATED),
        (TransactionState.APPROVED, TransactionState.SOURCE_COMMITTED),
        (TransactionState.APPROVED, TransactionState.INVALIDATED),
        (
            TransactionState.APPROVED,
            TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        ),
        (
            TransactionState.SOURCE_COMMITTED,
            TransactionState.SIGNOFFS_COMMITTED,
        ),
        (
            TransactionState.SOURCE_COMMITTED,
            TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        ),
        (TransactionState.SIGNOFFS_COMMITTED, TransactionState.VERIFIED),
        (
            TransactionState.SIGNOFFS_COMMITTED,
            TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        ),
        (TransactionState.VERIFIED, TransactionState.PUSHED),
        (
            TransactionState.VERIFIED,
            TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        ),
        (
            TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
            TransactionState.VERIFIED,
        ),
        (
            TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
            TransactionState.SOURCE_COMMITTED,
        ),
        (
            TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
            TransactionState.SIGNOFFS_COMMITTED,
        ),
    }
)
_REQUIRED_TRANSITION_FIELDS = {
    (TransactionState.PREPARED, TransactionState.APPROVED): frozenset(
        {"reviewed_at", "approval_event_id"}
    ),
    (TransactionState.APPROVED, TransactionState.SOURCE_COMMITTED): frozenset(
        {"source_commit_oid"}
    ),
    (
        TransactionState.APPROVED,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    ): frozenset({"source_commit_oid", "failure_code"}),
    (
        TransactionState.SOURCE_COMMITTED,
        TransactionState.SIGNOFFS_COMMITTED,
    ): frozenset({"signoff_commit_oid", "final_commit_oid"}),
    (TransactionState.PREPARED, TransactionState.INVALIDATED): frozenset(
        {"failure_code"}
    ),
    (TransactionState.APPROVED, TransactionState.INVALIDATED): frozenset(
        {"failure_code"}
    ),
    (
        TransactionState.SOURCE_COMMITTED,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    ): frozenset({"failure_code"}),
    (
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        TransactionState.SOURCE_COMMITTED,
    ): frozenset({"failure_code"}),
    (
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        TransactionState.SIGNOFFS_COMMITTED,
    ): frozenset({"signoff_commit_oid", "final_commit_oid", "failure_code"}),
    (
        TransactionState.SIGNOFFS_COMMITTED,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    ): frozenset({"failure_code"}),
    (
        TransactionState.VERIFIED,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    ): frozenset({"failure_code"}),
}


def _require_pattern(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise JournalError(f"journal {label} has a non-canonical format")
    return value


def _optional_pattern(
    value: Any, pattern: re.Pattern[str], label: str
) -> str | None:
    if value is None:
        return None
    return _require_pattern(value, pattern, label)


def _optional_reviewed_at(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise JournalError("journal reviewed_at must be a timestamp or null")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise JournalError("journal reviewed_at must be ISO-8601") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise JournalError("journal reviewed_at must include a timezone")
    if timestamp.isoformat() != value:
        raise JournalError("journal reviewed_at must use canonical ISO-8601")
    return value


def _parse_journal(value: Any) -> TransactionJournal:
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise JournalError("journal must be a JSON object")
    actual_fields = set(value)
    if actual_fields != _JOURNAL_FIELDS:
        missing = sorted(_JOURNAL_FIELDS - actual_fields)
        unexpected = sorted(actual_fields - _JOURNAL_FIELDS)
        details: list[str] = []
        if missing:
            details.append("missing fields: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected fields: " + ", ".join(unexpected))
        raise JournalError("journal field schema invalid: " + "; ".join(details))
    try:
        state = TransactionState(value["state"])
    except (TypeError, ValueError) as exc:
        raise JournalError("journal state is invalid") from exc
    journal = TransactionJournal(
        card_id=_require_pattern(value["card_id"], _CARD_ID_RE, "card_id"),
        card_sha256=_require_pattern(
            value["card_sha256"], _DIGEST_RE, "card_sha256"
        ),
        state=state,
        reviewed_at=_optional_reviewed_at(value["reviewed_at"]),
        approval_event_id=_optional_pattern(
            value["approval_event_id"], _EVENT_ID_RE, "approval_event_id"
        ),
        source_commit_oid=_optional_pattern(
            value["source_commit_oid"], _OID_RE, "source_commit_oid"
        ),
        signoff_commit_oid=_optional_pattern(
            value["signoff_commit_oid"], _OID_RE, "signoff_commit_oid"
        ),
        final_commit_oid=_optional_pattern(
            value["final_commit_oid"], _OID_RE, "final_commit_oid"
        ),
        failure_code=_optional_pattern(
            value["failure_code"], _FAILURE_CODE_RE, "failure_code"
        ),
    )
    _validate_state_fields(journal)
    return journal


def _validate_state_fields(journal: TransactionJournal) -> None:
    if (journal.reviewed_at is None) != (journal.approval_event_id is None):
        raise JournalError(
            "journal reviewed_at and approval_event_id must be persisted together"
        )
    if journal.state in {
        TransactionState.APPROVED,
        TransactionState.SOURCE_COMMITTED,
        TransactionState.SIGNOFFS_COMMITTED,
        TransactionState.VERIFIED,
        TransactionState.PUSHED,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    } and journal.reviewed_at is None:
        raise JournalError("journal approved transaction identity is missing")
    if journal.state in {
        TransactionState.SOURCE_COMMITTED,
        TransactionState.SIGNOFFS_COMMITTED,
        TransactionState.VERIFIED,
        TransactionState.PUSHED,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    } and journal.source_commit_oid is None:
        raise JournalError("journal source commit oid is missing")
    if journal.state in {
        TransactionState.SIGNOFFS_COMMITTED,
        TransactionState.VERIFIED,
        TransactionState.PUSHED,
    } and (
        journal.signoff_commit_oid is None or journal.final_commit_oid is None
    ):
        raise JournalError("journal signoff or final commit oid is missing")
    if (journal.signoff_commit_oid is None) != (journal.final_commit_oid is None):
        raise JournalError(
            "journal signoff_commit_oid and final_commit_oid must be persisted together"
        )
    if journal.state is TransactionState.PREPARED and any(
        value is not None
        for value in (
            journal.reviewed_at,
            journal.approval_event_id,
            journal.source_commit_oid,
            journal.signoff_commit_oid,
            journal.final_commit_oid,
            journal.failure_code,
        )
    ):
        raise JournalError("prepared journal cannot contain transaction results")
    if journal.state is TransactionState.APPROVED and any(
        value is not None
        for value in (
            journal.source_commit_oid,
            journal.signoff_commit_oid,
            journal.final_commit_oid,
            journal.failure_code,
        )
    ):
        raise JournalError("approved journal cannot contain commit results")
    if journal.state is TransactionState.SOURCE_COMMITTED and any(
        value is not None
        for value in (
            journal.signoff_commit_oid,
            journal.final_commit_oid,
            journal.failure_code,
        )
    ):
        raise JournalError("source_committed journal contains premature results")
    if journal.state is TransactionState.SIGNOFFS_COMMITTED and journal.failure_code:
        raise JournalError("signoffs_committed journal cannot contain failure state")
    if journal.state is TransactionState.INVALIDATED and any(
        value is not None
        for value in (
            journal.source_commit_oid,
            journal.signoff_commit_oid,
            journal.final_commit_oid,
        )
    ):
        raise JournalError("invalidated journal cannot contain committed OIDs")
    if journal.state in {
        TransactionState.INVALIDATED,
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
    }:
        if journal.failure_code is None:
            raise JournalError("journal failure state requires a redacted failure_code")
    elif journal.state not in {
        TransactionState.VERIFIED,
        TransactionState.PUSHED,
    } and journal.failure_code is not None:
        raise JournalError("journal failure_code is only valid in a failure state")


def _journal_dict(journal: TransactionJournal) -> dict[str, Any]:
    value = asdict(journal)
    value["state"] = journal.state.value
    return value


def _journal_name(path: Path) -> str:
    if path.name in {"", ".", ".."}:
        raise JournalError("journal path must name a file")
    return path.name


@contextmanager
def _locked_directory(
    directory: Path, *, exclusive: bool, create: bool = False
) -> Iterator[int]:
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(directory, flags)
    except OSError as exc:
        raise JournalError(f"journal directory could not be opened safely: {exc}") from exc
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise JournalError("journal parent must be a directory")
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(descriptor, operation)
        try:
            yield descriptor
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _temporary_file(directory_descriptor: int, target_name: str) -> tuple[int, str]:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    for _ in range(128):
        name = f".{target_name}.{secrets.token_hex(12)}.tmp"
        try:
            descriptor = os.open(
                name,
                flags,
                0o600,
                dir_fd=directory_descriptor,
            )
            return descriptor, name
        except FileExistsError:
            continue
        except OSError as exc:
            raise JournalError(f"journal temporary file could not be created: {exc}") from exc
    raise JournalError("journal temporary filename collision limit exceeded")


def _write_payload(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise JournalError("journal temporary write made no progress")
        view = view[written:]
    os.fsync(descriptor)


def _cleanup_temporary(directory_descriptor: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=directory_descriptor)
    except FileNotFoundError:
        return
    os.fsync(directory_descriptor)


def _serialized(journal: TransactionJournal) -> bytes:
    return (canonical_json(_journal_dict(journal)) + "\n").encode("utf-8")


def _publish_new(
    directory_descriptor: int, target_name: str, journal: TransactionJournal
) -> None:
    descriptor, temporary_name = _temporary_file(directory_descriptor, target_name)
    try:
        _write_payload(descriptor, _serialized(journal))
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(
                temporary_name,
                target_name,
                src_dir_fd=directory_descriptor,
                dst_dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise JournalError(f"journal already exists: {target_name}") from exc
        os.fsync(directory_descriptor)
    except JournalError:
        raise
    except OSError as exc:
        raise JournalError(f"atomic journal publication failed: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        _cleanup_temporary(directory_descriptor, temporary_name)


def _replace_existing(
    directory_descriptor: int, target_name: str, journal: TransactionJournal
) -> None:
    descriptor, temporary_name = _temporary_file(directory_descriptor, target_name)
    try:
        _write_payload(descriptor, _serialized(journal))
        os.close(descriptor)
        descriptor = -1
        os.replace(
            temporary_name,
            target_name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
        )
        os.fsync(directory_descriptor)
    except Exception as exc:
        if isinstance(exc, JournalError):
            raise
        raise JournalError(f"atomic journal replace failed: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        _cleanup_temporary(directory_descriptor, temporary_name)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, nested in pairs:
        if key in value:
            raise JournalError(f"journal JSON contains duplicate key: {key}")
        value[key] = nested
    return value


def _load_from_directory(
    directory_descriptor: int, name: str
) -> tuple[TransactionJournal, tuple[int, int]]:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(name, flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise JournalError(
            f"journal could not be loaded without following links: {exc}"
        ) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise JournalError("journal path must be a regular file")
        if metadata.st_size > _MAX_JOURNAL_BYTES:
            raise JournalError("journal exceeds the maximum byte size")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(64 * 1024, _MAX_JOURNAL_BYTES + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_JOURNAL_BYTES:
                raise JournalError("journal exceeds the maximum byte size")
        try:
            raw = b"".join(chunks).decode("utf-8")
            value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
        except JournalError:
            raise
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise JournalError(f"journal JSON could not be loaded: {exc}") from exc
        return _parse_journal(value), (metadata.st_dev, metadata.st_ino)
    finally:
        os.close(descriptor)


def _require_same_file(
    directory_descriptor: int, name: str, identity: tuple[int, int]
) -> None:
    try:
        metadata = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    except OSError as exc:
        raise JournalError(f"journal changed during transition: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode) or (metadata.st_dev, metadata.st_ino) != identity:
        raise JournalError("journal changed during transition")


def create_journal(
    path: str | Path, *, card_id: str, card_sha256: str
) -> TransactionJournal:
    journal_path = Path(path)
    journal = _parse_journal(
        {
            "card_id": card_id,
            "card_sha256": card_sha256,
            "state": TransactionState.PREPARED.value,
            "reviewed_at": None,
            "approval_event_id": None,
            "source_commit_oid": None,
            "signoff_commit_oid": None,
            "final_commit_oid": None,
            "failure_code": None,
        }
    )
    name = _journal_name(journal_path)
    with _locked_directory(journal_path.parent, exclusive=True, create=True) as directory:
        _publish_new(directory, name, journal)
    return journal


def load_journal(path: str | Path) -> TransactionJournal:
    journal_path = Path(path)
    name = _journal_name(journal_path)
    with _locked_directory(journal_path.parent, exclusive=False) as directory:
        journal, _ = _load_from_directory(directory, name)
        return journal


def transition_journal(
    path: str | Path,
    *,
    expected_state: TransactionState,
    new_state: TransactionState,
    reviewed_at: str | None | object = _UNSET,
    approval_event_id: str | None | object = _UNSET,
    source_commit_oid: str | None | object = _UNSET,
    signoff_commit_oid: str | None | object = _UNSET,
    final_commit_oid: str | None | object = _UNSET,
    failure_code: str | None | object = _UNSET,
) -> TransactionJournal:
    if not isinstance(expected_state, TransactionState) or not isinstance(
        new_state, TransactionState
    ):
        raise JournalError("journal transition states must be TransactionState values")
    transition = (expected_state, new_state)
    if transition not in _LEGAL_TRANSITIONS:
        raise JournalError(
            f"illegal journal state transition: {expected_state.value} -> "
            f"{new_state.value}"
        )

    updates = {
        key: value
        for key, value in {
            "reviewed_at": reviewed_at,
            "approval_event_id": approval_event_id,
            "source_commit_oid": source_commit_oid,
            "signoff_commit_oid": signoff_commit_oid,
            "final_commit_oid": final_commit_oid,
            "failure_code": failure_code,
        }.items()
        if value is not _UNSET
    }
    missing_updates = _REQUIRED_TRANSITION_FIELDS.get(transition, frozenset()) - set(
        updates
    )
    if missing_updates:
        raise JournalError(
            "journal transition is missing required fields: "
            + ", ".join(sorted(missing_updates))
        )
    journal_path = Path(path)
    name = _journal_name(journal_path)
    with _locked_directory(journal_path.parent, exclusive=True) as directory:
        current, identity = _load_from_directory(directory, name)
        for key, value in updates.items():
            existing = getattr(current, key)
            clearing_failure = key == "failure_code" and value is None
            if existing is not None and existing != value and not clearing_failure:
                raise JournalError(
                    f"journal transition conflicts with persisted {key}"
                )

        candidate = replace(current, state=new_state, **updates)
        candidate = _parse_journal(_journal_dict(candidate))
        if current.state is new_state:
            if candidate != current:
                raise JournalError(
                    "journal transition replay conflicts with persisted state"
                )
            return current
        if current.state is not expected_state:
            raise JournalError(
                f"journal state conflict: expected {expected_state.value}, "
                f"found {current.state.value}"
            )

        _require_same_file(directory, name, identity)
        _replace_existing(directory, name, candidate)
        return candidate


__all__ = [
    "JournalError",
    "TransactionJournal",
    "TransactionState",
    "create_journal",
    "load_journal",
    "transition_journal",
]
