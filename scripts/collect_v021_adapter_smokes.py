#!/usr/bin/env python3
"""Collect external v0.21 adapter-smoke summaries into KB CSV artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTERNAL_ROOT = Path("/data/protein-design/data/outputs/benchmark_v0.21/adapter_smokes")
DEPLOYMENT_ROOT = ROOT / "benchmark" / "deployment"

METHOD_ORDER = [
    "PepMLM",
    "SaLT&PepPr",
    "DiffPepBuilder",
    "PepGLAD",
    "D-Flow / PeptideDesign",
    "PepMirror",
    "AfCycDesign / ColabDesign cyclic peptide",
    "DexDesign / OSPREY3",
    "RFdiffusion + ProteinMPNN",
    "BindCraft",
]

MANIFEST_HEADERS = [
    "method",
    "workbench_root",
    "source_dir",
    "image_tag",
    "conda_env",
    "gpu_policy",
    "adapter_entrypoint",
    "external_output_dir",
    "command_log",
    "stdout_log",
    "stderr_log",
    "runtime_json",
    "outputs_manifest",
    "manifest_status",
    "evidence_boundary",
    "next_action",
]

RESULT_HEADERS = [
    "method",
    "adapter_smoke_id",
    "task_scope",
    "status",
    "exit_code",
    "runtime_sec",
    "image_tag",
    "conda_env",
    "source_commit",
    "gpu_required",
    "gpu_evidence",
    "output_status",
    "parser_status",
    "external_method_dir",
    "command_path",
    "stdout_log",
    "stderr_log",
    "runtime_json",
    "outputs_manifest",
    "model_or_weight_event",
    "blocker",
    "evidence_boundary",
    "next_gate",
]

ASSET_HEADERS = [
    "method",
    "asset_id",
    "source_url",
    "local_path",
    "expected_sha256",
    "observed_sha256",
    "size_bytes",
    "status",
    "notes",
]

SOURCE_DIRS = {
    "PepMLM": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/pepmlm",
    "SaLT&PepPr": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/saltnpeppr",
    "DiffPepBuilder": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/DiffPepBuilder",
    "PepGLAD": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepGLAD",
    "D-Flow / PeptideDesign": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PeptideDesign",
    "PepMirror": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepMirror",
    "AfCycDesign / ColabDesign cyclic peptide": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ColabDesign",
    "DexDesign / OSPREY3": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/OSPREY3",
    "RFdiffusion + ProteinMPNN": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion",
    "BindCraft": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/BindCraft",
}

TASK_SCOPE = {
    "PepMLM": "sequence_adapter_parser_fixture",
    "SaLT&PepPr": "license_gate_carry_forward",
    "DiffPepBuilder": "structure_conditioned_adapter_parser_fixture",
    "PepGLAD": "public_weight_unblock_codesign_smoke",
    "D-Flow / PeptideDesign": "public_weight_and_input_contract_unblock",
    "PepMirror": "public_checkpoint_unblock_generation_smoke",
    "AfCycDesign / ColabDesign cyclic peptide": "cli_adapter_gate_carry_forward",
    "DexDesign / OSPREY3": "cpu_route_carry_forward",
    "RFdiffusion + ProteinMPNN": "rf_to_mpnn_handoff_adapter",
    "BindCraft": "bounded_hard_stop_smoke_control",
}

NEXT_ACTION = {
    "adapter_smoke_passed_gpu": "Promote parser fixture to controlled multi-case fixture planning",
    "bounded_execution_control_passed": "Review BindCraft hard-stop output before another bounded generation attempt",
    "carried_forward_v020_ready": "Keep carry-forward evidence until a v0.21 adapter run is selected",
    "blocked_license": "Resolve license/gated model access before execution",
    "blocked_weights": "Resolve public checkpoint manifest/download before smoke",
    "blocked_input_contract": "Resolve required input cache/data contract before smoke",
    "blocked_cli_adapter": "Define non-notebook CLI adapter before smoke",
    "failed_timeout": "Triage timeout and strengthen execution boundary",
    "failed_command": "Triage command failure from external logs",
    "failed_no_gpu_evidence": "Rerun with GPU evidence or mark as CPU-only",
}


def boundary() -> str:
    return (
        "External v0.21 adapter/readiness evidence only; not target-set evidence, "
        "not scoring evidence, not method-ranking evidence, and not complete Benchmark evidence"
    )


def method_sort_key(row: dict[str, object]) -> int:
    try:
        return METHOD_ORDER.index(str(row.get("method", "")))
    except ValueError:
        return len(METHOD_ORDER)


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def read_runtime(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_assets(external_root: Path) -> list[dict[str, object]]:
    path = external_root / "asset_manifest_v0.21.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_status(runtime: dict[str, object]) -> str:
    status = str(runtime.get("smoke_status", "missing_runtime"))
    if str(runtime.get("exit_code")) == "124":
        return "failed_timeout"
    return status


def build_rows(external_root: Path = DEFAULT_EXTERNAL_ROOT) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    manifest_rows: list[dict[str, object]] = []
    result_rows: list[dict[str, object]] = []

    for runtime_path in sorted(external_root.glob("*/runtime.json")):
        method_dir = runtime_path.parent
        runtime = read_runtime(runtime_path)
        method = str(runtime.get("method", method_dir.name))
        status = normalize_status(runtime)
        command_path = method_dir / "command.sh"
        stdout_log = method_dir / "stdout.log"
        stderr_log = method_dir / "stderr.log"
        outputs_manifest = method_dir / "outputs_manifest.csv"
        next_gate = str(runtime.get("next_gate", "blocker_triage"))
        image = str(runtime.get("image", "not_observed"))
        conda_env = str(runtime.get("conda_env", "not_observed"))

        manifest_rows.append(
            {
                "method": method,
                "workbench_root": "/data/protein-design",
                "source_dir": SOURCE_DIRS.get(method, "unknown"),
                "image_tag": image,
                "conda_env": conda_env,
                "gpu_policy": "gpu_required" if runtime.get("gpu_required") == "yes" else "cpu_or_not_applicable",
                "adapter_entrypoint": str(command_path) if command_path.exists() else "not_run",
                "external_output_dir": str(method_dir),
                "command_log": str(command_path) if command_path.exists() else "not_run",
                "stdout_log": str(stdout_log) if stdout_log.exists() else "not_run",
                "stderr_log": str(stderr_log) if stderr_log.exists() else "not_run",
                "runtime_json": str(runtime_path),
                "outputs_manifest": str(outputs_manifest),
                "manifest_status": status,
                "evidence_boundary": boundary(),
                "next_action": NEXT_ACTION.get(status, "Triage v0.21 adapter status before comparative use"),
            }
        )
        result_rows.append(
            {
                "method": method,
                "adapter_smoke_id": str(runtime.get("job_id", f"v021_{method_dir.name}")),
                "task_scope": TASK_SCOPE.get(method, "v021_adapter_smoke"),
                "status": status,
                "exit_code": runtime.get("exit_code", "NA"),
                "runtime_sec": runtime.get("runtime_sec", 0),
                "image_tag": image,
                "conda_env": conda_env,
                "source_commit": runtime.get("source_commit", "unknown"),
                "gpu_required": runtime.get("gpu_required", "unknown"),
                "gpu_evidence": runtime.get("gpu_evidence", "not_observed"),
                "output_status": runtime.get("output_status", "not_run"),
                "parser_status": runtime.get("parser_status", "not_run"),
                "external_method_dir": str(method_dir),
                "command_path": str(command_path) if command_path.exists() else "not_run",
                "stdout_log": str(stdout_log) if stdout_log.exists() else "not_run",
                "stderr_log": str(stderr_log) if stderr_log.exists() else "not_run",
                "runtime_json": str(runtime_path),
                "outputs_manifest": str(outputs_manifest),
                "model_or_weight_event": runtime.get("model_or_weight_event", "not_recorded"),
                "blocker": runtime.get("blocker", ""),
                "evidence_boundary": boundary(),
                "next_gate": next_gate,
            }
        )

    manifest_rows.sort(key=method_sort_key)
    result_rows.sort(key=method_sort_key)
    return manifest_rows, result_rows, read_assets(external_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument("--deployment-root", type=Path, default=DEPLOYMENT_ROOT)
    args = parser.parse_args()

    manifest_rows, result_rows, asset_rows = build_rows(args.external_root)
    write_csv(args.deployment_root / "adapter_smoke_manifest_v0.21.csv", MANIFEST_HEADERS, manifest_rows)
    write_csv(args.deployment_root / "adapter_smoke_results_v0.21.csv", RESULT_HEADERS, result_rows)
    write_csv(args.deployment_root / "blocker_asset_manifest_v0.21.csv", ASSET_HEADERS, asset_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
