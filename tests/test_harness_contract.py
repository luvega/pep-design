from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from harness.engine.loader import ContractError, load_contract, load_json, validate_contract


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "harness/contracts/project_acceptance_v1.json"
ARTIFACTS_PATH = ROOT / "harness/registry/artifacts_v1.json"
CLAIMS_PATH = ROOT / "harness/registry/claims_v1.json"
PARITY_PATH = ROOT / "harness/registry/migration_parity_v1.json"
DFLOW_OVERLAP_PATH = ROOT / "harness/registry/dflow_3eqs_train_overlap_v1.json"
RF_SEMANTICS_PATH = ROOT / "harness/registry/rf_unconditional_example_v1.json"
PEPMIRROR_SEMANTICS_PATH = ROOT / "harness/registry/pepmirror_chirality_gap_v1.json"


EXPECTED_PROFILES = {
    "governance",
    "current_phase",
    "release_checkpoint",
    "full_project",
}
EXPECTED_DOMAINS = {
    "repository_provenance",
    "method_dataset_readiness",
    "target_control_governance",
    "execution_provenance",
    "output_representation",
    "scoring_validation",
    "manuscript_claims",
    "release_operations",
}
GATE_FIELDS = {
    "gate_id",
    "domain",
    "title",
    "severity",
    "evaluator",
    "inputs",
    "requires",
    "profiles",
    "pass_condition",
    "failure_reason_code",
    "claim_effects",
    "owner_role",
    "signoff_required",
}


def test_contract_defines_complete_acceptance_surface() -> None:
    contract = load_contract(CONTRACT_PATH)

    assert contract["contract_id"] == "pep_design_project_acceptance"
    assert contract["contract_version"] == "1.0.0"
    assert {row["profile_id"] for row in contract["profiles"]} == EXPECTED_PROFILES
    assert set(contract["domains"]) == EXPECTED_DOMAINS
    assert set(contract["severities"]) == {"Critical", "Major", "Advisory"}
    assert contract["evaluator_version"] == "1.0.0"


def test_contract_gates_are_unique_complete_allowlisted_and_acyclic() -> None:
    contract = load_contract(CONTRACT_PATH)
    gates = contract["gates"]
    gate_ids = [gate["gate_id"] for gate in gates]

    assert len(gate_ids) == len(set(gate_ids))
    assert all(GATE_FIELDS <= set(gate) for gate in gates)
    assert all(gate["domain"] in EXPECTED_DOMAINS for gate in gates)
    assert all(gate["severity"] in contract["severities"] for gate in gates)
    assert all(gate["evaluator"] in contract["allowed_evaluators"] for gate in gates)
    assert all(set(gate["requires"]) <= set(gate_ids) for gate in gates)
    assert all(set(gate["profiles"]) <= EXPECTED_PROFILES for gate in gates)

    validate_contract(contract)


def test_profile_signoff_roles_are_explicit() -> None:
    contract = load_contract(CONTRACT_PATH)
    profiles = {row["profile_id"]: row for row in contract["profiles"]}

    assert profiles["governance"]["required_signoff_roles"] == ["governance_owner"]
    assert profiles["current_phase"]["required_signoff_roles"] == ["governance_owner"]
    assert profiles["release_checkpoint"]["required_signoff_roles"] == [
        "engineering_reviewer",
        "scientific_reviewer",
    ]
    assert profiles["full_project"]["required_signoff_roles"] == [
        "governance_owner",
        "engineering_reviewer",
        "scientific_reviewer",
    ]


def test_contract_rejects_unknown_evaluator() -> None:
    contract = load_contract(CONTRACT_PATH)
    invalid = deepcopy(contract)
    invalid["gates"][0]["evaluator"] = "shell_anything"

    with pytest.raises(ContractError, match="unknown evaluator"):
        validate_contract(invalid)


def test_contract_rejects_v034_gate_rebound_to_a_generic_evaluator() -> None:
    contract = load_contract(CONTRACT_PATH)
    invalid = deepcopy(contract)
    gate = next(
        row
        for row in invalid["gates"]
        if row["gate_id"] == "current.v034_bounded_connectivity"
    )
    gate["evaluator"] = "v033_baseline"

    with pytest.raises(ContractError, match="engine gate specification"):
        validate_contract(invalid)


def test_contract_rejects_removing_v035_gate_from_current_profile() -> None:
    contract = load_contract(CONTRACT_PATH)
    invalid = deepcopy(contract)
    profile = next(
        row for row in invalid["profiles"] if row["profile_id"] == "current_phase"
    )
    profile["required_gate_ids"].remove("current.v035_bounded_connectivity")

    with pytest.raises(ContractError, match="required gate taxonomy"):
        validate_contract(invalid)


