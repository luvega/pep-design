#!/usr/bin/env python
"""Collect external v0.19 method smoke-test summaries into KB CSV artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_ROOT = Path("/data/protein-design/data/outputs/benchmark_v0.19/method_smokes")

METHODS = [
    {
        "method_id": "pepmlm",
        "method": "PepMLM",
        "task_scope": "sequence_binder_readme_like_smoke",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/pepmlm",
        "source_route": "external Git checkout; Hugging Face model route",
        "doc_route_checked": "README/model card route checked; local smoke wrapper uses TianlaiChen/PepMLM-650M",
        "example_route_checked": "minimal masked-peptide generation wrapper in v0.19 runner",
        "license_access_route": "metadata-level route; no KB-side model redistribution",
        "model_weight_route": "Hugging Face cache external to KB under /data/protein-design",
        "model_or_weight_event": "TianlaiChen/PepMLM-650M loaded from external Hugging Face cache; no KB copy",
        "next_action": "Add batch adapter and parser rule for noncanonical token caveats before comparative runs",
    },
    {
        "method_id": "saltnpeppr",
        "method": "SaLT&PepPr",
        "task_scope": "sequence_model_route_blocked",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/saltnpeppr",
        "source_route": "external Git checkout",
        "doc_route_checked": "README indicates UbiquiTx license and gated Hugging Face route",
        "example_route_checked": "not executed because access/license gate is unresolved",
        "license_access_route": "UbiquiTx license required before model use",
        "model_weight_route": "gated Hugging Face route; not downloaded in v0.19",
        "model_or_weight_event": "not downloaded; license/access blocked",
        "next_action": "Resolve license and gated model access before installation or smoke execution",
    },
    {
        "method_id": "diffpepbuilder",
        "method": "DiffPepBuilder",
        "task_scope": "structure_conditioned_peptide_design_example_smoke",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/DiffPepBuilder",
        "source_route": "external Git checkout; Zenodo checkpoint route",
        "doc_route_checked": "README and Zenodo public checkpoint route checked",
        "example_route_checked": "author receptor processing and minimal inference route",
        "license_access_route": "public checkpoint route recorded; no KB-side redistribution",
        "model_weight_route": "external /data/protein-design/data/benchmark_models/diffpepbuilder/diffpepbuilder_v1.pth",
        "model_or_weight_event": "Zenodo checkpoint downloaded externally; no KB copy",
        "next_action": "If smoke passes, add output parser and multi-target fixture contract",
    },
    {
        "method_id": "pepglad",
        "method": "PepGLAD",
        "task_scope": "pocket_detection_preflight_only",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepGLAD",
        "source_route": "external Git checkout; GitHub release route expected",
        "doc_route_checked": "README release-weight route checked",
        "example_route_checked": "pocket detection preflight only; no generation checkpoint inference",
        "license_access_route": "public repository route; checkpoint asset unresolved in v0.19",
        "model_weight_route": "GitHub release checkpoint route unresolved/rate-limited",
        "model_or_weight_event": "no checkpoint downloaded; only pocket-detection preflight output observed",
        "next_action": "Resolve release checkpoint URLs and checksum before generation smoke",
    },
    {
        "method_id": "dflow",
        "method": "D-Flow / PeptideDesign",
        "task_scope": "cuda_import_preflight_only",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PeptideDesign",
        "source_route": "external Git checkout; source archive includes dflow checkpoint",
        "doc_route_checked": "README/inference entry route checked",
        "example_route_checked": "CUDA/import preflight only; inference cache files missing",
        "license_access_route": "metadata-level route; no KB-side checkpoint copy",
        "model_weight_route": "source-local dflow.zip/dflow.pt observed outside KB",
        "model_or_weight_event": "checkpoint archive present outside KB; required pep_cache files absent",
        "next_action": "Recover input cache/pepmerge data contract before inference smoke",
    },
    {
        "method_id": "pepmirror",
        "method": "PepMirror",
        "task_scope": "dependency_blocked_route",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepMirror",
        "source_route": "external Git checkout",
        "doc_route_checked": "README dependency route checked",
        "example_route_checked": "not executed because PyRosetta/license and checkpoint routes are unresolved",
        "license_access_route": "PyRosetta license/install route required",
        "model_weight_route": "Zenodo/checkpoint route not resolved in v0.19",
        "model_or_weight_event": "not downloaded; license and checkpoint gates unresolved",
        "next_action": "Resolve PyRosetta license and checkpoint manifest before environment work",
    },
    {
        "method_id": "colabdesign",
        "method": "AfCycDesign / ColabDesign cyclic peptide",
        "task_scope": "notebook_route_deferred",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ColabDesign",
        "source_route": "external Git checkout",
        "doc_route_checked": "ColabDesign route checked; AfCycDesign is notebook-centric for this benchmark use",
        "example_route_checked": "not executed as a CLI smoke because non-notebook adapter is not locked",
        "license_access_route": "public source route; notebook/AF dependency route still needs adapter decision",
        "model_weight_route": "not applicable for v0.19 CLI smoke",
        "model_or_weight_event": "no new model or weight download",
        "next_action": "Choose notebook-to-CLI adapter strategy or keep as deferred route",
    },
    {
        "method_id": "osprey3",
        "method": "DexDesign / OSPREY3",
        "task_scope": "cpu_java_build_route_probe",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/OSPREY3",
        "source_route": "external Git checkout",
        "doc_route_checked": "Gradle/example route checked",
        "example_route_checked": "Gradle version and example file presence probe",
        "license_access_route": "CPU Java route; no GPU or model weights required",
        "model_weight_route": "not applicable",
        "model_or_weight_event": "no model weights",
        "next_action": "Select a minimal OSPREY3 design example before comparative use",
    },
    {
        "method_id": "rfdiffusion_proteinmpnn",
        "method": "RFdiffusion + ProteinMPNN",
        "task_scope": "component_example_smoke_with_handoff_gap",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion",
        "source_route": "external RFdiffusion checkout plus existing ProteinMPNN/Foundry image",
        "doc_route_checked": "existing RFpeptide and Foundry examples checked",
        "example_route_checked": "one RFpeptide/RFdiffusion macrocycle example and one ProteinMPNN PDL1 example",
        "license_access_route": "existing local images/checkpoints reused outside KB",
        "model_weight_route": "external RFpeptide models and Foundry ProteinMPNN checkpoint reused",
        "model_or_weight_event": "no new model weights downloaded; existing external checkpoint mounts reused",
        "next_action": "Write and run a single RFdiffusion-to-ProteinMPNN handoff adapter before comparison",
    },
    {
        "method_id": "bindcraft",
        "method": "BindCraft",
        "task_scope": "author_example_gpu_smoke",
        "source_dir": "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/BindCraft",
        "source_route": "external Git checkout; existing pd-bindcraft-gpu image",
        "doc_route_checked": "example CD47 peptide route checked",
        "example_route_checked": "author-style CD47 peptide quick settings route",
        "license_access_route": "existing PyRosetta-enabled image; no KB-side license material stored",
        "model_weight_route": "existing image/model assets reused outside KB",
        "model_or_weight_event": "no new KB-side model weights; existing image route reused",
        "next_action": "If example completes, add output parser; if it times out, reduce settings for smoke-only route",
    },
]

STATUS_MAP = {
    "passed_gpu": "example_smoke_passed_gpu",
    "passed_cpu_expected": "example_smoke_passed_cpu_expected",
    "preflight_passed_blocked_weights": "preflight_passed_blocked_weights",
    "preflight_passed_blocked_input_contract": "preflight_passed_blocked_input_contract",
    "blocked_license": "blocked_license",
    "deferred_notebook_route": "deferred_notebook_route",
    "failed_command": "failed_command",
    "failed_timeout": "failed_timeout",
    "failed_no_gpu_evidence": "failed_no_gpu_evidence",
}

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

DOC_HEADERS = [
    "method",
    "source_dir",
    "source_commit",
    "source_route",
    "doc_route_checked",
    "example_route_checked",
    "license_access_route",
    "model_weight_route",
    "verification_status",
    "blocker",
    "next_action",
]


def read_runtime(method_id: str) -> dict[str, object]:
    path = EXTERNAL_ROOT / method_id / "runtime.json"
    if not path.exists():
        return {
            "method": method_id,
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


def file_has_x(path: Path) -> bool:
    if not path.exists():
        return False
    return "X" in path.read_text(encoding="utf-8", errors="replace")


def has_bindcraft_low_confidence(method_dir: Path) -> bool:
    stdout = method_dir / "stdout.log"
    if not stdout.exists():
        return False
    text = stdout.read_text(encoding="utf-8", errors="replace")
    return "Trajectory starting confidence low" in text


def normalize_status(method_id: str, raw_status: str, method_dir: Path) -> str:
    status = STATUS_MAP.get(raw_status, raw_status or "missing_runtime")
    if method_id == "pepmlm" and status == "example_smoke_passed_gpu":
        if file_has_x(method_dir / "pepmlm_generated.csv"):
            return "example_smoke_passed_gpu_noncanonical_output_caveat"
    if method_id == "bindcraft" and status == "example_smoke_passed_gpu":
        if has_bindcraft_low_confidence(method_dir):
            return "example_smoke_passed_gpu_low_confidence_caveat"
    return status


def next_gate(status: str) -> str:
    if status.startswith("example_smoke_passed"):
        return "adapter_parser_and_multi_case_fixture_needed"
    if status.startswith("preflight_passed_blocked_weights"):
        return "weights_manifested"
    if status.startswith("preflight_passed_blocked_input_contract"):
        return "input_contract_ready"
    if "license" in status:
        return "license_checked"
    if "notebook" in status:
        return "cli_adapter_decision_needed"
    return "blocker_triage"


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    doc_rows = []
    manifest_rows = []
    result_rows = []

    for meta in METHODS:
        method_id = meta["method_id"]
        method_dir = EXTERNAL_ROOT / method_id
        runtime = read_runtime(method_id)
        raw_status = str(runtime.get("smoke_status", "missing_runtime"))
        status = normalize_status(method_id, raw_status, method_dir)
        command_path = method_dir / "command.sh"
        stdout_log = method_dir / "stdout.log"
        stderr_log = method_dir / "stderr.log"
        runtime_json = method_dir / "runtime.json"
        outputs_manifest = method_dir / "outputs_manifest.csv"
        blocker = str(runtime.get("blocker", ""))
        boundary = (
            "External method-provided example/preflight evidence only; not target-set evidence, "
            "not scoring evidence, not method-ranking evidence, and not complete Benchmark evidence"
        )

        doc_rows.append(
            {
                "method": meta["method"],
                "source_dir": meta["source_dir"],
                "source_commit": runtime.get("source_commit", "missing_runtime"),
                "source_route": meta["source_route"],
                "doc_route_checked": meta["doc_route_checked"],
                "example_route_checked": meta["example_route_checked"],
                "license_access_route": meta["license_access_route"],
                "model_weight_route": meta["model_weight_route"],
                "verification_status": status,
                "blocker": blocker or "none_observed_for_example_smoke_scope",
                "next_action": meta["next_action"],
            }
        )

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
                "smoke_test_id": f"v019_{method_id}",
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
                "blocker": blocker or "none_observed_for_example_smoke_scope",
                "evidence_boundary": boundary,
                "next_gate": next_gate(status),
            }
        )

    write_csv(ROOT / "benchmark/deployment/method_source_doc_verification_v0.19.csv", DOC_HEADERS, doc_rows)
    write_csv(ROOT / "benchmark/deployment/method_install_smoke_manifest_v0.19.csv", MANIFEST_HEADERS, manifest_rows)
    write_csv(ROOT / "benchmark/deployment/method_smoke_test_results_v0.19.csv", RESULT_HEADERS, result_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
