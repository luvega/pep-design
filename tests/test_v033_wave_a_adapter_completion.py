from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_SCRIPT = ROOT / "scripts" / "run_v033_wave_a_pilot.py"
PARSER_SCRIPT = ROOT / "scripts" / "parse_v033_pilot_outputs.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def test_v033_runner_selects_only_v031_placeholder_failed_wave_a_jobs() -> None:
    module = load_module(RUNNER_SCRIPT, "run_v033_wave_a_pilot")

    jobs = module.load_v033_jobs(
        ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv",
        ROOT / "benchmark/results/pilot_candidate_outputs_v0.31.csv",
    )

    assert len(jobs) == 10
    assert {job["execution_wave"] for job in jobs} == {"wave_a"}
    assert {job["random_seed"] for job in jobs} == {"42", "43"}
    assert {job["method"] for job in jobs} == {
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "PepMirror",
        "RFdiffusion + ProteinMPNN",
    }
    assert all(job["job_id"].startswith("v030_") for job in jobs)


def test_v033_runner_builds_method_specific_command_packages_without_placeholder_exit(tmp_path: Path) -> None:
    module = load_module(RUNNER_SCRIPT, "run_v033_wave_a_pilot")
    jobs = module.load_v033_jobs(
        ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv",
        ROOT / "benchmark/results/pilot_candidate_outputs_v0.31.csv",
    )
    matrix = module.load_execution_matrix(ROOT / "benchmark/deployment/pilot_execution_matrix_v0.30.csv")

    for job in jobs:
        output_dir = tmp_path / job["job_id"]
        module.write_command_package(job, matrix[job["job_id"]], output_dir)
        command_text = (output_dir / "command.sh").read_text(encoding="utf-8")
        assert "adapter_not_implemented_for_this_method" not in command_text
        assert "exit 86" not in command_text
        assert "method_specific_adapter.py" in command_text
        assert (output_dir / "method_specific_adapter.py").is_file()


def test_v033_runner_writes_standard_method_specific_failed_rows(tmp_path: Path) -> None:
    module = load_module(RUNNER_SCRIPT, "run_v033_wave_a_pilot")
    job = {
        "job_id": "v030_dflow_3eqs_seed42",
        "method": "D-Flow / PeptideDesign",
        "task_id": "T2_structure_peptide_binder",
        "target_id": "mdm2_p53_3eqs_fixture",
        "input_mode": "pdb_pocket_json",
        "target_pdb": "3EQS",
        "target_chains": "A",
        "binder_chain": "B",
        "pocket_definition": "fixture",
        "peptide_type": "linear",
        "chirality": "L",
        "cyclic": "no",
        "n_designs_requested": "1",
        "random_seed": "42",
        "adapter_config": "test_adapter",
        "status": "planned_pilot",
        "notes": "test",
        "pilot_target_id": "mdm2_p53_3eqs_fixture",
        "pilot_lane": "wave_a_structure_generation",
        "execution_wave": "wave_a",
        "expected_output_contract": "candidate_outputs_and_method_manifest",
        "failure_policy": "write_failed_candidate_row_on_exception",
        "evidence_boundary": "Planned computational pilot only; not Benchmark result; not scoring evidence",
    }
    execution = {
        "execution_id": "exec_v030_dflow_3eqs_seed42",
        "job_id": "v030_dflow_3eqs_seed42",
        "method": "D-Flow / PeptideDesign",
        "target_id": "mdm2_p53_3eqs_fixture",
        "execution_wave": "wave_a",
        "runner": "planned_dflow_adapter",
        "container_or_env": "pd-benchmark-methods-gpu:0.21/bench-dflow",
        "gpu_required": "yes",
        "max_runtime_sec": "1",
        "output_root": str(tmp_path / "dflow"),
        "expected_parser": "candidate_outputs.csv",
        "status": "planned_pilot",
        "blocked_reason": "none",
        "evidence_boundary": "Planned computational pilot only; not Benchmark result; not scoring evidence",
        "next_action": "test",
    }

    result = module.write_failed_job(
        job=job,
        execution=execution,
        output_dir=tmp_path / "dflow",
        status_reason="dflow_adapter_attempt_failed_exit_2",
        exit_code="2",
        runtime_seconds=0.25,
    )

    assert result["status"] == "failed"
    method_rows = read_csv(tmp_path / "dflow" / "method_output_manifest.csv")
    candidate_rows = read_csv(tmp_path / "dflow" / "candidate_outputs.csv")
    assert method_rows[0]["execution_stage"] == "bounded_wave_a_adapter_completion_v0.33"
    assert method_rows[0]["parser_status"] == "failed"
    assert "not Benchmark result" in method_rows[0]["status_reason"]
    assert candidate_rows[0]["parse_status"] == "failed"
    assert candidate_rows[0]["source_output_id"] == "not_generated"
    assert candidate_rows[0]["status_reason"] == "dflow_adapter_attempt_failed_exit_2"
    assert "not scoring evidence" in candidate_rows[0]["notes"]


