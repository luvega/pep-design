from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_v034_wave_a_generation.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_v034_wave_a_generation", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_selects_seven_jobs_per_stage() -> None:
    runner = load_runner()

    primary = runner.load_jobs(stage="primary")
    extension = runner.load_jobs(stage="extension")
    assert len(primary) == len(extension) == 7
    assert {job["method"] for job in primary} == {job["method"] for job in extension}
    assert {job["random_seed"] for job in primary} == {"42"}
    assert {job["random_seed"] for job in extension} == {"43"}


def test_runner_cli_bootstraps_repository_imports_outside_repo_cwd(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_runner_registry_uses_seven_versioned_method_modules() -> None:
    runner = load_runner()

    assert runner.ADAPTER_MODULES == {
        "PepMLM": "scripts.v034_adapters.pepmlm",
        "DiffPepBuilder": "scripts.v034_adapters.diffpepbuilder",
        "PepGLAD": "scripts.v034_adapters.pepglad",
        "D-Flow / PeptideDesign": "scripts.v034_adapters.dflow",
        "PepMirror": "scripts.v034_adapters.pepmirror",
        "AfCycDesign / ColabDesign cyclic peptide": "scripts.v034_adapters.colabdesign",
        "RFdiffusion + ProteinMPNN": "scripts.v034_adapters.rfdiffusion_mpnn",
    }


def test_attempt_directories_never_overwrite_existing_evidence(tmp_path: Path) -> None:
    runner = load_runner()
    job_root = tmp_path / "method" / "job"

    first = runner.allocate_attempt_dir(job_root, retry_failed=False)
    assert first.name == "attempt_001"
    (first / "run_result.json").write_text('{"status":"execution_failed"}\n', encoding="utf-8")
    with pytest.raises(FileExistsError):
        runner.allocate_attempt_dir(job_root, retry_failed=False)
    second = runner.allocate_attempt_dir(job_root, retry_failed=True)
    assert second.name == "attempt_002"
    assert (first / "run_result.json").is_file()


def test_extension_requires_primary_pass_or_pass_with_warning(tmp_path: Path) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    job_root = tmp_path / "pepmlm" / job["job_id"]
    attempt = job_root / "attempt_001"
    attempt.mkdir(parents=True)

    assert not runner.primary_is_eligible(job_root)
    _write_complete_passed_attempt(runner, attempt, job)
    assert runner.primary_is_eligible(job_root)
    _write_complete_passed_attempt(
        runner,
        attempt,
        job,
        overall_qc_status="pass_with_warning",
    )
    assert runner.primary_is_eligible(job_root)
    result = json.loads((attempt / "run_result.json").read_text(encoding="utf-8"))
    result.update({"status": "qc_failed", "overall_qc_status": "fail"})
    (attempt / "run_result.json").write_text(json.dumps(result) + "\n", encoding="utf-8")
    assert not runner.primary_is_eligible(job_root)


@pytest.mark.parametrize(
    "raw_result",
    [
        '[]\n',
        '{"status":"qc_failed","status":"passed","overall_qc_status":"pass"}\n',
        '{"status":"passed","overall_qc_status":"fail","overall_qc_status":"pass"}\n',
    ],
)
def test_extension_rejects_corrupt_or_duplicate_primary_result(
    tmp_path: Path, raw_result: str
) -> None:
    runner = load_runner()
    attempt = tmp_path / "method/primary_job/attempt_001"
    attempt.mkdir(parents=True)
    (attempt / "run_result.json").write_text(raw_result, encoding="utf-8")

    assert not runner.primary_is_eligible(attempt.parent)


def test_runner_failure_statuses_are_fixed_and_fail_closed() -> None:
    runner = load_runner()

    assert runner.execution_status(exit_code=0, timed_out=False, parsed=True, qc="pass") == "passed"
    assert runner.execution_status(exit_code=0, timed_out=False, parsed=True, qc="pass_with_warning") == "passed"
    assert runner.execution_status(exit_code=124, timed_out=True, parsed=False, qc="fail") == "execution_timeout"
    assert runner.execution_status(exit_code=2, timed_out=False, parsed=False, qc="fail") == "execution_failed"
    assert runner.execution_status(exit_code=0, timed_out=False, parsed=False, qc="fail") == "parse_failed"
    assert runner.execution_status(exit_code=0, timed_out=False, parsed=True, qc="typo") == "qc_failed"


def _fake_job() -> dict[str, str]:
    return {
        "job_id": "v034_fake_seed42",
        "method": "PepMLM",
        "task_id": "T1_sequence_binder",
        "target_id": "fixture",
        "peptide_type": "linear",
        "chirality": "L",
        "cyclic": "no",
        "random_seed": "42",
        "seed_stage": "primary",
        "length_min": "3",
        "length_max": "3",
        "expected_binder_chain": "not_applicable",
        "expected_target_chain": "not_applicable",
        "effective_seed_required": "yes",
        "target_binding_check_mode": "not_applicable",
    }


def _primary_contract_job(runner) -> dict[str, str]:
    return next(job for job in runner.load_jobs(stage="primary") if job["method"] == "PepMLM")


class _FakeAdapter:
    METHOD = "PepMLM"
    SOURCE_COMMIT = "a" * 40
    SOURCE_ENTRYPOINT_SHA256 = "b" * 64
    MODEL_ID = "fake/model"
    MODEL_REVISION = "fake-model"
    MODEL_WEIGHTS_SHA256 = "c" * 64
    DEFAULT_IMAGE = "fake"
    DEFAULT_ENV = "env"
    TOP_K = 3

    @staticmethod
    def prepare(job, execution, attempt_dir):
        del execution
        raw = attempt_dir / "raw"
        raw.mkdir(parents=True)
        (raw / "runtime_evidence.json").write_text(
            json.dumps(
                {
                    "conda_environment": _FakeAdapter.DEFAULT_ENV,
                    "container_image": _FakeAdapter.DEFAULT_IMAGE,
                    "effective_seed": int(job["random_seed"]),
                    "model_id": _FakeAdapter.MODEL_ID,
                    "model_revision": _FakeAdapter.MODEL_REVISION,
                    "model_weights_sha256": _FakeAdapter.MODEL_WEIGHTS_SHA256,
                    "requested_seed": int(job["random_seed"]),
                    "sampling_strategy": "top_k_categorical",
                    "seed_control_status": "honored",
                    "source_commit": _FakeAdapter.SOURCE_COMMIT,
                    "source_entrypoint_sha256": _FakeAdapter.SOURCE_ENTRYPOINT_SHA256,
                    "top_k": _FakeAdapter.TOP_K,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        command = attempt_dir / "command.sh"
        command.write_text("#!/usr/bin/env bash\nset -euo pipefail\nprintf ACX > raw/candidate.txt\n", encoding="utf-8")
        command.chmod(0o755)
        return ["bash", str(command)]

    @staticmethod
    def parse(job, attempt_dir):
        output = attempt_dir / "raw/candidate.txt"
        sequence = output.read_text(encoding="utf-8")
        runtime = json.loads(
            (attempt_dir / "raw/runtime_evidence.json").read_text(encoding="utf-8")
        )
        return (
            {
                "sequence": sequence,
                "structure_path": "",
                "source_output_path": str(output),
                "binder_chain": "not_applicable",
                "parse_status": "partial" if "X" in sequence else "parsed",
                "status_reason": "fake_parsed",
            },
            runtime,
        )


def _configure_single_stage(
    runner, monkeypatch, *, method: str = "PepMLM", job_id: str = "v034_fake_seed42"
) -> dict[str, str]:
    job = _fake_job()
    job.update({"method": method, "job_id": job_id})
    monkeypatch.setattr(runner, "load_jobs", lambda **kwargs: [job])
    monkeypatch.setattr(
        runner,
        "load_execution_matrix",
        lambda: {job["job_id"]: {"container_or_env": "fake/env", "max_runtime_sec": "10"}},
    )
    monkeypatch.setattr(runner, "load_adapter", lambda method: _FakeAdapter)
    return job


def _write_existing_attempt(
    runner,
    run_root: Path,
    job: dict[str, str],
    *,
    result: dict[str, object] | None = None,
    raw_result: str | None = None,
) -> Path:
    attempt = runner._job_root(run_root, job) / "attempt_003"
    attempt.mkdir(parents=True)
    if result is not None:
        (attempt / "run_result.json").write_text(
            json.dumps(result) + "\n",
            encoding="utf-8",
        )
    elif raw_result is not None:
        (attempt / "run_result.json").write_text(raw_result, encoding="utf-8")
    return attempt


def _write_complete_passed_attempt(
    runner,
    attempt: Path,
    job: dict[str, str],
    *,
    overall_qc_status: str = "pass",
    execution: dict[str, str] | None = None,
    adapter=None,
) -> None:
    execution = execution or runner.load_execution_matrix()[job["job_id"]]
    adapter = adapter or runner.load_adapter(job["method"])
    design_id = f"{job['job_id']}_candidate_1"
    created_at = "2026-07-12T00:00:00+00:00"
    status_reason = "bounded_connectivity_candidate_qc_passed"
    raw = attempt / "raw"
    raw.mkdir(exist_ok=True)
    sequence = "ACX" if overall_qc_status == "pass_with_warning" else "ACD"
    runtime = {
        "conda_environment": adapter.DEFAULT_ENV,
        "container_image": adapter.DEFAULT_IMAGE,
        "effective_seed": int(job["random_seed"]),
        "model_id": adapter.MODEL_ID,
        "model_revision": adapter.MODEL_REVISION,
        "model_weights_sha256": adapter.MODEL_WEIGHTS_SHA256,
        "requested_seed": int(job["random_seed"]),
        "sampling_strategy": "top_k_categorical",
        "seed_control_status": "honored",
        "source_commit": adapter.SOURCE_COMMIT,
        "source_entrypoint_sha256": adapter.SOURCE_ENTRYPOINT_SHA256,
        "top_k": adapter.TOP_K,
    }
    (raw / "runtime_evidence.json").write_text(
        json.dumps(runtime, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if isinstance(adapter, type):
        (raw / "candidate.txt").write_text(sequence, encoding="utf-8")
    else:
        runner.write_csv(
            raw / "pepmlm_generated.csv",
            ("job_id", "generated_binder", "binder_rank", "target_id"),
            [
                {
                    "job_id": job["job_id"],
                    "generated_binder": sequence,
                    "binder_rank": "1",
                    "target_id": job["target_id"],
                }
            ],
        )
    (attempt / "command.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (attempt / "stdout.log").write_text("fixture\n", encoding="utf-8")
    (attempt / "stderr.log").write_text("", encoding="utf-8")
    candidate_value, parsed_runtime = adapter.parse(job, attempt)
    candidate = runner._candidate_row(job, candidate_value)
    qc = runner.evaluate_candidate_qc(job, candidate, parsed_runtime, raw)
    qc_row = {"job_id": job["job_id"], "design_id": design_id, **qc}
    assert qc["overall_qc_status"] == overall_qc_status
    parser_status = candidate["parse_status"]
    result = {
        "attempt_dir": str(attempt),
        "created_at": created_at,
        "design_id": design_id,
        "exit_code": 0,
        "job_id": job["job_id"],
        "method": job["method"],
        "overall_qc_status": overall_qc_status,
        "parser_status": parser_status,
        "runtime_seconds": "1.000",
        "status": "passed",
        "status_reason": status_reason,
    }
    (attempt / "run_result.json").write_text(
        json.dumps(result, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "run_record_id": f"{job['job_id']}_{attempt.name}",
        "job_id": job["job_id"],
        "method": job["method"],
        "task_id": job["task_id"],
        "execution_stage": job["seed_stage"],
        "source_commit": adapter.SOURCE_COMMIT,
        "model_revision": adapter.MODEL_REVISION,
        "environment_id": execution["container_or_env"],
        "command": f"bash {attempt / 'command.sh'}",
        "raw_output_root": str(attempt / "raw"),
        "stdout_log": str(attempt / "stdout.log"),
        "stderr_log": str(attempt / "stderr.log"),
        "runtime_seconds": "1.000",
        "exit_code": "0",
        "parser_status": parser_status,
        "overall_qc_status": overall_qc_status,
        "status": "passed",
        "status_reason": status_reason,
        "created_at": created_at,
    }
    runner.write_csv(
        attempt / "method_output_manifest.csv",
        runner.METHOD_OUTPUT_HEADERS,
        [manifest],
    )
    runner.write_csv(
        attempt / "candidate_outputs.csv",
        runner.CANDIDATE_HEADERS,
        [candidate],
    )
    runner.write_csv(attempt / "candidate_qc.csv", qc_row.keys(), [qc_row])


def _rewrite_csv_cell(path: Path, field: str, value: str) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    rows[0][field] = value
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _append_duplicate_csv_row(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([*lines, lines[-1], ""]), encoding="utf-8")


def _append_csv_column(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    rows[0].append("unexpected")
    for row in rows[1:]:
        row.append("tampered")
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)


def test_resume_returns_existing_pass_without_creating_attempt(tmp_path: Path, monkeypatch) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)
    attempt = _write_existing_attempt(
        runner,
        tmp_path,
        job,
    )
    _write_complete_passed_attempt(runner, attempt, job)

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=True,
        resume=True,
        retry_failed=False,
    )

    assert results[0]["status"] == "resume_skipped_passed"
    assert results[0]["overall_qc_status"] == "pass"
    assert results[0]["job_id"] == job["job_id"]
    assert results[0]["method"] == job["method"]
    assert results[0]["attempt_dir"] == str(attempt)
    assert results[0]["resumed_from_status"] == "passed"
    assert sorted(path.name for path in attempt.parent.iterdir()) == ["attempt_003"]


@pytest.mark.parametrize(
    ("result", "write_artifacts"),
    [
        ({"status": "passed", "overall_qc_status": "fail"}, True),
        ({"status": "passed"}, True),
        ({"status": "passed", "overall_qc_status": "pass"}, False),
    ],
)
def test_resume_does_not_accept_incomplete_or_inconsistent_passed_attempt(
    tmp_path: Path,
    monkeypatch,
    result: dict[str, object],
    write_artifacts: bool,
) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)
    attempt = _write_existing_attempt(runner, tmp_path, job, result=result)
    if write_artifacts:
        for name in (
            "candidate_outputs.csv",
            "candidate_qc.csv",
            "method_output_manifest.csv",
        ):
            (attempt / name).write_text("", encoding="utf-8")

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=True,
        resume=True,
        retry_failed=False,
    )

    assert results[0]["status"] == "resume_skipped_invalid"
    assert results[0]["status_reason"] == "latest_run_result_invalid"
    assert sorted(path.name for path in attempt.parent.iterdir()) == ["attempt_003"]


def test_primary_rejects_passed_result_with_three_empty_evidence_files(tmp_path: Path) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    result = {
        "status": "passed",
        "overall_qc_status": "pass",
        "job_id": job["job_id"],
        "method": job["method"],
        "attempt_dir": str(attempt),
        "design_id": f"{job['job_id']}_candidate_1",
        "exit_code": 0,
        "parser_status": "partial",
        "status_reason": "bounded_connectivity_candidate_qc_passed",
        "runtime_seconds": "1.000",
        "created_at": "2026-07-12T00:00:00+00:00",
    }
    (attempt / "run_result.json").write_text(json.dumps(result) + "\n", encoding="utf-8")
    for name in (
        "candidate_outputs.csv",
        "candidate_qc.csv",
        "method_output_manifest.csv",
    ):
        (attempt / name).write_text("", encoding="utf-8")

    assert not runner.primary_is_eligible(attempt.parent)


def test_primary_rejects_coordinated_metadata_without_runtime_files(tmp_path: Path) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)

    for path in (attempt / "command.sh", attempt / "stdout.log", attempt / "stderr.log"):
        path.unlink()
    for path in (attempt / "raw").iterdir():
        path.unlink()
    (attempt / "raw").rmdir()
    assert not (attempt / "command.sh").exists()
    assert not (attempt / "stdout.log").exists()
    assert not (attempt / "stderr.log").exists()
    assert not (attempt / "raw").exists()
    assert not runner.primary_is_eligible(attempt.parent)


def test_primary_rejects_symlink_raw_candidate(tmp_path: Path) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    raw = attempt / "raw"
    outside = tmp_path / "pepmlm_generated.csv"
    (raw / "pepmlm_generated.csv").replace(outside)
    (raw / "pepmlm_generated.csv").symlink_to(outside)

    assert not runner.primary_is_eligible(attempt.parent)


def test_primary_rejects_forged_runtime_identity(tmp_path: Path) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    raw = attempt / "raw"
    (raw / "runtime_evidence.json").write_text(
        json.dumps(
            {
                "requested_seed": 42,
                "effective_seed": 42,
                "seed_control_status": "honored",
                "source_commit": "f" * 40,
                "model_revision": "forged",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert not runner.primary_is_eligible(attempt.parent)


def test_primary_rejects_original_file_change_during_snapshot_replay(
    tmp_path: Path, monkeypatch
) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    adapter = runner.load_adapter(job["method"])
    original_parse = adapter.parse

    def mutate_original(job_row, snapshot_attempt):
        (attempt / "raw/pepmlm_generated.csv").write_text("changed\n", encoding="utf-8")
        return original_parse(job_row, snapshot_attempt)

    monkeypatch.setattr(adapter, "parse", mutate_original)

    assert not runner.primary_is_eligible(attempt.parent)


@pytest.mark.parametrize(
    ("artifact", "field", "value"),
    [
        ("method_output_manifest.csv", "source_commit", "f" * 40),
        ("candidate_outputs.csv", "sequence", "FORGED"),
        ("candidate_qc.csv", "file_sha256", "f" * 64),
    ],
)
def test_primary_rejects_csv_swap_between_live_read_and_stable_capture(
    tmp_path: Path,
    monkeypatch,
    artifact: str,
    field: str,
    value: str,
) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    original_capture = runner._capture_attempt_replay_files
    swapped = False

    def swap_then_capture(job_row, attempt_path):
        nonlocal swapped
        if not swapped:
            _rewrite_csv_cell(attempt / artifact, field, value)
            swapped = True
        return original_capture(job_row, attempt_path)

    monkeypatch.setattr(runner, "_capture_attempt_replay_files", swap_then_capture)

    assert not runner.primary_is_eligible(attempt.parent)
    with (attempt / artifact).open(newline="", encoding="utf-8") as handle:
        assert next(csv.DictReader(handle))[field] == value


@pytest.mark.parametrize(
    ("artifact", "field", "value"),
    [
        ("run_result.json", "job_id", "other_job"),
        ("run_result.json", "method", "OtherMethod"),
        ("run_result.json", "attempt_dir", "/outside/attempt_999"),
        ("run_result.json", "design_id", "other_design"),
        ("run_result.json", "exit_code", 1),
        ("run_result.json", "parser_status", "failed"),
        ("run_result.json", "overall_qc_status", "fail"),
        ("method_output_manifest.csv", "job_id", "other_job"),
        ("method_output_manifest.csv", "method", "OtherMethod"),
        ("method_output_manifest.csv", "run_record_id", "other_attempt"),
        ("method_output_manifest.csv", "source_commit", "b" * 40),
        ("method_output_manifest.csv", "model_revision", "forged-model"),
        ("method_output_manifest.csv", "environment_id", "forged/env"),
        ("method_output_manifest.csv", "exit_code", "1"),
        ("method_output_manifest.csv", "parser_status", "failed"),
        ("candidate_outputs.csv", "job_id", "other_job"),
        ("candidate_outputs.csv", "method", "OtherMethod"),
        ("candidate_outputs.csv", "design_id", "other_design"),
        ("candidate_outputs.csv", "target_id", "other_target"),
        ("candidate_outputs.csv", "binder_chain", "B"),
        ("candidate_outputs.csv", "peptide_type", "cyclic"),
        ("candidate_outputs.csv", "chirality", "D"),
        ("candidate_outputs.csv", "cyclic", "yes"),
        ("candidate_outputs.csv", "source_output_id", "forged-output.bin"),
        ("candidate_outputs.csv", "source_output_path", "/outside/candidate.txt"),
        ("candidate_outputs.csv", "structure_path", "/outside/forged.pdb"),
        ("candidate_outputs.csv", "parse_status", "failed"),
        ("candidate_qc.csv", "job_id", "other_job"),
        ("candidate_qc.csv", "design_id", "other_design"),
        ("candidate_qc.csv", "parse_status", "fail"),
        ("candidate_qc.csv", "method_contract_status", "fail"),
        ("candidate_qc.csv", "overall_qc_status", "fail"),
    ],
)
def test_primary_rejects_cross_artifact_passed_evidence_tamper(
    tmp_path: Path, artifact: str, field: str, value: object
) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    assert runner.primary_is_eligible(attempt.parent)

    path = attempt / artifact
    if artifact == "run_result.json":
        result = json.loads(path.read_text(encoding="utf-8"))
        result[field] = value
        path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    else:
        _rewrite_csv_cell(path, field, str(value))

    assert not runner.primary_is_eligible(attempt.parent)


def test_primary_rejects_job_missing_from_authoritative_manifest(tmp_path: Path) -> None:
    runner = load_runner()
    real_job = _primary_contract_job(runner)
    execution = runner.load_execution_matrix()[real_job["job_id"]]
    adapter = runner.load_adapter(real_job["method"])
    fake_job = {**real_job, "job_id": "v034_unregistered_seed42"}
    attempt = tmp_path / "pepmlm" / fake_job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(
        runner,
        attempt,
        fake_job,
        execution=execution,
        adapter=adapter,
    )

    assert not runner.primary_is_eligible(attempt.parent)


@pytest.mark.parametrize("runtime_seconds", ["0", "-1", "nan", "inf", "not-a-number"])
def test_primary_rejects_nonpositive_or_nonfinite_runtime(
    tmp_path: Path, runtime_seconds: str
) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    result = json.loads((attempt / "run_result.json").read_text(encoding="utf-8"))
    result["runtime_seconds"] = runtime_seconds
    (attempt / "run_result.json").write_text(json.dumps(result) + "\n", encoding="utf-8")
    _rewrite_csv_cell(attempt / "method_output_manifest.csv", "runtime_seconds", runtime_seconds)

    assert not runner.primary_is_eligible(attempt.parent)


@pytest.mark.parametrize(
    "created_at",
    ["2026-07-12T00:00:00", "2026-07-12", "not-a-timestamp"],
)
def test_primary_rejects_timestamp_without_valid_timezone(
    tmp_path: Path, created_at: str
) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    result = json.loads((attempt / "run_result.json").read_text(encoding="utf-8"))
    result["created_at"] = created_at
    (attempt / "run_result.json").write_text(json.dumps(result) + "\n", encoding="utf-8")
    _rewrite_csv_cell(attempt / "method_output_manifest.csv", "created_at", created_at)

    assert not runner.primary_is_eligible(attempt.parent)


@pytest.mark.parametrize(
    "artifact",
    ["method_output_manifest.csv", "candidate_outputs.csv", "candidate_qc.csv"],
)
def test_primary_rejects_duplicate_csv_rows(tmp_path: Path, artifact: str) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    _append_duplicate_csv_row(attempt / artifact)

    assert not runner.primary_is_eligible(attempt.parent)


@pytest.mark.parametrize(
    "artifact",
    ["method_output_manifest.csv", "candidate_outputs.csv", "candidate_qc.csv"],
)
def test_primary_rejects_nonexact_csv_headers(tmp_path: Path, artifact: str) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    _append_csv_column(attempt / artifact)

    assert not runner.primary_is_eligible(attempt.parent)


@pytest.mark.parametrize(
    "artifact",
    ["method_output_manifest.csv", "candidate_outputs.csv", "candidate_qc.csv"],
)
def test_primary_rejects_symlink_evidence_file(
    tmp_path: Path, artifact: str
) -> None:
    runner = load_runner()
    job = _primary_contract_job(runner)
    attempt = tmp_path / "pepmlm" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)
    _write_complete_passed_attempt(runner, attempt, job)
    outside = tmp_path / f"outside-{artifact}"
    (attempt / artifact).replace(outside)
    (attempt / artifact).symlink_to(outside)

    assert not runner.primary_is_eligible(attempt.parent)


def test_resume_rejects_symlink_attempt_without_execution(
    tmp_path: Path, monkeypatch
) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)
    outside = tmp_path / "outside-attempt"
    outside.mkdir()
    _write_complete_passed_attempt(runner, outside, job)
    job_root = runner._job_root(tmp_path / "runs", job)
    job_root.mkdir(parents=True)
    (job_root / "attempt_003").symlink_to(outside, target_is_directory=True)

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path / "runs",
        execute=True,
        resume=True,
        retry_failed=False,
    )

    assert results[0]["status"] == "resume_skipped_invalid"
    assert results[0]["status_reason"] == "unsafe_attempt_path"
    assert not (job_root / "attempt_004").exists()


@pytest.mark.parametrize("redirect_component", ["method", "job"])
def test_allocate_rejects_symlink_redirect_outside_run_root(
    tmp_path: Path, redirect_component: str
) -> None:
    runner = load_runner()
    run_root = tmp_path / "runs"
    run_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    method_root = run_root / "pepmlm"
    job_root = method_root / "v034_fake_seed42"
    if redirect_component == "method":
        method_root.symlink_to(outside, target_is_directory=True)
    else:
        method_root.mkdir()
        job_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="unsafe|outside|symlink"):
        runner.allocate_attempt_dir(
            job_root,
            retry_failed=True,
            run_root=run_root,
        )
    assert not (outside / "attempt_001").exists()


def test_job_root_rejects_job_id_path_escape(tmp_path: Path) -> None:
    runner = load_runner()
    job = {**_fake_job(), "job_id": "../../outside"}

    with pytest.raises(ValueError, match="job_id|outside"):
        runner._job_root(tmp_path / "runs", job)


def test_resume_returns_existing_failure_without_implicit_retry(
    tmp_path: Path, monkeypatch
) -> None:
    runner = load_runner()
    job = _configure_single_stage(
        runner,
        monkeypatch,
        method="PepGLAD",
        job_id="v034_pepglad_3eqs_seed42",
    )
    attempt = _write_existing_attempt(
        runner,
        tmp_path,
        job,
        result={
            "status": "parse_failed",
            "status_reason": "pepglad_seed42_replay_mismatch",
            "overall_qc_status": "not_run",
        },
    )

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=True,
        resume=True,
        retry_failed=False,
    )

    assert results == [
        {
            "status": "resume_skipped_failed",
            "status_reason": "pepglad_seed42_replay_mismatch",
            "overall_qc_status": "not_run",
            "job_id": job["job_id"],
            "method": job["method"],
            "attempt_dir": str(attempt),
            "resumed_from_status": "parse_failed",
        }
    ]
    assert sorted(path.name for path in attempt.parent.iterdir()) == ["attempt_003"]
    assert not (attempt.parent / "attempt_004").exists()


@pytest.mark.parametrize("raw_result", ["{not-json\n", "[]\n"])
def test_resume_fails_closed_on_corrupt_existing_result_without_retry(
    tmp_path: Path, monkeypatch, raw_result: str
) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)
    attempt = _write_existing_attempt(
        runner,
        tmp_path,
        job,
        raw_result=raw_result,
    )

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=True,
        resume=True,
        retry_failed=False,
    )

    assert results == [
        {
            "job_id": job["job_id"],
            "method": job["method"],
            "attempt_dir": str(attempt),
            "status": "resume_skipped_invalid",
            "status_reason": "latest_run_result_invalid",
            "overall_qc_status": "not_run",
        }
    ]
    assert sorted(path.name for path in attempt.parent.iterdir()) == ["attempt_003"]


