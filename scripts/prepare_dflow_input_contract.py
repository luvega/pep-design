#!/usr/bin/env python
"""Prepare a D-Flow PepDataset input-contract fixture.

D-Flow's PepDataset expects a PepMerge-style directory:

    <structure_dir>/<case_id>/pocket.pdb
    <structure_dir>/<case_id>/peptide.pdb

and a hard-coded ../names.txt relative to the D-Flow source working directory.
This script builds that layout from a benchmark PDB fixture and verifies that
PepDataset can create and reload the expected LMDB cache.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RCSB_PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


def chain_ids_from_field(value: str) -> list[str]:
    """Parse one-character PDB chain IDs from manifest fields."""

    primary = re.split(r"\bwith\b|\(|\[", value.strip(), maxsplit=1, flags=re.IGNORECASE)[0]
    tokens = re.split(r"[;,\s]+", primary)
    return [token for token in (part.strip() for part in tokens) if re.fullmatch(r"[A-Za-z0-9]", token)]


def ensure_pdb(pdb_id: str, pdb_path: Path, force_download: bool = False) -> str:
    pdb_id = pdb_id.upper()
    pdb_path.parent.mkdir(parents=True, exist_ok=True)
    if pdb_path.exists() and pdb_path.stat().st_size > 0 and not force_download:
        return "cached"

    url = RCSB_PDB_URL.format(pdb_id=pdb_id)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if not data.startswith(b"HEADER") and not data.startswith(b"TITLE"):
        raise RuntimeError(f"Unexpected PDB response from {url}")
    pdb_path.write_bytes(data)
    return "downloaded"


def _heavy_atoms(residue) -> Iterable:
    for atom in residue.get_atoms():
        if getattr(atom, "element", "").upper() != "H":
            yield atom


def _residue_key(chain_id: str, residue) -> tuple[str, tuple]:
    return chain_id, residue.get_id()


def select_pocket_residues(structure, receptor_chains: list[str], peptide_chains: list[str], cutoff_angstrom: float) -> set[tuple[str, tuple]]:
    peptide_atoms = []
    receptor_residues = []
    model = next(structure.get_models())
    for chain in model:
        chain_id = chain.get_id()
        if chain_id in peptide_chains:
            for residue in chain:
                peptide_atoms.extend(_heavy_atoms(residue))
        elif chain_id in receptor_chains:
            receptor_residues.append((chain_id, chain, list(chain)))

    if not peptide_atoms:
        raise RuntimeError(f"No peptide atoms found for chain(s): {','.join(peptide_chains)}")

    selected: set[tuple[str, tuple]] = set()
    for chain_id, _chain, residues in receptor_residues:
        for residue in residues:
            for receptor_atom in _heavy_atoms(residue):
                if any((receptor_atom - peptide_atom) <= cutoff_angstrom for peptide_atom in peptide_atoms):
                    selected.add(_residue_key(chain_id, residue))
                    break
    if not selected:
        raise RuntimeError(
            f"No receptor pocket residues within {cutoff_angstrom:g} A for receptor chain(s): {','.join(receptor_chains)}"
        )
    return selected


def write_selected_pdbs(
    pdb_path: Path,
    case_dir: Path,
    receptor_chains: list[str],
    peptide_chains: list[str],
    cutoff_angstrom: float,
) -> dict[str, int]:
    from Bio.PDB import PDBIO, PDBParser, Select

    class ChainAndResidueSelect(Select):
        def __init__(self, chain_ids: set[str], residue_keys: set[tuple[str, tuple]] | None = None):
            self.chain_ids = chain_ids
            self.residue_keys = residue_keys

        def accept_chain(self, chain) -> int:
            return int(chain.get_id() in self.chain_ids)

        def accept_residue(self, residue) -> int:
            if self.residue_keys is None:
                return 1
            chain_id = residue.get_parent().get_id()
            return int((chain_id, residue.get_id()) in self.residue_keys)

        def accept_atom(self, atom) -> int:
            return int(getattr(atom, "element", "").upper() != "H")

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(pdb_path.stem, str(pdb_path))
    pocket_keys = select_pocket_residues(structure, receptor_chains, peptide_chains, cutoff_angstrom)

    case_dir.mkdir(parents=True, exist_ok=True)
    io = PDBIO()
    io.set_structure(structure)
    io.save(str(case_dir / "pocket.pdb"), ChainAndResidueSelect(set(receptor_chains), pocket_keys))
    io.save(str(case_dir / "peptide.pdb"), ChainAndResidueSelect(set(peptide_chains)))

    return {"pocket_residues": len(pocket_keys), "peptide_chains": len(peptide_chains)}


def dflow_names_file(source_dir: Path) -> Path:
    return source_dir.resolve().parent / "names.txt"


def write_names_file(source_dir: Path, case_id: str) -> Path:
    names_file = dflow_names_file(source_dir)
    names_file.parent.mkdir(parents=True, exist_ok=True)
    names_file.write_text(case_id + "\n", encoding="utf-8")
    return names_file


def run_pepdataset_smoke(
    env_python: Path,
    source_dir: Path,
    structure_dir: Path,
    dataset_dir: Path,
    dataset_name: str,
) -> dict[str, object]:
    code = r"""
import hashlib
import json
import os
from pathlib import Path

from dflow.data.pep_dataloader import PepDataset

source_dir = Path(os.environ["DFLOW_SOURCE_DIR"]).resolve()
structure_dir = Path(os.environ["DFLOW_STRUCTURE_DIR"]).resolve()
dataset_dir = Path(os.environ["DFLOW_DATASET_DIR"]).resolve()
dataset_name = os.environ["DFLOW_DATASET_NAME"]
os.chdir(source_dir)

