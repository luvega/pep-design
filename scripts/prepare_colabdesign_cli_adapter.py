#!/usr/bin/env python3
"""Prepare a standard ColabDesign job-row CLI adapter package.

The adapter layer is deliberately a dry-run packaging contract. It accepts one
standard job row, writes the command/config/manifests that a later execution
step can use, and avoids notebook execution or GPU design work.
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import time
from pathlib import Path
from typing import Any


METHOD = "AfCycDesign / ColabDesign cyclic peptide"
TASK_ID = "T2_structure_peptide_binder"
DEFAULT_SOURCE_DIR = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ColabDesign")
DEFAULT_PARAMS_DIR = Path("/data/protein-design/data/alphafold_db/params")
SOURCE_COMMIT = "e31a56f"
ENVIRONMENT_ID = "pd-benchmark-methods-gpu:0.21/bench-colabdesign"

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


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def split_field(value: str) -> list[str]:
    return [item.strip() for item in value.replace(",", ";").split(";") if item.strip()]


def bool_from_yes(value: str) -> bool:
    return value.strip().lower() in {"yes", "true", "1", "y"}


def select_job(job_manifest: Path, job_id: str) -> dict[str, str]:
    matches = [row for row in read_rows(job_manifest) if row.get("job_id") == job_id]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one job_id={job_id!r}, found {len(matches)}")
    row = matches[0]
    if row.get("method") != METHOD:
        raise ValueError(f"Job {job_id} method must be {METHOD!r}")
    if not row.get("target_pdb"):
        raise ValueError(f"Job {job_id} requires target_pdb")
    return row


def build_config(row: dict[str, str], source_dir: Path, dry_run: bool) -> dict[str, Any]:
    n_designs = int(row.get("n_designs_requested") or 1)
    random_seed = int(row["random_seed"]) if row.get("random_seed") else None
    return {
        "job_id": row["job_id"],
        "method": row["method"],
        "task_id": row.get("task_id") or TASK_ID,
        "target_id": row.get("target_id", ""),
        "input_mode": row.get("input_mode", ""),
        "target_pdb": row.get("target_pdb", ""),
        "target_chains": split_field(row.get("target_chains", "")),
        "binder_chain": row.get("binder_chain", "A") or "A",
        "pocket_definition": row.get("pocket_definition", ""),
        "peptide_type": row.get("peptide_type", "cyclic") or "cyclic",
        "chirality": row.get("chirality", "L") or "L",
        "cyclic": bool_from_yes(row.get("cyclic", "yes")),
        "n_designs_requested": n_designs,
        "random_seed": random_seed,
        "adapter_config": row.get("adapter_config", ""),
        "source_dir": str(source_dir),
        "dry_run": dry_run,
        "execution_boundary": "CLI adapter package only; no notebook execution and no GPU design run",
    }


def command_text(config_path: Path, output_dir: Path, source_dir: Path) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "# Planned ColabDesign adapter command. This package records the non-notebook CLI contract only.",
            "python scripts/prepare_colabdesign_cli_adapter.py "
            f"--adapter-config {shlex.quote(str(config_path))} "
            f"--output-dir {shlex.quote(str(output_dir))} "
            f"--source-dir {shlex.quote(str(source_dir))} "
            f"--params-dir {shlex.quote(str(DEFAULT_PARAMS_DIR))} "
            "--execute",
            "",
        ]
    )


def has_af_param_files(params_dir: Path) -> bool:
    if not params_dir.is_dir():
        return False
    suffixes = {".npz", ".pkl", ".params", ".json"}
    for path in params_dir.rglob("*"):
        if path.is_file() and (path.suffix.lower() in suffixes or "params_model" in path.name):
            return True
    return False


def gate_colabdesign_assets(config: dict[str, Any], params_dir: Path) -> dict[str, str]:
    source_dir = Path(str(config.get("source_dir") or DEFAULT_SOURCE_DIR))
    target_pdb = Path(str(config.get("target_pdb") or ""))
    if not has_af_param_files(params_dir):
        return {
            "status": "blocked_af_params_missing",
            "reason": f"AlphaFold/ColabDesign parameter files not found under {params_dir}",
        }
    if not source_dir.is_dir():
        return {
            "status": "blocked_source_missing",
            "reason": f"ColabDesign source directory not found: {source_dir}",
        }
    if not (source_dir / "colabdesign" / "af").is_dir():
        return {
            "status": "blocked_colabdesign_af_module_missing",
            "reason": f"ColabDesign af module not found under {source_dir}",
        }
    if not target_pdb.is_file():
        return {
            "status": "blocked_target_pdb_missing",
            "reason": f"Target PDB path not found: {target_pdb}",
        }
    return {
        "status": "ready_for_bounded_gpu_generation",
        "reason": "Source, target PDB and parameter files passed the bounded execution asset gate",
    }


def execute_command_text(config_path: Path, output_dir: Path, source_dir: Path, params_dir: Path) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "# Bounded ColabDesign execution gate. The Python adapter fails closed before generation if assets are missing.",
            "python scripts/prepare_colabdesign_cli_adapter.py "
            f"--adapter-config {shlex.quote(str(config_path))} "
            f"--output-dir {shlex.quote(str(output_dir))} "
            f"--source-dir {shlex.quote(str(source_dir))} "
            f"--params-dir {shlex.quote(str(params_dir))} "
            "--execute",
            "",
        ]
    )


def execute_adapter_package(
    *,
    adapter_config: Path,
    output_dir: Path,
    params_dir: Path = DEFAULT_PARAMS_DIR,
    timeout_sec: int = 1200,
) -> dict[str, str]:
    """Run the bounded execution gate and fail closed before design generation.

    This function intentionally does not synthesize a ColabDesign result. It
    verifies that the required source, target and AF parameter assets exist. If
    any gate fails, it writes standard manifests with failed parser status.
    """

    start = time.monotonic()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_json(adapter_config)
    if config.get("method") != METHOD:
        raise ValueError(f"Adapter config method must be {METHOD!r}")

    source_dir = Path(str(config.get("source_dir") or DEFAULT_SOURCE_DIR))
    command_path = output_dir / "command.sh"
    command_path.write_text(execute_command_text(adapter_config, output_dir, source_dir, params_dir), encoding="utf-8")
    command_path.chmod(0o755)

    gate = gate_colabdesign_assets(config, params_dir)
    elapsed = max(time.monotonic() - start, 0.0)
    job_id = str(config["job_id"])
    target_id = str(config.get("target_id", ""))
    peptide_type = str(config.get("peptide_type") or "cyclic")
    chirality = str(config.get("chirality") or "L")
    cyclic = "yes" if bool(config.get("cyclic", True)) else "no"

    if gate["status"] == "ready_for_bounded_gpu_generation":
        parser_status = "not_run"
        exit_code = "not_run"
        execution_stage = "dry_run"
        status_reason = (
            "ColabDesign bounded execution assets are present, but this KB adapter stops before GPU generation; "
            "not Benchmark result; no scoring or ranking evidence"
        )
        candidate_parse_status = "not_applicable"
        notes = "Asset gate passed only; not Benchmark result; bounded GPU generation still requires an execution run record"
    else:
        parser_status = "failed"
        exit_code = "not_run"
        execution_stage = "dry_run"
        status_reason = (
            f"{gate['status']}: {gate['reason']}; not Benchmark result; no GPU design run; "
            "no scoring or method-ranking evidence"
        )
        candidate_parse_status = "failed"
        notes = f"{gate['status']}; not Benchmark result; candidate not generated"

    method_row = {
        "run_record_id": f"{job_id}_colabdesign_bounded_execute_gate",
        "job_id": job_id,
        "method": METHOD,
        "task_id": str(config.get("task_id") or TASK_ID),
        "execution_stage": execution_stage,
        "source_commit": SOURCE_COMMIT,
        "model_revision": "af_params_not_verified" if gate["status"] != "ready_for_bounded_gpu_generation" else "af_params_asset_gate_present",
        "environment_id": ENVIRONMENT_ID,
        "command": str(command_path),
        "raw_output_root": str(output_dir),
        "stdout_log": "not_run",
        "stderr_log": "not_run",
        "runtime_seconds": f"{elapsed:.3f}",
        "exit_code": exit_code,
        "parser_status": parser_status,
        "status_reason": status_reason,
        "created_at": "2026-07-09",
    }
    candidate_row = {
        "design_id": f"{job_id}_colabdesign_not_generated",
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
        "parse_status": candidate_parse_status,
        "status_reason": gate["status"],
        "notes": notes,
    }
    write_csv(output_dir / "method_output_manifest.csv", METHOD_OUTPUT_HEADERS, [method_row])
    write_csv(output_dir / "candidate_outputs.csv", CANDIDATE_HEADERS, [candidate_row])
    (output_dir / "execution_gate_result.json").write_text(
        json.dumps(
            {
                "status": gate["status"],
                "reason": gate["reason"],
                "job_id": job_id,
                "adapter_config": str(adapter_config),
                "params_dir": str(params_dir),
                "timeout_sec": timeout_sec,
                "evidence_boundary": "ColabDesign bounded execute gate only; not Benchmark result",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "status": gate["status"],
        "job_id": job_id,
        "output_dir": str(output_dir),
        "method_manifest": str(output_dir / "method_output_manifest.csv"),
        "candidate_outputs": str(output_dir / "candidate_outputs.csv"),
    }


def prepare_adapter_package(
    *,
    job_manifest: Path,
    job_id: str,
    output_dir: Path,
    source_dir: Path,
    dry_run: bool = True,
) -> dict[str, str]:
    row = select_job(job_manifest, job_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = build_config(row, source_dir, dry_run=dry_run)
    config_path = output_dir / "colabdesign_adapter_config.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    command_path = output_dir / "command.sh"
    command_path.write_text(command_text(config_path, output_dir, source_dir), encoding="utf-8")
    command_path.chmod(0o755)

    method_row = {
        "run_record_id": f"{job_id}_colabdesign_cli_adapter",
        "job_id": job_id,
        "method": METHOD,
        "task_id": row.get("task_id") or TASK_ID,
        "execution_stage": "dry_run_plan",
        "source_commit": SOURCE_COMMIT,
        "model_revision": "not_downloaded_or_not_run",
        "environment_id": "notebook_cli_tooling_ready_adapter_dry_run",
        "command": str(command_path),
        "raw_output_root": str(output_dir),
        "stdout_log": "not_run",
        "stderr_log": "not_run",
        "runtime_seconds": "not_run",
        "exit_code": "not_run",
        "parser_status": "not_run",
        "status_reason": "ColabDesign CLI adapter package only; not Benchmark result; no notebook execution; no GPU design run",
        "created_at": "2026-07-09",
    }
    candidate_row = {
        "design_id": f"{job_id}_colabdesign_not_generated",
        "job_id": job_id,
        "method": METHOD,
        "target_id": row.get("target_id", ""),
        "binder_id": "not_generated",
        "source_output_id": "not_generated",
        "generation_rank": "",
        "sequence": "",
        "structure_path": "",
        "peptide_type": row.get("peptide_type", "cyclic") or "cyclic",
        "chirality": row.get("chirality", "L") or "L",
        "cyclic": row.get("cyclic", "yes") or "yes",
        "parse_status": "not_applicable",
        "status_reason": "cli_adapter_dry_run_no_generation",
        "notes": "Adapter package only; not Benchmark result",
    }
    write_csv(output_dir / "method_output_manifest.csv", METHOD_OUTPUT_HEADERS, [method_row])
    write_csv(output_dir / "candidate_outputs.csv", CANDIDATE_HEADERS, [candidate_row])
    return {
        "status": "cli_adapter_defined",
        "job_id": job_id,
        "output_dir": str(output_dir),
        "config_path": str(config_path),
        "command_path": str(command_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-manifest", type=Path)
    parser.add_argument("--job-id")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--params-dir", type=Path, default=DEFAULT_PARAMS_DIR)
    parser.add_argument("--timeout-sec", type=int, default=1200)
    parser.add_argument("--adapter-config", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.execute:
        if not args.adapter_config:
            raise SystemExit("--adapter-config is required with --execute")
        result = execute_adapter_package(
            adapter_config=args.adapter_config,
            output_dir=args.output_dir,
            params_dir=args.params_dir,
            timeout_sec=args.timeout_sec,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if not args.job_manifest or not args.job_id:
        raise SystemExit("--job-manifest and --job-id are required unless --execute is used")

    result = prepare_adapter_package(
        job_manifest=args.job_manifest,
        job_id=args.job_id,
        output_dir=args.output_dir,
        source_dir=args.source_dir,
        dry_run=True,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
