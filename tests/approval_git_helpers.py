from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


GIT_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class ApprovalGitFixture:
    work: Path
    remote: Path
    peer: Path
    environment: Mapping[str, str]
    template: Path


def sanitized_git_environment(home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("GIT_"):
            environment.pop(key, None)
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / "xdg"),
        }
    )
    return environment


def install_sanitized_git_environment(
    monkeypatch: object, environment: Mapping[str, str]
) -> None:
    environ = getattr(monkeypatch, "delenv")
    setenv = getattr(monkeypatch, "setenv")
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            environ(key, raising=False)
    for key, value in environment.items():
        if key.startswith("GIT_") or key in {"HOME", "XDG_CONFIG_HOME"}:
            setenv(key, value)


def run_git(
    root: Path,
    *arguments: str,
    environment: Mapping[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "tag.gpgSign=false",
            *arguments,
        ],
        cwd=root,
        check=check,
        capture_output=True,
        timeout=GIT_TIMEOUT_SECONDS,
        env=dict(environment),
    )


def _configure_identity(root: Path, environment: Mapping[str, str]) -> None:
    run_git(
        root,
        "config",
        "--local",
        "user.name",
        "Approval Test Reviewer",
        environment=environment,
    )
    run_git(
        root,
        "config",
        "--local",
        "user.email",
        "approval-reviewer@example.test",
        environment=environment,
    )


def init_repo_with_bare_remote(tmp_path: Path) -> ApprovalGitFixture:
    auxiliary = tmp_path / "git-environment"
    environment = sanitized_git_environment(auxiliary / "home")
    template = auxiliary / "empty-template"
    template.mkdir(parents=True)
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    peer = tmp_path / "peer"

    run_git(
        tmp_path,
        "init",
        "--bare",
        "--initial-branch=main",
        f"--template={template}",
        "--",
        str(remote),
        environment=environment,
    )
    run_git(
        tmp_path,
        "init",
        "--initial-branch=main",
        f"--template={template}",
        "--",
        str(work),
        environment=environment,
    )
    _configure_identity(work, environment)
    (work / "README.md").write_text("base\n", encoding="utf-8")
    (work / "docs").mkdir()
    (work / "docs/delete-me.txt").write_text("delete me\n", encoding="utf-8")
    run_git(
        work,
        "add",
        "--",
        "README.md",
        "docs/delete-me.txt",
        environment=environment,
    )
    run_git(work, "commit", "-m", "initial", environment=environment)
    run_git(work, "remote", "add", "origin", str(remote), environment=environment)
    run_git(
        work,
        "push",
        "--set-upstream",
        "origin",
        "HEAD:refs/heads/main",
        environment=environment,
    )

    run_git(
        tmp_path,
        "clone",
        f"--template={template}",
        "--",
        str(remote),
        str(peer),
        environment=environment,
    )
    _configure_identity(peer, environment)
    return ApprovalGitFixture(
        work=work,
        remote=remote,
        peer=peer,
        environment=environment,
        template=template,
    )


def advance_remote(
    fixture: ApprovalGitFixture,
    *,
    filename: str = "remote-change.txt",
    content: str = "remote moved\n",
) -> str:
    path = fixture.peer / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    run_git(fixture.peer, "add", "--", filename, environment=fixture.environment)
    run_git(fixture.peer, "commit", "-m", "advance remote", environment=fixture.environment)
    run_git(
        fixture.peer,
        "push",
        "origin",
        "HEAD:refs/heads/main",
        environment=fixture.environment,
    )
    return git_stdout(fixture.peer, fixture.environment, "rev-parse", "HEAD")


def git_stdout(
    root: Path,
    environment: Mapping[str, str],
    *arguments: str,
) -> str:
    return run_git(root, *arguments, environment=environment).stdout.decode(
        "utf-8", errors="surrogateescape"
    ).strip()


def nul_paths(
    root: Path,
    environment: Mapping[str, str],
    *arguments: str,
) -> tuple[str, ...]:
    raw = run_git(root, *arguments, environment=environment).stdout.decode(
        "utf-8", errors="surrogateescape"
    )
    return tuple(value for value in raw.split("\0") if value)


def commit_all(
    fixture: ApprovalGitFixture,
    root: Path,
    message: str,
    paths: Sequence[str],
) -> str:
    run_git(root, "add", "-A", "--", *paths, environment=fixture.environment)
    run_git(root, "commit", "-m", message, environment=fixture.environment)
    return git_stdout(root, fixture.environment, "rev-parse", "HEAD")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
