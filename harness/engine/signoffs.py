from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from harness.approval.models import PROFILE_RATIONALES


_CONTEXT_FIELDS = (
    "contract_id",
    "contract_version",
    "contract_digest",
    "profile_id",
    "evaluation_id",
    "evidence_digest",
)
_APPROVAL_BINDING_FIELDS = (
    "approval_card_id",
    "approval_card_digest",
    "approval_event_id",
)
_SIGNOFF_FIELDS = frozenset(
    {
        *_CONTEXT_FIELDS,
        "role",
        "reviewer_id",
        "decision",
        "rationale",
        "reviewed_at",
        "supersedes",
        *_APPROVAL_BINDING_FIELDS,
    }
)
_GIT_CONFIG_ARGUMENTS = (
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.attributesFile=/dev/null",
)


@dataclass(frozen=True)
class SignoffContext:
    contract_id: str
    contract_version: str
    contract_digest: str
    profile_id: str
    evaluation_id: str
    evidence_digest: str
    required_roles: tuple[str, ...]
    repository_root: str | None = None


@dataclass(frozen=True)
class SignoffIssue:
    path: str
    role: str | None
    reason_code: str
    message: str
    mismatched_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class SignoffValidationResult:
    valid_roles: tuple[str, ...]
    missing_roles: tuple[str, ...]
    stale_signoffs: tuple[SignoffIssue, ...]
    invalid_signoffs: tuple[SignoffIssue, ...]
    duplicate_roles: tuple[str, ...]
    ignored_metadata_files: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.missing_roles and not self.invalid_signoffs

    @property
    def valid_signoff_roles(self) -> frozenset[str]:
        return frozenset(self.valid_roles)


def _is_generated_metadata(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.endswith(".schema.json")
        or name.startswith("signoff_schema")
        or name.startswith("signoff_request")
        or name in {"schema.json", "request.json"}
    )


def _read_regular_file_once(path: Path) -> bytes | None:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError:
        return None
    finally:
        os.close(descriptor)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    payload = b"".join(chunks)
    if before_identity != after_identity or len(payload) != after.st_size:
        return None
    return payload


