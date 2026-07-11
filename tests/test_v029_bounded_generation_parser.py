from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLAB_RUNNER_SCRIPT = ROOT / "scripts" / "run_colabdesign_bounded_generation.py"
DEX_FIXTURE_SCRIPT = ROOT / "scripts" / "prepare_dexdesign_minimal_fixture.py"
BINDCRAFT_PARSER_SCRIPT = ROOT / "scripts" / "parse_bindcraft_accepted_outputs.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_colabdesign_runner_builds_gpu_docker_command_and_parses_binder_chain(tmp_path: Path) -> None:
    module = load_module(COLAB_RUNNER_SCRIPT, "run_colabdesign_bounded_generation")
    output_dir = tmp_path / "colab"
    target_pdb = tmp_path / "target.pdb"
    target_pdb.write_text("HEADER TEST\n", encoding="utf-8")

    command = module.build_docker_command(
        output_dir=output_dir,
        source_dir=Path("/opt/source/ColabDesign"),
        params_dir=Path("/data/params"),
        target_pdb=target_pdb,
        image="pd-benchmark-methods-gpu:0.21",
        timeout_sec=30,
    )

    assert "--gpus" in command
    assert "all" in command
    assert "pd-benchmark-methods-gpu:0.21" in command
    assert f"{target_pdb.parent}:/data/inputs:ro" in command
    assert "/data/params:/data/alphafold_params:ro" in command
    assert f"{output_dir.resolve()}:/data/outputs" in command

    pdb = tmp_path / "binder.pdb"
    pdb.write_text(
        "\n".join(
            [
                "ATOM      1  CA  GLY A   1       0.000   0.000   0.000  1.00 10.00           C",
                "ATOM      2  CA  ALA B   1       1.000   0.000   0.000  1.00 10.00           C",
                "ATOM      3  CA  LEU B   2       2.000   0.000   0.000  1.00 10.00           C",
                "ATOM      4  CA  TYR B   3       3.000   0.000   0.000  1.00 10.00           C",
                "END",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    parsed = module.parse_pdb_sequence(pdb, preferred_chain="B")
    assert parsed == {"chain_id": "B", "sequence": "ALY"}


def test_colabdesign_runner_resolves_relative_output_mount() -> None:
    module = load_module(COLAB_RUNNER_SCRIPT, "run_colabdesign_bounded_generation")
    command = module.build_docker_command(
        output_dir=Path("benchmark_runs/v0.29/relative_colab"),
        source_dir=Path("/opt/source/ColabDesign"),
        params_dir=Path("/data/params"),
        target_pdb=Path("/tmp/target.pdb"),
        image="pd-benchmark-methods-gpu:0.21",
        timeout_sec=30,
    )

    assert f"{Path('benchmark_runs/v0.29/relative_colab').resolve()}:/data/outputs" in command
    assert "benchmark_runs/v0.29/relative_colab:/data/outputs" not in command


def test_colabdesign_runner_can_write_inner_command_without_overwriting_outer_wrapper(tmp_path: Path, monkeypatch) -> None:
    module = load_module(COLAB_RUNNER_SCRIPT, "run_colabdesign_bounded_generation")
    output_dir = tmp_path / "colab"
    target_pdb = tmp_path / "target.pdb"
    target_pdb.write_text("HEADER TEST\n", encoding="utf-8")

    def fake_run(command, **kwargs):
        _ = command, kwargs
        (output_dir / "colabdesign_binder.pdb").write_text(
            "\n".join(
                [
                    "ATOM      1  CA  ALA B   1       1.000   0.000   0.000  1.00 10.00           C",
                    "ATOM      2  CA  LEU B   2       2.000   0.000   0.000  1.00 10.00           C",
                    "END",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return module.subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.run_bounded_generation(
        output_dir=output_dir,
        source_dir=tmp_path / "source",
        params_dir=tmp_path / "params",
        target_pdb=target_pdb,
        image="pd-benchmark-methods-gpu:0.21",
        timeout_sec=30,
        inner_command_filename="colabdesign_inner_command.sh",
    )

    method_output_manifest = output_dir / "method_output_manifest.csv"
    candidate_outputs = output_dir / "candidate_outputs.csv"
    method_rows = read_csv(method_output_manifest)
    candidate_rows = read_csv(candidate_outputs)
    assert result["parser_status"] == "parsed"
    assert (output_dir / "colabdesign_inner_command.sh").is_file()
    assert not (output_dir / "command.sh").exists()
    assert method_rows[0]["command"].endswith("colabdesign_inner_command.sh")
    assert candidate_rows[0]["sequence"] == "AL"
    assert b"\r" not in method_output_manifest.read_bytes()
    assert b"\r" not in candidate_outputs.read_bytes()


def test_dexdesign_minimal_fixture_contains_contract_chains(tmp_path: Path) -> None:
    module = load_module(DEX_FIXTURE_SCRIPT, "prepare_dexdesign_minimal_fixture")

    result = module.prepare_minimal_d_l_fixture(output_dir=tmp_path / "dex")

    assert result["status"] == "dexdesign_input_contract_ready_fixture_created"
    fixture_path = Path(result["fixture_path"])
    assert fixture_path.is_file()
    text = fixture_path.read_text(encoding="utf-8")
    chains = {line[21] for line in text.splitlines() if line.startswith("ATOM")}
    assert chains == {"z", "y"}
    assert "first chain is L-target" in text
    assert "second chain is D-peptide" in text


def test_bindcraft_accepted_parser_emits_standard_candidate_rows(tmp_path: Path) -> None:
    module = load_module(BINDCRAFT_PARSER_SCRIPT, "parse_bindcraft_accepted_outputs")
    output_root = tmp_path / "CD47"
    accepted = output_root / "Accepted"
    accepted.mkdir(parents=True)
    (accepted / "CD47_peptide_l14_s1_mpnn1_model1.pdb").write_text(
        "ATOM      1  CA  ALA B   1       0.000   0.000   0.000  1.00 10.00           C\n",
        encoding="utf-8",
    )
    (accepted / "CD47_peptide_l12_s2_mpnn3_model1.pdb").write_text(
        "ATOM      1  CA  SER B   1       0.000   0.000   0.000  1.00 10.00           C\n",
        encoding="utf-8",
    )
    (output_root / "final_design_stats.csv").write_text(
        "\n".join(
            [
                "Rank,Design,Sequence",
                "1,CD47_peptide_l14_s1_mpnn1,APTGKELWRKRLAE",
                "2,CD47_peptide_l12_s2_mpnn3,SPKEEWRKRLAE",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_csv = tmp_path / "bindcraft_candidates.csv"

    result = module.parse_bindcraft_accepted_outputs(
        output_root=output_root,
        out_csv=out_csv,
        job_id="v029_bindcraft_cd47_accepted_external",
        target_id="bindcraft_cd47_external_v029",
    )

    assert result["status"] == "accepted_candidate_parser_passed"
    assert result["candidate_count"] == 2
    assert b"\r" not in out_csv.read_bytes()
    rows = read_csv(out_csv)
    assert [row["sequence"] for row in rows] == ["APTGKELWRKRLAE", "SPKEEWRKRLAE"]
    assert {row["method"] for row in rows} == {"BindCraft"}
    assert {row["parse_status"] for row in rows} == {"parsed"}
    assert all("not Benchmark result" in row["notes"] for row in rows)
