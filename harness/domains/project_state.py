from __future__ import annotations

import csv
import fnmatch
import hashlib
import json
import re
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from harness.engine.loader import load_json, validate_contract
from harness.engine.models import (
    GateResult,
    GateVerdict,
    ProjectVerdict,
    Severity,
)

from .repository import run_legacy_validator


ArtifactIndex = Mapping[str, Mapping[str, Any]]

ARTIFACT_SCOPES = frozenset({"tracked", "external_pointer", "generated"})
CLAIM_EFFECTS = frozenset({"prohibit", "require", "allow"})
CLAIM_STATUS_TAXONOMY: Mapping[str, str] = {
    "supported": "promotion",
    "supported as action-gate boundary": "non_promotional",
    "supported as adapter/parser blocker evidence": "non_promotional",
    "supported as background synthesis": "non_promotional",
    "supported as blocker evidence": "non_promotional",
    "supported as boundary": "non_promotional",
    "supported as classification/readiness artifact": "non_promotional",
    "supported as coverage artifact": "non_promotional",
    "supported as data audit": "non_promotional",
    "supported as dataset-candidate evidence": "non_promotional",
    "supported as design evidence": "non_promotional",
    "supported as execution planning": "non_promotional",
    "supported as execution schema": "non_promotional",
    "supported as external readiness evidence": "non_promotional",
    "supported as future download manifest": "non_promotional",
    "supported as interface planning": "non_promotional",
    "supported as limitation": "non_promotional",
    "supported as metadata-level watchlist": "non_promotional",
    "supported as minimal execution evidence": "non_promotional",
    "supported as no-download dataset planning artifact": "non_promotional",
    "supported as parser replay evidence": "non_promotional",
    "supported as pilot-gate planning": "non_promotional",
    "supported as planning artifact": "non_promotional",
    "supported as planning boundary": "non_promotional",
    "supported as planning judgement": "non_promotional",
    "supported as planning/readiness evidence": "non_promotional",
    "supported as protocol artifact": "non_promotional",
    "supported as protocol rationale": "non_promotional",
    "supported as ranking lesson": "non_promotional",
    "supported as readiness audit": "non_promotional",
    "supported as review artifact": "non_promotional",
    "supported as review judgement": "non_promotional",
    "supported as schema": "non_promotional",
    "supported as scope boundary": "non_promotional",
    "supported as scoring lesson": "non_promotional",
    "supported as scoring rationale": "non_promotional",
    "supported as skill-routing decision": "non_promotional",
    "supported as target review boundary": "non_promotional",
    "supported as visual planning artifact": "non_promotional",
    "supported as writing artifact": "non_promotional",
    "supported as writing boundary": "non_promotional",
    "supported as writing-stage evaluation": "non_promotional",
    "supported with verification caveat": "non_promotional",
    "unsupported": "prohibited",
}
CLAIM_SEMANTIC_FIELDS = (
    "claim",
    "status",
    "allowed_wording",
    "forbidden_wording",
)
CLAIM_SEMANTIC_BINDING_SHA256 = (
    "efed4f159fa54c3919aee0183f7ebe10843f51b146a180d3db181ab2e5b11f7a"
)
GENERATED_ACCEPTANCE_ARTIFACT_IDS = frozenset(
    {
        "acceptance_document",
        "acceptance_report_json",
        "acceptance_report_markdown",
        "signoff_request",
    }
)
ARTIFACT_REQUIRED_FIELDS = frozenset(
    {
        "artifact_id",
        "path",
        "role",
        "format",
        "mutability",
        "evidence_class",
        "verification_scope",
        "freshness_rule",
        "allowed_uses",
        "forbidden_uses",
        "include_in_evidence_digest",
        "required_for_profiles",
    }
)
CLAIM_REQUIRED_FIELDS = frozenset(
    {
        "claim_id",
        "label",
        "required_evidence_classes",
        "forbidden_evidence_classes",
        "allowed_wording",
        "forbidden_wording",
        "promotion_patterns",
        "wet_lab_required",
    }
)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def _claim_semantic_binding_digest(rows: list[Mapping[str, Any]]) -> str:
    semantic_rows = [
        {field: row.get(field, "") for field in CLAIM_SEMANTIC_FIELDS}
        for row in rows
    ]
    payload = json.dumps(
        semantic_rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _repository_path(root: Path, raw_path: str) -> Path | None:
    windows_path = PureWindowsPath(raw_path)
    if Path(raw_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
        return None
    repository_root = root.resolve()
    candidate = (repository_root / raw_path).resolve(strict=False)
    try:
        candidate.relative_to(repository_root)
    except ValueError:
        return None
    return candidate


def validate_registry(
    root: Path,
    contract: Mapping[str, Any],
    artifact_registry: Mapping[str, Any],
    claim_registry: Mapping[str, Any],
) -> tuple[str, ...]:
    """Validate registry structure and all contract references without side effects."""

    errors: list[str] = []
    profiles = contract.get("profiles")
    known_profiles = {
        row["profile_id"]
        for row in profiles
        if isinstance(row, dict) and _nonempty_string(row.get("profile_id"))
    } if isinstance(profiles, list) else set()

    for field in ("registry_id", "registry_version"):
        if not _nonempty_string(artifact_registry.get(field)):
            errors.append(f"artifact_registry.{field} must be a non-empty string")
    rows = artifact_registry.get("artifacts")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        errors.append("artifact_registry.artifacts must be a list of objects")
        rows = []

    artifact_ids: set[str] = set()
    artifact_paths: set[str] = set()
    canonical_artifact_paths: set[str] = set()
    for index, row in enumerate(rows):
        prefix = f"artifact[{index}]"
        missing = ARTIFACT_REQUIRED_FIELDS - set(row)
        if missing:
            errors.append(f"{prefix} missing fields: {sorted(missing)}")

        for field in (
            "artifact_id",
            "path",
            "role",
            "format",
            "mutability",
            "evidence_class",
            "freshness_rule",
        ):
            if not _nonempty_string(row.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        for field in ("allowed_uses", "forbidden_uses", "required_for_profiles"):
            if not _string_list(row.get(field)):
                errors.append(f"{prefix}.{field} must be a list of non-empty strings")
        if not isinstance(row.get("include_in_evidence_digest"), bool):
            errors.append(f"{prefix}.include_in_evidence_digest must be a boolean")

        artifact_id = row.get("artifact_id")
        if _nonempty_string(artifact_id):
            if artifact_id in artifact_ids:
                errors.append(f"duplicate artifact_id: {artifact_id}")
            artifact_ids.add(artifact_id)

        scope = row.get("verification_scope")
        if scope not in ARTIFACT_SCOPES:
            errors.append(
                f"{prefix}.verification_scope must be one of {sorted(ARTIFACT_SCOPES)}"
            )
        if row.get("include_in_evidence_digest") is True and scope != "tracked":
            errors.append(
                f"{prefix}: only tracked artifacts may enter the evidence digest"
            )
        if _nonempty_string(artifact_id) and artifact_id in GENERATED_ACCEPTANCE_ARTIFACT_IDS and (
            scope != "generated" or row.get("include_in_evidence_digest") is not False
        ):
            errors.append(
                f"{prefix}: generated acceptance artifact must remain generated and excluded from the evidence digest"
            )

        path = row.get("path")
        canonical_path: str | None = None
        repository_path: Path | None = None
        duplicate_raw_path = False
        if _nonempty_string(path):
            if (
                path.startswith("harness/signoffs/")
                and path
                not in {
                    "harness/signoffs/signoff.schema.json",
                    "harness/signoffs/signoff_request_v1.json",
                }
            ):
                errors.append(
                    f"{prefix}: human signoff decisions cannot be registry evidence"
                )
            duplicate_raw_path = path in artifact_paths
            if duplicate_raw_path:
                errors.append(f"duplicate artifact path: {path}")
            artifact_paths.add(path)
            if scope in {"tracked", "generated"}:
                repository_path = _repository_path(root, path)
                if repository_path is None:
                    errors.append(
                        f"{prefix}.path must be a relative path within repository root"
                    )
                else:
                    canonical_path = str(repository_path)
            else:
                canonical_path = str(Path(path))
        if canonical_path is not None:
            if canonical_path in canonical_artifact_paths and not duplicate_raw_path:
                errors.append(f"duplicate artifact path: {path}")
            canonical_artifact_paths.add(canonical_path)

        required_profiles = row.get("required_for_profiles")
        if _string_list(required_profiles):
            unknown_profiles = set(required_profiles) - known_profiles
            if unknown_profiles:
                errors.append(
                    f"{prefix} has unknown required profile IDs: {sorted(unknown_profiles)}"
                )
            if (
                scope == "tracked"
                and required_profiles
                and repository_path is not None
                and not repository_path.exists()
            ):
                errors.append(
                    f"{prefix} required tracked path does not exist: {path}"
                )

    for field in ("registry_id", "registry_version"):
        if not _nonempty_string(claim_registry.get(field)):
            errors.append(f"claim_registry.{field} must be a non-empty string")
    if not _nonempty_string(claim_registry.get("claim_surface_path")):
        errors.append("claim_registry.claim_surface_path must be a non-empty string")
    if not re.fullmatch(r"[0-9a-f]{64}", str(claim_registry.get("claim_surface_sha256", ""))):
        errors.append("claim_registry.claim_surface_sha256 must be a SHA-256 digest")
    if not isinstance(claim_registry.get("claim_surface_row_count"), int):
        errors.append("claim_registry.claim_surface_row_count must be an integer")
    if (
        claim_registry.get("claim_semantic_binding_sha256")
        != CLAIM_SEMANTIC_BINDING_SHA256
    ):
        errors.append(
            "claim_registry.claim_semantic_binding_sha256 must match the engine-owned binding"
        )
    claim_surface_rows: list[dict[str, str]] = []
    claim_surface_path = claim_registry.get("claim_surface_path")
    if _nonempty_string(claim_surface_path):
        if claim_surface_path not in artifact_paths:
            errors.append("claim surface path must resolve through the artifact registry")
        resolved_claim_surface = _repository_path(root, claim_surface_path)
        if resolved_claim_surface is None or not resolved_claim_surface.is_file():
            errors.append("claim surface path is missing or outside the repository")
        else:
            observed_sha = hashlib.sha256(resolved_claim_surface.read_bytes()).hexdigest()
            if observed_sha != claim_registry.get("claim_surface_sha256"):
                errors.append("claim surface SHA-256 mismatch")
            with resolved_claim_surface.open(newline="", encoding="utf-8") as handle:
                claim_surface_rows = list(csv.DictReader(handle))
            if len(claim_surface_rows) != claim_registry.get("claim_surface_row_count"):
                errors.append("claim surface row-count mismatch")
    status_taxonomy = claim_registry.get("status_taxonomy")
    if status_taxonomy != CLAIM_STATUS_TAXONOMY:
        errors.append(
            "claim_registry.status_taxonomy must exactly match the engine-owned taxonomy"
        )
    observed_statuses = {row.get("status", "") for row in claim_surface_rows}
    unknown_statuses = observed_statuses - set(CLAIM_STATUS_TAXONOMY)
    if unknown_statuses:
        errors.append(
            f"claim surface has unrecognized statuses: {sorted(unknown_statuses)}"
        )
    if (
        _claim_semantic_binding_digest(claim_surface_rows)
        != CLAIM_SEMANTIC_BINDING_SHA256
    ):
        errors.append("claim surface semantic/status binding mismatch")
    claim_rows = claim_registry.get("claims")
    if not isinstance(claim_rows, list) or not all(
        isinstance(row, dict) for row in claim_rows
    ):
        errors.append("claim_registry.claims must be a list of objects")
        claim_rows = []

    claim_ids: set[str] = set()
    for index, row in enumerate(claim_rows):
        prefix = f"claim[{index}]"
        missing = CLAIM_REQUIRED_FIELDS - set(row)
        if missing:
            errors.append(f"{prefix} missing fields: {sorted(missing)}")
        for field in ("claim_id", "label"):
            if not _nonempty_string(row.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        for field in (
            "required_evidence_classes",
            "forbidden_evidence_classes",
            "allowed_wording",
            "forbidden_wording",
            "promotion_patterns",
        ):
            if not _string_list(row.get(field)):
                errors.append(f"{prefix}.{field} must be a list of non-empty strings")
        if not isinstance(row.get("wet_lab_required"), bool):
            errors.append(f"{prefix}.wet_lab_required must be a boolean")

        claim_id = row.get("claim_id")
        if _nonempty_string(claim_id):
            if claim_id in claim_ids:
                errors.append(f"duplicate claim_id: {claim_id}")
            claim_ids.add(claim_id)

    gates = contract.get("gates")
    if not isinstance(gates, list) or not all(isinstance(gate, dict) for gate in gates):
        errors.append("contract.gates must be a list of objects")
        gates = []
    for gate in gates:
        gate_id = gate.get("gate_id", "<unknown>")
        inputs = gate.get("inputs")
        if not _string_list(inputs):
            errors.append(f"gate {gate_id} inputs must be a list of artifact IDs")
        else:
            for artifact_id in inputs:
                if artifact_id not in artifact_ids:
                    errors.append(
                        f"gate {gate_id} has unresolved artifact input: {artifact_id}"
                    )

        effects = gate.get("claim_effects")
        if not isinstance(effects, list) or not all(
            isinstance(effect, dict) for effect in effects
        ):
            errors.append(f"gate {gate_id} claim_effects must be a list of objects")
            continue
        for effect in effects:
            claim_id = effect.get("claim_id")
            effect_name = effect.get("effect")
            if claim_id not in claim_ids:
                errors.append(f"gate {gate_id} has unknown claim_id: {claim_id}")
            if effect_name not in CLAIM_EFFECTS:
                errors.append(f"gate {gate_id} has invalid effect: {effect_name}")

    return tuple(errors)


def _artifact_path(root: Path, artifact: Mapping[str, Any]) -> Path:
    path = Path(str(artifact["path"]))
    return path if path.is_absolute() else root / path


def _input_paths(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> tuple[Path, ...]:
    return tuple(_artifact_path(root, artifacts[item]) for item in gate["inputs"])


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _details(**values: Any) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(values.items()))


def _result(
    gate: Mapping[str, Any],
    verdict: GateVerdict,
    message: str,
    evidence: tuple[Path, ...],
    *,
    details: tuple[tuple[str, Any], ...] = (),
    failure_status: ProjectVerdict = ProjectVerdict.NOT_ACCEPTED,
) -> GateResult:
    reason_code = "passed" if verdict is GateVerdict.PASS else gate["failure_reason_code"]
    return GateResult(
        gate_id=str(gate["gate_id"]),
        domain=str(gate["domain"]),
        severity=Severity(str(gate["severity"])),
        verdict=verdict,
        reason_code=str(reason_code),
        message=message,
        evidence=tuple(str(path) for path in evidence),
        failure_status=failure_status,
        details=details,
    )


def _error(
    gate: Mapping[str, Any], message: str, evidence: tuple[Path, ...]
) -> GateResult:
    return _result(gate, GateVerdict.ERROR, message, evidence)


def _evaluate_contract(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    contract = load_json(paths[0])
    validate_contract(contract)
    return _result(gate, GateVerdict.PASS, "Acceptance contract is structurally valid.", paths)


def _evaluate_artifact_registry(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    contract = load_json(root / "harness/contracts/project_acceptance_v1.json")
    registry = load_json(root / "harness/registry/artifacts_v1.json")
    claims = load_json(root / "harness/registry/claims_v1.json")
    errors = validate_registry(root, contract, registry, claims)
    rows = registry.get("artifacts", [])
    claim_rows = claims.get("claims", [])
    valid = not errors
    return _result(
        gate,
        GateVerdict.PASS if valid else GateVerdict.ERROR,
        "Artifact and claim registries and contract references are valid."
        if valid
        else "Artifact or claim registry security validation failed.",
        paths,
        details=_details(
            artifact_count=len(rows),
            claim_count=len(claim_rows),
            errors=errors,
        ),
    )


def _legacy_artifact_paths(agents_text: str) -> list[str]:
    section = agents_text.split("## Current Artifact Roles", 1)[1].split(
        "## Execution Gates", 1
    )[0]
    return re.findall(r"^\| `([^`]+)` \|", section, flags=re.MULTILINE)


def _evaluate_migration_parity(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    parity = load_json(paths[0])
    agents_text = paths[1].read_text(encoding="utf-8")
    snapshot_bytes = paths[2].read_bytes()
    snapshot_text = snapshot_bytes.decode("utf-8")
    missing_tokens = [
        token for token in parity["required_operating_tokens"] if token not in agents_text
    ]
    legacy_policy_keys = set(parity.get("legacy_policy_keys", ()))
    active_policy_map = parity.get("active_policy_map", {})
    active_policy_keys_valid = (
        isinstance(active_policy_map, dict)
        and set(active_policy_map) == legacy_policy_keys
        and all(
            isinstance(tokens, list)
            and bool(tokens)
            and all(isinstance(token, str) and token for token in tokens)
            for tokens in active_policy_map.values()
        )
    )
    missing_policy_tokens = tuple(
        sorted(
            f"{policy_key}:{token}"
            for policy_key, tokens in active_policy_map.items()
            if isinstance(tokens, list)
            for token in tokens
            if not isinstance(token, str) or token not in agents_text
        )
    ) if isinstance(active_policy_map, dict) else ("active_policy_map:not_object",)
    patterns = [row["path_pattern"] for row in parity["legacy_artifact_role_patterns"]]
    legacy_paths = _legacy_artifact_paths(snapshot_text)
    unmapped = [
        path
        for path in legacy_paths
        if not any(fnmatch.fnmatch(path, pattern) for pattern in patterns)
    ]
    snapshot_valid = (
        hashlib.sha256(snapshot_bytes).hexdigest() == parity["legacy_agents_sha256"]
        and len(snapshot_text.splitlines()) == parity["legacy_agents_line_count"]
        and len(legacy_paths) == parity["legacy_artifact_role_count"]
    )
    active_agents_valid = (
        hashlib.sha256(agents_text.encode("utf-8")).hexdigest()
        == parity.get("active_agents_sha256")
    )
    valid = (
        snapshot_valid
        and active_agents_valid
        and active_policy_keys_valid
        and not missing_policy_tokens
        and not missing_tokens
        and not unmapped
    )
    return _result(
        gate,
        GateVerdict.PASS if valid else GateVerdict.FAIL,
        "Legacy AGENTS policies and artifact roles are mapped."
        if valid
        else "Legacy rule migration is incomplete.",
        paths,
        details=_details(
            missing_tokens=tuple(missing_tokens),
            missing_policy_tokens=missing_policy_tokens,
            active_agents_valid=active_agents_valid,
            active_policy_keys_valid=active_policy_keys_valid,
            snapshot_valid=snapshot_valid,
            unmapped_artifacts=tuple(unmapped),
        ),
    )


def _evaluate_kb_validator(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    result = run_legacy_validator(root)
    passed = (
        result.get("status") == "pass"
        and result.get("errors") == []
        and result.get("warnings") == []
        and result.get("process_exit_code") == 0
    )
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        "Legacy KB validator passed read-only."
        if passed
        else "Legacy KB validator reported errors or warnings.",
        paths,
        details=_details(
            errors=len(result.get("errors", [])),
            warnings=len(result.get("warnings", [])),
        ),
    )


def _v033_counts(paths: tuple[Path, ...]) -> dict[str, int]:
    by_name = {path.name: path for path in paths}
    execution_rows = _read_csv(by_name["pilot_execution_results_v0.33.csv"])
    candidate_rows = _read_csv(by_name["pilot_candidate_outputs_v0.33.csv"])
    run_rows = _read_csv(by_name["pilot_run_v0.33.csv"])
    summary = json.loads(by_name["pilot_v033_merge_summary.json"].read_text(encoding="utf-8"))
    return {
        "execution_rows": len(execution_rows),
        "candidate_evidence_rows": len(candidate_rows),
        "run_rows": len(run_rows),
        "failed_rows": sum(row.get("status") == "failed" for row in execution_rows),
        "parsed_candidates": sum(
            row.get("parse_status") == "parsed" for row in candidate_rows
        ),
        "generated_runs": sum(row.get("status") == "generated" for row in run_rows),
        "active_exit_86_rows": sum(
            "exit_86" in row.get("blocked_reason", "") for row in execution_rows
        ),
        "method_specific_blockers": sum(
            row.get("blocked_reason", "").endswith("_no_supported_output_found")
            for row in execution_rows
        ),
        "summary_candidate_rows": int(summary.get("candidate_rows", -1)),
    }


def _evaluate_v033(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    counts = _v033_counts(paths)
    truthful = (
        counts["execution_rows"] == 10
        and counts["candidate_evidence_rows"] == 10
        and counts["run_rows"] == 10
        and counts["failed_rows"] == 10
        and counts["parsed_candidates"] == 0
        and counts["generated_runs"] == 0
        and counts["active_exit_86_rows"] == 0
        and counts["method_specific_blockers"] == 10
        and counts["summary_candidate_rows"] == 10
    )
    if gate["gate_id"] == "current.v033_baseline_truth":
        return _result(
            gate,
            GateVerdict.PASS if truthful else GateVerdict.FAIL,
            "v0.33 truthfully records ten method-specific blockers and zero generated candidates."
            if truthful
            else "v0.33 blocker counts or generation status do not match the contract.",
            paths,
            details=_details(**counts),
        )
    return _result(
        gate,
        GateVerdict.FAIL if truthful else GateVerdict.PASS,
        "Full-project generation readiness is incomplete because v0.33 still contains blockers."
        if truthful
        else "The v0.33 blocker baseline has been superseded and needs full-project review.",
        paths,
        details=_details(**counts),
    )


def _evaluate_target_controls(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    target_path = next(path for path in paths if "target_manifest" in path.name)
    control_path = next(path for path in paths if "control_manifest" in path.name)
    target_set_path = next(path for path in paths if path.name == "target_set_v0.csv")
    targets = _read_csv(target_path)
    controls = _read_csv(control_path)
    target_set = _read_csv(target_set_path)
    missing_controls = sum(
        row.get("status") in {"missing", "blocked"}
        or "missing" in row.get("blocker", "")
        or "unresolved" in row.get("blocker", "")
        for row in controls
    )
    frozen_targets = len(target_set)
    details = _details(
        pilot_targets=len(targets),
        pilot_controls=len(controls),
        missing_controls=missing_controls,
        frozen_target_rows=frozen_targets,
    )
    if gate["gate_id"] == "current.target_control_boundary":
        passed = frozen_targets == 0 and missing_controls >= 1
        return _result(
            gate,
            GateVerdict.PASS if passed else GateVerdict.FAIL,
            "Unfrozen target set and unresolved controls are explicitly represented."
            if passed
            else "Current target/control boundary is not represented consistently.",
            paths,
            details=details,
        )
    passed = frozen_targets > 0 and missing_controls == 0
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        "Target/control governance is complete."
        if passed
        else "Target set is not frozen with complete controls and leakage review.",
        paths,
        details=details,
    )


def _evaluate_dflow_leakage(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    evidence = load_json(paths[0])
    passed = (
        evidence.get("matched_value") == "3eqs_B"
        and evidence.get("split") == "train"
        and evidence.get("conclusion")
        == "known_training_overlap_fixture_only_scoring_prohibited"
        and evidence.get("source_sha256")
        == "ff168c194c225c8a117c1e1cfff365edc5ba2f812a0dcc9836e1d3238590da44"
    )
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        "Known D-Flow 3eqs_B training overlap is recorded as fixture-only."
        if passed
        else "D-Flow training-overlap derivation is missing or inconsistent.",
        paths,
        details=_details(
            matched_value=evidence.get("matched_value", ""),
            split=evidence.get("split", ""),
        ),
    )


def _job_and_candidate_rows(
    root: Path, artifacts: ArtifactIndex
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    jobs = _read_csv(_artifact_path(root, artifacts["pilot_job_manifest"]))
    candidates = _read_csv(_artifact_path(root, artifacts["v033_candidate_outputs"]))
    return jobs, candidates


def _evaluate_rf_conditioning(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    jobs, candidates = _job_and_candidate_rows(root, artifacts)
    rf_jobs = [row for row in jobs if row.get("method") == "RFdiffusion + ProteinMPNN"]
    rf_candidates = [
        row for row in candidates if row.get("method") == "RFdiffusion + ProteinMPNN"
    ]
    evidence = load_json(_artifact_path(root, artifacts["rf_unconditional_example"]))
    compact_derivation_valid = (
        evidence.get("source_sha256")
        == "44dc40d2a793d9b69636ef02acae9688f08f6fed85dcd5d93adb1f756242913d"
        and evidence.get("observed_contig") == "[12-18]"
        and evidence.get("target_conditioned") is False
        and evidence.get("conclusion")
        == "example_unconditional_not_target_conditioned_generation"
    )
    unconditional = bool(rf_jobs) and all(
        row.get("pocket_definition") == "contigmap.contigs=[12-18]" for row in rf_jobs
    )
    blocker_only = bool(rf_candidates) and all(
        row.get("parse_status") == "failed"
        and row.get("status_reason")
        == "rfdiffusion_proteinmpnn_adapter_attempt_no_supported_output_found"
        for row in rf_candidates
    )
    passed = compact_derivation_valid and unconditional and blocker_only
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        "The unconditional [12-18] RFdiffusion example is retained only as a target-conditioning blocker."
        if passed
        else "RFdiffusion target-conditioning semantics are not fail-closed.",
        paths,
        details=_details(
            compact_derivation_valid=compact_derivation_valid,
            rf_jobs=len(rf_jobs),
            blocker_rows=len(rf_candidates),
        ),
    )


def _evaluate_pepmirror_chirality(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    if gate["gate_id"] == "full.output_representation":
        return _result(
            gate,
            GateVerdict.FAIL,
            "Full topology and chirality representation has no accepted candidates to validate.",
            paths,
        )
    jobs, candidates = _job_and_candidate_rows(root, artifacts)
    jobs = [row for row in jobs if row.get("method") == "PepMirror"]
    candidates = [row for row in candidates if row.get("method") == "PepMirror"]
    evidence = load_json(_artifact_path(root, artifacts["pepmirror_chirality_gap"]))
    compact_derivation_valid = (
        evidence.get("source_sha256")
        == "77c332e3739f58f607b0cc5e0d9b52ffc8c1fc41786ef3664a143049f54316f2"
        and evidence.get("requested_chirality") == "D"
        and evidence.get("mirror_transform_observed") is False
        and evidence.get("conclusion")
        == "d_peptide_claim_blocked_without_mirror_transform"
    )
    d_jobs = bool(jobs) and all(row.get("chirality") == "D" for row in jobs)
    blocker_only = bool(candidates) and all(
        row.get("parse_status") == "failed"
        and row.get("status_reason") == "pepmirror_adapter_attempt_no_supported_output_found"
        for row in candidates
    )
    passed = compact_derivation_valid and d_jobs and blocker_only
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        "PepMirror D-peptide jobs remain blocked because mirror transformation evidence is absent."
        if passed
        else "PepMirror chirality semantics are not fail-closed.",
        paths,
        details=_details(
            compact_derivation_valid=compact_derivation_valid,
            d_jobs=len(jobs),
            blocker_rows=len(candidates),
        ),
    )


def _evaluate_scoring_guard(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    if gate["gate_id"] == "full.scoring_validation":
        return _result(
            gate,
            GateVerdict.FAIL,
            "No eligible controlled scoring artifacts exist for full-project acceptance.",
            paths,
        )
    plan = _artifact_path(root, artifacts["current_plan"]).read_text(encoding="utf-8")
    candidates = _read_csv(_artifact_path(root, artifacts["v033_candidate_outputs"]))
    no_scores = all(row.get("parse_status") == "failed" for row in candidates)
    plan_blocks_scoring = "不启动 scoring" in plan or "不执行 scoring" in plan
    passed = no_scores and plan_blocks_scoring
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        "Scoring remains disabled until candidate and target/control eligibility gates pass."
        if passed
        else "Scoring guard is missing or a v0.33 row was promoted.",
        paths,
        details=_details(scored_rows=0 if no_scores else 1),
    )


def _evaluate_manuscript_claims(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    claim_map_path = _artifact_path(root, artifacts["claim_evidence_map"])
    rows = _read_csv(claim_map_path)
    claim_registry = load_json(_artifact_path(root, artifacts["claim_registry"]))
    claim_policies = claim_registry["claims"]
    status_taxonomy_valid = (
        claim_registry.get("status_taxonomy") == CLAIM_STATUS_TAXONOMY
    )
    claim_semantic_binding_valid = (
        claim_registry.get("claim_semantic_binding_sha256")
        == CLAIM_SEMANTIC_BINDING_SHA256
        and _claim_semantic_binding_digest(rows)
        == CLAIM_SEMANTIC_BINDING_SHA256
    )
    artifact_registry = load_json(_artifact_path(root, artifacts["artifact_registry"]))
    evidence_class_by_path = {
        row["path"]: row["evidence_class"] for row in artifact_registry["artifacts"]
    }
    v033_rows = [row for row in rows if "v0.33" in row.get("claim", "")]
    protected_unsupported_claims = {
        "任何候选方法已完成本地复现",
        "计算评分可替代实验验证",
    }
    unrecognized_claim_statuses = tuple(
        sorted(
            {
                row.get("status", "")
                for row in rows
                if row.get("status", "") not in CLAIM_STATUS_TAXONOMY
            }
        )
    )
    promoted_claims = [
        row.get("claim", "")
        for row in rows
        if row.get("claim") in protected_unsupported_claims
        and CLAIM_STATUS_TAXONOMY.get(row.get("status")) != "prohibited"
    ]
    forbidden_wording_violations: list[str] = []
    for row in rows:
        if CLAIM_STATUS_TAXONOMY.get(row.get("status")) == "prohibited":
            continue
        surface = f"{row.get('claim', '')} {row.get('allowed_wording', '')}".casefold()
        for policy in claim_policies:
            for phrase in policy.get("forbidden_wording", ()):
                if phrase.casefold() in surface:
                    forbidden_wording_violations.append(
                        f"{policy['claim_id']}:{phrase}:{row.get('claim', '')}"
                    )
    unsupported_evidence_promotions = [
        row.get("claim", "")
        for row in rows
        if row.get("evidence", "").strip().casefold() in {"", "none"}
        and CLAIM_STATUS_TAXONOMY.get(row.get("status")) != "prohibited"
    ]
    claim_surface_valid = (
        hashlib.sha256(claim_map_path.read_bytes()).hexdigest()
        == claim_registry.get("claim_surface_sha256")
        and len(rows) == claim_registry.get("claim_surface_row_count")
        and claim_registry.get("claim_surface_path")
        == "manuscript/support/benchmark_manuscript_claim_evidence_map.csv"
    )
    evidence_policy_violations: list[str] = []
    for row in rows:
        polarity = CLAIM_STATUS_TAXONOMY.get(row.get("status"))
        if polarity != "promotion":
            continue
        surface = f"{row.get('claim', '')} {row.get('allowed_wording', '')}".casefold()
        evidence_paths = [
            value.strip() for value in row.get("evidence", "").split(";") if value.strip()
        ]
        observed_classes = {
            evidence_class_by_path[path]
            for path in evidence_paths
            if path in evidence_class_by_path
        }
        for policy in claim_policies:
            matches_promotion = any(
                pattern.casefold() in surface
                for pattern in policy.get("promotion_patterns", ())
            )
            if not matches_promotion:
                continue
            required_classes = set(policy.get("required_evidence_classes", ()))
            forbidden_classes = set(policy.get("forbidden_evidence_classes", ()))
            missing_classes = required_classes - observed_classes
            prohibited_classes = forbidden_classes & observed_classes
            if missing_classes or prohibited_classes:
                evidence_policy_violations.append(
                    f"{policy['claim_id']}:{row.get('claim', '')}:"
                    f"missing={sorted(missing_classes)}:"
                    f"forbidden={sorted(prohibited_classes)}"
                )
    passed = (
        not promoted_claims
        and not forbidden_wording_violations
        and not unsupported_evidence_promotions
        and claim_surface_valid
        and status_taxonomy_valid
        and claim_semantic_binding_valid
        and not unrecognized_claim_statuses
        and not evidence_policy_violations
        and len(v033_rows) == 1
        and (
        v033_rows[0].get("status") == "supported as adapter/parser blocker evidence"
        and "已完成正式 Wave A generation" in v033_rows[0].get("forbidden_wording", "")
        and "方法性能可排名" in v033_rows[0].get("forbidden_wording", "")
        )
    )
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        "The v0.33 manuscript claim remains bounded to adapter/parser blocker evidence."
        if passed
        else "The v0.33 claim boundary is missing or promoted.",
        paths,
        details=_details(
            promoted_unsupported_claims=tuple(promoted_claims),
            forbidden_wording_violations=tuple(forbidden_wording_violations),
            evidence_policy_violations=tuple(evidence_policy_violations),
            claim_semantic_binding_valid=claim_semantic_binding_valid,
            claim_surface_valid=claim_surface_valid,
            claim_status_taxonomy_valid=status_taxonomy_valid,
            unrecognized_claim_statuses=unrecognized_claim_statuses,
            unsupported_evidence_promotions=tuple(unsupported_evidence_promotions),
            v033_claim_rows=len(v033_rows),
        ),
    )


def _evaluate_benchmark_pillars(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    return _result(
        gate,
        GateVerdict.FAIL,
        "Empirical Findings remain unsupported because controlled scoring has not started; the companion method is optional.",
        paths,
        details=_details(missing_pillars=("empirical_findings",)),
    )


def _evaluate_release_integrity(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    required_tokens = {
        "README.md": "harness/PROJECT_ACCEPTANCE.md",
        "benchmark/README.md": "project_acceptance_report.md",
        "index.md": "ops/acceptance/project_acceptance_report.md",
        "AGENTS.md": "harness_engineering_plan_v1.0.md",
    }
    if version == "1.2.21":
        required_tokens.update(
            {
                "RELEASE_NOTES.md": (
                    "## Unreleased Harness Engineering Workflow "
                    "(`VERSION=1.2.21`)"
                ),
                "ops/log.md": "harness engineering v1.0 unsigned checkpoint",
            }
        )
    elif version == "1.2.22":
        required_tokens.update(
            {
                "RELEASE_NOTES.md": "## v1.2.22 Harness Engineering Checkpoint",
                "ops/log.md": "release | v1.2.22 harness engineering checkpoint",
            }
        )
    missing = []
    for filename, token in required_tokens.items():
        text = (root / filename).read_text(encoding="utf-8")
        if token not in text:
            missing.append(f"{filename}:{token}")
    if version not in {"1.2.21", "1.2.22"}:
        missing.append(f"VERSION:unsupported:{version}")
    for filename in ("README.md", "index.md", "AGENTS.md"):
        if version not in (root / filename).read_text(encoding="utf-8"):
            missing.append(f"{filename}:version:{version}")
    passed = not missing
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        f"Release checkpoint navigation and version boundary are consistent for {version}."
        if passed
        else "Pending release checkpoint documentation is incomplete.",
        paths,
        details=_details(missing_tokens=tuple(missing)),
    )


EVALUATORS = {
    "contract_integrity": _evaluate_contract,
    "artifact_registry_integrity": _evaluate_artifact_registry,
    "migration_parity": _evaluate_migration_parity,
    "kb_validator": _evaluate_kb_validator,
    "v033_baseline": _evaluate_v033,
    "target_controls": _evaluate_target_controls,
    "semantic_dflow_leakage": _evaluate_dflow_leakage,
    "semantic_rf_target_conditioning": _evaluate_rf_conditioning,
    "semantic_pepmirror_chirality": _evaluate_pepmirror_chirality,
    "scoring_guard": _evaluate_scoring_guard,
    "manuscript_claims": _evaluate_manuscript_claims,
    "benchmark_pillars": _evaluate_benchmark_pillars,
    "release_integrity": _evaluate_release_integrity,
}


def evaluate_gate(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    try:
        evidence = _input_paths(root, gate, artifacts)
        missing_external = tuple(
            path
            for artifact_id, path in zip(gate["inputs"], evidence, strict=True)
            if artifacts[artifact_id].get("verification_scope") == "external_pointer"
            and not path.exists()
        )
        if missing_external:
            return _result(
                gate,
                GateVerdict.FAIL,
                "Required external evidence is unavailable; historical records were not rewritten.",
                evidence,
                failure_status=ProjectVerdict.BLOCKED,
                details=_details(
                    missing_external=tuple(str(path) for path in missing_external)
                ),
            )
        evaluator = EVALUATORS[str(gate["evaluator"])]
        return evaluator(root, gate, artifacts)
    except Exception as exc:
        fallback_evidence = locals().get("evidence", ())
        return _error(gate, f"Evaluator error: {exc}", fallback_evidence)