def test_resume_rejects_duplicate_status_keys_without_retry(
    tmp_path: Path, monkeypatch
) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)
    attempt = _write_existing_attempt(
        runner,
        tmp_path,
        job,
        raw_result='{"status":"passed","status":"parse_failed"}\n',
    )

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=True,
        resume=True,
        retry_failed=False,
    )

    assert results[0]["status"] == "resume_skipped_invalid"
    assert results[0]["status_reason"] == "latest_run_result_invalid"
    assert sorted(path.name for path in attempt.parent.iterdir()) == ["attempt_003"]


def test_resume_without_existing_attempt_creates_first_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=False,
        resume=True,
        retry_failed=False,
    )

    assert results[0]["status"] == "packaged"
    assert Path(results[0]["attempt_dir"]).name == "attempt_001"
    assert (runner._job_root(tmp_path, job) / "attempt_001/run_result.json").is_file()


def test_resume_dry_run_reuses_existing_package_idempotently(
    tmp_path: Path, monkeypatch
) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)
    attempt = _write_existing_attempt(
        runner,
        tmp_path,
        job,
        result={
            "status": "packaged",
            "status_reason": "command_packaged_not_executed",
            "overall_qc_status": "not_run",
        },
    )

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=False,
        resume=True,
        retry_failed=False,
    )

    assert results[0]["status"] == "resume_skipped_packaged"
    assert results[0]["resumed_from_status"] == "packaged"
    assert results[0]["attempt_dir"] == str(attempt)
    assert sorted(path.name for path in attempt.parent.iterdir()) == ["attempt_003"]


