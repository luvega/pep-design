from __future__ import annotations

import csv
import json
import shlex
from pathlib import Path
from typing import Any, Mapping

from .common import (
    CANONICAL_AA,
    require_clean_git_checkout,
    require_file_sha256,
    validate_output_file,
)


METHOD = "PepMLM"
SOURCE_COMMIT = "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436"
SOURCE_ROOT = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/pepmlm")
SOURCE_ENTRYPOINT = SOURCE_ROOT / "scripts/generation.py"
SOURCE_ENTRYPOINT_SHA256 = "2c1844028c459e8e96d756da795b620b4ccaa65b98dd62c6f904100f0dc1e49b"
MODEL_ID = "TianlaiChen/PepMLM-650M"
MODEL_REVISION = "898fca941a9057aebdd1a6164b5ee09a1a71780e"
MODEL_SNAPSHOT = Path(
    "/data/protein-design/data/benchmark_models/huggingface/hub/"
    "models--TianlaiChen--PepMLM-650M/snapshots/898fca941a9057aebdd1a6164b5ee09a1a71780e"
)
MODEL_WEIGHTS = MODEL_SNAPSHOT / "pytorch_model.bin"
MODEL_WEIGHTS_SHA256 = "8a3225bca1f9acd9f701ca2e46597c12bab92320e32b68f380ddf3b6d3b20770"
DEFAULT_IMAGE = "pd-benchmark-methods-gpu:0.21"
DEFAULT_ENV = "bench-pepmlm"
TOP_K = 3


def _runtime_evidence(job: Mapping[str, str], raw: Path) -> dict[str, Any]:
    requested = int(job.get("random_seed", "-1"))
    fallback: dict[str, Any] = {
        "requested_seed": requested,
        "effective_seed": -1,
        "seed_control_status": "missing",
    }
    path = raw / "runtime_evidence.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return fallback
    if not isinstance(value, dict):
        return fallback
    fallback.update(value)
    return fallback


def _failed(reason: str) -> dict[str, str]:
    return {
        "sequence": "",
        "structure_path": "",
        "source_output_path": "",
        "binder_chain": "not_applicable",
        "parse_status": "failed",
        "status_reason": reason,
    }


