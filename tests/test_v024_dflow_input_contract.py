from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_dflow_input_contract.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("prepare_dflow_input_contract", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_rows(relative_path: str) -> list[dict[str, str]]:
    with (ROOT / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_chain_ids_from_manifest_field_accepts_common_separators() -> None:
    module = load_script_module()

    chain_ids_from_field = module.chain_ids_from_field
    assert chain_ids_from_field("A") == ["A"]
    assert chain_ids_from_field("A;B") == ["A", "B"]
    assert chain_ids_from_field("A,B with D confounder") == ["A", "B"]


def test_v024_dflow_contract_records_fixture_lmdb_ready_without_benchmark_claim() -> None:
    rows = read_rows("benchmark/deployment/dflow_input_contract_fixture_v0.24.csv")

    assert len(rows) == 1
    row = rows[0]
    assert row["method"] == "D-Flow / PeptideDesign"
    assert row["status"] == "input_contract_ready_fixture"
    assert row["pep_dataset_reset_false_status"] == "passed"
    assert row["lmdb_entries"] == "1"
    assert "pep_pocket_test_structure_cache.lmdb" in row["lmdb_path"]
    assert "not Benchmark result" in row["evidence_boundary"]