def test_contract_rejects_dependency_cycle() -> None:
    contract = load_contract(CONTRACT_PATH)
    invalid = deepcopy(contract)
    first, second = invalid["gates"][:2]
    first["requires"] = [second["gate_id"]]
    second["requires"] = [first["gate_id"]]

    with pytest.raises(ContractError, match="dependency cycle"):
        validate_contract(invalid)


def test_artifact_registry_distinguishes_tracked_external_and_generated() -> None:
    registry = load_json(ARTIFACTS_PATH)
    artifacts = registry["artifacts"]
    scopes = {row["verification_scope"] for row in artifacts}
    artifact_ids = {row["artifact_id"] for row in artifacts}

    assert {"tracked", "external_pointer", "generated"} <= scopes
    assert len(artifact_ids) == len(artifacts)
    assert "v033_candidate_outputs" in artifact_ids
    assert {
        "v034_job_manifest",
        "v034_execution_matrix",
        "v034_execution_results",
        "v034_method_output_manifest",
        "v034_candidate_outputs",
        "v034_candidate_qc",
        "v034_run_rows",
        "v034_runtime_provenance",
        "v034_failure_diagnostics",
        "v034_merge_summary",
        "v035_plan",
        "v035_pepglad_job_manifest",
        "v035_pepglad_execution_matrix",
        "v035_pepglad_connectivity_bundle",
    } <= artifact_ids
    assert "dflow_3eqs_train_overlap" in artifact_ids
    assert all(
        row["include_in_evidence_digest"] is False
        for row in artifacts
        if row["verification_scope"] == "generated"
    )


def test_claim_registry_preserves_separate_evidence_layers() -> None:
    registry = load_json(CLAIMS_PATH)
    claim_ids = {row["claim_id"] for row in registry["claims"]}

    assert {
        "generated_candidate",
        "scoring_evidence",
        "method_ranking",
        "frozen_target_set",
        "smoke_test_ready",
        "benchmark_ready",
        "wet_lab_validation",
        "biological_validation",
        "benchmark_pillar_research_gap",
        "benchmark_pillar_construction_pipeline",
        "benchmark_pillar_evaluation_framework",
        "benchmark_pillar_empirical_findings",
    } <= claim_ids


def test_v035_gate_is_current_while_v034_failure_remains_historical() -> None:
    contract = load_contract(CONTRACT_PATH)
    artifact_registry = load_json(ARTIFACTS_PATH)
    profiles = {row["profile_id"]: row for row in contract["profiles"]}
    gates = {row["gate_id"]: row for row in contract["gates"]}
    artifacts = {row["artifact_id"]: row for row in artifact_registry["artifacts"]}

    for profile_id in ("current_phase", "release_checkpoint", "full_project"):
        assert "current.v035_bounded_connectivity" in profiles[profile_id][
            "required_gate_ids"
        ]
        assert "current.v034_bounded_connectivity" not in profiles[profile_id][
            "required_gate_ids"
        ]
        assert "current.v033_baseline_truth" in profiles[profile_id][
            "required_gate_ids"
        ]
        assert "current.rf_conditioning_blocker_recorded" not in profiles[profile_id][
            "required_gate_ids"
        ]
        assert "current.pepmirror_chirality_blocker_recorded" not in profiles[
            profile_id
        ]["required_gate_ids"]

    assert "v0.35" in profiles["current_phase"]["description"]
    assert gates["current.rf_conditioning_blocker_recorded"]["profiles"] == []
    assert gates["current.pepmirror_chirality_blocker_recorded"]["profiles"] == []
    assert "Historical v0.33" in gates["current.rf_conditioning_blocker_recorded"][
        "title"
    ]
    assert "Historical v0.33" in gates[
        "current.pepmirror_chirality_blocker_recorded"
    ]["title"]
    assert gates["current.v034_bounded_connectivity"]["evaluator"] == (
        "v034_bounded_connectivity"
    )
    assert gates["current.v034_bounded_connectivity"]["profiles"] == []
    assert gates["current.v035_bounded_connectivity"]["evaluator"] == (
        "v035_bounded_connectivity"
    )
    assert "current.v034_bounded_connectivity" not in gates[
        "current.v035_bounded_connectivity"
    ]["requires"]
    assert "v034_runtime_provenance" in gates["current.v035_bounded_connectivity"][
        "inputs"
    ]
    assert "v034_failure_diagnostics" in gates[
        "current.v035_bounded_connectivity"
    ]["inputs"]
    assert "v035_pepglad_connectivity_bundle" in gates[
        "current.v035_bounded_connectivity"
    ]["inputs"]
    assert {
        "v034_execution_results",
        "v034_method_output_manifest",
        "v034_candidate_qc",
        "v034_runtime_provenance",
        "v034_failure_diagnostics",
    } <= set(gates["current.scoring_guard"]["inputs"])
    assert artifacts["current_plan"]["path"] == "ops/plans/updated_plan_v0.35.md"
    assert gates["current.scoring_guard"]["requires"] == [
        "current.v035_bounded_connectivity"
    ]
    assert gates["release.checkpoint_integrity"]["requires"] == []
    assert "generated_candidate_only_when_supported_candidate_yes" in artifacts[
        "v034_candidate_outputs"
    ]["allowed_uses"]
    assert "bounded_generated_candidate" not in artifacts["v034_candidate_outputs"][
        "allowed_uses"
    ]
    diagnostic = artifacts["v034_failure_diagnostics"]
    assert diagnostic["evidence_class"] == "failure_diagnostic_provenance"
    assert diagnostic["allowed_uses"] == [
        "bounded_failure_diagnosis",
        "claim_caveat",
    ]
    assert {
        "generated_candidate",
        "scoring_evidence",
        "method_ranking",
        "smoke_test_ready",
        "full_reproducibility",
    } <= set(diagnostic["forbidden_uses"])


