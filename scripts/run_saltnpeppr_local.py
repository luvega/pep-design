#!/usr/bin/env python3
"""Bounded, local SaLT&PepPr per-residue inference (not peptide generation)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = REPO_ROOT / "benchmark_runs" / "v0.36_saltnpeppr"
SOURCE_FILE = RUN_ROOT / "source" / "model.py"
CHECKPOINT = RUN_ROOT / "model" / "production_version_epoch=3.ckpt"
SOURCE_REVISION = "5f7e08f0ccdd6d4f9a2cfb4f1174779a9bd95453"
SOURCE_SHA256 = "a2925bfd445aa363615fe25a6345a4eff6cd454bea6310d8de79d3ee58c6dfc5"
CHECKPOINT_SHA256 = "3a9c64f10535198cce51a05576f54eeb54301cca0627536d67dfe3f4128479ff"
CANONICAL_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")
MAX_LENGTH = 1022  # ESM-2's 1024-token context includes BOS and EOS.


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    name: str | None = None
    sequence: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                records.append((name, "".join(sequence)))
            name = line[1:].split(maxsplit=1)[0]
            sequence = []
        elif name is None:
            raise ValueError("FASTA sequence appears before its header")
        else:
            sequence.append(line)
    if name is not None:
        records.append((name, "".join(sequence)))
    return records


def validate_records(records: list[tuple[str, str]]) -> None:
    if not records:
        raise ValueError("no input sequence")
    names: set[str] = set()
    for name, sequence in records:
        if not name or name in names or any(char in name for char in "\t\r\n,"):
            raise ValueError(f"invalid or duplicate record ID: {name!r}")
        names.add(name)
        if not 1 <= len(sequence) <= MAX_LENGTH:
            raise ValueError(f"{name}: length must be 1..{MAX_LENGTH}")
        unexpected = set(sequence) - CANONICAL_AA
        if unexpected:
            raise ValueError(f"{name}: noncanonical/invalid residues: {''.join(sorted(unexpected))}")


def load_vendor_model(source: Path, checkpoint: Path, device: str):
    import esm
    import torch

    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError(f"source SHA-256 mismatch: {source}")
    if sha256_file(checkpoint) != CHECKPOINT_SHA256:
        raise ValueError(f"checkpoint SHA-256 mismatch: {checkpoint}")

    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    config = payload["hyper_parameters"]["config"]
    state_dict = payload["state_dict"]
    if not any(key.startswith("esm_transformer.") for key in state_dict):
        raise ValueError("checkpoint does not contain ESM-2 weights")

    spec = importlib.util.spec_from_file_location("saltnpeppr_vendor_model", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pinned source: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Vendor constructor otherwise downloads ESM-2. The pinned checkpoint already
    # contains its weights, so instantiate the identical architecture locally.
    original_factory = esm.pretrained.esm2_t33_650M_UR50D

    def local_esm2_factory():
        alphabet = esm.Alphabet.from_architecture("ESM-1b")
        transformer = esm.ESM2(
            num_layers=33,
            embed_dim=1280,
            attention_heads=20,
            alphabet=alphabet,
            token_dropout=True,
        )
        return transformer, alphabet

    try:
        esm.pretrained.esm2_t33_650M_UR50D = local_esm2_factory
        model = module.SALTnPEPPR(config)
    finally:
        esm.pretrained.esm2_t33_650M_UR50D = original_factory
    model.load_state_dict(state_dict, strict=True)
    del payload, state_dict
    return model.to(device).eval(), esm.Alphabet.from_architecture("ESM-1b")


def run(args: argparse.Namespace) -> int:
    import torch

    records = parse_fasta(args.fasta) if args.fasta else [(args.record_id, args.sequence)]
    validate_records(records)

    output = args.output.resolve()
    if not output.is_relative_to(RUN_ROOT.resolve()):
        raise ValueError(f"output must stay under gitignored runtime root: {RUN_ROOT}")
    metadata_path = output.with_name(output.name + ".runtime.json")
    if output.exists() or metadata_path.exists():
        raise FileExistsError("output or runtime record already exists; choose a new path")

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device == "auto":
        device = "cpu"

    model, alphabet = load_vendor_model(SOURCE_FILE, CHECKPOINT, device)
    batch_converter = alphabet.get_batch_converter()
    rows: list[tuple[str, int, str, float]] = []
    with torch.inference_mode():
        for name, sequence in records:
            _, _, tokens = batch_converter([(name, sequence)])
            logits = model(tokens.to(device))
            if tuple(logits.shape) != (len(sequence), 2):
                raise RuntimeError(f"{name}: unexpected output shape {tuple(logits.shape)}")
            probabilities = torch.softmax(logits.float(), dim=-1)[:, 1].cpu().tolist()
            if any(not math.isfinite(value) or not 0 <= value <= 1 for value in probabilities):
                raise RuntimeError(f"{name}: invalid probability")
            rows.extend((name, index, residue, probability) for index, (residue, probability)
                        in enumerate(zip(sequence, probabilities, strict=True), start=1))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("record_id", "position_1based", "residue", "binder_probability"))
        writer.writerows(rows)

    metadata = {
        "method": "SaLT&PepPr",
        "scope": "local per-residue interface-probability inference only; not peptide generation, scoring, or biological validation",
        "source_repository": "https://huggingface.co/ubiquitx/saltnpeppr",
        "source_revision": SOURCE_REVISION,
        "source_model_sha256": SOURCE_SHA256,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "input_sha256": sha256_file(args.fasta) if args.fasta else hashlib.sha256(args.sequence.encode()).hexdigest(),
        "output_sha256": sha256_file(output),
        "record_count": len(records),
        "residue_count": len(rows),
        "device": device,
        "license_notice": "Non-commercial, non-drug-discovery research only. UbiquiTx owns output IP; attribution required. No hosted service.",
        "license_url": "https://huggingface.co/ubiquitx/saltnpeppr/blob/main/SaLT%26PepPr%20Licence%20FINAL.pdf",
    }
    with metadata_path.open("x", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Wrote {len(rows)} per-residue probabilities: {output}")
    print(f"Runtime/license record: {metadata_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--fasta", type=Path, help="input FASTA with unique record IDs")
    input_group.add_argument("--sequence", help="single uppercase canonical amino-acid sequence")
    parser.add_argument("--record-id", default="sequence_1", help="ID used with --sequence")
    parser.add_argument("--output", type=Path, required=True, help=f"new CSV path under {RUN_ROOT}")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"SaLT&PepPr local adapter: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
