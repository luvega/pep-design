#!/usr/bin/env python3
"""Replay and publish the single authorized v0.35 PepGLAD evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCHEMA_VERSION = "v0.35"
EVIDENCE_BOUNDARY = "bounded_connectivity_only_not_scoring_or_ranking"
JOB_ID = "v035_pepglad_3eqs_seed42"
DESIGN_ID = f"{JOB_ID}_candidate_1"
ATTEMPT_ID = "attempt_001"
PEPGLAD_SEED42_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)

DEFAULT_JOB_MANIFEST = (
    ROOT / "benchmark/input_sets/pilot_pepglad_job_manifest_v0.35.csv"
)
DEFAULT_EXECUTION_MATRIX = (
    ROOT / "benchmark/deployment/pilot_pepglad_execution_matrix_v0.35.csv"
)
DEFAULT_RUN_ROOT = ROOT / "benchmark_runs/v0.35"
DEFAULT_OUTPUT = (
    ROOT / "benchmark/results/pilot_pepglad_connectivity_v0.35.json"
)

HISTORICAL_ARTIFACT_NAMES = frozenset(
    {
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
    }
)

DEFAULT_HISTORICAL_ARTIFACTS = (
    ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv",
    ROOT / "benchmark/deployment/pilot_execution_matrix_v0.34.csv",
    ROOT / "benchmark/deployment/pilot_execution_results_v0.34.csv",
    ROOT / "benchmark/results/pilot_method_output_manifest_v0.34.csv",
    ROOT / "benchmark/results/pilot_candidate_outputs_v0.34.csv",
    ROOT / "benchmark/results/pilot_candidate_qc_v0.34.csv",
    ROOT / "benchmark/results/pilot_run_v0.34.csv",
    ROOT / "benchmark/results/pilot_runtime_provenance_v0.34.json",
    ROOT / "benchmark/results/pilot_failure_diagnostics_v0.34.json",
    ROOT / "benchmark/results/pilot_v034_merge_summary.json",
)

PUBLIC_ATTEMPT_FILES = (
    "raw/pepglad_candidate.pdb",
    "raw/pepglad_pre_relax.pdb",
    "raw/pepglad_summary.jsonl",
    "raw/runtime_evidence.json",
    "work/codesign/3EQS_0.pdb",
)

# These additional files are required by the adapter's producer-pin replay.
ATTEMPT_REPLAY_FILES = (
    "job.json",
    "execution.json",
    "run_result.json",
    *PUBLIC_ATTEMPT_FILES,
    "observer_patch_evidence.json",
    "pepglad_instrument_source.py",
    "pepglad_observer.py",
    "pepglad_seeded_entry.py",
    "work/api/run.py",
)

TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_boundary",
        "historical_v034_bindings",
        "job",
        "execution",
        "candidate",
        "qc",
        "runtime_provenance",
    }
)
HISTORICAL_FIELDS = frozenset(
    {"primary_supported", "pepglad_status", "artifacts"}
)
JOB_FIELDS = frozenset(
    {
        "job_id",
        "method",
        "random_seed",
        "seed_stage",
        "target_sha256",
        "target_chain",
        "binder_chain",
        "length",
        "chirality_constraint",
        "chirality_check_mode",
        "baseline_replay_policy",
    }
)
EXECUTION_FIELDS = frozenset(
    {"attempt_id", "attempt_dir", "exit_code", "status", "supported_candidate"}
)
CANDIDATE_FIELDS = frozenset(
    {
        "design_id",
        "sequence",
        "structure_path",
        "file_sha256",
        "binder_chain",
        "parse_status",
        "chirality",
    }
)
QC_FIELDS = frozenset(
    {
        "observed_chirality_class",
        "chirality_status",
        "chirality_evaluable",
        "chirality_l_count",
        "chirality_d_count",
        "chirality_unknown_count",
        "baseline_replay_status",
        "overall_qc_status",
    }
)
RUNTIME_FIELDS = frozenset(
    {
        "attempt_id",
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "runtime_evidence_path",
        "runtime_evidence_sha256",
        "runtime_semantic_sha256",
        "baseline_expected_sha256",
        "baseline_observed_sha256",
        "files",
        "producer_bindings",
    }
)
PRODUCER_FIELDS = frozenset(
    {
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
    }
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
_SEQUENCE_RE = re.compile(r"[A-Z]{11}\Z")
_FORBIDDEN_RE = re.compile(
    r"(?<![a-z0-9])(?:score|scoring|rank|ranking|leaderboard|"
    r"benchmark[_ -]?result|seed[_ -]?43|best[_ -]?performing)(?![a-z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CapturedFile:
    path: Path
    payload: bytes
    sha256: str
    identity: tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class AttemptCapture:
    attempt_dir: Path
    files: Mapping[str, CapturedFile]


@dataclass(frozen=True)
class ReplayResult:
    candidate: Mapping[str, Any]
    runtime: Mapping[str, Any]
    qc: Mapping[str, Any]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _strict_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    if type(value) is not dict:
        raise ValueError(f"{label} JSON must be an object")
    return value


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        payload = json.dumps(
            dict(value),
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("bundle is not canonical JSON data") from exc
    return (payload + "\n").encode("utf-8")


def _semantic_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        dict(value),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _exact_object(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"{label} has an invalid exact schema")
    return value


def _reject_forbidden_semantics(value: Any, path: tuple[str, ...] = ()) -> None:
    if type(value) is dict:
        for key, item in value.items():
            if _FORBIDDEN_RE.search(key):
                raise ValueError(f"forbidden result semantics at {'.'.join(path + (key,))}")
            _reject_forbidden_semantics(item, path + (key,))
    elif type(value) is list:
        for index, item in enumerate(value):
            _reject_forbidden_semantics(item, path + (str(index),))
    elif type(value) is str:
        if path == ("evidence_boundary",) and value == EVIDENCE_BOUNDARY:
            return
        if _FORBIDDEN_RE.search(value):
            raise ValueError(f"forbidden result semantics at {'.'.join(path)}")


def validate_bundle(bundle: Mapping[str, Any]) -> None:
    """Validate the exact one-candidate bounded-connectivity bundle schema."""

    root = _exact_object(bundle, TOP_LEVEL_FIELDS, "v0.35 bundle")
    if root["schema_version"] != SCHEMA_VERSION:
        raise ValueError("v0.35 bundle schema version mismatch")
    if root["evidence_boundary"] != EVIDENCE_BOUNDARY:
        raise ValueError("v0.35 evidence boundary mismatch")
    _reject_forbidden_semantics(root)

    historical = _exact_object(
        root["historical_v034_bindings"], HISTORICAL_FIELDS, "historical bindings"
    )
    if (
        historical["primary_supported"] != 6
        or type(historical["primary_supported"]) is not int
        or historical["pepglad_status"] != "historical_failure_not_promoted"
    ):
        raise ValueError("historical v0.34 status mismatch")
    artifacts = _exact_object(
        historical["artifacts"], HISTORICAL_ARTIFACT_NAMES, "historical artifacts"
    )
    if not all(_is_sha256(value) for value in artifacts.values()):
        raise ValueError("historical artifact digest is invalid")

    job = _exact_object(root["job"], JOB_FIELDS, "job")
    fixed_job = {
        "job_id": JOB_ID,
        "method": "PepGLAD",
        "random_seed": 42,
        "seed_stage": "primary",
        "target_chain": "A",
        "binder_chain": "B",
        "length": 11,
        "chirality_constraint": "unrestricted",
        "chirality_check_mode": "report_only",
        "baseline_replay_policy": "warn_on_mismatch",
    }
    if any(job.get(field) != expected for field, expected in fixed_job.items()):
        raise ValueError("v0.35 job identity or policy mismatch")
    if type(job["random_seed"]) is not int or type(job["length"]) is not int:
        raise ValueError("v0.35 job numeric fields must be integers")
    if not _is_sha256(job["target_sha256"]):
        raise ValueError("v0.35 target digest is invalid")

    execution = _exact_object(root["execution"], EXECUTION_FIELDS, "execution")
    attempt_dir = execution.get("attempt_dir")
    if (
        execution.get("attempt_id") != ATTEMPT_ID
        or type(attempt_dir) is not str
        or not Path(attempt_dir).is_absolute()
        or Path(attempt_dir).name != ATTEMPT_ID
        or Path(attempt_dir).parent.name != JOB_ID
        or Path(attempt_dir).parent.parent.name != "pepglad"
        or type(execution.get("exit_code")) is not int
        or execution.get("exit_code") != 0
        or execution.get("status") != "passed"
        or type(execution.get("supported_candidate")) is not bool
        or execution.get("supported_candidate") is not True
    ):
        raise ValueError("v0.35 execution is not a supported single attempt")

    candidate = _exact_object(root["candidate"], CANDIDATE_FIELDS, "candidate")
    if (
        candidate.get("design_id") != DESIGN_ID
        or type(candidate.get("sequence")) is not str
        or _SEQUENCE_RE.fullmatch(candidate["sequence"]) is None
        or candidate.get("structure_path") != "raw/pepglad_candidate.pdb"
        or not _is_sha256(candidate.get("file_sha256"))
        or candidate.get("binder_chain") != "B"
        or candidate.get("parse_status") != "parsed"
        or candidate.get("chirality") not in {"L", "D", "mixed"}
    ):
        raise ValueError("v0.35 candidate contract mismatch")

    qc = _exact_object(root["qc"], QC_FIELDS, "candidate QC")
    count_fields = (
        "chirality_evaluable",
        "chirality_l_count",
        "chirality_d_count",
        "chirality_unknown_count",
    )
    if any(type(qc.get(field)) is not int or qc[field] < 0 for field in count_fields):
        raise ValueError("v0.35 chirality counts are invalid")
    if (
        qc["chirality_evaluable"] != 11
        or qc["chirality_l_count"] + qc["chirality_d_count"] != 11
        or qc["chirality_unknown_count"] != 0
        or qc["observed_chirality_class"] != candidate["chirality"]
    ):
        raise ValueError("v0.35 chirality evidence is incomplete")
    chirality_class = qc["observed_chirality_class"]
    expected_chirality_status = "warn" if chirality_class == "mixed" else "pass"
    class_counts_valid = (
        chirality_class == "mixed"
        and qc["chirality_l_count"] > 0
        and qc["chirality_d_count"] > 0
    ) or (
        chirality_class == "L"
        and qc["chirality_l_count"] == 11
        and qc["chirality_d_count"] == 0
    ) or (
        chirality_class == "D"
        and qc["chirality_l_count"] == 0
        and qc["chirality_d_count"] == 11
    )
    if not class_counts_valid or qc["chirality_status"] != expected_chirality_status:
        raise ValueError("v0.35 chirality class is inconsistent")

    runtime = _exact_object(
        root["runtime_provenance"], RUNTIME_FIELDS, "runtime provenance"
    )
    files = _exact_object(
        runtime["files"], frozenset(PUBLIC_ATTEMPT_FILES), "runtime files"
    )
    producer = _exact_object(
        runtime["producer_bindings"], PRODUCER_FIELDS, "producer bindings"
    )
    if (
        runtime.get("attempt_id") != execution["attempt_id"]
        or type(runtime.get("requested_seed")) is not int
        or runtime.get("requested_seed") != 42
        or type(runtime.get("effective_seed")) is not int
        or runtime.get("effective_seed") != 42
        or runtime.get("seed_control_status") != "honored"
        or runtime.get("runtime_evidence_path") != "raw/runtime_evidence.json"
        or not _is_sha256(runtime.get("runtime_evidence_sha256"))
        or not _is_sha256(runtime.get("runtime_semantic_sha256"))
        or runtime.get("baseline_expected_sha256")
        != PEPGLAD_SEED42_BASELINE_SHA256
        or runtime.get("baseline_observed_sha256") != candidate["file_sha256"]
        or set(files) != set(PUBLIC_ATTEMPT_FILES)
        or not all(_is_sha256(value) for value in files.values())
        or files["raw/pepglad_candidate.pdb"] != candidate["file_sha256"]
        or files["work/codesign/3EQS_0.pdb"] != candidate["file_sha256"]
        or files["raw/runtime_evidence.json"]
        != runtime["runtime_evidence_sha256"]
    ):
        raise ValueError("v0.35 runtime cross-binding mismatch")
    if (
        type(producer.get("source_commit")) is not str
        or _COMMIT_RE.fullmatch(producer["source_commit"]) is None
        or producer.get("target_input_sha256") != job["target_sha256"]
        or any(
            not _is_sha256(producer.get(field))
            for field in PRODUCER_FIELDS
            - {"source_commit", "container_image", "conda_environment"}
        )
        or any(
            type(producer.get(field)) is not str or not producer[field]
            for field in ("container_image", "conda_environment")
        )
    ):
        raise ValueError("v0.35 producer binding mismatch")

    expected_baseline_status = (
        "pass"
        if runtime["baseline_observed_sha256"]
        == runtime["baseline_expected_sha256"]
        else "warn"
    )
    if qc.get("baseline_replay_status") != expected_baseline_status:
        raise ValueError("v0.35 baseline replay status mismatch")
    expected_overall = (
        "pass_with_warning"
        if "warn" in {qc["chirality_status"], qc["baseline_replay_status"]}
        else "pass"
    )
    if qc.get("overall_qc_status") != expected_overall:
        raise ValueError("v0.35 supported candidate has invalid QC")


def _absolute_no_symlink_path(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            break
        if stat.S_ISLNK(info.st_mode):
            raise ValueError(f"symlink is not allowed: {current}")
    return absolute


def _capture_path(path: Path, *, root: Path | None = None) -> CapturedFile:
    logical = _absolute_no_symlink_path(Path(path))
    try:
        before_path = os.lstat(logical)
    except OSError as exc:
        raise ValueError(f"cannot capture regular file: {logical}") from exc
    if not stat.S_ISREG(before_path.st_mode):
        raise ValueError(f"capture source is not a regular file: {logical}")

    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(logical, flags)
    except OSError as exc:
        raise ValueError(f"cannot open capture source without following links: {logical}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"capture source is not a regular file: {logical}")
        opened_link = os.readlink(f"/proc/self/fd/{descriptor}")
        if opened_link.endswith(" (deleted)"):
            raise ValueError(f"capture source changed while opening: {logical}")
        opened_path = Path(opened_link)
        if root is not None:
            confined_root = Path(root).resolve(strict=True)
            try:
                opened_path.resolve(strict=True).relative_to(confined_root)
            except (OSError, RuntimeError, ValueError) as exc:
                raise ValueError(f"capture escaped its root: {logical}") from exc
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mode,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mode,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    try:
        after_path = os.lstat(logical)
    except OSError as exc:
        raise ValueError(f"capture source disappeared: {logical}") from exc
    path_identity = (
        after_path.st_dev,
        after_path.st_ino,
        after_path.st_size,
        after_path.st_mode,
        after_path.st_mtime_ns,
        after_path.st_ctime_ns,
    )
    payload = b"".join(chunks)
    if identity != after_identity or identity != path_identity or len(payload) != before.st_size:
        raise ValueError(f"capture source changed while reading: {logical}")
    if not payload:
        raise ValueError(f"capture source is empty: {logical}")
    return CapturedFile(
        path=logical,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
        identity=identity,
    )


def _bound_relative(root: Path, relative_text: str) -> Path:
    relative = PurePosixPath(relative_text)
    if (
        not relative_text
        or "\\" in relative_text
        or relative.is_absolute()
        or relative.as_posix() != relative_text
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(f"path is not confined to the attempt: {relative_text}")
    return root.joinpath(*relative.parts)


def capture_attempt(attempt_dir: Path) -> AttemptCapture:
    """Capture every adapter replay dependency through stable no-follow reads."""

    logical = _absolute_no_symlink_path(Path(attempt_dir))
    if not logical.is_dir() or logical.name != ATTEMPT_ID:
        raise ValueError("v0.35 requires the single attempt_001 directory")
    attempt = logical.resolve(strict=True)
    files = {
        relative: _capture_path(_bound_relative(attempt, relative), root=attempt)
        for relative in ATTEMPT_REPLAY_FILES
    }
    return AttemptCapture(attempt_dir=attempt, files=files)


def _assert_capture_unchanged(before: AttemptCapture, after: AttemptCapture) -> None:
    if before.attempt_dir != after.attempt_dir or set(before.files) != set(after.files):
        raise ValueError("v0.35 attempt changed during replay")
    for relative, captured in before.files.items():
        repeated = after.files[relative]
        if (
            captured.identity != repeated.identity
            or captured.sha256 != repeated.sha256
            or captured.payload != repeated.payload
        ):
            raise ValueError(f"v0.35 attempt file changed during replay: {relative}")


@contextmanager
def snapshot_attempt(capture: AttemptCapture) -> Iterator[Path]:
    """Materialize a private byte-for-byte attempt snapshot for adapter replay."""

    with tempfile.TemporaryDirectory(prefix="v035-pepglad-replay-") as temporary:
        attempt = Path(temporary) / ATTEMPT_ID
        attempt.mkdir(mode=0o700)
        for relative, captured in capture.files.items():
            destination = _bound_relative(attempt, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(destination, flags, 0o600)
            try:
                with os.fdopen(descriptor, "wb", closefd=False) as handle:
                    handle.write(captured.payload)
                    handle.flush()
                    os.fsync(handle.fileno())
            finally:
                os.close(descriptor)
        yield attempt


def replay_attempt(capture: AttemptCapture, job: Mapping[str, str]) -> ReplayResult:
    """Run the v0.35 adapter and QC only against the private snapshot."""

    from scripts.v035_adapters import pepglad

    with snapshot_attempt(capture) as snapshot:
        candidate_value, runtime_value = pepglad.parse(job, snapshot)
        candidate = dict(candidate_value)
        runtime = dict(runtime_value)
        qc = dict(
            pepglad.evaluate_candidate(
                job, candidate, runtime, snapshot / "raw"
            )
        )
        structure = Path(str(candidate.get("structure_path", "")))
        try:
            relative = structure.resolve(strict=True).relative_to(
                snapshot.resolve(strict=True)
            ).as_posix()
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError("adapter candidate escaped the replay snapshot") from exc
        if relative != "raw/pepglad_candidate.pdb":
            raise ValueError("adapter selected an unauthorized candidate path")
        candidate["structure_path"] = relative
    return ReplayResult(candidate=candidate, runtime=runtime, qc=qc)


def v034_artifact_digests(paths: Sequence[Path]) -> dict[str, str]:
    """Hash the exact ten historical artifacts without writing to them."""

    selected = tuple(Path(path) for path in paths)
    names = [path.name for path in selected]
    if len(selected) != 10 or len(set(names)) != 10 or set(names) != HISTORICAL_ARTIFACT_NAMES:
        raise ValueError("historical v0.34 artifact set is not exact")
    captured = {path.name: _capture_path(path) for path in selected}
    return {name: item.sha256 for name, item in captured.items()}


def validate_historical_bindings(
    bindings: Mapping[str, Any], paths: Sequence[Path]
) -> None:
    historical = _exact_object(bindings, HISTORICAL_FIELDS, "historical bindings")
    if (
        type(historical["primary_supported"]) is not int
        or historical["primary_supported"] != 6
        or historical["pepglad_status"] != "historical_failure_not_promoted"
    ):
        raise ValueError("historical v0.34 status mismatch")
    artifacts = _exact_object(
        historical["artifacts"], HISTORICAL_ARTIFACT_NAMES, "historical artifacts"
    )
    observed = v034_artifact_digests(paths)
    if artifacts != observed:
        raise ValueError("historical v0.34 artifact binding is stale")


def _validate_run_result(result: Mapping[str, Any], attempt: Path) -> None:
    from scripts import run_v034_wave_a_generation as v034_runner

    if type(result) is not dict or set(result) != v034_runner.PASSED_RESULT_FIELDS:
        raise ValueError("v0.35 run_result has an invalid exact schema")
    string_fields = v034_runner.PASSED_RESULT_FIELDS - {"exit_code"}
    if any(type(result.get(field)) is not str for field in string_fields):
        raise ValueError("v0.35 run_result has an invalid field type")
    expected = {
        "attempt_dir": str(attempt),
        "design_id": DESIGN_ID,
        "job_id": JOB_ID,
        "method": "PepGLAD",
        "parser_status": "parsed",
        "status": "passed",
    }
    if any(result.get(field) != value for field, value in expected.items()):
        raise ValueError("v0.35 run_result is not a passing authorized attempt")
    if type(result.get("exit_code")) is not int or result.get("exit_code") != 0:
        raise ValueError("v0.35 run_result exit_code must be the integer zero")
    if result.get("overall_qc_status") not in v034_runner.PASS_QC_STATUSES:
        raise ValueError("v0.35 run_result QC is not supported")
    try:
        runtime_seconds = float(result["runtime_seconds"])
    except (TypeError, ValueError) as exc:
        raise ValueError("v0.35 run_result runtime_seconds is invalid") from exc
    if not math.isfinite(runtime_seconds) or runtime_seconds <= 0:
        raise ValueError("v0.35 run_result runtime_seconds must be positive")
    try:
        created_at = datetime.fromisoformat(
            result["created_at"].replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("v0.35 run_result created_at is invalid") from exc
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("v0.35 run_result created_at must include a timezone")
    if not result["status_reason"]:
        raise ValueError("v0.35 run_result status_reason is empty")


def _validate_run_result_replay(
    result: Mapping[str, Any], replay: ReplayResult
) -> None:
    from scripts import run_v034_wave_a_generation as v034_runner

    parser_status = replay.candidate.get("parse_status")
    qc_status = replay.qc.get("overall_qc_status")
    status = v034_runner.execution_status(
        exit_code=0,
        timed_out=False,
        parsed=parser_status in {"parsed", "partial"},
        qc=str(qc_status),
    )
    status_reason = (
        replay.candidate.get("status_reason", "parse_failed")
        if status == "parse_failed"
        else replay.qc.get("status_reason", "qc_failed")
        if status == "qc_failed"
        else "bounded_connectivity_candidate_qc_passed"
    )
    expected = {
        "design_id": DESIGN_ID,
        "overall_qc_status": qc_status,
        "parser_status": parser_status,
        "status": status,
        "status_reason": status_reason,
    }
    if any(result.get(field) != value for field, value in expected.items()):
        raise ValueError("v0.35 run_result does not match adapter replay and QC")


def _directory_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_mode,
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _attempt_directories_under(run_root: Path) -> tuple[Path, ...]:
    logical = _absolute_no_symlink_path(Path(run_root))
    try:
        root_lstat = os.lstat(logical)
    except OSError as exc:
        raise ValueError("v0.35 run root is absent") from exc
    if stat.S_ISLNK(root_lstat.st_mode) or not stat.S_ISDIR(root_lstat.st_mode):
        raise ValueError("v0.35 run root must be a regular directory topology")
    if logical.resolve(strict=True) != logical:
        raise ValueError("v0.35 run root cannot contain a symlink")

    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    attempts: list[Path] = []

    def walk(directory_fd: int, relative: PurePosixPath) -> None:
        before = os.fstat(directory_fd)
        if not stat.S_ISDIR(before.st_mode):
            raise ValueError("v0.35 run root contains a non-directory topology node")
        try:
            names = sorted(os.listdir(directory_fd))
        except OSError as exc:
            raise ValueError("cannot scan the complete v0.35 run root") from exc
        for name in names:
            try:
                child_lstat = os.stat(
                    name, dir_fd=directory_fd, follow_symlinks=False
                )
            except OSError as exc:
                raise ValueError("v0.35 run root changed during topology scan") from exc
            if stat.S_ISLNK(child_lstat.st_mode):
                raise ValueError("v0.35 run root cannot contain symlinks")
            is_attempt = re.fullmatch(r"attempt_[0-9]{3}", name) is not None
            child_relative = relative / name
            if not stat.S_ISDIR(child_lstat.st_mode):
                if is_attempt:
                    raise ValueError("v0.35 attempt topology node is not a directory")
                continue
            try:
                child_fd = os.open(name, directory_flags, dir_fd=directory_fd)
            except OSError as exc:
                raise ValueError("v0.35 run root contains an unsafe directory") from exc
            try:
                opened = os.fstat(child_fd)
                if _directory_identity(opened) != _directory_identity(child_lstat):
                    raise ValueError("v0.35 run root changed during topology scan")
                if is_attempt:
                    attempts.append(logical.joinpath(*child_relative.parts))
                else:
                    walk(child_fd, child_relative)
                repeated = os.stat(
                    name, dir_fd=directory_fd, follow_symlinks=False
                )
                if _directory_identity(repeated) != _directory_identity(opened):
                    raise ValueError("v0.35 run root changed during topology scan")
            finally:
                os.close(child_fd)
        after = os.fstat(directory_fd)
        if _directory_identity(after) != _directory_identity(before):
            raise ValueError("v0.35 run root changed during topology scan")

    root_fd = os.open(logical, directory_flags)
    try:
        if _directory_identity(os.fstat(root_fd)) != _directory_identity(root_lstat):
            raise ValueError("v0.35 run root changed before topology scan")
        walk(root_fd, PurePosixPath())
    finally:
        os.close(root_fd)
    return tuple(attempts)


def _single_attempt(run_root: Path) -> Path:
    logical_root = _absolute_no_symlink_path(Path(run_root))
    expected = logical_root / "pepglad" / JOB_ID / ATTEMPT_ID
    attempts = _attempt_directories_under(logical_root)
    if attempts != (expected,):
        raise ValueError(
            "v0.35 run root must contain only the authorized PepGLAD attempt_001"
        )
    return expected


def build_bundle(
    *,
    run_root: Path = DEFAULT_RUN_ROOT,
    job_manifest: Path = DEFAULT_JOB_MANIFEST,
    execution_matrix: Path = DEFAULT_EXECUTION_MATRIX,
    historical_paths: Sequence[Path] = DEFAULT_HISTORICAL_ARTIFACTS,
) -> dict[str, Any]:
    """Build one evidence bundle from an immutable, passing attempt replay."""

    from scripts import run_v035_pepglad_connectivity as runner
    from scripts.v035_adapters import pepglad

    job = runner.load_authorized_job(Path(job_manifest))
    execution_row = runner.load_authorized_execution(Path(execution_matrix))
    attempt = _single_attempt(Path(run_root))
    initial = capture_attempt(attempt)
    captured_job = _strict_json_bytes(initial.files["job.json"].payload, "attempt job")
    captured_execution = _strict_json_bytes(
        initial.files["execution.json"].payload, "attempt execution"
    )
    run_result = _strict_json_bytes(
        initial.files["run_result.json"].payload, "attempt run_result"
    )
    if captured_job != job or captured_execution != execution_row:
        raise ValueError("attempt job or execution differs from the authorized CSV row")
    _validate_run_result(run_result, initial.attempt_dir)

    target_text = job["target_pdb_path"]
    target_path = Path(target_text)
    if not target_path.is_absolute():
        target_path = ROOT / target_path
    target_before = _capture_path(target_path, root=ROOT)
    if target_before.sha256 != job["target_pdb_sha256"]:
        raise ValueError("v0.35 target input digest mismatch")

    replay = replay_attempt(initial, job)
    repeated = capture_attempt(attempt)
    _assert_capture_unchanged(initial, repeated)
    if _single_attempt(Path(run_root)) != attempt:
        raise ValueError("v0.35 run root attempt topology changed during replay")
    _validate_run_result_replay(run_result, replay)
    target_after = _capture_path(target_path, root=ROOT)
    if (
        target_before.identity != target_after.identity
        or target_before.payload != target_after.payload
    ):
        raise ValueError("v0.35 target input changed during replay")

    runtime_raw = _strict_json_bytes(
        initial.files["raw/runtime_evidence.json"].payload,
        "runtime evidence",
    )
    if runtime_raw != replay.runtime:
        raise ValueError("adapter runtime replay differs from captured evidence")
    pepglad.validate_runtime_bindings(replay.runtime)
    expected_bindings = pepglad.expected_runtime_bindings()
    producer = {field: replay.runtime.get(field) for field in PRODUCER_FIELDS}
    if producer != expected_bindings:
        raise ValueError("runtime producer bindings differ from the adapter pins")

    candidate = replay.candidate
    qc = replay.qc
    candidate_digest = initial.files["raw/pepglad_candidate.pdb"].sha256
    public_files = {
        relative: initial.files[relative].sha256 for relative in PUBLIC_ATTEMPT_FILES
    }
    if public_files["work/codesign/3EQS_0.pdb"] != candidate_digest:
        raise ValueError("official PepGLAD source candidate differs from the raw copy")

    historical_artifacts = v034_artifact_digests(historical_paths)
    historical = {
        "primary_supported": 6,
        "pepglad_status": "historical_failure_not_promoted",
        "artifacts": historical_artifacts,
    }
    validate_historical_bindings(historical, historical_paths)

    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "historical_v034_bindings": historical,
        "job": {
            "job_id": JOB_ID,
            "method": "PepGLAD",
            "random_seed": 42,
            "seed_stage": "primary",
            "target_sha256": job["target_pdb_sha256"],
            "target_chain": job["expected_target_chain"],
            "binder_chain": job["expected_binder_chain"],
            "length": 11,
            "chirality_constraint": job["chirality_constraint"],
            "chirality_check_mode": job["chirality_check_mode"],
            "baseline_replay_policy": job["baseline_replay_policy"],
        },
        "execution": {
            "attempt_id": ATTEMPT_ID,
            "attempt_dir": str(initial.attempt_dir),
            "exit_code": 0,
            "status": "passed",
            "supported_candidate": True,
        },
        "candidate": {
            "design_id": DESIGN_ID,
            "sequence": candidate.get("sequence"),
            "structure_path": "raw/pepglad_candidate.pdb",
            "file_sha256": candidate_digest,
            "binder_chain": candidate.get("binder_chain"),
            "parse_status": candidate.get("parse_status"),
            "chirality": candidate.get("chirality"),
        },
        "qc": {field: qc.get(field) for field in QC_FIELDS},
        "runtime_provenance": {
            "attempt_id": ATTEMPT_ID,
            "requested_seed": replay.runtime.get("requested_seed"),
            "effective_seed": replay.runtime.get("effective_seed"),
            "seed_control_status": replay.runtime.get("seed_control_status"),
            "runtime_evidence_path": "raw/runtime_evidence.json",
            "runtime_evidence_sha256": initial.files[
                "raw/runtime_evidence.json"
            ].sha256,
            "runtime_semantic_sha256": _semantic_sha256(runtime_raw),
            "baseline_expected_sha256": replay.runtime.get(
                "baseline_replay_expected_sha256"
            ),
            "baseline_observed_sha256": replay.runtime.get(
                "baseline_replay_observed_sha256"
            ),
            "files": public_files,
            "producer_bindings": producer,
        },
    }
    validate_bundle(bundle)
    return bundle


def publish_bundle(
    bundle: Mapping[str, Any], *, output_path: Path = DEFAULT_OUTPUT
) -> None:
    """Atomically publish canonical JSON without modifying historical inputs."""

    validate_bundle(bundle)
    output = Path(output_path)
    if output.name != "pilot_pepglad_connectivity_v0.35.json":
        raise ValueError("v0.35 bundle must use the canonical output filename")
    if output.name in HISTORICAL_ARTIFACT_NAMES or any(
        part in {"v0.34", "v034"} for part in output.parts
    ):
        raise ValueError("v0.35 publication cannot target historical artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    output = _absolute_no_symlink_path(output)
    if output.exists() and not output.is_file():
        raise ValueError("v0.35 output target is not a regular file")

    payload = _canonical_json_bytes(bundle)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
        directory_fd = os.open(output.parent, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--job-manifest", type=Path, default=DEFAULT_JOB_MANIFEST)
    parser.add_argument(
        "--execution-matrix", type=Path, default=DEFAULT_EXECUTION_MATRIX
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    bundle = build_bundle(
        run_root=args.run_root,
        job_manifest=args.job_manifest,
        execution_matrix=args.execution_matrix,
    )
    publish_bundle(bundle, output_path=args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "schema_version": SCHEMA_VERSION,
                "attempt_id": ATTEMPT_ID,
                "evidence_boundary": EVIDENCE_BOUNDARY,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
