from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from scripts.v034_adapters import pepglad as v034
from scripts.v034_adapters.common import (
    chirality_stats,
    evaluate_candidate_qc,
    overall_qc_status,
    parse_pdb_chain_sequences,
    require_file_sha256,
    sha256_file,
    validate_output_file,
)


ROOT = Path(__file__).resolve().parents[2]
METHOD = v034.METHOD
SOURCE_COMMIT = v034.SOURCE_COMMIT
MODEL_REVISION = v034.MODEL_REVISION
SOURCE_ENTRYPOINT_SHA256 = v034.SOURCE_ENTRYPOINT_SHA256
MODEL_WEIGHTS_SHA256 = v034.MODEL_WEIGHTS_SHA256
DEFAULT_IMAGE = v034.DEFAULT_IMAGE
DEFAULT_ENV = v034.DEFAULT_ENV
OBSERVER_SCRIPT_SHA256 = v034.OBSERVER_SCRIPT_SHA256
INSTRUMENTER_SCRIPT_SHA256 = v034.INSTRUMENTER_SCRIPT_SHA256
SEED_WRAPPER_SCRIPT_SHA256 = v034.SEED_WRAPPER_SCRIPT_SHA256
SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256 = (
    v034.SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256
)
SEED42_POST_RELAX_BASELINE_SHA256 = v034.SEED42_POST_RELAX_BASELINE_SHA256
TARGET_INPUT_SHA256 = (
    "7086cf2bc4723ccbb4be5ff7f86a50d9db59bc307f4fbb0395a3c6ce3569827d"
)

RUNTIME_FIELDS = frozenset(
    {
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "recovery_mode",
        "source_candidate_path",
        "pre_relax_path",
        "pre_relax_sha256",
        "post_relax_path",
        "post_relax_sha256",
        "official_candidate_stage",
        "pre_relax_role",
        "binder_chain",
        "expected_chirality",
        "pre_relax_binder_chirality",
        "post_relax_binder_chirality",
        "first_observed_chirality_failure_stage",
        "baseline_replay_expected_sha256",
        "baseline_replay_observed_sha256",
        "baseline_replay_status",
        "observer_patch_evidence_path",
        "observer_patch_evidence_sha256",
        "observer_patch_path",
        "observer_patch_sha256",
        "observer_source_path",
        "observer_source_sha256",
        "seed_wrapper_path",
        "seed_wrapper_sha256",
        "instrumented_source_path",
        "source_entrypoint_prepatch_sha256",
        "source_entrypoint_instrumented_sha256",
        "target_input_sha256",
        "target_preflight_verified",
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "container_image",
        "conda_environment",
    }
)

PATCH_EVIDENCE_FIELDS = frozenset(
    {
        "observer_injection_status",
        "observer_patch_path",
        "observer_patch_sha256",
        "observer_source_path",
        "observer_source_sha256",
        "source_entrypoint_path",
        "source_entrypoint_prepatch_sha256",
        "source_entrypoint_instrumented_sha256",
        "source_copy_mode",
        "target_input_path",
        "target_input_sha256",
        "target_preflight_verified",
    }
)