def test_retry_failed_remains_the_explicit_new_attempt_path(
    tmp_path: Path, monkeypatch
) -> None:
    runner = load_runner()
    job = _configure_single_stage(runner, monkeypatch)
    attempt = _write_existing_attempt(
        runner,
        tmp_path,
        job,
        result={"status": "parse_failed", "overall_qc_status": "not_run"},
    )

    results = runner.run_stage(
        stage="primary",
        run_root=tmp_path,
        execute=False,
        resume=False,
        retry_failed=True,
    )

    assert results[0]["status"] == "packaged"
    assert Path(results[0]["attempt_dir"]).name == "attempt_004"
    assert (attempt.parent / "attempt_003/run_result.json").is_file()
    assert (attempt.parent / "attempt_004/run_result.json").is_file()


@pytest.mark.parametrize(
    ("mode", "status", "expected_exit"),
    [
        ("--execute", "resume_skipped_passed", 0),
        ("--execute", "resume_skipped_failed", 1),
        ("--execute", "resume_skipped_invalid", 1),
        ("--dry-run", "resume_skipped_packaged", 0),
    ],
)
def test_resume_cli_exit_status_matches_existing_attempt_state(
    monkeypatch, capsys, mode: str, status: str, expected_exit: int
) -> None:
    runner = load_runner()
    monkeypatch.setattr(runner, "run_stage", lambda **kwargs: [{"status": status}])
    monkeypatch.setattr(
        sys,
        "argv",
        [str(RUNNER), "--stage", "primary", mode, "--resume"],
    )

    assert runner.main() == expected_exit
    assert json.loads(capsys.readouterr().out)["status_counts"] == {status: 1}


