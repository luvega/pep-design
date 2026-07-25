from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import pickle
from pathlib import Path

import pytest

from scripts.v034_adapters import pepglad as pepglad_adapter
from scripts.v034_adapters.common import (
    chirality_stats,
    evaluate_candidate_qc,
    parse_pdb_chain_sequences,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/parse_v034_generation_outputs.py"

RUNTIME_TARGET_CONTEXT_METHODS = frozenset(
    {"DiffPepBuilder", "D-Flow / PeptideDesign"}
)
JOB_TARGET_PDB_METHODS = frozenset(
    {
        "PepGLAD",
        "PepMirror",
        "AfCycDesign / ColabDesign cyclic peptide",
        "RFdiffusion + ProteinMPNN",
    }
)
EXACT_RUNTIME_TARGET_CONTEXTS = {
    "DiffPepBuilder": "TLLYTMKEVLFYLGQYIMTKRLYDEKQQHIVYCSFSVKEHRKIYTMI",
    "D-Flow / PeptideDesign": "TVLLLTMKEVLFYLGQYIMTKRLYDEKQQHIVYCLLFFSVKEHRKIYTMIY",
}

METHOD_MANIFEST_CONTRACTS = {
    "PepMLM": (
        "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
        "898fca941a9057aebdd1a6164b5ee09a1a71780e",
        "pd-benchmark-methods-gpu:0.21/bench-pepmlm",
    ),
    "DiffPepBuilder": (
        "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
        "diffpepbuilder_v1.pth_external_manifest_v0.20",
        "pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder",
    ),
    "PepGLAD": (
        "bad015ca50c312a89482adb5220c3d907f13df5c",
        "codesign.ckpt_external_manifest_v0.21",
        "pd-benchmark-methods-gpu:0.21/bench-pepglad",
    ),
    "D-Flow / PeptideDesign": (
        "3e3e9f501ee16db318e9bf52643513636a07699a",
        "sha256:95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17",
        "host:.venv/dflow-v023",
    ),
    "PepMirror": (
        "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
        "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2",
        "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror",
    ),
    "AfCycDesign / ColabDesign cyclic peptide": (
        "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
        "alphafold_model_1_ptm@sha256:5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84",
        "pd-benchmark-methods-gpu:0.21/bench-colabdesign",
    ),
    "RFdiffusion + ProteinMPNN": (
        "RFdiffusion@2d0c003df46b9db41d119321f15403dec3716cd9;"
        "ProteinMPNN@8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
        "RFdiffusion_external_models;proteinmpnn_v_48_020.pt",
        "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest",
    ),
}

METHOD_SOURCE_OUTPUT_IDS = {
    "PepMLM": "pepmlm_generated.csv",
    "DiffPepBuilder": "diffpepbuilder_candidate.pdb",
    "PepGLAD": "pepglad_candidate.pdb",
    "D-Flow / PeptideDesign": "dflow_candidate.pdb",
    "PepMirror": "pepmirror_candidate.pdb",
    "AfCycDesign / ColabDesign cyclic peptide": "afcycdesign_candidate.pdb",
    "RFdiffusion + ProteinMPNN": "design.fa:T=0.1",
}

PEPGLAD_SEED42_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)
PEPGLAD_SOURCE_ENTRYPOINT_SHA256 = (
    "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
)
PEPGLAD_PRODUCER_SHA256 = {
    "observer_patch_sha256": (
        "cd9ec19f6605fd2b067824d4e02971b3a203e827b6398a4ffd1c68c64464311a"
    ),
    "observer_source_sha256": (
        "a0a98420dd2fd5382479abe77526fb8fc206ffb1e69a8780912fb821dded0c61"
    ),
    "seed_wrapper_sha256": (
        "6a9b4c9012205d27526e13dbccbd7d11c010eddc3c85acdb2796c2fa6668aaba"
    ),
    "source_entrypoint_instrumented_sha256": (
        "c3b127e39be1b335ff6046bb2435451acfc1b323839377033bf438ccd4a32954"
    ),
}

AA1_TO_3 = {
    "A": "ALA",
    "C": "CYS",
    "D": "ASP",
    "E": "GLU",
    "F": "PHE",
    "G": "GLY",
    "H": "HIS",
    "I": "ILE",
    "K": "LYS",
    "L": "LEU",
    "M": "MET",
    "N": "ASN",
    "P": "PRO",
    "Q": "GLN",
    "R": "ARG",
    "S": "SER",
    "T": "THR",
    "V": "VAL",
    "W": "TRP",
    "Y": "TYR",
}


def load_parser():
    spec = importlib.util.spec_from_file_location(
        "parse_v034_generation_outputs", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=row.keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)


def write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    assert rows
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _one_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    return rows[0]


def _prepend_conflicting_json_key(path: Path, key: str, value: object) -> None:
    payload = path.read_text(encoding="utf-8")
    assert payload.startswith("{\n")
    duplicate = f"  {json.dumps(key)}: {json.dumps(value)},\n"
    path.write_text("{\n" + duplicate + payload[2:], encoding="utf-8")


