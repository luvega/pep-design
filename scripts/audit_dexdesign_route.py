#!/usr/bin/env python3
"""Audit the DexDesign-specific OSPREY3 route without running design jobs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


METHOD = "DexDesign / OSPREY3"
DEFAULT_SOURCE_DIR = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/OSPREY3")
DEX_ROUTE_REL = Path("examples/ccs.D-peptide-L-protein")
REQUIRED_DEX_FILES = [
    "DL.py",
    "DL_preprocess.py",
    "ccsKstar.py",
    "Confspace_Combiner.py",
]
CSV_HEADERS = [
    "method",
    "source_dir",
    "dexdesign_route_dir",
    "required_route_files",
    "missing_route_files",
    "generic_osprey_example_status",
    "input_pdb",
    "target_chain_role",
    "peptide_chain_role",
    "recommended_target_chain_id",
    "recommended_peptide_chain_id",
    "input_contract_summary",
    "status",
    "candidate_output_allowed",
    "evidence_boundary",
    "next_action",
]


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def generic_osprey_example_status(source_dir: Path) -> str:
    generic_markers = [
        source_dir / "examples" / "1FSV" / "KStar.cfg",
        source_dir / "examples" / "python.GMEC" / "findGMEC.py",
        source_dir / "examples" / "python.GMEC" / "findGMEC.py.template",
    ]
    if any(path.exists() for path in generic_markers):
        return "env_probe_only_not_dexdesign"
    return "not_observed"


def audit_dexdesign_route(
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    output_dir: Path,
    input_pdb: Path | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dex_dir = source_dir / DEX_ROUTE_REL
    missing_files = [name for name in REQUIRED_DEX_FILES if not (dex_dir / name).is_file()]
    generic_status = generic_osprey_example_status(source_dir)

    if missing_files:
        status = "blocked_dexdesign_route_missing"
        next_action = "Restore or pin the OSPREY3 ccs.D-peptide-L-protein DexDesign route files before any adapter work."
    elif input_pdb is None or not input_pdb.is_file():
        status = "blocked_dexdesign_input_contract"
        next_action = (
            "Define a minimal D-peptide/L-protein complex PDB fixture and document the chain-renaming/preprocess contract "
            "before running DL_preprocess.py or OSPREY KStar."
        )
    else:
        status = "dexdesign_input_contract_ready"
        next_action = "Run a bounded CPU smoke on the DexDesign D-peptide route and capture command/log/output pointers."

    row = {
        "method": METHOD,
        "source_dir": str(source_dir),
        "dexdesign_route_dir": str(dex_dir),
        "required_route_files": ";".join(REQUIRED_DEX_FILES),
        "missing_route_files": ";".join(missing_files) if missing_files else "none",
        "generic_osprey_example_status": generic_status,
        "input_pdb": str(input_pdb) if input_pdb is not None else "not_provided",
        "target_chain_role": "first_chain_l_target",
        "peptide_chain_role": "second_chain_d_peptide",
        "recommended_target_chain_id": "z",
        "recommended_peptide_chain_id": "y",
        "input_contract_summary": (
            "Input PDB must contain two chains: first chain is the L-target and second chain is the D-peptide. "
            "Chain_Renamer.py recommends target=z and peptide=y. DL_preprocess.py produces prepared D-L complex "
            "PDB files, and DL.py consumes a directory containing only prepared D-L complex PDB files."
        ),
        "status": status,
        "candidate_output_allowed": "no",
        "evidence_boundary": (
            "DexDesign route audit only; generic OSPREY examples are env probes only, not DexDesign evidence; "
            "not Benchmark result; no scoring or method-ranking evidence"
        ),
        "next_action": next_action,
    }
    write_csv(output_dir / "dexdesign_route_audit.csv", CSV_HEADERS, [row])
    (output_dir / "dexdesign_route_audit.json").write_text(
        json.dumps(row, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--input-pdb", type=Path)
    args = parser.parse_args()

    row = audit_dexdesign_route(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        input_pdb=args.input_pdb,
    )
    print(json.dumps({"status": row["status"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
