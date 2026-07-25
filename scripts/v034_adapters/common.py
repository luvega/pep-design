from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping


CANONICAL_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")
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


@dataclass(frozen=True)
class PDBAtom:
    record_type: str
    chain: str
    residue_key: tuple[str, str, str]
    resname: str
    atom_name: str
    x: float
    y: float
    z: float

    @property
    def xyz(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path, headers: Iterable[str], rows: Iterable[Mapping[str, Any]]
) -> None:
    fieldnames = list(headers)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=64)
def _verified_sha256(path_text: str, size: int, mtime_ns: int) -> str:
    del size, mtime_ns
    return sha256_file(Path(path_text))


def require_file_sha256(path: Path, expected: str, label: str) -> str:
    """Fail preflight when an external source or model asset changed."""

    path = Path(path)
    try:
        stat = path.stat()
    except OSError as exc:
        raise FileNotFoundError(f"missing {label}: {path}") from exc
    if not path.is_file() or stat.st_size <= 0:
        raise FileNotFoundError(f"missing {label}: {path}")
    observed = _verified_sha256(str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if observed != expected:
        raise ValueError(
            f"{label} SHA256 mismatch: expected {expected}, observed {observed}"
        )
    return observed


def require_clean_git_checkout(path: Path, expected_commit: str, label: str) -> str:
    path = Path(path)
    try:
        head = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"cannot verify {label} checkout: {path}") from exc
    if head != expected_commit:
        raise ValueError(
            f"{label} commit mismatch: expected {expected_commit}, observed {head}"
        )
    if dirty:
        raise ValueError(f"{label} checkout is dirty")
    return head


def _parse_pdb_atom_lines(lines: Iterable[str]) -> list[PDBAtom]:
    atoms: list[PDBAtom] = []
    for line in lines:
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 54:
            continue
        altloc = line[16].strip()
        if altloc not in {"", "A"}:
            continue
        chain = line[21].strip() or "_"
        resseq = line[22:26].strip()
        icode = line[26].strip()
        atoms.append(
            PDBAtom(
                record_type=line[:6].strip(),
                chain=chain,
                residue_key=(chain, resseq, icode),
                resname=line[17:20].strip().upper(),
                atom_name=line[12:16].strip().upper(),
                x=float(line[30:38]),
                y=float(line[38:46]),
                z=float(line[46:54]),
            )
        )
    return atoms


def parse_pdb_atoms(path: Path) -> list[PDBAtom]:
    return _parse_pdb_atom_lines(
        path.read_text(encoding="utf-8", errors="replace").splitlines()
    )


def _polymer_atoms(atoms: Iterable[PDBAtom]) -> list[PDBAtom]:
    residues: dict[tuple[str, str, str], list[PDBAtom]] = {}
    for atom in atoms:
        residues.setdefault(atom.residue_key, []).append(atom)
    selected: list[PDBAtom] = []
    for residue_atoms in residues.values():
        names = {atom.atom_name for atom in residue_atoms}
        if any(atom.record_type == "ATOM" for atom in residue_atoms) or {
            "N",
            "CA",
            "C",
        }.issubset(names):
            selected.extend(residue_atoms)
    return selected


def parse_pdb_chain_sequences(path: Path) -> dict[str, str]:
    sequences: dict[str, list[str]] = {}
    seen: set[tuple[str, str, str]] = set()
    for atom in _polymer_atoms(parse_pdb_atoms(path)):
        if atom.residue_key in seen:
            continue
        seen.add(atom.residue_key)
        sequences.setdefault(atom.chain, []).append(AA3_TO_1.get(atom.resname, "X"))
    return {chain: "".join(residues) for chain, residues in sequences.items()}


