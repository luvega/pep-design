from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_rows(relative_path: str) -> list[dict[str, str]]:
    with (ROOT / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_v023_notebook_cli_smoke_is_tooling_only() -> None:
    rows = read_rows("benchmark/deployment/notebook_cli_smoke_manifest_v0.23.csv")

    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "smoke_passed"
    assert "papermill" in row["installed_packages"]
    assert "not method output" in row["evidence_boundary"]


def test_v023_dflow_is_project_local_but_input_blocked() -> None:
    rows = read_rows("benchmark/deployment/dflow_project_install_contract_v0.23.csv")

    assert len(rows) == 1
    row = rows[0]
    assert row["source_mode"] == "project_internal_git_clone_not_symlink"
    assert row["is_symlink"] == "no"
    assert row["package_import_status"] == "dflow_import_ok_and_PepDataset_import_ok"
    assert row["model_import_status"] == "PepModel_import_ok"
    assert row["inference_import_status"] == "inference_pep_import_ok"
    assert row["input_contract_status"] == "blocked_input_contract"
    assert "PepMerge" in row["blocker"]


def test_v023_priority_gates_keep_claims_closed() -> None:
    gates = read_rows("benchmark/deployment/priority_gate_review_v0.23.csv")
    by_gate = {row["gate_id"]: row for row in gates}

    assert by_gate["v023_dflow_input_contract"]["allowed_v023_use"] == "blocked_contract_row_only"
    assert "Google Drive" in by_gate["v023_dflow_input_contract"]["remaining_blocker"]
    assert by_gate["v023_colabdesign_notebook_cli"]["allowed_v023_use"] == "cli_tooling_only"
    bindcraft_text = " ".join(by_gate["v023_bindcraft_wrapper_classifier"].values())
    for token in ["accepted_final", "low_confidence_only", "timeout_only", "no_output", "failed"]:
        assert token in bindcraft_text


def test_v023_alphafold_is_qc_only() -> None:
    rows = read_rows("benchmark/deployment/external_dry_run_package_manifest_v0.23.csv")
    alphafold = next(row for row in rows if row["package_item_id"] == "v023_alphafold_target_qc")

    assert alphafold["status"] == "pending_target_ids"
    assert alphafold["allowed_use"] == "target_qc_only_not_scoring"
