#!/usr/bin/env python
"""Parse v0.15 Batch A smoke outputs into small replay fixture tables."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_ROOT = Path("/data/protein-design/data/outputs/benchmark_v0.15/batch_a")
RESULT_ROOT = ROOT / "benchmark/results"

METHOD_OUTPUT_HEADERS = [
    "run_record_id",
    "job_id",
    "method",
    "task_id",
    "execution_stage",
    "source_commit",
    "model_revision",
    "environment_id",
    "command",
    "raw_output_root",
    "stdout_log",
    "stderr_log",
    "runtime_seconds",
    "exit_code",
    "parser_status",
    "status_reason",
    "created_at",
]

CANDIDATE_HEADERS = [
    "design_id",
    "job_id",
    "method",
    "target_id",
    "binder_id",
    "source_output_id",
    "generation_rank",
    "sequence",
    "structure_path",
    "peptide_type",
    "chirality",
    "cyclic",
    "parse_status",
    "status_reason",
    "notes",
]

RUN_HEADERS = [
    "design_id",
    "method",
    "task_id",
    "target_id",
    "binder_id",
    "input_mode",
    "target_sequence",
    "target_pdb",
    "target_chains",
    "binder_chain",
    "pocket_definition",
    "peptide_type",
    "chirality",
    "cyclic",
    "status",
    "notes",
]

AA3_TO_1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


def read_runtime(method_dir: Path) -> dict[str, object]:
    return json.loads((method_dir / "runtime.json").read_text(encoding="utf-8"))


def read_command(method_dir: Path) -> str:
    command = (method_dir / "command.sh").read_text(encoding="utf-8").strip()
    return " ".join(command.split())


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def parse_fasta(path: Path) -> tuple[str, str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    header = lines[0].lstrip(">")
    sequence = "".join(lines[1:])
    return header, sequence


def parse_pdb_sequence(path: Path, chain_id: str = "A") -> str:
    residues: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("ATOM"):
            continue
        if line[21].strip() != chain_id:
            continue
        key = (line[21].strip(), line[22:26].strip())
        if key in seen:
            continue
        seen.add(key)
        residues.append((line[17:20].strip(), line[22:26].strip()))
    return "".join(AA3_TO_1.get(resname, "X") for resname, _ in residues)


def method_output_row(
    *,
    method_dir: Path,
    run_record_id: str,
    job_id: str,
    method: str,
    task_id: str,
    model_revision: str,
    environment_id: str,
    parser_status: str,
    status_reason: str,
) -> dict[str, object]:
    runtime = read_runtime(method_dir)
    return {
        "run_record_id": run_record_id,
        "job_id": job_id,
        "method": method,
        "task_id": task_id,
        "execution_stage": "v0.15_minimal_smoke_replay_fixture",
        "source_commit": runtime.get("source_commit", ""),
        "model_revision": model_revision,
        "environment_id": environment_id,
        "command": read_command(method_dir),
        "raw_output_root": str(method_dir),
        "stdout_log": str(method_dir / "stdout.log"),
        "stderr_log": str(method_dir / "stderr.log"),
        "runtime_seconds": runtime.get("duration_seconds", ""),
        "exit_code": runtime.get("exit_code", ""),
        "parser_status": parser_status,
        "status_reason": status_reason,
        "created_at": runtime.get("end", ""),
    }


def build_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    method_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []

    pepmlm_dir = EXTERNAL_ROOT / "pepmlm_cpu_smoke"
    with (pepmlm_dir / "output/pepmlm_generated.csv").open(newline="", encoding="utf-8") as handle:
        pepmlm_record = next(csv.DictReader(handle))
    with (pepmlm_dir / "input.csv").open(newline="", encoding="utf-8") as handle:
        pepmlm_input = next(csv.DictReader(handle))
    pepmlm_sequence = pepmlm_record["generated_binder"]
    pepmlm_status = "partial" if "X" in pepmlm_sequence else "parsed"
    pepmlm_reason = "contains_noncanonical_X_from_smoke_output" if "X" in pepmlm_sequence else "parsed"
    method_rows.append(
        method_output_row(
            method_dir=pepmlm_dir,
            run_record_id="batch_a_pepmlm_cpu_smoke_replay",
            job_id="batch_a_pepmlm_cpu_smoke_replay",
            method="PepMLM",
            task_id="T1_sequence_binder",
            model_revision="TianlaiChen/PepMLM-650M",
            environment_id="pd-benchmark-methods-gpu:0.13/bench-pepmlm",
            parser_status=pepmlm_status,
            status_reason=pepmlm_reason,
        )
    )
    candidate_rows.append(
        {
            "design_id": "pepmlm_pepmlm_test_row0_fixture_0001",
            "job_id": "batch_a_pepmlm_cpu_smoke_replay",
            "method": "PepMLM",
            "target_id": "pepmlm_test_row0",
            "binder_id": "pepmlm_rank0",
            "source_output_id": "output/pepmlm_generated.csv:row0",
            "generation_rank": pepmlm_record["binder_rank"],
            "sequence": pepmlm_sequence,
            "structure_path": "",
            "peptide_type": "linear",
            "chirality": "L",
            "cyclic": "no",
            "parse_status": pepmlm_status,
            "status_reason": pepmlm_reason,
            "notes": "v0.15 CPU-only minimal smoke fixture; not a Benchmark target or result",
        }
    )
    run_rows.append(
        {
            "design_id": "pepmlm_pepmlm_test_row0_fixture_0001",
            "method": "PepMLM",
            "task_id": "T1_sequence_binder",
            "target_id": "pepmlm_test_row0",
            "binder_id": "pepmlm_rank0",
            "input_mode": "seq_only_csv",
            "target_sequence": pepmlm_input["receptor_sequence"],
            "target_pdb": "",
            "target_chains": "",
            "binder_chain": "",
            "pocket_definition": "",
            "peptide_type": "linear",
            "chirality": "L",
            "cyclic": "no",
            "status": "not_real_benchmark",
            "notes": "Parsed replay row from v0.15 minimal smoke fixture only",
        }
    )

    mpnn_dir = EXTERNAL_ROOT / "proteinmpnn_pdl1"
    mpnn_header, mpnn_sequence = parse_fasta(mpnn_dir / "output/PDL1.fa")
    method_rows.append(
        method_output_row(
            method_dir=mpnn_dir,
            run_record_id="batch_a_proteinmpnn_pdl1_replay",
            job_id="batch_a_proteinmpnn_pdl1_replay",
            method="ProteinMPNN",
            task_id="T3_miniprotein_binder_baseline",
            model_revision="proteinmpnn_v_48_020.pt",
            environment_id="pd-foundry-gpu:latest/foundry",
            parser_status="parsed",
            status_reason="parsed_fasta_fixture",
        )
    )
    candidate_rows.append(
        {
            "design_id": "proteinmpnn_pdl1_fixture_0001",
            "job_id": "batch_a_proteinmpnn_pdl1_replay",
            "method": "ProteinMPNN",
            "target_id": "pdl1_workbench_fixture",
            "binder_id": mpnn_header.split(",")[0],
            "source_output_id": "output/PDL1.fa:record0",
            "generation_rank": "0",
            "sequence": mpnn_sequence,
            "structure_path": "",
            "peptide_type": "protein_binder",
            "chirality": "L",
            "cyclic": "no",
            "parse_status": "parsed",
            "status_reason": "parsed_fasta_fixture",
            "notes": "v0.15 ProteinMPNN minimal smoke fixture; local PDL1 input is not a frozen target",
        }
    )
    run_rows.append(
        {
            "design_id": "proteinmpnn_pdl1_fixture_0001",
            "method": "ProteinMPNN",
            "task_id": "T3_miniprotein_binder_baseline",
            "target_id": "pdl1_workbench_fixture",
            "binder_id": mpnn_header.split(",")[0],
            "input_mode": "pdb_only",
            "target_sequence": "",
            "target_pdb": "/data/protein-design/data/inputs/PDL1.pdb",
            "target_chains": "unreviewed",
            "binder_chain": "not_applicable",
            "pocket_definition": "",
            "peptide_type": "protein_binder",
            "chirality": "L",
            "cyclic": "no",
            "status": "not_real_benchmark",
            "notes": "Parsed replay row from v0.15 minimal smoke fixture only",
        }
    )

    rf_dir = EXTERNAL_ROOT / "rfpeptide_macrocycle"
    rf_pdb = rf_dir / "output/uncond_cycpep_0.pdb"
    rf_sequence = parse_pdb_sequence(rf_pdb)
    method_rows.append(
        method_output_row(
            method_dir=rf_dir,
            run_record_id="batch_a_rfpeptide_macrocycle_replay",
            job_id="batch_a_rfpeptide_macrocycle_replay",
            method="RFpeptide/RFdiffusion",
            task_id="T2_structure_peptide_binder",
            model_revision="Base_ckpt.pt; Complex_base_ckpt.pt; InpaintSeq_ckpt.pt external mount",
            environment_id="pd-rfpeptide-gpu:fixed/SE3cuda",
            parser_status="parsed",
            status_reason="parsed_single_chain_pdb_fixture",
        )
    )
    candidate_rows.append(
        {
            "design_id": "rfpeptide_7zkr_macrocycle_fixture_0001",
            "job_id": "batch_a_rfpeptide_macrocycle_replay",
            "method": "RFpeptide/RFdiffusion",
            "target_id": "gabarap_7zkr_bundled_fixture",
            "binder_id": "uncond_cycpep_0",
            "source_output_id": "output/uncond_cycpep_0.pdb",
            "generation_rank": "0",
            "sequence": rf_sequence,
            "structure_path": str(rf_pdb),
            "peptide_type": "cyclic",
            "chirality": "L",
            "cyclic": "yes",
            "parse_status": "parsed",
            "status_reason": "parsed_single_chain_pdb_fixture",
            "notes": "v0.15 bundled 7ZKR/GABARAP RFpeptide fixture; not a target-set row",
        }
    )
    run_rows.append(
        {
            "design_id": "rfpeptide_7zkr_macrocycle_fixture_0001",
            "method": "RFpeptide/RFdiffusion",
            "task_id": "T2_structure_peptide_binder",
            "target_id": "gabarap_7zkr_bundled_fixture",
            "binder_id": "uncond_cycpep_0",
            "input_mode": "pdb_only",
            "target_sequence": "",
            "target_pdb": "/opt/RFdiffusion/examples/input_pdbs/7zkr_GABARAP.pdb",
            "target_chains": "A",
            "binder_chain": "A",
            "pocket_definition": "contigmap.contigs=[12-18]",
            "peptide_type": "cyclic",
            "chirality": "L",
            "cyclic": "yes",
            "status": "not_real_benchmark",
            "notes": "Parsed replay row from v0.15 bundled-example smoke fixture only",
        }
    )

    return method_rows, candidate_rows, run_rows


def main() -> None:
    if not EXTERNAL_ROOT.exists():
        raise SystemExit(f"Missing external Batch A output root: {EXTERNAL_ROOT}")
    method_rows, candidate_rows, run_rows = build_rows()
    write_csv(
        RESULT_ROOT / "batch_a_replay_method_output_manifest_v0.18.csv",
        METHOD_OUTPUT_HEADERS,
        method_rows,
    )
    write_csv(
        RESULT_ROOT / "batch_a_replay_candidate_outputs_v0.18.csv",
        CANDIDATE_HEADERS,
        candidate_rows,
    )
    write_csv(
        RESULT_ROOT / "batch_a_replay_run_v0.18.csv",
        RUN_HEADERS,
        run_rows,
    )


if __name__ == "__main__":
    main()
