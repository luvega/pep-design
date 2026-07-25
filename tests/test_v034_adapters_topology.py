from __future__ import annotations

import importlib
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.v034_adapters.common import sha256_file


FORBIDDEN_COMMAND_TOKENS = (
    "wget",
    "curl",
    "pip install",
    "git clone",
    "score",
    "rank",
)


def _load(name: str):
    return importlib.import_module(f"scripts.v034_adapters.{name}")


def _atom(serial: int, residue: str, chain: str, residue_number: int) -> str:
    coordinate = float(serial % 1000)
    return (
        f"ATOM  {serial:5d}  CA  {residue:>3s} {chain}{residue_number:4d}    "
        f"{coordinate:8.3f}{0.0:8.3f}{0.0:8.3f}  1.00 20.00           C\n"
    )


def _write_complex(
    path: Path,
    *,
    target_start: int = 1,
    target_end: int = 1,
    binder_sequence: str,
) -> None:
    aa3 = {
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
    serial = 1
    lines: list[str] = []
    for residue_number in range(target_start, target_end + 1):
        lines.append(_atom(serial, "GLY", "A", residue_number))
        serial += 1
    for residue_number, residue in enumerate(binder_sequence, start=1):
        lines.append(_atom(serial, aa3[residue], "B", residue_number))
        serial += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines) + "END\n", encoding="utf-8")


def _colab_job(tmp_path: Path) -> dict[str, str]:
    common = importlib.import_module("scripts.v034_adapters.common")
    target = tmp_path / "7zkr_GABARAP.pdb"
    _write_complex(target, binder_sequence="A" * 14)
    return {
        "job_id": "v034_colabdesign_7zkr_seed42",
        "method": "AfCycDesign / ColabDesign cyclic peptide",
        "task_id": "T2_structure_peptide_binder",
        "target_id": "gabarap_7zkr_fixture",
        "target_pdb_path": str(target),
        "target_pdb_sha256": common.sha256_file(target),
        "random_seed": "42",
        "length_min": "14",
        "length_max": "14",
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
        "peptide_type": "cyclic",
        "chirality": "L",
        "cyclic": "yes",
    }


def _rf_job(tmp_path: Path) -> dict[str, str]:
    common = importlib.import_module("scripts.v034_adapters.common")
    target = tmp_path / "7zkr_GABARAP.pdb"
    _write_complex(target, target_start=3, target_end=117, binder_sequence="A" * 14)
    return {
        "job_id": "v034_rfdiffusion_mpnn_7zkr_seed42",
        "method": "RFdiffusion + ProteinMPNN",
        "task_id": "T3_miniprotein_binder_baseline",
        "target_id": "gabarap_7zkr_t3_fixture",
        "target_pdb_path": str(target),
        "target_pdb_sha256": common.sha256_file(target),
        "random_seed": "42",
        "length_min": "70",
        "length_max": "100",
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
        "peptide_type": "miniprotein",
        "chirality": "L",
        "cyclic": "no",
    }


def _assert_command_package(command: list[str], attempt: Path) -> str:
    command_path = attempt / "command.sh"
    assert command == ["bash", str(command_path)]
    assert command_path.stat().st_mode & 0o111
    command_text = command_path.read_text(encoding="utf-8")
    lowered = command_text.lower()
    assert all(token not in lowered for token in FORBIDDEN_COMMAND_TOKENS)
    assert (attempt / "raw").is_dir()
    return command_text


def _write_colab_runtime(attempt: Path, candidate: Path, *, terminal_offset: int = 1) -> dict[str, object]:
    runtime: dict[str, object] = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "cyclic_offset_applied": True,
        "cyclic_offset_type": 2,
        "terminal_offset": terminal_offset,
        "candidate_path": str(candidate),
        "candidate_sha256": sha256_file(candidate),
        "source_commit": "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
        "source_notebook_sha256": "ca3bd3cc14daa95e1529fd2d5c1ca18263d12341a75d2967715ec23720b129ed",
        "alphafold_model_name": "model_1_ptm",
        "alphafold_params_sha256": "5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84",
        "container_image": "pd-benchmark-methods-gpu:0.21",
        "container_image_id": "sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2",
    }
    (attempt / "raw/runtime_evidence.json").write_text(
        json.dumps(runtime), encoding="utf-8"
    )
    return runtime


