from __future__ import annotations

import importlib
import hashlib
import json
from pathlib import Path

import pytest


PEPGLAD_SEED42_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)


def _module():
    return importlib.import_module("scripts.parse_v035_pepglad_connectivity")


def _bundle() -> dict[str, object]:
    historical_names = (
        "pilot_benchmark_job_manifest_v0.34.csv",
        "pilot_execution_matrix_v0.34.csv",
        "pilot_execution_results_v0.34.csv",
        "pilot_method_output_manifest_v0.34.csv",
        "pilot_candidate_outputs_v0.34.csv",
        "pilot_candidate_qc_v0.34.csv",
        "pilot_run_v0.34.csv",
        "pilot_runtime_provenance_v0.34.json",
        "pilot_failure_diagnostics_v0.34.json",
        "pilot_v034_merge_summary.json",
    )
    return {
        "schema_version": "v0.35",
        "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
        "historical_v034_bindings": {
            "primary_supported": 6,
            "pepglad_status": "historical_failure_not_promoted",
            "artifacts": {name: "a" * 64 for name in historical_names},
        },
        "job": {
            "job_id": "v035_pepglad_3eqs_seed42",
            "method": "PepGLAD",
            "random_seed": 42,
            "seed_stage": "primary",
            "target_sha256": "b" * 64,
            "target_chain": "A",
            "binder_chain": "B",
            "length": 11,
            "chirality_constraint": "unrestricted",
            "chirality_check_mode": "report_only",
            "baseline_replay_policy": "warn_on_mismatch",
        },
        "execution": {
            "attempt_id": "attempt_001",
            "attempt_dir": "/tmp/v0.35/pepglad/v035_pepglad_3eqs_seed42/attempt_001",
            "exit_code": 0,
            "status": "passed",
            "supported_candidate": True,
        },
        "candidate": {
            "design_id": "v035_pepglad_3eqs_seed42_candidate_1",
            "sequence": "AWHITLLIFTH",
            "structure_path": "raw/pepglad_candidate.pdb",
            "file_sha256": "c" * 64,
            "binder_chain": "B",
            "parse_status": "parsed",
            "chirality": "mixed",
        },
        "qc": {
            "observed_chirality_class": "mixed",
            "chirality_status": "warn",
            "chirality_evaluable": 11,
            "chirality_l_count": 4,
            "chirality_d_count": 7,
            "chirality_unknown_count": 0,
            "baseline_replay_status": "warn",
            "overall_qc_status": "pass_with_warning",
        },
        "runtime_provenance": {
            "attempt_id": "attempt_001",
            "requested_seed": 42,
            "effective_seed": 42,
            "seed_control_status": "honored",
            "runtime_evidence_path": "raw/runtime_evidence.json",
            "runtime_evidence_sha256": "d" * 64,
            "runtime_semantic_sha256": "e" * 64,
            "baseline_expected_sha256": PEPGLAD_SEED42_BASELINE_SHA256,
            "baseline_observed_sha256": "c" * 64,
            "files": {
                "raw/pepglad_candidate.pdb": "c" * 64,
                "raw/pepglad_pre_relax.pdb": "1" * 64,
                "raw/pepglad_summary.jsonl": "2" * 64,
                "raw/runtime_evidence.json": "d" * 64,
                "work/codesign/3EQS_0.pdb": "c" * 64,
            },
            "producer_bindings": {
                "source_commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
                "source_entrypoint_sha256": "3" * 64,
                "model_weights_sha256": "4" * 64,
                "target_input_sha256": "b" * 64,
                "container_image": "pd-benchmark-methods-gpu:0.21",
                "conda_environment": "bench-pepglad",
                "observer_source_sha256": "5" * 64,
                "observer_patch_sha256": "6" * 64,
                "seed_wrapper_sha256": "7" * 64,
                "source_entrypoint_instrumented_sha256": "8" * 64,
            },
        },
    }


def _write_build_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, tuple[Path, ...]]:
    from scripts import run_v035_pepglad_connectivity as runner
    from tests.test_v035_validator import _write_raw_replay_fixture

    run_root = tmp_path / "runs"
    attempt, *_ = _write_raw_replay_fixture(run_root, _bundle())
    job = runner.load_authorized_job()
    execution = runner.load_authorized_execution()
    run_result = {
        "attempt_dir": str(attempt.resolve()),
        "created_at": "2026-07-14T00:00:00+00:00",
        "design_id": "v035_pepglad_3eqs_seed42_candidate_1",
        "exit_code": 0,
        "job_id": "v035_pepglad_3eqs_seed42",
        "method": "PepGLAD",
        "overall_qc_status": "pass_with_warning",
        "parser_status": "parsed",
        "runtime_seconds": "1.000",
        "status": "passed",
        "status_reason": "bounded_connectivity_candidate_qc_passed",
    }
    for name, value in (
        ("job.json", job),
        ("execution.json", execution),
        ("run_result.json", run_result),
    ):
        (attempt / name).write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    historical_root = tmp_path / "historical"
    historical_root.mkdir()
    historical_paths = tuple(
        historical_root / name
        for name in _bundle()["historical_v034_bindings"]["artifacts"]
    )
    for index, path in enumerate(historical_paths):
        path.write_bytes(f"historical-v0.34-{index}\n".encode("utf-8"))
    return run_root, attempt, historical_paths


