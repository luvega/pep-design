#!/usr/bin/env python3
"""Validate or execute the single authorized v0.35 PepGLAD connectivity job."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_v034_wave_a_generation as v034_runner
from scripts.v035_adapters import pepglad


DEFAULT_JOB_MANIFEST = (
    ROOT / "benchmark/input_sets/pilot_pepglad_job_manifest_v0.35.csv"
)
DEFAULT_EXECUTION_MATRIX = (
    ROOT / "benchmark/deployment/pilot_pepglad_execution_matrix_v0.35.csv"
)
DEFAULT_RUN_ROOT = ROOT / "benchmark_runs/v0.35"

AUTHORIZED_JOB = {
    "job_id": "v035_pepglad_3eqs_seed42",
    "method": "PepGLAD",
    "task_id": "T2_structure_peptide_binder",
    "target_id": "mdm2_p53_3eqs_fixture",
    "input_mode": "pdb_pocket_json",
    "target_sequence": "",
    "target_pdb": "3EQS",
    "target_chains": "A",
    "binder_chain": "B",
    "pocket_definition": "pocket_from_target_chain_A_reference_chain_B",
    "peptide_type": "linear",
    "chirality": "L",
    "cyclic": "no",
    "n_designs_requested": "1",
    "random_seed": "42",
    "adapter_config": "v035_pepglad_3eqs_adapter",
    "status": "authorized_bounded_connectivity",
    "notes": "Prospective mixed L/D connectivity candidate only",
    "pilot_target_id": "mdm2_p53_3eqs_fixture",
    "pilot_lane": "structure_generation",
    "execution_wave": "wave_a_v035",
    "expected_output_contract": "candidate_outputs_method_manifest_and_qc",
    "failure_policy": "fail_closed_on_missing_pocket_or_pdb",
    "evidence_boundary": (
        "Bounded connectivity evidence only; not Benchmark result, scoring, or ranking"
    ),
    "length_min": "11",
    "length_max": "11",
    "expected_target_chain": "A",
    "expected_binder_chain": "B",
    "chirality_constraint": "unrestricted",
    "chirality_check_mode": "report_only",
    "baseline_replay_policy": "warn_on_mismatch",
    "cyclic_check_mode": "not_applicable",
    "noncanonical_policy": "warn_and_accept",
    "seed_stage": "primary",
    "primary_job_id": "",
    "effective_seed_required": "yes",
    "target_pdb_path": "data/dflow/pdbs/3EQS.pdb",
    "target_pdb_sha256": pepglad.TARGET_INPUT_SHA256,
    "target_binding_check_mode": "sequence_and_sha256",
}

AUTHORIZED_EXECUTION = {
    "execution_id": "exec_v035_pepglad_3eqs_seed42",
    "job_id": "v035_pepglad_3eqs_seed42",
    "method": "PepGLAD",
    "target_id": "mdm2_p53_3eqs_fixture",
    "execution_wave": "wave_a_v035",
    "runner": "v035_pepglad_adapter",
    "container_or_env": "pd-benchmark-methods-gpu:0.21/bench-pepglad",
    "gpu_required": "yes",
    "max_runtime_sec": "900",
    "output_root": (
        "benchmark_runs/v0.35/pepglad/v035_pepglad_3eqs_seed42"
    ),
    "expected_parser": (
        "method_output_manifest.csv;candidate_outputs.csv;candidate_qc.csv"
    ),
    "status": "authorized_bounded_connectivity",
    "blocked_reason": "none",
    "evidence_boundary": (
        "Bounded connectivity evidence only; not Benchmark result, scoring, or ranking"
    ),
    "next_action": "Run exactly one authorized primary attempt",
    "seed_stage": "primary",
    "primary_job_id": "",
    "random_seed": "42",
    "target_pdb_sha256": pepglad.TARGET_INPUT_SHA256,
    "length_min": "11",
    "length_max": "11",
    "expected_target_chain": "A",
    "expected_binder_chain": "B",
    "chirality_constraint": "unrestricted",
    "chirality_check_mode": "report_only",
    "baseline_replay_policy": "warn_on_mismatch",
}


def _load_exact_authorized_row(
    path: Path, expected: Mapping[str, str], label: str
) -> dict[str, str]:
    try:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            parsed = list(csv.reader(handle, strict=True))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"cannot read authorized v0.35 {label}") from exc
    parsed = [row for row in parsed if row]
    if len(parsed) != 2:
        raise ValueError(f"v0.35 {label} must contain exactly one authorized row")
    headers, values = parsed
    if (
        len(headers) != len(set(headers))
        or any(not header for header in headers)
        or len(values) != len(headers)
    ):
        raise ValueError(f"v0.35 {label} does not match the authorized schema")
    row = dict(zip(headers, values))
    if row != dict(expected):
        raise ValueError(f"v0.35 {label} row is not the exact authorized row")
    return row


def load_authorized_job(
    path: Path = DEFAULT_JOB_MANIFEST,
) -> dict[str, str]:
    return _load_exact_authorized_row(path, AUTHORIZED_JOB, "job manifest")


def load_authorized_jobs(
    path: Path = DEFAULT_JOB_MANIFEST,
) -> list[dict[str, str]]:
    return [load_authorized_job(path)]


def load_authorized_execution(
    path: Path = DEFAULT_EXECUTION_MATRIX,
) -> dict[str, str]:
    return _load_exact_authorized_row(
        path, AUTHORIZED_EXECUTION, "execution matrix"
    )


def _job_root(run_root: Path, job: Mapping[str, str]) -> Path:
    return Path(run_root) / "pepglad" / job["job_id"]


def validate_execution_request(
    job: Mapping[str, str],
    *,
    retry_failed: bool,
    run_root: Path = DEFAULT_RUN_ROOT,
) -> None:
    if retry_failed:
        raise ValueError("v0.35 PepGLAD retry is not authorized")
    if dict(job) != AUTHORIZED_JOB:
        raise ValueError("request does not match the exact authorized v0.35 job")
    job_root = _job_root(Path(run_root), job)
    if job_root.is_symlink():
        raise ValueError(f"v0.35 PepGLAD evidence is already recorded: {job_root}")
    if job_root.exists() and not job_root.is_dir():
        raise ValueError(f"v0.35 PepGLAD evidence is already recorded: {job_root}")
    if job_root.is_dir():
        for child in job_root.iterdir():
            if child.is_symlink() or re.fullmatch(r"attempt_[0-9]{3}", child.name):
                raise ValueError(
                    f"v0.35 PepGLAD attempt is already recorded: {child}"
                )


def _validate_job_execution_binding(
    job: Mapping[str, str], execution: Mapping[str, str]
) -> None:
    if dict(execution) != AUTHORIZED_EXECUTION:
        raise ValueError("execution matrix does not match the exact authorized row")
    shared = (
        "job_id",
        "method",
        "random_seed",
        "seed_stage",
        "target_pdb_sha256",
        "length_min",
        "length_max",
        "expected_target_chain",
        "expected_binder_chain",
        "chirality_constraint",
        "chirality_check_mode",
        "baseline_replay_policy",
    )
    if any(job.get(field) != execution.get(field) for field in shared):
        raise ValueError("authorized job and execution matrix are inconsistent")


def execute_authorized_job(
    job: Mapping[str, str],
    *,
    execution: Mapping[str, str] | None = None,
    execute: bool,
    run_root: Path = DEFAULT_RUN_ROOT,
) -> dict[str, Any]:
    selected_execution = (
        dict(execution) if execution is not None else load_authorized_execution()
    )
    validate_execution_request(job, retry_failed=False, run_root=run_root)
    _validate_job_execution_binding(job, selected_execution)
    if not execute:
        return {
            "job_id": job["job_id"],
            "method": job["method"],
            "status": "validated",
            "status_reason": "authorization_validated_without_attempt_creation",
            "overall_qc_status": "not_run",
        }
    return v034_runner.run_job(
        job,
        selected_execution,
        run_root=Path(run_root),
        execute=True,
        retry_failed=False,
        adapter=pepglad,
        qc_evaluator=pepglad.evaluate_candidate,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    job = load_authorized_job()
    execution = load_authorized_execution()
    validate_execution_request(job, retry_failed=False)
    if args.dry_run:
        result: dict[str, Any] = {
            "job_id": job["job_id"],
            "method": job["method"],
            "status": "validated",
            "status_reason": "authorization_validated_without_attempt_creation",
            "overall_qc_status": "not_run",
        }
    else:
        result = execute_authorized_job(job, execution=execution, execute=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"validated", "packaged", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