def _write_rf_outputs(attempt: Path) -> tuple[dict[str, object], str]:
    raw = attempt / "raw"
    backbone = raw / "rf/design.pdb"
    _write_complex(
        backbone,
        target_start=3,
        target_end=117,
        binder_sequence="G" * 70,
    )
    trb = raw / "rf/design.trb"
    _write_rf_trb(trb)
    fasta = raw / "mpnn/design.fa"
    fasta.parent.mkdir(parents=True, exist_ok=True)
    generated_sequence = "A" * 70
    fasta.write_text(
        ">design_native, fixed_chains=['A'], designed_chains=['B'], seed=42\n"
        + "G" * 70
        + "\n>design_b0_d0, sample=1, seed=42\n"
        + generated_sequence
        + "\n",
        encoding="utf-8",
    )
    runtime: dict[str, object] = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "rf_design_startnum": 42,
        "rf_target_conditioned": True,
        "rf_contig": "[A3-117/0 70-100]",
        "rf_hotspots": ["A48", "A50", "A51", "A52", "A62", "A65"],
        "rf_cyclic": False,
        "rf_deterministic": True,
        "mpnn_seed": 42,
        "mpnn_designed_chain": "B",
        "mpnn_fixed_chains": ["A"],
        "rf_backbone_path": str(backbone),
        "rf_backbone_sha256": sha256_file(backbone),
        "rf_trb_path": str(trb),
        "rf_trb_sha256": sha256_file(trb),
        "mpnn_fasta_path": str(fasta),
        "mpnn_fasta_sha256": sha256_file(fasta),
        "mpnn_selected_record_id": "design_b0_d0",
        "mpnn_record_type": "generated_sample",
        "rf_source_commit": "2d0c003df46b9db41d119321f15403dec3716cd9",
        "rf_source_entrypoint_sha256": "a22624d7d40d3d207d91e92163441da5a778c867ed6ea85aa546cc9fdbeb2105",
        "rf_checkpoint_sha256": "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc",
        "mpnn_source_commit": "8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
        "mpnn_source_entrypoint_sha256": "61f2c519a7f73fa12da9eb90da97b97ec2f8d5f31d42605639c7600cbd321cbe",
        "mpnn_checkpoint_sha256": "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd",
        "rf_container_image": "pd-rfpeptide-gpu:fixed",
        "rf_container_image_id": "sha256:95e2a19e4adf4b6e8bcdd1777b609bf717472a91643dc92f0ce6aaffbc5219f1",
        "mpnn_container_image": "pd-foundry-gpu:latest",
        "mpnn_container_image_id": "sha256:23f8612f4537f90078d54a5ac9669df7a6d5f436a48740e5d2884cfe856a5be4",
    }
    (raw / "runtime_evidence.json").write_text(json.dumps(runtime), encoding="utf-8")
    return runtime, generated_sequence


def _write_rf_trb(
    path: Path,
    *,
    seed: int = 42,
    contig: str = "A3-117/0 70-100",
    hotspots: list[str] | None = None,
    binder_length: int = 70,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": {
            "inference": {
                "input_pdb": "/data/input/7zkr_GABARAP.pdb",
                "num_designs": 1,
                "design_startnum": seed,
                "deterministic": True,
                "cyclic": False,
            },
            "contigmap": {"contigs": [contig]},
            "ppi": {
                "hotspot_res": hotspots
                or ["A48", "A50", "A51", "A52", "A62", "A65"]
            },
        },
        "sampled_mask": ["A3-117/0", f"{binder_length}-{binder_length}"],
    }
    path.write_bytes(pickle.dumps(payload, protocol=4))


class _UnsafeTrbPayload:
    def __init__(self, marker: Path):
        self.marker = marker

    def __reduce__(self):
        return os.system, (f"touch {self.marker}",)


def test_topology_adapters_expose_pinned_identity_constants() -> None:
    colab = _load("colabdesign")
    rf = _load("rfdiffusion_mpnn")

    assert colab.METHOD == "AfCycDesign / ColabDesign cyclic peptide"
    assert colab.SOURCE_COMMIT == "e31a56fe1d9b4de25c8697f3a28b75892941cc72"
    assert "alphafold" in colab.MODEL_REVISION.lower()
    assert rf.METHOD == "RFdiffusion + ProteinMPNN"
    assert "2d0c003df46b9db41d119321f15403dec3716cd9" in rf.SOURCE_COMMIT
    assert "8907e6671bfbfc92303b5f79c4b5e6ce47cdef57" in rf.SOURCE_COMMIT
    assert "proteinmpnn_v_48_020.pt" in rf.MODEL_REVISION


