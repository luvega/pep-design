from __future__ import annotations

import hashlib
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
METHOD = "PepMirror"
SOURCE_COMMIT = "41cb31f3974d91e1a2ca88f0db060405833e4a9c"
MODEL_REVISION = "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"

SOURCE_ROOT = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepMirror")
TARGET_PDB = ROOT / "data/dflow/pdbs/3EQS.pdb"
CHECKPOINT = Path(
    "/data/protein-design/data/benchmark_models/pepmirror/pepmirror_commutator_both_v1.ckpt"
)
COMPOSE_FILE = Path("/data/protein-design/compose/docker-compose.yml")
COMPOSE_SERVICE = "pd-pyrosetta-methods-gpu-v021"
COMPOSE_PROFILE = "v021"
EXPECTED_IMAGE_TAG = "pd-pyrosetta-methods-gpu:0.21"
EXPECTED_ENVIRONMENT_ID = f"{EXPECTED_IMAGE_TAG}/bench-pepmirror"
DOCKER_BIN = "docker"
CONTAINER_CHECKPOINT = "/data/benchmark_models/pepmirror/pepmirror_commutator_both_v1.ckpt"


def _require(path: Path, label: str, *, directory: bool = False) -> None:
    valid = path.is_dir() if directory else path.is_file()
    if not valid:
        raise FileNotFoundError(f"missing {label}: {path}")


def _tracked_source_paths(source: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "-C", str(source), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = os.fsdecode(completed.stderr).strip() or "no command output"
        raise RuntimeError(f"PepMirror tracked-source listing failed: {detail}")
    paths: list[Path] = []
    for encoded in completed.stdout.split(b"\0"):
        if not encoded:
            continue
        relative = Path(os.fsdecode(encoded))
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"unsafe PepMirror tracked path: {relative}")
        paths.append(relative)
    if not paths:
        raise RuntimeError("PepMirror checkout has no tracked files")
    return paths


def _copy_source(source: Path, destination: Path) -> list[Path]:
    tracked = _tracked_source_paths(source)
    destination.mkdir(parents=True, exist_ok=False)
    for relative in tracked:
        source_path = source / relative
        if source_path.is_symlink() or not source_path.is_file():
            raise RuntimeError(f"PepMirror tracked source must be a regular file: {relative}")
        destination_path = destination / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
    return tracked


def _run_text(command: list[str], label: str) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no command output"
        raise RuntimeError(f"{label} failed: {detail}")
    return completed.stdout.strip()


def _run_json(command: list[str], label: str) -> tuple[Any, str]:
    output = _run_text(command, label)
    try:
        return json.loads(output), output
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not return JSON") from exc


def _source_provenance(source: Path) -> dict[str, Any]:
    generate = source / "api/generate.py"
    mirror = source / "scripts/mirror_pdb.py"
    commit_command = ["git", "-C", str(source), "rev-parse", "--verify", "HEAD"]
    observed_commit = _run_text(commit_command, "PepMirror source commit inspection")
    if observed_commit != SOURCE_COMMIT:
        raise RuntimeError(
            f"PepMirror source commit mismatch: expected {SOURCE_COMMIT}, observed {observed_commit}"
        )
    relative_paths = ["api/generate.py", "scripts/mirror_pdb.py"]
    _run_text(
        ["git", "-C", str(source), "ls-files", "--error-unmatch", "--", *relative_paths],
        "PepMirror tracked-source inspection",
    )
    status_command = [
        "git",
        "-C",
        str(source),
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ]
    source_status = _run_text(status_command, "PepMirror source status inspection")
    if source_status:
        raise ValueError(f"PepMirror source checkout is dirty: {source_status}")
    return {
        "source_root": str(source),
        "source_commit_expected": SOURCE_COMMIT,
        "source_commit_observed": observed_commit,
        "source_commit_verified": True,
        "source_git_paths": relative_paths,
        "source_git_paths_clean": True,
        "source_git_checkout_clean": True,
        "source_commit_command": commit_command,
        "source_status_command": status_command,
        "generate_py_pre_path": str(generate),
        "generate_py_pre_sha256": sha256_file(generate),
        "mirror_pdb_py_pre_path": str(mirror),
        "mirror_pdb_py_pre_sha256": sha256_file(mirror),
    }


