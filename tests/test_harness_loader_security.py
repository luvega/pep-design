from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from harness.domains.project_state import EVALUATORS
from harness.engine.loader import (
    ENGINE_EVALUATOR_IDS,
    ContractError,
    load_contract,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "harness/contracts/project_acceptance_v1.json"


def _contract() -> dict:
    return deepcopy(load_contract(CONTRACT_PATH))


def test_engine_evaluator_allowlist_is_immutable() -> None:
    assert isinstance(ENGINE_EVALUATOR_IDS, frozenset)
    assert set(EVALUATORS) == ENGINE_EVALUATOR_IDS

    with pytest.raises(AttributeError):
        ENGINE_EVALUATOR_IDS.add("shell_anything")  # type: ignore[attr-defined]


def test_contract_cannot_extend_engine_evaluator_allowlist() -> None:
    contract = _contract()
    contract["allowed_evaluators"].append("shell_anything")
    contract["gates"][0]["evaluator"] = "shell_anything"

    with pytest.raises(ContractError, match="allowed_evaluators must exactly match"):
        validate_contract(contract)


def test_contract_cannot_reduce_engine_evaluator_allowlist() -> None:
    contract = _contract()
    contract["allowed_evaluators"].remove("benchmark_pillars")

    with pytest.raises(ContractError, match="allowed_evaluators must exactly match"):
        validate_contract(contract)


def test_contract_cannot_remove_full_project_gates_to_self_accept() -> None:
    contract = _contract()
    removed = {
        gate["gate_id"] for gate in contract["gates"] if gate["gate_id"].startswith("full.")
    }
    contract["gates"] = [
        gate for gate in contract["gates"] if gate["gate_id"] not in removed
    ]
    full_profile = next(
        row for row in contract["profiles"] if row["profile_id"] == "full_project"
    )
    full_profile["required_gate_ids"] = [
        gate_id for gate_id in full_profile["required_gate_ids"] if gate_id not in removed
    ]

    with pytest.raises(ContractError, match="gate IDs must exactly match"):
        validate_contract(contract)


def test_contract_cannot_downgrade_full_project_gates_to_advisory() -> None:
    contract = _contract()
    for gate in contract["gates"]:
        if gate["gate_id"].startswith("full."):
            gate["severity"] = "Advisory"

    with pytest.raises(ContractError, match="engine gate specification"):
        validate_contract(contract)


def test_contract_cannot_detach_full_gates_from_full_profile() -> None:
    contract = _contract()
    full_profile = next(
        row for row in contract["profiles"] if row["profile_id"] == "full_project"
    )
    full_gate_ids = {
        gate["gate_id"] for gate in contract["gates"] if gate["gate_id"].startswith("full.")
    }
    full_profile["required_gate_ids"] = [
        gate_id for gate_id in full_profile["required_gate_ids"] if gate_id not in full_gate_ids
    ]
    for gate in contract["gates"]:
        if gate["gate_id"] in full_gate_ids:
            gate["profiles"].remove("full_project")

    with pytest.raises(ContractError, match="required gate taxonomy"):
        validate_contract(contract)


def test_contract_cannot_remove_all_human_signoff_requirements() -> None:
    contract = _contract()
    for profile in contract["profiles"]:
        profile["required_signoff_roles"] = []
    for gate in contract["gates"]:
        gate["signoff_required"] = False

    with pytest.raises(
        ContractError, match="signoff role taxonomy|engine gate specification"
    ):
        validate_contract(contract)


def test_profile_must_include_transitive_gate_dependencies() -> None:
    contract = _contract()
    profile = next(
        row for row in contract["profiles"] if row["profile_id"] == "current_phase"
    )
    profile["required_gate_ids"].remove("current.scoring_guard")
    gate = next(
        row for row in contract["gates"] if row["gate_id"] == "current.scoring_guard"
    )
    gate["profiles"].remove("current_phase")

    with pytest.raises(ContractError, match="required gate taxonomy|dependency closure"):
        validate_contract(contract)


def test_gate_owner_role_must_be_known() -> None:
    contract = _contract()
    contract["gates"][0]["owner_role"] = "release_manager"

    with pytest.raises(ContractError, match="unknown owner role"):
        validate_contract(contract)


def test_profile_signoff_roles_must_be_known() -> None:
    contract = _contract()
    contract["profiles"][0]["required_signoff_roles"].append("release_manager")

    with pytest.raises(ContractError, match="unknown signoff roles"):
        validate_contract(contract)


@pytest.mark.parametrize(
    ("field", "invented", "message"),
    [
        ("severities", "Fatal", "severities"),
        ("domains", "invented_domain", "domains"),
    ],
)
def test_contract_cannot_self_authorize_taxonomy(
    field: str, invented: str, message: str
) -> None:
    contract = _contract()
    contract[field].append(invented)
    gate_field = "severity" if field == "severities" else "domain"
    contract["gates"][0][gate_field] = invented

    with pytest.raises(ContractError, match=message):
        validate_contract(contract)


def test_gate_signoff_policy_must_be_boolean() -> None:
    contract = _contract()
    contract["gates"][0]["signoff_required"] = "false"

    with pytest.raises(ContractError, match="signoff_required"):
        validate_contract(contract)


def test_signoff_required_gate_owner_must_be_required_by_each_profile() -> None:
    contract = _contract()
    profile = next(
        row for row in contract["profiles"] if row["profile_id"] == "release_checkpoint"
    )
    profile["required_signoff_roles"].remove("engineering_reviewer")

    with pytest.raises(ContractError, match="signoff role taxonomy|signoff owner"):
        validate_contract(contract)


@pytest.mark.parametrize("direction", ["profile_only", "gate_only"])
def test_gate_profiles_and_profile_required_lists_must_agree(direction: str) -> None:
    contract = _contract()
    profile = next(
        row for row in contract["profiles"] if row["profile_id"] == "governance"
    )
    gate = next(
        row
        for row in contract["gates"]
        if row["gate_id"] == "current.v033_baseline_truth"
    )

    if direction == "profile_only":
        profile["required_gate_ids"].append(gate["gate_id"])
    else:
        gate["profiles"].append(profile["profile_id"])

    with pytest.raises(
        ContractError, match="required gate taxonomy|profile membership mismatch"
    ):
        validate_contract(contract)
