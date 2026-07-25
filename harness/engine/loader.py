from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    pass


ENGINE_EVALUATOR_IDS = frozenset(
    {
        "artifact_registry_integrity",
        "benchmark_pillars",
        "contract_integrity",
        "kb_validator",
        "manuscript_claims",
        "migration_parity",
        "release_integrity",
        "scoring_guard",
        "semantic_dflow_leakage",
        "semantic_pepmirror_chirality",
        "semantic_rf_target_conditioning",
        "target_controls",
        "v033_baseline",
        "v034_bounded_connectivity",
        "v035_bounded_connectivity",
    }
)

ENGINE_PROFILE_IDS = frozenset(
    {"governance", "current_phase", "release_checkpoint", "full_project"}
)
ENGINE_SEVERITIES = frozenset({"Critical", "Major", "Advisory"})
ENGINE_DOMAINS = frozenset(
    {
        "repository_provenance",
        "method_dataset_readiness",
        "target_control_governance",
        "execution_provenance",
        "output_representation",
        "scoring_validation",
        "manuscript_claims",
        "release_operations",
    }
)
ENGINE_CLAIM_EFFECTS = frozenset({"prohibit", "require", "allow"})
ENGINE_GATE_IDS = frozenset(
    {
        "governance.contract_integrity",
        "governance.artifact_registry_integrity",
        "governance.migration_parity",
        "repository.kb_validator",
        "current.v033_baseline_truth",
        "current.v034_bounded_connectivity",
        "current.v035_bounded_connectivity",
        "current.target_control_boundary",
        "current.dflow_leakage_recorded",
        "current.rf_conditioning_blocker_recorded",
        "current.pepmirror_chirality_blocker_recorded",
        "current.scoring_guard",
        "current.manuscript_claim_boundary",
        "release.checkpoint_integrity",
        "full.method_readiness",
        "full.target_controls",
        "full.controlled_generation",
        "full.output_representation",
        "full.scoring_validation",
        "full.benchmark_pillars",
        "full.release_integrity",
    }
)
ENGINE_GATE_SPECS = {
    "governance.contract_integrity": ("repository_provenance", "Critical", "contract_integrity", "governance_owner", False),
    "governance.artifact_registry_integrity": ("repository_provenance", "Critical", "artifact_registry_integrity", "governance_owner", False),
    "governance.migration_parity": ("repository_provenance", "Critical", "migration_parity", "governance_owner", False),
    "repository.kb_validator": ("repository_provenance", "Critical", "kb_validator", "engineering_reviewer", False),
    "current.v033_baseline_truth": ("execution_provenance", "Critical", "v033_baseline", "engineering_reviewer", False),
    "current.v034_bounded_connectivity": ("execution_provenance", "Critical", "v034_bounded_connectivity", "engineering_reviewer", False),
    "current.v035_bounded_connectivity": ("execution_provenance", "Critical", "v035_bounded_connectivity", "engineering_reviewer", False),
    "current.target_control_boundary": ("target_control_governance", "Critical", "target_controls", "scientific_reviewer", False),
    "current.dflow_leakage_recorded": ("target_control_governance", "Critical", "semantic_dflow_leakage", "scientific_reviewer", False),
    "current.rf_conditioning_blocker_recorded": ("method_dataset_readiness", "Major", "semantic_rf_target_conditioning", "engineering_reviewer", False),
    "current.pepmirror_chirality_blocker_recorded": ("output_representation", "Major", "semantic_pepmirror_chirality", "scientific_reviewer", False),
    "current.scoring_guard": ("scoring_validation", "Critical", "scoring_guard", "scientific_reviewer", False),
    "current.manuscript_claim_boundary": ("manuscript_claims", "Critical", "manuscript_claims", "scientific_reviewer", False),
    "release.checkpoint_integrity": ("release_operations", "Critical", "release_integrity", "engineering_reviewer", True),
    "full.method_readiness": ("method_dataset_readiness", "Critical", "v033_baseline", "engineering_reviewer", False),
    "full.target_controls": ("target_control_governance", "Critical", "target_controls", "scientific_reviewer", False),
    "full.controlled_generation": ("execution_provenance", "Critical", "v033_baseline", "engineering_reviewer", False),
    "full.output_representation": ("output_representation", "Critical", "semantic_pepmirror_chirality", "scientific_reviewer", False),
    "full.scoring_validation": ("scoring_validation", "Critical", "scoring_guard", "scientific_reviewer", False),
    "full.benchmark_pillars": ("manuscript_claims", "Critical", "benchmark_pillars", "scientific_reviewer", False),
    "full.release_integrity": ("release_operations", "Critical", "release_integrity", "engineering_reviewer", True),
}
_GOVERNANCE_GATES = frozenset(
    {
        "governance.contract_integrity",
        "governance.artifact_registry_integrity",
        "governance.migration_parity",
        "repository.kb_validator",
    }
)
_CURRENT_GATES = _GOVERNANCE_GATES | frozenset(
    {
        "current.v033_baseline_truth",
        "current.v035_bounded_connectivity",
        "current.target_control_boundary",
        "current.dflow_leakage_recorded",
        "current.scoring_guard",
        "current.manuscript_claim_boundary",
    }
)
_RELEASE_GATES = _CURRENT_GATES | {"release.checkpoint_integrity"}
ENGINE_PROFILE_GATE_IDS = {
    "governance": _GOVERNANCE_GATES,
    "current_phase": _CURRENT_GATES,
    "release_checkpoint": frozenset(_RELEASE_GATES),
    "full_project": frozenset(_RELEASE_GATES | {gate for gate in ENGINE_GATE_IDS if gate.startswith("full.")}),
}
ENGINE_PROFILE_SIGNOFF_ROLES = {
    "governance": frozenset({"governance_owner"}),
    "current_phase": frozenset({"governance_owner"}),
    "release_checkpoint": frozenset(
        {"engineering_reviewer", "scientific_reviewer"}
    ),
    "full_project": frozenset(
        {"governance_owner", "engineering_reviewer", "scientific_reviewer"}
    ),
}

