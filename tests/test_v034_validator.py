from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

import pytest

from scripts import validate_benchmark_kb


ROOT = Path(__file__).resolve().parents[1]

V034_ARTIFACTS = [
    "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv",
    "benchmark/deployment/pilot_execution_matrix_v0.34.csv",
    "benchmark/deployment/pilot_execution_results_v0.34.csv",
    "benchmark/results/pilot_method_output_manifest_v0.34.csv",
    "benchmark/results/pilot_candidate_outputs_v0.34.csv",
    "benchmark/results/pilot_candidate_qc_v0.34.csv",
    "benchmark/results/pilot_run_v0.34.csv",
    "benchmark/results/pilot_v034_merge_summary.json",
    "benchmark/results/pilot_runtime_provenance_v0.34.json",
    "benchmark/results/pilot_failure_diagnostics_v0.34.json",
    "ops/plans/updated_plan_v0.34.md",
    "ops/audits/v034_bounded_connectivity_audit.md",
]

V034_REPLAY_DIAGNOSTIC_TOKENS = [
    "attempt_003",
    "L6/D5",
    "L4/D7",
    "b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b",
    "e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6",
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26",
    "pre_openmm_snapshot",
]


def _copy_v034_snapshot(destination: Path) -> None:
    for relative_path in V034_ARTIFACTS:
        source = ROOT / relative_path
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _rewrite_csv(path: Path, update) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    update(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _rewrite_provenance(path: Path, update, *, refresh_semantic_hashes: bool) -> None:
    provenance = json.loads(path.read_text(encoding="utf-8"))
    update(provenance["records"])
    if refresh_semantic_hashes:
        for record in provenance["records"]:
            semantic_payload = json.dumps(
                record["evidence"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            record["evidence_semantic_sha256"] = hashlib.sha256(
                semantic_payload
            ).hexdigest()
    path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")


def _prepend_conflicting_json_key(path: Path, key: str, value: object) -> None:
    document = path.read_text(encoding="utf-8")
    assert document.lstrip().startswith("{")
    object_start = document.index("{")
    tampered = (
        document[: object_start + 1]
        + f"\n  {json.dumps(key)}: {json.dumps(value)},"
        + document[object_start + 1 :]
    )
    path.write_text(tampered, encoding="utf-8")


def _replace_job_paths(destination: Path, job_id: str, old: Path, new: Path) -> None:
    old_text = str(old)
    new_text = str(new)
    for relative_path in [
        "benchmark/deployment/pilot_execution_results_v0.34.csv",
        "benchmark/results/pilot_method_output_manifest_v0.34.csv",
        "benchmark/results/pilot_candidate_outputs_v0.34.csv",
        "benchmark/results/pilot_run_v0.34.csv",
    ]:
        path = destination / relative_path

        def update(rows: list[dict[str, str]]) -> None:
            row = next(
                (value for value in rows if value["job_id"] == job_id), None
            )
            if row is None:
                return
            for key, value in row.items():
                row[key] = value.replace(old_text, new_text)

        _rewrite_csv(path, update)


def _copy_pepmlm_attempt(destination: Path, job_id: str) -> Path:
    execution_path = destination / "benchmark/deployment/pilot_execution_results_v0.34.csv"
    with execution_path.open(newline="", encoding="utf-8") as handle:
        execution = next(
            row for row in csv.DictReader(handle) if row["job_id"] == job_id
        )
    source = Path(execution["attempt_dir"])
    target = (
        destination
        / "benchmark_runs/v0.34/pepmlm"
        / job_id
        / source.name
    )
    shutil.copytree(source, target)
    _replace_job_paths(destination, job_id, source, target)
    return target


V034_IDENTITY_FORGERIES = [
    ("v034_pepmlm_sequence_seed42", "source", "source_commit"),
    ("v034_pepmlm_sequence_seed42", "model", "model_weights_sha256"),
    ("v034_pepmlm_sequence_seed42", "environment", "container_image"),
    ("v034_diffpepbuilder_3eqs_seed42", "source", "source_commit"),
    (
        "v034_diffpepbuilder_3eqs_seed42",
        "model",
        "model_asset_sha256.diffpepbuilder_v1.pth",
    ),
    ("v034_diffpepbuilder_3eqs_seed42", "environment", "container_image"),
    ("v034_pepglad_3eqs_seed42", "source", "source_commit"),
    ("v034_pepglad_3eqs_seed42", "model", "model_weights_sha256"),
    ("v034_pepglad_3eqs_seed42", "environment", "container_image"),
    ("v034_dflow_3eqs_seed42", "source", "source_commit"),
    (
        "v034_dflow_3eqs_seed42",
        "source",
        "source_entrypoint_patched_sha256",
    ),
    ("v034_dflow_3eqs_seed42", "source", "seed_patch_sha256"),
    ("v034_dflow_3eqs_seed42", "model", "checkpoint_sha256"),
    (
        "v034_dflow_3eqs_seed42",
        "environment",
        "execution_environment_declared",
    ),
    (
        "v034_dflow_3eqs_seed42",
        "environment",
        "python_executable_sha256",
    ),
    ("v034_pepmirror_3eqs_seed42", "source", "source_commit_expected"),
    ("v034_pepmirror_3eqs_seed42", "source", "generate_py_pre_sha256"),
    ("v034_pepmirror_3eqs_seed42", "source", "mirror_pdb_py_pre_sha256"),
    ("v034_pepmirror_3eqs_seed42", "model", "checkpoint_sha256"),
    (
        "v034_pepmirror_3eqs_seed42",
        "environment",
        "execution_environment_id",
    ),
    ("v034_pepmirror_3eqs_seed42", "environment", "compose_file_sha256"),
    (
        "v034_pepmirror_3eqs_seed42",
        "environment",
        "image_id_observed_pre_run",
    ),
    ("v034_colabdesign_7zkr_seed42", "source", "source_commit"),
    ("v034_colabdesign_7zkr_seed42", "model", "alphafold_params_sha256"),
    ("v034_colabdesign_7zkr_seed42", "environment", "container_image"),
    ("v034_rfdiffusion_mpnn_7zkr_seed42", "source", "rf_source_commit"),
    (
        "v034_rfdiffusion_mpnn_7zkr_seed42",
        "model",
        "rf_checkpoint_sha256",
    ),
    (
        "v034_rfdiffusion_mpnn_7zkr_seed42",
        "environment",
        "rf_container_image",
    ),
    (
        "v034_rfdiffusion_mpnn_7zkr_seed42",
        "environment",
        "rf_container_image_id",
    ),
    (
        "v034_rfdiffusion_mpnn_7zkr_seed42",
        "environment",
        "mpnn_container_image_id",
    ),
    (
        "v034_rfdiffusion_mpnn_7zkr_seed42",
        "model",
        "mpnn_checkpoint_sha256",
    ),
]


def _set_nested_value(document: dict[str, object], path: str, value: str) -> None:
    model_asset_prefix = "model_asset_sha256."
    if path.startswith(model_asset_prefix):
        assets = document["model_asset_sha256"]
        assert isinstance(assets, dict)
        assets[path.removeprefix(model_asset_prefix)] = value
        return
    keys = path.split(".")
    current: dict[str, object] = document
    for key in keys[:-1]:
        child = current[key]
        assert isinstance(child, dict)
        current = child
    current[keys[-1]] = value


def _coordinated_identity_forgery(
    destination: Path, job_id: str, category: str, runtime_field: str
) -> None:
    execution_path = destination / "benchmark/deployment/pilot_execution_results_v0.34.csv"
    with execution_path.open(newline="", encoding="utf-8") as handle:
        execution = next(
            row for row in csv.DictReader(handle) if row["job_id"] == job_id
        )
    source = Path(execution["attempt_dir"])
    target = destination / "benchmark_runs/v0.34" / source.parent.parent.name / job_id / source.name
    runtime_relative = (
        Path("raw/runtime_evidence.json")
        if (source / "raw/runtime_evidence.json").is_file()
        else Path("runtime_evidence.json")
    )
    (target / "raw").mkdir(parents=True)
    shutil.copy2(source / runtime_relative, target / runtime_relative)
    shutil.copy2(source / "method_output_manifest.csv", target / "method_output_manifest.csv")
    shutil.copy2(source / "run_result.json", target / "run_result.json")
    _replace_job_paths(destination, job_id, source, target)

    forged_sha = "1" * 64
    forged_value = forged_sha if "sha256" in runtime_field else "forged_identity"
    runtime_path = target / runtime_relative
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    _set_nested_value(runtime, runtime_field, forged_value)
    if job_id.startswith("v034_pepmirror") and runtime_field == "source_commit_expected":
        runtime["source_commit_observed"] = forged_value
    if category == "model" and job_id.startswith("v034_pepmirror"):
        runtime["checkpoint_revision"] = f"sha256:{forged_sha}"
    runtime_payload = (json.dumps(runtime, indent=2) + "\n").encode("utf-8")
    runtime_path.write_bytes(runtime_payload)

    manifest_fields = {
        "source": "source_commit",
        "model": "model_revision",
        "environment": "environment_id",
    }
    manifest_value = (
        f"sha256:{forged_sha}"
        if category == "model" and job_id.startswith(("v034_dflow", "v034_pepmirror"))
        else "forged_identity"
    )

    def forge_manifest(rows: list[dict[str, str]]) -> None:
        row = next(value for value in rows if value["job_id"] == job_id)
        row[manifest_fields[category]] = manifest_value

    _rewrite_csv(target / "method_output_manifest.csv", forge_manifest)
    _rewrite_csv(
        destination / "benchmark/results/pilot_method_output_manifest_v0.34.csv",
        forge_manifest,
    )

    provenance_path = destination / "benchmark/results/pilot_runtime_provenance_v0.34.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(
        (value for value in provenance["records"] if value["job_id"] == job_id),
        None,
    )
    semantic_payload = json.dumps(
        runtime, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    if record is not None:
        record["evidence"] = runtime
        record["runtime_evidence_sha256"] = hashlib.sha256(runtime_payload).hexdigest()
        record["evidence_semantic_sha256"] = hashlib.sha256(
            semantic_payload
        ).hexdigest()
        provenance_path.write_text(
            json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
        )
    else:
        diagnostic_path = destination / "benchmark/results/pilot_failure_diagnostics_v0.34.json"
        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
        diagnostic_record = diagnostic["records"][0]
        diagnostic_record["attempt_dir"] = str(target)
        diagnostic_record["runtime_evidence"]["sha256"] = hashlib.sha256(
            runtime_payload
        ).hexdigest()
        diagnostic_record["runtime_evidence"]["semantic_sha256"] = hashlib.sha256(
            semantic_payload
        ).hexdigest()
        diagnostic_path.write_text(
            json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8"
        )


def test_v034_current_snapshot_is_a_truthful_incomplete_connectivity_record(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    counts = validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert errors == []
    assert counts == {
        "jobs": 14,
        "execution_rows": 14,
        "method_rows": 13,
        "candidate_rows": 12,
        "qc_rows": 12,
        "run_rows": 14,
        "runtime_provenance_records": 12,
        "failure_diagnostic_records": 1,
        "primary_supported": 6,
        "extension_supported": 6,
    }


@pytest.mark.parametrize(
    ("relative_path", "duplicate_key", "conflicting_value"),
    [
        (
            "benchmark/results/pilot_runtime_provenance_v0.34.json",
            "schema_version",
            "tampered",
        ),
        (
            "benchmark/results/pilot_v034_merge_summary.json",
            "primary_passed",
            7,
        ),
        (
            "benchmark/results/pilot_failure_diagnostics_v0.34.json",
            "schema_version",
            "tampered",
        ),
    ],
)
def test_v034_validator_rejects_duplicate_keys_in_compact_json(
    tmp_path: Path,
    monkeypatch,
    relative_path: str,
    duplicate_key: str,
    conflicting_value: object,
) -> None:
    _copy_v034_snapshot(tmp_path)
    artifact_path = tmp_path / relative_path
    _prepend_conflicting_json_key(artifact_path, duplicate_key, conflicting_value)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    artifact_name = artifact_path.name
    assert any(
        artifact_name in error
        and f"duplicate JSON object key: {duplicate_key}" in error
        for error in errors
    )


@pytest.mark.parametrize(
    ("relative_path", "document"),
    [
        ("benchmark/results/pilot_runtime_provenance_v0.34.json", "[]\n"),
        ("benchmark/results/pilot_v034_merge_summary.json", "[]\n"),
        ("benchmark/results/pilot_failure_diagnostics_v0.34.json", "[]\n"),
        ("benchmark/results/pilot_runtime_provenance_v0.34.json", "{\n"),
        ("benchmark/results/pilot_v034_merge_summary.json", "{\n"),
        ("benchmark/results/pilot_failure_diagnostics_v0.34.json", "{\n"),
    ],
)
def test_v034_validator_reports_invalid_compact_json_without_crashing(
    tmp_path: Path, monkeypatch, relative_path: str, document: str
) -> None:
    _copy_v034_snapshot(tmp_path)
    artifact_path = tmp_path / relative_path
    artifact_path.write_text(document, encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    artifact_name = artifact_path.name
    if document.startswith("["):
        assert f"{artifact_name} must contain a JSON object" in errors
    else:
        assert any(
            error.startswith(f"{artifact_name} is not valid JSON:")
            for error in errors
        )


@pytest.mark.parametrize("record_count", [0, 2])
def test_v034_validator_requires_exactly_one_failure_diagnostic_record(
    tmp_path: Path, monkeypatch, record_count: int
) -> None:
    _copy_v034_snapshot(tmp_path)
    path = tmp_path / "benchmark/results/pilot_failure_diagnostics_v0.34.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = payload["records"][0]
    payload["records"] = [record for _ in range(record_count)]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert (
        "pilot_failure_diagnostics_v0.34.json records must contain exactly 1 item"
        in errors
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_record_key",
        "missing_nested_key",
        "attempt_id",
        "sequence",
        "pre_chirality",
        "post_sha",
        "baseline",
        "runtime_sha",
        "summary_sha",
        "producer_pin",
    ],
)
def test_v034_validator_rejects_failure_diagnostic_contract_tamper(
    tmp_path: Path, monkeypatch, mutation: str
) -> None:
    _copy_v034_snapshot(tmp_path)
    path = tmp_path / "benchmark/results/pilot_failure_diagnostics_v0.34.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = payload["records"][0]
    if mutation == "extra_record_key":
        record["unexpected"] = "tampered"
    elif mutation == "missing_nested_key":
        del record["producer_bindings"]["patch"]["injection_status"]
    elif mutation == "attempt_id":
        record["attempt_id"] = "attempt_999"
    elif mutation == "sequence":
        record["summary"]["sequence"] = "AAAAAAAAAAA"
    elif mutation == "pre_chirality":
        record["pre_openmm"]["chirality"]["l_count"] = 5
    elif mutation == "post_sha":
        record["post_openmm"]["sha256"] = "0" * 64
    elif mutation == "baseline":
        record["baseline"]["status"] = "match"
    elif mutation == "runtime_sha":
        record["runtime_evidence"]["semantic_sha256"] = "0" * 64
    elif mutation == "summary_sha":
        record["summary"]["sha256"] = "0" * 64
    elif mutation == "producer_pin":
        record["producer_bindings"]["observer"]["sha256"] = "0" * 64
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(
        error.startswith("pilot_failure_diagnostics_v0.34.json")
        for error in errors
    )


def test_v034_validator_rejects_false_completion_claim(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    summary_path = tmp_path / "benchmark/results/pilot_v034_merge_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["primary_complete"] = True
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("primary_complete must be false" in error for error in errors)


def test_v034_validator_rejects_extension_after_failed_primary(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    execution_path = tmp_path / "benchmark/deployment/pilot_execution_results_v0.34.csv"

    def update(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed43")
        row.update(
            status="passed",
            overall_qc_status="pass",
            supported_candidate="yes",
            merge_status="supported",
        )

    _rewrite_csv(execution_path, update)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("PepGLAD extension must remain not_run" in error for error in errors)


def test_v034_validator_checks_method_specific_qc_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    qc_path = tmp_path / "benchmark/results/pilot_candidate_qc_v0.34.csv"

    def update(rows: list[dict[str, str]]) -> None:
        by_job = {row["job_id"]: row for row in rows}
        by_job["v034_pepmlm_sequence_seed42"]["noncanonical_status"] = "pass"
        by_job["v034_rfdiffusion_mpnn_7zkr_seed42"]["handoff_status"] = "fail"
        by_job["v034_dflow_3eqs_seed42"]["chirality_status"] = "fail"
        by_job["v034_colabdesign_7zkr_seed42"]["cyclic_status"] = "fail"

    _rewrite_csv(qc_path, update)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("PepMLM partial-X warning" in error for error in errors)
    assert any("RF handoff_status must be pass" in error for error in errors)
    assert any("D-Flow / PeptideDesign chirality_status must be pass" in error for error in errors)
    assert any("ColabDesign cyclic_status must be pass" in error for error in errors)


def test_v034_validator_rejects_scoring_or_ranking_promotion(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    candidate_path = tmp_path / "benchmark/results/pilot_candidate_outputs_v0.34.csv"

    def update(rows: list[dict[str, str]]) -> None:
        rows[0]["notes"] = "best_performing scoring_passed"

    _rewrite_csv(candidate_path, update)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("overclaims best_performing" in error for error in errors)
    assert any("overclaims scoring_passed" in error for error in errors)


def test_v034_validator_rejects_unexpected_pepglad_candidate_and_qc_rows(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    candidate_path = tmp_path / "benchmark/results/pilot_candidate_outputs_v0.34.csv"
    qc_path = tmp_path / "benchmark/results/pilot_candidate_qc_v0.34.csv"

    def add_candidate(rows: list[dict[str, str]]) -> None:
        row = dict(rows[0])
        row.update(
            job_id="v034_pepglad_3eqs_seed42",
            method="PepGLAD",
            design_id="v034_pepglad_3eqs_seed42_candidate_1",
            supported_candidate="no",
        )
        rows.append(row)

    def add_qc(rows: list[dict[str, str]]) -> None:
        row = dict(rows[0])
        row.update(
            job_id="v034_pepglad_3eqs_seed42",
            design_id="v034_pepglad_3eqs_seed42_candidate_1",
            supported_candidate="no",
        )
        rows.append(row)

    _rewrite_csv(candidate_path, add_candidate)
    _rewrite_csv(qc_path, add_qc)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(
        "pilot_candidate_outputs_v0.34.csv must not contain PepGLAD rows" in error
        for error in errors
    )
    assert any(
        "pilot_candidate_qc_v0.34.csv must not contain PepGLAD rows" in error
        for error in errors
    )


def test_v034_validator_rejects_unexpected_pepglad_runtime_provenance(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    provenance_path = tmp_path / "benchmark/results/pilot_runtime_provenance_v0.34.json"

    def add_pepglad_record(records: list[dict[str, object]]) -> None:
        record = json.loads(json.dumps(records[0]))
        record.update(
            job_id="v034_pepglad_3eqs_seed42",
            method="PepGLAD",
            seed_stage="primary",
            random_seed=42,
            attempt_id="attempt_003",
        )
        record["evidence"].update(requested_seed=42, effective_seed=42)
        records.append(record)

    _rewrite_provenance(
        provenance_path, add_pepglad_record, refresh_semantic_hashes=True
    )
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(
        "runtime provenance job set must match the 12 supported jobs" in error
        for error in errors
    )


def test_v034_validator_requires_pepglad_attempt_003_bindings(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    execution_path = tmp_path / "benchmark/deployment/pilot_execution_results_v0.34.csv"
    method_path = tmp_path / "benchmark/results/pilot_method_output_manifest_v0.34.csv"
    run_path = tmp_path / "benchmark/results/pilot_run_v0.34.csv"

    def alter_execution(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
        row["attempt_id"] = "attempt_002"
        row["attempt_dir"] = row["attempt_dir"].replace("attempt_003", "attempt_002")

    def alter_method(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
        row["run_record_id"] = row["run_record_id"].replace(
            "attempt_003", "attempt_002"
        )
        row["raw_output_root"] = row["raw_output_root"].replace(
            "attempt_003", "attempt_002"
        )

    def alter_run(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
        row["attempt_id"] = "attempt_002"

    _rewrite_csv(execution_path, alter_execution)
    _rewrite_csv(method_path, alter_method)
    _rewrite_csv(run_path, alter_run)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("PepGLAD execution must bind attempt_003" in error for error in errors)
    assert any("PepGLAD method manifest must bind attempt_003" in error for error in errors)
    assert any("PepGLAD run row must bind attempt_003" in error for error in errors)


def test_v034_validator_rejects_stale_pepglad_parsed_qc_failure_status(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    execution_path = tmp_path / "benchmark/deployment/pilot_execution_results_v0.34.csv"
    method_path = tmp_path / "benchmark/results/pilot_method_output_manifest_v0.34.csv"
    run_path = tmp_path / "benchmark/results/pilot_run_v0.34.csv"

    def alter_execution(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
        row.update(status="qc_failed", merge_status="qc_failed")

    def alter_method(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
        row.update(parser_status="parsed", status="qc_failed")

    def alter_run(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
        row["status"] = "qc_failed"

    _rewrite_csv(execution_path, alter_execution)
    _rewrite_csv(method_path, alter_method)
    _rewrite_csv(run_path, alter_run)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(
        "PepGLAD execution must remain parse_failed/evidence_incomplete" in error
        for error in errors
    )
    assert any("PepGLAD method manifest must remain parse_failed" in error for error in errors)
    assert any("PepGLAD run row must remain parse_failed" in error for error in errors)


def test_v034_validator_requires_pepglad_replay_mismatch_reason(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    paths = [
        tmp_path / "benchmark/deployment/pilot_execution_results_v0.34.csv",
        tmp_path / "benchmark/results/pilot_method_output_manifest_v0.34.csv",
        tmp_path / "benchmark/results/pilot_run_v0.34.csv",
    ]

    def alter_reason(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
        row["status_reason"] = "stale_reason"

    for path in paths:
        _rewrite_csv(path, alter_reason)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("PepGLAD execution status_reason" in error for error in errors)
    assert any("PepGLAD method manifest status_reason" in error for error in errors)
    assert any("PepGLAD run row status_reason" in error for error in errors)


def test_v034_validator_requires_replay_failure_summary_counts(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    summary_path = tmp_path / "benchmark/results/pilot_v034_merge_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(
        parsed_candidate_rows=13,
        qc_failed_rows=1,
        runtime_provenance_rows=13,
    )
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("parsed_candidate_rows must be 12" in error for error in errors)
    assert any("qc_failed_rows must be 0" in error for error in errors)
    assert any("runtime_provenance_rows must be 12" in error for error in errors)


def test_v034_validator_requires_pepglad_evidence_incomplete_summary_status(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    summary_path = tmp_path / "benchmark/results/pilot_v034_merge_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["job_status"]["v034_pepglad_3eqs_seed42"] = "qc_failed"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("job_status must match the replay-failure snapshot" in error for error in errors)


def test_v034_validator_does_not_promote_summary_diagnostic_sequence(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    summary_path = tmp_path / "benchmark/results/pilot_v034_merge_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["pepglad_diagnostic_sequence"] = "AWHITLLIFTH"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    counts = validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert errors == []
    assert counts["candidate_rows"] == 12


def test_v034_validator_requires_replay_diagnostic_tokens_in_plan_and_audit(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    relative_paths = [
        "ops/plans/updated_plan_v0.34.md",
        "ops/audits/v034_bounded_connectivity_audit.md",
    ]
    for relative_path in relative_paths:
        path = tmp_path / relative_path
        document = path.read_text(encoding="utf-8")
        for index, token in enumerate(V034_REPLAY_DIAGNOSTIC_TOKENS):
            assert token in document
            document = document.replace(token, f"removed-diagnostic-token-{index}")
        path.write_text(document, encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    for relative_path in relative_paths:
        artifact_name = Path(relative_path).name
        for token in V034_REPLAY_DIAGNOSTIC_TOKENS:
            assert f"{artifact_name} missing required token {token}" in errors


def test_v034_validator_rejects_runtime_evidence_semantic_tamper(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    provenance_path = tmp_path / "benchmark/results/pilot_runtime_provenance_v0.34.json"

    def tamper(records: list[dict[str, object]]) -> None:
        for record in records:
            semantic_payload = json.dumps(
                record["evidence"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            record["evidence_semantic_sha256"] = hashlib.sha256(
                semantic_payload
            ).hexdigest()
        record = next(
            value for value in records if value["job_id"] == "v034_pepmlm_sequence_seed42"
        )
        record["evidence"]["model_id"] = "tampered/model"

    _rewrite_provenance(provenance_path, tamper, refresh_semantic_hashes=False)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("evidence_semantic_sha256 mismatch" in error for error in errors)


def test_v034_validator_requires_pepmirror_and_rf_runtime_provenance(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    provenance_path = tmp_path / "benchmark/results/pilot_runtime_provenance_v0.34.json"

    def remove_method_fields(records: list[dict[str, object]]) -> None:
        pepmirror = next(
            value for value in records if value["job_id"] == "v034_pepmirror_3eqs_seed42"
        )
        del pepmirror["evidence"]["mirror_output_sha256"]
        rf = next(
            value
            for value in records
            if value["job_id"] == "v034_rfdiffusion_mpnn_7zkr_seed42"
        )
        del rf["evidence"]["rf_trb_sha256"]

    _rewrite_provenance(
        provenance_path, remove_method_fields, refresh_semantic_hashes=True
    )
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("PepMirror provenance missing mirror_output_sha256" in error for error in errors)
    assert any("RF provenance missing rf_trb_sha256" in error for error in errors)


def test_v034_validator_binds_runtime_provenance_to_seed_and_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    provenance_path = tmp_path / "benchmark/results/pilot_runtime_provenance_v0.34.json"

    def alter_binding(records: list[dict[str, object]]) -> None:
        record = next(
            value
            for value in records
            if value["job_id"] == "v034_diffpepbuilder_3eqs_seed42"
        )
        record["attempt_id"] = "attempt_999"
        record["evidence"]["effective_seed"] = 999

    _rewrite_provenance(provenance_path, alter_binding, refresh_semantic_hashes=True)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("runtime provenance attempt_id" in error for error in errors)
    assert any("runtime evidence seed binding" in error for error in errors)


@pytest.mark.parametrize(
    "mutation",
    [
        "payload_extra",
        "record_extra",
        "evidence_extra_rehashed",
        "nested_extra_rehashed",
        "strict_type_rehashed",
        "nonfinite_rehashed",
    ],
)
def test_v034_validator_requires_exact_finite_runtime_provenance_schema(
    tmp_path: Path, monkeypatch, mutation: str
) -> None:
    _copy_v034_snapshot(tmp_path)
    provenance_path = tmp_path / "benchmark/results/pilot_runtime_provenance_v0.34.json"
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(
        value
        for value in payload["records"]
        if value["job_id"] == "v034_diffpepbuilder_3eqs_seed42"
    )
    if mutation == "payload_extra":
        payload["unexpected"] = "tampered"
    elif mutation == "record_extra":
        record["unexpected"] = "tampered"
    elif mutation == "evidence_extra_rehashed":
        record["evidence"]["unexpected"] = "tampered"
    elif mutation == "nested_extra_rehashed":
        record["evidence"]["model_asset_sha256"]["unexpected.bin"] = "0" * 64
    elif mutation == "strict_type_rehashed":
        record["evidence"]["requested_seed"] = True
    elif mutation == "nonfinite_rehashed":
        record["evidence"]["requested_seed"] = math.nan
    if mutation.endswith("rehashed"):
        semantic_payload = json.dumps(
            record["evidence"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        record["evidence_semantic_sha256"] = hashlib.sha256(
            semantic_payload
        ).hexdigest()
    provenance_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any("runtime provenance exact schema" in error for error in errors)


def test_v034_validator_replays_pepmlm_raw_sequence_not_synchronized_compact_rows(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    candidate_path = tmp_path / "benchmark/results/pilot_candidate_outputs_v0.34.csv"
    run_path = tmp_path / "benchmark/results/pilot_run_v0.34.csv"

    def update(rows: list[dict[str, str]]) -> None:
        row = next(
            value for value in rows if value["job_id"] == "v034_pepmlm_sequence_seed42"
        )
        row["sequence"] = "YYX"

    _rewrite_csv(candidate_path, update)
    _rewrite_csv(run_path, update)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(
        "v034_pepmlm_sequence_seed42: stable raw replay mismatch" in error
        for error in errors
    )


def test_v034_validator_replays_structure_sequence_and_bytes_not_reported_hashes(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    job_id = "v034_diffpepbuilder_3eqs_seed42"

    def change_sequence(rows: list[dict[str, str]]) -> None:
        row = next(value for value in rows if value["job_id"] == job_id)
        row["sequence"] = "AAAAAAAAAAA"

    def change_hash(rows: list[dict[str, str]]) -> None:
        row = next(value for value in rows if value["job_id"] == job_id)
        row["file_sha256"] = "0" * 64

    _rewrite_csv(
        tmp_path / "benchmark/results/pilot_candidate_outputs_v0.34.csv",
        change_sequence,
    )
    _rewrite_csv(tmp_path / "benchmark/results/pilot_run_v0.34.csv", change_sequence)
    _rewrite_csv(tmp_path / "benchmark/results/pilot_candidate_qc_v0.34.csv", change_hash)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(
        f"{job_id}: stable raw replay mismatch" in error for error in errors
    )


def test_v034_validator_reports_changed_raw_without_crashing(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    job_id = "v034_pepmlm_sequence_seed42"
    attempt = _copy_pepmlm_attempt(tmp_path, job_id)
    output = attempt / "raw/pepmlm_generated.csv"
    output.write_text(
        output.read_text(encoding="utf-8").replace("WWX", "YYX"),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(f"{job_id}: stable raw replay mismatch" in error for error in errors)


def test_v034_validator_reports_missing_raw_without_crashing(
    tmp_path: Path, monkeypatch
) -> None:
    _copy_v034_snapshot(tmp_path)
    job_id = "v034_pepmlm_sequence_seed42"
    attempt = _copy_pepmlm_attempt(tmp_path, job_id)
    (attempt / "raw/pepmlm_generated.csv").unlink()
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert any(f"{job_id}: stable raw replay mismatch" in error for error in errors)


@pytest.mark.parametrize(
    ("job_id", "category", "runtime_field"),
    V034_IDENTITY_FORGERIES,
)
def test_v034_validator_rejects_coordinated_fixed_identity_forgery(
    tmp_path: Path,
    monkeypatch,
    job_id: str,
    category: str,
    runtime_field: str,
) -> None:
    _copy_v034_snapshot(tmp_path)
    _coordinated_identity_forgery(tmp_path, job_id, category, runtime_field)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    validate_benchmark_kb.check_v034_bounded_connectivity(errors)

    assert f"{job_id}: fixed identity/pin mismatch ({category})" in errors


def test_v034_implementation_and_evidence_files_are_required() -> None:
    expected = {
        "scripts/run_v034_wave_a_generation.py",
        "scripts/parse_v034_generation_outputs.py",
        "scripts/v034_adapters/common.py",
        "scripts/v034_adapters/pepmlm.py",
        "scripts/v034_adapters/diffpepbuilder.py",
        "scripts/v034_adapters/pepglad.py",
        "scripts/v034_adapters/dflow.py",
        "scripts/v034_adapters/pepmirror.py",
        "scripts/v034_adapters/colabdesign.py",
        "scripts/v034_adapters/rfdiffusion_mpnn.py",
        "tests/test_v034_wave_a_generation.py",
        "tests/test_v034_runner.py",
        "tests/test_v034_merge.py",
        "tests/test_v034_adapters_linear.py",
        "tests/test_v034_adapters_chiral.py",
        "tests/test_v034_adapters_topology.py",
        "tests/test_v034_validator.py",
        *V034_ARTIFACTS,
    }

    assert expected <= set(validate_benchmark_kb.REQUIRED_FILES)
