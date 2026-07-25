from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, Mapping

from .common import (
    parse_pdb_chain_sequences,
    require_clean_git_checkout,
    require_file_sha256,
    validate_output_file,
)


METHOD = "PepGLAD"
SOURCE_COMMIT = "bad015ca50c312a89482adb5220c3d907f13df5c"
MODEL_REVISION = "codesign.ckpt_external_manifest_v0.21"
SOURCE_ROOT = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepGLAD")
MODEL_ROOT = Path("/data/protein-design/data/benchmark_models/pepglad/checkpoints")
SOURCE_ENTRYPOINT = SOURCE_ROOT / "api/run.py"
SOURCE_ENTRYPOINT_SHA256 = "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
MODEL_WEIGHTS = MODEL_ROOT / "codesign.ckpt"
MODEL_WEIGHTS_SHA256 = "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
DEFAULT_IMAGE = "pd-benchmark-methods-gpu:0.21"
DEFAULT_ENV = "bench-pepglad"
SEED42_POST_RELAX_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)
RECOVERY_MODE = "instrumented_official_pipeline"
PEPGLAD_LEGACY_RUNTIME_FIELDS = frozenset(
    {
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "source_candidate_path",
        "container_image",
        "conda_environment",
    }
)
PEPGLAD_LEGACY_SOURCE_CANDIDATE_PATH = "/data/attempt/work/codesign/3EQS_0.pdb"
OBSERVER_SCRIPT_SHA256 = (
    "a0a98420dd2fd5382479abe77526fb8fc206ffb1e69a8780912fb821dded0c61"
)
INSTRUMENTER_SCRIPT_SHA256 = (
    "cd9ec19f6605fd2b067824d4e02971b3a203e827b6398a4ffd1c68c64464311a"
)
SEED_WRAPPER_SCRIPT_SHA256 = (
    "6a9b4c9012205d27526e13dbccbd7d11c010eddc3c85acdb2796c2fa6668aaba"
)
SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256 = (
    "c3b127e39be1b335ff6046bb2435451acfc1b323839377033bf438ccd4a32954"
)


SEED_WRAPPER_SCRIPT = '''#!/usr/bin/env python3
import argparse
import random
import runpy
import sys

import numpy as np
import torch

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--seed", type=int, required=True)
args, remaining = parser.parse_known_args()
SEED = args.seed
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
sys.argv = ["api.run", *remaining]
runpy.run_module("api.run", run_name="__main__")
'''


OBSERVER_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def capture_pre_relax_pdb(pdb_path: str) -> str:
    source = Path(pdb_path)
    destination_text = os.environ.get("V034_PRE_RELAX_PATH", "")
    if not destination_text:
        raise RuntimeError("V034_PRE_RELAX_PATH is required")
    destination = Path(destination_text)
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f"invalid PepGLAD pre-relax source: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = source.read_bytes()
    if not payload:
        raise RuntimeError("PepGLAD pre-relax source is empty")
    try:
        with destination.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise RuntimeError(f"PepGLAD pre-relax evidence already exists: {destination}") from exc
    if destination.read_bytes() != payload:
        raise RuntimeError("PepGLAD pre-relax byte copy verification failed")
    return str(destination)


