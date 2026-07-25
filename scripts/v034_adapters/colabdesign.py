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


METHOD = "AfCycDesign / ColabDesign cyclic peptide"
SOURCE_COMMIT = "e31a56fe1d9b4de25c8697f3a28b75892941cc72"
MODEL_REVISION = "alphafold_model_1_ptm@sha256:5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84"

SOURCE_ROOT = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ColabDesign")
PARAMS_ROOT = Path("/data/protein-design/data/alphafold_db/params")
SOURCE_NOTEBOOK = SOURCE_ROOT / "af/examples/af_cyc_design.ipynb"
SOURCE_NOTEBOOK_SHA256 = "ca3bd3cc14daa95e1529fd2d5c1ca18263d12341a75d2967715ec23720b129ed"
ALPHAFOLD_MODEL_NAME = "model_1_ptm"
ALPHAFOLD_PARAMS = PARAMS_ROOT / "params_model_1_ptm.npz"
ALPHAFOLD_PARAMS_SHA256 = "5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84"
DEFAULT_IMAGE = "pd-benchmark-methods-gpu:0.21"
DEFAULT_ENV = "bench-colabdesign"
IMAGE_IDS = {
    DEFAULT_IMAGE: "sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2"
}


def _entry_text(*, seed: int, binder_len: int, target_name: str) -> str:
    return f'''#!/usr/bin/env python3
import hashlib
import json
import os
import random
from pathlib import Path

import numpy as np

os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

SEED = {seed}
random.seed(SEED)
np.random.seed(SEED)


def add_cyclic_offset(self, offset_type=2):
    """Apply the cyclic residue offset used by af/examples/af_cyc_design.ipynb."""
    def cyclic_offset(length):
        i = np.arange(length)
        ij = np.stack([i, i + length], -1)
        offset = i[:, None] - i[None, :]
        c_offset = np.abs(ij[:, None, :, None] - ij[None, :, None, :]).min((2, 3))
        if offset_type >= 2:
            a = c_offset < np.abs(offset)
            c_offset[a] = -c_offset[a]
        if offset_type == 3:
            idx = np.abs(c_offset) > 2
            c_offset[idx] = (32 * c_offset[idx]) / np.abs(c_offset[idx])
        return c_offset * np.sign(offset)

    idx = self._inputs["residue_index"]
    offset = np.array(idx[:, None] - idx[None, :])
    if self.protocol == "binder":
        c_offset = cyclic_offset(self._binder_len)
        offset[self._target_len:, self._target_len:] = c_offset
    elif self.protocol in ("fixbb", "partial", "hallucination"):
        start = 0
        for length in self._lengths:
            offset[start:start + length, start:start + length] = cyclic_offset(length)
            start += length
    self._inputs["offset"] = offset


try:
    from colabdesign import mk_afdesign_model
except ImportError:
    from colabdesign.af import mk_afdesign_model

model = mk_afdesign_model(
    protocol="binder",
    use_multimer=False,
    data_dir="/data/alphafold_params",
    num_recycles=0,
    recycle_mode="sample",
    model_names=["model_1_ptm"],
)
model.prep_inputs(
    pdb_filename="/data/input/{target_name}",
    chain="A",
    binder_len={binder_len},
    binder_chain=None,
    hotspot=None,
    ignore_missing=False,
)
model.set_seed(SEED)
add_cyclic_offset(model, offset_type=2)
binder_offset = np.asarray(model._inputs["offset"])[model._target_len:, model._target_len:]
terminal_offset = int(binder_offset[0, -1])
if abs(terminal_offset) != 1:
    raise RuntimeError(f"cyclic terminal offset must be +/-1, observed {{terminal_offset}}")
model.design_logits(1)

candidate = Path("/data/attempt/raw/afcycdesign_candidate.pdb")
model.save_pdb(str(candidate))
if not candidate.is_file() or candidate.stat().st_size <= 0:
    raise FileNotFoundError(candidate)

host_candidate = Path(os.environ["V034_HOST_ATTEMPT"]) / "raw/afcycdesign_candidate.pdb"
runtime = {{
    "requested_seed": SEED,
    "effective_seed": SEED,
    "seed_control_status": "honored",
    "cyclic_offset_applied": True,
    "cyclic_offset_type": 2,
    "terminal_offset": terminal_offset,
    "candidate_path": str(host_candidate),
    "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    "source_commit": "{SOURCE_COMMIT}",
    "source_notebook_sha256": "{SOURCE_NOTEBOOK_SHA256}",
    "alphafold_model_name": "{ALPHAFOLD_MODEL_NAME}",
    "alphafold_params_sha256": "{ALPHAFOLD_PARAMS_SHA256}",
    "container_image": os.environ["V034_CONTAINER_IMAGE"],
    "container_image_id": os.environ["V034_CONTAINER_IMAGE_ID"],
}}
Path("/data/attempt/raw/runtime_evidence.json").write_text(
    json.dumps(runtime, indent=2, sort_keys=True) + "\\n",
    encoding="utf-8",
)
'''


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
        "peptide_type": job.get("peptide_type", "cyclic"),
        "chirality": job.get("chirality", "L"),
        "cyclic": job.get("cyclic", "yes"),
        "binder_chain": job.get("expected_binder_chain", "B"),
        "parse_status": "parsed",
        "status_reason": "v034_afcycdesign_standard_candidate_parsed",
        "notes": "Bounded connectivity evidence only; not Benchmark result or scoring evidence",
    }


