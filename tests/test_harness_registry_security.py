from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from harness.domains.project_state import validate_registry
from harness.engine.loader import load_contract, load_json


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_contract(ROOT / "harness/contracts/project_acceptance_v1.json")
ARTIFACT_REGISTRY = load_json(ROOT / "harness/registry/artifacts_v1.json")
CLAIM_REGISTRY = load_json(ROOT / "harness/registry/claims_v1.json")


def validate(
    *,
    contract=CONTRACT,
    artifacts=ARTIFACT_REGISTRY,
    claims=CLAIM_REGISTRY,
) -> tuple[str, ...]:
    return validate_registry(ROOT, contract, artifacts, claims)


def test_current_artifact_and_claim_registries_are_secure() -> None:
    assert validate() == ()


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("artifact_id", 7),
        ("path", None),
        ("role", ""),
        ("format", []),
        ("mutability", False),
        ("evidence_class", 1),
        ("freshness_rule", {}),
        ("allowed_uses", "governance_evaluation"),
        ("forbidden_uses", ["benchmark_result", 1]),
        ("include_in_evidence_digest", "true"),
        ("required_for_profiles", "governance"),
    ],
)
def test_artifact_core_fields_have_strict_types(field: str, invalid_value: object) -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    registry["artifacts"][0][field] = invalid_value

    errors = validate(artifacts=registry)

    assert any(f"artifact[0].{field}" in error for error in errors)


def test_artifact_required_fields_cannot_be_omitted() -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    del registry["artifacts"][0]["role"]

    assert any("artifact[0] missing fields" in error for error in validate(artifacts=registry))


def test_artifact_ids_and_paths_are_unique() -> None:
    duplicate_id = deepcopy(ARTIFACT_REGISTRY)
    duplicate_id["artifacts"][1]["artifact_id"] = duplicate_id["artifacts"][0][
        "artifact_id"
    ]
    duplicate_path = deepcopy(ARTIFACT_REGISTRY)
    duplicate_path["artifacts"][1]["path"] = duplicate_path["artifacts"][0]["path"]

    assert any("duplicate artifact_id" in error for error in validate(artifacts=duplicate_id))
    assert any("duplicate artifact path" in error for error in validate(artifacts=duplicate_path))


def test_artifact_paths_remain_unique_across_scopes() -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    registry["artifacts"][1]["path"] = registry["artifacts"][0]["path"]
    registry["artifacts"][1]["verification_scope"] = "external_pointer"
    registry["artifacts"][1]["include_in_evidence_digest"] = False

    assert any("duplicate artifact path" in error for error in validate(artifacts=registry))


def test_artifact_scope_is_allowlisted() -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    registry["artifacts"][0]["verification_scope"] = "remote_url"

    assert any("verification_scope" in error for error in validate(artifacts=registry))


@pytest.mark.parametrize("malicious_path", ["/tmp/outside.json", "../outside.json"])
@pytest.mark.parametrize("scope", ["tracked", "generated"])
def test_tracked_and_generated_paths_cannot_escape_root(
    malicious_path: str, scope: str
) -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    artifact = registry["artifacts"][0]
    artifact["path"] = malicious_path
    artifact["verification_scope"] = scope
    artifact["include_in_evidence_digest"] = False

    assert any("must be a relative path within repository root" in error for error in validate(artifacts=registry))


@pytest.mark.parametrize("scope", ["external_pointer", "generated"])
def test_only_tracked_artifacts_can_enter_evidence_digest(scope: str) -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    artifact = registry["artifacts"][0]
    artifact["verification_scope"] = scope
    artifact["include_in_evidence_digest"] = True

    assert any("only tracked artifacts may enter the evidence digest" in error for error in validate(artifacts=registry))


def test_generated_acceptance_report_cannot_be_relabeled_as_digest_evidence() -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    artifact = next(
        row for row in registry["artifacts"] if row["artifact_id"] == "acceptance_report_json"
    )
    artifact["verification_scope"] = "tracked"
    artifact["include_in_evidence_digest"] = True

    assert any(
        "generated acceptance artifact" in error
        for error in validate(artifacts=registry)
    )


