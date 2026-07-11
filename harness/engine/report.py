from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from harness.domains.project_state import evaluate_gate, validate_registry

from .evaluator import resolve_gate_dependencies, roll_up_profile
from .loader import ContractError, load_contract, load_json
from .models import (
    EvaluationResult,
    GateResult,
    GateVerdict,
    HarnessStatus,
    ProfileResult,
    ProjectVerdict,
    canonical_json,
    canonical_digest,
    make_evaluation_id,
)
from .path_policy import is_workspace_source_path
from .signoffs import SignoffContext, validate_signoff_directory


CONTRACT_PATH = Path("harness/contracts/project_acceptance_v1.json")
ARTIFACT_REGISTRY_PATH = Path("harness/registry/artifacts_v1.json")
CLAIM_REGISTRY_PATH = Path("harness/registry/claims_v1.json")
MIGRATION_REGISTRY_PATH = Path("harness/registry/migration_parity_v1.json")
_GIT_CONFIG_ARGUMENTS = (
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.attributesFile=/dev/null",
)


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _git_workspace_paths(root: Path) -> tuple[str, ...]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"LANG", "TMPDIR", "TMP", "TEMP"}
        or key.startswith("LC_")
    }
    environment.update(
        {
            "PATH": os.defpath,
            "HOME": os.devnull,
            "XDG_CONFIG_HOME": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    completed = subprocess.run(
        [
            "git",
            *_GIT_CONFIG_ARGUMENTS,
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        timeout=30,
        env=environment,
    )
    if completed.returncode != 0:
        raise ContractError(
            "cannot enumerate the acceptance source surface: git_enumeration_failed"
        )
    values = completed.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return tuple(sorted({value for value in values if value}))


def workspace_source_digest(
    root: Path, relative_paths: list[str] | tuple[str, ...] | None = None
) -> str:
    """Digest the Git-visible acceptance and legacy-validator source surface."""
    root = root.resolve()
    candidates = relative_paths if relative_paths is not None else _git_workspace_paths(root)
    entries: dict[str, str] = {}
    for relative_path in sorted(set(candidates)):
        normalized = Path(relative_path).as_posix()
        if not is_workspace_source_path(normalized):
            continue
        path = root / normalized
        if path.is_symlink():
            raise ContractError(
                f"acceptance source surface cannot contain symlink: {normalized}"
            )
        elif path.is_file():
            payload = path.read_bytes()
        else:
            payload = b"missing"
        entries[normalized] = hashlib.sha256(payload).hexdigest()
    if not entries:
        raise ContractError("acceptance source surface is empty")
    return canonical_digest(entries)


def collect_evidence_digests(
    root: Path, registry: Mapping[str, Any]
) -> dict[str, str]:
    """Hash only portable tracked evidence explicitly admitted by the registry."""
    root = root.resolve()
    digests: dict[str, str] = {}
    for artifact in registry.get("artifacts", ()):
        if not artifact.get("include_in_evidence_digest", False):
            continue
        artifact_id = str(artifact["artifact_id"])
        if artifact.get("verification_scope") != "tracked":
            raise ContractError(
                f"digest artifact {artifact_id} must use tracked verification scope"
            )
        relative_path = Path(str(artifact["path"]))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ContractError(
                f"digest artifact {artifact_id} must stay inside project root"
            )
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root):
            raise ContractError(
                f"digest artifact {artifact_id} must stay inside project root"
            )
        if artifact.get("format") == "source_tree":
            if relative_path != Path("."):
                raise ContractError(
                    f"source-tree artifact {artifact_id} must use project root path '.'"
                )
            digests[artifact_id] = workspace_source_digest(root)
            continue
        if not path.is_file():
            raise ContractError(f"digest artifact is missing: {artifact_id} ({path})")
        digests[artifact_id] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(sorted(digests.items()))


def _profile(contract: Mapping[str, Any], profile_id: str) -> Mapping[str, Any]:
    for profile in contract["profiles"]:
        if profile["profile_id"] == profile_id:
            return profile
    raise ContractError(f"unknown acceptance profile: {profile_id}")


def _portable_gate_result(root: Path, result: GateResult) -> GateResult:
    evidence = []
    for value in result.evidence:
        path = Path(value)
        try:
            evidence.append(path.relative_to(root).as_posix())
        except ValueError:
            evidence.append(str(path))
    return replace(result, evidence=tuple(evidence))


def _reject_non_finite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _load_strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_non_finite_json_constant,
    )


def generated_artifact_freshness_errors(
    root: Path,
    *,
    contract: Mapping[str, Any],
    expected: EvaluationResult,
) -> tuple[str, ...]:
    errors: list[str] = []
    json_path = root / "ops/acceptance/project_acceptance_report.json"
    markdown_path = root / "ops/acceptance/project_acceptance_report.md"
    request_path = root / "harness/signoffs/signoff_request_v1.json"
    acceptance_path = root / "harness/PROJECT_ACCEPTANCE.md"
    try:
        report = _load_strict_json(json_path)
    except (OSError, ValueError) as exc:
        errors.append(f"report_json:{exc}")
        report = {}
    if canonical_json(report) != canonical_json(evaluation_dict(expected)):
        errors.append("report_json:content")
    try:
        markdown = markdown_path.read_text(encoding="utf-8")
        if markdown != render_report_markdown(expected):
            errors.append("report_markdown:content")
    except OSError as exc:
        errors.append(f"report_markdown:{exc}")
    try:
        request = _load_strict_json(request_path)
    except (OSError, ValueError) as exc:
        errors.append(f"signoff_request:{exc}")
        request = {}
    if canonical_json(request) != canonical_json(signoff_request_dict(expected)):
        errors.append("signoff_request:content")
    try:
        if acceptance_path.read_text(encoding="utf-8") != render_contract_markdown(
            contract
        ):
            errors.append("acceptance_markdown:contract_render")
    except OSError as exc:
        errors.append(f"acceptance_markdown:{exc}")
    return tuple(errors)


def evaluate_project(
    root: Path, profile_id: str, *, require_fresh_generated: bool = True
) -> EvaluationResult:
    root = root.resolve()
    contract = load_contract(root / CONTRACT_PATH)
    artifact_registry = load_json(root / ARTIFACT_REGISTRY_PATH)
    claim_registry = load_json(root / CLAIM_REGISTRY_PATH)
    migration_registry = load_json(root / MIGRATION_REGISTRY_PATH)
    artifact_index = {
        str(row["artifact_id"]): row for row in artifact_registry["artifacts"]
    }
    selected_profile = _profile(contract, profile_id)

    registry_errors = validate_registry(
        root, contract, artifact_registry, claim_registry
    )
    if registry_errors:
        raise ContractError(
            "artifact or claim registry validation failed: " + "; ".join(registry_errors)
        )

    contract_digest = canonical_digest(contract)
    registry_digest = canonical_digest(
        {
            "artifact_registry": artifact_registry,
            "claim_registry": claim_registry,
            "migration_registry": migration_registry,
        }
    )
    evidence_digests = collect_evidence_digests(root, artifact_registry)
    evidence_digest = canonical_digest(evidence_digests)
    evaluation_id = make_evaluation_id(
        contract_digest=contract_digest,
        registry_digest=registry_digest,
        evaluator_version=str(contract["evaluator_version"]),
        evidence_digests=evidence_digests,
    )

    selected_gate_ids = set(selected_profile["required_gate_ids"])
    selected_gates = [
        gate for gate in contract["gates"] if gate["gate_id"] in selected_gate_ids
    ]
    raw_results = {
        str(gate["gate_id"]): _portable_gate_result(
            root, evaluate_gate(root, gate, artifact_index)
        )
        for gate in selected_gates
    }
    gate_results = resolve_gate_dependencies(selected_gates, raw_results)

    signoffs = validate_signoff_directory(
        root / "harness/signoffs",
        SignoffContext(
            contract_id=str(contract["contract_id"]),
            contract_version=str(contract["contract_version"]),
            contract_digest=contract_digest,
            profile_id=profile_id,
            evaluation_id=evaluation_id,
            evidence_digest=evidence_digest,
            required_roles=tuple(selected_profile.get("required_signoff_roles", ())),
            repository_root=str(root),
        ),
    )

    def current_profile_result() -> ProfileResult:
        value = roll_up_profile(
            selected_profile, gate_results, signoffs.valid_signoff_roles
        )
        if signoffs.invalid_signoffs:
            return ProfileResult(
                profile_id=profile_id,
                harness_status=HarnessStatus.ERROR,
                project_status=ProjectVerdict.NOT_ACCEPTED,
                reason_codes=tuple(
                    sorted({issue.reason_code for issue in signoffs.invalid_signoffs})
                ),
                missing_signoff_roles=signoffs.missing_roles,
            )
        return value

    def build_result() -> EvaluationResult:
        return EvaluationResult(
            evaluation_id=evaluation_id,
            contract_id=str(contract["contract_id"]),
            contract_version=str(contract["contract_version"]),
            evaluator_version=str(contract["evaluator_version"]),
            profile=current_profile_result(),
            gate_results=tuple(
                gate_results[str(gate_id)]
                for gate_id in selected_profile["required_gate_ids"]
            ),
            contract_digest=contract_digest,
            registry_digest=registry_digest,
            evidence_digest=evidence_digest,
            evidence_digests=tuple(evidence_digests.items()),
            required_signoff_roles=tuple(
                selected_profile.get("required_signoff_roles", ())
            ),
            valid_signoff_roles=signoffs.valid_roles,
            stale_signoff_files=tuple(issue.path for issue in signoffs.stale_signoffs),
            invalid_signoff_files=tuple(issue.path for issue in signoffs.invalid_signoffs),
        )

    result = build_result()
    if require_fresh_generated and "release.checkpoint_integrity" in gate_results:
        freshness_errors = generated_artifact_freshness_errors(
            root, contract=contract, expected=result
        )
        if freshness_errors:
            release_result = gate_results["release.checkpoint_integrity"]
            gate_results["release.checkpoint_integrity"] = replace(
                release_result,
                verdict=GateVerdict.FAIL,
                reason_code="generated_artifact_stale",
                message="Generated acceptance artifacts do not match this evaluation.",
                details=release_result.details
                + (("freshness_errors", freshness_errors),),
            )
            gate_results = resolve_gate_dependencies(selected_gates, gate_results)
            result = build_result()
    return result


def _json_compatible(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("JSON mappings require string keys")
        return {key: _json_compatible(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("non-finite floats are not JSON compatible")
        return value
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise TypeError(f"{type(value).__name__} is not JSON compatible")


def gate_result_dict(result: GateResult) -> dict[str, Any]:
    return _json_compatible(
        {
            "gate_id": result.gate_id,
            "domain": result.domain,
            "severity": result.severity.value,
            "verdict": result.verdict.value,
            "reason_code": result.reason_code,
            "message": result.message,
            "evidence": list(result.evidence),
            "failure_status": result.failure_status.value,
            "details": dict(result.details),
        }
    )


def evaluation_dict(result: EvaluationResult) -> dict[str, Any]:
    return {
        "evaluation_id": result.evaluation_id,
        "contract_id": result.contract_id,
        "contract_version": result.contract_version,
        "contract_digest": result.contract_digest,
        "evaluator_version": result.evaluator_version,
        "profile_id": result.profile.profile_id,
        "harness_status": result.profile.harness_status.value,
        "project_status": result.profile.project_status.value,
        "reason_codes": list(result.profile.reason_codes),
        "required_signoff_roles": list(result.required_signoff_roles),
        "missing_signoff_roles": list(result.profile.missing_signoff_roles),
        "valid_signoff_roles": list(result.valid_signoff_roles),
        "stale_signoff_files": list(result.stale_signoff_files),
        "invalid_signoff_files": list(result.invalid_signoff_files),
        "registry_digest": result.registry_digest,
        "evidence_digest": result.evidence_digest,
        "evidence_digests": dict(result.evidence_digests),
        "gate_results": [gate_result_dict(gate) for gate in result.gate_results],
    }


def render_contract_markdown(contract: Mapping[str, Any]) -> str:
    lines = [
        "# Pep Design 项目验收契约",
        "",
        "> 本文件由 `harness/contracts/project_acceptance_v1.json` 生成；JSON 契约为机器权威来源。",
        "",
        f"- Contract ID: `{contract['contract_id']}`",
        f"- Contract version: `{contract['contract_version']}`",
        f"- Evaluator version: `{contract['evaluator_version']}`",
        "",
        "## 验收 Profiles",
        "",
        "| Profile | 含义 | 必需签核 |",
        "|:---|:---|:---|",
    ]
    for profile in contract["profiles"]:
        roles = ", ".join(f"`{role}`" for role in profile["required_signoff_roles"])
        lines.append(
            f"| `{profile['profile_id']}` | {profile['description']} | {roles or '无'} |"
        )
    lines.extend(
        [
            "",
            "## Gates",
            "",
            "| Gate | Domain | Severity | Pass condition |",
            "|:---|:---|:---|:---|",
        ]
    )
    for gate in contract["gates"]:
        lines.append(
            f"| `{gate['gate_id']}` | `{gate['domain']}` | `{gate['severity']}` | {gate['pass_condition']} |"
        )
    lines.extend(
        [
            "",
            "## 固定边界",
            "",
            "`check` 只读；`render` 才可更新生成报告。Critical/Major gate 不通过时项目不得验收。签核仅确认既有 machine evaluation，不能 waiver 或 override 失败项。",
            "",
        ]
    )
    return "\n".join(lines)


def render_report_markdown(result: EvaluationResult) -> str:
    lines = [
        "# Pep Design 项目验收报告",
        "",
        "> 本文件与 `project_acceptance_report.json` 来自同一确定性 evaluation。",
        "",
        f"- Evaluation ID: `{result.evaluation_id}`",
        f"- Profile: `{result.profile.profile_id}`",
        f"- Harness status: `{result.profile.harness_status.value}`",
        f"- Project status: `{result.profile.project_status.value}`",
        f"- Evidence digest: `{result.evidence_digest}`",
        f"- Missing signoff roles: {', '.join(result.profile.missing_signoff_roles) or 'none'}",
        "",
        "## Gate 结果",
        "",
        "| Gate | Severity | Verdict | Reason |",
        "|:---|:---|:---|:---|",
    ]
    for gate in result.gate_results:
        lines.append(
            f"| `{gate.gate_id}` | `{gate.severity.value}` | `{gate.verdict.value}` | `{gate.reason_code}` |"
        )
    lines.append("")
    return "\n".join(lines)


def signoff_request_dict(result: EvaluationResult) -> dict[str, Any]:
    return {
        "contract_id": result.contract_id,
        "contract_version": result.contract_version,
        "contract_digest": result.contract_digest,
        "profile_id": result.profile.profile_id,
        "evaluation_id": result.evaluation_id,
        "evidence_digest": result.evidence_digest,
        "required_roles": list(result.required_signoff_roles),
        "missing_roles": list(result.profile.missing_signoff_roles),
        "decision_required": "approved",
        "waiver_or_override_allowed": False,
    }


def render_outputs(root: Path, result: EvaluationResult) -> None:
    root = root.resolve()
    contract = load_contract(root / CONTRACT_PATH)
    outputs = {
        root / "harness/PROJECT_ACCEPTANCE.md": render_contract_markdown(contract),
        root / "ops/acceptance/project_acceptance_report.json": json.dumps(
            evaluation_dict(result),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        root / "ops/acceptance/project_acceptance_report.md": render_report_markdown(
            result
        ),
        root / "harness/signoffs/signoff_request_v1.json": json.dumps(
            signoff_request_dict(result),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
