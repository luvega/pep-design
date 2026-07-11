from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from harness.engine.models import HarnessStatus, ProjectVerdict
from harness.engine.report import evaluation_dict, evaluate_project, render_outputs


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "ops/acceptance/project_acceptance_report.json"
REPORT_MD = ROOT / "ops/acceptance/project_acceptance_report.md"
ACCEPTANCE_MD = ROOT / "harness/PROJECT_ACCEPTANCE.md"
SIGNOFF_REQUEST = ROOT / "harness/signoffs/signoff_request_v1.json"
GENERATED_OUTPUTS = (REPORT_JSON, REPORT_MD, ACCEPTANCE_MD, SIGNOFF_REQUEST)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(autouse=True)
def restore_generated_outputs() -> Iterator[None]:
    before = {
        path: path.read_bytes() if path.exists() else None
        for path in GENERATED_OUTPUTS
    }
    yield
    for path, content in before.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(content)


def test_rendered_json_markdown_and_signoff_request_share_evaluation() -> None:
    result = evaluate_project(ROOT, "current_phase")
    render_outputs(ROOT, result)

    payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    request = json.loads(SIGNOFF_REQUEST.read_text(encoding="utf-8"))
    markdown = REPORT_MD.read_text(encoding="utf-8")

    assert payload["evaluation_id"] == result.evaluation_id
    assert request["evaluation_id"] == result.evaluation_id
    assert request["contract_digest"] == result.contract_digest
    assert request["evidence_digest"] == result.evidence_digest
    assert request["profile_id"] == "current_phase"
    assert request["required_roles"] == ["governance_owner"]
    assert result.evaluation_id in markdown
    assert "harness/contracts/project_acceptance_v1.json" in ACCEPTANCE_MD.read_text(
        encoding="utf-8"
    )


def test_rerender_preserves_identity_and_generated_content() -> None:
    first = evaluate_project(ROOT, "current_phase")
    render_outputs(ROOT, first)
    before = {path: digest(path) for path in (REPORT_JSON, REPORT_MD, ACCEPTANCE_MD)}

    second = evaluate_project(ROOT, "current_phase")
    render_outputs(ROOT, second)
    after = {path: digest(path) for path in (REPORT_JSON, REPORT_MD, ACCEPTANCE_MD)}

    assert second.evaluation_id == first.evaluation_id
    assert after == before


def test_full_project_is_machine_valid_but_not_accepted() -> None:
    result = evaluate_project(ROOT, "full_project")

    assert result.profile.harness_status is HarnessStatus.VALID
    assert result.profile.project_status is ProjectVerdict.NOT_ACCEPTED
    assert "full_method_readiness_incomplete" in result.profile.reason_codes


def test_signoff_schema_has_no_failure_override_field() -> None:
    schema = json.loads(
        (ROOT / "harness/signoffs/signoff.schema.json").read_text(encoding="utf-8")
    )

    assert schema["additionalProperties"] is False
    assert "waiver" not in schema["properties"]
    assert "override" not in schema["properties"]


def test_release_profile_detects_a_stale_generated_report() -> None:
    rendered = evaluate_project(
        ROOT, "release_checkpoint", require_fresh_generated=False
    )
    render_outputs(ROOT, rendered)
    payload = json.loads(REPORT_JSON.read_bytes())
    payload["evaluation_id"] = "evaluation_000000000000000000000000"
    REPORT_JSON.write_text(json.dumps(payload), encoding="utf-8")
    result = evaluate_project(ROOT, "release_checkpoint")

    release_gate = next(
        gate for gate in result.gate_results if gate.gate_id == "release.checkpoint_integrity"
    )
    assert release_gate.verdict.value == "fail"
    assert "generated_artifact_stale" in release_gate.reason_code


def test_release_profile_rejects_current_phase_report_with_shared_digest() -> None:
    current = evaluate_project(ROOT, "current_phase")
    render_outputs(ROOT, current)

    result = evaluate_project(ROOT, "release_checkpoint")

    release_gate = next(
        gate for gate in result.gate_results if gate.gate_id == "release.checkpoint_integrity"
    )
    assert release_gate.verdict.value == "fail"
    assert release_gate.reason_code == "generated_artifact_stale"


def test_release_profile_detects_tampered_report_details() -> None:
    rendered = evaluate_project(
        ROOT, "release_checkpoint", require_fresh_generated=False
    )
    render_outputs(ROOT, rendered)
    payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    release_payload = next(
        gate
        for gate in payload["gate_results"]
        if gate["gate_id"] == "release.checkpoint_integrity"
    )
    release_payload["details"]["missing_tokens"] = ["tampered"]
    REPORT_JSON.write_text(json.dumps(payload), encoding="utf-8")

    checked = evaluate_project(ROOT, "release_checkpoint")

    release_gate = next(
        gate
        for gate in checked.gate_results
        if gate.gate_id == "release.checkpoint_integrity"
    )
    assert release_gate.reason_code == "generated_artifact_stale"


@pytest.mark.parametrize("profile_id", ["release_checkpoint", "full_project"])
def test_rendered_tuple_details_are_fresh_for_the_same_profile(
    profile_id: str,
) -> None:
    rendered = evaluate_project(ROOT, profile_id, require_fresh_generated=False)
    assert any(
        isinstance(value, tuple)
        for gate in rendered.gate_results
        for _, value in gate.details
    )
    payload = evaluation_dict(rendered)
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload

    render_outputs(ROOT, rendered)
    checked = evaluate_project(ROOT, profile_id, require_fresh_generated=True)

    release_gate = next(
        gate
        for gate in checked.gate_results
        if gate.gate_id == "release.checkpoint_integrity"
    )
    assert release_gate.verdict.value == "pass"
    assert release_gate.reason_code == "passed"


