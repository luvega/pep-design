from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLAB_SCRIPT = ROOT / "scripts" / "prepare_colabdesign_cli_adapter.py"
BINDCRAFT_SCRIPT = ROOT / "scripts" / "classify_bindcraft_outputs.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_job_manifest(path: Path, target_pdb: Path) -> None:
    headers = [
        "job_id",
        "method",
        "task_id",
        "target_id",
        "input_mode",
        "target_sequence",
        "target_pdb",
        "target_chains",
        "binder_chain",
        "pocket_definition",
        "peptide_type",
        "chirality",
        "cyclic",
        "n_designs_requested",
        "random_seed",
        "adapter_config",
        "status",
        "notes",
    ]
    row = {
        "job_id": "test_colabdesign_7zkr_seed42",
        "method": "AfCycDesign / ColabDesign cyclic peptide",
        "task_id": "T2_structure_peptide_binder",
        "target_id": "gabarap_7zkr_fixture",
        "input_mode": "pdb_cli",
        "target_sequence": "",
        "target_pdb": str(target_pdb),
        "target_chains": "A",
        "binder_chain": "A",
        "pocket_definition": "cyclic_offset_binder_or_fixbb_policy",
        "peptide_type": "cyclic",
        "chirality": "L",
        "cyclic": "yes",
        "n_designs_requested": "1",
        "random_seed": "42",
        "adapter_config": "test_colabdesign_cli_adapter",
        "status": "planned_fixture_only",
        "notes": "test row",
    }
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow(row)


def test_colabdesign_cli_adapter_packages_standard_job_row(tmp_path: Path) -> None:
    module = load_module(COLAB_SCRIPT, "prepare_colabdesign_cli_adapter")
    target_pdb = tmp_path / "target.pdb"
    target_pdb.write_text("HEADER TEST\n", encoding="utf-8")
    manifest = tmp_path / "jobs.csv"
    output_dir = tmp_path / "adapter"
    write_job_manifest(manifest, target_pdb)

    result = module.prepare_adapter_package(
        job_manifest=manifest,
        job_id="test_colabdesign_7zkr_seed42",
        output_dir=output_dir,
        source_dir=Path("/opt/pep_design_benchmark/ColabDesign"),
        dry_run=True,
    )

    assert result["status"] == "cli_adapter_defined"
    config = json.loads((output_dir / "colabdesign_adapter_config.json").read_text(encoding="utf-8"))
    assert config["job_id"] == "test_colabdesign_7zkr_seed42"
    assert config["method"] == "AfCycDesign / ColabDesign cyclic peptide"
    assert config["cyclic"] is True
    assert config["target_chains"] == ["A"]
    assert config["n_designs_requested"] == 1

    method_rows = read_csv(output_dir / "method_output_manifest.csv")
    candidate_rows = read_csv(output_dir / "candidate_outputs.csv")
    assert method_rows[0]["parser_status"] == "not_run"
    assert method_rows[0]["execution_stage"] == "dry_run_plan"
    assert "not Benchmark result" in method_rows[0]["status_reason"]
    assert candidate_rows[0]["parse_status"] == "not_applicable"
    assert candidate_rows[0]["source_output_id"] == "not_generated"
    assert (output_dir / "command.sh").is_file()


def test_bindcraft_classifier_distinguishes_output_classes(tmp_path: Path) -> None:
    module = load_module(BINDCRAFT_SCRIPT, "classify_bindcraft_outputs")

    accepted = tmp_path / "accepted"
    (accepted / "designs" / "Accepted" / "Ranked").mkdir(parents=True)
    (accepted / "designs" / "Accepted" / "Ranked" / "rank_1.pdb").write_text("ATOM\n", encoding="utf-8")
    assert module.classify_bindcraft_output(accepted)["classification"] == "accepted_final"

    low_conf = tmp_path / "low_conf"
    (low_conf / "designs" / "Trajectory" / "LowConfidence").mkdir(parents=True)
    (low_conf / "designs" / "Trajectory" / "LowConfidence" / "low.pdb").write_text("ATOM\n", encoding="utf-8")
    assert module.classify_bindcraft_output(low_conf)["classification"] == "low_confidence_only"

    timeout = tmp_path / "timeout"
    timeout.mkdir()
    (timeout / "runtime.json").write_text(json.dumps({"exit_code": 124}), encoding="utf-8")
    assert module.classify_bindcraft_output(timeout)["classification"] == "timeout_only"

    no_output = tmp_path / "no_output"
    no_output.mkdir()
    assert module.classify_bindcraft_output(no_output)["classification"] == "no_output"

    failed = tmp_path / "failed"
    failed.mkdir()
    (failed / "runtime.json").write_text(json.dumps({"exit_code": 1}), encoding="utf-8")
    assert module.classify_bindcraft_output(failed)["classification"] == "failed"


def test_v026_gate_manifest_records_three_gate_updates_without_benchmark_claim() -> None:
    rows = read_csv(ROOT / "benchmark/deployment/dflow_colabdesign_bindcraft_v0.26.csv")

    assert {row["item_id"] for row in rows} == {
        "v026_dflow_bounded_dry_run",
        "v026_colabdesign_cli_adapter",
        "v026_bindcraft_wrapper_classifier",
    }
    by_id = {row["item_id"]: row for row in rows}
    assert by_id["v026_dflow_bounded_dry_run"]["status"] == "bounded_dry_run_passed"
    assert by_id["v026_dflow_bounded_dry_run"]["exit_code"] == "0"
    assert by_id["v026_colabdesign_cli_adapter"]["status"] == "cli_adapter_defined"
    assert by_id["v026_colabdesign_cli_adapter"]["execution_status"] == "dry_run_package_only"
    assert by_id["v026_bindcraft_wrapper_classifier"]["parser_or_classifier_status"] == "low_confidence_only"
    for row in rows:
        assert "not Benchmark result" in row["evidence_boundary"]


def test_v026_dflow_and_bindcraft_result_rows_keep_parser_boundaries() -> None:
    dflow_rows = read_csv(ROOT / "benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv")
    bindcraft_rows = read_csv(ROOT / "benchmark/results/bindcraft_wrapper_classification_v0.26.csv")

    assert len(dflow_rows) == 1
    assert dflow_rows[0]["method"] == "D-Flow / PeptideDesign"
    assert dflow_rows[0]["sequence"] == "MRRRRRRRRY"
    assert dflow_rows[0]["parse_status"] == "parsed"
    assert "not target-set evidence" in dflow_rows[0]["notes"]
    assert len(bindcraft_rows) == 1
    assert bindcraft_rows[0]["classification"] == "low_confidence_only"
    assert bindcraft_rows[0]["accepted_pdb_count"] == "0"
