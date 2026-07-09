from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_v030_pilot_targets_define_computational_fixtures_without_freezing_target_set() -> None:
    rows = read_csv(ROOT / "benchmark/input_sets/pilot_benchmark_target_manifest_v0.30.csv")
    target_set_rows = read_csv(ROOT / "benchmark/input_sets/target_set_v0.csv")
    by_id = {row["pilot_target_id"]: row for row in rows}

    assert target_set_rows == []
    assert set(by_id) == {
        "pepmlm_sequence_contract_fixture",
        "mdm2_p53_3eqs_fixture",
        "gabarap_7zkr_fixture",
        "mhcii_hiv_1sjh_fixture",
        "pdl1_workbench_fixture",
        "dexdesign_synthetic_d_l_fixture",
        "bindcraft_cd47_method_example_control",
    }
    assert by_id["mdm2_p53_3eqs_fixture"]["benchmark_lane"] == "wave_a_structure_generation"
    assert by_id["gabarap_7zkr_fixture"]["benchmark_lane"] == "wave_a_topology_parser"
    assert by_id["mhcii_hiv_1sjh_fixture"]["benchmark_lane"] == "review_only"
    assert by_id["pdl1_workbench_fixture"]["benchmark_lane"] == "reserve_only"
    for row in rows:
        assert row["target_status"] != "frozen_target_set"
        assert "not Benchmark result" in row["evidence_boundary"]
        assert "benchmark_ready" not in " ".join(row.values()).lower()


def test_v030_jobs_and_execution_matrix_match_wave_lanes() -> None:
    jobs = read_csv(ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv")
    matrix = read_csv(ROOT / "benchmark/deployment/pilot_execution_matrix_v0.30.csv")

    wave_a_jobs = [row for row in jobs if row["execution_wave"] == "wave_a"]
    wave_b_jobs = [row for row in jobs if row["execution_wave"] == "wave_b"]
    blocked_jobs = [row for row in jobs if row["execution_wave"] == "blocked"]

    assert len(wave_a_jobs) == 14
    assert len(wave_b_jobs) == 2
    assert len(blocked_jobs) == 1
    assert {row["random_seed"] for row in wave_a_jobs} == {"42", "43"}
    assert {row["method"] for row in wave_a_jobs} == {
        "PepMLM",
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "PepMirror",
        "RFdiffusion + ProteinMPNN",
        "AfCycDesign / ColabDesign cyclic peptide",
    }
    assert blocked_jobs[0]["method"] == "SaLT&PepPr"
    assert blocked_jobs[0]["status"] == "blocked_license"

    matrix_by_job = {row["job_id"]: row for row in matrix}
    assert {row["job_id"] for row in jobs} == set(matrix_by_job)
    assert matrix_by_job["v030_saltnpeppr_blocked_access"]["status"] == "blocked_license"
    for row in matrix:
        assert row["output_root"].startswith("benchmark_runs/v0.31/") or row["output_root"] == "not_applicable"
        assert "not Benchmark result" in row["evidence_boundary"]


def test_v030_wet_lab_panel_is_prospective_only() -> None:
    rows = read_csv(ROOT / "benchmark/input_sets/wet_lab_candidate_panel_v0.30.csv")
    by_id = {row["wet_lab_candidate_id"]: row for row in rows}

    assert set(by_id) == {
        "wetlab_mdm2_p53",
        "wetlab_gabarap_stapled",
        "wetlab_ncam1_sequence",
        "wetlab_amhr2_sequence",
    }
    assert by_id["wetlab_mdm2_p53"]["recommended_assay"] == "SPR_or_BLI_or_fluorescence_polarization"
    assert by_id["wetlab_gabarap_stapled"]["validation_tier"] == "higher_complexity_follow_up"
    for row in rows:
        text = " ".join(row.values()).lower()
        assert row["status"] == "prospective_not_run"
        assert "not wet-lab validated" in row["evidence_boundary"]
        assert "wet_lab_validated" not in text
        assert "not benchmark result" in text
