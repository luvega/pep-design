#!/usr/bin/env python3
"""Prepare and run the pinned native DexDesign route under the shared runner.

This adapter preserves the IAS/K* algorithm. It bounds resource parameters,
records native convergence evidence, and never calls an OSPREY environment probe
a design. Structural candidate QC is a separate required acceptance check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

METHOD = "DexDesign / OSPREY3"
SOURCE_COMMIT = "3d53244851f0388db9e01b288bbd330145935aa7"
ROUTE = Path("examples/ccs.D-peptide-L-protein")
REQUIRED = ("DL.py", "DL_preprocess.py", "ccsKstar.py", "Confspace_Combiner.py",
            "Chain_Renamer.py", "Scaffold_Generator.py", "Slurm_Maker.py")
D_LIBRARY = Path("src/main/resources/edu/duke/cs/osprey/gui/conflib/D-lovell.conflib")
DEFAULT_SOURCE = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/OSPREY3")
NATIVE_QUALITY = {
    "partition_function_statuses": ["Estimated", "Estimated", "Estimated"],
    "score": "finite positive K* with finite ordered log10 lower/score/upper",
    "epsilon": 0.68,
    "ensemble_selection": "first conformation in each native ten-conformation ensemble; raw ensemble retained",
    "structure": "required separately: sequence/chain/input binding, L target, D peptide, complete backbone and applicable clash/bond QC",
    "excluded_claims": ["biological_validity", "experimental_affinity", "fair_benchmark_ranking"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def regular(path: Path) -> Path:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"required nonempty regular file: {path}")
    return path


def write_json_new(path: Path, data: Any) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def validate_config(config: dict[str, Any]) -> None:
    for key, low, high in (("threads", 1, 24), ("memory_mib", 2048, 262144),
                           ("heap_mib", 1024, 253952), ("timeout_seconds", 1, 86400)):
        value = config.get(key)
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"invalid bounded {key}")
    if config["heap_mib"] + 1024 > config["memory_mib"]:
        raise ValueError("heap must leave at least 1024 MiB for non-heap allocations")
    if config.get("native_epsilon", 0.68) != 0.68:
        raise ValueError("native K* epsilon must remain 0.68")
    if config.get("input_provenance", {}).get("kind") not in {
        "experimental_d_l_complex", "documented_native_scaffold"
    }:
        raise ValueError("real D/L input provenance is required; synthetic fixture is not eligible")
    for key in ("source_dir", "input_pdb", "python"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError(f"missing {key}")


def source_manifest(source: Path) -> dict[str, str]:
    head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                          text=True, capture_output=True, check=True).stdout.strip()
    if head != SOURCE_COMMIT:
        raise ValueError(f"source commit is not the pinned DexDesign source: {head}")
    tracked = [str(ROUTE / name) for name in REQUIRED] + ["LICENSE.txt", str(D_LIBRARY)]
    dirty = subprocess.run(["git", "-C", str(source), "diff", "--name-only", "HEAD", "--", *tracked],
                           text=True, capture_output=True, check=True).stdout.strip()
    if dirty:
        raise ValueError(f"pinned native source has local modifications: {dirty}")
    manifest = {name: sha256(regular(source / ROUTE / name)) for name in REQUIRED}
    manifest["LICENSE.txt"] = sha256(regular(source / "LICENSE.txt"))
    manifest[str(D_LIBRARY)] = sha256(regular(source / D_LIBRARY))
    return manifest


def verify_runtime_files(config: dict[str, Any]) -> bool:
    """Bind the assembled official engine, Python bridge, JVM and native tools."""
    manifest = regular(Path(config["runtime_manifest"]))
    if sha256(manifest) != config["runtime_manifest_sha256"]:
        return False
    paths = json.loads(manifest.read_text())
    return bool(paths) and all((manifest.parent / name).resolve().is_relative_to(manifest.parent.resolve())
                               and (manifest.parent / name).is_file() and not (manifest.parent / name).is_symlink()
                               and sha256(manifest.parent / name) == digest
                               for name, digest in paths.items())


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    """Read filesystem and package metadata only; do not start JVM/search."""
    validate_config(config)
    source = Path(config["source_dir"]).resolve()
    manifest = source_manifest(source)
    input_pdb = regular(Path(config["input_pdb"]))
    text = input_pdb.read_text(encoding="utf-8")
    if "SYNTHETIC" in text[:4000].upper():
        raise ValueError("synthetic input-contract fixture cannot count as a native design input")
    chains = list(dict.fromkeys(line[21] for line in text.splitlines()
                               if line.startswith(("ATOM  ", "HETATM"))))
    if chains != ["z", "y"]:
        raise ValueError("input must contain L-target z first and D-peptide y second")
    # find_spec does not import OSPREY or start its JVM.
    probe = subprocess.run([config["python"], "-c", (
        "import importlib.util,json; "
        "print(json.dumps({m:(None if importlib.util.find_spec(m) is None else "
        "importlib.util.find_spec(m).origin) for m in ['osprey','Bio','numpy','jpype']}))"
    )], text=True, capture_output=True, check=True, timeout=20)
    packages = json.loads(probe.stdout)
    missing = [name for name, origin in packages.items() if origin is None]
    return {"method": METHOD, "status": "preflight_packages_present" if not missing else "blocked_dependencies",
            "source_commit": SOURCE_COMMIT, "source_files_sha256": manifest,
            "input_sha256": sha256(input_pdb), "packages": packages,
            "missing_packages": missing, "native_jvm_verified": False,
            "candidate_quality_policy": NATIVE_QUALITY}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"native source patch anchor changed: {old[:100]}")
    return text.replace(old, new, 1)


def native_scripts(source: Path, config: dict[str, Any]) -> dict[str, str]:
    """Only runtime configuration and output instrumentation change."""
    result = {name: regular(source / ROUTE / name).read_text() for name in REQUIRED}
    heap = config["heap_mib"]
    threads = config["threads"]
    start = f"osprey.start(heapSizeMiB={heap}, garbageSizeMiB=1024, stackSizeMiB=2)"
    result["DL_preprocess.py"] = replace_once(result["DL_preprocess.py"], "osprey.start()", start)
    result["DL.py"] = replace_once(result["DL.py"], "osprey.start()", start)
    result["DL.py"] = replace_once(result["DL.py"], "slurm_mem = 750", f"slurm_mem = {config['memory_mib'] // 1024}")
    result["DL.py"] = replace_once(result["DL.py"], "slurm_cpus = 48", f"slurm_cpus = {threads}")
    # The official generic engine accepts native custom conformation libraries.
    # Load the exact pinned DexDesign library through that API, without editing
    # the engine or changing rotamers/forcefields/search parameters.
    result["DL.py"] = replace_once(
        result["DL.py"],
        "next(lib for lib in osprey.prep.confLibs if lib.getId() == 'D-lovell2000-osprey3').load()",
        "osprey.prep._kotlin_companion(osprey.c.gui.io.ConfLib).from_(Path('D-lovell.conflib').read_text())")
    # Keep failed intermediate artifacts rather than upstream cleanup deleting them.
    result["DL.py"] = replace_once(result["DL.py"], "    shutil.rmtree(f)",
                                    "    raise RuntimeError('Native confspace compilation failed: ' + f)")
    kstar = result["ccsKstar.py"]
    kstar = replace_once(kstar, "osprey.start(heapSizeMiB=572205, garbageSizeMiB=19074)", start)
    kstar = replace_once(kstar, "cpuCores=48", f"cpuCores={threads}")
    kstar = replace_once(kstar, "# writeSequencesToFile='sequences.tsv',", "writeSequencesToFile='sequences.tsv',")
    kstar = replace_once(kstar, "for scored_sequence in scored_sequences:",
                        "import json\n_acceptance_rows = []\nfor scored_sequence in scored_sequences:\n"
                        "    _score = scored_sequence.score\n"
                        "    _row = {'sequence_native': str(scored_sequence.sequence),\n"
                        "            'sequence_assignments': [{'position': str(a.getResNum()), 'residue_type': str(a.getResType().name)} for a in scored_sequence.sequence.assignments()],\n"
                        "            'partition_statuses': [str(_score.protein.status), str(_score.ligand.status), str(_score.complex.status)],\n"
                        "            'score_log10': str(_score.scoreLog10()),\n"
                        "            'lower_log10': str(_score.lowerBoundLog10()),\n"
                        "            'upper_log10': str(_score.upperBoundLog10()),\n"
                        "            'structure_file': 'ensembles/seq.%s.pdb' % scored_sequence.sequence}\n"
                        "    _acceptance_rows.append(_row)\n"
                        "    if _row['partition_statuses'] != ['Estimated'] * 3:\n"
                        "        continue")
    kstar += ("\nwith open('native_search_results.json', 'x') as _out:\n"
              "    json.dump({'epsilon': 0.68, 'rows': _acceptance_rows}, _out, indent=2, sort_keys=True)\n")
    result["ccsKstar.py"] = kstar
    result["prepare_native.py"] = "from DL_preprocess import DL_preprocess\nDL_preprocess('input', 'prepared-PDBs')\n"
    for name, text in result.items():
        compile(text, name, "exec")
    return result


def stage(config: dict[str, Any], output: Path) -> dict[str, Any]:
    validate_config(config)
    source = Path(config["source_dir"]).resolve()
    original = source_manifest(source)
    input_pdb = regular(Path(config["input_pdb"]))
    scripts = native_scripts(source, config)
    output.mkdir(parents=True, exist_ok=False)
    for name, content in scripts.items():
        (output / name).write_text(content, encoding="utf-8")
    shutil.copyfile(source / D_LIBRARY, output / "D-lovell.conflib")
    from scripts.method_acceptance_quality import criteria_sha256
    bound = {**config, "source_commit": SOURCE_COMMIT,
             "source_files_sha256": original, "input_sha256": sha256(input_pdb),
             "candidate_quality_policy": NATIVE_QUALITY,
             "structural_criteria_sha256": criteria_sha256(),
             "staged_scripts_sha256": {name: sha256(output / name) for name in [*scripts, "D-lovell.conflib"]}}
    write_json_new(output / "config.json", bound)
    return {"status": "staged_not_executed", "stage_dir": str(output),
            "config_sha256": sha256(output / "config.json")}


def native_score_is_eligible(row: dict[str, Any]) -> bool:
    if row.get("partition_statuses") != ["Estimated"] * 3:
        return False
    try:
        lo, score, hi = (float(row[key]) for key in ("lower_log10", "score_log10", "upper_log10"))
    except (KeyError, ValueError, TypeError):
        return False
    return all(math.isfinite(v) for v in (lo, score, hi)) and lo <= score <= hi


def first_conformation(payload: bytes) -> bytes:
    """Select native MODEL 1 without changing coordinates or atom identity."""
    lines = payload.decode("utf-8").splitlines()
    if not any(line.startswith("MODEL ") for line in lines):
        raise ValueError("expected the native multi-conformation ensemble")
    selected = []
    started = False
    finished = False
    for line in lines:
        if line.startswith("MODEL "):
            if started:
                raise ValueError("unterminated first native MODEL")
            started = True
            continue
        if started and line.startswith("ENDMDL"):
            finished = True
            break
        if started:
            selected.append(line)
    if not finished or not any(line.startswith(("ATOM  ", "HETATM")) for line in selected):
        raise ValueError("missing or empty native first conformation")
    return ("REMARK 900 FIRST NATIVE CONFORMATION; COORDINATES UNMODIFIED\n"
            + "\n".join(selected) + "\nEND\n").encode()


def residue_identities(path: Path, chain: str) -> dict[str, str]:
    residues: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if line.startswith(("ATOM  ", "HETATM")) and line[21] == chain:
            key, name = line[22:27].strip(), line[17:20]
            if key in residues and residues[key] != name:
                raise ValueError("inconsistent residue identity")
            residues[key] = name
    return residues


def candidate_checks(row: dict[str, Any], config: dict[str, Any], structure: Path) -> dict[str, Any]:
    from scripts.method_acceptance_quality import evaluate_candidate, criteria_sha256
    from scripts.v034_adapters.common import AA3_TO_1, chirality_stats
    input_path = Path(config["input_pdb"])
    expected_binder = residue_identities(input_path, "y")
    expected_target = residue_identities(input_path, "z")
    observed_binder = residue_identities(structure, "y")
    observed_target = residue_identities(structure, "z")
    sequence = "".join(AA3_TO_1.get(name, "X") for name in observed_binder.values())
    # Native position names are '<residue id> <initial residue type>'. Input
    # chain numbering is disjoint, so each position has exactly one chain.
    all_expected = {**expected_target, **expected_binder}
    assignments = row.get("sequence_assignments", [])
    mapped = {}
    valid = bool(assignments) and not (expected_target.keys() & expected_binder.keys())
    for assignment in assignments:
        parts = assignment.get("position", "").split()
        if len(parts) != 2 or parts[0] not in all_expected or all_expected[parts[0]] != parts[1]:
            valid = False
            continue
        if parts[0] in mapped:
            valid = False
        mapped[parts[0]] = assignment.get("residue_type", "").upper()
    valid = valid and all(mapped.get(key) == name for key, name in observed_binder.items())
    valid = valid and all(key in observed_binder or observed_target.get(key) == name for key, name in mapped.items())
    target_chirality = chirality_stats(structure, "z")
    target_l = (target_chirality["unknown_count"] == 0 and target_chirality["d_count"] == 0
                and target_chirality["l_count"] + target_chirality["gly_count"] == len(expected_target))
    quality = evaluate_candidate(method=METHOD, sequence=sequence, length_min=len(expected_binder),
                                 length_max=len(expected_binder), structure_path=structure, binder_chain="y")
    checks = {"native_kstar_converged": native_score_is_eligible(row),
              "predeclared_structural_criteria": config.get("structural_criteria_sha256") == criteria_sha256(),
              "binder_residue_ids": list(expected_binder) == list(observed_binder),
              "target_sequence_and_residue_ids": expected_target == observed_target,
              "native_sequence_structure_binding": valid,
              "target_l_chirality": target_l,
              "candidate_quality": quality["candidate_quality_status"] == "pass"}
    return {"sequence": sequence, "checks": checks, "quality": quality,
            "target_chirality": target_chirality, "passed": all(checks.values())}


def runner_binding(output_dir: Path) -> dict[str, Any]:
    attempt = os.environ.get("METHOD_ACCEPTANCE_ATTEMPT_DIR")
    policy_sha = os.environ.get("METHOD_ACCEPTANCE_POLICY_SHA256")
    if not attempt or not policy_sha:
        raise ValueError("run requires the shared method-acceptance runner binding")
    attempt_dir = Path(attempt).resolve()
    if not output_dir.resolve().is_relative_to(attempt_dir):
        raise ValueError("native outputs must remain inside the reserved attempt")
    job = json.loads(regular(attempt_dir / "job.json").read_text())
    if job.get("method") != "dexdesign" or job.get("kind", "method") != "method":
        raise ValueError("runner allocation is not a DexDesign method attempt")
    policy_file = Path(__file__).resolve().parents[1] / "benchmark/deployment/method_acceptance_policy_v1.json"
    if (sha256(regular(policy_file)) != policy_sha
            or json.loads(regular(attempt_dir / "policy.json").read_text()) != json.loads(policy_file.read_text())):
        raise ValueError("runner policy binding mismatch")
    return job


def run(stage_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Must be invoked by the phase resource runner, never used for preflight."""
    job = runner_binding(output_dir)
    config = json.loads(regular(stage_dir / "config.json").read_text())
    validate_config(config)
    required_stage = {*REQUIRED, "prepare_native.py", "D-lovell.conflib"}
    if set(config["staged_scripts_sha256"]) != required_stage:
        raise ValueError("staged native file set is incomplete or unexpected")
    for path in (stage_dir / "config.json", Path(__file__).resolve()):
        if job.get("input_sha256", {}).get(str(path.resolve())) != sha256(regular(path)):
            raise ValueError("shared job must pin native stage configuration and adapter")
    if job["quality_contract"].get("native") != NATIVE_QUALITY:
        raise ValueError("job must prospectively declare native candidate quality requirements")
    if not verify_runtime_files(config):
        raise ValueError("assembled native runtime files changed after preparation")
    if (config["threads"] > job["threads"] or config["memory_mib"] > job["memory_gib"] * 1024
            or config["timeout_seconds"] > job["timeout_seconds"]):
        raise ValueError("staged resources exceed the shared runner reservation")
    if source_manifest(Path(config["source_dir"])) != config["source_files_sha256"]:
        raise ValueError("source files changed after staging")
    input_pdb = regular(Path(config["input_pdb"]))
    if sha256(input_pdb) != config["input_sha256"]:
        raise ValueError("input changed after staging")
    for name, digest in config["staged_scripts_sha256"].items():
        if sha256(regular(stage_dir / name)) != digest:
            raise ValueError(f"staged script changed: {name}")
    output_dir.mkdir(parents=True, exist_ok=False)
    work = output_dir / "work"
    work.mkdir()
    for name in config["staged_scripts_sha256"]:
        shutil.copyfile(stage_dir / name, work / name)
    (work / "input").mkdir()
    (work / "prepared-PDBs").mkdir()
    shutil.copyfile(input_pdb, work / "input" / "case-complex.pdb")
    start = time.monotonic()
    commands: list[dict[str, Any]] = []
    env = os.environ.copy()
    env.update({"OMP_NUM_THREADS": str(config["threads"]), "OPENBLAS_NUM_THREADS": str(config["threads"]),
                "CUDA_VISIBLE_DEVICES": "", "JAVA_TOOL_OPTIONS": f"-XX:ActiveProcessorCount={config['threads']}"})

    def invoke(label: str, argv: list[str], cwd: Path) -> None:
        remaining = config["timeout_seconds"] - (time.monotonic() - start)
        if remaining <= 0:
            raise TimeoutError("DexDesign total worker timeout exhausted")
        command = {"stage": label, "argv": argv, "cwd": str(cwd)}
        commands.append(command)
        with (output_dir / f"{label}.stdout.log").open("x") as out, (output_dir / f"{label}.stderr.log").open("x") as err:
            done = subprocess.run(argv, cwd=cwd, env=env, stdout=out, stderr=err, timeout=remaining)
        command["exit_code"] = done.returncode
        if done.returncode:
            raise RuntimeError(f"{label} exited {done.returncode}")

    try:
        invoke("preprocess", [config["python"], "prepare_native.py"], work)
        invoke("compile", [config["python"], "DL.py"], work)
        groups = sorted((work / "case").glob("*/"))
        if not groups:
            raise RuntimeError("no native IAS conformation-space groups")
        for index, group in enumerate(groups):
            paths = {}
            for kind in ("complex", "target", "peptide"):
                choices = list(group.glob(f"*{kind}.ccsx"))
                if len(choices) != 1:
                    raise RuntimeError(f"missing/ambiguous {kind} compiled space in {group}")
                paths[kind] = str(regular(choices[0]).resolve())
            invoke(f"kstar_{index:03}", [config["python"], str(work.resolve() / "ccsKstar.py"),
                   paths["complex"], paths["target"], paths["peptide"]], group)
        eligible = []
        all_rows = []
        for group in groups:
            payload = json.loads(regular(group / "native_search_results.json").read_text())
            for row in payload["rows"]:
                all_rows.append({**row, "ias_group": str(group.relative_to(work))})
                if native_score_is_eligible(row):
                    structure = regular(group / row["structure_file"])
                    derived = group / "candidate_first_conformations"
                    derived.mkdir(exist_ok=True)
                    model = derived / f"candidate_{len(eligible):04d}.pdb"
                    with model.open("xb") as f:
                        f.write(first_conformation(structure.read_bytes()))
                    eligible.append({**row, "ias_group": str(group.relative_to(work)),
                                     "structure_path": str(structure.resolve()), "structure_sha256": sha256(structure),
                                     "first_conformation_path": str(model.resolve()),
                                     "first_conformation_sha256": sha256(model),
                                     "quality_replay": candidate_checks(row, config, model)})
        result = {"status": "native_search_complete_structure_qc_required" if eligible else "failed_no_converged_native_candidate",
                  "native_search_rows": all_rows, "native_converged_candidates": eligible,
                  "method_accepted": False, "structural_qc_status": "required_not_performed_by_native_search_adapter"}
    except Exception as exc:
        result = {"status": "failed", "error_type": type(exc).__name__, "error": str(exc), "method_accepted": False}
    result.update({"method": METHOD, "shared_job_id": job["job_id"],
                   "runtime_seconds": time.monotonic() - start, "commands": commands,
                   "config_sha256": sha256(stage_dir / "config.json"),
                   "stage_dir": str(stage_dir.resolve()),
                   "artifacts_sha256": {str(path.relative_to(output_dir)): sha256(path)
                                        for path in output_dir.rglob("*") if path.is_file()},
                   "candidate_quality_policy": NATIVE_QUALITY})
    write_json_new(output_dir / "native_execution.json", result)
    return result


