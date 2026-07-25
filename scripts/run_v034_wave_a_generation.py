#!/usr/bin/env python3
"""Package and execute bounded v0.34 Wave A connectivity jobs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import io
import json
import math
import os
import shlex
import stat
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.engine.bounded_process import BoundedProcessError, run_bounded_process
from scripts.v034_adapters.common import evaluate_candidate_qc, read_csv, write_csv


DEFAULT_JOB_MANIFEST = ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv"
DEFAULT_EXECUTION_MATRIX = ROOT / "benchmark/deployment/pilot_execution_matrix_v0.34.csv"
DEFAULT_RUN_ROOT = ROOT / "benchmark_runs/v0.34"

ADAPTER_MODULES = {
    "PepMLM": "scripts.v034_adapters.pepmlm",
    "DiffPepBuilder": "scripts.v034_adapters.diffpepbuilder",
    "PepGLAD": "scripts.v034_adapters.pepglad",
    "D-Flow / PeptideDesign": "scripts.v034_adapters.dflow",
    "PepMirror": "scripts.v034_adapters.pepmirror",
    "AfCycDesign / ColabDesign cyclic peptide": "scripts.v034_adapters.colabdesign",
    "RFdiffusion + ProteinMPNN": "scripts.v034_adapters.rfdiffusion_mpnn",
}

METHOD_SLUGS = {
    "PepMLM": "pepmlm",
    "DiffPepBuilder": "diffpepbuilder",
    "PepGLAD": "pepglad",
    "D-Flow / PeptideDesign": "dflow",
    "PepMirror": "pepmirror",
    "AfCycDesign / ColabDesign cyclic peptide": "colabdesign",
    "RFdiffusion + ProteinMPNN": "rfdiffusion_proteinmpnn",
}

CANDIDATE_HEADERS = (
    "design_id",
    "job_id",
    "method",
    "target_id",
    "binder_id",
    "source_output_id",
    "generation_rank",
    "sequence",
    "structure_path",
    "source_output_path",
    "binder_chain",
    "peptide_type",
    "chirality",
    "cyclic",
    "parse_status",
    "status_reason",
    "notes",
)

METHOD_OUTPUT_HEADERS = (
    "run_record_id",
    "job_id",
    "method",
    "task_id",
    "execution_stage",
    "source_commit",
    "model_revision",
    "environment_id",
    "command",
    "raw_output_root",
    "stdout_log",
    "stderr_log",
    "runtime_seconds",
    "exit_code",
    "parser_status",
    "overall_qc_status",
    "status",
    "status_reason",
    "created_at",
)

PASSED_RESULT_FIELDS = frozenset(
    {
        "attempt_dir",
        "created_at",
        "design_id",
        "exit_code",
        "job_id",
        "method",
        "overall_qc_status",
        "parser_status",
        "runtime_seconds",
        "status",
        "status_reason",
    }
)
PASS_QC_STATUSES = frozenset({"pass", "pass_with_warning"})


def _qc_headers(
    *,
    chirality_counts: bool = False,
    terminal_distance: bool = False,
    mirror_metrics: bool = False,
    backbone_handoff: bool = False,
) -> tuple[str, ...]:
    headers = [
        "job_id",
        "design_id",
        "file_status",
        "file_reason",
        "file_sha256",
        "file_size_bytes",
        "parse_status",
        "chain_status",
        "target_binding_status",
        "length_status",
        "sequence_length",
        "sequence_structure_status",
        "chirality_status",
    ]
    if chirality_counts:
        headers.extend(
            (
                "chirality_evaluable",
                "chirality_l_count",
                "chirality_d_count",
                "chirality_gly_count",
                "chirality_unknown_count",
            )
        )
    if terminal_distance:
        headers.append("terminal_cn_distance")
    headers.extend(
        (
            "cyclic_status",
            "noncanonical_status",
            "noncanonical_residues",
            "seed_status",
        )
    )
    if mirror_metrics:
        headers.extend(
            (
                "mirror_target_atom_identity_status",
                "mirror_target_central_inversion_status",
                "mirror_target_atom_count",
                "mirror_target_central_inversion_max_residual",
                "mirror_target_central_inversion_tolerance",
                "mirror_output_atom_identity_status",
                "mirror_output_central_inversion_status",
                "mirror_output_atom_count",
                "mirror_output_central_inversion_max_residual",
                "mirror_output_central_inversion_tolerance",
            )
        )
    headers.append("method_contract_status")
    if backbone_handoff:
        headers.append("backbone_to_fasta_handoff_status")
    headers.extend(("handoff_status", "overall_qc_status", "status_reason"))
    return tuple(headers)


_QC_BASE = _qc_headers()
_QC_BASE_HANDOFF = _qc_headers(backbone_handoff=True)
_QC_CHIRAL = _qc_headers(chirality_counts=True)
_QC_CHIRAL_HANDOFF = _qc_headers(chirality_counts=True, backbone_handoff=True)
_QC_CYCLIC = _qc_headers(chirality_counts=True, terminal_distance=True)
_QC_CYCLIC_HANDOFF = _qc_headers(
    chirality_counts=True,
    terminal_distance=True,
    backbone_handoff=True,
)
_QC_MIRROR_HANDOFF = _qc_headers(
    chirality_counts=True,
    mirror_metrics=True,
    backbone_handoff=True,
)

QC_HEADER_PROFILES = {
    "PepMLM": frozenset({_QC_BASE, _QC_BASE_HANDOFF}),
    "DiffPepBuilder": frozenset({_QC_CHIRAL, _QC_CHIRAL_HANDOFF}),
    "PepGLAD": frozenset({_QC_CHIRAL, _QC_CHIRAL_HANDOFF}),
    "D-Flow / PeptideDesign": frozenset({_QC_CHIRAL, _QC_CHIRAL_HANDOFF}),
    "PepMirror": frozenset({_QC_MIRROR_HANDOFF}),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        {_QC_CYCLIC, _QC_CYCLIC_HANDOFF}
    ),
    "RFdiffusion + ProteinMPNN": frozenset({_QC_BASE_HANDOFF}),
}


def load_jobs(
    *, stage: str, job_manifest: Path = DEFAULT_JOB_MANIFEST, job_ids: set[str] | None = None
) -> list[dict[str, str]]:
    if stage not in {"primary", "extension"}:
        raise ValueError(f"Unknown stage: {stage}")
    rows = [row for row in read_csv(job_manifest) if row.get("seed_stage") == stage]
    return [row for row in rows if job_ids is None or row["job_id"] in job_ids]


def load_execution_matrix(path: Path = DEFAULT_EXECUTION_MATRIX) -> dict[str, dict[str, str]]:
    return {row["job_id"]: row for row in read_csv(path)}


def _inferred_run_root(job_root: Path) -> Path:
    try:
        return job_root.parents[1]
    except IndexError as exc:
        raise ValueError(f"unsafe job root outside a run root: {job_root}") from exc


def _confined_job_root(
    job_root: Path, run_root: Path, *, create: bool
) -> tuple[Path, Path]:
    job_root = Path(job_root)
    run_root = Path(run_root)
    if run_root.is_symlink():
        raise ValueError(f"unsafe symlink run root: {run_root}")
    if run_root.exists() and not run_root.is_dir():
        raise ValueError(f"unsafe non-directory run root: {run_root}")
    if not run_root.exists():
        if not create:
            raise FileNotFoundError(run_root)
        run_root.mkdir(parents=True)
    try:
        run_root_abs = run_root.absolute()
        job_root_abs = job_root.absolute()
        relative = job_root_abs.relative_to(run_root_abs)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"job root is outside run root: {job_root}") from exc
    if len(relative.parts) != 2:
        raise ValueError(f"unsafe job root layout: {job_root}")

    run_root_resolved = run_root.resolve(strict=True)
    current = run_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"unsafe symlink job-root component: {current}")
        if current.exists():
            if not current.is_dir():
                raise ValueError(f"unsafe non-directory job-root component: {current}")
        elif create:
            current.mkdir()
        else:
            raise FileNotFoundError(current)
        try:
            current.resolve(strict=True).relative_to(run_root_resolved)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(f"job root is outside run root: {current}") from exc
    return job_root, run_root


def _attempt_directories(job_root: Path, run_root: Path) -> list[Path]:
    try:
        job_root, run_root = _confined_job_root(job_root, run_root, create=False)
    except FileNotFoundError:
        return []
    run_root_resolved = run_root.resolve(strict=True)
    job_root_resolved = job_root.resolve(strict=True)
    attempts: list[Path] = []
    for path in job_root.glob("attempt_[0-9][0-9][0-9]"):
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"unsafe attempt path: {path}")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(run_root_resolved)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(f"attempt path is outside run root: {path}") from exc
        if resolved.parent != job_root_resolved:
            raise ValueError(f"unsafe attempt parent: {path}")
        attempts.append(path)
    return sorted(attempts)


def allocate_attempt_dir(
    job_root: Path, *, retry_failed: bool, run_root: Path | None = None
) -> Path:
    run_root = Path(run_root) if run_root is not None else _inferred_run_root(job_root)
    job_root, run_root = _confined_job_root(job_root, run_root, create=True)
    existing = _attempt_directories(job_root, run_root)
    if existing and not retry_failed:
        raise FileExistsError(f"Job already has attempt evidence: {job_root}")
    number = int(existing[-1].name.split("_")[-1]) + 1 if existing else 1
    attempt = job_root / f"attempt_{number:03d}"
    if attempt.exists() or attempt.is_symlink():
        raise ValueError(f"unsafe attempt path: {attempt}")
    attempt.mkdir(parents=False, exist_ok=False)
    if attempt.is_symlink() or attempt.resolve(strict=True).parent != job_root.resolve(strict=True):
        raise ValueError(f"unsafe attempt parent: {attempt}")
    return attempt


def _latest_attempt(job_root: Path, *, run_root: Path | None = None) -> Path | None:
    run_root = Path(run_root) if run_root is not None else _inferred_run_root(job_root)
    attempts = _attempt_directories(job_root, run_root)
    return attempts[-1] if attempts else None


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_strict_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_json_object,
        )
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _canonical_attempt_file(attempt: Path, filename: str) -> Path | None:
    path = attempt / filename
    try:
        if attempt.is_symlink() or not attempt.is_dir():
            return None
        attempt_root = attempt.resolve(strict=True)
        if path.is_symlink() or not path.is_file():
            return None
        if path.resolve(strict=True) != attempt_root / filename:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return path


def _read_attempt_json_object(attempt: Path, filename: str) -> dict[str, Any] | None:
    path = _canonical_attempt_file(attempt, filename)
    return _read_strict_json_object(path) if path is not None else None


def _strict_csv_row(
    attempt: Path,
    filename: str,
    expected_headers: frozenset[tuple[str, ...]],
) -> dict[str, str] | None:
    path = _canonical_attempt_file(attempt, filename)
    if path is None:
        return None
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    return _strict_csv_bytes(payload, expected_headers)


def _strict_csv_bytes(
    payload: bytes, expected_headers: frozenset[tuple[str, ...]]
) -> dict[str, str] | None:
    try:
        parsed = list(
            csv.reader(io.StringIO(payload.decode("utf-8"), newline=""), strict=True)
        )
    except (UnicodeError, csv.Error):
        return None
    if len(parsed) != 2:
        return None
    headers, row = parsed
    header_tuple = tuple(headers)
    if header_tuple not in expected_headers or len(row) != len(headers):
        return None
    if any("\x00" in cell or "\n" in cell or "\r" in cell for cell in row):
        return None
    return dict(zip(headers, row))


def _is_exact_zero(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def _positive_finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _timezone_aware_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _candidate_path_within_raw(attempt: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = attempt / path
    try:
        attempt_root = attempt.resolve(strict=True)
        raw_root = (attempt_root / "raw").resolve(strict=False)
        resolved = path.resolve(strict=False)
        resolved.relative_to(raw_root)
    except (OSError, RuntimeError, ValueError):
        return None
    current = path
    while current != attempt and current != current.parent:
        if current.exists() and current.is_symlink():
            return None
        current = current.parent
    return resolved


def _candidate_paths_match_method(
    job: Mapping[str, str], attempt: Path, candidate: Mapping[str, str]
) -> bool:
    source_value = candidate.get("source_output_path")
    source = _candidate_path_within_raw(attempt, source_value)
    structure_value = candidate.get("structure_path", "")
    method = job["method"]
    source_output_id = candidate.get("source_output_id", "")
    source_name = Path(source_value).name if source_value else ""
    if source is None or not source_output_id or not source_name:
        return False
    if method == "RFdiffusion + ProteinMPNN":
        if not (
            source_output_id == source_name
            or source_output_id.startswith(f"{source_name}:")
        ):
            return False
    elif source_output_id != source_name:
        return False
    if method == "PepMLM":
        return not structure_value
    structure = _candidate_path_within_raw(attempt, structure_value)
    if structure is None:
        return False
    if method == "RFdiffusion + ProteinMPNN":
        return source != structure
    return source == structure


_RUNTIME_EVIDENCE_PATHS = {
    "PepMLM": Path("raw/runtime_evidence.json"),
    "DiffPepBuilder": Path("raw/runtime_evidence.json"),
    "PepGLAD": Path("raw/runtime_evidence.json"),
    "D-Flow / PeptideDesign": Path("runtime_evidence.json"),
    "PepMirror": Path("runtime_evidence.json"),
    "AfCycDesign / ColabDesign cyclic peptide": Path("raw/runtime_evidence.json"),
    "RFdiffusion + ProteinMPNN": Path("raw/runtime_evidence.json"),
}


def _stable_attempt_file(attempt: Path, relative: Path) -> bytes | None:
    if relative.is_absolute() or ".." in relative.parts:
        return None
    path = attempt / relative
    try:
        attempt_root = attempt.resolve(strict=True)
        path.resolve(strict=True).relative_to(attempt_root)
        current = path
        while current != attempt:
            if current.is_symlink():
                return None
            current = current.parent
        preliminary = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(preliminary.st_mode):
            return None
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(path, flags)
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                return None
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        observed = path.stat(follow_symlinks=False)
    except (OSError, RuntimeError, ValueError):
        return None
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    identity_observed = (
        observed.st_dev,
        observed.st_ino,
        observed.st_size,
        observed.st_mtime_ns,
    )
    return b"".join(chunks) if identity_before == identity_after == identity_observed else None


def _strict_json_bytes(payload: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_strict_json_object)
    except (UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _capture_attempt_replay_files(
    job: Mapping[str, str], attempt: Path
) -> dict[Path, bytes] | None:
    runtime_relative = _RUNTIME_EVIDENCE_PATHS.get(job["method"])
    if runtime_relative is None:
        return None
    other_runtime = (
        Path("runtime_evidence.json")
        if runtime_relative.parent == Path("raw")
        else Path("raw/runtime_evidence.json")
    )
    if (attempt / other_runtime).exists() or (attempt / other_runtime).is_symlink():
        return None
    required = {
        Path("run_result.json"),
        Path("method_output_manifest.csv"),
        Path("candidate_outputs.csv"),
        Path("candidate_qc.csv"),
        Path("command.sh"),
        Path("stdout.log"),
        Path("stderr.log"),
        runtime_relative,
    }
    if job["method"] == "PepMirror":
        required.update(
            {
                Path("package_evidence.json"),
                Path("executed_source_manifest.json"),
                Path("execution_preflight_evidence.json"),
            }
        )
    raw = attempt / "raw"
    try:
        if raw.is_symlink() or not raw.is_dir():
            return None
        for directory, directories, filenames in os.walk(raw, followlinks=False):
            directory_path = Path(directory)
            if directory_path.is_symlink():
                return None
            for name in directories:
                child = directory_path / name
                if child.is_symlink() or not child.is_dir():
                    return None
            for name in filenames:
                required.add((directory_path / name).relative_to(attempt))
    except (OSError, RuntimeError, ValueError):
        return None

    captured: dict[Path, bytes] = {}
    for relative in sorted(required):
        payload = _stable_attempt_file(attempt, relative)
        if payload is None:
            return None
        captured[relative] = payload
    if not captured[Path("command.sh")]:
        return None

    if job["method"] == "PepMirror":
        source_manifest = _strict_json_bytes(captured[Path("executed_source_manifest.json")])
        files = source_manifest.get("files") if source_manifest is not None else None
        if not isinstance(files, dict) or not files:
            return None
        for relative_text in files:
            source_relative = Path(relative_text)
            if source_relative.is_absolute() or ".." in source_relative.parts:
                return None
            relative = Path("work/PepMirror") / source_relative
            payload = _stable_attempt_file(attempt, relative)
            if payload is None:
                return None
            captured[relative] = payload
    return captured


def _relocate_value(value: Any, source_root: str, snapshot_root: str) -> Any:
    if isinstance(value, str):
        return value.replace(source_root, snapshot_root)
    if isinstance(value, list):
        return [_relocate_value(item, source_root, snapshot_root) for item in value]
    if isinstance(value, dict):
        return {
            key: _relocate_value(item, source_root, snapshot_root)
            for key, item in value.items()
        }
    return value


def _write_snapshot_json(path: Path, value: Mapping[str, Any]) -> bytes:
    payload = (json.dumps(dict(value), indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(payload)
    return payload


def _relocate_snapshot_json(
    snapshot: Path,
    relative: Path,
    source_attempt: Path,
) -> dict[str, Any] | None:
    path = snapshot / relative
    value = _strict_json_bytes(path.read_bytes())
    if value is None:
        return None
    relocated = _relocate_value(value, str(source_attempt), str(snapshot))
    _write_snapshot_json(path, relocated)
    return relocated


def _prepare_snapshot_json(
    job: Mapping[str, str], source_attempt: Path, snapshot: Path
) -> bool:
    runtime_relative = _RUNTIME_EVIDENCE_PATHS[job["method"]]
    if job["method"] != "PepMirror":
        return _relocate_snapshot_json(snapshot, runtime_relative, source_attempt) is not None

    manifest = _relocate_snapshot_json(
        snapshot, Path("executed_source_manifest.json"), source_attempt
    )
    preflight = _relocate_snapshot_json(
        snapshot, Path("execution_preflight_evidence.json"), source_attempt
    )
    package = _relocate_snapshot_json(snapshot, Path("package_evidence.json"), source_attempt)
    runtime = _relocate_snapshot_json(snapshot, runtime_relative, source_attempt)
    if any(value is None for value in (manifest, preflight, package, runtime)):
        return False
    assert manifest is not None and preflight is not None and package is not None and runtime is not None
    manifest_payload = _write_snapshot_json(snapshot / "executed_source_manifest.json", manifest)
    manifest_sha = hashlib.sha256(manifest_payload).hexdigest()
    preflight_payload = _write_snapshot_json(snapshot / "execution_preflight_evidence.json", preflight)
    preflight_sha = hashlib.sha256(preflight_payload).hexdigest()
    package["executed_source_manifest_path"] = str(snapshot / "executed_source_manifest.json")
    package["executed_source_manifest_sha256"] = manifest_sha
    package_payload = _write_snapshot_json(snapshot / "package_evidence.json", package)
    package_sha = hashlib.sha256(package_payload).hexdigest()
    runtime.update(package)
    runtime.update(preflight)
    runtime["executed_source_manifest_path"] = str(snapshot / "executed_source_manifest.json")
    runtime["executed_source_manifest_sha256"] = manifest_sha
    runtime["execution_preflight_evidence_path"] = str(
        snapshot / "execution_preflight_evidence.json"
    )
    runtime["execution_preflight_evidence_sha256"] = preflight_sha
    runtime["package_evidence_path"] = str(snapshot / "package_evidence.json")
    runtime["package_evidence_sha256"] = package_sha
    _write_snapshot_json(snapshot / runtime_relative, runtime)
    return True


def _runtime_identity_matches(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    adapter: Any,
    runtime: Mapping[str, Any],
) -> bool:
    try:
        from scripts import parse_v034_generation_outputs as merge_contract

        method = job["method"]
        if method == "PepGLAD":
            schemas = {
                merge_contract.PEPGLAD_LEGACY_RUNTIME_FIELDS,
                merge_contract.PEPGLAD_INSTRUMENTED_RUNTIME_FIELDS,
            }
            if frozenset(runtime) not in schemas:
                return False
        elif set(runtime) != merge_contract.NON_PEPGLAD_RUNTIME_EVIDENCE_FIELDS.get(method):
            return False
    except (ImportError, AttributeError, TypeError):
        return False
    seed = int(job["random_seed"])
    if not all(
        (
            runtime.get("requested_seed") == seed,
            runtime.get("effective_seed") == seed,
            runtime.get("seed_control_status") == "honored",
        )
    ):
        return False
    method = job["method"]
    if method in {"PepMLM", "DiffPepBuilder", "PepGLAD"}:
        if runtime.get("source_commit") != adapter.SOURCE_COMMIT:
            return False
    if method == "PepMLM":
        return all(
            (
                runtime.get("source_entrypoint_sha256") == adapter.SOURCE_ENTRYPOINT_SHA256,
                runtime.get("model_revision") == adapter.MODEL_REVISION,
                runtime.get("model_weights_sha256") == adapter.MODEL_WEIGHTS_SHA256,
                runtime.get("container_image") == adapter.DEFAULT_IMAGE,
                runtime.get("conda_environment") == adapter.DEFAULT_ENV,
                execution.get("container_or_env")
                == f"{adapter.DEFAULT_IMAGE}/{adapter.DEFAULT_ENV}",
            )
        )
    if method == "DiffPepBuilder":
        return all(
            (
                runtime.get("source_entrypoint_sha256") == adapter.SOURCE_ENTRYPOINT_SHA256,
                runtime.get("model_asset_sha256") == adapter.MODEL_ASSETS,
                runtime.get("container_image") == adapter.DEFAULT_IMAGE,
                runtime.get("conda_environment") == adapter.DEFAULT_ENV,
                execution.get("container_or_env")
                == f"{adapter.DEFAULT_IMAGE}/{adapter.DEFAULT_ENV}",
            )
        )
    if method == "D-Flow / PeptideDesign":
        return all(
            (
                runtime.get("source_commit") == adapter.SOURCE_COMMIT,
                runtime.get("checkpoint_sha256") == adapter.CHECKPOINT_SHA256,
                runtime.get("execution_environment_declared") == adapter.HOST_ENV_DECLARATION,
                execution.get("container_or_env") == adapter.HOST_ENV_DECLARATION,
            )
        )
    if method == "PepMirror":
        return all(
            (
                runtime.get("source_commit_expected") == adapter.SOURCE_COMMIT,
                runtime.get("source_commit_observed") == adapter.SOURCE_COMMIT,
                runtime.get("checkpoint_revision") == adapter.MODEL_REVISION,
                runtime.get("execution_environment_id") == execution.get("container_or_env"),
            )
        )
    if method == "AfCycDesign / ColabDesign cyclic peptide":
        return all(
            (
                runtime.get("source_commit") == adapter.SOURCE_COMMIT,
                runtime.get("alphafold_params_sha256") == adapter.ALPHAFOLD_PARAMS_SHA256,
                runtime.get("container_image") == adapter.DEFAULT_IMAGE,
                execution.get("container_or_env")
                == f"{adapter.DEFAULT_IMAGE}/{adapter.DEFAULT_ENV}",
            )
        )
    if method == "RFdiffusion + ProteinMPNN":
        return all(
            (
                runtime.get("rf_source_commit") == adapter.RFDIFFUSION_COMMIT,
                runtime.get("mpnn_source_commit") == adapter.PROTEINMPNN_COMMIT,
                runtime.get("rf_checkpoint_sha256") == adapter.RFDIFFUSION_CHECKPOINT_SHA256,
                runtime.get("mpnn_checkpoint_sha256") == adapter.PROTEINMPNN_CHECKPOINT_SHA256,
            )
        )
    return method == "PepGLAD"


def _stringified_row(value: Mapping[str, Any]) -> dict[str, str]:
    return {key: "" if item is None else str(item) for key, item in value.items()}


def _normalize_snapshot_candidate(
    candidate: Mapping[str, Any], snapshot: Path, source_attempt: Path
) -> dict[str, str]:
    normalized = _stringified_row(candidate)
    for field in ("structure_path", "source_output_path"):
        value = normalized.get(field, "")
        if value.startswith(str(snapshot)):
            normalized[field] = str(source_attempt) + value[len(str(snapshot)) :]
    return normalized


def _snapshot_replay_matches(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    attempt: Path,
    result: Mapping[str, Any],
    manifest: Mapping[str, str],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    captured = _capture_attempt_replay_files(job, attempt)
    if captured is None:
        return False
    if _strict_json_bytes(captured[Path("run_result.json")]) != dict(result):
        return False
    captured_manifest = _strict_csv_bytes(
        captured[Path("method_output_manifest.csv")],
        frozenset({tuple(METHOD_OUTPUT_HEADERS)}),
    )
    captured_candidate = _strict_csv_bytes(
        captured[Path("candidate_outputs.csv")],
        frozenset({tuple(CANDIDATE_HEADERS)}),
    )
    qc_profiles = QC_HEADER_PROFILES.get(job["method"])
    captured_qc = (
        _strict_csv_bytes(captured[Path("candidate_qc.csv")], qc_profiles)
        if qc_profiles is not None
        else None
    )
    if not all(
        (
            captured_manifest == dict(manifest),
            captured_candidate == dict(candidate),
            captured_qc == dict(qc),
        )
    ):
        return False
    with tempfile.TemporaryDirectory(prefix="v034-runner-snapshot-") as temporary:
        snapshot = (
            Path(temporary)
            / METHOD_SLUGS[job["method"]]
            / job["job_id"]
            / attempt.name
        )
        snapshot.mkdir(parents=True)
        for relative, payload in captured.items():
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        if not _prepare_snapshot_json(job, attempt, snapshot):
            return False
        try:
            adapter = load_adapter(job["method"])
            candidate_value, runtime = adapter.parse(job, snapshot)
            replay_candidate = _candidate_row(job, candidate_value)
            replay_qc = evaluate_candidate_qc(
                job, replay_candidate, runtime, snapshot / "raw"
            )
        except Exception:
            return False
        if not _runtime_identity_matches(job, execution, adapter, runtime):
            return False
        normalized_candidate = _normalize_snapshot_candidate(
            replay_candidate, snapshot, attempt
        )
        if normalized_candidate != dict(candidate):
            return False
        replay_qc_row = _stringified_row(
            {"job_id": job["job_id"], "design_id": result["design_id"], **replay_qc}
        )
        if "backbone_to_fasta_handoff_status" not in qc and replay_qc_row.get(
            "backbone_to_fasta_handoff_status"
        ) == "not_applicable":
            replay_qc_row.pop("backbone_to_fasta_handoff_status")
        if replay_qc_row != dict(qc):
            return False
    return _capture_attempt_replay_files(job, attempt) == captured


def _qc_supports_candidate(
    job: Mapping[str, str], qc: Mapping[str, str], overall_qc_status: str
) -> bool:
    required_passes = (
        "file_status",
        "parse_status",
        "length_status",
        "seed_status",
        "method_contract_status",
    )
    if any(qc.get(field) != "pass" for field in required_passes):
        return False
    status_values = [
        value
        for field, value in qc.items()
        if field.endswith("_status") and field != "overall_qc_status"
    ]
    if not status_values or any(
        value not in {"pass", "warn", "not_applicable"} for value in status_values
    ):
        return False
    expected_overall = "pass_with_warning" if "warn" in status_values else "pass"
    if overall_qc_status != expected_overall:
        return False
    method = job["method"]
    expected_handoff = "pass" if method == "RFdiffusion + ProteinMPNN" else "not_applicable"
    if qc.get("handoff_status") != expected_handoff:
        return False
    backbone_handoff = qc.get("backbone_to_fasta_handoff_status")
    if method == "RFdiffusion + ProteinMPNN":
        if backbone_handoff != "pass":
            return False
    elif backbone_handoff not in {None, "not_applicable"}:
        return False
    return bool(qc.get("status_reason"))


def _passed_attempt_is_complete(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    attempt: Path,
    result: Mapping[str, Any],
) -> bool:
    job_id = job.get("job_id", "")
    method = job.get("method", "")
    expected_slug = METHOD_SLUGS.get(method)
    if not job_id or expected_slug is None:
        return False
    if not all(
        (
            attempt.name.startswith("attempt_"),
            len(attempt.name) == len("attempt_000"),
            attempt.name.removeprefix("attempt_").isdigit(),
            attempt.parent.name == job_id,
            attempt.parent.parent.name == expected_slug,
            set(result) == PASSED_RESULT_FIELDS,
        )
    ):
        return False

    design_id = f"{job_id}_candidate_1"
    parser_status = result.get("parser_status")
    overall_qc_status = result.get("overall_qc_status")
    runtime_seconds = _positive_finite_float(result.get("runtime_seconds"))
    created_at = _timezone_aware_timestamp(result.get("created_at"))
    if not all(
        (
            result.get("job_id") == job_id,
            result.get("method") == method,
            result.get("attempt_dir") == str(attempt),
            result.get("design_id") == design_id,
            result.get("status") == "passed",
            result.get("status_reason")
            == "bounded_connectivity_candidate_qc_passed",
            parser_status in {"parsed", "partial"},
            overall_qc_status in PASS_QC_STATUSES,
            _is_exact_zero(result.get("exit_code")),
            runtime_seconds is not None,
            created_at is not None,
        )
    ):
        return False

    manifest = _strict_csv_row(
        attempt,
        "method_output_manifest.csv",
        frozenset({tuple(METHOD_OUTPUT_HEADERS)}),
    )
    candidate = _strict_csv_row(
        attempt,
        "candidate_outputs.csv",
        frozenset({tuple(CANDIDATE_HEADERS)}),
    )
    qc_profiles = QC_HEADER_PROFILES.get(method)
    qc = (
        _strict_csv_row(attempt, "candidate_qc.csv", qc_profiles)
        if qc_profiles is not None
        else None
    )
    if manifest is None or candidate is None or qc is None:
        return False

    expected_stage = job.get("seed_stage", "primary")
    try:
        adapter = load_adapter(method)
    except (ImportError, ValueError):
        return False
    try:
        command = shlex.split(manifest.get("command", ""))
    except ValueError:
        return False
    manifest_ok = all(
        (
            all(manifest.values()),
            manifest.get("run_record_id") == f"{job_id}_{attempt.name}",
            manifest.get("job_id") == job_id,
            manifest.get("method") == method,
            not job.get("task_id") or manifest.get("task_id") == job.get("task_id"),
            manifest.get("execution_stage") == expected_stage,
            manifest.get("source_commit") == getattr(adapter, "SOURCE_COMMIT", None),
            manifest.get("model_revision") == getattr(adapter, "MODEL_REVISION", None),
            manifest.get("environment_id") == execution.get("container_or_env"),
            manifest.get("status") == result.get("status"),
            manifest.get("status_reason") == result.get("status_reason"),
            manifest.get("parser_status") == parser_status,
            manifest.get("overall_qc_status") == overall_qc_status,
            manifest.get("runtime_seconds") == result.get("runtime_seconds"),
            manifest.get("created_at") == result.get("created_at"),
            _positive_finite_float(manifest.get("runtime_seconds")) == runtime_seconds,
            _timezone_aware_timestamp(manifest.get("created_at")) == created_at,
            manifest.get("exit_code") == "0",
            manifest.get("raw_output_root") == str(attempt / "raw"),
            manifest.get("stdout_log") == str(attempt / "stdout.log"),
            manifest.get("stderr_log") == str(attempt / "stderr.log"),
            command == ["bash", str(attempt / "command.sh")],
        )
    )
    candidate_ok = all(
        (
            candidate.get("job_id") == job_id,
            candidate.get("method") == method,
            candidate.get("design_id") == design_id,
            candidate.get("target_id") == job.get("target_id"),
            candidate.get("binder_id") == f"{job_id}_binder_1",
            candidate.get("generation_rank") == "1",
            candidate.get("binder_chain") == job.get("expected_binder_chain"),
            candidate.get("peptide_type") == job.get("peptide_type"),
            candidate.get("chirality") == job.get("chirality"),
            candidate.get("cyclic") == job.get("cyclic"),
            candidate.get("parse_status") == parser_status,
            bool(candidate.get("sequence")),
            bool(candidate.get("status_reason")),
            _candidate_paths_match_method(job, attempt, candidate),
        )
    )
    qc_ok = all(
        (
            qc.get("job_id") == job_id,
            qc.get("design_id") == design_id,
            qc.get("overall_qc_status") == overall_qc_status,
            _qc_supports_candidate(job, qc, str(overall_qc_status)),
        )
    )
    return (
        manifest_ok
        and candidate_ok
        and qc_ok
        and _snapshot_replay_matches(
            job,
            execution,
            attempt,
            result,
            manifest,
            candidate,
            qc,
        )
    )


def _invalid_resume_result(job: Mapping[str, str], attempt: Path) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "method": job["method"],
        "attempt_dir": str(attempt),
        "status": "resume_skipped_invalid",
        "status_reason": "latest_run_result_invalid",
        "overall_qc_status": "not_run",
    }


def _resume_existing_result(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    attempt: Path,
    *,
    execute: bool,
) -> dict[str, Any]:
    prior = _read_attempt_json_object(attempt, "run_result.json")
    if prior is None or not isinstance(prior.get("status"), str):
        return _invalid_resume_result(job, attempt)

    prior_status = prior["status"]
    if prior_status == "passed":
        if not _passed_attempt_is_complete(job, execution, attempt, prior):
            return _invalid_resume_result(job, attempt)
        status = "resume_skipped_passed"
    elif prior_status == "packaged" and not execute:
        status = "resume_skipped_packaged"
    else:
        status = "resume_skipped_failed"
    return {
        **prior,
        "job_id": job["job_id"],
        "method": job["method"],
        "attempt_dir": str(attempt),
        "resumed_from_status": prior_status,
        "status": status,
    }


def primary_is_eligible(primary_job_root: Path) -> bool:
    try:
        attempt = _latest_attempt(primary_job_root)
    except ValueError:
        return False
    if attempt is None:
        return False
    result = _read_attempt_json_object(attempt, "run_result.json")
    if result is None:
        return False
    matching_jobs = [
        job
        for job in load_jobs(stage="primary")
        if job.get("job_id") == primary_job_root.name
    ]
    if len(matching_jobs) != 1:
        return False
    job = matching_jobs[0]
    try:
        run_root = _inferred_run_root(primary_job_root)
        expected_job_root = _job_root(run_root, job)
        execution = load_execution_matrix()[job["job_id"]]
    except (KeyError, ValueError):
        return False
    if expected_job_root.absolute() != primary_job_root.absolute():
        return False
    return result.get("status") == "passed" and _passed_attempt_is_complete(
        job, execution, attempt, result
    )


def execution_status(*, exit_code: int, timed_out: bool, parsed: bool, qc: str) -> str:
    if timed_out:
        return "execution_timeout"
    if exit_code != 0:
        return "execution_failed"
    if not parsed:
        return "parse_failed"
    if qc not in {"pass", "pass_with_warning"}:
        return "qc_failed"
    return "passed"


def load_adapter(method: str) -> Any:
    try:
        module_name = ADAPTER_MODULES[method]
    except KeyError as exc:
        raise ValueError(f"No v0.34 adapter registered for {method}") from exc
    return importlib.import_module(module_name)


def validate_mode(*, dry_run: bool, execute: bool) -> None:
    if dry_run == execute:
        raise ValueError("select exactly one of --dry-run or --execute")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _job_root(run_root: Path, job: Mapping[str, str]) -> Path:
    try:
        slug = METHOD_SLUGS[job["method"]]
    except KeyError as exc:
        raise ValueError(f"No v0.34 method slug registered for {job.get('method', '')}") from exc
    job_id = job.get("job_id", "")
    if (
        not job_id
        or job_id in {".", ".."}
        or Path(job_id).name != job_id
        or "/" in job_id
        or "\\" in job_id
    ):
        raise ValueError(f"unsafe job_id outside run root: {job_id}")
    return Path(run_root) / slug / job_id


def _candidate_row(job: Mapping[str, str], candidate: Mapping[str, Any]) -> dict[str, Any]:
    job_id = job["job_id"]
    row = {
        "design_id": f"{job_id}_candidate_1",
        "job_id": job_id,
        "method": job["method"],
        "target_id": job.get("target_id", ""),
        "binder_id": f"{job_id}_binder_1",
        "source_output_id": Path(str(candidate.get("source_output_path", ""))).name,
        "generation_rank": "1",
        "sequence": "",
        "structure_path": "",
        "source_output_path": "",
        "binder_chain": job.get("expected_binder_chain", job.get("binder_chain", "")),
        "peptide_type": job.get("peptide_type", ""),
        "chirality": job.get("chirality", ""),
        "cyclic": job.get("cyclic", ""),
        "parse_status": "failed",
        "status_reason": "adapter_parse_failed",
        "notes": "Bounded connectivity evidence only; not Benchmark result or scoring evidence",
    }
    row.update(candidate)
    return row


def _write_method_output_manifest(
    attempt: Path,
    job: Mapping[str, str],
    execution: Mapping[str, str],
    adapter: Any,
    command: list[str],
    result: Mapping[str, Any],
) -> None:
    attempt_id = attempt.name
    row = {
        "run_record_id": f"{job['job_id']}_{attempt_id}",
        "job_id": job["job_id"],
        "method": job["method"],
        "task_id": job.get("task_id", ""),
        "execution_stage": job.get("seed_stage", ""),
        "source_commit": getattr(adapter, "SOURCE_COMMIT", "unrecorded"),
        "model_revision": getattr(adapter, "MODEL_REVISION", "unrecorded"),
        "environment_id": execution.get("container_or_env", ""),
        "command": shlex.join(command) if command else "",
        "raw_output_root": str(attempt / "raw"),
        "stdout_log": str(attempt / "stdout.log") if (attempt / "stdout.log").is_file() else "",
        "stderr_log": str(attempt / "stderr.log") if (attempt / "stderr.log").is_file() else "",
        "runtime_seconds": result.get("runtime_seconds", "0.000"),
        "exit_code": result.get("exit_code", ""),
        "parser_status": result.get("parser_status", "not_run"),
        "overall_qc_status": result.get("overall_qc_status", "not_run"),
        "status": result.get("status", "unknown"),
        "status_reason": result.get("status_reason", "unknown"),
        "created_at": result.get("created_at", _utc_now()),
    }
    write_csv(attempt / "method_output_manifest.csv", METHOD_OUTPUT_HEADERS, [row])


def _finish(
    attempt: Path,
    job: Mapping[str, str],
    execution: Mapping[str, str],
    adapter: Any,
    command: list[str],
    result: dict[str, Any],
) -> dict[str, Any]:
    result.setdefault("job_id", job["job_id"])
    result.setdefault("method", job["method"])
    result.setdefault("attempt_dir", str(attempt))
    result.setdefault("created_at", _utc_now())
    result.setdefault("overall_qc_status", "not_run")
    result.setdefault("parser_status", "not_run")
    result.setdefault("runtime_seconds", "0.000")
    result.setdefault("exit_code", "")
    _write_json(attempt / "run_result.json", result)
    _write_method_output_manifest(attempt, job, execution, adapter, command, result)
    return result


def run_job(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    *,
    run_root: Path = DEFAULT_RUN_ROOT,
    execute: bool,
    retry_failed: bool,
    adapter: Any | None = None,
    qc_evaluator: Any | None = None,
) -> dict[str, Any]:
    """Package one immutable attempt and optionally run its bounded command."""

    adapter = adapter or load_adapter(job["method"])
    if qc_evaluator is None:
        qc_evaluator = evaluate_candidate_qc
    attempt = allocate_attempt_dir(
        _job_root(run_root, job),
        retry_failed=retry_failed,
        run_root=run_root,
    )
    _write_json(attempt / "job.json", job)
    _write_json(attempt / "execution.json", execution)
    command: list[str] = []
    try:
        prepared = adapter.prepare(job, execution, attempt)
        if not isinstance(prepared, list) or not prepared or not all(
            isinstance(token, str) and token for token in prepared
        ):
            raise ValueError("adapter returned an invalid command")
        command = prepared
        _write_json(attempt / "command.json", {"arguments": command})
    except Exception as exc:  # The attempt must retain exact preflight failure evidence.
        return _finish(
            attempt,
            job,
            execution,
            adapter,
            command,
            {"status": "preflight_failed", "status_reason": f"{type(exc).__name__}: {exc}"},
        )

    if not execute:
        return _finish(
            attempt,
            job,
            execution,
            adapter,
            command,
            {"status": "packaged", "status_reason": "command_packaged_not_executed"},
        )

    started = time.monotonic()
    try:
        completed = run_bounded_process(
            attempt,
            command,
            label=job["job_id"],
            timeout=int(execution.get("max_runtime_sec", "0")),
            environment=os.environ.copy(),
        )
    except BoundedProcessError as exc:
        elapsed = f"{time.monotonic() - started:.3f}"
        (attempt / "stdout.log").write_text("", encoding="utf-8")
        (attempt / "stderr.log").write_text(str(exc) + "\n", encoding="utf-8")
        status = "execution_timeout" if exc.code == "timeout" else "execution_failed"
        return _finish(
            attempt,
            job,
            execution,
            adapter,
            command,
            {
                "status": status,
                "status_reason": exc.code,
                "runtime_seconds": elapsed,
                "exit_code": 124 if exc.code == "timeout" else (exc.returncode or ""),
            },
        )

    elapsed = f"{time.monotonic() - started:.3f}"
    (attempt / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (attempt / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        return _finish(
            attempt,
            job,
            execution,
            adapter,
            command,
            {
                "status": "execution_failed",
                "status_reason": f"process_exit_{completed.returncode}",
                "runtime_seconds": elapsed,
                "exit_code": completed.returncode,
            },
        )

    try:
        candidate_value, runtime = adapter.parse(job, attempt)
        candidate = _candidate_row(job, candidate_value)
    except Exception as exc:
        return _finish(
            attempt,
            job,
            execution,
            adapter,
            command,
            {
                "status": "parse_failed",
                "status_reason": f"{type(exc).__name__}: {exc}",
                "runtime_seconds": elapsed,
                "exit_code": completed.returncode,
                "parser_status": "failed",
            },
        )

    parsed = candidate.get("parse_status") in {"parsed", "partial"}
    write_csv(attempt / "candidate_outputs.csv", CANDIDATE_HEADERS, [candidate])
    try:
        qc = qc_evaluator(job, candidate, runtime, attempt / "raw")
    except Exception as exc:
        qc = {
            "overall_qc_status": "fail",
            "status_reason": f"qc_exception_{type(exc).__name__}: {exc}",
        }
    qc_row = {"job_id": job["job_id"], "design_id": candidate["design_id"], **qc}
    write_csv(attempt / "candidate_qc.csv", qc_row.keys(), [qc_row])
    qc_status = str(qc.get("overall_qc_status", "fail"))
    status = execution_status(
        exit_code=completed.returncode,
        timed_out=False,
        parsed=parsed,
        qc=qc_status,
    )
    reason = (
        candidate.get("status_reason", "parse_failed")
        if status == "parse_failed"
        else str(qc.get("status_reason", "qc_failed"))
        if status == "qc_failed"
        else "bounded_connectivity_candidate_qc_passed"
    )
    return _finish(
        attempt,
        job,
        execution,
        adapter,
        command,
        {
            "status": status,
            "status_reason": reason,
            "runtime_seconds": elapsed,
            "exit_code": completed.returncode,
            "parser_status": candidate.get("parse_status", "failed"),
            "overall_qc_status": qc_status,
            "design_id": candidate["design_id"],
        },
    )


def run_stage(
    *,
    stage: str,
    run_root: Path,
    execute: bool,
    resume: bool,
    retry_failed: bool,
    job_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    jobs = load_jobs(stage=stage, job_ids=job_ids)
    matrix = load_execution_matrix()
    results: list[dict[str, Any]] = []
    for job in jobs:
        job_root = _job_root(run_root, job)
        if stage == "extension":
            primary_id = job.get("primary_job_id", "")
            primary_job = next(
                (row for row in load_jobs(stage="primary") if row["job_id"] == primary_id), None
            )
            if primary_job is None or not primary_is_eligible(_job_root(run_root, primary_job)):
                results.append(
                    {
                        "job_id": job["job_id"],
                        "method": job["method"],
                        "status": "blocked_primary_not_passed",
                        "overall_qc_status": "not_run",
                    }
                )
                continue
        try:
            latest = _latest_attempt(job_root, run_root=run_root)
        except ValueError:
            results.append(
                {
                    "job_id": job["job_id"],
                    "method": job["method"],
                    "attempt_dir": str(job_root),
                    "status": "resume_skipped_invalid",
                    "status_reason": "unsafe_attempt_path",
                    "overall_qc_status": "not_run",
                }
            )
            continue
        if resume and latest is not None:
            results.append(
                _resume_existing_result(
                    job,
                    matrix[job["job_id"]],
                    latest,
                    execute=execute,
                )
            )
            continue
        results.append(
            run_job(
                job,
                matrix[job["job_id"]],
                run_root=run_root,
                execute=execute,
                retry_failed=retry_failed,
            )
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("primary", "extension"), required=True)
    parser.add_argument("--jobs", nargs="*")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    recovery = parser.add_mutually_exclusive_group()
    recovery.add_argument("--resume", action="store_true")
    recovery.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    validate_mode(dry_run=args.dry_run, execute=args.execute)
    results = run_stage(
        stage=args.stage,
        run_root=args.run_root,
        execute=args.execute,
        resume=args.resume,
        retry_failed=args.retry_failed,
        job_ids=set(args.jobs) if args.jobs else None,
    )
    summary = {
        "stage": args.stage,
        "execute": args.execute,
        "jobs": len(results),
        "status_counts": {
            status: sum(result.get("status") == status for result in results)
            for status in sorted({str(result.get("status", "unknown")) for result in results})
        },
        "results": results,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    successful_statuses = {
        "packaged",
        "passed",
        "resume_skipped_packaged",
        "resume_skipped_passed",
        "blocked_primary_not_passed",
    }
    return 0 if all(result.get("status") in successful_statuses for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