def test_colabdesign_prepare_packages_notebook_equivalent_cyclic_offset(tmp_path: Path) -> None:
    module = _load("colabdesign")
    attempt = tmp_path / "attempt"

    text = _assert_command_package(
        module.prepare(
            _colab_job(tmp_path),
            {"container_or_env": "pd-benchmark-methods-gpu:0.21/bench-colabdesign"},
            attempt,
        ),
        attempt,
    )
    entry = (attempt / "afcycdesign_entry.py").read_text(encoding="utf-8")

    assert "pd-benchmark-methods-gpu:0.21" in text
    assert "conda activate bench-colabdesign" in text
    assert "/data/alphafold_params" in text
    assert "docker image inspect" in text
    assert "afcycdesign_entry.py" in text
    for required in (
        "def add_cyclic_offset(self, offset_type=2):",
        "c_offset[a] = -c_offset[a]",
        'offset[self._target_len:, self._target_len:] = c_offset',
        'protocol="binder"',
        'model_names=["model_1_ptm"]',
        'chain="A"',
        "binder_len=14",
        "model.set_seed(SEED)",
        "add_cyclic_offset(model, offset_type=2)",
        "model.design_logits(1)",
        'Path("/data/attempt/raw/afcycdesign_candidate.pdb")',
        '"cyclic_offset_applied": True',
        '"cyclic_offset_type": 2',
        '"seed_control_status": "honored"',
        '"alphafold_params_sha256"',
        '"container_image_id"',
    ):
        assert required in entry
    assert entry.index("add_cyclic_offset(model, offset_type=2)") < entry.index(
        "model.design_logits(1)"
    )


def test_colabdesign_parse_binds_standard_cyclic_candidate_and_runtime(tmp_path: Path) -> None:
    module = _load("colabdesign")
    attempt = tmp_path / "attempt"
    candidate_path = attempt / "raw/afcycdesign_candidate.pdb"
    sequence = "ACDEFGHIKLMNPQ"
    _write_complex(candidate_path, binder_sequence=sequence)
    runtime = _write_colab_runtime(attempt, candidate_path)

    candidate, observed = module.parse(_colab_job(tmp_path), attempt)

    assert candidate["sequence"] == sequence
    assert candidate["structure_path"] == str(candidate_path)
    assert candidate["source_output_path"] == str(candidate_path)
    assert candidate["binder_chain"] == "B"
    assert candidate["parse_status"] == "parsed"
    assert observed == runtime


def test_colabdesign_parse_rejects_noncyclic_or_nonstandard_output(tmp_path: Path) -> None:
    module = _load("colabdesign")
    attempt = tmp_path / "attempt"
    standard = attempt / "raw/afcycdesign_candidate.pdb"
    _write_complex(standard, binder_sequence="A" * 14)
    _write_colab_runtime(attempt, standard, terminal_offset=2)

    with pytest.raises(ValueError, match="terminal_offset"):
        module.parse(_colab_job(tmp_path), attempt)

    standard.unlink()
    stale = attempt / "raw/old/afcycdesign_candidate.pdb"
    _write_complex(stale, binder_sequence="A" * 14)
    _write_colab_runtime(attempt, stale)
    with pytest.raises(FileNotFoundError, match="raw/afcycdesign_candidate.pdb"):
        module.parse(_colab_job(tmp_path), attempt)


def test_rfdiffusion_mpnn_prepare_packages_exact_target_conditioned_handoff(tmp_path: Path) -> None:
    module = _load("rfdiffusion_mpnn")
    attempt = tmp_path / "attempt"

    text = _assert_command_package(
        module.prepare(
            _rf_job(tmp_path),
            {"container_or_env": "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest"},
            attempt,
        ),
        attempt,
    )

    assert text.index("pd-rfpeptide-gpu:fixed") < text.index("pd-foundry-gpu:latest")
    for required in (
        "7zkr_GABARAP.pdb",
        "contigmap.contigs=[A3-117/0 70-100]",
        "ppi.hotspot_res=[A48,A50,A51,A52,A62,A65]",
        "inference.cyclic=False",
        "inference.deterministic=True",
        "inference.design_startnum=42",
        "inference.num_designs=1",
        "inference.ckpt_override_path=/data/models/Complex_base_ckpt.pt",
        "inference.schedule_directory_path=/data/attempt/work/rf_schedules",
        "hydra.run.dir=/data/attempt/work/rf_hydra",
        "diffuser.T=50",
        "raw/rf/design.pdb",
        "raw/rf/design.trb",
        "--pdb_path_chains B",
        "--num_seq_per_target 1",
        "--seed 42",
        "raw/mpnn/design.fa",
        "finalize_runtime.py",
        "docker image inspect",
    ):
        assert required in text
    finalizer = (attempt / "finalize_runtime.py").read_text(encoding="utf-8")
    for required in (
        '"rf_contig": "[A3-117/0 70-100]"',
        '"rf_hotspots": HOTSPOTS',
        '"rf_cyclic": False',
        '"rf_deterministic": True',
        '"mpnn_designed_chain": "B"',
        '"mpnn_fixed_chains": ["A"]',
        '"mpnn_record_type": "generated_sample"',
        "rf_backbone_sha256",
        "rf_trb_sha256",
        "mpnn_fasta_sha256",
        '"rf_checkpoint_sha256"',
        '"mpnn_checkpoint_sha256"',
        '"rf_container_image_id"',
        '"mpnn_container_image_id"',
    ):
        assert required in finalizer