def _contains_override(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = str(key).lower()
            if "waiv" in normalized_key or "override" in normalized_key:
                return True
            if _contains_override(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_override(item) for item in value)
    return False


def _issue(
    path: Path,
    *,
    role: str | None,
    reason_code: str,
    message: str,
    mismatched_fields: tuple[str, ...] = (),
) -> SignoffIssue:
    return SignoffIssue(
        path=path.name,
        role=role,
        reason_code=reason_code,
        message=message,
        mismatched_fields=mismatched_fields,
    )


def _expected_context(context: SignoffContext) -> dict[str, str]:
    return {
        "contract_id": context.contract_id,
        "contract_version": context.contract_version,
        "contract_digest": context.contract_digest,
        "profile_id": context.profile_id,
        "evaluation_id": context.evaluation_id,
        "evidence_digest": context.evidence_digest,
    }


def _valid_review_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return timestamp.tzinfo is not None and timestamp.utcoffset() is not None


def _matches_current_sibling_dialog_context(
    value: Mapping[str, Any], expected_context: Mapping[str, str]
) -> bool:
    profile_id = value.get("profile_id")
    expected_profile_id = expected_context["profile_id"]
    return bool(
        isinstance(profile_id, str)
        and profile_id in PROFILE_RATIONALES
        and expected_profile_id in PROFILE_RATIONALES
        and profile_id != expected_profile_id
        and value.get("rationale") == PROFILE_RATIONALES[profile_id]
        and all(
            value.get(field) == expected_context[field]
            for field in _CONTEXT_FIELDS
            if field != "profile_id"
        )
    )


def _valid_approval_binding(
    value: Mapping[str, Any], *, require_current_rationale: bool = True
) -> bool:
    present = tuple(field in value for field in _APPROVAL_BINDING_FIELDS)
    if not any(present):
        return True
    if not all(present):
        return False
    card_id = value["approval_card_id"]
    card_digest = value["approval_card_digest"]
    event_id = value["approval_event_id"]
    raw_profile_id = value.get("profile_id")
    profile_id = raw_profile_id if isinstance(raw_profile_id, str) else ""
    rationale = value.get("rationale")
    rationale_valid = isinstance(rationale, str) and (
        not require_current_rationale
        or rationale == PROFILE_RATIONALES.get(profile_id)
    )
    return bool(
        isinstance(card_id, str)
        and re.fullmatch(r"approval_[0-9a-f]{24}", card_id)
        and isinstance(card_digest, str)
        and re.fullmatch(r"[0-9a-f]{64}", card_digest)
        and isinstance(event_id, str)
        and re.fullmatch(r"approval_event_[0-9a-f]{24}", event_id)
        and value.get("reviewer_id") == "project_owner"
        and rationale_valid
    )


def _sanitized_git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"LANG", "TMPDIR", "TMP", "TEMP"} or key.startswith("LC_")
    }
    environment.update(
        {
            "PATH": os.defpath,
            "HOME": os.devnull,
            "XDG_CONFIG_HOME": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _git_arguments(arguments: Sequence[str]) -> tuple[str, ...]:
    values = tuple(arguments)
    if not values:
        raise ValueError("Git arguments cannot be empty")
    command = ("git", *_GIT_CONFIG_ARGUMENTS, values[0])
    if values[0] in {"diff", "log", "show"}:
        command += ("--no-ext-diff", "--no-textconv")
    return (*command, *values[1:])


def _run_git(
    repository_root: Path,
    arguments: Sequence[str],
    *,
    environment: Mapping[str, str] | None = None,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        _git_arguments(arguments),
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=text,
        timeout=15,
        env=dict(environment or _sanitized_git_environment()),
    )


@dataclass(frozen=True)
class _RawGitRepository:
    """Raw object view that excludes repository refs, grafts, config, and index."""

    root: Path
    head_oid: str
    object_directory: Path
    object_format: str


def _initialize_isolated_git_directory(
    git_directory: Path, object_format: str
) -> None:
    for relative in ("objects/info", "objects/pack", "refs/heads", "refs/tags"):
        (git_directory / relative).mkdir(parents=True, exist_ok=True)
    (git_directory / "HEAD").write_text(
        "ref: refs/heads/untrusted-input-disabled\n",
        encoding="ascii",
    )
    if object_format == "sha256":
        (git_directory / "config").write_text(
            "[core]\n\trepositoryFormatVersion = 1\n\tbare = true\n"
            "[extensions]\n\tobjectFormat = sha256\n",
            encoding="ascii",
        )


def _run_raw_git(
    repository: _RawGitRepository,
    arguments: Sequence[str],
    *,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    with tempfile.TemporaryDirectory(prefix="signoff-git-", dir="/tmp") as temporary:
        git_directory = Path(temporary)
        _initialize_isolated_git_directory(git_directory, repository.object_format)
        environment = _sanitized_git_environment()
        environment.update(
            {
                "GIT_DIR": str(git_directory),
                "GIT_OBJECT_DIRECTORY": str(repository.object_directory),
            }
        )
        return _run_git(
            repository.root,
            arguments,
            environment=environment,
            text=text,
        )


def _open_raw_git_repository(repository_root: Path) -> _RawGitRepository | None:
    repository_root = repository_root.resolve()
    environment = _sanitized_git_environment()
    head = _run_git(
        repository_root,
        ("rev-parse", "--verify", "HEAD"),
        environment=environment,
    )
    objects = _run_git(
        repository_root,
        ("rev-parse", "--path-format=absolute", "--git-path", "objects"),
        environment=environment,
    )
    object_format = _run_git(
        repository_root,
        ("rev-parse", "--show-object-format"),
        environment=environment,
    )
    if any(
        completed.returncode != 0
        for completed in (head, objects, object_format)
    ):
        return None
    head_oid = head.stdout.strip()
    format_name = object_format.stdout.strip()
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", head_oid):
        return None
    if format_name not in {"sha1", "sha256"}:
        return None
    try:
        object_directory = Path(objects.stdout.strip()).resolve(strict=True)
    except OSError:
        return None
    if not object_directory.is_dir():
        return None
    repository = _RawGitRepository(
        root=repository_root,
        head_oid=head_oid,
        object_directory=object_directory,
        object_format=format_name,
    )
    object_type = _run_raw_git(repository, ("cat-file", "-t", head_oid))
    if object_type.returncode != 0 or object_type.stdout.strip() != "commit":
        return None
    return repository


def _relative_signoff_path(
    repository: _RawGitRepository, path: Path
) -> Path | None:
    try:
        absolute = Path(os.path.abspath(path))
        relative = absolute.relative_to(repository.root)
    except ValueError:
        return None
    if relative.parts[:2] != ("harness", "signoffs"):
        return None
    return relative


def _git_signoff_is_committed_clean(
    repository: _RawGitRepository, path: Path, working_payload: bytes
) -> bool:
    relative = _relative_signoff_path(repository, path)
    if relative is None:
        return False
    committed = _run_raw_git(
        repository,
        ("cat-file", "blob", f"{repository.head_oid}:{relative.as_posix()}"),
        text=False,
    )
    if committed.returncode != 0 or committed.stdout != working_payload:
        return False
    history_commits = _git_path_history_commits(repository, path)
    if history_commits is None or len(history_commits) != 1:
        return False
    addition_commit = _git_first_addition_commit(repository, path)
    if addition_commit is None or addition_commit != history_commits[0]:
        return False
    original = _run_raw_git(
        repository,
        ("cat-file", "blob", f"{addition_commit}:{relative.as_posix()}"),
        text=False,
    )
    return original.returncode == 0 and original.stdout == working_payload


def _git_path_history_commits(
    repository: _RawGitRepository, path: Path
) -> tuple[str, ...] | None:
    relative = _relative_signoff_path(repository, path)
    if relative is None:
        return None
    completed = _run_raw_git(
        repository,
        (
            "log",
            "--full-history",
            "--no-renames",
            "--format=%H",
            repository.head_oid,
            "--",
            relative.as_posix(),
        ),
    )
    if completed.returncode != 0:
        return None
    return tuple(
        line.strip() for line in completed.stdout.splitlines() if line.strip()
    )


def _git_first_addition_commit(
    repository: _RawGitRepository, path: Path
) -> str | None:
    relative = _relative_signoff_path(repository, path)
    if relative is None:
        return None
    completed = _run_raw_git(
        repository,
        (
            "log",
            "--full-history",
            "--no-renames",
            "--reverse",
            "--diff-filter=A",
            "--format=%H",
            repository.head_oid,
            "--",
            relative.as_posix(),
        ),
    )
    if completed.returncode != 0:
        return None
    commits = tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())
    return commits[0] if commits else None


def _git_target_predates_source(
    repository: _RawGitRepository, source: Path, target: Path
) -> bool:
    source_commit = _git_first_addition_commit(repository, source)
    target_commit = _git_first_addition_commit(repository, target)
    if source_commit is None or target_commit is None or source_commit == target_commit:
        return False
    completed = _run_raw_git(
        repository,
        ("merge-base", "--is-ancestor", target_commit, source_commit),
    )
    return completed.returncode == 0


def validate_signoff_directory(
    directory: str | Path,
    context: SignoffContext,
) -> SignoffValidationResult:
    """Validate append-only signoffs for one profile evaluation.

    Stale signoffs are retained as explicit audit findings but do not make an
    otherwise current approval invalid. Two current approvals for the same
    role are both rejected so filesystem ordering cannot select a reviewer.
    """

    root = Path(directory)
    paths = sorted(root.glob("*.json")) if root.is_dir() else []
    regular_files: dict[Path, bool] = {}
    for path in paths:
        try:
            regular_files[path] = stat.S_ISREG(path.lstat().st_mode)
        except OSError:
            regular_files[path] = False
    metadata_paths = tuple(
        path
        for path in paths
        if regular_files[path] and _is_generated_metadata(path)
    )
    signoff_paths = tuple(path for path in paths if path not in metadata_paths)

    required_roles = tuple(dict.fromkeys(context.required_roles))
    required_role_set = set(required_roles)
    expected_context = _expected_context(context)
    stale: list[SignoffIssue] = []
    invalid: list[SignoffIssue] = []
    current_by_role: dict[str, list[Path]] = {}
    current_values: dict[Path, Mapping[str, Any]] = {}
    validated_values: dict[Path, Mapping[str, Any]] = {}
    repository_root = (
        Path(context.repository_root) if context.repository_root is not None else None
    )
    git_repository = (
        _open_raw_git_repository(repository_root)
        if repository_root is not None
        and bool(signoff_paths)
        and all(regular_files[path] for path in signoff_paths)
        else None
    )

    for path in signoff_paths:
        captured_payload = (
            _read_regular_file_once(path) if regular_files[path] else None
        )
        if captured_payload is None or (
            repository_root is not None
            and (
                git_repository is None
                or not _git_signoff_is_committed_clean(
                    git_repository, path, captured_payload
                )
            )
        ):
            invalid.append(
                _issue(
                    path,
                    role=None,
                    reason_code="signoff_file_untrusted",
                    message=(
                        "Production signoffs must be regular, committed, and clean "
                        "files under harness/signoffs/."
                    ),
                )
            )
            continue
        try:
            value = json.loads(captured_payload)
        except (UnicodeError, json.JSONDecodeError) as exc:
            invalid.append(
                _issue(
                    path,
                    role=None,
                    reason_code="signoff_json_invalid",
                    message=f"Signoff JSON could not be read: {exc}",
                )
            )
            continue

        if not isinstance(value, Mapping):
            invalid.append(
                _issue(
                    path,
                    role=None,
                    reason_code="signoff_not_object",
                    message="Signoff JSON must be an object.",
                )
            )
            continue

        raw_role = value.get("role")
        role = raw_role if isinstance(raw_role, str) else None

        if _contains_override(value):
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_override_forbidden",
                    message="Signoffs cannot contain waiver or override semantics.",
                )
            )
            continue

        if value.get("decision") != "approved":
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_decision_not_approved",
                    message="Only an explicit approved decision is valid.",
                )
            )
            continue

        if not _valid_approval_binding(value, require_current_rationale=False):
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_approval_binding_invalid",
                    message=(
                        "Dialog signoffs require a canonical approval card ID, "
                        "full card digest, approval event ID, project owner, "
                        "and string rationale."
                    ),
                )
            )
            continue

        unknown_fields = set(value) - _SIGNOFF_FIELDS
        review_metadata_valid = (
            isinstance(value.get("reviewer_id"), str)
            and bool(value["reviewer_id"].strip())
            and isinstance(value.get("rationale"), str)
            and bool(value["rationale"].strip())
            and _valid_review_timestamp(value.get("reviewed_at"))
        )
        if unknown_fields or not review_metadata_valid:
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_review_metadata_invalid",
                    message=(
                        "Signoff reviewer identity, rationale, and timezone-aware "
                        "reviewed_at are required; unknown fields are forbidden."
                    ),
                    mismatched_fields=tuple(sorted(unknown_fields)),
                )
            )
            continue

        missing_fields = tuple(field for field in _CONTEXT_FIELDS if field not in value)
        if missing_fields:
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_context_missing",
                    message="Signoff is missing evaluation context fields.",
                    mismatched_fields=missing_fields,
                )
            )
            continue

        mismatched_fields = tuple(
            field
            for field in _CONTEXT_FIELDS
            if value.get(field) != expected_context[field]
        )
        if mismatched_fields:
            has_dialog_binding = any(
                field in value for field in _APPROVAL_BINDING_FIELDS
            )
            known_stale_dialog = bool(
                git_repository is not None
                or _matches_current_sibling_dialog_context(value, expected_context)
            )
            if has_dialog_binding and not known_stale_dialog:
                invalid.append(
                    _issue(
                        path,
                        role=role,
                        reason_code="signoff_approval_binding_invalid",
                        message=(
                            "A stale dialog signoff must be committed-clean in "
                            "the production repository or exactly match the "
                            "current sibling profile context and rationale."
                        ),
                    )
                )
                continue

            validated_values[path] = value
            stale.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_context_mismatch",
                    message="Signoff belongs to a different evaluation context.",
                    mismatched_fields=mismatched_fields,
                )
            )
            continue

        if not _valid_approval_binding(value):
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_approval_binding_invalid",
                    message=(
                        "Dialog signoffs for the current evaluation require the "
                        "fixed profile rationale."
                    ),
                )
            )
            continue

        validated_values[path] = value

        if role not in required_role_set:
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_role_not_required",
                    message="Signoff role is not required by this profile.",
                )
            )
            continue

        current_by_role.setdefault(role, []).append(path)
        current_values[path] = value

    superseded_paths: set[Path] = set()
    invalid_current_paths: set[Path] = set()
    supersession_edges: dict[Path, Path] = {}
    for path, value in current_values.items():
        supersedes = value.get("supersedes")
        if supersedes is None:
            continue
        role = str(value["role"])
        valid_name = (
            isinstance(supersedes, str)
            and supersedes == Path(supersedes).name
            and supersedes != path.name
        )
        target = root / supersedes if valid_name else None
        target_value = validated_values.get(target) if target is not None else None
        same_binding = bool(
            target_value is not None
            and all(
                target_value.get(field) == value.get(field)
                for field in ("contract_id", "profile_id", "role")
            )
        )
        history_valid = bool(
            repository_root is None
            or (
                git_repository is not None
                and target is not None
                and _git_target_predates_source(git_repository, path, target)
            )
        )
        if (
            not valid_name
            or target_value is None
            or not same_binding
            or not history_valid
        ):
            invalid_current_paths.add(path)
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_supersedes_invalid",
                    message=(
                        "supersedes must name a prior committed signoff for the "
                        "same contract, profile, and role."
                    ),
                )
            )
            continue
        supersession_edges[path] = target

    for start in supersession_edges:
        seen: set[Path] = set()
        current = start
        while current in supersession_edges:
            if current in seen:
                cycle = seen | {current}
                for path in cycle:
                    if path in invalid_current_paths:
                        continue
                    invalid_current_paths.add(path)
                    invalid.append(
                        _issue(
                            path,
                            role=str(current_values[path]["role"]),
                            reason_code="signoff_supersession_cycle",
                            message="Signoff supersession references must be acyclic.",
                        )
                    )
                break
            seen.add(current)
            current = supersession_edges[current]

    for source, target in supersession_edges.items():
        if source not in invalid_current_paths:
            superseded_paths.add(target)

    active_by_role = {
        role: [
            path
            for path in role_paths
            if path not in superseded_paths and path not in invalid_current_paths
        ]
        for role, role_paths in current_by_role.items()
    }

    duplicate_role_set = {
        role for role, role_paths in active_by_role.items() if len(role_paths) > 1
    }
    for role in required_roles:
        if role not in duplicate_role_set:
            continue
        for path in sorted(active_by_role[role]):
            invalid.append(
                _issue(
                    path,
                    role=role,
                    reason_code="signoff_duplicate_role",
                    message="Multiple current signoffs claim the same reviewer role.",
                )
            )

    valid_role_set = {
        role for role, role_paths in active_by_role.items() if len(role_paths) == 1
    } - duplicate_role_set
    valid_roles = tuple(role for role in required_roles if role in valid_role_set)
    missing_roles = tuple(role for role in required_roles if role not in valid_role_set)

    return SignoffValidationResult(
        valid_roles=valid_roles,
        missing_roles=missing_roles,
        stale_signoffs=tuple(sorted(stale, key=lambda issue: issue.path)),
        invalid_signoffs=tuple(sorted(invalid, key=lambda issue: issue.path)),
        duplicate_roles=tuple(
            role for role in required_roles if role in duplicate_role_set
        ),
        ignored_metadata_files=tuple(path.name for path in metadata_paths),
    )
