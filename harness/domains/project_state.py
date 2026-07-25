from __future__ import annotations

import csv
import fnmatch
import hashlib
import importlib
import io
import json
import math
import os
import re
import stat
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from harness.engine.loader import load_json, validate_contract
from harness.engine.models import (
    GateResult,
    GateVerdict,
    ProjectVerdict,
    Severity,
)
from scripts.v034_adapters.common import (
    chirality_stats,
    chirality_stats_from_pdb_bytes,
    evaluate_candidate_qc,
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
    "8c8f988437ce4a6550c37069e34f6162b7d90f5048e83ca74087d879af2f2f53"
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
        {field: row.get(field, "") for field in CLAIM_SEMANTIC_FIELDS} for row in rows
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
    known_profiles = (
        {
            row["profile_id"]
            for row in profiles
            if isinstance(row, dict) and _nonempty_string(row.get("profile_id"))
        }
        if isinstance(profiles, list)
        else set()
    )

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
        if (
            _nonempty_string(artifact_id)
            and artifact_id in GENERATED_ACCEPTANCE_ARTIFACT_IDS
            and (
                scope != "generated"
                or row.get("include_in_evidence_digest") is not False
            )
        ):
            errors.append(
                f"{prefix}: generated acceptance artifact must remain generated and excluded from the evidence digest"
            )

        path = row.get("path")
        canonical_path: str | None = None
        repository_path: Path | None = None
        duplicate_raw_path = False
        if _nonempty_string(path):
            if path.startswith("harness/signoffs/") and path not in {
                "harness/signoffs/signoff.schema.json",
                "harness/signoffs/signoff_request_v1.json",
            }:
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
                errors.append(f"{prefix} required tracked path does not exist: {path}")

    for field in ("registry_id", "registry_version"):
        if not _nonempty_string(claim_registry.get(field)):
            errors.append(f"claim_registry.{field} must be a non-empty string")
    if not _nonempty_string(claim_registry.get("claim_surface_path")):
        errors.append("claim_registry.claim_surface_path must be a non-empty string")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(claim_registry.get("claim_surface_sha256", ""))
    ):
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
            errors.append(
                "claim surface path must resolve through the artifact registry"
            )
        resolved_claim_surface = _repository_path(root, claim_surface_path)
        if resolved_claim_surface is None or not resolved_claim_surface.is_file():
            errors.append("claim surface path is missing or outside the repository")
        else:
            observed_sha = hashlib.sha256(
                resolved_claim_surface.read_bytes()
            ).hexdigest()
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
    reason_code = (
        "passed" if verdict is GateVerdict.PASS else gate["failure_reason_code"]
    )
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
    return _result(
        gate, GateVerdict.PASS, "Acceptance contract is structurally valid.", paths
    )


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
        (
            "Artifact and claim registries and contract references are valid."
            if valid
            else "Artifact or claim registry security validation failed."
        ),
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
        token
        for token in parity["required_operating_tokens"]
        if token not in agents_text
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
    missing_policy_tokens = (
        tuple(
            sorted(
                f"{policy_key}:{token}"
                for policy_key, tokens in active_policy_map.items()
                if isinstance(tokens, list)
                for token in tokens
                if not isinstance(token, str) or token not in agents_text
            )
        )
        if isinstance(active_policy_map, dict)
        else ("active_policy_map:not_object",)
    )
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
    active_agents_valid = hashlib.sha256(
        agents_text.encode("utf-8")
    ).hexdigest() == parity.get("active_agents_sha256")
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
        (
            "Legacy AGENTS policies and artifact roles are mapped."
            if valid
            else "Legacy rule migration is incomplete."
        ),
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
        (
            "Legacy KB validator passed read-only."
            if passed
            else "Legacy KB validator reported errors or warnings."
        ),
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
    summary = json.loads(
        by_name["pilot_v033_merge_summary.json"].read_text(encoding="utf-8")
    )
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
            (
                "v0.33 truthfully records ten method-specific blockers and zero generated candidates."
                if truthful
                else "v0.33 blocker counts or generation status do not match the contract."
            ),
            paths,
            details=_details(**counts),
        )
    return _result(
        gate,
        GateVerdict.FAIL if truthful else GateVerdict.PASS,
        (
            "Full-project generation readiness is incomplete because v0.33 still contains blockers."
            if truthful
            else "The v0.33 blocker baseline has been superseded and needs full-project review."
        ),
        paths,
        details=_details(**counts),
    )


V034_METHODS = frozenset(
    {
        "PepMLM",
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "PepMirror",
        "AfCycDesign / ColabDesign cyclic peptide",
        "RFdiffusion + ProteinMPNN",
    }
)
V034_ACCEPTED_QC = frozenset({"pass", "pass_with_warning"})
V034_ADAPTER_MODULES = {
    "PepMLM": "scripts.v034_adapters.pepmlm",
    "DiffPepBuilder": "scripts.v034_adapters.diffpepbuilder",
    "PepGLAD": "scripts.v034_adapters.pepglad",
    "D-Flow / PeptideDesign": "scripts.v034_adapters.dflow",
    "PepMirror": "scripts.v034_adapters.pepmirror",
    "AfCycDesign / ColabDesign cyclic peptide": (
        "scripts.v034_adapters.colabdesign"
    ),
    "RFdiffusion + ProteinMPNN": "scripts.v034_adapters.rfdiffusion_mpnn",
}
V034_RUNTIME_PAYLOAD_FIELDS = frozenset(
    {"schema_version", "evidence_boundary", "records"}
)
V034_RUNTIME_RECORD_FIELDS = frozenset(
    {
        "job_id",
        "method",
        "seed_stage",
        "random_seed",
        "attempt_id",
        "runtime_evidence_path",
        "runtime_evidence_sha256",
        "evidence_semantic_sha256",
        "evidence",
    }
)
V034_NON_PEPGLAD_RUNTIME_FIELDS = {
    "PepMLM": frozenset(
        """conda_environment container_image effective_seed model_id model_revision
        model_weights_sha256 requested_seed sampling_strategy seed_control_status
        source_commit source_entrypoint_sha256 top_k""".split()
    ),
    "DiffPepBuilder": frozenset(
        """conda_environment container_image effective_seed filtered_receptor_sha256
        model_asset_sha256 requested_seed seed_control_status source_candidate_path
        source_commit source_entrypoint_sha256 target_context_chain
        target_context_mode target_context_path target_context_sha256""".split()
    ),
    "D-Flow / PeptideDesign": frozenset(
        """candidate_path candidate_sha256 checkpoint_path checkpoint_resolved_path
        checkpoint_sha256 containerized effective_seed execution_environment_declared
        execution_environment_type host_environment_path method python_base_prefix
        python_executable_path python_executable_realpath python_executable_sha256
        python_invocation_path python_prefix python_version requested_seed
        seed_control_status seed_patch_path seed_patch_sha256 source_checkout_path
        source_commit source_content_manifest_path source_content_manifest_sha256
        source_copy_mode source_entrypoint_patched_sha256 source_entrypoint_path
        source_entrypoint_prepatch_sha256 source_git_tracked_paths_clean
        source_tracked_file_count target_context_chain target_context_mode
        target_context_path target_context_sha256 x_mirror_applied""".split()
    ),
    "PepMirror": frozenset(
        """checkpoint_container_binding_verified checkpoint_container_path
        checkpoint_mount_mode checkpoint_path checkpoint_pin_verified
        checkpoint_revision checkpoint_sha256 checkpoint_verified_pre_run
        compose_config_command compose_config_output_sha256 compose_file_path
        compose_file_sha256 compose_file_verified_pre_run compose_image_tag
        compose_profile compose_service compose_service_verified effective_seed
        executed_source_manifest_path executed_source_manifest_sha256
        executed_source_manifest_verified_pre_run execution_environment_id
        execution_environment_verified execution_preflight_evidence_path
        execution_preflight_evidence_sha256 generate_py_post_path
        generate_py_post_sha256 generate_py_pre_path generate_py_pre_sha256
        image_id_observed_at_prepare image_id_observed_pre_run
        image_identity_stable_pre_run image_inspect_command
        image_inspect_execution_command image_inspect_execution_output_sha256
        image_inspect_execution_stage image_inspect_output_sha256
        image_inspect_stage image_repo_tags_observed_at_prepare method
        mirror_commands_in_pinned_container mirror_input_path mirror_input_sha256
        mirror_output_path mirror_output_sha256 mirror_pdb_py_post_path
        mirror_pdb_py_post_sha256 mirror_pdb_py_pre_path mirror_pdb_py_pre_sha256
        mirror_roundtrip_applied mirror_runtime_conda_environment
        mirror_runtime_scope mirrored_generated_path mirrored_generated_sha256
        mirrored_target_path mirrored_target_sha256 package_evidence_path
        package_evidence_sha256 provenance_capture_stage requested_seed
        seed_control_status seed_patch_path seed_patch_sha256 source_commit_command
        source_commit_expected source_commit_observed source_commit_verified
        source_git_checkout_clean source_git_paths source_git_paths_clean source_root
        source_status_command source_tracked_file_count target_input_verified_pre_run
        target_pdb_path target_pdb_sha256 target_preflight_verified""".split()
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        """alphafold_model_name alphafold_params_sha256 candidate_path
        candidate_sha256 container_image container_image_id cyclic_offset_applied
        cyclic_offset_type effective_seed requested_seed seed_control_status
        source_commit source_notebook_sha256 terminal_offset""".split()
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        """effective_seed mpnn_checkpoint_sha256 mpnn_container_image
        mpnn_container_image_id mpnn_designed_chain mpnn_fasta_path
        mpnn_fasta_sha256 mpnn_fixed_chains mpnn_record_type mpnn_seed
        mpnn_selected_record_id mpnn_source_commit mpnn_source_entrypoint_sha256
        requested_seed rf_backbone_path rf_backbone_sha256 rf_checkpoint_sha256
        rf_container_image rf_container_image_id rf_contig rf_cyclic
        rf_design_startnum rf_deterministic rf_hotspots rf_source_commit
        rf_source_entrypoint_sha256 rf_target_conditioned rf_trb_path
        rf_trb_semantic_extract rf_trb_semantic_parser rf_trb_semantic_sha256
        rf_trb_sha256 seed_control_status sequence_representation
        sequence_threaded_onto_backbone structure_representation""".split()
    ),
}
V034_RUNTIME_INT_FIELDS = {
    "PepMLM": frozenset({"requested_seed", "effective_seed", "top_k"}),
    "DiffPepBuilder": frozenset({"requested_seed", "effective_seed"}),
    "D-Flow / PeptideDesign": frozenset(
        {"requested_seed", "effective_seed", "source_tracked_file_count"}
    ),
    "PepMirror": frozenset(
        {"requested_seed", "effective_seed", "source_tracked_file_count"}
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        {"requested_seed", "effective_seed", "cyclic_offset_type", "terminal_offset"}
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {"requested_seed", "effective_seed", "rf_design_startnum", "mpnn_seed"}
    ),
}
V034_RUNTIME_BOOL_FIELDS = {
    "D-Flow / PeptideDesign": frozenset(
        {"containerized", "source_git_tracked_paths_clean", "x_mirror_applied"}
    ),
    "PepMirror": frozenset(
        """checkpoint_container_binding_verified checkpoint_pin_verified
        checkpoint_verified_pre_run compose_file_verified_pre_run
        compose_service_verified executed_source_manifest_verified_pre_run
        execution_environment_verified image_identity_stable_pre_run
        mirror_commands_in_pinned_container mirror_roundtrip_applied
        source_commit_verified source_git_checkout_clean source_git_paths_clean
        target_input_verified_pre_run target_preflight_verified""".split()
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        {"cyclic_offset_applied"}
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {
            "rf_cyclic",
            "rf_deterministic",
            "rf_target_conditioned",
            "sequence_threaded_onto_backbone",
        }
    ),
}
V034_RUNTIME_LIST_FIELDS = {
    "PepMirror": frozenset(
        """compose_config_command image_inspect_command
        image_inspect_execution_command image_repo_tags_observed_at_prepare
        source_commit_command source_git_paths source_status_command""".split()
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {"mpnn_fixed_chains", "rf_hotspots"}
    ),
}
V034_RF_TRB_FIELDS = frozenset(
    {
        "input_pdb",
        "contigs",
        "cyclic",
        "design_startnum",
        "deterministic",
        "hotspot_res",
        "num_designs",
        "sampled_mask",
    }
)
V034_EXPECTED_RUNTIME_PATH = {
    "PepMLM": "raw/runtime_evidence.json",
    "DiffPepBuilder": "raw/runtime_evidence.json",
    "PepGLAD": "raw/runtime_evidence.json",
    "D-Flow / PeptideDesign": "runtime_evidence.json",
    "PepMirror": "runtime_evidence.json",
    "AfCycDesign / ColabDesign cyclic peptide": "raw/runtime_evidence.json",
    "RFdiffusion + ProteinMPNN": "raw/runtime_evidence.json",
}
V034_EXPECTED_CANDIDATE_PATHS = {
    "PepMLM": ("", "raw/pepmlm_generated.csv"),
    "DiffPepBuilder": (
        "raw/diffpepbuilder_candidate.pdb",
        "raw/diffpepbuilder_candidate.pdb",
    ),
    "PepGLAD": (
        "raw/pepglad_candidate.pdb",
        "raw/pepglad_candidate.pdb",
    ),
    "D-Flow / PeptideDesign": (
        "raw/dflow_candidate.pdb",
        "raw/dflow_candidate.pdb",
    ),
    "PepMirror": (
        "raw/pepmirror_candidate.pdb",
        "raw/pepmirror_candidate.pdb",
    ),
    "AfCycDesign / ColabDesign cyclic peptide": (
        "raw/afcycdesign_candidate.pdb",
        "raw/afcycdesign_candidate.pdb",
    ),
    "RFdiffusion + ProteinMPNN": (
        "raw/rf/design.pdb",
        "raw/mpnn/design.fa",
    ),
}
V034_REPLAY_FILES = {
    "PepMLM": frozenset({"raw/pepmlm_generated.csv"}),
    "DiffPepBuilder": frozenset(
        {
            "raw/diffpepbuilder_candidate.pdb",
            "raw/diffpepbuilder_target_context.pdb",
        }
    ),
    "PepGLAD": frozenset(
        {"raw/pepglad_candidate.pdb", "raw/pepglad_summary.jsonl"}
    ),
    "D-Flow / PeptideDesign": frozenset(
        {"raw/dflow_candidate.pdb", "raw/dflow_target_context.pdb"}
    ),
    "PepMirror": frozenset(
        {
            "raw/mirror_input.pdb",
            "raw/mirrored_target.pdb",
            "raw/mirrored_generated.pdb",
            "raw/pepmirror_candidate.pdb",
            "package_evidence.json",
            "execution_preflight_evidence.json",
            "executed_source_manifest.json",
        }
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        {"raw/afcycdesign_candidate.pdb"}
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {"raw/rf/design.pdb", "raw/rf/design.trb", "raw/mpnn/design.fa"}
    ),
}
V034_FIXED_IDENTITIES: Mapping[str, Mapping[str, Mapping[str, Any]]] = {
    "PepMLM": {
        "manifest": {
            "source_commit": "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
            "model_revision": "898fca941a9057aebdd1a6164b5ee09a1a71780e",
            "environment_id": "pd-benchmark-methods-gpu:0.21/bench-pepmlm",
        },
        "evidence": {
            "source_commit": "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
            "source_entrypoint_sha256": (
                "2c1844028c459e8e96d756da795b620b4ccaa65b98dd62c6f904100f0dc1e49b"
            ),
            "model_id": "TianlaiChen/PepMLM-650M",
            "model_revision": "898fca941a9057aebdd1a6164b5ee09a1a71780e",
            "model_weights_sha256": (
                "8a3225bca1f9acd9f701ca2e46597c12bab92320e32b68f380ddf3b6d3b20770"
            ),
            "container_image": "pd-benchmark-methods-gpu:0.21",
            "conda_environment": "bench-pepmlm",
        },
    },
    "DiffPepBuilder": {
        "manifest": {
            "source_commit": "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
            "model_revision": "diffpepbuilder_v1.pth_external_manifest_v0.20",
            "environment_id": (
                "pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder"
            ),
        },
        "evidence": {
            "source_commit": "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
            "source_entrypoint_sha256": (
                "872868f48e3cf66f0ce159ada589ca2126a3b2ba98470ab3bbcb9ffc4481f7c6"
            ),
            "model_asset_sha256": {
                "diffpepbuilder_v1.pth": (
                    "dbc4283257d27e38a1ce90c9344063b046ab7161745ebed1fd98a4b0439b992a"
                ),
                "esm2_t33_650M_UR50D.pt": (
                    "ea9d0522b335a8778dea6535a65301f10208dece28cd5865482b0b1fc446168c"
                ),
                "esm2_t33_650M_UR50D-contact-regression.pt": (
                    "8ffe6edbd4173dc8d45c2cd5cb27d43aad77ec26b4c768200c58ae1f96693575"
                ),
            },
            "container_image": "pd-pyrosetta-methods-gpu:0.20",
            "conda_environment": "bench-diffpepbuilder",
        },
    },
    "PepGLAD": {
        "manifest": {
            "source_commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
            "model_revision": "codesign.ckpt_external_manifest_v0.21",
            "environment_id": "pd-benchmark-methods-gpu:0.21/bench-pepglad",
        },
        "evidence": {
            "source_commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
            "source_entrypoint_sha256": (
                "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
            ),
            "model_weights_sha256": (
                "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
            ),
            "container_image": "pd-benchmark-methods-gpu:0.21",
            "conda_environment": "bench-pepglad",
        },
    },
    "D-Flow / PeptideDesign": {
        "manifest": {
            "source_commit": "3e3e9f501ee16db318e9bf52643513636a07699a",
            "model_revision": (
                "sha256:95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17"
            ),
            "environment_id": "host:.venv/dflow-v023",
        },
        "evidence": {
            "source_commit": "3e3e9f501ee16db318e9bf52643513636a07699a",
            "source_entrypoint_prepatch_sha256": (
                "6be8b50b876cc94c8a212165d7327bd46c0e906d2c85fc6c2b03a66ff9e2cd9d"
            ),
            "source_entrypoint_patched_sha256": (
                "e55db330d920d0c189a5f539ede4344219177430619228418062d0c4b4e73cad"
            ),
            "seed_patch_sha256": (
                "e55db330d920d0c189a5f539ede4344219177430619228418062d0c4b4e73cad"
            ),
            "checkpoint_sha256": (
                "95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17"
            ),
            "python_executable_sha256": (
                "b1220424db191e57100891b277192f24cbae078324ffdf2242c68ce526590c3d"
            ),
            "execution_environment_type": "host_local_python_environment",
            "execution_environment_declared": "host:.venv/dflow-v023",
            "containerized": False,
        },
    },
    "PepMirror": {
        "manifest": {
            "source_commit": "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            "model_revision": (
                "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"
            ),
            "environment_id": (
                "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror"
            ),
        },
        "evidence": {
            "source_commit_expected": "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            "source_commit_observed": "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            "generate_py_pre_sha256": (
                "452ba18b29d9647785a2a4160fcaacd97e3769af4b58e5c532fb6b3394881459"
            ),
            "generate_py_post_sha256": (
                "32cb77ec34c9f10b2223c0bb19ef09e7fad3c7d9c2c0798a5ff9e72a699e5ecb"
            ),
            "seed_patch_sha256": (
                "32cb77ec34c9f10b2223c0bb19ef09e7fad3c7d9c2c0798a5ff9e72a699e5ecb"
            ),
            "mirror_pdb_py_pre_sha256": (
                "d8438835c3c26fbf3a1971c577be037e3bfe7114338d0c6e1fb32a2a4a11a233"
            ),
            "mirror_pdb_py_post_sha256": (
                "d8438835c3c26fbf3a1971c577be037e3bfe7114338d0c6e1fb32a2a4a11a233"
            ),
            "checkpoint_revision": (
                "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"
            ),
            "checkpoint_sha256": (
                "a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"
            ),
            "compose_file_sha256": (
                "e3a9e6e2b67d6eb13635238bf50aa519a30b70febc8cced57276c77b26831b5d"
            ),
            "compose_service": "pd-pyrosetta-methods-gpu-v021",
            "compose_image_tag": "pd-pyrosetta-methods-gpu:0.21",
            "execution_environment_id": (
                "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror"
            ),
            "mirror_runtime_conda_environment": "bench-pepmirror",
            "image_id_observed_at_prepare": (
                "sha256:6b0dd1b775ad1e3e91c618f4ab245db88d9964b20faa2331f4fe9870496d2992"
            ),
            "image_id_observed_pre_run": (
                "sha256:6b0dd1b775ad1e3e91c618f4ab245db88d9964b20faa2331f4fe9870496d2992"
            ),
        },
    },
    "AfCycDesign / ColabDesign cyclic peptide": {
        "manifest": {
            "source_commit": "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
            "model_revision": (
                "alphafold_model_1_ptm@sha256:"
                "5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84"
            ),
            "environment_id": (
                "pd-benchmark-methods-gpu:0.21/bench-colabdesign"
            ),
        },
        "evidence": {
            "source_commit": "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
            "source_notebook_sha256": (
                "ca3bd3cc14daa95e1529fd2d5c1ca18263d12341a75d2967715ec23720b129ed"
            ),
            "alphafold_model_name": "model_1_ptm",
            "alphafold_params_sha256": (
                "5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84"
            ),
            "container_image": "pd-benchmark-methods-gpu:0.21",
            "container_image_id": (
                "sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2"
            ),
        },
    },
    "RFdiffusion + ProteinMPNN": {
        "manifest": {
            "source_commit": (
                "RFdiffusion@2d0c003df46b9db41d119321f15403dec3716cd9;"
                "ProteinMPNN@8907e6671bfbfc92303b5f79c4b5e6ce47cdef57"
            ),
            "model_revision": "RFdiffusion_external_models;proteinmpnn_v_48_020.pt",
            "environment_id": (
                "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest"
            ),
        },
        "evidence": {
            "rf_source_commit": "2d0c003df46b9db41d119321f15403dec3716cd9",
            "rf_source_entrypoint_sha256": (
                "a22624d7d40d3d207d91e92163441da5a778c867ed6ea85aa546cc9fdbeb2105"
            ),
            "mpnn_source_commit": "8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
            "mpnn_source_entrypoint_sha256": (
                "61f2c519a7f73fa12da9eb90da97b97ec2f8d5f31d42605639c7600cbd321cbe"
            ),
            "rf_checkpoint_sha256": (
                "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc"
            ),
            "mpnn_checkpoint_sha256": (
                "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd"
            ),
            "rf_container_image": "pd-rfpeptide-gpu:fixed",
            "rf_container_image_id": (
                "sha256:95e2a19e4adf4b6e8bcdd1777b609bf717472a91643dc92f0ce6aaffbc5219f1"
            ),
            "mpnn_container_image": "pd-foundry-gpu:latest",
            "mpnn_container_image_id": (
                "sha256:23f8612f4537f90078d54a5ac9669df7a6d5f436a48740e5d2884cfe856a5be4"
            ),
        },
    },
}
V034_RF_MODEL_REVISION = "RFdiffusion_external_models;proteinmpnn_v_48_020.pt"
V034_RF_CHECKPOINT_SHA256 = (
    "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc"
)
V034_MPNN_CHECKPOINT_SHA256 = (
    "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd"
)
V034_PEPGLAD_RECOVERY_MODE = "instrumented_official_pipeline"
V034_PEPGLAD_SOURCE_COMMIT = "bad015ca50c312a89482adb5220c3d907f13df5c"
V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256 = (
    "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
)
V034_PEPGLAD_MODEL_WEIGHTS_SHA256 = (
    "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
)
V034_PEPGLAD_SEED42_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)
V034_PEPGLAD_TARGET_SHA256 = (
    "7086cf2bc4723ccbb4be5ff7f86a50d9db59bc307f4fbb0395a3c6ce3569827d"
)
V034_PEPGLAD_MODEL_REVISION = "codesign.ckpt_external_manifest_v0.21"
V034_PEPGLAD_CONTAINER_IMAGE = "pd-benchmark-methods-gpu:0.21"
V034_PEPGLAD_CONDA_ENVIRONMENT = "bench-pepglad"
V034_PEPGLAD_ENVIRONMENT_ID = (
    f"{V034_PEPGLAD_CONTAINER_IMAGE}/{V034_PEPGLAD_CONDA_ENVIRONMENT}"
)
V034_PEPGLAD_OBSERVER_SOURCE_SHA256 = (
    "a0a98420dd2fd5382479abe77526fb8fc206ffb1e69a8780912fb821dded0c61"
)
V034_PEPGLAD_OBSERVER_PATCH_SHA256 = (
    "cd9ec19f6605fd2b067824d4e02971b3a203e827b6398a4ffd1c68c64464311a"
)
V034_PEPGLAD_SEED_WRAPPER_SHA256 = (
    "6a9b4c9012205d27526e13dbccbd7d11c010eddc3c85acdb2796c2fa6668aaba"
)
V034_PEPGLAD_INSTRUMENTED_SOURCE_SHA256 = (
    "c3b127e39be1b335ff6046bb2435451acfc1b323839377033bf438ccd4a32954"
)
V034_PEPGLAD_DIAGNOSTIC_PRE_SHA256 = (
    "b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b"
)
V034_PEPGLAD_DIAGNOSTIC_POST_SHA256 = (
    "e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6"
)
V034_PEPGLAD_DIAGNOSTIC_PATCH_EVIDENCE_SHA256 = (
    "0342297b2094fe43fe2e7bf49d720e58eccdc3103b0a02e943c0861ca160a9aa"
)
V034_PEPGLAD_DIAGNOSTIC_RUNTIME_SHA256 = (
    "06d65928279969e0289038c2f0d1801459a698ceccf1cc87b6a0474a68eb3e85"
)
V034_PEPGLAD_DIAGNOSTIC_RUNTIME_SEMANTIC_SHA256 = (
    "e0db9a3380984fb8232ce36e5dae7bc4cea91612a0f6529c3e950dfe58e92fae"
)
V034_PEPGLAD_DIAGNOSTIC_SUMMARY_SHA256 = (
    "2f6fdc775c44e0ab525fbe26f9baf7d44760fcedc041a302a86d6529b634b76c"
)
V034_PEPGLAD_DIAGNOSTIC_ATTEMPT_DIR = (
    "/mnt/ssd4t/Pep_design/benchmark_runs/v0.34/pepglad/"
    "v034_pepglad_3eqs_seed42/attempt_003"
)
V034_PEPGLAD_LEGACY_SOURCE_CANDIDATE_PATH = "/data/attempt/work/codesign/3EQS_0.pdb"
V034_PEPGLAD_LEGACY_RUNTIME_FIELDS = frozenset(
    {
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "source_candidate_path",
        "container_image",
        "conda_environment",
    }
)
V034_PEPGLAD_INSTRUMENTED_RUNTIME_FIELDS = frozenset(
    {
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "recovery_mode",
        "source_candidate_path",
        "pre_relax_path",
        "pre_relax_sha256",
        "post_relax_path",
        "post_relax_sha256",
        "official_candidate_stage",
        "pre_relax_role",
        "binder_chain",
        "expected_chirality",
        "pre_relax_binder_chirality",
        "post_relax_binder_chirality",
        "first_observed_chirality_failure_stage",
        "baseline_replay_expected_sha256",
        "baseline_replay_observed_sha256",
        "baseline_replay_status",
        "observer_patch_evidence_path",
        "observer_patch_evidence_sha256",
        "observer_patch_path",
        "observer_patch_sha256",
        "observer_source_path",
        "observer_source_sha256",
        "seed_wrapper_path",
        "seed_wrapper_sha256",
        "instrumented_source_path",
        "source_entrypoint_prepatch_sha256",
        "source_entrypoint_instrumented_sha256",
        "target_input_sha256",
        "target_preflight_verified",
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "container_image",
        "conda_environment",
    }
)


