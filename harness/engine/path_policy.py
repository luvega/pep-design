from __future__ import annotations

from pathlib import Path


_EXACT_STATE_FILES = frozenset(
    {
        "harness/PROJECT_ACCEPTANCE.md",
        "harness/signoffs/signoff_request_v1.json",
    }
)

_WORKSPACE_TOP_LEVEL_FILES = frozenset(
    {
        ".gitattributes",
        ".gitignore",
        "AGENTS.md",
        "README.md",
        "RELEASE_NOTES.md",
        "VERSION",
        "index.md",
        "pytest.ini",
    }
)

_WORKSPACE_TOP_LEVEL_DIRECTORIES = frozenset(
    {
        "benchmark",
        "docs",
        "harness",
        "kb",
        "manuscript",
        "ops",
        "scripts",
        "sources",
        "tests",
    }
)


def _safe_project_relative_path(value: str | Path) -> str | None:
    normalized = Path(value).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    path = Path(normalized)
    if normalized in {"", "."} or path.is_absolute() or ".." in path.parts:
        return None
    return normalized


def is_acceptance_state_path(value: str | Path) -> bool:
    """Return whether a safe project-relative path is mutable acceptance state."""

    normalized = _safe_project_relative_path(value)
    if normalized is None:
        return False
    if (
        normalized in _EXACT_STATE_FILES
        or normalized == "ops/acceptance"
        or normalized.startswith("ops/acceptance/")
    ):
        return True
    path = Path(normalized)
    return (
        len(path.parts) == 3
        and path.parts[:2] == ("harness", "signoffs")
        and path.suffix == ".json"
        and path.name not in {"signoff.schema.json", "signoff_request_v1.json"}
    )


def is_workspace_source_path(value: str | Path) -> bool:
    """Return whether a safe path belongs to the acceptance source surface."""

    normalized = _safe_project_relative_path(value)
    if normalized is None or is_acceptance_state_path(normalized):
        return False
    path = Path(normalized)
    return normalized in _WORKSPACE_TOP_LEVEL_FILES or (
        len(path.parts) > 1 and path.parts[0] in _WORKSPACE_TOP_LEVEL_DIRECTORIES
    )
