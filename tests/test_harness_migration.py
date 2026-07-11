from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARITY = json.loads(
    (ROOT / "harness/registry/migration_parity_v1.json").read_text(encoding="utf-8")
)


def test_legacy_agents_snapshot_is_digest_bound_and_complete() -> None:
    snapshot = ROOT / "harness/policies/legacy_agents_v1.md"
    content = snapshot.read_bytes()
    text = content.decode("utf-8")
    section = text.split("## Current Artifact Roles", 1)[1].split(
        "## Execution Gates", 1
    )[0]
    roles = re.findall(r"^\| `([^`]+)` \|", section, flags=re.MULTILINE)

    assert hashlib.sha256(content).hexdigest() == PARITY["legacy_agents_sha256"]
    assert len(text.splitlines()) == PARITY["legacy_agents_line_count"]
    assert len(roles) == PARITY["legacy_artifact_role_count"] == 89
    patterns = [row["path_pattern"] for row in PARITY["legacy_artifact_role_patterns"]]
    assert all(any(fnmatch.fnmatch(path, pattern) for pattern in patterns) for path in roles)


def test_every_legacy_policy_key_has_an_active_digest_bound_mapping() -> None:
    agents = (ROOT / "AGENTS.md").read_bytes()

    assert set(PARITY["active_policy_map"]) == set(PARITY["legacy_policy_keys"])
    assert hashlib.sha256(agents).hexdigest() == PARITY["active_agents_sha256"]
    for tokens in PARITY["active_policy_map"].values():
        assert tokens
        assert all(token in agents.decode("utf-8") for token in tokens)


def test_active_agents_is_a_concise_progressive_disclosure_map() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert len(text.splitlines()) <= 120
    for token in PARITY["required_operating_tokens"]:
        assert token in text
    assert "harness/contracts/project_acceptance_v1.json" in text
    assert "harness/registry/artifacts_v1.json" in text
    assert "harness/policies/legacy_agents_v1.md" in text
    assert "scripts/run_project_acceptance.py check" in text


def test_version_remains_unsigned_checkpoint() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "1.2.21"