def prepare(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    attempt_dir: Path,
) -> list[str]:
    attempt_dir = Path(attempt_dir)
    raw = attempt_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    seed = int(job["random_seed"])
    mask_count = int(job.get("length_min", "3"))
    if mask_count <= 0 or mask_count != int(job.get("length_max", str(mask_count))):
        raise ValueError("PepMLM v0.34 requires one fixed positive peptide length")
    target_sequence = job.get("target_sequence", "").strip().upper()
    if not target_sequence:
        raise ValueError("PepMLM requires target_sequence")
    environment = execution.get("container_or_env", "")
    image, _, conda_env = environment.partition("/")
    image = image or DEFAULT_IMAGE
    conda_env = conda_env or DEFAULT_ENV
    source_commit = require_clean_git_checkout(SOURCE_ROOT, SOURCE_COMMIT, "PepMLM source")
    source_digest = require_file_sha256(
        SOURCE_ENTRYPOINT, SOURCE_ENTRYPOINT_SHA256, "PepMLM pinned generation source"
    )
    model_digest = require_file_sha256(
        MODEL_WEIGHTS, MODEL_WEIGHTS_SHA256, "PepMLM pinned model weights"
    )

    sampling = attempt_dir / "pepmlm_sampling.py"
    sampling.write_text(
        '''from __future__ import annotations

import torch


def sample_top_k(logits: torch.Tensor, *, seed: int, top_k: int) -> torch.Tensor:
    if logits.ndim != 2 or top_k <= 0 or top_k > logits.shape[-1]:
        raise ValueError("invalid top-k sampling contract")
    generator = torch.Generator(device=logits.device)
    generator.manual_seed(seed)
    top_logits, top_indices = logits.topk(top_k, dim=-1)
    probabilities = torch.nn.functional.softmax(top_logits, dim=-1)
    selected = torch.multinomial(probabilities, 1, generator=generator).squeeze(-1)
    return top_indices.gather(-1, selected.unsqueeze(-1)).squeeze(-1)
''',
        encoding="utf-8",
    )

    entry = attempt_dir / "pepmlm_entry.py"
    payload = json.dumps(
        {
            "job_id": job.get("job_id", ""),
            "target_id": job.get("target_id", ""),
            "target_sequence": target_sequence,
        },
        sort_keys=True,
    )
    entry.write_text(
        f'''#!/usr/bin/env python3
import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer
from pepmlm_sampling import sample_top_k

JOB = json.loads({json.dumps(payload)})
MASK_COUNT = {mask_count}
MODEL_ID = {json.dumps(MODEL_ID)}
MODEL_REVISION = {json.dumps(MODEL_REVISION)}
TOP_K = {TOP_K}
RAW = Path("/data/attempt/raw")

parser = argparse.ArgumentParser()
parser.add_argument("--seed", type=int, required=True)
parser.add_argument("--n-samples", type=int, choices=[1], required=True)
args = parser.parse_args()
SEED = args.seed

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

protein_sequence = JOB["target_sequence"].replace("X", "")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID, revision=MODEL_REVISION, local_files_only=True
)
model = AutoModelForMaskedLM.from_pretrained(
    MODEL_ID, revision=MODEL_REVISION, local_files_only=True
)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
model.eval()
masked_sequence = protein_sequence + tokenizer.mask_token * MASK_COUNT
inputs = tokenizer(masked_sequence, return_tensors="pt").to(device)
with torch.no_grad():
    logits = model(**inputs).logits
mask_positions = (inputs["input_ids"] == tokenizer.mask_token_id).nonzero(as_tuple=True)[1]
if mask_positions.numel() != MASK_COUNT:
    raise RuntimeError(f"expected {{MASK_COUNT}} mask positions, observed {{mask_positions.numel()}}")
tokens = sample_top_k(logits[0, mask_positions], seed=SEED, top_k=TOP_K)
peptide = tokenizer.decode(tokens, skip_special_tokens=True).replace(" ", "").upper()
if not peptide:
    raise RuntimeError("PepMLM returned an empty peptide")

with (RAW / "pepmlm_generated.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["job_id", "generated_binder", "binder_rank", "target_id"],
        lineterminator="\\n",
    )
    writer.writeheader()
    writer.writerow({{
        "job_id": JOB["job_id"],
        "generated_binder": peptide,
        "binder_rank": 1,
        "target_id": JOB["target_id"],
    }})
(RAW / "runtime_evidence.json").write_text(
    json.dumps({{
        "requested_seed": SEED,
        "effective_seed": SEED,
        "seed_control_status": "honored",
        "sampling_strategy": "top_k_categorical",
        "top_k": TOP_K,
        "source_commit": {json.dumps(source_commit)},
        "source_entrypoint_sha256": {json.dumps(source_digest)},
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_weights_sha256": {json.dumps(model_digest)},
        "container_image": {json.dumps(image)},
        "conda_environment": {json.dumps(conda_env)},
    }}, indent=2, sort_keys=True) + "\\n",
    encoding="utf-8",
)
''',
        encoding="utf-8",
    )
    entry.chmod(0o755)

    attempt_mount = f"{attempt_dir.resolve()}:/data/attempt"
    inner = (
        "set -euo pipefail; "
        "source /opt/conda/etc/profile.d/conda.sh; "
        f"conda activate {shlex.quote(conda_env)}; "
        f"python /data/attempt/pepmlm_entry.py --seed {seed} --n-samples 1"
    )
    command_path = attempt_dir / "command.sh"
    command_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "docker run --rm --gpus all --shm-size 16g "
                "-e HF_HOME=/data/benchmark_models/huggingface "
                "-e TRANSFORMERS_CACHE=/data/benchmark_models/huggingface "
                "-e TRANSFORMERS_OFFLINE=1 "
                f"-v {shlex.quote(attempt_mount)} "
                "-v /data/protein-design/data/benchmark_models:/data/benchmark_models:ro "
                f"{shlex.quote(image)} bash -lc {shlex.quote(inner)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    command_path.chmod(0o755)
    return ["bash", str(command_path)]


def parse(job: Mapping[str, str], attempt_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    raw = Path(attempt_dir) / "raw"
    runtime = _runtime_evidence(job, raw)
    output = raw / "pepmlm_generated.csv"
    if validate_output_file(output, raw)["status"] != "pass":
        return _failed("pepmlm_standard_output_missing"), runtime
    try:
        with output.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error):
        return _failed("pepmlm_standard_output_invalid"), runtime
    if len(rows) != 1:
        return _failed("pepmlm_standard_output_invalid"), runtime
    required = {"job_id", "generated_binder", "binder_rank", "target_id"}
    if not required.issubset(rows[0]):
        return _failed("pepmlm_output_contract_invalid"), runtime
    row = rows[0]
    if not (
        row.get("job_id") == job.get("job_id")
        and row.get("target_id") == job.get("target_id")
        and row.get("binder_rank") == "1"
    ):
        return _failed("pepmlm_output_contract_invalid"), runtime
    sequence = row.get("generated_binder", "").strip().upper()
    if not sequence or not sequence.isalpha():
        return _failed("pepmlm_sequence_invalid"), runtime
    noncanonical = {residue for residue in sequence if residue not in CANONICAL_AA}
    parse_status = "partial" if noncanonical else "parsed"
    reason = "pepmlm_noncanonical_residue" if noncanonical else "pepmlm_standard_output_parsed"
    return (
        {
            "sequence": sequence,
            "structure_path": "",
            "source_output_path": str(output),
            "binder_chain": "not_applicable",
            "parse_status": parse_status,
            "status_reason": reason,
        },
        runtime,
    )
