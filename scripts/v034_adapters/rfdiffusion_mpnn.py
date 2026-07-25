from __future__ import annotations

import hashlib
import json
import pickletools
import re
import shlex
from pathlib import Path
from typing import Any, Mapping

from .common import (
    CANONICAL_AA,
    parse_pdb_chain_sequences,
    require_clean_git_checkout,
    require_file_sha256,
    validate_output_file,
)


METHOD = "RFdiffusion + ProteinMPNN"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RFDIFFUSION_COMMIT = "2d0c003df46b9db41d119321f15403dec3716cd9"
PROTEINMPNN_COMMIT = "8907e6671bfbfc92303b5f79c4b5e6ce47cdef57"
SOURCE_COMMIT = f"RFdiffusion@{RFDIFFUSION_COMMIT};ProteinMPNN@{PROTEINMPNN_COMMIT}"
MODEL_REVISION = "RFdiffusion_external_models;proteinmpnn_v_48_020.pt"

RFDIFFUSION_ROOT = Path(
    "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion"
)
PROTEINMPNN_ROOT = Path(
    "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ProteinMPNN"
)
RFDIFFUSION_MODELS = Path("/data/protein-design/data/rfpeptide_models")
RFDIFFUSION_ENTRYPOINT = RFDIFFUSION_ROOT / "scripts/run_inference.py"
RFDIFFUSION_ENTRYPOINT_SHA256 = "a22624d7d40d3d207d91e92163441da5a778c867ed6ea85aa546cc9fdbeb2105"
RFDIFFUSION_CHECKPOINT = RFDIFFUSION_MODELS / "Complex_base_ckpt.pt"
RFDIFFUSION_CHECKPOINT_SHA256 = "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc"
PROTEINMPNN_ENTRYPOINT = PROTEINMPNN_ROOT / "protein_mpnn_run.py"
PROTEINMPNN_ENTRYPOINT_SHA256 = "61f2c519a7f73fa12da9eb90da97b97ec2f8d5f31d42605639c7600cbd321cbe"
PROTEINMPNN_CHECKPOINT = Path(
    "/data/protein-design/data/foundry_checkpoints/proteinmpnn_v_48_020.pt"
)
PROTEINMPNN_CHECKPOINT_SHA256 = "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd"
DEFAULT_RF_IMAGE = "pd-rfpeptide-gpu:fixed"
DEFAULT_MPNN_IMAGE = "pd-foundry-gpu:latest"
IMAGE_IDS = {
    DEFAULT_RF_IMAGE: "sha256:95e2a19e4adf4b6e8bcdd1777b609bf717472a91643dc92f0ce6aaffbc5219f1",
    DEFAULT_MPNN_IMAGE: "sha256:23f8612f4537f90078d54a5ac9669df7a6d5f436a48740e5d2884cfe856a5be4",
}

RF_CONTIG = "[A3-117/0 70-100]"
RF_HOTSPOTS = ("A48", "A50", "A51", "A52", "A62", "A65")
RF_TRB_SEMANTIC_PARSER = "pickletools_literal_scan_v1"
RF_TRB_MAX_BYTES = 8 * 1024 * 1024


def _trb_key_index(
    operations: list[tuple[pickletools.OpcodeInfo, Any, int]], key: str
) -> int:
    matches = [
        index
        for index, (_, argument, _) in enumerate(operations)
        if isinstance(argument, str) and argument == key
    ]
    if len(matches) != 1:
        raise ValueError(f"RF TRB semantic key {key!r} must occur exactly once")
    return matches[0]


def _skip_memo_writes(
    operations: list[tuple[pickletools.OpcodeInfo, Any, int]], index: int
) -> int:
    while index < len(operations) and operations[index][0].name in {
        "MEMOIZE",
        "BINPUT",
        "LONG_BINPUT",
        "PUT",
    }:
        index += 1
    return index