def test_v033_parser_merges_only_v033_placeholder_completion_jobs(tmp_path: Path) -> None:
    module = load_module(PARSER_SCRIPT, "parse_v033_pilot_outputs")
    job_headers = [
        "job_id",
        "method",
        "task_id",
        "target_id",
        "input_mode",
        "target_sequence",
        "target_pdb",
        "target_chains",
        "binder_chain",
        "pocket_definition",
        "peptide_type",
        "chirality",
        "cyclic",
        "n_designs_requested",
        "random_seed",
        "adapter_config",
        "status",
        "notes",
        "pilot_target_id",
        "pilot_lane",
        "execution_wave",
        "expected_output_contract",
        "failure_policy",
        "evidence_boundary",
    ]
    jobs = [
        {
            "job_id": "v030_dflow_3eqs_seed42",
            "method": "D-Flow / PeptideDesign",
            "task_id": "T2_structure_peptide_binder",
            "target_id": "mdm2_p53_3eqs_fixture",
            "input_mode": "pdb_pocket_json",
            "target_pdb": "3EQS",
            "peptide_type": "linear",
            "chirality": "L",
            "cyclic": "no",
            "random_seed": "42",
            "execution_wave": "wave_a",
        },
        {
            "job_id": "v030_colabdesign_7zkr_seed42",
            "method": "AfCycDesign / ColabDesign cyclic peptide",
            "task_id": "T2_structure_peptide_binder",
            "target_id": "gabarap_7zkr_fixture",
            "input_mode": "pdb_binder_len",
            "target_pdb": "7ZKR",
            "peptide_type": "cyclic",
            "chirality": "L",
            "cyclic": "yes",
            "random_seed": "42",
            "execution_wave": "wave_a",
        },
    ]
    v031_headers = [
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
    v031_rows = [
        {
            "design_id": "v030_dflow_3eqs_seed42_failed",
            "job_id": "v030_dflow_3eqs_seed42",
            "method": "D-Flow / PeptideDesign",
            "target_id": "mdm2_p53_3eqs_fixture",
            "parse_status": "failed",
            "status_reason": "adapter_execution_failed_or_not_implemented_exit_86",
        },
        {
            "design_id": "v030_colabdesign_7zkr_seed42_candidate_1",
            "job_id": "v030_colabdesign_7zkr_seed42",
            "method": "AfCycDesign / ColabDesign cyclic peptide",
            "target_id": "gabarap_7zkr_fixture",
            "parse_status": "parsed",
            "status_reason": "bounded_colabdesign_output_parsed",
        },
    ]
    execution_headers = [
        "execution_id",
        "job_id",
        "method",
        "target_id",
        "execution_wave",
        "runner",
        "container_or_env",
        "gpu_required",
        "max_runtime_sec",
        "output_root",
        "expected_parser",
        "status",
        "blocked_reason",
        "evidence_boundary",
        "next_action",
    ]
    job_manifest = tmp_path / "jobs.csv"
    v031_candidates = tmp_path / "v031_candidates.csv"
    execution_matrix = tmp_path / "execution.csv"
    write_csv(job_manifest, job_headers, jobs)
    write_csv(v031_candidates, v031_headers, v031_rows)
    write_csv(
        execution_matrix,
        execution_headers,
        [
            {
                "execution_id": "exec_v030_dflow_3eqs_seed42",
                "job_id": "v030_dflow_3eqs_seed42",
                "method": "D-Flow / PeptideDesign",
                "target_id": "mdm2_p53_3eqs_fixture",
                "execution_wave": "wave_a",
                "runner": "planned_dflow_adapter",
                "container_or_env": "test_env",
                "output_root": "benchmark_runs/v0.33/dflow/v030_dflow_3eqs_seed42",
            }
        ],
    )

    parsed_dir = tmp_path / "runs" / "dflow" / "v030_dflow_3eqs_seed42"
    write_csv(
        parsed_dir / "method_output_manifest.csv",
        module.METHOD_OUTPUT_HEADERS,
        [
            {
                "run_record_id": "v030_dflow_3eqs_seed42_v033_wave_a",
                "job_id": "v030_dflow_3eqs_seed42",
                "method": "D-Flow / PeptideDesign",
                "task_id": "T2_structure_peptide_binder",
                "execution_stage": "bounded_wave_a_adapter_completion_v0.33",
                "source_commit": "external_or_not_applicable",
                "model_revision": "external_or_not_applicable",
                "environment_id": "test_env",
                "command": "command.sh",
                "raw_output_root": str(parsed_dir),
                "stdout_log": "stdout.log",
                "stderr_log": "stderr.log",
                "runtime_seconds": "1.0",
                "exit_code": "0",
                "parser_status": "parsed",
                "status_reason": "dflow_standard_candidate_fixture_parsed; not Benchmark result; not scoring evidence",
                "created_at": "2026-07-10",
            }
        ],
    )
    write_csv(
        parsed_dir / "candidate_outputs.csv",
        module.CANDIDATE_HEADERS,
        [
            {
                "design_id": "v030_dflow_3eqs_seed42_candidate_1",
                "job_id": "v030_dflow_3eqs_seed42",
                "method": "D-Flow / PeptideDesign",
                "target_id": "mdm2_p53_3eqs_fixture",
                "binder_id": "candidate_1",
                "source_output_id": "sample_0.pdb",
                "generation_rank": "1",
                "sequence": "ACDE",
                "structure_path": str(parsed_dir / "sample_0.pdb"),
                "peptide_type": "linear",
                "chirality": "L",
                "cyclic": "no",
                "parse_status": "parsed",
                "status_reason": "dflow_standard_candidate_fixture_parsed",
                "notes": "Bounded v0.33 adapter completion row only; not Benchmark result; not scoring evidence",
            }
        ],
    )

    result = module.merge_v033_outputs(
        job_manifest=job_manifest,
        v031_candidate_outputs=v031_candidates,
        execution_matrix=execution_matrix,
        run_root=tmp_path / "runs",
        out_dir=tmp_path / "out",
        deployment_dir=tmp_path / "deploy",
    )

    assert result["wave_a_jobs"] == 1
    assert result["candidate_rows"] == 1
    candidates = read_csv(tmp_path / "out" / "pilot_candidate_outputs_v0.33.csv")
    execution_rows = read_csv(tmp_path / "deploy" / "pilot_execution_results_v0.33.csv")
    assert [row["job_id"] for row in candidates] == ["v030_dflow_3eqs_seed42"]
    assert [row["job_id"] for row in execution_rows] == ["v030_dflow_3eqs_seed42"]
    assert execution_rows[0]["status"] == "parsed"
    assert "not Benchmark result" in execution_rows[0]["evidence_boundary"]