def test_rfdiffusion_finalizer_persists_safe_trb_semantic_binding(
    tmp_path: Path,
) -> None:
    module = _load("rfdiffusion_mpnn")
    attempt = tmp_path / "attempt"
    _write_rf_outputs(attempt)
    finalizer = attempt / "finalize_runtime.py"
    finalizer.write_text(
        module._finalizer_text(
            seed=42,
            attempt_dir=attempt,
            rf_image=module.DEFAULT_RF_IMAGE,
            mpnn_image=module.DEFAULT_MPNN_IMAGE,
        ),
        encoding="utf-8",
    )

    subprocess.run([sys.executable, str(finalizer)], check=True)

    runtime = json.loads(
        (attempt / "raw/runtime_evidence.json").read_text(encoding="utf-8")
    )
    assert runtime["structure_representation"] == "unthreaded_rf_backbone"
    assert runtime["sequence_representation"] == "proteinmpnn_generated_fasta"
    assert runtime["sequence_threaded_onto_backbone"] is False
    assert runtime["rf_trb_semantic_parser"] == "pickletools_literal_scan_v1"
    assert runtime["rf_trb_semantic_extract"]["design_startnum"] == 42
    assert runtime["rf_trb_semantic_extract"]["sampled_mask"] == [
        "A3-117/0",
        "70-70",
    ]
    assert len(runtime["rf_trb_semantic_sha256"]) == 64


@pytest.mark.parametrize(
    ("adapter_name", "job_factory"),
    [("colabdesign", _colab_job), ("rfdiffusion_mpnn", _rf_job)],
)
def test_topology_prepare_rejects_target_digest_mismatch(
    tmp_path: Path, adapter_name: str, job_factory
) -> None:
    module = _load(adapter_name)
    job = job_factory(tmp_path)
    job["target_pdb_sha256"] = "0" * 64
    execution = {
        "container_or_env": (
            "pd-benchmark-methods-gpu:0.21/bench-colabdesign"
            if adapter_name == "colabdesign"
            else "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest"
        )
    }

    with pytest.raises(ValueError, match="target.*SHA256 mismatch"):
        module.prepare(job, execution, tmp_path / "attempt")


def test_rfdiffusion_mpnn_parse_selects_generated_record_and_binds_three_files(
    tmp_path: Path,
) -> None:
    module = _load("rfdiffusion_mpnn")
    attempt = tmp_path / "attempt"
    runtime, generated_sequence = _write_rf_outputs(attempt)

    candidate, observed = module.parse(_rf_job(tmp_path), attempt)

    assert candidate["sequence"] == generated_sequence
    assert candidate["structure_path"] == str(attempt / "raw/rf/design.pdb")
    assert candidate["source_output_path"] == str(attempt / "raw/mpnn/design.fa")
    assert candidate["binder_chain"] == "B"
    assert candidate["source_output_id"] == "design.fa:design_b0_d0"
    assert candidate["parse_status"] == "parsed"
    assert candidate["notes"].endswith(
        "unthreaded RF backbone plus ProteinMPNN FASTA handoff"
    )
    assert observed["structure_representation"] == "unthreaded_rf_backbone"
    assert observed["sequence_representation"] == "proteinmpnn_generated_fasta"
    assert observed["sequence_threaded_onto_backbone"] is False
    assert observed["rf_trb_semantic_extract"]["design_startnum"] == 42
    assert observed["rf_trb_semantic_extract"]["sampled_mask"] == [
        "A3-117/0",
        "70-70",
    ]
    assert len(observed["rf_trb_semantic_sha256"]) == 64
    assert {
        key: value
        for key, value in observed.items()
        if key
        not in {
            "structure_representation",
            "sequence_representation",
            "sequence_threaded_onto_backbone",
            "rf_trb_semantic_extract",
            "rf_trb_semantic_sha256",
            "rf_trb_semantic_parser",
        }
    } == runtime
    assert observed["mpnn_selected_record_id"] == "design_b0_d0"
    assert observed["mpnn_record_type"] == "generated_sample"


