from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, Mapping

from .common import (
    parse_pdb_chain_sequences,
    require_clean_git_checkout,
    require_file_sha256,
    sha256_file,
    validate_output_file,
)


METHOD = "DiffPepBuilder"
SOURCE_COMMIT = "c19eb4f0cd2419d3bcc116184c0868243b6c4169"
MODEL_REVISION = "diffpepbuilder_v1.pth_external_manifest_v0.20"
SOURCE_ROOT = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/DiffPepBuilder")
MODEL_ROOT = Path("/data/protein-design/data/benchmark_models/diffpepbuilder")
SOURCE_ENTRYPOINT = SOURCE_ROOT / "experiments/run_inference.py"
SOURCE_ENTRYPOINT_SHA256 = "872868f48e3cf66f0ce159ada589ca2126a3b2ba98470ab3bbcb9ffc4481f7c6"
MODEL_ASSETS = {
    "diffpepbuilder_v1.pth": "dbc4283257d27e38a1ce90c9344063b046ab7161745ebed1fd98a4b0439b992a",
    "esm2_t33_650M_UR50D.pt": "ea9d0522b335a8778dea6535a65301f10208dece28cd5865482b0b1fc446168c",
    "esm2_t33_650M_UR50D-contact-regression.pt": "8ffe6edbd4173dc8d45c2cd5cb27d43aad77ec26b4c768200c58ae1f96693575",
}
DEFAULT_IMAGE = "pd-pyrosetta-methods-gpu:0.20"
DEFAULT_ENV = "bench-diffpepbuilder"


