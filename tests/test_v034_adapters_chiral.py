from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.v034_adapters.common import read_csv, sha256_file


def _atom(serial: int, atom: str, chain: str, residue: int, x: float, y: float, z: float) -> str:
    return (
        f"ATOM  {serial:5d} {atom:^4s} ALA {chain}{residue:4d}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {atom[0]:>2s}\n"
    )


def _write_complex(path: Path, binder_length: int = 11) -> None:
    lines: list[str] = []
    serial = 1
    for chain, length, y_offset, cb_z in (("A", 1, 20.0, 1.0), ("B", binder_length, 0.0, -1.0)):
        for residue in range(1, length + 1):
            origin = float((residue - 1) * 4)
            for atom, xyz in {
                "N": (origin + 1.0, y_offset, 0.0),
                "CA": (origin, y_offset, 0.0),
                "C": (origin, y_offset + 1.0, 0.0),
                "CB": (origin, y_offset, cb_z),
            }.items():
                lines.append(_atom(serial, atom, chain, residue, *xyz))
                serial += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines) + "END\n", encoding="utf-8")


def _job(method: str, seed: str = "42") -> dict[str, str]:
    return {
        "job_id": f"v034_{method.lower()}_seed{seed}",
        "method": method,
        "target_id": "mdm2_p53_3eqs_fixture",
        "target_chains": "A",
        "binder_chain": "B",
        "expected_binder_chain": "B",
        "peptide_type": "D-peptide",
        "chirality": "D",
        "cyclic": "no",
        "random_seed": seed,
        "n_designs_requested": "1",
    }


def _execution() -> dict[str, str]:
    return {"container_or_env": "test-env", "max_runtime_sec": "900"}


def _pepmirror_execution() -> dict[str, str]:
    return {
        "container_or_env": "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror",
        "max_runtime_sec": "900",
    }


def _dflow_execution() -> dict[str, str]:
    return {"container_or_env": "host:.venv/dflow-v023", "max_runtime_sec": "900"}