def test_human_signoff_decision_cannot_be_registered_as_digest_evidence() -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    artifact = deepcopy(registry["artifacts"][0])
    artifact.update(
        artifact_id="human_approval",
        path="harness/signoffs/approval.json",
        verification_scope="tracked",
        include_in_evidence_digest=True,
        required_for_profiles=[],
    )
    registry["artifacts"].append(artifact)

    assert any(
        "signoff decisions cannot be registry evidence" in error
        for error in validate(artifacts=registry)
    )


def test_required_tracked_artifact_must_exist() -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    registry["artifacts"][0]["path"] = "harness/does-not-exist.json"

    assert any("required tracked path does not exist" in error for error in validate(artifacts=registry))


def test_required_profile_ids_must_be_declared_by_contract() -> None:
    registry = deepcopy(ARTIFACT_REGISTRY)
    registry["artifacts"][0]["required_for_profiles"] = ["future_profile"]

    assert any("unknown required profile" in error for error in validate(artifacts=registry))


def test_every_gate_input_resolves_to_an_artifact() -> None:
    contract = deepcopy(CONTRACT)
    contract["gates"][0]["inputs"].append("unregistered_artifact")

    assert any("unresolved artifact input" in error for error in validate(contract=contract))


@pytest.mark.parametrize(
    ("claim_id", "effect", "expected"),
    [
        ("unregistered_claim", "prohibit", "unknown claim_id"),
        ("generated_candidate", "waive", "invalid effect"),
    ],
)
def test_gate_claim_effects_are_allowlisted_and_resolve(
    claim_id: str, effect: str, expected: str
) -> None:
    contract = deepcopy(CONTRACT)
    contract["gates"][4]["claim_effects"] = [
        {"claim_id": claim_id, "effect": effect}
    ]

    assert any(expected in error for error in validate(contract=contract))


def test_claim_ids_are_unique() -> None:
    registry = deepcopy(CLAIM_REGISTRY)
    registry["claims"][1]["claim_id"] = registry["claims"][0]["claim_id"]

    assert any("duplicate claim_id" in error for error in validate(claims=registry))


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("claim_id", None),
        ("label", ""),
        ("required_evidence_classes", "parsed_candidate_output"),
        ("forbidden_evidence_classes", ["planning", False]),
        ("allowed_wording", 1),
        ("forbidden_wording", [""]),
        ("wet_lab_required", "false"),
    ],
)
def test_claim_core_fields_have_strict_types(field: str, invalid_value: object) -> None:
    registry = deepcopy(CLAIM_REGISTRY)
    registry["claims"][0][field] = invalid_value

    assert any(f"claim[0].{field}" in error for error in validate(claims=registry))


def test_claim_required_fields_cannot_be_omitted() -> None:
    registry = deepcopy(CLAIM_REGISTRY)
    del registry["claims"][0]["label"]

    assert any("claim[0] missing fields" in error for error in validate(claims=registry))


def test_claim_surface_digest_and_row_count_are_verified() -> None:
    registry = deepcopy(CLAIM_REGISTRY)
    registry["claim_surface_sha256"] = "0" * 64
    registry["claim_surface_row_count"] = 1

    errors = validate(claims=registry)

    assert any("claim surface SHA-256 mismatch" in error for error in errors)
    assert any("claim surface row-count mismatch" in error for error in errors)


def test_claim_status_taxonomy_is_engine_owned_and_exact() -> None:
    registry = deepcopy(CLAIM_REGISTRY)
    registry["status_taxonomy"]["supported as benchmark result"] = "non_promotional"

    assert any(
        "status_taxonomy must exactly match" in error
        for error in validate(claims=registry)
    )


def test_claim_status_taxonomy_polarities_are_not_relabelable() -> None:
    registry = deepcopy(CLAIM_REGISTRY)
    registry["status_taxonomy"]["supported"] = "non_promotional"

    assert any(
        "status_taxonomy must exactly match" in error
        for error in validate(claims=registry)
    )


def test_claim_semantic_status_binding_is_engine_owned() -> None:
    registry = deepcopy(CLAIM_REGISTRY)
    registry["claim_semantic_binding_sha256"] = "0" * 64

    assert any(
        "claim_semantic_binding_sha256 must match" in error
        for error in validate(claims=registry)
    )
