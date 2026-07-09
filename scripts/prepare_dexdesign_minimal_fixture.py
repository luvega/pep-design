#!/usr/bin/env python3
"""Create a minimal DexDesign D-peptide/L-protein input-contract fixture."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


METHOD = "DexDesign / OSPREY3"
STATUS = "dexdesign_input_contract_ready_fixture_created"
FIXTURE_NAME = "synthetic_minimal-D-L-complex.pdb"
TARGET_CHAIN = "z"
PEPTIDE_CHAIN = "y"

MANIFEST_HEADERS = [
    "method",
    "fixture_id",
    "fixture_path",
    "target_chain_id",
    "peptide_chain_id",
    "status",
    "candidate_output_allowed",
    "evidence_boundary",
    "notes",
]


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def atom_line(
    *,
    serial: int,
    atom: str,
    resname: str,
    chain_id: str,
    resseq: int,
    x: float,
    y: float,
    z: float,
    element: str,
) -> str:
    return (
        f"ATOM  {serial:5d} {atom:<4s} {resname:>3s} {chain_id}{resseq:4d}"
        f"    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {element:>2s}"
    )


def residue_atoms(
    *,
    serial_start: int,
    resname: str,
    chain_id: str,
    resseq: int,
    x0: float,
    y0: float,
    z0: float,
) -> tuple[list[str], int]:
    atom_specs = [
        ("N", "N", x0, y0, z0),
        ("CA", "C", x0 + 1.45, y0, z0),
        ("C", "C", x0 + 2.35, y0 + 1.20, z0),
        ("O", "O", x0 + 2.05, y0 + 2.35, z0),
        ("CB", "C", x0 + 1.70, y0 - 0.85, z0 + 1.15),
    ]
    lines = []
    serial = serial_start
    for atom, element, x, y, z in atom_specs:
        lines.append(
            atom_line(
                serial=serial,
                atom=atom,
                resname=resname,
                chain_id=chain_id,
                resseq=resseq,
                x=x,
                y=y,
                z=z,
                element=element,
            )
        )
        serial += 1
    return lines, serial


def build_fixture_pdb() -> str:
    lines = [
        "HEADER    SYNTHETIC DEXDESIGN INPUT-CONTRACT FIXTURE",
        "REMARK    Synthetic fixture only; not Benchmark result; no scoring evidence.",
        "REMARK    DexDesign contract: first chain is L-target and second chain is D-peptide.",
        "REMARK    Contract chain IDs follow route audit recommendation: target=z, peptide=y.",
    ]
    serial = 1
    for resseq, resname in enumerate(["ALA", "LEU", "SER"], start=1):
        residue, serial = residue_atoms(
            serial_start=serial,
            resname=resname,
            chain_id=TARGET_CHAIN,
            resseq=resseq,
            x0=float(resseq - 1) * 3.2,
            y0=0.0,
            z0=0.0,
        )
        lines.extend(residue)
    lines.append(f"TER   {serial:5d}      SER {TARGET_CHAIN}   3")
    serial += 1
    for resseq, resname in enumerate(["GLY", "LYS", "TYR"], start=1):
        residue, serial = residue_atoms(
            serial_start=serial,
            resname=resname,
            chain_id=PEPTIDE_CHAIN,
            resseq=resseq,
            x0=float(resseq - 1) * 3.2,
            y0=4.0,
            z0=1.5,
        )
        lines.extend(residue)
    lines.append(f"TER   {serial:5d}      TYR {PEPTIDE_CHAIN}   3")
    lines.append("END")
    return "\n".join(lines) + "\n"


def prepare_minimal_d_l_fixture(output_dir: Path) -> dict[str, str]:
    prepared_dir = output_dir / "prepared-PDBs"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = prepared_dir / FIXTURE_NAME
    fixture_path.write_text(build_fixture_pdb(), encoding="utf-8")

    row = {
        "method": METHOD,
        "fixture_id": "v029_dexdesign_synthetic_minimal_d_l_complex",
        "fixture_path": str(fixture_path),
        "target_chain_id": TARGET_CHAIN,
        "peptide_chain_id": PEPTIDE_CHAIN,
        "status": STATUS,
        "candidate_output_allowed": "no",
        "evidence_boundary": "Input-contract fixture only; not Benchmark result; not scoring evidence",
        "notes": "Synthetic prepared D-L complex fixture for DexDesign route audit; no design job was run.",
    }
    write_csv(output_dir / "dexdesign_minimal_fixture_manifest.csv", MANIFEST_HEADERS, [row])
    (output_dir / "dexdesign_minimal_fixture_manifest.json").write_text(
        json.dumps(row, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": STATUS,
        "fixture_path": str(fixture_path),
        "manifest_csv": str(output_dir / "dexdesign_minimal_fixture_manifest.csv"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = prepare_minimal_d_l_fixture(args.output_dir)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
