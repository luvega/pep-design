from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts import validate_benchmark_kb


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAP = (
    ROOT
    / "benchmark/method_sources/method_homepage_source_map_v0.35.csv"
)
EXPECTED_METHODS = {
    "PepMLM",
    "SaLT&PepPr",
    "DiffPepBuilder",
    "PepGLAD",
    "D-Flow / PeptideDesign",
    "PepMirror",
    "AfCycDesign / ColabDesign cyclic peptide",
    "DexDesign / OSPREY3",
    "RFdiffusion + ProteinMPNN",
    "BindCraft",
}
EXPECTED_HEADERS = [
    "method",
    "task_id",
    "method_family",
    "input_contract",
    "output_contract",
    "repo_url",
    "pinned_commit",
    "publication_title",
    "publication_url",
    "persistent_id",
    "publication_status",
    "verified_on",
    "evidence_boundary",
]
README = ROOT / "README.md"
README_REQUIRED_SECTIONS = [
    "## 项目定位",
    "## 当前证据状态",
    "## 方法分类与来源",
    "## 标准输入与输出",
    "## 代表性测试数据",
    "## 评价标准",
    "## 复核与复现边界",
]


def write_source_rows(
    root: Path, rows: list[dict[str, str]]
) -> Path:
    relative = Path(
        "benchmark/method_sources/method_homepage_source_map_v0.35.csv"
    )
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return target


def read_source_rows() -> list[dict[str, str]]:
    with SOURCE_MAP.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_readme_homepage_exposes_sources_interfaces_and_claim_boundaries() -> None:
    text = README.read_text(encoding="utf-8")

    assert all(section in text for section in README_REQUIRED_SECTIONS)
    assert "docs/assets/readme/pep_design_icon_v1.png" in text
    assert "docs/assets/readme/pep_design_homepage_workflow_v1.png" in text
    assert (
        "benchmark/method_sources/method_homepage_source_map_v0.35.csv"
        in text
    )
    assert all(method in text for method in EXPECTED_METHODS)
    assert "source_and_interface_navigation_only_not_runnability_or_performance" in text
    assert "current.v035_bounded_connectivity" in text
    assert "基础设施失败，不是 PepGLAD 方法失败" in text
    assert "尚未开展统一评分或方法排名" in text


def test_homepage_method_source_map_is_complete_and_navigation_only() -> None:
    assert SOURCE_MAP.is_file()
    with SOURCE_MAP.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert list(reader.fieldnames or []) == EXPECTED_HEADERS
    assert (
        "benchmark/method_sources/method_homepage_source_map_v0.35.csv"
        in validate_benchmark_kb.REQUIRED_FILES
    )
    assert {row["method"] for row in rows} == EXPECTED_METHODS
    assert len(rows) == len(EXPECTED_METHODS)
    assert all(row["task_id"] in validate_benchmark_kb.REQUIRED_PROTOCOL_TASKS for row in rows)
    assert all(row["repo_url"].startswith("https://github.com/") for row in rows)
    assert all(row["pinned_commit"] for row in rows)
    assert all(row["publication_url"].startswith("https://") for row in rows)
    assert all(row["verified_on"] == "2026-07-25" for row in rows)
    assert all(
        row["evidence_boundary"]
        == "source_and_interface_navigation_only_not_runnability_or_performance"
        for row in rows
    )


def test_homepage_source_validator_rejects_missing_included_method(
    tmp_path: Path, monkeypatch
) -> None:
    check = getattr(
        validate_benchmark_kb, "check_homepage_method_sources", None
    )
    assert callable(check)
    rows = [row for row in read_source_rows() if row["method"] != "PepMLM"]
    write_source_rows(tmp_path, rows)

    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    checked = check(errors)

    assert checked == len(EXPECTED_METHODS) - 1
    assert errors == [
        "method_homepage_source_map_v0.35.csv missing included methods: PepMLM"
    ]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        (
            "task_id",
            "T4_unknown",
            "PepMLM: homepage source map has invalid task_id T4_unknown",
        ),
        (
            "repo_url",
            "https://example.com/pepmlm",
            "PepMLM: homepage source map repo_url must use GitHub HTTPS routes",
        ),
        (
            "pinned_commit",
            "",
            "PepMLM: homepage source map missing pinned_commit",
        ),
        (
            "publication_url",
            "http://example.com/paper",
            "PepMLM: homepage source map publication_url must use HTTPS",
        ),
        (
            "verified_on",
            "2026/07/25",
            "PepMLM: homepage source map verified_on must be YYYY-MM-DD",
        ),
        (
            "evidence_boundary",
            "benchmark_performance",
            "PepMLM: homepage source map has invalid evidence_boundary",
        ),
    ],
)
def test_homepage_source_validator_rejects_invalid_fields(
    field: str,
    value: str,
    expected: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    check = getattr(
        validate_benchmark_kb, "check_homepage_method_sources", None
    )
    assert callable(check)
    rows = read_source_rows()
    rows[0][field] = value
    write_source_rows(tmp_path, rows)
    monkeypatch.setattr(validate_benchmark_kb, "ROOT", tmp_path)
    errors: list[str] = []

    checked = check(errors)

    assert checked == len(EXPECTED_METHODS)
    assert expected in errors