def prepare(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    attempt_dir: Path,
) -> list[str]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    minimum = int(job.get("length_min", "14"))
    maximum = int(job.get("length_max", "14"))
    if minimum != 14 or maximum != 14:
        raise ValueError("AfCycDesign v0.34 requires binder_len=14")
    if job.get("expected_target_chain", "A") != "A":
        raise ValueError("AfCycDesign v0.34 requires target chain A")
    if job.get("expected_binder_chain", "B") != "B" or job.get("cyclic", "yes") != "yes":
        raise ValueError("AfCycDesign v0.34 requires cyclic binder chain B")

    seed = int(job["random_seed"])
    target = Path(job["target_pdb_path"]).resolve()
    require_file_sha256(target, job.get("target_pdb_sha256", ""), "AfCycDesign target")
    require_clean_git_checkout(SOURCE_ROOT, SOURCE_COMMIT, "ColabDesign source")
    require_file_sha256(
        SOURCE_NOTEBOOK, SOURCE_NOTEBOOK_SHA256, "ColabDesign cyclic notebook"
    )
    require_file_sha256(
        ALPHAFOLD_PARAMS, ALPHAFOLD_PARAMS_SHA256, "AlphaFold model_1_ptm parameters"
    )
    entry = attempt_dir / "afcycdesign_entry.py"
    entry.write_text(
        _entry_text(seed=seed, binder_len=minimum, target_name=target.name),
        encoding="utf-8",
    )
    entry.chmod(0o755)

    environment = execution.get("container_or_env", "")
    image, separator, conda_env = environment.partition("/")
    image = image or DEFAULT_IMAGE
    conda_env = conda_env if separator and conda_env else DEFAULT_ENV
    if image not in IMAGE_IDS:
        raise ValueError(f"unregistered ColabDesign image: {image}")
    image_id = IMAGE_IDS[image]
    inner = "\n".join(
        (
            "set -euo pipefail",
            "source /opt/conda/etc/profile.d/conda.sh",
            f"conda activate {shlex.quote(conda_env)}",
            "export PYTHONPATH=/data/source:${PYTHONPATH:-}",
            "python /data/attempt/afcycdesign_entry.py",
        )
    )
    mounts = (
        f"-v {shlex.quote(str(attempt_dir) + ':/data/attempt')}",
        f"-v {shlex.quote(str(SOURCE_ROOT) + ':/data/source:ro')}",
        f"-v {shlex.quote(str(PARAMS_ROOT) + ':/data/alphafold_params:ro')}",
        f"-v {shlex.quote(str(target) + ':/data/input/' + target.name + ':ro')}",
    )
    command_path = attempt_dir / "command.sh"
    command_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"observed_image_id=$(docker image inspect --format '{{{{.Id}}}}' {shlex.quote(image)})\n"
        f"test \"$observed_image_id\" = {shlex.quote(image_id)}\n"
        "docker run --rm --gpus all --shm-size 16g "
        f"-e V034_HOST_ATTEMPT={shlex.quote(str(attempt_dir))} "
        f"-e V034_CONTAINER_IMAGE={shlex.quote(image)} "
        f"-e V034_CONTAINER_IMAGE_ID={shlex.quote(image_id)} "
        + " ".join(mounts)
        + f" {shlex.quote(image)} bash -lc {shlex.quote(inner)}\n",
        encoding="utf-8",
    )
    command_path.chmod(0o755)
    return ["bash", str(command_path)]