def _v034_pepglad_runtime_schema_pass(evidence: Mapping[str, Any]) -> bool:
    keys = set(evidence)
    if keys == V034_PEPGLAD_LEGACY_RUNTIME_FIELDS:
        int_fields = {"requested_seed", "effective_seed"}
        return all(
            type(evidence.get(field)) is int for field in int_fields
        ) and all(
            type(evidence.get(field)) is str for field in keys - int_fields
        )
    if keys != V034_PEPGLAD_INSTRUMENTED_RUNTIME_FIELDS:
        return False
    chirality_fields = {
        "chain",
        "evaluable",
        "l_count",
        "d_count",
        "gly_count",
        "unknown_count",
        "status",
    }
    chirality_objects = (
        evidence.get("pre_relax_binder_chirality"),
        evidence.get("post_relax_binder_chirality"),
    )
    chirality_valid = all(
        isinstance(value, dict)
        and set(value) == chirality_fields
        and type(value.get("chain")) is str
        and type(value.get("status")) is str
        and all(
            type(value.get(field)) is int
            for field in chirality_fields - {"chain", "status"}
        )
        for value in chirality_objects
    )
    non_string_fields = {
        "requested_seed",
        "effective_seed",
        "target_preflight_verified",
        "pre_relax_binder_chirality",
        "post_relax_binder_chirality",
    }
    return all(
        (
            evidence.get("recovery_mode") == V034_PEPGLAD_RECOVERY_MODE,
            type(evidence.get("requested_seed")) is int,
            type(evidence.get("effective_seed")) is int,
            type(evidence.get("target_preflight_verified")) is bool,
            chirality_valid,
            all(
                type(evidence.get(field)) is str
                for field in keys - non_string_fields
            ),
        )
    )


def _v034_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(type(item) is str for item in value)


def _v034_rf_trb_schema_pass(value: Any) -> bool:
    return all(
        (
            isinstance(value, dict),
            set(value) == V034_RF_TRB_FIELDS if isinstance(value, dict) else False,
            type(value.get("input_pdb")) is str if isinstance(value, dict) else False,
            _v034_string_list(value.get("contigs")) if isinstance(value, dict) else False,
            type(value.get("cyclic")) is bool if isinstance(value, dict) else False,
            type(value.get("design_startnum")) is int
            if isinstance(value, dict)
            else False,
            type(value.get("deterministic")) is bool
            if isinstance(value, dict)
            else False,
            _v034_string_list(value.get("hotspot_res"))
            if isinstance(value, dict)
            else False,
            type(value.get("num_designs")) is int
            if isinstance(value, dict)
            else False,
            _v034_string_list(value.get("sampled_mask"))
            if isinstance(value, dict)
            else False,
        )
    )


def _v034_runtime_evidence_schema_pass(
    method: Any, evidence: Any
) -> bool:
    if not isinstance(method, str) or not isinstance(evidence, dict):
        return False
    if method == "PepGLAD":
        return _v034_pepglad_runtime_schema_pass(evidence)
    expected = V034_NON_PEPGLAD_RUNTIME_FIELDS.get(method)
    if expected is None or set(evidence) != expected:
        return False
    int_fields = V034_RUNTIME_INT_FIELDS.get(method, frozenset())
    bool_fields = V034_RUNTIME_BOOL_FIELDS.get(method, frozenset())
    list_fields = V034_RUNTIME_LIST_FIELDS.get(method, frozenset())
    dict_fields = (
        frozenset({"model_asset_sha256"})
        if method == "DiffPepBuilder"
        else frozenset({"rf_trb_semantic_extract"})
        if method == "RFdiffusion + ProteinMPNN"
        else frozenset()
    )
    if any(type(evidence.get(field)) is not int for field in int_fields):
        return False
    if any(type(evidence.get(field)) is not bool for field in bool_fields):
        return False
    if any(not _v034_string_list(evidence.get(field)) for field in list_fields):
        return False
    if any(
        type(evidence.get(field)) is not str
        for field in expected - int_fields - bool_fields - list_fields - dict_fields
    ):
        return False
    if method == "DiffPepBuilder":
        assets = evidence.get("model_asset_sha256")
        expected_assets = {
            "diffpepbuilder_v1.pth",
            "esm2_t33_650M_UR50D-contact-regression.pt",
            "esm2_t33_650M_UR50D.pt",
        }
        if not (
            isinstance(assets, dict)
            and set(assets) == expected_assets
            and all(type(value) is str for value in assets.values())
        ):
            return False
    if method == "RFdiffusion + ProteinMPNN" and not _v034_rf_trb_schema_pass(
        evidence.get("rf_trb_semantic_extract")
    ):
        return False
    return True


def _v034_runtime_record_schema_pass(record: Any) -> bool:
    return all(
        (
            isinstance(record, dict),
            set(record) == V034_RUNTIME_RECORD_FIELDS
            if isinstance(record, dict)
            else False,
            type(record.get("job_id")) is str if isinstance(record, dict) else False,
            type(record.get("method")) is str if isinstance(record, dict) else False,
            type(record.get("seed_stage")) is str
            if isinstance(record, dict)
            else False,
            type(record.get("random_seed")) is int
            if isinstance(record, dict)
            else False,
            type(record.get("attempt_id")) is str
            if isinstance(record, dict)
            else False,
            type(record.get("runtime_evidence_path")) is str
            if isinstance(record, dict)
            else False,
            _v034_sha256(record.get("runtime_evidence_sha256"))
            if isinstance(record, dict)
            else False,
            _v034_sha256(record.get("evidence_semantic_sha256"))
            if isinstance(record, dict)
            else False,
            _v034_runtime_evidence_schema_pass(
                record.get("method"), record.get("evidence")
            )
            if isinstance(record, dict)
            else False,
        )
    )