def test_v035_bundle_shape_accepts_one_warning_candidate() -> None:
    assert _module().validate_bundle(_bundle()) is None


def test_v035_build_bundle_accepts_exact_replayed_attempt(tmp_path: Path) -> None:
    run_root, _, historical_paths = _write_build_fixture(tmp_path)

    bundle = _module().build_bundle(
        run_root=run_root,
        historical_paths=historical_paths,
    )

    assert bundle["execution"]["supported_candidate"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [("score", 1.0), ("rank", 1), ("fake", "forged")],
    ids=("extra_a", "extra_b", "extra_c"),
)
def test_v035_build_rejects_run_result_extra_field(
    tmp_path: Path, field: str, value: object
) -> None:
    run_root, attempt, historical_paths = _write_build_fixture(tmp_path)
    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result[field] = value
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="run_result"):
        _module().build_bundle(
            run_root=run_root,
            historical_paths=historical_paths,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("overall_qc_status", "pass"),
        ("status_reason", "forged_success"),
    ],
    ids=("binding_a", "binding_b"),
)
def test_v035_build_cross_binds_run_result_to_replay(
    tmp_path: Path, field: str, value: object
) -> None:
    run_root, attempt, historical_paths = _write_build_fixture(tmp_path)
    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result[field] = value
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="run_result|replay|QC"):
        _module().build_bundle(
            run_root=run_root,
            historical_paths=historical_paths,
        )


@pytest.mark.parametrize(
    "relative_attempt",
    [
        "pepglad/v035_pepglad_other_fixture_seed42/attempt_001",
        "pepglad/v035_pepglad_3eqs_seed43/attempt_001",
        "pepmlm/v035_pepmlm_fixture_seed42/attempt_001",
    ],
    ids=("topology_a", "topology_b", "topology_c"),
)
def test_v035_build_rejects_extra_attempt_anywhere_in_run_root(
    tmp_path: Path, relative_attempt: str
) -> None:
    run_root, _, historical_paths = _write_build_fixture(tmp_path)
    (run_root / relative_attempt).mkdir(parents=True)

    with pytest.raises(
        ValueError,
        match="run.root|attempt|authorized|topology|job",
    ):
        _module().build_bundle(
            run_root=run_root,
            historical_paths=historical_paths,
        )


def test_v035_build_allows_runtime_symlink_inside_authorized_attempt(
    tmp_path: Path,
) -> None:
    run_root, attempt, historical_paths = _write_build_fixture(tmp_path)
    checkpoint_dir = attempt / "work/checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "weights.bin").write_bytes(b"fixture weights\n")
    (checkpoint_dir / "codesign.ckpt").symlink_to("weights.bin")

    bundle = _module().build_bundle(
        run_root=run_root,
        historical_paths=historical_paths,
    )

    assert bundle["execution"]["attempt_id"] == "attempt_001"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("score", 1.0),
        ("rank", 1),
        ("scoring", {}),
        ("leaderboard", []),
        ("benchmark_result", True),
        ("seed43", {"status": "not_run"}),
        ("extra", None),
    ],
)
def test_v035_bundle_rejects_scoring_ranking_or_seed43(
    path: str, value: object
) -> None:
    bundle = _bundle()
    bundle[path] = value

    with pytest.raises(ValueError):
        _module().validate_bundle(bundle)


def test_v035_bundle_rejects_empty_historical_or_runtime_provenance() -> None:
    for field in ("historical_v034_bindings", "runtime_provenance"):
        bundle = _bundle()
        bundle[field] = {}
        with pytest.raises(ValueError):
            _module().validate_bundle(bundle)


def test_v035_bundle_rejects_nested_scoring_content() -> None:
    bundle = _bundle()
    bundle["runtime_provenance"]["producer_bindings"]["score"] = 1.0

    with pytest.raises(ValueError):
        _module().validate_bundle(bundle)