created = PepDataset(
    structure_dir=str(structure_dir),
    dataset_dir=str(dataset_dir),
    name=dataset_name,
    reset=True,
)
created_count = len(created)
created._close_db()
loaded = PepDataset(
    structure_dir=str(structure_dir),
    dataset_dir=str(dataset_dir),
    name=dataset_name,
    reset=False,
)
loaded_count = len(loaded)
if loaded_count < 1:
    raise RuntimeError("PepDataset reset=False loaded zero entries")

item = loaded[0]
cache_path = dataset_dir / f"{dataset_name}_structure_cache.lmdb"
entry_hash = hashlib.sha256()
for idx in range(loaded_count):
    entry = loaded[idx]
    entry_hash.update(str(entry["id"]).encode("utf-8"))

print(json.dumps({
    "reset_true_status": "passed",
    "reset_false_status": "passed",
    "created_entries": created_count,
    "loaded_entries": loaded_count,
    "first_id": str(item["id"]),
    "first_total_residues": int(item["aa"].shape[0]),
    "first_generated_residues": int(item["generate_mask"].sum().item()),
    "cache_path": str(cache_path),
    "cache_exists": cache_path.exists(),
    "cache_size_bytes": cache_path.stat().st_size if cache_path.exists() else 0,
    "entry_id_sha256": entry_hash.hexdigest(),
}))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_dir.resolve()) + os.pathsep + env.get("PYTHONPATH", "")
    env["DFLOW_SOURCE_DIR"] = str(source_dir)
    env["DFLOW_STRUCTURE_DIR"] = str(structure_dir)
    env["DFLOW_DATASET_DIR"] = str(dataset_dir)
    env["DFLOW_DATASET_NAME"] = dataset_name
    completed = subprocess.run(
        [str(env_python), "-c", code],
        cwd=str(source_dir),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "PepDataset smoke failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    json_line = completed.stdout.strip().splitlines()[-1]
    result = json.loads(json_line)
    result["stdout_tail"] = completed.stdout.strip().splitlines()[-5:]
    result["stderr_tail"] = completed.stderr.strip().splitlines()[-5:]
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", default="mdm2_p53_3eqs_fixture")
    parser.add_argument("--pdb-id", default="3EQS")
    parser.add_argument("--receptor-chains", default="A")
    parser.add_argument("--peptide-chains", default="B")
    parser.add_argument("--pocket-cutoff-angstrom", type=float, default=10.0)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "method_sources/dflow/PeptideDesign")
    parser.add_argument("--env-python", type=Path, default=ROOT / ".venv/dflow-v023/bin/python")
    parser.add_argument("--pdb-cache-dir", type=Path, default=ROOT / "data/dflow/pdbs")
    parser.add_argument("--structure-dir", type=Path, default=ROOT / "data/dflow/pepmerge")
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "data/dflow/pep_cache")
    parser.add_argument("--dataset-name", default="pep_pocket_test")
    parser.add_argument("--log-path", type=Path, default=ROOT / "logs/v0.24/dflow_input_contract_fixture_smoke.json")
    parser.add_argument("--force-download", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.time()
    receptor_chains = chain_ids_from_field(args.receptor_chains)
    peptide_chains = chain_ids_from_field(args.peptide_chains)
    if not receptor_chains:
        raise SystemExit("--receptor-chains did not contain any PDB chain IDs")
    if not peptide_chains:
        raise SystemExit("--peptide-chains did not contain any PDB chain IDs")
    if not args.env_python.exists():
        raise SystemExit(f"D-Flow Python not found: {args.env_python}")
    if not args.source_dir.exists():
        raise SystemExit(f"D-Flow source dir not found: {args.source_dir}")

    pdb_path = args.pdb_cache_dir / f"{args.pdb_id.upper()}.pdb"
    pdb_source_status = ensure_pdb(args.pdb_id, pdb_path, args.force_download)
    case_dir = args.structure_dir / args.case_id
    selection = write_selected_pdbs(
        pdb_path=pdb_path,
        case_dir=case_dir,
        receptor_chains=receptor_chains,
        peptide_chains=peptide_chains,
        cutoff_angstrom=args.pocket_cutoff_angstrom,
    )
    names_file = write_names_file(args.source_dir, args.case_id)
    smoke = run_pepdataset_smoke(
        env_python=args.env_python,
        source_dir=args.source_dir,
        structure_dir=args.structure_dir,
        dataset_dir=args.dataset_dir,
        dataset_name=args.dataset_name,
    )

    report = {
        "method_id": "dflow",
        "case_id": args.case_id,
        "pdb_id": args.pdb_id.upper(),
        "pdb_source_status": pdb_source_status,
        "receptor_chains": receptor_chains,
        "peptide_chains": peptide_chains,
        "pocket_cutoff_angstrom": args.pocket_cutoff_angstrom,
        "structure_dir": str(args.structure_dir.resolve()),
        "case_dir": str(case_dir.resolve()),
        "dataset_dir": str(args.dataset_dir.resolve()),
        "names_file": str(names_file.resolve()),
        "pep_dataset": smoke,
        "selection": selection,
        "status": "input_contract_ready_fixture",
        "evidence_boundary": "D-Flow PepDataset input-contract fixture only; not Benchmark result, not scoring evidence",
        "elapsed_sec": round(time.time() - started, 3),
    }
    args.log_path.parent.mkdir(parents=True, exist_ok=True)
    args.log_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