def test_generated_candidate_policy_does_not_promote_scoring_or_ranking() -> None:
    registry = load_json(CLAIMS_PATH)
    policy = next(
        row for row in registry["claims"] if row["claim_id"] == "generated_candidate"
    )

    assert "parsed_candidate_output" in policy["required_evidence_classes"]
    assert "execution_provenance" in policy["required_evidence_classes"]
    assert "产生可解析候选" in policy["allowed_wording"]
    assert "产生可评分候选" in policy["forbidden_wording"]
    assert "方法性能可排名" in policy["forbidden_wording"]
    assert "best-performing" in policy["forbidden_wording"]


def test_migration_registry_covers_every_legacy_policy_category() -> None:
    registry = load_json(PARITY_PATH)

    assert set(registry["legacy_policy_keys"]) == {
        "purpose_and_current_plan",
        "source_boundaries",
        "skill_routing",
        "artifact_roles",
        "execution_gates",
        "language_and_claim_rules",
        "update_order",
        "validation_rules",
        "git_and_safety",
    }
    assert registry["legacy_artifact_role_patterns"]


def test_dflow_overlap_is_a_compact_tracked_derivation() -> None:
    evidence = load_json(DFLOW_OVERLAP_PATH)

    assert evidence == {
        "evidence_id": "dflow_3eqs_train_overlap_v1",
        "source_path": "data/dflow/pepmerge_lmdb/train_names.txt",
        "source_sha256": "ff168c194c225c8a117c1e1cfff365edc5ba2f812a0dcc9836e1d3238590da44",
        "match_rule": "exact_line_match",
        "matched_value": "3eqs_B",
        "split": "train",
        "conclusion": "known_training_overlap_fixture_only_scoring_prohibited",
    }


def test_rf_and_pepmirror_semantic_blockers_have_compact_derivations() -> None:
    rf = load_json(RF_SEMANTICS_PATH)
    pepmirror = load_json(PEPMIRROR_SEMANTICS_PATH)

    assert rf["source_sha256"] == "44dc40d2a793d9b69636ef02acae9688f08f6fed85dcd5d93adb1f756242913d"
    assert rf["observed_contig"] == "[12-18]"
    assert rf["target_conditioned"] is False
    assert rf["conclusion"] == "example_unconditional_not_target_conditioned_generation"
    assert pepmirror["source_sha256"] == "77c332e3739f58f607b0cc5e0d9b52ffc8c1fc41786ef3664a143049f54316f2"
    assert pepmirror["requested_chirality"] == "D"
    assert pepmirror["mirror_transform_observed"] is False
    assert pepmirror["conclusion"] == "d_peptide_claim_blocked_without_mirror_transform"


def test_json_sources_are_canonicalizable() -> None:
    for path in [
        CONTRACT_PATH,
        ARTIFACTS_PATH,
        CLAIMS_PATH,
        PARITY_PATH,
        DFLOW_OVERLAP_PATH,
        RF_SEMANTICS_PATH,
        PEPMIRROR_SEMANTICS_PATH,
    ]:
        value = load_json(path)
        assert json.loads(json.dumps(value, sort_keys=True)) == value


def test_current_profiles_route_connectivity_through_v035() -> None:
    from harness.engine import loader

    assert "v035_bounded_connectivity" in loader.ENGINE_EVALUATOR_IDS
    assert "current.v035_bounded_connectivity" in loader.ENGINE_GATE_IDS
    assert "current.v035_bounded_connectivity" in loader.ENGINE_PROFILE_GATE_IDS[
        "current_phase"
    ]
    assert "current.v034_bounded_connectivity" not in loader.ENGINE_PROFILE_GATE_IDS[
        "current_phase"
    ]
    assert "current.v035_bounded_connectivity" in loader.ENGINE_PROFILE_GATE_IDS[
        "release_checkpoint"
    ]
    assert "current.v035_bounded_connectivity" in loader.ENGINE_PROFILE_GATE_IDS[
        "full_project"
    ]