def validate_output_file(path: Path, raw_root: Path) -> dict[str, Any]:
    path = Path(path)
    raw_root = Path(raw_root)
    result: dict[str, Any] = {
        "status": "fail",
        "reason": "unknown",
        "sha256": "",
        "size_bytes": 0,
    }
    try:
        resolved = path.resolve(strict=True)
        root = raw_root.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, ValueError):
        result["reason"] = "missing_or_outside_raw_root"
        return result
    if path.is_symlink() or not path.is_file():
        result["reason"] = "not_regular_file"
        return result
    size = path.stat().st_size
    result["size_bytes"] = size
    if size <= 0:
        result["reason"] = "empty_file"
        return result
    result["sha256"] = sha256_file(path)
    if path.suffix.lower() == ".pdb":
        try:
            atoms = parse_pdb_atoms(path)
        except (OSError, UnicodeError, ValueError):
            result["reason"] = "pdb_parse_failed"
            return result
        if not atoms:
            result["reason"] = "pdb_has_no_atoms"
            return result
        if any(not all(math.isfinite(value) for value in atom.xyz) for atom in atoms):
            result["reason"] = "pdb_nonfinite_coordinate"
            return result
    result.update(status="pass", reason="validated")
    return result


def _subtract(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(a - b for a, b in zip(left, right))  # type: ignore[return-value]


def _cross(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _chirality_stats_from_atoms(atoms: Iterable[PDBAtom], chain: str) -> dict[str, Any]:
    residues: dict[tuple[str, str, str], dict[str, PDBAtom]] = {}
    names: dict[tuple[str, str, str], str] = {}
    for atom in _polymer_atoms(atoms):
        if atom.chain != chain:
            continue
        residues.setdefault(atom.residue_key, {})[atom.atom_name] = atom
        names[atom.residue_key] = atom.resname

    l_count = d_count = gly_count = unknown_count = 0
    for key, atoms in residues.items():
        if names[key] == "GLY":
            gly_count += 1
            continue
        if not all(name in atoms for name in ("N", "CA", "C", "CB")):
            unknown_count += 1
            continue
        ca = atoms["CA"].xyz
        n_vec = _subtract(atoms["N"].xyz, ca)
        c_vec = _subtract(atoms["C"].xyz, ca)
        cb_vec = _subtract(atoms["CB"].xyz, ca)
        signed_volume = _dot(_cross(n_vec, c_vec), cb_vec)
        if signed_volume > 0:
            l_count += 1
        elif signed_volume < 0:
            d_count += 1
        else:
            unknown_count += 1
    evaluable = l_count + d_count
    return {
        "evaluable": evaluable,
        "l_count": l_count,
        "d_count": d_count,
        "gly_count": gly_count,
        "unknown_count": unknown_count,
        "status": "pass" if evaluable > 0 and unknown_count == 0 else "fail",
    }


def chirality_stats(path: Path, chain: str) -> dict[str, Any]:
    return _chirality_stats_from_atoms(parse_pdb_atoms(path), chain)


def chirality_stats_from_pdb_bytes(payload: bytes, chain: str) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise TypeError("PDB payload must be bytes")
    atoms = _parse_pdb_atom_lines(
        payload.decode("utf-8", errors="replace").splitlines()
    )
    return _chirality_stats_from_atoms(atoms, chain)


def terminal_cn_distance(path: Path, chain: str) -> float | None:
    residues: dict[tuple[str, str, str], dict[str, PDBAtom]] = {}
    order: list[tuple[str, str, str]] = []
    for atom in _polymer_atoms(parse_pdb_atoms(path)):
        if atom.chain != chain:
            continue
        if atom.residue_key not in residues:
            residues[atom.residue_key] = {}
            order.append(atom.residue_key)
        residues[atom.residue_key][atom.atom_name] = atom
    if not order or "N" not in residues[order[0]] or "C" not in residues[order[-1]]:
        return None
    n_xyz = residues[order[0]]["N"].xyz
    c_xyz = residues[order[-1]]["C"].xyz
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(n_xyz, c_xyz)))


def _chain_residue_numbers(path: Path, chain: str) -> list[int]:
    numbers: list[int] = []
    seen: set[tuple[str, str, str]] = set()
    for atom in _polymer_atoms(parse_pdb_atoms(path)):
        if atom.chain != chain or atom.residue_key in seen:
            continue
        seen.add(atom.residue_key)
        try:
            numbers.append(int(atom.residue_key[1]))
        except ValueError:
            return []
    return numbers


