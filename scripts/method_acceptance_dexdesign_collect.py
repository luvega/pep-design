#!/usr/bin/env python3
"""Collect native DexDesign outputs with an explicit residue-label I/O repair.

The native executor remains frozen. Empty native ensembles fail individually.
Only PDB columns 18--20 may change, from the same native sequence assignments;
every model's exact heavy-atom set must agree before a derivative is accepted.
No coordinates, atoms, scores, search settings or native assignments change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import method_acceptance_dexdesign as native
from scripts.method_acceptance_quality import SIDECHAINS, criteria_sha256
from scripts.v034_adapters.common import AA3_TO_1

FORMAT_POLICY = {
    "kind": "native_candidate_residue_label_format_repair",
    "changed_bytes": "only PDB residue-name columns 18-20 (zero-based17:20)",
    "assignment_source": "same native_search_results.json row sequence_assignments",
    "atom_validation": "every MODEL and residue: exact assigned canonical heavy-atom names, plus optional terminal OXT",
    "coordinate_or_atom_changes": "forbidden",
    "raw_preservation": "retain original mislabelled/empty PDB and its SHA256",
    "selection": native.NATIVE_QUALITY["ensemble_selection"],
    "source_explanation": "AssignedCoords.java:242-266 chooses assigned-conf atom names/coordinates; :342 writes resInfo.resType",
}


NATIVE_SCOPE = {
    "endpoint": "one independent native IAS K* design search: ALA5, all 19 sequence outcomes",
    "selection_basis": "reuse the first fully completed native IAS group from the infrastructure-interrupted batch; no search rerun",
    "reuse_known_results": True,
    "input": "experimental 3LNJ A/B coordinate-resolved D/L complex",
    "required_chain": "native preprocessing, conformation-space compilation, complete ALA5 K* search, explicit output-format repair and candidate QC",
    "batch_status": "11 IAS compiled; ALA5 complete; ARG12 partial; remaining 9 not searched",
    "excludes": ["all_11_IAS_completed", "cross_IAS_consensus_or_optimization", "whole_paper_reproduction", "optimized_inhibitor_or_affinity_claim"],
}


def file_hash(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"expected regular artifact: {path}")
    return native.sha256(path)


def initial_identities(config: dict[str, Any]) -> dict[tuple[str, str], str]:
    return {(chain, residue): name for chain in ("z", "y")
            for residue, name in native.residue_identities(Path(config["input_pdb"]), chain).items()}


def complete_native_assignments(row: dict[str, Any], group: Path,
                                initial: dict[tuple[str, str], str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recover fixed WT positions which native SeqSpace omits from its string."""
    paths = list(group.glob("*peptide.confspace"))
    if len(paths) != 1:
        raise ValueError("missing or ambiguous native peptide confspace")
    path = paths[0]
    positions = tomllib.loads(path.read_text())["confspace"]["positions"]
    assignments = [dict(x) for x in row["sequence_assignments"]]
    names = {a["position"] for a in assignments}
    added = []
    for position in positions.values():
        name = position["name"]
        parts = name.split()
        if len(parts) != 2 or initial.get(("y", parts[0])) != parts[1]:
            raise ValueError("native peptide position not bound to input")
        mutations = position["confspace"]["mutations"]
        existing = [a for a in assignments if a["position"] == name]
        if existing and (len(existing) != 1 or existing[0]["residue_type"] not in mutations):
            raise ValueError("native assignment outside compiled conformation space")
        if name not in names:
            if mutations != [parts[1]]:
                raise ValueError("missing mutable native sequence position")
            assignment = {"position": name, "residue_type": parts[1]}
            assignments.append(assignment)
            added.append(assignment)
    if len(positions) != sum(chain == "y" for chain, _ in initial):
        raise ValueError("native peptide conformation space does not cover the binder")
    return {**row, "sequence_assignments": assignments}, {
        "native_confspace_path": str(path), "native_confspace_sha256": file_hash(path),
        "fixed_native_positions_omitted_by_seqspace": added,
        "raw_sequence_assignments_unchanged": True,
    }