def chirality_counts(path: str, chain: str) -> dict[str, Any]:
    residues: dict[tuple[str, str, str], dict[str, tuple[float, float, float]]] = {}
    residue_names: dict[tuple[str, str, str], str] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 54:
            continue
        if line[16].strip() not in {"", "A"}:
            continue
        observed_chain = line[21].strip() or "_"
        if observed_chain != chain:
            continue
        key = (observed_chain, line[22:26].strip(), line[26].strip())
        atom = line[12:16].strip().upper()
        try:
            xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        except ValueError:
            continue
        residues.setdefault(key, {})[atom] = xyz
        residue_names[key] = line[17:20].strip().upper()

    l_count = d_count = gly_count = unknown_count = 0
    for key, atoms in residues.items():
        if residue_names.get(key) == "GLY":
            gly_count += 1
            continue
        if not all(atom in atoms for atom in ("N", "CA", "C", "CB")):
            unknown_count += 1
            continue
        ca = atoms["CA"]
        n_vec = tuple(left - right for left, right in zip(atoms["N"], ca))
        c_vec = tuple(left - right for left, right in zip(atoms["C"], ca))
        cb_vec = tuple(left - right for left, right in zip(atoms["CB"], ca))
        cross = (
            n_vec[1] * c_vec[2] - n_vec[2] * c_vec[1],
            n_vec[2] * c_vec[0] - n_vec[0] * c_vec[2],
            n_vec[0] * c_vec[1] - n_vec[1] * c_vec[0],
        )
        signed_volume = sum(left * right for left, right in zip(cross, cb_vec))
        if signed_volume > 0:
            l_count += 1
        elif signed_volume < 0:
            d_count += 1
        else:
            unknown_count += 1
    evaluable = l_count + d_count
    return {
        "chain": chain,
        "evaluable": evaluable,
        "l_count": l_count,
        "d_count": d_count,
        "gly_count": gly_count,
        "unknown_count": unknown_count,
        "status": "pass" if evaluable > 0 and unknown_count == 0 else "fail",
    }
'''


INSTRUMENTER_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ANCHOR = b"def openmm_relax(pdb_path):\n    force_field = ForceFieldMinimizer()\n"
REPLACEMENT = (
    b"def openmm_relax(pdb_path):\n"
    b"    from pepglad_observer import capture_pre_relax_pdb\n"
    b"    capture_pre_relax_pdb(pdb_path)\n"
    b"    force_field = ForceFieldMinimizer()\n"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_digest(path: Path, expected: str, label: str) -> str:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"invalid {label}: {path}")
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(f"{label} SHA256 mismatch: expected {expected}, observed {observed}")
    return observed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-entrypoint", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--expected-instrumented-source-sha256", required=True)
    parser.add_argument("--observer-source", type=Path, required=True)
    parser.add_argument("--expected-observer-sha256", required=True)
    parser.add_argument("--expected-patch-sha256", required=True)
    parser.add_argument("--target-input", type=Path, required=True)
    parser.add_argument("--expected-target-sha256", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    patch_path = Path(__file__).resolve()
    patch_digest = require_digest(
        patch_path, args.expected_patch_sha256, "PepGLAD observer patch"
    )
    observer_digest = require_digest(
        args.observer_source,
        args.expected_observer_sha256,
        "PepGLAD observer source",
    )
    target_digest = require_digest(
        args.target_input, args.expected_target_sha256, "PepGLAD target input"
    )
    source_digest = require_digest(
        args.source_entrypoint,
        args.expected_source_sha256,
        "PepGLAD source entrypoint",
    )
    source = args.source_entrypoint.read_bytes()
    if source.count(ANCHOR) != 1:
        raise RuntimeError("PepGLAD OpenMM observer anchor must occur exactly once")
    instrumented = source.replace(ANCHOR, REPLACEMENT, 1)
    args.source_entrypoint.write_bytes(instrumented)
    instrumented_digest = require_digest(
        args.source_entrypoint,
        args.expected_instrumented_source_sha256,
        "PepGLAD instrumented source",
    )
    attempt_root = args.evidence.parent.resolve(strict=True)

    def attempt_relative(path: Path, label: str) -> str:
        try:
            return path.resolve(strict=True).relative_to(attempt_root).as_posix()
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"{label} must be inside the PepGLAD attempt") from exc

    evidence = {
        "observer_injection_status": "applied",
        "observer_patch_path": attempt_relative(patch_path, "observer patch"),
        "observer_patch_sha256": patch_digest,
        "observer_source_path": attempt_relative(
            args.observer_source, "observer source"
        ),
        "observer_source_sha256": observer_digest,
        "source_entrypoint_path": attempt_relative(
            args.source_entrypoint, "source entrypoint"
        ),
        "source_entrypoint_prepatch_sha256": source_digest,
        "source_entrypoint_instrumented_sha256": instrumented_digest,
        "source_copy_mode": "attempt_local_copy",
        "target_input_path": str(args.target_input),
        "target_input_sha256": target_digest,
        "target_preflight_verified": True,
    }
    args.evidence.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
'''


