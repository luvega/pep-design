from __future__ import annotations

import importlib
import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts import validate_benchmark_kb as validator


ROOT = Path(__file__).resolve().parents[1]
PEPGLAD_SEED42_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)


AA3 = {
    "A": "ALA",
    "C": "CYS",
    "D": "ASP",
    "E": "GLU",
    "F": "PHE",
    "H": "HIS",
    "I": "ILE",
    "L": "LEU",
    "T": "THR",
    "W": "TRP",
}


def _atom(
    serial: int,
    atom: str,
    residue_name: str,
    chain: str,
    residue: int,
    x: float,
    y: float,
    z: float,
) -> str:
    return (
        f"ATOM  {serial:5d} {atom:^4s} {residue_name:>3s} {chain}{residue:4d}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {atom[0]:>2s}\n"
    )


def _write_complex(
    path: Path,
    *,
    binder_sequence: str = "AWHITLLIFTH",
    target_chain: str = "A",
    binder_chain: str = "B",
    signs: list[int] | None = None,
) -> None:
    signs = signs or ([1] * 4 + [-1] * 7)
    if len(signs) != len(binder_sequence):
        raise ValueError("chirality signs must match binder length")
    target = ROOT / "data/dflow/pdbs/3EQS.pdb"
    target_lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = [
        f"{line[:21]}{target_chain}{line[22:]}"
        for line in target_lines
        if line.startswith(("ATOM  ", "HETATM"))
        and len(line) >= 54
        and (line[21].strip() or "_") == "A"
    ]
    serial = len(lines) + 1
    for residue, (code, sign) in enumerate(zip(binder_sequence, signs), start=1):
        origin = float((residue - 1) * 4 + 100)
        atoms = {
            "N": (origin + 1.0, 0.0, 0.0),
            "CA": (origin, 0.0, 0.0),
            "C": (origin, 1.0, 0.0),
            "CB": (origin, 0.0, float(sign)),
        }
        for atom, xyz in atoms.items():
            lines.append(
                _atom(serial, atom, AA3[code], binder_chain, residue, *xyz)
            )
            serial += 1
    path.write_text("".join(lines) + "END\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_sha256(value: dict[str, object]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _refresh_runtime_bundle(bundle: dict[str, object], runtime_path: Path) -> None:
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    provenance = bundle["runtime_provenance"]
    digest = _sha256(runtime_path)
    provenance["runtime_evidence_sha256"] = digest
    provenance["runtime_semantic_sha256"] = _semantic_sha256(runtime)
    provenance["files"]["raw/runtime_evidence.json"] = digest


def _write_producer_fixture(
    attempt: Path, bindings: dict[str, str]
) -> Path:
    from scripts.v034_adapters import pepglad as v034

    if not v034.SOURCE_ENTRYPOINT.is_file():
        pytest.skip("fixed PepGLAD source checkout is not present")

    instrumenter = attempt / "pepglad_instrument_source.py"
    observer = attempt / "pepglad_observer.py"
    wrapper = attempt / "pepglad_seeded_entry.py"
    instrumenter.write_text(v034.INSTRUMENTER_SCRIPT, encoding="utf-8")
    observer.write_text(v034.OBSERVER_SCRIPT, encoding="utf-8")
    wrapper.write_text(v034.SEED_WRAPPER_SCRIPT, encoding="utf-8")

    anchor = (
        b"def openmm_relax(pdb_path):\n"
        b"    force_field = ForceFieldMinimizer()\n"
    )
    replacement = (
        b"def openmm_relax(pdb_path):\n"
        b"    from pepglad_observer import capture_pre_relax_pdb\n"
        b"    capture_pre_relax_pdb(pdb_path)\n"
        b"    force_field = ForceFieldMinimizer()\n"
    )
    source = v034.SOURCE_ENTRYPOINT.read_bytes()
    assert source.count(anchor) == 1
    instrumented = attempt / "work/api/run.py"
    instrumented.parent.mkdir(parents=True, exist_ok=True)
    instrumented.write_bytes(source.replace(anchor, replacement, 1))

    assert _sha256(instrumenter) == bindings["observer_patch_sha256"]
    assert _sha256(observer) == bindings["observer_source_sha256"]
    assert _sha256(wrapper) == bindings["seed_wrapper_sha256"]
    assert _sha256(instrumented) == bindings[
        "source_entrypoint_instrumented_sha256"
    ]

    evidence = attempt / "observer_patch_evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "observer_injection_status": "applied",
                "observer_patch_path": "pepglad_instrument_source.py",
                "observer_patch_sha256": bindings["observer_patch_sha256"],
                "observer_source_path": "pepglad_observer.py",
                "observer_source_sha256": bindings["observer_source_sha256"],
                "source_entrypoint_path": "work/api/run.py",
                "source_entrypoint_prepatch_sha256": bindings[
                    "source_entrypoint_sha256"
                ],
                "source_entrypoint_instrumented_sha256": bindings[
                    "source_entrypoint_instrumented_sha256"
                ],
                "source_copy_mode": "attempt_local_copy",
                "target_input_path": "/data/input/3EQS.pdb",
                "target_input_sha256": bindings["target_input_sha256"],
                "target_preflight_verified": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return evidence


def _write_attempt_control_files(attempt: Path) -> None:
    from scripts import run_v035_pepglad_connectivity as runner

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
        ("job.json", runner.AUTHORIZED_JOB),
        ("execution.json", runner.AUTHORIZED_EXECUTION),
        ("run_result.json", run_result),
    ):
        (attempt / name).write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )


def _write_raw_replay_fixture(
    root: Path, bundle: dict[str, object]
) -> tuple[Path, Path, Path, Path, Path]:
    adapter = importlib.import_module("scripts.v035_adapters.pepglad")
    bindings = adapter.expected_runtime_bindings()
    attempt = root / "pepglad/v035_pepglad_3eqs_seed42/attempt_001"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    _write_attempt_control_files(attempt)
    candidate = raw / "pepglad_candidate.pdb"
    pre_relax = raw / "pepglad_pre_relax.pdb"
    summary = raw / "pepglad_summary.jsonl"
    runtime_path = raw / "runtime_evidence.json"
    source_candidate = attempt / "work/codesign/3EQS_0.pdb"
    source_candidate.parent.mkdir(parents=True)
    _write_complex(candidate)
    _write_complex(pre_relax, signs=[1] * 6 + [-1] * 5)
    source_candidate.write_bytes(candidate.read_bytes())
    summary.write_text(
        json.dumps(
            {
                "id": "3EQS_0",
                "rec_chains": ["A"],
                "pep_chain": "B",
                "pep_seq": "AWHITLLIFTH",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    candidate_digest = _sha256(candidate)
    pre_digest = _sha256(pre_relax)
    patch_evidence = _write_producer_fixture(attempt, bindings)
    runtime = {
        **bindings,
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "recovery_mode": "instrumented_official_pipeline",
        "source_candidate_path": "work/codesign/3EQS_0.pdb",
        "pre_relax_path": "raw/pepglad_pre_relax.pdb",
        "pre_relax_sha256": pre_digest,
        "post_relax_path": "raw/pepglad_candidate.pdb",
        "post_relax_sha256": candidate_digest,
        "official_candidate_stage": "post_openmm_relaxation",
        "pre_relax_role": "diagnostic_evidence_only",
        "binder_chain": "B",
        "expected_chirality": "L",
        "pre_relax_binder_chirality": {
            "chain": "B",
            "evaluable": 11,
            "l_count": 6,
            "d_count": 5,
            "gly_count": 0,
            "unknown_count": 0,
            "status": "pass",
        },
        "post_relax_binder_chirality": {
            "chain": "B",
            "evaluable": 11,
            "l_count": 4,
            "d_count": 7,
            "gly_count": 0,
            "unknown_count": 0,
            "status": "pass",
        },
        "first_observed_chirality_failure_stage": "pre_openmm_snapshot",
        "baseline_replay_expected_sha256": PEPGLAD_SEED42_BASELINE_SHA256,
        "baseline_replay_observed_sha256": candidate_digest,
        "baseline_replay_status": "mismatch",
        "observer_patch_evidence_path": "observer_patch_evidence.json",
        "observer_patch_evidence_sha256": _sha256(patch_evidence),
        "observer_patch_path": "pepglad_instrument_source.py",
        "observer_source_path": "pepglad_observer.py",
        "seed_wrapper_path": "pepglad_seeded_entry.py",
        "instrumented_source_path": "work/api/run.py",
        "source_entrypoint_prepatch_sha256": bindings[
            "source_entrypoint_sha256"
        ],
        "target_preflight_verified": True,
    }
    runtime_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    bundle["job"]["target_sha256"] = bindings["target_input_sha256"]
    bundle["execution"]["attempt_dir"] = str(attempt)
    bundle["candidate"]["file_sha256"] = candidate_digest
    provenance = bundle["runtime_provenance"]
    provenance["producer_bindings"] = dict(bindings)
    provenance["baseline_expected_sha256"] = PEPGLAD_SEED42_BASELINE_SHA256
    provenance["baseline_observed_sha256"] = candidate_digest
    provenance["files"] = {
        "raw/pepglad_candidate.pdb": candidate_digest,
        "raw/pepglad_pre_relax.pdb": pre_digest,
        "raw/pepglad_summary.jsonl": _sha256(summary),
        "raw/runtime_evidence.json": _sha256(runtime_path),
        "work/codesign/3EQS_0.pdb": _sha256(source_candidate),
    }
    _refresh_runtime_bundle(bundle, runtime_path)
    return attempt, candidate, source_candidate, summary, runtime_path


def _merge_module():
    return importlib.import_module("scripts.parse_v035_pepglad_connectivity")


def _bundle() -> dict[str, object]:
    from tests.test_v035_merge import _bundle as merge_bundle

    return merge_bundle()


def test_v035_validator_treats_expected_scientific_warnings_as_valid(
    monkeypatch,
) -> None:
    errors: list[str] = []
    warnings: list[str] = []
    calls: list[str] = []
    monkeypatch.setattr(
        validator,
        "_v035_raw_replay_valid",
        lambda *_: calls.append("raw") or True,
    )
    monkeypatch.setattr(
        validator,
        "_v035_historical_bindings_valid",
        lambda *_: calls.append("historical") or True,
    )

    validator.validate_v035_pepglad_bundle(
        errors,
        warnings,
        bundle=_bundle(),
    )

    assert errors == []
    assert warnings == []
    assert calls == ["raw", "historical"]


@pytest.mark.parametrize(
    ("raw_valid", "historical_valid", "expected"),
    [
        (False, True, "raw replay"),
        (True, False, "historical"),
    ],
)
def test_v035_validator_independently_rejects_unbound_evidence(
    monkeypatch, raw_valid: bool, historical_valid: bool, expected: str
) -> None:
    errors: list[str] = []
    warnings: list[str] = []
    monkeypatch.setattr(validator, "_v035_raw_replay_valid", lambda *_: raw_valid)
    monkeypatch.setattr(
        validator,
        "_v035_historical_bindings_valid",
        lambda *_: historical_valid,
    )

    validator.validate_v035_pepglad_bundle(
        errors,
        warnings,
        bundle=_bundle(),
    )

    assert any(expected in error for error in errors)
    assert warnings == []


def test_v035_validator_rejects_scoring_content_even_with_valid_replay(
    monkeypatch,
) -> None:
    bundle = _bundle()
    bundle["score"] = 1.0
    errors: list[str] = []
    warnings: list[str] = []
    monkeypatch.setattr(validator, "_v035_raw_replay_valid", lambda *_: True)
    monkeypatch.setattr(
        validator, "_v035_historical_bindings_valid", lambda *_: True
    )

    validator.validate_v035_pepglad_bundle(errors, warnings, bundle=bundle)

    assert any("schema" in error or "scoring" in error for error in errors)
    assert warnings == []


def test_v035_raw_replay_helper_accepts_real_files_then_rejects_tamper(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    _, candidate, _, _, _ = _write_raw_replay_fixture(tmp_path, bundle)

    assert validator._v035_raw_replay_valid(bundle)

    candidate.write_bytes(candidate.read_bytes() + b"REMARK tampered\n")
    assert not validator._v035_raw_replay_valid(bundle)


@pytest.mark.parametrize(
    ("artifact", "mutation"),
    [
        ("job.json", "missing"),
        ("job.json", "extra_field"),
        ("execution.json", "missing"),
        ("execution.json", "extra_field"),
        ("run_result.json", "missing"),
        ("run_result.json", "extra_field"),
    ],
)
def test_v035_raw_replay_requires_exact_attempt_control_artifact_schema(
    tmp_path: Path,
    artifact: str,
    mutation: str,
) -> None:
    bundle = _bundle()
    attempt, *_ = _write_raw_replay_fixture(tmp_path, bundle)
    path = attempt / artifact
    if mutation == "missing":
        path.unlink()
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["unexpected"] = "tampered"
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    assert not validator._v035_raw_replay_valid(bundle)


@pytest.mark.parametrize(
    ("artifact", "field", "value"),
    [
        ("job.json", "job_id", "v035_pepglad_other_fixture_seed42"),
        ("execution.json", "job_id", "v035_pepglad_other_fixture_seed42"),
        ("run_result.json", "overall_qc_status", "pass"),
        ("run_result.json", "status_reason", "forged_success"),
        ("run_result.json", "runtime_seconds", "0.000"),
        ("run_result.json", "created_at", "2026-07-14T00:00:00"),
    ],
)
def test_v035_raw_replay_cross_binds_attempt_controls_to_authorization_and_replay(
    tmp_path: Path,
    artifact: str,
    field: str,
    value: object,
) -> None:
    bundle = _bundle()
    attempt, *_ = _write_raw_replay_fixture(tmp_path, bundle)
    path = attempt / artifact
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    assert not validator._v035_raw_replay_valid(bundle)


@pytest.mark.parametrize(
    "relative_attempt",
    [
        "pepglad/v035_pepglad_3eqs_seed42/attempt_002",
        "pepglad/v035_pepglad_3eqs_seed43/attempt_001",
        "pepglad/v035_pepglad_other_fixture_seed42/attempt_001",
        "pepmlm/v035_pepmlm_fixture_seed42/attempt_001",
    ],
    ids=("retry", "seed43", "other_job", "other_method"),
)
def test_v035_raw_replay_rejects_any_extra_attempt_in_derived_run_root(
    tmp_path: Path,
    relative_attempt: str,
) -> None:
    bundle = _bundle()
    attempt, *_ = _write_raw_replay_fixture(tmp_path, bundle)
    run_root = attempt.parents[2]
    (run_root / relative_attempt).mkdir(parents=True)

    assert not validator._v035_raw_replay_valid(bundle)


def test_v035_raw_replay_allows_runtime_symlink_inside_authorized_attempt(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    attempt, *_ = _write_raw_replay_fixture(tmp_path, bundle)
    checkpoint_dir = attempt / "work/checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "weights.bin").write_bytes(b"fixture weights\n")
    (checkpoint_dir / "codesign.ckpt").symlink_to("weights.bin")

    assert validator._v035_raw_replay_valid(bundle)


@pytest.mark.parametrize("mutation", ["missing", "independent_tamper"])
def test_v035_raw_replay_binds_official_source_candidate(
    tmp_path: Path, mutation: str
) -> None:
    bundle = _bundle()
    _, _, source_candidate, _, _ = _write_raw_replay_fixture(tmp_path, bundle)
    if mutation == "missing":
        source_candidate.unlink()
    else:
        source_candidate.write_bytes(
            source_candidate.read_bytes() + b"REMARK source-only tamper\n"
        )
        bundle["runtime_provenance"]["files"][
            "work/codesign/3EQS_0.pdb"
        ] = _sha256(source_candidate)

    assert not validator._v035_raw_replay_valid(bundle)


def test_v035_historical_binding_helper_rejects_stale_bytes(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    artifact_paths: list[Path] = []
    for name in bundle["historical_v034_bindings"]["artifacts"]:
        path = tmp_path / name
        path.write_bytes((name + "\n").encode("utf-8"))
        artifact_paths.append(path)
    bundle["historical_v034_bindings"]["artifacts"] = {
        path.name: _sha256(path) for path in artifact_paths
    }

    assert validator._v035_historical_bindings_valid(
        bundle, artifact_paths=artifact_paths
    )

    artifact_paths[0].write_bytes(b"changed historical bytes\n")
    assert not validator._v035_historical_bindings_valid(
        bundle, artifact_paths=artifact_paths
    )


@pytest.mark.parametrize("replacement", ["symlink", "different_inode"])
def test_v035_stable_file_rejects_parent_swap_between_check_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    parent = tmp_path / "evidence"
    parent.mkdir()
    target = parent / "payload.json"
    target.write_text('{"status":"valid"}\n', encoding="utf-8")
    moved = tmp_path / "evidence-before-swap"
    real_open = os.open
    swapped = False

    def open_after_parent_swap(path, flags, *args, **kwargs):
        nonlocal swapped
        try:
            opens_target = Path(path).name == target.name
        except TypeError:
            opens_target = False
        if opens_target and not swapped:
            parent.rename(moved)
            if replacement == "symlink":
                parent.symlink_to(moved, target_is_directory=True)
            else:
                parent.mkdir()
                os.link(moved / target.name, parent / target.name)
            swapped = True
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(validator.os, "open", open_after_parent_swap)

    assert validator._v035_stable_file(target, confined_root=tmp_path) is None
    assert swapped is True


@pytest.mark.parametrize("artifact", ["raw_candidate", "source_candidate"])
@pytest.mark.parametrize("change", ["bytes", "identity"])
def test_v035_raw_replay_detects_change_after_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
    change: str,
) -> None:
    bundle = _bundle()
    _, candidate, source_candidate, _, _ = _write_raw_replay_fixture(
        tmp_path, bundle
    )
    live_path = candidate if artifact == "raw_candidate" else source_candidate
    adapter = importlib.import_module("scripts.v035_adapters.pepglad")
    original_parse = adapter.parse
    changed = False

    def parse_then_change(job, snapshot_attempt):
        nonlocal changed
        result = original_parse(job, snapshot_attempt)
        if not changed:
            if change == "bytes":
                live_path.write_bytes(live_path.read_bytes() + b"REMARK changed\n")
            else:
                replacement = live_path.with_name("replacement.pdb")
                replacement.write_bytes(live_path.read_bytes())
                replacement.replace(live_path)
            changed = True
        return result

    monkeypatch.setattr(adapter, "parse", parse_then_change)

    assert not validator._v035_raw_replay_valid(bundle)
    assert changed is True


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "wrong_type",
        "effective_seed",
        "semantic_digest",
        "baseline_pin",
    ],
)
def test_v035_raw_replay_rejects_runtime_contract_tamper(
    tmp_path: Path, mutation: str
) -> None:
    bundle = _bundle()
    _, _, _, _, runtime_path = _write_raw_replay_fixture(tmp_path, bundle)
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if mutation == "extra":
        runtime["unexpected"] = "tampered"
    elif mutation == "wrong_type":
        runtime["requested_seed"] = True
    elif mutation == "effective_seed":
        runtime["effective_seed"] = 43
    elif mutation == "semantic_digest":
        bundle["runtime_provenance"]["runtime_semantic_sha256"] = "0" * 64
    else:
        runtime["baseline_replay_expected_sha256"] = "0" * 64
        bundle["runtime_provenance"]["baseline_expected_sha256"] = "0" * 64
    if mutation != "semantic_digest":
        runtime_path.write_text(
            json.dumps(runtime, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        _refresh_runtime_bundle(bundle, runtime_path)

    assert not validator._v035_raw_replay_valid(bundle)


@pytest.mark.parametrize(
    "mutation",
    [
        "summary_sequence",
        "pdb_sequence",
        "pdb_chain",
        "pdb_length",
        "pdb_target_chain",
        "target_pin",
    ],
)
def test_v035_raw_replay_integrates_summary_structure_and_target_contracts(
    tmp_path: Path, mutation: str
) -> None:
    bundle = _bundle()
    _, candidate, _, summary, runtime_path = _write_raw_replay_fixture(
        tmp_path, bundle
    )
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if mutation == "summary_sequence":
        row = json.loads(summary.read_text(encoding="utf-8"))
        row["pep_seq"] = "A" * 11
        summary.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
        bundle["runtime_provenance"]["files"][
            "raw/pepglad_summary.jsonl"
        ] = _sha256(summary)
    elif mutation == "pdb_sequence":
        _write_complex(candidate, binder_sequence="A" * 11)
    elif mutation == "pdb_chain":
        _write_complex(candidate, binder_chain="C")
    elif mutation == "pdb_length":
        _write_complex(
            candidate,
            binder_sequence="AWHITLLIFT",
            signs=[1] * 4 + [-1] * 6,
        )
    elif mutation == "pdb_target_chain":
        _write_complex(candidate, target_chain="C")
    else:
        runtime["target_input_sha256"] = "0" * 64
        bundle["job"]["target_sha256"] = "0" * 64
        bundle["runtime_provenance"]["producer_bindings"][
            "target_input_sha256"
        ] = "0" * 64

    if mutation.startswith("pdb_"):
        candidate_digest = _sha256(candidate)
        bundle["candidate"]["file_sha256"] = candidate_digest
        bundle["runtime_provenance"]["baseline_observed_sha256"] = candidate_digest
        bundle["runtime_provenance"]["files"][
            "raw/pepglad_candidate.pdb"
        ] = candidate_digest
        runtime["post_relax_sha256"] = candidate_digest
        runtime["baseline_replay_observed_sha256"] = candidate_digest
    if mutation != "summary_sequence":
        runtime_path.write_text(
            json.dumps(runtime, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        _refresh_runtime_bundle(bundle, runtime_path)

    assert not validator._v035_raw_replay_valid(bundle)