def _v034_runtime_payload_schema_pass(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != V034_RUNTIME_PAYLOAD_FIELDS:
        return False
    records = payload.get("records")
    return all(
        (
            payload.get("schema_version") == "v0.34",
            payload.get("evidence_boundary")
            == "bounded_connectivity_only_not_scoring_or_ranking",
            isinstance(records, list),
            all(_v034_runtime_record_schema_pass(record) for record in records or []),
        )
    )


def _v034_fixed_identity_pass(
    method: Any, manifest: Mapping[str, str], evidence: Any
) -> bool:
    contract = V034_FIXED_IDENTITIES.get(method) if isinstance(method, str) else None
    if contract is None or not isinstance(evidence, Mapping):
        return False
    manifest_contract = contract.get("manifest")
    evidence_contract = contract.get("evidence")
    if not isinstance(manifest_contract, Mapping) or not isinstance(
        evidence_contract, Mapping
    ):
        return False
    return all(
        manifest.get(field) == expected
        for field, expected in manifest_contract.items()
    ) and all(
        evidence.get(field) == expected
        for field, expected in evidence_contract.items()
    )


def _v034_sha256(value: Any, *, prefixed: bool = False) -> bool:
    pattern = r"sha256:[0-9a-f]{64}" if prefixed else r"[0-9a-f]{64}"
    return type(value) is str and re.fullmatch(pattern, value) is not None


def _v034_positive_runtime(value: Any) -> bool:
    try:
        runtime = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(runtime) and runtime > 0


def _v034_positive_int(value: Any) -> bool:
    try:
        return int(str(value)) > 0
    except (TypeError, ValueError):
        return False


def _v034_stat_fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_mode,
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _v034_stable_attempt_file(
    attempt_dir: Any, relative_path: Any, *, allow_empty: bool = False
) -> tuple[Path, bytes, str, tuple[int, ...]] | None:
    if not isinstance(attempt_dir, str) or not isinstance(relative_path, str):
        return None
    if not attempt_dir or not relative_path or "\\" in relative_path:
        return None
    root = Path(attempt_dir)
    windows_root = PureWindowsPath(attempt_dir)
    relative = PurePosixPath(relative_path)
    if (
        not root.is_absolute()
        or windows_root.drive
        or relative.is_absolute()
        or relative.as_posix() != relative_path
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        return None

    absolute_root = Path(os.path.abspath(root))
    try:
        root_lstat = os.lstat(root)
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if (
        absolute_root != root
        or resolved_root != absolute_root
        or stat.S_ISLNK(root_lstat.st_mode)
        or not stat.S_ISDIR(root_lstat.st_mode)
    ):
        return None

    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    directory_fds: list[int] = []
    directory_stats: list[os.stat_result] = []
    file_fd: int | None = None
    try:
        root_fd = os.open(root, directory_flags)
        directory_fds.append(root_fd)
        opened_root_stat = os.fstat(root_fd)
        directory_stats.append(opened_root_stat)
        if not stat.S_ISDIR(opened_root_stat.st_mode) or _v034_stat_fingerprint(
            root_lstat
        ) != _v034_stat_fingerprint(opened_root_stat):
            return None

        current_fd = root_fd
        for part in relative.parts[:-1]:
            child_fd = os.open(part, directory_flags, dir_fd=current_fd)
            child_stat = os.fstat(child_fd)
            if not stat.S_ISDIR(child_stat.st_mode):
                os.close(child_fd)
                return None
            directory_fds.append(child_fd)
            directory_stats.append(child_stat)
            current_fd = child_fd

        final_name = relative.parts[-1]
        file_fd = os.open(final_name, file_flags, dir_fd=current_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or (
            before.st_size <= 0 and not allow_empty
        ):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(file_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(file_fd)
        current_file = os.stat(final_name, dir_fd=current_fd, follow_symlinks=False)
        fingerprint = _v034_stat_fingerprint(before)
        if not all(
            fingerprint == _v034_stat_fingerprint(value)
            for value in (after, current_file)
        ):
            return None

        current_root = os.lstat(root)
        if _v034_stat_fingerprint(current_root) != _v034_stat_fingerprint(
            directory_stats[0]
        ):
            return None
        for index in range(1, len(directory_fds)):
            current_directory = os.stat(
                relative.parts[index - 1],
                dir_fd=directory_fds[index - 1],
                follow_symlinks=False,
            )
            if _v034_stat_fingerprint(current_directory) != _v034_stat_fingerprint(
                directory_stats[index]
            ):
                return None

        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            return None
        return (
            absolute_root.joinpath(*relative.parts),
            payload,
            hashlib.sha256(payload).hexdigest(),
            fingerprint,
        )
    except (OSError, ValueError):
        return None
    finally:
        if file_fd is not None:
            try:
                os.close(file_fd)
            except OSError:
                pass
        for directory_fd in reversed(directory_fds):
            try:
                os.close(directory_fd)
            except OSError:
                pass


def _v034_json_object(payload: bytes) -> dict[str, Any] | None:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_nonfinite(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        decoded = payload.decode("utf-8")
        parsed = json.loads(
            decoded,
            object_pairs_hook=unique_object,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _v034_central_inversion_geometry_pass(qc: Mapping[str, str], prefix: str) -> bool:
    try:
        atom_count = int(qc.get(f"{prefix}_atom_count", ""))
        max_residual = float(qc.get(f"{prefix}_central_inversion_max_residual", ""))
        tolerance = float(qc.get(f"{prefix}_central_inversion_tolerance", ""))
    except (TypeError, ValueError):
        return False
    return all(
        (
            atom_count > 0,
            math.isfinite(max_residual),
            max_residual >= 0,
            math.isfinite(tolerance),
            tolerance >= 0,
            max_residual <= tolerance,
        )
    )


def _unique_rows(
    rows: list[dict[str, str]], key: str
) -> tuple[dict[str, dict[str, str]], tuple[str, ...]]:
    indexed: dict[str, dict[str, str]] = {}
    duplicates: set[str] = set()
    for row in rows:
        value = row.get(key, "")
        if not value or value in indexed:
            duplicates.add(value or "<empty>")
        else:
            indexed[value] = row
    return indexed, tuple(sorted(duplicates))


def _v034_required_qc_checks_pass(
    job: Mapping[str, str], qc: Mapping[str, str]
) -> bool:
    required_pass = {
        "file_status",
        "length_status",
        "parse_status",
        "seed_status",
        "method_contract_status",
    }
    if job.get("expected_binder_chain") != "not_applicable":
        required_pass.update({"chain_status", "target_binding_status"})
        if job.get("method") == "RFdiffusion + ProteinMPNN":
            required_pass.add("backbone_to_fasta_handoff_status")
        else:
            required_pass.add("sequence_structure_status")
    if job.get("chirality_check_mode") == "geometry":
        required_pass.add("chirality_status")
    if job.get("cyclic_check_mode") != "not_applicable":
        required_pass.add("cyclic_status")
    if job.get("method") == "RFdiffusion + ProteinMPNN":
        required_pass.add("handoff_status")
    if job.get("method") == "PepMirror":
        required_pass.update(
            {
                "mirror_target_atom_identity_status",
                "mirror_target_central_inversion_status",
                "mirror_output_atom_identity_status",
                "mirror_output_central_inversion_status",
            }
        )
    rf_representation_valid = (
        job.get("method") != "RFdiffusion + ProteinMPNN"
        or qc.get("sequence_structure_status") == "not_applicable"
    )
    pepmirror_geometry_valid = job.get("method") != "PepMirror" or all(
        _v034_central_inversion_geometry_pass(qc, prefix)
        for prefix in ("mirror_target", "mirror_output")
    )
    return (
        all(qc.get(field) == "pass" for field in required_pass)
        and qc.get("noncanonical_status") in {"pass", "warn"}
        and rf_representation_valid
        and pepmirror_geometry_valid
    )


def _v034_exact_regular_path(value: Any, expected: Path) -> bool:
    if not isinstance(value, str) or not value:
        return False
    candidate = Path(value)
    if not candidate.is_absolute() or PureWindowsPath(value).drive:
        return False
    if Path(os.path.abspath(candidate)) != candidate or candidate != expected:
        return False
    try:
        observed = os.lstat(candidate)
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    return all(
        (
            resolved == expected,
            stat.S_ISREG(observed.st_mode),
            not stat.S_ISLNK(observed.st_mode),
            observed.st_size > 0,
        )
    )


def _v034_pepglad_instrumented_provenance_pass(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
    provenance: Mapping[str, Any],
) -> bool:
    evidence = provenance.get("evidence")
    if not isinstance(evidence, Mapping):
        return False
    recovery_mode = evidence.get("recovery_mode")
    if not _v034_pepglad_runtime_schema_pass(evidence):
        return False
    if recovery_mode is None:
        attempt_dir = execution.get("attempt_dir", "")
        official_candidate = _v034_stable_attempt_file(
            attempt_dir, "raw/pepglad_candidate.pdb"
        )
        if official_candidate is None:
            return False
        candidate_path, candidate_payload, candidate_sha256, _ = official_candidate
        stable_candidate = _v034_stable_attempt_file(
            attempt_dir, "raw/pepglad_candidate.pdb"
        )
        return all(
            (
                job.get("random_seed") == "42",
                job.get("seed_stage") == "primary",
                evidence.get("source_candidate_path")
                == V034_PEPGLAD_LEGACY_SOURCE_CANDIDATE_PATH,
                candidate_sha256 == V034_PEPGLAD_SEED42_BASELINE_SHA256,
                qc.get("file_sha256") == candidate_sha256,
                qc.get("file_size_bytes") == str(len(candidate_payload)),
                _v034_exact_regular_path(
                    candidate.get("structure_path"), candidate_path
                ),
                _v034_exact_regular_path(
                    candidate.get("source_output_path"), candidate_path
                ),
                stable_candidate is not None,
                (
                    stable_candidate[1:] == official_candidate[1:]
                    if stable_candidate is not None
                    else False
                ),
            )
        )

    attempt_dir = execution.get("attempt_dir", "")
    runtime_relative = provenance.get("runtime_evidence_path")
    if runtime_relative != "raw/runtime_evidence.json":
        return False
    runtime_file = _v034_stable_attempt_file(attempt_dir, runtime_relative)
    if runtime_file is None:
        return False
    _, runtime_payload, runtime_sha256, _ = runtime_file
    runtime_object = _v034_json_object(runtime_payload)
    if not all(
        (
            runtime_object is not None,
            runtime_object == dict(evidence),
            runtime_sha256 == provenance.get("runtime_evidence_sha256"),
        )
    ):
        return False

    expected_paths = {
        "source_candidate_path": "work/codesign/3EQS_0.pdb",
        "pre_relax_path": "raw/pepglad_pre_relax.pdb",
        "post_relax_path": "raw/pepglad_candidate.pdb",
        "observer_patch_evidence_path": "observer_patch_evidence.json",
        "observer_patch_path": "pepglad_instrument_source.py",
        "observer_source_path": "pepglad_observer.py",
        "seed_wrapper_path": "pepglad_seeded_entry.py",
        "instrumented_source_path": "work/api/run.py",
    }
    files: dict[str, tuple[Path, bytes, str, tuple[int, ...]]] = {}
    for field, expected_relative in expected_paths.items():
        if evidence.get(field) != expected_relative:
            return False
        observed = _v034_stable_attempt_file(attempt_dir, expected_relative)
        if observed is None:
            return False
        files[field] = observed

    source_candidate = files["source_candidate_path"]
    pre_relax = files["pre_relax_path"]
    post_relax = files["post_relax_path"]
    patch_evidence = files["observer_patch_evidence_path"]
    observer_patch = files["observer_patch_path"]
    observer_source = files["observer_source_path"]
    seed_wrapper = files["seed_wrapper_path"]
    instrumented_source = files["instrumented_source_path"]
    if not all(
        (
            source_candidate[2] == post_relax[2],
            evidence.get("pre_relax_sha256") == pre_relax[2],
            evidence.get("post_relax_sha256") == post_relax[2],
            evidence.get("observer_patch_evidence_sha256") == patch_evidence[2],
            evidence.get("observer_patch_sha256")
            == observer_patch[2]
            == V034_PEPGLAD_OBSERVER_PATCH_SHA256,
            evidence.get("observer_source_sha256")
            == observer_source[2]
            == V034_PEPGLAD_OBSERVER_SOURCE_SHA256,
            evidence.get("seed_wrapper_sha256")
            == seed_wrapper[2]
            == V034_PEPGLAD_SEED_WRAPPER_SHA256,
            evidence.get("source_entrypoint_instrumented_sha256")
            == instrumented_source[2]
            == V034_PEPGLAD_INSTRUMENTED_SOURCE_SHA256,
            qc.get("file_sha256") == post_relax[2],
            qc.get("file_size_bytes") == str(len(post_relax[1])),
            _v034_exact_regular_path(candidate.get("structure_path"), post_relax[0]),
            _v034_exact_regular_path(
                candidate.get("source_output_path"), post_relax[0]
            ),
            post_relax[0] != pre_relax[0],
        )
    ):
        return False

    patch_object = _v034_json_object(patch_evidence[1])
    expected_patch = {
        "observer_injection_status": "applied",
        "observer_patch_path": evidence.get("observer_patch_path"),
        "observer_patch_sha256": V034_PEPGLAD_OBSERVER_PATCH_SHA256,
        "observer_source_path": evidence.get("observer_source_path"),
        "observer_source_sha256": V034_PEPGLAD_OBSERVER_SOURCE_SHA256,
        "source_entrypoint_path": evidence.get("instrumented_source_path"),
        "source_entrypoint_prepatch_sha256": (V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256),
        "source_entrypoint_instrumented_sha256": (
            V034_PEPGLAD_INSTRUMENTED_SOURCE_SHA256
        ),
        "source_copy_mode": "attempt_local_copy",
        "target_input_path": "/data/input/3EQS.pdb",
        "target_input_sha256": V034_PEPGLAD_TARGET_SHA256,
        "target_preflight_verified": True,
    }
    if patch_object != expected_patch:
        return False

    binder_chain = job.get("expected_binder_chain")
    expected_chirality = job.get("chirality")
    if not isinstance(binder_chain, str) or expected_chirality not in {"L", "D"}:
        return False
    try:
        pre_stats = chirality_stats_from_pdb_bytes(pre_relax[1], binder_chain)
        post_stats = chirality_stats_from_pdb_bytes(post_relax[1], binder_chain)
    except (TypeError, UnicodeError, ValueError, KeyError):
        return False
    stable_pre = _v034_stable_attempt_file(
        attempt_dir, expected_paths["pre_relax_path"]
    )
    stable_post = _v034_stable_attempt_file(
        attempt_dir, expected_paths["post_relax_path"]
    )
    if (
        stable_pre is None
        or stable_post is None
        or stable_pre[1:] != pre_relax[1:]
        or stable_post[1:] != post_relax[1:]
    ):
        return False
    expected_pre_report = {"chain": binder_chain, **pre_stats}
    expected_post_report = {"chain": binder_chain, **post_stats}
    pre_report = evidence.get("pre_relax_binder_chirality")
    post_report = evidence.get("post_relax_binder_chirality")
    if not all(
        (
            pre_stats.get("status") == "pass",
            post_stats.get("status") == "pass",
            isinstance(pre_report, Mapping),
            isinstance(post_report, Mapping),
            (
                dict(pre_report) == expected_pre_report
                if isinstance(pre_report, Mapping)
                else False
            ),
            (
                dict(post_report) == expected_post_report
                if isinstance(post_report, Mapping)
                else False
            ),
        )
    ):
        return False

    expected_count_key = "l_count" if expected_chirality == "L" else "d_count"

    def chirality_passes(stats: Mapping[str, Any]) -> bool:
        return all(
            (
                stats.get("status") == "pass",
                isinstance(stats.get("evaluable"), int),
                stats.get("evaluable", 0) > 0,
                stats.get(expected_count_key) == stats.get("evaluable"),
            )
        )

    if not chirality_passes(pre_stats):
        first_failure_stage = "pre_openmm_snapshot"
    elif not chirality_passes(post_stats):
        first_failure_stage = "post_openmm_relaxation"
    else:
        first_failure_stage = "none_observed"
    post_chirality_status = "pass" if chirality_passes(post_stats) else "fail"
    qc_counts_match = all(
        qc.get(f"chirality_{field}") == str(post_stats.get(field))
        for field in (
            "evaluable",
            "l_count",
            "d_count",
            "gly_count",
            "unknown_count",
        )
    )
    if not all(
        (
            qc_counts_match,
            qc.get("chirality_status") == post_chirality_status,
            evidence.get("first_observed_chirality_failure_stage")
            == first_failure_stage,
        )
    ):
        return False

    try:
        expected_seed = int(job.get("random_seed", ""))
    except (TypeError, ValueError):
        return False
    if expected_seed == 42:
        baseline_valid = all(
            (
                job.get("seed_stage") == "primary",
                evidence.get("baseline_replay_expected_sha256")
                == V034_PEPGLAD_SEED42_BASELINE_SHA256,
                evidence.get("baseline_replay_observed_sha256") == post_relax[2],
                post_relax[2] == V034_PEPGLAD_SEED42_BASELINE_SHA256,
                evidence.get("baseline_replay_status") == "match",
            )
        )
    elif expected_seed == 43:
        baseline_valid = all(
            (
                job.get("seed_stage") == "extension",
                evidence.get("baseline_replay_expected_sha256") == "",
                evidence.get("baseline_replay_observed_sha256") == post_relax[2],
                evidence.get("baseline_replay_status") == "not_applicable",
            )
        )
    else:
        baseline_valid = False

    contract_valid = all(
        (
            baseline_valid,
            job.get("target_id") == "mdm2_p53_3eqs_fixture",
            job.get("target_pdb") == "3EQS",
            job.get("target_pdb_path") == "data/dflow/pdbs/3EQS.pdb",
            job.get("target_pdb_sha256") == V034_PEPGLAD_TARGET_SHA256,
            job.get("expected_target_chain") == "A",
            binder_chain == "B",
            expected_chirality == "L",
            evidence.get("official_candidate_stage") == "post_openmm_relaxation",
            evidence.get("pre_relax_role") == "diagnostic_evidence_only",
            evidence.get("binder_chain") == binder_chain,
            evidence.get("expected_chirality") == expected_chirality,
            evidence.get("target_input_sha256") == V034_PEPGLAD_TARGET_SHA256,
            evidence.get("target_preflight_verified") is True,
            evidence.get("source_entrypoint_prepatch_sha256")
            == V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            evidence.get("source_commit") == V034_PEPGLAD_SOURCE_COMMIT,
            evidence.get("source_entrypoint_sha256")
            == V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            evidence.get("model_weights_sha256") == V034_PEPGLAD_MODEL_WEIGHTS_SHA256,
            evidence.get("container_image") == V034_PEPGLAD_CONTAINER_IMAGE,
            evidence.get("conda_environment") == V034_PEPGLAD_CONDA_ENVIRONMENT,
        )
    )
    if not contract_valid:
        return False

    stable_runtime = _v034_stable_attempt_file(attempt_dir, runtime_relative)
    if stable_runtime is None or stable_runtime[1:] != runtime_file[1:]:
        return False
    for field, expected_relative in expected_paths.items():
        stable_file = _v034_stable_attempt_file(attempt_dir, expected_relative)
        if stable_file is None or stable_file[1:] != files[field][1:]:
            return False
    return True


def _v034_runtime_provenance_pass(
    job: Mapping[str, str],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
    provenance: Mapping[str, Any],
) -> bool:
    if not _v034_runtime_record_schema_pass(provenance):
        return False
    evidence = provenance.get("evidence")
    if not isinstance(evidence, dict):
        return False
    try:
        semantic_payload = json.dumps(
            evidence,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    semantic_sha256 = hashlib.sha256(semantic_payload).hexdigest()
    try:
        record_seed = int(provenance.get("random_seed", -1))
    except (TypeError, ValueError):
        return False
    expected_seed = int(job["random_seed"])
    common = all(
        (
            provenance.get("job_id") == job.get("job_id"),
            provenance.get("method") == job.get("method"),
            provenance.get("seed_stage") == job.get("seed_stage"),
            record_seed == expected_seed,
            re.fullmatch(r"attempt_[0-9]{3}", str(provenance.get("attempt_id", "")))
            is not None,
            provenance.get("runtime_evidence_path")
            in {"runtime_evidence.json", "raw/runtime_evidence.json"},
            _v034_sha256(provenance.get("runtime_evidence_sha256")),
            provenance.get("evidence_semantic_sha256") == semantic_sha256,
            evidence.get("requested_seed") == expected_seed,
            evidence.get("effective_seed") == expected_seed,
            evidence.get("seed_control_status") == "honored",
        )
    )
    if not common:
        return False

    method = job.get("method")
    file_sha = qc.get("file_sha256", "")
    if method == "PepMLM":
        return all(
            (
                _v034_sha256(evidence.get("source_entrypoint_sha256")),
                _v034_sha256(evidence.get("model_weights_sha256")),
                bool(evidence.get("source_commit")),
                bool(evidence.get("model_revision")),
                bool(evidence.get("container_image")),
                evidence.get("sampling_strategy") == "top_k_categorical",
                isinstance(evidence.get("top_k"), int),
                evidence.get("top_k", 0) > 0,
            )
        )
    if method == "DiffPepBuilder":
        model_assets = evidence.get("model_asset_sha256")
        expected_assets = {
            "diffpepbuilder_v1.pth",
            "esm2_t33_650M_UR50D-contact-regression.pt",
            "esm2_t33_650M_UR50D.pt",
        }
        return all(
            (
                _v034_sha256(evidence.get("source_entrypoint_sha256")),
                isinstance(model_assets, Mapping),
                (
                    set(model_assets) == expected_assets
                    if isinstance(model_assets, Mapping)
                    else False
                ),
                (
                    all(_v034_sha256(value) for value in model_assets.values())
                    if isinstance(model_assets, Mapping)
                    else False
                ),
                _v034_sha256(evidence.get("target_context_sha256")),
                bool(evidence.get("source_commit")),
                bool(evidence.get("container_image")),
            )
        )
    if method == "PepGLAD":
        recovery_mode = evidence.get("recovery_mode")
        legacy_contract = recovery_mode is not None or all(
            (
                evidence.get("source_candidate_path")
                == V034_PEPGLAD_LEGACY_SOURCE_CANDIDATE_PATH,
                evidence.get("conda_environment") == V034_PEPGLAD_CONDA_ENVIRONMENT,
            )
        )
        return all(
            (
                _v034_pepglad_runtime_schema_pass(evidence),
                legacy_contract,
                evidence.get("source_entrypoint_sha256")
                == V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
                evidence.get("model_weights_sha256")
                == V034_PEPGLAD_MODEL_WEIGHTS_SHA256,
                evidence.get("source_commit") == V034_PEPGLAD_SOURCE_COMMIT,
                evidence.get("container_image") == V034_PEPGLAD_CONTAINER_IMAGE,
            )
        )
    if method == "D-Flow / PeptideDesign":
        return all(
            (
                evidence.get("x_mirror_applied") is True,
                _v034_sha256(evidence.get("seed_patch_sha256")),
                _v034_sha256(evidence.get("candidate_sha256")),
                evidence.get("candidate_sha256") == file_sha,
                _v034_sha256(evidence.get("target_context_sha256")),
                re.fullmatch(r"[0-9a-f]{40}", str(evidence.get("source_commit", "")))
                is not None,
                evidence.get("source_git_tracked_paths_clean") is True,
                evidence.get("source_copy_mode") == "git_tracked_files_only",
                _v034_sha256(evidence.get("source_entrypoint_prepatch_sha256")),
                _v034_sha256(evidence.get("source_entrypoint_patched_sha256")),
                _v034_sha256(evidence.get("source_content_manifest_sha256")),
                isinstance(evidence.get("source_tracked_file_count"), int),
                evidence.get("source_tracked_file_count", 0) > 0,
                _v034_sha256(evidence.get("checkpoint_sha256")),
                evidence.get("execution_environment_type")
                == "host_local_python_environment",
                evidence.get("execution_environment_declared")
                == "host:.venv/dflow-v023",
                evidence.get("containerized") is False,
                _v034_sha256(evidence.get("python_executable_sha256")),
                bool(evidence.get("python_version")),
            )
        )
    if method == "PepMirror":
        hashes = (
            evidence.get("mirror_input_sha256"),
            evidence.get("mirrored_target_sha256"),
            evidence.get("mirrored_generated_sha256"),
            evidence.get("mirror_output_sha256"),
        )
        return all(
            (
                evidence.get("mirror_roundtrip_applied") is True,
                all(_v034_sha256(value) for value in hashes),
                evidence.get("mirror_input_sha256") == job.get("target_pdb_sha256"),
                evidence.get("mirror_input_sha256")
                != evidence.get("mirrored_target_sha256"),
                evidence.get("mirror_output_sha256") == file_sha,
                evidence.get("mirror_output_path") == candidate.get("structure_path"),
                candidate.get("structure_path") == candidate.get("source_output_path"),
                _v034_sha256(evidence.get("seed_patch_sha256")),
                _v034_sha256(evidence.get("checkpoint_revision"), prefixed=True),
                re.fullmatch(
                    r"[0-9a-f]{40}", str(evidence.get("source_commit_observed", ""))
                )
                is not None,
                evidence.get("source_commit_expected")
                == evidence.get("source_commit_observed"),
                evidence.get("source_commit_verified") is True,
                evidence.get("source_git_paths_clean") is True,
                evidence.get("source_git_checkout_clean") is True,
                isinstance(evidence.get("source_tracked_file_count"), int),
                evidence.get("source_tracked_file_count", 0) > 0,
                _v034_sha256(evidence.get("generate_py_pre_sha256")),
                _v034_sha256(evidence.get("generate_py_post_sha256")),
                _v034_sha256(evidence.get("mirror_pdb_py_pre_sha256")),
                evidence.get("mirror_pdb_py_pre_sha256")
                == evidence.get("mirror_pdb_py_post_sha256"),
                _v034_sha256(evidence.get("executed_source_manifest_sha256")),
                _v034_sha256(evidence.get("checkpoint_sha256")),
                evidence.get("checkpoint_revision")
                == f"sha256:{evidence.get('checkpoint_sha256', '')}",
                evidence.get("checkpoint_pin_verified") is True,
                evidence.get("checkpoint_container_path")
                == (
                    "/data/benchmark_models/pepmirror/"
                    "pepmirror_commutator_both_v1.ckpt"
                ),
                evidence.get("checkpoint_mount_mode") == "explicit_read_only_file_bind",
                evidence.get("checkpoint_container_binding_verified") is True,
                evidence.get("checkpoint_verified_pre_run") is True,
                _v034_sha256(evidence.get("compose_file_sha256")),
                evidence.get("compose_file_verified_pre_run") is True,
                evidence.get("compose_service") == "pd-pyrosetta-methods-gpu-v021",
                evidence.get("compose_service_verified") is True,
                evidence.get("compose_image_tag") == "pd-pyrosetta-methods-gpu:0.21",
                evidence.get("execution_environment_id")
                == "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror",
                evidence.get("execution_environment_verified") is True,
                _v034_sha256(
                    evidence.get("image_id_observed_at_prepare"), prefixed=True
                ),
                evidence.get("image_id_observed_pre_run")
                == evidence.get("image_id_observed_at_prepare"),
                evidence.get("image_identity_stable_pre_run") is True,
                evidence.get("executed_source_manifest_verified_pre_run") is True,
                evidence.get("target_input_verified_pre_run") is True,
                evidence.get("target_preflight_verified") is True,
                evidence.get("mirror_runtime_scope")
                == "pinned_compose_conda_environment",
                evidence.get("mirror_runtime_conda_environment") == "bench-pepmirror",
                evidence.get("mirror_commands_in_pinned_container") is True,
                _v034_sha256(evidence.get("package_evidence_sha256")),
                _v034_sha256(evidence.get("execution_preflight_evidence_sha256")),
            )
        )
    if method == "AfCycDesign / ColabDesign cyclic peptide":
        return all(
            (
                evidence.get("cyclic_offset_applied") is True,
                evidence.get("cyclic_offset_type") == 2,
                evidence.get("candidate_sha256") == file_sha,
                _v034_sha256(evidence.get("source_notebook_sha256")),
                _v034_sha256(evidence.get("alphafold_params_sha256")),
                _v034_sha256(evidence.get("container_image_id"), prefixed=True),
            )
        )
    if method == "RFdiffusion + ProteinMPNN":
        digest_fields = (
            "rf_backbone_sha256",
            "rf_trb_sha256",
            "mpnn_fasta_sha256",
            "rf_checkpoint_sha256",
            "mpnn_checkpoint_sha256",
            "rf_source_entrypoint_sha256",
            "mpnn_source_entrypoint_sha256",
        )
        trb_semantics = evidence.get("rf_trb_semantic_extract")
        trb_semantic_sha256 = (
            hashlib.sha256(
                json.dumps(
                    trb_semantics,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            if isinstance(trb_semantics, Mapping)
            else ""
        )
        sequence_length = len(candidate.get("sequence", ""))
        return all(
            (
                all(_v034_sha256(evidence.get(field)) for field in digest_fields),
                all(
                    re.fullmatch(r"[0-9a-f]{40}", str(evidence.get(field, "")))
                    is not None
                    for field in ("rf_source_commit", "mpnn_source_commit")
                ),
                bool(evidence.get("rf_container_image")),
                bool(evidence.get("mpnn_container_image")),
                evidence.get("rf_backbone_path") == candidate.get("structure_path"),
                evidence.get("mpnn_fasta_path") == candidate.get("source_output_path"),
                evidence.get("rf_backbone_sha256") == file_sha,
                _v034_sha256(evidence.get("rf_container_image_id"), prefixed=True),
                _v034_sha256(evidence.get("mpnn_container_image_id"), prefixed=True),
                evidence.get("rf_contig") == "[A3-117/0 70-100]",
                evidence.get("rf_hotspots")
                == ["A48", "A50", "A51", "A52", "A62", "A65"],
                evidence.get("rf_target_conditioned") is True,
                evidence.get("rf_deterministic") is True,
                evidence.get("rf_cyclic") is False,
                evidence.get("mpnn_fixed_chains") == ["A"],
                evidence.get("mpnn_designed_chain") == "B",
                evidence.get("mpnn_record_type") == "generated_sample",
                evidence.get("mpnn_seed") == expected_seed,
                evidence.get("structure_representation") == "unthreaded_rf_backbone",
                evidence.get("sequence_representation")
                == "proteinmpnn_generated_fasta",
                evidence.get("sequence_threaded_onto_backbone") is False,
                evidence.get("rf_trb_semantic_parser") == "pickletools_literal_scan_v1",
                evidence.get("rf_trb_semantic_sha256") == trb_semantic_sha256,
                isinstance(trb_semantics, Mapping),
                (
                    trb_semantics.get("input_pdb") == "/data/input/7zkr_GABARAP.pdb"
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
                (
                    trb_semantics.get("num_designs") == 1
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
                (
                    trb_semantics.get("design_startnum") == expected_seed
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
                (
                    trb_semantics.get("deterministic") is True
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
                (
                    trb_semantics.get("cyclic") is False
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
                (
                    trb_semantics.get("contigs") == ["A3-117/0 70-100"]
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
                (
                    trb_semantics.get("hotspot_res")
                    == ["A48", "A50", "A51", "A52", "A62", "A65"]
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
                (
                    trb_semantics.get("sampled_mask")
                    == ["A3-117/0", f"{sequence_length}-{sequence_length}"]
                    if isinstance(trb_semantics, Mapping)
                    else False
                ),
            )
        )
    return False


def _v034_one_csv_object(payload: bytes) -> dict[str, str] | None:
    try:
        decoded = payload.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        if (
            reader.fieldnames is None
            or len(reader.fieldnames) != len(set(reader.fieldnames))
            or any(not field for field in reader.fieldnames)
        ):
            return None
        rows = list(reader)
    except (UnicodeError, csv.Error):
        return None
    return rows[0] if len(rows) == 1 else None


def _v034_replay_file_set(
    method: str, attempt_dir: str
) -> set[str] | None:
    files = set(V034_REPLAY_FILES.get(method, ()))
    runtime_relative = V034_EXPECTED_RUNTIME_PATH.get(method)
    if runtime_relative is None:
        return None
    files.update(
        {
            runtime_relative,
            "run_result.json",
            "method_output_manifest.csv",
            "candidate_outputs.csv",
            "candidate_qc.csv",
            "command.sh",
            "stdout.log",
            "stderr.log",
        }
    )
    if method != "PepMirror":
        return files
    manifest_file = _v034_stable_attempt_file(
        attempt_dir, "executed_source_manifest.json"
    )
    if manifest_file is None:
        return None
    manifest = _v034_json_object(manifest_file[1])
    entries = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(entries, dict) or not all(
        isinstance(path, str) and isinstance(digest, str)
        for path, digest in entries.items()
    ):
        return None
    for relative_text in entries:
        relative = PurePosixPath(relative_text)
        if (
            relative.is_absolute()
            or relative.as_posix() != relative_text
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            return None
        files.add(PurePosixPath("work/PepMirror", relative).as_posix())
    return files


def _v034_raw_replay_pass(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    manifest: Mapping[str, str],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
    run: Mapping[str, str],
    provenance: Mapping[str, Any],
) -> bool:
    method = job.get("method", "")
    module_name = V034_ADAPTER_MODULES.get(method)
    expected_paths = V034_EXPECTED_CANDIDATE_PATHS.get(method)
    runtime_relative = V034_EXPECTED_RUNTIME_PATH.get(method)
    attempt_dir_raw = execution.get("attempt_dir", "")
    attempt_dir = Path(attempt_dir_raw)
    if not all(
        (
            module_name,
            expected_paths,
            runtime_relative,
            isinstance(attempt_dir_raw, str),
            attempt_dir.is_absolute(),
            str(attempt_dir) == attempt_dir_raw,
            Path(os.path.abspath(attempt_dir)) == attempt_dir,
            attempt_dir.name == execution.get("attempt_id"),
            attempt_dir.parent.name == job.get("job_id"),
            provenance.get("runtime_evidence_path") == runtime_relative,
        )
    ):
        return False

    relative_files = _v034_replay_file_set(method, attempt_dir_raw)
    if relative_files is None:
        return False
    captured: dict[str, tuple[Path, bytes, str, tuple[int, ...]]] = {}
    for relative in relative_files:
        observed = _v034_stable_attempt_file(
            attempt_dir_raw,
            relative,
            allow_empty=relative in {"stdout.log", "stderr.log"},
        )
        if observed is None:
            return False
        captured[relative] = observed

    runtime_file = captured[runtime_relative]
    runtime_object = _v034_json_object(runtime_file[1])
    evidence = provenance.get("evidence")
    if runtime_object is None or not isinstance(evidence, dict):
        return False
    try:
        runtime_semantic = json.dumps(
            runtime_object,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    if not all(
        (
            _v034_runtime_evidence_schema_pass(method, runtime_object),
            runtime_object == evidence,
            runtime_file[2] == provenance.get("runtime_evidence_sha256"),
            hashlib.sha256(runtime_semantic).hexdigest()
            == provenance.get("evidence_semantic_sha256"),
        )
    ):
        return False

    local_manifest = _v034_one_csv_object(
        captured["method_output_manifest.csv"][1]
    )
    local_candidate = _v034_one_csv_object(captured["candidate_outputs.csv"][1])
    local_qc = _v034_one_csv_object(captured["candidate_qc.csv"][1])
    result = _v034_json_object(captured["run_result.json"][1])
    if any(value is None for value in (local_manifest, local_candidate, local_qc, result)):
        return False
    assert local_manifest is not None
    assert local_candidate is not None
    assert local_qc is not None
    assert result is not None

    structure_relative, source_relative = expected_paths
    structure_file = captured.get(structure_relative) if structure_relative else None
    source_file = captured.get(source_relative)
    expected_structure = str(structure_file[0]) if structure_file is not None else ""
    expected_source = str(source_file[0]) if source_file is not None else ""
    if not all(
        (
            candidate.get("structure_path") == expected_structure,
            candidate.get("source_output_path") == expected_source,
            not expected_structure
            or _v034_exact_regular_path(expected_structure, structure_file[0]),
            bool(expected_source),
            source_file is not None,
            _v034_exact_regular_path(expected_source, source_file[0])
            if source_file is not None
            else False,
            local_manifest == dict(manifest),
            set(candidate) == set(local_candidate) | {"supported_candidate"},
            candidate.get("supported_candidate") == "yes",
            all(candidate.get(key) == value for key, value in local_candidate.items()),
            local_qc.keys() <= qc.keys(),
            all(qc.get(key) == value for key, value in local_qc.items()),
        )
    ):
        return False

    try:
        adapter = importlib.import_module(str(module_name))
        replay_candidate, replay_evidence = adapter.parse(job, attempt_dir)
        replay_qc = evaluate_candidate_qc(
            job, replay_candidate, replay_evidence, attempt_dir / "raw"
        )
    except Exception:
        return False
    if not all(
        (
            isinstance(replay_candidate, dict),
            isinstance(replay_evidence, dict),
            replay_evidence == runtime_object,
            all(
                candidate.get(key) == str(value)
                for key, value in replay_candidate.items()
            ),
            all(qc.get(key) == str(value) for key, value in replay_qc.items()),
            all(
                key in local_qc
                or key in replay_qc
                or (key == "supported_candidate" and value == "yes")
                or (key.endswith("_status") and value == "not_applicable")
                or value == ""
                for key, value in qc.items()
            ),
        )
    ):
        return False

    expected_result_fields = {
        "attempt_dir",
        "created_at",
        "design_id",
        "exit_code",
        "job_id",
        "method",
        "overall_qc_status",
        "parser_status",
        "runtime_seconds",
        "status",
        "status_reason",
    }
    expected_run = {
        "design_id": candidate.get("design_id", ""),
        "job_id": job.get("job_id", ""),
        "method": method,
        "task_id": job.get("task_id", ""),
        "target_id": job.get("target_id", ""),
        "input_mode": job.get("input_mode", ""),
        "peptide_type": job.get("peptide_type", ""),
        "chirality": job.get("chirality", ""),
        "cyclic": job.get("cyclic", ""),
        "random_seed": job.get("random_seed", ""),
        "seed_stage": job.get("seed_stage", ""),
        "attempt_id": execution.get("attempt_id", ""),
        "status": "passed",
        "overall_qc_status": qc.get("overall_qc_status", ""),
        "supported_candidate": "yes",
        "sequence": candidate.get("sequence", ""),
        "structure_path": candidate.get("structure_path", ""),
        "status_reason": "bounded_connectivity_candidate_qc_passed",
        "notes": (
            "Bounded connectivity evidence only; not scoring, ranking, or "
            "Benchmark result"
        ),
    }
    expected_execution = {
        "execution_id": f"exec_{job.get('job_id', '')}",
        "job_id": job.get("job_id", ""),
        "method": method,
        "seed_stage": job.get("seed_stage", ""),
        "random_seed": job.get("random_seed", ""),
        "attempt_id": attempt_dir.name,
        "attempt_dir": attempt_dir_raw,
        "status": "passed",
        "overall_qc_status": qc.get("overall_qc_status", ""),
        "supported_candidate": "yes",
        "merge_status": "supported",
        "status_reason": "bounded_connectivity_candidate_qc_passed",
        "candidate_parse_status": candidate.get("parse_status", ""),
        "qc_status_reason": qc.get("status_reason", ""),
        "chirality_evaluable": qc.get("chirality_evaluable", ""),
        "chirality_l_count": qc.get("chirality_l_count", ""),
        "chirality_d_count": qc.get("chirality_d_count", ""),
        "chirality_unknown_count": qc.get("chirality_unknown_count", ""),
        "method_contract_status": qc.get("method_contract_status", ""),
        "handoff_status": qc.get("handoff_status", ""),
    }
    if not all(
        (
            set(result) == expected_result_fields,
            result.get("attempt_dir") == attempt_dir_raw,
            result.get("created_at") == manifest.get("created_at"),
            result.get("design_id") == candidate.get("design_id"),
            type(result.get("exit_code")) is int,
            result.get("exit_code") == 0,
            result.get("job_id") == job.get("job_id"),
            result.get("method") == method,
            result.get("overall_qc_status") == qc.get("overall_qc_status"),
            result.get("parser_status") == candidate.get("parse_status"),
            str(result.get("runtime_seconds")) == manifest.get("runtime_seconds"),
            result.get("status") == "passed",
            result.get("status_reason") == "bounded_connectivity_candidate_qc_passed",
            dict(run) == expected_run,
            dict(execution) == expected_execution,
            manifest.get("command") == f"bash {attempt_dir / 'command.sh'}",
            manifest.get("raw_output_root") == str(attempt_dir / "raw"),
            manifest.get("stdout_log") == str(attempt_dir / "stdout.log"),
            manifest.get("stderr_log") == str(attempt_dir / "stderr.log"),
        )
    ):
        return False

    for relative, original in captured.items():
        repeated = _v034_stable_attempt_file(
            attempt_dir_raw,
            relative,
            allow_empty=relative in {"stdout.log", "stderr.log"},
        )
        if repeated is None or repeated[1:] != original[1:]:
            return False
    return True


def _v034_process_and_candidate_provenance_pass(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    manifest: Mapping[str, str],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
    run: Mapping[str, str],
    provenance: Mapping[str, Any],
) -> bool:
    attempt_id = execution.get("attempt_id", "")
    structure_required = job.get("expected_binder_chain") != "not_applicable"
    candidate_structure = candidate.get("structure_path", "")
    runtime_evidence = provenance.get("evidence")
    dflow_cross_binding = job.get("method") != "D-Flow / PeptideDesign" or (
        isinstance(runtime_evidence, Mapping)
        and manifest.get("source_commit") == runtime_evidence.get("source_commit")
        and manifest.get("model_revision")
        == f"sha256:{runtime_evidence.get('checkpoint_sha256', '')}"
        and manifest.get("environment_id")
        == runtime_evidence.get("execution_environment_declared")
    )
    pepmirror_cross_binding = job.get("method") != "PepMirror" or (
        isinstance(runtime_evidence, Mapping)
        and manifest.get("source_commit")
        == runtime_evidence.get("source_commit_observed")
        and manifest.get("model_revision")
        == runtime_evidence.get("checkpoint_revision")
        and manifest.get("environment_id")
        == runtime_evidence.get("execution_environment_id")
    )
    pepglad_cross_binding = job.get("method") != "PepGLAD" or (
        isinstance(runtime_evidence, Mapping)
        and manifest.get("source_commit") == V034_PEPGLAD_SOURCE_COMMIT
        and manifest.get("source_commit") == runtime_evidence.get("source_commit")
        and manifest.get("model_revision") == V034_PEPGLAD_MODEL_REVISION
        and manifest.get("environment_id") == V034_PEPGLAD_ENVIRONMENT_ID
        and runtime_evidence.get("container_image") == V034_PEPGLAD_CONTAINER_IMAGE
    )
    pepglad_recovery_binding = job.get("method") != "PepGLAD" or (
        _v034_pepglad_instrumented_provenance_pass(
            job, execution, candidate, qc, provenance
        )
    )
    rf_cross_binding = job.get("method") != "RFdiffusion + ProteinMPNN" or (
        isinstance(runtime_evidence, Mapping)
        and manifest.get("source_commit")
        == (
            f"RFdiffusion@{runtime_evidence.get('rf_source_commit', '')};"
            f"ProteinMPNN@{runtime_evidence.get('mpnn_source_commit', '')}"
        )
        and manifest.get("environment_id")
        == (
            f"{runtime_evidence.get('rf_container_image', '')} + "
            f"{runtime_evidence.get('mpnn_container_image', '')}"
        )
        and manifest.get("model_revision") == V034_RF_MODEL_REVISION
        and runtime_evidence.get("rf_checkpoint_sha256") == V034_RF_CHECKPOINT_SHA256
        and runtime_evidence.get("mpnn_checkpoint_sha256")
        == V034_MPNN_CHECKPOINT_SHA256
    )
    return all(
        (
            re.fullmatch(r"attempt_[0-9]{3}", attempt_id) is not None,
            Path(execution.get("attempt_dir", "")).name == attempt_id,
            manifest.get("run_record_id") == f"{job['job_id']}_{attempt_id}",
            manifest.get("execution_stage") == job.get("seed_stage"),
            bool(manifest.get("source_commit")),
            bool(manifest.get("model_revision")),
            bool(manifest.get("environment_id")),
            bool(manifest.get("command")),
            bool(manifest.get("raw_output_root")),
            bool(manifest.get("stdout_log")),
            bool(manifest.get("stderr_log")),
            _v034_positive_runtime(manifest.get("runtime_seconds")),
            manifest.get("exit_code") == "0",
            candidate.get("target_id") == job.get("target_id"),
            candidate.get("generation_rank") == "1",
            candidate.get("binder_chain") == job.get("expected_binder_chain"),
            candidate.get("peptide_type") == job.get("peptide_type"),
            candidate.get("chirality") == job.get("chirality"),
            candidate.get("cyclic") == job.get("cyclic"),
            bool(candidate.get("source_output_path")),
            bool(candidate_structure) is structure_required,
            _v034_sha256(qc.get("file_sha256")),
            _v034_positive_int(qc.get("file_size_bytes")),
            run.get("attempt_id") == attempt_id,
            run.get("structure_path", "") == candidate_structure,
            run.get("target_id") == job.get("target_id"),
            run.get("peptide_type") == job.get("peptide_type"),
            run.get("chirality") == job.get("chirality"),
            run.get("cyclic") == job.get("cyclic"),
            provenance.get("attempt_id") == attempt_id,
            _v034_runtime_provenance_pass(job, candidate, qc, provenance),
            dflow_cross_binding,
            pepmirror_cross_binding,
            pepglad_cross_binding,
            pepglad_recovery_binding,
            rf_cross_binding,
            _v034_fixed_identity_pass(
                job.get("method"), manifest, runtime_evidence
            ),
        )
    )


def _v034_parsed_failure_valid(
    job: Mapping[str, str],
    execution: Mapping[str, str] | None,
    manifest: Mapping[str, str] | None,
    candidate: Mapping[str, str] | None,
    qc: Mapping[str, str] | None,
    run: Mapping[str, str] | None,
    provenance: Mapping[str, Any] | None,
) -> bool:
    if not all((execution, manifest, candidate, qc, run, provenance)):
        return False
    assert execution is not None
    assert manifest is not None
    assert candidate is not None
    assert qc is not None
    assert run is not None
    assert provenance is not None
    design_id = candidate.get("design_id", "")
    failed_status_fields = {
        key
        for key, value in qc.items()
        if key.endswith("_status") and key != "overall_qc_status" and value == "fail"
    }
    pepglad_failure_valid = job.get("method") != "PepGLAD" or all(
        (
            failed_status_fields == {"chirality_status"},
            qc.get("chirality_status") == "fail",
            qc.get("chirality_evaluable") == "11",
            qc.get("chirality_l_count") == "4",
            qc.get("chirality_d_count") == "7",
            qc.get("chirality_unknown_count") == "0",
        )
    )
    return all(
        (
            execution.get("status") == "qc_failed",
            execution.get("overall_qc_status") == "fail",
            execution.get("supported_candidate") == "no",
            execution.get("merge_status") == "qc_failed",
            manifest.get("status") == "qc_failed",
            manifest.get("overall_qc_status") == "fail",
            manifest.get("parser_status") in {"parsed", "partial"},
            manifest.get("exit_code") == "0",
            candidate.get("method") == job.get("method"),
            candidate.get("parse_status") in {"parsed", "partial"},
            candidate.get("supported_candidate") == "no",
            bool(design_id),
            bool(candidate.get("sequence")),
            qc.get("design_id") == design_id,
            qc.get("overall_qc_status") == "fail",
            qc.get("supported_candidate") == "no",
            bool(failed_status_fields),
            run.get("design_id") == design_id,
            run.get("status") == "qc_failed",
            run.get("overall_qc_status") == "fail",
            run.get("supported_candidate") == "no",
            run.get("sequence") == candidate.get("sequence"),
            run.get("structure_path") == candidate.get("structure_path"),
            execution.get("attempt_id") == run.get("attempt_id"),
            execution.get("attempt_id") == provenance.get("attempt_id"),
            _v034_process_and_candidate_provenance_pass(
                job, execution, manifest, candidate, qc, run, provenance
            ),
            pepglad_failure_valid,
        )
    )


def _v034_manifest_only_failure_valid(
    job: Mapping[str, str],
    execution: Mapping[str, str] | None,
    manifest: Mapping[str, str] | None,
    candidate: Mapping[str, str] | None,
    qc: Mapping[str, str] | None,
    run: Mapping[str, str] | None,
    provenance: Mapping[str, Any] | None,
) -> bool:
    """Validate an executed parser failure that produced no candidate evidence."""

    if execution is None or manifest is None or run is None:
        return False
    if any(value is not None for value in (candidate, qc, provenance)):
        return False

    job_id = job.get("job_id", "")
    attempt_id = execution.get("attempt_id", "")
    attempt_dir_raw = execution.get("attempt_dir", "")
    attempt_dir = Path(attempt_dir_raw)
    failure_reason = execution.get("status_reason", "")
    common_binding = all(
        (
            bool(job_id),
            re.fullmatch(r"attempt_[0-9]{3}", attempt_id) is not None,
            attempt_dir.is_absolute(),
            str(attempt_dir) == attempt_dir_raw,
            attempt_dir.name == attempt_id,
            attempt_dir.parent.name == job_id,
            execution.get("execution_id") == f"exec_{job_id}",
            execution.get("job_id") == job_id,
            execution.get("method") == job.get("method"),
            execution.get("seed_stage") == job.get("seed_stage"),
            execution.get("random_seed") == job.get("random_seed"),
            execution.get("status") == "parse_failed",
            execution.get("overall_qc_status") == "fail",
            execution.get("supported_candidate") == "no",
            execution.get("merge_status") == "evidence_incomplete",
            execution.get("candidate_parse_status") == "failed",
            bool(failure_reason),
            manifest.get("run_record_id") == f"{job_id}_{attempt_id}",
            manifest.get("job_id") == job_id,
            manifest.get("method") == job.get("method"),
            manifest.get("task_id") == job.get("task_id"),
            manifest.get("execution_stage") == job.get("seed_stage"),
            bool(manifest.get("source_commit")),
            bool(manifest.get("model_revision")),
            bool(manifest.get("environment_id")),
            manifest.get("command") == f"bash {attempt_dir / 'command.sh'}",
            manifest.get("raw_output_root") == str(attempt_dir / "raw"),
            manifest.get("stdout_log") == str(attempt_dir / "stdout.log"),
            manifest.get("stderr_log") == str(attempt_dir / "stderr.log"),
            _v034_positive_runtime(manifest.get("runtime_seconds")),
            manifest.get("exit_code") == "0",
            manifest.get("parser_status") == "failed",
            manifest.get("overall_qc_status") == "fail",
            manifest.get("status") == "parse_failed",
            manifest.get("status_reason") == failure_reason,
            bool(manifest.get("created_at")),
            run.get("job_id") == job_id,
            run.get("method") == job.get("method"),
            run.get("task_id") == job.get("task_id"),
            run.get("target_id") == job.get("target_id"),
            run.get("input_mode") == job.get("input_mode"),
            run.get("peptide_type") == job.get("peptide_type"),
            run.get("chirality") == job.get("chirality"),
            run.get("cyclic") == job.get("cyclic"),
            run.get("random_seed") == job.get("random_seed"),
            run.get("seed_stage") == job.get("seed_stage"),
            run.get("attempt_id") == attempt_id,
            run.get("status") == "parse_failed",
            run.get("overall_qc_status") == "fail",
            run.get("supported_candidate") == "no",
            run.get("status_reason") == failure_reason,
            not run.get("design_id"),
            not run.get("sequence"),
            not run.get("structure_path"),
        )
    )

    # Manifest-only failures have no runtime provenance to cross-bind. Admit only
    # explicitly reviewed method/reason identities; new failure types fail closed.
    reviewed_failure_identity = job.get("method") == "PepGLAD" and all(
        (
            job_id == "v034_pepglad_3eqs_seed42",
            job.get("task_id") == "T2_structure_peptide_binder",
            job.get("target_id") == "mdm2_p53_3eqs_fixture",
            job.get("target_pdb") == "3EQS",
            job.get("target_pdb_path") == "data/dflow/pdbs/3EQS.pdb",
            job.get("target_pdb_sha256") == V034_PEPGLAD_TARGET_SHA256,
            job.get("target_binding_check_mode") == "sequence_and_sha256",
            job.get("random_seed") == "42",
            job.get("seed_stage") == "primary",
            attempt_id == "attempt_003",
            failure_reason == "pepglad_seed42_replay_mismatch",
            execution.get("qc_status_reason")
            == (
                "file_status;parse_status;target_binding_status;length_status;"
                "chirality_status;overall_qc_status"
            ),
            execution.get("method_contract_status") == "pass",
            execution.get("handoff_status") == "not_applicable",
            manifest.get("source_commit") == V034_PEPGLAD_SOURCE_COMMIT,
            manifest.get("model_revision") == V034_PEPGLAD_MODEL_REVISION,
            manifest.get("environment_id") == V034_PEPGLAD_ENVIRONMENT_ID,
        )
    )
    return common_binding and reviewed_failure_identity


def _v034_not_run_row_valid(
    job: Mapping[str, str],
    execution: Mapping[str, str] | None,
    manifest: Mapping[str, str] | None,
    candidate: Mapping[str, str] | None,
    qc: Mapping[str, str] | None,
    run: Mapping[str, str] | None,
    provenance: Mapping[str, Any] | None,
) -> bool:
    if execution is None or run is None:
        return False
    if any(value is not None for value in (manifest, candidate, qc, provenance)):
        return False

    job_id = job.get("job_id", "")
    return all(
        (
            bool(job_id),
            execution.get("execution_id") == f"exec_{job_id}",
            execution.get("job_id") == job_id,
            execution.get("method") == job.get("method"),
            execution.get("seed_stage") == job.get("seed_stage"),
            execution.get("random_seed") == job.get("random_seed"),
            not execution.get("attempt_id"),
            not execution.get("attempt_dir"),
            execution.get("status") == "not_run",
            execution.get("overall_qc_status") == "not_run",
            execution.get("supported_candidate") == "no",
            execution.get("merge_status") == "not_run",
            execution.get("status_reason") == "no_attempt_recorded",
            run.get("job_id") == job_id,
            run.get("method") == job.get("method"),
            run.get("target_id") == job.get("target_id"),
            run.get("peptide_type") == job.get("peptide_type"),
            run.get("chirality") == job.get("chirality"),
            run.get("cyclic") == job.get("cyclic"),
            run.get("random_seed") == job.get("random_seed"),
            run.get("seed_stage") == job.get("seed_stage"),
            not run.get("design_id"),
            not run.get("attempt_id"),
            run.get("status") == "not_run",
            run.get("overall_qc_status") == "not_run",
            run.get("supported_candidate") == "no",
            not run.get("sequence"),
            not run.get("structure_path"),
            run.get("status_reason") == "no_attempt_recorded",
        )
    )


def _v034_row_supported(
    job: Mapping[str, str],
    execution: Mapping[str, str] | None,
    manifest: Mapping[str, str] | None,
    candidate: Mapping[str, str] | None,
    qc: Mapping[str, str] | None,
    run: Mapping[str, str] | None,
    provenance: Mapping[str, Any] | None,
) -> bool:
    if not all((execution, manifest, candidate, qc, run, provenance)):
        return False
    assert execution is not None
    assert manifest is not None
    assert candidate is not None
    assert qc is not None
    assert run is not None
    assert provenance is not None
    design_id = candidate.get("design_id", "")
    qc_check_statuses = [
        value
        for key, value in qc.items()
        if key.endswith("_status") and key != "overall_qc_status"
    ]
    qc_checks_valid = bool(qc_check_statuses) and all(
        value in {"pass", "warn", "not_applicable"} for value in qc_check_statuses
    )
    expected_qc_status = "pass_with_warning" if "warn" in qc_check_statuses else "pass"
    qc_summary_consistent = all(
        row.get("overall_qc_status") == expected_qc_status
        for row in (execution, manifest, qc, run)
    )
    common = all(
        (
            execution.get("method") == job.get("method"),
            execution.get("seed_stage") == job.get("seed_stage"),
            execution.get("random_seed") == job.get("random_seed"),
            execution.get("status") == "passed",
            execution.get("overall_qc_status") in V034_ACCEPTED_QC,
            execution.get("supported_candidate") == "yes",
            execution.get("merge_status") == "supported",
            manifest.get("method") == job.get("method"),
            manifest.get("status") == "passed",
            manifest.get("parser_status") in {"parsed", "partial"},
            manifest.get("overall_qc_status") in V034_ACCEPTED_QC,
            candidate.get("method") == job.get("method"),
            candidate.get("parse_status") in {"parsed", "partial"},
            bool(design_id),
            bool(candidate.get("sequence", "")),
            qc.get("design_id") == design_id,
            qc.get("overall_qc_status") in V034_ACCEPTED_QC,
            qc_checks_valid,
            qc_summary_consistent,
            _v034_required_qc_checks_pass(job, qc),
            run.get("method") == job.get("method"),
            run.get("seed_stage") == job.get("seed_stage"),
            run.get("random_seed") == job.get("random_seed"),
            run.get("design_id") == design_id,
            run.get("status") == "passed",
            run.get("overall_qc_status") in V034_ACCEPTED_QC,
            run.get("supported_candidate") == "yes",
            run.get("sequence") == candidate.get("sequence"),
            candidate.get("supported_candidate") == "yes",
            qc.get("supported_candidate") == "yes",
            _v034_process_and_candidate_provenance_pass(
                job, execution, manifest, candidate, qc, run, provenance
            ),
            _v034_raw_replay_pass(
                job, execution, manifest, candidate, qc, run, provenance
            ),
        )
    )
    if job.get("method") == "RFdiffusion + ProteinMPNN":
        return common and qc.get("handoff_status") == "pass"
    if job.get("method") == "PepMirror":
        return common and qc.get("chirality_status") == "pass"
    return common


def _v034_failure_diagnostic_expected(attempt_dir: str) -> dict[str, Any]:
    chirality_common = {
        "calculation_status": "pass",
        "chain": "B",
        "evaluable": 11,
        "gly_count": 0,
        "unknown_count": 0,
    }
    return {
        "attempt_dir": attempt_dir,
        "attempt_id": "attempt_003",
        "baseline": {
            "expected_sha256": V034_PEPGLAD_SEED42_BASELINE_SHA256,
            "failure_stage": "pre_openmm_snapshot",
            "observed_sha256": V034_PEPGLAD_DIAGNOSTIC_POST_SHA256,
            "status": "mismatch",
        },
        "candidate_eligible": False,
        "job_id": "v034_pepglad_3eqs_seed42",
        "merge": {"status": "evidence_incomplete"},
        "method": "PepGLAD",
        "parser": {
            "status": "failed",
            "status_reason": "pepglad_seed42_replay_mismatch",
        },
        "post_openmm": {
            "chirality": {**chirality_common, "d_count": 7, "l_count": 4},
            "path": "raw/pepglad_candidate.pdb",
            "sha256": V034_PEPGLAD_DIAGNOSTIC_POST_SHA256,
        },
        "pre_openmm": {
            "chirality": {**chirality_common, "d_count": 5, "l_count": 6},
            "path": "raw/pepglad_pre_relax.pdb",
            "sha256": V034_PEPGLAD_DIAGNOSTIC_PRE_SHA256,
        },
        "process": {"exit_code": 0},
        "producer_bindings": {
            "container": {"image": V034_PEPGLAD_CONTAINER_IMAGE},
            "environment": {
                "conda_environment": V034_PEPGLAD_CONDA_ENVIRONMENT
            },
            "instrumented_source": {
                "path": "work/api/run.py",
                "prepatch_sha256": V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
                "sha256": V034_PEPGLAD_INSTRUMENTED_SOURCE_SHA256,
            },
            "model": {"weights_sha256": V034_PEPGLAD_MODEL_WEIGHTS_SHA256},
            "observer": {
                "path": "pepglad_observer.py",
                "sha256": V034_PEPGLAD_OBSERVER_SOURCE_SHA256,
            },
            "patch": {
                "evidence_path": "observer_patch_evidence.json",
                "evidence_sha256": V034_PEPGLAD_DIAGNOSTIC_PATCH_EVIDENCE_SHA256,
                "injection_status": "applied",
                "instrumenter_path": "pepglad_instrument_source.py",
                "instrumenter_sha256": V034_PEPGLAD_OBSERVER_PATCH_SHA256,
                "source_copy_mode": "attempt_local_copy",
            },
            "source": {
                "commit": V034_PEPGLAD_SOURCE_COMMIT,
                "entrypoint_sha256": V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            },
            "target": {
                "path": "/data/input/3EQS.pdb",
                "preflight_verified": True,
                "sha256": V034_PEPGLAD_TARGET_SHA256,
            },
            "wrapper": {
                "path": "pepglad_seeded_entry.py",
                "sha256": V034_PEPGLAD_SEED_WRAPPER_SHA256,
            },
        },
        "random_seed": 42,
        "runtime_evidence": {
            "path": "raw/runtime_evidence.json",
            "semantic_sha256": V034_PEPGLAD_DIAGNOSTIC_RUNTIME_SEMANTIC_SHA256,
            "sha256": V034_PEPGLAD_DIAGNOSTIC_RUNTIME_SHA256,
        },
        "seed43_status": "not_run",
        "seed_stage": "primary",
        "summary": {
            "path": "raw/pepglad_summary.jsonl",
            "sequence": "AWHITLLIFTH",
            "sha256": V034_PEPGLAD_DIAGNOSTIC_SUMMARY_SHA256,
        },
    }


def _v034_failure_diagnostic_valid(
    payload: Mapping[str, Any],
    jobs_by_id: Mapping[str, Mapping[str, str]],
    executions_by_id: Mapping[str, Mapping[str, str]],
    manifests_by_id: Mapping[str, Mapping[str, str]],
    candidates_by_id: Mapping[str, Mapping[str, str]],
    qcs_by_id: Mapping[str, Mapping[str, str]],
    runs_by_id: Mapping[str, Mapping[str, str]],
    provenance_by_id: Mapping[str, Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> bool:
    if set(payload) != {"schema_version", "evidence_boundary", "records"}:
        return False
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 1:
        return False
    record = records[0]
    if not isinstance(record, dict):
        return False
    attempt_dir_raw = record.get("attempt_dir")
    if not isinstance(attempt_dir_raw, str):
        return False
    attempt_dir = Path(attempt_dir_raw)
    fixed_payload_valid = all(
        (
            payload.get("schema_version") == "v0.34",
            payload.get("evidence_boundary")
            == "failure_diagnostic_only_not_candidate_or_scoring",
            attempt_dir.is_absolute(),
            attempt_dir_raw == V034_PEPGLAD_DIAGNOSTIC_ATTEMPT_DIR,
            attempt_dir.name == "attempt_003",
            attempt_dir.parent.name == "v034_pepglad_3eqs_seed42",
            record == _v034_failure_diagnostic_expected(attempt_dir_raw),
        )
    )
    if not fixed_payload_valid:
        return False

    primary_id = "v034_pepglad_3eqs_seed42"
    extension_id = "v034_pepglad_3eqs_seed43"
    job = jobs_by_id.get(primary_id, {})
    execution = executions_by_id.get(primary_id, {})
    manifest = manifests_by_id.get(primary_id, {})
    run = runs_by_id.get(primary_id, {})

    # Once a later accepted attempt exists, keep this immutable diagnostic as
    # historical failure evidence without rebinding it to the latest-only rows.
    if _v034_row_supported(
        job,
        execution,
        manifest,
        candidates_by_id.get(primary_id),
        qcs_by_id.get(primary_id),
        run,
        provenance_by_id.get(primary_id),
    ):
        return True

    extension_job = jobs_by_id.get(extension_id, {})
    extension_execution = executions_by_id.get(extension_id)
    extension_run = runs_by_id.get(extension_id)
    summary_job_status = summary.get("job_status")
    if not isinstance(summary_job_status, Mapping):
        return False
    current_failure_bindings = all(
        (
            _v034_manifest_only_failure_valid(
                job, execution, manifest, None, None, run, None
            ),
            _v034_not_run_row_valid(
                extension_job,
                extension_execution,
                None,
                None,
                None,
                extension_run,
                None,
            ),
            execution.get("attempt_id") == record.get("attempt_id"),
            execution.get("attempt_dir") == attempt_dir_raw,
            execution.get("merge_status") == record["merge"]["status"],
            execution.get("status_reason")
            == record["parser"]["status_reason"],
            manifest.get("exit_code") == str(record["process"]["exit_code"]),
            manifest.get("source_commit")
            == record["producer_bindings"]["source"]["commit"],
            manifest.get("model_revision") == V034_PEPGLAD_MODEL_REVISION,
            manifest.get("environment_id") == V034_PEPGLAD_ENVIRONMENT_ID,
            run.get("attempt_id") == record.get("attempt_id"),
            run.get("status_reason") == record["parser"]["status_reason"],
            primary_id not in candidates_by_id,
            primary_id not in qcs_by_id,
            primary_id not in provenance_by_id,
            extension_id not in manifests_by_id,
            extension_id not in candidates_by_id,
            extension_id not in qcs_by_id,
            extension_id not in provenance_by_id,
            summary.get("primary_total") == 7,
            summary.get("primary_passed") == 6,
            summary.get("extension_total") == 7,
            summary.get("extension_passed") == 6,
            summary.get("parsed_candidate_rows") == 12,
            summary.get("runtime_provenance_rows") == 12,
            summary_job_status.get(primary_id) == record["merge"]["status"],
            summary_job_status.get(extension_id) == record["seed43_status"],
        )
    )
    return current_failure_bindings


def _evaluate_v034_connectivity(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    by_name = {path.name: path for path in paths}
    jobs = _read_csv(by_name["pilot_benchmark_job_manifest_v0.34.csv"])
    executions = _read_csv(by_name["pilot_execution_results_v0.34.csv"])
    manifests = _read_csv(by_name["pilot_method_output_manifest_v0.34.csv"])
    candidates = _read_csv(by_name["pilot_candidate_outputs_v0.34.csv"])
    qcs = _read_csv(by_name["pilot_candidate_qc_v0.34.csv"])
    runs = _read_csv(by_name["pilot_run_v0.34.csv"])
    provenance_payload = _v034_json_object(
        by_name["pilot_runtime_provenance_v0.34.json"].read_bytes()
    ) or {}
    runtime_payload_schema_valid = _v034_runtime_payload_schema_pass(
        provenance_payload
    )
    provenance_records = provenance_payload.get("records", [])
    if not isinstance(provenance_records, list) or not all(
        isinstance(record, dict) for record in provenance_records
    ):
        provenance_records = []
    failure_diagnostic_payload = _v034_json_object(
        by_name["pilot_failure_diagnostics_v0.34.json"].read_bytes()
    ) or {}
    failure_diagnostic_records = failure_diagnostic_payload.get("records", [])
    if not isinstance(failure_diagnostic_records, list) or not all(
        isinstance(row, dict) for row in failure_diagnostic_records
    ):
        failure_diagnostic_records = []
    summary = _v034_json_object(
        by_name["pilot_v034_merge_summary.json"].read_bytes()
    ) or {}

    jobs_by_id, job_duplicates = _unique_rows(jobs, "job_id")
    executions_by_id, execution_duplicates = _unique_rows(executions, "job_id")
    manifests_by_id, manifest_duplicates = _unique_rows(manifests, "job_id")
    candidates_by_id, candidate_duplicates = _unique_rows(candidates, "job_id")
    qcs_by_id, qc_duplicates = _unique_rows(qcs, "job_id")
    runs_by_id, run_duplicates = _unique_rows(runs, "job_id")
    provenance_by_id, provenance_duplicates = _unique_rows(provenance_records, "job_id")
    duplicate_ids = tuple(
        sorted(
            set(job_duplicates)
            | set(execution_duplicates)
            | set(manifest_duplicates)
            | set(candidate_duplicates)
            | set(qc_duplicates)
            | set(run_duplicates)
            | set(provenance_duplicates)
        )
    )

    primary_jobs = [row for row in jobs if row.get("seed_stage") == "primary"]
    extension_jobs = [row for row in jobs if row.get("seed_stage") == "extension"]
    primary_ids = {row.get("job_id", "") for row in primary_jobs}
    extension_ids = {row.get("job_id", "") for row in extension_jobs}
    all_job_ids = primary_ids | extension_ids
    job_contract_valid = all(
        (
            len(jobs) == 14,
            len(primary_jobs) == 7,
            len(extension_jobs) == 7,
            {row.get("method") for row in primary_jobs} == V034_METHODS,
            {row.get("method") for row in extension_jobs} == V034_METHODS,
            all(row.get("random_seed") == "42" for row in primary_jobs),
            all(row.get("random_seed") == "43" for row in extension_jobs),
            all(
                row.get("primary_job_id") in primary_ids
                and jobs_by_id.get(row.get("primary_job_id", ""), {}).get("method")
                == row.get("method")
                for row in extension_jobs
            ),
        )
    )
    table_ids_valid = all(
        (
            set(executions_by_id) == all_job_ids,
            set(runs_by_id) == all_job_ids,
            set(manifests_by_id) <= all_job_ids,
            set(candidates_by_id) <= all_job_ids,
            set(qcs_by_id) <= all_job_ids,
            set(provenance_by_id) <= all_job_ids,
            provenance_payload.get("schema_version") == "v0.34",
            provenance_payload.get("evidence_boundary")
            == "bounded_connectivity_only_not_scoring_or_ranking",
            runtime_payload_schema_valid,
        )
    )

    supported_ids = {
        job_id
        for job_id, job in jobs_by_id.items()
        if _v034_row_supported(
            job,
            executions_by_id.get(job_id),
            manifests_by_id.get(job_id),
            candidates_by_id.get(job_id),
            qcs_by_id.get(job_id),
            runs_by_id.get(job_id),
            provenance_by_id.get(job_id),
        )
    }
    declared_supported_ids = {
        job_id
        for job_id, row in executions_by_id.items()
        if row.get("supported_candidate") == "yes"
    }
    manifest_ids = set(manifests_by_id)
    candidate_ids = set(candidates_by_id)
    qc_ids = set(qcs_by_id)
    provenance_ids = set(provenance_by_id)
    parsed_failure_ids = candidate_ids - supported_ids
    parsed_failure_rows_valid = all(
        _v034_parsed_failure_valid(
            jobs_by_id.get(job_id, {}),
            executions_by_id.get(job_id),
            manifests_by_id.get(job_id),
            candidates_by_id.get(job_id),
            qcs_by_id.get(job_id),
            runs_by_id.get(job_id),
            provenance_by_id.get(job_id),
        )
        for job_id in parsed_failure_ids
    )
    failure_evidence_ids = manifest_ids - candidate_ids
    failure_evidence_valid = all(
        _v034_manifest_only_failure_valid(
            jobs_by_id.get(job_id, {}),
            executions_by_id.get(job_id),
            manifests_by_id.get(job_id),
            candidates_by_id.get(job_id),
            qcs_by_id.get(job_id),
            runs_by_id.get(job_id),
            provenance_by_id.get(job_id),
        )
        for job_id in failure_evidence_ids
    )
    not_run_ids = all_job_ids - manifest_ids
    not_run_rows_valid = all(
        _v034_not_run_row_valid(
            jobs_by_id.get(job_id, {}),
            executions_by_id.get(job_id),
            manifests_by_id.get(job_id),
            candidates_by_id.get(job_id),
            qcs_by_id.get(job_id),
            runs_by_id.get(job_id),
            provenance_by_id.get(job_id),
        )
        for job_id in not_run_ids
    )
    attempted_execution_ids = {
        job_id
        for job_id, row in executions_by_id.items()
        if row.get("status") not in {"", "not_run"}
    }
    attempted_run_ids = {
        job_id
        for job_id, row in runs_by_id.items()
        if row.get("status") not in {"", "not_run"}
    }
    evidence_sets_consistent = all(
        (
            declared_supported_ids == supported_ids,
            supported_ids <= candidate_ids,
            candidate_ids == qc_ids,
            candidate_ids == provenance_ids,
            candidate_ids <= manifest_ids,
            manifest_ids == attempted_execution_ids,
            manifest_ids == attempted_run_ids,
            failure_evidence_valid,
            not_run_rows_valid,
            runtime_payload_schema_valid,
            {
                job_id
                for job_id, row in candidates_by_id.items()
                if row.get("supported_candidate") == "yes"
            }
            == supported_ids,
            {
                job_id
                for job_id, row in qcs_by_id.items()
                if row.get("supported_candidate") == "yes"
            }
            == supported_ids,
        )
    )
    primary_supported = len(primary_ids & supported_ids)
    extension_supported = len(extension_ids & supported_ids)

    extension_orphans = 0
    for job in extension_jobs:
        job_id = job.get("job_id", "")
        execution = executions_by_id.get(job_id, {})
        run = runs_by_id.get(job_id, {})
        has_evidence = any(
            (
                execution.get("status") not in {"", "not_run"},
                run.get("status") not in {"", "not_run"},
                job_id in manifests_by_id,
                job_id in candidates_by_id,
                job_id in qcs_by_id,
            )
        )
        if has_evidence and job.get("primary_job_id") not in supported_ids:
            extension_orphans += 1

    expected_job_status = {
        job_id: row.get("merge_status", "") for job_id, row in executions_by_id.items()
    }
    summary_consistent = all(
        (
            summary.get("schema_version") == "v0.34",
            summary.get("evidence_boundary")
            == "bounded_connectivity_only_not_scoring_or_ranking",
            summary.get("primary_total") == 7,
            summary.get("primary_passed") == primary_supported,
            summary.get("primary_complete") is (primary_supported == 7),
            summary.get("extension_total") == 7,
            summary.get("extension_passed") == extension_supported,
            summary.get("extension_complete") is (extension_supported == 7),
            summary.get("parsed_candidate_rows") == len(candidates_by_id),
            summary.get("qc_failed_rows")
            == sum(row.get("status") == "qc_failed" for row in executions),
            summary.get("runtime_provenance_rows") == len(provenance_by_id),
            summary.get("job_status") == expected_job_status,
        )
    )
    failure_diagnostic_valid = _v034_failure_diagnostic_valid(
        failure_diagnostic_payload,
        jobs_by_id,
        executions_by_id,
        manifests_by_id,
        candidates_by_id,
        qcs_by_id,
        runs_by_id,
        provenance_by_id,
        summary,
    )
    evidence_sets_consistent = (
        evidence_sets_consistent and failure_diagnostic_valid
    )
    rf_job = next(
        (
            row
            for row in primary_jobs
            if row.get("method") == "RFdiffusion + ProteinMPNN"
        ),
        {},
    )
    pepmirror_job = next(
        (row for row in primary_jobs if row.get("method") == "PepMirror"), {}
    )
    rf_qc = qcs_by_id.get(rf_job.get("job_id", ""), {})
    pepmirror_qc = qcs_by_id.get(pepmirror_job.get("job_id", ""), {})
    rf_handoff_resolved = (
        rf_job.get("job_id") in supported_ids and rf_qc.get("handoff_status") == "pass"
    )
    pepmirror_chirality_resolved = all(
        (
            pepmirror_job.get("job_id") in supported_ids,
            pepmirror_qc.get("method_contract_status") == "pass",
            pepmirror_qc.get("chirality_status") == "pass",
        )
    )
    structural_checks_passed = all(
        (
            not duplicate_ids,
            job_contract_valid,
            table_ids_valid,
            evidence_sets_consistent,
            parsed_failure_rows_valid,
            failure_evidence_valid,
            not_run_rows_valid,
            extension_orphans == 0,
            summary_consistent,
            rf_handoff_resolved,
            pepmirror_chirality_resolved,
        )
    )
    passed = structural_checks_passed and primary_supported == 7
    if passed:
        message = (
            "Seven v0.34 primary methods produced parseable candidates with bounded QC and provenance; scoring remains out of scope."
        )
    elif structural_checks_passed and primary_supported == 6:
        message = (
            "Six of seven v0.34 primary methods have supported bounded candidates; PepGLAD remains evidence_incomplete."
        )
    else:
        message = "v0.34 bounded connectivity evidence is missing or inconsistent."
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        message,
        paths,
        details=_details(
            candidate_rows=len(candidates),
            duplicate_ids=duplicate_ids,
            evidence_sets_consistent=evidence_sets_consistent,
            failure_diagnostic_rows=len(failure_diagnostic_records),
            failure_diagnostic_valid=failure_diagnostic_valid,
            failure_evidence_rows=len(failure_evidence_ids),
            failure_evidence_valid=failure_evidence_valid,
            extension_orphans=extension_orphans,
            extension_supported=extension_supported,
            job_contract_valid=job_contract_valid,
            method_output_manifest_rows=len(manifests),
            not_run_rows_valid=not_run_rows_valid,
            primary_jobs=len(primary_jobs),
            primary_supported=primary_supported,
            parsed_failure_rows=len(parsed_failure_ids),
            parsed_failure_rows_valid=parsed_failure_rows_valid,
            qc_rows=len(qcs),
            runtime_provenance_rows=len(provenance_records),
            rf_handoff_resolved=rf_handoff_resolved,
            pepmirror_chirality_resolved=pepmirror_chirality_resolved,
            structural_checks_passed=structural_checks_passed,
            summary_consistent=summary_consistent,
            table_ids_valid=table_ids_valid,
        ),
    )


V035_HISTORICAL_ARTIFACT_NAMES = frozenset(
    {
        "pilot_benchmark_job_manifest_v0.34.csv",
        "pilot_execution_matrix_v0.34.csv",
        "pilot_execution_results_v0.34.csv",
        "pilot_method_output_manifest_v0.34.csv",
        "pilot_candidate_outputs_v0.34.csv",
        "pilot_candidate_qc_v0.34.csv",
        "pilot_run_v0.34.csv",
        "pilot_runtime_provenance_v0.34.json",
        "pilot_failure_diagnostics_v0.34.json",
        "pilot_v034_merge_summary.json",
    }
)
V035_RAW_FILES = frozenset(
    {
        "raw/pepglad_candidate.pdb",
        "raw/pepglad_pre_relax.pdb",
        "raw/pepglad_summary.jsonl",
        "raw/runtime_evidence.json",
        "work/codesign/3EQS_0.pdb",
    }
)
V035_REPLAY_FILES = V035_RAW_FILES | frozenset(
    {
        "job.json",
        "execution.json",
        "run_result.json",
        "observer_patch_evidence.json",
        "pepglad_instrument_source.py",
        "pepglad_observer.py",
        "pepglad_seeded_entry.py",
        "work/api/run.py",
    }
)
V035_BUNDLE_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_boundary",
        "historical_v034_bindings",
        "job",
        "execution",
        "candidate",
        "qc",
        "runtime_provenance",
    }
)
V035_HISTORICAL_FIELDS = frozenset(
    {"primary_supported", "pepglad_status", "artifacts"}
)
V035_JOB_FIELDS = frozenset(
    {
        "job_id",
        "method",
        "random_seed",
        "seed_stage",
        "target_sha256",
        "target_chain",
        "binder_chain",
        "length",
        "chirality_constraint",
        "chirality_check_mode",
        "baseline_replay_policy",
    }
)
V035_EXECUTION_FIELDS = frozenset(
    {
        "attempt_id",
        "attempt_dir",
        "exit_code",
        "status",
        "supported_candidate",
    }
)
V035_CANDIDATE_FIELDS = frozenset(
    {
        "design_id",
        "sequence",
        "structure_path",
        "file_sha256",
        "binder_chain",
        "parse_status",
        "chirality",
    }
)
V035_QC_FIELDS = frozenset(
    {
        "observed_chirality_class",
        "chirality_status",
        "chirality_evaluable",
        "chirality_l_count",
        "chirality_d_count",
        "chirality_unknown_count",
        "baseline_replay_status",
        "overall_qc_status",
    }
)
V035_RUNTIME_FIELDS = frozenset(
    {
        "attempt_id",
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "runtime_evidence_path",
        "runtime_evidence_sha256",
        "runtime_semantic_sha256",
        "baseline_expected_sha256",
        "baseline_observed_sha256",
        "files",
        "producer_bindings",
    }
)
V035_PRODUCER_FIELDS = frozenset(
    {
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "target_input_sha256",
        "container_image",
        "conda_environment",
        "observer_source_sha256",
        "observer_patch_sha256",
        "seed_wrapper_sha256",
        "source_entrypoint_instrumented_sha256",
    }
)
V035_PRODUCER_PINS: Mapping[str, str] = {
    "source_commit": V034_PEPGLAD_SOURCE_COMMIT,
    "source_entrypoint_sha256": V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
    "model_weights_sha256": V034_PEPGLAD_MODEL_WEIGHTS_SHA256,
    "target_input_sha256": V034_PEPGLAD_TARGET_SHA256,
    "container_image": V034_PEPGLAD_CONTAINER_IMAGE,
    "conda_environment": V034_PEPGLAD_CONDA_ENVIRONMENT,
    "observer_source_sha256": V034_PEPGLAD_OBSERVER_SOURCE_SHA256,
    "observer_patch_sha256": V034_PEPGLAD_OBSERVER_PATCH_SHA256,
    "seed_wrapper_sha256": V034_PEPGLAD_SEED_WRAPPER_SHA256,
    "source_entrypoint_instrumented_sha256": (
        V034_PEPGLAD_INSTRUMENTED_SOURCE_SHA256
    ),
}


def _v035_authorized_protocol() -> tuple[Mapping[str, str], Mapping[str, str]]:
    from scripts.run_v035_pepglad_connectivity import (
        AUTHORIZED_EXECUTION,
        AUTHORIZED_JOB,
    )

    return AUTHORIZED_JOB, AUTHORIZED_EXECUTION


def _v035_bundle_schema_pass(bundle: Any) -> bool:
    if not isinstance(bundle, dict) or set(bundle) != V035_BUNDLE_FIELDS:
        return False
    historical = bundle.get("historical_v034_bindings")
    job = bundle.get("job")
    execution = bundle.get("execution")
    candidate = bundle.get("candidate")
    qc = bundle.get("qc")
    runtime = bundle.get("runtime_provenance")
    if not all(isinstance(value, dict) for value in (historical, job, execution, candidate, qc, runtime)):
        return False
    assert isinstance(historical, dict)
    assert isinstance(job, dict)
    assert isinstance(execution, dict)
    assert isinstance(candidate, dict)
    assert isinstance(qc, dict)
    assert isinstance(runtime, dict)
    files = runtime.get("files")
    producer = runtime.get("producer_bindings")
    historical_files = historical.get("artifacts")
    if not all(isinstance(value, dict) for value in (files, producer, historical_files)):
        return False
    assert isinstance(files, dict)
    assert isinstance(producer, dict)
    assert isinstance(historical_files, dict)
    if not all(
        (
            set(historical) == V035_HISTORICAL_FIELDS,
            set(job) == V035_JOB_FIELDS,
            set(execution) == V035_EXECUTION_FIELDS,
            set(candidate) == V035_CANDIDATE_FIELDS,
            set(qc) == V035_QC_FIELDS,
            set(runtime) == V035_RUNTIME_FIELDS,
            set(files) == V035_RAW_FILES,
            set(producer) == V035_PRODUCER_FIELDS,
            set(historical_files) == V035_HISTORICAL_ARTIFACT_NAMES,
        )
    ):
        return False
    sha_values = list(historical_files.values()) + list(files.values()) + [
        candidate.get("file_sha256"),
        runtime.get("runtime_evidence_sha256"),
        runtime.get("runtime_semantic_sha256"),
        runtime.get("baseline_expected_sha256"),
        runtime.get("baseline_observed_sha256"),
    ]
    if not all(_v034_sha256(value) for value in sha_values):
        return False
    if producer != V035_PRODUCER_PINS:
        return False
    int_fields = (
        job.get("random_seed"),
        job.get("length"),
        execution.get("exit_code"),
        qc.get("chirality_evaluable"),
        qc.get("chirality_l_count"),
        qc.get("chirality_d_count"),
        qc.get("chirality_unknown_count"),
        runtime.get("requested_seed"),
        runtime.get("effective_seed"),
    )
    if not all(type(value) is int for value in int_fields):
        return False
    l_count = qc.get("chirality_l_count")
    d_count = qc.get("chirality_d_count")
    evaluable = qc.get("chirality_evaluable")
    unknown = qc.get("chirality_unknown_count")
    if not all(type(value) is int for value in (l_count, d_count, evaluable, unknown)):
        return False
    if l_count == evaluable and d_count == 0:
        observed_class = "L"
        chirality_status = "pass"
    elif d_count == evaluable and l_count == 0:
        observed_class = "D"
        chirality_status = "pass"
    elif l_count > 0 and d_count > 0 and l_count + d_count == evaluable:
        observed_class = "mixed"
        chirality_status = "warn"
    else:
        return False
    baseline_status = (
        "pass"
        if runtime.get("baseline_observed_sha256")
        == V034_PEPGLAD_SEED42_BASELINE_SHA256
        else "warn"
    )
    overall_status = (
        "pass_with_warning"
        if "warn" in {chirality_status, baseline_status}
        else "pass"
    )
    candidate_sha = candidate.get("file_sha256")
    return all(
        (
            bundle.get("schema_version") == "v0.35",
            bundle.get("evidence_boundary")
            == "bounded_connectivity_only_not_scoring_or_ranking",
            historical.get("primary_supported") == 6,
            historical.get("pepglad_status")
            == "historical_failure_not_promoted",
            job.get("job_id") == "v035_pepglad_3eqs_seed42",
            job.get("method") == "PepGLAD",
            job.get("random_seed") == 42,
            job.get("seed_stage") == "primary",
            job.get("target_sha256") == V034_PEPGLAD_TARGET_SHA256,
            job.get("target_chain") == "A",
            job.get("binder_chain") == "B",
            job.get("length") == 11,
            job.get("chirality_constraint") == "unrestricted",
            job.get("chirality_check_mode") == "report_only",
            job.get("baseline_replay_policy") == "warn_on_mismatch",
            execution.get("attempt_id") == "attempt_001",
            type(execution.get("attempt_dir")) is str,
            execution.get("exit_code") == 0,
            execution.get("status") == "passed",
            execution.get("supported_candidate") is True,
            candidate.get("design_id")
            == "v035_pepglad_3eqs_seed42_candidate_1",
            type(candidate.get("sequence")) is str,
            len(candidate.get("sequence", "")) == 11,
            candidate.get("structure_path") == "raw/pepglad_candidate.pdb",
            candidate.get("binder_chain") == "B",
            candidate.get("parse_status") == "parsed",
            candidate.get("chirality") == observed_class,
            qc.get("observed_chirality_class") == observed_class,
            qc.get("chirality_status") == chirality_status,
            evaluable == 11,
            l_count + d_count == 11,
            unknown == 0,
            qc.get("baseline_replay_status") == baseline_status,
            qc.get("overall_qc_status") == overall_status,
            runtime.get("attempt_id") == execution.get("attempt_id"),
            runtime.get("requested_seed") == 42,
            runtime.get("effective_seed") == 42,
            runtime.get("seed_control_status") == "honored",
            runtime.get("runtime_evidence_path") == "raw/runtime_evidence.json",
            runtime.get("baseline_expected_sha256")
            == V034_PEPGLAD_SEED42_BASELINE_SHA256,
            runtime.get("baseline_observed_sha256") == candidate_sha,
            files.get("raw/pepglad_candidate.pdb") == candidate_sha,
            files.get("work/codesign/3EQS_0.pdb") == candidate_sha,
            files.get("raw/runtime_evidence.json")
            == runtime.get("runtime_evidence_sha256"),
        )
    )


def _v035_protocol_pass(job_path: Path, execution_path: Path) -> tuple[bool, dict[str, str]]:
    authorized_job, authorized_execution = _v035_authorized_protocol()
    job_capture = _v034_stable_attempt_file(
        str(Path(os.path.abspath(job_path.parent))), job_path.name
    )
    execution_capture = _v034_stable_attempt_file(
        str(Path(os.path.abspath(execution_path.parent))), execution_path.name
    )
    if job_capture is None or execution_capture is None:
        return False, {}
    job = _v034_one_csv_object(job_capture[1])
    execution = _v034_one_csv_object(execution_capture[1])
    valid = all(
        (
            job == authorized_job,
            execution == authorized_execution,
            _v034_stable_attempt_file(
                str(Path(os.path.abspath(job_path.parent))), job_path.name
            )
            == job_capture,
            _v034_stable_attempt_file(
                str(Path(os.path.abspath(execution_path.parent))), execution_path.name
            )
            == execution_capture,
        )
    )
    return valid, dict(job) if isinstance(job, dict) else {}


def _v035_historical_digest_pass(
    historical: Mapping[str, Any], paths: tuple[Path, ...]
) -> bool:
    artifacts = historical.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != V035_HISTORICAL_ARTIFACT_NAMES:
        return False
    observed: dict[str, tuple[Path, bytes, str, tuple[int, ...]]] = {}
    for path in paths:
        capture = _v034_stable_attempt_file(
            str(Path(os.path.abspath(path.parent))), path.name
        )
        if capture is None:
            return False
        observed[path.name] = capture
    if set(observed) != V035_HISTORICAL_ARTIFACT_NAMES or any(
        artifacts.get(name) != capture[2] for name, capture in observed.items()
    ):
        return False
    return all(
        _v034_stable_attempt_file(
            str(Path(os.path.abspath(capture[0].parent))), capture[0].name
        )
        == capture
        for capture in observed.values()
    )


def _v035_single_attempt_topology_pass(attempt: Path) -> bool:
    try:
        run_root = attempt.parents[2]
    except IndexError:
        return False
    expected = (
        run_root
        / "pepglad"
        / "v035_pepglad_3eqs_seed42"
        / "attempt_001"
    )
    if (
        attempt != expected
        or not run_root.is_absolute()
        or Path(os.path.abspath(run_root)) != run_root
    ):
        return False
    try:
        root_info = os.lstat(run_root)
        if (
            stat.S_ISLNK(root_info.st_mode)
            or not stat.S_ISDIR(root_info.st_mode)
            or run_root.resolve(strict=True) != run_root
        ):
            return False
    except (OSError, RuntimeError, ValueError):
        return False

    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    found: list[Path] = []

    def walk(directory_fd: int, relative: PurePosixPath) -> bool:
        before = os.fstat(directory_fd)
        if not stat.S_ISDIR(before.st_mode):
            return False
        try:
            names = sorted(os.listdir(directory_fd))
        except OSError:
            return False
        for name in names:
            try:
                child_lstat = os.stat(
                    name, dir_fd=directory_fd, follow_symlinks=False
                )
            except OSError:
                return False
            if stat.S_ISLNK(child_lstat.st_mode):
                return False
            is_attempt = re.fullmatch(r"attempt_[0-9]{3}", name) is not None
            child_relative = relative / name
            if not stat.S_ISDIR(child_lstat.st_mode):
                if is_attempt:
                    return False
                continue
            try:
                child_fd = os.open(name, directory_flags, dir_fd=directory_fd)
            except OSError:
                return False
            try:
                opened = os.fstat(child_fd)
                if _v034_stat_fingerprint(opened) != _v034_stat_fingerprint(
                    child_lstat
                ):
                    return False
                if is_attempt:
                    found.append(run_root.joinpath(*child_relative.parts))
                elif not walk(child_fd, child_relative):
                    return False
                repeated = os.stat(
                    name, dir_fd=directory_fd, follow_symlinks=False
                )
                if _v034_stat_fingerprint(repeated) != _v034_stat_fingerprint(
                    opened
                ):
                    return False
            finally:
                os.close(child_fd)
        return _v034_stat_fingerprint(os.fstat(directory_fd)) == (
            _v034_stat_fingerprint(before)
        )

    try:
        root_fd = os.open(run_root, directory_flags)
    except OSError:
        return False
    try:
        if _v034_stat_fingerprint(os.fstat(root_fd)) != _v034_stat_fingerprint(
            root_info
        ):
            return False
        if not walk(root_fd, PurePosixPath()):
            return False
        if _v034_stat_fingerprint(os.lstat(run_root)) != _v034_stat_fingerprint(
            os.fstat(root_fd)
        ):
            return False
    finally:
        os.close(root_fd)
    return tuple(found) == (attempt,)


def _v035_run_result_pass(
    result: Mapping[str, Any],
    attempt: Path,
    execution: Mapping[str, Any],
    candidate: Mapping[str, Any],
    qc: Mapping[str, Any],
) -> bool:
    from scripts import run_v034_wave_a_generation as v034_runner

    if type(result) is not dict or set(result) != v034_runner.PASSED_RESULT_FIELDS:
        return False
    string_fields = v034_runner.PASSED_RESULT_FIELDS - {"exit_code"}
    if any(type(result.get(field)) is not str for field in string_fields):
        return False
    runtime_seconds = result.get("runtime_seconds")
    try:
        elapsed = float(runtime_seconds)
    except (TypeError, ValueError):
        return False
    try:
        created_at = datetime.fromisoformat(
            str(result.get("created_at", "")).replace("Z", "+00:00")
        )
    except ValueError:
        return False
    return all(
        (
            math.isfinite(elapsed),
            elapsed > 0,
            created_at.tzinfo is not None,
            created_at.utcoffset() is not None,
            result.get("attempt_dir") == str(attempt),
            result.get("job_id") == "v035_pepglad_3eqs_seed42",
            result.get("method") == "PepGLAD",
            type(result.get("exit_code")) is int,
            result.get("exit_code") == execution.get("exit_code") == 0,
            result.get("status") == execution.get("status") == "passed",
            result.get("design_id") == candidate.get("design_id"),
            result.get("parser_status") == candidate.get("parse_status"),
            result.get("overall_qc_status") == qc.get("overall_qc_status"),
            result.get("overall_qc_status") in v034_runner.PASS_QC_STATUSES,
            result.get("status_reason")
            == "bounded_connectivity_candidate_qc_passed",
        )
    )


def _v035_raw_replay_pass(
    bundle: Mapping[str, Any], job: Mapping[str, str]
) -> bool:
    execution = bundle.get("execution")
    candidate = bundle.get("candidate")
    qc = bundle.get("qc")
    provenance = bundle.get("runtime_provenance")
    if not all(isinstance(value, Mapping) for value in (execution, candidate, qc, provenance)):
        return False
    assert isinstance(execution, Mapping)
    assert isinstance(candidate, Mapping)
    assert isinstance(qc, Mapping)
    assert isinstance(provenance, Mapping)
    attempt_dir_raw = execution.get("attempt_dir")
    files = provenance.get("files")
    if type(attempt_dir_raw) is not str or not isinstance(files, Mapping):
        return False
    attempt = Path(attempt_dir_raw)
    if not all(
        (
            attempt.is_absolute(),
            Path(os.path.abspath(attempt)) == attempt,
            attempt.name == "attempt_001",
            attempt.parent.name == "v035_pepglad_3eqs_seed42",
            attempt.parent.parent.name == "pepglad",
            set(files) == V035_RAW_FILES,
        )
    ):
        return False
    if not _v035_single_attempt_topology_pass(attempt):
        return False
    captured: dict[str, tuple[Path, bytes, str, tuple[int, ...]]] = {}
    for relative in V035_REPLAY_FILES:
        capture = _v034_stable_attempt_file(attempt_dir_raw, relative)
        if capture is None or (
            relative in V035_RAW_FILES and files.get(relative) != capture[2]
        ):
            return False
        captured[relative] = capture
    authorized_job, authorized_execution = _v035_authorized_protocol()
    captured_job = _v034_json_object(captured["job.json"][1])
    captured_execution = _v034_json_object(captured["execution.json"][1])
    captured_run_result = _v034_json_object(captured["run_result.json"][1])
    if not all(
        (
            captured_job == dict(authorized_job) == dict(job),
            captured_execution == dict(authorized_execution),
            isinstance(captured_run_result, Mapping),
        )
    ):
        return False
    candidate_capture = captured["raw/pepglad_candidate.pdb"]
    source_capture = captured["work/codesign/3EQS_0.pdb"]
    runtime_capture = captured["raw/runtime_evidence.json"]
    runtime = _v034_json_object(runtime_capture[1])
    if runtime is None or not _v034_pepglad_runtime_schema_pass(runtime):
        return False
    try:
        runtime_semantic = json.dumps(
            runtime, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    post_stats = runtime.get("post_relax_binder_chirality")
    if not all(
        (
            candidate_capture[1] == source_capture[1],
            candidate_capture[2] == candidate.get("file_sha256"),
            runtime_capture[2] == provenance.get("runtime_evidence_sha256"),
            hashlib.sha256(runtime_semantic).hexdigest()
            == provenance.get("runtime_semantic_sha256"),
            runtime.get("requested_seed") == 42,
            runtime.get("effective_seed") == 42,
            runtime.get("seed_control_status") == "honored",
            runtime.get("recovery_mode") == V034_PEPGLAD_RECOVERY_MODE,
            runtime.get("source_candidate_path") == "work/codesign/3EQS_0.pdb",
            runtime.get("post_relax_path") == "raw/pepglad_candidate.pdb",
            runtime.get("post_relax_sha256") == candidate_capture[2],
            runtime.get("baseline_replay_expected_sha256")
            == V034_PEPGLAD_SEED42_BASELINE_SHA256,
            runtime.get("baseline_replay_observed_sha256") == candidate_capture[2],
            runtime.get("baseline_replay_status")
            == (
                "match"
                if candidate_capture[2] == V034_PEPGLAD_SEED42_BASELINE_SHA256
                else "mismatch"
            ),
            runtime.get("binder_chain") == "B",
            runtime.get("target_input_sha256") == V034_PEPGLAD_TARGET_SHA256,
            runtime.get("target_preflight_verified") is True,
            runtime.get("source_entrypoint_prepatch_sha256")
            == V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            all(runtime.get(field) == value for field, value in V035_PRODUCER_PINS.items()),
            isinstance(post_stats, Mapping),
            post_stats.get("chain") == "B" if isinstance(post_stats, Mapping) else False,
        )
    ):
        return False

    with tempfile.TemporaryDirectory(prefix="v035-harness-replay-") as temporary:
        snapshot = (
            Path(temporary)
            / "pepglad"
            / "v035_pepglad_3eqs_seed42"
            / "attempt_001"
        )
        snapshot.mkdir(parents=True)
        for relative, capture in captured.items():
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(capture[1])
        try:
            adapter = importlib.import_module("scripts.v035_adapters.pepglad")
            replay_candidate, replay_runtime = adapter.parse(job, snapshot)
            replay_qc = adapter.evaluate_candidate(
                job, replay_candidate, replay_runtime, snapshot / "raw"
            )
        except Exception:
            return False
        if not all(
            (
                isinstance(replay_candidate, dict),
                isinstance(replay_runtime, dict),
                isinstance(replay_qc, dict),
                replay_runtime == runtime,
                replay_candidate.get("sequence") == candidate.get("sequence"),
                replay_candidate.get("binder_chain") == candidate.get("binder_chain"),
                replay_candidate.get("parse_status") == candidate.get("parse_status"),
                replay_candidate.get("chirality") == candidate.get("chirality"),
                replay_qc.get("observed_chirality_class")
                == qc.get("observed_chirality_class"),
                replay_qc.get("chirality_status") == qc.get("chirality_status"),
                replay_qc.get("chirality_evaluable") == qc.get("chirality_evaluable"),
                replay_qc.get("chirality_l_count") == qc.get("chirality_l_count"),
                replay_qc.get("chirality_d_count") == qc.get("chirality_d_count"),
                replay_qc.get("chirality_unknown_count")
                == qc.get("chirality_unknown_count"),
                replay_qc.get("baseline_replay_status")
                == qc.get("baseline_replay_status"),
                replay_qc.get("overall_qc_status") == qc.get("overall_qc_status"),
            )
        ):
            return False
        assert isinstance(captured_run_result, Mapping)
        if not _v035_run_result_pass(
            captured_run_result,
            attempt,
            execution,
            candidate,
            qc,
        ):
            return False
    return all(
        (
            _v035_single_attempt_topology_pass(attempt),
            all(
                _v034_stable_attempt_file(attempt_dir_raw, relative) == capture
                for relative, capture in captured.items()
            ),
        )
    )


def _evaluate_v035_connectivity(
    root: Path, gate: Mapping[str, Any], artifacts: ArtifactIndex
) -> GateResult:
    paths = _input_paths(root, gate, artifacts)
    historical_ids = (
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
    )
    historical_gate = {
        **gate,
        "gate_id": "current.v034_bounded_connectivity",
        "evaluator": "v034_bounded_connectivity",
        "inputs": [item for item in historical_ids if item != "v034_execution_matrix"],
        "failure_reason_code": "v034_bounded_connectivity_incomplete",
    }
    historical_result = _evaluate_v034_connectivity(root, historical_gate, artifacts)
    historical_details = dict(historical_result.details)
    historical_state_valid = all(
        (
            historical_result.verdict is GateVerdict.FAIL,
            historical_details.get("structural_checks_passed") is True,
            historical_details.get("primary_supported") == 6,
            historical_details.get("extension_supported") == 6,
        )
    )
    bundle_path = _artifact_path(root, artifacts["v035_pepglad_connectivity_bundle"])
    bundle_capture = _v034_stable_attempt_file(
        str(Path(os.path.abspath(bundle_path.parent))), bundle_path.name
    )
    bundle = _v034_json_object(bundle_capture[1]) if bundle_capture is not None else None
    bundle_schema_valid = _v035_bundle_schema_pass(bundle)
    job_path = _artifact_path(root, artifacts["v035_pepglad_job_manifest"])
    execution_path = _artifact_path(root, artifacts["v035_pepglad_execution_matrix"])
    protocol_valid, job = _v035_protocol_pass(job_path, execution_path)
    historical_paths = tuple(
        _artifact_path(root, artifacts[item]) for item in historical_ids
    )
    digest_valid = (
        _v035_historical_digest_pass(
            bundle.get("historical_v034_bindings", {}), historical_paths
        )
        if bundle_schema_valid and isinstance(bundle, dict)
        else False
    )
    historical_bindings_valid = historical_state_valid and digest_valid
    raw_replay_valid = (
        _v035_raw_replay_pass(bundle, job)
        if bundle_schema_valid and protocol_valid and isinstance(bundle, dict)
        else False
    )
    attempt_matches_matrix = False
    if bundle_schema_valid and isinstance(bundle, dict):
        _, authorized_execution = _v035_authorized_protocol()
        execution = bundle.get("execution", {})
        attempt_dir = execution.get("attempt_dir") if isinstance(execution, dict) else None
        if type(attempt_dir) is str:
            attempt_matches_matrix = Path(attempt_dir).parent == (
                root / authorized_execution["output_root"]
            )
    evidence_valid = all(
        (
            bundle_schema_valid,
            protocol_valid,
            historical_bindings_valid,
            raw_replay_valid,
            attempt_matches_matrix,
            bundle_capture is not None,
            _v034_stable_attempt_file(
                str(Path(os.path.abspath(bundle_path.parent))), bundle_path.name
            )
            == bundle_capture,
        )
    )
    v035_primary_supported = 1 if evidence_valid else 0
    combined = 6 + v035_primary_supported if historical_state_valid else 0
    passed = evidence_valid and combined == 7
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        (
            "Six historical v0.34 primaries plus one independently replayed v0.35 PepGLAD primary satisfy bounded connectivity; scoring remains disabled."
            if passed
            else "v0.35 bounded connectivity evidence is missing, inconsistent, or not independently replayable."
        ),
        paths,
        details=_details(
            historical_primary_supported=historical_details.get(
                "primary_supported", 0
            ),
            v035_primary_supported=v035_primary_supported,
            combined_primary_supported=combined,
            historical_bindings_valid=historical_bindings_valid,
            v035_raw_replay_valid=raw_replay_valid,
            v035_evidence_valid=evidence_valid,
            v035_bundle_schema_valid=bundle_schema_valid,
            v035_protocol_valid=protocol_valid,
        ),
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
            (
                "Unfrozen target set and unresolved controls are explicitly represented."
                if passed
                else "Current target/control boundary is not represented consistently."
            ),
            paths,
            details=details,
        )
    passed = frozen_targets > 0 and missing_controls == 0
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        (
            "Target/control governance is complete."
            if passed
            else "Target set is not frozen with complete controls and leakage review."
        ),
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
        (
            "Known D-Flow 3eqs_B training overlap is recorded as fixture-only."
            if passed
            else "D-Flow training-overlap derivation is missing or inconsistent."
        ),
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
        (
            "The historical unconditional [12-18] RFdiffusion example is retained only as v0.33 blocker evidence."
            if passed
            else "RFdiffusion target-conditioning semantics are not fail-closed."
        ),
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
        and row.get("status_reason")
        == "pepmirror_adapter_attempt_no_supported_output_found"
        for row in candidates
    )
    passed = compact_derivation_valid and d_jobs and blocker_only
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        (
            "The historical v0.33 PepMirror D-peptide row is retained as blocker evidence because mirror transformation evidence was absent."
            if passed
            else "PepMirror chirality semantics are not fail-closed."
        ),
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
    executions = _read_csv(_artifact_path(root, artifacts["v034_execution_results"]))
    manifests = _read_csv(
        _artifact_path(root, artifacts["v034_method_output_manifest"])
    )
    candidates = _read_csv(_artifact_path(root, artifacts["v034_candidate_outputs"]))
    qcs = _read_csv(_artifact_path(root, artifacts["v034_candidate_qc"]))
    runs = _read_csv(_artifact_path(root, artifacts["v034_run_rows"]))
    runtime_provenance = load_json(
        _artifact_path(root, artifacts["v034_runtime_provenance"])
    )
    failure_diagnostics = _v034_json_object(
        _artifact_path(root, artifacts["v034_failure_diagnostics"]).read_bytes()
    ) or {}
    summary = load_json(_artifact_path(root, artifacts["v034_merge_summary"]))
    v035_bundle_path = _artifact_path(
        root, artifacts["v035_pepglad_connectivity_bundle"]
    )
    v035_bundle = (
        _v034_json_object(v035_bundle_path.read_bytes()) or {}
        if v035_bundle_path.is_file()
        else {}
    )

    def walk_runtime(value: Any) -> tuple[set[str], list[str]]:
        keys: set[str] = set()
        values: list[str] = []
        if isinstance(value, Mapping):
            for key, nested in value.items():
                keys.add(str(key))
                nested_keys, nested_values = walk_runtime(nested)
                keys.update(nested_keys)
                values.extend(nested_values)
        elif isinstance(value, list):
            for nested in value:
                nested_keys, nested_values = walk_runtime(nested)
                keys.update(nested_keys)
                values.extend(nested_values)
        elif value is not None:
            values.append(str(value))
        return keys, values

    runtime_keys, runtime_values = walk_runtime(
        {
            "runtime_provenance": runtime_provenance,
            "failure_diagnostics": failure_diagnostics,
            "v035_pepglad_connectivity_bundle": v035_bundle,
        }
    )
    evidence_rows = executions + manifests + candidates + qcs + runs
    fieldnames = {key for row in evidence_rows for key in row} | runtime_keys
    forbidden_result_columns = tuple(
        sorted(
            field
            for field in fieldnames
            if field != "generation_rank"
            and re.search(
                r"(^|_)(score|scores|scoring|rank|ranking|metric|plddt|ptm|iptm|pae|rmsd|tm_score|dockq|confidence|affinity|ddg|energy)(_|$)",
                field.casefold(),
            )
        )
    )
    marker_patterns = (
        "best-performing",
        "best method identified",
        "method_rank=",
        "method_score=",
        "method ranking complete",
        "methods ranked",
        "ranking_complete",
        "scoring_complete",
        "scored candidate",
        "已评分",
        "方法性能可排名",
    )
    forbidden_result_markers = tuple(
        sorted(
            {
                marker
                for row in evidence_rows
                for marker in marker_patterns
                if marker in " ".join(row.values()).casefold()
            }
            | {
                marker
                for marker in marker_patterns
                if marker in " ".join(runtime_values).casefold()
            }
            | {
                marker
                for marker in marker_patterns
                if marker in plan.casefold()
            }
        )
    )
    plan_blocks_scoring = any(
        phrase in plan
        for phrase in (
            "不启动 scoring",
            "不执行 scoring",
            "不进行 scoring",
            "禁止 scoring",
            "不支持 scoring",
        )
    )
    plan_blocks_ranking = any(
        phrase in plan
        for phrase in (
            "不启动 ranking",
            "不执行 ranking",
            "不进行 ranking",
            "禁止 ranking",
            "不写方法排名",
            "不做方法排名",
            "不进行方法排名",
            "禁止方法排名",
            "不支持 ranking",
        )
    ) or bool(
        re.search(
            r"(?:不启动|不执行|不进行|禁止|不支持)\s*scoring\s*[/、和与]\s*ranking",
            plan,
        )
    )
    expected_candidate_rows = int(summary.get("primary_passed", -1)) + int(
        summary.get("extension_passed", -1)
    )
    supported_candidate_rows = sum(
        row.get("supported_candidate") == "yes" for row in candidates
    )
    failure_diagnostic_records = failure_diagnostics.get("records")
    failure_diagnostic_boundary_valid = all(
        (
            set(failure_diagnostics)
            == {"schema_version", "evidence_boundary", "records"},
            failure_diagnostics.get("schema_version") == "v0.34",
            failure_diagnostics.get("evidence_boundary")
            == "failure_diagnostic_only_not_candidate_or_scoring",
            isinstance(failure_diagnostic_records, list),
            len(failure_diagnostic_records) == 1
            if isinstance(failure_diagnostic_records, list)
            else False,
        )
    )
    boundary_valid = (
        summary.get("schema_version") == "v0.34"
        and summary.get("primary_total") == 7
        and isinstance(summary.get("primary_passed"), int)
        and 0 <= summary.get("primary_passed", -1) <= 7
        and summary.get("primary_complete")
        is (summary.get("primary_passed") == summary.get("primary_total"))
        and summary.get("extension_total") == 7
        and isinstance(summary.get("extension_passed"), int)
        and 0 <= summary.get("extension_passed", -1) <= 7
        and summary.get("extension_complete")
        is (summary.get("extension_passed") == summary.get("extension_total"))
        and summary.get("evidence_boundary")
        == "bounded_connectivity_only_not_scoring_or_ranking"
        and supported_candidate_rows == expected_candidate_rows
        and len(candidates) == summary.get("parsed_candidate_rows")
        and failure_diagnostic_boundary_valid
    )
    passed = all(
        (
            boundary_valid,
            plan_blocks_scoring,
            plan_blocks_ranking,
            not forbidden_result_columns,
            not forbidden_result_markers,
        )
    )
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        (
            "v0.34 history and the optional v0.35 incremental bundle remain bounded connectivity evidence; scoring and ranking are disabled."
            if passed
            else "The v0.35 scoring/ranking guard is missing or result evidence was introduced."
        ),
        paths,
        details=_details(
            boundary_valid=boundary_valid,
            candidate_rows=len(candidates),
            failure_diagnostic_boundary_valid=failure_diagnostic_boundary_valid,
            supported_candidate_rows=supported_candidate_rows,
            forbidden_result_columns=forbidden_result_columns,
            forbidden_result_markers=forbidden_result_markers,
            plan_blocks_ranking=plan_blocks_ranking,
            plan_blocks_scoring=plan_blocks_scoring,
        ),
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
        and _claim_semantic_binding_digest(rows) == CLAIM_SEMANTIC_BINDING_SHA256
    )
    artifact_registry = load_json(_artifact_path(root, artifacts["artifact_registry"]))
    evidence_class_by_path = {
        row["path"]: row["evidence_class"] for row in artifact_registry["artifacts"]
    }
    v033_rows = [row for row in rows if "v0.33" in row.get("claim", "")]
    v034_rows = [row for row in rows if "v0.34" in row.get("claim", "")]
    expected_v034_claims = {
        "v0.34 最新合并有 12 条候选记录，6 个 primary 通过基础 QC",
        "v0.34 RFdiffusion 与 ProteinMPNN 只完成 backbone-to-FASTA handoff",
        "v0.34 compact runtime provenance 有 12 条，PepGLAD 最新诊断因 replay mismatch 未纳入",
        "v0.34 D-Flow 3EQS 行只支持连通性检查",
    }
    v034_by_claim = {row.get("claim", ""): row for row in v034_rows}
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
            value.strip()
            for value in row.get("evidence", "").split(";")
            if value.strip()
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
    v034_primary = v034_by_claim.get(
        "v0.34 最新合并有 12 条候选记录，6 个 primary 通过基础 QC", {}
    )
    v034_rf = v034_by_claim.get(
        "v0.34 RFdiffusion 与 ProteinMPNN 只完成 backbone-to-FASTA handoff", {}
    )
    v034_provenance = v034_by_claim.get(
        "v0.34 compact runtime provenance 有 12 条，PepGLAD 最新诊断因 replay mismatch 未纳入",
        {},
    )
    v034_dflow = v034_by_claim.get("v0.34 D-Flow 3EQS 行只支持连通性检查", {})
    v034_claims_valid = all(
        (
            len(v034_rows) == len(expected_v034_claims),
            set(v034_by_claim) == expected_v034_claims,
            v034_primary.get("status") == "supported with verification caveat",
            all(
                wording in v034_primary.get("allowed_wording", "")
                for wording in (
                    "12 条 candidate/QC",
                    "12 条 runtime provenance",
                    "attempt_003",
                    "AWHITLLIFTH",
                    "未晋升候选",
                    "L6/D5",
                    "L4/D7",
                    "pre_openmm_snapshot",
                    "post-OpenMM",
                    "固定 baseline",
                    "e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6",
                    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26",
                    "不证明模型根因",
                    "不证明 OpenMM 无影响",
                )
            ),
            all(
                wording in v034_primary.get("forbidden_wording", "")
                for wording in (
                    "7 个 primary 均可解析",
                    "13 条 runtime provenance",
                    "产生可评分候选",
                    "方法性能可排名",
                    "完整复现",
                )
            ),
            "benchmark/results/pilot_candidate_outputs_v0.34.csv"
            in v034_primary.get("evidence", ""),
            "benchmark/deployment/pilot_execution_results_v0.34.csv"
            in v034_primary.get("evidence", ""),
            "benchmark/results/pilot_runtime_provenance_v0.34.json"
            in v034_primary.get("evidence", ""),
            v034_rf.get("status") == "supported with verification caveat",
            "未线程化 all-Gly backbone" in v034_rf.get("allowed_wording", ""),
            "没有 sequence-resolved structure" in v034_rf.get("allowed_wording", ""),
            "已经 thread 回 backbone" in v034_rf.get("forbidden_wording", ""),
            v034_provenance.get("status") == "supported as limitation",
            "6 个 supported primary"
            in v034_provenance.get("allowed_wording", ""),
            "6 个 supported seed43 candidates"
            in v034_provenance.get("allowed_wording", ""),
            "pepglad_seed42_replay_mismatch"
            in v034_provenance.get("allowed_wording", ""),
            "13 条 provenance" in v034_provenance.get("forbidden_wording", ""),
            "完整可复现" in v034_provenance.get("forbidden_wording", ""),
            v034_dflow.get("status") == "supported as boundary",
            "train overlap" in v034_dflow.get("allowed_wording", ""),
            "公平 scoring 资格" in v034_dflow.get("forbidden_wording", ""),
        )
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
            and "已完成正式 Wave A generation"
            in v033_rows[0].get("forbidden_wording", "")
            and "方法性能可排名" in v033_rows[0].get("forbidden_wording", "")
        )
        and v034_claims_valid
    )
    return _result(
        gate,
        GateVerdict.PASS if passed else GateVerdict.FAIL,
        (
            "The historical v0.33 blocker claim and current v0.34 bounded generation claim remain evidence-scoped."
            if passed
            else "The v0.33/v0.34 claim boundary is missing or promoted."
        ),
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
            v034_claim_rows=len(v034_rows),
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
                    "## Unreleased Harness Engineering Workflow " "(`VERSION=1.2.21`)"
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
        (
            f"Release checkpoint navigation and version boundary are consistent for {version}."
            if passed
            else "Pending release checkpoint documentation is incomplete."
        ),
        paths,
        details=_details(missing_tokens=tuple(missing)),
    )


EVALUATORS = {
    "contract_integrity": _evaluate_contract,
    "artifact_registry_integrity": _evaluate_artifact_registry,
    "migration_parity": _evaluate_migration_parity,
    "kb_validator": _evaluate_kb_validator,
    "v033_baseline": _evaluate_v033,
    "v034_bounded_connectivity": _evaluate_v034_connectivity,
    "v035_bounded_connectivity": _evaluate_v035_connectivity,
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