def normalize_labels(payload: bytes, assignments: list[dict[str, str]],
                     initial: dict[tuple[str, str], str]) -> tuple[bytes, dict[str, Any]]:
    """Normalize verified exporter metadata, with no structural reconstruction."""
    by_id: dict[str, tuple[str, str]] = {}
    for key in initial:
        if key[1] in by_id:
            raise ValueError("ambiguous native position names across chains")
        by_id[key[1]] = key
    expected = dict(initial)
    assigned = set()
    for assignment in assignments:
        parts = assignment.get("position", "").split()
        identity = assignment.get("residue_type", "").upper()
        if (len(parts) != 2 or parts[0] not in by_id or identity not in AA3_TO_1
                or initial[by_id[parts[0]]] != parts[1] or parts[0] in assigned):
            raise ValueError("invalid/ambiguous native sequence assignment")
        assigned.add(parts[0])
        expected[by_id[parts[0]]] = identity
    if any(residue not in assigned for chain, residue in initial if chain == "y"):
        raise ValueError("native assignments do not cover the complete binder")
    terminal = {chain: [key for key in initial if key[0] == chain][-1] for chain in {key[0] for key in initial}}
    models: list[dict[tuple[str, str], set[str]]] = []
    identities: set[tuple[tuple[str, str], str]] = set()
    current = None
    changes = []
    output = []
    for number, line in enumerate(payload.splitlines(keepends=True), 1):
        if line.startswith(b"MODEL "):
            if current is not None:
                raise ValueError("nested native MODEL")
            current = {}
            identities = set()
        elif line.startswith(b"ENDMDL"):
            if current is None or not current:
                raise ValueError("empty or unmatched native MODEL")
            models.append(current)
            current = None
        elif line.startswith((b"ATOM  ", b"HETATM")):
            if current is None or len(line) < 78:
                raise ValueError("native atom outside MODEL or truncated PDB atom")
            key = (line[21:22].decode(), line[22:27].decode().strip())
            atom = line[12:16].decode().strip()
            element = line[76:78].decode().strip()
            if key not in expected or (key, atom) in identities or line[16:17] != b" ":
                raise ValueError("unexpected residue, alternate atom or duplicate identity")
            identities.add((key, atom))
            current.setdefault(key, set())
            if element not in {"H", "D"}:
                if element not in {"C", "N", "O", "S"}:
                    raise ValueError("unrecognized native atom element")
                current[key].add(atom)
            old = line[17:20].decode()
            new = expected[key]
            if old not in {initial[key], new}:
                raise ValueError("native residue label is unrelated to input or assignment")
            changed = line[:17] + new.encode() + line[20:]
            if changed[:17] != line[:17] or changed[20:] != line[20:]:
                raise AssertionError("format repair modified non-label bytes")
            if old != new:
                changes.append({"line": number, "chain": key[0], "residue": key[1], "old": old, "new": new})
            line = changed
        output.append(line)
    if current is not None or not models:
        raise ValueError("native PDB contains no complete coordinate model")
    for index, model in enumerate(models, 1):
        if set(model) != set(expected):
            raise ValueError(f"native MODEL {index} residue set differs from the input")
        for key, names in model.items():
            letter = AA3_TO_1[expected[key]]
            required = {"N", "CA", "C", "O"}
            required.update(atom for bond in SIDECHAINS[letter].split() for atom in bond.split("-"))
            if "OXT" in names and key == terminal[key[0]]:
                required.add("OXT")
            if names != required:
                raise ValueError(f"native MODEL {index} {key} atom set incompatible with {expected[key]}: "
                                 f"missing={sorted(required - names)} extra={sorted(names - required)}")
    normalized = b"".join(output)
    return normalized, {"model_count": len(models), "changed_atom_lines": changes,
                        "all_models_exact_assigned_heavy_atoms": True,
                        "only_residue_name_columns_changed": True,
                        "source_sha256": hashlib.sha256(payload).hexdigest(),
                        "normalized_sha256": hashlib.sha256(normalized).hexdigest()}


def snapshot_parent(parent: Path, destination: Path) -> dict[str, Any]:
    """Pin post-interruption evidence; never infer or fabricate native exit codes."""
    parent = parent.resolve()
    receipt = json.loads(native.regular(parent / "run_result.json").read_text())
    if not receipt.get("cleanup", {}).get("confirmed") or receipt.get("exit_code") != 127:
        raise ValueError("expected the stopped, confirmed-cleanup interrupted parent")
    files = {str(p.relative_to(parent)): file_hash(p) for p in sorted(parent.rglob("*")) if p.is_file()}
    report = {"parent_attempt": str(parent), "parent_exit_code": receipt["exit_code"],
              "parent_termination_reason": receipt["termination_reason"],
              "created_after_interruption": True, "files_sha256": files,
              "does_not_create_missing_native_exit_codes": True}
    native.write_json_new(destination, report)
    return {"snapshot_path": str(destination.resolve()), "sha256": file_hash(destination), "file_count": len(files)}


