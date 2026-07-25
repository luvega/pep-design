from __future__ import annotations

import json
import os
import shutil
import shlex
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .common import (
    parse_pdb_chain_sequences,
    require_file_sha256,
    sha256_file,
    validate_output_file,
)


ROOT = Path(__file__).resolve().parents[2]
METHOD = "D-Flow / PeptideDesign"
SOURCE_COMMIT = "3e3e9f501ee16db318e9bf52643513636a07699a"
MODEL_REVISION = "sha256:95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17"
SOURCE_ENTRYPOINT_SHA256 = "6be8b50b876cc94c8a212165d7327bd46c0e906d2c85fc6c2b03a66ff9e2cd9d"
CHECKPOINT_SHA256 = "95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17"
HOST_ENV_DECLARATION = "host:.venv/dflow-v023"

SOURCE_ROOT = ROOT / "method_sources/dflow/PeptideDesign"
PYTHON = ROOT / ".venv/dflow-v023/bin/python"
WEIGHT = ROOT / "weights/dflow/dflow.pt"
STRUCTURE_DIR = ROOT / "data/dflow/pepmerge"
DATASET_DIR = ROOT / "data/dflow/pep_cache"


def _require(path: Path, label: str, *, directory: bool = False) -> None:
    valid = path.is_dir() if directory else path.is_file()
    if not valid:
        raise FileNotFoundError(f"missing {label}: {path}")


def _verified_tracked_files(source: Path) -> tuple[str, list[Path]]:
    try:
        head = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        tracked_status = subprocess.run(
            ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        listed = subprocess.run(
            ["git", "-C", str(source), "ls-files", "-z"],
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"cannot verify D-Flow source checkout: {source}") from exc
    if head != SOURCE_COMMIT:
        raise ValueError(
            f"D-Flow source commit mismatch: expected {SOURCE_COMMIT}, observed {head}"
        )
    if tracked_status:
        raise ValueError("D-Flow source tracked paths are dirty")
    relative_paths: list[Path] = []
    for item in listed.split(b"\0"):
        if not item:
            continue
        relative = Path(os.fsdecode(item))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe D-Flow tracked source path: {relative}")
        if not (source / relative).is_file():
            raise ValueError(f"D-Flow tracked source is not a file: {relative}")
        relative_paths.append(relative)
    if not relative_paths:
        raise ValueError("D-Flow source checkout has no tracked files")
    return head, sorted(relative_paths, key=lambda path: path.as_posix())


def _copy_tracked_source(source: Path, destination: Path, paths: list[Path]) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target, follow_symlinks=True)


