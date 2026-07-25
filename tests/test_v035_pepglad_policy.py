from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PEPGLAD_SEED42_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)


def _atom(
    serial: int, atom: str, chain: str, residue: int, x: float, y: float, z: float
) -> str:
    return (
        f"ATOM  {serial:5d} {atom:^4s} ALA {chain}{residue:4d}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {atom[0]:>2s}\n"
    )


def _write_chirality_fixture(path: Path, signs: list[int | None]) -> None:
    lines: list[str] = []
    serial = 1
    for residue, sign in enumerate(signs, start=1):
        origin = float((residue - 1) * 4)
        atoms = {
            "N": (origin + 1.0, 0.0, 0.0),
            "CA": (origin, 0.0, 0.0),
            "C": (origin, 1.0, 0.0),
        }
        if sign is not None:
            atoms["CB"] = (origin, 0.0, float(sign))
        for atom, xyz in atoms.items():
            lines.append(_atom(serial, atom, "B", residue, *xyz))
            serial += 1
    path.write_text("".join(lines) + "END\n", encoding="utf-8")


def _module():
    return importlib.import_module("scripts.v035_adapters.pepglad")


def test_v035_report_only_accepts_mixed_ld_with_warning() -> None:
    observed = _module().evaluate_connectivity_chirality(
        {
            "chain": "B",
            "status": "pass",
            "evaluable": 11,
            "l_count": 4,
            "d_count": 7,
            "gly_count": 0,
            "unknown_count": 0,
        }
    )

    assert observed == {
        "observed_chirality_class": "mixed",
        "chirality_status": "warn",
        "chirality_evaluable": 11,
        "chirality_l_count": 4,
        "chirality_d_count": 7,
        "chirality_unknown_count": 0,
    }


def test_v035_report_only_rejects_unknown_chirality() -> None:
    observed = _module().evaluate_connectivity_chirality(
        {
            "chain": "B",
            "status": "pass",
            "evaluable": 10,
            "l_count": 4,
            "d_count": 6,
            "gly_count": 0,
            "unknown_count": 1,
        }
    )

    assert observed["observed_chirality_class"] == "unknown"
    assert observed["chirality_status"] == "fail"


@pytest.mark.parametrize(
    ("signs", "observed_class", "status", "l_count", "d_count"),
    [
        ([1] * 6 + [-1] * 5, "mixed", "warn", 6, 5),
        ([1] * 11, "L", "pass", 11, 0),
        ([-1] * 11, "D", "pass", 0, 11),
        ([1] * 10 + [None], "unknown", "fail", 10, 0),
    ],
)
def test_v035_report_only_uses_pdb_geometry(
    tmp_path: Path,
    signs: list[int | None],
    observed_class: str,
    status: str,
    l_count: int,
    d_count: int,
) -> None:
    pdb = tmp_path / "candidate.pdb"
    _write_chirality_fixture(pdb, signs)

    observed = _module().evaluate_candidate_chirality(
        pdb, binder_chain="B", expected_length=11
    )

    assert observed["observed_chirality_class"] == observed_class
    assert observed["chirality_status"] == status
    assert observed["chirality_l_count"] == l_count
    assert observed["chirality_d_count"] == d_count


def test_v035_baseline_mismatch_is_a_reproducibility_warning() -> None:
    observed = _module().evaluate_baseline_replay(
        expected_sha256=PEPGLAD_SEED42_BASELINE_SHA256,
        observed_sha256="b" * 64,
        post_relax_sha256="b" * 64,
        file_sha256="b" * 64,
        policy="warn_on_mismatch",
    )

    assert observed == {
        "baseline_expected_sha256": PEPGLAD_SEED42_BASELINE_SHA256,
        "baseline_observed_sha256": "b" * 64,
        "baseline_replay_match": False,
        "baseline_replay_status": "warn",
    }


def test_v035_baseline_warning_does_not_relax_candidate_self_hash() -> None:
    with pytest.raises(ValueError, match="self-hash"):
        _module().evaluate_baseline_replay(
            expected_sha256=PEPGLAD_SEED42_BASELINE_SHA256,
            observed_sha256="b" * 64,
            post_relax_sha256="b" * 64,
            file_sha256="c" * 64,
            policy="warn_on_mismatch",
        )