def parse(job: Mapping[str, str], attempt_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    output = raw / "afcycdesign_candidate.pdb"
    if not output.is_file():
        raise FileNotFoundError(f"missing standard AfCycDesign candidate: {output}")
    validation = validate_output_file(output, raw)
    if validation["status"] != "pass":
        raise ValueError(f"invalid AfCycDesign candidate: {validation['reason']}")

    runtime_path = raw / "runtime_evidence.json"
    if not runtime_path.is_file():
        raise FileNotFoundError(f"missing standard AfCycDesign runtime evidence: {runtime_path}")
    runtime_value = json.loads(runtime_path.read_text(encoding="utf-8"))
    if not isinstance(runtime_value, dict):
        raise ValueError("AfCycDesign runtime evidence must be a JSON object")
    runtime: dict[str, Any] = runtime_value
    requested = int(job["random_seed"])
    if not (
        runtime.get("requested_seed") == requested
        and runtime.get("effective_seed") == requested
        and runtime.get("seed_control_status") == "honored"
    ):
        raise ValueError("AfCycDesign runtime seed evidence is invalid")
    if runtime.get("cyclic_offset_applied") is not True or runtime.get("cyclic_offset_type") != 2:
        raise ValueError("AfCycDesign cyclic offset evidence is invalid")
    try:
        terminal_offset = int(runtime.get("terminal_offset"))
    except (TypeError, ValueError) as exc:
        raise ValueError("AfCycDesign terminal_offset is invalid") from exc
    if abs(terminal_offset) != 1:
        raise ValueError("AfCycDesign terminal_offset must be +/-1")
    if runtime.get("candidate_path") != str(output):
        raise ValueError("candidate_path does not bind the standard raw path")
    if runtime.get("candidate_sha256") != validation["sha256"]:
        raise ValueError("candidate_sha256 does not match the standard raw file")
    provenance_ok = all(
        (
            runtime.get("source_commit") == SOURCE_COMMIT,
            runtime.get("source_notebook_sha256") == SOURCE_NOTEBOOK_SHA256,
            runtime.get("alphafold_model_name") == ALPHAFOLD_MODEL_NAME,
            runtime.get("alphafold_params_sha256") == ALPHAFOLD_PARAMS_SHA256,
            runtime.get("container_image") in IMAGE_IDS,
            IMAGE_IDS.get(str(runtime.get("container_image")))
            == runtime.get("container_image_id"),
        )
    )
    if not provenance_ok:
        raise ValueError("AfCycDesign source, model, or image provenance is invalid")

    sequences = parse_pdb_chain_sequences(output)
    target_chain = job.get("expected_target_chain", "A")
    binder_chain = job.get("expected_binder_chain", "B")
    sequence = sequences.get(binder_chain, "")
    if not sequence or target_chain not in sequences or target_chain == binder_chain:
        raise ValueError("AfCycDesign candidate does not contain target A and binder B")
    minimum = int(job.get("length_min", "14"))
    maximum = int(job.get("length_max", "14"))
    if not minimum <= len(sequence) <= maximum:
        raise ValueError("AfCycDesign binder length is outside the job contract")
    return _candidate(job, output, sequence), runtime