def parent_context(attempt: Path, snapshot_path: Path) -> tuple[dict[str, Any], dict[str, Any], list[Path]]:
    attempt = attempt.resolve()
    output = attempt / "raw"
    job = json.loads(native.regular(attempt / "job.json").read_text())
    result = json.loads(native.regular(attempt / "run_result.json").read_text())
    launch = json.loads(native.regular(attempt / "launch.json").read_text())
    snapshot = json.loads(native.regular(snapshot_path).read_text())
    stage = Path(job["argv"][job["argv"].index("--stage-dir") + 1])
    config = json.loads(native.regular(stage / "config.json").read_text())
    group = output / "work/case/ALA5"
    payload = json.loads(native.regular(group / "native_search_results.json").read_text())
    checks = {
        "parent_job_method": job.get("method") == "dexdesign" and job.get("kind") == "method",
        "parent_receipt_binding": result.get("job_sha256") == file_hash(attempt / "job.json")
            and result.get("job_id") == job.get("job_id"),
        "parent_infrastructure_failure_preserved": result.get("exit_code") == 127
            and "FileNotFoundError" in result.get("termination_reason", "")
            and "complex.confdb.wal.0" in result.get("termination_reason", "")
            and result.get("cleanup", {}).get("confirmed") is True,
        "parent_log_binding": all(result.get(f"{name}_sha256") == file_hash(attempt / f"{name}.log")
                                  for name in ("stdout", "stderr")),
        "parent_policy_binding": result.get("policy_sha256") == launch.get("policy_sha256"),
        "parent_declared_input_pins": all(file_hash(Path(p)) == h for p, h in job["input_sha256"].items()),
        "parent_adapter_frozen": job["input_sha256"].get(str(Path(native.__file__).resolve())) == file_hash(Path(native.__file__)),
        "parent_source_pins": native.source_manifest(Path(config["source_dir"])) == config["source_files_sha256"],
        "parent_stage_pins": all(file_hash(stage / name) == h for name, h in config["staged_scripts_sha256"].items()),
        "parent_runtime_pins": native.verify_runtime_files(config),
        "parent_quality_policy": job.get("quality_contract", {}).get("native") == native.NATIVE_QUALITY
            and config.get("structural_criteria_sha256") == criteria_sha256(),
        "post_interruption_snapshot": snapshot.get("parent_attempt") == str(attempt)
            and snapshot.get("created_after_interruption") is True
            and bool(snapshot.get("files_sha256")) and all(
                (attempt / p).resolve().is_relative_to(attempt) and file_hash(attempt / p) == h
                for p, h in snapshot["files_sha256"].items()),
        "staged_native_work_scripts": all(file_hash(output / "work" / name) == h
                                           for name, h in config["staged_scripts_sha256"].items()),
        "input_copy_bound": file_hash(output / "work/input/case-complex.pdb") == config["input_sha256"],
    }
    checks["native_preprocess_completed"] = (output / "work/prepared-PDBs/case-D-L-complex.pdb").is_file() and         "successfully completed PDB preprocessing" in (output / "preprocess.stdout.log").read_text()
    all_groups = sorted((output / "work/case").glob("*/"))
    checks["native_compile_completed"] = (len(all_groups) == 11
        and all(len(list(g.glob(f"*{kind}.ccsx"))) == 1 for g in all_groups for kind in ("target", "peptide", "complex"))
        and "completed IAS preparations successfully" in (output / "compile.stdout.log").read_text())
    checks["one_ias_complete_native_search"] = (group.name == "ALA5" and payload.get("epsilon") == 0.68
        and len(payload.get("rows", [])) == 19 and len((group / "sequences.tsv").read_text().splitlines()) == 20
        and "KStar runtime was " in (output / "kstar_000.stdout.log").read_text())
    # The frozen executor invokes each subprocess with a return-code check and
    # only starts ARG12 after ALA5 returns successfully. This is control-flow
    # evidence, not an invented subprocess receipt or exit-code field.
    checks["frozen_wrapper_advanced_after_ala5"] = "computing K* scores for 19 sequences" in (output / "kstar_001.stdout.log").read_text()
    context = {"checks": checks, "passed": all(checks.values()), "parent_attempt": str(attempt),
               "parent_snapshot_path": str(snapshot_path.resolve()), "parent_snapshot_sha256": file_hash(snapshot_path),
               "parent_exit_code": result["exit_code"], "parent_termination_reason": result["termination_reason"],
               "completion_evidence": "native completion logs and frozen wrapper's checked transition to ARG12; no native exit code fabricated",
               "native_scope": NATIVE_SCOPE,
               "observed_batch_status": {"compiled_ias_groups": 11, "complete_native_search_groups": ["ALA5"],
                    "partial_native_search_groups": ["ARG12"], "not_searched_groups": [g.name for g in all_groups if g.name not in {"ALA5", "ARG12"}]}}
    return context, config, [group]


