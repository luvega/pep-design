#!/usr/bin/env python3
"""Prepare independently named native-quality structural jobs; never launch them.

Existing adapters only prepare pinned sources, inputs and wrappers. New descriptors
go through method_acceptance_runner; historical jobs and attempts are not reused.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shlex
import subprocess
import sys
import tarfile
import tempfile
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.method_acceptance_quality import CYCLIC, criteria, evaluate_candidate
from scripts.v034_adapters import colabdesign, diffpepbuilder, dflow
from scripts.v034_adapters.common import AA3_TO_1, parse_pdb_chain_sequences, parse_pdb_atoms

METHODS = {"diffpepbuilder": ("DiffPepBuilder", diffpepbuilder),
           "afcycdesign": (CYCLIC, colabdesign),
           "dflow": ("D-Flow / PeptideDesign", dflow)}
IMAGES = {"pd-pyrosetta-methods-gpu:0.20": "sha256:02a4cb04b3ee470ae4fdbee0a9e3d249052326cfeec1f3171bb51e26c2fa4e00",
          "pd-benchmark-methods-gpu:0.21": "sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2"}
POLICY_SLUGS = {"diffpepbuilder": "diffpepbuilder", "afcycdesign": "colabdesign", "dflow": "dflow"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def native_inner(slug, inner):
    """Restore native schedules exactly; reject missing/ambiguous old markers."""
    if slug == "diffpepbuilder":
        if inner.count("inference.denoising.num_t=2 ") != 1:
            raise ValueError("DiffPepBuilder bounded-step marker changed")
        inner = inner.replace("inference.denoising.num_t=2 ", "inference.denoising.num_t=200 ")
        inner = inner.replace("inference.ss_bond.build_ss_bond=False", "inference.ss_bond.build_ss_bond=True")
        copy_marker = 'cp -a /data/source/. "$work/"'
        if inner.count(copy_marker) != 1:
            raise ValueError("DiffPepBuilder source-copy marker changed")
        inner = inner.replace(copy_marker, copy_marker + '\ntar -xzf "$work/SSbuilder/SSBLIB.tar.gz" -C "$work/SSbuilder"')
    return inner


def _dflow_command(template, job, *, steps=200, samples=1):
    """Use the existing pinned environment inside a resource-limited container."""
    old_command = (template / "command.sh").read_text()
    invocation = old_command.split("\ntest -s ", 1)[0]
    if invocation.count("sample.num_steps=1 ") != 1 or invocation.count("sample.angle_purify=False") != 1:
        raise ValueError("D-Flow bounded settings changed")
    invocation = invocation.replace("sample.num_steps=1 ", f"sample.num_steps={steps} ")
    invocation = invocation.replace("sample.num_samples=1 ", f"sample.num_samples={samples} ")
    invocation = invocation.replace("sample.angle_purify=False", "sample.angle_purify=True")
    invocation = invocation.replace(str(template), "/data/attempt")
    native = f"/data/attempt/raw/dflow_native/dflow.pt_{steps}_{samples}_False_x_mirror/{job['target_id']}/sample_0.pdb"
    invocation += f"\ntest -s {shlex.quote(native)}\ncp -- {shlex.quote(native)} /data/attempt/raw/dflow_candidate.pdb\n"
    # No old host-runtime finalizer is reused: this execution is containerized.
    invocation += f"{shlex.quote(str(dflow.PYTHON))} /data/attempt/native_completion.py\n"
    completion = {
        "method": "D-Flow / PeptideDesign", "source_commit": dflow.SOURCE_COMMIT,
        "checkpoint_sha256": dflow.CHECKPOINT_SHA256, "requested_seed": int(job["random_seed"]),
        "num_steps": steps, "num_samples": samples, "angle_purify": True, "llm": False,
        "x_mirror": True, "containerized": True,
        "execution_environment_type": "container_with_readonly_existing_dflow_venv",
        "image_id": IMAGES["pd-benchmark-methods-gpu:0.21"],
        "python_environment": str(dflow.PYTHON.parent.parent),
    }
    (template / "native_completion.py").write_text(
        "import hashlib,json\nfrom pathlib import Path\n"
        f"record={completion!r}\n"
        "path=Path('/data/attempt/raw/dflow_candidate.pdb')\n"
        "record['candidate_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()\n"
        "record['target_context_sha256']=hashlib.sha256(Path('/data/attempt/raw/dflow_target_context.pdb').read_bytes()).hexdigest()\n"
        f"files=sorted(path.parent.glob('dflow_native/dflow.pt_{steps}_{samples}_False_x_mirror/{job['target_id']}/sample_*.pdb'))\n"
        f"assert len(files)=={samples}, 'incomplete native sample batch'\n"
        "record['native_candidates']={str(p.relative_to('/data/attempt')):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}\n"
        "Path('/data/attempt/raw/runtime_evidence.json').write_text(json.dumps(record,indent=2)+'\\n')\n")
    image = "pd-benchmark-methods-gpu:0.21"
    argv = ["docker", "run", "--rm", "--gpus", "all", "--shm-size", "16g",
            "-v", str(template) + ":/data/attempt",
            "-v", str(dflow.PYTHON.parent.parent) + ":" + str(dflow.PYTHON.parent.parent) + ":ro",
            "-v", str(dflow.WEIGHT.resolve()) + ":" + str(dflow.WEIGHT.resolve()) + ":ro",
            "-v", str(dflow.STRUCTURE_DIR) + ":" + str(dflow.STRUCTURE_DIR) + ":ro",
            "-v", "/home/a/.cache/torch/hub/checkpoints:/root/.cache/torch/hub/checkpoints:ro",
            image, "bash", "-lc", invocation]
    return argv


def prepare(slug, *, seed=42, suffix="native01", prepared_root=None, steps=200, samples=1):
    method, adapter = METHODS[slug]
    if type(steps) is not int or not 200 <= steps <= 1000 or type(samples) is not int or not 1 <= samples <= 8:
        raise ValueError("native sampling settings exceed prepared bounds")
    job_id = f"ma_{slug}_{suffix}_seed{seed}"
    prepared = Path(prepared_root or ROOT / "benchmark_runs/method_acceptance_v1/prepared") / job_id
    template = prepared / "template"
    template.mkdir(parents=True, exist_ok=False)
    old = next(row for row in _rows(ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv")
               if row["method"] == method and row["seed_stage"] == "primary")
    execution = next(row for row in _rows(ROOT / "benchmark/deployment/pilot_execution_matrix_v0.34.csv")
                     if row["job_id"] == old["job_id"])
    job = {**old, "job_id": job_id, "random_seed": str(seed)}
    adapter.prepare(job, execution, template)
    native_settings = {}
    if slug == "afcycdesign":
        entry = template / "afcycdesign_entry.py"
        text = entry.read_text()
        if text.count("model.design_logits(1)") != 1:
            raise ValueError("AfCycDesign bounded-iteration marker changed")
        text = text.replace("model.design_logits(1)", "model.design_3stage()")
        text = text.replace('    "cyclic_offset_applied": True,', '    "native_design_schedule": {"soft": 300, "temperature": 100, "hard": 10},\n    "cyclic_offset_applied": True,')
        entry.write_text(text)
        native_settings = {"design_3stage": [300, 100, 10], "cyclic_offset": 2,
                           "num_recycles": 0, "model": "model_1_ptm", "native_filters": "none declared by notebook"}
    elif slug == "diffpepbuilder":
        native_settings = {"denoising_num_t": 200, "samples_per_length": 1,
                           "build_ss_bond": True, "length": 11}
    else:
        native_settings = {"num_steps": steps, "angle_purify": True, "llm": False,
                           "x_mirror": True, "samples": samples, "known_training_overlap": "3EQS fixture only"}
    if slug == "diffpepbuilder":
        archive = diffpepbuilder.SOURCE_ROOT / "SSbuilder/SSBLIB.tar.gz"
        with tarfile.open(archive, "r:gz") as stream:
            members = stream.getmembers()
        if not members or any(Path(m.name).is_absolute() or ".." in Path(m.name).parts
                              or not (m.isfile() or m.isdir()) for m in members):
            raise ValueError("unsafe native SSBLIB archive")
        native_settings["ss_library_sha256"] = sha(archive)
    if slug == "dflow":
        for name, expected in diffpepbuilder.MODEL_ASSETS.items():
            if name.startswith("esm2_"):
                if sha(Path("/home/a/.cache/torch/hub/checkpoints") / name) != expected:
                    raise ValueError("D-Flow existing ESM cache differs from pinned assets")
    if slug == "dflow":
        argv = _dflow_command(template, job, steps=steps, samples=samples)
    else:
        command = (template / "command.sh").read_text()
        tail = command.split("docker run ", 1)[1]
        argv = ["docker", "run", *shlex.split(tail)]
    image_position = argv.index("bash") - 1
    image = argv[image_position]
    observed = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                              text=True, capture_output=True, check=True).stdout.strip()
    if observed != IMAGES[image]:
        raise ValueError("pinned image identity changed")
    argv[image_position] = observed
    inner = native_inner(slug, argv[-1])
    # Copy only new preparation files into the newly allocated attempt. Legacy
    # finalizers contain host paths; bind them to the new attempt before use.
    bootstrap = ("mkdir -p /data/attempt/raw\ncp -a /prepared/. /data/attempt/\n"
                 "python3 - <<'PY'\nimport os\nfrom pathlib import Path\n"
                 f"old={str(template)!r}\n"
                 "for p in Path('/data/attempt').glob('*.py'):\n"
                 " p.write_text(p.read_text().replace(old, os.environ['V034_HOST_ATTEMPT']))\nPY\n")
    argv[-1] = "set -euo pipefail\n" + bootstrap + inner
    argv = [value.replace(str(template) + ":/data/attempt", "{attempt_dir}:/data/attempt")
            .replace("V034_HOST_ATTEMPT=" + str(template), "V034_HOST_ATTEMPT={attempt_dir}") for value in argv]
    argv[2:2] = ["--name", "{container_name}", "--memory", "64g", "--cpus", "4", "--network", "none",
                 "-e", "V034_HOST_ATTEMPT={attempt_dir}", "-e", "OMP_NUM_THREADS=4",
                 "-e", "OPENBLAS_NUM_THREADS=4", "-e", "MKL_NUM_THREADS=4",
                 "-e", "PYTHONDONTWRITEBYTECODE=1", "-v", str(template) + ":/prepared:ro"]
    inputs = {str(p): sha(p) for p in template.rglob("*") if p.is_file() and not p.is_symlink()}
    inputs[str(Path(old["target_pdb_path"]).resolve())] = old["target_pdb_sha256"]
    # Preserve preparer/evaluator snapshots outside the template; future source
    # improvements cannot invalidate the execution's captured preparation.
    for name in ("method_acceptance_structural.py", "method_acceptance_quality.py"):
        capture = prepared / name
        capture.write_bytes((ROOT / "scripts" / name).read_bytes())
        inputs[str(capture)] = sha(capture)
    if slug == "diffpepbuilder":
        inputs.update({str(diffpepbuilder.MODEL_ROOT / name): digest for name, digest in diffpepbuilder.MODEL_ASSETS.items()})
        inputs[str(diffpepbuilder.SOURCE_ENTRYPOINT)] = diffpepbuilder.SOURCE_ENTRYPOINT_SHA256
        inputs[str(diffpepbuilder.SOURCE_ROOT / "SSbuilder/SSBLIB.tar.gz")] = native_settings["ss_library_sha256"]
    elif slug == "afcycdesign":
        inputs[str(colabdesign.ALPHAFOLD_PARAMS)] = colabdesign.ALPHAFOLD_PARAMS_SHA256
        inputs[str(colabdesign.SOURCE_NOTEBOOK)] = colabdesign.SOURCE_NOTEBOOK_SHA256
    else:
        inputs[str(dflow.WEIGHT)] = dflow.CHECKPOINT_SHA256
        inputs[str(dflow.PYTHON.resolve())] = sha(dflow.PYTHON.resolve())
        inputs.update({str(Path("/home/a/.cache/torch/hub/checkpoints") / name): expected
                       for name, expected in diffpepbuilder.MODEL_ASSETS.items() if name.startswith("esm2_")})
    descriptor = {"job_id": job_id, "method": POLICY_SLUGS[slug], "method_name": method, "resource": "gpu", "threads": 4,
                  "memory_gib": 64, "timeout_seconds": 3600, "argv": argv,
                  "quality_contract": criteria(), "input_sha256": inputs,
                  "native_settings": native_settings, "source_commit": adapter.SOURCE_COMMIT,
                  "random_seed": seed,
                  "target_input_sha256": old["target_pdb_sha256"], "binder_chain": old["expected_binder_chain"],
                  "length_min": int(old["length_min"]), "length_max": int(old["length_max"]),
                  "candidate_path": {"diffpepbuilder": "raw/diffpepbuilder_candidate.pdb", "afcycdesign": "raw/afcycdesign_candidate.pdb", "dflow": "raw/dflow_candidate.pdb"}[slug],
                  "source_scope": "separate native task, no historical evidence promotion"}
    path = prepared / "job.json"
    path.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n")
    return path


def inspect(attempt):
    attempt = Path(attempt)
    job = json.loads((attempt / "job.json").read_text())
    candidate = attempt / job["candidate_path"]
    sequence = parse_pdb_chain_sequences(candidate).get(job["binder_chain"], "")
    method = job.get("method_name") or {POLICY_SLUGS[k]: v[0] for k, v in METHODS.items()}.get(job["method"], job["method"])
    result = evaluate_candidate(method=method, sequence=sequence,
        length_min=job["length_min"], length_max=job["length_max"], structure_path=candidate,
        binder_chain=job["binder_chain"])
    result.update(job_id=job["job_id"], attempt_dir=str(attempt), native_settings=job["native_settings"],
                  provenance_status="requires_independent_execution_and_input_replay")
    return result


def prepare_dflow_batch(selection, prepared_root=None):
    """One native inference invocation over prospectively fixed existing inputs."""
    selection = Path(selection).resolve()
    manifest = json.loads(selection.read_text())
    cases = manifest["selected_inputs"]
    if [r["case_id"] for r in cases] != ["1uoo_B", "5o3w_X", "1sem_C"]:
        raise ValueError("batch differs from authorized prospective input selection")
    schedule = {"num_steps":400,"samples":4,"angle_purify":True,"llm":False,"x_mirror":True}
    job_id = "ma_dflow_native03_three_inputs_seed44"
    prepared = Path(prepared_root or ROOT/"benchmark_runs/method_acceptance_v1/prepared")/job_id
    template = prepared/"template"
    template.mkdir(parents=True,exist_ok=False)
    commit, tracked = dflow._verified_tracked_files(dflow.SOURCE_ROOT)
    source = template/"work/PeptideDesign"
    dflow._copy_tracked_source(dflow.SOURCE_ROOT,source,tracked)
    entry = source/"dflow/experiments/inference_pep.py"
    original = entry.read_text()
    if sha(entry) != dflow.SOURCE_ENTRYPOINT_SHA256 or original.count("seed_all(2024)") != 1:
        raise ValueError("native inference entrypoint changed")
    entry.write_text(original.replace("seed_all(2024)", 'seed_all(int(os.environ["V034_SEED"]))'))
    dflow._write_source_manifest(template/"source_content_manifest.json",source,tracked,
        source_commit=commit,prepatch_sha256=dflow.SOURCE_ENTRYPOINT_SHA256,patched_sha256=sha(entry))
    (source/"dflow.pt").symlink_to(dflow.WEIGHT.resolve())
    (template/"work/names.txt").write_text("\n".join(r["case_id"] for r in cases)+"\n")
    bound_cases=[]
    for case in cases:
        folder=template/"inputs"/case["case_id"];folder.mkdir(parents=True)
        pins=case["input_sha256"]
        for path,digest in pins.items():
            if sha(path)!=digest:
                raise ValueError("selected native input changed: "+path)
            shutil.copyfile(path,folder/Path(path).name)
        bound_cases.append({"case_id":case["case_id"],"length":case["length"],
            "binder_chain":case["binder_chain"],"target_chain":case["target_chain"],
            "reference_sequence":case["peptide_sequence"],
            "input_sha256":{name:sha(folder/name) for name in ("peptide.pdb","pocket.pdb","pocket_merge.pdb","peptide.fasta","receptor.fasta")}})
    config={"source_commit":commit,"requested_seed":44,"native_settings":schedule,
        "native_invocations":1,"cases":bound_cases,"selection_sha256":sha(selection),
        "checkpoint_sha256":dflow.CHECKPOINT_SHA256,"entrypoint_patched_sha256":sha(entry)}
    (template/"batch_config.json").write_text(json.dumps(config,indent=2)+"\n")
    (template/"selection.json").write_bytes(selection.read_bytes())
    (template/"complete_batch.py").write_text('''import hashlib,json,pickle
from pathlib import Path
import lmdb
root=Path('/data/attempt')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
record=json.loads((root/'batch_config.json').read_text())
prefix=root/'raw/dflow_native/dflow.pt_400_4_False_x_mirror'
expected={case['case_id'] for case in record['cases']}
assert {p.name for p in prefix.iterdir() if p.is_dir()}==expected,'native dataset output incomplete'
record['native_candidates']={}
for case in record['cases']:
 folder=prefix/case['case_id']
 files=sorted(folder.glob('sample_*.pdb'))
 assert {p.name for p in files}=={'sample_0.pdb','sample_1.pdb','sample_2.pdb','sample_3.pdb'},'native sample batch incomplete'
 for path in files:record['native_candidates'][str(path.relative_to(root))]=sha(path)
cache=root/'work/pep_cache/pep_pocket_test_structure_x_cache.lmdb'
db=lmdb.open(str(cache),subdir=False,readonly=True,lock=False,create=False)
with db.begin() as txn:
 ids=[key.decode() for key in txn.cursor().iternext(values=False)]
 assert set(ids)==expected,'native cached input IDs differ from prospective selection'
 record['native_cache_inputs']={}
 record['native_dataset_iteration_order']=ids
 for ident in ids:
  data=pickle.loads(txn.get(ident.encode()))
  mask=data['generate_mask']
  record['native_cache_inputs'][ident]={'generated_residues':int(mask.sum()),'total_residues':len(mask),
   'binder_chains':sorted(set(chain for chain,selected in zip(data['chain_id'],mask) if bool(selected))),
   'target_chains':sorted(set(chain for chain,selected in zip(data['chain_id'],mask) if not bool(selected)))}
db.close()
record['native_cache_sha256']=sha(cache)
record['batch_config_sha256']=sha(root/'batch_config.json')
record['native_completed']=True
(root/'raw/runtime_evidence.json').write_text(json.dumps(record,indent=2)+'\\n')
''')
    inner=f'''set -euo pipefail
cp -a /prepared/template/. /data/attempt/
mkdir -p /data/attempt/raw /data/attempt/work/pep_cache
export V034_SEED=44
cd /data/attempt/work/PeptideDesign
{shlex.quote(str(dflow.PYTHON))} -m dflow.experiments.inference_pep sample.ckpt_path=dflow.pt sample.output=/data/attempt/raw/dflow_native sample.device=cuda sample.num_steps=400 sample.num_samples=4 sample.x_mirror=True sample.y_mirror=False sample.z_mirror=False sample.angle_purify=True sample.llm=False dataset.val.structure_dir=/data/attempt/inputs dataset.val.dataset_dir=/data/attempt/work/pep_cache dataset.val.name=pep_pocket_test dataset.val.reset=False
{shlex.quote(str(dflow.PYTHON))} /data/attempt/complete_batch.py
'''
    argv=["docker","run","--rm","--name","{container_name}","--memory","48g","--cpus","4","--network","none",
        "--gpus","device=0","--shm-size","4g","-e","OMP_NUM_THREADS=4","-e","OPENBLAS_NUM_THREADS=4","-e","MKL_NUM_THREADS=4",
        "-e","LOKY_MAX_CPU_COUNT=4","-e","PYTHONDONTWRITEBYTECODE=1","-e","PYTHONUNBUFFERED=1",
        "-v",str(prepared)+":/prepared:ro","-v","{attempt_dir}:/data/attempt",
        "-v",str(dflow.PYTHON.parent.parent)+":"+str(dflow.PYTHON.parent.parent)+":ro",
        "-v",str(dflow.WEIGHT.resolve())+":"+str(dflow.WEIGHT.resolve())+":ro",
        "-v","/home/a/.cache/torch/hub/checkpoints:/root/.cache/torch/hub/checkpoints:ro",
        IMAGES["pd-benchmark-methods-gpu:0.21"],"bash","-lc",inner]
    inputs={str(p):sha(p) for p in template.rglob("*") if p.is_file() and not p.is_symlink()}
    inputs.update({str(selection):sha(selection),str(dflow.WEIGHT.resolve()):dflow.CHECKPOINT_SHA256,
                   str(dflow.PYTHON.resolve()):sha(dflow.PYTHON.resolve())})
    for case in cases:inputs.update(case["input_sha256"])
    for name,digest in diffpepbuilder.MODEL_ASSETS.items():
        if name.startswith("esm2_"):inputs[str(Path('/home/a/.cache/torch/hub/checkpoints')/name)]=digest
    for name in ("method_acceptance_structural.py","method_acceptance_quality.py"):
        path=prepared/name;path.write_bytes((ROOT/"scripts"/name).read_bytes());inputs[str(path)]=sha(path)
    job={"job_id":job_id,"method":"dflow","method_name":"D-Flow / PeptideDesign","resource":"gpu","threads":4,
        "memory_gib":48,"timeout_seconds":3600,"argv":argv,"quality_contract":criteria(),"input_sha256":inputs,
        "native_stage":"multi_input","native_invocations":1,"native_settings":schedule,"random_seed":44,
        "cases":bound_cases,"batch_config_sha256":sha(template/"batch_config.json"),"selection_sha256":sha(selection),
        "source_commit":commit,"entrypoint_patched_sha256":sha(entry),
        "sampling_rationale":"Fixed 400-step native schedule already executed offline; new input length/integrity/diversity, not increasing steps to rescue old fixture",
        "attempt_scope":"one native invocation processes all three IDs; no loop of invocations, retries, or candidate filtering",
        "scientific_boundary":"existing official test inputs; training independence unknown; not a fair benchmark"}
    path=prepared/"job.json";path.write_text(json.dumps(job,indent=2,sort_keys=True)+"\n")
    return path


def _verify_dflow_batch(attempt, job, result):
    checks=result["checks"]
    runtime=json.loads((attempt/"raw/runtime_evidence.json").read_text())
    checks["single_native_invocation"]=(job.get("native_invocations")==runtime.get("native_invocations")==1
        and job["argv"][-1].count(" -m dflow.experiments.inference_pep ")==1)
    checks["batch_config_replay"]=(sha(attempt/"batch_config.json")==job["batch_config_sha256"]==runtime["batch_config_sha256"])
    checks["selection_replay"]=sha(attempt/"selection.json")==job["selection_sha256"]==runtime["selection_sha256"]
    checks["native_schedule"]=(job["native_settings"]==runtime["native_settings"]==
        {"num_steps":400,"samples":4,"angle_purify":True,"llm":False,"x_mirror":True})
    checks["seed_and_source"]=(runtime["requested_seed"]==job["random_seed"]==44
        and runtime["source_commit"]==dflow.SOURCE_COMMIT and runtime["checkpoint_sha256"]==dflow.CHECKPOINT_SHA256)
    checks["native_entrypoint_replay"]=(sha(attempt/"work/PeptideDesign/dflow/experiments/inference_pep.py")==
        runtime["entrypoint_patched_sha256"]==job["entrypoint_patched_sha256"])
    checks["native_cache_replay"]=sha(attempt/"work/pep_cache/pep_pocket_test_structure_x_cache.lmdb")==runtime["native_cache_sha256"]
    checks["native_batch_completion"]=runtime.get("native_completed") is True and runtime["cases"]==job["cases"]
    checks["native_dataset_order"] = runtime.get("native_dataset_iteration_order") == sorted(case["case_id"] for case in job["cases"])
    mapping=runtime["native_candidates"]
    expected={f"raw/dflow_native/dflow.pt_400_4_False_x_mirror/{case['case_id']}/sample_{i}.pdb"
              for case in job["cases"] for i in range(4)}
    actual={str(p.relative_to(attempt)) for p in (attempt/"raw/dflow_native").rglob("sample_*.pdb")}
    checks["all_twelve_native_outputs"]=(set(mapping)==expected==actual and all(sha(attempt/p)==digest for p,digest in mapping.items()))
    for case in job["cases"]:
        folder=attempt/"inputs"/case["case_id"]
        checks["input_files_"+case["case_id"]]=all(sha(folder/name)==digest for name,digest in case["input_sha256"].items())
        cache=runtime["native_cache_inputs"].get(case["case_id"],{})
        checks["native_input_contract_"+case["case_id"]]=(cache.get("generated_residues")==case["length"]
            and cache.get("binder_chains")==[case["binder_chain"]] and cache.get("target_chains")==[case["target_chain"]])
        for i in range(4):
            relative=f"raw/dflow_native/dflow.pt_400_4_False_x_mirror/{case['case_id']}/sample_{i}.pdb"
            path=attempt/relative
            try:
                with tempfile.TemporaryDirectory(prefix="dflow-batch-quality-") as tmp:
                    composite=Path(tmp)/"complex.pdb"
                    binding=_context_composite(path,folder/"pocket.pdb",case["binder_chain"],composite,target_chain=case["target_chain"])
                    qc=evaluate_candidate(method="D-Flow / PeptideDesign",sequence=parse_pdb_chain_sequences(path).get(case["binder_chain"],""),
                        length_min=case["length"],length_max=case["length"],structure_path=composite,binder_chain=case["binder_chain"])
                    qc.update(case_id=case["case_id"],candidate_path=relative,raw_bindings=binding)
                    result["candidates"].append(qc)
            except (OSError,ValueError,KeyError,TypeError) as exc:
                result["candidates"].append({"case_id":case["case_id"],"candidate_path":relative,"candidate_quality_status":"fail",
                    "failed_checks":["target_context_or_candidate_binding"],"error":str(exc)})


def postprocess_contract():
    return {"method": "DiffPepBuilder", "endpoint": "native_reconstruction_amber_rosetta_full_atom",
            "source": "DiffPepBuilder/README.md:108-112; experiments/run_postprocess.py",
            "required_stages": ["recon", "fixed", "amber_relaxed", "rosetta_relaxed", "final"],
            "geometry": "same predeclared numeric criteria, canonical full-heavy-atom L schema",
            "prestage_representation": "backbone/CB endpoint is an intermediate, not final acceptance",
            "native_selection": "all candidates retained; no save_best; no affinity claim"}


def prepare_diff_postprocess(parent, prepared_root=None):
    """Complete the README-mandated native pipeline from immutable generation."""
    parent = Path(parent).resolve()
    review = verify(parent)
    if review["provenance_status"] != "pass":
        raise ValueError("parent native-generation provenance does not replay")
    parent_job = json.loads((parent / "job.json").read_text())
    if parent_job["method"] != "diffpepbuilder" or parent_job.get("native_stage"):
        raise ValueError("parent must be native DiffPepBuilder generation")
    job_id = "ma_diffpepbuilder_native03_postprocess_seed42"
    prepared = Path(prepared_root or ROOT / "benchmark_runs/method_acceptance_v1/prepared") / job_id
    prepared.mkdir(parents=True, exist_ok=False)
    producer = prepared / "complete.py"
    producer.write_text('''import hashlib,json,shutil
from pathlib import Path
root=Path('/data/attempt')
folder=root/'native/3EQS/length_11'
stem='3EQS_length_11_sample_0'
stages={name:folder/'postprocess_results'/(stem+'_'+name+'.pdb') for name in ('recon','fixed','amber_relaxed','rosetta_relaxed')}
stages['final']=folder/(stem+'_final.pdb')
stages['score']=folder/'postprocess_results/rosetta_score.sc'
stages['summary']=root/'native/postprocess_results.csv'
for name,path in stages.items():
 assert path.is_file() and path.stat().st_size, 'missing native stage '+name
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(stages['final'])==sha(stages['rosetta_relaxed']), 'native relaxation was skipped'
candidate=root/'raw/diffpepbuilder_final.pdb'
shutil.copyfile(stages['final'],candidate)
record={'native_stage':'postprocess','required_stages_complete':True,
 'stages':{name:{'path':str(path.relative_to(root)),'sha256':sha(path)} for name,path in stages.items()},
 'candidate_sha256':sha(candidate),'input_generation_sha256':sha(folder/(stem+'.pdb')),
 'input_receptor_sha256':sha(root/'ori/3EQS.pdb')}
(root/'raw/runtime_evidence.json').write_text(json.dumps(record,indent=2)+'\\n')
''')
    source = diffpepbuilder.SOURCE_ROOT
    candidate = parent / parent_job["candidate_path"]
    context = parent / "raw/diffpepbuilder_target_context.pdb"
    inner = """set -euo pipefail