def _trb_scalar(
    operations: list[tuple[pickletools.OpcodeInfo, Any, int]], key: str
) -> Any:
    index = _skip_memo_writes(operations, _trb_key_index(operations, key) + 1)
    if index >= len(operations):
        raise ValueError(f"RF TRB semantic key {key!r} has no value")
    operation, argument, _ = operations[index]
    if operation.name == "NEWTRUE":
        return True
    if operation.name == "NEWFALSE":
        return False
    if operation.name == "NONE":
        return None
    if operation.name in {
        "INT",
        "BININT",
        "BININT1",
        "BININT2",
        "LONG",
        "LONG1",
        "LONG4",
    } and isinstance(argument, int):
        return argument
    if operation.name in {
        "UNICODE",
        "BINUNICODE",
        "SHORT_BINUNICODE",
        "BINUNICODE8",
    } and isinstance(argument, str):
        return argument
    raise ValueError(f"RF TRB semantic key {key!r} is not a primitive scalar")


def _trb_string_list(
    operations: list[tuple[pickletools.OpcodeInfo, Any, int]], key: str
) -> list[str]:
    index = _skip_memo_writes(operations, _trb_key_index(operations, key) + 1)
    if index >= len(operations) or operations[index][0].name != "EMPTY_LIST":
        raise ValueError(f"RF TRB semantic key {key!r} is not a list")
    index = _skip_memo_writes(operations, index + 1)
    if index < len(operations) and operations[index][0].name == "MARK":
        index += 1
    values: list[str] = []
    while index < len(operations):
        operation, argument, _ = operations[index]
        if operation.name in {"MEMOIZE", "BINPUT", "LONG_BINPUT", "PUT"}:
            index += 1
            continue
        if operation.name in {"APPEND", "APPENDS"}:
            if not values:
                raise ValueError(f"RF TRB semantic key {key!r} is empty")
            return values
        if operation.name in {
            "UNICODE",
            "BINUNICODE",
            "SHORT_BINUNICODE",
            "BINUNICODE8",
        } and isinstance(argument, str):
            values.append(argument)
            index += 1
            continue
        raise ValueError(f"RF TRB semantic key {key!r} is not a string list")
    raise ValueError(f"RF TRB semantic key {key!r} is incomplete")


def extract_rf_trb_semantics(path: Path) -> dict[str, Any]:
    """Extract the bounded RF contract from pickle opcodes without unpickling."""

    path = Path(path)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"RF TRB semantic evidence is unreadable: {path}") from exc
    if not payload or len(payload) > RF_TRB_MAX_BYTES:
        raise ValueError("RF TRB semantic evidence has an invalid size")
    try:
        operations = list(pickletools.genops(payload))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("RF TRB semantic evidence is not a valid pickle stream") from exc
    if (
        not operations
        or operations[-1][0].name != "STOP"
        or operations[-1][2] != len(payload) - 1
    ):
        raise ValueError("RF TRB semantic evidence is incomplete or has trailing data")
    try:
        return {
            "input_pdb": _trb_scalar(operations, "input_pdb"),
            "num_designs": _trb_scalar(operations, "num_designs"),
            "design_startnum": _trb_scalar(operations, "design_startnum"),
            "deterministic": _trb_scalar(operations, "deterministic"),
            "cyclic": _trb_scalar(operations, "cyclic"),
            "contigs": _trb_string_list(operations, "contigs"),
            "hotspot_res": _trb_string_list(operations, "hotspot_res"),
            "sampled_mask": _trb_string_list(operations, "sampled_mask"),
        }
    except ValueError as exc:
        raise ValueError(f"RF TRB semantic extraction failed: {exc}") from exc