def _runtime_evidence(job: Mapping[str, str], raw: Path) -> dict[str, Any]:
    requested = int(job.get("random_seed", "-1"))
    fallback: dict[str, Any] = {
        "requested_seed": requested,
        "effective_seed": -1,
        "seed_control_status": "missing",
    }
    try:
        value = json.loads((raw / "runtime_evidence.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return fallback
    if isinstance(value, dict):
        fallback.update(value)
    return fallback


def _failed(reason: str) -> dict[str, str]:
    return {
        "sequence": "",
        "structure_path": "",
        "source_output_path": "",
        "binder_chain": "A",
        "parse_status": "failed",
        "status_reason": reason,
    }


def _write_polymer_receptor(source: Path, destination: Path, chains: set[str]) -> None:
    """Remove waters/hetero atoms that upstream treats as ligand residues."""

    kept: list[str] = []
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM  ") or len(line) < 27:
            continue
        if line[21].strip() not in chains or line[16].strip() not in {"", "A"}:
            continue
        kept.append(line)
    if not kept:
        raise ValueError("DiffPepBuilder receptor filter found no polymer atoms")
    destination.write_text("\n".join(kept) + "\nEND\n", encoding="utf-8")
    source_sequences = parse_pdb_chain_sequences(source)
    filtered_sequences = parse_pdb_chain_sequences(destination)
    if any(
        not source_sequences.get(chain)
        or filtered_sequences.get(chain) != source_sequences.get(chain)
        for chain in chains
    ):
        raise ValueError("DiffPepBuilder receptor filter changed a required chain sequence")


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
        raise ValueError("DiffPepBuilder v0.34 requires one fixed positive peptide length")
    target = Path(job["target_pdb_path"]).resolve()
    target_digest = require_file_sha256(
        target,
        job.get("target_pdb_sha256", ""),
        "DiffPepBuilder target input",
    )
    source_commit = require_clean_git_checkout(
        SOURCE_ROOT, SOURCE_COMMIT, "DiffPepBuilder source"
    )
    source_digest = require_file_sha256(
        SOURCE_ENTRYPOINT,
        SOURCE_ENTRYPOINT_SHA256,
        "DiffPepBuilder inference source",
    )
    model_digests = {
        name: require_file_sha256(MODEL_ROOT / name, expected, f"DiffPepBuilder {name}")
        for name, expected in MODEL_ASSETS.items()
    }
    environment = execution.get("container_or_env", "")
    image, _, conda_env = environment.partition("/")
    image = image or DEFAULT_IMAGE
    conda_env = conda_env or DEFAULT_ENV
    filtered_target = attempt_dir / "diffpepbuilder_receptor.pdb"
    _write_polymer_receptor(target, filtered_target, {"A", "B"})
    filtered_target_digest = sha256_file(filtered_target)

    (attempt_dir / "receptor_info.json").write_text(
        json.dumps({"3EQS": {"lig_chain": "B"}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    seeded_entry = attempt_dir / "diffpepbuilder_seeded_entry.py"
    seeded_entry.write_text(
        '''#!/usr/bin/env python3
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
sys.argv = ["experiments.run_inference", *remaining]
runpy.run_module("experiments.run_inference", run_name="__main__")
''',
        encoding="utf-8",
    )
    seeded_entry.chmod(0o755)
    finalizer = attempt_dir / "diffpepbuilder_finalize.py"
    finalizer.write_text(
        f'''#!/usr/bin/env python3
import json
import hashlib
import shutil
from pathlib import Path

SEED = {seed}
WORK = Path("/data/attempt/work")
OUTPUT = Path("/data/attempt/raw/diffpepbuilder_candidate.pdb")
CONTEXT_SOURCE = WORK / "input/3EQS_processed.pdb"
CONTEXT_OUTPUT = Path("/data/attempt/raw/diffpepbuilder_target_context.pdb")
HOST_CONTEXT_OUTPUT = Path({str(attempt_dir / 'raw/diffpepbuilder_target_context.pdb')!r})
RUNTIME = Path("/data/attempt/raw/runtime_evidence.json")
matches = sorted(WORK.glob("runs/**/3EQS_length_{minimum}_sample_0.pdb"))
if len(matches) != 1:
    raise RuntimeError(f"expected one fresh DiffPepBuilder candidate, observed {{len(matches)}}")
shutil.copy2(matches[0], OUTPUT)
if not CONTEXT_SOURCE.is_file():
    raise FileNotFoundError(CONTEXT_SOURCE)
shutil.copy2(CONTEXT_SOURCE, CONTEXT_OUTPUT)
RUNTIME.write_text(json.dumps({{
    "requested_seed": SEED,
    "effective_seed": SEED,
    "seed_control_status": "honored",
    "source_candidate_path": str(matches[0]),
    "source_commit": {json.dumps(source_commit)},
    "source_entrypoint_sha256": {json.dumps(source_digest)},
    "model_asset_sha256": {json.dumps(model_digests, sort_keys=True)},
    "container_image": {json.dumps(image)},
    "conda_environment": {json.dumps(conda_env)},
	    "filtered_receptor_sha256": {json.dumps(filtered_target_digest)},
	    "target_input_sha256": {json.dumps(target_digest)},
    "target_context_path": str(HOST_CONTEXT_OUTPUT),
    "target_context_sha256": hashlib.sha256(CONTEXT_OUTPUT.read_bytes()).hexdigest(),
    "target_context_chain": "B",
    "target_context_mode": "ordered_subsequence",
}}, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
''',
        encoding="utf-8",
    )
    finalizer.chmod(0o755)

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
            'cp /data/attempt/receptor_info.json "$work/receptor_info.json"',
            'cd "$work"',
            "mkdir -p experiments/checkpoints",
            "ln -sf /data/models/diffpepbuilder_v1.pth experiments/checkpoints/diffpepbuilder_v1.pth",
            "for checkpoint in esm2_t33_650M_UR50D.pt esm2_t33_650M_UR50D-contact-regression.pt; do "
            'test ! -s "/data/models/$checkpoint" || ln -sf "/data/models/$checkpoint" "experiments/checkpoints/$checkpoint"; '
            "done",
            "python experiments/process_receptor.py --pdb_dir input --write_dir data/receptor_data "
            "--receptor_info_path receptor_info.json",
            'export BASE_PATH="$work"',
            'PYTHONPATH="$work:${PYTHONPATH:-}" python /data/attempt/diffpepbuilder_seeded_entry.py '
            f"--seed {seed} data.val_csv_path=data/receptor_data/metadata_test.csv "
            "experiment.use_ddp=False experiment.num_gpus=1 experiment.eval_batch_size=1 "
            "experiment.num_loader_workers=1 inference.denoising.num_t=2 "
            f"inference.seed={seed} inference.sampling.samples_per_length=1 "
            f"inference.sampling.min_length={minimum} inference.sampling.max_length={maximum} "
            "inference.ss_bond.build_ss_bond=False",
            "python /data/attempt/diffpepbuilder_finalize.py",
            "test -s /data/attempt/raw/diffpepbuilder_candidate.pdb",
            "test -s /data/attempt/raw/diffpepbuilder_target_context.pdb",
            "test -s /data/attempt/raw/runtime_evidence.json",
        ]
    )
    command_path = attempt_dir / "command.sh"
    mounts = [
        f"-v {shlex.quote(str(attempt_dir.resolve()) + ':/data/attempt')}",
        f"-v {shlex.quote(str(SOURCE_ROOT) + ':/data/source:ro')}",
        f"-v {shlex.quote(str(filtered_target.resolve()) + ':/data/input/3EQS.pdb:ro')}",
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
    output = raw / "diffpepbuilder_candidate.pdb"
    if validate_output_file(output, raw)["status"] != "pass":
        return _failed("diffpepbuilder_standard_output_missing"), runtime
    try:
        sequences = parse_pdb_chain_sequences(output)
    except (OSError, UnicodeError, ValueError):
        return _failed("diffpepbuilder_standard_output_invalid"), runtime
    binder_chain = job.get("expected_binder_chain", "A") or "A"
    target_chain = job.get("expected_target_chain", "B") or "B"
    sequence = sequences.get(binder_chain, "")
    if not sequence or target_chain not in sequences or target_chain == binder_chain:
        return _failed("diffpepbuilder_chain_contract_invalid"), runtime
    return (
        {
            "sequence": sequence,
            "structure_path": str(output),
            "source_output_path": str(output),
            "binder_chain": binder_chain,
            "parse_status": "parsed",
            "status_reason": "diffpepbuilder_standard_output_parsed",
        },
        runtime,
    )