FINALIZER_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_regular(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
        raise RuntimeError(f"invalid {label}: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pre-relax", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-source", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--patch-evidence", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--observer-patch", type=Path, required=True)
    parser.add_argument("--observer-source", type=Path, required=True)
    parser.add_argument("--seed-wrapper", type=Path, required=True)
    parser.add_argument("--instrumented-source", type=Path, required=True)
    parser.add_argument("--target-input", type=Path, required=True)
    parser.add_argument("--expected-target-sha256", required=True)
    parser.add_argument("--binder-chain", required=True)
    parser.add_argument("--expected-chirality", choices=("L", "D"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--source-commit", required=False, default="")
    parser.add_argument("--source-entrypoint-sha256", required=False, default="")
    parser.add_argument("--model-weights-sha256", required=False, default="")
    parser.add_argument("--container-image", required=False, default="")
    parser.add_argument("--conda-environment", required=False, default="")
    args = parser.parse_args()

    if (
        not args.attempt_root.is_dir()
        or args.attempt_root.is_symlink()
    ):
        raise RuntimeError(f"invalid PepGLAD attempt root: {args.attempt_root}")
    attempt_root = args.attempt_root.resolve(strict=True)

    def attempt_relative(path: Path, label: str) -> str:
        try:
            resolved = path.resolve(strict=path.exists())
            return resolved.relative_to(attempt_root).as_posix()
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"{label} must be inside the PepGLAD attempt") from exc

    bound_paths = {
        "source": attempt_relative(args.source, "official post-relax PDB"),
        "pre_relax": attempt_relative(args.pre_relax, "pre-relax PDB"),
        "output": attempt_relative(args.output, "candidate output"),
        "summary_source": attempt_relative(args.summary_source, "official summary"),
        "summary_output": attempt_relative(args.summary_output, "summary output"),
        "runtime": attempt_relative(args.runtime, "runtime evidence"),
        "patch_evidence": attempt_relative(args.patch_evidence, "patch evidence"),
        "observer_patch": attempt_relative(args.observer_patch, "observer patch"),
        "observer_source": attempt_relative(args.observer_source, "observer source"),
        "seed_wrapper": attempt_relative(args.seed_wrapper, "seed wrapper"),
        "instrumented_source": attempt_relative(
            args.instrumented_source, "instrumented source"
        ),
    }

    for path, label in (
        (args.source, "PepGLAD official post-relax PDB"),
        (args.pre_relax, "PepGLAD observed pre-relax PDB"),
        (args.summary_source, "PepGLAD official summary"),
        (args.patch_evidence, "PepGLAD observer evidence"),
        (args.observer_patch, "PepGLAD observer patch"),
        (args.observer_source, "PepGLAD observer source"),
        (args.seed_wrapper, "PepGLAD seed wrapper"),
        (args.instrumented_source, "PepGLAD instrumented entrypoint"),
        (args.target_input, "PepGLAD target input"),
    ):
        require_regular(path, label)
    patch = json.loads(args.patch_evidence.read_text(encoding="utf-8"))
    if not isinstance(patch, dict):
        raise RuntimeError("PepGLAD observer evidence must be an object")
    checks = (
        patch.get("observer_injection_status") == "applied",
        patch.get("target_preflight_verified") is True,
        patch.get("target_input_sha256") == args.expected_target_sha256,
        sha256(args.target_input) == args.expected_target_sha256,
        patch.get("observer_patch_path") == bound_paths["observer_patch"],
        patch.get("observer_patch_sha256") == sha256(args.observer_patch),
        patch.get("observer_source_path") == bound_paths["observer_source"],
        patch.get("observer_source_sha256") == sha256(args.observer_source),
        patch.get("source_entrypoint_path") == bound_paths["instrumented_source"],
        patch.get("source_entrypoint_instrumented_sha256")
        == sha256(args.instrumented_source),
    )
    if not all(checks):
        raise RuntimeError("PepGLAD observer evidence verification failed")
    if args.source_entrypoint_sha256 and (
        patch.get("source_entrypoint_prepatch_sha256")
        != args.source_entrypoint_sha256
    ):
        raise RuntimeError("PepGLAD source entrypoint prepatch SHA256 mismatch")

    spec = importlib.util.spec_from_file_location("pepglad_observer", args.observer_source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PepGLAD observer source")
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.source, args.output)
    shutil.copyfile(args.summary_source, args.summary_output)
    source_digest = sha256(args.source)
    output_digest = sha256(args.output)
    if source_digest != output_digest:
        raise RuntimeError("PepGLAD post-relax byte copy verification failed")
    pre_digest = sha256(args.pre_relax)
    if args.seed == 42:
        replay_status = "match" if output_digest == args.baseline_sha256 else "mismatch"
        replay_expected = args.baseline_sha256
    else:
        replay_status = "not_applicable"
        replay_expected = ""
    pre_chirality = observer.chirality_counts(
        str(args.pre_relax), args.binder_chain
    )
    post_chirality = observer.chirality_counts(
        str(args.output), args.binder_chain
    )

    def chirality_passes(stats: dict[str, object]) -> bool:
        expected_key = "l_count" if args.expected_chirality == "L" else "d_count"
        return (
            stats.get("status") == "pass"
            and isinstance(stats.get("evaluable"), int)
            and stats.get("evaluable", 0) > 0
            and stats.get(expected_key) == stats.get("evaluable")
        )

    if not chirality_passes(pre_chirality):
        first_failure_stage = "pre_openmm_snapshot"
    elif not chirality_passes(post_chirality):
        first_failure_stage = "post_openmm_relaxation"
    else:
        first_failure_stage = "none_observed"
    runtime = {
        "requested_seed": args.seed,
        "effective_seed": args.seed,
        "seed_control_status": "honored",
        "recovery_mode": "instrumented_official_pipeline",
        "source_candidate_path": bound_paths["source"],
        "pre_relax_path": bound_paths["pre_relax"],
        "pre_relax_sha256": pre_digest,
        "post_relax_path": bound_paths["output"],
        "post_relax_sha256": output_digest,
        "official_candidate_stage": "post_openmm_relaxation",
        "pre_relax_role": "diagnostic_evidence_only",
        "binder_chain": args.binder_chain,
        "expected_chirality": args.expected_chirality,
        "pre_relax_binder_chirality": pre_chirality,
        "post_relax_binder_chirality": post_chirality,
        "first_observed_chirality_failure_stage": first_failure_stage,
        "baseline_replay_expected_sha256": replay_expected,
        "baseline_replay_observed_sha256": output_digest,
        "baseline_replay_status": replay_status,
        "observer_patch_evidence_path": bound_paths["patch_evidence"],
        "observer_patch_evidence_sha256": sha256(args.patch_evidence),
        "observer_patch_path": bound_paths["observer_patch"],
        "observer_patch_sha256": patch["observer_patch_sha256"],
        "observer_source_path": bound_paths["observer_source"],
        "observer_source_sha256": patch["observer_source_sha256"],
        "seed_wrapper_path": bound_paths["seed_wrapper"],
        "seed_wrapper_sha256": sha256(args.seed_wrapper),
        "instrumented_source_path": bound_paths["instrumented_source"],
        "source_entrypoint_prepatch_sha256": patch[
            "source_entrypoint_prepatch_sha256"
        ],
        "source_entrypoint_instrumented_sha256": patch[
            "source_entrypoint_instrumented_sha256"
        ],
        "target_input_sha256": args.expected_target_sha256,
        "target_preflight_verified": True,
        "source_commit": args.source_commit,
        "source_entrypoint_sha256": args.source_entrypoint_sha256,
        "model_weights_sha256": args.model_weights_sha256,
        "container_image": args.container_image,
        "conda_environment": args.conda_environment,
    }
    args.runtime.write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
'''


class _DuplicateJsonKeyError(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJsonKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _runtime_evidence(job: Mapping[str, str], raw: Path) -> dict[str, Any]:
    requested = int(job.get("random_seed", "-1"))
    fallback: dict[str, Any] = {
        "requested_seed": requested,
        "effective_seed": -1,
        "seed_control_status": "missing",
    }
    try:
        value = json.loads(
            (raw / "runtime_evidence.json").read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, _DuplicateJsonKeyError):
        return fallback
    if isinstance(value, dict):
        fallback.update(value)
    return fallback


def _failed(reason: str) -> dict[str, str]:
    return {
        "sequence": "",
        "structure_path": "",
        "source_output_path": "",
        "binder_chain": "B",
        "parse_status": "failed",
        "status_reason": reason,
    }


def _legacy_seed42_replay_valid(
    runtime: Mapping[str, Any], output_sha256: object
) -> bool:
    return all(
        (
            set(runtime) == PEPGLAD_LEGACY_RUNTIME_FIELDS,
            output_sha256 == SEED42_POST_RELAX_BASELINE_SHA256,
            runtime.get("requested_seed") == 42,
            runtime.get("effective_seed") == 42,
            runtime.get("seed_control_status") == "honored",
            runtime.get("source_commit") == SOURCE_COMMIT,
            runtime.get("source_entrypoint_sha256") == SOURCE_ENTRYPOINT_SHA256,
            runtime.get("model_weights_sha256") == MODEL_WEIGHTS_SHA256,
            runtime.get("source_candidate_path")
            == PEPGLAD_LEGACY_SOURCE_CANDIDATE_PATH,
            runtime.get("container_image") == DEFAULT_IMAGE,
            runtime.get("conda_environment") == DEFAULT_ENV,
        )
    )


def prepare(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    attempt_dir: Path,
) -> list[str]:
    attempt_dir = Path(attempt_dir)
    raw = attempt_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    seed = int(job["random_seed"])
    minimum = int(job.get("length_min", "11"))
    maximum = int(job.get("length_max", str(minimum)))
    if minimum != maximum or minimum <= 0:
        raise ValueError("PepGLAD v0.34 requires one fixed positive peptide length")
    target = Path(job["target_pdb_path"]).resolve()
    target_digest = require_file_sha256(
        target,
        job.get("target_pdb_sha256", ""),
        "PepGLAD target input",
    )
    source_commit = require_clean_git_checkout(SOURCE_ROOT, SOURCE_COMMIT, "PepGLAD source")
    source_digest = require_file_sha256(
        SOURCE_ENTRYPOINT, SOURCE_ENTRYPOINT_SHA256, "PepGLAD inference source"
    )
    model_digest = require_file_sha256(
        MODEL_WEIGHTS, MODEL_WEIGHTS_SHA256, "PepGLAD codesign checkpoint"
    )
    environment = execution.get("container_or_env", "")
    image, _, conda_env = environment.partition("/")
    image = image or DEFAULT_IMAGE
    conda_env = conda_env or DEFAULT_ENV

    entry = attempt_dir / "pepglad_seeded_entry.py"
    entry.write_text(SEED_WRAPPER_SCRIPT, encoding="utf-8")
    entry.chmod(0o755)
    require_file_sha256(
        entry,
        SEED_WRAPPER_SCRIPT_SHA256,
        "PepGLAD seed wrapper script",
    )

    observer = attempt_dir / "pepglad_observer.py"
    observer.write_text(OBSERVER_SCRIPT, encoding="utf-8")
    observer.chmod(0o755)
    observer_digest = require_file_sha256(
        observer,
        OBSERVER_SCRIPT_SHA256,
        "PepGLAD observer script",
    )

    instrumenter = attempt_dir / "pepglad_instrument_source.py"
    instrumenter.write_text(INSTRUMENTER_SCRIPT, encoding="utf-8")
    instrumenter.chmod(0o755)
    instrumenter_digest = require_file_sha256(
        instrumenter,
        INSTRUMENTER_SCRIPT_SHA256,
        "PepGLAD instrumenter script",
    )

    finalizer = attempt_dir / "pepglad_finalize.py"
    finalizer.write_text(FINALIZER_SCRIPT, encoding="utf-8")
    finalizer.chmod(0o755)

    exclusive_maximum = maximum + 1
    instrument_command = shlex.join(
        [
            "python",
            "/data/attempt/pepglad_instrument_source.py",
            "--source-entrypoint",
            "/data/attempt/work/api/run.py",
            "--expected-source-sha256",
            source_digest,
            "--expected-instrumented-source-sha256",
            SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256,
            "--observer-source",
            "/data/attempt/pepglad_observer.py",
            "--expected-observer-sha256",
            observer_digest,
            "--expected-patch-sha256",
            instrumenter_digest,
            "--target-input",
            "/data/input/3EQS.pdb",
            "--expected-target-sha256",
            target_digest,
            "--evidence",
            "/data/attempt/observer_patch_evidence.json",
        ]
    )
    finalize_command = shlex.join(
        [
            "python",
            "/data/attempt/pepglad_finalize.py",
            "--source",
            "/data/attempt/work/codesign/3EQS_0.pdb",
            "--pre-relax",
            "/data/attempt/raw/pepglad_pre_relax.pdb",
            "--output",
            "/data/attempt/raw/pepglad_candidate.pdb",
            "--summary-source",
            "/data/attempt/work/codesign/summary.jsonl",
            "--summary-output",
            "/data/attempt/raw/pepglad_summary.jsonl",
            "--runtime",
            "/data/attempt/raw/runtime_evidence.json",
            "--patch-evidence",
            "/data/attempt/observer_patch_evidence.json",
            "--attempt-root",
            "/data/attempt",
            "--observer-patch",
            "/data/attempt/pepglad_instrument_source.py",
            "--observer-source",
            "/data/attempt/pepglad_observer.py",
            "--seed-wrapper",
            "/data/attempt/pepglad_seeded_entry.py",
            "--instrumented-source",
            "/data/attempt/work/api/run.py",
            "--target-input",
            "/data/input/3EQS.pdb",
            "--expected-target-sha256",
            target_digest,
            "--binder-chain",
            job.get("expected_binder_chain", "B") or "B",
            "--expected-chirality",
            job.get("chirality", "L") or "L",
            "--seed",
            str(seed),
            "--baseline-sha256",
            SEED42_POST_RELAX_BASELINE_SHA256,
            "--source-commit",
            source_commit,
            "--source-entrypoint-sha256",
            source_digest,
            "--model-weights-sha256",
            model_digest,
            "--container-image",
            image,
            "--conda-environment",
            conda_env,
        ]
    )
    inner = "\n".join(
        [
            "set -euo pipefail",
            "source /opt/conda/etc/profile.d/conda.sh",
            f"conda activate {shlex.quote(conda_env)}",
            "work=/data/attempt/work",
            'rm -rf "$work"',
            'mkdir -p "$work/input"',
            'cp -a /data/source/. "$work/"',
            'cp /data/input/3EQS.pdb "$work/input/3EQS.pdb"',
            instrument_command,
            'cd "$work"',
            "mkdir -p checkpoints",
            "ln -sf /data/models/codesign.ckpt checkpoints/codesign.ckpt",
            'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="/data/attempt:$work:${PYTHONPATH:-}" '
            "python -m api.detect_pocket "
            "--pdb input/3EQS.pdb --target_chains A --ligand_chains B --out input/3EQS_pocket.json",
            'V034_PRE_RELAX_PATH=/data/attempt/raw/pepglad_pre_relax.pdb '
            'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="/data/attempt:$work:${PYTHONPATH:-}" '
            "python /data/attempt/pepglad_seeded_entry.py "
            f"--seed {seed} --mode codesign --pdb input/3EQS.pdb --pocket input/3EQS_pocket.json "
            f"--out_dir codesign --length_min {minimum} --length_max {exclusive_maximum} --n_samples 1 --gpu 0",
            finalize_command,
        ]
    )
    command_path = attempt_dir / "command.sh"
    mounts = [
        f"-v {shlex.quote(str(attempt_dir.resolve()) + ':/data/attempt')}",
        f"-v {shlex.quote(str(SOURCE_ROOT) + ':/data/source:ro')}",
        f"-v {shlex.quote(str(target) + ':/data/input/3EQS.pdb:ro')}",
        f"-v {shlex.quote(str(MODEL_ROOT) + ':/data/models:ro')}",
    ]
    command_path.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        + "docker run --rm --gpus all --shm-size 16g "
        + " ".join(mounts)
        + f" {shlex.quote(image)} bash -lc {shlex.quote(inner)}\n",
        encoding="utf-8",
    )
    command_path.chmod(0o755)
    return ["bash", str(command_path)]


def parse(job: Mapping[str, str], attempt_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    raw = Path(attempt_dir) / "raw"
    runtime = _runtime_evidence(job, raw)
    output = raw / "pepglad_candidate.pdb"
    summary_path = raw / "pepglad_summary.jsonl"
    output_validation = validate_output_file(output, raw)
    summary_validation = validate_output_file(summary_path, raw)
    if (
        output_validation["status"] != "pass"
        or summary_validation["status"] != "pass"
    ):
        return _failed("pepglad_standard_output_missing"), runtime
    if int(job.get("random_seed", "-1")) == 42:
        if runtime.get("recovery_mode") == RECOVERY_MODE:
            replay_valid = all(
                (
                    runtime.get("baseline_replay_expected_sha256")
                    == SEED42_POST_RELAX_BASELINE_SHA256,
                    runtime.get("baseline_replay_observed_sha256")
                    == SEED42_POST_RELAX_BASELINE_SHA256,
                    runtime.get("baseline_replay_observed_sha256")
                    == runtime.get("post_relax_sha256"),
                    runtime.get("post_relax_sha256")
                    == output_validation.get("sha256"),
                    runtime.get("post_relax_path")
                    == "raw/pepglad_candidate.pdb",
                    runtime.get("baseline_replay_status") == "match",
                )
            )
        else:
            replay_valid = _legacy_seed42_replay_valid(
                runtime, output_validation.get("sha256")
            )
        if not replay_valid:
            return _failed("pepglad_seed42_replay_mismatch"), runtime
    try:
        summary_lines = [line for line in summary_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(summary_lines) != 1:
            raise ValueError("expected one summary row")
        summary = json.loads(summary_lines[0])
        if not isinstance(summary, dict):
            raise ValueError("summary row must be an object")
        sequences = parse_pdb_chain_sequences(output)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return _failed("pepglad_standard_output_invalid"), runtime
    binder_chain = job.get("expected_binder_chain", "B") or "B"
    target_chain = job.get("expected_target_chain", "A") or "A"
    sequence = str(summary.get("pep_seq", "")).strip().upper()
    receptor_chains = summary.get("rec_chains", [])
    if isinstance(receptor_chains, str):
        receptor_chains = [receptor_chains]
    if not isinstance(receptor_chains, list) or not all(
        isinstance(chain, str) for chain in receptor_chains
    ):
        return _failed("pepglad_standard_output_invalid"), runtime
    valid = (
        summary.get("id") == "3EQS_0"
        and summary.get("pep_chain") == binder_chain
        and target_chain in receptor_chains
        and binder_chain in sequences
        and target_chain in sequences
        and bool(sequence)
    )
    if not valid:
        return _failed("pepglad_output_contract_invalid"), runtime
    return (
        {
            "sequence": sequence,
            "structure_path": str(output),
            "source_output_path": str(output),
            "binder_chain": binder_chain,
            "parse_status": "parsed",
            "status_reason": "pepglad_standard_output_parsed",
        },
        runtime,
    )