def overall_qc_status(checks: Mapping[str, Any]) -> str:
    statuses = {str(value) for key, value in checks.items() if key.endswith("_status")}
    if not statuses or not statuses.issubset(
        {"pass", "warn", "fail", "not_applicable"}
    ):
        return "fail"
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "pass_with_warning"
    return "pass"


def _not_applicable() -> str:
    return "not_applicable"


def _is_sha256(value: Any) -> bool:
    text = str(value)
    return len(text) == 64 and all(
        character in "0123456789abcdef" for character in text.lower()
    )


def _fasta_records(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header = ""
    current: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            if header and current:
                records.append((header, "".join(current).upper()))
                current = []
            header = stripped[1:]
        else:
            current.append(stripped)
    if header and current:
        records.append((header, "".join(current).upper()))
    return records


def _bound_evidence_file(
    runtime_evidence: Mapping[str, Any],
    path_key: str,
    digest_key: str,
    raw_root: Path,
) -> tuple[bool, Path | None]:
    path_text = str(runtime_evidence.get(path_key, ""))
    expected_digest = str(runtime_evidence.get(digest_key, ""))
    if not path_text or not _is_sha256(expected_digest):
        return False, None
    path = Path(path_text)
    validation = validate_output_file(path, raw_root)
    return (
        validation["status"] == "pass" and validation["sha256"] == expected_digest,
        path,
    )


def _source_file_matches(
    path_text: str, expected_digest: str
) -> tuple[bool, Path | None]:
    if not path_text or not _is_sha256(expected_digest):
        return False, None
    path = Path(path_text)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
            return False, None
        return sha256_file(path) == expected_digest, path
    except OSError:
        return False, None


def _central_inversion_correspondence(
    source_path: Path | None,
    mirrored_path: Path | None,
    *,
    tolerance: float = 0.002,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "atom_identity_status": "fail",
        "central_inversion_status": "fail",
        "atom_count": 0,
        "max_residual": "",
        "tolerance": f"{tolerance:.3f}",
    }
    if source_path is None or mirrored_path is None:
        return result
    try:
        source_lines = source_path.read_text(encoding="utf-8").splitlines()
        mirrored_lines = mirrored_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError, ValueError):
        return result

    def records(
        lines: list[str],
    ) -> list[tuple[tuple[str, str], tuple[float, float, float]]] | None:
        parsed: list[tuple[tuple[str, str], tuple[float, float, float]]] = []
        for line in lines:
            if not line.startswith(("ATOM  ", "HETATM")):
                continue
            try:
                xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            except (ValueError, IndexError):
                return None
            parsed.append(((line[:30], line[54:]), xyz))
        return parsed

    source_records = records(source_lines)
    mirrored_records = records(mirrored_lines)
    if source_records is None or mirrored_records is None or not source_records:
        return result
    source_identities = [identity for identity, _ in source_records]
    mirrored_identities = [identity for identity, _ in mirrored_records]
    if source_identities != mirrored_identities:
        return result
    result["atom_identity_status"] = "pass"
    result["atom_count"] = len(source_records)
    center = tuple(
        sum(xyz[axis] for _, xyz in source_records) / len(source_records)
        for axis in range(3)
    )
    residuals = []
    for (_, source_xyz), (_, mirrored_xyz) in zip(source_records, mirrored_records):
        expected = tuple(2.0 * center[axis] - source_xyz[axis] for axis in range(3))
        residuals.append(
            math.sqrt(
                sum(
                    (observed - wanted) ** 2
                    for observed, wanted in zip(mirrored_xyz, expected)
                )
            )
        )
    maximum = max(residuals)
    result["max_residual"] = f"{maximum:.6f}"
    result["central_inversion_status"] = "pass" if maximum <= tolerance else "fail"
    return result


def _is_ordered_subsequence(candidate: str, reference: str) -> bool:
    if not candidate or not reference or len(candidate) >= len(reference):
        return False
    positions = iter(reference)
    return all(residue in positions for residue in candidate)