def collect(parent: Path, snapshot: Path, output: Path) -> dict[str, Any]:
    job = native.runner_binding(output)
    if (job.get("quality_contract", {}).get("format_repair") != FORMAT_POLICY
            or job["quality_contract"].get("native_scope") != NATIVE_SCOPE):
        raise ValueError("collector format policy must be declared before launch")
    for path in (Path(__file__).resolve(), snapshot, parent / "run_result.json"):
        if job.get("input_sha256", {}).get(str(path.resolve())) != file_hash(path):
            raise ValueError("collector must pin itself and parent execution/receipt")
    context, config, groups = parent_context(parent, snapshot)
    if not context["passed"]:
        raise ValueError("parent native chain is incomplete: " + repr(context["checks"]))
    output.mkdir(parents=True, exist_ok=False)
    records = []
    initial = initial_identities(config)
    for group in groups:
        scores = group / "native_search_results.json"
        for index, row in enumerate(json.loads(scores.read_text())["rows"]):
            record: dict[str, Any] = {"ias_group": group.name, "row_index": index,
                "native_row": row, "native_scores_path": str(scores), "native_scores_sha256": file_hash(scores), "passed": False}
            try:
                if not native.native_score_is_eligible(row):
                    raise ValueError("native K* not converged with finite ordered bounds")
                raw = group / row["structure_file"]
                if not raw.resolve().is_relative_to(group.resolve()):
                    raise ValueError("native ensemble escapes its IAS group")
                record.update(raw_ensemble_path=str(raw), raw_ensemble_sha256=file_hash(raw))
                full_row, fixed = complete_native_assignments(row, group, initial)
                normalized, proof = normalize_labels(raw.read_bytes(), full_row["sequence_assignments"], initial)
                folder = output / "candidates" / f"{group.name}_{index:02d}"
                folder.mkdir(parents=True, exist_ok=False)
                repaired = folder / "native_labels_repaired.pdb"
                repaired.write_bytes(normalized)
                selected = folder / "first_native_conformation.pdb"
                selected.write_bytes(native.first_conformation(normalized))
                quality = native.candidate_checks(full_row, config, selected)
                record.update(format_proof=proof, fixed_position_provenance=fixed, normalized_ensemble_path=str(repaired.resolve()),
                    normalized_ensemble_sha256=file_hash(repaired), first_conformation_path=str(selected.resolve()),
                    first_conformation_sha256=file_hash(selected), quality=quality, passed=quality["passed"])
            except (OSError, ValueError, KeyError, TypeError) as exc:
                record.update(failure_type=type(exc).__name__, failure_reason=str(exc))
            records.append(record)
    report = {"method": native.METHOD, "parent_context": context, "format_policy": FORMAT_POLICY,
        "records": records, "candidate_count": len(records), "qualified_candidate_count": sum(x["passed"] for x in records),
        "collector_job_id": job["job_id"], "structural_criteria_sha256": criteria_sha256(),
        "status": "collected_requires_receipt_replay"}
    native.write_json_new(output / "collection.json", report)
    return report