def rf_trb_semantic_sha256(semantics: Mapping[str, Any]) -> str:
    payload = json.dumps(
        dict(semantics), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def bind_rf_trb_semantics(
    runtime: dict[str, Any], trb: Path, *, seed: int, binder_length: int
) -> None:
    semantics = extract_rf_trb_semantics(trb)
    expected = {
        "input_pdb": "/data/input/7zkr_GABARAP.pdb",
        "num_designs": 1,
        "design_startnum": seed,
        "deterministic": True,
        "cyclic": False,
        "contigs": [RF_CONTIG.removeprefix("[").removesuffix("]")],
        "hotspot_res": list(RF_HOTSPOTS),
        "sampled_mask": ["A3-117/0", f"{binder_length}-{binder_length}"],
    }
    if semantics != expected:
        raise ValueError(
            f"RF TRB semantics do not match the job contract: {semantics!r}"
        )
    runtime.update(
        structure_representation="unthreaded_rf_backbone",
        sequence_representation="proteinmpnn_generated_fasta",
        sequence_threaded_onto_backbone=False,
        rf_trb_semantic_parser=RF_TRB_SEMANTIC_PARSER,
        rf_trb_semantic_extract=semantics,
        rf_trb_semantic_sha256=rf_trb_semantic_sha256(semantics),
    )


def _fasta_records(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header = ""
    sequence: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            if header:
                records.append((header, "".join(sequence).upper()))
            header = stripped[1:]
            sequence = []
        elif header:
            sequence.append(stripped)
    if header:
        records.append((header, "".join(sequence).upper()))
    return records


def _record_id(header: str) -> str:
    return header.split(",", 1)[0].split()[0]


def _is_generated(header: str) -> bool:
    identifier = _record_id(header)
    return (
        "sample=" in header
        or " T=" in f" {header}"
        or re.search(r"_b\d+_d\d+$", identifier) is not None
    )


def _native_chain_seed_matches(records: list[tuple[str, str]], seed: int) -> bool:
    native_headers = [header for header, _ in records if not _is_generated(header)]
    if len(native_headers) != 1:
        return False
    compact = native_headers[0].replace(" ", "")
    fixed_a = "fixed_chains=['A']" in compact or 'fixed_chains=["A"]' in compact
    designed_b = "designed_chains=['B']" in compact or 'designed_chains=["B"]' in compact
    seed_match = re.search(r"(?:^|,)seed=(\d+)(?:,|$)", compact)
    return fixed_a and designed_b and seed_match is not None and int(seed_match.group(1)) == seed


def _finalizer_text(*, seed: int, attempt_dir: Path, rf_image: str, mpnn_image: str) -> str:
    return f'''#!/usr/bin/env python3
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, {str(PROJECT_ROOT)!r})
from scripts.v034_adapters.rfdiffusion_mpnn import bind_rf_trb_semantics

SEED = {seed}
HOTSPOTS = {list(RF_HOTSPOTS)!r}
RAW = Path({str(attempt_dir / "raw")!r})
BACKBONE = RAW / "rf/design.pdb"
TRB = RAW / "rf/design.trb"
FASTA = RAW / "mpnn/design.fa"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fasta_records(path):
    records = []
    header = ""
    sequence = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            if header:
                records.append((header, "".join(sequence).upper()))
            header = stripped[1:]
            sequence = []
        elif header:
            sequence.append(stripped)
    if header:
        records.append((header, "".join(sequence).upper()))
    return records


def record_id(header):
    return header.split(",", 1)[0].split()[0]


def is_generated(header):
    identifier = record_id(header)
    return (
        "sample=" in header
        or " T=" in f" {{header}}"
        or re.search(r"_b\\d+_d\\d+$", identifier) is not None
    )


def native_chain_seed_matches(records):
    native_headers = [header for header, _ in records if not is_generated(header)]
    if len(native_headers) != 1:
        return False
    compact = native_headers[0].replace(" ", "")
    fixed_a = "fixed_chains=['A']" in compact or 'fixed_chains=["A"]' in compact
    designed_b = "designed_chains=['B']" in compact or 'designed_chains=["B"]' in compact
    seed_match = re.search(r"(?:^|,)seed=(\\d+)(?:,|$)", compact)
    return fixed_a and designed_b and seed_match is not None and int(seed_match.group(1)) == SEED


for path in (BACKBONE, TRB, FASTA):
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
records = fasta_records(FASTA)
if not native_chain_seed_matches(records):
    raise RuntimeError("ProteinMPNN FASTA does not bind fixed A, designed B, and the requested seed")
generated = [(header, sequence) for header, sequence in records if is_generated(header)]
if len(generated) != 1:
    raise RuntimeError(f"expected one generated ProteinMPNN record, observed {{len(generated)}}")
selected_header, selected_sequence = generated[0]
if not selected_sequence or "/" in selected_sequence:
    raise RuntimeError("generated ProteinMPNN record is not a single designed chain")

semantic_binding = {{}}
bind_rf_trb_semantics(
    semantic_binding,
    TRB,
    seed=SEED,
    binder_length=len(selected_sequence),
)

payload = {{
    "requested_seed": SEED,
    "effective_seed": SEED,
    "seed_control_status": "honored",
    "rf_design_startnum": SEED,
    "rf_target_conditioned": True,
    "rf_contig": "[A3-117/0 70-100]",
    "rf_hotspots": HOTSPOTS,
    "rf_cyclic": False,
    "rf_deterministic": True,
    "mpnn_seed": SEED,
    "mpnn_designed_chain": "B",
    "mpnn_fixed_chains": ["A"],
    "mpnn_selected_record_id": record_id(selected_header),
    "mpnn_record_type": "generated_sample",
    "rf_source_commit": "{RFDIFFUSION_COMMIT}",
    "rf_source_entrypoint_sha256": "{RFDIFFUSION_ENTRYPOINT_SHA256}",
    "rf_checkpoint_sha256": "{RFDIFFUSION_CHECKPOINT_SHA256}",
    "mpnn_source_commit": "{PROTEINMPNN_COMMIT}",
    "mpnn_source_entrypoint_sha256": "{PROTEINMPNN_ENTRYPOINT_SHA256}",
    "mpnn_checkpoint_sha256": "{PROTEINMPNN_CHECKPOINT_SHA256}",
    "rf_container_image": "{rf_image}",
    "rf_container_image_id": "{IMAGE_IDS[rf_image]}",
    "mpnn_container_image": "{mpnn_image}",
    "mpnn_container_image_id": "{IMAGE_IDS[mpnn_image]}",
    "rf_backbone_path": str(BACKBONE),
    "rf_backbone_sha256": digest(BACKBONE),
    "rf_trb_path": str(TRB),
    "rf_trb_sha256": digest(TRB),
    "mpnn_fasta_path": str(FASTA),
    "mpnn_fasta_sha256": digest(FASTA),
}}
payload.update(semantic_binding)
(RAW / "runtime_evidence.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\\n",
    encoding="utf-8",
)
'''


def _candidate(
    job: Mapping[str, str], backbone: Path, fasta: Path, record_id: str, sequence: str
) -> dict[str, str]:
    job_id = job.get("job_id", "")
    return {
        "design_id": f"{job_id}_candidate_1",
        "job_id": job_id,
        "method": METHOD,
        "target_id": job.get("target_id", ""),
        "binder_id": f"{job_id}_binder_1",
        "source_output_id": f"{fasta.name}:{record_id}",
        "generation_rank": "1",
        "sequence": sequence,
        "structure_path": str(backbone),
        "source_output_path": str(fasta),
        "peptide_type": job.get("peptide_type", "miniprotein"),
        "chirality": job.get("chirality", "L"),
        "cyclic": job.get("cyclic", "no"),
        "binder_chain": job.get("expected_binder_chain", "B"),
        "parse_status": "parsed",
        "status_reason": "v034_rf_to_mpnn_generated_handoff_parsed",
        "notes": (
            "Bounded connectivity evidence only; not Benchmark result or scoring evidence; "
            "unthreaded RF backbone plus ProteinMPNN FASTA handoff"
        ),
    }


def _images(execution: Mapping[str, str]) -> tuple[str, str]:
    configured = execution.get("container_or_env", "")
    parts = [part.strip() for part in configured.split("+") if part.strip()]
    if len(parts) == 2:
        return parts[0], parts[1]
    return DEFAULT_RF_IMAGE, DEFAULT_MPNN_IMAGE


def prepare(
    job: Mapping[str, str],
    execution: Mapping[str, str],
    attempt_dir: Path,
) -> list[str]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    if job.get("expected_target_chain", "A") != "A":
        raise ValueError("RFdiffusion v0.34 requires target chain A")
    if job.get("expected_binder_chain", "B") != "B" or job.get("cyclic", "no") != "no":
        raise ValueError("RFdiffusion v0.34 requires noncyclic binder chain B")
    if int(job.get("length_min", "70")) != 70 or int(job.get("length_max", "100")) != 100:
        raise ValueError("RFdiffusion v0.34 requires binder length range 70-100")

    seed = int(job["random_seed"])
    target = Path(job["target_pdb_path"]).resolve()
    require_file_sha256(target, job.get("target_pdb_sha256", ""), "RFdiffusion target")
    require_clean_git_checkout(
        RFDIFFUSION_ROOT, RFDIFFUSION_COMMIT, "RFdiffusion source"
    )
    require_clean_git_checkout(
        PROTEINMPNN_ROOT, PROTEINMPNN_COMMIT, "ProteinMPNN source"
    )
    require_file_sha256(
        RFDIFFUSION_ENTRYPOINT,
        RFDIFFUSION_ENTRYPOINT_SHA256,
        "RFdiffusion inference source",
    )
    require_file_sha256(
        PROTEINMPNN_ENTRYPOINT,
        PROTEINMPNN_ENTRYPOINT_SHA256,
        "ProteinMPNN inference source",
    )
    require_file_sha256(
        RFDIFFUSION_CHECKPOINT,
        RFDIFFUSION_CHECKPOINT_SHA256,
        "RFdiffusion Complex checkpoint",
    )
    require_file_sha256(
        PROTEINMPNN_CHECKPOINT,
        PROTEINMPNN_CHECKPOINT_SHA256,
        "ProteinMPNN checkpoint",
    )
    rf_image, mpnn_image = _images(execution)
    if rf_image not in IMAGE_IDS or mpnn_image not in IMAGE_IDS:
        raise ValueError("unregistered RFdiffusion or ProteinMPNN image")
    finalizer = attempt_dir / "finalize_runtime.py"
    finalizer.write_text(
        _finalizer_text(
            seed=seed,
            attempt_dir=attempt_dir,
            rf_image=rf_image,
            mpnn_image=mpnn_image,
        ),
        encoding="utf-8",
    )
    finalizer.chmod(0o755)

    rf_inner = "\n".join(
        (
            "set -euo pipefail",
            "source /opt/conda/etc/profile.d/conda.sh",
            "conda activate SE3cuda",
            "rm -rf /data/attempt/raw/rf",
            "mkdir -p /data/attempt/raw/rf/native",
            "cd /opt/RFdiffusion",
            "PYTHONPATH=/opt/RFdiffusion python scripts/run_inference.py "
            "inference.input_pdb=/data/input/7zkr_GABARAP.pdb "
            "inference.output_prefix=/data/attempt/raw/rf/native/design "
            f"'contigmap.contigs={RF_CONTIG}' "
            f"'ppi.hotspot_res=[{','.join(RF_HOTSPOTS)}]' "
            "inference.cyclic=False inference.deterministic=True "
            f"inference.design_startnum={seed} inference.num_designs=1 "
            "inference.write_trajectory=False diffuser.T=50 "
            "inference.model_directory_path=/data/models "
            "inference.ckpt_override_path=/data/models/Complex_base_ckpt.pt "
            "inference.schedule_directory_path=/data/attempt/work/rf_schedules "
            "hydra.run.dir=/data/attempt/work/rf_hydra",
            f"test -s /data/attempt/raw/rf/native/design_{seed}.pdb",
            f"test -s /data/attempt/raw/rf/native/design_{seed}.trb",
            f"mv -- /data/attempt/raw/rf/native/design_{seed}.pdb /data/attempt/raw/rf/design.pdb",
            f"mv -- /data/attempt/raw/rf/native/design_{seed}.trb /data/attempt/raw/rf/design.trb",
        )
    )
    rf_mounts = (
        f"-v {shlex.quote(str(attempt_dir) + ':/data/attempt')}",
        f"-v {shlex.quote(str(target) + ':/data/input/7zkr_GABARAP.pdb:ro')}",
        f"-v {shlex.quote(str(RFDIFFUSION_ROOT) + ':/opt/RFdiffusion:ro')}",
        f"-v {shlex.quote(str(RFDIFFUSION_MODELS) + ':/data/models:ro')}",
    )

    mpnn_inner = "\n".join(
        (
            "set -euo pipefail",
            "rm -rf /data/attempt/raw/mpnn",
            "mkdir -p /data/attempt/raw/mpnn/native",
            "/opt/conda/bin/conda run -n foundry python /opt/ProteinMPNN/protein_mpnn_run.py "
            "--pdb_path /data/attempt/raw/rf/design.pdb "
            "--pdb_path_chains B "
            "--out_folder /data/attempt/raw/mpnn/native "
            "--path_to_model_weights /data/model_weights "
            "--model_name v_48_020 "
            "--num_seq_per_target 1 --sampling_temp 0.1 "
            f"--seed {seed} --batch_size 1",
            "test -s /data/attempt/raw/mpnn/native/seqs/design.fa",
            "cp -- /data/attempt/raw/mpnn/native/seqs/design.fa /data/attempt/raw/mpnn/design.fa",
        )
    )
    mpnn_mounts = (
        f"-v {shlex.quote(str(attempt_dir) + ':/data/attempt')}",
        f"-v {shlex.quote(str(PROTEINMPNN_ROOT) + ':/opt/ProteinMPNN:ro')}",
        f"-v {shlex.quote(str(PROTEINMPNN_CHECKPOINT) + ':/data/model_weights/v_48_020.pt:ro')}",
    )

    command_path = attempt_dir / "command.sh"
    command_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"mkdir -p {shlex.quote(str(attempt_dir / 'work/rf_schedules'))} "
        f"{shlex.quote(str(attempt_dir / 'work/rf_hydra'))}\n"
        f"rf_image_id=$(docker image inspect --format '{{{{.Id}}}}' {shlex.quote(rf_image)})\n"
        f"test \"$rf_image_id\" = {shlex.quote(IMAGE_IDS[rf_image])}\n"
        f"mpnn_image_id=$(docker image inspect --format '{{{{.Id}}}}' {shlex.quote(mpnn_image)})\n"
        f"test \"$mpnn_image_id\" = {shlex.quote(IMAGE_IDS[mpnn_image])}\n"
        "docker run --rm --gpus all --shm-size 16g "
        + " ".join(rf_mounts)
        + f" {shlex.quote(rf_image)} bash -lc {shlex.quote(rf_inner)}\n"
        "docker run --rm --gpus all --shm-size 8g "
        + " ".join(mpnn_mounts)
        + f" {shlex.quote(mpnn_image)} bash -lc {shlex.quote(mpnn_inner)}\n"
        f"python {shlex.quote(str(finalizer))}\n",
        encoding="utf-8",
    )
    command_path.chmod(0o755)
    return ["bash", str(command_path)]


def _bind_runtime_file(
    runtime: Mapping[str, Any], raw: Path, name: str, path: Path
) -> None:
    path_key = f"{name}_path"
    digest_key = f"{name}_sha256"
    if runtime.get(path_key) != str(path):
        raise ValueError(f"{path_key} does not bind the standard raw path")
    validation = validate_output_file(path, raw)
    if validation["status"] != "pass":
        raise ValueError(f"invalid {name}: {validation['reason']}")
    if runtime.get(digest_key) != validation["sha256"]:
        raise ValueError(f"{digest_key} does not match the standard raw file")


def parse(job: Mapping[str, str], attempt_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    attempt_dir = Path(attempt_dir).resolve()
    raw = attempt_dir / "raw"
    backbone = raw / "rf/design.pdb"
    trb = raw / "rf/design.trb"
    fasta = raw / "mpnn/design.fa"
    for path in (backbone, trb, fasta):
        if not path.is_file():
            raise FileNotFoundError(f"missing standard RFdiffusion/ProteinMPNN output: {path}")

    runtime_path = raw / "runtime_evidence.json"
    if not runtime_path.is_file():
        raise FileNotFoundError(f"missing standard RFdiffusion/ProteinMPNN runtime: {runtime_path}")
    runtime_value = json.loads(runtime_path.read_text(encoding="utf-8"))
    if not isinstance(runtime_value, dict):
        raise ValueError("RFdiffusion/ProteinMPNN runtime evidence must be a JSON object")
    runtime: dict[str, Any] = runtime_value

    requested = int(job["random_seed"])
    contract_ok = (
        runtime.get("requested_seed") == requested
        and runtime.get("effective_seed") == requested
        and runtime.get("seed_control_status") == "honored"
        and runtime.get("rf_design_startnum") == requested
        and runtime.get("mpnn_seed") == requested
        and runtime.get("rf_target_conditioned") is True
        and runtime.get("rf_contig") == RF_CONTIG
        and runtime.get("rf_hotspots") == list(RF_HOTSPOTS)
        and runtime.get("rf_cyclic") is False
        and runtime.get("rf_deterministic") is True
        and runtime.get("mpnn_designed_chain") == "B"
        and runtime.get("mpnn_fixed_chains") == ["A"]
    )
    if not contract_ok:
        raise ValueError("RFdiffusion/ProteinMPNN target, chain, or seed runtime evidence is invalid")
    provenance_ok = all(
        (
            runtime.get("rf_source_commit") == RFDIFFUSION_COMMIT,
            runtime.get("rf_source_entrypoint_sha256")
            == RFDIFFUSION_ENTRYPOINT_SHA256,
            runtime.get("rf_checkpoint_sha256") == RFDIFFUSION_CHECKPOINT_SHA256,
            runtime.get("mpnn_source_commit") == PROTEINMPNN_COMMIT,
            runtime.get("mpnn_source_entrypoint_sha256")
            == PROTEINMPNN_ENTRYPOINT_SHA256,
            runtime.get("mpnn_checkpoint_sha256") == PROTEINMPNN_CHECKPOINT_SHA256,
            runtime.get("rf_container_image") in IMAGE_IDS,
            IMAGE_IDS.get(str(runtime.get("rf_container_image")))
            == runtime.get("rf_container_image_id"),
            runtime.get("mpnn_container_image") in IMAGE_IDS,
            IMAGE_IDS.get(str(runtime.get("mpnn_container_image")))
            == runtime.get("mpnn_container_image_id"),
        )
    )
    if not provenance_ok:
        raise ValueError("RFdiffusion/ProteinMPNN source, model, or image provenance is invalid")

    _bind_runtime_file(runtime, raw, "rf_backbone", backbone)
    _bind_runtime_file(runtime, raw, "rf_trb", trb)
    _bind_runtime_file(runtime, raw, "mpnn_fasta", fasta)

    records = _fasta_records(fasta)
    if not _native_chain_seed_matches(records, requested):
        raise ValueError("ProteinMPNN FASTA does not bind fixed A and designed B to the requested seed")
    selected_id = str(runtime.get("mpnn_selected_record_id", ""))
    matching = [
        (header, sequence)
        for header, sequence in records
        if _record_id(header) == selected_id
    ]
    if (
        len(matching) != 1
        or not _is_generated(matching[0][0])
        or runtime.get("mpnn_record_type") != "generated_sample"
    ):
        raise ValueError("runtime does not select an explicit generated ProteinMPNN record")
    sequence = matching[0][1]
    if not sequence or "/" in sequence or any(residue not in CANONICAL_AA for residue in sequence):
        raise ValueError("generated ProteinMPNN record is not one canonical designed chain")
    minimum = int(job.get("length_min", "70"))
    maximum = int(job.get("length_max", "100"))
    if not minimum <= len(sequence) <= maximum:
        raise ValueError("generated ProteinMPNN binder length is outside the job contract")

    bind_rf_trb_semantics(runtime, trb, seed=requested, binder_length=len(sequence))

    chains = parse_pdb_chain_sequences(backbone)
    target_chain = job.get("expected_target_chain", "A")
    binder_chain = job.get("expected_binder_chain", "B")
    if target_chain not in chains or binder_chain not in chains or target_chain == binder_chain:
        raise ValueError("RFdiffusion backbone does not contain target A and binder B")
    return _candidate(job, backbone, fasta, selected_id, sequence), runtime