def evaluate_candidate_qc(
    job: Mapping[str, str],
    candidate: Mapping[str, str],
    runtime_evidence: Mapping[str, Any],
    raw_root: Path,
) -> dict[str, Any]:
    sequence = candidate.get("sequence", "").strip().upper()
    noncanonical = sorted({aa for aa in sequence if aa not in CANONICAL_AA})
    structure_text = candidate.get("structure_path", "").strip()
    source_text = candidate.get("source_output_path", "").strip()
    output_path = (
        Path(structure_text or source_text) if (structure_text or source_text) else None
    )
    structure_path = Path(structure_text) if structure_text else None

    file_result = (
        validate_output_file(output_path, raw_root)
        if output_path is not None
        else {
            "status": "fail",
            "reason": "missing_output_file",
            "sha256": "",
            "size_bytes": 0,
        }
    )
    checks: dict[str, Any] = {
        "file_status": file_result["status"],
        "file_reason": file_result["reason"],
        "file_sha256": file_result.get("sha256", ""),
        "file_size_bytes": file_result.get("size_bytes", 0),
    }
    parse_value = candidate.get("parse_status", "")
    checks["parse_status"] = (
        "pass"
        if parse_value == "parsed" or (parse_value == "partial" and bool(noncanonical))
        else "fail"
    )

    expected_binder = job.get("expected_binder_chain", "")
    expected_target = job.get("expected_target_chain", "")
    pdb_sequence = ""
    if structure_path is None or expected_binder in {"", "not_applicable"}:
        checks["chain_status"] = _not_applicable()
    elif file_result["status"] != "pass":
        checks["chain_status"] = "fail"
    else:
        chains = parse_pdb_chain_sequences(structure_path)
        pdb_sequence = chains.get(expected_binder, "")
        binder_ok = expected_binder in chains and bool(chains[expected_binder])
        target_ok = expected_target in {"", "not_applicable"} or (
            expected_target in chains and expected_target != expected_binder
        )
        observed_binder = candidate.get("binder_chain", expected_binder)
        checks["chain_status"] = (
            "pass"
            if binder_ok and target_ok and observed_binder == expected_binder
            else "fail"
        )

    target_binding_mode = job.get("target_binding_check_mode", "not_applicable")
    if target_binding_mode == "not_applicable":
        checks["target_binding_status"] = _not_applicable()
    elif structure_path is None or file_result["status"] != "pass":
        checks["target_binding_status"] = "fail"
    else:
        source_ok, source_path = _source_file_matches(
            job.get("target_pdb_path", ""), job.get("target_pdb_sha256", "")
        )
        input_chain = job.get("target_chains", "").replace(",", ";").split(";")[0]
        output_target_sequence = parse_pdb_chain_sequences(structure_path).get(
            expected_target, ""
        )
        source_target_sequence = (
            parse_pdb_chain_sequences(source_path).get(input_chain, "")
            if source_ok and source_path is not None and input_chain
            else ""
        )
        if target_binding_mode == "sequence_and_sha256":
            target_binding_ok = (
                source_ok
                and bool(source_target_sequence)
                and output_target_sequence == source_target_sequence
            )
        elif target_binding_mode == "pocket_subsequence_and_sha256":
            context_ok, context_path = _bound_evidence_file(
                runtime_evidence,
                "target_context_path",
                "target_context_sha256",
                raw_root,
            )
            context_chain = str(
                runtime_evidence.get("target_context_chain", expected_target)
            )
            context_sequence = (
                parse_pdb_chain_sequences(context_path).get(context_chain, "")
                if context_ok and context_path is not None
                else ""
            )
            target_binding_ok = all(
                (
                    source_ok,
                    context_ok,
                    runtime_evidence.get("target_context_mode")
                    == "ordered_subsequence",
                    bool(source_target_sequence),
                    context_sequence == output_target_sequence,
                    _is_ordered_subsequence(context_sequence, source_target_sequence),
                )
            )
        else:
            target_binding_ok = False
        checks["target_binding_status"] = "pass" if target_binding_ok else "fail"

    try:
        minimum = int(job.get("length_min", "0"))
        maximum = int(job.get("length_max", "0"))
    except ValueError:
        minimum = maximum = -1
    checks["length_status"] = (
        "pass" if sequence and minimum <= len(sequence) <= maximum else "fail"
    )
    checks["sequence_length"] = len(sequence)

    if job.get("method") == "RFdiffusion + ProteinMPNN":
        checks["sequence_structure_status"] = _not_applicable()
    elif (
        structure_path is None
        or expected_binder in {"", "not_applicable"}
        or file_result["status"] != "pass"
    ):
        checks["sequence_structure_status"] = (
            _not_applicable() if structure_path is None else "fail"
        )
    else:
        if not pdb_sequence:
            pdb_sequence = parse_pdb_chain_sequences(structure_path).get(
                expected_binder, ""
            )
        pdb_noncanonical = sorted({aa for aa in pdb_sequence if aa not in CANONICAL_AA})
        combined_noncanonical = sorted(set(noncanonical) | set(pdb_noncanonical))
        sequence_matches = pdb_sequence == sequence
        unknown_only_mismatch = (
            len(pdb_sequence) == len(sequence)
            and bool(combined_noncanonical)
            and all(
                left == right or left == "X" or right == "X"
                for left, right in zip(pdb_sequence, sequence)
            )
        )
        checks["sequence_structure_status"] = (
            "pass"
            if sequence_matches and pdb_sequence
            else "warn" if unknown_only_mismatch else "fail"
        )

    chirality_mode = job.get("chirality_check_mode", "not_applicable")
    if chirality_mode == "not_applicable":
        checks["chirality_status"] = _not_applicable()
    elif structure_path is None or file_result["status"] != "pass":
        checks["chirality_status"] = "fail"
    else:
        chain = job.get("expected_binder_chain", "")
        stats = chirality_stats(structure_path, chain)
        expected = job.get("chirality", "")
        expected_count = (
            stats["l_count"]
            if expected == "L"
            else stats["d_count"] if expected == "D" else -1
        )
        checks["chirality_status"] = (
            "pass"
            if stats["status"] == "pass"
            and expected_count == stats["evaluable"]
            and stats["evaluable"] > 0
            else "fail"
        )
        checks.update(
            {
                f"chirality_{key}": value
                for key, value in stats.items()
                if key != "status"
            }
        )

    if job.get("cyclic", "no") != "yes":
        checks["cyclic_status"] = _not_applicable()
    elif structure_path is None or file_result["status"] != "pass":
        checks["cyclic_status"] = "fail"
    else:
        offset_applied = runtime_evidence.get("cyclic_offset_applied") is True
        try:
            offset_valid = abs(float(runtime_evidence.get("terminal_offset", 0))) == 1.0
        except (TypeError, ValueError):
            offset_valid = False
        distance = terminal_cn_distance(
            structure_path, job.get("expected_binder_chain", "")
        )
        checks["terminal_cn_distance"] = "" if distance is None else f"{distance:.3f}"
        checks["cyclic_status"] = (
            "pass"
            if offset_applied
            and offset_valid
            and distance is not None
            and 0.9 <= distance <= 2.0
            else "fail"
        )

    pdb_noncanonical = sorted({aa for aa in pdb_sequence if aa not in CANONICAL_AA})
    combined_noncanonical = sorted(set(noncanonical) | set(pdb_noncanonical))
    checks["noncanonical_status"] = "warn" if combined_noncanonical else "pass"
    checks["noncanonical_residues"] = "".join(combined_noncanonical)

    if job.get("effective_seed_required") == "yes":
        try:
            requested = int(job.get("random_seed", ""))
            recorded_requested = int(runtime_evidence.get("requested_seed", -1))
            effective = int(runtime_evidence.get("effective_seed", -1))
        except (TypeError, ValueError):
            requested = recorded_requested = effective = -1
        checks["seed_status"] = (
            "pass"
            if requested >= 0
            and requested == recorded_requested == effective
            and runtime_evidence.get("seed_control_status") == "honored"
            else "fail"
        )
    else:
        checks["seed_status"] = _not_applicable()

    method = job.get("method", "")
    if method == "D-Flow / PeptideDesign":
        checks["method_contract_status"] = (
            "pass" if runtime_evidence.get("x_mirror_applied") is True else "fail"
        )
    elif method == "PepMirror":
        input_ok, input_path = _bound_evidence_file(
            runtime_evidence, "mirror_input_path", "mirror_input_sha256", raw_root
        )
        target_ok, target_path = _bound_evidence_file(
            runtime_evidence, "mirrored_target_path", "mirrored_target_sha256", raw_root
        )
        generated_ok, generated_path = _bound_evidence_file(
            runtime_evidence,
            "mirrored_generated_path",
            "mirrored_generated_sha256",
            raw_root,
        )
        output_ok, output_path = _bound_evidence_file(
            runtime_evidence, "mirror_output_path", "mirror_output_sha256", raw_root
        )
        input_digest = runtime_evidence.get("mirror_input_sha256")
        mirrored_digest = runtime_evidence.get("mirrored_target_sha256")
        target_geometry = _central_inversion_correspondence(input_path, target_path)
        output_geometry = _central_inversion_correspondence(generated_path, output_path)
        checks["mirror_target_atom_identity_status"] = target_geometry[
            "atom_identity_status"
        ]
        checks["mirror_target_central_inversion_status"] = target_geometry[
            "central_inversion_status"
        ]
        checks["mirror_target_atom_count"] = target_geometry["atom_count"]
        checks["mirror_target_central_inversion_max_residual"] = target_geometry[
            "max_residual"
        ]
        checks["mirror_target_central_inversion_tolerance"] = target_geometry[
            "tolerance"
        ]
        checks["mirror_output_atom_identity_status"] = output_geometry[
            "atom_identity_status"
        ]
        checks["mirror_output_central_inversion_status"] = output_geometry[
            "central_inversion_status"
        ]
        checks["mirror_output_atom_count"] = output_geometry["atom_count"]
        checks["mirror_output_central_inversion_max_residual"] = output_geometry[
            "max_residual"
        ]
        checks["mirror_output_central_inversion_tolerance"] = output_geometry[
            "tolerance"
        ]
        mirror_ok = (
            runtime_evidence.get("mirror_roundtrip_applied") is True
            and input_ok
            and target_ok
            and generated_ok
            and output_ok
            and input_path is not None
            and output_path is not None
            and input_digest == job.get("target_pdb_sha256")
            and input_digest != mirrored_digest
            and target_geometry["atom_identity_status"] == "pass"
            and target_geometry["central_inversion_status"] == "pass"
            and output_geometry["atom_identity_status"] == "pass"
            and output_geometry["central_inversion_status"] == "pass"
            and structure_path is not None
            and output_path.resolve() == structure_path.resolve()
        )
        checks["method_contract_status"] = "pass" if mirror_ok else "fail"
    else:
        checks["method_contract_status"] = "pass"

    if method == "RFdiffusion + ProteinMPNN":
        backbone_ok, backbone_path = _bound_evidence_file(
            runtime_evidence, "rf_backbone_path", "rf_backbone_sha256", raw_root
        )
        trb_ok, trb_path = _bound_evidence_file(
            runtime_evidence, "rf_trb_path", "rf_trb_sha256", raw_root
        )
        fasta_ok, fasta_path = _bound_evidence_file(
            runtime_evidence, "mpnn_fasta_path", "mpnn_fasta_sha256", raw_root
        )
        hotspots = runtime_evidence.get("rf_hotspots", [])
        if isinstance(hotspots, str):
            hotspots = [
                token for token in hotspots.replace(",", ";").split(";") if token
            ]
        fixed_chains = runtime_evidence.get("mpnn_fixed_chains", [])
        if isinstance(fixed_chains, str):
            fixed_chains = [
                token for token in fixed_chains.replace(",", ";").split(";") if token
            ]
        fasta_sequence_ok = False
        if fasta_ok and fasta_path is not None:
            selected_id = str(runtime_evidence.get("mpnn_selected_record_id", ""))
            for header, fasta_sequence in _fasta_records(fasta_path):
                record_id = header.split(",", 1)[0].split()[0]
                generated_header = (
                    "sample=" in header
                    or " T=" in f" {header}"
                    or ("_b" in record_id and "_d" in record_id)
                )
                if record_id == selected_id:
                    fasta_sequence_ok = (
                        fasta_sequence == sequence
                        and generated_header
                        and runtime_evidence.get("mpnn_record_type")
                        == "generated_sample"
                    )
                    break
        candidate_backbone_ok = False
        backbone_binder_length_ok = False
        target_segment_ok = False
        if backbone_ok and backbone_path is not None and structure_path is not None:
            candidate_backbone_ok = backbone_path.resolve() == structure_path.resolve()
            backbone_binder_length_ok = len(
                parse_pdb_chain_sequences(backbone_path).get("B", "")
            ) == len(sequence)
            target_segment_ok = _chain_residue_numbers(backbone_path, "A") == list(
                range(3, 118)
            )
        trb_semantics = runtime_evidence.get("rf_trb_semantic_extract")
        trb_semantics_ok = False
        observed_trb_semantics: Mapping[str, Any] | None = None
        if trb_ok and trb_path is not None:
            try:
                from .rfdiffusion_mpnn import extract_rf_trb_semantics

                observed_trb_semantics = extract_rf_trb_semantics(trb_path)
            except (ImportError, ValueError):
                observed_trb_semantics = None
        if (
            isinstance(trb_semantics, Mapping)
            and observed_trb_semantics == trb_semantics
        ):
            semantic_digest = hashlib.sha256(
                json.dumps(
                    dict(trb_semantics), sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            trb_semantics_ok = all(
                (
                    runtime_evidence.get("rf_trb_semantic_parser")
                    == "pickletools_literal_scan_v1",
                    runtime_evidence.get("rf_trb_semantic_sha256") == semantic_digest,
                    trb_semantics.get("input_pdb") == "/data/input/7zkr_GABARAP.pdb",
                    trb_semantics.get("num_designs") == 1,
                    trb_semantics.get("design_startnum")
                    == int(job.get("random_seed", "-1")),
                    trb_semantics.get("deterministic") is True,
                    trb_semantics.get("cyclic") is False,
                    trb_semantics.get("contigs") == ["A3-117/0 70-100"],
                    trb_semantics.get("hotspot_res")
                    == ["A48", "A50", "A51", "A52", "A62", "A65"],
                    trb_semantics.get("sampled_mask")
                    == ["A3-117/0", f"{len(sequence)}-{len(sequence)}"],
                )
            )
        representation_ok = all(
            (
                runtime_evidence.get("structure_representation")
                == "unthreaded_rf_backbone",
                runtime_evidence.get("sequence_representation")
                == "proteinmpnn_generated_fasta",
                runtime_evidence.get("sequence_threaded_onto_backbone") is False,
            )
        )
        handoff_ok = all(
            (
                backbone_ok,
                trb_ok,
                trb_semantics_ok,
                fasta_ok,
                fasta_sequence_ok,
                candidate_backbone_ok,
                backbone_binder_length_ok,
                target_segment_ok,
                representation_ok,
                runtime_evidence.get("rf_target_conditioned") is True,
                runtime_evidence.get("rf_contig") == "[A3-117/0 70-100]",
                set(hotspots) == {"A48", "A50", "A51", "A52", "A62", "A65"},
                runtime_evidence.get("mpnn_designed_chain") == "B",
                set(fixed_chains) == {"A"},
            )
        )
        checks["backbone_to_fasta_handoff_status"] = "pass" if handoff_ok else "fail"
        checks["handoff_status"] = "pass" if handoff_ok else "fail"
    else:
        checks["backbone_to_fasta_handoff_status"] = _not_applicable()
        checks["handoff_status"] = _not_applicable()

    checks["overall_qc_status"] = overall_qc_status(checks)
    failed = [
        key
        for key, value in checks.items()
        if key.endswith("_status") and value == "fail"
    ]
    warned = [
        key
        for key, value in checks.items()
        if key.endswith("_status") and value == "warn"
    ]
    checks["status_reason"] = ";".join(failed or warned) or "all_required_checks_passed"
    return checks