@pytest.mark.parametrize(
    "invalid_detail",
    [
        pytest.param({"unexpected"}, id="set"),
        pytest.param(Path("unexpected"), id="path"),
        pytest.param({1: "unexpected"}, id="non-string-mapping-key"),
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="positive-infinity"),
        pytest.param(float("-inf"), id="negative-infinity"),
    ],
)
def test_evaluation_dict_rejects_non_json_detail_values(
    invalid_detail: object,
) -> None:
    result = evaluate_project(ROOT, "current_phase", require_fresh_generated=False)
    invalid_gate = replace(
        result.gate_results[0], details=(("invalid", invalid_detail),)
    )
    invalid_result = replace(
        result, gate_results=(invalid_gate, *result.gate_results[1:])
    )

    with pytest.raises(TypeError, match="JSON"):
        evaluation_dict(invalid_result)


@pytest.mark.parametrize(
    ("gate_id", "detail_key", "original", "tampered"),
    [
        pytest.param(
            "governance.migration_parity",
            "active_agents_valid",
            True,
            1,
            id="bool-to-int",
        ),
        pytest.param(
            "current.manuscript_claim_boundary",
            "v033_claim_rows",
            1,
            1.0,
            id="int-to-float",
        ),
    ],
)
def test_release_profile_detects_json_scalar_type_tampering(
    gate_id: str,
    detail_key: str,
    original: object,
    tampered: object,
) -> None:
    rendered = evaluate_project(
        ROOT, "release_checkpoint", require_fresh_generated=False
    )
    render_outputs(ROOT, rendered)
    payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    gate_payload = next(
        gate for gate in payload["gate_results"] if gate["gate_id"] == gate_id
    )
    assert gate_payload["details"][detail_key] == original
    assert type(gate_payload["details"][detail_key]) is type(original)
    gate_payload["details"][detail_key] = tampered
    REPORT_JSON.write_text(json.dumps(payload), encoding="utf-8")

    checked = evaluate_project(ROOT, "release_checkpoint")

    release_gate = next(
        gate
        for gate in checked.gate_results
        if gate.gate_id == "release.checkpoint_integrity"
    )
    assert release_gate.reason_code == "generated_artifact_stale"


@pytest.mark.parametrize(
    ("path", "error_prefix"),
    [
        pytest.param(REPORT_JSON, "report_json", id="report"),
        pytest.param(SIGNOFF_REQUEST, "signoff_request", id="signoff-request"),
    ],
)
@pytest.mark.parametrize(
    "constant",
    [
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="positive-infinity"),
        pytest.param(float("-inf"), id="negative-infinity"),
    ],
)
def test_freshness_strictly_rejects_non_finite_json_constants(
    path: Path,
    error_prefix: str,
    constant: float,
) -> None:
    rendered = evaluate_project(
        ROOT, "release_checkpoint", require_fresh_generated=False
    )
    render_outputs(ROOT, rendered)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["contract_version"] = constant
    path.write_text(json.dumps(payload), encoding="utf-8")

    checked = evaluate_project(ROOT, "release_checkpoint")

    release_gate = next(
        gate
        for gate in checked.gate_results
        if gate.gate_id == "release.checkpoint_integrity"
    )
    freshness_errors = dict(release_gate.details)["freshness_errors"]
    assert release_gate.reason_code == "generated_artifact_stale"
    assert any(
        error.startswith(f"{error_prefix}:non-finite JSON constant:")
        for error in freshness_errors
    )


@pytest.mark.parametrize(
    ("path", "error_prefix", "needle", "duplicate"),
    [
        pytest.param(
            REPORT_JSON,
            "report_json",
            '"active_agents_valid": true,',
            '"active_agents_valid": true,\n'
            '        "active_agents_valid": "sensitive-marker-do-not-echo",',
            id="nested-report-details",
        ),
        pytest.param(
            SIGNOFF_REQUEST,
            "signoff_request",
            '"profile_id": "release_checkpoint",',
            '"profile_id": "release_checkpoint",\n'
            '  "profile_id": "sensitive-marker-do-not-echo",',
            id="signoff-request",
        ),
    ],
)
def test_freshness_strictly_rejects_duplicate_json_keys(
    path: Path,
    error_prefix: str,
    needle: str,
    duplicate: str,
) -> None:
    rendered = evaluate_project(
        ROOT, "release_checkpoint", require_fresh_generated=False
    )
    render_outputs(ROOT, rendered)
    raw = path.read_text(encoding="utf-8")
    assert raw.count(needle) == 1
    path.write_text(raw.replace(needle, duplicate, 1), encoding="utf-8")

    checked = evaluate_project(ROOT, "release_checkpoint")

    release_gate = next(
        gate
        for gate in checked.gate_results
        if gate.gate_id == "release.checkpoint_integrity"
    )
    freshness_errors = dict(release_gate.details)["freshness_errors"]
    assert release_gate.reason_code == "generated_artifact_stale"
    assert f"{error_prefix}:duplicate JSON key" in freshness_errors
    assert "sensitive-marker-do-not-echo" not in "\n".join(freshness_errors)
