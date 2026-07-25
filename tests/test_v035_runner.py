from __future__ import annotations

import importlib
import csv
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
JOB_MANIFEST = ROOT / "benchmark/input_sets/pilot_pepglad_job_manifest_v0.35.csv"
EXECUTION_MATRIX = (
    ROOT / "benchmark/deployment/pilot_pepglad_execution_matrix_v0.35.csv"
)
TARGET_SHA256 = "7086cf2bc4723ccbb4be5ff7f86a50d9db59bc307f4fbb0395a3c6ce3569827d"


def _module():
    return importlib.import_module("scripts.run_v035_pepglad_connectivity")


def _one_csv_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    return rows[0]


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_v035_manifest_contains_exactly_one_pepglad_seed42_primary() -> None:
    jobs = _module().load_authorized_jobs()
    assert len(jobs) == 1
    job = jobs[0]

    assert job["job_id"] == "v035_pepglad_3eqs_seed42"
    assert job["method"] == "PepGLAD"
    assert job["random_seed"] == "42"
    assert job["seed_stage"] == "primary"
    assert job["target_pdb_sha256"] == TARGET_SHA256
    assert job["length_min"] == "11"
    assert job["length_max"] == "11"
    assert job["expected_target_chain"] == "A"
    assert job["expected_binder_chain"] == "B"
    assert job["chirality_constraint"] == "unrestricted"
    assert job["chirality_check_mode"] == "report_only"
    assert job["baseline_replay_policy"] == "warn_on_mismatch"
    assert job == _one_csv_row(JOB_MANIFEST)


def test_v035_execution_matrix_contains_exactly_the_authorized_job() -> None:
    execution = _module().load_authorized_execution()

    assert execution["job_id"] == "v035_pepglad_3eqs_seed42"
    assert execution["method"] == "PepGLAD"
    assert execution["random_seed"] == "42"
    assert execution["seed_stage"] == "primary"
    assert execution["target_pdb_sha256"] == TARGET_SHA256
    assert execution["length_min"] == "11"
    assert execution["length_max"] == "11"
    assert execution["expected_target_chain"] == "A"
    assert execution["expected_binder_chain"] == "B"
    assert execution["chirality_constraint"] == "unrestricted"
    assert execution["chirality_check_mode"] == "report_only"
    assert execution["baseline_replay_policy"] == "warn_on_mismatch"
    assert execution == _one_csv_row(EXECUTION_MATRIX)


def test_v035_runner_rejects_retry_failed() -> None:
    with pytest.raises(ValueError, match="retry"):
        _module().validate_execution_request(
            _module().load_authorized_job(), retry_failed=True
        )


def test_v035_runner_rejects_a_second_attempt(tmp_path: Path) -> None:
    job = _module().load_authorized_job()
    attempt = tmp_path / "pepglad" / job["job_id"] / "attempt_001"
    attempt.mkdir(parents=True)

    with pytest.raises(ValueError, match="already recorded"):
        _module().validate_execution_request(
            job,
            retry_failed=False,
            run_root=tmp_path,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("job_id", "v035_unlisted_job"),
        ("method", "PepMLM"),
        ("random_seed", "43"),
        ("seed_stage", "extension"),
        ("target_pdb_sha256", "0" * 64),
        ("length_min", "10"),
        ("length_max", "12"),
        ("expected_target_chain", "C"),
        ("expected_binder_chain", "C"),
        ("chirality_constraint", "L_only"),
        ("chirality_check_mode", "geometry"),
        ("baseline_replay_policy", "require_match"),
    ],
)
def test_v035_runner_rejects_an_unlisted_job(field: str, value: str) -> None:
    job = dict(_module().load_authorized_job())
    job[field] = value

    with pytest.raises(ValueError, match="authorized"):
        _module().validate_execution_request(
            job, retry_failed=False
        )


def test_v035_manifest_rejects_a_second_row(tmp_path: Path) -> None:
    module = _module()
    job = dict(module.load_authorized_job())
    manifest = tmp_path / "jobs.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(job))
        writer.writeheader()
        writer.writerow(job)
        writer.writerow({**job, "random_seed": "43", "seed_stage": "extension"})

    with pytest.raises(ValueError, match="exactly one"):
        module.load_authorized_job(manifest)


