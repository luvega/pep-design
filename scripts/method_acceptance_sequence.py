#!/usr/bin/env python3
"""Native sequence-method execution and replay checks for method acceptance v1.

This module does not allocate an execution budget or launch an environment. The
project's shared runner must do that before invoking ``run``. Preparation and
``verify`` are CPU-only and never load a model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any


CANONICAL_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")
REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / "benchmark_runs" / "method_acceptance_v1"
PEPMLM_SOURCE = Path("/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/pepmlm")
PEPMLM_REVISION = "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436"
PEPMLM_WEIGHTS_REVISION = "898fca941a9057aebdd1a6164b5ee09a1a71780e"
PEPMLM_MODEL = Path(
    "/data/protein-design/data/benchmark_models/huggingface/hub/"
    "models--TianlaiChen--PepMLM-650M/snapshots/" + PEPMLM_WEIGHTS_REVISION
)
PEPMLM_SOURCE_SHA = "2c1844028c459e8e96d756da795b620b4ccaa65b98dd62c6f904100f0dc1e49b"
PEPMLM_WEIGHTS_SHA = "8a3225bca1f9acd9f701ca2e46597c12bab92320e32b68f380ddf3b6d3b20770"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def semantic_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write_json_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def validate_sequence(sequence: str, *, label: str = "sequence") -> None:
    if not isinstance(sequence, str) or not sequence or set(sequence) - CANONICAL_AA:
        raise ValueError(f"{label} must contain only unmodified uppercase canonical residues")


def pepmlm_candidate_qc(sequence: str, ppl: Any, requested_length: int) -> dict[str, Any]:
    """Numerical native PPL and sequence validity, not binding-quality inference."""
    canonical = isinstance(sequence, str) and bool(sequence) and not (set(sequence) - CANONICAL_AA)
    length_ok = isinstance(sequence, str) and len(sequence) == requested_length
    ppl_ok = isinstance(ppl, (int, float)) and not isinstance(ppl, bool) and math.isfinite(ppl) and ppl >= 1
    checks = {
        "canonical_sequence": bool(canonical),
        "requested_length": bool(length_ok),
        "native_pseudo_perplexity_finite_ge_one": bool(ppl_ok),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "native_ppl_threshold": None,
        "quality_scope": "canonical sequence and numerically valid native pseudo-perplexity",
        "not_evaluated": ["binding affinity", "structure", "biological activity"],
    }


def validate_config(config: dict[str, Any], *, check_files: bool = True) -> None:
    if config.get("schema_version") != "method_acceptance_sequence_v1":
        raise ValueError("unsupported sequence execution schema")
    method = config.get("method")
    if method not in {"PepMLM", "SaLT&PepPr"}:
        raise ValueError("unsupported method")
    validate_sequence(config["input"]["sequence"], label="input sequence")
    params = config["parameters"]
    if not isinstance(params.get("seed"), int) or isinstance(params["seed"], bool):
        raise ValueError("an explicit integer seed is required")
    if not 1 <= params["peptide_length"] <= 50 or not 1 <= params["num_candidates"] <= 8:
        raise ValueError("bounded sequence lengths/candidate count exceeded")
    if len(config["input"]["sequence"]) + params["peptide_length"] > 1022:
        raise ValueError("bounded ESM context exceeded")
    if not config["input"].get("provenance"):
        raise ValueError("input provenance is required")
    if not config.get("license", {}).get("execution_scope_cleared", False):
        raise ValueError("method usage scope has not been cleared")
    if method == "PepMLM":
        if params.get("top_k") != 3:
            raise ValueError("this contract fixes native top_k=3")
        if config["quality_policy"].get("ppl_hard_threshold") is not None:
            raise ValueError("native source does not define a PPL passing threshold")
    else:
        if not config["input"].get("target_id") or not config["input"].get("partner_id"):
            raise ValueError("SaLT&PepPr needs an identified target and interacting partner")
        if not config["input"].get("interaction_evidence"):
            raise ValueError("SaLT&PepPr requires physical PPI evidence")
        # The paper's prose does not uniquely specify the author's extraction
        # implementation. Execution stays blocked until that source is pinned.
        if params.get("selection_implementation") != "official_notebook_pinned":
            raise ValueError("official SaLT&PepPr notebook extraction source is required")
    if check_files:
        for entry in config["pinned_files"]:
            if sha256_file(Path(entry["path"])) != entry["sha256"]:
                raise ValueError(f"pinned file changed: {entry['role']}")


def _pin(path: Path, role: str) -> dict[str, str]:
    return {"path": str(path), "sha256": sha256_file(path), "role": role}


def prepare_pepmlm(destination: Path) -> dict[str, Any]:
    """Prepare the first real canonical PDB-derived author test case, without inference."""
    commit = subprocess.check_output(["git", "-C", str(PEPMLM_SOURCE), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(PEPMLM_SOURCE), "status", "--porcelain"], text=True).strip()
    if commit != PEPMLM_REVISION or dirty:
        raise ValueError("PepMLM source checkout identity or cleanliness mismatch")
    dataset = PEPMLM_SOURCE / "data/pepnn_test.csv"
    with dataset.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    sequence, reference = row["Receptor Sequence"], row["Sequence"]
    validate_sequence(sequence)
    validate_sequence(reference, label="native reference peptide")
    native = PEPMLM_SOURCE / "scripts/generation.py"
    if sha256_file(native) != PEPMLM_SOURCE_SHA:
        raise ValueError("PepMLM native generation source changed")
    if sha256_file(PEPMLM_MODEL / "pytorch_model.bin") != PEPMLM_WEIGHTS_SHA:
        raise ValueError("PepMLM model weights changed")
    config = {
        "schema_version": "method_acceptance_sequence_v1", "method": "PepMLM",
        "source_revision": PEPMLM_REVISION,
        "source_generation_path": str(native), "model_path": str(PEPMLM_MODEL),
        "model_revision": PEPMLM_WEIGHTS_REVISION,
        "input": {
            "target_id": f"{row['PDB']}_{row['Receptor']}", "sequence": sequence,
            "reference_peptide": reference,
            "provenance": {"dataset_path": str(dataset), "data_row_1based": 1,
                           "pdb_id": row["PDB"], "receptor_chain": row["Receptor"],
                           "reference_peptide_chain": row["Peptide"],
                           "source_commit": PEPMLM_REVISION,
                           "scope": "author test fixture for runtime acceptance; no independent test claim"},
        },
        "parameters": {"seed": 42, "peptide_length": len(reference), "top_k": 3, "num_candidates": 4},
        "quality_policy": {
            "canonical_only": True, "length_equals_requested": True,
            "ppl_hard_threshold": None, "ppl_requirement": "finite and >= 1",
            "selection": "lowest native PPL among candidates passing sequence checks",
            "scope": "sequence validity and native numerical quality only; no binding-quality claim",
        },
        "license": {"execution_scope_cleared": True,
                    "model_card_license": "MIT",
                    "model_card_url": "https://huggingface.co/ChatterjeeLab/PepMLM-650M",
                    "historical_model_id": "TianlaiChen/PepMLM-650M",
                    "use": "local academic computational method acceptance"},
        "pinned_files": [_pin(native, "native_generation"), _pin(dataset, "input_dataset")]
            + [_pin(p, "model_" + p.name) for p in sorted(PEPMLM_MODEL.iterdir()) if p.is_file()],
        "old_WWX_diagnosis": {
            "old_input": "upstream scripts/data/test.csv data row 1 has trailing XXX and binder KPLX",
            "old_adapter": "v0.34 deleted all target X and forced peptide length 3",
            "vocabulary": "X is a regular ESM vocabulary token; native full-vocabulary sampling can emit it",
            "new_policy": "real canonical target input; native sampling unchanged; no post-generation X deletion",
            "causal_limit": "input defects do not establish the unique cause of historical WWX output",
        },
    }
    validate_config(config)
    destination.mkdir(parents=True, exist_ok=True)
    write_json_new(destination / "config.json", config)
    return config


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load pinned source {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _environment(torch) -> dict[str, Any]:
    packages = {}
    for name in ("torch", "transformers", "numpy", "pandas", "fair-esm", "pytorch-lightning", "torchmetrics"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": sys.version, "executable": sys.executable, "packages": packages,
            "cuda_runtime": torch.version.cuda, "cuda_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}


def _run_pepmlm(config: dict[str, Any], output: Path, torch) -> dict[str, Any]:
    import numpy as np
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(config["model_path"], local_files_only=True)
    sequence = config["input"]["sequence"]
    params = config["parameters"]
    tokens = tokenizer(sequence, return_tensors="pt")["input_ids"][0].tolist()
    decoded_input = tokenizer.decode(tokens, skip_special_tokens=True).replace(" ", "")
    if decoded_input != sequence or len(tokens) != len(sequence) + 2:
        raise ValueError("canonical input does not round-trip one token per amino acid")
    masked = tokenizer(sequence + tokenizer.mask_token * params["peptide_length"], return_tensors="pt")
    if int((masked["input_ids"] == tokenizer.mask_token_id).sum()) != params["peptide_length"]:
        raise ValueError("native mask count does not equal requested peptide length")
    model = AutoModelForMaskedLM.from_pretrained(config["model_path"], local_files_only=True)
    model = model.to("cuda").eval()
    native = _load_module(Path(config["source_generation_path"]), "pepmlm_native_acceptance")
    # Upstream file intentionally contains functions only. These are its notebook globals.
    native.torch, native.np = torch, np
    native.Categorical = torch.distributions.Categorical
    native.tokenizer, native.model = tokenizer, model
    decoded_tokens: list[list[int]] = []
    original_decode = tokenizer.decode

    def record_native_decode(token_ids, *args, **kwargs):
        decoded_tokens.append([int(t) for t in token_ids.detach().cpu().tolist()])
        return original_decode(token_ids, *args, **kwargs)

    tokenizer.decode = record_native_decode
    generated = native.generate_peptide_for_single_sequence(
        sequence, params["peptide_length"], params["top_k"], params["num_candidates"]
    )
    tokenizer.decode = original_decode
    if len(generated) != params["num_candidates"] or len(decoded_tokens) != len(generated):
        raise ValueError("native output count or token provenance mismatch")
    candidates = []
    for index, ((binder, ppl), token_ids) in enumerate(zip(generated, decoded_tokens), 1):
        ppl = float(ppl)
        candidates.append({"candidate_id": f"pepmlm_{index:03d}", "sequence": binder,
                           "native_pseudo_perplexity": ppl if math.isfinite(ppl) else None,
                           "native_pseudo_perplexity_nonfinite": None if math.isfinite(ppl) else str(ppl),
                           "native_token_ids": token_ids,
                           "native_tokens": tokenizer.convert_ids_to_tokens(token_ids),
                           "qc": pepmlm_candidate_qc(binder, ppl, params["peptide_length"])})
    write_json_new(output / "native_candidates.json", candidates)
    passing = [row for row in candidates if row["qc"]["status"] == "pass"]
    selected = min(passing, key=lambda row: row["native_pseudo_perplexity"])["candidate_id"] if passing else None
    return {"candidates": candidates, "selected_candidate_id": selected,
            "input_token_ids": tokens, "native_generation_invoked": True,
            "native_ppl_invoked": "compute_pseudo_perplexity via upstream generation function",
            "native_algorithm_changes": [], "passed": bool(passing)}


def _run_saltnpeppr(config: dict[str, Any], output: Path, torch) -> dict[str, Any]:
    raise RuntimeError("SaLT&PepPr native notebook extraction has not yet been pinned; no inference started")


def validate_execution_lease(config_path: Path, output: Path, config: dict[str, Any]) -> dict[str, str]:
    lease = os.environ.get("METHOD_ACCEPTANCE_ATTEMPT_DIR")
    if not lease or Path(lease).resolve() != output.resolve().parent:
        raise ValueError("a matching shared-runner execution lease is required")
    attempt = Path(lease).resolve()
    job_path, policy_path = attempt / "job.json", attempt / "policy.json"
    job, policy = json.loads(job_path.read_text()), json.loads(policy_path.read_text())
    method = {"PepMLM": "pepmlm", "SaLT&PepPr": "saltnpeppr"}[config["method"]]
    if job["method"] != method or method not in policy["methods"]:
        raise ValueError("shared-runner method lease mismatch")
    pins = job.get("input_sha256", {})
    for path in (config_path.resolve(), Path(__file__).resolve()):
        if pins.get(str(path)) != sha256_file(path):
            raise ValueError("execution lease must pin the config and wrapper")
    if job.get("quality_contract") != config["quality_policy"]:
        raise ValueError("execution lease quality contract differs from prepared config")
    return {"attempt_dir": str(attempt), "job_sha256": sha256_file(job_path),
            "policy_sha256": sha256_file(policy_path)}


def run(config_path: Path, output: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    output = output.resolve()
    if not output.is_relative_to(RUNTIME_ROOT.resolve()):
        raise ValueError("method outputs must remain in the designated gitignored stage root")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("refusing to overwrite existing method evidence")
    lease = validate_execution_lease(config_path, output, config)
    import numpy as np
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("the pinned execution contract requires CUDA")
    torch.set_num_threads(min(24, int(os.environ.get("OMP_NUM_THREADS", "8"))))
    seed = config["parameters"]["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    output.mkdir(parents=True, exist_ok=True)
    result = (_run_pepmlm(config, output, torch) if config["method"] == "PepMLM"
              else _run_saltnpeppr(config, output, torch))
    result.update({"schema_version": "method_acceptance_sequence_result_v1", "method": config["method"],
                   "config_path": str(config_path.resolve()), "config_sha256": sha256_file(config_path),
                   "config_semantic_sha256": semantic_sha256(config), "execution_lease": lease,
                   "producer_sha256": sha256_file(Path(__file__)), "environment": _environment(torch),
                   "requested_seed": seed, "effective_seed": seed,
                   "evidence_boundary": "method_native_runtime_and_sequence_quality_only_not_benchmark_or_binding_validation",
                   "raw_file_sha256": {p.name: sha256_file(p) for p in output.iterdir() if p.is_file()}})
    write_json_new(output / "sequence_result.json", result)
    return result


def verify(config: dict[str, Any], output: Path) -> dict[str, Any]:
    """Recompute sequence/output checks without importing any model dependency."""
    validate_config(config, check_files=False)
    result = json.loads((output / "sequence_result.json").read_text())
    if result.get("method") != config["method"]:
        raise ValueError("method binding mismatch")
    if result.get("config_semantic_sha256") != semantic_sha256(config):
        raise ValueError("config binding mismatch")
    for filename, digest in result["raw_file_sha256"].items():
        path = output / filename
        if path.parent.resolve() != output.resolve() or sha256_file(path) != digest:
            raise ValueError("raw evidence binding mismatch")
    if config["method"] == "PepMLM":
        candidates = json.loads((output / "native_candidates.json").read_text())
        if candidates != result["candidates"] or len(candidates) != config["parameters"]["num_candidates"]:
            raise ValueError("native candidate list mismatch")
        for row in candidates:
            token_ids = row.get("native_token_ids", [])
            native_tokens = row.get("native_tokens", [])
            if len(token_ids) != config["parameters"]["peptide_length"] or len(native_tokens) != len(token_ids):
                raise ValueError("native token count does not replay")
            if row["qc"]["status"] == "pass" and "".join(native_tokens) != row["sequence"]:
                raise ValueError("native token sequence does not replay")
            qc = pepmlm_candidate_qc(row["sequence"], row["native_pseudo_perplexity"], config["parameters"]["peptide_length"])
            if qc != row["qc"]:
                raise ValueError("candidate QC does not replay")
        passing = [row for row in candidates if row["qc"]["status"] == "pass"]
        selected = min(passing, key=lambda row: row["native_pseudo_perplexity"])["candidate_id"] if passing else None
    else:
        raise ValueError("SaLT&PepPr native notebook extraction verifier is not yet available")
    if result["selected_candidate_id"] != selected or result["passed"] is not bool(passing):
        raise ValueError("selected candidate or passing result does not replay")
    return {"method": config["method"], "passed": bool(passing), "candidate_count": len(candidates),
            "qualified_candidate_count": len(passing), "selected_candidate_id": selected}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare-pepmlm")
    prepare.add_argument("--destination", type=Path, required=True)
    for action in ("run", "verify"):
        command = sub.add_parser(action)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare-pepmlm":
        config = prepare_pepmlm(args.destination)
        print(json.dumps({"method": config["method"], "target": config["input"]["target_id"], "parameters": config["parameters"]}))
        return 0
    result = (run(args.config, args.output) if args.action == "run" else
              verify(json.loads(args.config.read_text()), args.output))
    print(json.dumps({key: result[key] for key in ("method", "passed", "selected_candidate_id")}, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
