#!/usr/bin/env python3
"""Merge v0.33 Wave A adapter/parser completion outputs into compact KB tables."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOB_MANIFEST = ROOT / "benchmark" / "input_sets" / "pilot_benchmark_job_manifest_v0.30.csv"
DEFAULT_EXECUTION_MATRIX = ROOT / "benchmark" / "deployment" / "pilot_execution_matrix_v0.30.csv"
DEFAULT_V031_CANDIDATES = ROOT / "benchmark" / "results" / "pilot_candidate_outputs_v0.31.csv"
DEFAULT_RUN_ROOT = ROOT / "benchmark_runs" / "v0.33"
DEFAULT_OUT_DIR = ROOT / "benchmark" / "results"
DEFAULT_DEPLOYMENT_DIR = ROOT / "benchmark" / "deployment"

PLACEHOLDER_REASON = "adapter_execution_failed_or_not_implemented_exit_86"
EVIDENCE_BOUNDARY = "Bounded Wave A adapter/parser completion merge only; not Benchmark result; not scoring evidence"
EXECUTION_STAGE = "bounded_wave_a_adapter_completion_v0.33"

METHOD_OUTPUT_HEADERS = [
    "run_record_id",
    "job_id",
    "method",
    "task_id",
    "execution_stage",
    "source_commit",
    "model_revision",
    "environment_id",
    "command",
    "raw_output_root",
    "stdout_log",
    "stderr_log",
    "runtime_seconds",
    "exit_code",
    "parser_status",
    "status_reason",
    "created_at",
]

CANDIDATE_HEADERS = [
    "design_id",
    "job_id",
    "method",
    "target_id",
    "binder_id",
    "source_output_id",
    "generation_rank",
    "sequence",
    "structure_path",
    "peptide_type",
    "chirality",
    "cyclic",
    "parse_status",
    "status_reason",
    "notes",
]

EXECUTION_RESULT_HEADERS = [
    "execution_id",
    "job_id",
    "method",
    "target_id",
    "execution_wave",
    "runner",
    "container_or_env",
    "output_root",
    "status",
    "exit_code",
    "runtime_seconds",
    "parser_status",
    "candidate_count",
    "blocked_reason",
    "evidence_boundary",
    "next_action",
]

RUN_HEADERS = [
    "design_id",
    "method",
    "task_id",
    "target_id",
    "binder_id",
    "input_mode",
    "target_sequence",
    "target_pdb",
    "target_chains",
    "binder_chain",
    "pocket_definition",
    "peptide_type",
    "chirality",
    "cyclic",
    "status",
    "notes",
    "parent_job_id",
    "source_output_id",
    "generation_rank",
    "random_seed",
    "adapter_status",
    "status_reason",
]

METHOD_CONFIGS = {
    "DiffPepBuilder": "pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder",
    "PepGLAD": "pd-benchmark-methods-gpu:0.21/bench-pepglad",
    "D-Flow / PeptideDesign": "pd-benchmark-methods-gpu:0.21/bench-dflow",
    "PepMirror": "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror",
    "RFdiffusion + ProteinMPNN": "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def load_v033_jobs(
    job_manifest: Path = DEFAULT_JOB_MANIFEST,
    v031_candidate_outputs: Path = DEFAULT_V031_CANDIDATES,
) -> list[dict[str, str]]:
    jobs_by_id = {row["job_id"]: row for row in read_csv(job_manifest)}
    placeholder_job_ids = {
        row["job_id"]
        for row in read_csv(v031_candidate_outputs)
        if row.get("parse_status") == "failed" and row.get("status_reason") == PLACEHOLDER_REASON
    }
    return [
        jobs_by_id[job_id]
        for job_id in sorted(placeholder_job_ids)
        if job_id in jobs_by_id
        and jobs_by_id[job_id].get("execution_wave") == "wave_a"
        and jobs_by_id[job_id].get("method") in METHOD_CONFIGS
    ]


def execution_matrix_rows(path: Path = DEFAULT_EXECUTION_MATRIX) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row.get("job_id", ""): row for row in read_csv(path)}


def find_job_dir(run_root: Path, job_id: str) -> Path | None:
    direct = run_root / job_id
    if direct.exists():
        return direct
    matches = sorted(run_root.glob(f"*/{job_id}"))
    if matches:
        return matches[0]
    return None


def failed_method_row(job: dict[str, str], raw_output_root: Path | None, reason: str) -> dict[str, str]:
    output_root = str(raw_output_root) if raw_output_root is not None else "not_found"
    return {
        "run_record_id": f"{job['job_id']}_v033_wave_a",
        "job_id": job["job_id"],
        "method": job.get("method", ""),
        "task_id": job.get("task_id", ""),
        "execution_stage": EXECUTION_STAGE,
        "source_commit": "external_or_not_applicable",
        "model_revision": "external_or_not_applicable",
        "environment_id": METHOD_CONFIGS.get(job.get("method", ""), "unknown"),
        "command": str(raw_output_root / "command.sh") if raw_output_root is not None else "not_run",
        "raw_output_root": output_root,
        "stdout_log": str(raw_output_root / "stdout.log") if raw_output_root is not None else "not_run",
        "stderr_log": str(raw_output_root / "stderr.log") if raw_output_root is not None else "not_run",
        "runtime_seconds": "0.000",
        "exit_code": "not_run",
        "parser_status": "failed",
        "status_reason": f"{reason}; not Benchmark result; not scoring evidence",
        "created_at": now_utc(),
    }


def failed_candidate_row(job: dict[str, str], reason: str) -> dict[str, str]:
    return {
        "design_id": f"{job['job_id']}_failed",
        "job_id": job["job_id"],
        "method": job.get("method", ""),
        "target_id": job.get("target_id", ""),
        "binder_id": "not_generated",
        "source_output_id": "not_generated",
        "generation_rank": "",
        "sequence": "",
        "structure_path": "",
        "peptide_type": job.get("peptide_type", ""),
        "chirality": job.get("chirality", ""),
        "cyclic": job.get("cyclic", ""),
        "parse_status": "failed",
        "status_reason": reason,
        "notes": "Bounded v0.33 adapter/parser output missing or failed; not Benchmark result; not scoring evidence",
    }


def run_row_from_candidate(candidate: dict[str, str], job: dict[str, str]) -> dict[str, str]:
    parsed = candidate.get("parse_status") == "parsed"
    return {
        "design_id": candidate.get("design_id", ""),
        "method": candidate.get("method", job.get("method", "")),
        "task_id": job.get("task_id", ""),
        "target_id": candidate.get("target_id", job.get("target_id", "")),
        "binder_id": candidate.get("binder_id", ""),
        "input_mode": job.get("input_mode", ""),
        "target_sequence": job.get("target_sequence", ""),
        "target_pdb": job.get("target_pdb", ""),
        "target_chains": job.get("target_chains", ""),
        "binder_chain": job.get("binder_chain", ""),
        "pocket_definition": job.get("pocket_definition", ""),
        "peptide_type": candidate.get("peptide_type", job.get("peptide_type", "")),
        "chirality": candidate.get("chirality", job.get("chirality", "")),
        "cyclic": candidate.get("cyclic", job.get("cyclic", "")),
        "status": "generated" if parsed else "failed",
        "notes": "Bounded v0.33 adapter/parser row only; not Benchmark result; not scoring evidence",
        "parent_job_id": job.get("job_id", ""),
        "source_output_id": candidate.get("source_output_id", ""),
        "generation_rank": candidate.get("generation_rank", ""),
        "random_seed": job.get("random_seed", ""),
        "adapter_status": candidate.get("parse_status", ""),
        "status_reason": candidate.get("status_reason", ""),
    }


def execution_row_from_outputs(
    *,
    job: dict[str, str],
    execution: dict[str, str],
    job_dir: Path | None,
    method_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
) -> dict[str, str]:
    method_row = method_rows[0] if method_rows else {}
    parsed_count = sum(1 for row in candidate_rows if row.get("parse_status") == "parsed")
    parser_status = method_row.get("parser_status") or ("parsed" if parsed_count else "failed")
    status = "parsed" if parser_status == "parsed" and parsed_count else "failed"
    output_root = (
        method_row.get("raw_output_root")
        or (str(job_dir) if job_dir is not None else "")
        or execution.get("output_root")
        or "not_found"
    )
    blocked_reason = "none"
    if status != "parsed":
        blocked_reason = (
            (candidate_rows[0].get("status_reason", "") if candidate_rows else "")
            or method_row.get("status_reason", "")
            or "missing_or_failed_parser_output"
        )
    return {
        "execution_id": execution.get("execution_id", f"exec_{job['job_id']}_v033"),
        "job_id": job["job_id"],
        "method": job.get("method", ""),
        "target_id": job.get("target_id", ""),
        "execution_wave": job.get("execution_wave", ""),
        "runner": execution.get("runner", ""),
        "container_or_env": execution.get("container_or_env") or method_row.get("environment_id", ""),
        "output_root": output_root,
        "status": status,
        "exit_code": method_row.get("exit_code", "not_run"),
        "runtime_seconds": method_row.get("runtime_seconds", "0.000"),
        "parser_status": parser_status,
        "candidate_count": str(len(candidate_rows)),
        "blocked_reason": blocked_reason,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "next_action": (
            "Keep as bounded v0.33 adapter/parser evidence; do not score or rank."
            if status == "parsed"
            else "Inspect method-specific adapter logs and input contract before scoring or rerun."
        ),
    }


def merge_v033_outputs(
    *,
    job_manifest: Path = DEFAULT_JOB_MANIFEST,
    v031_candidate_outputs: Path = DEFAULT_V031_CANDIDATES,
    execution_matrix: Path = DEFAULT_EXECUTION_MATRIX,
    run_root: Path = DEFAULT_RUN_ROOT,
    out_dir: Path = DEFAULT_OUT_DIR,
    deployment_dir: Path = DEFAULT_DEPLOYMENT_DIR,
) -> dict[str, int]:
    jobs = load_v033_jobs(job_manifest, v031_candidate_outputs)
    matrix = execution_matrix_rows(execution_matrix)
    method_rows: list[dict[str, str]] = []
    candidate_rows: list[dict[str, str]] = []
    run_rows: list[dict[str, str]] = []
    execution_rows: list[dict[str, str]] = []

    for job in jobs:
        job_dir = find_job_dir(run_root, job["job_id"])
        method_path = job_dir / "method_output_manifest.csv" if job_dir is not None else None
        candidate_path = job_dir / "candidate_outputs.csv" if job_dir is not None else None
        if method_path is not None and method_path.is_file():
            job_method_rows = read_csv(method_path)
        else:
            job_method_rows = [failed_method_row(job, job_dir, "missing_v033_method_output_manifest")]
        if candidate_path is not None and candidate_path.is_file():
            job_candidate_rows = read_csv(candidate_path)
        else:
            job_candidate_rows = [failed_candidate_row(job, "missing_v033_candidate_outputs")]

        method_rows.extend(job_method_rows)
        candidate_rows.extend(job_candidate_rows)
        run_rows.extend(run_row_from_candidate(row, job) for row in job_candidate_rows)
        execution_rows.append(
            execution_row_from_outputs(
                job=job,
                execution=matrix.get(job["job_id"], {}),
                job_dir=job_dir,
                method_rows=job_method_rows,
                candidate_rows=job_candidate_rows,
            )
        )

    write_csv(out_dir / "pilot_method_output_manifest_v0.33.csv", METHOD_OUTPUT_HEADERS, method_rows)
    write_csv(out_dir / "pilot_candidate_outputs_v0.33.csv", CANDIDATE_HEADERS, candidate_rows)
    write_csv(out_dir / "pilot_run_v0.33.csv", RUN_HEADERS, run_rows)
    write_csv(deployment_dir / "pilot_execution_results_v0.33.csv", EXECUTION_RESULT_HEADERS, execution_rows)
    (out_dir / "pilot_v033_merge_summary.json").write_text(
        json.dumps(
            {
                "wave_a_jobs": len(jobs),
                "method_rows": len(method_rows),
                "candidate_rows": len(candidate_rows),
                "run_rows": len(run_rows),
                "execution_rows": len(execution_rows),
                "evidence_boundary": EVIDENCE_BOUNDARY,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "wave_a_jobs": len(jobs),
        "method_rows": len(method_rows),
        "candidate_rows": len(candidate_rows),
        "run_rows": len(run_rows),
        "execution_rows": len(execution_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-manifest", type=Path, default=DEFAULT_JOB_MANIFEST)
    parser.add_argument("--v031-candidate-outputs", type=Path, default=DEFAULT_V031_CANDIDATES)
    parser.add_argument("--execution-matrix", type=Path, default=DEFAULT_EXECUTION_MATRIX)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--deployment-dir", type=Path, default=DEFAULT_DEPLOYMENT_DIR)
    args = parser.parse_args()
    result = merge_v033_outputs(
        job_manifest=args.job_manifest,
        v031_candidate_outputs=args.v031_candidate_outputs,
        execution_matrix=args.execution_matrix,
        run_root=args.run_root,
        out_dir=args.out_dir,
        deployment_dir=args.deployment_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
