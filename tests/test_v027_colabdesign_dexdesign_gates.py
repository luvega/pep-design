from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLAB_SCRIPT = ROOT / "scripts" / "prepare_colabdesign_cli_adapter.py"
DEXDESIGN_SCRIPT = ROOT / "scripts" / "audit_dexdesign_route.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_colab_config(path: Path, target_pdb: Path, source_dir: Path) -> None:
    payload = {
        "job_id": "v027_colabdesign_missing_assets",
        "method": "AfCycDesign / ColabDesign cyclic peptide",
        "task_id": "T2_structure_peptide_binder",
        "target_id": "gabarap_7zkr_fixture",
        "target_pdb": str(target_pdb),
        "target_chains": ["A"],
        "binder_chain": "A",
        "peptide_type": "cyclic",
        "chirality": "L",
        "cyclic": True,
        "n_designs_requested": 1,
        "random_seed": 42,
        "source_dir": str(source_dir),
        "dry_run": False,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_colabdesign_execute_gate_fails_closed_when_af_params_missing(tmp_path: Path) -> None:
    module = load_module(COLAB_SCRIPT, "prepare_colabdesign_cli_adapter")
    source_dir = tmp_path / "ColabDesign"
    (source_dir / "colabdesign" / "af").mkdir(parents=True)
    (source_dir / "colabdesign" / "__init__.py").write_text("", encoding="utf-8")
    (source_dir / "colabdesign" / "af" / "__init__.py").write_text("", encoding="utf-8")
    target_pdb = tmp_path / "target.pdb"
    target_pdb.write_text("HEADER TEST\n", encoding="utf-8")
    config_path = tmp_path / "colabdesign_adapter_config.json"
    output_dir = tmp_path / "colab_execute"
    write_colab_config(config_path, target_pdb, source_dir)

    result = module.execute_adapter_package(
        adapter_config=config_path,
        output_dir=output_dir,
        params_dir=tmp_path / "missing_af_params",
        timeout_sec=1,
    )

    assert result["status"] == "blocked_af_params_missing"
    method_rows = read_csv(output_dir / "method_output_manifest.csv")
    candidate_rows = read_csv(output_dir / "candidate_outputs.csv")
    assert method_rows[0]["execution_stage"] == "dry_run"
    assert method_rows[0]["exit_code"] == "not_run"
    assert method_rows[0]["parser_status"] == "failed"
    assert "not Benchmark result" in method_rows[0]["status_reason"]
    assert candidate_rows[0]["parse_status"] == "failed"
    assert candidate_rows[0]["source_output_id"] == "not_generated"


def test_dexdesign_audit_requires_d_peptide_route_and_rejects_generic_osprey(tmp_path: Path) -> None:
    module = load_module(DEXDESIGN_SCRIPT, "audit_dexdesign_route")
    source_dir = tmp_path / "OSPREY3"
    generic = source_dir / "examples" / "1FSV"
    dex = source_dir / "examples" / "ccs.D-peptide-L-protein"
    generic.mkdir(parents=True)
    dex.mkdir(parents=True)
    (source_dir / "gradlew").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (generic / "KStar.cfg").write_text("runName 1FSV\n", encoding="utf-8")
    (dex / "DL.py").write_text("# D-peptide route\n", encoding="utf-8")
    (dex / "DL_preprocess.py").write_text("# preprocess\n", encoding="utf-8")
    (dex / "ccsKstar.py").write_text("# kstar\n", encoding="utf-8")
    (dex / "Confspace_Combiner.py").write_text("# combine\n", encoding="utf-8")

    row = module.audit_dexdesign_route(
        source_dir=source_dir,
        output_dir=tmp_path / "dex_audit",
        input_pdb=tmp_path / "missing_d_l_complex.pdb",
    )

    assert row["method"] == "DexDesign / OSPREY3"
    assert row["generic_osprey_example_status"] == "env_probe_only_not_dexdesign"
    assert row["status"] == "blocked_dexdesign_input_contract"
    assert row["candidate_output_allowed"] == "no"
    assert "not Benchmark result" in row["evidence_boundary"]


def test_v027_gate_manifest_keeps_colabdesign_and_dexdesign_boundaries() -> None:
    rows = read_csv(ROOT / "benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv")
    by_id = {row["item_id"]: row for row in rows}

    assert set(by_id) == {"v027_colabdesign_bounded_execute_gate", "v027_dexdesign_route_audit"}
    assert by_id["v027_colabdesign_bounded_execute_gate"]["method"] == "AfCycDesign / ColabDesign cyclic peptide"
    assert by_id["v027_colabdesign_bounded_execute_gate"]["status"] in {
        "blocked_af_params_missing",
        "bounded_gpu_generation_passed",
    }
    assert by_id["v027_dexdesign_route_audit"]["method"] == "DexDesign / OSPREY3"
    assert by_id["v027_dexdesign_route_audit"]["generic_osprey_example_status"] == "env_probe_only_not_dexdesign"
    for row in rows:
        assert "not Benchmark result" in row["evidence_boundary"]
        assert "performance_ranking" not in " ".join(row.values()).lower()