def _fake_dflow_source(path: Path) -> tuple[str, str]:
    inference = path / "dflow/experiments/inference_pep.py"
    inference.parent.mkdir(parents=True)
    inference.write_text(
        "import os\nfrom dflow.experiments.utils import seed_all\n"
        "def main():\n    seed_all(2024)\n",
        encoding="utf-8",
    )
    (path / "dflow/configs").mkdir(parents=True)
    (path / "dflow/configs/pep_codesign.yaml").write_text("sample: {}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=v034 test",
            "-c",
            "user.email=v034@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    commit = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return commit, sha256_file(inference)


def _valid_dflow_runtime(module: object, seed: int = 42) -> dict[str, object]:
    return {
        "requested_seed": seed,
        "effective_seed": seed,
        "seed_control_status": "honored",
        "seed_patch_sha256": "a" * 64,
        "x_mirror_applied": True,
        "source_commit": getattr(module, "SOURCE_COMMIT"),
        "source_git_tracked_paths_clean": True,
        "source_copy_mode": "git_tracked_files_only",
        "source_entrypoint_prepatch_sha256": getattr(
            module, "SOURCE_ENTRYPOINT_SHA256"
        ),
        "source_entrypoint_patched_sha256": "a" * 64,
        "source_content_manifest_sha256": "b" * 64,
        "source_tracked_file_count": 1,
        "checkpoint_sha256": getattr(module, "CHECKPOINT_SHA256"),
        "execution_environment_type": "host_local_python_environment",
        "execution_environment_declared": getattr(module, "HOST_ENV_DECLARATION"),
        "containerized": False,
        "host_environment_path": "/tmp/.venv/dflow-v023",
        "python_invocation_path": "/tmp/.venv/dflow-v023/bin/python",
        "python_executable_realpath": "/tmp/.venv/dflow-v023/bin/python3.10",
        "python_executable_sha256": "c" * 64,
        "python_version": "3.10.20",
    }


def _fake_pepmirror_source(path: Path) -> None:
    generate = path / "api/generate.py"
    generate.parent.mkdir(parents=True)
    generate.write_text(
        "import os\nfrom utils.random_seed import setup_seed\n"
        "if __name__ == '__main__':\n    setup_seed(12)\n",
        encoding="utf-8",
    )
    mirror = path / "scripts/mirror_pdb.py"
    mirror.parent.mkdir(parents=True)
    mirror.write_text("# mirror CLI fixture\n", encoding="utf-8")


def _commit_fixture_repo(path: Path) -> str:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "v034 test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "v034@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "api/generate.py", "scripts/mirror_pdb.py"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "fixture"], check=True)
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _prepare_pepglad_instrumentation_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    script_override: tuple[str, str] | None = None,
) -> tuple[object, Path, dict[str, str], Path, str]:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    source = tmp_path / "PepGLAD"
    entrypoint = source / "api/run.py"
    entrypoint.parent.mkdir(parents=True)
    (entrypoint.parent / "__init__.py").write_text("", encoding="utf-8")
    entrypoint.write_text(
        "from pathlib import Path\n"
        "import os\n\n"
        "class ForceFieldMinimizer:\n"
        "    def __call__(self, source, output):\n"
        "        Path(os.environ['V034_RELAX_MARKER']).write_text('called\\n')\n"
        "        with Path(output).open('ab') as handle:\n"
        "            handle.write(b'REMARK OPENMM RELAXATION EXECUTED\\n')\n\n"
        "def openmm_relax(pdb_path):\n"
        "    force_field = ForceFieldMinimizer()\n"
        "    force_field(pdb_path, pdb_path)\n"
        "    return pdb_path\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "user.name=v034 test",
            "-c",
            "user.email=v034@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    source_commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    entrypoint_sha256 = sha256_file(entrypoint)

    model_root = tmp_path / "models"
    model_root.mkdir()
    model = model_root / "codesign.ckpt"
    model.write_bytes(b"pinned model fixture\n")
    target = tmp_path / "3EQS.pdb"
    _write_complex(target)
    job = {
        **_job("PepGLAD"),
        "peptide_type": "L-peptide",
        "chirality": "L",
        "target_pdb_path": str(target),
        "target_pdb_sha256": sha256_file(target),
        "target_chains": "A",
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
        "length_min": "11",
        "length_max": "11",
    }
    monkeypatch.setattr(module, "SOURCE_ROOT", source)
    monkeypatch.setattr(module, "SOURCE_ENTRYPOINT", entrypoint)
    monkeypatch.setattr(module, "SOURCE_COMMIT", source_commit)
    monkeypatch.setattr(module, "SOURCE_ENTRYPOINT_SHA256", entrypoint_sha256)
    monkeypatch.setattr(
        module,
        "SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256",
        _pepglad_instrumented_sha256(entrypoint),
        raising=False,
    )
    monkeypatch.setattr(module, "MODEL_ROOT", model_root)
    monkeypatch.setattr(module, "MODEL_WEIGHTS", model)
    monkeypatch.setattr(module, "MODEL_WEIGHTS_SHA256", sha256_file(model))
    if script_override is not None:
        monkeypatch.setattr(module, *script_override, raising=False)

    attempt = tmp_path / "attempt_003"
    module.prepare(
        job,
        {"container_or_env": "pd-benchmark-methods-gpu:0.21/bench-pepglad"},
        attempt,
    )
    work = attempt / "work"
    shutil.copytree(source, work)
    return module, attempt, job, entrypoint, entrypoint_sha256


def _instrument_pepglad_attempt(
    attempt: Path,
    job: dict[str, str],
    source_sha256: str,
    instrumented_sha256: str,
) -> Path:
    observer = attempt / "pepglad_observer.py"
    patcher = attempt / "pepglad_instrument_source.py"
    evidence = attempt / "observer_patch_evidence.json"
    subprocess.run(
        [
            sys.executable,
            str(patcher),
            "--source-entrypoint",
            str(attempt / "work/api/run.py"),
            "--expected-source-sha256",
            source_sha256,
            "--expected-instrumented-source-sha256",
            instrumented_sha256,
            "--observer-source",
            str(observer),
            "--expected-observer-sha256",
            sha256_file(observer),
            "--expected-patch-sha256",
            sha256_file(patcher),
            "--target-input",
            job["target_pdb_path"],
            "--expected-target-sha256",
            job["target_pdb_sha256"],
            "--evidence",
            str(evidence),
        ],
        check=True,
    )
    return evidence


def _pepglad_instrumented_sha256(source_entrypoint: Path) -> str:
    anchor = b"def openmm_relax(pdb_path):\n    force_field = ForceFieldMinimizer()\n"
    replacement = (
        b"def openmm_relax(pdb_path):\n"
        b"    from pepglad_observer import capture_pre_relax_pdb\n"
        b"    capture_pre_relax_pdb(pdb_path)\n"
        b"    force_field = ForceFieldMinimizer()\n"
    )
    source = source_entrypoint.read_bytes()
    assert source.count(anchor) == 1
    return hashlib.sha256(source.replace(anchor, replacement, 1)).hexdigest()


def _fake_docker_cli(path: Path, image_id: str) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "args = sys.argv[1:]\n"
        "if args and args[0] == 'compose':\n"
        "    print(json.dumps({'services': {\n"
        "        'pd-pyrosetta-methods-gpu-v021': {\n"
        "            'image': 'pd-pyrosetta-methods-gpu:0.21'\n"
        "        }\n"
        "    }}))\n"
        "elif args[:2] == ['image', 'inspect']:\n"
        f"    print(json.dumps([{{'Id': {image_id!r}, "
        "'RepoTags': ['pd-pyrosetta-methods-gpu:0.21']}]))\n"
        "else:\n"
        "    raise SystemExit(2)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _bind_pepmirror_provenance(
    module: object, attempt: Path, runtime: dict[str, object]
) -> None:
    generate = attempt / "work/PepMirror/api/generate.py"
    mirror = attempt / "work/PepMirror/scripts/mirror_pdb.py"
    generate.parent.mkdir(parents=True, exist_ok=True)
    mirror.parent.mkdir(parents=True, exist_ok=True)
    generate.write_text('setup_seed(int(os.environ["V034_SEED"]))\n', encoding="utf-8")
    mirror.write_text("# mirror utility\n", encoding="utf-8")
    generate_digest = sha256_file(generate)
    mirror_digest = sha256_file(mirror)
    image_id = "sha256:" + "1" * 64
    source_manifest = {
        "source_commit": module.SOURCE_COMMIT,
        "files": {
            "api/generate.py": generate_digest,
            "scripts/mirror_pdb.py": mirror_digest,
        },
    }
    source_manifest_path = attempt / "executed_source_manifest.json"
    source_manifest_path.write_text(json.dumps(source_manifest), encoding="utf-8")
    package = {
        "provenance_capture_stage": "prepare",
        "source_commit_expected": module.SOURCE_COMMIT,
        "source_commit_observed": module.SOURCE_COMMIT,
        "source_commit_verified": True,
        "source_git_paths_clean": True,
        "source_git_checkout_clean": True,
        "generate_py_pre_sha256": "a" * 64,
        "generate_py_post_path": str(generate),
        "generate_py_post_sha256": generate_digest,
        "mirror_pdb_py_pre_sha256": mirror_digest,
        "mirror_pdb_py_post_path": str(mirror),
        "mirror_pdb_py_post_sha256": mirror_digest,
        "source_tracked_file_count": 2,
        "executed_source_manifest_path": str(source_manifest_path),
        "executed_source_manifest_sha256": sha256_file(source_manifest_path),
        "checkpoint_revision": module.MODEL_REVISION,
        "checkpoint_sha256": module.MODEL_REVISION.removeprefix("sha256:"),
        "checkpoint_pin_verified": True,
        "checkpoint_container_path": module.CONTAINER_CHECKPOINT,
        "checkpoint_mount_mode": "explicit_read_only_file_bind",
        "checkpoint_container_binding_verified": True,
        "compose_file_path": str(module.COMPOSE_FILE),
        "compose_profile": module.COMPOSE_PROFILE,
        "compose_service": module.COMPOSE_SERVICE,
        "compose_service_verified": True,
        "compose_image_tag": module.EXPECTED_IMAGE_TAG,
        "execution_environment_id": module.EXPECTED_ENVIRONMENT_ID,
        "execution_environment_verified": True,
        "target_pdb_sha256": runtime.get("mirror_input_sha256", ""),
        "target_preflight_verified": True,
        "mirror_runtime_scope": "pinned_compose_conda_environment",
        "mirror_runtime_conda_environment": "bench-pepmirror",
        "mirror_commands_in_pinned_container": True,
        "image_inspect_stage": "prepare",
        "image_id_observed_at_prepare": image_id,
    }
    package_path = attempt / "package_evidence.json"
    package_path.write_text(json.dumps(package), encoding="utf-8")
    preflight = {
        "image_inspect_execution_stage": "execution_pre_run",
        "image_id_observed_pre_run": image_id,
        "image_identity_stable_pre_run": True,
        "executed_source_manifest_verified_pre_run": True,
        "compose_file_verified_pre_run": True,
        "checkpoint_verified_pre_run": True,
        "target_input_verified_pre_run": True,
    }
    preflight_path = attempt / "execution_preflight_evidence.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
    runtime.update(package)
    runtime.update(preflight)
    runtime["seed_patch_sha256"] = generate_digest
    runtime["package_evidence_path"] = str(package_path)
    runtime["package_evidence_sha256"] = sha256_file(package_path)
    runtime["execution_preflight_evidence_path"] = str(preflight_path)
    runtime["execution_preflight_evidence_sha256"] = sha256_file(preflight_path)