def _write_source_manifest(
    path: Path,
    work: Path,
    tracked_files: list[Path],
    *,
    source_commit: str,
    prepatch_sha256: str,
    patched_sha256: str,
) -> str:
    payload = {
        "schema_version": "v034_dflow_source_content_v1",
        "source_commit": source_commit,
        "source_copy_mode": "git_tracked_files_only",
        "source_entrypoint_prepatch_sha256": prepatch_sha256,
        "source_entrypoint_patched_sha256": patched_sha256,
        "files": [
            {
                "path": relative.as_posix(),
                "sha256": sha256_file(work / relative),
                "size_bytes": (work / relative).stat().st_size,
            }
            for relative in tracked_files
        ],
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return sha256_file(path)


def _candidate(job: Mapping[str, str], path: Path, sequence: str) -> dict[str, str]:
    job_id = job.get("job_id", "")
    return {
        "design_id": f"{job_id}_candidate_1",
        "job_id": job_id,
        "method": METHOD,
        "target_id": job.get("target_id", ""),
        "binder_id": f"{job_id}_binder_1",
        "source_output_id": path.name,
        "generation_rank": "1",
        "sequence": sequence,
        "structure_path": str(path),
        "source_output_path": str(path),
        "peptide_type": job.get("peptide_type", "D-peptide"),
        "chirality": job.get("chirality", "D"),
        "cyclic": job.get("cyclic", "no"),
        "binder_chain": job.get("expected_binder_chain", job.get("binder_chain", "B")),
        "parse_status": "parsed",
        "status_reason": "v034_dflow_standard_candidate_parsed",
        "notes": "Bounded connectivity evidence only; not Benchmark result or scoring evidence",
    }


def prepare(
    job: Mapping[str, str], execution: Mapping[str, str], attempt_dir: Path
) -> list[str]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    work = attempt_dir / "work/PeptideDesign"
    attempt_dataset = attempt_dir / "work/pep_cache"
    target_id = job.get("target_id", "")
    if not target_id or any(character in target_id for character in "\r\n/\\"):
        raise ValueError("D-Flow target_id is not a safe one-entry dataset key")
    inference_source = SOURCE_ROOT / "dflow/experiments/inference_pep.py"
    target_context_source = STRUCTURE_DIR / target_id / "pocket.pdb"
    declared_environment = execution.get("container_or_env", "").strip()
    if declared_environment != HOST_ENV_DECLARATION:
        raise ValueError(
            "D-Flow v0.34 must declare the host .venv environment as "
            f"{HOST_ENV_DECLARATION}"
        )
    _require(SOURCE_ROOT, "D-Flow source", directory=True)
    _require(inference_source, "D-Flow inference entrypoint")
    _require(PYTHON, "D-Flow Python")
    _require(WEIGHT, "D-Flow checkpoint")
    _require(STRUCTURE_DIR, "D-Flow structure directory", directory=True)
    _require(target_context_source, "D-Flow target pocket context")
    source_commit, tracked_files = _verified_tracked_files(SOURCE_ROOT)
    prepatch_sha256 = require_file_sha256(
        inference_source, SOURCE_ENTRYPOINT_SHA256, "D-Flow inference entrypoint"
    )
    checkpoint_sha256 = require_file_sha256(
        WEIGHT, CHECKPOINT_SHA256, "D-Flow checkpoint"
    )
    python_realpath = PYTHON.resolve(strict=True)
    python_sha256 = sha256_file(python_realpath)

    raw.mkdir(parents=True, exist_ok=True)
    work.parent.mkdir(parents=True, exist_ok=True)
    _copy_tracked_source(SOURCE_ROOT, work, tracked_files)
    (work.parent / "names.txt").write_text(target_id + "\n", encoding="utf-8")
    attempt_dataset.mkdir(parents=True, exist_ok=False)
    inference = work / "dflow/experiments/inference_pep.py"
    source_text = inference.read_text(encoding="utf-8")
    marker = "seed_all(2024)"
    if source_text.count(marker) != 1:
        raise RuntimeError("D-Flow seed patch marker must occur exactly once")
    inference.write_text(
        source_text.replace(marker, 'seed_all(int(os.environ["V034_SEED"]))'),
        encoding="utf-8",
    )
    patch_sha256 = sha256_file(inference)
    source_manifest_path = attempt_dir / "source_content_manifest.json"
    source_manifest_sha256 = _write_source_manifest(
        source_manifest_path,
        work,
        tracked_files,
        source_commit=source_commit,
        prepatch_sha256=prepatch_sha256,
        patched_sha256=patch_sha256,
    )

    seed = int(job["random_seed"])
    native = (
        raw
        / "dflow_native/dflow.pt_1_1_False_x_mirror"
        / target_id
        / "sample_0.pdb"
    )
    standard = raw / "dflow_candidate.pdb"
    target_context = raw / "dflow_target_context.pdb"
    shutil.copyfile(target_context_source, target_context)
    target_context_digest = sha256_file(target_context)
    runtime_path = attempt_dir / "runtime_evidence.json"
    finalizer = attempt_dir / "finalize_runtime.py"
    checkpoint_path = work / "dflow.pt"
    prepared_evidence = {
        "method": METHOD,
        "requested_seed": seed,
        "effective_seed": seed,
        "seed_control_status": "honored",
        "seed_patch_path": str(inference),
        "seed_patch_sha256": patch_sha256,
        "x_mirror_applied": True,
        "target_context_path": str(target_context),
        "target_context_sha256": target_context_digest,
        "target_context_chain": job.get("expected_target_chain", "A"),
        "target_context_mode": "ordered_subsequence",
        "source_commit": source_commit,
        "source_git_tracked_paths_clean": True,
        "source_copy_mode": "git_tracked_files_only",
        "source_checkout_path": str(work),
        "source_content_manifest_path": str(source_manifest_path),
        "source_content_manifest_sha256": source_manifest_sha256,
        "source_tracked_file_count": len(tracked_files),
        "source_entrypoint_path": str(inference),
        "source_entrypoint_prepatch_sha256": prepatch_sha256,
        "source_entrypoint_patched_sha256": patch_sha256,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_resolved_path": str(WEIGHT.resolve()),
        "checkpoint_sha256": checkpoint_sha256,
        "execution_environment_type": "host_local_python_environment",
        "execution_environment_declared": declared_environment,
        "containerized": False,
        "host_environment_path": str(PYTHON.parent.parent.resolve()),
        "python_invocation_path": str(PYTHON),
        "python_executable_realpath": str(python_realpath),
        "python_executable_sha256": python_sha256,
    }
    finalizer.write_text(
        "from pathlib import Path\n"
        "import hashlib, json, platform, sys\n"
        "def digest(path):\n"
        "    return hashlib.sha256(Path(path).read_bytes()).hexdigest()\n"
        f"payload = {prepared_evidence!r}\n"
        "manifest_path = Path(payload['source_content_manifest_path'])\n"
        "if digest(manifest_path) != payload['source_content_manifest_sha256']:\n"
        "    raise RuntimeError('D-Flow source content manifest changed after prepare')\n"
        "manifest = json.loads(manifest_path.read_text(encoding='utf-8'))\n"
        "files = manifest.get('files', [])\n"
        "if len(files) != payload['source_tracked_file_count']:\n"
        "    raise RuntimeError('D-Flow source content manifest file count changed')\n"
        "source_root = Path(payload['source_checkout_path'])\n"
        "for item in files:\n"
        "    source_path = source_root / item['path']\n"
        "    if not source_path.is_file() or digest(source_path) != item['sha256']:\n"
        "        raise RuntimeError(f'D-Flow executed source content mismatch: {source_path}')\n"
        "entrypoint = Path(payload['source_entrypoint_path'])\n"
        "if digest(entrypoint) != payload['source_entrypoint_patched_sha256']:\n"
        "    raise RuntimeError('D-Flow patched entrypoint changed before finalization')\n"
        "checkpoint = Path(payload['checkpoint_path'])\n"
        "if checkpoint.resolve() != Path(payload['checkpoint_resolved_path']):\n"
        "    raise RuntimeError('D-Flow checkpoint symlink target changed')\n"
        "if digest(checkpoint) != payload['checkpoint_sha256']:\n"
        "    raise RuntimeError('D-Flow checkpoint changed before finalization')\n"
        "python_realpath = Path(sys.executable).resolve()\n"
        "if python_realpath != Path(payload['python_executable_realpath']):\n"
        "    raise RuntimeError('D-Flow finalizer did not use the prepared Python executable')\n"
        "if digest(python_realpath) != payload['python_executable_sha256']:\n"
        "    raise RuntimeError('D-Flow Python executable changed after prepare')\n"
        "payload['python_executable_path'] = sys.executable\n"
        "payload['python_executable_realpath'] = str(python_realpath)\n"
        "payload['python_version'] = platform.python_version()\n"
        "payload['python_prefix'] = sys.prefix\n"
        "payload['python_base_prefix'] = sys.base_prefix\n"
        f"candidate = Path({str(standard)!r})\n"
        "if not candidate.is_file():\n"
        "    raise FileNotFoundError(candidate)\n"
        "payload['candidate_path'] = str(candidate)\n"
        "payload['candidate_sha256'] = digest(candidate)\n"
        f"Path({str(runtime_path)!r}).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )

    q = shlex.quote
    script = attempt_dir / "command.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"export V034_SEED={seed}\n"
        f"cd {q(str(work))}\n"
        f"{q(str(PYTHON))} -m dflow.experiments.inference_pep \\\n"
        "  sample.ckpt_path=dflow.pt \\\n"
        f"  sample.output={q(str(raw / 'dflow_native'))} \\\n"
        "  sample.device=cuda \\\n"
        "  sample.num_steps=1 \\\n"
        "  sample.num_samples=1 \\\n"
        "  sample.x_mirror=True \\\n"
        "  sample.y_mirror=False \\\n"
        "  sample.z_mirror=False \\\n"
        "  sample.angle_purify=False \\\n"
        "  sample.llm=False \\\n"
        f"  dataset.val.structure_dir={q(str(STRUCTURE_DIR))} \\\n"
        f"  dataset.val.dataset_dir={q(str(attempt_dataset))} \\\n"
        "  dataset.val.name=pep_pocket_test \\\n"
        "  dataset.val.reset=False\n"
        f"test -s {q(str(attempt_dataset / 'pep_pocket_test_structure_x_cache.lmdb'))}\n"
        f"test -s {q(str(native))}\n"
        f"cp -- {q(str(native))} {q(str(standard))}\n"
        f"{q(str(PYTHON))} {q(str(finalizer))}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    # Keep the method's expected relative checkpoint name without copying the 91 MB file.
    checkpoint_path.symlink_to(WEIGHT.resolve())
    return ["bash", str(script)]


def parse(job: Mapping[str, str], attempt_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    path = raw / "dflow_candidate.pdb"
    if not path.is_file():
        raise FileNotFoundError(f"missing standard D-Flow candidate: {path}")
    validation = validate_output_file(path, raw)
    if validation["status"] != "pass":
        raise ValueError(f"invalid D-Flow candidate: {validation['reason']}")
    runtime_path = attempt_dir / "runtime_evidence.json"
    if not runtime_path.is_file():
        raise FileNotFoundError(f"missing runtime evidence: {runtime_path}")
    runtime: dict[str, Any] = json.loads(runtime_path.read_text(encoding="utf-8"))
    requested = int(job["random_seed"])
    if not (
        runtime.get("requested_seed") == requested
        and runtime.get("effective_seed") == requested
        and runtime.get("seed_control_status") == "honored"
        and runtime.get("x_mirror_applied") is True
        and len(str(runtime.get("seed_patch_sha256", ""))) == 64
    ):
        raise ValueError("D-Flow runtime seed or x_mirror evidence is invalid")
    provenance_valid = all(
        (
            runtime.get("source_commit") == SOURCE_COMMIT,
            runtime.get("source_git_tracked_paths_clean") is True,
            runtime.get("source_copy_mode") == "git_tracked_files_only",
            runtime.get("source_entrypoint_prepatch_sha256")
            == SOURCE_ENTRYPOINT_SHA256,
            runtime.get("source_entrypoint_patched_sha256")
            == runtime.get("seed_patch_sha256"),
            len(str(runtime.get("source_content_manifest_sha256", ""))) == 64,
            isinstance(runtime.get("source_tracked_file_count"), int)
            and runtime.get("source_tracked_file_count", 0) > 0,
            runtime.get("checkpoint_sha256") == CHECKPOINT_SHA256,
            runtime.get("execution_environment_type")
            == "host_local_python_environment",
            runtime.get("execution_environment_declared") == HOST_ENV_DECLARATION,
            runtime.get("containerized") is False,
            bool(runtime.get("host_environment_path")),
            bool(runtime.get("python_invocation_path")),
            bool(runtime.get("python_executable_realpath")),
            len(str(runtime.get("python_executable_sha256", ""))) == 64,
            bool(runtime.get("python_version")),
        )
    )
    if not provenance_valid:
        raise ValueError("D-Flow runtime provenance evidence is invalid")
    binder_chain = job.get("expected_binder_chain", job.get("binder_chain", "B"))
    sequence = parse_pdb_chain_sequences(path).get(binder_chain, "")
    if not sequence:
        raise ValueError(f"D-Flow candidate lacks binder chain {binder_chain}")
    return _candidate(job, path, sequence), runtime