source /opt/conda/etc/profile.d/conda.sh
conda activate bench-diffpepbuilder
mkdir -p /data/attempt/work /data/attempt/native/3EQS/length_11 /data/attempt/ori /data/attempt/raw
cp -a /data/source/. /data/attempt/work/
cp /data/parent/raw/diffpepbuilder_candidate.pdb /data/attempt/native/3EQS/length_11/3EQS_length_11_sample_0.pdb
cp /data/parent/raw/diffpepbuilder_target_context.pdb /data/attempt/ori/3EQS.pdb
cd /data/attempt/work
export BASE_PATH=/data/attempt/work
python experiments/run_postprocess.py --in_pdbs /data/attempt/native --ori_pdbs /data/attempt/ori --nproc 1 --postprocess_xml_path /data/attempt/work/analysis/interface_analyze.xml --amber_relax --rosetta_relax
python /prepared/complete.py
"""
    argv = ["docker","run","--rm","--name","{container_name}","--memory","16g","--cpus","4","--network","none",
            "-e","OMP_NUM_THREADS=4","-e","OPENBLAS_NUM_THREADS=4","-e","MKL_NUM_THREADS=4","-e","OPENMM_CPU_THREADS=4",
            "-e","PYTHONDONTWRITEBYTECODE=1","-v","{attempt_dir}:/data/attempt","-v",str(parent)+":/data/parent:ro",
            "-v",str(source)+":/data/source:ro","-v",str(prepared)+":/prepared:ro",IMAGES["pd-pyrosetta-methods-gpu:0.20"],"bash","-lc",inner]
    pins = {**parent_job["input_sha256"]}
    for name in ("job.json","run_result.json","launch.json","stdout.log","stderr.log","raw/runtime_evidence.json"):
        pins[str(parent/name)] = sha(parent/name)
    pins.update({str(p):sha(p) for p in (candidate,context,producer,source/"README.md")})
    for p in source.rglob("*"):
        if p.is_file() and not p.is_symlink() and p.suffix in {".py",".xml"} and ".git" not in p.parts:
            pins[str(p)] = sha(p)
    for name in ("method_acceptance_structural.py","method_acceptance_quality.py"):
        capture = prepared/name
        capture.write_bytes((ROOT/"scripts"/name).read_bytes())
        pins[str(capture)] = sha(capture)
    job = {"job_id":job_id,"method":"diffpepbuilder","method_name":"DiffPepBuilder","resource":"cpu","threads":4,
           "memory_gib":16,"timeout_seconds":3600,"argv":argv,"quality_contract":criteria(),"input_sha256":pins,
           "native_stage":"postprocess","native_settings":{"amber_relax":True,"rosetta_relax":True,"nproc":1,"save_best":False},
           "native_completion_contract":postprocess_contract(),"parent_attempt":str(parent),"source_commit":diffpepbuilder.SOURCE_COMMIT,
           "binder_chain":"A","length_min":11,"length_max":11,"candidate_path":"raw/diffpepbuilder_final.pdb"}
    path=prepared/"job.json"
    path.write_text(json.dumps(job,indent=2,sort_keys=True)+"\n")
    return path


def _verify_diff_postprocess(attempt, job, result):
    checks, records = result["checks"], result["candidates"]
    checks["native_endpoint_contract"] = job["native_completion_contract"] == postprocess_contract()
    parent = Path(job["parent_attempt"])
    parent_job = json.loads((parent/"job.json").read_text())
    if parent == attempt or parent_job.get("native_stage") or parent_job["method"] != "diffpepbuilder":
        raise ValueError("invalid parent generation stage")
    parent_review = verify(parent)
    checks["parent_generation_provenance"] = parent_review["provenance_status"] == "pass"
    result["parent_generation_review"] = parent_review
    runtime = json.loads((attempt/"raw/runtime_evidence.json").read_text())
    stages = runtime["stages"]
    checks.update(_replay_postprocess_stages(attempt, stages))
    candidate=attempt/job["candidate_path"]
    checks["candidate_digest"] = sha(candidate) == runtime["candidate_sha256"] == stages["final"]["sha256"]
    checks["parent_candidate_input"] = runtime["input_generation_sha256"] == sha(parent/parent_job["candidate_path"])
    context=parent/"raw/diffpepbuilder_target_context.pdb"
    checks["parent_receptor_input"] = runtime["input_receptor_sha256"] == sha(context)
    checks["copied_generation_replay"] = runtime["input_generation_sha256"] == sha(attempt/"native/3EQS/length_11/3EQS_length_11_sample_0.pdb")
    checks["copied_receptor_replay"] = runtime["input_receptor_sha256"] == sha(attempt/"ori/3EQS.pdb")
    recon=attempt/stages["recon"]["path"]
    checks["reconstruction_binder_coordinates"] = _same_chain_coordinates(parent/parent_job["candidate_path"],recon,"A",drop_virtual_gly_cb=True)
    checks["reconstruction_target_coordinates"] = _same_chain_coordinates(context,recon,"B")
    checks["native_postprocess_options"] = job["native_settings"] == {"amber_relax":True,"rosetta_relax":True,"nproc":1,"save_best":False}
    final_seq = parse_pdb_chain_sequences(candidate)
    checks["binder_sequence_preserved"] = final_seq.get("A") == parse_pdb_chain_sequences(parent/parent_job["candidate_path"]).get("A")
    checks["target_sequence_preserved"] = final_seq.get("B") == parse_pdb_chain_sequences(context).get("B")
    qc=_diff_fullatom_quality(candidate, final_seq.get("A",""), 11, 11, "A")
    qc.update(candidate_path=job["candidate_path"],native_completion_contract=postprocess_contract())
    records.append(qc)


def _same_chain_coordinates(source, reconstructed, chain, *, drop_virtual_gly_cb=False):
    def atoms(path):
        return {(a.residue_key,a.resname,a.atom_name):a.xyz for a in parse_pdb_atoms(path)
                if a.chain == chain and not (drop_virtual_gly_cb and a.resname == "GLY" and a.atom_name == "CB")}
    a,b=atoms(source),atoms(reconstructed)
    return bool(a) and set(a)==set(b) and all(math.dist(a[k],b[k])<=.001 for k in a)


def _replay_postprocess_stages(attempt, stages):
    checks={"all_native_stages":set(stages)==set(postprocess_contract()["required_stages"]+["score","summary"])}
    for name,row in stages.items():
        path=(attempt/row["path"]).resolve()
        path.relative_to(attempt)
        checks["native_stage_"+name]=path.is_file() and path.stat().st_size>0 and sha(path)==row["sha256"]
    checks["native_no_skipped_relaxation"] = (stages.get("final",{}).get("sha256") is not None
        and stages["final"]["sha256"]==stages.get("rosetta_relaxed",{}).get("sha256"))
    return checks


def _diff_fullatom_quality(candidate, sequence, length_min, length_max, binder_chain):
    # BindCraft selects the generic complete-heavy-atom L schema in the frozen
    # evaluator; no BindCraft execution/filter evidence is claimed or reused.
    qc=evaluate_candidate(method="BindCraft",sequence=sequence,length_min=length_min,length_max=length_max,
                          structure_path=candidate,binder_chain=binder_chain)
    qc.update(method="DiffPepBuilder",representation="native_postprocessed_full_atom_L",
              evaluator_schema="canonical full-heavy-atom L geometry (same frozen engine as BindCraft)")
    return qc


def _context_composite(candidate, context, binder_chain, destination, *, target_chain=None):
    """Bind native pocket identity/frame by all C-alpha anchors, then add full target.

    D-Flow translates the entire complex during input centering. DiffPepBuilder
    reconstructs target backbone atoms but preserves CA positions. Only a single
    translation with <=0.003 A maximum residual is accepted; no fitting/relaxation
    of the candidate is performed. Original files are never changed.
    """
    target_chain = target_chain or ("A" if binder_chain == "B" else "B")
    if target_chain == binder_chain:
        raise ValueError("target and binder chains must differ")
    a = [a for a in parse_pdb_atoms(candidate) if a.chain == target_chain and a.atom_name == "CA"]
    b = [a for a in parse_pdb_atoms(context) if a.chain == target_chain and a.atom_name == "CA"]
    if not a or len(a) != len(b) or [v.resname for v in a] != [v.resname for v in b]:
        raise ValueError("target CA sequence/coverage mismatch")
    shifts = [tuple(x-y for x,y in zip(left.xyz,right.xyz)) for left,right in zip(a,b)]
    shift = tuple(sum(row[i] for row in shifts)/len(shifts) for i in range(3))
    residual = max(math.dist(row, shift) for row in shifts)
    if residual > .003:
        raise ValueError(f"target coordinate frame cannot be replayed: {residual}")
    native_lines = candidate.read_text().splitlines()
    context_lines = context.read_text().splitlines()
    protein = lambda line: line.startswith(("ATOM  ","HETATM")) and line[21] == target_chain and line[17:20] in AA3_TO_1
    key = lambda line: (line[22:27], line[17:20], line[12:16].strip())
    native_target = [line for line in native_lines if protein(line)]
    alternatives = {}
    for line in context_lines:
        if protein(line):
            alternatives.setdefault(key(line), []).append(line)
    # D-Flow writes the complete target with one selected native conformer.
    # Replay every target atom against the context alternatives; never choose a
    # conformer according to whether it improves candidate quality.
    if {key(line) for line in native_target} == set(alternatives):
        if len(native_target) != len(alternatives) or any(line[16] != " " for line in native_target):
            raise ValueError("native target has ambiguous atom identity")
        for line in native_target:
            xyz = tuple(float(line[s:s+8]) for s in (30,38,46))
            expected = [tuple(float(alt[s:s+8])+shift[i] for i,s in enumerate((30,38,46))) for alt in alternatives[key(line)]]
            if min(math.dist(xyz, coord) for coord in expected) > .003:
                raise ValueError("native full target atom does not replay against context")
        destination.write_bytes(candidate.read_bytes())
        return {"source_candidate_sha256": sha(candidate), "source_context_sha256": sha(context),
                "target_ca_count": len(a), "translation_angstrom": shift,
                "target_atom_count": len(native_target),
                "target_altloc_policy": "native_full_target_atoms_verified_against_context",
                "target_scope": "native protein target; context-only solvent and ligands are not invented",
                "maximum_ca_residual_angstrom": residual, "qc_composite_sha256": sha(destination)}
    lines = [line for line in native_lines if line.startswith(("ATOM  ","HETATM")) and line[21] == binder_chain]
    for line in context_lines:
        if line.startswith(("ATOM  ","HETATM")) and line[21] == target_chain:
            if line[16] not in {" ","A"}:
                raise ValueError("context has unresolved alternative conformers")
            # The native processed receptor retains A labels after selecting
            # that sole conformer. Remove only the label in the QC derivative;
            # no alternate coordinates are substituted or silently discarded.
            line = line[:16] + " " + line[17:]
            xyz = [float(line[s:s+8]) + shift[i] for i,s in enumerate((30,38,46))]
            lines.append(line[:30] + "".join(f"{v:8.3f}" for v in xyz) + line[54:])
    destination.write_text("\n".join(lines) + "\nEND\n")
    return {"source_candidate_sha256": sha(candidate), "source_context_sha256": sha(context),
            "target_ca_count": len(a), "translation_angstrom": shift,
            "target_altloc_policy": "sole_native_A_labels_normalized; other_conformers_rejected",
            "maximum_ca_residual_angstrom": residual, "qc_composite_sha256": sha(destination)}


def verify(attempt):
    """Replay completed native execution and every generated candidate, read-only."""
    attempt = Path(attempt).resolve()
    checks, records, errors = {}, [], []
    result = {"attempt_dir": str(attempt), "checks": checks, "candidates": records,
              "errors": errors, "evidence_boundary": "native_method_integrity_not_benchmark_or_affinity"}
    try:
        job = json.loads((attempt / "job.json").read_text())
        result.update(method=job["method"], job_id=job["job_id"])
        method = job.get("method_name") or {POLICY_SLUGS[k]: v[0] for k,v in METHODS.items()}[job["method"]]
        run = json.loads((attempt / "run_result.json").read_text())
        launch = json.loads((attempt / "launch.json").read_text())
        checks["execution_completed"] = run["exit_code"] == 0 and run["termination_reason"] == "completed"
        checks["job_binding"] = run["job_sha256"] == sha(attempt / "job.json")
        checks["logs_bound"] = all(run.get(name+"_sha256") == sha(attempt/(name+".log")) for name in ("stdout","stderr"))
        checks["quality_contract_unchanged"] = job["quality_contract"] == criteria()
        argv = launch["argv"]
        expected_argv = [v.replace("{attempt_dir}",str(attempt)).replace("{container_name}","pd-ma-"+job["job_id"]) for v in job["argv"]]
        checks["launch_command_binding"] = argv == expected_argv
        checks["offline_execution"] = "--network" in argv and argv[argv.index("--network")+1] == "none"
        expected_image = IMAGES["pd-pyrosetta-methods-gpu:0.20" if job["method"]=="diffpepbuilder" else "pd-benchmark-methods-gpu:0.21"]
        checks["immutable_image"] = expected_image in argv
        bad_inputs = [p for p,digest in job["input_sha256"].items() if not Path(p).is_file() or sha(p) != digest]
        checks["input_and_producer_bindings"] = not bad_inputs
        if bad_inputs:
            result["changed_inputs"] = bad_inputs
        if job.get("native_stage") == "postprocess":
            _verify_diff_postprocess(attempt, job, result)
            return _finish_verify(result)
        if job["method"] == "dflow" and job.get("native_stage") == "multi_input":
            _verify_dflow_batch(attempt, job, result)
            return _finish_verify(result)
        runtime = json.loads((attempt / "raw/runtime_evidence.json").read_text())
        candidate = attempt / job["candidate_path"]
        settings = job["native_settings"]
        checks["requested_seed"] = runtime.get("requested_seed") == job.get("random_seed",int(job["job_id"].rsplit("seed",1)[1]))
        if job["method"] == "dflow":
            mapping = runtime.get("native_candidates", {})
            expected = settings["samples"]
            candidates = [attempt / p for p in sorted(mapping)]
            checks["native_batch_complete"] = len(candidates) == expected and all(sha(attempt/p)==v for p,v in mapping.items())
            # The first native task predates the multi-candidate runtime schema.
            # Recover its sole native file using the already-bound candidate SHA
            # and exact captured 200-step / one-sample command, never a later
            # schedule. Its missing offline asset provenance remains a failure.
            single_schema = (job["job_id"] == "ma_dflow_native01_seed42" and expected == 1
                and settings["num_steps"] == 200 and "native_candidates" not in runtime and "num_samples" not in runtime)
            if single_schema:
                candidates = sorted((attempt/"raw/dflow_native/dflow.pt_200_1_False_x_mirror").glob("*/sample_*.pdb"))
                checks["native_batch_complete"] = (len(candidates)==1 and candidates[0].name=="sample_0.pdb"
                    and sha(candidates[0])==sha(candidate)==runtime.get("candidate_sha256"))
                result["runtime_schema"] = "early_single_candidate_v1; sample count replayed from captured command and sole native-file digest"
            checks["native_schedule"] = all(runtime.get(k)==v for k,v in {
                "num_steps":settings["num_steps"], "angle_purify":True,
                "llm":False, "x_mirror":True, "source_commit":dflow.SOURCE_COMMIT}.items())
            checks["native_sample_count"] = (single_schema and checks["native_batch_complete"]) or runtime.get("num_samples")==expected
            checks["native_command_schedule"] = (f"sample.num_steps={settings['num_steps']} " in argv[-1]
                and f"sample.num_samples={expected} " in argv[-1] and "sample.angle_purify=True" in argv[-1])
            checks["checkpoint_identity"] = runtime.get("checkpoint_sha256") == dflow.CHECKPOINT_SHA256
            checks["candidate_digest"] = runtime.get("candidate_sha256") == sha(candidate)
            context = attempt / "raw/dflow_target_context.pdb"
            checks["target_context_digest"] = runtime.get("target_context_sha256") == sha(context)
        elif job["method"] == "diffpepbuilder":
            source = Path(runtime["source_candidate_path"].replace("/data/attempt",str(attempt),1))
            candidates = [candidate]
            checks["native_candidate_copy"] = source.is_file() and sha(source)==sha(candidate)
            checks["native_schedule"] = "inference.denoising.num_t=200 " in argv[-1] and "inference.ss_bond.build_ss_bond=True" in argv[-1]
            context = attempt / "raw/diffpepbuilder_target_context.pdb"
            checks["target_context_digest"] = runtime.get("target_context_sha256") == sha(context)
            checks["source_identity"] = runtime.get("source_commit") == diffpepbuilder.SOURCE_COMMIT
            checks["model_identity"] = runtime.get("model_asset_sha256") == diffpepbuilder.MODEL_ASSETS
        else:
            candidates, context = [candidate], None
            checks["native_schedule"] = runtime.get("native_design_schedule") == {"soft":300,"temperature":100,"hard":10}
            checks["cyclic_offset_replayed"] = (runtime.get("cyclic_offset_applied") is True and runtime.get("cyclic_offset_type")==2
                                                  and type(runtime.get("terminal_offset")) is int and abs(runtime["terminal_offset"])==1)
            checks["candidate_digest"] = runtime.get("candidate_sha256") == sha(candidate)
            checks["source_identity"] = runtime.get("source_commit") == colabdesign.SOURCE_COMMIT
            checks["model_identity"] = (runtime.get("alphafold_params_sha256")==colabdesign.ALPHAFOLD_PARAMS_SHA256
                and runtime.get("source_notebook_sha256")==colabdesign.SOURCE_NOTEBOOK_SHA256)
            target = next(Path(p) for p,d in job["input_sha256"].items() if d == job["target_input_sha256"])
            checks["target_sequence_binding"] = parse_pdb_chain_sequences(candidate).get("A") == parse_pdb_chain_sequences(target).get("A")
        for native in candidates:
            native.resolve().relative_to(attempt)
            try:
                with tempfile.TemporaryDirectory(prefix="method-quality-context-") as tmp:
                    path = native
                    if context is not None:
                        path = Path(tmp)/"qc_complex.pdb"
                        binding = _context_composite(native,context,job["binder_chain"],path)
                    else:
                        binding = {"source_candidate_sha256":sha(native)}
                    sequence = parse_pdb_chain_sequences(native).get(job["binder_chain"],"")
                    qc = evaluate_candidate(method=method, sequence=sequence, length_min=job["length_min"],length_max=job["length_max"],
                                            structure_path=path,binder_chain=job["binder_chain"])
                    qc.update(candidate_path=str(native.relative_to(attempt)),raw_bindings=binding)
                    records.append(qc)
            except (OSError,ValueError,KeyError,TypeError) as exc:
                records.append({"candidate_path":str(native.relative_to(attempt)),"candidate_quality_status":"fail",
                                "failed_checks":["target_context_or_candidate_binding"],"error":str(exc)})
    except (OSError,ValueError,KeyError,TypeError,StopIteration) as exc:
        errors.append(str(exc))
    return _finish_verify(result)


def _finish_verify(result):
    checks, errors, records = result["checks"], result["errors"], result["candidates"]
    result["provenance_status"] = "pass" if checks and all(checks.values()) and not errors else "fail"
    result["qualified_candidates"] = sum(r["candidate_quality_status"]=="pass" for r in records)
    result["method_acceptance_status"] = "pass" if result["provenance_status"]=="pass" and result["qualified_candidates"] else "not_passed"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("method", choices=METHODS)
    prep.add_argument("--seed", type=int, default=42)
    prep.add_argument("--suffix", default="native01")
    prep.add_argument("--steps", type=int, default=200)
    prep.add_argument("--samples", type=int, default=1)
    check = commands.add_parser("inspect")
    check.add_argument("attempt", type=Path)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("attempt", type=Path)
    postprocess_parser = commands.add_parser("prepare-postprocess")
    postprocess_parser.add_argument("parent", type=Path)
    batch_parser = commands.add_parser("prepare-dflow-batch")
    batch_parser.add_argument("selection", type=Path)
    args = parser.parse_args(argv)
    if args.command == "prepare-dflow-batch":
        print(prepare_dflow_batch(args.selection))
    elif args.command == "prepare-postprocess":
        print(prepare_diff_postprocess(args.parent))
    elif args.command == "prepare":
        print(prepare(args.method, seed=args.seed, suffix=args.suffix, steps=args.steps, samples=args.samples))
    elif args.command == "verify":
        print(json.dumps(verify(args.attempt), indent=2, allow_nan=False))
    else:
        print(json.dumps(inspect(args.attempt), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