def test_v035_policy_replays_real_mixed_candidate_without_promoting_v034() -> None:
    attempt = (
        ROOT
        / "benchmark_runs/v0.34/pepglad/v034_pepglad_3eqs_seed42/attempt_003"
    )
    if not attempt.is_dir():
        pytest.skip("external v0.34 PepGLAD diagnostic fixture is not present")
    job = json.loads((attempt / "job.json").read_text(encoding="utf-8"))
    job.update(
        {
            "job_id": "v035_pepglad_3eqs_seed42",
            "chirality_constraint": "unrestricted",
            "chirality_check_mode": "report_only",
            "baseline_replay_policy": "warn_on_mismatch",
        }
    )

    candidate, runtime = _module().parse(job, attempt)
    qc = _module().evaluate_candidate(job, candidate, runtime, attempt / "raw")

    assert candidate["parse_status"] == "parsed"
    assert candidate["sequence"] == "AWHITLLIFTH"
    assert candidate["chirality"] == "mixed"
    assert runtime["baseline_replay_status"] == "mismatch"
    assert qc["observed_chirality_class"] == "mixed"
    assert qc["chirality_l_count"] == 4
    assert qc["chirality_d_count"] == 7
    assert qc["chirality_unknown_count"] == 0
    assert qc["chirality_status"] == "warn"
    assert qc["baseline_replay_status"] == "warn"
    assert qc["overall_qc_status"] == "pass_with_warning"


@pytest.mark.parametrize(
    "field",
    [
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "target_input_sha256",
        "container_image",
        "conda_environment",
        "observer_source_sha256",
        "observer_patch_sha256",
        "seed_wrapper_sha256",
        "source_entrypoint_instrumented_sha256",
    ],
)
def test_v035_runtime_contract_rejects_any_fixed_pin_change(field: str) -> None:
    module = _module()
    runtime = module.expected_runtime_bindings()
    runtime[field] = "tampered"

    with pytest.raises(ValueError, match="pin"):
        module.validate_runtime_bindings(runtime)


@pytest.mark.parametrize(
    ("field", "tampered_value"),
    [
        ("official_candidate_stage", "pre_openmm_snapshot"),
        ("pre_relax_role", "official_candidate"),
        ("binder_chain", "C"),
        ("expected_chirality", "D"),
        (
            "first_observed_chirality_failure_stage",
            "post_openmm_relaxation",
        ),
    ],
)
def test_v035_parse_rejects_runtime_semantic_tamper(
    tmp_path: Path, field: str, tampered_value: str
) -> None:
    from scripts.run_v035_pepglad_connectivity import AUTHORIZED_JOB
    from tests.test_v035_merge import _bundle
    from tests.test_v035_validator import _write_raw_replay_fixture

    attempt, _, _, _, runtime_path = _write_raw_replay_fixture(
        tmp_path, _bundle()
    )
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime[field] = tampered_value
    runtime_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        _module().parse(dict(AUTHORIZED_JOB), attempt)


def test_v035_runtime_loader_rejects_duplicate_and_nonfinite_json(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime_evidence.json"
    runtime.write_text('{"requested_seed":42,"requested_seed":0}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        _module().load_runtime_evidence(runtime)

    runtime.write_text('{"runtime_seconds":NaN}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        _module().load_runtime_evidence(runtime)


def test_v035_attempt_file_rejects_escape_and_symlink(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt_001"
    attempt.mkdir()
    outside = tmp_path / "outside.pdb"
    outside.write_text("outside\n", encoding="utf-8")
    link = attempt / "candidate.pdb"
    link.symlink_to(outside)

    with pytest.raises(ValueError, match="attempt"):
        _module().bound_attempt_file(attempt, "../outside.pdb")
    with pytest.raises(ValueError, match="symlink"):
        _module().bound_attempt_file(attempt, "candidate.pdb")