def _deployment_provenance() -> dict[str, Any]:
    compose_command = [
        DOCKER_BIN,
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "--profile",
        COMPOSE_PROFILE,
        "config",
        "--format",
        "json",
    ]
    config, config_output = _run_json(compose_command, "PepMirror Compose inspection")
    services = config.get("services") if isinstance(config, dict) else None
    service = services.get(COMPOSE_SERVICE) if isinstance(services, dict) else None
    if not isinstance(service, dict):
        raise RuntimeError(f"PepMirror Compose service is missing: {COMPOSE_SERVICE}")
    image_tag = service.get("image")
    if image_tag != EXPECTED_IMAGE_TAG:
        raise RuntimeError(
            f"PepMirror Compose image mismatch: expected {EXPECTED_IMAGE_TAG}, observed {image_tag}"
        )
    image_command = [DOCKER_BIN, "image", "inspect", image_tag]
    image_data, image_output = _run_json(image_command, "PepMirror image inspection")
    image_record = image_data[0] if isinstance(image_data, list) and image_data else None
    image_id = image_record.get("Id") if isinstance(image_record, dict) else None
    if not (
        isinstance(image_id, str)
        and image_id.startswith("sha256:")
        and len(image_id.removeprefix("sha256:")) == 64
    ):
        raise RuntimeError("PepMirror image inspection returned an invalid image ID")
    return {
        "compose_file_path": str(COMPOSE_FILE),
        "compose_file_sha256": sha256_file(COMPOSE_FILE),
        "compose_profile": COMPOSE_PROFILE,
        "compose_service": COMPOSE_SERVICE,
        "compose_service_verified": True,
        "compose_image_tag": image_tag,
        "compose_config_command": compose_command,
        "compose_config_output_sha256": hashlib.sha256(config_output.encode("utf-8")).hexdigest(),
        "image_inspect_command": image_command,
        "image_inspect_output_sha256": hashlib.sha256(image_output.encode("utf-8")).hexdigest(),
        "image_inspect_stage": "prepare",
        "image_id_observed_at_prepare": image_id,
        "image_repo_tags_observed_at_prepare": image_record.get("RepoTags", []),
    }


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
        "status_reason": "v034_pepmirror_roundtrip_candidate_parsed",
        "notes": "Bounded connectivity evidence only; not Benchmark result or scoring evidence",
    }