def test_rfdiffusion_trb_semantic_extract_is_safe_and_deterministic(
    tmp_path: Path,
) -> None:
    module = _load("rfdiffusion_mpnn")
    trb = tmp_path / "design.trb"
    _write_rf_trb(trb)

    first = module.extract_rf_trb_semantics(trb)
    second = module.extract_rf_trb_semantics(trb)

    assert first == second == {
        "input_pdb": "/data/input/7zkr_GABARAP.pdb",
        "num_designs": 1,
        "design_startnum": 42,
        "deterministic": True,
        "cyclic": False,
        "contigs": ["A3-117/0 70-100"],
        "hotspot_res": ["A48", "A50", "A51", "A52", "A62", "A65"],
        "sampled_mask": ["A3-117/0", "70-70"],
    }

    marker = tmp_path / "unsafe_payload_executed"
    trb.write_bytes(pickle.dumps(_UnsafeTrbPayload(marker), protocol=4))
    with pytest.raises(ValueError, match="TRB semantic"):
        module.extract_rf_trb_semantics(trb)
    assert not marker.exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"seed": 43},
        {"contig": "A3-117/0 71-100"},
        {"hotspots": ["A48"]},
        {"binder_length": 71},
    ],
)
def test_rfdiffusion_mpnn_parse_rejects_hash_bound_wrong_trb_semantics(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    module = _load("rfdiffusion_mpnn")
    attempt = tmp_path / "attempt"
    runtime, _ = _write_rf_outputs(attempt)
    trb = attempt / "raw/rf/design.trb"
    _write_rf_trb(trb, **changes)
    runtime["rf_trb_sha256"] = sha256_file(trb)
    (attempt / "raw/runtime_evidence.json").write_text(
        json.dumps(runtime), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="TRB semantics"):
        module.parse(_rf_job(tmp_path), attempt)


def test_rfdiffusion_mpnn_parse_rejects_native_record_and_hash_mismatch(tmp_path: Path) -> None:
    module = _load("rfdiffusion_mpnn")
    attempt = tmp_path / "attempt"
    runtime, _ = _write_rf_outputs(attempt)
    runtime["mpnn_selected_record_id"] = "design_native"
    (attempt / "raw/runtime_evidence.json").write_text(
        json.dumps(runtime), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="generated ProteinMPNN record"):
        module.parse(_rf_job(tmp_path), attempt)

    runtime["mpnn_selected_record_id"] = "design_b0_d0"
    runtime["mpnn_fasta_sha256"] = "0" * 64
    (attempt / "raw/runtime_evidence.json").write_text(
        json.dumps(runtime), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="mpnn_fasta_sha256"):
        module.parse(_rf_job(tmp_path), attempt)


def test_rfdiffusion_mpnn_parse_binds_fixed_a_and_designed_b_to_fasta(tmp_path: Path) -> None:
    module = _load("rfdiffusion_mpnn")
    attempt = tmp_path / "attempt"
    runtime, _ = _write_rf_outputs(attempt)
    fasta = attempt / "raw/mpnn/design.fa"
    fasta.write_text(
        fasta.read_text(encoding="utf-8").replace(
            "fixed_chains=['A'], designed_chains=['B']",
            "fixed_chains=['B'], designed_chains=['A']",
        ),
        encoding="utf-8",
    )
    runtime["mpnn_fasta_sha256"] = sha256_file(fasta)
    (attempt / "raw/runtime_evidence.json").write_text(
        json.dumps(runtime), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="fixed A and designed B"):
        module.parse(_rf_job(tmp_path), attempt)


def test_rfdiffusion_mpnn_parse_does_not_scan_stale_handoff_outputs(tmp_path: Path) -> None:
    module = _load("rfdiffusion_mpnn")
    attempt = tmp_path / "attempt"
    stale = attempt / "raw/old"
    _write_complex(stale / "rf/design.pdb", binder_sequence="A" * 70)
    (stale / "rf/design.trb").write_bytes(b"stale\n")
    (stale / "mpnn").mkdir(parents=True)
    (stale / "mpnn/design.fa").write_text(
        ">design_b0_d0, sample=1\n" + "A" * 70 + "\n", encoding="utf-8"
    )
    (attempt / "raw").mkdir(parents=True, exist_ok=True)
    (attempt / "raw/runtime_evidence.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="raw/rf/design.pdb"):
        module.parse(_rf_job(tmp_path), attempt)
