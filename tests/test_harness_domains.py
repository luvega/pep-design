from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

import pytest

from harness.domains import project_state
from harness.domains.project_state import _v034_parsed_failure_valid, evaluate_gate
from harness.engine.loader import load_contract, load_json
from harness.engine.models import GateVerdict, ProjectVerdict
from scripts import validate_benchmark_kb
from scripts.run_v035_pepglad_connectivity import (
    AUTHORIZED_EXECUTION,
    AUTHORIZED_JOB,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_contract(ROOT / "harness/contracts/project_acceptance_v1.json")
REGISTRY = load_json(ROOT / "harness/registry/artifacts_v1.json")
ARTIFACTS = {row["artifact_id"]: row for row in REGISTRY["artifacts"]}
GATES = {row["gate_id"]: row for row in CONTRACT["gates"]}


def evaluate(gate_id: str, root: Path = ROOT):
    synthetic_marker = root / ".v034_compact_logic_fixture"
    if synthetic_marker.is_file():
        with patch.object(project_state, "_v034_raw_replay_pass", return_value=True):
            return evaluate_gate(root, GATES[gate_id], ARTIFACTS)
    return evaluate_gate(root, GATES[gate_id], ARTIFACTS)


def copy_artifacts(tmp_path: Path, artifact_ids: list[str]) -> None:
    for artifact_id in artifact_ids:
        rel = Path(ARTIFACTS[artifact_id]["path"])
        source = ROOT / rel
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


V034_EVIDENCE_ARTIFACT_IDS = [
    "v034_job_manifest",
    "v034_execution_results",
    "v034_method_output_manifest",
    "v034_candidate_outputs",
    "v034_candidate_qc",
    "v034_run_rows",
    "v034_runtime_provenance",
    "v034_failure_diagnostics",
    "v034_merge_summary",
]


V035_HISTORICAL_ARTIFACT_IDS = [
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
]

V035_TEST_ARTIFACT_PATHS = {
    "v035_pepglad_job_manifest": (
        "benchmark/input_sets/pilot_pepglad_job_manifest_v0.35.csv"
    ),
    "v035_pepglad_execution_matrix": (
        "benchmark/deployment/pilot_pepglad_execution_matrix_v0.35.csv"
    ),
    "v035_pepglad_connectivity_bundle": (
        "benchmark/results/pilot_pepglad_connectivity_v0.35.json"
    ),
}

V035_AUTHORIZED_JOB_ROW = dict(AUTHORIZED_JOB)
V035_AUTHORIZED_EXECUTION_ROW = dict(AUTHORIZED_EXECUTION)


def copy_current_v034_evidence(tmp_path: Path) -> None:
    copy_artifacts(tmp_path, V034_EVIDENCE_ARTIFACT_IDS)


def _write_or_copy_v035_protocol_artifact(
    tmp_path: Path,
    artifact_id: str,
    expected_row: dict[str, str],
) -> None:
    relative = Path(
        ARTIFACTS.get(artifact_id, {}).get(
            "path", V035_TEST_ARTIFACT_PATHS[artifact_id]
        )
    )
    source = ROOT / relative
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_file():
        shutil.copy2(source, target)
    else:
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(expected_row), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerow(expected_row)

    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert all(rows[0].get(key) == value for key, value in expected_row.items())


def write_v035_harness_fixture(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    from tests.test_v035_merge import _bundle
    from tests.test_v035_validator import _write_raw_replay_fixture

    copy_artifacts(tmp_path, V035_HISTORICAL_ARTIFACT_IDS)
    _write_or_copy_v035_protocol_artifact(
        tmp_path, "v035_pepglad_job_manifest", V035_AUTHORIZED_JOB_ROW
    )
    _write_or_copy_v035_protocol_artifact(
        tmp_path, "v035_pepglad_execution_matrix", V035_AUTHORIZED_EXECUTION_ROW
    )
    bundle = _bundle()
    historical = bundle["historical_v034_bindings"]
    assert isinstance(historical, dict)
    bound_artifacts = historical["artifacts"]
    assert isinstance(bound_artifacts, dict)
    for artifact_id in V035_HISTORICAL_ARTIFACT_IDS:
        artifact_path = tmp_path / ARTIFACTS[artifact_id]["path"]
        bound_artifacts[artifact_path.name] = hashlib.sha256(
            artifact_path.read_bytes()
        ).hexdigest()

    _write_raw_replay_fixture(tmp_path / "benchmark_runs/v0.35", bundle)
    bundle_path = tmp_path / ARTIFACTS.get(
        "v035_pepglad_connectivity_bundle",
        {"path": V035_TEST_ARTIFACT_PATHS["v035_pepglad_connectivity_bundle"]},
    )["path"]
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bundle_path, bundle


def evaluate_v035(root: Path):
    artifacts = dict(ARTIFACTS)
    for artifact_id, path in V035_TEST_ARTIFACT_PATHS.items():
        artifacts.setdefault(
            artifact_id, {"path": path, "verification_scope": "tracked"}
        )
    gate = GATES.get(
        "current.v035_bounded_connectivity",
        {
            "gate_id": "current.v035_bounded_connectivity",
            "domain": "execution_provenance",
            "severity": "Critical",
            "evaluator": "v035_bounded_connectivity",
            "inputs": V035_HISTORICAL_ARTIFACT_IDS
            + [
                "v035_pepglad_job_manifest",
                "v035_pepglad_execution_matrix",
                "v035_pepglad_connectivity_bundle",
            ],
            "failure_reason_code": "v035_bounded_connectivity_incomplete",
        },
    )
    return evaluate_gate(root, gate, artifacts)


def _write_v035_bundle(path: Path, bundle: dict[str, object]) -> None:
    path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _coordinate_v034_history_tamper(
    tmp_path: Path, bundle: dict[str, object]
) -> None:
    execution_path = tmp_path / ARTIFACTS["v034_execution_results"]["path"]

    def mutate(rows: list[dict[str, str]]) -> None:
        row = next(
            item
            for item in rows
            if item["seed_stage"] == "primary"
            and item["supported_candidate"] == "yes"
        )
        row["overall_qc_status"] = "fail"

    rewrite_csv(execution_path, mutate)
    bundle["historical_v034_bindings"]["artifacts"][execution_path.name] = (
        hashlib.sha256(execution_path.read_bytes()).hexdigest()
    )


def _coordinate_v035_raw_tamper(bundle: dict[str, object]) -> None:
    attempt = Path(bundle["execution"]["attempt_dir"])
    candidate = attempt / bundle["candidate"]["structure_path"]
    source_candidate = attempt / "work/codesign/3EQS_0.pdb"
    runtime_path = attempt / bundle["runtime_provenance"]["runtime_evidence_path"]

    original = candidate.read_bytes()
    mutated = original.replace(b" ALA B   1", b" CYS B   1", 1)
    assert mutated != original
    candidate.write_bytes(mutated)
    source_candidate.write_bytes(mutated)
    candidate_sha = hashlib.sha256(mutated).hexdigest()

    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["post_relax_sha256"] = candidate_sha
    runtime["baseline_replay_observed_sha256"] = candidate_sha
    runtime_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    runtime_sha = hashlib.sha256(runtime_path.read_bytes()).hexdigest()
    runtime_semantic_sha = hashlib.sha256(
        json.dumps(
            runtime, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()

    bundle["candidate"]["file_sha256"] = candidate_sha
    provenance = bundle["runtime_provenance"]
    provenance["baseline_observed_sha256"] = candidate_sha
    provenance["runtime_evidence_sha256"] = runtime_sha
    provenance["runtime_semantic_sha256"] = runtime_semantic_sha
    provenance["files"].update(
        {
            "raw/pepglad_candidate.pdb": candidate_sha,
            "raw/runtime_evidence.json": runtime_sha,
            "work/codesign/3EQS_0.pdb": candidate_sha,
        }
    )


def rewrite_csv(path: Path, update) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    update(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_complete_v034_evidence(
    tmp_path: Path, *, extension_methods: set[str] | None = None
) -> None:
    # This synthetic 7/7 fixture isolates compact-table logic. The evaluate()
    # helper bypasses only raw replay for this marked root; dedicated replay
    # tests use the real immutable attempts and never create this marker.
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".v034_compact_logic_fixture").write_text(
        "synthetic compact-logic fixture; raw replay covered separately\n",
        encoding="utf-8",
    )
    _write_legacy_synthetic_v034_evidence(
        tmp_path, extension_methods=extension_methods
    )


def _write_legacy_synthetic_v034_evidence(
    tmp_path: Path, *, extension_methods: set[str] | None = None
) -> None:
    copy_artifacts(tmp_path, ["v034_job_manifest", "v034_failure_diagnostics"])
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    primary = [row for row in jobs if row["seed_stage"] == "primary"]
    extension_methods = extension_methods or set()
    passed_job_ids = {row["job_id"] for row in primary} | {
        row["job_id"]
        for row in jobs
        if row["seed_stage"] == "extension" and row["method"] in extension_methods
    }
    execution_rows: list[dict[str, object]] = []
    manifest_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    qc_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []
    provenance_rows: list[dict[str, object]] = []

    for job in jobs:
        passed = job["job_id"] in passed_job_ids
        design_id = f"{job['job_id']}_candidate_1" if passed else ""
        legacy_pepglad = (
            passed
            and job["method"] == "PepGLAD"
            and job["seed_stage"] == "primary"
        )
        attempt_id = "attempt_002" if legacy_pepglad else ("attempt_001" if passed else "")
        attempt_dir = (
            tmp_path / "external" / job["job_id"] / attempt_id
            if legacy_pepglad
            else (
                Path(f"/external/{job['job_id']}/{attempt_id}")
                if passed
                else Path()
            )
        )
        if legacy_pepglad:
            baseline = (
                ROOT
                / "benchmark_runs/v0.34/pepglad/v034_pepglad_3eqs_seed42/"
                "attempt_002/raw/pepglad_candidate.pdb"
            )
            if not baseline.is_file():
                pytest.skip("external v0.34 PepGLAD attempt_002 is not present")
            structure_path = attempt_dir / "raw/pepglad_candidate.pdb"
            source_candidate = attempt_dir / "work/codesign/3EQS_0.pdb"
            structure_path.parent.mkdir(parents=True)
            source_candidate.parent.mkdir(parents=True)
            shutil.copy2(baseline, structure_path)
            shutil.copy2(baseline, source_candidate)
            file_sha256 = _file_sha256(structure_path)
            file_size_bytes = str(structure_path.stat().st_size)
        else:
            structure_path = (
                attempt_dir / "raw/candidate.pdb"
                if passed and job["expected_binder_chain"] != "not_applicable"
                else Path()
            )
            source_candidate = Path()
            file_sha256 = "4" * 64
            file_size_bytes = "100"
        source_output_path = (
            structure_path
            if legacy_pepglad or (passed and job["method"] == "PepMirror")
            else (attempt_dir / "raw/candidate.out" if passed else Path())
        )
        execution_rows.append(
            {
                "execution_id": f"exec_{job['job_id']}",
                "job_id": job["job_id"],
                "method": job["method"],
                "target_id": job["target_id"],
                "peptide_type": job["peptide_type"],
                "chirality": job["chirality"],
                "cyclic": job["cyclic"],
                "seed_stage": job["seed_stage"],
                "random_seed": job["random_seed"],
                "attempt_id": attempt_id,
                "attempt_dir": str(attempt_dir) if passed else "",
                "status": "passed" if passed else "not_run",
                "overall_qc_status": "pass" if passed else "not_run",
                "supported_candidate": "yes" if passed else "no",
                "merge_status": "supported" if passed else "not_run",
                "status_reason": (
                    "bounded_connectivity_candidate_qc_passed"
                    if passed
                    else "no_attempt_recorded"
                ),
            }
        )
        run_rows.append(
            {
                "design_id": design_id,
                "job_id": job["job_id"],
                "method": job["method"],
                "target_id": job["target_id"],
                "peptide_type": job["peptide_type"],
                "chirality": job["chirality"],
                "cyclic": job["cyclic"],
                "seed_stage": job["seed_stage"],
                "random_seed": job["random_seed"],
                "attempt_id": attempt_id,
                "status": "passed" if passed else "not_run",
                "overall_qc_status": "pass" if passed else "not_run",
                "supported_candidate": "yes" if passed else "no",
                "sequence": "ACD" if passed else "",
                "structure_path": (
                    str(structure_path)
                    if passed and job["expected_binder_chain"] != "not_applicable"
                    else ""
                ),
                "status_reason": (
                    "bounded_connectivity_candidate_qc_passed"
                    if passed
                    else "no_attempt_recorded"
                ),
                "notes": "Bounded connectivity evidence only; not scoring, ranking, or Benchmark result",
            }
        )
        if not passed:
            continue
        manifest_rows.append(
            {
                "run_record_id": f"{job['job_id']}_{attempt_id}",
                "job_id": job["job_id"],
                "method": job["method"],
                "execution_stage": job["seed_stage"],
                "source_commit": (
                    "3" * 40
                    if job["method"] == "D-Flow / PeptideDesign"
                    else (
                        "9" * 40
                        if job["method"] == "PepMirror"
                        else (
                            f"RFdiffusion@{'b' * 40};ProteinMPNN@{'c' * 40}"
                            if job["method"] == "RFdiffusion + ProteinMPNN"
                            else (
                                "bad015ca50c312a89482adb5220c3d907f13df5c"
                                if job["method"] == "PepGLAD"
                                else "1" * 40
                            )
                        )
                    )
                ),
                "model_revision": (
                    "sha256:" + "8" * 64
                    if job["method"] in {"D-Flow / PeptideDesign", "PepMirror"}
                    else (
                        "RFdiffusion_external_models;proteinmpnn_v_48_020.pt"
                        if job["method"] == "RFdiffusion + ProteinMPNN"
                        else (
                            "codesign.ckpt_external_manifest_v0.21"
                            if job["method"] == "PepGLAD"
                            else "sha256:" + "2" * 64
                        )
                    )
                ),
                "environment_id": (
                    "host:.venv/dflow-v023"
                    if job["method"] == "D-Flow / PeptideDesign"
                    else (
                        "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror"
                        if job["method"] == "PepMirror"
                        else (
                            "test-rf-image + test-mpnn-image"
                            if job["method"] == "RFdiffusion + ProteinMPNN"
                            else (
                                "pd-benchmark-methods-gpu:0.21/bench-pepglad"
                                if job["method"] == "PepGLAD"
                                else "test-environment@sha256:" + "3" * 64
                            )
                        )
                    )
                ),
                "command": "test-runner --bounded",
                "raw_output_root": str(attempt_dir / "raw"),
                "stdout_log": str(attempt_dir / "stdout.log"),
                "stderr_log": str(attempt_dir / "stderr.log"),
                "runtime_seconds": "1.000",
                "exit_code": "0",
                "parser_status": "parsed",
                "overall_qc_status": "pass",
                "status": "passed",
                "status_reason": "bounded_connectivity_candidate_qc_passed",
            }
        )
        candidate_rows.append(
            {
                "design_id": design_id,
                "job_id": job["job_id"],
                "method": job["method"],
                "target_id": job["target_id"],
                "generation_rank": "1",
                "sequence": "ACD",
                "structure_path": (
                    str(structure_path)
                    if job["expected_binder_chain"] != "not_applicable"
                    else ""
                ),
                "source_output_path": str(source_output_path),
                "binder_chain": job["expected_binder_chain"],
                "peptide_type": job["peptide_type"],
                "chirality": job["chirality"],
                "cyclic": job["cyclic"],
                "parse_status": "parsed",
                "status_reason": "parsed",
                "notes": "Bounded connectivity evidence only; not scoring, ranking, or Benchmark result",
                "supported_candidate": "yes",
            }
        )
        qc_rows.append(
            {
                "job_id": job["job_id"],
                "design_id": design_id,
                "overall_qc_status": "pass",
                "status_reason": "all_required_checks_passed",
                "file_sha256": file_sha256,
                "file_size_bytes": file_size_bytes,
                "file_status": "pass",
                "length_status": "pass",
                "parse_status": "pass",
                "seed_status": "pass",
                "chain_status": (
                    "pass"
                    if job["expected_binder_chain"] != "not_applicable"
                    else "not_applicable"
                ),
                "sequence_structure_status": (
                    "not_applicable"
                    if job["method"] == "RFdiffusion + ProteinMPNN"
                    else (
                        "pass"
                        if job["expected_binder_chain"] != "not_applicable"
                        else "not_applicable"
                    )
                ),
                "target_binding_status": (
                    "pass"
                    if job["target_binding_check_mode"] != "not_applicable"
                    else "not_applicable"
                ),
                "method_contract_status": "pass",
                "noncanonical_status": "pass",
                "handoff_status": (
                    "pass"
                    if job["method"] == "RFdiffusion + ProteinMPNN"
                    else "not_applicable"
                ),
                "backbone_to_fasta_handoff_status": (
                    "pass"
                    if job["method"] == "RFdiffusion + ProteinMPNN"
                    else "not_applicable"
                ),
                "chirality_evaluable": "",
                "chirality_l_count": "",
                "chirality_d_count": "",
                "chirality_gly_count": "",
                "chirality_unknown_count": "",
                "chirality_status": (
                    "pass"
                    if job["chirality_check_mode"] == "geometry"
                    else "not_applicable"
                ),
                "cyclic_status": (
                    "pass"
                    if job["cyclic_check_mode"] != "not_applicable"
                    else "not_applicable"
                ),
                "mirror_target_atom_identity_status": (
                    "pass" if job["method"] == "PepMirror" else "not_applicable"
                ),
                "mirror_target_atom_count": (
                    "1001" if job["method"] == "PepMirror" else ""
                ),
                "mirror_target_central_inversion_max_residual": (
                    "0.000277" if job["method"] == "PepMirror" else ""
                ),
                "mirror_target_central_inversion_tolerance": (
                    "0.002" if job["method"] == "PepMirror" else ""
                ),
                "mirror_target_central_inversion_status": (
                    "pass" if job["method"] == "PepMirror" else "not_applicable"
                ),
                "mirror_output_atom_identity_status": (
                    "pass" if job["method"] == "PepMirror" else "not_applicable"
                ),
                "mirror_output_atom_count": (
                    "787" if job["method"] == "PepMirror" else ""
                ),
                "mirror_output_central_inversion_max_residual": (
                    "0.000152" if job["method"] == "PepMirror" else ""
                ),
                "mirror_output_central_inversion_tolerance": (
                    "0.002" if job["method"] == "PepMirror" else ""
                ),
                "mirror_output_central_inversion_status": (
                    "pass" if job["method"] == "PepMirror" else "not_applicable"
                ),
                "supported_candidate": "yes",
            }
        )
        evidence: dict[str, object] = {
            "requested_seed": int(job["random_seed"]),
            "effective_seed": int(job["random_seed"]),
            "seed_control_status": "honored",
        }
        if job["method"] == "PepMLM":
            evidence.update(
                source_entrypoint_sha256="1" * 64,
                model_weights_sha256="2" * 64,
                source_commit="3" * 40,
                model_revision="test-model-revision",
                container_image="test-image",
                sampling_strategy="top_k_categorical",
                top_k=5,
            )
        elif job["method"] == "DiffPepBuilder":
            evidence.update(
                source_entrypoint_sha256="1" * 64,
                model_asset_sha256={
                    "diffpepbuilder_v1.pth": "2" * 64,
                    "esm2_t33_650M_UR50D-contact-regression.pt": "3" * 64,
                    "esm2_t33_650M_UR50D.pt": "4" * 64,
                },
                target_context_sha256="3" * 64,
                source_commit="4" * 40,
                container_image="test-image",
            )
        elif job["method"] == "PepGLAD":
            evidence.update(
                source_entrypoint_sha256=(
                    "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
                ),
                model_weights_sha256=(
                    "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
                ),
                source_commit="bad015ca50c312a89482adb5220c3d907f13df5c",
                source_candidate_path="/data/attempt/work/codesign/3EQS_0.pdb",
                container_image="pd-benchmark-methods-gpu:0.21",
                conda_environment="bench-pepglad",
            )
        elif job["method"] == "D-Flow / PeptideDesign":
            evidence.update(
                x_mirror_applied=True,
                seed_patch_sha256="1" * 64,
                candidate_sha256="4" * 64,
                target_context_sha256="2" * 64,
                source_commit="3" * 40,
                source_git_tracked_paths_clean=True,
                source_copy_mode="git_tracked_files_only",
                source_entrypoint_prepatch_sha256="5" * 64,
                source_entrypoint_patched_sha256="6" * 64,
                source_content_manifest_sha256="7" * 64,
                source_tracked_file_count=141,
                checkpoint_sha256="8" * 64,
                execution_environment_type="host_local_python_environment",
                execution_environment_declared="host:.venv/dflow-v023",
                containerized=False,
                python_executable_sha256="9" * 64,
                python_version="3.10.20",
            )
        elif job["method"] == "PepMirror":
            evidence.update(
                mirror_roundtrip_applied=True,
                mirror_input_sha256=job["target_pdb_sha256"],
                mirrored_target_sha256="5" * 64,
                mirrored_generated_sha256="6" * 64,
                mirror_output_sha256="4" * 64,
                mirror_output_path=(
                    f"/external/{job['job_id']}/attempt_001/raw/candidate.pdb"
                ),
                seed_patch_sha256="7" * 64,
                checkpoint_revision="sha256:" + "8" * 64,
                source_commit_expected="9" * 40,
                source_commit_observed="9" * 40,
                source_commit_verified=True,
                source_git_paths_clean=True,
                source_git_checkout_clean=True,
                source_tracked_file_count=179,
                generate_py_pre_sha256="a" * 64,
                generate_py_post_sha256="b" * 64,
                mirror_pdb_py_pre_sha256="c" * 64,
                mirror_pdb_py_post_sha256="c" * 64,
                executed_source_manifest_sha256="d" * 64,
                checkpoint_sha256="8" * 64,
                checkpoint_pin_verified=True,
                checkpoint_container_path=(
                    "/data/benchmark_models/pepmirror/"
                    "pepmirror_commutator_both_v1.ckpt"
                ),
                checkpoint_container_binding_verified=True,
                checkpoint_mount_mode="explicit_read_only_file_bind",
                checkpoint_verified_pre_run=True,
                compose_file_sha256="e" * 64,
                compose_file_verified_pre_run=True,
                compose_service="pd-pyrosetta-methods-gpu-v021",
                compose_service_verified=True,
                compose_image_tag="pd-pyrosetta-methods-gpu:0.21",
                execution_environment_id=(
                    "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror"
                ),
                execution_environment_verified=True,
                mirror_runtime_scope="pinned_compose_conda_environment",
                mirror_runtime_conda_environment="bench-pepmirror",
                image_id_observed_at_prepare="sha256:" + "f" * 64,
                image_id_observed_pre_run="sha256:" + "f" * 64,
                image_identity_stable_pre_run=True,
                executed_source_manifest_verified_pre_run=True,
                target_input_verified_pre_run=True,
                target_preflight_verified=True,
                mirror_commands_in_pinned_container=True,
                package_evidence_sha256="1" * 64,
                execution_preflight_evidence_sha256="2" * 64,
            )
        elif job["method"] == "AfCycDesign / ColabDesign cyclic peptide":
            evidence.update(
                cyclic_offset_applied=True,
                cyclic_offset_type=2,
                candidate_sha256="4" * 64,
                source_notebook_sha256="5" * 64,
                alphafold_params_sha256="6" * 64,
                container_image_id="sha256:" + "7" * 64,
            )
        elif job["method"] == "RFdiffusion + ProteinMPNN":
            evidence.update(
                rf_backbone_sha256="4" * 64,
                rf_trb_sha256="5" * 64,
                mpnn_fasta_sha256="6" * 64,
                rf_checkpoint_sha256=(
                    "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc"
                ),
                mpnn_checkpoint_sha256=(
                    "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd"
                ),
                rf_source_entrypoint_sha256="9" * 64,
                mpnn_source_entrypoint_sha256="a" * 64,
                rf_source_commit="b" * 40,
                mpnn_source_commit="c" * 40,
                rf_container_image="test-rf-image",
                mpnn_container_image="test-mpnn-image",
                rf_container_image_id="sha256:" + "b" * 64,
                mpnn_container_image_id="sha256:" + "c" * 64,
                rf_backbone_path=(
                    f"/external/{job['job_id']}/attempt_001/raw/candidate.pdb"
                ),
                mpnn_fasta_path=(
                    f"/external/{job['job_id']}/attempt_001/raw/candidate.out"
                ),
                rf_contig="[A3-117/0 70-100]",
                rf_hotspots=["A48", "A50", "A51", "A52", "A62", "A65"],
                rf_target_conditioned=True,
                rf_deterministic=True,
                rf_cyclic=False,
                mpnn_fixed_chains=["A"],
                mpnn_designed_chain="B",
                mpnn_record_type="generated_sample",
                mpnn_seed=int(job["random_seed"]),
                structure_representation="unthreaded_rf_backbone",
                sequence_representation="proteinmpnn_generated_fasta",
                sequence_threaded_onto_backbone=False,
                rf_trb_semantic_parser="pickletools_literal_scan_v1",
                rf_trb_semantic_extract={
                    "input_pdb": "/data/input/7zkr_GABARAP.pdb",
                    "num_designs": 1,
                    "design_startnum": int(job["random_seed"]),
                    "deterministic": True,
                    "cyclic": False,
                    "contigs": ["A3-117/0 70-100"],
                    "hotspot_res": ["A48", "A50", "A51", "A52", "A62", "A65"],
                    "sampled_mask": ["A3-117/0", "3-3"],
                },
            )
            evidence["rf_trb_semantic_sha256"] = hashlib.sha256(
                json.dumps(
                    evidence["rf_trb_semantic_extract"],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        runtime_evidence_path = "runtime_evidence.json"
        runtime_evidence_sha256 = "d" * 64
        if legacy_pepglad:
            runtime_path = attempt_dir / "raw/runtime_evidence.json"
            runtime_path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            runtime_evidence_path = "raw/runtime_evidence.json"
            runtime_evidence_sha256 = _file_sha256(runtime_path)
        expected_runtime_fields = project_state.V034_NON_PEPGLAD_RUNTIME_FIELDS.get(
            job["method"]
        )
        if expected_runtime_fields is not None:
            int_fields = project_state.V034_RUNTIME_INT_FIELDS.get(
                job["method"], frozenset()
            )
            bool_fields = project_state.V034_RUNTIME_BOOL_FIELDS.get(
                job["method"], frozenset()
            )
            list_fields = project_state.V034_RUNTIME_LIST_FIELDS.get(
                job["method"], frozenset()
            )
            dict_fields = (
                {"model_asset_sha256"}
                if job["method"] == "DiffPepBuilder"
                else {"rf_trb_semantic_extract"}
                if job["method"] == "RFdiffusion + ProteinMPNN"
                else set()
            )
            for field in expected_runtime_fields:
                if field in evidence:
                    continue
                if field in int_fields:
                    evidence[field] = int(job["random_seed"])
                elif field in bool_fields:
                    evidence[field] = False
                elif field in list_fields:
                    evidence[field] = []
                elif field not in dict_fields:
                    evidence[field] = "synthetic_compact_logic_fixture"
        fixed_identity = project_state.V034_FIXED_IDENTITIES[job["method"]]
        evidence.update(fixed_identity["evidence"])
        manifest_rows[-1].update(fixed_identity["manifest"])
        provenance_rows.append(
            {
                "job_id": job["job_id"],
                "method": job["method"],
                "seed_stage": job["seed_stage"],
                "random_seed": int(job["random_seed"]),
                "attempt_id": attempt_id,
                "runtime_evidence_path": runtime_evidence_path,
                "runtime_evidence_sha256": runtime_evidence_sha256,
                "evidence_semantic_sha256": hashlib.sha256(
                    json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode(
                        "utf-8"
                    )
                ).hexdigest(),
                "evidence": evidence,
            }
        )

    write_rows(tmp_path / ARTIFACTS["v034_execution_results"]["path"], execution_rows)
    write_rows(
        tmp_path / ARTIFACTS["v034_method_output_manifest"]["path"], manifest_rows
    )
    write_rows(tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"], candidate_rows)
    write_rows(tmp_path / ARTIFACTS["v034_candidate_qc"]["path"], qc_rows)
    write_rows(tmp_path / ARTIFACTS["v034_run_rows"]["path"], run_rows)
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        json.dumps(
            {
                "schema_version": "v0.34",
                "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
                "records": provenance_rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema_version": "v0.34",
        "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
        "primary_total": 7,
        "primary_passed": 7,
        "primary_complete": True,
        "extension_total": 7,
        "extension_passed": len(extension_methods),
        "extension_complete": len(extension_methods) == 7,
        "parsed_candidate_rows": len(passed_job_ids),
        "qc_failed_rows": 0,
        "runtime_provenance_rows": len(passed_job_ids),
        "job_status": {row["job_id"]: row["merge_status"] for row in execution_rows},
    }
    summary_path = tmp_path / ARTIFACTS["v034_merge_summary"]["path"]
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_chiral_pdb(path: Path, handedness: str) -> None:
    lines: list[str] = []
    serial = 1
    for residue, hand in enumerate(handedness, start=1):
        origin = float((residue - 1) * 4)
        cb_z = 1.0 if hand == "L" else -1.0
        for atom, xyz in {
            "N": (origin + 1.0, 0.0, 0.0),
            "CA": (origin, 0.0, 0.0),
            "C": (origin, 1.0, 0.0),
            "CB": (origin, 0.0, cb_z),
        }.items():
            x, y, z = xyz
            lines.append(
                f"ATOM  {serial:5d} {atom:^4s} ALA B{residue:4d}    "
                f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           "
                f"{atom[0]:>2s}\n"
            )
            serial += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines) + "END\n", encoding="utf-8")


def _chirality_report(handedness: str) -> dict[str, object]:
    return {
        "chain": "B",
        "evaluable": len(handedness),
        "l_count": handedness.count("L"),
        "d_count": handedness.count("D"),
        "gly_count": 0,
        "unknown_count": 0,
        "status": "pass",
    }


def _write_instrumented_pepglad_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Path | str]:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job = next(
        row
        for row in jobs
        if row["method"] == "PepGLAD" and row["seed_stage"] == "primary"
    )
    job_id = job["job_id"]
    attempt = tmp_path / "external" / job_id / "attempt_003"
    pre = attempt / "raw/pepglad_pre_relax.pdb"
    post = attempt / "raw/pepglad_candidate.pdb"
    source_candidate = attempt / "work/codesign/3EQS_0.pdb"
    observer_patch = attempt / "pepglad_instrument_source.py"
    observer_source = attempt / "pepglad_observer.py"
    seed_wrapper = attempt / "pepglad_seeded_entry.py"
    instrumented_source = attempt / "work/api/run.py"
    patch_path = attempt / "observer_patch_evidence.json"
    runtime_path = attempt / "raw/runtime_evidence.json"

    _write_chiral_pdb(pre, "L" * 11)
    _write_chiral_pdb(post, "L" * 4 + "D" * 7)
    source_candidate.parent.mkdir(parents=True, exist_ok=True)
    source_candidate.write_bytes(post.read_bytes())
    for path, payload in (
        (observer_patch, b"# instrument PepGLAD source\n"),
        (observer_source, b"# observe PepGLAD pre-relax candidate\n"),
        (seed_wrapper, b"# seed PepGLAD deterministically\n"),
        (instrumented_source, b"# instrumented official api/run.py\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    monkeypatch.setattr(
        project_state,
        "V034_PEPGLAD_OBSERVER_PATCH_SHA256",
        _file_sha256(observer_patch),
        raising=False,
    )
    monkeypatch.setattr(
        project_state,
        "V034_PEPGLAD_OBSERVER_SOURCE_SHA256",
        _file_sha256(observer_source),
        raising=False,
    )
    monkeypatch.setattr(
        project_state,
        "V034_PEPGLAD_SEED_WRAPPER_SHA256",
        _file_sha256(seed_wrapper),
        raising=False,
    )
    monkeypatch.setattr(
        project_state,
        "V034_PEPGLAD_INSTRUMENTED_SOURCE_SHA256",
        _file_sha256(instrumented_source),
        raising=False,
    )

    source_entrypoint_sha256 = (
        "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
    )
    target_sha256 = "7086cf2bc4723ccbb4be5ff7f86a50d9db59bc307f4fbb0395a3c6ce3569827d"
    patch = {
        "observer_injection_status": "applied",
        "observer_patch_path": "pepglad_instrument_source.py",
        "observer_patch_sha256": _file_sha256(observer_patch),
        "observer_source_path": "pepglad_observer.py",
        "observer_source_sha256": _file_sha256(observer_source),
        "source_entrypoint_path": "work/api/run.py",
        "source_entrypoint_prepatch_sha256": source_entrypoint_sha256,
        "source_entrypoint_instrumented_sha256": _file_sha256(instrumented_source),
        "source_copy_mode": "attempt_local_copy",
        "target_input_path": "/data/input/3EQS.pdb",
        "target_input_sha256": target_sha256,
        "target_preflight_verified": True,
    }
    patch_path.write_text(
        json.dumps(patch, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    baseline_sha256 = _file_sha256(post)
    monkeypatch.setattr(
        project_state,
        "V034_PEPGLAD_SEED42_BASELINE_SHA256",
        baseline_sha256,
        raising=False,
    )
    runtime: dict[str, object] = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "recovery_mode": "instrumented_official_pipeline",
        "source_candidate_path": "work/codesign/3EQS_0.pdb",
        "pre_relax_path": "raw/pepglad_pre_relax.pdb",
        "pre_relax_sha256": _file_sha256(pre),
        "post_relax_path": "raw/pepglad_candidate.pdb",
        "post_relax_sha256": baseline_sha256,
        "official_candidate_stage": "post_openmm_relaxation",
        "pre_relax_role": "diagnostic_evidence_only",
        "binder_chain": "B",
        "expected_chirality": "L",
        "pre_relax_binder_chirality": _chirality_report("L" * 11),
        "post_relax_binder_chirality": _chirality_report("L" * 4 + "D" * 7),
        "first_observed_chirality_failure_stage": "post_openmm_relaxation",
        "baseline_replay_expected_sha256": baseline_sha256,
        "baseline_replay_observed_sha256": baseline_sha256,
        "baseline_replay_status": "match",
        "observer_patch_evidence_path": "observer_patch_evidence.json",
        "observer_patch_evidence_sha256": _file_sha256(patch_path),
        "observer_patch_path": "pepglad_instrument_source.py",
        "observer_patch_sha256": _file_sha256(observer_patch),
        "observer_source_path": "pepglad_observer.py",
        "observer_source_sha256": _file_sha256(observer_source),
        "seed_wrapper_path": "pepglad_seeded_entry.py",
        "seed_wrapper_sha256": _file_sha256(seed_wrapper),
        "instrumented_source_path": "work/api/run.py",
        "source_entrypoint_prepatch_sha256": source_entrypoint_sha256,
        "source_entrypoint_instrumented_sha256": _file_sha256(instrumented_source),
        "target_input_sha256": target_sha256,
        "target_preflight_verified": True,
        "source_commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
        "source_entrypoint_sha256": source_entrypoint_sha256,
        "model_weights_sha256": (
            "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
        ),
        "container_image": "pd-benchmark-methods-gpu:0.21",
        "conda_environment": "bench-pepglad",
    }
    runtime_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    execution_path = tmp_path / ARTIFACTS["v034_execution_results"]["path"]
    rewrite_csv(
        execution_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            attempt_id="attempt_003",
            attempt_dir=str(attempt),
            status="qc_failed",
            overall_qc_status="fail",
            supported_candidate="no",
            merge_status="qc_failed",
            status_reason="chirality_status;overall_qc_status",
        ),
    )
    manifest_path = tmp_path / ARTIFACTS["v034_method_output_manifest"]["path"]
    rewrite_csv(
        manifest_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            run_record_id=f"{job_id}_attempt_003",
            source_commit="bad015ca50c312a89482adb5220c3d907f13df5c",
            model_revision="codesign.ckpt_external_manifest_v0.21",
            environment_id="pd-benchmark-methods-gpu:0.21/bench-pepglad",
            command=str(attempt / "command.sh"),
            raw_output_root=str(attempt / "raw"),
            stdout_log=str(attempt / "stdout.log"),
            stderr_log=str(attempt / "stderr.log"),
            status="qc_failed",
            overall_qc_status="fail",
            status_reason="chirality_status;overall_qc_status",
        ),
    )
    candidate_path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    rewrite_csv(
        candidate_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            sequence="A" * 11,
            structure_path=str(post),
            source_output_path=str(post),
            status_reason="pepglad_standard_output_parsed",
            supported_candidate="no",
        ),
    )
    qc_path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]
    rewrite_csv(
        qc_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            overall_qc_status="fail",
            status_reason="chirality_status;overall_qc_status",
            file_sha256=baseline_sha256,
            file_size_bytes=str(post.stat().st_size),
            chirality_status="fail",
            chirality_evaluable="11",
            chirality_l_count="4",
            chirality_d_count="7",
            chirality_gly_count="0",
            chirality_unknown_count="0",
            supported_candidate="no",
        ),
    )
    run_path = tmp_path / ARTIFACTS["v034_run_rows"]["path"]
    rewrite_csv(
        run_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            attempt_id="attempt_003",
            sequence="A" * 11,
            structure_path=str(post),
            status="qc_failed",
            overall_qc_status="fail",
            supported_candidate="no",
            status_reason="chirality_status;overall_qc_status",
        ),
    )

    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(row for row in provenance["records"] if row["job_id"] == job_id)
    record.update(
        attempt_id="attempt_003",
        runtime_evidence_path="raw/runtime_evidence.json",
        runtime_evidence_sha256=_file_sha256(runtime_path),
        evidence_semantic_sha256=hashlib.sha256(
            json.dumps(runtime, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        evidence=runtime,
    )
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )

    summary_path = tmp_path / ARTIFACTS["v034_merge_summary"]["path"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(primary_passed=6, primary_complete=False, qc_failed_rows=1)
    summary["job_status"][job_id] = "qc_failed"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return {
        "attempt": attempt,
        "job_id": job_id,
        "patch": patch_path,
        "pre": pre,
        "post": post,
        "provenance": provenance_path,
        "runtime": runtime_path,
        "source_candidate": source_candidate,
    }


def _instrumented_pepglad_failure_valid(
    tmp_path: Path, fixture: dict[str, Path | str]
) -> bool:
    job_id = str(fixture["job_id"])

    def row(artifact_id: str) -> dict[str, str]:
        return next(
            value
            for value in _read_rows(tmp_path / ARTIFACTS[artifact_id]["path"])
            if value["job_id"] == job_id
        )

    provenance = json.loads(Path(fixture["provenance"]).read_text(encoding="utf-8"))
    record = next(value for value in provenance["records"] if value["job_id"] == job_id)
    return _v034_parsed_failure_valid(
        row("v034_job_manifest"),
        row("v034_execution_results"),
        row("v034_method_output_manifest"),
        row("v034_candidate_outputs"),
        row("v034_candidate_qc"),
        row("v034_run_rows"),
        record,
    )


def _rewrite_instrumented_runtime(
    fixture: dict[str, Path | str], update, *, record_only: bool = False
) -> None:
    provenance_path = Path(fixture["provenance"])
    runtime_path = Path(fixture["runtime"])
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(
        row for row in provenance["records"] if row["job_id"] == fixture["job_id"]
    )
    if record_only:
        update(record["evidence"])
    else:
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        update(runtime)
        runtime_path.write_text(
            json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        record["evidence"] = runtime
        record["runtime_evidence_sha256"] = _file_sha256(runtime_path)
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(record["evidence"], sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def test_v033_baseline_fails_if_failed_row_is_promoted_to_generated(
    tmp_path: Path,
) -> None:
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


def test_v034_bounded_connectivity_requires_seven_consistent_primary_candidates(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.PASS
    assert details["primary_jobs"] == 7
    assert details["primary_supported"] == 7
    assert details["candidate_rows"] == 7
    assert details["qc_rows"] == 7
    assert details["rf_handoff_resolved"] is True
    assert details["pepmirror_chirality_resolved"] is True
    assert details["extension_supported"] == 0


def test_v034_current_snapshot_reports_postdiagnostic_compact_evidence() -> None:
    result = evaluate("current.v034_bounded_connectivity")
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert result.severity.value == "Critical"
    assert result.reason_code == "v034_bounded_connectivity_incomplete"
    assert details["primary_jobs"] == 7
    assert details["primary_supported"] == 6
    assert details["extension_supported"] == 6
    assert details["candidate_rows"] == 12
    assert details["qc_rows"] == 12
    assert details["method_output_manifest_rows"] == 13
    assert details["runtime_provenance_rows"] == 12
    assert details["parsed_failure_rows"] == 0
    assert details["parsed_failure_rows_valid"] is True
    assert details["failure_evidence_rows"] == 1
    assert details["failure_evidence_valid"] is True
    assert details["failure_diagnostic_rows"] == 1
    assert details["failure_diagnostic_valid"] is True
    assert details["evidence_sets_consistent"] is True
    assert details["not_run_rows_valid"] is True
    assert details["summary_consistent"] is True
    assert "Six of seven" in result.message


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_record",
        "extra_record",
        "extra_top_level_key",
        "missing_nested_key",
        "extra_nested_key",
        "tampered_sequence",
        "tampered_pre_sha",
        "tampered_chirality",
        "tampered_producer_pin",
        "tampered_exit_code",
        "tampered_seed43_status",
        "tampered_attempt_binding",
    ],
)
def test_v034_failure_diagnostic_fails_closed_on_schema_content_or_binding_tamper(
    tmp_path: Path, mutation: str
) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_failure_diagnostics"]["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))

    if mutation == "missing_record":
        payload["records"] = []
    elif mutation == "extra_record":
        payload["records"].append(dict(payload["records"][0]))
    elif mutation == "extra_top_level_key":
        payload["unexpected"] = True
    elif mutation == "missing_nested_key":
        del payload["records"][0]["summary"]["sequence"]
    elif mutation == "extra_nested_key":
        payload["records"][0]["parser"]["unexpected"] = "value"
    elif mutation == "tampered_sequence":
        payload["records"][0]["summary"]["sequence"] = "FORGED"
    elif mutation == "tampered_pre_sha":
        payload["records"][0]["pre_openmm"]["sha256"] = "0" * 64
    elif mutation == "tampered_chirality":
        payload["records"][0]["post_openmm"]["chirality"]["d_count"] = 6
    elif mutation == "tampered_producer_pin":
        payload["records"][0]["producer_bindings"]["observer"]["sha256"] = (
            "0" * 64
        )
    elif mutation == "tampered_exit_code":
        payload["records"][0]["process"]["exit_code"] = 1
    elif mutation == "tampered_seed43_status":
        payload["records"][0]["seed43_status"] = "supported"
    elif mutation == "tampered_attempt_binding":
        payload["records"][0]["attempt_dir"] += "_forged"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["failure_diagnostic_valid"] is False
    assert details["evidence_sets_consistent"] is False


def test_v034_failure_diagnostic_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_failure_diagnostics"]["path"]
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            '"schema_version": "v0.34"',
            '"schema_version": "v0.34",\n  "schema_version": "v0.34"',
            1,
        ),
        encoding="utf-8",
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["failure_diagnostic_rows"] == 0
    assert details["failure_diagnostic_valid"] is False
    assert details["evidence_sets_consistent"] is False


@pytest.mark.parametrize(
    "artifact_id",
    [
        "v034_method_output_manifest",
        "v034_candidate_outputs",
        "v034_candidate_qc",
    ],
)
def test_v034_bounded_connectivity_fails_when_primary_evidence_row_is_missing(
    tmp_path: Path, artifact_id: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS[artifact_id]["path"]
    rows = _read_rows(path)
    write_rows(path, rows[1:])

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "v034_bounded_connectivity_incomplete"
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_fails_when_summary_is_promoted(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_merge_summary"]["path"]
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["primary_passed"] = 8
    path.write_text(json.dumps(summary) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["summary_consistent"] is False


def test_v034_bounded_connectivity_binds_run_seed_to_job_contract(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_run_rows"]["path"]
    rewrite_csv(path, lambda rows: rows[0].update(random_seed="999"))

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_accepts_explicit_qc_warning(tmp_path: Path) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(row["job_id"] for row in jobs if row["seed_stage"] == "primary")
    for artifact_id in (
        "v034_execution_results",
        "v034_method_output_manifest",
        "v034_candidate_qc",
        "v034_run_rows",
    ):
        path = tmp_path / ARTIFACTS[artifact_id]["path"]
        rewrite_csv(
            path,
            lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
                overall_qc_status="pass_with_warning"
            ),
        )
    qc_path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]
    rewrite_csv(
        qc_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            noncanonical_status="warn"
        ),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.PASS


def test_v034_bounded_connectivity_rejects_inconsistent_overall_qc(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_execution_results"]["path"]
    rewrite_csv(
        path,
        lambda rows: rows[0].update(overall_qc_status="pass_with_warning"),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_rejects_hidden_failed_qc_check(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == "AfCycDesign / ColabDesign cyclic peptide"
        and row["seed_stage"] == "primary"
    )
    path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]
    rows = _read_rows(path)
    for row in rows:
        row["cyclic_status"] = "fail" if row["job_id"] == job_id else "not_applicable"
    write_rows(path, rows)

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


@pytest.mark.parametrize(
    ("method", "field"),
    [
        ("PepMLM", "file_status"),
        ("PepMLM", "seed_status"),
        ("DiffPepBuilder", "chain_status"),
        ("PepGLAD", "target_binding_status"),
        ("D-Flow / PeptideDesign", "chirality_status"),
        ("AfCycDesign / ColabDesign cyclic peptide", "cyclic_status"),
        ("PepMirror", "mirror_target_central_inversion_status"),
    ],
)
def test_v034_bounded_connectivity_rejects_required_check_marked_not_applicable(
    tmp_path: Path, method: str, field: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == method and row["seed_stage"] == "primary"
    )
    path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]

    def remove_required_check(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == job_id)
        row[field] = "not_applicable"

    rewrite_csv(path, remove_required_check)
    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


@pytest.mark.parametrize(
    ("method", "field"),
    [
        ("RFdiffusion + ProteinMPNN", "handoff_status"),
        ("PepMirror", "method_contract_status"),
        ("PepMirror", "chirality_status"),
    ],
)
def test_v034_bounded_connectivity_requires_resolved_method_semantics(
    tmp_path: Path, method: str, field: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]

    def remove_resolution(rows: list[dict[str, str]]) -> None:
        row = next(
            row
            for row in rows
            if row["job_id"]
            in {
                job["job_id"]
                for job in _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
                if job["method"] == method and job["seed_stage"] == "primary"
            }
        )
        row[field] = "fail"

    rewrite_csv(path, remove_resolution)
    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


@pytest.mark.parametrize(
    ("method", "mutation"),
    [
        (
            "PepMirror",
            lambda evidence: evidence.update(mirror_output_sha256="e" * 64),
        ),
        (
            "RFdiffusion + ProteinMPNN",
            lambda evidence: evidence.update(rf_contig="[A3-117/0 10-20]"),
        ),
        (
            "RFdiffusion + ProteinMPNN",
            lambda evidence: evidence.update(mpnn_fixed_chains=["B"]),
        ),
        (
            "D-Flow / PeptideDesign",
            lambda evidence: evidence.update(source_git_tracked_paths_clean=False),
        ),
        (
            "PepMirror",
            lambda evidence: evidence.update(source_commit_verified=False),
        ),
        (
            "PepMirror",
            lambda evidence: evidence.update(
                checkpoint_container_binding_verified=False
            ),
        ),
        (
            "PepMirror",
            lambda evidence: evidence.update(checkpoint_verified_pre_run=False),
        ),
        (
            "PepMirror",
            lambda evidence: evidence.update(compose_service_verified=False),
        ),
        (
            "PepMirror",
            lambda evidence: evidence.update(
                executed_source_manifest_verified_pre_run=False
            ),
        ),
        (
            "PepMirror",
            lambda evidence: evidence.update(target_input_verified_pre_run=False),
        ),
        (
            "PepMirror",
            lambda evidence: evidence.update(mirror_runtime_scope="host"),
        ),
        (
            "RFdiffusion + ProteinMPNN",
            lambda evidence: evidence["rf_trb_semantic_extract"].update(
                design_startnum=99
            ),
        ),
    ],
)
def test_v034_bounded_connectivity_requires_method_specific_runtime_provenance(
    tmp_path: Path, method: str, mutation
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = next(
        row
        for row in payload["records"]
        if row["method"] == method and row["seed_stage"] == "primary"
    )
    mutation(record["evidence"])
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(record["evidence"], sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_binds_runtime_provenance_semantics(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = next(
        row
        for row in payload["records"]
        if row["method"] == "PepMLM" and row["seed_stage"] == "primary"
    )
    record["evidence"]["unbound_tamper"] = True
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_replays_pepmlm_sequence_from_raw_csv(
    tmp_path: Path,
) -> None:
    copy_current_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == "PepMLM" and row["seed_stage"] == "primary"
    )
    for artifact_id in ("v034_candidate_outputs", "v034_run_rows"):
        rewrite_csv(
            tmp_path / ARTIFACTS[artifact_id]["path"],
            lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
                sequence="VVV"
            ),
        )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["primary_supported"] == 5
    assert details["evidence_sets_consistent"] is False


def test_v034_bounded_connectivity_rejects_coordinated_structure_record_tamper(
    tmp_path: Path,
) -> None:
    copy_current_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == "D-Flow / PeptideDesign"
        and row["seed_stage"] == "primary"
    )
    candidate_path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    candidate = next(
        row for row in _read_rows(candidate_path) if row["job_id"] == job_id
    )
    tampered_structure = tmp_path / "coordinated" / "dflow_candidate.pdb"
    tampered_structure.parent.mkdir(parents=True)
    shutil.copy2(candidate["structure_path"], tampered_structure)
    tampered_sha = _file_sha256(tampered_structure)
    tampered_size = str(tampered_structure.stat().st_size)

    rewrite_csv(
        candidate_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            sequence="AAAAAAAAAAA",
            structure_path=str(tampered_structure),
            source_output_path=str(tampered_structure),
        ),
    )
    rewrite_csv(
        tmp_path / ARTIFACTS["v034_run_rows"]["path"],
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            sequence="AAAAAAAAAAA", structure_path=str(tampered_structure)
        ),
    )
    rewrite_csv(
        tmp_path / ARTIFACTS["v034_candidate_qc"]["path"],
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            file_sha256=tampered_sha,
            file_size_bytes=tampered_size,
            sequence_length="11",
        ),
    )
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(row for row in payload["records"] if row["job_id"] == job_id)
    record["evidence"].update(
        candidate_path=str(tampered_structure), candidate_sha256=tampered_sha
    )
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(
            record["evidence"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    provenance_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["primary_supported"] == 5
    assert details["evidence_sets_consistent"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "payload_extra",
        "record_extra",
        "record_wrong_type",
        "evidence_extra_rehashed",
        "evidence_wrong_type_rehashed",
        "rf_nested_extra_rehashed",
        "rf_nested_wrong_type_rehashed",
        "rf_list_wrong_type_rehashed",
        "nonfinite_rehashed",
    ],
)
def test_v034_runtime_provenance_rejects_schema_extensions_and_nonfinite_values(
    tmp_path: Path, mutation: str
) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    pepmlm = next(
        row
        for row in payload["records"]
        if row["method"] == "PepMLM" and row["seed_stage"] == "primary"
    )
    if mutation == "payload_extra":
        payload["unexpected"] = True
    elif mutation == "record_extra":
        pepmlm["unexpected"] = True
    elif mutation == "record_wrong_type":
        pepmlm["random_seed"] = "42"
    elif mutation == "evidence_extra_rehashed":
        pepmlm["evidence"]["unexpected"] = True
        pepmlm["evidence_semantic_sha256"] = hashlib.sha256(
            json.dumps(
                pepmlm["evidence"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
    elif mutation == "evidence_wrong_type_rehashed":
        pepmlm["evidence"]["model_revision"] = True
        pepmlm["evidence_semantic_sha256"] = hashlib.sha256(
            json.dumps(
                pepmlm["evidence"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
    elif mutation == "rf_nested_extra_rehashed":
        rf = next(
            row
            for row in payload["records"]
            if row["method"] == "RFdiffusion + ProteinMPNN"
            and row["seed_stage"] == "primary"
        )
        rf["evidence"]["rf_trb_semantic_extract"]["unexpected"] = "coordinated"
        rf["evidence"]["rf_trb_semantic_sha256"] = hashlib.sha256(
            json.dumps(
                rf["evidence"]["rf_trb_semantic_extract"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        rf["evidence_semantic_sha256"] = hashlib.sha256(
            json.dumps(rf["evidence"], sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
    elif mutation in {"rf_nested_wrong_type_rehashed", "rf_list_wrong_type_rehashed"}:
        rf = next(
            row
            for row in payload["records"]
            if row["method"] == "RFdiffusion + ProteinMPNN"
            and row["seed_stage"] == "primary"
        )
        if mutation == "rf_nested_wrong_type_rehashed":
            rf["evidence"]["rf_trb_semantic_extract"]["num_designs"] = True
            rf["evidence"]["rf_trb_semantic_sha256"] = hashlib.sha256(
                json.dumps(
                    rf["evidence"]["rf_trb_semantic_extract"],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        else:
            rf["evidence"]["rf_hotspots"] = [48]
        rf["evidence_semantic_sha256"] = hashlib.sha256(
            json.dumps(rf["evidence"], sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
    elif mutation == "nonfinite_rehashed":
        pepmlm["evidence"]["model_revision"] = float("nan")
        pepmlm["evidence_semantic_sha256"] = hashlib.sha256(
            json.dumps(
                pepmlm["evidence"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["evidence_sets_consistent"] is False


def _coordinate_v034_identity_spoof(
    method: str,
    category: str,
    manifest: dict[str, str],
    evidence: dict[str, object],
) -> None:
    zero_sha = "0" * 64
    one_sha = "1" * 64
    zero_commit = "0" * 40
    one_commit = "1" * 40
    if category == "source":
        if method == "RFdiffusion + ProteinMPNN":
            evidence.update(
                rf_source_commit=zero_commit,
                mpnn_source_commit=one_commit,
                rf_source_entrypoint_sha256=zero_sha,
                mpnn_source_entrypoint_sha256=one_sha,
            )
            manifest["source_commit"] = (
                f"RFdiffusion@{zero_commit};ProteinMPNN@{one_commit}"
            )
        elif method == "PepMirror":
            evidence.update(
                source_commit_expected=zero_commit,
                source_commit_observed=zero_commit,
                generate_py_pre_sha256=zero_sha,
                generate_py_post_sha256=one_sha,
                seed_patch_sha256=one_sha,
                mirror_pdb_py_pre_sha256=zero_sha,
                mirror_pdb_py_post_sha256=zero_sha,
            )
            manifest["source_commit"] = zero_commit
        elif method == "D-Flow / PeptideDesign":
            evidence.update(
                source_commit=zero_commit,
                source_entrypoint_prepatch_sha256=zero_sha,
                source_entrypoint_patched_sha256=one_sha,
                seed_patch_sha256=one_sha,
                python_executable_sha256=zero_sha,
            )
            manifest["source_commit"] = zero_commit
        else:
            evidence["source_commit"] = zero_commit
            for field in ("source_entrypoint_sha256", "source_notebook_sha256"):
                if field in evidence:
                    evidence[field] = zero_sha
            manifest["source_commit"] = zero_commit
    elif category == "model":
        if method == "PepMLM":
            evidence.update(model_revision=zero_commit, model_weights_sha256=zero_sha)
            manifest["model_revision"] = zero_commit
        elif method == "DiffPepBuilder":
            evidence["model_asset_sha256"] = {
                "diffpepbuilder_v1.pth": zero_sha,
                "esm2_t33_650M_UR50D-contact-regression.pt": one_sha,
                "esm2_t33_650M_UR50D.pt": "2" * 64,
            }
            manifest["model_revision"] = "forged_diffpepbuilder_model"
        elif method == "PepGLAD":
            evidence["model_weights_sha256"] = zero_sha
            manifest["model_revision"] = "forged_pepglad_model"
        elif method == "D-Flow / PeptideDesign":
            evidence["checkpoint_sha256"] = zero_sha
            manifest["model_revision"] = f"sha256:{zero_sha}"
        elif method == "PepMirror":
            evidence.update(
                checkpoint_sha256=zero_sha,
                checkpoint_revision=f"sha256:{zero_sha}",
            )
            manifest["model_revision"] = f"sha256:{zero_sha}"
        elif method == "AfCycDesign / ColabDesign cyclic peptide":
            evidence["alphafold_params_sha256"] = zero_sha
            manifest["model_revision"] = f"alphafold_model_1_ptm@sha256:{zero_sha}"
        else:
            evidence.update(
                rf_checkpoint_sha256=zero_sha,
                mpnn_checkpoint_sha256=one_sha,
            )
            manifest["model_revision"] = (
                "RFdiffusion_external_models;forged_proteinmpnn.pt"
            )
    else:
        if method in {"PepMLM", "DiffPepBuilder", "PepGLAD"}:
            evidence.update(container_image="forged-image:latest", conda_environment="forged-env")
            manifest["environment_id"] = "forged-image:latest/forged-env"
        elif method == "D-Flow / PeptideDesign":
            evidence["execution_environment_declared"] = "host:.venv/forged"
            manifest["environment_id"] = "host:.venv/forged"
        elif method == "PepMirror":
            evidence.update(
                compose_image_tag="forged-image:latest",
                execution_environment_id="forged-image:latest/forged-env",
                compose_file_sha256=zero_sha,
                image_id_observed_at_prepare=f"sha256:{zero_sha}",
                image_id_observed_pre_run=f"sha256:{zero_sha}",
            )
            manifest["environment_id"] = "forged-image:latest/forged-env"
        elif method == "AfCycDesign / ColabDesign cyclic peptide":
            evidence.update(
                container_image="forged-image:latest",
                container_image_id=f"sha256:{zero_sha}",
            )
            manifest["environment_id"] = "forged-image:latest/forged-env"
        else:
            evidence.update(
                rf_container_image="forged-rf:latest",
                rf_container_image_id=f"sha256:{zero_sha}",
                mpnn_container_image="forged-mpnn:latest",
                mpnn_container_image_id=f"sha256:{one_sha}",
            )
            manifest["environment_id"] = "forged-rf:latest + forged-mpnn:latest"


@pytest.mark.parametrize("method", sorted(project_state.V034_METHODS))
@pytest.mark.parametrize("category", ["source", "model", "environment"])
def test_v034_consumer_pins_reject_coordinated_identity_spoof(
    tmp_path: Path, method: str, category: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    manifest_path = tmp_path / ARTIFACTS["v034_method_output_manifest"]["path"]
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    manifests = _read_rows(manifest_path)
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    manifest = next(row for row in manifests if row["method"] == method)
    record = next(row for row in payload["records"] if row["method"] == method)

    _coordinate_v034_identity_spoof(method, category, manifest, record["evidence"])
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(
            record["evidence"], sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()
    write_rows(manifest_path, manifests)
    provenance_path.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["primary_supported"] == 6
    assert details["evidence_sets_consistent"] is False


def test_v034_pepmlm_consumer_pin_survives_raw_and_compact_coordinated_spoof(
    tmp_path: Path,
) -> None:
    copy_current_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job = next(
        row
        for row in jobs
        if row["method"] == "PepMLM" and row["seed_stage"] == "primary"
    )
    job_id = job["job_id"]
    execution_path = tmp_path / ARTIFACTS["v034_execution_results"]["path"]
    execution_rows = _read_rows(execution_path)
    execution = next(row for row in execution_rows if row["job_id"] == job_id)
    old_attempt = Path(execution["attempt_dir"])
    new_attempt = (
        tmp_path / "attempts" / job_id / execution["attempt_id"]
    ).resolve()
    shutil.copytree(old_attempt, new_attempt, symlinks=True)
    old_prefix = str(old_attempt)
    new_prefix = str(new_attempt)
    execution["attempt_dir"] = new_prefix
    write_rows(execution_path, execution_rows)

    forged_revision = "0" * 40
    manifest_path = tmp_path / ARTIFACTS["v034_method_output_manifest"]["path"]
    manifests = _read_rows(manifest_path)
    compact_manifest = next(row for row in manifests if row["job_id"] == job_id)
    compact_manifest["model_revision"] = forged_revision
    for field in ("command", "raw_output_root", "stdout_log", "stderr_log"):
        compact_manifest[field] = compact_manifest[field].replace(
            old_prefix, new_prefix
        )
    write_rows(manifest_path, manifests)

    local_manifest_path = new_attempt / "method_output_manifest.csv"
    rewrite_csv(
        local_manifest_path,
        lambda rows: rows[0].update(
            model_revision=forged_revision,
            command=rows[0]["command"].replace(old_prefix, new_prefix),
            raw_output_root=rows[0]["raw_output_root"].replace(
                old_prefix, new_prefix
            ),
            stdout_log=rows[0]["stdout_log"].replace(old_prefix, new_prefix),
            stderr_log=rows[0]["stderr_log"].replace(old_prefix, new_prefix),
        ),
    )

    candidate_path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    rewrite_csv(
        candidate_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            source_output_path=next(
                row for row in rows if row["job_id"] == job_id
            )["source_output_path"].replace(old_prefix, new_prefix)
        ),
    )
    rewrite_csv(
        new_attempt / "candidate_outputs.csv",
        lambda rows: rows[0].update(
            source_output_path=rows[0]["source_output_path"].replace(
                old_prefix, new_prefix
            )
        ),
    )

    result_path = new_attempt / "run_result.json"
    local_result = json.loads(result_path.read_text(encoding="utf-8"))
    local_result["attempt_dir"] = new_prefix
    result_path.write_text(
        json.dumps(local_result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    runtime_path = new_attempt / "raw/runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["model_revision"] = forged_revision
    runtime_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(row for row in provenance["records"] if row["job_id"] == job_id)
    record["evidence"] = runtime
    record["runtime_evidence_sha256"] = _file_sha256(runtime_path)
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(
            runtime, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()
    provenance_path.write_text(
        json.dumps(provenance, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["primary_supported"] == 5
    assert details["evidence_sets_consistent"] is False


@pytest.mark.parametrize(
    "checkpoint_field", ["rf_checkpoint_sha256", "mpnn_checkpoint_sha256"]
)
def test_v034_bounded_connectivity_binds_each_rf_checkpoint_to_model_revision(
    tmp_path: Path, checkpoint_field: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = next(
        row
        for row in payload["records"]
        if row["method"] == "RFdiffusion + ProteinMPNN"
        and row["seed_stage"] == "primary"
    )
    record["evidence"][checkpoint_field] = "0" * 64
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(record["evidence"], sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_rejects_unbound_extra_runtime_provenance(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    extension = next(row for row in jobs if row["seed_stage"] == "extension")
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    extra = dict(payload["records"][0])
    extra.update(
        job_id=extension["job_id"],
        method=extension["method"],
        seed_stage="extension",
        random_seed=43,
        attempt_id="attempt_001",
        evidence_semantic_sha256="0" * 64,
    )
    extra["evidence"] = dict(extra["evidence"])
    extra["evidence"].update(requested_seed=43, effective_seed=43)
    payload["records"].append(extra)
    provenance_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    summary_path = tmp_path / ARTIFACTS["v034_merge_summary"]["path"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["runtime_provenance_rows"] = 8
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["evidence_sets_consistent"] is False


@pytest.mark.parametrize(
    ("artifact_id", "method", "field", "value"),
    [
        ("v034_method_output_manifest", "PepMLM", "exit_code", "1"),
        ("v034_candidate_qc", "PepMLM", "file_sha256", ""),
        ("v034_candidate_qc", "PepMLM", "file_size_bytes", "not-a-number"),
        ("v034_run_rows", "DiffPepBuilder", "structure_path", "/wrong/path.pdb"),
        ("v034_candidate_outputs", "DiffPepBuilder", "chirality", "D"),
        (
            "v034_method_output_manifest",
            "RFdiffusion + ProteinMPNN",
            "source_commit",
            "unbound-source",
        ),
        (
            "v034_method_output_manifest",
            "RFdiffusion + ProteinMPNN",
            "environment_id",
            "unbound-environment",
        ),
        (
            "v034_method_output_manifest",
            "RFdiffusion + ProteinMPNN",
            "model_revision",
            "unbound-model-revision",
        ),
    ],
)
def test_v034_bounded_connectivity_binds_process_and_candidate_provenance(
    tmp_path: Path,
    artifact_id: str,
    method: str,
    field: str,
    value: str,
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == method and row["seed_stage"] == "primary"
    )
    path = tmp_path / ARTIFACTS[artifact_id]["path"]

    def corrupt(rows: list[dict[str, str]]) -> None:
        row = next(row for row in rows if row["job_id"] == job_id)
        row[field] = value

    rewrite_csv(path, corrupt)
    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_binds_rf_candidate_paths_to_runtime(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == "RFdiffusion + ProteinMPNN"
        and row["seed_stage"] == "primary"
    )
    candidate_path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    rewrite_csv(
        candidate_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            structure_path="/wrong/backbone.pdb",
            source_output_path="/wrong/design.fa",
        ),
    )
    run_path = tmp_path / ARTIFACTS["v034_run_rows"]["path"]
    rewrite_csv(
        run_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            structure_path="/wrong/backbone.pdb"
        ),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mirror_target_atom_count", "0"),
        ("mirror_output_atom_count", "not-an-integer"),
        ("mirror_target_central_inversion_max_residual", "0.003"),
        ("mirror_target_central_inversion_max_residual", "nan"),
        ("mirror_output_central_inversion_max_residual", "inf"),
        ("mirror_target_central_inversion_max_residual", "-0.001"),
        ("mirror_output_central_inversion_tolerance", "nan"),
        ("mirror_target_central_inversion_tolerance", "inf"),
        ("mirror_output_central_inversion_tolerance", "-0.001"),
    ],
)
def test_v034_bounded_connectivity_rejects_invalid_pepmirror_geometry_evidence(
    tmp_path: Path, field: str, value: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == "PepMirror" and row["seed_stage"] == "primary"
    )
    qc_path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]
    rewrite_csv(
        qc_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            {field: value}
        ),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


@pytest.mark.parametrize("prefix", ["mirror_target", "mirror_output"])
def test_v034_bounded_connectivity_accepts_exact_zero_central_inversion_geometry(
    tmp_path: Path, prefix: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == "PepMirror" and row["seed_stage"] == "primary"
    )
    qc_path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]
    rewrite_csv(
        qc_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            {
                f"{prefix}_central_inversion_max_residual": "0",
                f"{prefix}_central_inversion_tolerance": "0",
            }
        ),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.PASS


@pytest.mark.parametrize("candidate_field", ["structure_path", "source_output_path"])
def test_v034_bounded_connectivity_binds_each_pepmirror_candidate_path_to_runtime(
    tmp_path: Path, candidate_field: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job_id = next(
        row["job_id"]
        for row in jobs
        if row["method"] == "PepMirror" and row["seed_stage"] == "primary"
    )
    candidate_path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    rewrite_csv(
        candidate_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            {candidate_field: "/wrong/pepmirror_candidate.pdb"}
        ),
    )
    if candidate_field == "structure_path":
        run_path = tmp_path / ARTIFACTS["v034_run_rows"]["path"]
        rewrite_csv(
            run_path,
            lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
                structure_path="/wrong/pepmirror_candidate.pdb"
            ),
        )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_bounded_connectivity_binds_pepmirror_runtime_output_path_to_candidate(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = next(
        row
        for row in payload["records"]
        if row["method"] == "PepMirror" and row["seed_stage"] == "primary"
    )
    record["evidence"]["mirror_output_path"] = "/wrong/runtime_candidate.pdb"
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(record["evidence"], sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_extension_evidence_cannot_precede_its_primary(tmp_path: Path) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    extension = next(row for row in jobs if row["seed_stage"] == "extension")
    primary_id = extension["primary_job_id"]
    execution_path = tmp_path / ARTIFACTS["v034_execution_results"]["path"]

    def swap_support(rows: list[dict[str, str]]) -> None:
        primary = next(row for row in rows if row["job_id"] == primary_id)
        primary.update(
            status="not_run",
            overall_qc_status="not_run",
            supported_candidate="no",
            merge_status="not_run",
        )
        ext = next(row for row in rows if row["job_id"] == extension["job_id"])
        ext.update(
            status="passed",
            overall_qc_status="pass",
            supported_candidate="yes",
            merge_status="supported",
        )

    rewrite_csv(execution_path, swap_support)
    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["extension_orphans"] == 1


def test_v034_extension_is_optional_after_its_primary_passes(tmp_path: Path) -> None:
    write_complete_v034_evidence(tmp_path, extension_methods={"PepMLM"})

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.PASS
    assert dict(result.details)["extension_supported"] == 1


def test_v034_parsed_failure_evidence_requires_a_real_qc_failed_attempt(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    extension = next(row for row in jobs if row["seed_stage"] == "extension")
    job_id = extension["job_id"]
    design_id = f"{job_id}_candidate_1"

    for artifact_id, updates in (
        (
            "v034_method_output_manifest",
            {
                "run_record_id": f"{job_id}_attempt_001",
                "job_id": job_id,
                "execution_stage": "extension",
                "status": "qc_failed",
                "overall_qc_status": "fail",
            },
        ),
        (
            "v034_candidate_outputs",
            {
                "design_id": design_id,
                "job_id": job_id,
                "target_id": extension["target_id"],
                "supported_candidate": "no",
            },
        ),
        (
            "v034_candidate_qc",
            {
                "design_id": design_id,
                "job_id": job_id,
                "overall_qc_status": "fail",
                "supported_candidate": "no",
            },
        ),
    ):
        path = tmp_path / ARTIFACTS[artifact_id]["path"]
        rows = _read_rows(path)
        added = dict(rows[0])
        added.update(updates)
        rows.append(added)
        write_rows(path, rows)

    execution_path = tmp_path / ARTIFACTS["v034_execution_results"]["path"]
    rewrite_csv(
        execution_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            attempt_id="attempt_001",
            attempt_dir=f"/external/{job_id}/attempt_001",
            status="not_run",
            overall_qc_status="not_run",
            supported_candidate="no",
            merge_status="qc_failed",
        ),
    )
    run_path = tmp_path / ARTIFACTS["v034_run_rows"]["path"]
    rewrite_csv(
        run_path,
        lambda rows: next(row for row in rows if row["job_id"] == job_id).update(
            design_id=design_id,
            attempt_id="attempt_001",
            sequence="ACD",
            status="not_run",
            overall_qc_status="not_run",
            supported_candidate="no",
        ),
    )

    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    added_provenance = dict(provenance["records"][0])
    added_provenance.update(
        job_id=job_id,
        seed_stage="extension",
        random_seed=43,
        attempt_id="attempt_001",
    )
    added_provenance["evidence"] = dict(added_provenance["evidence"])
    added_provenance["evidence"].update(requested_seed=43, effective_seed=43)
    added_provenance["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(
            added_provenance["evidence"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    provenance["records"].append(added_provenance)
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )

    summary_path = tmp_path / ARTIFACTS["v034_merge_summary"]["path"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(parsed_candidate_rows=8, qc_failed_rows=0, runtime_provenance_rows=8)
    summary["job_status"][job_id] = "qc_failed"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["parsed_failure_rows_valid"] is False


def test_v034_parsed_failure_reuses_common_process_and_candidate_checks(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    jobs = _read_rows(tmp_path / ARTIFACTS["v034_job_manifest"]["path"])
    job = next(
        row
        for row in jobs
        if row["method"] == "PepGLAD" and row["seed_stage"] == "primary"
    )
    job_id = job["job_id"]

    def csv_row(artifact_id: str) -> dict[str, str]:
        return next(
            row
            for row in _read_rows(tmp_path / ARTIFACTS[artifact_id]["path"])
            if row["job_id"] == job_id
        )

    execution = csv_row("v034_execution_results")
    manifest = csv_row("v034_method_output_manifest")
    candidate = csv_row("v034_candidate_outputs")
    qc = csv_row("v034_candidate_qc")
    run = csv_row("v034_run_rows")
    provenance_payload = json.loads(
        (tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    provenance = next(
        row for row in provenance_payload["records"] if row["job_id"] == job_id
    )

    execution.update(
        status="qc_failed",
        overall_qc_status="fail",
        supported_candidate="no",
        merge_status="qc_failed",
    )
    manifest.update(status="qc_failed", overall_qc_status="fail")
    candidate.update(supported_candidate="no")
    qc.update(
        overall_qc_status="fail",
        supported_candidate="no",
        chirality_status="fail",
        chirality_evaluable="11",
        chirality_l_count="4",
        chirality_d_count="7",
        chirality_unknown_count="0",
    )
    run.update(status="qc_failed", overall_qc_status="fail", supported_candidate="no")

    assert _v034_parsed_failure_valid(
        job, execution, manifest, candidate, qc, run, provenance
    )

    qc["chain_status"] = "fail"
    assert not _v034_parsed_failure_valid(
        job, execution, manifest, candidate, qc, run, provenance
    )
    qc["chain_status"] = "pass"

    candidate["chirality"] = "D"
    qc["file_sha256"] = ""
    assert not _v034_parsed_failure_valid(
        job, execution, manifest, candidate, qc, run, provenance
    )


def test_v034_instrumented_pepglad_mixed_chirality_is_valid_failure_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert _instrumented_pepglad_failure_valid(tmp_path, fixture)
    assert result.verdict is GateVerdict.FAIL
    assert details["primary_supported"] == 6
    assert details["parsed_failure_rows"] == 1
    assert details["parsed_failure_rows_valid"] is True


def test_v034_nonbaseline_synthetic_legacy_pepglad_is_rejected(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(row for row in payload["records"] if row["method"] == "PepGLAD")
    candidate_path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    candidate = next(
        row
        for row in _read_rows(candidate_path)
        if row["job_id"] == record["job_id"]
    )
    synthetic = b"self-consistent but nonbaseline PepGLAD candidate\n"
    Path(candidate["structure_path"]).write_bytes(synthetic)
    synthetic_sha256 = hashlib.sha256(synthetic).hexdigest()
    qc_path = tmp_path / ARTIFACTS["v034_candidate_qc"]["path"]
    rewrite_csv(
        qc_path,
        lambda rows: next(
            row for row in rows if row["job_id"] == record["job_id"]
        ).update(
            file_sha256=synthetic_sha256,
            file_size_bytes=str(len(synthetic)),
        ),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert "recovery_mode" not in record["evidence"]
    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


@pytest.mark.parametrize(
    ("random_seed", "seed_stage"),
    [("43", "extension"), ("42", "extension")],
)
def test_v034_legacy_pepglad_is_limited_to_seed42_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    random_seed: str,
    seed_stage: str,
) -> None:
    attempt = tmp_path / "external/pepglad/attempt_002"
    official_candidate = attempt / "raw/pepglad_candidate.pdb"
    source_candidate = attempt / "work/codesign/3EQS_0.pdb"
    official_candidate.parent.mkdir(parents=True)
    source_candidate.parent.mkdir(parents=True)
    payload = b"synthetic legacy PepGLAD candidate\n"
    official_candidate.write_bytes(payload)
    source_candidate.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(
        project_state, "V034_PEPGLAD_SEED42_BASELINE_SHA256", digest
    )
    evidence = {
        "requested_seed": int(random_seed),
        "effective_seed": int(random_seed),
        "seed_control_status": "honored",
        "source_commit": project_state.V034_PEPGLAD_SOURCE_COMMIT,
        "source_entrypoint_sha256": (
            project_state.V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256
        ),
        "model_weights_sha256": project_state.V034_PEPGLAD_MODEL_WEIGHTS_SHA256,
        "source_candidate_path": (
            project_state.V034_PEPGLAD_LEGACY_SOURCE_CANDIDATE_PATH
        ),
        "container_image": project_state.V034_PEPGLAD_CONTAINER_IMAGE,
        "conda_environment": project_state.V034_PEPGLAD_CONDA_ENVIRONMENT,
    }

    assert not project_state._v034_pepglad_instrumented_provenance_pass(
        {"random_seed": random_seed, "seed_stage": seed_stage},
        {"attempt_dir": str(attempt)},
        {
            "structure_path": str(official_candidate),
            "source_output_path": str(official_candidate),
        },
        {"file_sha256": digest, "file_size_bytes": str(len(payload))},
        {"evidence": evidence},
    )


def test_v034_instrumented_pepglad_cannot_downgrade_to_exact_legacy_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)

    def remove_instrumentation(runtime: dict[str, object]) -> None:
        legacy = {
            field: runtime[field]
            for field in project_state.V034_PEPGLAD_LEGACY_RUNTIME_FIELDS
        }
        legacy["source_candidate_path"] = (
            project_state.V034_PEPGLAD_LEGACY_SOURCE_CANDIDATE_PATH
        )
        runtime.clear()
        runtime.update(legacy)

    _rewrite_instrumented_runtime(fixture, remove_instrumentation)
    monkeypatch.setattr(
        project_state,
        "V034_PEPGLAD_SEED42_BASELINE_SHA256",
        "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26",
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


def test_v034_current_pepglad_attempt_003_remains_manifest_only() -> None:
    result = evaluate("current.v034_bounded_connectivity")
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["method_output_manifest_rows"] == 13
    assert details["candidate_rows"] == 12
    assert details["qc_rows"] == 12
    assert details["runtime_provenance_rows"] == 12
    assert details["parsed_failure_rows"] == 0
    assert details["parsed_failure_rows_valid"] is True
    assert details["failure_evidence_rows"] == 1
    assert details["failure_evidence_valid"] is True
    assert details["evidence_sets_consistent"] is True


@pytest.mark.parametrize(
    ("artifact_id", "field", "value"),
    [
        ("v034_execution_results", "attempt_id", "attempt_004"),
        ("v034_execution_results", "merge_status", "supported"),
        ("v034_execution_results", "status_reason", "forged_parser_failure"),
        ("v034_method_output_manifest", "parser_status", "parsed"),
        ("v034_method_output_manifest", "exit_code", "1"),
        ("v034_method_output_manifest", "source_commit", "0" * 40),
        ("v034_method_output_manifest", "model_revision", "forged.ckpt"),
        ("v034_method_output_manifest", "environment_id", "forged/env"),
        ("v034_method_output_manifest", "execution_stage", "extension"),
        ("v034_run_rows", "attempt_id", "attempt_004"),
        ("v034_run_rows", "sequence", "AWHITLLIFTH"),
        ("v034_run_rows", "status_reason", "forged_parser_failure"),
    ],
)
def test_v034_manifest_only_failure_rejects_tampered_bindings(
    tmp_path: Path, artifact_id: str, field: str, value: str
) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS[artifact_id]["path"]
    rewrite_csv(
        path,
        lambda rows: next(
            row
            for row in rows
            if row["job_id"] == "v034_pepglad_3eqs_seed42"
        ).update({field: value}),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["failure_evidence_rows"] == 1
    assert details["failure_evidence_valid"] is False
    assert details["evidence_sets_consistent"] is False


def test_v034_rejects_extra_manifest_for_not_run_pepglad_seed43(
    tmp_path: Path,
) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_method_output_manifest"]["path"]
    rows = _read_rows(path)
    forged = dict(
        next(row for row in rows if row["job_id"] == "v034_pepglad_3eqs_seed42")
    )
    forged.update(
        job_id="v034_pepglad_3eqs_seed43",
        run_record_id="v034_pepglad_3eqs_seed43_attempt_003",
        execution_stage="extension",
    )
    write_rows(path, [*rows, forged])

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["failure_evidence_rows"] == 2
    assert details["failure_evidence_valid"] is False
    assert details["evidence_sets_consistent"] is False


@pytest.mark.parametrize(
    ("artifact_id", "field", "value"),
    [
        ("v034_execution_results", "status", ""),
        ("v034_execution_results", "attempt_id", "attempt_003"),
        ("v034_run_rows", "status", ""),
        ("v034_run_rows", "sequence", "FORGED"),
    ],
)
def test_v034_pepglad_seed43_requires_exact_not_run_rows(
    tmp_path: Path, artifact_id: str, field: str, value: str
) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS[artifact_id]["path"]
    rewrite_csv(
        path,
        lambda rows: next(
            row
            for row in rows
            if row["job_id"] == "v034_pepglad_3eqs_seed43"
        ).update({field: value}),
    )

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["not_run_rows_valid"] is False
    assert details["evidence_sets_consistent"] is False


def test_v034_manifest_only_failure_rejects_promoted_candidate_row(
    tmp_path: Path,
) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    rows = _read_rows(path)
    forged = dict(rows[0])
    forged.update(
        job_id="v034_pepglad_3eqs_seed42",
        method="PepGLAD",
        design_id="v034_pepglad_3eqs_seed42_forged_candidate",
    )
    write_rows(path, [*rows, forged])

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert details["evidence_sets_consistent"] is False


@pytest.mark.parametrize(
    ("artifact_id", "payload"),
    [
        ("v034_runtime_provenance", "duplicate_schema_key"),
        ("v034_runtime_provenance", "[]"),
        ("v034_runtime_provenance", "{"),
        ("v034_merge_summary", "duplicate_schema_key"),
        ("v034_merge_summary", "[]"),
        ("v034_merge_summary", "{"),
    ],
)
def test_v034_json_inputs_fail_closed_without_unhandled_errors(
    tmp_path: Path, artifact_id: str, payload: str
) -> None:
    copy_current_v034_evidence(tmp_path)
    path = tmp_path / ARTIFACTS[artifact_id]["path"]
    if payload == "duplicate_schema_key":
        original = path.read_text(encoding="utf-8")
        payload = original.replace(
            "{",
            '{\n  "schema_version": "v0.34",',
            1,
        )
    path.write_text(payload, encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    if artifact_id == "v034_runtime_provenance":
        assert details["table_ids_valid"] is False
    else:
        assert details["summary_consistent"] is False


@pytest.mark.parametrize("schema_change", ["extra", "missing"])
def test_v034_legacy_pepglad_requires_exact_historical_runtime_fields(
    tmp_path: Path, schema_change: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    record = next(row for row in payload["records"] if row["method"] == "PepGLAD")
    evidence = record["evidence"]
    if schema_change == "extra":
        evidence["unreviewed_field"] = "accepted_by_old_validator"
    else:
        evidence.pop("conda_environment")
    record["evidence_semantic_sha256"] = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    provenance_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = evaluate("current.v034_bounded_connectivity", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert dict(result.details)["primary_supported"] == 6


def test_v034_pepglad_production_identity_constants_are_fixed() -> None:
    assert getattr(project_state, "V034_PEPGLAD_SOURCE_COMMIT", None) == (
        "bad015ca50c312a89482adb5220c3d907f13df5c"
    )
    assert getattr(project_state, "V034_PEPGLAD_SOURCE_ENTRYPOINT_SHA256", None) == (
        "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
    )
    assert getattr(project_state, "V034_PEPGLAD_MODEL_WEIGHTS_SHA256", None) == (
        "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
    )
    assert getattr(project_state, "V034_PEPGLAD_SEED42_BASELINE_SHA256", None) == (
        "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
    )
    assert getattr(project_state, "V034_PEPGLAD_OBSERVER_SOURCE_SHA256", None) == (
        "a0a98420dd2fd5382479abe77526fb8fc206ffb1e69a8780912fb821dded0c61"
    )
    assert getattr(project_state, "V034_PEPGLAD_OBSERVER_PATCH_SHA256", None) == (
        "cd9ec19f6605fd2b067824d4e02971b3a203e827b6398a4ffd1c68c64464311a"
    )
    assert getattr(project_state, "V034_PEPGLAD_SEED_WRAPPER_SHA256", None) == (
        "6a9b4c9012205d27526e13dbccbd7d11c010eddc3c85acdb2796c2fa6668aaba"
    )
    assert getattr(project_state, "V034_PEPGLAD_INSTRUMENTED_SOURCE_SHA256", None) == (
        "c3b127e39be1b335ff6046bb2435451acfc1b323839377033bf438ccd4a32954"
    )


def test_v034_instrumented_pepglad_rejects_unknown_recovery_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    _rewrite_instrumented_runtime(
        fixture, lambda runtime: runtime.update(recovery_mode="unreviewed_recovery")
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize("schema_change", ["extra", "missing_mode"])
def test_v034_instrumented_pepglad_requires_exact_runtime_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    schema_change: str,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)

    def change_schema(runtime: dict[str, object]) -> None:
        if schema_change == "extra":
            runtime["unreviewed_field"] = "accepted_by_old_validator"
        else:
            runtime.pop("recovery_mode")

    _rewrite_instrumented_runtime(fixture, change_schema)

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


def test_v034_instrumented_pepglad_chirality_uses_captured_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)

    def reject_path_reopen(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise OSError("chirality must not reopen the captured PDB path")

    monkeypatch.setattr(
        project_state, "chirality_stats", reject_path_reopen, raising=False
    )

    assert _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    ("relative_path", "runtime_field", "patch_field"),
    [
        (
            "pepglad_observer.py",
            "observer_source_sha256",
            "observer_source_sha256",
        ),
        (
            "pepglad_instrument_source.py",
            "observer_patch_sha256",
            "observer_patch_sha256",
        ),
        ("pepglad_seeded_entry.py", "seed_wrapper_sha256", None),
        (
            "work/api/run.py",
            "source_entrypoint_instrumented_sha256",
            "source_entrypoint_instrumented_sha256",
        ),
    ],
)
def test_v034_instrumented_pepglad_rejects_self_consistent_unreviewed_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
    runtime_field: str,
    patch_field: str | None,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    identity_path = Path(fixture["attempt"]) / relative_path
    identity_path.write_bytes(f"unreviewed replacement for {relative_path}\n".encode())
    replacement_sha256 = _file_sha256(identity_path)
    patch_path = Path(fixture["patch"])
    if patch_field is not None:
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        patch[patch_field] = replacement_sha256
        patch_path.write_text(
            json.dumps(patch, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def update_runtime(runtime: dict[str, object]) -> None:
        runtime[runtime_field] = replacement_sha256
        runtime["observer_patch_evidence_sha256"] = _file_sha256(patch_path)

    _rewrite_instrumented_runtime(fixture, update_runtime)

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


def test_v034_instrumented_pepglad_binds_record_to_runtime_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    alternate = Path(fixture["attempt"]) / "work/codesign/alternate.pdb"
    alternate.write_bytes(Path(fixture["source_candidate"]).read_bytes())
    _rewrite_instrumented_runtime(
        fixture,
        lambda runtime: runtime.update(
            source_candidate_path="work/codesign/alternate.pdb"
        ),
        record_only=True,
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize("path_mode", ["absolute", "escape", "symlink"])
def test_v034_instrumented_pepglad_rejects_unsafe_attempt_relative_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path_mode: str
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    attempt = Path(fixture["attempt"])
    source = Path(fixture["source_candidate"])
    if path_mode == "absolute":
        replacement = str(source)
    elif path_mode == "escape":
        escaped = attempt.parent / "escaped_candidate.pdb"
        escaped.write_bytes(source.read_bytes())
        replacement = "../escaped_candidate.pdb"
    else:
        link = attempt / "work/codesign/candidate_link.pdb"
        link.symlink_to(source)
        replacement = "work/codesign/candidate_link.pdb"
    _rewrite_instrumented_runtime(
        fixture,
        lambda runtime: runtime.update(source_candidate_path=replacement),
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    "field",
    [
        "pre_relax_sha256",
        "post_relax_sha256",
        "observer_patch_evidence_sha256",
        "observer_patch_sha256",
        "observer_source_sha256",
        "seed_wrapper_sha256",
        "source_entrypoint_instrumented_sha256",
    ],
)
def test_v034_instrumented_pepglad_recomputes_attempt_file_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    _rewrite_instrumented_runtime(
        fixture, lambda runtime: runtime.update({field: "0" * 64})
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


def test_v034_instrumented_pepglad_rejects_source_candidate_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    Path(fixture["source_candidate"]).write_bytes(b"replaced candidate\n")

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    ("artifact_id", "field"),
    [
        ("v034_candidate_outputs", "source_output_path"),
        ("v034_candidate_qc", "file_sha256"),
    ],
)
def test_v034_instrumented_pepglad_binds_post_to_candidate_and_qc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_id: str,
    field: str,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    artifact_path = tmp_path / ARTIFACTS[artifact_id]["path"]
    value = str(fixture["pre"]) if field == "source_output_path" else "0" * 64
    rewrite_csv(
        artifact_path,
        lambda rows: next(
            row for row in rows if row["job_id"] == fixture["job_id"]
        ).update({field: value}),
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    ("report_field", "count_field"),
    [
        ("post_relax_binder_chirality", "l_count"),
        ("pre_relax_binder_chirality", "d_count"),
    ],
)
def test_v034_instrumented_pepglad_recomputes_reported_chirality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    report_field: str,
    count_field: str,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)

    def tamper(runtime: dict[str, object]) -> None:
        report = dict(runtime[report_field])
        report[count_field] = 99
        runtime[report_field] = report

    _rewrite_instrumented_runtime(fixture, tamper)

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("official_candidate_stage", "pre_openmm_snapshot"),
        ("pre_relax_role", "candidate"),
        ("binder_chain", "A"),
        ("expected_chirality", "D"),
        ("first_observed_chirality_failure_stage", "none_observed"),
    ],
)
def test_v034_instrumented_pepglad_binds_stage_role_and_chirality_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    _rewrite_instrumented_runtime(
        fixture, lambda runtime: runtime.update({field: value})
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("baseline_replay_expected_sha256", "0" * 64),
        ("baseline_replay_observed_sha256", "0" * 64),
        ("baseline_replay_status", "mismatch"),
    ],
)
def test_v034_instrumented_pepglad_binds_seed42_baseline_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    _rewrite_instrumented_runtime(
        fixture, lambda runtime: runtime.update({field: value})
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_input_sha256", "0" * 64),
        ("target_preflight_verified", False),
    ],
)
def test_v034_instrumented_pepglad_binds_target_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    _rewrite_instrumented_runtime(
        fixture, lambda runtime: runtime.update({field: value})
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_commit", "0" * 40),
        ("source_entrypoint_sha256", "0" * 64),
        ("model_weights_sha256", "0" * 64),
        ("container_image", "unreviewed-image"),
        ("conda_environment", "unreviewed-env"),
    ],
)
def test_v034_instrumented_pepglad_binds_upstream_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    _rewrite_instrumented_runtime(
        fixture, lambda runtime: runtime.update({field: value})
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


def test_v034_instrumented_pepglad_validates_patch_json_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _write_instrumented_pepglad_failure(tmp_path, monkeypatch)
    patch_path = Path(fixture["patch"])
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    patch["source_entrypoint_prepatch_sha256"] = "0" * 64
    patch_path.write_text(
        json.dumps(patch, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _rewrite_instrumented_runtime(
        fixture,
        lambda runtime: runtime.update(
            observer_patch_evidence_sha256=_file_sha256(patch_path)
        ),
    )

    assert not _instrumented_pepglad_failure_valid(tmp_path, fixture)


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


def test_v035_gate_combines_six_historical_primaries_with_one_replayed_candidate(
    tmp_path: Path,
) -> None:
    write_v035_harness_fixture(tmp_path)

    historical = evaluate("current.v034_bounded_connectivity", tmp_path)
    current = evaluate_v035(tmp_path)
    current_details = dict(current.details)

    assert historical.verdict is GateVerdict.FAIL
    assert dict(historical.details)["primary_supported"] == 6
    assert historical.reason_code == "v034_bounded_connectivity_incomplete"
    assert current.verdict is GateVerdict.PASS
    assert current_details["historical_primary_supported"] == 6
    assert current_details["v035_primary_supported"] == 1
    assert current_details["combined_primary_supported"] == 7
    assert current_details["historical_bindings_valid"] is True
    assert current_details["v035_raw_replay_valid"] is True
    assert current_details["v035_evidence_valid"] is True


@pytest.mark.parametrize(
    ("artifact", "mutation"),
    [
        ("job.json", "missing"),
        ("job.json", "extra_field"),
        ("execution.json", "missing"),
        ("execution.json", "extra_field"),
        ("run_result.json", "missing"),
        ("run_result.json", "extra_field"),
    ],
)
def test_v035_gate_requires_exact_attempt_control_artifact_schema(
    tmp_path: Path,
    artifact: str,
    mutation: str,
) -> None:
    _, bundle = write_v035_harness_fixture(tmp_path)
    attempt = Path(bundle["execution"]["attempt_dir"])
    path = attempt / artifact
    if mutation == "missing":
        path.unlink()
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["unexpected"] = "tampered"
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    result = evaluate_v035(tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "v035_bounded_connectivity_incomplete"
    assert dict(result.details)["v035_raw_replay_valid"] is False


@pytest.mark.parametrize(
    ("artifact", "field", "value"),
    [
        ("job.json", "job_id", "v035_pepglad_other_fixture_seed42"),
        ("execution.json", "job_id", "v035_pepglad_other_fixture_seed42"),
        ("run_result.json", "overall_qc_status", "pass"),
        ("run_result.json", "status_reason", "forged_success"),
        ("run_result.json", "runtime_seconds", "0.000"),
        ("run_result.json", "created_at", "2026-07-14T00:00:00"),
    ],
)
def test_v035_gate_cross_binds_attempt_controls_to_authorization_and_replay(
    tmp_path: Path,
    artifact: str,
    field: str,
    value: object,
) -> None:
    _, bundle = write_v035_harness_fixture(tmp_path)
    attempt = Path(bundle["execution"]["attempt_dir"])
    path = attempt / artifact
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    result = evaluate_v035(tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "v035_bounded_connectivity_incomplete"
    assert dict(result.details)["v035_raw_replay_valid"] is False


@pytest.mark.parametrize(
    "relative_attempt",
    [
        "pepglad/v035_pepglad_3eqs_seed42/attempt_002",
        "pepglad/v035_pepglad_3eqs_seed43/attempt_001",
        "pepglad/v035_pepglad_other_fixture_seed42/attempt_001",
        "pepmlm/v035_pepmlm_fixture_seed42/attempt_001",
    ],
    ids=("retry", "seed43", "other_job", "other_method"),
)
def test_v035_gate_rejects_any_extra_attempt_in_derived_run_root(
    tmp_path: Path,
    relative_attempt: str,
) -> None:
    _, bundle = write_v035_harness_fixture(tmp_path)
    attempt = Path(bundle["execution"]["attempt_dir"])
    run_root = attempt.parents[2]
    (run_root / relative_attempt).mkdir(parents=True)

    result = evaluate_v035(tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "v035_bounded_connectivity_incomplete"
    assert dict(result.details)["v035_raw_replay_valid"] is False


def test_v035_gate_allows_runtime_symlink_inside_authorized_attempt(
    tmp_path: Path,
) -> None:
    _, bundle = write_v035_harness_fixture(tmp_path)
    attempt = Path(bundle["execution"]["attempt_dir"])
    checkpoint_dir = attempt / "work/checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "weights.bin").write_bytes(b"fixture weights\n")
    (checkpoint_dir / "codesign.ckpt").symlink_to("weights.bin")

    result = evaluate_v035(tmp_path)

    assert result.verdict is GateVerdict.PASS
    assert dict(result.details)["v035_raw_replay_valid"] is True


@pytest.mark.parametrize(
    "tamper",
    [
        "historical_content_rehashed",
        "raw_candidate_rehashed",
        "supported_qc_contradiction",
    ],
)
def test_v035_gate_fails_closed_without_trusting_bundle_support_boolean(
    tmp_path: Path,
    tamper: str,
) -> None:
    bundle_path, bundle = write_v035_harness_fixture(tmp_path)
    if tamper == "historical_content_rehashed":
        _coordinate_v034_history_tamper(tmp_path, bundle)
    elif tamper == "raw_candidate_rehashed":
        _coordinate_v035_raw_tamper(bundle)
    else:
        assert bundle["execution"]["supported_candidate"] is True
        bundle["qc"].update(
            chirality_status="fail",
            chirality_unknown_count=1,
            overall_qc_status="fail",
        )

    if tamper != "supported_qc_contradiction":
        from scripts.parse_v035_pepglad_connectivity import validate_bundle

        assert validate_bundle(bundle) is None
    _write_v035_bundle(bundle_path, bundle)
    result = evaluate_v035(tmp_path)
    details = dict(result.details)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "v035_bounded_connectivity_incomplete"
    assert details["v035_evidence_valid"] is False
    if tamper == "historical_content_rehashed":
        assert details["historical_bindings_valid"] is False
    elif tamper == "raw_candidate_rehashed":
        assert details["v035_raw_replay_valid"] is False


def test_v035_scoring_guard_scans_incremental_bundle_and_still_prohibits_scoring(
    tmp_path: Path,
) -> None:
    bundle_path, bundle = write_v035_harness_fixture(tmp_path)
    copy_artifacts(tmp_path, ["current_plan", "pilot_control_manifest"])
    assert "v035_pepglad_connectivity_bundle" in GATES["current.scoring_guard"][
        "inputs"
    ]

    clean = evaluate("current.scoring_guard", tmp_path)
    assert clean.verdict is GateVerdict.PASS

    bundle["runtime_provenance"]["producer_bindings"]["method_score"] = 0.9
    _write_v035_bundle(bundle_path, bundle)
    scored = evaluate("current.scoring_guard", tmp_path)

    assert scored.verdict is GateVerdict.FAIL
    assert scored.reason_code == "scoring_started_before_eligibility"
    assert "method_score" in dict(scored.details)["forbidden_result_columns"]


def test_v035_scoring_guard_does_not_treat_plan_boundary_words_as_results(
    tmp_path: Path,
) -> None:
    write_v035_harness_fixture(tmp_path)
    copy_artifacts(tmp_path, ["current_plan", "pilot_control_manifest"])
    plan = tmp_path / ARTIFACTS["current_plan"]["path"]
    plan.write_text(
        "本阶段禁止 scoring，不支持 ranking。\n",
        encoding="utf-8",
    )

    result = evaluate("current.scoring_guard", tmp_path)

    assert result.verdict is GateVerdict.PASS
    assert dict(result.details)["forbidden_result_markers"] == ()


@pytest.mark.parametrize(
    "result_marker",
    ["ranking_complete", "method_score=0.99", "best method identified"],
)
def test_v035_scoring_guard_rejects_result_marker_hidden_in_blocking_plan(
    tmp_path: Path,
    result_marker: str,
) -> None:
    write_v035_harness_fixture(tmp_path)
    copy_artifacts(tmp_path, ["current_plan", "pilot_control_manifest"])
    plan = tmp_path / ARTIFACTS["current_plan"]["path"]
    plan.write_text(
        f"本阶段禁止 scoring，不支持 ranking。\n状态：{result_marker}\n",
        encoding="utf-8",
    )

    result = evaluate("current.scoring_guard", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == "scoring_started_before_eligibility"


def test_current_scoring_guard_passes_while_full_scoring_gate_fails() -> None:
    assert evaluate("current.scoring_guard").verdict is GateVerdict.PASS
    assert evaluate("full.scoring_validation").verdict is GateVerdict.FAIL


def test_v034_scoring_guard_accepts_candidates_but_rejects_score_or_rank_evidence(
    tmp_path: Path,
) -> None:
    write_complete_v034_evidence(tmp_path)
    plan = tmp_path / ARTIFACTS["current_plan"]["path"]
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("本阶段不启动 scoring，不执行 ranking。\n", encoding="utf-8")

    passed = evaluate("current.scoring_guard", tmp_path)
    assert passed.verdict is GateVerdict.PASS
    assert dict(passed.details)["candidate_rows"] == 7

    candidate_path = tmp_path / ARTIFACTS["v034_candidate_outputs"]["path"]
    rewrite_csv(
        candidate_path,
        lambda rows: rows[0].update(notes="method_rank=1; best-performing"),
    )
    failed = evaluate("current.scoring_guard", tmp_path)

    assert failed.verdict is GateVerdict.FAIL
    assert failed.reason_code == "scoring_started_before_eligibility"
    assert dict(failed.details)["forbidden_result_markers"]


@pytest.mark.parametrize("score_field", ["method_score", "plddt"])
def test_v034_scoring_guard_scans_runtime_provenance_keys(
    tmp_path: Path, score_field: str
) -> None:
    write_complete_v034_evidence(tmp_path)
    plan = tmp_path / ARTIFACTS["current_plan"]["path"]
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("本阶段不启动 scoring，不执行 ranking。\n", encoding="utf-8")
    provenance_path = tmp_path / ARTIFACTS["v034_runtime_provenance"]["path"]
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["records"][0]["evidence"][score_field] = 0.9
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )

    result = evaluate("current.scoring_guard", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert score_field in dict(result.details)["forbidden_result_columns"]


def test_v034_scoring_guard_scans_failure_diagnostic_keys(tmp_path: Path) -> None:
    write_complete_v034_evidence(tmp_path)
    plan = tmp_path / ARTIFACTS["current_plan"]["path"]
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("本阶段不启动 scoring，不执行 ranking。\n", encoding="utf-8")
    diagnostic_path = tmp_path / ARTIFACTS["v034_failure_diagnostics"]["path"]
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    diagnostic["records"][0]["method_score"] = 0.9
    diagnostic_path.write_text(
        json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8"
    )

    result = evaluate("current.scoring_guard", tmp_path)

    assert result.verdict is GateVerdict.FAIL
    assert "method_score" in dict(result.details)["forbidden_result_columns"]


def test_current_claim_boundary_passes_while_empirical_pillar_is_unsupported() -> None:
    assert evaluate("current.manuscript_claim_boundary").verdict is GateVerdict.PASS
    assert evaluate("full.benchmark_pillars").verdict is GateVerdict.FAIL


def test_v034_claims_preserve_generation_and_provenance_boundaries() -> None:
    result = evaluate("current.manuscript_claim_boundary")
    rows = _read_rows(ROOT / ARTIFACTS["claim_evidence_map"]["path"])
    v034_rows = [row for row in rows if "v0.34" in row["claim"]]
    by_claim = {row["claim"]: row for row in v034_rows}

    assert result.verdict is GateVerdict.PASS
    assert dict(result.details)["v034_claim_rows"] == 4
    assert len(v034_rows) == 4

    primary = by_claim["v0.34 最新合并有 12 条候选记录，6 个 primary 通过基础 QC"]
    assert primary["status"] == "supported with verification caveat"
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
    ):
        assert wording in primary["allowed_wording"]
    for wording in (
        "7 个 primary 均可解析",
        "13 条 runtime provenance",
        "产生可评分候选",
        "方法性能可排名",
        "完整复现",
    ):
        assert wording in primary["forbidden_wording"]

    rf = by_claim["v0.34 RFdiffusion 与 ProteinMPNN 只完成 backbone-to-FASTA handoff"]
    assert rf["status"] == "supported with verification caveat"
    assert "未线程化 all-Gly backbone" in rf["allowed_wording"]
    assert "没有 sequence-resolved structure" in rf["allowed_wording"]

    provenance = by_claim[
        "v0.34 compact runtime provenance 有 12 条，PepGLAD 最新诊断因 replay mismatch 未纳入"
    ]
    assert provenance["status"] == "supported as limitation"
    assert "6 个 supported primary" in provenance["allowed_wording"]
    assert "6 个 supported seed43 candidates" in provenance["allowed_wording"]
    assert "pepglad_seed42_replay_mismatch" in provenance["allowed_wording"]
    assert "13 条 provenance" in provenance["forbidden_wording"]
    assert "完整可复现" in provenance["forbidden_wording"]

    dflow = by_claim["v0.34 D-Flow 3EQS 行只支持连通性检查"]
    assert dflow["status"] == "supported as boundary"
    assert "train overlap" in dflow["allowed_wording"]
    assert "公平 scoring 资格" in dflow["forbidden_wording"]


def test_v034_registry_roles_keep_latest_supported_rows_bounded() -> None:
    artifacts = {
        row["artifact_id"]: row
        for row in load_json(ROOT / "harness/registry/artifacts_v1.json")["artifacts"]
    }

    assert "failed parser attempt" in artifacts["v034_method_output_manifest"]["role"]
    for artifact_id in (
        "v034_candidate_outputs",
        "v034_candidate_qc",
        "v034_runtime_provenance",
    ):
        artifact = artifacts[artifact_id]
        assert "12 supported latest-attempt rows" in artifact["role"]
        assert "scoring_evidence" in artifact["forbidden_uses"]
        assert "method_ranking" in artifact["forbidden_uses"]
        assert "benchmark_result" in artifact["forbidden_uses"]


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
        path.write_text(
            "[generated broken link](missing-generated.md)\n", encoding="utf-8"
        )
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