def test_v035_execution_matrix_rejects_a_second_row(tmp_path: Path) -> None:
    module = _module()
    execution = dict(module.load_authorized_execution())
    matrix = tmp_path / "execution.csv"
    _write_rows(
        matrix,
        [
            execution,
            {**execution, "random_seed": "43", "seed_stage": "extension"},
        ],
    )

    with pytest.raises(ValueError, match="exactly one"):
        module.load_authorized_execution(matrix)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_pdb_sha256", "0" * 64),
        ("length_min", "10"),
        ("length_max", "12"),
        ("expected_target_chain", "C"),
        ("expected_binder_chain", "C"),
        ("chirality_constraint", "L_only"),
        ("chirality_check_mode", "geometry"),
        ("baseline_replay_policy", "require_match"),
    ],
)
def test_v035_execution_matrix_rejects_critical_field_tamper(
    tmp_path: Path, field: str, value: str
) -> None:
    module = _module()
    execution = dict(module.load_authorized_execution())
    matrix = tmp_path / "execution.csv"
    _write_rows(matrix, [{**execution, field: value}])

    with pytest.raises(ValueError, match="authorized"):
        module.load_authorized_execution(matrix)


def test_v035_manifest_and_matrix_bind_every_authorized_field(
    tmp_path: Path,
) -> None:
    module = _module()
    cases = (
        ("manifest", dict(module.load_authorized_job()), module.load_authorized_job),
        (
            "execution",
            dict(module.load_authorized_execution()),
            module.load_authorized_execution,
        ),
    )
    for label, authorized, loader in cases:
        for field in authorized:
            path = tmp_path / f"{label}-{field}.csv"
            _write_rows(path, [{**authorized, field: "tampered"}])
            with pytest.raises(ValueError, match="authorized"):
                loader(path)
        extra_path = tmp_path / f"{label}-extra.csv"
        _write_rows(extra_path, [{**authorized, "unexpected": "tampered"}])
        with pytest.raises(ValueError, match="authorized"):
            loader(extra_path)

        missing = dict(authorized)
        missing.pop(next(iter(missing)))
        missing_path = tmp_path / f"{label}-missing.csv"
        _write_rows(missing_path, [missing])
        with pytest.raises(ValueError, match="authorized"):
            loader(missing_path)


def test_v035_cli_cannot_bypass_execution_validation(monkeypatch) -> None:
    module = _module()
    calls: list[dict[str, str]] = []

    def validate(job, **_kwargs):
        calls.append(dict(job))

    monkeypatch.setattr(module, "validate_execution_request", validate)
    monkeypatch.setattr(
        module,
        "execute_authorized_job",
        lambda *_args, **_kwargs: {"status": "packaged"},
    )

    assert module.main(["--dry-run"]) == 0
    assert [call["job_id"] for call in calls] == ["v035_pepglad_3eqs_seed42"]


def test_v035_execute_validates_before_running_exactly_one_job(monkeypatch) -> None:
    module = _module()
    calls: list[tuple[str, str]] = []

    def load_execution(*_args, **_kwargs):
        calls.append(("load_execution", "v035_pepglad_3eqs_seed42"))
        return {"job_id": "v035_pepglad_3eqs_seed42"}

    def validate(job, **_kwargs):
        calls.append(("validate", job["job_id"]))

    def execute(job, **_kwargs):
        calls.append(("execute", job["job_id"]))
        return {"status": "packaged"}

    monkeypatch.setattr(module, "load_authorized_execution", load_execution)
    monkeypatch.setattr(module, "validate_execution_request", validate)
    monkeypatch.setattr(module, "execute_authorized_job", execute)

    assert module.main(["--execute"]) == 0
    assert calls == [
        ("load_execution", "v035_pepglad_3eqs_seed42"),
        ("validate", "v035_pepglad_3eqs_seed42"),
        ("execute", "v035_pepglad_3eqs_seed42"),
    ]
