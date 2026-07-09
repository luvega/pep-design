#!/usr/bin/env python3
"""Run one bounded ColabDesign GPU generation attempt and parse its output."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any


METHOD = "AfCycDesign / ColabDesign cyclic peptide"
TASK_ID = "T2_structure_peptide_binder"
JOB_ID = "v029_colabdesign_7zkr_bounded_seed42"
TARGET_ID = "gabarap_7zkr_fixture_v029"
SOURCE_COMMIT = "e31a56f"
ENVIRONMENT_ID = "pd-benchmark-methods-gpu:0.21/bench-colabdesign"
DEFAULT_IMAGE = "pd-benchmark-methods-gpu:0.21"
DEFAULT_SOURCE_DIR = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ColabDesign")
DEFAULT_PARAMS_DIR = Path("/data/protein-design/data/alphafold_db/params")
DEFAULT_TARGET_PDB = Path(
    "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion/examples/input_pdbs/7zkr_GABARAP.pdb"
)

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

AA3_TO_1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def shell_join(command: list[str]) -> str:
    return " ".join(_shell_quote(part) for part in command)


def _shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def runtime_script_text(target_pdb_name: str, random_seed: int = 42, binder_len: int = 14) -> str:
    return f'''#!/usr/bin/env python3
import json
import os
import random
import sys
import traceback
from pathlib import Path

os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
random.seed({random_seed})
sys.path.insert(0, "/opt/ColabDesign")

result = {{
    "status": "started",
    "target_pdb": "/data/inputs/{target_pdb_name}",
    "output_pdb": "/data/outputs/colabdesign_binder.pdb",
    "evidence_boundary": "Bounded ultra-smoke only; not Benchmark result",
}}

try:
    try:
        from colabdesign import mk_afdesign_model
    except ImportError:
        from colabdesign.af import mk_afdesign_model

    model = mk_afdesign_model(
        protocol="binder",
        use_multimer=False,
        data_dir="/data/alphafold_params",
        num_recycles=0,
        recycle_mode="sample",
    )
    model.prep_inputs(
        pdb_filename="/data/inputs/{target_pdb_name}",
        chain="A",
        binder_len={binder_len},
        binder_chain=None,
        hotspot=None,
        ignore_missing=False,
    )
    try:
        model.design_logits(1, num_models=1, num_recycles=0, dropout=False, save_best=True)
    except TypeError:
        model.design_logits(1)
    model.save_pdb("/data/outputs/colabdesign_binder.pdb")
    result["status"] = "bounded_gpu_generation_completed"
except Exception as exc:
    result["status"] = "bounded_gpu_generation_failed"
    result["error"] = repr(exc)
    result["traceback"] = traceback.format_exc()
    Path("/data/outputs/colabdesign_runtime_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\\n",
        encoding="utf-8",
    )
    raise

Path("/data/outputs/colabdesign_runtime_result.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\\n",
    encoding="utf-8",
)
'''


def build_docker_command(
    *,
    output_dir: Path,
    source_dir: Path,
    params_dir: Path,
    target_pdb: Path,
    image: str = DEFAULT_IMAGE,
    timeout_sec: int = 900,
) -> list[str]:
    _ = timeout_sec
    output_dir = output_dir.resolve()
    source_dir = source_dir.resolve()
    params_dir = params_dir.resolve()
    target_pdb = target_pdb.resolve()
    return [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--shm-size",
        "16g",
        "-v",
        f"{source_dir}:/opt/ColabDesign:ro",
        "-v",
        f"{params_dir}:/data/alphafold_params:ro",
        "-v",
        f"{target_pdb.parent}:/data/inputs:ro",
        "-v",
        f"{output_dir}:/data/outputs",
        "--workdir",
        "/data/outputs",
        image,
        "bash",
        "-lc",
        (
            "source /opt/conda/etc/profile.d/conda.sh && "
            "conda activate bench-colabdesign && "
            "export PYTHONPATH=/opt/ColabDesign:$PYTHONPATH && "
            "python /data/outputs/colabdesign_ultra_smoke.py"
        ),
    ]


def parse_pdb_sequence(pdb_path: Path, preferred_chain: str = "B") -> dict[str, str]:
    chains: dict[str, list[tuple[str, str]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 26:
            continue
        chain_id = line[21].strip() or "_"
        resseq = line[22:27].strip()
        resname = line[17:20].strip().upper()
        key = (chain_id, resseq, resname)
        if key in seen:
            continue
        seen.add(key)
        chains.setdefault(chain_id, []).append((resseq, AA3_TO_1.get(resname, "X")))
    if not chains:
        return {"chain_id": "", "sequence": ""}
    chain_id = preferred_chain if preferred_chain in chains else next(reversed(chains))
    return {"chain_id": chain_id, "sequence": "".join(aa for _, aa in chains[chain_id])}


def write_result_tables(
    *,
    output_dir: Path,
    command: list[str],
    command_path: Path,
    runtime_seconds: float,
    exit_code: str,
    parser_status: str,
    status_reason: str,
    candidate_row: dict[str, Any],
    job_id: str = JOB_ID,
    task_id: str = TASK_ID,
) -> None:
    method_row = {
        "run_record_id": f"{job_id}_colabdesign_bounded_generation",
        "job_id": job_id,
        "method": METHOD,
        "task_id": task_id,
        "execution_stage": "bounded_gpu_generation",
        "source_commit": SOURCE_COMMIT,
        "model_revision": "af_params_asset_gate_present",
        "environment_id": ENVIRONMENT_ID,
        "command": str(command_path),
        "raw_output_root": str(output_dir),
        "stdout_log": str(output_dir / "stdout.log"),
        "stderr_log": str(output_dir / "stderr.log"),
        "runtime_seconds": f"{runtime_seconds:.3f}",
        "exit_code": exit_code,
        "parser_status": parser_status,
        "status_reason": status_reason,
        "created_at": "2026-07-09",
    }
    write_csv(output_dir / "method_output_manifest.csv", METHOD_OUTPUT_HEADERS, [method_row])
    write_csv(output_dir / "candidate_outputs.csv", CANDIDATE_HEADERS, [candidate_row])
    (output_dir / "run_result.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "status": parser_status,
                "exit_code": exit_code,
                "command": command,
                "runtime_seconds": runtime_seconds,
                "status_reason": status_reason,
                "evidence_boundary": "Bounded ColabDesign generation attempt only; not Benchmark result",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def run_bounded_generation(
    *,
    output_dir: Path,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    params_dir: Path = DEFAULT_PARAMS_DIR,
    target_pdb: Path = DEFAULT_TARGET_PDB,
    image: str = DEFAULT_IMAGE,
    timeout_sec: int = 900,
    job_id: str = JOB_ID,
    target_id: str = TARGET_ID,
    task_id: str = TASK_ID,
    random_seed: int = 42,
    peptide_type: str = "linear",
    chirality: str = "L",
    cyclic: str = "no",
    binder_len: int = 14,
    inner_command_filename: str = "command.sh",
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    source_dir = source_dir.resolve()
    params_dir = params_dir.resolve()
    target_pdb = target_pdb.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "colabdesign_ultra_smoke.py").write_text(
        runtime_script_text(target_pdb.name, random_seed=random_seed, binder_len=binder_len),
        encoding="utf-8",
    )
    command = build_docker_command(
        output_dir=output_dir,
        source_dir=source_dir,
        params_dir=params_dir,
        target_pdb=target_pdb,
        image=image,
        timeout_sec=timeout_sec,
    )
    inner_command_path = output_dir / inner_command_filename
    inner_command_path.write_text(shell_join(command) + "\n", encoding="utf-8")
    inner_command_path.chmod(0o755)

    start = time.monotonic()
    stdout = ""
    stderr = ""
    exit_code = "not_run"
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = str(completed.returncode)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTimed out after {timeout_sec} seconds\n"
        exit_code = "124"
    except FileNotFoundError as exc:
        stderr = repr(exc)
        exit_code = "docker_missing"
    runtime_seconds = max(time.monotonic() - start, 0.0)

    (output_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    (output_dir / "stderr.log").write_text(stderr, encoding="utf-8")

    output_pdb = output_dir / "colabdesign_binder.pdb"
    parsed = parse_pdb_sequence(output_pdb, preferred_chain="B") if output_pdb.is_file() else {"chain_id": "", "sequence": ""}

    if exit_code == "0" and parsed["sequence"]:
        parser_status = "parsed"
        status = "bounded_gpu_generation_passed"
        status_reason = "bounded_colabdesign_gpu_generation_parsed; not Benchmark result; not scoring evidence"
        candidate_row = {
            "design_id": f"{job_id}_candidate_1",
            "job_id": job_id,
            "method": METHOD,
            "target_id": target_id,
            "binder_id": parsed["chain_id"],
            "source_output_id": output_pdb.name,
            "generation_rank": "1",
            "sequence": parsed["sequence"],
            "structure_path": str(output_pdb),
            "peptide_type": peptide_type,
            "chirality": chirality,
            "cyclic": cyclic,
            "parse_status": "parsed",
            "status_reason": "bounded_colabdesign_output_parsed",
            "notes": "Single bounded GPU generation attempt; not Benchmark result; not controlled multi-case; not scoring evidence",
        }
    else:
        parser_status = "failed"
        status = "bounded_gpu_generation_failed"
        status_reason = (
            f"bounded_colabdesign_gpu_generation_failed_exit_{exit_code}; "
            "not Benchmark result; not scoring evidence"
        )
        candidate_row = {
            "design_id": f"{job_id}_not_generated",
            "job_id": job_id,
            "method": METHOD,
            "target_id": target_id,
            "binder_id": "not_generated",
            "source_output_id": "not_generated",
            "generation_rank": "",
            "sequence": "",
            "structure_path": "",
            "peptide_type": peptide_type,
            "chirality": chirality,
            "cyclic": cyclic,
            "parse_status": "failed",
            "status_reason": f"exit_{exit_code}_or_no_parseable_pdb",
            "notes": "Bounded GPU generation attempt failed or produced no parseable PDB; not Benchmark result; not scoring evidence",
        }

    write_result_tables(
        output_dir=output_dir,
        command=command,
        command_path=inner_command_path,
        runtime_seconds=runtime_seconds,
        exit_code=exit_code,
        parser_status=parser_status,
        status_reason=status_reason,
        candidate_row=candidate_row,
        job_id=job_id,
        task_id=task_id,
    )
    return {
        "status": status,
        "exit_code": exit_code,
        "parser_status": parser_status,
        "candidate_outputs": str(output_dir / "candidate_outputs.csv"),
        "method_output_manifest": str(output_dir / "method_output_manifest.csv"),
        "output_dir": str(output_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--params-dir", type=Path, default=DEFAULT_PARAMS_DIR)
    parser.add_argument("--target-pdb", type=Path, default=DEFAULT_TARGET_PDB)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--job-id", default=JOB_ID)
    parser.add_argument("--target-id", default=TARGET_ID)
    parser.add_argument("--task-id", default=TASK_ID)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--peptide-type", default="linear")
    parser.add_argument("--chirality", default="L")
    parser.add_argument("--cyclic", default="no")
    parser.add_argument("--binder-len", type=int, default=14)
    parser.add_argument("--inner-command-filename", default="command.sh")
    args = parser.parse_args()

    result = run_bounded_generation(
        output_dir=args.output_dir,
        source_dir=args.source_dir,
        params_dir=args.params_dir,
        target_pdb=args.target_pdb,
        image=args.image,
        timeout_sec=args.timeout_sec,
        job_id=args.job_id,
        target_id=args.target_id,
        task_id=args.task_id,
        random_seed=args.random_seed,
        peptide_type=args.peptide_type,
        chirality=args.chirality,
        cyclic=args.cyclic,
        binder_len=args.binder_len,
        inner_command_filename=args.inner_command_filename,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
