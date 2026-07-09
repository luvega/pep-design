#!/usr/bin/env python
"""Collect external v0.20 method-unblock smoke summaries into KB CSV artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_ROOT = Path("/data/protein-design/data/outputs/benchmark_v0.20/method_unblock_smokes")

METHODS = [
    {
        "method_id": "pepmlm",
        "method": "PepMLM",
        "task_scope": "v019_smoke_carry_forward_non_pyrosetta_method",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/pepmlm",
        "model_or_weight_event": "v0.19 Hugging Face cache evidence carried forward; no v0.20 download",
        "next_action": "Add parser rules for noncanonical token caveats before comparative runs",
    },
    {
        "method_id": "saltnpeppr",
        "method": "SaLT&PepPr",
        "task_scope": "license_access_recheck",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/saltnpeppr",
        "model_or_weight_event": "not downloaded; UbiquiTx/Hugging Face access remains blocked",
        "next_action": "Resolve UbiquiTx license and gated model access",
    },
    {
        "method_id": "diffpepbuilder",
        "method": "DiffPepBuilder",
        "task_scope": "independent_pyrosetta_image_unblock",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/DiffPepBuilder",
        "model_or_weight_event": "DiffPepBuilder Zenodo checkpoint and ESM2 cache remain external; independent PyRosetta image built from quarterly mirror",
        "next_action": "Convert successful example smoke into adapter/parser and multi-case fixture coverage",
    },
    {
        "method_id": "pepglad",
        "method": "PepGLAD",
        "task_scope": "release_weight_resolution",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepGLAD",
        "model_or_weight_event": "no checkpoint downloaded; direct guessed release asset URLs returned 404 and GitHub API was rate-limited",
        "next_action": "Resolve release asset names/checksums through a non-rate-limited route",
    },
    {
        "method_id": "dflow",
        "method": "D-Flow / PeptideDesign",
        "task_scope": "input_contract_recheck",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PeptideDesign",
        "model_or_weight_event": "source-local dflow.zip observed; test_set/PepMerge cache absent",
        "next_action": "Recover test_set/PepMerge pep_cache route before inference smoke",
    },
    {
        "method_id": "pepmirror",
        "method": "PepMirror",
        "task_scope": "independent_pyrosetta_and_checkpoint_unblock",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepMirror",
        "model_or_weight_event": "not downloaded; independent PyRosetta image route and checkpoint manifest require verification",
        "next_action": "Resolve PepMirror checkpoint manifest before generation smoke; PyRosetta image route is available",
    },
    {
        "method_id": "colabdesign",
        "method": "AfCycDesign / ColabDesign cyclic peptide",
        "task_scope": "cli_adapter_decision",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ColabDesign",
        "model_or_weight_event": "no new model or weight download",
        "next_action": "Choose a non-notebook AfCycDesign CLI adapter or keep deferred",
    },
    {
        "method_id": "osprey3",
        "method": "DexDesign / OSPREY3",
        "task_scope": "v019_cpu_probe_carry_forward",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/OSPREY3",
        "model_or_weight_event": "no model weights",
        "next_action": "Select a minimal OSPREY3 design example before comparative use",
    },
    {
        "method_id": "rfdiffusion_proteinmpnn",
        "method": "RFdiffusion + ProteinMPNN",
        "task_scope": "v019_component_smoke_carry_forward",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion",
        "model_or_weight_event": "existing external RFdiffusion and ProteinMPNN checkpoint/image routes carried forward",
        "next_action": "Write a single RFdiffusion-to-ProteinMPNN handoff adapter before comparison",
    },
    {
        "method_id": "bindcraft",
        "method": "BindCraft",
        "task_scope": "bounded_smoke_only_configuration",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/BindCraft",
        "model_or_weight_event": "existing BindCraft image route reused only for BindCraft; independent PyRosetta image not reused",
        "next_action": "Tighten hard stop around trajectory count or add an explicit one-trajectory wrapper",
    },
]

RESULT_HEADERS = [
    "method",
    "smoke_test_id",
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

MANIFEST_HEADERS = [
    "method",
    "workbench_root",
    "source_dir",
    "image_tag",
    "conda_env",
    "gpu_policy",
    "smoke_entrypoint",
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

STATUS_MAP = {
    "carried_forward_v019_ready": "carried_forward_v019_ready",
    "carried_forward_v019_cpu_ready": "carried_forward_v019_cpu_ready",
    "blocked_license": "blocked_license",
    "blocked_input_contract": "blocked_input_contract",
    "blocked_pyrosetta_image_missing": "blocked_pyrosetta_image_missing",
    "blocked_weights": "blocked_weights",
    "deferred_cli_adapter": "deferred_cli_adapter",
    "unblock_smoke_passed_gpu": "unblock_smoke_passed_gpu",
    "failed_command": "failed_command",
    "failed_timeout": "failed_timeout",
    "failed_no_gpu_evidence": "failed_no_gpu_evidence",
    "missing_runtime": "missing_runtime",
}


def read_runtime(method_id: str) -> dict[str, object]:
    path = EXTERNAL_ROOT / method_id / "runtime.json"
    if not path.exists():
        return {
            "source_commit": "missing_runtime",
            "image": "not_observed",
            "conda_env": "not_observed",
            "gpu_required": "unknown",
            "exit_code": "NA",
            "runtime_sec": 0,
            "gpu_evidence": "not_observed",
            "output_status": "not_run",
            "parser_status": "missing_runtime",
            "smoke_status": "missing_runtime",
            "blocker": f"{path} missing",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_status(runtime: dict[str, object]) -> str:
    if str(runtime.get("exit_code")) == "124":
        return "failed_timeout"
    raw = str(runtime.get("smoke_status", "missing_runtime"))
    return STATUS_MAP.get(raw, raw or "missing_runtime")


def next_gate(status: str) -> str:
    if status.startswith("carried_forward") or status == "unblock_smoke_passed_gpu":
        return "adapter_parser_and_multi_case_fixture_needed"
    if status == "blocked_pyrosetta_image_missing":
        return "image_build_ready"
    if status == "blocked_weights":
        return "weights_manifested"
    if status == "blocked_input_contract":
        return "input_contract_ready"
    if status == "blocked_license":
        return "license_checked"
    if status == "deferred_cli_adapter":
        return "cli_adapter_decision_needed"
    return "blocker_triage"


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    manifest_rows = []
    result_rows = []
    boundary = (
        "External v0.20 unblock/readiness evidence only; not target-set evidence, "
        "not scoring evidence, not method-ranking evidence, and not complete Benchmark evidence"
    )

    for meta in METHODS:
        method_id = meta["method_id"]
        method_dir = EXTERNAL_ROOT / method_id
        runtime = read_runtime(method_id)
        status = normalize_status(runtime)
        command_path = method_dir / "command.sh"
        stdout_log = method_dir / "stdout.log"
        stderr_log = method_dir / "stderr.log"
        runtime_json = method_dir / "runtime.json"
        outputs_manifest = method_dir / "outputs_manifest.csv"

        manifest_rows.append(
            {
                "method": meta["method"],
                "workbench_root": "/data/protein-design",
                "source_dir": meta["source_dir"],
                "image_tag": runtime.get("image", "not_observed"),
                "conda_env": runtime.get("conda_env", "not_observed"),
                "gpu_policy": "gpu_required" if runtime.get("gpu_required") == "yes" else "cpu_or_not_applicable",
                "smoke_entrypoint": str(command_path) if command_path.exists() else "not_run",
                "external_output_dir": str(method_dir),
                "command_log": str(command_path) if command_path.exists() else "not_run",
                "stdout_log": str(stdout_log) if stdout_log.exists() else "not_run",
                "stderr_log": str(stderr_log) if stderr_log.exists() else "not_run",
                "runtime_json": str(runtime_json) if runtime_json.exists() else "missing_runtime",
                "outputs_manifest": str(outputs_manifest) if outputs_manifest.exists() else "missing_outputs_manifest",
                "manifest_status": status,
                "evidence_boundary": boundary,
                "next_action": meta["next_action"],
            }
        )
        result_rows.append(
            {
                "method": meta["method"],
                "smoke_test_id": f"v020_{method_id}",
                "task_scope": meta["task_scope"],
                "status": status,
                "exit_code": runtime.get("exit_code", "NA"),
                "runtime_sec": runtime.get("runtime_sec", 0),
                "image_tag": runtime.get("image", "not_observed"),
                "conda_env": runtime.get("conda_env", "not_observed"),
                "source_commit": runtime.get("source_commit", "missing_runtime"),
                "gpu_required": runtime.get("gpu_required", "unknown"),
                "gpu_evidence": runtime.get("gpu_evidence", "not_observed"),
                "output_status": runtime.get("output_status", "not_run"),
                "parser_status": runtime.get("parser_status", "not_run"),
                "external_method_dir": str(method_dir),
                "command_path": str(command_path) if command_path.exists() else "not_run",
                "stdout_log": str(stdout_log) if stdout_log.exists() else "not_run",
                "stderr_log": str(stderr_log) if stderr_log.exists() else "not_run",
                "runtime_json": str(runtime_json) if runtime_json.exists() else "missing_runtime",
                "outputs_manifest": str(outputs_manifest) if outputs_manifest.exists() else "missing_outputs_manifest",
                "model_or_weight_event": meta["model_or_weight_event"],
                "blocker": runtime.get("blocker", "none_observed_for_v020_unblock_scope"),
                "evidence_boundary": boundary,
                "next_gate": next_gate(status),
            }
        )

    write_csv(ROOT / "benchmark/deployment/method_unblock_manifest_v0.20.csv", MANIFEST_HEADERS, manifest_rows)
    write_csv(ROOT / "benchmark/deployment/method_unblock_smoke_results_v0.20.csv", RESULT_HEADERS, result_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