def _validate_package_provenance(runtime: Mapping[str, Any], attempt_dir: Path) -> None:
    package_path = attempt_dir / "package_evidence.json"
    package_validation = validate_output_file(package_path, attempt_dir)
    if package_validation["status"] != "pass":
        raise ValueError("PepMirror package provenance file is missing or invalid")
    if runtime.get("package_evidence_path") != str(package_path):
        raise ValueError("PepMirror package provenance path is not bound to this attempt")
    if runtime.get("package_evidence_sha256") != package_validation["sha256"]:
        raise ValueError("PepMirror package provenance hash does not match")
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("PepMirror package provenance JSON is invalid") from exc
    if not isinstance(package, dict) or any(runtime.get(key) != value for key, value in package.items()):
        raise ValueError("PepMirror runtime does not preserve package provenance")

    manifest_path = attempt_dir / "executed_source_manifest.json"
    manifest_validation = validate_output_file(manifest_path, attempt_dir)
    if (
        manifest_validation["status"] != "pass"
        or package.get("executed_source_manifest_path") != str(manifest_path)
        or package.get("executed_source_manifest_sha256") != manifest_validation["sha256"]
    ):
        raise ValueError("PepMirror executed-source manifest is missing or invalid")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("PepMirror executed-source manifest JSON is invalid") from exc
    manifest_files = manifest.get("files") if isinstance(manifest, dict) else None
    if (
        not isinstance(manifest_files, dict)
        or manifest.get("source_commit") != SOURCE_COMMIT
        or package.get("source_tracked_file_count") != len(manifest_files)
    ):
        raise ValueError("PepMirror executed-source manifest content is invalid")
    work_root = attempt_dir / "work/PepMirror"
    for relative_text, expected_digest in manifest_files.items():
        relative = Path(relative_text)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("PepMirror executed-source manifest contains an unsafe path")
        validation = validate_output_file(work_root / relative, work_root)
        if validation["status"] != "pass" or validation["sha256"] != expected_digest:
            raise ValueError("PepMirror executed-source manifest does not match the attempt copy")

    preflight_path = attempt_dir / "execution_preflight_evidence.json"
    preflight_validation = validate_output_file(preflight_path, attempt_dir)
    if (
        preflight_validation["status"] != "pass"
        or runtime.get("execution_preflight_evidence_path") != str(preflight_path)
        or runtime.get("execution_preflight_evidence_sha256") != preflight_validation["sha256"]
    ):
        raise ValueError("PepMirror execution preflight evidence is missing or invalid")
    try:
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("PepMirror execution preflight JSON is invalid") from exc
    if not isinstance(preflight, dict) or any(
        runtime.get(key) != value for key, value in preflight.items()
    ):
        raise ValueError("PepMirror runtime does not preserve execution preflight evidence")

    generate_post = attempt_dir / "work/PepMirror/api/generate.py"
    mirror_post = attempt_dir / "work/PepMirror/scripts/mirror_pdb.py"
    post_paths = {
        "generate_py_post": generate_post,
        "mirror_pdb_py_post": mirror_post,
    }
    for name, path in post_paths.items():
        if package.get(f"{name}_path") != str(path):
            raise ValueError(f"PepMirror {name} path is not bound to the attempt copy")
        validation = validate_output_file(path, attempt_dir / "work")
        if (
            validation["status"] != "pass"
            or package.get(f"{name}_sha256") != validation["sha256"]
        ):
            raise ValueError(f"PepMirror {name} hash does not match the attempt copy")

    checkpoint_sha256 = str(package.get("checkpoint_sha256", ""))
    image_id = str(package.get("image_id_observed_at_prepare", ""))
    required = (
        package.get("provenance_capture_stage") == "prepare",
        package.get("source_commit_expected") == SOURCE_COMMIT,
        package.get("source_commit_observed") == SOURCE_COMMIT,
        package.get("source_commit_verified") is True,
        package.get("source_git_paths_clean") is True,
        package.get("source_git_checkout_clean") is True,
        package.get("generate_py_post_sha256") == runtime.get("seed_patch_sha256"),
        package.get("generate_py_pre_sha256") != package.get("generate_py_post_sha256"),
        package.get("mirror_pdb_py_pre_sha256") == package.get("mirror_pdb_py_post_sha256"),
        package.get("checkpoint_revision") == MODEL_REVISION,
        checkpoint_sha256 == MODEL_REVISION.removeprefix("sha256:"),
        package.get("checkpoint_pin_verified") is True,
        package.get("checkpoint_container_path") == CONTAINER_CHECKPOINT,
        package.get("checkpoint_mount_mode") == "explicit_read_only_file_bind",
        package.get("checkpoint_container_binding_verified") is True,
        package.get("compose_file_path") == str(COMPOSE_FILE),
        package.get("compose_profile") == COMPOSE_PROFILE,
        package.get("compose_service") == COMPOSE_SERVICE,
        package.get("compose_service_verified") is True,
        package.get("compose_image_tag") == EXPECTED_IMAGE_TAG,
        package.get("execution_environment_id") == EXPECTED_ENVIRONMENT_ID,
        package.get("execution_environment_verified") is True,
        package.get("target_preflight_verified") is True,
        package.get("target_pdb_sha256") == runtime.get("mirror_input_sha256"),
        package.get("mirror_runtime_scope") == "pinned_compose_conda_environment",
        package.get("mirror_runtime_conda_environment") == "bench-pepmirror",
        package.get("mirror_commands_in_pinned_container") is True,
        package.get("image_inspect_stage") == "prepare",
        image_id.startswith("sha256:") and len(image_id.removeprefix("sha256:")) == 64,
        preflight.get("image_inspect_execution_stage") == "execution_pre_run",
        preflight.get("image_id_observed_pre_run") == image_id,
        preflight.get("image_identity_stable_pre_run") is True,
        preflight.get("executed_source_manifest_verified_pre_run") is True,
        preflight.get("compose_file_verified_pre_run") is True,
        preflight.get("checkpoint_verified_pre_run") is True,
        preflight.get("target_input_verified_pre_run") is True,
    )
    if not all(required):
        raise ValueError("PepMirror package provenance is incomplete or inconsistent")


