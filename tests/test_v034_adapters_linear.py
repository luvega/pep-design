from __future__ import annotations

import csv
import hashlib
import importlib
import json
from pathlib import Path

import pytest


FORBIDDEN = ("wget", "curl", "pip install", "git clone", "score", "rank")


def load_adapter(name: str):
    return importlib.import_module(f"scripts.v034_adapters.{name}")


def base_job(tmp_path: Path, method: str, **updates: str) -> dict[str, str]:
    target = tmp_path / "3EQS.pdb"
    target.write_text("HEADER    TEST INPUT\n", encoding="utf-8")
    row = {
        "job_id": f"v034_{method.lower()}_seed42",
        "method": method,
        "task_id": "T2_structure_peptide_binder",
        "target_id": "mdm2_p53_3eqs_fixture",
        "target_sequence": "MPEPTIDEXXX",
        "target_pdb_path": str(target),
        "target_pdb_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "random_seed": "42",
        "length_min": "11",
        "length_max": "11",
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
    }
    row.update(updates)
    return row


def base_execution(image: str) -> dict[str, str]:
    return {"container_or_env": image, "max_runtime_sec": "900"}


def write_runtime(raw: Path, seed: int = 42) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "runtime_evidence.json").write_text(
        json.dumps(
            {
                "requested_seed": seed,
                "effective_seed": seed,
                "seed_control_status": "honored",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def write_pepglad_legacy_runtime(raw: Path, adapter: object) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "runtime_evidence.json").write_text(
        json.dumps(
            {
                "requested_seed": 42,
                "effective_seed": 42,
                "seed_control_status": "honored",
                "source_commit": getattr(adapter, "SOURCE_COMMIT"),
                "source_entrypoint_sha256": getattr(
                    adapter, "SOURCE_ENTRYPOINT_SHA256"
                ),
                "model_weights_sha256": getattr(adapter, "MODEL_WEIGHTS_SHA256"),
                "source_candidate_path": (
                    "/data/attempt/work/codesign/3EQS_0.pdb"
                ),
                "container_image": getattr(adapter, "DEFAULT_IMAGE"),
                "conda_environment": getattr(adapter, "DEFAULT_ENV"),
            }
        )
        + "\n",
        encoding="utf-8",
    )


def pdb_atom(serial: int, residue: str, chain: str, resseq: int) -> str:
    x = float(serial)
    return (
        f"ATOM  {serial:5d}  CA  {residue:>3s} {chain:1s}{resseq:4d}    "
        f"{x:8.3f}{0.0:8.3f}{0.0:8.3f}  1.00 20.00           C\n"
    )


def write_complex(path: Path, target_chain: str, binder_chain: str, binder_sequence: str) -> None:
    aa1_to_3 = {
        "A": "ALA",
        "C": "CYS",
        "D": "ASP",
        "E": "GLU",
        "F": "PHE",
        "G": "GLY",
        "H": "HIS",
        "I": "ILE",
        "K": "LYS",
        "L": "LEU",
        "M": "MET",
        "N": "ASN",
        "P": "PRO",
        "Q": "GLN",
        "R": "ARG",
        "S": "SER",
        "T": "THR",
        "V": "VAL",
        "W": "TRP",
        "Y": "TYR",
    }
    lines = [pdb_atom(1, "ALA", target_chain, 1)]
    lines.extend(
        pdb_atom(index + 2, aa1_to_3[residue], binder_chain, index + 1)
        for index, residue in enumerate(binder_sequence)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines) + "END\n", encoding="utf-8")


def assert_package(command: list[str], attempt: Path) -> str:
    command_path = attempt / "command.sh"
    assert command == ["bash", str(command_path)]
    assert command_path.stat().st_mode & 0o111
    text = command_path.read_text(encoding="utf-8")
    lowered = text.lower()
    assert all(token not in lowered for token in FORBIDDEN)
    assert (attempt / "raw").is_dir()
    return text


def assert_runtime_honored(runtime: dict[str, object]) -> None:
    assert runtime["requested_seed"] == 42
    assert runtime["effective_seed"] == 42
    assert runtime["seed_control_status"] == "honored"


def test_pepmlm_prepare_packages_seeded_three_mask_real_entrypoint(tmp_path: Path) -> None:
    adapter = load_adapter("pepmlm")
    attempt = tmp_path / "attempt_001"
    job = base_job(
        tmp_path,
        "PepMLM",
        task_id="T1_sequence_binder",
        length_min="3",
        length_max="3",
        expected_target_chain="not_applicable",
        expected_binder_chain="not_applicable",
    )

    text = assert_package(
        adapter.prepare(job, base_execution("pd-benchmark-methods-gpu:0.21/bench-pepmlm"), attempt),
        attempt,
    )
    entry = (attempt / "pepmlm_entry.py").read_text(encoding="utf-8")

    assert adapter.METHOD == "PepMLM"
    assert len(adapter.SOURCE_COMMIT) == 40
    assert adapter.MODEL_ID == "TianlaiChen/PepMLM-650M"
    assert adapter.MODEL_REVISION == "898fca941a9057aebdd1a6164b5ee09a1a71780e"
    assert "pd-benchmark-methods-gpu:0.21" in text
    assert "conda activate bench-pepmlm" in text
    assert "pepmlm_entry.py" in text
    assert "--seed 42" in text
    assert "--n-samples 1" in text
    assert "TianlaiChen/PepMLM-650M" in entry
    assert "MASK_COUNT = 3" in entry
    assert "random.seed(SEED)" in entry
    assert "np.random.seed(SEED)" in entry
    assert "torch.manual_seed(SEED)" in entry
    assert "sample_top_k" in entry
    assert "argmax" not in entry
    assert "pepmlm_generated.csv" in entry
    assert "runtime_evidence.json" in entry
    assert (attempt / "pepmlm_sampling.py").is_file()


def test_pepmlm_top_k_sampling_is_seeded_and_reproducible(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    adapter = load_adapter("pepmlm")
    attempt = tmp_path / "attempt_001"
    job = base_job(
        tmp_path,
        "PepMLM",
        task_id="T1_sequence_binder",
        length_min="3",
        length_max="3",
        expected_target_chain="not_applicable",
        expected_binder_chain="not_applicable",
    )
    adapter.prepare(job, base_execution("pd-benchmark-methods-gpu:0.21/bench-pepmlm"), attempt)
    spec = importlib.util.spec_from_file_location("pepmlm_sampling", attempt / "pepmlm_sampling.py")
    assert spec is not None and spec.loader is not None
    sampling = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sampling)
    logits = torch.zeros((32, 20))

    first = sampling.sample_top_k(logits, seed=42, top_k=20)
    repeated = sampling.sample_top_k(logits, seed=42, top_k=20)
    different = sampling.sample_top_k(logits, seed=43, top_k=20)

    assert torch.equal(first, repeated)
    assert not torch.equal(first, different)


@pytest.mark.parametrize(
    ("sequence", "expected_status"),
    [("ACD", "parsed"), ("WWX", "partial")],
)
def test_pepmlm_parse_reads_only_standard_csv_and_allows_x(
    tmp_path: Path, sequence: str, expected_status: str
) -> None:
    adapter = load_adapter("pepmlm")
    attempt = tmp_path / "attempt_001"
    raw = attempt / "raw"
    write_runtime(raw)
    job = base_job(tmp_path, "PepMLM", length_min="3", length_max="3")
    with (raw / "pepmlm_generated.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["job_id", "generated_binder", "binder_rank", "target_id"])
        writer.writeheader()
        writer.writerow(
            {
                "job_id": job["job_id"],
                "generated_binder": sequence,
                "binder_rank": "1",
                "target_id": job["target_id"],
            }
        )

    candidate, runtime = adapter.parse(job, attempt)

    assert candidate["sequence"] == sequence
    assert candidate["structure_path"] == ""
    assert candidate["source_output_path"] == str(raw / "pepmlm_generated.csv")
    assert candidate["binder_chain"] == "not_applicable"
    assert candidate["parse_status"] == expected_status
    assert_runtime_honored(runtime)


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [("job_id", "wrong_job"), ("target_id", "wrong_target"), ("binder_rank", "2")],
)
def test_pepmlm_parse_rejects_output_not_bound_to_job(
    tmp_path: Path, field: str, wrong_value: str
) -> None:
    adapter = load_adapter("pepmlm")
    attempt = tmp_path / "attempt_001"
    raw = attempt / "raw"
    write_runtime(raw)
    job = base_job(tmp_path, "PepMLM", length_min="3", length_max="3")
    row = {
        "job_id": job["job_id"],
        "generated_binder": "ACD",
        "binder_rank": "1",
        "target_id": job["target_id"],
    }
    row[field] = wrong_value
    with (raw / "pepmlm_generated.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)

    candidate, _ = adapter.parse(job, attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["status_reason"] == "pepmlm_output_contract_invalid"


def test_pepmlm_parse_fails_closed_and_ignores_stale_csv(tmp_path: Path) -> None:
    adapter = load_adapter("pepmlm")
    attempt = tmp_path / "attempt_001"
    write_runtime(attempt / "raw")
    (attempt / "old").mkdir()
    (attempt / "old" / "pepmlm_generated.csv").write_text(
        "generated_binder\nACD\n", encoding="utf-8"
    )

    candidate, runtime = adapter.parse(base_job(tmp_path, "PepMLM"), attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["sequence"] == ""
    assert candidate["source_output_path"] == ""
    assert "standard_output_missing" in candidate["status_reason"]
    assert_runtime_honored(runtime)


def test_diffpepbuilder_prepare_packages_v021_real_inference_contract(tmp_path: Path) -> None:
    adapter = load_adapter("diffpepbuilder")
    attempt = tmp_path / "attempt_001"
    job = base_job(
        tmp_path,
        "DiffPepBuilder",
        expected_target_chain="B",
        expected_binder_chain="A",
    )
    write_complex(
        Path(job["target_pdb_path"]),
        target_chain="A",
        binder_chain="B",
        binder_sequence="ACDEFGHIKLM",
    )
    job["target_pdb_sha256"] = hashlib.sha256(
        Path(job["target_pdb_path"]).read_bytes()
    ).hexdigest()

    text = assert_package(
        adapter.prepare(job, base_execution("pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder"), attempt),
        attempt,
    )

    assert adapter.METHOD == "DiffPepBuilder"
    assert adapter.SOURCE_COMMIT.startswith("c19eb4f")
    assert json.loads((attempt / "receptor_info.json").read_text(encoding="utf-8")) == {
        "3EQS": {"lig_chain": "B"}
    }
    for required in (
        "cp -a",
        "experiments/process_receptor.py",
        "diffpepbuilder_seeded_entry.py",
        "inference.seed=42",
        "inference.denoising.num_t=2",
        "inference.sampling.samples_per_length=1",
        "inference.sampling.min_length=11",
        "inference.sampling.max_length=11",
        "experiment.num_loader_workers=1",
        "diffpepbuilder_candidate.pdb",
        "diffpepbuilder_target_context.pdb",
        "runtime_evidence.json",
    ):
        assert required in text
    entry = (attempt / "diffpepbuilder_seeded_entry.py").read_text(encoding="utf-8")
    finalizer = (attempt / "diffpepbuilder_finalize.py").read_text(encoding="utf-8")
    assert "random.seed(SEED)" in entry
    assert "np.random.seed(SEED)" in entry
    assert "torch.manual_seed(SEED)" in entry
    assert 'runpy.run_module("experiments.run_inference", run_name="__main__")' in entry
    assert str(attempt / "raw/diffpepbuilder_target_context.pdb") in finalizer


@pytest.mark.parametrize(
    ("adapter_name", "method", "image"),
    [
        (
            "diffpepbuilder",
            "DiffPepBuilder",
            "pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder",
        ),
        ("pepglad", "PepGLAD", "pd-benchmark-methods-gpu:0.21/bench-pepglad"),
    ],
)
def test_structure_adapter_prepare_rejects_target_sha_mismatch(
    tmp_path: Path, adapter_name: str, method: str, image: str
) -> None:
    adapter = load_adapter(adapter_name)
    job = base_job(tmp_path, method)
    Path(job["target_pdb_path"]).write_text("HEADER    TAMPERED\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        adapter.prepare(job, base_execution(image), tmp_path / "attempt_001")


def test_diffpepbuilder_filters_chain_b_waters_before_receptor_processing(
    tmp_path: Path,
) -> None:
    adapter = load_adapter("diffpepbuilder")
    source = tmp_path / "3EQS.pdb"
    write_complex(source, target_chain="A", binder_chain="B", binder_sequence="ACDEFGHIKLM")
    source.write_text(
        source.read_text(encoding="utf-8").replace("END\n", "")
        + "HETATM 9999  O   HOH B  23      10.000  10.000  10.000  1.00 20.00           O\nEND\n",
        encoding="utf-8",
    )
    filtered = tmp_path / "filtered.pdb"

    adapter._write_polymer_receptor(source, filtered, {"A", "B"})

    text = filtered.read_text(encoding="utf-8")
    assert "HETATM" not in text
    assert "HOH" not in text
    assert adapter.parse_pdb_chain_sequences(filtered) == adapter.parse_pdb_chain_sequences(source)


def test_diffpepbuilder_parse_standard_pdb_chain_a(tmp_path: Path) -> None:
    adapter = load_adapter("diffpepbuilder")
    attempt = tmp_path / "attempt_001"
    raw = attempt / "raw"
    write_runtime(raw)
    sequence = "ACDEFGHIKLM"
    candidate_path = raw / "diffpepbuilder_candidate.pdb"
    write_complex(candidate_path, target_chain="B", binder_chain="A", binder_sequence=sequence)
    job = base_job(
        tmp_path,
        "DiffPepBuilder",
        expected_target_chain="B",
        expected_binder_chain="A",
    )

    candidate, runtime = adapter.parse(job, attempt)

    assert candidate == {
        "sequence": sequence,
        "structure_path": str(candidate_path),
        "source_output_path": str(candidate_path),
        "binder_chain": "A",
        "parse_status": "parsed",
        "status_reason": "diffpepbuilder_standard_output_parsed",
    }
    assert_runtime_honored(runtime)


def test_diffpepbuilder_parse_does_not_scan_stale_work_pdb(tmp_path: Path) -> None:
    adapter = load_adapter("diffpepbuilder")
    attempt = tmp_path / "attempt_001"
    write_runtime(attempt / "raw")
    write_complex(
        attempt / "work" / "runs" / "stale.pdb",
        target_chain="B",
        binder_chain="A",
        binder_sequence="ACDEFGHIKLM",
    )

    candidate, _ = adapter.parse(base_job(tmp_path, "DiffPepBuilder"), attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["structure_path"] == ""
    assert "standard_output_missing" in candidate["status_reason"]


def test_pepglad_prepare_packages_detect_pocket_seeded_codesign(tmp_path: Path) -> None:
    adapter = load_adapter("pepglad")
    attempt = tmp_path / "attempt_001"
    job = base_job(tmp_path, "PepGLAD")

    text = assert_package(
        adapter.prepare(job, base_execution("pd-benchmark-methods-gpu:0.21/bench-pepglad"), attempt),
        attempt,
    )
    entry = (attempt / "pepglad_seeded_entry.py").read_text(encoding="utf-8")

    assert adapter.METHOD == "PepGLAD"
    assert adapter.SOURCE_COMMIT.startswith("bad015c")
    for required in (
        "cp -a",
        "python -m api.detect_pocket",
        "--target_chains A",
        "--ligand_chains B",
        "--mode codesign",
        "--length_min 11",
        "--length_max 12",
        "--n_samples 1",
        "--seed 42",
        "3EQS_0.pdb",
        "pepglad_candidate.pdb",
        "pepglad_summary.jsonl",
        "runtime_evidence.json",
    ):
        assert required in text
    assert "random.seed(SEED)" in entry
    assert "np.random.seed(SEED)" in entry
    assert "torch.manual_seed(SEED)" in entry
    assert "runpy.run_module(\"api.run\", run_name=\"__main__\")" in entry


def test_pepglad_parse_requires_exact_pdb_and_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = load_adapter("pepglad")
    attempt = tmp_path / "attempt_001"
    raw = attempt / "raw"
    write_pepglad_legacy_runtime(raw, adapter)
    sequence = "ACDEFGHIKLM"
    candidate_path = raw / "pepglad_candidate.pdb"
    write_complex(candidate_path, target_chain="A", binder_chain="B", binder_sequence=sequence)
    monkeypatch.setattr(
        adapter,
        "SEED42_POST_RELAX_BASELINE_SHA256",
        hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    )
    (raw / "pepglad_summary.jsonl").write_text(
        json.dumps(
            {"id": "3EQS_0", "rec_chains": ["A"], "pep_chain": "B", "pep_seq": sequence}
        )
        + "\n",
        encoding="utf-8",
    )

    candidate, runtime = adapter.parse(base_job(tmp_path, "PepGLAD"), attempt)

    assert candidate == {
        "sequence": sequence,
        "structure_path": str(candidate_path),
        "source_output_path": str(candidate_path),
        "binder_chain": "B",
        "parse_status": "parsed",
        "status_reason": "pepglad_standard_output_parsed",
    }
    assert_runtime_honored(runtime)


def test_pepglad_parse_rejects_non_object_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = load_adapter("pepglad")
    attempt = tmp_path / "attempt_001"
    raw = attempt / "raw"
    write_pepglad_legacy_runtime(raw, adapter)
    candidate_path = raw / "pepglad_candidate.pdb"
    write_complex(
        candidate_path,
        target_chain="A",
        binder_chain="B",
        binder_sequence="ACDEFGHIKLM",
    )
    monkeypatch.setattr(
        adapter,
        "SEED42_POST_RELAX_BASELINE_SHA256",
        hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    )
    (raw / "pepglad_summary.jsonl").write_text("[]\n", encoding="utf-8")

    candidate, _ = adapter.parse(base_job(tmp_path, "PepGLAD"), attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["status_reason"] == "pepglad_standard_output_invalid"


@pytest.mark.parametrize("missing_name", ["pepglad_candidate.pdb", "pepglad_summary.jsonl"])
def test_pepglad_parse_fails_when_a_standard_output_is_missing(
    tmp_path: Path, missing_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = load_adapter("pepglad")
    attempt = tmp_path / "attempt_001"
    raw = attempt / "raw"
    write_pepglad_legacy_runtime(raw, adapter)
    candidate_path = raw / "pepglad_candidate.pdb"
    if missing_name != "pepglad_candidate.pdb":
        write_complex(
            candidate_path,
            target_chain="A",
            binder_chain="B",
            binder_sequence="ACDEFGHIKLM",
        )
        monkeypatch.setattr(
            adapter,
            "SEED42_POST_RELAX_BASELINE_SHA256",
            hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        )
    if missing_name != "pepglad_summary.jsonl":
        (raw / "pepglad_summary.jsonl").write_text(
            '{"id":"3EQS_0","rec_chains":["A"],"pep_chain":"B","pep_seq":"ACDEFGHIKLM"}\n',
            encoding="utf-8",
        )
    write_complex(
        attempt / "codesign" / "3EQS_0.pdb",
        target_chain="A",
        binder_chain="B",
        binder_sequence="ACDEFGHIKLM",
    )

    candidate, _ = adapter.parse(base_job(tmp_path, "PepGLAD"), attempt)

    assert candidate["parse_status"] == "failed"
    assert candidate["structure_path"] == ""
    assert "standard_output_missing" in candidate["status_reason"]