def test_dflow_prepare_uses_attempt_copy_seed_patch_and_d_mirror(tmp_path: Path, monkeypatch) -> None:
    module = importlib.import_module("scripts.v034_adapters.dflow")
    source = tmp_path / "source"
    source_commit, source_entrypoint_sha256 = _fake_dflow_source(source)
    python = tmp_path / "venv/bin/python"
    weight = tmp_path / "dflow.pt"
    structure_dir = tmp_path / "pepmerge"
    dataset_dir = tmp_path / "pep_cache"
    names = tmp_path / "names.txt"
    for path in (weight, names):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    python.parent.mkdir(parents=True)
    python.symlink_to(Path(sys.executable).resolve())
    context = structure_dir / "mdm2_p53_3eqs_fixture/pocket.pdb"
    _write_complex(context)
    names.write_text("unrelated_upstream_case\n", encoding="utf-8")
    monkeypatch.setattr(module, "SOURCE_ROOT", source)
    monkeypatch.setattr(module, "SOURCE_COMMIT", source_commit)
    monkeypatch.setattr(
        module, "SOURCE_ENTRYPOINT_SHA256", source_entrypoint_sha256, raising=False
    )
    monkeypatch.setattr(module, "PYTHON", python)
    monkeypatch.setattr(module, "WEIGHT", weight)
    monkeypatch.setattr(module, "CHECKPOINT_SHA256", sha256_file(weight), raising=False)
    monkeypatch.setattr(module, "STRUCTURE_DIR", structure_dir)
    monkeypatch.setattr(module, "DATASET_DIR", dataset_dir)

    command = module.prepare(
        _job("D-Flow / PeptideDesign"), _dflow_execution(), tmp_path / "attempt"
    )

    assert command == ["bash", str(tmp_path / "attempt/command.sh")]
    patched = (tmp_path / "attempt/work/PeptideDesign/dflow/experiments/inference_pep.py").read_text()
    assert 'seed_all(int(os.environ["V034_SEED"]))' in patched
    assert "seed_all(2024)" in (source / "dflow/experiments/inference_pep.py").read_text()
    script = (tmp_path / "attempt/command.sh").read_text()
    for token in (
        "V034_SEED=42",
        "sample.num_steps=1",
        "sample.num_samples=1",
        "sample.x_mirror=True",
        "sample.angle_purify=False",
        "sample.llm=False",
        "pep_pocket_test_structure_x_cache.lmdb",
        "work/pep_cache",
        "raw/dflow_candidate.pdb",
    ):
        assert token in script
    assert "seed_patch_sha256" in (tmp_path / "attempt/finalize_runtime.py").read_text()
    assert (tmp_path / "attempt/work/names.txt").read_text() == "mdm2_p53_3eqs_fixture\n"
    assert (tmp_path / "attempt/raw/dflow_target_context.pdb").is_file()
    assert not any(token in script for token in ("pip install", "git clone", "wget ", "curl "))

    candidate = tmp_path / "attempt/raw/dflow_candidate.pdb"
    _write_complex(candidate)
    subprocess.run([str(python), str(tmp_path / "attempt/finalize_runtime.py")], check=True)
    runtime = json.loads((tmp_path / "attempt/runtime_evidence.json").read_text())
    patched_path = tmp_path / "attempt/work/PeptideDesign/dflow/experiments/inference_pep.py"
    manifest_path = tmp_path / "attempt/source_content_manifest.json"
    assert runtime["source_commit"] == source_commit
    assert runtime["source_checkout_path"] == str(tmp_path / "attempt/work/PeptideDesign")
    assert runtime["source_content_manifest_path"] == str(manifest_path)
    assert runtime["source_content_manifest_sha256"] == sha256_file(manifest_path)
    assert runtime["source_tracked_file_count"] == 2
    assert runtime["source_entrypoint_path"] == str(patched_path)
    assert runtime["source_entrypoint_prepatch_sha256"] == source_entrypoint_sha256
    assert runtime["source_entrypoint_patched_sha256"] == sha256_file(patched_path)
    assert runtime["checkpoint_path"] == str(tmp_path / "attempt/work/PeptideDesign/dflow.pt")
    assert runtime["checkpoint_resolved_path"] == str(weight.resolve())
    assert runtime["checkpoint_sha256"] == sha256_file(weight)
    assert runtime["execution_environment_type"] == "host_local_python_environment"
    assert runtime["execution_environment_declared"] == "host:.venv/dflow-v023"
    assert runtime["containerized"] is False
    assert runtime["host_environment_path"] == str(python.parent.parent.resolve())
    assert runtime["python_invocation_path"] == str(python)
    assert runtime["python_executable_realpath"] == str(Path(sys.executable).resolve())
    assert runtime["python_executable_sha256"] == sha256_file(Path(sys.executable))
    assert runtime["python_version"]
    assert "container_image" not in runtime


def test_dflow_prepare_rejects_unpinned_source_entrypoint(tmp_path: Path, monkeypatch) -> None:
    module = importlib.import_module("scripts.v034_adapters.dflow")
    source = tmp_path / "source"
    source_commit, _ = _fake_dflow_source(source)
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(Path(sys.executable).resolve())
    weight = tmp_path / "dflow.pt"
    weight.write_text("checkpoint\n", encoding="utf-8")
    context = tmp_path / "pepmerge/mdm2_p53_3eqs_fixture/pocket.pdb"
    _write_complex(context)
    monkeypatch.setattr(module, "SOURCE_ROOT", source)
    monkeypatch.setattr(module, "SOURCE_COMMIT", source_commit)
    monkeypatch.setattr(module, "SOURCE_ENTRYPOINT_SHA256", "0" * 64, raising=False)
    monkeypatch.setattr(module, "PYTHON", python)
    monkeypatch.setattr(module, "WEIGHT", weight)
    monkeypatch.setattr(module, "CHECKPOINT_SHA256", sha256_file(weight), raising=False)
    monkeypatch.setattr(module, "STRUCTURE_DIR", context.parents[1])

    with pytest.raises(ValueError, match="entrypoint SHA256 mismatch"):
        module.prepare(
            _job("D-Flow / PeptideDesign"), _dflow_execution(), tmp_path / "attempt"
        )


def test_dflow_prepare_rejects_unpinned_checkpoint(tmp_path: Path, monkeypatch) -> None:
    module = importlib.import_module("scripts.v034_adapters.dflow")
    source = tmp_path / "source"
    source_commit, source_entrypoint_sha256 = _fake_dflow_source(source)
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(Path(sys.executable).resolve())
    weight = tmp_path / "dflow.pt"
    weight.write_text("checkpoint\n", encoding="utf-8")
    context = tmp_path / "pepmerge/mdm2_p53_3eqs_fixture/pocket.pdb"
    _write_complex(context)
    monkeypatch.setattr(module, "SOURCE_ROOT", source)
    monkeypatch.setattr(module, "SOURCE_COMMIT", source_commit)
    monkeypatch.setattr(
        module, "SOURCE_ENTRYPOINT_SHA256", source_entrypoint_sha256, raising=False
    )
    monkeypatch.setattr(module, "PYTHON", python)
    monkeypatch.setattr(module, "WEIGHT", weight)
    monkeypatch.setattr(module, "CHECKPOINT_SHA256", "0" * 64, raising=False)
    monkeypatch.setattr(module, "STRUCTURE_DIR", context.parents[1])

    with pytest.raises(ValueError, match="checkpoint SHA256 mismatch"):
        module.prepare(
            _job("D-Flow / PeptideDesign"), _dflow_execution(), tmp_path / "attempt"
        )


def test_dflow_execution_matrix_declares_host_venv() -> None:
    rows = read_csv(Path("benchmark/deployment/pilot_execution_matrix_v0.34.csv"))
    dflow_rows = [row for row in rows if row["method"] == "D-Flow / PeptideDesign"]
    assert len(dflow_rows) == 2
    assert {row["container_or_env"] for row in dflow_rows} == {"host:.venv/dflow-v023"}