KNOWN_REVIEW_ROLES = frozenset(
    {"governance_owner", "engineering_reviewer", "scientific_reviewer"}
)


REQUIRED_GATE_FIELDS = {
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


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Cannot load JSON source {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON source must contain an object: {path}")
    return value


def load_contract(path: Path) -> dict[str, Any]:
    contract = load_json(path)
    validate_contract(contract)
    return contract


def validate_contract(contract: dict[str, Any]) -> None:
    required_top_level = {
        "contract_id",
        "contract_version",
        "evaluator_version",
        "severities",
        "allowed_evaluators",
        "profiles",
        "domains",
        "gates",
    }
    missing = required_top_level - set(contract)
    if missing:
        raise ContractError(f"contract missing fields: {sorted(missing)}")

    profiles = contract["profiles"]
    gates = contract["gates"]
    if not isinstance(profiles, list) or not isinstance(gates, list):
        raise ContractError("profiles and gates must be lists")
    if not all(isinstance(item, dict) for item in profiles + gates):
        raise ContractError("profiles and gates must contain objects")

    declared_evaluators = contract["allowed_evaluators"]
    if not isinstance(declared_evaluators, list) or not all(
        isinstance(item, str) and item for item in declared_evaluators
    ):
        raise ContractError("allowed_evaluators must be a list of evaluator IDs")
    declared_evaluator_set = set(declared_evaluators)
    if (
        len(declared_evaluators) != len(declared_evaluator_set)
        or declared_evaluator_set != ENGINE_EVALUATOR_IDS
    ):
        missing = sorted(ENGINE_EVALUATOR_IDS - declared_evaluator_set)
        unexpected = sorted(declared_evaluator_set - ENGINE_EVALUATOR_IDS)
        raise ContractError(
            "allowed_evaluators must exactly match the engine allowlist; "
            f"missing={missing}, unexpected={unexpected}"
        )

    declared_domains = contract["domains"]
    if (
        not isinstance(declared_domains, list)
        or not all(isinstance(item, str) and item for item in declared_domains)
        or len(declared_domains) != len(set(declared_domains))
        or set(declared_domains) != ENGINE_DOMAINS
    ):
        raise ContractError("domains must exactly match the engine domain taxonomy")
    domains = set(declared_domains)
    declared_severities = contract["severities"]
    if (
        not isinstance(declared_severities, list)
        or not all(isinstance(item, str) and item for item in declared_severities)
        or len(declared_severities) != len(set(declared_severities))
        or set(declared_severities) != ENGINE_SEVERITIES
    ):
        raise ContractError("severities must exactly match the engine severity taxonomy")
    severities = set(declared_severities)

    profile_ids = [str(item.get("profile_id", "")) for item in profiles]
    if not all(profile_ids) or len(profile_ids) != len(set(profile_ids)):
        raise ContractError("profile IDs must be present and unique")
    if set(profile_ids) != ENGINE_PROFILE_IDS:
        raise ContractError("profile IDs must exactly match the engine profile taxonomy")

    gate_ids = [str(item.get("gate_id", "")) for item in gates]
    if not all(gate_ids) or len(gate_ids) != len(set(gate_ids)):
        raise ContractError("gate IDs must be present and unique")
    if set(gate_ids) != ENGINE_GATE_IDS:
        raise ContractError("gate IDs must exactly match the engine gate taxonomy")
    known_gate_ids = set(gate_ids)
    known_profile_ids = set(profile_ids)

    for profile in profiles:
        profile_id = str(profile["profile_id"])
        required_profile_fields = {
            "profile_id",
            "description",
            "applicable",
            "required_gate_ids",
            "required_signoff_roles",
        }
        missing_profile_fields = required_profile_fields - set(profile)
        if missing_profile_fields:
            raise ContractError(
                f"profile {profile_id} missing fields: {sorted(missing_profile_fields)}"
            )
        if not isinstance(profile["description"], str) or not profile["description"]:
            raise ContractError(f"profile {profile_id} description must be non-empty")
        if not isinstance(profile["applicable"], bool):
            raise ContractError(f"profile {profile_id} applicable must be boolean")
        required_gate_ids = profile.get("required_gate_ids")
        required_signoff_roles = profile.get("required_signoff_roles")
        if not isinstance(required_gate_ids, list) or not all(
            isinstance(item, str) and item for item in required_gate_ids
        ):
            raise ContractError(
                f"profile {profile_id} required_gate_ids must be a list of gate IDs"
            )
        if len(required_gate_ids) != len(set(required_gate_ids)):
            raise ContractError(f"profile {profile_id} has duplicate required gates")
        if set(required_gate_ids) != ENGINE_PROFILE_GATE_IDS[profile_id]:
            raise ContractError(
                f"profile {profile_id} does not match the engine required gate taxonomy"
            )
        if not isinstance(required_signoff_roles, list) or not all(
            isinstance(item, str) and item for item in required_signoff_roles
        ):
            raise ContractError(
                f"profile {profile_id} required_signoff_roles must be a list of roles"
            )
        unknown_roles = set(required_signoff_roles) - KNOWN_REVIEW_ROLES
        if unknown_roles:
            raise ContractError(
                f"profile {profile_id} has unknown signoff roles: {sorted(unknown_roles)}"
            )
        if len(required_signoff_roles) != len(set(required_signoff_roles)):
            raise ContractError(f"profile {profile_id} has duplicate signoff roles")
        if set(required_signoff_roles) != ENGINE_PROFILE_SIGNOFF_ROLES[profile_id]:
            raise ContractError(
                f"profile {profile_id} does not match the engine signoff role taxonomy"
            )

    signoff_roles_by_profile = {
        str(profile["profile_id"]): set(profile["required_signoff_roles"])
        for profile in profiles
    }

    for gate in gates:
        gate_id = str(gate.get("gate_id", ""))
        gate_missing = REQUIRED_GATE_FIELDS - set(gate)
        if gate_missing:
            raise ContractError(f"gate {gate_id} missing fields: {sorted(gate_missing)}")
        if gate["domain"] not in domains:
            raise ContractError(f"gate {gate_id} has unknown domain {gate['domain']}")
        if gate["severity"] not in severities:
            raise ContractError(f"gate {gate_id} has unknown severity {gate['severity']}")
        if gate["evaluator"] not in ENGINE_EVALUATOR_IDS:
            raise ContractError(f"gate {gate_id} has unknown evaluator {gate['evaluator']}")
        if gate["owner_role"] not in KNOWN_REVIEW_ROLES:
            raise ContractError(
                f"gate {gate_id} has unknown owner role {gate['owner_role']}"
            )
        if not isinstance(gate["signoff_required"], bool):
            raise ContractError(f"gate {gate_id} signoff_required must be boolean")
        actual_spec = (
            gate["domain"],
            gate["severity"],
            gate["evaluator"],
            gate["owner_role"],
            gate["signoff_required"],
        )
        if actual_spec != ENGINE_GATE_SPECS[gate_id]:
            raise ContractError(
                f"gate {gate_id} does not match the engine gate specification"
            )
        if not isinstance(gate["inputs"], list) or not all(
            isinstance(item, str) and item for item in gate["inputs"]
        ):
            raise ContractError(f"gate {gate_id} inputs must be a list of artifact IDs")
        if len(gate["inputs"]) != len(set(gate["inputs"])):
            raise ContractError(f"gate {gate_id} has duplicate artifact inputs")
        if not isinstance(gate["claim_effects"], list) or not all(
            isinstance(item, dict)
            and isinstance(item.get("claim_id"), str)
            and bool(item["claim_id"])
            and item.get("effect") in ENGINE_CLAIM_EFFECTS
            for item in gate["claim_effects"]
        ):
            raise ContractError(f"gate {gate_id} has invalid claim_effects")
        if not isinstance(gate["requires"], list) or not all(
            isinstance(item, str) and item for item in gate["requires"]
        ):
            raise ContractError(f"gate {gate_id} requires must be a list of gate IDs")
        if not isinstance(gate["profiles"], list) or not all(
            isinstance(item, str) and item for item in gate["profiles"]
        ):
            raise ContractError(f"gate {gate_id} profiles must be a list of profile IDs")
        if len(gate["requires"]) != len(set(gate["requires"])):
            raise ContractError(f"gate {gate_id} has duplicate dependencies")
        if len(gate["profiles"]) != len(set(gate["profiles"])):
            raise ContractError(f"gate {gate_id} has duplicate profiles")
        unknown_requirements = set(gate["requires"]) - known_gate_ids
        if unknown_requirements:
            raise ContractError(
                f"gate {gate_id} has unknown dependencies: {sorted(unknown_requirements)}"
            )
        unknown_profiles = set(gate["profiles"]) - known_profile_ids
        if unknown_profiles:
            raise ContractError(
                f"gate {gate_id} has unknown profiles: {sorted(unknown_profiles)}"
            )
        if gate["signoff_required"] is True:
            missing_owner_profiles = [
                profile_id
                for profile_id in gate["profiles"]
                if gate["owner_role"] not in signoff_roles_by_profile[profile_id]
            ]
            if missing_owner_profiles:
                raise ContractError(
                    f"gate {gate_id} signoff owner is not required by profiles: "
                    f"{sorted(missing_owner_profiles)}"
                )

    for profile in profiles:
        required = set(profile.get("required_gate_ids", ()))
        unknown = required - known_gate_ids
        if unknown:
            raise ContractError(
                f"profile {profile['profile_id']} has unknown gates: {sorted(unknown)}"
            )

        declared_by_gates = {
            gate["gate_id"]
            for gate in gates
            if profile["profile_id"] in gate["profiles"]
        }
        if required != declared_by_gates:
            missing_from_profile = sorted(declared_by_gates - required)
            missing_from_gates = sorted(required - declared_by_gates)
            raise ContractError(
                f"profile membership mismatch for {profile['profile_id']}; "
                f"missing_from_profile={missing_from_profile}, "
                f"missing_from_gates={missing_from_gates}"
            )

    dependencies = {gate["gate_id"]: tuple(gate["requires"]) for gate in gates}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(gate_id: str) -> None:
        if gate_id in visiting:
            raise ContractError(f"dependency cycle detected at {gate_id}")
        if gate_id in visited:
            return
        visiting.add(gate_id)
        for requirement in dependencies[gate_id]:
            visit(requirement)
        visiting.remove(gate_id)
        visited.add(gate_id)

    for gate_id in gate_ids:
        visit(gate_id)

    closure_cache: dict[str, frozenset[str]] = {}

    def dependency_closure(gate_id: str) -> frozenset[str]:
        if gate_id not in closure_cache:
            closure: set[str] = set(dependencies[gate_id])
            for requirement in dependencies[gate_id]:
                closure.update(dependency_closure(requirement))
            closure_cache[gate_id] = frozenset(closure)
        return closure_cache[gate_id]

    for profile in profiles:
        required = set(profile["required_gate_ids"])
        missing_dependencies = {
            dependency
            for gate_id in required
            for dependency in dependency_closure(gate_id)
            if dependency not in required
        }
        if missing_dependencies:
            raise ContractError(
                f"profile {profile['profile_id']} violates dependency closure; "
                f"missing={sorted(missing_dependencies)}"
            )
