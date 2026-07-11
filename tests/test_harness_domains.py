from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from harness.domains.project_state import evaluate_gate
from harness.engine.loader import load_contract, load_json
from harness.engine.models import GateVerdict, ProjectVerdict
from scripts import validate_benchmark_kb


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_contract(ROOT / "harness/contracts/project_acceptance_v1.json")
REGISTRY = load_json(ROOT / "harness/registry/artifacts_v1.json")
ARTIFACTS = {row["artifact_id"]: row for row in REGISTRY["artifacts"]}
GATES = {row["gate_id"]: row for row in CONTRACT["gates"]}


def evaluate(gate_id: str, root: Path = ROOT):
    return evaluate_gate(root, GATES[gate_id], ARTIFACTS)


def copy_artifacts(tmp_path: Path, artifact_ids: list[str]) -> None:
    for artifact_id in artifact_ids:
        rel = Path(ARTIFACTS[artifact_id]["path"])
        source = ROOT / rel
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def rewrite_csv(path: Path, update) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    update(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_v033_baseline_is_truthful_blocker_evidence_not_generation() -> None:
    result = evaluate("current.v033_baseline_truth")
    details = dict(result.details)

    assert result.verdict is GateVerdict.PASS
    assert details["execution_rows"] == 10
    assert details["candidate_evidence_rows"] == 10
    assert details["failed_rows"] == 10
    assert details["parsed_candidates"] == 0
    assert details["generated_runs"] == 0
    assert details["active_exit_86_rows"] == 0


def test_v033_baseline_fails_if_failed_row_is_promoted_to_generated(tmp_path: Path) -> None:
    ids = [
        "v033_execution_results",
        "v033_candidate_outputs",
        "v033_run_rows",
        "v033_merge_summary",
    ]
    copy_artifacts(tmp_path, ids)
    candidate_path = tmp_path / ARTIFACTS["v033_candidate_outputs"]["path"]
    run_path = tmp_path / ARTIFACTS["v033_run_rows"]["path"]
    rewrite_csv(candidate_path, lambda rows: rows[0].update(parse_status="parsed"))
    rewrite_csv(run_path, lambda rows: rows[0].update(status="generated"))

    result = evaluate("current.v033_baseline_truth", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "v033_baseline_mismatch"


def test_current_target_boundary_passes_because_unresolved_state_is_explicit() -> None:
    result = evaluate("current.target_control_boundary")
    details = dict(result.details)

    assert result.verdict is GateVerdict.PASS
    assert details["frozen_target_rows"] == 0
    assert details["missing_controls"] >= 1


def test_full_target_gate_fails_until_targets_and_controls_are_governed() -> None:
    result = evaluate("full.target_controls")

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "full_target_controls_incomplete"


def test_dflow_training_overlap_is_portable_and_scoring_prohibited() -> None:
    result = evaluate("current.dflow_leakage_recorded")
    details = dict(result.details)

    assert result.verdict is GateVerdict.PASS
    assert details["matched_value"] == "3eqs_B"
    assert details["split"] == "train"


def test_rf_unconditional_example_is_recorded_as_a_blocker() -> None:
    result = evaluate("current.rf_conditioning_blocker_recorded")

    assert result.verdict is GateVerdict.PASS
    assert "unconditional" in result.message


def test_rf_semantic_gate_is_portable_without_external_command(tmp_path: Path) -> None:
    copy_artifacts(
        tmp_path,
        ["pilot_job_manifest", "v033_candidate_outputs", "rf_unconditional_example"],
    )

    result = evaluate("current.rf_conditioning_blocker_recorded", tmp_path)

    assert result.verdict is GateVerdict.PASS


def test_pepmirror_d_job_without_mirror_evidence_is_recorded_as_a_blocker() -> None:
    result = evaluate("current.pepmirror_chirality_blocker_recorded")

    assert result.verdict is GateVerdict.PASS
    assert "mirror" in result.message.lower()


def test_current_scoring_guard_passes_while_full_scoring_gate_fails() -> None:
    assert evaluate("current.scoring_guard").verdict is GateVerdict.PASS
    assert evaluate("full.scoring_validation").verdict is GateVerdict.FAIL


def test_current_claim_boundary_passes_while_empirical_pillar_is_unsupported() -> None:
    assert evaluate("current.manuscript_claim_boundary").verdict is GateVerdict.PASS
    assert evaluate("full.benchmark_pillars").verdict is GateVerdict.FAIL


def test_computational_proxy_cannot_be_promoted_to_biological_validation(
    tmp_path: Path,
) -> None:
    copy_artifacts(
        tmp_path,
        ["claim_evidence_map", "claim_registry", "artifact_registry", "current_plan"],
    )
    path = tmp_path / ARTIFACTS["claim_evidence_map"]["path"]

    def promote(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["claim"] == "计算评分可替代实验验证")
        row["status"] = "supported"

    rewrite_csv(path, promote)
    result = evaluate("current.manuscript_claim_boundary", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "unsupported_claim_promoted"


@pytest.mark.parametrize(
    "promoted_claim",
    [
        "Benchmark completed",
        "best-performing method identified",
        "experimentally validated candidate",
    ],
)
def test_claim_registry_forbidden_wording_cannot_be_added_as_supported(
    tmp_path: Path, promoted_claim: str
) -> None:
    copy_artifacts(
        tmp_path,
        ["claim_evidence_map", "current_plan", "claim_registry", "artifact_registry"],
    )
    path = tmp_path / ARTIFACTS["claim_evidence_map"]["path"]

    def append_claim(rows: list[dict[str, str]]) -> None:
        rows.append(
            {
                "claim": promoted_claim,
                "evidence": "fabricated_evidence",
                "status": "supported",
                "allowed_wording": promoted_claim,
                "forbidden_wording": "",
                "next_check": "",
            }
        )

    rewrite_csv(path, append_claim)
    result = evaluate("current.manuscript_claim_boundary", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "unsupported_claim_promoted"


def test_unrecognized_claim_status_cannot_bypass_policy_after_surface_relock(
    tmp_path: Path,
) -> None:
    copy_artifacts(
        tmp_path,
        ["claim_evidence_map", "current_plan", "claim_registry", "artifact_registry"],
    )
    claim_map_path = tmp_path / ARTIFACTS["claim_evidence_map"]["path"]
    claim_registry_path = tmp_path / ARTIFACTS["claim_registry"]["path"]

    def forge_result_claim(rows: list[dict[str, str]]) -> None:
        rows[0].update(
            claim="completed evaluation",
            evidence="README.md",
            status="supported as benchmark result",
            allowed_wording="completed evaluation",
            forbidden_wording="",
        )

    rewrite_csv(claim_map_path, forge_result_claim)
    registry = json.loads(claim_registry_path.read_text(encoding="utf-8"))
    registry["claim_surface_sha256"] = hashlib.sha256(
        claim_map_path.read_bytes()
    ).hexdigest()
    claim_registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = evaluate("current.manuscript_claim_boundary", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "unsupported_claim_promoted"
    assert dict(result.details)["unrecognized_claim_statuses"] == (
        "supported as benchmark result",
    )


def test_known_boundary_status_cannot_carry_changed_promotion_semantics(
    tmp_path: Path,
) -> None:
    copy_artifacts(
        tmp_path,
        ["claim_evidence_map", "current_plan", "claim_registry", "artifact_registry"],
    )
    claim_map_path = tmp_path / ARTIFACTS["claim_evidence_map"]["path"]
    claim_registry_path = tmp_path / ARTIFACTS["claim_registry"]["path"]

    def forge_result_claim(rows: list[dict[str, str]]) -> None:
        rows[0].update(
            claim="completed evaluation",
            evidence="README.md",
            status="supported as boundary",
            allowed_wording="completed evaluation",
            forbidden_wording="",
        )

    rewrite_csv(claim_map_path, forge_result_claim)
    registry = json.loads(claim_registry_path.read_text(encoding="utf-8"))
    registry["claim_surface_sha256"] = hashlib.sha256(
        claim_map_path.read_bytes()
    ).hexdigest()
    claim_registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = evaluate("current.manuscript_claim_boundary", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "unsupported_claim_promoted"
    assert dict(result.details)["claim_semantic_binding_valid"] is False


def test_validator_no_write_mode_does_not_touch_tracked_report() -> None:
    report = ROOT / "ops/validation/wiki_validation_report.md"
    before = report.read_bytes()
    before_mtime = report.stat().st_mtime_ns

    completed = subprocess.run(
        [sys.executable, "scripts/validate_benchmark_kb.py", "--no-write-report"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "pass"
    assert report.read_bytes() == before
    assert report.stat().st_mtime_ns == before_mtime


def test_generated_acceptance_markdown_is_excluded_from_legacy_link_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    generated_paths = [
        tmp_path / "harness/PROJECT_ACCEPTANCE.md",
        tmp_path / "ops/acceptance/project_acceptance_report.md",
    ]
    for path in generated_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[generated broken link](missing-generated.md)\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "[governed broken link](missing-governed.md)\n", encoding="utf-8"
    )
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    checked = validate_benchmark_kb.check_markdown_links(errors)

    assert checked == 1
    assert errors == ["README.md: broken link -> missing-governed.md"]


def test_missing_required_external_pointer_is_a_project_blocker(tmp_path: Path) -> None:
    gate = {
        "gate_id": "test.external",
        "domain": "method_dataset_readiness",
        "severity": "Critical",
        "evaluator": "semantic_dflow_leakage",
        "inputs": ["external"],
        "failure_reason_code": "external_evidence_unavailable",
    }
    artifacts = {
        "external": {
            "path": "/missing/external/evidence.json",
            "verification_scope": "external_pointer",
        }
    }

    result = evaluate_gate(tmp_path, gate, artifacts)

    assert result.verdict is GateVerdict.FAIL
    assert result.failure_status is ProjectVerdict.BLOCKED
    assert result.reason_code == "external_evidence_unavailable"


def test_migration_gate_fails_when_a_legacy_policy_mapping_is_removed(
    tmp_path: Path,
) -> None:
    copy_artifacts(
        tmp_path, ["migration_parity", "agents_rules", "legacy_agents_snapshot"]
    )
    path = tmp_path / ARTIFACTS["migration_parity"]["path"]
    value = json.loads(path.read_text(encoding="utf-8"))
    value["active_policy_map"].pop("git_and_safety")
    path.write_text(json.dumps(value), encoding="utf-8")

    result = evaluate("governance.migration_parity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "migration_parity_missing"


def test_release_gate_can_validate_a_post_governance_v122_candidate(
    tmp_path: Path,
) -> None:
    gate = GATES["release.checkpoint_integrity"]
    copy_artifacts(tmp_path, list(gate["inputs"]))
    (tmp_path / "VERSION").write_text("1.2.22\n", encoding="utf-8")
    for relative in ("README.md", "index.md", "AGENTS.md"):
        path = tmp_path / relative
        path.write_text(
            path.read_text(encoding="utf-8").replace("1.2.21", "1.2.22"),
            encoding="utf-8",
        )
    release_notes = tmp_path / "RELEASE_NOTES.md"
    release_notes.write_text(
        release_notes.read_text(encoding="utf-8").replace(
            "## Unreleased Harness Engineering Workflow "
            "(`VERSION=1.2.21`) - 2026-07-10",
            "## v1.2.22 Harness Engineering Checkpoint",
        ),
        encoding="utf-8",
    )
    ops_log = tmp_path / "ops/log.md"
    ops_log.write_text(
        ops_log.read_text(encoding="utf-8").replace(
            "governance | harness engineering v1.0 unsigned checkpoint",
            "release | v1.2.22 harness engineering checkpoint",
        ),
        encoding="utf-8",
    )

    result = evaluate("release.checkpoint_integrity", tmp_path)

    assert result.verdict is GateVerdict.PASS
