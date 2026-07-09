from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_rows(relative_path: str) -> list[dict[str, str]]:
    with (ROOT / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_v022_jobs_keep_priority_blockers_closed() -> None:
    rows = read_rows("benchmark/input_sets/multi_case_fixture_job_manifest_v0.22.csv")
    by_method = {row["method"]: row for row in rows}

    assert by_method["D-Flow / PeptideDesign"]["status"] == "blocked_input_contract"
    assert by_method["D-Flow / PeptideDesign"]["contract_status"] == "blocked_missing_pepmerge_lmdb"
    assert "lmdb" in by_method["D-Flow / PeptideDesign"]["failure_policy"]

    colab = by_method["AfCycDesign / ColabDesign cyclic peptide"]
    assert colab["status"] == "blocked_cli_adapter"
    assert colab["contract_status"] == "blocked_cli_adapter"
    assert "standard_cli" in colab["failure_policy"]

    bindcraft = by_method["BindCraft"]
    assert bindcraft["status"] == "wrapper_review_only"
    assert bindcraft["contract_status"] == "wrapper_review_required"
    assert "low_confidence_only" in bindcraft["failure_policy"]


def test_v022_target_and_control_manifests_are_fixture_only() -> None:
    targets = read_rows("benchmark/input_sets/multi_case_fixture_target_manifest_v0.22.csv")
    controls = read_rows("benchmark/input_sets/multi_case_fixture_control_manifest_v0.22.csv")

    assert len(targets) == 5
    assert all("not_frozen" in row["target_status"] for row in targets)
    assert any(row["fixture_case_id"] == "mdm2_p53_3eqs_fixture" for row in targets)
    assert any(row["fixture_case_id"] == "gabarap_7zkr_fixture" for row in targets)

    bindcraft_controls = [row for row in controls if row["control_id"] == "bindcraft_low_confidence_output_control"]
    assert len(bindcraft_controls) == 1
    assert bindcraft_controls[0]["status"] == "wrapper_review_required"
    assert "not accepted final" in bindcraft_controls[0]["expected_use"]


def test_v022_evidence_rows_remain_method_example_adapter_smoke() -> None:
    evidence = read_rows("benchmark/deployment/method_example_fixture_evidence_v0.22.csv")

    assert len(evidence) == 10
    assert {row["evidence_type"] for row in evidence} == {"method_example_adapter_smoke"}
    pepmlm = next(row for row in evidence if row["method"] == "PepMLM")
    assert pepmlm["parse_status"] == "partial"
    assert pepmlm["parsed_sequence"] == "LTLX"