def test_cli_rejects_resume_and_retry_failed_together(monkeypatch) -> None:
    runner = load_runner()
    monkeypatch.setattr(runner, "run_stage", lambda **kwargs: [])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER),
            "--stage",
            "primary",
            "--dry-run",
            "--resume",
            "--retry-failed",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runner.main()
    assert exc_info.value.code == 2


def test_package_job_writes_contract_without_claiming_execution(tmp_path: Path) -> None:
    runner = load_runner()
    execution = {"container_or_env": "fake/env", "max_runtime_sec": "10"}

    result = runner.run_job(
        _fake_job(),
        execution,
        run_root=tmp_path,
        execute=False,
        retry_failed=False,
        adapter=_FakeAdapter,
    )

    attempt = Path(result["attempt_dir"])
    assert result["status"] == "packaged"
    assert (attempt / "job.json").is_file()
    assert (attempt / "execution.json").is_file()
    assert (attempt / "command.json").is_file()
    assert json.loads((attempt / "run_result.json").read_text())["status"] == "packaged"
    assert not (attempt / "stdout.log").exists()


def test_execute_job_writes_logs_candidate_qc_and_manifest(tmp_path: Path, monkeypatch) -> None:
    runner = load_runner()
    execution = {"container_or_env": "fake/env", "max_runtime_sec": "10"}
    monkeypatch.setattr(
        runner,
        "evaluate_candidate_qc",
        lambda job, candidate, runtime, raw: {
            "file_status": "pass",
            "parse_status": "pass",
            "noncanonical_status": "warn",
            "overall_qc_status": "pass_with_warning",
            "status_reason": "noncanonical_status",
        },
    )

    result = runner.run_job(
        _fake_job(),
        execution,
        run_root=tmp_path,
        execute=True,
        retry_failed=False,
        adapter=_FakeAdapter,
    )

    attempt = Path(result["attempt_dir"])
    assert result["status"] == "passed"
    assert result["overall_qc_status"] == "pass_with_warning"
    assert (attempt / "stdout.log").is_file()
    assert (attempt / "stderr.log").is_file()
    assert (attempt / "candidate_outputs.csv").read_text().count("ACX") == 1
    assert "pass_with_warning" in (attempt / "candidate_qc.csv").read_text()
    assert "fake-model" in (attempt / "method_output_manifest.csv").read_text()


def test_run_job_records_timeout_without_parsing(tmp_path: Path, monkeypatch) -> None:
    runner = load_runner()
    execution = {"container_or_env": "fake/env", "max_runtime_sec": "10"}

    def timeout(*args, **kwargs):
        del args, kwargs
        raise runner.BoundedProcessError("timeout", "fake")

    monkeypatch.setattr(runner, "run_bounded_process", timeout)
    result = runner.run_job(
        _fake_job(),
        execution,
        run_root=tmp_path,
        execute=True,
        retry_failed=False,
        adapter=_FakeAdapter,
    )

    attempt = Path(result["attempt_dir"])
    assert result["status"] == "execution_timeout"
    assert json.loads((attempt / "run_result.json").read_text())["status"] == "execution_timeout"
    assert not (attempt / "candidate_outputs.csv").exists()


def test_execute_requires_an_explicit_mode() -> None:
    runner = load_runner()
    with pytest.raises(ValueError, match="exactly one"):
        runner.validate_mode(dry_run=False, execute=False)
    with pytest.raises(ValueError, match="exactly one"):
        runner.validate_mode(dry_run=True, execute=True)
    runner.validate_mode(dry_run=True, execute=False)
    runner.validate_mode(dry_run=False, execute=True)
