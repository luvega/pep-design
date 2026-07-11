from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, TypeVar

from harness.engine.path_policy import is_workspace_source_path

from .models import ApprovalError, SourceEntry


EXPECTED_REMOTE_URL = "git@github.com:luvega/pep-design.git"
EXPECTED_REMOTE_NAME = "origin"
EXPECTED_REMOTE_REF = "refs/heads/main"
_OID_PATTERN = re.compile(r"[0-9a-f]{40}")
_CARD_ID_PATTERN = re.compile(r"approval_[0-9a-f]{24}")
_SIGNOFF_PATH_PATTERN = re.compile(
    r"harness/signoffs/signoff_(governance|current_phase)_v[0-9]+\.json"
)
_ZERO_OID = "0" * 40
_SAFE_OPERATION_CONFIG = (
    "core.hooksPath=/dev/null",
    "core.fsmonitor=false",
    "core.attributesFile=/dev/null",
)
_SAFE_TRANSPORT_CONFIG = (
    "core.sshCommand=ssh -F /dev/null -o BatchMode=yes",
    "ssh.variant=ssh",
)
_T = TypeVar("_T")

# Approval cards use the same immutable four-field representation.
SourceManifestEntry = SourceEntry


class GitApprovalError(ApprovalError):
    """Raised when Git state does not match the reviewed approval binding."""


class GitExecutionError(GitApprovalError):
    """Raised only when a raw Git subprocess cannot execute successfully."""


@dataclass(frozen=True)
class RemoteSnapshot:
    name: str
    fetch_url: str
    push_url: str
    ref: str
    oid: str
    head_oid: str
    ahead_commits: tuple[str, ...]


def redact_git_error(value: str) -> str:
    """Remove credential-shaped values without exposing process environment."""

    redacted = re.sub(
        r"(?im)\b(GIT_SSH_COMMAND|GIT_ASKPASS|SSH_ASKPASS)\s*=.*$",
        r"\1=[REDACTED]",
        value,
    )
    redacted = re.sub(
        r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
        "Authorization: [REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)([a-z][a-z0-9+.-]*://)[^/@\s]+@",
        r"\1[REDACTED]@",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b(access_token|oauth(?:_token)?|token|password|passwd)\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s&;,]+)",
        r"\1=[REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b",
        "[REDACTED]",
        redacted,
    )
    return redacted.strip()


def _sanitized_git_environment(
    override: Mapping[str, str] | None,
) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "SSH_ASKPASS"
    }
    environment.update(
        {
            "PATH": os.defpath,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LITERAL_PATHSPECS": "1",
        }
    )
    if override is None:
        return environment
    if set(override) != {"GIT_INDEX_FILE"}:
        raise GitApprovalError(
            "Git environment overrides are forbidden except GIT_INDEX_FILE"
        )
    index = override["GIT_INDEX_FILE"]
    if not isinstance(index, str) or not index or not Path(index).is_absolute():
        raise GitApprovalError("GIT_INDEX_FILE must be a non-empty absolute path")
    environment["GIT_INDEX_FILE"] = index
    return environment


def _discover_git_value(
    root: Path,
    environment: Mapping[str, str],
    *args: str,
    timeout: int,
) -> str:
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "tag.gpgSign=false",
            *(
                option
                for config in _SAFE_OPERATION_CONFIG
                for option in ("-c", config)
            ),
            *args,
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        timeout=timeout,
        env=dict(environment),
    )
    if completed.returncode != 0:
        _raise_git_error(completed)
    value = completed.stdout.strip()
    if not value or "\n" in value or "\r" in value:
        raise GitApprovalError("Git discovery response is not canonical")
    return value


def _discover_git_object_directory(
    root: Path,
    environment: Mapping[str, str],
    *,
    timeout: int,
) -> Path:
    common_value = _discover_git_value(
        root,
        environment,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
        timeout=timeout,
    )
    common = Path(common_value)
    if not common_value or not common.is_absolute():
        raise GitApprovalError("Git common directory is not an absolute path")
    try:
        common = common.resolve(strict=True)
        objects = (common / "objects").resolve(strict=True)
        metadata = objects.lstat()
    except (OSError, RuntimeError) as exc:
        raise GitApprovalError("Git object directory cannot be resolved safely") from exc
    if not stat.S_ISDIR(metadata.st_mode) or objects.parent != common:
        raise GitApprovalError("Git object directory is not a direct regular directory")
    return objects


def _prepare_transport_git_dir(git_dir: Path, object_directory: Path) -> None:
    git_dir.chmod(0o700)
    (git_dir / "refs").mkdir(mode=0o700)
    (git_dir / "objects").symlink_to(object_directory, target_is_directory=True)
    (git_dir / "HEAD").write_text(
        "ref: refs/heads/transport\n",
        encoding="ascii",
    )
    (git_dir / "config").write_text(
        "[core]\n\trepositoryformatversion = 0\n\tbare = true\n",
        encoding="ascii",
    )


def _prepare_staging_git_dir(
    git_dir: Path,
    object_directory: Path,
    head_oid: str,
) -> None:
    _require_oid(head_oid, label="isolated staging HEAD")
    git_dir.chmod(0o700)
    (git_dir / "refs").mkdir(mode=0o700)
    (git_dir / "objects").symlink_to(object_directory, target_is_directory=True)
    (git_dir / "HEAD").write_text(f"{head_oid}\n", encoding="ascii")
    (git_dir / "config").write_text(
        "[core]\n\trepositoryformatversion = 0\n\tbare = false\n",
        encoding="ascii",
    )