def test_pepmirror_prepare_builds_exact_three_step_roundtrip(tmp_path: Path, monkeypatch) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    source = tmp_path / "source"
    _fake_pepmirror_source(source)
    source_commit = _commit_fixture_repo(source)
    target = tmp_path / "3EQS.pdb"
    checkpoint = tmp_path / "pepmirror_commutator_both_v1.ckpt"
    compose = tmp_path / "docker-compose.yml"
    docker = tmp_path / "docker"
    _write_complex(target)
    checkpoint.write_text("checkpoint\n", encoding="utf-8")
    compose.write_text(
        "services:\n"
        "  pd-pyrosetta-methods-gpu-v021:\n"
        "    image: pd-pyrosetta-methods-gpu:0.21\n",
        encoding="utf-8",
    )
    _fake_docker_cli(docker, "sha256:" + "1" * 64)
    monkeypatch.setattr(module, "SOURCE_ROOT", source)
    monkeypatch.setattr(module, "SOURCE_COMMIT", source_commit)
    monkeypatch.setattr(module, "TARGET_PDB", target)
    monkeypatch.setattr(module, "CHECKPOINT", checkpoint)
    monkeypatch.setattr(module, "MODEL_REVISION", "sha256:" + sha256_file(checkpoint))
    monkeypatch.setattr(module, "COMPOSE_FILE", compose)
    monkeypatch.setattr(module, "DOCKER_BIN", str(docker))

    job = _job("PepMirror")
    job["target_pdb_sha256"] = sha256_file(target)
    command = module.prepare(job, _pepmirror_execution(), tmp_path / "attempt")

    assert command == ["bash", str(tmp_path / "attempt/command.sh")]
    patched = (tmp_path / "attempt/work/PepMirror/api/generate.py").read_text()
    assert 'setup_seed(int(os.environ["V034_SEED"]))' in patched
    assert "setup_seed(12)" in (source / "api/generate.py").read_text()
    script = (tmp_path / "attempt/command.sh").read_text()
    first_mirror = script.index("raw/mirrored_target.pdb")
    generation = script.index("api.generate")
    mirror_back = script.index("raw/pepmirror_candidate.pdb")
    assert first_mirror < generation < mirror_back
    for token in (
        "V034_SEED=42",
        "tgt_chains",
        "lig_chains",
        "size_min: 11",
        "size_max: 12",
        "n_samples: 1",
        "pepmirror_commutator_both_v1.ckpt",
        "pd-pyrosetta-methods-gpu-v021",
    ):
        assert token in script or token in (tmp_path / "attempt/raw/pepmirror_config.yaml").read_text()
    assert sha256_file(tmp_path / "attempt/raw/mirror_input.pdb") == sha256_file(target)
    assert not any(token in script for token in ("pip install", "git clone", "wget ", "curl ", "rank.py"))


