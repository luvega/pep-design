#!/usr/bin/env python3
"""Parse v0.21 adapter smoke outputs into small KB tables.

Large structures, logs and raw method outputs remain under /data/protein-design.
This script stores only schema-level summaries in the KB.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTERNAL_ROOT = Path("/data/protein-design/data/outputs/benchmark_v0.21/adapter_smokes")
RESULT_ROOT = ROOT / "benchmark" / "results"

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

METHOD_TASK = {
    "PepMLM": ("T1_sequence_binder", "sequence_csv"),
    "DiffPepBuilder": ("T2_structure_conditioned_peptide", "method_example_pdb"),
    "RFdiffusion + ProteinMPNN": ("T3_structure_to_sequence_handoff", "rf_to_mpnn_handoff"),
    "BindCraft": ("T4_bindcraft_peptide_smoke", "method_example_pdb"),
    "PepGLAD": ("T2_structure_conditioned_peptide", "method_example_pdb"),
    "PepMirror": ("T5_mirror_d_peptide", "method_example_pdb"),
    "D-Flow / PeptideDesign": ("T5_mirror_d_peptide", "method_example_pdb"),
}

PASSED_STATUSES = {
    "adapter_smoke_passed_gpu",
    "unblock_smoke_passed_gpu",
    "bounded_execution_control_passed",
}


def slug(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", text.lower()).strip("_")
    return value or "unknown"


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def read_runtime(method_dir: Path) -> dict[str, object]:
    return json.loads((method_dir / "runtime.json").read_text(encoding="utf-8"))


def read_command(method_dir: Path) -> str:
    path = method_dir / "command.sh"
    if not path.exists():
        return "not_run"
    return " ".join(path.read_text(encoding="utf-8").split())


def parse_fasta(path: Path) -> tuple[str, str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return path.stem, ""
    header = lines[0].lstrip(">") if lines[0].startswith(">") else path.stem
    sequence_lines = lines[1:] if lines[0].startswith(">") else lines
    return header, "".join(line for line in sequence_lines if not line.startswith(">"))


def parse_pdb_sequence(path: Path, chain_id: str = "A") -> str:
    residues: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        chain = line[21].strip()
        if chain_id and chain != chain_id:
            continue
        residue_key = (chain, line[22:26].strip(), line[26].strip())
        if residue_key in seen:
            continue
        seen.add(residue_key)
        residues.append(AA3_TO_1.get(line[17:20].strip().upper(), "X"))
    return "".join(residues)


def parse_pdb_chain_sequences(path: Path) -> dict[str, str]:
    residues: dict[str, list[str]] = {}
    seen: set[tuple[str, str, str]] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        chain = line[21].strip() or "_"
        residue_key = (chain, line[22:26].strip(), line[26].strip())
        if residue_key in seen:
            continue
        seen.add(residue_key)
        residues.setdefault(chain, []).append(AA3_TO_1.get(line[17:20].strip().upper(), "X"))
    return {chain: "".join(seq) for chain, seq in residues.items()}


def choose_chain(sequences: dict[str, str], preferred: list[str]) -> tuple[str, str]:
    for chain in preferred:
        sequence = sequences.get(chain, "")
        if sequence:
            return chain, sequence
    peptide_like = [(chain, sequence) for chain, sequence in sequences.items() if 2 <= len(sequence) <= 50]
    if peptide_like:
        return min(peptide_like, key=lambda item: (len(item[1]), item[0]))
    if sequences:
        return min(sequences.items(), key=lambda item: (len(item[1]), item[0]))
    return "", ""


def method_pdb_candidates(method_dir: Path, method: str) -> list[Path]:
    if method == "DiffPepBuilder":
        primary = sorted((method_dir / "workdir" / "runs").rglob("*.pdb"))
    elif method == "BindCraft":
        primary = sorted((method_dir / "designs").rglob("*.pdb"))
    elif method == "PepGLAD":
        primary = sorted((method_dir / "codesign").glob("*.pdb"))
    elif method == "PepMirror":
        primary = sorted((method_dir / "generated").rglob("*.pdb"))
    else:
        primary = []

    fallback = sorted(method_dir.rglob("*.pdb"))
    seen: set[Path] = set()
    candidates: list[Path] = []
    for path in primary + fallback:
        if path in seen or path.stat().st_size <= 0:
            continue
        if any(part in {"traj", "failed", ".git", "__pycache__"} for part in path.parts):
            continue
        seen.add(path)
        candidates.append(path)
    return candidates


def method_chain_policy(method: str) -> tuple[list[str], str, str, str]:
    if method == "DiffPepBuilder":
        return ["A"], "linear", "L", "no"
    if method == "BindCraft":
        return ["B", "A"], "linear", "L", "no"
    if method == "PepGLAD":
        return ["B", "A"], "linear", "L", "no"
    if method == "PepMirror":
        return ["H", "L", "B", "A"], "linear", "D", "no"
    if method == "D-Flow / PeptideDesign":
        return ["B", "A"], "linear", "D", "no"
    return ["A"], "linear", "L", "no"


def method_output_row(method_dir: Path, runtime: dict[str, object], parser_status: str, reason: str) -> dict[str, object]:
    method = str(runtime.get("method", method_dir.name))
    task_id = METHOD_TASK.get(method, ("T0_unmapped_adapter_smoke", "unknown"))[0]
    run_id = str(runtime.get("job_id") or f"v021_{slug(method)}")
    return {
        "run_record_id": run_id,
        "job_id": run_id,
        "method": method,
        "task_id": task_id,
        "execution_stage": "v0.21_adapter_smoke_fixture",
        "source_commit": runtime.get("source_commit", ""),
        "model_revision": runtime.get("model_revision", runtime.get("model_or_weight_revision", "external_or_not_applicable")),
        "environment_id": f"{runtime.get('image', '')}/{runtime.get('conda_env', '')}".strip("/"),
        "command": read_command(method_dir),
        "raw_output_root": str(method_dir),
        "stdout_log": str(method_dir / "stdout.log") if (method_dir / "stdout.log").exists() else "not_run",
        "stderr_log": str(method_dir / "stderr.log") if (method_dir / "stderr.log").exists() else "not_run",
        "runtime_seconds": runtime.get("runtime_sec", ""),
        "exit_code": runtime.get("exit_code", ""),
        "parser_status": parser_status,
        "status_reason": reason,
        "created_at": runtime.get("created_at", runtime.get("end", "")),
    }


def candidate_row(
    *,
    method_dir: Path,
    runtime: dict[str, object],
    binder_id: str,
    source_output: Path | str,
    sequence: str,
    structure_path: Path | str = "",
    generation_rank: str = "0",
    peptide_type: str = "linear",
    chirality: str = "L",
    cyclic: str = "no",
    binder_chain: str = "A",
    status_reason: str = "parsed",
) -> dict[str, object]:
    method = str(runtime.get("method", method_dir.name))
    task_id, input_mode = METHOD_TASK.get(method, ("T0_unmapped_adapter_smoke", "unknown"))
    job_id = str(runtime.get("job_id") or f"v021_{slug(method)}")
    parse_status = "parsed" if sequence and "X" not in sequence else "partial"
    design_id = f"{slug(method)}_{slug(binder_id)}_v021_0001"
    source_id = relpath(source_output, method_dir) if isinstance(source_output, Path) else source_output
    structure = str(structure_path) if structure_path else ""
    return {
        "design_id": design_id,
        "job_id": job_id,
        "method": method,
        "target_id": f"{slug(method)}_method_example_v021",
        "binder_id": binder_id,
        "source_output_id": source_id,
        "generation_rank": generation_rank,
        "sequence": sequence,
        "structure_path": structure,
        "peptide_type": peptide_type,
        "chirality": chirality,
        "cyclic": cyclic,
        "binder_chain": binder_chain,
        "parse_status": parse_status,
        "status_reason": status_reason if parse_status == "parsed" else "sequence_contains_unknown_or_noncanonical_residue",
        "notes": "v0.21 adapter smoke fixture only; not target-set evidence, scoring evidence, or Benchmark result",
    }


def run_row(candidate: dict[str, object]) -> dict[str, object]:
    method = str(candidate["method"])
    task_id, input_mode = METHOD_TASK.get(method, ("T0_unmapped_adapter_smoke", "unknown"))
    return {
        "design_id": candidate["design_id"],
        "method": method,
        "task_id": task_id,
        "target_id": candidate["target_id"],
        "binder_id": candidate["binder_id"],
        "input_mode": input_mode,
        "target_sequence": "",
        "target_pdb": "",
        "target_chains": "",
        "binder_chain": candidate.get("binder_chain", "A"),
        "pocket_definition": "",
        "peptide_type": candidate["peptide_type"],
        "chirality": candidate["chirality"],
        "cyclic": candidate["cyclic"],
        "status": "not_real_benchmark",
        "notes": "Parsed v0.21 adapter smoke row only",
    }


def parse_pepmlm(method_dir: Path, runtime: dict[str, object]) -> list[dict[str, object]]:
    candidates = []
    for path in sorted(method_dir.rglob("*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "generated_binder" not in reader.fieldnames:
                continue
            for index, row in enumerate(reader):
                sequence = row.get("generated_binder", "")
                candidates.append(
                    candidate_row(
                        method_dir=method_dir,
                        runtime=runtime,
                        binder_id=f"pepmlm_rank{row.get('binder_rank', index)}",
                        source_output=f"{relpath(path, method_dir)}:row{index}",
                        sequence=sequence,
                        generation_rank=str(row.get("binder_rank", index)),
                        status_reason="parsed_generated_binder_csv",
                    )
                )
                return candidates
    return candidates


def parse_diff_or_pdb_method(method_dir: Path, runtime: dict[str, object]) -> list[dict[str, object]]:
    method = str(runtime.get("method", method_dir.name))
    pdbs = method_pdb_candidates(method_dir, method)
    if not pdbs:
        return []
    pdb = pdbs[0]
    preferred_chains, peptide_type, chirality, cyclic = method_chain_policy(method)
    chain, sequence = choose_chain(parse_pdb_chain_sequences(pdb), preferred_chains)
    return [
        candidate_row(
            method_dir=method_dir,
            runtime=runtime,
            binder_id=f"{pdb.stem}_chain{chain or 'unknown'}",
            source_output=pdb,
            sequence=sequence,
            structure_path=pdb,
            peptide_type=peptide_type,
            chirality=chirality,
            cyclic=cyclic,
            binder_chain=chain,
            status_reason=f"parsed_single_pdb_output_chain_{chain or 'unknown'}",
        )
    ]


def parse_rfdiffusion_handoff(method_dir: Path, runtime: dict[str, object]) -> list[dict[str, object]]:
    manifest = method_dir / "handoff_manifest.csv"
    if not manifest.exists():
        return parse_diff_or_pdb_method(method_dir, runtime)
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    candidates: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        if row.get("status") not in {"parsed", "passed", "adapter_smoke_passed_gpu"}:
            continue
        fasta = method_dir / row.get("mpnn_fasta", "")
        if not fasta.exists():
            continue
        header, sequence = parse_fasta(fasta)
        candidates.append(
            candidate_row(
                method_dir=method_dir,
                runtime=runtime,
                binder_id=header.split(",")[0],
                source_output=f"{relpath(fasta, method_dir)}:record{index}",
                sequence=sequence,
                structure_path=method_dir / row.get("mpnn_input_pdb", ""),
                peptide_type="protein_binder",
                chirality="L",
                cyclic="no",
                binder_chain="A",
                status_reason="parsed_rf_to_mpnn_handoff_fasta",
            )
        )
        break
    return candidates


def parse_candidates(method_dir: Path, runtime: dict[str, object]) -> list[dict[str, object]]:
    method = str(runtime.get("method", method_dir.name))
    if method == "PepMLM":
        return parse_pepmlm(method_dir, runtime)
    if method == "RFdiffusion + ProteinMPNN":
        return parse_rfdiffusion_handoff(method_dir, runtime)
    return parse_diff_or_pdb_method(method_dir, runtime)


def build_rows(external_root: Path = DEFAULT_EXTERNAL_ROOT) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    method_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []

    for runtime_path in sorted(external_root.glob("*/runtime.json")):
        method_dir = runtime_path.parent
        runtime = read_runtime(method_dir)
        status = str(runtime.get("smoke_status", "missing_runtime"))
        blocker = str(runtime.get("blocker", "")).strip()
        if status not in PASSED_STATUSES:
            reason = f"{status}: {blocker}" if blocker else status
            method_rows.append(method_output_row(method_dir, runtime, "not_applicable", reason))
            continue

        parsed_candidates = parse_candidates(method_dir, runtime)
        if parsed_candidates:
            parser_status = "parsed" if all(row["parse_status"] == "parsed" for row in parsed_candidates) else "partial"
            reason = "parsed_v021_adapter_outputs"
        else:
            parser_status = "failed"
            reason = "no_candidate_output_observed"
        method_rows.append(method_output_row(method_dir, runtime, parser_status, reason))
        candidate_rows.extend(parsed_candidates)
        run_rows.extend(run_row(row) for row in parsed_candidates)

    return method_rows, candidate_rows, run_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    args = parser.parse_args()

    method_rows, candidate_rows, run_rows = build_rows(args.external_root)
    write_csv(args.result_root / "adapter_method_output_manifest_v0.21.csv", METHOD_OUTPUT_HEADERS, method_rows)
    write_csv(args.result_root / "adapter_candidate_outputs_v0.21.csv", CANDIDATE_HEADERS, candidate_rows)
    write_csv(args.result_root / "adapter_run_rows_v0.21.csv", RUN_HEADERS, run_rows)
    print(
        json.dumps(
            {
                "method_rows": len(method_rows),
                "candidate_rows": len(candidate_rows),
                "run_rows": len(run_rows),
                "external_root": str(args.external_root),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