def _invoke_git(
    root: Path,
    *args: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
    safe_transport: bool = False,
    safe_staging: bool = False,
) -> subprocess.CompletedProcess[str]:
    if safe_transport and safe_staging:
        raise GitApprovalError("Git command cannot use two isolated execution modes")
    environment = _sanitized_git_environment(env)
    if safe_staging and "GIT_INDEX_FILE" not in environment:
        raise GitApprovalError("isolated staging requires an explicit Git index")
    safe_config = _SAFE_OPERATION_CONFIG + (
        _SAFE_TRANSPORT_CONFIG if safe_transport else ()
    )
    safe_options = tuple(
        option
        for config in safe_config
        for option in ("-c", config)
    )
    argv = [
        "git",
        "--no-replace-objects",
        "-c",
        "commit.gpgSign=false",
        "-c",
        "tag.gpgSign=false",
        *safe_options,
        *args,
    ]

    def invoke(active_environment: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            timeout=timeout,
            env=dict(active_environment),
        )

    try:
        if not safe_transport and not safe_staging:
            return invoke(environment)
        object_directory = _discover_git_object_directory(
            root,
            environment,
            timeout=timeout,
        )
        prefix = (
            "approval-transport-git-"
            if safe_transport
            else "approval-staging-git-"
        )
        with tempfile.TemporaryDirectory(prefix=prefix) as temporary:
            git_dir = Path(temporary)
            isolated_environment = dict(environment)
            if safe_transport:
                _prepare_transport_git_dir(git_dir, object_directory)
            else:
                head_oid = _require_oid(
                    _discover_git_value(
                        root,
                        environment,
                        "rev-parse",
                        "HEAD",
                        timeout=timeout,
                    ),
                    label="HEAD",
                )
                _prepare_staging_git_dir(git_dir, object_directory, head_oid)
                isolated_environment["GIT_WORK_TREE"] = str(root)
            isolated_environment["GIT_DIR"] = str(git_dir)
            return invoke(isolated_environment)
    except subprocess.TimeoutExpired as exc:
        raise GitExecutionError("Git command timed out") from exc
    except OSError as exc:
        raise GitExecutionError("Git command could not be launched") from exc


def _raise_git_error(completed: subprocess.CompletedProcess[str]) -> None:
    detail = completed.stderr or completed.stdout or "Git command failed"
    raise GitExecutionError(redact_git_error(detail))


def run_git(
    root: Path,
    *args: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
    safe_transport: bool = False,
    safe_staging: bool = False,
) -> subprocess.CompletedProcess[str]:
    completed = _invoke_git(
        root,
        *args,
        timeout=timeout,
        env=env,
        safe_transport=safe_transport,
        safe_staging=safe_staging,
    )
    if completed.returncode != 0:
        _raise_git_error(completed)
    return completed


def run_git_optional(
    root: Path,
    *args: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
    safe_transport: bool = False,
    safe_staging: bool = False,
) -> subprocess.CompletedProcess[str] | None:
    completed = _invoke_git(
        root,
        *args,
        timeout=timeout,
        env=env,
        safe_transport=safe_transport,
        safe_staging=safe_staging,
    )
    if completed.returncode == 0:
        return completed
    if completed.returncode == 1:
        return None
    _raise_git_error(completed)


def run_git_bytes(
    root: Path,
    *args: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    environment = _sanitized_git_environment(env)
    try:
        completed = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-c",
                "commit.gpgSign=false",
                "-c",
                "tag.gpgSign=false",
                *(
                    option
                    for config in _SAFE_OPERATION_CONFIG
                    for option in ("-c", config)
                ),
                *args,
            ],
            cwd=root,
            check=False,
            capture_output=True,
            text=False,
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitExecutionError("Git command timed out") from exc
    except OSError as exc:
        raise GitExecutionError("Git command could not be launched") from exc
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or b"Git command failed"
        raise GitExecutionError(
            redact_git_error(detail.decode("utf-8", errors="surrogateescape"))
        )
    return completed


def _run_git_status(
    root: Path,
    *args: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
    safe_transport: bool = False,
    safe_staging: bool = False,
) -> subprocess.CompletedProcess[str]:
    return _invoke_git(
        root,
        *args,
        timeout=timeout,
        env=env,
        safe_transport=safe_transport,
        safe_staging=safe_staging,
    )


def _split_nul(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split("\0") if item)


def _require_oid(value: str, *, label: str) -> str:
    oid = value.strip()
    if _OID_PATTERN.fullmatch(oid) is None:
        raise GitApprovalError(f"{label} is not a canonical Git object ID")
    return oid


def _require_card_id(value: str) -> None:
    if _CARD_ID_PATTERN.fullmatch(value) is None:
        raise GitApprovalError("approval card ID is not canonical")


def _actual_index_environment(root: Path) -> dict[str, str]:
    value = run_git(
        root,
        "rev-parse",
        "--path-format=absolute",
        "--git-path",
        "index",
    ).stdout.strip()
    index = Path(value)
    if not value or not index.is_absolute():
        raise GitApprovalError("Git index path is not absolute")
    try:
        parent = index.parent.resolve(strict=True)
        index = parent / index.name
        if index.exists() and not stat.S_ISREG(index.lstat().st_mode):
            raise GitApprovalError("Git index is not a regular file")
    except OSError as exc:
        raise GitApprovalError("Git index path cannot be resolved safely") from exc
    return {"GIT_INDEX_FILE": str(index)}


def _require_clean_index(root: Path) -> None:
    completed = _run_git_status(
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--cached",
        "--quiet",
    )
    if completed.returncode == 0:
        return
    if completed.returncode == 1:
        raise GitApprovalError("Git index contains staged or cached changes")
    _raise_git_error(completed)


def require_main_with_clean_index(root: Path) -> None:
    branch = run_git(root, "symbolic-ref", "--short", "HEAD").stdout.strip()
    if branch != "main":
        raise GitApprovalError(f"approval requires branch main, found {branch!r}")
    _require_clean_index(root)


