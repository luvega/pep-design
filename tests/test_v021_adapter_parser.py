from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def write_runtime(method_dir: Path, method: str, status: str = "adapter_smoke_passed_gpu") -> None:
    method_dir.mkdir(parents=True, exist_ok=True)
    (method_dir / "runtime.json").write_text(
        json.dumps(
            {
                "method": method,
                "job_id": f"v021_{method}",
                "source_commit": "abc123",
                "image": "test-image:latest",
                "conda_env": "test-env",
                "smoke_command": str(method_dir / "command.sh"),
                "exit_code": 0 if status.endswith("passed_gpu") else "NA",
                "runtime_sec": 1.25,
                "smoke_status": status,
                "parser_status": "outputs_manifest_written",
                "blocker": "none" if status.endswith("passed_gpu") else "missing checkpoint",
                "next_gate": "adapter_parser_and_multi_case_fixture_needed",
            }
        ),
        encoding="utf-8",
    )
    (method_dir / "command.sh").write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")


def test_parse_pdb_sequence_uses_unique_residues(tmp_path: Path) -> None:
    from parse_v021_adapter_outputs import parse_pdb_sequence

    pdb = tmp_path / "candidate.pdb"
    pdb.write_text(
        "\n".join(
            [
                "ATOM      1  N   GLY A   1      11.104  13.207  14.099  1.00 20.00           N",
                "ATOM      2  CA  GLY A   1      12.104  13.207  14.099  1.00 20.00           C",
                "ATOM      3  N   DLE A   2      13.104  13.207  14.099  1.00 20.00           N",
                "ATOM      4  CA  DLE A   2      14.104  13.207  14.099  1.00 20.00           C",
                "ATOM      5  N   ALA B   1      15.104  13.207  14.099  1.00 20.00           N",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert parse_pdb_sequence(pdb, chain_id="A") == "GX"


def test_build_rows_parses_diffpepbuilder_and_rfdiffusion_handoff(tmp_path: Path) -> None:
    from parse_v021_adapter_outputs import build_rows

    external = tmp_path / "benchmark_v0.21" / "adapter_smokes"

    diff = external / "diffpepbuilder"
    write_runtime(diff, "DiffPepBuilder")
    pdb = diff / "workdir" / "runs" / "inference" / "sample" / "alk1_length_8_sample_0.pdb"
    pdb.parent.mkdir(parents=True)
    pdb.write_text(
        "ATOM      1  N   GLY A   1      11.104  13.207  14.099  1.00 20.00           N\n"
        "ATOM      2  N   ALA A   2      12.104  13.207  14.099  1.00 20.00           N\n",
        encoding="utf-8",
    )

    handoff = external / "rfdiffusion_proteinmpnn"
    write_runtime(handoff, "RFdiffusion + ProteinMPNN")
    (handoff / "handoff_manifest.csv").write_text(
        "job_id,rf_pdb,rf_trb,mpnn_input_pdb,mpnn_fasta,chain_policy,status,reason\n"
        "rfmpnn_fixture,rf/output/uncond_cycpep_0.pdb,rf/output/uncond_cycpep_0.trb,"
        "mpnn/input/uncond_cycpep_0.pdb,mpnn/output/uncond_cycpep_0.fa,all_chains,parsed,ok\n",
        encoding="utf-8",
    )
    fasta = handoff / "mpnn" / "output" / "uncond_cycpep_0.fa"
    fasta.parent.mkdir(parents=True)
    fasta.write_text(">rfmpnn_b0_d0, score=0.1\nGGGG\n", encoding="utf-8")

    method_rows, candidate_rows, run_rows = build_rows(external)

    assert {row["method"] for row in method_rows} == {"DiffPepBuilder", "RFdiffusion + ProteinMPNN"}
    parsed = {row["method"]: row for row in candidate_rows}
    assert parsed["DiffPepBuilder"]["sequence"] == "GA"
    assert parsed["DiffPepBuilder"]["parse_status"] == "parsed"
    assert parsed["RFdiffusion + ProteinMPNN"]["sequence"] == "GGGG"
    assert parsed["RFdiffusion + ProteinMPNN"]["source_output_id"] == "mpnn/output/uncond_cycpep_0.fa:record0"
    assert {row["status"] for row in run_rows} == {"not_real_benchmark"}


def test_build_rows_records_blocked_method_without_candidate(tmp_path: Path) -> None:
    from parse_v021_adapter_outputs import build_rows

    external = tmp_path / "benchmark_v0.21" / "adapter_smokes"
    pepmirror = external / "pepmirror"
    write_runtime(pepmirror, "PepMirror", status="blocked_weights")

    method_rows, candidate_rows, run_rows = build_rows(external)

    assert len(method_rows) == 1
    assert method_rows[0]["parser_status"] == "not_applicable"
    assert method_rows[0]["status_reason"] == "blocked_weights: missing checkpoint"
    assert candidate_rows == []
    assert run_rows == []


def test_build_rows_uses_method_specific_binder_chains(tmp_path: Path) -> None:
    from parse_v021_adapter_outputs import build_rows

    external = tmp_path / "benchmark_v0.21" / "adapter_smokes"

    pepglad = external / "pepglad"
    write_runtime(pepglad, "PepGLAD")
    pepglad_pdb = pepglad / "codesign" / "sample.pdb"
    pepglad_pdb.parent.mkdir(parents=True)
    pepglad_pdb.write_text(
        "ATOM      1  N   GLY A   1      11.104  13.207  14.099  1.00 20.00           N\n"
        "ATOM      2  N   GLY A   2      12.104  13.207  14.099  1.00 20.00           N\n"
        "ATOM      3  N   ALA B   1      13.104  13.207  14.099  1.00 20.00           N\n"
        "ATOM      4  N   SER B   2      14.104  13.207  14.099  1.00 20.00           N\n",
        encoding="utf-8",
    )

    pepmirror = external / "pepmirror"
    write_runtime(pepmirror, "PepMirror")
    pepmirror_pdb = pepmirror / "generated" / "LinearPeptide" / "candidates" / "demo" / "0.pdb"
    pepmirror_pdb.parent.mkdir(parents=True)
    pepmirror_pdb.write_text(
        "ATOM      1  N   GLY A   1      11.104  13.207  14.099  1.00 20.00           N\n"
        "ATOM      2  N   GLY A   2      12.104  13.207  14.099  1.00 20.00           N\n"
        "ATOM      3  N   TYR H   1      13.104  13.207  14.099  1.00 20.00           N\n"
        "ATOM      4  N   TRP H   2      14.104  13.207  14.099  1.00 20.00           N\n",
        encoding="utf-8",
    )

    _, candidate_rows, run_rows = build_rows(external)

    parsed = {row["method"]: row for row in candidate_rows}
    runs = {row["method"]: row for row in run_rows}
    assert parsed["PepGLAD"]["sequence"] == "AS"
    assert parsed["PepMirror"]["sequence"] == "YW"
    assert parsed["PepMirror"]["cyclic"] == "no"
    assert runs["PepGLAD"]["binder_chain"] == "B"
    assert runs["PepMirror"]["binder_chain"] == "H"