@pytest.mark.parametrize(
    "mutation",
    [
        "attempt_id",
        "candidate_file",
        "target_pin",
        "runtime_sha",
        "baseline_pin",
        "second_job",
    ],
)
def test_v035_bundle_rejects_cross_binding_tamper(mutation: str) -> None:
    bundle = _bundle()
    if mutation == "attempt_id":
        bundle["runtime_provenance"]["attempt_id"] = "attempt_002"
    elif mutation == "candidate_file":
        bundle["runtime_provenance"]["files"][
            "raw/pepglad_candidate.pdb"
        ] = "9" * 64
    elif mutation == "target_pin":
        bundle["runtime_provenance"]["producer_bindings"][
            "target_input_sha256"
        ] = "9" * 64
    elif mutation == "runtime_sha":
        bundle["runtime_provenance"]["files"][
            "raw/runtime_evidence.json"
        ] = "9" * 64
    elif mutation == "baseline_pin":
        bundle["runtime_provenance"]["baseline_expected_sha256"] = "9" * 64
    else:
        bundle["jobs"] = [bundle["job"], dict(bundle["job"])]

    with pytest.raises(ValueError):
        _module().validate_bundle(bundle)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_chirality",
        "failed_overall_qc",
        "failed_execution",
        "wrong_effective_seed",
    ],
)
def test_v035_bundle_never_supports_a_failing_candidate(mutation: str) -> None:
    bundle = _bundle()
    if mutation == "unknown_chirality":
        bundle["candidate"]["chirality"] = "unknown"
        bundle["qc"].update(
            observed_chirality_class="unknown",
            chirality_status="fail",
            chirality_evaluable=10,
            chirality_l_count=4,
            chirality_d_count=6,
            chirality_unknown_count=1,
            overall_qc_status="fail",
        )
    elif mutation == "failed_overall_qc":
        bundle["qc"]["overall_qc_status"] = "fail"
    elif mutation == "failed_execution":
        bundle["execution"].update(exit_code=1, status="failed")
    else:
        bundle["runtime_provenance"]["effective_seed"] = 43

    assert bundle["execution"]["supported_candidate"] is True
    with pytest.raises(ValueError):
        _module().validate_bundle(bundle)


@pytest.mark.parametrize(
    "container_path",
    [
        ("historical_v034_bindings",),
        ("historical_v034_bindings", "artifacts"),
        ("job",),
        ("execution",),
        ("candidate",),
        ("qc",),
        ("runtime_provenance",),
        ("runtime_provenance", "files"),
        ("runtime_provenance", "producer_bindings"),
    ],
)
def test_v035_bundle_rejects_any_nested_extra_key(
    container_path: tuple[str, ...],
) -> None:
    bundle = _bundle()
    container = bundle
    for key in container_path:
        container = container[key]
    container["unexpected"] = "tampered"

    with pytest.raises(ValueError):
        _module().validate_bundle(bundle)


@pytest.mark.parametrize(
    ("container_path", "field", "value"),
    [
        (("job",), "job_id", "score_candidate"),
        (("execution",), "status", "ranking_complete"),
        (("candidate",), "design_id", "leaderboard_entry"),
        (("qc",), "overall_qc_status", "benchmark_result"),
        (
            ("runtime_provenance", "producer_bindings"),
            "container_image",
            "best-performing-image",
        ),
    ],
)
def test_v035_bundle_rejects_forbidden_semantics_in_values(
    container_path: tuple[str, ...], field: str, value: str
) -> None:
    bundle = _bundle()
    container = bundle
    for key in container_path:
        container = container[key]
    container[field] = value

    with pytest.raises(ValueError):
        _module().validate_bundle(bundle)


def test_v035_v034_digest_capture_is_read_only(tmp_path: Path) -> None:
    historical_names = tuple(_bundle()["historical_v034_bindings"]["artifacts"])
    paths: list[Path] = []
    before: dict[Path, bytes] = {}
    for index, name in enumerate(historical_names):
        path = tmp_path / name
        path.write_bytes(f"historical-v0.34-{index}\n".encode())
        paths.append(path)
        before[path] = path.read_bytes()

    digests = _module().v034_artifact_digests(paths)

    assert set(digests) == set(historical_names)
    assert digests == {
        path.name: hashlib.sha256(before[path]).hexdigest() for path in paths
    }
    assert {path: path.read_bytes() for path in paths} == before


def test_v035_historical_binding_rejects_stale_sha(tmp_path: Path) -> None:
    names = tuple(_bundle()["historical_v034_bindings"]["artifacts"])
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(name.encode())
        paths.append(path)
    bindings = {
        "primary_supported": 6,
        "pepglad_status": "historical_failure_not_promoted",
        "artifacts": _module().v034_artifact_digests(paths),
    }
    bindings["artifacts"][names[0]] = "0" * 64

    with pytest.raises(ValueError, match="historical"):
        _module().validate_historical_bindings(bindings, paths)


def test_v035_publication_preserves_every_bound_v034_byte(tmp_path: Path) -> None:
    bundle = _bundle()
    names = tuple(bundle["historical_v034_bindings"]["artifacts"])
    historical_paths: list[Path] = []
    for name in names:
        path = tmp_path / "v034" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((f"immutable:{name}\n").encode("utf-8"))
        historical_paths.append(path)
    before = {
        path: (path.stat().st_dev, path.stat().st_ino, path.read_bytes())
        for path in historical_paths
    }
    bundle["historical_v034_bindings"]["artifacts"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in historical_paths
    }
    output = tmp_path / "results/pilot_pepglad_connectivity_v0.35.json"

    _module().publish_bundle(bundle, output_path=output)

    assert json.loads(output.read_text(encoding="utf-8")) == bundle
    assert output.read_bytes().endswith(b"\n")
    assert {
        path: (path.stat().st_dev, path.stat().st_ino, path.read_bytes())
        for path in historical_paths
    } == before