def verify(attempt: Path | str) -> dict[str, Any]:
    attempt = Path(attempt).resolve()
    if (attempt / "collection.json").is_file():
        attempt = attempt.parent
    output = attempt / "raw"
    checks: dict[str, bool] = {}
    records = []
    result: dict[str, Any] = {"method": native.METHOD, "passed": False, "qualified_candidate_count": 0,
        "records": records, "checks": checks, "failedchecks": []}
    try:
        report = json.loads(native.regular(output / "collection.json").read_text())
        receipt = json.loads(native.regular(attempt / "run_result.json").read_text())
        job = json.loads(native.regular(attempt / "job.json").read_text())
        checks["collector_completed"] = receipt.get("exit_code") == 0 and receipt.get("termination_reason") == "completed"
        checks["collector_job_binding"] = receipt.get("job_sha256") == file_hash(attempt / "job.json") and receipt.get("job_id") == job.get("job_id") == report.get("collector_job_id")
        checks["collector_pins"] = all(file_hash(Path(p)) == h for p, h in job["input_sha256"].items())
        checks["collector_stdout_binding"] = file_hash(attempt / "stdout.log") == receipt.get("stdout_sha256") and json.loads((attempt / "stdout.log").read_text()) == report
        checks["collector_stderr_binding"] = file_hash(attempt / "stderr.log") == receipt.get("stderr_sha256")
        checks["format_policy"] = report.get("format_policy") == FORMAT_POLICY == job.get("quality_contract", {}).get("format_repair")
        checks["prospective_bounded_native_scope"] = job["quality_contract"].get("native_scope") == NATIVE_SCOPE
        context, config, groups = parent_context(Path(report["parent_context"]["parent_attempt"]), Path(report["parent_context"]["parent_snapshot_path"]))
        checks["complete_parent_native_chain"] = context["passed"] and context == report["parent_context"]
        checks["all_candidates_recorded"] = len(report["records"]) == len(groups) * 19
        expected = {(g.name, i) for g in groups for i in range(19)}
        checks["unique_native_rows"] = {(r["ias_group"], r["row_index"]) for r in report["records"]} == expected
        initial = initial_identities(config)
        for record in report["records"]:
            replay = {"ias_group": record["ias_group"], "row_index": record["row_index"], "passed": False}
            scores = Path(record["native_scores_path"])
            native_row = json.loads(scores.read_text())["rows"][record["row_index"]]
            native_binding = (file_hash(scores) == record["native_scores_sha256"] and native_row == record["native_row"]
                and scores == Path(context["parent_attempt"]) / "raw/work/case" / record["ias_group"] / "native_search_results.json")
            replay["native_row_binding"] = native_binding
            if record.get("passed"):
                raw = Path(record["raw_ensemble_path"])
                repaired = Path(record["normalized_ensemble_path"])
                selected = Path(record["first_conformation_path"])
                full_row, fixed = complete_native_assignments(native_row, scores.parent, initial)
                normalized, proof = normalize_labels(raw.read_bytes(), full_row["sequence_assignments"], initial)
                binding = (raw.resolve() == (scores.parent / native_row["structure_file"]).resolve()
                    and repaired.resolve().is_relative_to(output) and selected.resolve().is_relative_to(output)
                    and file_hash(raw) == record["raw_ensemble_sha256"]
                    and fixed == record["fixed_position_provenance"]
                    and proof == record["format_proof"] and normalized == repaired.read_bytes()
                    and file_hash(repaired) == record["normalized_ensemble_sha256"]
                    and selected.read_bytes() == native.first_conformation(normalized)
                    and file_hash(selected) == record["first_conformation_sha256"])
                quality = native.candidate_checks(full_row, config, selected)
                replay.update(format_derivation_binding=binding, quality=quality,
                              structure_path=str(selected), sequence=quality["sequence"],
                              passed=binding and native_binding and quality["passed"])
            else:
                replay["failure_reason"] = record.get("failure_reason") or record.get("quality", {}).get("quality", {}).get("failed_checks")
            records.append(replay)
        checks["native_score_bindings"] = all(r["native_row_binding"] for r in records)
        count = sum(r["passed"] for r in records) if all(checks.values()) else 0
        result.update(passed=count > 0, qualified_candidate_count=count, parent_context=context,
            failedchecks=[k for k, ok in checks.items() if not ok], format_repair_note=FORMAT_POLICY)
        if not count:
            result["failedchecks"].append("no_quality_qualified_native_candidate")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["failedchecks"].append(f"replay_incomplete: {type(exc).__name__}: {exc}")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    run = sub.add_parser("collect")
    run.add_argument("--parent-attempt", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--parent-snapshot", type=Path, required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--parent-attempt", type=Path, required=True)
    snap.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("verify")
    check.add_argument("--attempt", type=Path, required=True)
    args = p.parse_args()
    if args.mode == "snapshot":
        print(json.dumps(snapshot_parent(args.parent_attempt, args.output), indent=2))
        return 0
    report = collect(args.parent_attempt, args.parent_snapshot, args.output_dir) if args.mode == "collect" else verify(args.attempt)
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if args.mode == "collect" or report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