def verify(path: Path | str) -> dict[str, Any]:
    """Replay one shared attempt (or its raw output directory), without writes."""
    path = Path(path).resolve()
    output = path if (path / "native_execution.json").is_file() else path / "raw"
    attempt = output.parent
    checks: dict[str, bool] = {}
    records = []
    report: dict[str, Any] = {"method": METHOD, "passed": False, "qualified_candidate_count": 0,
                              "records": records, "checks": checks, "failedchecks": []}
    try:
        execution = json.loads(regular(output / "native_execution.json").read_text())
        job = json.loads(regular(attempt / "job.json").read_text())
        run_result = json.loads(regular(attempt / "run_result.json").read_text())
        launch = json.loads(regular(attempt / "launch.json").read_text())
        stage = Path(execution["stage_dir"])
        config = json.loads(regular(stage / "config.json").read_text())
        checks["job_method_and_native_kind"] = job.get("method") == "dexdesign" and job.get("kind", "method") == "method"
        checks["shared_execution_completed"] = (run_result.get("exit_code") == 0
                                                 and run_result.get("termination_reason") == "completed"
                                                 and run_result.get("job_id") == job.get("job_id") == execution.get("shared_job_id"))
        checks["run_job_hash"] = run_result.get("job_sha256") == sha256(attempt / "job.json")
        checks["raw_log_hashes"] = all(run_result.get(f"{name}_sha256") == sha256(regular(attempt / f"{name}.log"))
                                        for name in ("stdout", "stderr"))
        checks["execution_payload_in_bound_stdout"] = json.loads((attempt / "stdout.log").read_text()) == execution
        checks["shared_policy_binding"] = launch.get("policy_sha256") == run_result.get("policy_sha256")
        checks["job_adapter_stage_pins"] = all(job.get("input_sha256", {}).get(str(p.resolve())) == sha256(regular(p))
                                               for p in (stage / "config.json", Path(__file__).resolve()))
        checks["stage_config_hash"] = execution.get("config_sha256") == sha256(stage / "config.json")
        checks["native_source_pins"] = source_manifest(Path(config["source_dir"])) == config["source_files_sha256"]
        checks["native_stage_pins"] = (set(config["staged_scripts_sha256"]) == {*REQUIRED, "prepare_native.py", "D-lovell.conflib"}
                                         and all(sha256(regular(stage / name)) == digest for name, digest in config["staged_scripts_sha256"].items()))
        checks["original_input_pin"] = sha256(regular(Path(config["input_pdb"]))) == config["input_sha256"]
        checks["native_engine_environment_pins"] = verify_runtime_files(config)
        checks["native_quality_contract"] = (execution.get("candidate_quality_policy") == NATIVE_QUALITY
                                                and job.get("quality_contract", {}).get("native") == NATIVE_QUALITY)
        artifacts = execution.get("artifacts_sha256", {})
        checks["native_artifacts_hashes"] = bool(artifacts) and all(
            (output / name).resolve().is_relative_to(output) and sha256(regular(output / name)) == digest
            for name, digest in artifacts.items())
        groups = sorted((output / "work/case").glob("*/"))
        expected_groups = len(residue_identities(Path(config["input_pdb"]), "y"))
        commands = execution.get("commands", [])
        checks["complete_preprocess_compile_search_chain"] = (
            len(groups) == expected_groups and len(commands) == expected_groups + 2
            and [x.get("stage") for x in commands] == ["preprocess", "compile"] + [f"kstar_{i:03}" for i in range(expected_groups)]
            and all(x.get("exit_code") == 0 for x in commands)
            and all((group / "native_search_results.json").is_file() for group in groups)
            and (output / "work/prepared-PDBs/case-D-L-complex.pdb").is_file())
        checks["native_search_complete"] = execution.get("status") == "native_search_complete_structure_qc_required"
        for candidate in execution.get("native_converged_candidates", []):
            ensemble = Path(candidate["structure_path"])
            model = Path(candidate["first_conformation_path"])
            local = ensemble.resolve().is_relative_to(output) and model.resolve().is_relative_to(output)
            artifact_checks = {"inside_attempt": local,
                               "ensemble_hash": sha256(regular(ensemble)) == candidate["structure_sha256"],
                               "first_conformation_hash": sha256(regular(model)) == candidate["first_conformation_sha256"],
                               "first_conformation_exact_derivation": model.read_bytes() == first_conformation(ensemble.read_bytes())}
            group = output / "work" / candidate["ias_group"]
            native = json.loads(regular(group / "native_search_results.json").read_text())
            matching = [r for r in native.get("rows", []) if r.get("structure_file") == candidate.get("structure_file")
                        and r.get("sequence_native") == candidate.get("sequence_native")]
            artifact_checks["raw_native_score_binding"] = (len(matching) == 1 and
                all(matching[0].get(key) == candidate.get(key) for key in (
                    "sequence_assignments", "partition_statuses", "score_log10", "lower_log10", "upper_log10")))
            record = candidate_checks(candidate, config, model)
            record.update(artifact_checks=artifact_checks, structure_path=str(model),
                          native_kstar={key: candidate[key] for key in ("partition_statuses", "score_log10", "lower_log10", "upper_log10")})
            record["passed"] = record["passed"] and all(artifact_checks.values())
            records.append(record)
        qualified = sum(record["passed"] for record in records) if all(checks.values()) else 0
        report.update(qualified_candidate_count=qualified, passed=qualified > 0,
                      failedchecks=[name for name, passed in checks.items() if not passed])
        if not qualified:
            report["failedchecks"].append("no_quality_qualified_native_candidate")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report["failedchecks"].append(f"replay_incomplete: {type(exc).__name__}: {exc}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="mode", required=True)
    for name in ("preflight", "stage"):
        sub = subs.add_parser(name)
        sub.add_argument("--config", required=True, type=Path)
        if name == "stage":
            sub.add_argument("--output-dir", required=True, type=Path)
    sub = subs.add_parser("run")
    sub.add_argument("--stage-dir", required=True, type=Path)
    sub.add_argument("--output-dir", required=True, type=Path)
    sub = subs.add_parser("verify")
    sub.add_argument("--attempt", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "verify":
            result = verify(args.attempt)
            print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
            return 0 if result["passed"] else 1
        elif args.mode == "run":
            result = run(args.stage_dir, args.output_dir)
        else:
            config = json.loads(args.config.read_text())
            result = preflight(config) if args.mode == "preflight" else stage(config, args.output_dir)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["status"] not in {"failed", "failed_no_converged_native_candidate", "blocked_dependencies"} else 1
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
