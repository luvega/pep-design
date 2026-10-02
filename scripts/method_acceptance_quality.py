#!/usr/bin/env python3
"""Read-only candidate integrity review; never generation, scoring or ranking.

The criteria below are declared before reviewing the historical candidates.
They define structural/sequence integrity, not affinity, stability or synthesis
quality. No native selection threshold is invented when the method has none.
Historical provenance is replayed separately and is necessary but insufficient.
Only disposable replay copies are written, by the existing replay implementation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v034_adapters.common import AA3_TO_1, CANONICAL_AA, PDBAtom

RF = "RFdiffusion + ProteinMPNN"
CYCLIC = "AfCycDesign / ColabDesign cyclic peptide"
METHODS = {"PepMLM": "sequence", "DiffPepBuilder": "L", "PepGLAD": "mixed_allowed",
           "D-Flow / PeptideDesign": "D", "PepMirror": "D", CYCLIC: "L", RF: "backbone",
           "DexDesign / OSPREY3": "D", "BindCraft": "L", "SaLT&PepPr": "sequence"}
CRITERIA = {
    "version": "method_candidate_integrity_v1",
    "scope": "sequence_legality_and_structural_integrity_only",
    "sequence": "nonempty uppercase canonical amino acids; requested length; no X",
    "structure": "finite single-model coordinates, unique atoms, endpoint atom completeness",
    "full_atom_sequence": "exact binder PDB sequence equality",
    "rf_endpoint": "unthreaded backbone + separately verified FASTA; length equality only",
    "diffpepbuilder_endpoint": "native N/CA/C/O/CB backbone and sequence; Gly CB is virtual and excluded from physical clashes; no complete-sidechain claim",
    "diffpepbuilder_endpoint_source": "DiffPepBuilder/data/all_atom.py:152-174 compute_backbone; experiments/train.py:984-1004",
    "chirality": "Gly achiral; non-Gly normalized signed volume abs>0.05; method-specific L/D/mixed",
    "cn_ideal_angstrom": [1.329, 1.341],
    "cn_sd_angstrom": [0.014, 0.016],
    "ca_c_n_cosine": [-0.4473, 0.0311],
    "c_n_ca_cosine": [-0.5203, 0.0353],
    "between_residue_tolerance_factor": 12.0,
    "native_geometry_source": "ColabDesign@e31a56fe1d9b4de25c8697f3a28b75892941cc72/colabdesign/af/alphafold/common/residue_constants.py:481-486; model/config.py:347,366",
    "other_covalent_bond_angstrom": [0.9, 2.0],
    "sulfur_covalent_bond_angstrom": [1.6, 2.2],
    "n_ca_c_angle_degrees": [80.0, 140.0],
    "gross_geometry_basis": "prospective project integrity bounds, not method-native efficacy filters",
    "vdw_radii_angstrom": {"C": 1.7, "N": 1.55, "O": 1.52, "S": 1.8},
    "severe_clash_overlap_angstrom": 1.5,
    "clash_exclusions": "covalent graph distance <=2; plausible SG-SG disulfide 1.8..2.3 Angstrom",
    "clash_scope": "binder internal and binder-target heavy atoms; not target internal",
    "cyclic": "same inter-residue C-N bond and angle criteria at closure, plus replayed cyclic offset",
    "pass": "zero failed checks and independently replayable provenance",
    "not_evaluated": ["binding_affinity", "biological_activity", "experimental_stability",
                      "synthetic_feasibility", "full_stereochemical_validation", "fair_benchmark"],
}

# Expected heavy atoms and bonds for the canonical residue endpoint. Hydrogens,
# terminal OXT and experimental ligands are not required. RF has no sidechains.
SIDECHAINS = {
    "A": "CA-CB", "G": "", "V": "CA-CB CB-CG1 CB-CG2",
    "L": "CA-CB CB-CG CG-CD1 CG-CD2", "I": "CA-CB CB-CG1 CB-CG2 CG1-CD1",
    "S": "CA-CB CB-OG", "T": "CA-CB CB-OG1 CB-CG2", "C": "CA-CB CB-SG",
    "M": "CA-CB CB-CG CG-SD SD-CE", "P": "CA-CB CB-CG CG-CD CD-N",
    "D": "CA-CB CB-CG CG-OD1 CG-OD2", "N": "CA-CB CB-CG CG-OD1 CG-ND2",
    "E": "CA-CB CB-CG CG-CD CD-OE1 CD-OE2", "Q": "CA-CB CB-CG CG-CD CD-OE1 CD-NE2",
    "K": "CA-CB CB-CG CG-CD CD-CE CE-NZ", "R": "CA-CB CB-CG CG-CD CD-NE NE-CZ CZ-NH1 CZ-NH2",
    "H": "CA-CB CB-CG CG-ND1 CG-CD2 ND1-CE1 CD2-NE2 CE1-NE2",
    "F": "CA-CB CB-CG CG-CD1 CG-CD2 CD1-CE1 CD2-CE2 CE1-CZ CE2-CZ",
    "Y": "CA-CB CB-CG CG-CD1 CG-CD2 CD1-CE1 CD2-CE2 CE1-CZ CE2-CZ CZ-OH",
    "W": "CA-CB CB-CG CG-CD1 CG-CD2 CD1-NE1 NE1-CE2 CD2-CE2 CD2-CE3 CE2-CZ2 CE3-CZ3 CZ2-CH2 CZ3-CH2",
}


def criteria() -> dict[str, Any]:
    """Return a detached, JSON-serializable declaration for prospective policies."""
    return json.loads(json.dumps(CRITERIA))


def criteria_sha256() -> str:
    return hashlib.sha256(json.dumps(CRITERIA, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _vector(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _cosine(a, b, c):
    u, v = _vector(a, b), _vector(c, b)
    denominator = _norm(u) * _norm(v)
    return sum(x * y for x, y in zip(u, v)) / denominator if denominator else None


def _distance(a: PDBAtom, b: PDBAtom) -> float:
    return math.dist(a.xyz, b.xyz)


def _read_atoms(payload: bytes) -> list[PDBAtom]:
    lines = payload.decode("utf-8").splitlines()
    if sum(line.startswith("MODEL ") for line in lines) > 1:
        raise ValueError("multiple_models")
    atoms = []
    for line in lines:
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        if len(line) < 54:
            raise ValueError("truncated_atom")
        if line[16].strip():
            raise ValueError("ambiguous_alternate_location")
        name = line[12:16].strip()
        element = line[76:78].strip() if len(line) >= 78 else name[:1]
        if element in {"H", "D"}:
            continue
        atom = PDBAtom(line[:6].strip(), line[21].strip() or "_",
                       (line[21].strip() or "_", line[22:26].strip(), line[26].strip()),
                       line[17:20].strip(), name,
                       float(line[30:38]), float(line[38:46]), float(line[46:54]))
        if not all(math.isfinite(x) for x in atom.xyz):
            raise ValueError("nonfinite_coordinate")
        atoms.append(atom)
    if not atoms:
        raise ValueError("empty_structure")
    return atoms


def evaluate_candidate(*, method: str, sequence: str, length_min: int, length_max: int,
                       structure_path: Path | str | None = None, binder_chain: str = "B") -> dict[str, Any]:
    """Evaluate integrity only. This API never asserts execution/provenance validity.

    Method determines chirality, cyclic topology and output representation; callers
    cannot silently override those checks. Use review_existing() for full replay.
    """
    result: dict[str, Any] = {"method": method, "sequence": sequence,
                            "criteria_sha256": criteria_sha256(), "scope": CRITERIA["scope"],
                            "checks": {}, "metrics": {}, "not_evaluated": CRITERIA["not_evaluated"][:]}
    checks, metrics = result["checks"], result["metrics"]
    checks["known_method"] = method in METHODS
    checks["canonical_sequence"] = bool(sequence) and set(sequence) <= CANONICAL_AA
    checks["requested_length"] = (type(length_min) is int and type(length_max) is int
                                  and 0 < length_min <= len(sequence) <= length_max)
    if method not in METHODS or METHODS[method] == "sequence":
        return _finish(result)
    try:
        path = Path(structure_path) if structure_path else None
        if path is None or path.is_symlink() or not path.is_file():
            raise ValueError("missing_or_nonregular_structure")
        payload = path.read_bytes()
        metrics["structure_sha256"] = hashlib.sha256(payload).hexdigest()
        atoms = _read_atoms(payload)
        if method == "DiffPepBuilder":
            atoms = [a for a in atoms if not (a.chain == binder_chain and a.resname == "GLY" and a.atom_name == "CB")]
    except (OSError, ValueError, UnicodeError) as exc:
        checks["structure_readable"] = False
        result["error"] = str(exc)
        return _finish(result)
    checks["structure_readable"] = True
    residues: dict[tuple, dict[str, PDBAtom]] = {}
    duplicate = False
    for atom in atoms:
        residue = residues.setdefault(atom.residue_key, {})
        if atom.atom_name in residue or (residue and next(iter(residue.values())).resname != atom.resname):
            duplicate = True
        residue[atom.atom_name] = atom
    binder = [(key, row) for key, row in residues.items() if key[0] == binder_chain]
    checks["unique_atom_identity"] = not duplicate
    pdb_sequence = "".join(AA3_TO_1.get(next(iter(row.values())).resname, "X") for _, row in binder)
    metrics["structure_sequence"] = pdb_sequence
    checks["binder_present"] = bool(binder)
    checks["structure_sequence_consistency"] = (len(pdb_sequence) == len(sequence) if method == RF else pdb_sequence == sequence)
    if method == CYCLIC:
        checks["cyclic_has_multiple_residues"] = len(binder) > 1
    if method == RF:
        result["representation"] = "unthreaded_backbone_and_separate_fasta"
        result["not_evaluated"].extend(["sequence_resolved_sidechains", "sequence_resolved_chirality"])
    if method == "DiffPepBuilder":
        result["representation"] = "native_backbone_cb_and_sequence"
        result["not_evaluated"].append("complete_sidechain_geometry")

    graph: dict[tuple, set] = {}
    bond_errors, missing_atoms, angle_errors = [], [], []
    atom_lookup = {(a.residue_key, a.atom_name): a for a in atoms}
    def bond(key1, key2, *, peptide=False):
        graph.setdefault(key1, set()).add(key2)
        graph.setdefault(key2, set()).add(key1)
        if key1 not in atom_lookup or key2 not in atom_lookup:
            return
        a, b = atom_lookup[key1], atom_lookup[key2]
        if key1[0][0] != binder_chain and key2[0][0] != binder_chain:
            return
        dist = _distance(a, b)
        if peptide:
            proline = b.resname == "PRO"
            ideal = CRITERIA["cn_ideal_angstrom"][int(proline)]
            tol = CRITERIA["cn_sd_angstrom"][int(proline)] * 12
            low, high = ideal - tol, ideal + tol
        else:
            low, high = CRITERIA["sulfur_covalent_bond_angstrom"] if a.atom_name.startswith("S") or b.atom_name.startswith("S") else CRITERIA["other_covalent_bond_angstrom"]
        if not low <= dist <= high:
            bond_errors.append({"atoms": [str(key1), str(key2)], "distance": round(dist, 5), "allowed": [low, high]})

    # Build molecular adjacency for every polymer residue to exclude bonded
    # target/binder pairs correctly; assess completeness for the binder only.
    for key, row in residues.items():
        aa = AA3_TO_1.get(next(iter(row.values())).resname)
        if aa is None:
            if key[0] == binder_chain:
                missing_atoms.append(str(key) + ":unknown_residue")
            continue
        sidechain_edges = SIDECHAINS[aa]
        if key[0] == binder_chain and method == RF:
            sidechain_edges = ""
        elif key[0] == binder_chain and method == "DiffPepBuilder":
            sidechain_edges = "CA-CB" if aa != "G" else ""
        edges = "N-CA CA-C C-O " + sidechain_edges
        required = {name for edge in edges.split() for name in edge.split("-")}
        if key[0] == binder_chain:
            missing_atoms.extend(str(key) + ":" + name for name in sorted(required - set(row)))
            if {"N", "CA", "C"} <= row.keys():
                cosine = _cosine(row["N"].xyz, row["CA"].xyz, row["C"].xyz)
                angle = math.degrees(math.acos(max(-1, min(1, cosine)))) if cosine is not None else None
                if angle is None or not 80 <= angle <= 140:
                    angle_errors.append({"residue": str(key), "angle": angle, "kind": "N_CA_C"})
        for edge in edges.split():
            a, b = edge.split("-")
            bond((key, a), (key, b))
        # OXT is an optional covalently bonded terminal oxygen, never a
        # nonbonded clash partner of its own carbonyl carbon.
        if "OXT" in row:
            bond((key, "C"), (key, "OXT"))
    chains: dict[str, list] = {}
    for key, row in residues.items():
        if {"N", "CA", "C"} <= row.keys():
            chains.setdefault(key[0], []).append((key, row))
    for chain, chain_rows in chains.items():
        pairs = list(zip(chain_rows, chain_rows[1:]))
        if method == CYCLIC and chain == binder_chain and len(chain_rows) > 1:
            pairs.append((chain_rows[-1], chain_rows[0]))
        for (left_key, left), (right_key, right) in pairs:
            bond((left_key, "C"), (right_key, "N"), peptide=True)
            if chain != binder_chain:
                continue
            for label, triplet in [("ca_c_n_cosine", (left["CA"], left["C"], right["N"])),
                                   ("c_n_ca_cosine", (left["C"], right["N"], right["CA"]))]:
                cosine = _cosine(*(a.xyz for a in triplet))
                ideal, sd = CRITERIA[label]
                if cosine is None or abs(cosine - ideal) > 12 * sd:
                    angle_errors.append({"residue": str(left_key), "kind": label, "cosine": cosine})

    chiral = {"L": 0, "D": 0, "gly_achiral": 0, "unknown": 0}
    for _, row in binder:
        if next(iter(row.values())).resname == "GLY":
            chiral["gly_achiral"] += 1
        elif {"N", "CA", "C", "CB"} <= row.keys():
            n, c, cb = (_vector(row[name].xyz, row["CA"].xyz) for name in ("N", "C", "CB"))
            cross = (n[1]*c[2]-n[2]*c[1], n[2]*c[0]-n[0]*c[2], n[0]*c[1]-n[1]*c[0])
            denom = _norm(n)*_norm(c)*_norm(cb)
            signed = sum(a*b for a,b in zip(cross, cb))/denom if denom else 0
            chiral["unknown" if abs(signed) <= 0.05 else "L" if signed > 0 else "D"] += 1
        else:
            chiral["unknown"] += 1
    if method != RF:
        checks["chirality"] = not chiral["unknown"] and (METHODS[method] == "mixed_allowed" or chiral["D" if METHODS[method] == "L" else "L"] == 0)
    metrics["chirality"] = chiral
    clashes = []
    for i, a in enumerate(atoms):
        for b in atoms[i+1:]:
            if binder_chain not in {a.chain, b.chain}:
                continue
            ka, kb = (a.residue_key, a.atom_name), (b.residue_key, b.atom_name)
            neighbors = graph.get(ka, set())
            if kb in neighbors or any(kb in graph.get(n, set()) for n in neighbors):
                continue
            dist = _distance(a, b)
            if a.atom_name == b.atom_name == "SG" and 1.8 <= dist <= 2.3:
                continue
            radii = CRITERIA["vdw_radii_angstrom"]
            if a.atom_name[:1] not in radii or b.atom_name[:1] not in radii:
                continue
            if dist < radii[a.atom_name[:1]] + radii[b.atom_name[:1]] - 1.5:
                clashes.append({"atoms": [str(ka), str(kb)], "distance": round(dist, 5)})
    checks.update(complete_endpoint_atoms=not missing_atoms, covalent_geometry=not bond_errors,
                  backbone_angles=not angle_errors, no_severe_clashes=not clashes)
    metrics.update(missing_atoms=missing_atoms, covalent_violation_count=len(bond_errors),
                   covalent_violations=bond_errors[:20], angle_violation_count=len(angle_errors),
                   angle_violations=angle_errors[:20], severe_clash_count=len(clashes), severe_clashes=clashes[:20])
    if method == CYCLIC:
        metrics["closure_cn_angstrom"] = (_distance(binder[-1][1]["C"], binder[0][1]["N"])
                                           if binder and "C" in binder[-1][1] and "N" in binder[0][1] else None)
    return _finish(result)


def _finish(result):
    result["failed_checks"] = [key for key, value in result["checks"].items() if value is not True]
    result["candidate_quality_status"] = "pass" if not result["failed_checks"] else "fail"
    return result


def _rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def review_existing(root: Path = ROOT) -> dict[str, Any]:
    """Replay each existing supported candidate, then independently inspect quality.

    No historical result is rewritten. The existing v034 capture/replay machinery
    uses temporary copies; it never invokes model inference or container startup.
    """
    from scripts import parse_v034_generation_outputs as replay
    from scripts.run_pepglad_fresh_acceptance import acceptance_checks

    root = Path(root)
    jobs = {row["job_id"]: row for row in _rows(root / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv")}
    executions = _rows(root / "benchmark/deployment/pilot_execution_results_v0.34.csv")
    records = []
    for execution in executions:
        if execution["supported_candidate"] != "yes":
            continue
        job = jobs[execution["job_id"]]
        attempt = Path(execution["attempt_dir"])
        try:
            if replay._ACTIVE_CAPTURE_STORE is not None:
                raise RuntimeError("concurrent historical replay is not supported")
            store = replay._CaptureStore()
            replay._ACTIVE_CAPTURE_STORE = store
            try:
                candidate = replay._one_csv_row(attempt / "candidate_outputs.csv")
                supported = replay._supported(job, attempt, replay._json_object(attempt / "run_result.json") or {},
                    replay._one_csv_row(attempt / "method_output_manifest.csv"), candidate,
                    replay._one_csv_row(attempt / "candidate_qc.csv"), replay._runtime_provenance(job, attempt))
            finally:
                replay._ACTIVE_CAPTURE_STORE = None
                store.close()
            if candidate is None:
                raise ValueError("missing candidate")
            quality = evaluate_candidate(method=job["method"], sequence=candidate["sequence"],
                length_min=int(job["length_min"]), length_max=int(job["length_max"]),
                structure_path=candidate.get("structure_path"), binder_chain=candidate.get("binder_chain", "B"))
            quality.update(job_id=job["job_id"], attempt_dir=str(attempt), provenance_status="pass" if supported else "fail")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            quality = {"method": job["method"], "job_id": job["job_id"], "candidate_quality_status": "not_evaluated",
                       "provenance_status": "fail", "error": str(exc)}
        quality["method_acceptance_status"] = "pass" if quality["candidate_quality_status"] == quality["provenance_status"] == "pass" else "not_passed"
        records.append(quality)
    bundle = json.loads((root / "benchmark/results/pepglad_fresh_connectivity_v1.json").read_text())
    try:
        replay_checks = acceptance_checks(bundle)
        candidate, job = bundle["candidate"], bundle["job"]
        quality = evaluate_candidate(method="PepGLAD", sequence=candidate["sequence"],
            length_min=job["length"], length_max=job["length"],
            structure_path=Path(bundle["execution"]["attempt_dir"]) / candidate["structure_path"], binder_chain=candidate["binder_chain"])
        quality.update(job_id=job["job_id"], attempt_dir=bundle["execution"]["attempt_dir"], provenance_checks=replay_checks,
                       provenance_status="pass" if all(replay_checks.values()) else "fail")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        quality = {"method": "PepGLAD", "candidate_quality_status": "not_evaluated", "provenance_status": "fail", "error": str(exc)}
    quality["method_acceptance_status"] = "pass" if quality["candidate_quality_status"] == quality["provenance_status"] == "pass" else "not_passed"
    records.append(quality)
    return {"criteria": criteria(), "criteria_sha256": criteria_sha256(), "records": records,
            "method_pass_count": len({r["method"] for r in records if r["method_acceptance_status"] == "pass"}),
            "limitations": ["Reduced historical sampling schedules are retained; this review does not assert native default-quality equivalence.",
                            "No method-native efficacy filter is inferred from structural integrity.",
                            "D-Flow 3EQS known training overlap remains fixture-only and ineligible for fair scoring."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--criteria", action="store_true", help="print prospective criteria without opening candidate files")
    args = parser.parse_args(argv)
    payload = {"criteria": criteria(), "criteria_sha256": criteria_sha256()} if args.criteria else review_existing()
    print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