def write_complete_attempt(
    parser, run_root: Path, job: dict[str, str], number: int = 1
) -> Path:
    job_root = run_root / parser.METHOD_SLUGS[job["method"]] / job["job_id"]
    attempt = job_root / f"attempt_{number:03d}"
    attempt.mkdir(parents=True)
    design_id = f"{job['job_id']}_candidate_1"
    (attempt / "run_result.json").write_text(
        json.dumps(
            {
                "job_id": job["job_id"],
                "method": job["method"],
                "status": "passed",
                "overall_qc_status": "pass",
                "design_id": design_id,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(
        attempt / "method_output_manifest.csv",
        {
            "run_record_id": f"{job['job_id']}_attempt_{number:03d}",
            "job_id": job["job_id"],
            "status": "passed",
        },
    )
    write_csv(
        attempt / "candidate_outputs.csv",
        {
            "design_id": design_id,
            "job_id": job["job_id"],
            "sequence": "ACD",
            "parse_status": "parsed",
        },
    )
    write_csv(
        attempt / "candidate_qc.csv",
        {"design_id": design_id, "job_id": job["job_id"], "overall_qc_status": "pass"},
    )
    runtime = {
        "requested_seed": int(job["random_seed"]),
        "effective_seed": int(job["random_seed"]),
        "seed_control_status": "honored",
    }
    (attempt / "runtime_evidence.json").write_text(
        json.dumps(runtime, indent=2) + "\n", encoding="utf-8"
    )
    return attempt


def _write_bound_file(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _minimal_pdb(
    chains: dict[str, str],
    *,
    chain_chirality: dict[str, str] | None = None,
    chain_starts: dict[str, int] | None = None,
    cyclic_chains: frozenset[str] = frozenset(),
) -> bytes:
    chain_chirality = chain_chirality or {}
    chain_starts = chain_starts or {}
    lines: list[str] = []
    serial = 1
    for chain_index, (chain, sequence) in enumerate(chains.items()):
        start = chain_starts.get(chain, 1)
        y = float(chain_index * 10)
        for offset_index, residue in enumerate(sequence):
            residue_index = start + offset_index
            resname = AA1_TO_3[residue]
            base = float(offset_index * 3)
            coordinates = {
                "N": (base + 1.0, y, 0.0),
                "CA": (base, y, 0.0),
                "C": (base, y + 1.0, 0.0),
            }
            if chain in cyclic_chains and offset_index == 0:
                coordinates.update(N=(0.0, y, 0.0), CA=(-1.0, y, 0.0), C=(-1.0, y + 1.0, 0.0))
            if chain in cyclic_chains and offset_index == len(sequence) - 1:
                coordinates.update(N=(2.3, y - 1.0, 0.0), CA=(1.3, y - 1.0, 0.0), C=(1.3, y, 0.0))
            if residue != "G":
                z = 1.0 if chain_chirality.get(chain, "L") == "L" else -1.0
                ca = coordinates["CA"]
                coordinates["CB"] = (ca[0], ca[1], z)
            for atom_name, element in (
                ("N", "N"),
                ("CA", "C"),
                ("C", "C"),
                ("CB", "C"),
            ):
                if atom_name not in coordinates:
                    continue
                x, atom_y, z = coordinates[atom_name]
                lines.append(
                    f"ATOM  {serial:5d} {atom_name:>4s} {resname:>3s} "
                    f"{chain:1s}{residue_index:4d}    "
                    f"{x:8.3f}{atom_y:8.3f}{z:8.3f}"
                    f"  1.00 20.00           {element:>2s}"
                )
                serial += 1
        lines.append("TER")
    lines.append("END")
    return ("\n".join(lines) + "\n").encode("ascii")


def _central_invert_pdb(payload: bytes) -> bytes:
    lines = payload.decode("ascii").splitlines()
    atom_indexes = [
        index
        for index, line in enumerate(lines)
        if line.startswith(("ATOM  ", "HETATM"))
    ]
    coordinates = [
        (float(lines[index][30:38]), float(lines[index][38:46]), float(lines[index][46:54]))
        for index in atom_indexes
    ]
    center = tuple(
        sum(point[axis] for point in coordinates) / len(coordinates)
        for axis in range(3)
    )
    for index, point in zip(atom_indexes, coordinates):
        inverted = tuple(2.0 * center[axis] - point[axis] for axis in range(3))
        line = lines[index]
        lines[index] = (
            f"{line[:30]}{inverted[0]:8.3f}{inverted[1]:8.3f}{inverted[2]:8.3f}{line[54:]}"
        )
    return ("\n".join(lines) + "\n").encode("ascii")


def _job_target_sequence(job: dict[str, str]) -> str:
    target_path = Path(job["target_pdb_path"])
    if not target_path.is_absolute():
        target_path = ROOT / target_path
    return parse_pdb_chain_sequences(target_path)[job["expected_target_chain"]]


def _runtime_target_context_sequence(job: dict[str, str]) -> str:
    return EXACT_RUNTIME_TARGET_CONTEXTS[job["method"]]


def _contract_runtime(
    job: dict[str, str], attempt: Path, candidate_path: Path, source_output_path: Path
) -> dict[str, object]:
    method = job["method"]
    seed = int(job["random_seed"])
    source_commit, model_revision, environment = METHOD_MANIFEST_CONTRACTS[method]
    runtime: dict[str, object] = {
        "requested_seed": seed,
        "effective_seed": seed,
        "seed_control_status": "honored",
    }
    if method == "PepMLM":
        runtime.update(
            source_commit=source_commit,
            source_entrypoint_sha256=(
                "2c1844028c459e8e96d756da795b620b4ccaa65b98dd62c6f904100f0dc1e49b"
            ),
            model_id="TianlaiChen/PepMLM-650M",
            model_revision=model_revision,
            model_weights_sha256=(
                "8a3225bca1f9acd9f701ca2e46597c12bab92320e32b68f380ddf3b6d3b20770"
            ),
            container_image="pd-benchmark-methods-gpu:0.21",
            conda_environment="bench-pepmlm",
            sampling_strategy="top_k_categorical",
            top_k=3,
        )
    elif method == "DiffPepBuilder":
        target = attempt / "raw/diffpepbuilder_target_context.pdb"
        target_sha = _write_bound_file(
            target,
            _minimal_pdb(
                {
                    job["expected_target_chain"]: _runtime_target_context_sequence(
                        job
                    )
                }
            ),
        )
        runtime.update(
            source_commit=source_commit,
            source_entrypoint_sha256=(
                "872868f48e3cf66f0ce159ada589ca2126a3b2ba98470ab3bbcb9ffc4481f7c6"
            ),
            model_asset_sha256={
                "diffpepbuilder_v1.pth": (
                    "dbc4283257d27e38a1ce90c9344063b046ab7161745ebed1fd98a4b0439b992a"
                ),
                "esm2_t33_650M_UR50D-contact-regression.pt": (
                    "8ffe6edbd4173dc8d45c2cd5cb27d43aad77ec26b4c768200c58ae1f96693575"
                ),
                "esm2_t33_650M_UR50D.pt": (
                    "ea9d0522b335a8778dea6535a65301f10208dece28cd5865482b0b1fc446168c"
                ),
            },
            filtered_receptor_sha256="7" * 64,
            source_candidate_path="/data/attempt/work/runs/inference/3EQS_length_11_sample_0.pdb",
            container_image="pd-pyrosetta-methods-gpu:0.20",
            conda_environment="bench-diffpepbuilder",
            target_context_chain="B",
            target_context_mode="ordered_subsequence",
            target_context_path=str(target),
            target_context_sha256=target_sha,
        )
    elif method == "PepGLAD":
        runtime.update(
            source_commit=source_commit,
            source_entrypoint_sha256=(
                "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
            ),
            model_weights_sha256=(
                "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
            ),
            source_candidate_path="/data/attempt/work/codesign/3EQS_0.pdb",
            container_image="pd-benchmark-methods-gpu:0.21",
            conda_environment="bench-pepglad",
        )
    elif method == "D-Flow / PeptideDesign":
        source_entrypoint = (
            attempt / "work/PeptideDesign/dflow/experiments/inference_pep.py"
        )
        source_entrypoint_sha = _write_bound_file(
            source_entrypoint, b"# bounded test entrypoint\n"
        )
        source_manifest = attempt / "source_content_manifest.json"
        source_manifest_payload = {
            "schema_version": "v034_dflow_source_content_v1",
            "source_commit": source_commit,
            "source_copy_mode": "git_tracked_files_only",
            "source_entrypoint_prepatch_sha256": (
                "6be8b50b876cc94c8a212165d7327bd46c0e906d2c85fc6c2b03a66ff9e2cd9d"
            ),
            "source_entrypoint_patched_sha256": source_entrypoint_sha,
            "files": [
                {
                    "path": "dflow/experiments/inference_pep.py",
                    "sha256": source_entrypoint_sha,
                    "size_bytes": source_entrypoint.stat().st_size,
                }
            ],
        }
        source_manifest_sha = _write_bound_file(
            source_manifest,
            (
                json.dumps(source_manifest_payload, indent=2, sort_keys=True) + "\n"
            ).encode(),
        )
        target = attempt / "raw/dflow_target_context.pdb"
        target_sha = _write_bound_file(
            target,
            _minimal_pdb(
                {
                    job["expected_target_chain"]: _runtime_target_context_sequence(
                        job
                    )
                }
            ),
        )
        runtime.update(
            method=method,
            source_commit=source_commit,
            source_copy_mode="git_tracked_files_only",
            source_git_tracked_paths_clean=True,
            source_tracked_file_count=1,
            source_content_manifest_path=str(source_manifest),
            source_content_manifest_sha256=source_manifest_sha,
            source_entrypoint_path=str(source_entrypoint),
            source_entrypoint_prepatch_sha256=(
                "6be8b50b876cc94c8a212165d7327bd46c0e906d2c85fc6c2b03a66ff9e2cd9d"
            ),
            source_entrypoint_patched_sha256=source_entrypoint_sha,
            checkpoint_path=str(attempt / "work/dflow.pt"),
            checkpoint_resolved_path="/weights/dflow.pt",
            checkpoint_sha256=model_revision.removeprefix("sha256:"),
            execution_environment_declared=environment,
            execution_environment_type="host_local_python_environment",
            containerized=False,
            host_environment_path=str(attempt / "work/PeptideDesign/.venv"),
            python_invocation_path=str(attempt / "work/PeptideDesign/.venv/bin/python"),
            python_executable_path=str(attempt / "work/PeptideDesign/.venv/bin/python"),
            python_executable_realpath="/usr/bin/python3",
            python_executable_sha256="8" * 64,
            python_version="3.10.0",
            python_prefix=str(attempt / "work/PeptideDesign/.venv"),
            python_base_prefix="/usr",
            source_checkout_path=str(attempt / "work/PeptideDesign"),
            seed_patch_path=str(source_entrypoint),
            seed_patch_sha256=source_entrypoint_sha,
            candidate_path=str(candidate_path),
            candidate_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
            target_context_chain="A",
            target_context_mode="ordered_subsequence",
            target_context_path=str(target),
            target_context_sha256=target_sha,
            x_mirror_applied=True,
        )
    elif method == "PepMirror":
        target_source = ROOT / job["target_pdb_path"]
        mirror_input = attempt / "raw/mirror_input.pdb"
        mirror_input.parent.mkdir(parents=True, exist_ok=True)
        mirror_input.write_bytes(target_source.read_bytes())
        mirror_input_sha = hashlib.sha256(mirror_input.read_bytes()).hexdigest()
        mirrored_target = attempt / "raw/mirrored_target.pdb"
        mirrored_generated = attempt / "raw/mirrored_generated.pdb"
        package = attempt / "package_evidence.json"
        preflight = attempt / "execution_preflight_evidence.json"
        source_root = Path(
            "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/PepMirror"
        )
        generate_pre = source_root / "api/generate.py"
        mirror_pre = source_root / "scripts/mirror_pdb.py"
        generate_post = attempt / "work/PepMirror/api/generate.py"
        mirror_post = attempt / "work/PepMirror/scripts/mirror_pdb.py"
        generate_payload = generate_pre.read_text(encoding="utf-8").replace(
            "setup_seed(12)", 'setup_seed(int(os.environ["V034_SEED"]))'
        )
        generate_post.parent.mkdir(parents=True, exist_ok=True)
        mirror_post.parent.mkdir(parents=True, exist_ok=True)
        generate_post.write_text(generate_payload, encoding="utf-8")
        mirror_post.write_bytes(mirror_pre.read_bytes())
        generate_post_sha = hashlib.sha256(generate_post.read_bytes()).hexdigest()
        mirror_post_sha = hashlib.sha256(mirror_post.read_bytes()).hexdigest()
        assert (
            generate_post_sha
            == "32cb77ec34c9f10b2223c0bb19ef09e7fad3c7d9c2c0798a5ff9e72a699e5ecb"
        )
        manifest = attempt / "executed_source_manifest.json"
        manifest_value = {
            "source_commit": source_commit,
            "files": {
                "api/generate.py": generate_post_sha,
                "scripts/mirror_pdb.py": mirror_post_sha,
            },
        }
        manifest.write_text(
            json.dumps(manifest_value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
        image_id = "sha256:" + "9" * 64
        package_value = {
            "source_root": str(source_root),
            "source_commit_expected": source_commit,
            "source_commit_observed": source_commit,
            "source_commit_verified": True,
            "source_git_paths": ["api/generate.py", "scripts/mirror_pdb.py"],
            "source_git_paths_clean": True,
            "source_git_checkout_clean": True,
            "source_commit_command": [
                "git",
                "-C",
                str(source_root),
                "rev-parse",
                "--verify",
                "HEAD",
            ],
            "source_status_command": [
                "git",
                "-C",
                str(source_root),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ],
            "generate_py_pre_path": str(generate_pre),
            "generate_py_pre_sha256": hashlib.sha256(
                generate_pre.read_bytes()
            ).hexdigest(),
            "mirror_pdb_py_pre_path": str(mirror_pre),
            "mirror_pdb_py_pre_sha256": hashlib.sha256(
                mirror_pre.read_bytes()
            ).hexdigest(),
            "compose_file_path": "/data/protein-design/compose/docker-compose.yml",
            "compose_file_sha256": "a" * 64,
            "compose_profile": "v021",
            "compose_service": "pd-pyrosetta-methods-gpu-v021",
            "compose_service_verified": True,
            "compose_image_tag": "pd-pyrosetta-methods-gpu:0.21",
            "compose_config_command": ["docker", "compose", "config"],
            "compose_config_output_sha256": "b" * 64,
            "image_inspect_command": ["docker", "image", "inspect"],
            "image_inspect_output_sha256": "c" * 64,
            "image_inspect_stage": "prepare",
            "image_id_observed_at_prepare": image_id,
            "image_repo_tags_observed_at_prepare": [
                "pd-pyrosetta-methods-gpu:0.21"
            ],
            "provenance_capture_stage": "prepare",
            "generate_py_post_path": str(generate_post),
            "generate_py_post_sha256": generate_post_sha,
            "mirror_pdb_py_post_path": str(mirror_post),
            "mirror_pdb_py_post_sha256": mirror_post_sha,
            "source_tracked_file_count": 2,
            "executed_source_manifest_path": str(manifest),
            "executed_source_manifest_sha256": manifest_sha,
            "checkpoint_path": "/weights/pepmirror.ckpt",
            "checkpoint_revision": model_revision,
            "checkpoint_sha256": model_revision.removeprefix("sha256:"),
            "checkpoint_pin_verified": True,
            "checkpoint_container_path": (
                "/data/benchmark_models/pepmirror/"
                "pepmirror_commutator_both_v1.ckpt"
            ),
            "checkpoint_mount_mode": "explicit_read_only_file_bind",
            "checkpoint_container_binding_verified": True,
            "execution_environment_id": environment,
            "execution_environment_verified": True,
            "target_pdb_path": str(target_source),
            "target_pdb_sha256": job["target_pdb_sha256"],
            "target_preflight_verified": True,
            "mirror_runtime_scope": "pinned_compose_conda_environment",
            "mirror_runtime_conda_environment": "bench-pepmirror",
            "mirror_commands_in_pinned_container": True,
        }
        package.write_text(
            json.dumps(package_value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
        preflight_value = {
            "image_inspect_execution_command": [
                "docker",
                "image",
                "inspect",
                "pd-pyrosetta-methods-gpu:0.21",
            ],
            "image_inspect_execution_output_sha256": "d" * 64,
            "image_inspect_execution_stage": "execution_pre_run",
            "image_id_observed_pre_run": image_id,
            "image_identity_stable_pre_run": True,
            "executed_source_manifest_verified_pre_run": True,
            "compose_file_verified_pre_run": True,
            "checkpoint_verified_pre_run": True,
            "target_input_verified_pre_run": True,
        }
        preflight.write_text(
            json.dumps(preflight_value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        preflight_sha = hashlib.sha256(preflight.read_bytes()).hexdigest()
        runtime.update(package_value)
        runtime.update(preflight_value)
        runtime.update(
            method=method,
            package_evidence_path=str(package),
            package_evidence_sha256=package_sha,
            execution_preflight_evidence_path=str(preflight),
            execution_preflight_evidence_sha256=preflight_sha,
            seed_patch_path=str(generate_post),
            seed_patch_sha256=generate_post_sha,
            mirror_input_path=str(mirror_input),
            mirror_input_sha256=mirror_input_sha,
            mirrored_target_path=str(mirrored_target),
            mirrored_target_sha256=_write_bound_file(
                mirrored_target, _central_invert_pdb(mirror_input.read_bytes())
            ),
            mirrored_generated_path=str(mirrored_generated),
            mirrored_generated_sha256=hashlib.sha256(
                mirrored_generated.read_bytes()
            ).hexdigest(),
            mirror_output_path=str(candidate_path),
            mirror_output_sha256=hashlib.sha256(
                candidate_path.read_bytes()
            ).hexdigest(),
            mirror_roundtrip_applied=True,
        )
    elif method == "AfCycDesign / ColabDesign cyclic peptide":
        runtime.update(
            source_commit=source_commit,
            source_notebook_sha256=(
                "ca3bd3cc14daa95e1529fd2d5c1ca18263d12341a75d2967715ec23720b129ed"
            ),
            alphafold_model_name="model_1_ptm",
            alphafold_params_sha256=model_revision.split("sha256:", 1)[1],
            container_image="pd-benchmark-methods-gpu:0.21",
            container_image_id=(
                "sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2"
            ),
            candidate_path=str(candidate_path),
            candidate_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
            cyclic_offset_applied=True,
            cyclic_offset_type=2,
            terminal_offset=1,
        )
    elif method == "RFdiffusion + ProteinMPNN":
        trb = attempt / "raw/rf/design.trb"
        fasta = source_output_path
        semantic = {
            "input_pdb": "/data/input/7zkr_GABARAP.pdb",
            "contigs": ["A3-117/0 70-100"],
            "cyclic": False,
            "design_startnum": seed,
            "deterministic": True,
            "hotspot_res": ["A48", "A50", "A51", "A52", "A62", "A65"],
            "num_designs": 1,
            "sampled_mask": ["A3-117/0", "70-70"],
        }
        trb_sha = _write_bound_file(trb, pickle.dumps(semantic, protocol=4))
        semantic_sha = hashlib.sha256(
            json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        runtime.update(
            rf_source_commit="2d0c003df46b9db41d119321f15403dec3716cd9",
            rf_source_entrypoint_sha256=(
                "a22624d7d40d3d207d91e92163441da5a778c867ed6ea85aa546cc9fdbeb2105"
            ),
            mpnn_source_commit="8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
            mpnn_source_entrypoint_sha256=(
                "61f2c519a7f73fa12da9eb90da97b97ec2f8d5f31d42605639c7600cbd321cbe"
            ),
            rf_checkpoint_sha256=(
                "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc"
            ),
            mpnn_checkpoint_sha256=(
                "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd"
            ),
            rf_container_image="pd-rfpeptide-gpu:fixed",
            rf_container_image_id=(
                "sha256:95e2a19e4adf4b6e8bcdd1777b609bf717472a91643dc92f0ce6aaffbc5219f1"
            ),
            mpnn_container_image="pd-foundry-gpu:latest",
            mpnn_container_image_id=(
                "sha256:23f8612f4537f90078d54a5ac9669df7a6d5f436a48740e5d2884cfe856a5be4"
            ),
            rf_backbone_path=str(candidate_path),
            rf_backbone_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
            rf_trb_path=str(trb),
            rf_trb_sha256=trb_sha,
            rf_trb_semantic_extract=semantic,
            rf_trb_semantic_parser="pickletools_literal_scan_v1",
            rf_trb_semantic_sha256=semantic_sha,
            mpnn_fasta_path=str(fasta),
            mpnn_fasta_sha256=hashlib.sha256(fasta.read_bytes()).hexdigest(),
            rf_target_conditioned=True,
            rf_contig="[A3-117/0 70-100]",
            rf_hotspots=["A48", "A50", "A51", "A52", "A62", "A65"],
            rf_cyclic=False,
            rf_design_startnum=seed,
            rf_deterministic=True,
            mpnn_seed=seed,
            mpnn_designed_chain="B",
            mpnn_fixed_chains=["A"],
            mpnn_record_type="generated_sample",
            mpnn_selected_record_id="T=0.1",
            structure_representation="unthreaded_rf_backbone",
            sequence_representation="proteinmpnn_generated_fasta",
            sequence_threaded_onto_backbone=False,
        )
    return runtime


def write_contract_complete_attempt(
    parser, run_root: Path, job: dict[str, str], number: int = 1
) -> Path:
    attempt = write_complete_attempt(parser, run_root, job, number)
    design_id = f"{job['job_id']}_candidate_1"
    raw = attempt / "raw"
    source_commit, model_revision, environment = METHOD_MANIFEST_CONTRACTS[
        job["method"]
    ]
    candidate_paths = {
        "DiffPepBuilder": raw / "diffpepbuilder_candidate.pdb",
        "PepGLAD": raw / "pepglad_candidate.pdb",
        "D-Flow / PeptideDesign": raw / "dflow_candidate.pdb",
        "PepMirror": raw / "pepmirror_candidate.pdb",
        "AfCycDesign / ColabDesign cyclic peptide": raw
        / "afcycdesign_candidate.pdb",
        "RFdiffusion + ProteinMPNN": raw / "rf/design.pdb",
    }
    candidate_path = candidate_paths.get(job["method"], raw / "candidate.pdb")
    source_output_path = candidate_path
    if job["method"] == "PepMLM":
        sequence = "ACD"
    elif job["method"] == "AfCycDesign / ColabDesign cyclic peptide":
        sequence = "ACDEFGHIKLMNPQ"
    elif job["method"] == "RFdiffusion + ProteinMPNN":
        sequence = "A" * 70
    else:
        sequence = "ACDEFGHIKLM"
    if job["method"] == "PepMLM":
        source_output_path = raw / "pepmlm_generated.csv"
        write_csv(
            source_output_path,
            {
                "job_id": job["job_id"],
                "generated_binder": sequence,
                "binder_rank": "1",
                "target_id": job["target_id"],
            },
        )
        structure_path = ""
    else:
        binder_sequence = (
            "G" * len(sequence)
            if job["method"] == "RFdiffusion + ProteinMPNN"
            else sequence
        )
        target_sequence = (
            _runtime_target_context_sequence(job)
            if job["method"] in RUNTIME_TARGET_CONTEXT_METHODS
            else _job_target_sequence(job)
        )
        structure_chains = {
            job["expected_target_chain"]: target_sequence,
            job["expected_binder_chain"]: binder_sequence,
        }
        structure_options = {
            "chain_chirality": {
                job["expected_binder_chain"]: job["chirality"]
            },
            "chain_starts": (
                {job["expected_target_chain"]: 3}
                if job["method"] == "RFdiffusion + ProteinMPNN"
                else {}
            ),
            "cyclic_chains": (
                frozenset({job["expected_binder_chain"]})
                if job["cyclic"] == "yes"
                else frozenset()
            ),
        }
        if job["method"] == "PepMirror":
            mirrored_generated = raw / "mirrored_generated.pdb"
            generated = _minimal_pdb(
                structure_chains,
                chain_chirality={job["expected_binder_chain"]: "L"},
            )
            _write_bound_file(mirrored_generated, generated)
            _write_bound_file(candidate_path, _central_invert_pdb(generated))
        else:
            _write_bound_file(
                candidate_path,
                _minimal_pdb(structure_chains, **structure_options),
            )
        structure_path = str(candidate_path)
        if job["method"] == "RFdiffusion + ProteinMPNN":
            source_output_path = raw / "mpnn/design.fa"
            _write_bound_file(
                source_output_path,
                (
                    ">native,fixed_chains=['A'],designed_chains=['B'],"
                    f"seed={job['random_seed']}\n{_job_target_sequence(job)}\n"
                    f">T=0.1, sample=1\n{sequence}\n"
                ).encode("utf-8"),
            )
        elif job["method"] == "PepGLAD":
            (raw / "pepglad_summary.jsonl").write_text(
                json.dumps(
                    {
                        "id": "3EQS_0",
                        "rec_chains": [job["expected_target_chain"]],
                        "pep_chain": job["expected_binder_chain"],
                        "pep_seq": sequence,
                    },
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )

    runtime_seconds = "1.250"
    created_at = "2026-07-12T00:00:00+00:00"
    command = attempt / "command.sh"
    _write_bound_file(command, b"#!/usr/bin/env bash\nexit 0\n")
    _write_bound_file(attempt / "stdout.log", b"bounded stdout\n")
    _write_bound_file(attempt / "stderr.log", b"")
    (attempt / "run_result.json").write_text(
        json.dumps(
            {
                "attempt_dir": str(attempt),
                "created_at": created_at,
                "design_id": design_id,
                "exit_code": 0,
                "job_id": job["job_id"],
                "method": job["method"],
                "overall_qc_status": "pass",
                "parser_status": "parsed",
                "runtime_seconds": runtime_seconds,
                "status": "passed",
                "status_reason": "bounded_connectivity_candidate_qc_passed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(
        attempt / "method_output_manifest.csv",
        {
            "run_record_id": f"{job['job_id']}_attempt_{number:03d}",
            "job_id": job["job_id"],
            "method": job["method"],
            "task_id": job["task_id"],
            "execution_stage": job["seed_stage"],
            "source_commit": source_commit,
            "model_revision": model_revision,
            "environment_id": environment,
            "command": f"bash {command}",
            "raw_output_root": str(raw),
            "stdout_log": str(attempt / "stdout.log"),
            "stderr_log": str(attempt / "stderr.log"),
            "runtime_seconds": runtime_seconds,
            "exit_code": "0",
            "parser_status": "parsed",
            "overall_qc_status": "pass",
            "status": "passed",
            "status_reason": "bounded_connectivity_candidate_qc_passed",
            "created_at": created_at,
        },
    )
    status_reasons = {
        "PepMLM": "pepmlm_standard_output_parsed",
        "DiffPepBuilder": "diffpepbuilder_standard_output_parsed",
        "PepGLAD": "pepglad_standard_output_parsed",
        "D-Flow / PeptideDesign": "v034_dflow_standard_candidate_parsed",
        "PepMirror": "v034_pepmirror_roundtrip_candidate_parsed",
        "AfCycDesign / ColabDesign cyclic peptide": (
            "v034_afcycdesign_standard_candidate_parsed"
        ),
        "RFdiffusion + ProteinMPNN": "v034_rf_to_mpnn_generated_handoff_parsed",
    }
    notes = "Bounded connectivity evidence only; not Benchmark result or scoring evidence"
    if job["method"] == "RFdiffusion + ProteinMPNN":
        notes += "; unthreaded RF backbone plus ProteinMPNN FASTA handoff"
    candidate_row = {
        "design_id": design_id,
        "job_id": job["job_id"],
        "method": job["method"],
        "target_id": job["target_id"],
        "binder_id": f"{job['job_id']}_binder_1",
        "source_output_id": METHOD_SOURCE_OUTPUT_IDS[job["method"]],
        "generation_rank": "1",
        "sequence": sequence,
        "structure_path": structure_path,
        "source_output_path": str(source_output_path),
        "binder_chain": job["expected_binder_chain"],
        "peptide_type": job["peptide_type"],
        "chirality": job["chirality"],
        "cyclic": job["cyclic"],
        "parse_status": "parsed",
        "status_reason": status_reasons[job["method"]],
        "notes": notes,
    }
    write_csv(attempt / "candidate_outputs.csv", candidate_row)
    runtime = _contract_runtime(job, attempt, candidate_path, source_output_path)
    (attempt / "runtime_evidence.json").write_text(
        json.dumps(runtime, indent=2) + "\n", encoding="utf-8"
    )
    oracle_job = dict(job)
    if oracle_job.get("target_pdb_path"):
        target_path = Path(oracle_job["target_pdb_path"])
        if not target_path.is_absolute():
            oracle_job["target_pdb_path"] = str(ROOT / target_path)
    observed_qc = evaluate_candidate_qc(oracle_job, candidate_row, runtime, raw)
    assert observed_qc["overall_qc_status"] == "pass", observed_qc
    qc = {
        "design_id": design_id,
        "job_id": job["job_id"],
        **{key: str(value) for key, value in observed_qc.items()},
    }
    write_csv(attempt / "candidate_qc.csv", qc)
    return attempt


def _pepglad_pdb(job: dict[str, str], chirality_pattern: str) -> bytes:
    assert chirality_pattern and set(chirality_pattern) <= {"L", "D"}
    payload = _minimal_pdb(
        {
            job["expected_target_chain"]: _job_target_sequence(job),
            job["expected_binder_chain"]: "A" * len(chirality_pattern),
        },
        chain_chirality={job["expected_binder_chain"]: "L"},
    )
    lines = payload.decode("ascii").splitlines()
    observed = 0
    for index, line in enumerate(lines):
        if (
            line.startswith("ATOM  ")
            and line[21].strip() == job["expected_binder_chain"]
            and line[12:16].strip() == "CB"
        ):
            z = 1.0 if chirality_pattern[observed] == "L" else -1.0
            lines[index] = f"{line[:46]}{z:8.3f}{line[54:]}"
            observed += 1
    assert observed == len(chirality_pattern)
    return ("\n".join(lines) + "\n").encode("ascii")


def _pepglad_runtime_chirality(path: Path, chain: str) -> dict[str, object]:
    return {"chain": chain, **chirality_stats(path, chain)}


def _fixed_pepglad_producer_payloads() -> dict[str, bytes]:
    source = pepglad_adapter.SOURCE_ENTRYPOINT.read_bytes()
    assert hashlib.sha256(source).hexdigest() == PEPGLAD_SOURCE_ENTRYPOINT_SHA256
    instrumenter_namespace = {"__name__": "pepglad_instrumenter_fixture"}
    exec(
        compile(
            pepglad_adapter.INSTRUMENTER_SCRIPT,
            "<pepglad_instrumenter_fixture>",
            "exec",
        ),
        instrumenter_namespace,
    )
    anchor = instrumenter_namespace["ANCHOR"]
    replacement = instrumenter_namespace["REPLACEMENT"]
    assert isinstance(anchor, bytes) and isinstance(replacement, bytes)
    assert source.count(anchor) == 1
    payloads = {
        "observer_patch_sha256": pepglad_adapter.INSTRUMENTER_SCRIPT.encode(),
        "observer_source_sha256": pepglad_adapter.OBSERVER_SCRIPT.encode(),
        "seed_wrapper_sha256": pepglad_adapter.SEED_WRAPPER_SCRIPT.encode(),
        "source_entrypoint_instrumented_sha256": source.replace(
            anchor, replacement, 1
        ),
    }
    assert {
        field: hashlib.sha256(payload).hexdigest()
        for field, payload in payloads.items()
    } == PEPGLAD_PRODUCER_SHA256
    return payloads


def write_instrumented_pepglad_attempt(
    parser,
    run_root: Path,
    job: dict[str, str],
    *,
    number: int = 1,
    pre_pattern: str = "L" * 11,
    post_pattern: str = "L" * 11,
    baseline_sha256: str | None = None,
) -> tuple[Path, str]:
    attempt = write_contract_complete_attempt(parser, run_root, job, number)
    raw = attempt / "raw"
    binder_chain = job["expected_binder_chain"]
    pre_relax = raw / "pepglad_pre_relax.pdb"
    post_relax = raw / "pepglad_candidate.pdb"
    source_candidate = attempt / "work/codesign/3EQS_0.pdb"
    pre_relax.write_bytes(
        _pepglad_pdb(job, pre_pattern) + b"REMARK PRE_RELAX_SNAPSHOT\n"
    )
    post_payload = _pepglad_pdb(job, post_pattern)
    post_digest = _write_bound_file(post_relax, post_payload)
    _write_bound_file(source_candidate, post_payload)

    observer_patch = attempt / "pepglad_instrument_source.py"
    observer_source = attempt / "pepglad_observer.py"
    seed_wrapper = attempt / "pepglad_seeded_entry.py"
    instrumented_source = attempt / "work/api/run.py"
    producer_payloads = _fixed_pepglad_producer_payloads()
    observer_patch_digest = _write_bound_file(
        observer_patch, producer_payloads["observer_patch_sha256"]
    )
    observer_source_digest = _write_bound_file(
        observer_source, producer_payloads["observer_source_sha256"]
    )
    seed_wrapper_digest = _write_bound_file(
        seed_wrapper, producer_payloads["seed_wrapper_sha256"]
    )
    instrumented_source_digest = _write_bound_file(
        instrumented_source,
        producer_payloads["source_entrypoint_instrumented_sha256"],
    )

    def relative(path: Path) -> str:
        return path.relative_to(attempt).as_posix()

    patch_evidence_path = attempt / "observer_patch_evidence.json"
    patch_evidence = {
        "observer_injection_status": "applied",
        "observer_patch_path": relative(observer_patch),
        "observer_patch_sha256": observer_patch_digest,
        "observer_source_path": relative(observer_source),
        "observer_source_sha256": observer_source_digest,
        "source_entrypoint_path": relative(instrumented_source),
        "source_entrypoint_prepatch_sha256": PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
        "source_entrypoint_instrumented_sha256": instrumented_source_digest,
        "source_copy_mode": "attempt_local_copy",
        "target_input_path": "/data/input/3EQS.pdb",
        "target_input_sha256": job["target_pdb_sha256"],
        "target_preflight_verified": True,
    }
    patch_evidence_path.write_text(
        json.dumps(patch_evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    patch_evidence_digest = hashlib.sha256(
        patch_evidence_path.read_bytes()
    ).hexdigest()
    seed = int(job["random_seed"])
    expected_baseline = (baseline_sha256 or post_digest) if seed == 42 else ""
    runtime = {
        "requested_seed": seed,
        "effective_seed": seed,
        "seed_control_status": "honored",
        "recovery_mode": "instrumented_official_pipeline",
        "source_candidate_path": relative(source_candidate),
        "pre_relax_path": relative(pre_relax),
        "pre_relax_sha256": hashlib.sha256(pre_relax.read_bytes()).hexdigest(),
        "post_relax_path": relative(post_relax),
        "post_relax_sha256": post_digest,
        "official_candidate_stage": "post_openmm_relaxation",
        "pre_relax_role": "diagnostic_evidence_only",
        "binder_chain": binder_chain,
        "expected_chirality": "L",
        "pre_relax_binder_chirality": _pepglad_runtime_chirality(
            pre_relax, binder_chain
        ),
        "post_relax_binder_chirality": _pepglad_runtime_chirality(
            post_relax, binder_chain
        ),
        "first_observed_chirality_failure_stage": (
            "pre_openmm_snapshot"
            if "D" in pre_pattern
            else "post_openmm_relaxation" if "D" in post_pattern else "none_observed"
        ),
        "baseline_replay_expected_sha256": expected_baseline,
        "baseline_replay_observed_sha256": post_digest,
        "baseline_replay_status": (
            "match"
            if seed == 42 and expected_baseline == post_digest
            else "mismatch" if seed == 42 else "not_applicable"
        ),
        "observer_patch_evidence_path": relative(patch_evidence_path),
        "observer_patch_evidence_sha256": patch_evidence_digest,
        "observer_patch_path": relative(observer_patch),
        "observer_patch_sha256": observer_patch_digest,
        "observer_source_path": relative(observer_source),
        "observer_source_sha256": observer_source_digest,
        "seed_wrapper_path": relative(seed_wrapper),
        "seed_wrapper_sha256": seed_wrapper_digest,
        "instrumented_source_path": relative(instrumented_source),
        "source_entrypoint_prepatch_sha256": PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
        "source_entrypoint_instrumented_sha256": instrumented_source_digest,
        "target_input_sha256": job["target_pdb_sha256"],
        "target_preflight_verified": True,
        "source_commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
        "source_entrypoint_sha256": PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
        "model_weights_sha256": (
            "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
        ),
        "container_image": "pd-benchmark-methods-gpu:0.21",
        "conda_environment": "bench-pepglad",
    }
    runtime_path = attempt / "runtime_evidence.json"
    runtime_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    candidate_path = attempt / "candidate_outputs.csv"
    candidate = _one_row(candidate_path)
    candidate.update(
        sequence="A" * len(post_pattern),
        structure_path=str(post_relax),
        source_output_path=str(post_relax),
    )
    write_csv(candidate_path, candidate)
    (raw / "pepglad_summary.jsonl").write_text(
        json.dumps(
            {
                "id": "3EQS_0",
                "rec_chains": [job["expected_target_chain"]],
                "pep_chain": job["expected_binder_chain"],
                "pep_seq": candidate["sequence"],
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    oracle_job = dict(job)
    target_path = Path(oracle_job["target_pdb_path"])
    if not target_path.is_absolute():
        oracle_job["target_pdb_path"] = str(ROOT / target_path)
    observed_qc = evaluate_candidate_qc(oracle_job, candidate, runtime, raw)
    qc = {
        "design_id": candidate["design_id"],
        "job_id": job["job_id"],
        **{key: str(value) for key, value in observed_qc.items()},
    }
    write_csv(attempt / "candidate_qc.csv", qc)

    passed = observed_qc["overall_qc_status"] in {"pass", "pass_with_warning"}
    status = "passed" if passed else "qc_failed"
    status_reason = (
        "bounded_connectivity_candidate_qc_passed"
        if passed
        else str(observed_qc["status_reason"])
    )
    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result.update(
        overall_qc_status=observed_qc["overall_qc_status"],
        status=status,
        status_reason=status_reason,
    )
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    manifest_path = attempt / "method_output_manifest.csv"
    manifest = _one_row(manifest_path)
    manifest.update(
        overall_qc_status=observed_qc["overall_qc_status"],
        status=status,
        status_reason=status_reason,
    )
    write_csv(manifest_path, manifest)
    return attempt, post_digest


def write_pepglad_replay_mismatch_attempt(
    parser, run_root: Path, job: dict[str, str]
) -> tuple[Path, dict[str, object]]:
    attempt, post_digest = write_instrumented_pepglad_attempt(
        parser,
        run_root,
        job,
        number=3,
        pre_pattern="L" * 6 + "D" * 5,
        post_pattern="L" * 4 + "D" * 7,
        baseline_sha256=PEPGLAD_SEED42_BASELINE_SHA256,
    )
    assert post_digest != PEPGLAD_SEED42_BASELINE_SHA256
    reason = "pepglad_seed42_replay_mismatch"

    runtime_source = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_source.read_text(encoding="utf-8"))
    assert runtime["baseline_replay_status"] == "mismatch"
    runtime_path = attempt / "raw/runtime_evidence.json"
    runtime_source.replace(runtime_path)

    sequence = "A" * 11
    summary_path = attempt / "raw/pepglad_summary.jsonl"
    summary_path.write_text(
        json.dumps(
            {
                "id": "3EQS_0",
                "rec_chains": ["A"],
                "pep_chain": "B",
                "pep_seq": sequence,
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result.update(
        parser_status="failed",
        overall_qc_status="fail",
        status="parse_failed",
        status_reason=reason,
    )
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

    manifest_path = attempt / "method_output_manifest.csv"
    manifest = _one_row(manifest_path)
    manifest.update(
        parser_status="failed",
        overall_qc_status="fail",
        status="parse_failed",
        status_reason=reason,
    )
    write_csv(manifest_path, manifest)

    candidate_path = attempt / "candidate_outputs.csv"
    candidate = _one_row(candidate_path)
    candidate.update(
        source_output_id="",
        sequence="",
        structure_path="",
        source_output_path="",
        parse_status="failed",
        status_reason=reason,
    )
    write_csv(candidate_path, candidate)

    write_csv(
        attempt / "candidate_qc.csv",
        {
            "job_id": job["job_id"],
            "design_id": result["design_id"],
            "file_status": "fail",
            "file_reason": "missing_output_file",
            "file_sha256": "",
            "file_size_bytes": "0",
            "parse_status": "fail",
            "chain_status": "not_applicable",
            "target_binding_status": "fail",
            "length_status": "fail",
            "sequence_length": "0",
            "sequence_structure_status": "not_applicable",
            "chirality_status": "fail",
            "cyclic_status": "not_applicable",
            "noncanonical_status": "pass",
            "noncanonical_residues": "",
            "seed_status": "pass",
            "method_contract_status": "pass",
            "backbone_to_fasta_handoff_status": "not_applicable",
            "handoff_status": "not_applicable",
            "overall_qc_status": "fail",
            "status_reason": (
                "file_status;parse_status;target_binding_status;length_status;"
                "chirality_status;overall_qc_status"
            ),
        },
    )
    return attempt, runtime


def write_primary_set_with_pepglad_replay_mismatch(
    parser, run_root: Path
) -> tuple[dict[str, str], Path, dict[str, object]]:
    pepglad_job: dict[str, str] | None = None
    pepglad_attempt: Path | None = None
    pepglad_runtime: dict[str, object] | None = None
    for job in parser.load_jobs():
        if job["seed_stage"] != "primary":
            continue
        if job["method"] == "PepGLAD":
            pepglad_job = job
            pepglad_attempt, pepglad_runtime = write_pepglad_replay_mismatch_attempt(
                parser, run_root, job
            )
        else:
            write_contract_complete_attempt(parser, run_root, job)
    assert pepglad_job is not None
    assert pepglad_attempt is not None
    assert pepglad_runtime is not None
    return pepglad_job, pepglad_attempt, pepglad_runtime


def test_merge_rejects_shallow_pass_without_method_specific_runtime_contract(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    jobs = parser.load_jobs()
    for job in jobs:
        if job["seed_stage"] == "primary":
            write_complete_attempt(parser, tmp_path / "runs", job)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["primary_complete"] is False
    rows = list(
        csv.DictReader((tmp_path / "deployment.csv").open(newline="", encoding="utf-8"))
    )
    primary_ids = {job["job_id"] for job in jobs if job["seed_stage"] == "primary"}
    assert {
        row["job_id"] for row in rows if row["merge_status"] == "evidence_incomplete"
    } == primary_ids
    assert all(
        row["supported_candidate"] == "no"
        for row in rows
        if row["job_id"] in primary_ids
    )


def test_merge_uses_only_latest_attempt_and_requires_complete_evidence(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    jobs = parser.load_jobs()
    primary = next(job for job in jobs if job["seed_stage"] == "primary")
    old = write_complete_attempt(parser, tmp_path / "runs", primary, 1)
    latest = old.parent / "attempt_002"
    latest.mkdir()
    (latest / "run_result.json").write_text(
        json.dumps(
            {
                "job_id": primary["job_id"],
                "status": "execution_failed",
                "overall_qc_status": "not_run",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["primary_complete"] is False
    rows = list(
        csv.DictReader((tmp_path / "deployment.csv").open(newline="", encoding="utf-8"))
    )
    row = next(value for value in rows if value["job_id"] == primary["job_id"])
    assert row["attempt_id"] == "attempt_002"
    assert row["status"] == "execution_failed"
    candidates = list(
        csv.DictReader(
            (tmp_path / "results/pilot_candidate_outputs_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    assert all(value["job_id"] != primary["job_id"] for value in candidates)


def test_merge_marks_primary_complete_only_for_seven_supported_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    jobs = parser.load_jobs()
    pepglad_digest = ""
    for job in jobs:
        if job["seed_stage"] == "primary":
            attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
            if job["method"] == "PepGLAD":
                candidate = _one_row(attempt / "candidate_outputs.csv")
                pepglad_digest = hashlib.sha256(
                    Path(candidate["structure_path"]).read_bytes()
                ).hexdigest()
    assert pepglad_digest and pepglad_digest != PEPGLAD_SEED42_BASELINE_SHA256
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        pepglad_digest,
        raising=False,
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_total"] == 7
    assert summary["primary_passed"] == 7
    assert summary["primary_complete"] is True
    assert summary["extension_passed"] == 0
    stored = json.loads(
        (tmp_path / "results/pilot_v034_merge_summary.json").read_text(encoding="utf-8")
    )
    assert stored == summary
    candidates = list(
        csv.DictReader(
            (tmp_path / "results/pilot_candidate_outputs_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    assert len(candidates) == 7


def _write_primary_set_with_instrumented_pepglad(
    parser,
    run_root: Path,
    *,
    pre_pattern: str = "L" * 11,
    post_pattern: str = "L" * 11,
) -> tuple[dict[str, str], Path, str]:
    pepglad_job: dict[str, str] | None = None
    pepglad_attempt: Path | None = None
    post_digest = ""
    for job in parser.load_jobs():
        if job["seed_stage"] != "primary":
            continue
        if job["method"] == "PepGLAD":
            pepglad_job = job
            pepglad_attempt, post_digest = write_instrumented_pepglad_attempt(
                parser,
                run_root,
                job,
                pre_pattern=pre_pattern,
                post_pattern=post_pattern,
            )
        else:
            write_contract_complete_attempt(parser, run_root, job)
    assert pepglad_job is not None and pepglad_attempt is not None and post_digest
    return pepglad_job, pepglad_attempt, post_digest


def _write_primary_set_with_seed43_instrumented_pepglad(
    parser, run_root: Path
) -> tuple[dict[str, str], Path]:
    jobs = parser.load_jobs()
    for job in jobs:
        if job["seed_stage"] == "primary" and job["method"] != "PepGLAD":
            write_contract_complete_attempt(parser, run_root, job)
    extension = next(
        job
        for job in jobs
        if job["method"] == "PepGLAD" and job["seed_stage"] == "extension"
    )
    attempt, _ = write_instrumented_pepglad_attempt(parser, run_root, extension)
    return extension, attempt


def test_merge_pins_pepglad_seed42_replay_baseline() -> None:
    parser = load_parser()

    assert (
        parser.PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256
        == PEPGLAD_SEED42_BASELINE_SHA256
    )


def test_merge_pins_pepglad_producer_identities() -> None:
    parser = load_parser()

    assert {
        "observer_patch_sha256": parser.PEPGLAD_INSTRUMENTER_SCRIPT_SHA256,
        "observer_source_sha256": parser.PEPGLAD_OBSERVER_SCRIPT_SHA256,
        "seed_wrapper_sha256": parser.PEPGLAD_SEED_WRAPPER_SCRIPT_SHA256,
        "source_entrypoint_instrumented_sha256": (
            parser.PEPGLAD_SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256
        ),
    } == PEPGLAD_PRODUCER_SHA256
    _fixed_pepglad_producer_payloads()


def test_merge_rejects_nonbaseline_synthetic_legacy_pepglad(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    pepglad_job: dict[str, str] | None = None
    pepglad_digest = ""
    for job in parser.load_jobs():
        if job["seed_stage"] != "primary":
            continue
        attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
        if job["method"] == "PepGLAD":
            pepglad_job = job
            candidate = _one_row(attempt / "candidate_outputs.csv")
            pepglad_digest = hashlib.sha256(
                Path(candidate["structure_path"]).read_bytes()
            ).hexdigest()
    assert pepglad_job is not None
    assert pepglad_digest != PEPGLAD_SEED42_BASELINE_SHA256

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 6
    assert summary["parsed_candidate_rows"] == 7
    assert summary["job_status"][pepglad_job["job_id"]] == "evidence_incomplete"


def test_merge_rejects_legacy_pepglad_seed43_even_with_synthetic_baseline_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    jobs = parser.load_jobs()
    primary = next(
        job
        for job in jobs
        if job["method"] == "PepGLAD" and job["seed_stage"] == "primary"
    )
    extension = next(
        job
        for job in jobs
        if job["method"] == "PepGLAD" and job["seed_stage"] == "extension"
    )
    primary_attempt = write_contract_complete_attempt(
        parser, tmp_path / "runs", primary
    )
    extension_attempt = write_contract_complete_attempt(
        parser, tmp_path / "runs", extension
    )
    primary_candidate = _one_row(primary_attempt / "candidate_outputs.csv")
    extension_candidate = _one_row(extension_attempt / "candidate_outputs.csv")
    primary_digest = hashlib.sha256(
        Path(primary_candidate["structure_path"]).read_bytes()
    ).hexdigest()
    extension_digest = hashlib.sha256(
        Path(extension_candidate["structure_path"]).read_bytes()
    ).hexdigest()
    assert primary_digest == extension_digest
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        primary_digest,
        raising=False,
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 1
    assert summary["extension_passed"] == 0
    assert summary["job_status"][extension["job_id"]] == "evidence_incomplete"


def test_merge_rejects_self_reported_match_for_nonbaseline_seed42_post_digest(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job, attempt, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    assert post_digest != PEPGLAD_SEED42_BASELINE_SHA256
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime.update(
        baseline_replay_expected_sha256=PEPGLAD_SEED42_BASELINE_SHA256,
        baseline_replay_observed_sha256=post_digest,
        baseline_replay_status="match",
    )
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 6
    assert summary["parsed_candidate_rows"] == 6
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_emits_bound_pepglad_replay_mismatch_failure_diagnostic(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job, attempt, runtime = write_primary_set_with_pepglad_replay_mismatch(
        parser, tmp_path / "runs"
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    artifact = json.loads(
        (tmp_path / "results/pilot_failure_diagnostics_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(artifact) == {"schema_version", "evidence_boundary", "records"}
    assert artifact["schema_version"] == "v0.34"
    assert (
        artifact["evidence_boundary"]
        == "failure_diagnostic_only_not_candidate_or_scoring"
    )
    assert len(artifact["records"]) == 1
    record = artifact["records"][0]
    assert set(record) == {
        "job_id",
        "method",
        "seed_stage",
        "random_seed",
        "attempt_id",
        "attempt_dir",
        "candidate_eligible",
        "seed43_status",
        "process",
        "parser",
        "merge",
        "runtime_evidence",
        "summary",
        "pre_openmm",
        "post_openmm",
        "baseline",
        "producer_bindings",
    }
    assert record["job_id"] == job["job_id"]
    assert record["method"] == "PepGLAD"
    assert record["seed_stage"] == "primary"
    assert record["random_seed"] == 42
    assert record["attempt_id"] == "attempt_003"
    assert record["attempt_dir"] == str(attempt)
    assert record["candidate_eligible"] is False
    assert record["seed43_status"] == "not_run"
    assert record["process"] == {"exit_code": 0}
    assert record["parser"] == {
        "status": "failed",
        "status_reason": "pepglad_seed42_replay_mismatch",
    }
    assert record["merge"] == {"status": "evidence_incomplete"}

    runtime_path = attempt / "raw/runtime_evidence.json"
    runtime_payload = runtime_path.read_bytes()
    runtime_semantic = json.dumps(
        runtime, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert record["runtime_evidence"] == {
        "path": "raw/runtime_evidence.json",
        "sha256": hashlib.sha256(runtime_payload).hexdigest(),
        "semantic_sha256": hashlib.sha256(runtime_semantic).hexdigest(),
    }
    summary_path = attempt / "raw/pepglad_summary.jsonl"
    assert record["summary"] == {
        "path": "raw/pepglad_summary.jsonl",
        "sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        "sequence": "A" * 11,
    }
    assert record["pre_openmm"] == {
        "path": "raw/pepglad_pre_relax.pdb",
        "sha256": runtime["pre_relax_sha256"],
        "chirality": {
            "chain": "B",
            "calculation_status": "pass",
            "evaluable": 11,
            "l_count": 6,
            "d_count": 5,
            "gly_count": 0,
            "unknown_count": 0,
        },
    }
    assert record["post_openmm"] == {
        "path": "raw/pepglad_candidate.pdb",
        "sha256": runtime["post_relax_sha256"],
        "chirality": {
            "chain": "B",
            "calculation_status": "pass",
            "evaluable": 11,
            "l_count": 4,
            "d_count": 7,
            "gly_count": 0,
            "unknown_count": 0,
        },
    }
    assert record["baseline"] == {
        "expected_sha256": PEPGLAD_SEED42_BASELINE_SHA256,
        "observed_sha256": runtime["post_relax_sha256"],
        "status": "mismatch",
        "failure_stage": "pre_openmm_snapshot",
    }
    assert set(record["producer_bindings"]) == {
        "target",
        "source",
        "model",
        "container",
        "environment",
        "observer",
        "patch",
        "wrapper",
        "instrumented_source",
    }
    assert record["producer_bindings"] == {
        "target": {
            "path": "/data/input/3EQS.pdb",
            "sha256": job["target_pdb_sha256"],
            "preflight_verified": True,
        },
        "source": {
            "commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
            "entrypoint_sha256": PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
        },
        "model": {
            "weights_sha256": (
                "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
            )
        },
        "container": {"image": "pd-benchmark-methods-gpu:0.21"},
        "environment": {"conda_environment": "bench-pepglad"},
        "observer": {
            "path": "pepglad_observer.py",
            "sha256": PEPGLAD_PRODUCER_SHA256["observer_source_sha256"],
        },
        "patch": {
            "evidence_path": "observer_patch_evidence.json",
            "evidence_sha256": runtime["observer_patch_evidence_sha256"],
            "instrumenter_path": "pepglad_instrument_source.py",
            "instrumenter_sha256": PEPGLAD_PRODUCER_SHA256[
                "observer_patch_sha256"
            ],
            "injection_status": "applied",
            "source_copy_mode": "attempt_local_copy",
        },
        "wrapper": {
            "path": "pepglad_seeded_entry.py",
            "sha256": PEPGLAD_PRODUCER_SHA256["seed_wrapper_sha256"],
        },
        "instrumented_source": {
            "path": "work/api/run.py",
            "prepatch_sha256": PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            "sha256": PEPGLAD_PRODUCER_SHA256[
                "source_entrypoint_instrumented_sha256"
            ],
        },
    }

    assert summary["primary_passed"] == 6
    assert summary["parsed_candidate_rows"] == 6
    assert summary["runtime_provenance_rows"] == 6
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"
    candidate_rows = list(
        csv.DictReader(
            (tmp_path / "results/pilot_candidate_outputs_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    qc_rows = list(
        csv.DictReader(
            (tmp_path / "results/pilot_candidate_qc_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    provenance = json.loads(
        (tmp_path / "results/pilot_runtime_provenance_v0.34.json").read_text(
            encoding="utf-8"
        )
    )["records"]
    assert all(row["job_id"] != job["job_id"] for row in candidate_rows)
    assert all(row["job_id"] != job["job_id"] for row in qc_rows)
    assert all(row["job_id"] != job["job_id"] for row in provenance)


@pytest.mark.parametrize(
    "mutation",
    (
        "pre_bytes",
        "summary_missing",
        "summary_sequence",
        "runtime_duplicate_key",
        "pre_symlink",
    ),
)
def test_merge_excludes_unbound_pepglad_failure_diagnostic(
    tmp_path: Path, mutation: str
) -> None:
    parser = load_parser()
    _, attempt, _ = write_primary_set_with_pepglad_replay_mismatch(
        parser, tmp_path / "runs"
    )
    runtime_path = attempt / "raw/runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if mutation == "pre_bytes":
        pre = attempt / runtime["pre_relax_path"]
        pre.write_bytes(pre.read_bytes() + b"REMARK TAMPERED\n")
    elif mutation == "summary_missing":
        (attempt / "raw/pepglad_summary.jsonl").unlink()
    elif mutation == "summary_sequence":
        summary_path = attempt / "raw/pepglad_summary.jsonl"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["pep_seq"] = "C" * 11
        summary_path.write_text(json.dumps(summary) + "\n", encoding="utf-8")
    elif mutation == "runtime_duplicate_key":
        _prepend_conflicting_json_key(runtime_path, "requested_seed", -1)
    else:
        pre = attempt / runtime["pre_relax_path"]
        replacement = attempt / "raw/pre-relax-replacement.pdb"
        pre.replace(replacement)
        pre.symlink_to(replacement.name)

    parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    artifact = json.loads(
        (tmp_path / "results/pilot_failure_diagnostics_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["records"] == []


def test_merge_does_not_emit_failure_diagnostic_for_promoted_status(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    _, attempt, _ = write_primary_set_with_pepglad_replay_mismatch(
        parser, tmp_path / "runs"
    )
    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result.update(
        parser_status="parsed",
        overall_qc_status="pass",
        status="passed",
        status_reason="bounded_connectivity_candidate_qc_passed",
    )
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    manifest_path = attempt / "method_output_manifest.csv"
    manifest = _one_row(manifest_path)
    manifest.update(
        parser_status="parsed",
        overall_qc_status="pass",
        status="passed",
        status_reason="bounded_connectivity_candidate_qc_passed",
    )
    write_csv(manifest_path, manifest)

    parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    artifact = json.loads(
        (tmp_path / "results/pilot_failure_diagnostics_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["records"] == []


def test_merge_requires_pepglad_seed43_to_remain_not_run_for_failure_diagnostic(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    _, _, _ = write_primary_set_with_pepglad_replay_mismatch(
        parser, tmp_path / "runs"
    )
    extension = next(
        job
        for job in parser.load_jobs()
        if job["method"] == "PepGLAD" and job["seed_stage"] == "extension"
    )
    write_complete_attempt(parser, tmp_path / "runs", extension)

    parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    artifact = json.loads(
        (tmp_path / "results/pilot_failure_diagnostics_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["records"] == []


@pytest.mark.parametrize(
    ("artifact_path_field", "runtime_digest_field", "patch_digest_field"),
    (
        ("observer_patch_path", "observer_patch_sha256", "observer_patch_sha256"),
        ("observer_source_path", "observer_source_sha256", "observer_source_sha256"),
        ("seed_wrapper_path", "seed_wrapper_sha256", None),
        (
            "instrumented_source_path",
            "source_entrypoint_instrumented_sha256",
            "source_entrypoint_instrumented_sha256",
        ),
    ),
)
def test_merge_rejects_replaced_pepglad_producer_with_synced_self_reports(
    tmp_path: Path,
    artifact_path_field: str,
    runtime_digest_field: str,
    patch_digest_field: str | None,
) -> None:
    parser = load_parser()
    job, attempt = _write_primary_set_with_seed43_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    artifact = attempt / runtime[artifact_path_field]
    replacement_digest = _write_bound_file(
        artifact, b"# replacement PepGLAD producer\n"
    )
    runtime[runtime_digest_field] = replacement_digest
    if patch_digest_field is not None:
        patch_path = attempt / runtime["observer_patch_evidence_path"]
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        patch[patch_digest_field] = replacement_digest
        patch_path.write_text(json.dumps(patch) + "\n", encoding="utf-8")
        runtime["observer_patch_evidence_sha256"] = hashlib.sha256(
            patch_path.read_bytes()
        ).hexdigest()
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["extension_passed"] == 0
    assert summary["parsed_candidate_rows"] == 6
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


@pytest.mark.parametrize(
    "mutation", ("extra_field", "recovery_mode_removed", "recovery_mode_changed")
)
def test_merge_requires_exact_instrumented_pepglad_runtime_fields(
    tmp_path: Path, mutation: str
) -> None:
    parser = load_parser()
    job, attempt = _write_primary_set_with_seed43_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if mutation == "extra_field":
        runtime["unbound_recovery_claim"] = "forged"
    elif mutation == "recovery_mode_removed":
        runtime.pop("recovery_mode")
    else:
        runtime["recovery_mode"] = "legacy"
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["extension_passed"] == 0
    assert summary["parsed_candidate_rows"] == 6
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_rejects_conflicting_duplicate_runtime_json_key(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        job
        for job in parser.load_jobs()
        if job["method"] == "PepMLM" and job["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    _prepend_conflicting_json_key(runtime_path, "requested_seed", -1)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["runtime_provenance_rows"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_rejects_conflicting_duplicate_pepglad_patch_json_key(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job, attempt = _write_primary_set_with_seed43_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    patch_path = attempt / runtime["observer_patch_evidence_path"]
    _prepend_conflicting_json_key(
        patch_path, "observer_injection_status", "skipped"
    )
    runtime["observer_patch_evidence_sha256"] = hashlib.sha256(
        patch_path.read_bytes()
    ).hexdigest()
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["extension_passed"] == 0
    assert summary["parsed_candidate_rows"] == 6
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_accepts_fully_bound_instrumented_pepglad_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    _, _, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        post_digest,
        raising=False,
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 7
    assert summary["primary_complete"] is True


def test_merge_allows_distinct_pre_and_post_files_with_identical_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    _, attempt, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        post_digest,
        raising=False,
    )
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    pre_relax = attempt / runtime["pre_relax_path"]
    post_relax = attempt / runtime["post_relax_path"]
    assert pre_relax != post_relax
    pre_relax.write_bytes(post_relax.read_bytes())
    runtime["pre_relax_sha256"] = post_digest
    runtime["pre_relax_binder_chirality"] = _pepglad_runtime_chirality(
        pre_relax, "B"
    )
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 7


def test_merge_preserves_mixed_chirality_pepglad_as_six_of_seven_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    _, _, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser,
        tmp_path / "runs",
        pre_pattern="D" * 7 + "L" * 4,
        post_pattern="D" * 7 + "L" * 4,
    )
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        post_digest,
        raising=False,
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 6
    assert summary["primary_complete"] is False
    assert summary["parsed_candidate_rows"] == 7
    row = next(
        row
        for row in csv.DictReader(
            (tmp_path / "deployment.csv").open(newline="", encoding="utf-8")
        )
        if row["method"] == "PepGLAD" and row["seed_stage"] == "primary"
    )
    assert row["supported_candidate"] == "no"
    assert row["merge_status"] == "qc_failed"
    assert row["chirality_evaluable"] == "11"
    assert row["chirality_l_count"] == "4"
    assert row["chirality_d_count"] == "7"


def test_merge_excludes_tampered_mixed_chirality_diagnostic_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    job, attempt, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser,
        tmp_path / "runs",
        pre_pattern="D" * 7 + "L" * 4,
        post_pattern="D" * 7 + "L" * 4,
    )
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        post_digest,
        raising=False,
    )
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["first_observed_chirality_failure_stage"] = "none_observed"
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 6
    assert summary["parsed_candidate_rows"] == 6
    assert summary["runtime_provenance_rows"] == 6
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


@pytest.mark.parametrize(
    "digest_field",
    (
        "pre_relax_sha256",
        "post_relax_sha256",
        "observer_patch_evidence_sha256",
        "observer_patch_sha256",
        "observer_source_sha256",
        "seed_wrapper_sha256",
        "source_entrypoint_instrumented_sha256",
    ),
)
def test_merge_rehashes_each_instrumented_pepglad_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    digest_field: str,
) -> None:
    parser = load_parser()
    _, attempt, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        post_digest,
        raising=False,
    )
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime[digest_field] = "0" * 64
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 6


@pytest.mark.parametrize(
    "mutation",
    (
        "absolute_path",
        "escaped_path",
        "symlink_path",
        "source_candidate_bytes",
        "post_not_candidate",
        "chirality_report",
        "failure_stage",
        "baseline",
        "target",
        "patch_evidence",
        "prepatch_identity",
        "recovery_mode_removed",
    ),
)
def test_merge_rejects_inconsistent_instrumented_pepglad_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    parser = load_parser()
    _, attempt, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        post_digest,
        raising=False,
    )
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if mutation == "absolute_path":
        runtime["pre_relax_path"] = str(attempt / runtime["pre_relax_path"])
    elif mutation == "escaped_path":
        escaped = attempt.parent / "escaped-pre-relax.pdb"
        escaped.write_bytes((attempt / runtime["pre_relax_path"]).read_bytes())
        runtime["pre_relax_path"] = "../escaped-pre-relax.pdb"
    elif mutation == "symlink_path":
        pre_relax = attempt / runtime["pre_relax_path"]
        replacement = attempt / "raw/pre-relax-replacement.pdb"
        pre_relax.replace(replacement)
        pre_relax.symlink_to(replacement.name)
    elif mutation == "source_candidate_bytes":
        source = attempt / runtime["source_candidate_path"]
        source.write_bytes(source.read_bytes() + b"REMARK TAMPERED\n")
    elif mutation == "post_not_candidate":
        duplicate = attempt / "raw/duplicate-post-relax.pdb"
        duplicate.write_bytes((attempt / runtime["post_relax_path"]).read_bytes())
        runtime["post_relax_path"] = duplicate.relative_to(attempt).as_posix()
    elif mutation == "chirality_report":
        runtime["pre_relax_binder_chirality"]["l_count"] = 10
        runtime["pre_relax_binder_chirality"]["d_count"] = 1
    elif mutation == "failure_stage":
        runtime["first_observed_chirality_failure_stage"] = "pre_openmm_snapshot"
    elif mutation == "baseline":
        runtime["baseline_replay_expected_sha256"] = "0" * 64
    elif mutation == "target":
        runtime["target_input_sha256"] = "0" * 64
    elif mutation == "patch_evidence":
        patch_path = attempt / runtime["observer_patch_evidence_path"]
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        patch["observer_injection_status"] = "skipped"
        patch_path.write_text(json.dumps(patch) + "\n", encoding="utf-8")
        runtime["observer_patch_evidence_sha256"] = hashlib.sha256(
            patch_path.read_bytes()
        ).hexdigest()
    elif mutation == "prepatch_identity":
        runtime["source_entrypoint_prepatch_sha256"] = "0" * 64
    else:
        runtime.pop("recovery_mode")
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 6


def test_merge_never_promotes_pepglad_pre_relax_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    _, attempt, post_digest = _write_primary_set_with_instrumented_pepglad(
        parser, tmp_path / "runs"
    )
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        post_digest,
        raising=False,
    )
    runtime = json.loads(
        (attempt / "runtime_evidence.json").read_text(encoding="utf-8")
    )
    pre_relax = attempt / runtime["pre_relax_path"]
    candidate_path = attempt / "candidate_outputs.csv"
    candidate = _one_row(candidate_path)
    candidate["structure_path"] = str(pre_relax)
    candidate["source_output_path"] = str(pre_relax)
    write_csv(candidate_path, candidate)
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc["file_sha256"] = hashlib.sha256(pre_relax.read_bytes()).hexdigest()
    qc["file_size_bytes"] = str(pre_relax.stat().st_size)
    write_csv(qc_path, qc)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 6


@pytest.mark.parametrize(
    "method", ("PepMLM", "DiffPepBuilder", "RFdiffusion + ProteinMPNN")
)
def test_merge_rejects_zero_byte_primary_artifact(tmp_path: Path, method: str) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    artifact = Path(
        candidate["source_output_path"]
        if method == "PepMLM"
        else candidate["structure_path"]
    )
    artifact.write_bytes(b"")
    digest = hashlib.sha256(b"").hexdigest()
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(file_sha256=digest, file_size_bytes="0")
    write_csv(qc_path, qc)
    if method == "RFdiffusion + ProteinMPNN":
        runtime_path = attempt / "runtime_evidence.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime["rf_backbone_sha256"] = digest
        runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize(
    ("method", "artifact_kind"),
    (
        ("PepMLM", "source_csv"),
        ("DiffPepBuilder", "structure_sequence"),
        ("RFdiffusion + ProteinMPNN", "fasta_sequence"),
        ("RFdiffusion + ProteinMPNN", "backbone_length"),
    ),
)
def test_merge_rejects_candidate_artifact_content_mismatch(
    tmp_path: Path, method: str, artifact_kind: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))

    if artifact_kind == "source_csv":
        artifact = Path(candidate["source_output_path"])
        write_csv(
            artifact,
            {
                "job_id": job["job_id"],
                "generated_binder": "AAA",
                "binder_rank": "1",
                "target_id": job["target_id"],
            },
        )
        qc.update(
            file_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            file_size_bytes=str(artifact.stat().st_size),
        )
    elif artifact_kind == "structure_sequence":
        artifact = Path(candidate["structure_path"])
        artifact.write_bytes(
            _minimal_pdb(
                {
                    job["expected_target_chain"]: _runtime_target_context_sequence(
                        job
                    ),
                    job["expected_binder_chain"]: "A" * len(candidate["sequence"]),
                }
            )
        )
        qc.update(
            file_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            file_size_bytes=str(artifact.stat().st_size),
        )
    elif artifact_kind == "fasta_sequence":
        artifact = Path(candidate["source_output_path"])
        artifact.write_text(
            f">T=0.1, sample=1\n{'C' * len(candidate['sequence'])}\n",
            encoding="utf-8",
        )
        runtime["mpnn_fasta_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    else:
        artifact = Path(candidate["structure_path"])
        artifact.write_bytes(
            _minimal_pdb(
                {
                    job["expected_target_chain"]: _job_target_sequence(job),
                    job["expected_binder_chain"]: "G"
                    * (len(candidate["sequence"]) - 1),
                }
            )
        )
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        qc.update(file_sha256=digest, file_size_bytes=str(artifact.stat().st_size))
        runtime["rf_backbone_sha256"] = digest
    write_csv(qc_path, qc)
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("method", sorted(RUNTIME_TARGET_CONTEXT_METHODS))
def test_merge_rejects_mutually_forged_candidate_and_runtime_context(
    tmp_path: Path, method: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    candidate_path = Path(candidate["structure_path"])
    candidate_path.write_bytes(
        _minimal_pdb(
            {
                job["expected_target_chain"]: "CCC",
                job["expected_binder_chain"]: candidate["sequence"],
            }
        )
    )
    candidate_digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(
        file_sha256=candidate_digest,
        file_size_bytes=str(candidate_path.stat().st_size),
    )
    write_csv(qc_path, qc)

    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    context_path = Path(runtime["target_context_path"])
    context_path.write_bytes(
        _minimal_pdb({runtime["target_context_chain"]: "CCC"})
    )
    runtime["target_context_sha256"] = hashlib.sha256(
        context_path.read_bytes()
    ).hexdigest()
    if method == "D-Flow / PeptideDesign":
        runtime["candidate_sha256"] = candidate_digest
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("method", sorted(RUNTIME_TARGET_CONTEXT_METHODS))
@pytest.mark.parametrize("variant", ("single_t", "alternate_subsequence"))
def test_merge_requires_exact_method_target_context(
    tmp_path: Path, method: str, variant: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    context_sequence = (
        "T"
        if variant == "single_t"
        else EXACT_RUNTIME_TARGET_CONTEXTS[method][:-1]
    )
    candidate_path = Path(candidate["structure_path"])
    candidate_path.write_bytes(
        _minimal_pdb(
            {
                job["expected_target_chain"]: context_sequence,
                job["expected_binder_chain"]: candidate["sequence"],
            },
            chain_chirality={job["expected_binder_chain"]: job["chirality"]},
        )
    )
    candidate_digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(
        file_sha256=candidate_digest,
        file_size_bytes=str(candidate_path.stat().st_size),
    )
    write_csv(qc_path, qc)

    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    context_path = Path(runtime["target_context_path"])
    context_path.write_bytes(
        _minimal_pdb({runtime["target_context_chain"]: context_sequence})
    )
    runtime["target_context_sha256"] = hashlib.sha256(
        context_path.read_bytes()
    ).hexdigest()
    if method == "D-Flow / PeptideDesign":
        runtime["candidate_sha256"] = candidate_digest
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("nonfinite", ("nan", "inf"))
def test_merge_rejects_nonfinite_candidate_pdb(
    tmp_path: Path, nonfinite: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepGLAD" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    candidate_path = Path(candidate["structure_path"])
    lines = candidate_path.read_text(encoding="ascii").splitlines()
    atom_index = next(
        index for index, line in enumerate(lines) if line.startswith("ATOM  ")
    )
    lines[atom_index] = (
        f"{lines[atom_index][:30]}{nonfinite:>8s}{lines[atom_index][38:]}"
    )
    candidate_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(file_sha256=digest, file_size_bytes=str(candidate_path.stat().st_size))
    write_csv(qc_path, qc)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


def test_merge_recomputes_candidate_chirality(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "DiffPepBuilder" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    candidate_path = Path(candidate["structure_path"])
    candidate_path.write_bytes(
        _minimal_pdb(
            {
                job["expected_target_chain"]: EXACT_RUNTIME_TARGET_CONTEXTS[job["method"]],
                job["expected_binder_chain"]: candidate["sequence"],
            },
            chain_chirality={job["expected_binder_chain"]: "D"},
        )
    )
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(file_sha256=digest, file_size_bytes=str(candidate_path.stat().st_size))
    write_csv(qc_path, qc)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


def test_merge_recomputes_cyclic_terminal_distance(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "AfCycDesign / ColabDesign cyclic peptide"
        and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    assert qc["terminal_cn_distance"] == "1.300"
    qc["terminal_cn_distance"] = "1.500"
    write_csv(qc_path, qc)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


def test_merge_recomputes_pepmirror_geometry(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMirror" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    mirror_input = Path(runtime["mirror_input_path"])
    mirrored_target = Path(runtime["mirrored_target_path"])
    mirrored_target.write_bytes(mirror_input.read_bytes())
    runtime["mirrored_target_sha256"] = hashlib.sha256(
        mirrored_target.read_bytes()
    ).hexdigest()
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("method", sorted(RUNTIME_TARGET_CONTEXT_METHODS))
def test_merge_rejects_candidate_target_not_matching_runtime_context(
    tmp_path: Path, method: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    artifact = Path(candidate["structure_path"])
    artifact.write_bytes(
        _minimal_pdb(
            {
                job["expected_target_chain"]: "CCC",
                job["expected_binder_chain"]: candidate["sequence"],
            }
        )
    )
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(file_sha256=digest, file_size_bytes=str(artifact.stat().st_size))
    write_csv(qc_path, qc)
    if method == "D-Flow / PeptideDesign":
        runtime_path = attempt / "runtime_evidence.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime["candidate_sha256"] = digest
        runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("method", sorted(JOB_TARGET_PDB_METHODS))
def test_merge_rejects_candidate_target_not_matching_hash_bound_job_target(
    tmp_path: Path, method: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    artifact = Path(candidate["structure_path"])
    binder_sequence = (
        "G" * len(candidate["sequence"])
        if method == "RFdiffusion + ProteinMPNN"
        else candidate["sequence"]
    )
    artifact.write_bytes(
        _minimal_pdb(
            {
                job["expected_target_chain"]: "CCC",
                job["expected_binder_chain"]: binder_sequence,
            }
        )
    )
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(file_sha256=digest, file_size_bytes=str(artifact.stat().st_size))
    write_csv(qc_path, qc)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if method == "PepMirror":
        runtime["mirror_output_sha256"] = digest
    elif method == "AfCycDesign / ColabDesign cyclic peptide":
        runtime["candidate_sha256"] = digest
    elif method == "RFdiffusion + ProteinMPNN":
        runtime["rf_backbone_sha256"] = digest
    runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


def test_merge_requires_supported_primary_before_extension(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMLM" and value["seed_stage"] == "extension"
    )
    write_contract_complete_attempt(parser, tmp_path / "runs", job)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["extension_passed"] == 0
    candidate = next(
        row
        for row in csv.DictReader(
            (tmp_path / "results/pilot_candidate_outputs_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
        if row["job_id"] == job["job_id"]
    )
    assert candidate["supported_candidate"] == "no"
    provenance = json.loads(
        (tmp_path / "results/pilot_runtime_provenance_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["runtime_provenance_rows"] == 0
    assert provenance["records"] == []


@pytest.mark.parametrize("symlink_level", ("method", "job", "attempt"))
def test_merge_rejects_symlinked_run_ancestor_escape(
    tmp_path: Path, symlink_level: str
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    outside_runs = tmp_path / "outside-runs"
    outside_attempt = write_contract_complete_attempt(parser, outside_runs, job)
    run_root = tmp_path / "runs"
    slug = parser.METHOD_SLUGS[job["method"]]
    if symlink_level == "method":
        run_root.mkdir()
        (run_root / slug).symlink_to(outside_runs / slug, target_is_directory=True)
    elif symlink_level == "job":
        (run_root / slug).mkdir(parents=True)
        (run_root / slug / job["job_id"]).symlink_to(
            outside_attempt.parent, target_is_directory=True
        )
    else:
        job_root = run_root / slug / job["job_id"]
        job_root.mkdir(parents=True)
        (job_root / "attempt_001").symlink_to(outside_attempt, target_is_directory=True)

    summary = parser.merge_outputs(
        run_root=run_root,
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


def test_merge_requires_fixed_pepmirror_geometry_tolerance(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMirror" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc["mirror_target_central_inversion_tolerance"] = "0.010"
    qc["mirror_output_central_inversion_tolerance"] = "0.010"
    write_csv(qc_path, qc)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("ragged_kind", ("extra", "missing"))
def test_merge_rejects_ragged_candidate_csv_without_crash(
    tmp_path: Path, ragged_kind: str
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    path = attempt / "candidate_outputs.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    values = lines[1].split(",")
    lines[1] = ",".join(values + ["EXTRA"] if ragged_kind == "extra" else values[:-1])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("malformation", ("duplicate_header", "nul_cell"))
def test_merge_rejects_duplicate_headers_and_malformed_cells(
    tmp_path: Path, malformation: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepGLAD" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    path = attempt / "candidate_outputs.csv"
    if malformation == "duplicate_header":
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        rows[0].append("job_id")
        rows[1].append(job["job_id"])
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, lineterminator="\n").writerows(rows)
    else:
        row = _one_row(path)
        row["notes"] += "\x00"
        write_csv(path, row)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0


@pytest.mark.parametrize("swap_kind", ("runtime", "candidate"))
def test_merge_uses_one_captured_snapshot_when_input_path_is_swapped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    swap_kind: str,
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepGLAD" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    runtime_path = attempt / "runtime_evidence.json"
    candidate_path = Path(candidate["structure_path"])
    candidate_digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    assert candidate_digest != PEPGLAD_SEED42_BASELINE_SHA256
    monkeypatch.setattr(
        parser,
        "PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256",
        candidate_digest,
        raising=False,
    )
    target_path = runtime_path if swap_kind == "runtime" else candidate_path
    replacement = attempt / f"replacement-{swap_kind}{target_path.suffix}"
    if swap_kind == "runtime":
        replacement.write_text("{}\n", encoding="utf-8")
    else:
        replacement.write_bytes(
            _minimal_pdb(
                {
                    job["expected_target_chain"]: _job_target_sequence(job),
                    job["expected_binder_chain"]: "A" * len(candidate["sequence"]),
                }
            )
        )
    original_bound = parser._bound_attempt_file
    swapped = False

    def bind_then_swap(*args, **kwargs):
        nonlocal swapped
        bound = original_bound(*args, **kwargs)
        path_value = kwargs.get("path_value") if "path_value" in kwargs else args[1]
        if not swapped and bound is not None and Path(str(path_value)) == target_path:
            replacement.replace(target_path)
            swapped = True
        return bound

    monkeypatch.setattr(parser, "_bound_attempt_file", bind_then_swap)
    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert swapped is True
    assert summary["primary_passed"] == 1


def test_merge_does_not_touch_existing_outputs_on_prewrite_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    write_contract_complete_attempt(parser, tmp_path / "runs", job)
    deployment = tmp_path / "deployment.csv"
    summary_path = tmp_path / "results/pilot_v034_merge_summary.json"
    deployment.write_text("existing deployment\n", encoding="utf-8")
    summary_path.parent.mkdir(parents=True)
    summary_path.write_text("existing summary\n", encoding="utf-8")

    def fail_headers(*_args, **_kwargs):
        raise RuntimeError("prewrite validation failed")

    monkeypatch.setattr(parser, "_headers", fail_headers)
    with pytest.raises(RuntimeError, match="prewrite"):
        parser.merge_outputs(
            run_root=tmp_path / "runs",
            results_root=tmp_path / "results",
            deployment_path=deployment,
        )

    assert deployment.read_text(encoding="utf-8") == "existing deployment\n"
    assert summary_path.read_text(encoding="utf-8") == "existing summary\n"


def test_merge_rolls_back_whole_output_bundle_when_second_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepGLAD" and value["seed_stage"] == "primary"
    )
    write_contract_complete_attempt(parser, tmp_path / "runs", job)
    deployment = tmp_path / "deployment.csv"
    results = tmp_path / "results"
    output_paths = (
        deployment,
        results / "pilot_method_output_manifest_v0.34.csv",
        results / "pilot_candidate_outputs_v0.34.csv",
        results / "pilot_candidate_qc_v0.34.csv",
        results / "pilot_run_v0.34.csv",
        results / "pilot_runtime_provenance_v0.34.json",
        results / "pilot_failure_diagnostics_v0.34.json",
        results / "pilot_v034_merge_summary.json",
    )
    prior = {}
    for index, path in enumerate(output_paths):
        path.parent.mkdir(parents=True, exist_ok=True)
        prior[path] = f"prior-{index}\n".encode("ascii")
        path.write_bytes(prior[path])

    real_replace = parser.os.replace
    replace_calls = 0

    def fail_second_replace(source, destination, *args, **kwargs):
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("injected second replace failure")
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(parser.os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="second replace"):
        parser.merge_outputs(
            run_root=tmp_path / "runs",
            results_root=results,
            deployment_path=deployment,
        )

    assert replace_calls >= 2
    assert {path: path.read_bytes() for path in output_paths} == prior


def test_merge_normalizes_relative_run_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    write_contract_complete_attempt(parser, Path("runs"), job)

    summary = parser.merge_outputs(
        run_root=Path("runs"),
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 1


@pytest.mark.parametrize(
    ("record_name", "field", "bad_value"),
    (
        ("manifest", "run_record_id", "wrong_attempt"),
        ("manifest", "execution_stage", "extension"),
        ("manifest", "parser_status", "partial"),
        ("manifest", "overall_qc_status", "pass_with_warning"),
        ("manifest", "raw_output_root", "<outside>"),
        ("manifest", "stdout_log", "<outside>"),
        ("manifest", "stderr_log", "<outside>"),
        ("manifest", "command", "<outside-command>"),
        ("manifest", "runtime_seconds", "nan"),
        ("manifest", "exit_code", "1"),
        ("result", "parser_status", "partial"),
        ("result", "overall_qc_status", "pass_with_warning"),
        ("result", "attempt_dir", "<outside>"),
        ("result", "runtime_seconds", "0"),
        ("result", "exit_code", 1),
    ),
)
def test_merge_rejects_unbound_or_contradictory_execution_evidence(
    tmp_path: Path, record_name: str, field: str, bad_value: object
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    if bad_value == "<outside>":
        bad_value = str(tmp_path / "outside")
    elif bad_value == "<outside-command>":
        outside = tmp_path / "outside-command.sh"
        outside.write_text("exit 0\n", encoding="utf-8")
        bad_value = f"bash {outside}"

    if record_name == "manifest":
        path = attempt / "method_output_manifest.csv"
        record = _one_row(path)
        record[field] = str(bad_value)
        write_csv(path, record)
    else:
        path = attempt / "run_result.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record[field] = bad_value
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_rejects_runtime_evidence_symlink_escape(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    outside = tmp_path / "outside-runtime-evidence.json"
    outside.write_bytes(runtime_path.read_bytes())
    runtime_path.unlink()
    runtime_path.symlink_to(outside)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["runtime_provenance_rows"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


@pytest.mark.parametrize(
    "filename",
    (
        "run_result.json",
        "method_output_manifest.csv",
        "candidate_outputs.csv",
        "candidate_qc.csv",
    ),
)
def test_merge_rejects_external_symlink_for_canonical_attempt_input(
    tmp_path: Path, filename: str
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    path = attempt / filename
    outside = tmp_path / f"outside-{filename}"
    path.replace(outside)
    path.symlink_to(outside)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] != "supported"


@pytest.mark.parametrize(
    ("record_name", "field"),
    (
        ("manifest", "status_reason"),
        ("manifest", "created_at"),
        ("result", "status_reason"),
        ("result", "created_at"),
        ("candidate", "status_reason"),
        ("candidate", "notes"),
        ("qc", "file_reason"),
        ("qc", "status_reason"),
    ),
)
def test_merge_rejects_incomplete_canonical_attempt_records(
    tmp_path: Path, record_name: str, field: str
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    paths = {
        "manifest": attempt / "method_output_manifest.csv",
        "result": attempt / "run_result.json",
        "candidate": attempt / "candidate_outputs.csv",
        "qc": attempt / "candidate_qc.csv",
    }
    path = paths[record_name]
    if path.suffix == ".json":
        record = json.loads(path.read_text(encoding="utf-8"))
        record.pop(field)
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    else:
        record = _one_row(path)
        record.pop(field)
        write_csv(path, record)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


@pytest.mark.parametrize("sequence", ("A1D", "A D"))
def test_merge_rejects_non_letter_peptide_sequence(
    tmp_path: Path, sequence: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMLM" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate_path = attempt / "candidate_outputs.csv"
    candidate = _one_row(candidate_path)
    candidate["sequence"] = sequence
    write_csv(candidate_path, candidate)

    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(
        sequence_length=str(len(sequence)),
        noncanonical_status="warn",
        noncanonical_residues="".join(
            sorted({character for character in sequence if not character.isalpha()})
        ),
        overall_qc_status="pass_with_warning",
        status_reason="noncanonical_status",
    )
    write_csv(qc_path, qc)
    manifest_path = attempt / "method_output_manifest.csv"
    manifest = _one_row(manifest_path)
    manifest["overall_qc_status"] = "pass_with_warning"
    write_csv(manifest_path, manifest)
    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["overall_qc_status"] = "pass_with_warning"
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


@pytest.mark.parametrize(
    "mutation",
    (
        "duplicate_primary_method",
        "duplicate_job_id",
        "orphan_extension",
        "mismatched_extension_contract",
    ),
)
def test_load_jobs_rejects_noncanonical_method_topology(
    tmp_path: Path, mutation: str
) -> None:
    parser = load_parser()
    rows = [dict(row) for row in parser.load_jobs()]
    if mutation == "duplicate_primary_method":
        for row in rows:
            if row["method"] == "DiffPepBuilder":
                row["method"] = "PepMLM"
    elif mutation == "duplicate_job_id":
        rows[1]["job_id"] = rows[0]["job_id"]
    elif mutation == "orphan_extension":
        extension = next(row for row in rows if row["seed_stage"] == "extension")
        wrong_primary = next(
            row
            for row in rows
            if row["seed_stage"] == "primary" and row["method"] != extension["method"]
        )
        extension["primary_job_id"] = wrong_primary["job_id"]
    else:
        extension = next(row for row in rows if row["seed_stage"] == "extension")
        extension["target_id"] = "wrong_target"
    manifest = tmp_path / "jobs.csv"
    write_csv_rows(manifest, rows)

    with pytest.raises(ValueError, match="topology|unique"):
        parser.load_jobs(manifest)


@pytest.mark.parametrize(
    ("method", "record_name", "field", "bad_value"),
    (
        ("DiffPepBuilder", "candidate", "binder_chain", "Z"),
        ("DiffPepBuilder", "candidate", "chirality", "D"),
        ("DiffPepBuilder", "candidate", "peptide_type", "D-peptide"),
        ("DiffPepBuilder", "candidate", "source_output_id", ""),
        ("DiffPepBuilder", "qc", "noncanonical_status", ""),
        ("DiffPepBuilder", "qc", "sequence_length", "999"),
        ("DiffPepBuilder", "qc", "file_size_bytes", "0"),
        ("DiffPepBuilder", "qc", "chirality_l_count", "0"),
        ("DiffPepBuilder", "qc", "chirality_unknown_count", "1"),
        (
            "AfCycDesign / ColabDesign cyclic peptide",
            "qc",
            "terminal_cn_distance",
            "nan",
        ),
        (
            "PepMirror",
            "qc",
            "mirror_output_central_inversion_max_residual",
            "0.003",
        ),
    ),
)
def test_merge_rejects_contradictory_candidate_or_numeric_qc_metadata(
    tmp_path: Path,
    method: str,
    record_name: str,
    field: str,
    bad_value: str,
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    path = attempt / (
        "candidate_outputs.csv" if record_name == "candidate" else "candidate_qc.csv"
    )
    record = _one_row(path)
    record[field] = bad_value
    write_csv(path, record)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_requires_runtime_evidence_for_supported_candidate(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    (attempt / "runtime_evidence.json").unlink()

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    row = next(
        value
        for value in csv.DictReader(
            (tmp_path / "deployment.csv").open(newline="", encoding="utf-8")
        )
        if value["job_id"] == job["job_id"]
    )
    assert row["merge_status"] == "evidence_incomplete"
    assert row["supported_candidate"] == "no"


def test_merge_excludes_runtime_provenance_for_non_pepglad_parse_failure(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMLM" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result.update(
        status="parse_failed",
        parser_status="failed",
        overall_qc_status="fail",
        status_reason="parser_contract_failed",
    )
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    manifest_path = attempt / "method_output_manifest.csv"
    manifest = _one_row(manifest_path)
    manifest.update(
        status="parse_failed",
        parser_status="failed",
        overall_qc_status="fail",
        status_reason="parser_contract_failed",
    )
    write_csv(manifest_path, manifest)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    provenance = json.loads(
        (tmp_path / "results/pilot_runtime_provenance_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["runtime_provenance_rows"] == 0
    assert provenance["records"] == []


def test_merge_excludes_runtime_provenance_for_non_pepglad_qc_failure(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMLM" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    result_path = attempt / "run_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result.update(
        status="qc_failed",
        overall_qc_status="fail",
        status_reason="candidate_qc_failed",
    )
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    manifest_path = attempt / "method_output_manifest.csv"
    manifest = _one_row(manifest_path)
    manifest.update(
        status="qc_failed",
        overall_qc_status="fail",
        status_reason="candidate_qc_failed",
    )
    write_csv(manifest_path, manifest)
    qc_path = attempt / "candidate_qc.csv"
    qc = _one_row(qc_path)
    qc.update(overall_qc_status="fail", status_reason="candidate_qc_failed")
    write_csv(qc_path, qc)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    provenance = json.loads(
        (tmp_path / "results/pilot_runtime_provenance_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["runtime_provenance_rows"] == 0
    assert provenance["records"] == []


def test_merge_excludes_runtime_provenance_for_non_supported_pseudo_runtime(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMLM" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    runtime_path.write_text(
        json.dumps(
            {
                "requested_seed": 42,
                "effective_seed": 42,
                "seed_control_status": "honored",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    provenance = json.loads(
        (tmp_path / "results/pilot_runtime_provenance_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["runtime_provenance_rows"] == 0
    assert provenance["records"] == []


@pytest.mark.parametrize(
    ("method", "missing_field"),
    (
        ("PepMLM", "model_weights_sha256"),
        ("DiffPepBuilder", "model_asset_sha256"),
        ("PepGLAD", "source_commit"),
        ("D-Flow / PeptideDesign", "source_content_manifest_sha256"),
        ("PepMirror", "mirror_output_sha256"),
        ("AfCycDesign / ColabDesign cyclic peptide", "alphafold_params_sha256"),
        ("RFdiffusion + ProteinMPNN", "rf_trb_semantic_sha256"),
    ),
)
def test_merge_rejects_missing_method_specific_runtime_evidence(
    tmp_path: Path, method: str, missing_field: str
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == method and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime.pop(missing_field)
    runtime_path.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_rejects_candidate_path_outside_attempt(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "D-Flow / PeptideDesign"
        and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate_path = tmp_path / "outside-attempt.pdb"
    candidate_path.write_text("outside\n", encoding="utf-8")
    candidate = _one_row(attempt / "candidate_outputs.csv")
    candidate["structure_path"] = str(candidate_path)
    write_csv(attempt / "candidate_outputs.csv", candidate)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_rejects_failed_method_specific_qc(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMirror" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    qc = _one_row(attempt / "candidate_qc.csv")
    qc["mirror_output_atom_identity_status"] = "fail"
    write_csv(attempt / "candidate_qc.csv", qc)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_marks_missing_method_specific_qc_statuses_not_applicable(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMLM" and value["seed_stage"] == "primary"
    )
    write_complete_attempt(parser, tmp_path / "runs", job)

    parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    qc_rows = list(
        csv.DictReader(
            (tmp_path / "results/pilot_candidate_qc_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    qc = next(value for value in qc_rows if value["job_id"] == job["job_id"])
    for field in (
        "backbone_to_fasta_handoff_status",
        "mirror_target_atom_identity_status",
        "mirror_target_central_inversion_status",
        "mirror_output_atom_identity_status",
        "mirror_output_central_inversion_status",
    ):
        assert qc.get(field) == "not_applicable"


def test_merge_preserves_qc_failure_diagnostics_in_execution_summary(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        value for value in parser.load_jobs() if value["seed_stage"] == "primary"
    )
    attempt = write_complete_attempt(parser, tmp_path / "runs", job)
    result = json.loads((attempt / "run_result.json").read_text(encoding="utf-8"))
    result.update(
        status="qc_failed", overall_qc_status="fail", status_reason="chirality_status"
    )
    (attempt / "run_result.json").write_text(
        json.dumps(result) + "\n", encoding="utf-8"
    )
    write_csv(
        attempt / "candidate_qc.csv",
        {
            "design_id": result["design_id"],
            "job_id": job["job_id"],
            "overall_qc_status": "fail",
            "status_reason": "chirality_status",
            "chirality_evaluable": "11",
            "chirality_l_count": "4",
            "chirality_d_count": "7",
        },
    )

    parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    row = next(
        value
        for value in csv.DictReader(
            (tmp_path / "deployment.csv").open(newline="", encoding="utf-8")
        )
        if value["job_id"] == job["job_id"]
    )
    assert row["qc_status_reason"] == "chirality_status"
    assert row["chirality_evaluable"] == "11"
    assert row["chirality_l_count"] == "4"
    assert row["chirality_d_count"] == "7"

    candidates = list(
        csv.DictReader(
            (tmp_path / "results/pilot_candidate_outputs_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    candidate = next(value for value in candidates if value["job_id"] == job["job_id"])
    assert candidate["design_id"] == result["design_id"]
    assert candidate["sequence"] == "ACD"
    assert candidate["parse_status"] == "parsed"
    assert candidate["supported_candidate"] == "no"

    qc_rows = list(
        csv.DictReader(
            (tmp_path / "results/pilot_candidate_qc_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    failed_qc = next(value for value in qc_rows if value["job_id"] == job["job_id"])
    assert failed_qc["overall_qc_status"] == "fail"
    assert failed_qc["supported_candidate"] == "no"

    run_rows = list(
        csv.DictReader(
            (tmp_path / "results/pilot_run_v0.34.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    failed_run = next(value for value in run_rows if value["job_id"] == job["job_id"])
    assert failed_run["design_id"] == result["design_id"]
    assert failed_run["sequence"] == "ACD"
    assert failed_run["supported_candidate"] == "no"


def test_merge_binds_method_specific_runtime_provenance(tmp_path: Path) -> None:
    parser = load_parser()
    job = next(
        value
        for value in parser.load_jobs()
        if value["method"] == "PepMirror" and value["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    provenance = json.loads(
        (tmp_path / "results/pilot_runtime_provenance_v0.34.json").read_text(
            encoding="utf-8"
        )
    )
    record = next(
        value for value in provenance["records"] if value["job_id"] == job["job_id"]
    )
    assert summary["primary_passed"] == 1
    assert summary["runtime_provenance_rows"] == 1
    assert record["attempt_id"] == "attempt_001"
    assert record["runtime_evidence_path"] == "runtime_evidence.json"
    assert (
        record["runtime_evidence_sha256"]
        == hashlib.sha256(runtime_path.read_bytes()).hexdigest()
    )
    assert (
        record["evidence_semantic_sha256"]
        == hashlib.sha256(
            json.dumps(runtime, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    assert record["evidence"] == runtime


def _rewrite_attempt_qc(
    job: dict[str, str], attempt: Path, candidate: dict[str, str]
) -> None:
    runtime_path = next(
        path
        for path in (
            attempt / "runtime_evidence.json",
            attempt / "raw/runtime_evidence.json",
        )
        if path.is_file()
    )
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    oracle_job = dict(job)
    target = Path(oracle_job.get("target_pdb_path", ""))
    if target and not target.is_absolute():
        oracle_job["target_pdb_path"] = str(ROOT / target)
    observed = evaluate_candidate_qc(
        oracle_job, candidate, runtime, attempt / "raw"
    )
    assert observed["overall_qc_status"] in {"pass", "pass_with_warning"}
    write_csv(
        attempt / "candidate_qc.csv",
        {
            "design_id": candidate["design_id"],
            "job_id": job["job_id"],
            **{key: str(value) for key, value in observed.items()},
        },
    )


def test_merge_replays_pepmlm_adapter_instead_of_trusting_coordinated_compact_rows(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        row
        for row in parser.load_jobs()
        if row["method"] == "PepMLM" and row["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    official = Path(candidate["source_output_path"])
    official_payload = official.read_bytes()
    forged = attempt / "raw/forged_pepmlm_generated.csv"
    write_csv(
        forged,
        {
            "job_id": job["job_id"],
            "generated_binder": "ACE",
            "binder_rank": "1",
            "target_id": job["target_id"],
        },
    )
    candidate.update(sequence="ACE", source_output_path=str(forged))
    write_csv(attempt / "candidate_outputs.csv", candidate)
    _rewrite_attempt_qc(job, attempt, candidate)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert official.read_bytes() == official_payload
    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


def test_merge_replays_structure_adapter_instead_of_trusting_forged_pdb_sequence(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        row
        for row in parser.load_jobs()
        if row["method"] == "DiffPepBuilder" and row["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    candidate = _one_row(attempt / "candidate_outputs.csv")
    official = Path(candidate["structure_path"])
    official_payload = official.read_bytes()
    forged = attempt / "raw/forged_diffpepbuilder_candidate.pdb"
    forged.write_bytes(
        _minimal_pdb(
            {
                job["expected_target_chain"]: _runtime_target_context_sequence(job),
                job["expected_binder_chain"]: "LMKIHGFEDCA",
            },
            chain_chirality={job["expected_binder_chain"]: job["chirality"]},
        )
    )
    candidate.update(
        sequence="LMKIHGFEDCA",
        structure_path=str(forged),
        source_output_path=str(forged),
    )
    write_csv(attempt / "candidate_outputs.csv", candidate)
    _rewrite_attempt_qc(job, attempt, candidate)

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert official.read_bytes() == official_payload
    assert summary["primary_passed"] == 0
    assert summary["job_status"][job["job_id"]] == "evidence_incomplete"


@pytest.mark.parametrize("bad_value", ("extra", float("nan")))
def test_merge_rejects_runtime_extra_fields_even_with_recomputed_semantic_digest(
    tmp_path: Path, bad_value: object
) -> None:
    parser = load_parser()
    job = next(
        row
        for row in parser.load_jobs()
        if row["method"] == "PepMLM" and row["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["unexpected_runtime_field"] = bad_value
    runtime_path.write_text(
        json.dumps(runtime, indent=2, allow_nan=True) + "\n", encoding="utf-8"
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["runtime_provenance_rows"] == 0


def test_merge_rejects_nested_runtime_extra_field_with_recomputed_semantic_digest(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        row
        for row in parser.load_jobs()
        if row["method"] == "RFdiffusion + ProteinMPNN"
        and row["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["rf_trb_semantic_extract"]["unexpected_nested_field"] = "forged"
    runtime["rf_trb_semantic_sha256"] = hashlib.sha256(
        json.dumps(
            runtime["rf_trb_semantic_extract"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    runtime_path.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["runtime_provenance_rows"] == 0


def test_merge_rejects_overflowed_runtime_number_before_semantic_hashing(
    tmp_path: Path,
) -> None:
    parser = load_parser()
    job = next(
        row
        for row in parser.load_jobs()
        if row["method"] == "PepMLM" and row["seed_stage"] == "primary"
    )
    attempt = write_contract_complete_attempt(parser, tmp_path / "runs", job)
    runtime_path = attempt / "runtime_evidence.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    payload = json.dumps({**runtime, "unexpected_runtime_number": 0})
    runtime_path.write_text(
        payload.replace('"unexpected_runtime_number": 0', '"unexpected_runtime_number": 1e999')
        + "\n",
        encoding="utf-8",
    )

    summary = parser.merge_outputs(
        run_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        deployment_path=tmp_path / "deployment.csv",
    )

    assert summary["primary_passed"] == 0
    assert summary["runtime_provenance_rows"] == 0


def test_runtime_provenance_payload_schema_rejects_top_and_record_extra() -> None:
    parser = load_parser()
    record = {
        "job_id": "job",
        "method": "PepMLM",
        "seed_stage": "primary",
        "random_seed": 42,
        "attempt_id": "attempt_001",
        "runtime_evidence_path": "raw/runtime_evidence.json",
        "runtime_evidence_sha256": "a" * 64,
        "evidence_semantic_sha256": "b" * 64,
        "evidence": {},
    }
    payload = {
        "schema_version": "v0.34",
        "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
        "records": [record],
    }

    assert parser._runtime_provenance_payload_contract(payload) is True
    assert parser._runtime_provenance_payload_contract(
        {**payload, "unexpected_top_level": True}
    ) is False
    assert parser._runtime_provenance_payload_contract(
        {**payload, "records": [{**record, "unexpected_record_field": True}]}
    ) is False