def prepare(
    job: Mapping[str, str], execution: Mapping[str, str], attempt_dir: Path
) -> list[str]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    work = attempt_dir / "work/PepMirror"
    _require(SOURCE_ROOT, "PepMirror source", directory=True)
    _require(SOURCE_ROOT / "api/generate.py", "PepMirror generation entrypoint")
    _require(SOURCE_ROOT / "scripts/mirror_pdb.py", "PepMirror mirror utility")
    _require(TARGET_PDB, "3EQS target")
    _require(CHECKPOINT, "PepMirror commutator checkpoint")
    _require(COMPOSE_FILE, "v0.21 compose file")
    execution_environment_id = execution.get("container_or_env", "")
    if execution_environment_id != EXPECTED_ENVIRONMENT_ID:
        raise ValueError(
            "PepMirror execution environment mismatch: "
            f"expected {EXPECTED_ENVIRONMENT_ID}, observed {execution_environment_id}"
        )
    target_sha256 = require_file_sha256(
        TARGET_PDB,
        job.get("target_pdb_sha256", ""),
        "PepMirror target",
    )

    source_evidence = _source_provenance(SOURCE_ROOT)
    checkpoint_sha256 = sha256_file(CHECKPOINT)
    expected_checkpoint_sha256 = MODEL_REVISION.removeprefix("sha256:")
    if checkpoint_sha256 != expected_checkpoint_sha256:
        raise RuntimeError(
            "PepMirror checkpoint mismatch: "
            f"expected {expected_checkpoint_sha256}, observed {checkpoint_sha256}"
        )
    deployment_evidence = _deployment_provenance()

    raw.mkdir(parents=True, exist_ok=True)
    work.parent.mkdir(parents=True, exist_ok=True)
    tracked_paths = _copy_source(SOURCE_ROOT, work)
    generate = work / "api/generate.py"
    source_text = generate.read_text(encoding="utf-8")
    marker = "setup_seed(12)"
    if source_text.count(marker) != 1:
        raise RuntimeError("PepMirror seed patch marker must occur exactly once")
    generate.write_text(
        source_text.replace(marker, 'setup_seed(int(os.environ["V034_SEED"]))'),
        encoding="utf-8",
    )
    patch_sha256 = sha256_file(generate)
    mirror_utility = work / "scripts/mirror_pdb.py"

    source_manifest_path = attempt_dir / "executed_source_manifest.json"
    source_manifest = {
        "source_commit": SOURCE_COMMIT,
        "files": {
            relative.as_posix(): sha256_file(work / relative)
            for relative in tracked_paths
        },
    }
    source_manifest_path.write_text(
        json.dumps(source_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    package_path = attempt_dir / "package_evidence.json"
    package_evidence = {
        **source_evidence,
        **deployment_evidence,
        "provenance_capture_stage": "prepare",
        "generate_py_post_path": str(generate),
        "generate_py_post_sha256": patch_sha256,
        "mirror_pdb_py_post_path": str(mirror_utility),
        "mirror_pdb_py_post_sha256": sha256_file(mirror_utility),
        "source_tracked_file_count": len(tracked_paths),
        "executed_source_manifest_path": str(source_manifest_path),
        "executed_source_manifest_sha256": sha256_file(source_manifest_path),
        "checkpoint_path": str(CHECKPOINT),
        "checkpoint_revision": MODEL_REVISION,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_pin_verified": True,
        "checkpoint_container_path": CONTAINER_CHECKPOINT,
        "checkpoint_mount_mode": "explicit_read_only_file_bind",
        "checkpoint_container_binding_verified": True,
        "execution_environment_id": execution_environment_id,
        "execution_environment_verified": True,
        "target_pdb_path": str(TARGET_PDB),
        "target_pdb_sha256": target_sha256,
        "target_preflight_verified": True,
        "mirror_runtime_scope": "pinned_compose_conda_environment",
        "mirror_runtime_conda_environment": "bench-pepmirror",
        "mirror_commands_in_pinned_container": True,
    }
    package_path.write_text(json.dumps(package_evidence, indent=2) + "\n", encoding="utf-8")
    package_sha256 = sha256_file(package_path)

    mirror_input = raw / "mirror_input.pdb"
    mirrored_target = raw / "mirrored_target.pdb"
    mirrored_generated = raw / "mirrored_generated.pdb"
    mirror_output = raw / "pepmirror_candidate.pdb"
    shutil.copyfile(TARGET_PDB, mirror_input)
    config = raw / "pepmirror_config.yaml"
    config.write_text(
        "dataset:\n"
        "  pdb_paths:\n"
        "    - /v034/raw/mirrored_target.pdb\n"
        "  tgt_chains:\n"
        "    - [A]\n"
        "  lig_chains:\n"
        "    - [B]\n"
        "templates:\n"
        "  - class: LinearPeptide\n"
        "    size_min: 11\n"
        "    size_max: 12\n"
        "batch_size: 1\n"
        "n_samples: 1\n"
        "axial_type: commutator\n"
        "axial_position: Both\n",
        encoding="utf-8",
    )

    seed = int(job["random_seed"])
    runtime_path = attempt_dir / "runtime_evidence.json"
    preflight_path = attempt_dir / "execution_preflight_evidence.json"
    preflight = attempt_dir / "verify_runtime_preflight.py"
    finalizer = attempt_dir / "finalize_runtime.py"
    evidence_paths = {
        "mirror_input": mirror_input,
        "mirrored_target": mirrored_target,
        "mirrored_generated": mirrored_generated,
        "mirror_output": mirror_output,
    }
    provenance_paths = {
        "generate_py_pre": Path(package_evidence["generate_py_pre_path"]),
        "generate_py_post": Path(package_evidence["generate_py_post_path"]),
        "mirror_pdb_py_pre": Path(package_evidence["mirror_pdb_py_pre_path"]),
        "mirror_pdb_py_post": Path(package_evidence["mirror_pdb_py_post_path"]),
        "checkpoint": CHECKPOINT,
        "compose_file": COMPOSE_FILE,
    }
    provenance_digests = {
        name: package_evidence[f"{name}_sha256"] for name in provenance_paths
    }
    preflight.write_text(
        "from pathlib import Path\n"
        "import hashlib, json, subprocess\n"
        "def digest(path):\n"
        "    return hashlib.sha256(Path(path).read_bytes()).hexdigest()\n"
        f"manifest_path = Path({str(source_manifest_path)!r})\n"
        f"if digest(manifest_path) != {package_evidence['executed_source_manifest_sha256']!r}:\n"
        "    raise RuntimeError('executed-source manifest changed before execution')\n"
        "manifest = json.loads(manifest_path.read_text(encoding='utf-8'))\n"
        f"work_root = Path({str(work)!r})\n"
        "for relative, expected_digest in manifest['files'].items():\n"
        "    path = work_root / relative\n"
        "    if not path.is_file() or path.is_symlink() or digest(path) != expected_digest:\n"
        "        raise RuntimeError(f'executed source changed before execution: {relative}')\n"
        f"pre_run_files = {repr({'compose_file': (str(COMPOSE_FILE), package_evidence['compose_file_sha256']), 'checkpoint': (str(CHECKPOINT), checkpoint_sha256), 'target_input': (str(mirror_input), target_sha256)})}\n"
        "for name, (path, expected_digest) in pre_run_files.items():\n"
        "    if not Path(path).is_file() or Path(path).is_symlink() or digest(path) != expected_digest:\n"
        "        raise RuntimeError(f'{name} changed before execution')\n"
        f"command = {package_evidence['image_inspect_command']!r}\n"
        "completed = subprocess.run(command, capture_output=True, text=True, check=False)\n"
        "if completed.returncode != 0:\n"
        "    raise RuntimeError(completed.stderr.strip() or 'image inspect failed')\n"
        "records = json.loads(completed.stdout)\n"
        "observed = records[0]['Id'] if isinstance(records, list) and records else ''\n"
        f"expected = {package_evidence['image_id_observed_at_prepare']!r}\n"
        "if observed != expected:\n"
        "    raise RuntimeError(f'image identity changed before execution: {expected} -> {observed}')\n"
        "payload = {\n"
        "    'image_inspect_execution_command': command,\n"
        "    'image_inspect_execution_output_sha256': hashlib.sha256(completed.stdout.strip().encode('utf-8')).hexdigest(),\n"
        "    'image_inspect_execution_stage': 'execution_pre_run',\n"
        "    'image_id_observed_pre_run': observed,\n"
        "    'image_identity_stable_pre_run': True,\n"
        "    'executed_source_manifest_verified_pre_run': True,\n"
        "    'compose_file_verified_pre_run': True,\n"
        "    'checkpoint_verified_pre_run': True,\n"
        "    'target_input_verified_pre_run': True,\n"
        "}\n"
        f"Path({str(preflight_path)!r}).write_text(json.dumps(payload, indent=2) + '\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    finalizer.write_text(
        "from pathlib import Path\n"
        "import hashlib, json\n"
        "def digest(path):\n"
        "    return hashlib.sha256(Path(path).read_bytes()).hexdigest()\n"
        f"package_path = Path({str(package_path)!r})\n"
        "if not package_path.is_file():\n"
        "    raise FileNotFoundError(package_path)\n"
        f"if digest(package_path) != {package_sha256!r}:\n"
        "    raise RuntimeError('package evidence changed after prepare')\n"
        "payload = json.loads(package_path.read_text(encoding='utf-8'))\n"
        f"preflight_path = Path({str(preflight_path)!r})\n"
        "if not preflight_path.is_file():\n"
        "    raise FileNotFoundError(preflight_path)\n"
        "preflight = json.loads(preflight_path.read_text(encoding='utf-8'))\n"
        "if not (preflight.get('image_identity_stable_pre_run') is True\n"
        "        and preflight.get('image_id_observed_pre_run') == payload.get('image_id_observed_at_prepare')):\n"
        "    raise RuntimeError('image execution preflight is invalid')\n"
        "payload.update(preflight)\n"
        "payload['execution_preflight_evidence_path'] = str(preflight_path)\n"
        "payload['execution_preflight_evidence_sha256'] = digest(preflight_path)\n"
        f"provenance_paths = {repr({key: str(value) for key, value in provenance_paths.items()})}\n"
        f"provenance_digests = {repr(provenance_digests)}\n"
        "for name, path in provenance_paths.items():\n"
        "    if not Path(path).is_file():\n"
        "        raise FileNotFoundError(path)\n"
        "    if digest(path) != provenance_digests[name]:\n"
        "        raise RuntimeError(f'{name} changed after prepare')\n"
        f"paths = {repr({key: str(value) for key, value in evidence_paths.items()})}\n"
        "for path in paths.values():\n"
        "    if not Path(path).is_file():\n"
        "        raise FileNotFoundError(path)\n"
        f"payload.update({repr({'method': METHOD, 'requested_seed': seed, 'effective_seed': seed, 'seed_control_status': 'honored', 'seed_patch_path': str(generate), 'seed_patch_sha256': patch_sha256, 'mirror_roundtrip_applied': True, 'package_evidence_path': str(package_path), 'package_evidence_sha256': package_sha256})})\n"
        "for name, path in paths.items():\n"
        "    payload[name + '_path'] = path\n"
        "    payload[name + '_sha256'] = digest(path)\n"
        f"Path({str(runtime_path)!r}).write_text(json.dumps(payload, indent=2) + '\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )

    q = shlex.quote
    script = attempt_dir / "command.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"export V034_SEED={seed}\n"
        f"python {q(str(preflight))}\n"
        f"docker compose -f {q(str(COMPOSE_FILE))} --profile v021 run --rm --no-deps "
        f"-e V034_SEED={seed} -e PYTHONDONTWRITEBYTECODE=1 "
        f"-v {q(str(work))}:/v034/work "
        f"-v {q(str(raw))}:/v034/raw "
        f"-v {q(f'{CHECKPOINT}:{CONTAINER_CHECKPOINT}:ro')} "
        f"{COMPOSE_SERVICE} bash -lc "
        + q(
            "set -euo pipefail; "
            "source /opt/conda/etc/profile.d/conda.sh; "
            "conda activate bench-pepmirror; "
            "cd /v034/work; "
            "PYTHONPATH=/v034/work python scripts/mirror_pdb.py "
            "-i /v034/raw/mirror_input.pdb -o /v034/raw/mirrored_target.pdb "
            "-m central -j 1; "
            "PYTHONPATH=/v034/work python -m api.generate "
            "--config /v034/raw/pepmirror_config.yaml "
            "--save_dir /v034/raw/pepmirror_native --gpu 0 --n_cpus 1 "
            f"--ckpt {CONTAINER_CHECKPOINT}; "
            "test -s /v034/raw/pepmirror_native/LinearPeptide/candidates/mirrored_target/0.pdb; "
            "cp -- /v034/raw/pepmirror_native/LinearPeptide/candidates/mirrored_target/0.pdb "
            "/v034/raw/mirrored_generated.pdb; "
            "PYTHONPATH=/v034/work python scripts/mirror_pdb.py "
            "-i /v034/raw/mirrored_generated.pdb -o /v034/raw/pepmirror_candidate.pdb "
            "-m central -j 1"
        )
        + "\n"
        f"python {q(str(finalizer))}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return ["bash", str(script)]


def parse(job: Mapping[str, str], attempt_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    expected = {
        "mirror_input": raw / "mirror_input.pdb",
        "mirrored_target": raw / "mirrored_target.pdb",
        "mirrored_generated": raw / "mirrored_generated.pdb",
        "mirror_output": raw / "pepmirror_candidate.pdb",
    }
    output = expected["mirror_output"]
    if not output.is_file():
        raise FileNotFoundError(f"missing standard PepMirror candidate: {output}")
    runtime_path = attempt_dir / "runtime_evidence.json"
    if not runtime_path.is_file():
        raise FileNotFoundError(f"missing runtime evidence: {runtime_path}")
    runtime: dict[str, Any] = json.loads(runtime_path.read_text(encoding="utf-8"))
    requested = int(job["random_seed"])
    if not (
        runtime.get("requested_seed") == requested
        and runtime.get("effective_seed") == requested
        and runtime.get("seed_control_status") == "honored"
        and runtime.get("mirror_roundtrip_applied") is True
        and len(str(runtime.get("seed_patch_sha256", ""))) == 64
    ):
        raise ValueError("PepMirror runtime seed or roundtrip evidence is invalid")
    _validate_package_provenance(runtime, attempt_dir)
    for name, path in expected.items():
        path_key = f"{name}_path"
        digest_key = f"{name}_sha256"
        if runtime.get(path_key) != str(path):
            raise ValueError(f"{path_key} does not bind the standard raw path")
        validation = validate_output_file(path, raw)
        if validation["status"] != "pass":
            raise ValueError(f"invalid {name}: {validation['reason']}")
        if runtime.get(digest_key) != validation["sha256"]:
            raise ValueError(f"{digest_key} does not match the raw file")
    target_digest = job.get("target_pdb_sha256", "")
    if target_digest and runtime["mirror_input_sha256"] != target_digest:
        raise ValueError("mirror_input_sha256 does not match the job target")
    binder_chain = job.get("expected_binder_chain", job.get("binder_chain", "B"))
    sequence = parse_pdb_chain_sequences(output).get(binder_chain, "")
    if not sequence:
        raise ValueError(f"PepMirror candidate lacks binder chain {binder_chain}")
    return _candidate(job, output, sequence), runtime
