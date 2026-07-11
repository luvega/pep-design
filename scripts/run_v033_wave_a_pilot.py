#!/usr/bin/env python3
"""Run or package v0.33 Wave A adapter/parser completion jobs.

This layer targets only the v0.31 Wave A rows that failed because the bounded
pilot still used placeholder adapters. Runtime files stay under gitignored
benchmark_runs/. Tracked compact tables are produced by
scripts/parse_v033_pilot_outputs.py after execution.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOB_MANIFEST = ROOT / "benchmark" / "input_sets" / "pilot_benchmark_job_manifest_v0.30.csv"
DEFAULT_EXECUTION_MATRIX = ROOT / "benchmark" / "deployment" / "pilot_execution_matrix_v0.30.csv"
DEFAULT_V031_CANDIDATES = ROOT / "benchmark" / "results" / "pilot_candidate_outputs_v0.31.csv"
DEFAULT_RUN_ROOT = ROOT / "benchmark_runs" / "v0.33"

PLACEHOLDER_REASON = "adapter_execution_failed_or_not_implemented_exit_86"
EVIDENCE_BOUNDARY = "Bounded Wave A adapter/parser completion record only; not Benchmark result; not scoring evidence"
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

METHOD_SLUGS = {
    "DiffPepBuilder": "diffpepbuilder",
    "PepGLAD": "pepglad",
    "D-Flow / PeptideDesign": "dflow",
    "PepMirror": "pepmirror",
    "RFdiffusion + ProteinMPNN": "rfdiffusion_proteinmpnn",
}

METHOD_CONFIGS = {
    "DiffPepBuilder": {
        "slug": "diffpepbuilder",
        "environment_id": "pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder",
        "source_commit": "external_source_pinned_v0.19",
        "model_revision": "external_checkpoint_or_not_applicable",
        "candidate_globs": ["*.pdb", "outputs/*.pdb", "samples/*.pdb"],
    },
    "PepGLAD": {
        "slug": "pepglad",
        "environment_id": "pd-benchmark-methods-gpu:0.21/bench-pepglad",
        "source_commit": "external_source_pinned_v0.19",
        "model_revision": "pepglad_checkpoint_manifested_v0.21",
        "candidate_globs": ["*.pdb", "outputs/*.pdb", "samples/*.pdb"],
    },
    "D-Flow / PeptideDesign": {
        "slug": "dflow",
        "environment_id": "pd-benchmark-methods-gpu:0.21/bench-dflow",
        "source_commit": "external_source_pinned_v0.19",
        "model_revision": "dflow_checkpoint_and_pepmerge_manifested_v0.25",
        "candidate_globs": ["sample_*.pdb", "*.pdb", "outputs/*.pdb", "samples/*.pdb"],
    },
    "PepMirror": {
        "slug": "pepmirror",
        "environment_id": "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror",
        "source_commit": "external_source_pinned_v0.19",
        "model_revision": "pepmirror_checkpoint_manifested_v0.21",
        "candidate_globs": ["*.pdb", "outputs/*.pdb", "samples/*.pdb"],
    },
    "RFdiffusion + ProteinMPNN": {
        "slug": "rfdiffusion_proteinmpnn",
        "environment_id": "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest",
        "source_commit": "external_source_pinned_v0.19",
        "model_revision": "rfpeptide_and_proteinmpnn_external_weights",
        "candidate_globs": ["*.pdb", "backbones/*.pdb", "seqs/*.pdb", "outputs/*.pdb"],
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def slug_method(method: str) -> str:
    if method in METHOD_SLUGS:
        return METHOD_SLUGS[method]
    return re.sub(r"[^a-z0-9]+", "_", method.lower()).strip("_") or "unknown"


def shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def load_execution_matrix(path: Path = DEFAULT_EXECUTION_MATRIX) -> dict[str, dict[str, str]]:
    return {row["job_id"]: row for row in read_csv(path)}


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
    selected = [
        jobs_by_id[job_id]
        for job_id in sorted(placeholder_job_ids)
        if job_id in jobs_by_id
        and jobs_by_id[job_id].get("execution_wave") == "wave_a"
        and jobs_by_id[job_id].get("method") in METHOD_CONFIGS
    ]
    return selected


def output_dir_for(job: dict[str, str], run_root: Path) -> Path:
    return run_root / slug_method(job["method"]) / job["job_id"]


def write_input_manifest(job: dict[str, str], execution: dict[str, str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "input_manifest.json").write_text(
        json.dumps(
            {
                "job": job,
                "execution": execution,
                "v031_placeholder_reason": PLACEHOLDER_REASON,
                "evidence_boundary": EVIDENCE_BOUNDARY,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def method_config(method: str) -> dict[str, Any]:
    if method not in METHOD_CONFIGS:
        raise ValueError(f"No v0.33 method adapter config for {method}")
    return METHOD_CONFIGS[method]


def write_failed_job(
    *,
    job: dict[str, str],
    execution: dict[str, str],
    output_dir: Path,
    status_reason: str,
    exit_code: str,
    runtime_seconds: float = 0.0,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_input_manifest(job, execution, output_dir)
    config = method_config(job["method"])
    job_id = job["job_id"]
    method_row = {
        "run_record_id": f"{job_id}_v033_wave_a",
        "job_id": job_id,
        "method": job["method"],
        "task_id": job.get("task_id", ""),
        "execution_stage": EXECUTION_STAGE,
        "source_commit": config["source_commit"],
        "model_revision": config["model_revision"],
        "environment_id": execution.get("container_or_env") or config["environment_id"],
        "command": str(output_dir / "command.sh") if (output_dir / "command.sh").exists() else "not_run",
        "raw_output_root": str(output_dir),
        "stdout_log": str(output_dir / "stdout.log"),
        "stderr_log": str(output_dir / "stderr.log"),
        "runtime_seconds": f"{runtime_seconds:.3f}",
        "exit_code": exit_code,
        "parser_status": "failed",
        "status_reason": f"{status_reason}; not Benchmark result; not scoring evidence",
        "created_at": now_utc(),
    }
    candidate_row = {
        "design_id": f"{job_id}_failed",
        "job_id": job_id,
        "method": job["method"],
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
        "status_reason": status_reason,
        "notes": "Bounded v0.33 adapter completion attempt failed or produced no parseable candidate; not Benchmark result; not scoring evidence",
    }
    write_csv(output_dir / "method_output_manifest.csv", METHOD_OUTPUT_HEADERS, [method_row])
    write_csv(output_dir / "candidate_outputs.csv", CANDIDATE_HEADERS, [candidate_row])
    return {
        "execution_id": execution.get("execution_id", f"exec_{job_id}"),
        "job_id": job_id,
        "method": job["method"],
        "target_id": job.get("target_id", ""),
        "execution_wave": job.get("execution_wave", ""),
        "runner": execution.get("runner", ""),
        "container_or_env": execution.get("container_or_env") or config["environment_id"],
        "output_root": str(output_dir),
        "status": "failed",
        "exit_code": exit_code,
        "runtime_seconds": f"{runtime_seconds:.3f}",
        "parser_status": "failed",
        "candidate_count": "1",
        "blocked_reason": status_reason,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "next_action": "Inspect method-specific adapter logs and input contract before scoring or rerun.",
    }


def method_specific_adapter_text(job: dict[str, str], execution: dict[str, str], output_dir: Path) -> str:
    payload = {
        "job": job,
        "execution": execution,
        "config": method_config(job["method"]),
        "output_dir": str(output_dir),
        "method_output_headers": METHOD_OUTPUT_HEADERS,
        "candidate_headers": CANDIDATE_HEADERS,
        "execution_stage": EXECUTION_STAGE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    return f'''#!/usr/bin/env python3
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

PAYLOAD = json.loads({json.dumps(json.dumps(payload))})
JOB = PAYLOAD["job"]
EXECUTION = PAYLOAD["execution"]
CONFIG = PAYLOAD["config"]
OUT = Path(PAYLOAD["output_dir"])
AA3_TO_1 = {{
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}}


def write_csv(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({{header: row.get(header, "") for header in headers}})


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def method_slug():
    return CONFIG["slug"]


def find_candidate_pdbs():
    seen = set()
    candidates = []
    for pattern in CONFIG.get("candidate_globs", []):
        for path in sorted(OUT.glob(pattern)):
            if path.name == "input_manifest.json" or path.name.endswith("_input.pdb"):
                continue
            if path.is_file() and path.suffix.lower() == ".pdb" and path not in seen:
                seen.add(path)
                candidates.append(path)
    return candidates


def parse_pdb_sequence(path):
    residues = []
    seen = set()
    preferred = JOB.get("binder_chain") or ""
    chain_order = [preferred, "B", "A", ""] if preferred else ["B", "A", ""]
    atoms = []
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith(("ATOM  ", "HETATM")):
                continue
            resname = line[17:20].strip().upper()
            chain = line[21].strip()
            resseq = line[22:26].strip()
            icode = line[26].strip()
            atoms.append((chain, resseq, icode, resname))
    for chain in chain_order:
        for atom_chain, resseq, icode, resname in atoms:
            if chain and atom_chain != chain:
                continue
            key = (atom_chain, resseq, icode)
            if key in seen:
                continue
            seen.add(key)
            residues.append(AA3_TO_1.get(resname, "X"))
        if residues:
            return "".join(residues)
    return ""


def write_result(candidate_path, runtime):
    sequence = parse_pdb_sequence(candidate_path)
    parsed = bool(sequence)
    status_reason = f"{{method_slug()}}_standard_candidate_pdb_parsed" if parsed else f"{{method_slug()}}_candidate_pdb_sequence_empty"
    method_row = {{
        "run_record_id": f"{{JOB['job_id']}}_v033_wave_a",
        "job_id": JOB["job_id"],
        "method": JOB["method"],
        "task_id": JOB.get("task_id", ""),
        "execution_stage": PAYLOAD["execution_stage"],
        "source_commit": CONFIG["source_commit"],
        "model_revision": CONFIG["model_revision"],
        "environment_id": EXECUTION.get("container_or_env") or CONFIG["environment_id"],
        "command": str(OUT / "command.sh"),
        "raw_output_root": str(OUT),
        "stdout_log": str(OUT / "stdout.log"),
        "stderr_log": str(OUT / "stderr.log"),
        "runtime_seconds": f"{{runtime:.3f}}",
        "exit_code": "0",
        "parser_status": "parsed" if parsed else "failed",
        "status_reason": f"{{status_reason}}; not Benchmark result; not scoring evidence",
        "created_at": now_utc(),
    }}
    candidate_row = {{
        "design_id": f"{{JOB['job_id']}}_candidate_1" if parsed else f"{{JOB['job_id']}}_failed",
        "job_id": JOB["job_id"],
        "method": JOB["method"],
        "target_id": JOB.get("target_id", ""),
        "binder_id": "candidate_1" if parsed else "not_generated",
        "source_output_id": candidate_path.name if parsed else "not_generated",
        "generation_rank": "1" if parsed else "",
        "sequence": sequence if parsed else "",
        "structure_path": str(candidate_path) if parsed else "",
        "peptide_type": JOB.get("peptide_type", ""),
        "chirality": JOB.get("chirality", ""),
        "cyclic": JOB.get("cyclic", ""),
        "parse_status": "parsed" if parsed else "failed",
        "status_reason": status_reason,
        "notes": "Bounded v0.33 adapter completion row only; not Benchmark result; not scoring evidence",
    }}
    write_csv(OUT / "method_output_manifest.csv", PAYLOAD["method_output_headers"], [method_row])
    write_csv(OUT / "candidate_outputs.csv", PAYLOAD["candidate_headers"], [candidate_row])


def write_no_output(runtime):
    reason = f"{{method_slug()}}_adapter_attempt_no_supported_output_found"
    method_row = {{
        "run_record_id": f"{{JOB['job_id']}}_v033_wave_a",
        "job_id": JOB["job_id"],
        "method": JOB["method"],
        "task_id": JOB.get("task_id", ""),
        "execution_stage": PAYLOAD["execution_stage"],
        "source_commit": CONFIG["source_commit"],
        "model_revision": CONFIG["model_revision"],
        "environment_id": EXECUTION.get("container_or_env") or CONFIG["environment_id"],
        "command": str(OUT / "command.sh"),
        "raw_output_root": str(OUT),
        "stdout_log": str(OUT / "stdout.log"),
        "stderr_log": str(OUT / "stderr.log"),
        "runtime_seconds": f"{{runtime:.3f}}",
        "exit_code": "0",
        "parser_status": "failed",
        "status_reason": f"{{reason}}; not Benchmark result; not scoring evidence",
        "created_at": now_utc(),
    }}
    candidate_row = {{
        "design_id": f"{{JOB['job_id']}}_failed",
        "job_id": JOB["job_id"],
        "method": JOB["method"],
        "target_id": JOB.get("target_id", ""),
        "binder_id": "not_generated",
        "source_output_id": "not_generated",
        "generation_rank": "",
        "sequence": "",
        "structure_path": "",
        "peptide_type": JOB.get("peptide_type", ""),
        "chirality": JOB.get("chirality", ""),
        "cyclic": JOB.get("cyclic", ""),
        "parse_status": "failed",
        "status_reason": reason,
        "notes": "Bounded v0.33 adapter found no supported method output; not Benchmark result; not scoring evidence",
    }}
    write_csv(OUT / "method_output_manifest.csv", PAYLOAD["method_output_headers"], [method_row])
    write_csv(OUT / "candidate_outputs.csv", PAYLOAD["candidate_headers"], [candidate_row])


def main():
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = find_candidate_pdbs()
    runtime = max(time.monotonic() - start, 0.0)
    if candidates:
        write_result(candidates[0], runtime)
    else:
        write_no_output(runtime)


if __name__ == "__main__":
    main()
'''


def method_specific_command_text(output_dir: Path) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"python {shell_quote(str((output_dir / 'method_specific_adapter.py').resolve()))}",
            "",
        ]
    )


def write_command_package(job: dict[str, str], execution: dict[str, str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "method_specific_adapter.py").write_text(
        method_specific_adapter_text(job, execution, output_dir),
        encoding="utf-8",
    )
    command_path = output_dir / "command.sh"
    command_path.write_text(method_specific_command_text(output_dir), encoding="utf-8")
    command_path.chmod(0o755)
    write_input_manifest(job, execution, output_dir)


def summarize_existing_job(
    job: dict[str, str],
    execution: dict[str, str],
    output_dir: Path,
    runtime_seconds: float,
    exit_code: str,
) -> dict[str, str] | None:
    method_path = output_dir / "method_output_manifest.csv"
    candidate_path = output_dir / "candidate_outputs.csv"
    if not method_path.is_file() or not candidate_path.is_file():
        return None
    method_rows = read_csv(method_path)
    candidate_rows = read_csv(candidate_path)
    parser_status = method_rows[0].get("parser_status", "failed") if method_rows else "failed"
    parsed_count = sum(1 for row in candidate_rows if row.get("parse_status") == "parsed")
    status = "parsed" if parser_status == "parsed" and parsed_count else "failed"
    blocked_reason = "none" if status == "parsed" else (
        candidate_rows[0].get("status_reason", "") if candidate_rows else "parser_status_not_parsed"
    )
    config = method_config(job["method"])
    return {
        "execution_id": execution.get("execution_id", f"exec_{job['job_id']}"),
        "job_id": job["job_id"],
        "method": job["method"],
        "target_id": job.get("target_id", ""),
        "execution_wave": job.get("execution_wave", ""),
        "runner": execution.get("runner", ""),
        "container_or_env": execution.get("container_or_env") or config["environment_id"],
        "output_root": str(output_dir),
        "status": status,
        "exit_code": exit_code,
        "runtime_seconds": f"{runtime_seconds:.3f}",
        "parser_status": parser_status,
        "candidate_count": str(len(candidate_rows)),
        "blocked_reason": blocked_reason,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "next_action": (
            "Keep as bounded adapter/parser evidence; do not score or rank."
            if status == "parsed"
            else "Inspect method-specific adapter logs and input contract before scoring or rerun."
        ),
    }


def run_one_job(
    *,
    job: dict[str, str],
    execution: dict[str, str],
    output_dir: Path,
    execute: bool,
) -> dict[str, str]:
    write_command_package(job, execution, output_dir)
    if not execute:
        return write_failed_job(
            job=job,
            execution=execution,
            output_dir=output_dir,
            status_reason="dry_run_package_created_no_execution",
            exit_code="not_run",
        )

    start = time.monotonic()
    exit_code = "not_run"
    try:
        completed = subprocess.run(
            ["bash", str(output_dir / "command.sh")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=int(execution.get("max_runtime_sec") or 900),
        )
        (output_dir / "stdout.log").write_text(completed.stdout, encoding="utf-8")
        (output_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
        exit_code = str(completed.returncode)
    except subprocess.TimeoutExpired as exc:
        (output_dir / "stdout.log").write_text(exc.stdout or "", encoding="utf-8")
        (output_dir / "stderr.log").write_text((exc.stderr or "") + "\nTimed out\n", encoding="utf-8")
        exit_code = "124"
    runtime_seconds = max(time.monotonic() - start, 0.0)
    existing = summarize_existing_job(job, execution, output_dir, runtime_seconds, exit_code)
    if existing is not None and exit_code == "0":
        return existing
    return write_failed_job(
        job=job,
        execution=execution,
        output_dir=output_dir,
        status_reason=f"{slug_method(job['method'])}_adapter_attempt_failed_exit_{exit_code}",
        exit_code=exit_code,
        runtime_seconds=runtime_seconds,
    )


def run_wave_a(
    *,
    job_manifest: Path = DEFAULT_JOB_MANIFEST,
    v031_candidate_outputs: Path = DEFAULT_V031_CANDIDATES,
    execution_matrix: Path = DEFAULT_EXECUTION_MATRIX,
    run_root: Path = DEFAULT_RUN_ROOT,
    job_ids: set[str] | None = None,
    execute: bool = False,
    resume: bool = False,
    fail_fast: bool = False,
) -> list[dict[str, str]]:
    jobs = load_v033_jobs(job_manifest, v031_candidate_outputs)
    matrix = load_execution_matrix(execution_matrix)
    selected = [job for job in jobs if job_ids is None or job["job_id"] in job_ids]
    results: list[dict[str, str]] = []
    for job in selected:
        execution = matrix[job["job_id"]]
        output_dir = output_dir_for(job, run_root)
        if resume and (output_dir / "method_output_manifest.csv").exists() and (output_dir / "candidate_outputs.csv").exists():
            continue
        try:
            results.append(run_one_job(job=job, execution=execution, output_dir=output_dir, execute=execute))
        except Exception as exc:
            results.append(
                write_failed_job(
                    job=job,
                    execution=execution,
                    output_dir=output_dir,
                    status_reason=f"{slug_method(job['method'])}_runner_exception_{type(exc).__name__}: {exc}",
                    exit_code="runner_exception",
                )
            )
            if fail_fast:
                raise
    if results:
        write_csv(run_root / "pilot_execution_results_v0.33.csv", EXECUTION_RESULT_HEADERS, results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-manifest", type=Path, default=DEFAULT_JOB_MANIFEST)
    parser.add_argument("--v031-candidate-outputs", type=Path, default=DEFAULT_V031_CANDIDATES)
    parser.add_argument("--execution-matrix", type=Path, default=DEFAULT_EXECUTION_MATRIX)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--jobs", nargs="*", default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    execute = args.execute and not args.dry_run
    results = run_wave_a(
        job_manifest=args.job_manifest,
        v031_candidate_outputs=args.v031_candidate_outputs,
        execution_matrix=args.execution_matrix,
        run_root=args.run_root,
        job_ids=set(args.jobs) if args.jobs else None,
        execute=execute,
        resume=args.resume,
        fail_fast=args.fail_fast,
    )
    print(json.dumps({"jobs": len(results), "execute": execute}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