def test_pepmirror_prepare_captures_verified_source_checkpoint_and_image_provenance(
    tmp_path: Path, monkeypatch
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    source = tmp_path / "source"
    _fake_pepmirror_source(source)
    source_commit = _commit_fixture_repo(source)
    target = tmp_path / "3EQS.pdb"
    checkpoint = tmp_path / "pepmirror_commutator_both_v1.ckpt"
    compose = tmp_path / "docker-compose.yml"
    docker = tmp_path / "docker"
    _write_complex(target)
    checkpoint.write_text("checkpoint\n", encoding="utf-8")
    compose.write_text(
        "services:\n"
        "  pd-pyrosetta-methods-gpu-v021:\n"
        "    image: pd-pyrosetta-methods-gpu:0.21\n",
        encoding="utf-8",
    )
    image_id = "sha256:" + "1" * 64
    _fake_docker_cli(docker, image_id)
    monkeypatch.setattr(module, "SOURCE_ROOT", source)
    monkeypatch.setattr(module, "SOURCE_COMMIT", source_commit)
    monkeypatch.setattr(module, "TARGET_PDB", target)
    monkeypatch.setattr(module, "CHECKPOINT", checkpoint)
    monkeypatch.setattr(module, "MODEL_REVISION", "sha256:" + sha256_file(checkpoint))
    monkeypatch.setattr(module, "COMPOSE_FILE", compose)
    monkeypatch.setattr(module, "DOCKER_BIN", str(docker), raising=False)

    attempt = tmp_path / "attempt"
    job = _job("PepMirror")
    job["target_pdb_sha256"] = sha256_file(target)
    module.prepare(job, _pepmirror_execution(), attempt)

    package_path = attempt / "package_evidence.json"
    assert package_path.is_file()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert package["source_commit_observed"] == source_commit
    assert package["source_commit_verified"] is True
    assert package["source_git_paths_clean"] is True
    assert package["source_tracked_file_count"] == 2
    source_manifest = Path(package["executed_source_manifest_path"])
    assert source_manifest.is_file()
    assert package["executed_source_manifest_sha256"] == sha256_file(source_manifest)
    assert package["generate_py_pre_sha256"] == sha256_file(source / "api/generate.py")
    assert package["generate_py_post_sha256"] == sha256_file(
        attempt / "work/PepMirror/api/generate.py"
    )
    assert package["generate_py_pre_sha256"] != package["generate_py_post_sha256"]
    assert package["mirror_pdb_py_pre_sha256"] == sha256_file(
        source / "scripts/mirror_pdb.py"
    )
    assert package["mirror_pdb_py_post_sha256"] == sha256_file(
        attempt / "work/PepMirror/scripts/mirror_pdb.py"
    )
    assert package["mirror_pdb_py_pre_sha256"] == package["mirror_pdb_py_post_sha256"]
    assert package["checkpoint_sha256"] == sha256_file(checkpoint)
    assert package["checkpoint_pin_verified"] is True
    assert package["target_pdb_sha256"] == sha256_file(target)
    assert package["target_preflight_verified"] is True
    assert package["compose_file_sha256"] == sha256_file(compose)
    assert package["compose_service"] == "pd-pyrosetta-methods-gpu-v021"
    assert package["compose_image_tag"] == "pd-pyrosetta-methods-gpu:0.21"
    assert package["image_id_observed_at_prepare"] == image_id
    assert package["image_inspect_stage"] == "prepare"
    assert str(docker) in package["image_inspect_command"]
    assert package["execution_environment_id"] == _pepmirror_execution()["container_or_env"]
    assert package["execution_environment_verified"] is True

    script = (attempt / "command.sh").read_text(encoding="utf-8")
    assert script.index("verify_runtime_preflight.py") < script.index("docker compose")
    assert script.index("docker compose") < script.index("scripts/mirror_pdb.py")
    assert "-e PYTHONDONTWRITEBYTECODE=1" in script
    assert f"{checkpoint}:{module.CONTAINER_CHECKPOINT}:ro" in script
    subprocess.run([sys.executable, str(attempt / "verify_runtime_preflight.py")], check=True)

    for name in ("mirrored_target.pdb", "mirrored_generated.pdb", "pepmirror_candidate.pdb"):
        _write_complex(attempt / "raw" / name)
    subprocess.run([sys.executable, str(attempt / "finalize_runtime.py")], check=True)
    runtime = json.loads((attempt / "runtime_evidence.json").read_text(encoding="utf-8"))
    for key, value in package.items():
        assert runtime[key] == value
    assert runtime["package_evidence_path"] == str(package_path)
    assert runtime["package_evidence_sha256"] == sha256_file(package_path)
    assert runtime["image_id_observed_pre_run"] == image_id
    assert runtime["image_identity_stable_pre_run"] is True
    assert runtime["image_inspect_execution_stage"] == "execution_pre_run"
    assert runtime["executed_source_manifest_verified_pre_run"] is True
    assert runtime["compose_file_verified_pre_run"] is True
    assert runtime["checkpoint_verified_pre_run"] is True
    assert runtime["target_input_verified_pre_run"] is True
    assert runtime["mirror_runtime_scope"] == "pinned_compose_conda_environment"
    assert runtime["mirror_runtime_conda_environment"] == "bench-pepmirror"
    assert runtime["mirror_commands_in_pinned_container"] is True

    candidate, _ = module.parse(job, attempt)
    assert candidate["structure_path"] == str(attempt / "raw/pepmirror_candidate.pdb")
    runtime["image_id_observed_pre_run"] = "sha256:" + "2" * 64
    (attempt / "runtime_evidence.json").write_text(json.dumps(runtime), encoding="utf-8")
    with pytest.raises(ValueError, match="execution preflight"):
        module.parse(job, attempt)


def test_pepmirror_source_provenance_rejects_modified_transitive_module(
    tmp_path: Path, monkeypatch
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    source = tmp_path / "source"
    _fake_pepmirror_source(source)
    helper = source / "api/helper.py"
    helper.write_text("VALUE = 1\n", encoding="utf-8")
    source_commit = _commit_fixture_repo(source)
    subprocess.run(["git", "-C", str(source), "add", "api/helper.py"], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-qm", "helper"], check=True)
    source_commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    helper.write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.setattr(module, "SOURCE_COMMIT", source_commit)

    with pytest.raises(ValueError, match="dirty"):
        module._source_provenance(source)


def test_pepmirror_copy_source_excludes_gitignored_injection(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    source = tmp_path / "source"
    _fake_pepmirror_source(source)
    (source / ".gitignore").write_text("api/ignored_inject.py\n", encoding="utf-8")
    _commit_fixture_repo(source)
    subprocess.run(["git", "-C", str(source), "add", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-qm", "ignore fixture"], check=True)
    (source / "api/ignored_inject.py").write_text("raise RuntimeError('injected')\n", encoding="utf-8")

    destination = tmp_path / "copied"
    module._copy_source(source, destination)

    assert (destination / "api/generate.py").is_file()
    assert not (destination / "api/ignored_inject.py").exists()


def test_dflow_parse_reads_only_standard_candidate_and_seed_evidence(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.v034_adapters.dflow")
    attempt = tmp_path / "attempt"
    candidate_path = attempt / "raw/dflow_candidate.pdb"
    _write_complex(candidate_path)
    runtime = _valid_dflow_runtime(module)
    (attempt / "runtime_evidence.json").write_text(json.dumps(runtime), encoding="utf-8")

    candidate, observed = module.parse(_job("D-Flow / PeptideDesign"), attempt)

    assert candidate["structure_path"] == str(candidate_path)
    assert candidate["sequence"] == "A" * 11
    assert candidate["binder_chain"] == "B"
    assert observed == runtime


def test_dflow_parse_fails_when_standard_candidate_is_missing(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.v034_adapters.dflow")
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    (attempt / "runtime_evidence.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="dflow_candidate.pdb"):
        module.parse(_job("D-Flow / PeptideDesign"), attempt)


def test_dflow_parse_rejects_unpinned_runtime_provenance(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.v034_adapters.dflow")
    attempt = tmp_path / "attempt"
    _write_complex(attempt / "raw/dflow_candidate.pdb")
    runtime = _valid_dflow_runtime(module)
    runtime["checkpoint_sha256"] = "0" * 64
    (attempt / "runtime_evidence.json").write_text(json.dumps(runtime), encoding="utf-8")

    with pytest.raises(ValueError, match="provenance"):
        module.parse(_job("D-Flow / PeptideDesign"), attempt)


def test_pepmirror_parse_binds_all_roundtrip_hashes_to_raw_files(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    attempt = tmp_path / "attempt"
    raw = attempt / "raw"
    paths = {
        "mirror_input": raw / "mirror_input.pdb",
        "mirrored_target": raw / "mirrored_target.pdb",
        "mirrored_generated": raw / "mirrored_generated.pdb",
        "mirror_output": raw / "pepmirror_candidate.pdb",
    }
    for index, path in enumerate(paths.values()):
        _write_complex(path)
        path.write_text(path.read_text() + f"REMARK {index}\n", encoding="utf-8")
    runtime = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "seed_patch_sha256": "b" * 64,
        "mirror_roundtrip_applied": True,
    }
    for name, path in paths.items():
        runtime[f"{name}_path"] = str(path)
        runtime[f"{name}_sha256"] = sha256_file(path)
    _bind_pepmirror_provenance(module, attempt, runtime)
    (attempt / "runtime_evidence.json").write_text(json.dumps(runtime), encoding="utf-8")

    candidate, observed = module.parse(_job("PepMirror"), attempt)

    assert candidate["structure_path"] == str(paths["mirror_output"])
    assert candidate["source_output_path"] == str(paths["mirror_output"])
    assert observed["mirror_roundtrip_applied"] is True
    assert all(str(raw) in observed[f"{name}_path"] for name in paths)


def test_pepmirror_parse_rejects_runtime_without_verified_package_provenance(
    tmp_path: Path,
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    attempt = tmp_path / "attempt"
    raw = attempt / "raw"
    paths = {
        "mirror_input": raw / "mirror_input.pdb",
        "mirrored_target": raw / "mirrored_target.pdb",
        "mirrored_generated": raw / "mirrored_generated.pdb",
        "mirror_output": raw / "pepmirror_candidate.pdb",
    }
    for path in paths.values():
        _write_complex(path)
    runtime = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "seed_patch_sha256": "b" * 64,
        "mirror_roundtrip_applied": True,
    }
    for name, path in paths.items():
        runtime[f"{name}_path"] = str(path)
        runtime[f"{name}_sha256"] = sha256_file(path)
    (attempt / "runtime_evidence.json").write_text(json.dumps(runtime), encoding="utf-8")

    with pytest.raises(ValueError, match="package provenance"):
        module.parse(_job("PepMirror"), attempt)


def test_pepmirror_parse_rejects_hash_mismatch(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    attempt = tmp_path / "attempt"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    for name in ("mirror_input.pdb", "mirrored_target.pdb", "mirrored_generated.pdb", "pepmirror_candidate.pdb"):
        _write_complex(raw / name)
    runtime = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "seed_patch_sha256": "b" * 64,
        "mirror_roundtrip_applied": True,
        "mirror_input_path": str(raw / "mirror_input.pdb"),
        "mirror_input_sha256": "0" * 64,
        "mirrored_target_path": str(raw / "mirrored_target.pdb"),
        "mirrored_target_sha256": sha256_file(raw / "mirrored_target.pdb"),
        "mirrored_generated_path": str(raw / "mirrored_generated.pdb"),
        "mirrored_generated_sha256": sha256_file(raw / "mirrored_generated.pdb"),
        "mirror_output_path": str(raw / "pepmirror_candidate.pdb"),
        "mirror_output_sha256": sha256_file(raw / "pepmirror_candidate.pdb"),
    }
    _bind_pepmirror_provenance(module, attempt, runtime)
    (attempt / "runtime_evidence.json").write_text(json.dumps(runtime), encoding="utf-8")
    with pytest.raises(ValueError, match="mirror_input_sha256"):
        module.parse(_job("PepMirror"), attempt)


def test_pepmirror_parse_does_not_promote_unmirrored_temporary_pdb(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepmirror")
    attempt = tmp_path / "attempt"
    _write_complex(attempt / "raw/mirrored_generated.pdb")
    (attempt / "runtime_evidence.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="pepmirror_candidate.pdb"):
        module.parse(_job("PepMirror"), attempt)


def test_pepglad_execution_identity_constants_match_fixed_bytes() -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")

    assert hashlib.sha256(module.OBSERVER_SCRIPT.encode("utf-8")).hexdigest() == (
        module.OBSERVER_SCRIPT_SHA256
    )
    assert hashlib.sha256(module.INSTRUMENTER_SCRIPT.encode("utf-8")).hexdigest() == (
        module.INSTRUMENTER_SCRIPT_SHA256
    )
    assert hashlib.sha256(module.SEED_WRAPPER_SCRIPT.encode("utf-8")).hexdigest() == (
        module.SEED_WRAPPER_SCRIPT_SHA256
    )
    assert sha256_file(module.SOURCE_ENTRYPOINT) == module.SOURCE_ENTRYPOINT_SHA256
    assert _pepglad_instrumented_sha256(module.SOURCE_ENTRYPOINT) == (
        module.SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256
    )


@pytest.mark.parametrize(
    "script_name",
    ("OBSERVER_SCRIPT", "INSTRUMENTER_SCRIPT", "SEED_WRAPPER_SCRIPT"),
)
def test_pepglad_prepare_rejects_replaced_execution_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    script_name: str,
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    replacement = getattr(module, script_name, "") + "\n# replaced execution identity\n"

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        _prepare_pepglad_instrumentation_fixture(
            tmp_path,
            monkeypatch,
            script_override=(script_name, replacement),
        )


def test_pepglad_instrumenter_rejects_changed_instrumented_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, attempt, job, _, source_sha256 = _prepare_pepglad_instrumentation_fixture(
        tmp_path, monkeypatch
    )
    patcher = attempt / "pepglad_instrument_source.py"
    original_patcher = patcher.read_text(encoding="utf-8")
    changed_patcher = original_patcher.replace(
        'b"    capture_pre_relax_pdb(pdb_path)\\n"',
        'b"    capture_pre_relax_pdb(str(pdb_path))\\n"',
        1,
    )
    assert changed_patcher != original_patcher
    patcher.write_text(changed_patcher, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(patcher),
            "--source-entrypoint",
            str(attempt / "work/api/run.py"),
            "--expected-source-sha256",
            source_sha256,
            "--expected-instrumented-source-sha256",
            module.SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256,
            "--observer-source",
            str(attempt / "pepglad_observer.py"),
            "--expected-observer-sha256",
            sha256_file(attempt / "pepglad_observer.py"),
            "--expected-patch-sha256",
            sha256_file(patcher),
            "--target-input",
            job["target_pdb_path"],
            "--expected-target-sha256",
            job["target_pdb_sha256"],
            "--evidence",
            str(attempt / "observer_patch_evidence.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "PepGLAD instrumented source SHA256 mismatch" in result.stderr
    assert not (attempt / "observer_patch_evidence.json").exists()


def test_pepglad_attempt_observer_captures_before_and_preserves_relaxation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, attempt, job, source_entrypoint, source_sha256 = (
        _prepare_pepglad_instrumentation_fixture(tmp_path, monkeypatch)
    )
    original_source = source_entrypoint.read_bytes()
    evidence_path = _instrument_pepglad_attempt(
        attempt,
        job,
        source_sha256,
        module.SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256,
    )
    candidate = attempt / "work/codesign/3EQS_0.pdb"
    _write_complex(candidate)
    initial_candidate = candidate.read_bytes()
    marker = attempt / "relaxation_called.txt"
    pre_relax = attempt / "raw/pepglad_pre_relax.pdb"
    env = dict(os.environ)
    env.update(
        PYTHONPATH=f"{attempt}:{attempt / 'work'}",
        V034_PRE_RELAX_PATH=str(pre_relax),
        V034_RELAX_MARKER=str(marker),
    )

    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from api.run import openmm_relax; "
                f"openmm_relax({str(candidate)!r})"
            ),
        ],
        check=True,
        env=env,
    )

    instrumented = (attempt / "work/api/run.py").read_text(encoding="utf-8")
    assert instrumented.index("capture_pre_relax_pdb(pdb_path)") < instrumented.index(
        "force_field = ForceFieldMinimizer()"
    )
    assert instrumented.count("force_field(pdb_path, pdb_path)") == 1
    assert marker.read_text(encoding="utf-8") == "called\n"
    assert pre_relax.read_bytes() == initial_candidate
    assert candidate.read_bytes() == initial_candidate + b"REMARK OPENMM RELAXATION EXECUTED\n"
    assert source_entrypoint.read_bytes() == original_source
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["observer_injection_status"] == "applied"
    assert evidence["target_preflight_verified"] is True
    assert evidence["observer_patch_path"] == "pepglad_instrument_source.py"
    assert evidence["observer_source_path"] == "pepglad_observer.py"
    assert evidence["source_entrypoint_path"] == "work/api/run.py"
    assert evidence["source_entrypoint_prepatch_sha256"] == source_sha256
    assert evidence["source_entrypoint_instrumented_sha256"] == sha256_file(
        attempt / "work/api/run.py"
    )
    assert evidence["observer_source_sha256"] == sha256_file(
        attempt / "pepglad_observer.py"
    )
    assert evidence["observer_patch_sha256"] == sha256_file(
        attempt / "pepglad_instrument_source.py"
    )


def test_pepglad_finalizer_keeps_post_relax_candidate_and_records_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, attempt, job, _, source_sha256 = _prepare_pepglad_instrumentation_fixture(
        tmp_path, monkeypatch
    )
    evidence_path = _instrument_pepglad_attempt(
        attempt,
        job,
        source_sha256,
        module.SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256,
    )
    post_relax = attempt / "work/codesign/3EQS_0.pdb"
    pre_relax = attempt / "raw/pepglad_pre_relax.pdb"
    summary_source = attempt / "work/codesign/summary.jsonl"
    _write_complex(post_relax)
    pre_relax.write_bytes(post_relax.read_bytes())
    post_relax.write_bytes(post_relax.read_bytes() + b"REMARK RELAXED\n")
    summary_source.parent.mkdir(parents=True, exist_ok=True)
    summary_source.write_text(
        '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B",'
        '"pep_seq":"AAAAAAAAAAA"}\n',
        encoding="utf-8",
    )
    output = attempt / "raw/pepglad_candidate.pdb"
    summary_output = attempt / "raw/pepglad_summary.jsonl"
    runtime = attempt / "raw/runtime_evidence.json"
    baseline = sha256_file(post_relax)
    monkeypatch.setattr(module, "SEED42_POST_RELAX_BASELINE_SHA256", baseline)

    subprocess.run(
        [
            sys.executable,
            str(attempt / "pepglad_finalize.py"),
            "--source",
            str(post_relax),
            "--pre-relax",
            str(pre_relax),
            "--output",
            str(output),
            "--summary-source",
            str(summary_source),
            "--summary-output",
            str(summary_output),
            "--runtime",
            str(runtime),
            "--patch-evidence",
            str(evidence_path),
            "--attempt-root",
            str(attempt),
            "--observer-patch",
            str(attempt / "pepglad_instrument_source.py"),
            "--observer-source",
            str(attempt / "pepglad_observer.py"),
            "--seed-wrapper",
            str(attempt / "pepglad_seeded_entry.py"),
            "--instrumented-source",
            str(attempt / "work/api/run.py"),
            "--target-input",
            job["target_pdb_path"],
            "--expected-target-sha256",
            job["target_pdb_sha256"],
            "--binder-chain",
            "B",
            "--expected-chirality",
            "L",
            "--seed",
            "42",
            "--baseline-sha256",
            baseline,
        ],
        check=True,
    )

    observed = json.loads(runtime.read_text(encoding="utf-8"))
    assert output.read_bytes() == post_relax.read_bytes()
    assert output.read_bytes() != pre_relax.read_bytes()
    assert summary_output.read_bytes() == summary_source.read_bytes()
    assert observed["recovery_mode"] == "instrumented_official_pipeline"
    assert observed["pre_relax_path"] == "raw/pepglad_pre_relax.pdb"
    assert observed["pre_relax_sha256"] == sha256_file(pre_relax)
    assert observed["post_relax_path"] == "raw/pepglad_candidate.pdb"
    assert observed["post_relax_sha256"] == sha256_file(output)
    assert observed["source_candidate_path"] == "work/codesign/3EQS_0.pdb"
    assert observed["observer_patch_path"] == "pepglad_instrument_source.py"
    assert observed["observer_source_path"] == "pepglad_observer.py"
    assert observed["seed_wrapper_path"] == "pepglad_seeded_entry.py"
    assert observed["seed_wrapper_sha256"] == sha256_file(
        attempt / "pepglad_seeded_entry.py"
    )
    assert observed["instrumented_source_path"] == "work/api/run.py"
    assert observed["first_observed_chirality_failure_stage"] == (
        "pre_openmm_snapshot"
    )
    for field in (
        "pre_relax_path",
        "post_relax_path",
        "source_candidate_path",
        "observer_patch_path",
        "observer_source_path",
        "seed_wrapper_path",
        "instrumented_source_path",
    ):
        assert (attempt / observed[field]).resolve().is_relative_to(attempt.resolve())
        assert (attempt / observed[field]).is_file()
    assert observed["target_preflight_verified"] is True
    assert observed["baseline_replay_status"] == "match"
    assert observed["baseline_replay_expected_sha256"] == baseline
    assert observed["baseline_replay_observed_sha256"] == baseline
    assert observed["pre_relax_binder_chirality"] == {
        "chain": "B",
        "d_count": 11,
        "evaluable": 11,
        "gly_count": 0,
        "l_count": 0,
        "status": "pass",
        "unknown_count": 0,
    }
    assert observed["post_relax_binder_chirality"] == observed[
        "pre_relax_binder_chirality"
    ]
    candidate, parsed_runtime = module.parse(job, attempt)
    assert candidate["structure_path"] == str(output)
    assert candidate["source_output_path"] == str(output)
    assert candidate["structure_path"] != observed["pre_relax_path"]
    assert parsed_runtime["baseline_replay_status"] == "match"


def test_pepglad_seed42_replay_mismatch_is_not_promoted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    attempt = tmp_path / "attempt_003"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    candidate_path = raw / "pepglad_candidate.pdb"
    _write_complex(candidate_path)
    (raw / "pepglad_summary.jsonl").write_text(
        '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B",'
        '"pep_seq":"AAAAAAAAAAA"}\n',
        encoding="utf-8",
    )
    baseline = "a" * 64
    monkeypatch.setattr(module, "SEED42_POST_RELAX_BASELINE_SHA256", baseline)
    (raw / "runtime_evidence.json").write_text(
        json.dumps(
            {
                "requested_seed": 42,
                "effective_seed": 42,
                "seed_control_status": "honored",
                "recovery_mode": "instrumented_official_pipeline",
                "baseline_replay_expected_sha256": baseline,
                "baseline_replay_observed_sha256": sha256_file(candidate_path),
                "baseline_replay_status": "mismatch",
            }
        ),
        encoding="utf-8",
    )
    job = {
        **_job("PepGLAD"),
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
    }

    candidate, runtime = module.parse(job, attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["structure_path"] == ""
    assert candidate["status_reason"] == "pepglad_seed42_replay_mismatch"
    assert runtime["baseline_replay_status"] == "mismatch"


def test_pepglad_seed42_replay_rejects_post_output_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    attempt = tmp_path / "attempt_003"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    candidate_path = raw / "pepglad_candidate.pdb"
    _write_complex(candidate_path)
    original_digest = sha256_file(candidate_path)
    monkeypatch.setattr(
        module, "SEED42_POST_RELAX_BASELINE_SHA256", original_digest
    )
    (raw / "pepglad_summary.jsonl").write_text(
        '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B",'
        '"pep_seq":"AAAAAAAAAAA"}\n',
        encoding="utf-8",
    )
    (raw / "runtime_evidence.json").write_text(
        json.dumps(
            {
                "requested_seed": 42,
                "effective_seed": 42,
                "seed_control_status": "honored",
                "recovery_mode": "instrumented_official_pipeline",
                "baseline_replay_expected_sha256": original_digest,
                "baseline_replay_observed_sha256": original_digest,
                "post_relax_sha256": original_digest,
                "baseline_replay_status": "match",
            }
        ),
        encoding="utf-8",
    )
    candidate_path.write_bytes(candidate_path.read_bytes() + b"REMARK TAMPERED\n")
    job = {
        **_job("PepGLAD"),
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
    }

    candidate, _ = module.parse(job, attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["status_reason"] == "pepglad_seed42_replay_mismatch"


def test_pepglad_seed42_replay_rejects_self_consistent_nonbaseline_output(
    tmp_path: Path,
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    attempt = tmp_path / "attempt_003"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    candidate_path = raw / "pepglad_candidate.pdb"
    _write_complex(candidate_path)
    observed_digest = sha256_file(candidate_path)
    assert observed_digest != module.SEED42_POST_RELAX_BASELINE_SHA256
    (raw / "pepglad_summary.jsonl").write_text(
        '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B",'
        '"pep_seq":"AAAAAAAAAAA"}\n',
        encoding="utf-8",
    )
    (raw / "runtime_evidence.json").write_text(
        json.dumps(
            {
                "requested_seed": 42,
                "effective_seed": 42,
                "seed_control_status": "honored",
                "recovery_mode": "instrumented_official_pipeline",
                "baseline_replay_expected_sha256": (
                    module.SEED42_POST_RELAX_BASELINE_SHA256
                ),
                "baseline_replay_observed_sha256": observed_digest,
                "post_relax_path": "raw/pepglad_candidate.pdb",
                "post_relax_sha256": observed_digest,
                "baseline_replay_status": "match",
            }
        ),
        encoding="utf-8",
    )
    job = {
        **_job("PepGLAD"),
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
    }

    candidate, _ = module.parse(job, attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["status_reason"] == "pepglad_seed42_replay_mismatch"


def test_pepglad_seed42_replay_gate_cannot_be_skipped_without_recovery_mode(
    tmp_path: Path,
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    attempt = tmp_path / "attempt_003"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    candidate_path = raw / "pepglad_candidate.pdb"
    _write_complex(candidate_path)
    observed_digest = sha256_file(candidate_path)
    (raw / "pepglad_summary.jsonl").write_text(
        '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B",'
        '"pep_seq":"AAAAAAAAAAA"}\n',
        encoding="utf-8",
    )
    (raw / "runtime_evidence.json").write_text(
        json.dumps(
            {
                "requested_seed": 42,
                "effective_seed": 42,
                "seed_control_status": "honored",
                "baseline_replay_expected_sha256": (
                    module.SEED42_POST_RELAX_BASELINE_SHA256
                ),
                "baseline_replay_observed_sha256": observed_digest,
                "post_relax_path": "raw/pepglad_candidate.pdb",
                "post_relax_sha256": observed_digest,
                "baseline_replay_status": "match",
            }
        ),
        encoding="utf-8",
    )
    job = {
        **_job("PepGLAD"),
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
    }

    candidate, _ = module.parse(job, attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["status_reason"] == "pepglad_seed42_replay_mismatch"


@pytest.mark.parametrize("duplicate_key", ("requested_seed", "recovery_mode"))
def test_pepglad_duplicate_runtime_json_key_falls_back_missing_and_is_not_promoted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    duplicate_key: str,
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    attempt = tmp_path / "attempt_003"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    candidate_path = raw / "pepglad_candidate.pdb"
    _write_complex(candidate_path)
    observed_digest = sha256_file(candidate_path)
    monkeypatch.setattr(
        module, "SEED42_POST_RELAX_BASELINE_SHA256", observed_digest
    )
    (raw / "pepglad_summary.jsonl").write_text(
        '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B",'
        '"pep_seq":"AAAAAAAAAAA"}\n',
        encoding="utf-8",
    )
    pairs: list[tuple[str, object]] = [
        ("requested_seed", 42),
        ("effective_seed", 42),
        ("seed_control_status", "honored"),
        ("recovery_mode", module.RECOVERY_MODE),
        ("baseline_replay_expected_sha256", observed_digest),
        ("baseline_replay_observed_sha256", observed_digest),
        ("post_relax_path", "raw/pepglad_candidate.pdb"),
        ("post_relax_sha256", observed_digest),
        ("baseline_replay_status", "match"),
    ]
    duplicate_value: object
    if duplicate_key == "requested_seed":
        duplicate_value = 0
    else:
        duplicate_value = "untrusted_recovery_mode"
    duplicate_index = next(
        index for index, (key, _) in enumerate(pairs) if key == duplicate_key
    )
    pairs.insert(duplicate_index, (duplicate_key, duplicate_value))
    runtime_payload = "{\n" + ",\n".join(
        f"{json.dumps(key)}: {json.dumps(value)}" for key, value in pairs
    ) + "\n}\n"
    (raw / "runtime_evidence.json").write_text(runtime_payload, encoding="utf-8")
    job = {
        **_job("PepGLAD"),
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
    }

    candidate, runtime = module.parse(job, attempt)

    assert runtime == {
        "requested_seed": 42,
        "effective_seed": -1,
        "seed_control_status": "missing",
    }
    assert candidate["parse_status"] == "failed"
    assert candidate["structure_path"] == ""
    assert candidate["status_reason"] == "pepglad_seed42_replay_mismatch"


def test_pepglad_seed42_legacy_runtime_copy_rejects_nonbaseline_candidate(
    tmp_path: Path,
) -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    attempt = tmp_path / "attempt_002"
    raw = attempt / "raw"
    raw.mkdir(parents=True)
    candidate_path = raw / "pepglad_candidate.pdb"
    _write_complex(candidate_path)
    (raw / "pepglad_summary.jsonl").write_text(
        '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B",'
        '"pep_seq":"AAAAAAAAAAA"}\n',
        encoding="utf-8",
    )
    legacy_runtime = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "source_commit": module.SOURCE_COMMIT,
        "source_entrypoint_sha256": module.SOURCE_ENTRYPOINT_SHA256,
        "model_weights_sha256": module.MODEL_WEIGHTS_SHA256,
        "source_candidate_path": "/data/attempt/work/codesign/3EQS_0.pdb",
        "container_image": module.DEFAULT_IMAGE,
        "conda_environment": module.DEFAULT_ENV,
    }
    assert set(legacy_runtime) == {
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
    (raw / "runtime_evidence.json").write_text(
        json.dumps(legacy_runtime), encoding="utf-8"
    )
    job = {
        **_job("PepGLAD"),
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
    }

    candidate, _ = module.parse(job, attempt)

    assert sha256_file(candidate_path) != module.SEED42_POST_RELAX_BASELINE_SHA256
    assert candidate["parse_status"] == "failed"
    assert candidate["status_reason"] == "pepglad_seed42_replay_mismatch"


def test_pepglad_seed42_real_legacy_attempt_002_remains_parseable() -> None:
    module = importlib.import_module("scripts.v034_adapters.pepglad")
    attempt = (
        Path(__file__).resolve().parents[1]
        / "benchmark_runs/v0.34/pepglad/v034_pepglad_3eqs_seed42/attempt_002"
    )
    if not attempt.is_dir():
        pytest.skip("external v0.34 PepGLAD attempt_002 is not present")
    job = json.loads((attempt / "job.json").read_text(encoding="utf-8"))
    candidate_path = attempt / "raw/pepglad_candidate.pdb"

    candidate, runtime = module.parse(job, attempt)

    assert sha256_file(candidate_path) == module.SEED42_POST_RELAX_BASELINE_SHA256
    assert set(runtime) == module.PEPGLAD_LEGACY_RUNTIME_FIELDS
    assert candidate["parse_status"] == "parsed"
    assert candidate["structure_path"] == str(candidate_path)


def test_chiral_adapters_expose_pinned_identity_constants() -> None:
    dflow = importlib.import_module("scripts.v034_adapters.dflow")
    pepmirror = importlib.import_module("scripts.v034_adapters.pepmirror")
    assert dflow.METHOD == "D-Flow / PeptideDesign"
    assert dflow.SOURCE_COMMIT == "3e3e9f501ee16db318e9bf52643513636a07699a"
    assert dflow.MODEL_REVISION == "sha256:95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17"
    assert pepmirror.METHOD == "PepMirror"
    assert pepmirror.SOURCE_COMMIT == "41cb31f3974d91e1a2ca88f0db060405833e4a9c"
    assert pepmirror.MODEL_REVISION == "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"