CHIRALITY_FIELDS = frozenset(
    {
        "chain",
        "evaluable",
        "l_count",
        "d_count",
        "gly_count",
        "unknown_count",
        "status",
    }
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _strict_json_text(payload: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} JSON must be an object")
    return value


def _is_sha256(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def expected_runtime_bindings() -> dict[str, str]:
    return {
        "source_commit": SOURCE_COMMIT,
        "source_entrypoint_sha256": SOURCE_ENTRYPOINT_SHA256,
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "target_input_sha256": TARGET_INPUT_SHA256,
        "container_image": DEFAULT_IMAGE,
        "conda_environment": DEFAULT_ENV,
        "observer_source_sha256": OBSERVER_SCRIPT_SHA256,
        "observer_patch_sha256": INSTRUMENTER_SCRIPT_SHA256,
        "seed_wrapper_sha256": SEED_WRAPPER_SCRIPT_SHA256,
        "source_entrypoint_instrumented_sha256": (
            SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256
        ),
    }


def validate_runtime_bindings(runtime: Mapping[str, Any]) -> None:
    for field, expected in expected_runtime_bindings().items():
        if runtime.get(field) != expected:
            raise ValueError(
                f"PepGLAD runtime pin mismatch for {field}: expected {expected}"
            )


def _validate_chirality_record(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != CHIRALITY_FIELDS:
        raise ValueError(f"{label} has an invalid chirality schema")
    counts = [
        value.get("evaluable"),
        value.get("l_count"),
        value.get("d_count"),
        value.get("gly_count"),
        value.get("unknown_count"),
    ]
    if any(type(item) is not int or item < 0 for item in counts):
        raise ValueError(f"{label} has invalid chirality counts")
    if value.get("evaluable") != value.get("l_count") + value.get("d_count"):
        raise ValueError(f"{label} has inconsistent chirality counts")
    if value.get("chain") != "B" or value.get("status") not in {"pass", "fail"}:
        raise ValueError(f"{label} has invalid chirality identity")


def _chirality_record_is_all_l(value: Mapping[str, Any]) -> bool:
    return all(
        (
            value.get("status") == "pass",
            type(value.get("evaluable")) is int,
            value.get("evaluable", 0) > 0,
            value.get("l_count") == value.get("evaluable"),
            value.get("d_count") == 0,
            value.get("gly_count") == 0,
            value.get("unknown_count") == 0,
        )
    )


def _validate_runtime_semantics(runtime: Mapping[str, Any]) -> None:
    fixed = {
        "official_candidate_stage": "post_openmm_relaxation",
        "pre_relax_role": "diagnostic_evidence_only",
        "binder_chain": "B",
        "expected_chirality": "L",
    }
    for field, expected in fixed.items():
        if runtime.get(field) != expected:
            raise ValueError(f"PepGLAD runtime semantic mismatch for {field}")

    pre_relax = runtime["pre_relax_binder_chirality"]
    post_relax = runtime["post_relax_binder_chirality"]
    if not _chirality_record_is_all_l(pre_relax):
        expected_failure_stage = "pre_openmm_snapshot"
    elif not _chirality_record_is_all_l(post_relax):
        expected_failure_stage = "post_openmm_relaxation"
    else:
        expected_failure_stage = "none_observed"
    if (
        runtime.get("first_observed_chirality_failure_stage")
        != expected_failure_stage
    ):
        raise ValueError(
            "PepGLAD runtime semantic mismatch for "
            "first_observed_chirality_failure_stage"
        )


def load_runtime_evidence(path: Path) -> dict[str, Any]:
    try:
        payload = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read PepGLAD runtime evidence: {path}") from exc
    runtime = _strict_json_text(payload, "PepGLAD runtime evidence")
    if set(runtime) != RUNTIME_FIELDS:
        raise ValueError("PepGLAD runtime evidence has an invalid exact schema")
    if any(
        type(runtime.get(field)) is not int
        for field in ("requested_seed", "effective_seed")
    ):
        raise ValueError("PepGLAD runtime seed fields must be integers")
    if type(runtime.get("target_preflight_verified")) is not bool:
        raise ValueError("PepGLAD runtime target preflight field must be boolean")
    string_fields = RUNTIME_FIELDS - {
        "requested_seed",
        "effective_seed",
        "target_preflight_verified",
        "pre_relax_binder_chirality",
        "post_relax_binder_chirality",
    }
    if any(type(runtime.get(field)) is not str for field in string_fields):
        raise ValueError("PepGLAD runtime string fields have invalid types")
    _validate_chirality_record(
        runtime["pre_relax_binder_chirality"], "pre-relax evidence"
    )
    _validate_chirality_record(
        runtime["post_relax_binder_chirality"], "post-relax evidence"
    )
    _validate_runtime_semantics(runtime)
    validate_runtime_bindings(runtime)
    return runtime


def bound_attempt_file(attempt_dir: Path, relative_path: str) -> Path:
    attempt = Path(attempt_dir)
    relative = PurePosixPath(relative_path)
    if (
        not relative_path
        or "\\" in relative_path
        or relative.is_absolute()
        or relative.as_posix() != relative_path
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(f"path must stay inside the PepGLAD attempt: {relative_path}")
    if attempt.is_symlink():
        raise ValueError(f"PepGLAD attempt cannot be a symlink: {attempt}")
    if not attempt.is_dir():
        raise ValueError(f"invalid PepGLAD attempt directory: {attempt}")
    root = attempt.resolve(strict=True)
    current = attempt
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink is not allowed inside the PepGLAD attempt: {current}")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"path must stay inside the PepGLAD attempt: {relative_path}") from exc
    if not current.is_file() or current.stat().st_size <= 0:
        raise ValueError(f"missing regular PepGLAD attempt file: {relative_path}")
    return current


def _job_target(job: Mapping[str, str]) -> Path:
    target = Path(job.get("target_pdb_path", ""))
    if not target.is_absolute():
        target = ROOT / target
    require_file_sha256(target, TARGET_INPUT_SHA256, "PepGLAD v0.35 target input")
    return target


def _validate_job_policy(job: Mapping[str, str]) -> None:
    expected = {
        "job_id": "v035_pepglad_3eqs_seed42",
        "method": METHOD,
        "random_seed": "42",
        "seed_stage": "primary",
        "length_min": "11",
        "length_max": "11",
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
        "target_pdb_sha256": TARGET_INPUT_SHA256,
        "target_binding_check_mode": "sequence_and_sha256",
        "chirality_constraint": "unrestricted",
        "chirality_check_mode": "report_only",
        "baseline_replay_policy": "warn_on_mismatch",
    }
    for field, value in expected.items():
        if job.get(field) != value:
            raise ValueError(f"PepGLAD v0.35 job policy mismatch for {field}")


def evaluate_connectivity_chirality(stats: Mapping[str, Any]) -> dict[str, Any]:
    values = {
        key: stats.get(key)
        for key in ("evaluable", "l_count", "d_count", "unknown_count")
    }
    if any(type(value) is not int or value < 0 for value in values.values()):
        observed_class = "unknown"
        status = "fail"
    else:
        evaluable = values["evaluable"]
        l_count = values["l_count"]
        d_count = values["d_count"]
        unknown = values["unknown_count"]
        fully_evaluable = all(
            (
                stats.get("status") == "pass",
                evaluable > 0,
                unknown == 0,
                l_count + d_count == evaluable,
                stats.get("gly_count", 0) == 0,
            )
        )
        if not fully_evaluable:
            observed_class, status = "unknown", "fail"
        elif l_count and d_count:
            observed_class, status = "mixed", "warn"
        elif l_count == evaluable:
            observed_class, status = "L", "pass"
        elif d_count == evaluable:
            observed_class, status = "D", "pass"
        else:
            observed_class, status = "unknown", "fail"
    return {
        "observed_chirality_class": observed_class,
        "chirality_status": status,
        "chirality_evaluable": values.get("evaluable", 0),
        "chirality_l_count": values.get("l_count", 0),
        "chirality_d_count": values.get("d_count", 0),
        "chirality_unknown_count": values.get("unknown_count", 0),
    }


def evaluate_candidate_chirality(
    path: Path, *, binder_chain: str, expected_length: int
) -> dict[str, Any]:
    stats = chirality_stats(Path(path), binder_chain)
    if (
        stats.get("evaluable") != expected_length
        or stats.get("unknown_count") != 0
        or stats.get("gly_count") != 0
    ):
        stats = {**stats, "status": "fail"}
    return evaluate_connectivity_chirality(stats)


def evaluate_baseline_replay(
    *,
    expected_sha256: str,
    observed_sha256: str,
    post_relax_sha256: str,
    file_sha256: str,
    policy: str,
) -> dict[str, Any]:
    if expected_sha256 != SEED42_POST_RELAX_BASELINE_SHA256:
        raise ValueError("PepGLAD seed42 baseline pin mismatch")
    if policy != "warn_on_mismatch":
        raise ValueError("PepGLAD v0.35 baseline replay policy mismatch")
    if not all(
        _is_sha256(value)
        for value in (
            expected_sha256,
            observed_sha256,
            post_relax_sha256,
            file_sha256,
        )
    ):
        raise ValueError("PepGLAD baseline replay contains an invalid SHA256")
    if observed_sha256 != post_relax_sha256 or post_relax_sha256 != file_sha256:
        raise ValueError("PepGLAD candidate self-hash mismatch")
    matched = observed_sha256 == expected_sha256
    return {
        "baseline_expected_sha256": expected_sha256,
        "baseline_observed_sha256": observed_sha256,
        "baseline_replay_match": matched,
        "baseline_replay_status": "pass" if matched else "warn",
    }


def _strict_summary(path: Path) -> dict[str, Any]:
    try:
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError) as exc:
        raise ValueError("cannot read PepGLAD summary") from exc
    if len(lines) != 1:
        raise ValueError("PepGLAD summary must contain exactly one row")
    value = _strict_json_text(lines[0], "PepGLAD summary")
    if set(value) != {"id", "rec_chains", "pep_chain", "pep_seq"}:
        raise ValueError("PepGLAD summary has an invalid exact schema")
    return value


def _validate_actual_producer_files(
    attempt: Path, runtime: Mapping[str, Any], target: Path
) -> None:
    expected_files = {
        "observer_patch_path": INSTRUMENTER_SCRIPT_SHA256,
        "observer_source_path": OBSERVER_SCRIPT_SHA256,
        "seed_wrapper_path": SEED_WRAPPER_SCRIPT_SHA256,
        "instrumented_source_path": SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256,
    }
    for path_field, digest in expected_files.items():
        observed = bound_attempt_file(attempt, str(runtime[path_field]))
        if sha256_file(observed) != digest:
            raise ValueError(f"PepGLAD producer pin mismatch for {path_field}")

    evidence = bound_attempt_file(
        attempt, str(runtime["observer_patch_evidence_path"])
    )
    if sha256_file(evidence) != runtime["observer_patch_evidence_sha256"]:
        raise ValueError("PepGLAD observer evidence self-hash mismatch")
    patch = _strict_json_text(
        evidence.read_text(encoding="utf-8"), "PepGLAD observer evidence"
    )
    if set(patch) != PATCH_EVIDENCE_FIELDS:
        raise ValueError("PepGLAD observer evidence has an invalid exact schema")
    expected_patch = {
        "observer_injection_status": "applied",
        "observer_patch_path": runtime["observer_patch_path"],
        "observer_patch_sha256": INSTRUMENTER_SCRIPT_SHA256,
        "observer_source_path": runtime["observer_source_path"],
        "observer_source_sha256": OBSERVER_SCRIPT_SHA256,
        "source_entrypoint_path": runtime["instrumented_source_path"],
        "source_entrypoint_prepatch_sha256": SOURCE_ENTRYPOINT_SHA256,
        "source_entrypoint_instrumented_sha256": (
            SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256
        ),
        "source_copy_mode": "attempt_local_copy",
        "target_input_path": "/data/input/3EQS.pdb",
        "target_input_sha256": TARGET_INPUT_SHA256,
        "target_preflight_verified": True,
    }
    if patch != expected_patch or sha256_file(target) != TARGET_INPUT_SHA256:
        raise ValueError("PepGLAD observer evidence pin mismatch")


def prepare(
    job: Mapping[str, str], execution: Mapping[str, str], attempt_dir: Path
) -> list[str]:
    _validate_job_policy(job)
    return v034.prepare(job, execution, attempt_dir)


def parse(
    job: Mapping[str, str], attempt_dir: Path
) -> tuple[dict[str, str], dict[str, Any]]:
    _validate_job_policy(job)
    attempt = Path(attempt_dir)
    raw = attempt / "raw"
    runtime_path = bound_attempt_file(attempt, "raw/runtime_evidence.json")
    runtime = load_runtime_evidence(runtime_path)
    if not all(
        (
            runtime["requested_seed"] == 42,
            runtime["effective_seed"] == 42,
            runtime["seed_control_status"] == "honored",
            runtime["recovery_mode"] == v034.RECOVERY_MODE,
            runtime["target_preflight_verified"] is True,
            runtime["source_entrypoint_prepatch_sha256"]
            == SOURCE_ENTRYPOINT_SHA256,
        )
    ):
        raise ValueError("PepGLAD v0.35 runtime identity mismatch")

    expected_paths = {
        "source_candidate_path": "work/codesign/3EQS_0.pdb",
        "pre_relax_path": "raw/pepglad_pre_relax.pdb",
        "post_relax_path": "raw/pepglad_candidate.pdb",
        "observer_patch_evidence_path": "observer_patch_evidence.json",
        "observer_patch_path": "pepglad_instrument_source.py",
        "observer_source_path": "pepglad_observer.py",
        "seed_wrapper_path": "pepglad_seeded_entry.py",
        "instrumented_source_path": "work/api/run.py",
    }
    if any(runtime.get(field) != value for field, value in expected_paths.items()):
        raise ValueError("PepGLAD runtime attempt path binding mismatch")

    output = bound_attempt_file(attempt, "raw/pepglad_candidate.pdb")
    source = bound_attempt_file(attempt, "work/codesign/3EQS_0.pdb")
    pre_relax = bound_attempt_file(attempt, "raw/pepglad_pre_relax.pdb")
    summary_path = bound_attempt_file(attempt, "raw/pepglad_summary.jsonl")
    for path, label in (
        (output, "candidate"),
        (source, "official source candidate"),
        (pre_relax, "pre-relax candidate"),
    ):
        validation = validate_output_file(path, raw if path.parent == raw else attempt)
        if validation["status"] != "pass":
            raise ValueError(f"PepGLAD {label} is invalid")

    candidate_digest = sha256_file(output)
    if sha256_file(source) != candidate_digest:
        raise ValueError("PepGLAD official source and raw candidate differ")
    if runtime["post_relax_sha256"] != candidate_digest:
        raise ValueError("PepGLAD runtime post-relax self-hash mismatch")
    if runtime["pre_relax_sha256"] != sha256_file(pre_relax):
        raise ValueError("PepGLAD runtime pre-relax self-hash mismatch")

    replay = evaluate_baseline_replay(
        expected_sha256=runtime["baseline_replay_expected_sha256"],
        observed_sha256=runtime["baseline_replay_observed_sha256"],
        post_relax_sha256=runtime["post_relax_sha256"],
        file_sha256=candidate_digest,
        policy=job["baseline_replay_policy"],
    )
    expected_runtime_replay = "match" if replay["baseline_replay_match"] else "mismatch"
    if runtime["baseline_replay_status"] != expected_runtime_replay:
        raise ValueError("PepGLAD runtime baseline replay state mismatch")

    target = _job_target(job)
    _validate_actual_producer_files(attempt, runtime, target)
    summary = _strict_summary(summary_path)
    output_sequences = parse_pdb_chain_sequences(output)
    target_sequences = parse_pdb_chain_sequences(target)
    sequence = str(summary.get("pep_seq", "")).strip().upper()
    if not all(
        (
            summary.get("id") == "3EQS_0",
            summary.get("rec_chains") == ["A"],
            summary.get("pep_chain") == "B",
            set(output_sequences) == {"A", "B"},
            output_sequences.get("A") == target_sequences.get("A"),
            output_sequences.get("B") == sequence,
            len(sequence) == 11,
        )
    ):
        raise ValueError("PepGLAD summary, sequence, chain, length, or target mismatch")

    pre_stats = {"chain": "B", **chirality_stats(pre_relax, "B")}
    post_stats = {"chain": "B", **chirality_stats(output, "B")}
    if runtime["pre_relax_binder_chirality"] != pre_stats:
        raise ValueError("PepGLAD pre-relax chirality evidence mismatch")
    if runtime["post_relax_binder_chirality"] != post_stats:
        raise ValueError("PepGLAD post-relax chirality evidence mismatch")
    observed = evaluate_candidate_chirality(
        output, binder_chain="B", expected_length=11
    )
    reason = (
        "pepglad_standard_output_parsed_with_replay_warning"
        if replay["baseline_replay_status"] == "warn"
        else "pepglad_standard_output_parsed"
    )
    return (
        {
            "sequence": sequence,
            "structure_path": str(output),
            "source_output_path": str(output),
            "binder_chain": "B",
            "chirality": str(observed["observed_chirality_class"]),
            "parse_status": "parsed",
            "status_reason": reason,
        },
        runtime,
    )


def evaluate_candidate(
    job: Mapping[str, str],
    candidate: Mapping[str, str],
    runtime: Mapping[str, Any],
    raw_root: Path,
) -> dict[str, Any]:
    _validate_job_policy(job)
    if set(runtime) != RUNTIME_FIELDS:
        raise ValueError("PepGLAD runtime evidence has an invalid exact schema")
    _validate_runtime_semantics(runtime)
    validate_runtime_bindings(runtime)
    structure = Path(candidate.get("structure_path", ""))
    validation = validate_output_file(structure, Path(raw_root))
    if validation["status"] != "pass":
        raise ValueError("PepGLAD candidate is not a bound regular raw file")
    observed = evaluate_candidate_chirality(
        structure, binder_chain="B", expected_length=11
    )
    if candidate.get("chirality") != observed["observed_chirality_class"]:
        raise ValueError("PepGLAD candidate chirality class mismatch")
    replay = evaluate_baseline_replay(
        expected_sha256=str(runtime["baseline_replay_expected_sha256"]),
        observed_sha256=str(runtime["baseline_replay_observed_sha256"]),
        post_relax_sha256=str(runtime["post_relax_sha256"]),
        file_sha256=str(validation["sha256"]),
        policy=job["baseline_replay_policy"],
    )
    base_job = {**job, "chirality_check_mode": "not_applicable"}
    checks = evaluate_candidate_qc(base_job, candidate, runtime, Path(raw_root))
    checks.update(observed)
    checks["baseline_replay_status"] = replay["baseline_replay_status"]
    checks["overall_qc_status"] = overall_qc_status(checks)
    failed = sorted(
        key
        for key, value in checks.items()
        if key.endswith("_status")
        and key != "overall_qc_status"
        and value == "fail"
    )
    warned = sorted(
        key
        for key, value in checks.items()
        if key.endswith("_status")
        and key != "overall_qc_status"
        and value == "warn"
    )
    checks["status_reason"] = ";".join(failed or warned) or "all_required_checks_passed"
    return checks
