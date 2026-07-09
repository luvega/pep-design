from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_rows(relative_path: str) -> list[dict[str, str]]:
    with (ROOT / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_v025_dflow_full_pepmerge_download_records_load_ready_boundary() -> None:
    rows = read_rows("benchmark/deployment/dflow_full_pepmerge_download_v0.25.csv")

    assert len(rows) == 1
    row = rows[0]
    assert row["method"] == "D-Flow / PeptideDesign"
    assert row["download_status"] == "downloaded_verified"
    assert row["release_zip_integrity_status"] == "unzip_test_passed"
    assert row["lmdb_zip_integrity_status"] == "unzip_test_passed"
    assert row["required_file_missing_case_dirs"] == "0"
    assert row["test_names_missing_in_release"] == "0"
    assert row["pep_dataset_test_entries"] == "154"
    assert row["pep_dataset_train_entries"] == "9849"
    assert row["pep_dataset_load_status"] == "passed"
    assert row["status"] == "input_contract_ready_full_pepmerge"
    assert row["release_zip_path"].startswith("data/dflow/")
    assert row["lmdb_zip_path"].startswith("data/dflow/")
    assert "not Benchmark result" in row["evidence_boundary"]
    assert "not smoke_test_ready" in row["evidence_boundary"]
