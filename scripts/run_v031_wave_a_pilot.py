#!/usr/bin/env python3
"""Run or package v0.31 bounded Wave A pilot jobs.

Large runtime outputs stay under gitignored benchmark_runs/. Tracked result
tables are produced by scripts/parse_v031_pilot_outputs.py after execution.
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
DEFAULT_RUN_ROOT = ROOT / "benchmark_runs" / "v0.31"
DEFAULT_7ZKR_PDB = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion/examples/input_pdbs/7zkr_GABARAP.pdb")

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
    "PepMLM": "pepmlm",
    "DiffPepBuilder": "diffpepbuilder",
    "PepGLAD": "pepglad",
    "D-Flow / PeptideDesign": "dflow",
    "PepMirror": "pepmirror",
    "RFdiffusion + ProteinMPNN": "rfdiffusion_proteinmpnn",
    "AfCycDesign / ColabDesign cyclic peptide": "colabdesign",
}


def shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


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


def load_wave_a_jobs(job_manifest: Path = DEFAULT_JOB_MANIFEST) -> list[dict[str, str]]:
    return [row for row in read_csv(job_manifest) if row.get("execution_wave") == "wave_a"]


def load_execution_matrix(path: Path = DEFAULT_EXECUTION_MATRIX) -> dict[str, dict[str, str]]:
    return {row["job_id"]: row for row in read_csv(path)}


def output_dir_for(job: dict[str, str], execution: dict[str, str], run_root: Path) -> Path:
    output_root = execution.get("output_root", "")
    if output_root.startswith("benchmark_runs/v0.31/"):
        return ROOT / output_root
    return run_root / slug_method(job["method"]) / job["job_id"]


def write_input_manifest(job: dict[str, str], execution: dict[str, str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "input_manifest.json").write_text(
        json.dumps(
            {
                "job": job,
                "execution": execution,
                "evidence_boundary": "Bounded Wave A pilot input manifest only; not Benchmark result",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


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
    method = job["method"]
    job_id = job["job_id"]
    method_row = {
        "run_record_id": f"{job_id}_v031_wave_a",
        "job_id": job_id,
        "method": method,
        "task_id": job.get("task_id", ""),
        "execution_stage": "bounded_wave_a_pilot",
        "source_commit": "external_or_not_applicable",
        "model_revision": "external_or_not_applicable",
        "environment_id": execution.get("container_or_env", ""),
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
        "method": method,
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
        "notes": "Bounded Wave A pilot failed or did not produce a parseable candidate; not Benchmark result; not scoring evidence",
    }
    write_csv(output_dir / "method_output_manifest.csv", METHOD_OUTPUT_HEADERS, [method_row])
    write_csv(output_dir / "candidate_outputs.csv", CANDIDATE_HEADERS, [candidate_row])
    return {
        "execution_id": execution.get("execution_id", f"exec_{job_id}"),
        "job_id": job_id,
        "method": method,
        "target_id": job.get("target_id", ""),
        "execution_wave": job.get("execution_wave", ""),
        "runner": execution.get("runner", ""),
        "container_or_env": execution.get("container_or_env", ""),
        "output_root": str(output_dir),
        "status": "failed",
        "exit_code": exit_code,
        "runtime_seconds": f"{runtime_seconds:.3f}",
        "parser_status": "failed",
        "candidate_count": "1",
        "blocked_reason": status_reason,
        "evidence_boundary": "Bounded Wave A pilot execution record only; not Benchmark result; not scoring evidence",
        "next_action": "Inspect method logs and adapter contract before scoring or rerun.",
    }


def pepmlm_adapter_text(job: dict[str, str], output_dir: Path) -> str:
    payload = {
        "job_id": job["job_id"],
        "method": job["method"],
        "task_id": job["task_id"],
        "target_id": job["target_id"],
        "target_sequence": job["target_sequence"],
        "peptide_type": job["peptide_type"],
        "chirality": job["chirality"],
        "cyclic": job["cyclic"],
        "random_seed": int(job["random_seed"]),
        "host_output_dir": str(output_dir),
    }
    return f'''#!/usr/bin/env python3
import csv
import json
import random
import time
from pathlib import Path

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

JOB = json.loads({json.dumps(json.dumps(payload))})
METHOD_OUTPUT_HEADERS = {json.dumps(METHOD_OUTPUT_HEADERS)}
CANDIDATE_HEADERS = {json.dumps(CANDIDATE_HEADERS)}
OUT = Path("/data/outputs")
MODEL_ID = "TianlaiChen/PepMLM-650M"


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({{header: row.get(header, "") for header in headers}})


start = time.monotonic()
random.seed(JOB["random_seed"])
torch.manual_seed(JOB["random_seed"])
target = JOB["target_sequence"]
mask_count = max(target.count("X"), 1)
protein_seq = target.replace("X", "")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForMaskedLM.from_pretrained(MODEL_ID).to("cuda" if torch.cuda.is_available() else "cpu")
model.eval()
masked = tokenizer.mask_token * mask_count
inputs = tokenizer(protein_seq + masked, return_tensors="pt").to(model.device)
with torch.no_grad():
    logits = model(**inputs).logits
mask_idx = (inputs["input_ids"] == tokenizer.mask_token_id).nonzero(as_tuple=True)[1]
tokens = logits[0, mask_idx].argmax(dim=-1)
peptide = tokenizer.decode(tokens, skip_special_tokens=True).replace(" ", "")
runtime = max(time.monotonic() - start, 0.0)

raw_path = OUT / "pepmlm_generated.csv"
write_csv(raw_path, ["job_id", "generated_binder", "binder_rank", "target_id"], [
    {{
        "job_id": JOB["job_id"],
        "generated_binder": peptide,
        "binder_rank": "1",
        "target_id": JOB["target_id"],
    }}
])
method_row = {{
    "run_record_id": f"{{JOB['job_id']}}_v031_wave_a",
    "job_id": JOB["job_id"],
    "method": JOB["method"],
    "task_id": JOB["task_id"],
    "execution_stage": "bounded_wave_a_pilot",
    "source_commit": "3169c49",
    "model_revision": MODEL_ID,
    "environment_id": "pd-benchmark-methods-gpu:0.21/bench-pepmlm",
    "command": str(Path(JOB["host_output_dir"]) / "command.sh"),
    "raw_output_root": JOB["host_output_dir"],
    "stdout_log": str(Path(JOB["host_output_dir"]) / "stdout.log"),
    "stderr_log": str(Path(JOB["host_output_dir"]) / "stderr.log"),
    "runtime_seconds": f"{{runtime:.3f}}",
    "exit_code": "0",
    "parser_status": "parsed" if peptide else "failed",
    "status_reason": "pepmlm_v031_sequence_parsed; not Benchmark result; not scoring evidence" if peptide else "pepmlm_v031_empty_output; not Benchmark result; not scoring evidence",
    "created_at": "2026-07-09",
}}
candidate_row = {{
    "design_id": f"{{JOB['job_id']}}_candidate_1",
    "job_id": JOB["job_id"],
    "method": JOB["method"],
    "target_id": JOB["target_id"],
    "binder_id": "pepmlm_rank1",
    "source_output_id": raw_path.name,
    "generation_rank": "1",
    "sequence": peptide,
    "structure_path": "",
    "peptide_type": JOB["peptide_type"],
    "chirality": JOB["chirality"],
    "cyclic": JOB["cyclic"],
    "parse_status": "parsed" if peptide else "failed",
    "status_reason": "pepmlm_masked_sequence_generated" if peptide else "pepmlm_empty_output",
    "notes": "Bounded Wave A PepMLM pilot only; not Benchmark result; not scoring evidence",
}}
write_csv(OUT / "method_output_manifest.csv", METHOD_OUTPUT_HEADERS, [method_row])
write_csv(OUT / "candidate_outputs.csv", CANDIDATE_HEADERS, [candidate_row])
(OUT / "pepmlm_runtime_result.json").write_text(
    json.dumps({{"job_id": JOB["job_id"], "sequence": peptide, "runtime_seconds": runtime, "not_benchmark_result": True}}, indent=2) + "\\n",
    encoding="utf-8",
)
'''


def pepmlm_command_text(output_dir: Path) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "docker run --rm --gpus all --shm-size 16g "
            "-e HF_HOME=/data/benchmark_models/huggingface "
            "-e TRANSFORMERS_CACHE=/data/benchmark_models/huggingface "
            "-v /data/protein-design/data/benchmark_models:/data/benchmark_models "
            f"-v {shell_quote(str(output_dir.resolve()))}:/data/outputs "
            "--workdir /data/outputs "
            "pd-benchmark-methods-gpu:0.21 "
            "bash -lc 'source /opt/conda/etc/profile.d/conda.sh && conda activate bench-pepmlm && python /data/outputs/pepmlm_v031_adapter.py'",
            "",
        ]
    )


def colabdesign_command_text(job: dict[str, str], output_dir: Path, execution: dict[str, str]) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"python {shell_quote(str(ROOT / 'scripts' / 'run_colabdesign_bounded_generation.py'))} "
            f"--output-dir {shell_quote(str(output_dir.resolve()))} "
            f"--target-pdb {shell_quote(str(DEFAULT_7ZKR_PDB))} "
            f"--job-id {shell_quote(job['job_id'])} "
            f"--target-id {shell_quote(job['target_id'])} "
            f"--task-id {shell_quote(job['task_id'])} "
            f"--random-seed {shell_quote(job['random_seed'])} "
            f"--peptide-type {shell_quote(job.get('peptide_type') or 'cyclic')} "
            f"--chirality {shell_quote(job.get('chirality') or 'L')} "
            f"--cyclic {shell_quote(job.get('cyclic') or 'yes')} "
            f"--binder-len 14 "
            "--inner-command-filename colabdesign_inner_command.sh "
            f"--timeout-sec {shell_quote(execution.get('max_runtime_sec') or '900')}",
            "",
        ]
    )


def placeholder_command_text(job: dict[str, str]) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"# v0.31 bounded Wave A pilot placeholder for {job['job_id']}",
            "# Method-specific execution is intentionally routed through this wrapper.",
            "echo 'adapter_not_implemented_for_this_method'",
            "exit 86",
            "",
        ]
    )


def write_command_package(job: dict[str, str], execution: dict[str, str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    command_path = output_dir / "command.sh"
    if job["method"] == "PepMLM":
        (output_dir / "pepmlm_v031_adapter.py").write_text(pepmlm_adapter_text(job, output_dir), encoding="utf-8")
        command_path.write_text(pepmlm_command_text(output_dir), encoding="utf-8")
    elif job["method"] == "AfCycDesign / ColabDesign cyclic peptide":
        command_path.write_text(colabdesign_command_text(job, output_dir, execution), encoding="utf-8")
    else:
        command_path.write_text(placeholder_command_text(job), encoding="utf-8")
    command_path.chmod(0o755)
    write_input_manifest(job, execution, output_dir)


def summarize_existing_job(job: dict[str, str], execution: dict[str, str], output_dir: Path, runtime_seconds: float, exit_code: str) -> dict[str, str] | None:
    method_path = output_dir / "method_output_manifest.csv"
    candidate_path = output_dir / "candidate_outputs.csv"
    if not method_path.is_file() or not candidate_path.is_file():
        return None
    method_rows = read_csv(method_path)
    candidate_rows = read_csv(candidate_path)
    parser_status = method_rows[0].get("parser_status", "failed") if method_rows else "failed"
    parsed_count = sum(1 for row in candidate_rows if row.get("parse_status") == "parsed")
    status = "parsed" if parser_status == "parsed" and parsed_count else "failed"
    return {
        "execution_id": execution.get("execution_id", f"exec_{job['job_id']}"),
        "job_id": job["job_id"],
        "method": job["method"],
        "target_id": job.get("target_id", ""),
        "execution_wave": job.get("execution_wave", ""),
        "runner": execution.get("runner", ""),
        "container_or_env": execution.get("container_or_env", ""),
        "output_root": str(output_dir),
        "status": status,
        "exit_code": exit_code,
        "runtime_seconds": f"{runtime_seconds:.3f}",
        "parser_status": parser_status,
        "candidate_count": str(len(candidate_rows)),
        "blocked_reason": "none" if status == "parsed" else "parser_status_not_parsed",
        "evidence_boundary": "Bounded Wave A pilot execution record only; not Benchmark result; not scoring evidence",
        "next_action": "Merge parser output into v0.31 compact tables; do not score or rank.",
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
    command = ["bash", str(output_dir / "command.sh")]
    exit_code = "not_run"
    try:
        completed = subprocess.run(
            command,
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
        status_reason=f"adapter_execution_failed_or_not_implemented_exit_{exit_code}",
        exit_code=exit_code,
        runtime_seconds=runtime_seconds,
    )


def run_wave_a(
    *,
    job_manifest: Path = DEFAULT_JOB_MANIFEST,
    execution_matrix: Path = DEFAULT_EXECUTION_MATRIX,
    run_root: Path = DEFAULT_RUN_ROOT,
    job_ids: set[str] | None = None,
    execute: bool = False,
    resume: bool = False,
    fail_fast: bool = False,
) -> list[dict[str, str]]:
    jobs = load_wave_a_jobs(job_manifest)
    matrix = load_execution_matrix(execution_matrix)
    selected = [job for job in jobs if job_ids is None or job["job_id"] in job_ids]
    results: list[dict[str, str]] = []
    for job in selected:
        execution = matrix[job["job_id"]]
        output_dir = output_dir_for(job, execution, run_root)
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
                    status_reason=f"runner_exception_{type(exc).__name__}: {exc}",
                    exit_code="runner_exception",
                )
            )
            if fail_fast:
                raise
    if results:
        write_csv(run_root / "pilot_execution_results_v0.31.csv", EXECUTION_RESULT_HEADERS, results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-manifest", type=Path, default=DEFAULT_JOB_MANIFEST)
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