def _run_raw_git_config_optional(
    root: Path,
    *args: str,
) -> subprocess.CompletedProcess[str] | None:
    if not args or args[0] not in {"--get", "--get-all", "--get-regexp"}:
        raise GitApprovalError("raw Git config inspection arguments are not allowed")
    environment = _sanitized_git_environment(None)
    try:
        completed = subprocess.run(
            ["git", "config", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            timeout=30,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitExecutionError("Git config inspection timed out") from exc
    except OSError as exc:
        raise GitExecutionError("Git config inspection could not be launched") from exc
    if completed.returncode == 0:
        return completed
    if completed.returncode == 1:
        return None
    _raise_git_error(completed)


def _configured_value(root: Path, *args: str) -> str | None:
    completed = _run_raw_git_config_optional(root, *args)
    return None if completed is None else completed.stdout.strip()


def _configured_values(root: Path, key: str) -> tuple[str, ...]:
    completed = _run_raw_git_config_optional(root, "--get-all", key)
    if completed is None:
        return ()
    return tuple(completed.stdout.splitlines())


def reject_active_git_customization(root: Path) -> None:
    forbidden = (
        ("core.hooksPath", _configured_value(root, "--get", "core.hooksPath")),
        ("core.sshCommand", _configured_value(root, "--get", "core.sshCommand")),
        ("core.fsmonitor", _configured_value(root, "--get", "core.fsmonitor")),
        (
            "core.attributesFile",
            _configured_value(root, "--get", "core.attributesFile"),
        ),
        ("diff.external", _configured_value(root, "--get", "diff.external")),
        (
            "diff.*.command/textconv",
            _configured_value(
                root,
                "--get-regexp",
                r"^diff\..*\.(command|textconv)$",
            ),
        ),
        (
            "url.*.insteadOf/pushInsteadOf",
            _configured_value(
                root,
                "--get-regexp",
                r"^url\..*\.(insteadof|pushinsteadof)$",
            ),
        ),
        (
            "filter.*.clean/smudge/process",
            _configured_value(
                root,
                "--get-regexp",
                r"^filter\..*\.(clean|smudge|process)$",
            ),
        ),
    )
    for label, value in forbidden:
        if value is not None:
            raise GitApprovalError(f"active Git config {label} is not allowed")

    common_value = _discover_git_value(
        root,
        _sanitized_git_environment(None),
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
        timeout=30,
    )
    hooks_root = Path(common_value).resolve() / "hooks"
    if not hooks_root.is_dir():
        return
    for hook in sorted(hooks_root.iterdir(), key=lambda value: value.name):
        if hook.name.endswith(".sample"):
            continue
        try:
            metadata = hook.lstat()
        except FileNotFoundError:
            continue
        executable = bool(metadata.st_mode & 0o111)
        if executable and (stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode)):
            raise GitApprovalError(f"active Git hook {hook.name} is not allowed")


def _reject_executable_clean_filters(root: Path) -> None:
    configured = _configured_value(
        root,
        "--get-regexp",
        r"^filter\..*\.(clean|smudge|process)$",
    )
    if configured is not None:
        raise GitApprovalError(
            "active Git clean/smudge/process filter configuration is not allowed"
        )


def _remote_tracking_ref(remote_name: str, ref: str) -> str:
    if remote_name != EXPECTED_REMOTE_NAME or ref != EXPECTED_REMOTE_REF:
        raise GitApprovalError("remote name/ref must be origin and refs/heads/main")
    return "refs/remotes/origin/main"


def _require_expected_remote_urls(
    root: Path,
    *,
    remote_name: str,
    expected_url: str,
) -> tuple[str, str]:
    fetch_urls = _configured_values(root, f"remote.{remote_name}.url")
    if len(fetch_urls) != 1:
        raise GitApprovalError(
            f"remote {remote_name} must have exactly one fetch URL"
        )
    push_urls = _configured_values(root, f"remote.{remote_name}.pushurl")
    if len(push_urls) > 1:
        raise GitApprovalError(
            f"remote {remote_name} must have zero or exactly one push URL"
        )
    fetch_url = fetch_urls[0]
    push_url = fetch_url if not push_urls else push_urls[0]
    if fetch_url != expected_url:
        raise GitApprovalError("remote fetch URL does not match the expected URL")
    if push_url != expected_url:
        raise GitApprovalError("remote push URL does not match the expected URL")
    return fetch_url, push_url


def list_ahead_commits(
    root: Path, *, remote_tracking_ref: str = "refs/remotes/origin/main"
) -> tuple[str, ...]:
    remote_oid = _require_oid(
        run_git(root, "rev-parse", remote_tracking_ref).stdout,
        label="remote tracking ref",
    )
    head_oid = current_head_oid(root)
    output = run_git(
        root,
        "rev-list",
        "--reverse",
        f"{remote_oid}..{head_oid}",
        safe_transport=True,
    ).stdout
    return tuple(line for line in output.splitlines() if line)


def _transport_remote_oid(root: Path, *, url: str, ref: str) -> str:
    completed = run_git(
        root,
        "fetch-pack",
        "--no-progress",
        "--upload-pack=git-upload-pack",
        url,
        ref,
        safe_transport=True,
    )
    pack_pattern = re.compile(rf"pack\t{_OID_PATTERN.pattern}")
    ref_pattern = re.compile(rf"({_OID_PATTERN.pattern}) {re.escape(ref)}")
    pack_seen = False
    remote_oid: str | None = None
    for line in completed.stdout.splitlines():
        if pack_pattern.fullmatch(line) is not None:
            if pack_seen or remote_oid is not None:
                raise GitApprovalError("remote ref response is not canonical")
            pack_seen = True
            continue
        ref_match = ref_pattern.fullmatch(line)
        if ref_match is None or remote_oid is not None:
            raise GitApprovalError("remote ref response is not canonical")
        remote_oid = ref_match.group(1)
    if remote_oid is None:
        raise GitApprovalError("remote ref response is not canonical")
    return remote_oid


def _update_remote_tracking_ref(root: Path, tracking_ref: str, oid: str) -> None:
    new_oid = _require_oid(oid, label="remote tracking OID")
    current = run_git_optional(
        root,
        "rev-parse",
        "--verify",
        "--quiet",
        tracking_ref,
    )
    old_oid = (
        _ZERO_OID
        if current is None
        else _require_oid(current.stdout, label="prior remote tracking OID")
    )
    updated = _run_git_status(
        root,
        "update-ref",
        tracking_ref,
        new_oid,
        old_oid,
    )
    if updated.returncode == 0:
        return
    observed = run_git_optional(
        root,
        "rev-parse",
        "--verify",
        "--quiet",
        tracking_ref,
    )
    if observed is not None and _require_oid(
        observed.stdout, label="observed remote tracking OID"
    ) == new_oid:
        return
    if updated.returncode == 1:
        raise GitApprovalError("remote tracking ref changed during fetch")
    _raise_git_error(updated)


def fetch_remote_snapshot(
    root: Path,
    *,
    remote_name: str = EXPECTED_REMOTE_NAME,
    expected_url: str = EXPECTED_REMOTE_URL,
    ref: str = EXPECTED_REMOTE_REF,
) -> RemoteSnapshot:
    tracking_ref = _remote_tracking_ref(remote_name, ref)
    fetch_url, push_url = _require_expected_remote_urls(
        root,
        remote_name=remote_name,
        expected_url=expected_url,
    )
    remote_oid = _transport_remote_oid(root, url=fetch_url, ref=ref)
    _update_remote_tracking_ref(root, tracking_ref, remote_oid)
    head_oid = _require_oid(run_git(root, "rev-parse", "HEAD").stdout, label="HEAD")
    ancestor = _run_git_status(
        root,
        "merge-base",
        "--is-ancestor",
        remote_oid,
        head_oid,
        safe_transport=True,
    )
    if ancestor.returncode == 1:
        raise GitApprovalError(
            "remote origin/main is not an ancestor of HEAD; local main is behind or diverged"
        )
    if ancestor.returncode != 0:
        _raise_git_error(ancestor)
    return RemoteSnapshot(
        name=remote_name,
        fetch_url=fetch_url,
        push_url=push_url,
        ref=ref,
        oid=remote_oid,
        head_oid=head_oid,
        ahead_commits=list_ahead_commits(root, remote_tracking_ref=tracking_ref),
    )


def _mode_for_regular_file(path: Path) -> str:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise GitApprovalError(f"manifest path is not a regular file: {path}")
    return "100755" if metadata.st_mode & 0o111 else "100644"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_blob(
    root: Path,
    blob_oid: str,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    blob = run_git_bytes(root, "cat-file", "blob", blob_oid, env=env).stdout
    return hashlib.sha256(blob).hexdigest()


def collect_source_manifest(root: Path) -> tuple[SourceManifestEntry, ...]:
    _reject_executable_clean_filters(root)
    index_environment = _actual_index_environment(root)
    changed = set(
        _split_nul(
            run_git(
                root,
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--name-only",
                "-z",
                "HEAD",
                env=index_environment,
                safe_staging=True,
            ).stdout
        )
    )
    untracked = set(
        _split_nul(
            run_git(
                root,
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                env=index_environment,
                safe_staging=True,
            ).stdout
        )
    )
    statuses: list[tuple[str, str]] = []
    for relative in sorted(changed | untracked):
        if not is_workspace_source_path(relative):
            continue
        path = root / relative
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            if relative not in changed:
                raise GitApprovalError(f"untracked manifest path disappeared: {relative}")
            statuses.append((relative, "deleted"))
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise GitApprovalError(f"manifest path is not a regular file: {path}")
        statuses.append(
            (relative, "untracked" if relative in untracked else "modified")
        )

    paths = tuple(relative for relative, _status in statuses)
    if not paths:
        return ()
    _reject_executable_clean_filters(root)
    with tempfile.TemporaryDirectory(prefix="approval-manifest-index-") as temporary:
        index = Path(temporary) / "index"
        environment = {"GIT_INDEX_FILE": str(index)}
        run_git(root, "read-tree", "HEAD", env=environment)
        run_git(
            root,
            "add",
            "-A",
            "--",
            *paths,
            env=environment,
            safe_staging=True,
        )
        if _cached_paths(root, env=environment) != paths:
            raise GitApprovalError(
                "canonical manifest index paths do not match workspace changes"
            )
        entries: list[SourceManifestEntry] = []
        for relative, status in statuses:
            staged = _staged_entry(root, relative, env=environment)
            if status == "deleted":
                if staged is not None:
                    raise GitApprovalError(
                        f"deleted manifest path remains in canonical index: {relative}"
                    )
                entries.append(
                    SourceManifestEntry(
                        path=relative,
                        status=status,
                        mode=None,
                        sha256=None,
                    )
                )
                continue
            if staged is None:
                raise GitApprovalError(
                    f"manifest path is absent from canonical index: {relative}"
                )
            mode, blob_oid = staged
            if mode not in {"100644", "100755"}:
                raise GitApprovalError(
                    f"canonical manifest mode is not a regular file: {relative}"
                )
            entries.append(
                SourceManifestEntry(
                    path=relative,
                    status=status,
                    mode=mode,
                    sha256=_sha256_blob(root, blob_oid, env=environment),
                )
            )
        return tuple(entries)


def _manifest_paths(
    manifest: tuple[SourceManifestEntry, ...],
) -> tuple[str, ...]:
    paths = tuple(entry.path for entry in manifest)
    if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
        raise GitApprovalError("source manifest paths must be unique and sorted")
    for entry in manifest:
        if not is_workspace_source_path(entry.path):
            raise GitApprovalError(f"path is outside governed workspace: {entry.path}")
        if entry.status not in {"modified", "untracked", "deleted"}:
            raise GitApprovalError(f"unsupported manifest status: {entry.status}")
        if entry.status == "deleted":
            if entry.mode is not None or entry.sha256 is not None:
                raise GitApprovalError("deleted manifest entry must use deletion markers")
        elif entry.mode not in {"100644", "100755"} or not re.fullmatch(
            r"[0-9a-f]{64}", entry.sha256 or ""
        ):
            raise GitApprovalError("manifest mode or SHA-256 is invalid")
    return paths


def _require_manifest_unchanged(
    root: Path, manifest: tuple[SourceManifestEntry, ...]
) -> tuple[str, ...]:
    paths = _manifest_paths(manifest)
    if collect_source_manifest(root) != manifest:
        raise GitApprovalError("source manifest changed or drifted after review")
    return paths


def _cached_paths(
    root: Path, *, env: Mapping[str, str] | None = None
) -> tuple[str, ...]:
    return tuple(
        sorted(
            _split_nul(
                run_git(
                    root,
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--cached",
                    "--name-only",
                    "-z",
                    env=env,
                ).stdout
            )
        )
    )


def _staged_entry(
    root: Path,
    relative: str,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[str, str] | None:
    records = _split_nul(
        run_git(
            root,
            "ls-files",
            "--stage",
            "-z",
            "--",
            relative,
            env=env,
        ).stdout
    )
    if not records:
        return None
    if len(records) != 1 or "\t" not in records[0]:
        raise GitApprovalError(f"staged index entry is ambiguous: {relative}")
    header, staged_path = records[0].split("\t", 1)
    fields = header.split()
    if len(fields) != 3 or fields[2] != "0" or staged_path != relative:
        raise GitApprovalError(f"staged index entry is not canonical: {relative}")
    mode, blob_oid, _stage = fields
    _require_oid(blob_oid, label=f"staged blob for {relative}")
    return mode, blob_oid


def _verify_staged_manifest(
    root: Path,
    manifest: tuple[SourceManifestEntry, ...],
    *,
    env: Mapping[str, str] | None = None,
) -> None:
    for entry in manifest:
        staged = _staged_entry(root, entry.path, env=env)
        if entry.status == "deleted":
            if staged is not None:
                raise GitApprovalError(
                    f"deleted manifest path remains in staged index: {entry.path}"
                )
            continue
        if staged is None:
            raise GitApprovalError(f"manifest path is missing from staged index: {entry.path}")
        mode, blob_oid = staged
        if mode != entry.mode:
            raise GitApprovalError(f"staged mode differs from manifest: {entry.path}")
        blob_sha256 = _sha256_blob(root, blob_oid, env=env)
        if blob_sha256 != entry.sha256:
            raise GitApprovalError(
                f"staged blob SHA-256 differs from manifest: {entry.path}"
            )


def _temporary_index_tree(
    root: Path,
    manifest: tuple[SourceManifestEntry, ...],
) -> tuple[str, str]:
    paths = _require_manifest_unchanged(root, manifest)
    with tempfile.TemporaryDirectory(prefix="approval-index-") as temporary:
        index = Path(temporary) / "index"
        environment = {"GIT_INDEX_FILE": str(index)}
        run_git(root, "read-tree", "HEAD", env=environment)
        if paths:
            _reject_executable_clean_filters(root)
            run_git(
                root,
                "add",
                "-A",
                "--",
                *paths,
                env=environment,
                safe_staging=True,
            )
        staged = _cached_paths(root, env=environment)
        if staged != paths:
            raise GitApprovalError("temporary index staged paths do not match manifest")
        _verify_staged_manifest(root, manifest, env=environment)
        tree_oid = _require_oid(
            run_git(root, "write-tree", env=environment).stdout,
            label="proposed tree",
        )
        insertions = 0
        deletions = 0
        binaries = 0
        if paths:
            numstat = run_git(
                root,
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--cached",
                "--numstat",
                "-z",
                "--no-renames",
                "HEAD",
                "--",
                *paths,
                env=environment,
            ).stdout
            rows = tuple(row for row in numstat.split("\0") if row)
            if len(rows) != len(paths):
                raise GitApprovalError(
                    "temporary index numstat rows do not match manifest paths"
                )
            for row in rows:
                fields = row.split("\t", 2)
                if len(fields) != 3:
                    raise GitApprovalError("temporary index numstat is malformed")
                added, removed, _path = fields
                if added == "-" or removed == "-":
                    binaries += 1
                    continue
                try:
                    insertions += int(added)
                    deletions += int(removed)
                except ValueError as exc:
                    raise GitApprovalError(
                        "temporary index numstat counts are malformed"
                    ) from exc
        summary = (
            f"files={len(paths)};insertions={insertions};"
            f"deletions={deletions};binaries={binaries}"
        )
        return tree_oid, summary


def build_proposed_tree(
    root: Path, manifest: tuple[SourceManifestEntry, ...]
) -> str:
    return _temporary_index_tree(root, manifest)[0]


def diff_stat(root: Path, manifest: tuple[SourceManifestEntry, ...]) -> str:
    return _temporary_index_tree(root, manifest)[1]


def check_worktree_diff(root: Path) -> None:
    """Run config-isolated `git diff --check` against the real worktree/index."""

    run_git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--check",
        env=_actual_index_environment(root),
        safe_staging=True,
    )


def stage_exact_manifest(
    root: Path, manifest: tuple[SourceManifestEntry, ...]
) -> None:
    paths = _require_manifest_unchanged(root, manifest)
    _require_clean_index(root)
    if paths:
        _reject_executable_clean_filters(root)
        run_git(
            root,
            "add",
            "-A",
            "--",
            *paths,
            env=_actual_index_environment(root),
            safe_staging=True,
        )
    if _cached_paths(root) != paths:
        raise GitApprovalError("staged paths do not exactly match source manifest")
    _verify_staged_manifest(root, manifest)


def _require_exact_cached_paths(root: Path, paths: tuple[str, ...]) -> None:
    expected = tuple(sorted(paths))
    if _cached_paths(root) != expected:
        raise GitApprovalError("cached paths do not match the reviewed commit set")


def current_head_oid(root: Path) -> str:
    return _require_oid(run_git(root, "rev-parse", "HEAD").stdout, label="HEAD")


def _commit_object(
    root: Path,
    *,
    tree_oid: str,
    parent_oid: str,
    subject: str,
    card_id: str,
) -> str:
    _require_oid(tree_oid, label="staged tree")
    _require_oid(parent_oid, label="expected parent")
    return _require_oid(
        run_git(
            root,
            "commit-tree",
            tree_oid,
            "-p",
            parent_oid,
            "-m",
            subject,
            "-m",
            f"Approval-Card: {card_id}",
        ).stdout,
        label="card commit",
    )


def _normalize_reconciled_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(sorted(paths))
    if len(normalized) != len(set(normalized)):
        raise GitApprovalError("reconciliation paths must be distinct")
    for relative in normalized:
        path = Path(relative)
        if (
            not relative
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != relative
        ):
            raise GitApprovalError("reconciliation path is not project-relative")
    return normalized


def _tree_entry(
    root: Path, commit_oid: str, relative: str
) -> tuple[str, str] | None:
    records = _split_nul(
        run_git(
            root,
            "ls-tree",
            "-z",
            commit_oid,
            "--",
            relative,
            safe_transport=True,
        ).stdout
    )
    if not records:
        return None
    if len(records) != 1 or "\t" not in records[0]:
        raise GitApprovalError(f"commit tree entry is ambiguous: {relative}")
    header, actual_path = records[0].split("\t", 1)
    fields = header.split()
    if len(fields) != 3 or fields[1] != "blob" or actual_path != relative:
        raise GitApprovalError(f"commit tree entry is not a blob: {relative}")
    mode, _kind, blob_oid = fields
    _require_oid(blob_oid, label=f"commit blob for {relative}")
    return mode, blob_oid


def _verify_commit_manifest(
    root: Path,
    commit_oid: str,
    manifest: tuple[SourceManifestEntry, ...],
) -> None:
    for entry in manifest:
        tree_entry = _tree_entry(root, commit_oid, entry.path)
        if entry.status == "deleted":
            if tree_entry is not None:
                raise GitApprovalError(
                    f"deleted manifest path remains in commit tree: {entry.path}"
                )
            continue
        if tree_entry is None:
            raise GitApprovalError(f"manifest path is absent from commit tree: {entry.path}")
        mode, blob_oid = tree_entry
        if mode != entry.mode:
            raise GitApprovalError(f"commit mode differs from manifest: {entry.path}")
        if _sha256_blob(root, blob_oid) != entry.sha256:
            raise GitApprovalError(
                f"commit blob SHA-256 differs from manifest: {entry.path}"
            )


def _verify_exact_card_commit(
    root: Path,
    new_commit_oid: str,
    expected_parent_oid: str,
    card_id: str,
    expected_paths: tuple[str, ...],
    *,
    expected_tree_oid: str | None = None,
    expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
) -> str:
    commit_oid = _require_oid(new_commit_oid, label="new card commit")
    parent_oid = _require_oid(expected_parent_oid, label="expected parent")
    _require_card_id(card_id)
    paths = _normalize_reconciled_paths(expected_paths)
    if expected_tree_oid is not None:
        _require_oid(expected_tree_oid, label="expected tree")
    if expected_manifest is not None:
        if tuple(sorted(entry.path for entry in expected_manifest)) != paths:
            raise GitApprovalError("reconciliation manifest paths do not match commit paths")

    ancestry = run_git(
        root,
        "rev-list",
        "--parents",
        "-n",
        "1",
        commit_oid,
        safe_transport=True,
    ).stdout.split()
    if ancestry != [commit_oid, parent_oid]:
        raise GitApprovalError("card commit is not the exact single child of expected parent")
    message = run_git(
        root,
        "show",
        "-s",
        "--format=%B",
        commit_oid,
        safe_transport=True,
    ).stdout
    approval_lines = [
        line for line in message.splitlines() if line.startswith("Approval-Card:")
    ]
    if approval_lines != [f"Approval-Card: {card_id}"]:
        raise GitApprovalError("card commit does not contain the exact approval card trailer")
    changed_paths = tuple(
        sorted(
            _split_nul(
                run_git(
                    root,
                    "diff-tree",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--no-commit-id",
                    "--name-only",
                    "--no-renames",
                    "-r",
                    "-z",
                    commit_oid,
                    safe_transport=True,
                ).stdout
            )
        )
    )
    if changed_paths != paths:
        raise GitApprovalError("card commit paths do not match approval card paths")
    tree_oid = commit_tree_oid(root, commit_oid)
    if expected_tree_oid is not None and tree_oid != expected_tree_oid:
        raise GitApprovalError("card commit tree does not match reviewed tree")
    if expected_manifest is not None:
        _verify_commit_manifest(root, commit_oid, expected_manifest)
    return commit_oid


def reconcile_card_commit(
    root: Path,
    expected_parent_oid: str,
    card_id: str,
    expected_paths: tuple[str, ...],
    *,
    expected_tree_oid: str | None = None,
    expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
) -> str | None:
    parent_oid = _require_oid(expected_parent_oid, label="expected parent")
    head_oid = current_head_oid(root)
    if head_oid == parent_oid:
        return None
    return _verify_exact_card_commit(
        root,
        head_oid,
        parent_oid,
        card_id,
        expected_paths,
        expected_tree_oid=expected_tree_oid,
        expected_manifest=expected_manifest,
    )


def _publish_card_commit(
    root: Path,
    *,
    new_commit_oid: str,
    expected_parent_oid: str,
    card_id: str,
    expected_paths: tuple[str, ...],
    expected_tree_oid: str,
    expected_manifest: tuple[SourceManifestEntry, ...] | None,
) -> str:
    _verify_exact_card_commit(
        root,
        new_commit_oid,
        expected_parent_oid,
        card_id,
        expected_paths,
        expected_tree_oid=expected_tree_oid,
        expected_manifest=expected_manifest,
    )
    update = _run_git_status(
        root,
        "update-ref",
        "refs/heads/main",
        new_commit_oid,
        expected_parent_oid,
    )
    if update.returncode == 0:
        published_oid = new_commit_oid
    else:
        try:
            reconciled = reconcile_card_commit(
                root,
                expected_parent_oid,
                card_id,
                expected_paths,
                expected_tree_oid=expected_tree_oid,
                expected_manifest=expected_manifest,
            )
        except GitApprovalError as exc:
            raise GitApprovalError(f"atomic ref parent race: {exc}") from exc
        if reconciled is None:
            _raise_git_error(update)
        published_oid = reconciled
    if current_head_oid(root) != published_oid:
        raise GitApprovalError("published card commit is not current HEAD")
    if commit_tree_oid(root, published_oid) != expected_tree_oid:
        raise GitApprovalError("published commit tree changed during ref update")
    if _require_oid(run_git(root, "write-tree").stdout, label="index tree") != expected_tree_oid:
        raise GitApprovalError("Git index is inconsistent with published commit tree")
    if _cached_paths(root):
        raise GitApprovalError("Git index remains staged after published card commit")
    return published_oid


def commit_source(
    root: Path,
    manifest: tuple[SourceManifestEntry, ...],
    card_id: str,
    expected_parent_oid: str | None = None,
) -> str:
    _require_card_id(card_id)
    paths = _manifest_paths(manifest)
    parent_oid = current_head_oid(root) if expected_parent_oid is None else _require_oid(
        expected_parent_oid, label="expected parent"
    )
    if current_head_oid(root) != parent_oid:
        raise GitApprovalError("HEAD moved from expected parent before source commit")
    if not paths:
        return parent_oid
    _require_exact_cached_paths(root, paths)
    _verify_staged_manifest(root, manifest)
    tree_oid = _require_oid(run_git(root, "write-tree").stdout, label="staged tree")
    commit_oid = _commit_object(
        root,
        tree_oid=tree_oid,
        parent_oid=parent_oid,
        subject="chore: checkpoint dialog approval source",
        card_id=card_id,
    )
    return _publish_card_commit(
        root,
        new_commit_oid=commit_oid,
        expected_parent_oid=parent_oid,
        card_id=card_id,
        expected_paths=paths,
        expected_tree_oid=tree_oid,
        expected_manifest=manifest,
    )


def _validate_signoff_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    if len(paths) != 2 or len(set(paths)) != 2:
        raise GitApprovalError("exactly two distinct signoff paths are required")
    normalized = tuple(sorted(paths))
    if any(_SIGNOFF_PATH_PATTERN.fullmatch(path) is None for path in normalized):
        raise GitApprovalError("signoff path is outside the approved signoff namespace")
    return normalized


def _signoff_manifest(
    root: Path, paths: tuple[str, ...]
) -> tuple[SourceManifestEntry, ...]:
    return tuple(
        SourceManifestEntry(
            path=relative,
            status="untracked",
            mode=_mode_for_regular_file(root / relative),
            sha256=_sha256_file(root / relative),
        )
        for relative in paths
    )


def _validate_signoff_manifest(
    manifest: tuple[SourceManifestEntry, ...], paths: tuple[str, ...]
) -> None:
    if tuple(entry.path for entry in manifest) != paths:
        raise GitApprovalError("signoff manifest paths do not match signoff commit paths")
    for entry in manifest:
        if entry.status == "deleted" or entry.mode not in {"100644", "100755"}:
            raise GitApprovalError("signoff manifest cannot contain deletion or invalid mode")
        if re.fullmatch(r"[0-9a-f]{64}", entry.sha256 or "") is None:
            raise GitApprovalError("signoff manifest SHA-256 is invalid")


def require_main_with_clean_or_exact_signoff_index(
    root: Path,
    expected_manifest: tuple[SourceManifestEntry, ...],
) -> bool:
    """Accept only a clean index or the exact staged recovery signoffs."""

    branch = run_git(root, "symbolic-ref", "--short", "HEAD").stdout.strip()
    if branch != "main":
        raise GitApprovalError(f"approval requires branch main, found {branch!r}")
    paths = _validate_signoff_paths(
        tuple(entry.path for entry in expected_manifest)
    )
    _validate_signoff_manifest(expected_manifest, paths)
    cached_paths = _cached_paths(root)
    if not cached_paths:
        _require_clean_index(root)
        return False
    if cached_paths != paths:
        raise GitApprovalError(
            "recoverable signoff index paths do not exactly match the reviewed manifest"
        )
    try:
        _verify_staged_manifest(root, expected_manifest)
    except GitApprovalError as exc:
        raise GitApprovalError(
            "recoverable signoff index does not exactly match the reviewed manifest"
        ) from exc
    return True


def commit_signoffs(
    root: Path,
    signoff_paths: tuple[str, ...],
    card_id: str,
    expected_parent_oid: str | None = None,
    expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
    *,
    allow_exact_prestaged: bool = False,
) -> str:
    _require_card_id(card_id)
    paths = _validate_signoff_paths(signoff_paths)
    parent_oid = current_head_oid(root) if expected_parent_oid is None else _require_oid(
        expected_parent_oid, label="expected parent"
    )
    if current_head_oid(root) != parent_oid:
        raise GitApprovalError("HEAD moved from expected parent before signoff commit")
    for relative in paths:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise GitApprovalError(f"signoff is not a regular file: {relative}")
    reviewed_manifest = (
        _signoff_manifest(root, paths)
        if expected_manifest is None
        else expected_manifest
    )
    _validate_signoff_manifest(reviewed_manifest, paths)
    if not isinstance(allow_exact_prestaged, bool):
        raise GitApprovalError("allow_exact_prestaged must be boolean")
    exact_prestaged = False
    if allow_exact_prestaged:
        exact_prestaged = require_main_with_clean_or_exact_signoff_index(
            root, reviewed_manifest
        )
    else:
        _require_clean_index(root)
    if not exact_prestaged:
        _reject_executable_clean_filters(root)
        run_git(
            root,
            "add",
            "--",
            *paths,
            env=_actual_index_environment(root),
            safe_staging=True,
        )
    _require_exact_cached_paths(root, paths)
    _verify_staged_manifest(root, reviewed_manifest)
    tree_oid = _require_oid(run_git(root, "write-tree").stdout, label="staged tree")
    commit_oid = _commit_object(
        root,
        tree_oid=tree_oid,
        parent_oid=parent_oid,
        subject="governance: approve acceptance profiles",
        card_id=card_id,
    )
    return _publish_card_commit(
        root,
        new_commit_oid=commit_oid,
        expected_parent_oid=parent_oid,
        card_id=card_id,
        expected_paths=paths,
        expected_tree_oid=tree_oid,
        expected_manifest=reviewed_manifest,
    )


def commit_tree_oid(root: Path, commit_oid: str) -> str:
    _require_oid(commit_oid, label="commit")
    return _require_oid(
        run_git(
            root,
            "show",
            "-s",
            "--format=%T",
            commit_oid,
            safe_transport=True,
        ).stdout,
        label="commit tree",
    )


def temporary_clean_worktree(
    root: Path,
    source_commit_oid: str,
    callback: Callable[[Path], _T],
) -> _T:
    source_oid = _require_oid(source_commit_oid, label="source commit")
    holder = Path(tempfile.mkdtemp(prefix="approval-worktree-", dir=root.parent))
    worktree = holder / "checkout"
    added = False
    try:
        run_git(
            root,
            "worktree",
            "add",
            "--detach",
            "--no-checkout",
            str(worktree),
            source_oid,
        )
        added = True
        index_environment = _actual_index_environment(worktree)
        run_git(
            worktree,
            "read-tree",
            "--reset",
            "-u",
            source_oid,
            env=index_environment,
            safe_staging=True,
        )
        if current_head_oid(worktree) != source_oid:
            raise GitApprovalError("isolated worktree HEAD differs from source commit")
        expected_tree = commit_tree_oid(root, source_oid)
        index_tree = _require_oid(
            run_git(
                worktree,
                "write-tree",
                env=index_environment,
                safe_staging=True,
            ).stdout,
            label="isolated worktree index tree",
        )
        if index_tree != expected_tree:
            raise GitApprovalError("isolated worktree index differs from source tree")
        worktree_diff = _run_git_status(
            worktree,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--quiet",
            source_oid,
            "--",
            env=index_environment,
            safe_staging=True,
        )
        if worktree_diff.returncode == 1:
            raise GitApprovalError("isolated worktree content differs from source tree")
        if worktree_diff.returncode != 0:
            _raise_git_error(worktree_diff)
        untracked = _split_nul(
            run_git(
                worktree,
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                env=index_environment,
                safe_staging=True,
            ).stdout
        )
        if untracked:
            raise GitApprovalError("isolated worktree contains untracked files")
        return callback(worktree)
    finally:
        if added:
            removal = _run_git_status(
                root, "worktree", "remove", "--force", str(worktree)
            )
            if removal.returncode != 0 and worktree.exists():
                _raise_git_error(removal)
        shutil.rmtree(holder, ignore_errors=True)


def latest_committed_signoffs(
    root: Path,
    *,
    contract_id: str,
    contract_version: str,
    contract_digest: str,
    profile_id: str,
    evaluation_id: str,
    evidence_digest: str,
    role: str,
) -> tuple[str, ...]:
    context = (
        contract_id,
        contract_version,
        contract_digest,
        profile_id,
        evaluation_id,
        evidence_digest,
        role,
    )
    if not all(isinstance(value, str) and value for value in context):
        raise GitApprovalError("signoff context must use non-empty strings")
    current_context = {
        "contract_version": contract_version,
        "contract_digest": contract_digest,
        "evaluation_id": evaluation_id,
        "evidence_digest": evidence_digest,
    }
    head_oid = current_head_oid(root)
    commits = tuple(
        line
        for line in run_git(
            root,
            "log",
            "--format=%H",
            head_oid,
            "--",
            "harness/signoffs",
            safe_transport=True,
        ).stdout.splitlines()
        if line
    )
    seen: set[str] = set()
    current: list[str] = []
    stale: list[str] = []
    for commit in commits:
        changed = _split_nul(
            run_git(
                root,
                "diff-tree",
                "--no-ext-diff",
                "--no-textconv",
                "--root",
                "--no-commit-id",
                "--name-only",
                "-r",
                "-z",
                commit,
                "--",
                "harness/signoffs",
                safe_transport=True,
            ).stdout
        )
        for path in changed:
            if path in seen or _SIGNOFF_PATH_PATTERN.fullmatch(path) is None:
                continue
            seen.add(path)
            present = _run_git_status(
                root,
                "cat-file",
                "-e",
                f"{head_oid}:{path}",
                safe_transport=True,
            )
            if present.returncode == 1:
                continue
            if present.returncode != 0:
                _raise_git_error(present)
            raw = run_git(
                root,
                "show",
                f"{head_oid}:{path}",
                safe_transport=True,
            ).stdout
            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError) as exc:
                raise GitApprovalError(f"committed signoff is not valid JSON: {path}") from exc
            if not isinstance(payload, dict):
                raise GitApprovalError(f"committed signoff must be a JSON object: {path}")
            if (
                payload.get("contract_id") == contract_id
                and payload.get("profile_id") == profile_id
                and payload.get("role") == role
            ):
                destination = (
                    current
                    if all(
                        payload.get(field) == expected
                        for field, expected in current_context.items()
                    )
                    else stale
                )
                destination.append(Path(path).name)
    return tuple(current + stale)


def _same_remote_binding(current: RemoteSnapshot, expected: RemoteSnapshot) -> bool:
    return (
        current.name == expected.name
        and current.fetch_url == expected.fetch_url
        and current.push_url == expected.push_url
        and current.ref == expected.ref
        and current.oid == expected.oid
    )


def push_exact(root: Path, final_commit_oid: str, expected: RemoteSnapshot) -> str:
    final_oid = _require_oid(final_commit_oid, label="final commit")
    head_oid = _require_oid(run_git(root, "rev-parse", "HEAD").stdout, label="HEAD")
    if head_oid != final_oid:
        raise GitApprovalError("final commit OID does not match current HEAD")
    current = fetch_remote_snapshot(
        root,
        remote_name=expected.name,
        expected_url=expected.fetch_url,
        ref=expected.ref,
    )
    if not _same_remote_binding(current, expected):
        raise GitApprovalError("remote URL, ref, or OID moved after approval review")
    ancestor = _run_git_status(
        root,
        "merge-base",
        "--is-ancestor",
        expected.oid,
        final_oid,
        safe_transport=True,
    )
    if ancestor.returncode == 1:
        raise GitApprovalError("push would not be a fast-forward from reviewed remote OID")
    if ancestor.returncode != 0:
        _raise_git_error(ancestor)

    run_git(
        root,
        "send-pack",
        "--receive-pack=git-receive-pack",
        f"--force-with-lease={expected.ref}:{expected.oid}",
        expected.push_url,
        f"{final_oid}:{expected.ref}",
        safe_transport=True,
    )
    confirmation_oid = _transport_remote_oid(
        root,
        url=expected.fetch_url,
        ref=expected.ref,
    )
    if confirmation_oid != final_oid:
        raise GitApprovalError("remote ref confirmation does not match final commit OID")
    _update_remote_tracking_ref(
        root,
        _remote_tracking_ref(expected.name, expected.ref),
        final_oid,
    )
    return final_oid


@dataclass(frozen=True)
class GitBackend:
    root: Path

    def require_main_with_clean_index(self) -> None:
        require_main_with_clean_index(self.root)

    def require_main_with_clean_or_exact_signoff_index(
        self, expected_manifest: tuple[SourceManifestEntry, ...]
    ) -> bool:
        return require_main_with_clean_or_exact_signoff_index(
            self.root, expected_manifest
        )

    def reject_active_git_customization(self) -> None:
        reject_active_git_customization(self.root)

    def fetch_remote_snapshot(
        self,
        *,
        remote_name: str = EXPECTED_REMOTE_NAME,
        expected_url: str = EXPECTED_REMOTE_URL,
        ref: str = EXPECTED_REMOTE_REF,
    ) -> RemoteSnapshot:
        return fetch_remote_snapshot(
            self.root,
            remote_name=remote_name,
            expected_url=expected_url,
            ref=ref,
        )

    def collect_source_manifest(self) -> tuple[SourceManifestEntry, ...]:
        return collect_source_manifest(self.root)

    def build_proposed_tree(
        self, manifest: tuple[SourceManifestEntry, ...]
    ) -> str:
        return build_proposed_tree(self.root, manifest)

    def diff_stat(self, manifest: tuple[SourceManifestEntry, ...]) -> str:
        return diff_stat(self.root, manifest)

    def check_worktree_diff(self) -> None:
        check_worktree_diff(self.root)

    def latest_committed_signoffs(
        self,
        *,
        contract_id: str,
        contract_version: str,
        contract_digest: str,
        profile_id: str,
        evaluation_id: str,
        evidence_digest: str,
        role: str,
    ) -> tuple[str, ...]:
        return latest_committed_signoffs(
            self.root,
            contract_id=contract_id,
            contract_version=contract_version,
            contract_digest=contract_digest,
            profile_id=profile_id,
            evaluation_id=evaluation_id,
            evidence_digest=evidence_digest,
            role=role,
        )

    def stage_exact_manifest(
        self, manifest: tuple[SourceManifestEntry, ...]
    ) -> None:
        stage_exact_manifest(self.root, manifest)

    def commit_source(
        self,
        manifest: tuple[SourceManifestEntry, ...],
        card_id: str,
        expected_parent_oid: str | None = None,
    ) -> str:
        return commit_source(
            self.root,
            manifest,
            card_id,
            expected_parent_oid=expected_parent_oid,
        )

    def commit_tree_oid(self, commit_oid: str) -> str:
        return commit_tree_oid(self.root, commit_oid)

    def current_head_oid(self) -> str:
        return current_head_oid(self.root)

    def reconcile_card_commit(
        self,
        expected_parent_oid: str,
        card_id: str,
        expected_paths: tuple[str, ...],
        *,
        expected_tree_oid: str | None = None,
        expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
    ) -> str | None:
        return reconcile_card_commit(
            self.root,
            expected_parent_oid,
            card_id,
            expected_paths,
            expected_tree_oid=expected_tree_oid,
            expected_manifest=expected_manifest,
        )

    def temporary_clean_worktree(
        self,
        source_commit_oid: str,
        callback: Callable[[Path], _T],
    ) -> _T:
        return temporary_clean_worktree(
            self.root,
            source_commit_oid,
            callback,
        )

    def commit_signoffs(
        self,
        signoff_paths: tuple[str, ...],
        card_id: str,
        expected_parent_oid: str | None = None,
        expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
        *,
        allow_exact_prestaged: bool = False,
    ) -> str:
        return commit_signoffs(
            self.root,
            signoff_paths,
            card_id,
            expected_parent_oid=expected_parent_oid,
            expected_manifest=expected_manifest,
            allow_exact_prestaged=allow_exact_prestaged,
        )

    def push_exact(self, final_commit_oid: str, expected: RemoteSnapshot) -> str:
        return push_exact(self.root, final_commit_oid, expected)
