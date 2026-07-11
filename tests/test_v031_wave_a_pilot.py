from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_SCRIPT = ROOT / "scripts" / "run_v031_wave_a_pilot.py"
PARSER_SCRIPT = ROOT / "scripts" / "parse_v031_pilot_outputs.py"


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


def test_v031_runner_selects_only_wave_a_jobs_from_v030_manifest() -> None:
    module = load_module(RUNNER_SCRIPT, "run_v031_wave_a_pilot")

    jobs = module.load_wave_a_jobs(ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv")

    assert len(jobs) == 14
    assert {job["execution_wave"] for job in jobs} == {"wave_a"}
    assert {job["random_seed"] for job in jobs} == {"42", "43"}
    assert {job["method"] for job in jobs} == {
        "PepMLM",
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "PepMirror",
        "RFdiffusion + ProteinMPNN",
        "AfCycDesign / ColabDesign cyclic peptide",
    }


def test_v031_runner_writes_standard_failed_rows_when_execution_is_not_available(tmp_path: Path) -> None:
    module = load_module(RUNNER_SCRIPT, "run_v031_wave_a_pilot")
    job = {
        "job_id": "v031_test_job",
        "method": "PepMLM",
        "task_id": "T1_sequence_binder",
        "target_id": "pepmlm_sequence_contract_fixture",
        "input_mode": "seq_only_csv",
        "target_sequence": "AAAXXX",
        "target_pdb": "",
        "target_chains": "not_applicable",
        "binder_chain": "not_applicable",
        "pocket_definition": "",
        "peptide_type": "linear",
        "chirality": "L",
        "cyclic": "no",
        "n_designs_requested": "1",
        "random_seed": "42",
        "adapter_config": "test_adapter",
        "status": "planned_pilot",
        "notes": "test",
        "pilot_target_id": "pepmlm_sequence_contract_fixture",
        "pilot_lane": "sequence_generation",
        "execution_wave": "wave_a",
        "expected_output_contract": "candidate_outputs_and_method_manifest",
        "failure_policy": "write_failed_candidate_row_on_exception",
        "evidence_boundary": "Planned computational pilot only; not Benchmark result; not scoring evidence",
    }
    execution = {
        "execution_id": "exec_v031_test_job",
        "job_id": "v031_test_job",
        "method": "PepMLM",
        "target_id": "pepmlm_sequence_contract_fixture",
        "execution_wave": "wave_a",
        "runner": "planned_pepmlm_adapter",
        "container_or_env": "test_env",
        "gpu_required": "yes",
        "max_runtime_sec": "1",
        "output_root": str(tmp_path / "v031_test_job"),
        "expected_parser": "candidate_outputs.csv",
        "status": "planned_pilot",
        "blocked_reason": "none",
        "evidence_boundary": "Planned computational pilot only; not Benchmark result; not scoring evidence",
        "next_action": "test",
    }

    result = module.write_failed_job(
        job=job,
        execution=execution,
        output_dir=tmp_path / "v031_test_job",
        status_reason="forced_failure_for_test",
        exit_code="not_run",
    )

    assert result["status"] == "failed"
    method_rows = read_csv(tmp_path / "v031_test_job" / "method_output_manifest.csv")
    candidate_rows = read_csv(tmp_path / "v031_test_job" / "candidate_outputs.csv")
    assert method_rows[0]["job_id"] == "v031_test_job"
    assert method_rows[0]["parser_status"] == "failed"
    assert candidate_rows[0]["parse_status"] == "failed"
    assert candidate_rows[0]["source_output_id"] == "not_generated"
    assert "not Benchmark result" in candidate_rows[0]["notes"]


def test_v031_runner_builds_real_pepmlm_command_package(tmp_path: Path) -> None:
    module = load_module(RUNNER_SCRIPT, "run_v031_wave_a_pilot")
    job = [row for row in module.load_wave_a_jobs(ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv") if row["method"] == "PepMLM"][0]
    execution = module.load_execution_matrix(ROOT / "benchmark/deployment/pilot_execution_matrix_v0.30.csv")[job["job_id"]]

    module.write_command_package(job, execution, tmp_path / job["job_id"])

    command_text = (tmp_path / job["job_id"] / "command.sh").read_text(encoding="utf-8")
    adapter_text = (tmp_path / job["job_id"] / "pepmlm_v031_adapter.py").read_text(encoding="utf-8")
    assert "docker run" in command_text
    assert "bench-pepmlm" in command_text
    assert job["job_id"] in adapter_text
    assert "adapter_not_implemented_for_this_method" not in command_text


def test_v031_runner_builds_colabdesign_bounded_command_package(tmp_path: Path) -> None:
    module = load_module(RUNNER_SCRIPT, "run_v031_wave_a_pilot")
    job = [
        row
        for row in module.load_wave_a_jobs(ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv")
        if row["method"] == "AfCycDesign / ColabDesign cyclic peptide"
    ][0]
    execution = module.load_execution_matrix(ROOT / "benchmark/deployment/pilot_execution_matrix_v0.30.csv")[job["job_id"]]

    module.write_command_package(job, execution, tmp_path / job["job_id"])

    command_text = (tmp_path / job["job_id"] / "command.sh").read_text(encoding="utf-8")
    assert "run_colabdesign_bounded_generation.py" in command_text
    assert f"--job-id {job['job_id']}" in command_text
    assert f"--target-id {job['target_id']}" in command_text
    assert "--inner-command-filename colabdesign_inner_command.sh" in command_text
    assert "adapter_not_implemented_for_this_method" not in command_text


def test_v031_parser_merges_outputs_and_inserts_missing_failed_rows(tmp_path: Path) -> None:
    module = load_module(PARSER_SCRIPT, "parse_v031_pilot_outputs")
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
            "job_id": "parsed_job",
            "method": "PepMLM",
            "task_id": "T1_sequence_binder",
            "target_id": "pepmlm_sequence_contract_fixture",
            "input_mode": "seq_only_csv",
            "target_sequence": "AAAXXX",
            "peptide_type": "linear",
            "chirality": "L",
            "cyclic": "no",
            "random_seed": "42",
            "execution_wave": "wave_a",
        },
        {
            "job_id": "missing_job",
            "method": "PepGLAD",
            "task_id": "T2_structure_peptide_binder",
            "target_id": "mdm2_p53_3eqs_fixture",
            "input_mode": "pdb_pocket_json",
            "target_pdb": "3EQS",
            "peptide_type": "linear",
            "chirality": "L",
            "cyclic": "no",
            "random_seed": "43",
            "execution_wave": "wave_a",
        },
        {
            "job_id": "wave_b_job",
            "method": "BindCraft",
            "task_id": "T4_bindcraft_peptide_smoke",
            "target_id": "bindcraft_cd47_method_example_control",
            "execution_wave": "wave_b",
        },
    ]
    job_manifest = tmp_path / "jobs.csv"
    write_csv(job_manifest, job_headers, jobs)
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
    execution_matrix = tmp_path / "execution.csv"
    write_csv(
        execution_matrix,
        execution_headers,
        [
            {
                "execution_id": "exec_parsed_job",
                "job_id": "parsed_job",
                "method": "PepMLM",
                "target_id": "pepmlm_sequence_contract_fixture",
                "execution_wave": "wave_a",
                "runner": "planned_pepmlm_adapter",
                "container_or_env": "test_env",
                "output_root": "benchmark_runs/v0.31/parsed_job",
            },
            {
                "execution_id": "exec_missing_job",
                "job_id": "missing_job",
                "method": "PepGLAD",
                "target_id": "mdm2_p53_3eqs_fixture",
                "execution_wave": "wave_a",
                "runner": "planned_placeholder",
                "container_or_env": "test_env",
                "output_root": "benchmark_runs/v0.31/missing_job",
            },
            {
                "execution_id": "exec_wave_b_job",
                "job_id": "wave_b_job",
                "method": "BindCraft",
                "target_id": "bindcraft_cd47_method_example_control",
                "execution_wave": "wave_b",
                "runner": "blocked",
                "container_or_env": "not_applicable",
                "output_root": "benchmark_runs/v0.31/wave_b_job",
            },
        ],
    )

    parsed_dir = tmp_path / "runs" / "parsed_job"
    write_csv(parsed_dir / "method_output_manifest.csv", module.METHOD_OUTPUT_HEADERS, [
        {
            "run_record_id": "parsed_job_run",
            "job_id": "parsed_job",
            "method": "PepMLM",
            "task_id": "T1_sequence_binder",
            "execution_stage": "bounded_wave_a_pilot",
            "source_commit": "abc123",
            "model_revision": "external",
            "environment_id": "test_env",
            "command": "command.sh",
            "raw_output_root": str(parsed_dir),
            "stdout_log": "stdout.log",
            "stderr_log": "stderr.log",
            "runtime_seconds": "1.0",
            "exit_code": "0",
            "parser_status": "parsed",
            "status_reason": "parsed; not Benchmark result",
            "created_at": "2026-07-09",
        }
    ])
    write_csv(parsed_dir / "candidate_outputs.csv", module.CANDIDATE_HEADERS, [
        {
            "design_id": "parsed_job_candidate_1",
            "job_id": "parsed_job",
            "method": "PepMLM",
            "target_id": "pepmlm_sequence_contract_fixture",
            "binder_id": "candidate_1",
            "source_output_id": "parsed.csv",
            "generation_rank": "1",
            "sequence": "AAA",
            "structure_path": "",
            "peptide_type": "linear",
            "chirality": "L",
            "cyclic": "no",
            "parse_status": "parsed",
            "status_reason": "parsed",
            "notes": "Bounded Wave A pilot only; not Benchmark result; not scoring evidence",
        }
    ])

    result = module.merge_v031_outputs(
        job_manifest=job_manifest,
        execution_matrix=execution_matrix,
        run_root=tmp_path / "runs",
        out_dir=tmp_path / "out",
        deployment_dir=tmp_path / "deploy",
    )

    assert result["wave_a_jobs"] == 2
    assert result["method_rows"] == 2
    assert result["candidate_rows"] == 2
    assert result["execution_rows"] == 2
    tracked_outputs = [
        tmp_path / "out" / "pilot_method_output_manifest_v0.31.csv",
        tmp_path / "out" / "pilot_candidate_outputs_v0.31.csv",
        tmp_path / "out" / "pilot_run_v0.31.csv",
        tmp_path / "deploy" / "pilot_execution_results_v0.31.csv",
    ]
    for output_path in tracked_outputs:
        assert b"\r" not in output_path.read_bytes()
        assert read_csv(output_path)
    candidates = read_csv(tmp_path / "out" / "pilot_candidate_outputs_v0.31.csv")
    execution_rows = read_csv(tmp_path / "deploy" / "pilot_execution_results_v0.31.csv")
    assert {row["job_id"] for row in candidates} == {"parsed_job", "missing_job"}
    assert {row["job_id"] for row in execution_rows} == {"parsed_job", "missing_job"}
    assert {row["execution_wave"] for row in execution_rows} == {"wave_a"}
    assert {row["status"] for row in execution_rows} == {"parsed", "failed"}
    missing = [row for row in candidates if row["job_id"] == "missing_job"][0]
    assert missing["parse_status"] == "failed"
    assert missing["source_output_id"] == "not_generated"
    assert "not Benchmark result" in missing["notes"]
