#!/usr/bin/env python
"""Validate the peptide-design benchmark knowledge base artifacts."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MASTER_HEADERS = [
    "source_id",
    "zotero_key",
    "bibtex_key",
    "doi",
    "pmid",
    "arxiv_id",
    "title",
    "year",
    "venue",
    "method_family",
    "design_modality",
    "input_requirement",
    "output_type",
    "availability_status",
    "code_url",
    "weights_url",
    "pdf_status",
    "screening_status",
    "exclusion_reason",
]

EVIDENCE_HEADERS = [
    "method",
    "paper_key",
    "task",
    "target_type",
    "peptide_type",
    "input",
    "output",
    "reported_metrics",
    "datasets",
    "claimed_strengths",
    "limitations",
    "reproducibility_notes",
]

SCORE_HEADERS = [
    "method",
    "primary_paper",
    "code_status",
    "weights_status",
    "license",
    "inputs_standardizable",
    "outputs_evaluable",
    "gpu_cost",
    "peptide_fit",
    "recency_evidence",
    "total_score",
    "decision",
]

RUNNABILITY_HEADERS = [
    "method",
    "task_id",
    "tier",
    "scientific_priority",
    "engineering_readiness",
    "repo_url",
    "license_status",
    "weights_route",
    "install_route",
    "batch_inference",
    "expected_inputs",
    "expected_outputs",
    "scoring_compatible",
    "hardware_notes",
    "blocking_risks",
    "next_action",
]

MANUSCRIPT_CLAIM_HEADERS = [
    "claim",
    "evidence",
    "status",
    "allowed_wording",
    "forbidden_wording",
    "next_check",
]

BENCHMARK_LITERATURE_HEADERS = [
    "zotero_key",
    "bibtex_key",
    "title",
    "year",
    "benchmark_lesson",
    "limitation",
    "planned_use",
]

TARGET_SET_HEADERS = [
    "target_id",
    "task_id",
    "target_class",
    "pdb_id",
    "chain_ids",
    "apo_or_holo",
    "known_binder",
    "negative_controls",
    "experimental_affinity",
    "assay_type",
    "sequence_identity_cluster",
    "train_leakage_risk",
    "license",
    "notes",
]

DATASET_CANDIDATE_HEADERS = [
    "dataset_id",
    "source_name",
    "source_type",
    "citation_key",
    "doi",
    "url",
    "access_route",
    "version",
    "record_count",
    "data_volume",
    "task_fit",
    "target_class",
    "benchmark_track",
    "has_structure",
    "has_affinity",
    "has_controls",
    "license_status",
    "leakage_risk",
    "download_policy",
    "recommended_use",
    "next_action",
]

METHOD_SOURCE_HEADERS = [
    "method",
    "repo_url",
    "repo_host",
    "default_branch",
    "latest_release_or_tag",
    "commit_to_pin",
    "license_status",
    "code_access_status",
    "weights_route",
    "large_artifact_policy",
    "clone_recommended",
    "next_action",
]

ENVIRONMENT_HEADERS = [
    "method",
    "task_id",
    "environment_type",
    "python_version",
    "cuda_needed",
    "gpu_needed",
    "estimated_gpu_memory",
    "conda_or_pip",
    "critical_dependencies",
    "license_blockers",
    "external_tools",
    "install_risk",
    "smoke_test_priority",
    "next_action",
]

EXPERT_REVIEW_HEADERS = [
    "reviewer_role",
    "severity",
    "artifact",
    "issue",
    "recommendation",
    "decision",
    "status",
    "evidence",
    "next_action",
]

DATASET_READINESS_HEADERS = [
    "dataset_id",
    "license_readiness",
    "schema_readiness",
    "assay_readout_readiness",
    "controls_readiness",
    "leakage_risk",
    "task_fit",
    "decision",
    "evidence",
    "next_action",
]

TARGET_CANDIDATE_HEADERS = [
    "candidate_id",
    "dataset_id",
    "target_id",
    "task_id",
    "target_class",
    "record_count",
    "positive_control_status",
    "negative_decoy_status",
    "assay_evidence_status",
    "license_status",
    "leakage_initial",
    "decision",
    "evidence",
    "next_action",
]

SOURCE_PIN_HEADERS = [
    "method",
    "repo_name",
    "repo_url",
    "external_audit_path",
    "default_branch",
    "commit_sha",
    "license_file",
    "readme_entrypoint",
    "environment_file",
    "batch_route",
    "weights_policy",
    "audit_status",
    "next_action",
]

REQUIRED_FILES = [
    "AGENTS.md",
    "index.md",
    "log.md",
    "benchmarks/README.md",
    "benchmarks/protocols/benchmark_protocol_v0.md",
    "benchmarks/protocols/run_csv_schema.md",
    "benchmarks/protocols/scoring_outputs_schema.md",
    "benchmarks/scoring/scoring_protocol_v0.md",
    "benchmarks/smoke_tests/README.md",
    "benchmarks/input_sets/README.md",
    "benchmarks/input_sets/candidate_benchmark_datasets.csv",
    "benchmarks/input_sets/dataset_readiness_scorecard.csv",
    "benchmarks/input_sets/target_candidate_matrix_v0.4.csv",
    "benchmarks/input_sets/target_set_v0.csv",
    "benchmarks/input_sets/target_set_v0_schema.md",
    "benchmarks/input_sets/negative_design_panel_schema.md",
    "benchmarks/method_sources/README.md",
    "benchmarks/method_sources/method_source_manifest.csv",
    "benchmarks/method_sources/source_pin_audit_v0.4.csv",
    "benchmarks/environments/README.md",
    "benchmarks/environments/environment_feasibility_matrix.csv",
    "benchmarks/results/README.md",
    "raw_sources/_index.md",
    "references/references.bib",
    "references/zotero-map.tsv",
    "references/search_log.md",
    "references/dedupe_report.csv",
    "tables/master_literature_manifest.csv",
    "tables/method_evidence_matrix.csv",
    "tables/candidate_method_scorecard.csv",
    "tables/method_runnability_matrix.csv",
    "tables/benchmark_literature_lessons.csv",
    "tables/expert_review_action_items.csv",
    "reports/skill_selection.md",
    "reports/literature_scope_report.md",
    "reports/candidate_methods_shortlist.md",
    "reports/method_runnability_audit.md",
    "reports/dataset_candidate_audit.md",
    "reports/method_source_audit.md",
    "reports/environment_feasibility_audit.md",
    "reports/expert_panel_review_v0.4.md",
    "reports/benchmark_literature_lessons.md",
    "reports/benchmark_manuscript_outline.md",
    "reports/benchmark_manuscript_claim_evidence_map.csv",
    "reports/benchmark_manuscript_figure_table_plan.md",
    "wiki/literature/_index.md",
    "wiki/methods/_index.md",
    "wiki/concepts/_index.md",
    "wiki/benchmark_candidates/_index.md",
]

METHOD_REQUIRED_TOKENS = [
    "## 输入",
    "## 输出",
    "## 适用 peptide 类型",
    "## 依赖",
    "## 原始论文",
    "## 候选评分",
    "## 复现风险",
]

METHOD_SLUG_OVERRIDES = {
    "AfCycDesign / ColabDesign cyclic peptide": "afcycdesign-colabdesign",
}

REQUIRED_PROTOCOL_TASKS = [
    "T1_sequence_binder",
    "T2_structure_peptide_binder",
    "T3_miniprotein_binder_baseline",
]

REQUIRED_SCORING_OUTPUTS = [
    "run.csv",
    "confidence_metrics.csv",
    "interface_metrics.csv",
    "rmsd.csv",
    "dockq.csv",
    "rosetta_metrics.csv",
    "developability_metrics.csv",
    "negative_design_metrics.csv",
    "leakage_homology_assessment.csv",
    "merged_run.csv",
]

MANUSCRIPT_REQUIRED_TOKENS = [
    "Benchmark framework / protocol-first manuscript",
    "Main Thesis",
    "Benchmark Lessons From Local Zotero Literature",
    "Expert review",
    "Target Set And Control Set Design",
    "Dataset Readiness And Target Candidates",
    "Generation Benchmark Protocol",
    "Ranking And Rescoring Benchmark Protocol",
    "Data Leakage, Homology Control And Target Novelty",
    "Reverse Outline",
    "Self-Review Checklist",
]

REQUIRED_EXPERT_ROLES = {
    "medicinal_chemistry",
    "computational_structural_biology",
    "ai_benchmark",
    "data_statistics",
    "engineering_reproducibility",
}

FORBIDDEN_TRACKED_SUFFIXES = {
    ".ckpt",
    ".pt",
    ".pth",
    ".pdb",
    ".zst",
    ".zstd",
    ".tar",
    ".gz",
    ".zip",
    ".7z",
}

ALLOWED_LARGE_TRACKED_FILES = {
    "raw_sources/zotero/seed_items_by_collection.json",
}


def read_csv(path: Path, delimiter: str = ",") -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return list(reader.fieldnames or []), list(reader)


def check_headers(errors: list[str], rel: str, expected: list[str], delimiter: str = ",") -> list[dict[str, str]]:
    path = ROOT / rel
    headers, rows = read_csv(path, delimiter=delimiter)
    if headers != expected:
        errors.append(f"{rel}: header mismatch: {headers}")
    return rows


def check_markdown_links(errors: list[str]) -> int:
    checked = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        rel_path = path.relative_to(ROOT)
        if rel_path.parts and rel_path.parts[0] == "raw_sources":
            continue
        text = path.read_text(encoding="utf-8")
        for link in link_pattern.findall(text):
            if "://" in link or link.startswith("#") or link.startswith("mailto:"):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            target_path = (path.parent / target).resolve()
            try:
                target_path.relative_to(ROOT.resolve())
            except ValueError:
                continue
            checked += 1
            if not target_path.exists():
                errors.append(f"{rel_path}: broken link -> {link}")
    return checked


def method_slug(method: str) -> str:
    if method in METHOD_SLUG_OVERRIDES:
        return METHOD_SLUG_OVERRIDES[method]
    return re.sub(r"[^a-z0-9]+", "-", method.lower()).strip("-")


def has_unqualified_forbidden_wording(text: str, phrase: str) -> bool:
    for line in text.splitlines():
        if phrase not in line:
            continue
        if any(marker in line for marker in ["避免", "不", "不能", "不得", "未", "尚未", "forbidden"]):
            continue
        return True
    return False


def check_tracked_large_or_forbidden_files(errors: list[str]) -> int:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    checked = 0
    for rel in completed.stdout.splitlines():
        path = ROOT / rel
        if not path.is_file():
            continue
        checked += 1
        if path.stat().st_size > 5_000_000 and rel not in ALLOWED_LARGE_TRACKED_FILES:
            errors.append(f"tracked file too large for KB release: {rel}")
        if path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES:
            errors.append(f"forbidden tracked large/artifact extension: {rel}")
        parts = set(Path(rel).parts)
        if ".git" in parts:
            errors.append(f"git metadata must not be tracked: {rel}")
    return checked


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    if errors:
        result = {"status": "fail", "errors": errors, "warnings": warnings}
        (ROOT / "reports/wiki_validation_report.md").write_text(
            "# Wiki Validation Report\n\n```json\n"
            + json.dumps(result, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    master_rows = check_headers(errors, "tables/master_literature_manifest.csv", MASTER_HEADERS)
    evidence_rows = check_headers(errors, "tables/method_evidence_matrix.csv", EVIDENCE_HEADERS)
    score_rows = check_headers(errors, "tables/candidate_method_scorecard.csv", SCORE_HEADERS)
    runnability_rows = check_headers(errors, "tables/method_runnability_matrix.csv", RUNNABILITY_HEADERS)
    benchmark_lesson_rows = check_headers(
        errors,
        "tables/benchmark_literature_lessons.csv",
        BENCHMARK_LITERATURE_HEADERS,
    )
    target_set_rows = check_headers(errors, "benchmarks/input_sets/target_set_v0.csv", TARGET_SET_HEADERS)
    dataset_candidate_rows = check_headers(
        errors,
        "benchmarks/input_sets/candidate_benchmark_datasets.csv",
        DATASET_CANDIDATE_HEADERS,
    )
    method_source_rows = check_headers(
        errors,
        "benchmarks/method_sources/method_source_manifest.csv",
        METHOD_SOURCE_HEADERS,
    )
    environment_rows = check_headers(
        errors,
        "benchmarks/environments/environment_feasibility_matrix.csv",
        ENVIRONMENT_HEADERS,
    )
    expert_review_rows = check_headers(errors, "tables/expert_review_action_items.csv", EXPERT_REVIEW_HEADERS)
    dataset_readiness_rows = check_headers(
        errors,
        "benchmarks/input_sets/dataset_readiness_scorecard.csv",
        DATASET_READINESS_HEADERS,
    )
    target_candidate_rows = check_headers(
        errors,
        "benchmarks/input_sets/target_candidate_matrix_v0.4.csv",
        TARGET_CANDIDATE_HEADERS,
    )
    source_pin_rows = check_headers(
        errors,
        "benchmarks/method_sources/source_pin_audit_v0.4.csv",
        SOURCE_PIN_HEADERS,
    )
    manuscript_claim_rows = check_headers(
        errors,
        "reports/benchmark_manuscript_claim_evidence_map.csv",
        MANUSCRIPT_CLAIM_HEADERS,
    )
    _map_rows = check_headers(errors, "references/zotero-map.tsv", ["zotero_key", "bibtex_key", "title"], delimiter="\t")

    included_master = [row for row in master_rows if row.get("screening_status") == "included"]
    for row in included_master:
        if not row.get("title") or not row.get("year") or not row.get("source_id"):
            errors.append(f"included row missing title/year/source_id: {row.get('zotero_key')}")

    included_methods = [row for row in score_rows if row.get("decision") == "include"]
    if not (5 <= len(included_methods) <= 10):
        errors.append(f"include method count must be 5-10, found {len(included_methods)}")

    for row in included_methods:
        if "public" not in row.get("code_status", "").lower() and "github" not in row.get("code_status", "").lower():
            warnings.append(f"{row.get('method')}: included method code status should be manually checked")
        total = int(row.get("total_score") or 0)
        if total < 15:
            errors.append(f"{row.get('method')}: total_score below minimum screening threshold")

    runnability_by_method = {row.get("method", ""): row for row in runnability_rows}
    included_method_names = [row.get("method", "") for row in included_methods]
    for method in included_method_names:
        runnability = runnability_by_method.get(method)
        if not runnability:
            errors.append(f"{method}: missing runnability row")
            continue
        if runnability.get("tier") not in {"Tier 1", "Tier 2", "Tier 3"}:
            errors.append(f"{method}: invalid runnability tier {runnability.get('tier')}")
        if runnability.get("scientific_priority") not in {"high", "medium", "low"}:
            errors.append(f"{method}: invalid scientific_priority {runnability.get('scientific_priority')}")
        if runnability.get("engineering_readiness") not in {"ready", "needs_mapping", "heavy_dependency"}:
            errors.append(f"{method}: invalid engineering_readiness {runnability.get('engineering_readiness')}")
        if runnability.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{method}: invalid task_id {runnability.get('task_id')}")
        for required_field in ["repo_url", "expected_inputs", "expected_outputs", "next_action"]:
            if not runnability.get(required_field):
                errors.append(f"{method}: runnability row missing {required_field}")

        smoke_path = ROOT / "benchmarks/smoke_tests" / method_slug(method) / "README.md"
        if not smoke_path.exists():
            errors.append(f"{method}: missing smoke-test README at {smoke_path.relative_to(ROOT)}")

    extra_runnability = sorted(set(runnability_by_method) - set(included_method_names))
    if extra_runnability:
        warnings.append("runnability rows for non-included methods: " + ", ".join(extra_runnability))

    if len(dataset_candidate_rows) < 6:
        errors.append(f"candidate_benchmark_datasets.csv should have at least 6 rows, found {len(dataset_candidate_rows)}")
    dataset_by_id = {row.get("dataset_id", ""): row for row in dataset_candidate_rows}
    overath = dataset_by_id.get("overath_binder_success_2025")
    if not overath:
        errors.append("candidate_benchmark_datasets.csv missing overath_binder_success_2025")
    else:
        for required_field in [
            "doi",
            "url",
            "version",
            "record_count",
            "download_policy",
            "benchmark_track",
            "recommended_use",
        ]:
            if not overath.get(required_field):
                errors.append(f"overath_binder_success_2025 missing {required_field}")
        if "10.1101/2025.08.14.670059" not in overath.get("doi", ""):
            errors.append("overath_binder_success_2025 missing bioRxiv DOI")
        if "10.5281/zenodo.15722219" not in overath.get("doi", ""):
            errors.append("overath_binder_success_2025 missing Zenodo DOI")
        if "metadata_only_in_v0.3" not in overath.get("download_policy", ""):
            errors.append("overath_binder_success_2025 must remain metadata_only_in_v0.3")
        if "ranking_rescoring" not in overath.get("benchmark_track", ""):
            errors.append("overath_binder_success_2025 should support ranking_rescoring")
        if "scoring_calibration" not in overath.get("benchmark_track", ""):
            errors.append("overath_binder_success_2025 should support scoring_calibration")

    method_source_by_method = {row.get("method", ""): row for row in method_source_rows}
    environment_by_method = {row.get("method", ""): row for row in environment_rows}
    allowed_source_status = {"public_url_recorded_not_cloned", "public_urls_recorded_not_cloned"}
    for method in included_method_names:
        source_row = method_source_by_method.get(method)
        if not source_row:
            errors.append(f"{method}: missing method source row")
        else:
            if source_row.get("code_access_status") not in allowed_source_status:
                errors.append(f"{method}: method source row must not claim cloned/installed status")
            for required_field in ["repo_url", "license_status", "weights_route", "large_artifact_policy", "next_action"]:
                if not source_row.get(required_field):
                    errors.append(f"{method}: method source row missing {required_field}")

        environment_row = environment_by_method.get(method)
        if not environment_row:
            errors.append(f"{method}: missing environment feasibility row")
        else:
            if environment_row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
                errors.append(f"{method}: invalid environment task_id {environment_row.get('task_id')}")
            for required_field in ["environment_type", "critical_dependencies", "install_risk", "next_action"]:
                if not environment_row.get(required_field):
                    errors.append(f"{method}: environment row missing {required_field}")

    if not benchmark_lesson_rows:
        errors.append("benchmark_literature_lessons.csv has no rows")
    for row in benchmark_lesson_rows:
        for required_field in ["zotero_key", "bibtex_key", "title", "year", "benchmark_lesson", "limitation"]:
            if not row.get(required_field):
                errors.append(f"benchmark_literature_lessons.csv row missing {required_field}: {row.get('bibtex_key')}")

    expert_roles = {row.get("reviewer_role", "") for row in expert_review_rows}
    missing_roles = sorted(REQUIRED_EXPERT_ROLES - expert_roles)
    if missing_roles:
        errors.append("expert_review_action_items.csv missing expert roles: " + ", ".join(missing_roles))
    if len(expert_review_rows) < 5:
        errors.append("expert_review_action_items.csv must contain at least 5 rows")
    for row in expert_review_rows:
        if row.get("severity") not in {"critical", "major", "minor"}:
            errors.append(f"expert review row has invalid severity: {row.get('issue')}")
        for required_field in ["artifact", "issue", "recommendation", "decision", "status", "evidence", "next_action"]:
            if not row.get(required_field):
                errors.append(f"expert review row missing {required_field}: {row.get('issue')}")

    if len(dataset_readiness_rows) < 7:
        errors.append(f"dataset_readiness_scorecard.csv should have at least 7 rows, found {len(dataset_readiness_rows)}")
    readiness_by_id = {row.get("dataset_id", ""): row for row in dataset_readiness_rows}
    for dataset_id, row in readiness_by_id.items():
        if not row.get("decision"):
            errors.append(f"{dataset_id}: missing dataset readiness decision")
    overath_readiness = readiness_by_id.get("overath_binder_success_2025")
    if not overath_readiness:
        errors.append("dataset_readiness_scorecard.csv missing overath_binder_success_2025")
    else:
        decision = overath_readiness.get("decision", "").lower()
        evidence = overath_readiness.get("evidence", "").lower()
        if "generation" in decision and "not_generation" not in decision:
            errors.append("Overath readiness must not be peptide generation evidence")
        if "3676" not in evidence or "blank target" not in evidence:
            errors.append("Overath readiness evidence must record scanned row count and blank target rows")

    if len(target_candidate_rows) == 0:
        errors.append("target_candidate_matrix_v0.4.csv must contain target candidates")
    if target_set_rows:
        warnings.append("target_set_v0.csv has frozen rows; verify all controls/license/leakage fields manually")
    blank_target_rows = [
        row for row in target_candidate_rows if row.get("dataset_id") == "overath_binder_success_2025" and not row.get("target_id")
    ]
    if not blank_target_rows:
        errors.append("target_candidate_matrix_v0.4.csv should record Overath blank target rows")
    for row in target_candidate_rows:
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{row.get('candidate_id')}: invalid target candidate task_id {row.get('task_id')}")
        if not row.get("decision"):
            errors.append(f"{row.get('candidate_id')}: missing target candidate decision")

    source_pin_methods = {row.get("method", "") for row in source_pin_rows if row.get("audit_status") == "pinned_no_install"}
    for method in ["PepMLM", "RFdiffusion + ProteinMPNN", "PepMirror"]:
        if method not in source_pin_methods:
            errors.append(f"{method}: missing pinned_no_install source pin row")
    if len(source_pin_rows) < 3:
        errors.append("source_pin_audit_v0.4.csv must contain at least 3 priority source pins")
    for row in source_pin_rows:
        if row.get("audit_status") != "pinned_no_install":
            errors.append(f"{row.get('method')} {row.get('repo_name')}: source pin audit must remain pinned_no_install")
        for required_field in ["repo_url", "external_audit_path", "default_branch", "commit_sha", "weights_policy", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('method')} {row.get('repo_name')}: source pin row missing {required_field}")
        for field in ["audit_status", "weights_policy", "batch_route"]:
            value = row.get(field, "").lower()
            if "installed" in value or "reproduced" in value or "ran_locally" in value:
                errors.append(f"{row.get('method')} {row.get('repo_name')}: source pin row overclaims {field}")

    protocol_text = (ROOT / "benchmarks/protocols/benchmark_protocol_v0.md").read_text(encoding="utf-8")
    for task in REQUIRED_PROTOCOL_TASKS:
        if task not in protocol_text:
            errors.append(f"benchmark_protocol_v0.md missing task {task}")
    for token in ["Generation Versus Ranking Tracks", "Target Set And Controls", "Leakage And Homology Control"]:
        if token not in protocol_text:
            errors.append(f"benchmark_protocol_v0.md missing required section {token}")

    scoring_schema = (ROOT / "benchmarks/protocols/scoring_outputs_schema.md").read_text(encoding="utf-8")
    for filename in REQUIRED_SCORING_OUTPUTS:
        if filename not in scoring_schema:
            errors.append(f"scoring_outputs_schema.md missing output table {filename}")
    scoring_protocol = (ROOT / "benchmarks/scoring/scoring_protocol_v0.md").read_text(encoding="utf-8")
    for family in ["developability", "negative_design", "leakage_homology"]:
        if family not in scoring_protocol:
            errors.append(f"scoring_protocol_v0.md missing metric family {family}")

    manuscript_outline = (ROOT / "reports/benchmark_manuscript_outline.md").read_text(encoding="utf-8")
    for token in MANUSCRIPT_REQUIRED_TOKENS:
        if token not in manuscript_outline:
            errors.append(f"benchmark_manuscript_outline.md missing required token {token}")
    for forbidden in ["性能最佳", "已复现", "已经完成性能排名"]:
        if has_unqualified_forbidden_wording(manuscript_outline, forbidden):
            errors.append(f"benchmark_manuscript_outline.md contains unsupported claim wording: {forbidden}")
    if not manuscript_claim_rows:
        errors.append("benchmark_manuscript_claim_evidence_map.csv has no claim rows")
    if len(manuscript_claim_rows) < 12:
        errors.append("benchmark_manuscript_claim_evidence_map.csv should cover revised benchmark claims")

    method_files = sorted((ROOT / "wiki/methods").glob("*.md"))
    method_files = [path for path in method_files if path.name != "_index.md"]
    if len(method_files) < len(score_rows):
        errors.append(f"method card count {len(method_files)} is less than score rows {len(score_rows)}")
    for path in method_files:
        text = path.read_text(encoding="utf-8")
        for token in METHOD_REQUIRED_TOKENS:
            if token not in text:
                errors.append(f"{path.relative_to(ROOT)} missing required section {token}")

    if len(evidence_rows) != len(score_rows):
        errors.append("method_evidence_matrix and candidate_method_scorecard row counts differ")

    bibtex = (ROOT / "references/references.bib").read_text(encoding="utf-8")
    bib_entries = len(re.findall(r"@\w+\{", bibtex))
    if bib_entries == 0:
        errors.append("references.bib has no BibTeX entries")

    link_count = check_markdown_links(errors)
    tracked_file_count = check_tracked_large_or_forbidden_files(errors)

    literature_cards = [path for path in (ROOT / "wiki/literature").glob("*.md") if path.name != "_index.md"]
    if len(literature_cards) < 10:
        warnings.append(f"only {len(literature_cards)} literature cards generated")

    result = {
        "status": "pass" if not errors else "fail",
        "counts": {
            "master_rows": len(master_rows),
            "included_master_rows": len(included_master),
            "evidence_rows": len(evidence_rows),
            "score_rows": len(score_rows),
            "included_methods": len(included_methods),
            "runnability_rows": len(runnability_rows),
            "benchmark_literature_rows": len(benchmark_lesson_rows),
            "target_set_rows": len(target_set_rows),
            "candidate_dataset_rows": len(dataset_candidate_rows),
            "method_source_rows": len(method_source_rows),
            "environment_rows": len(environment_rows),
            "expert_review_rows": len(expert_review_rows),
            "dataset_readiness_rows": len(dataset_readiness_rows),
            "target_candidate_rows": len(target_candidate_rows),
            "source_pin_rows": len(source_pin_rows),
            "manuscript_claim_rows": len(manuscript_claim_rows),
            "smoke_test_readmes": len(
                [path for path in (ROOT / "benchmarks/smoke_tests").glob("*/README.md")]
            ),
            "method_cards": len(method_files),
            "literature_cards": len(literature_cards),
            "bibtex_entries": bib_entries,
            "markdown_links_checked": link_count,
            "tracked_files_checked": tracked_file_count,
        },
        "errors": errors,
        "warnings": warnings,
    }

    report = "# Wiki Validation Report\n\n"
    report += "## Summary\n"
    report += f"- Status: {result['status']}\n"
    for key, value in result["counts"].items():
        report += f"- {key}: {value}\n"
    report += "\n## Errors\n"
    report += "\n".join(f"- {item}" for item in errors) if errors else "- None"
    report += "\n\n## Warnings\n"
    report += "\n".join(f"- {item}" for item in warnings) if warnings else "- None"
    report += "\n\n## Raw JSON\n\n```json\n"
    report += json.dumps(result, ensure_ascii=False, indent=2)
    report += "\n```\n"
    (ROOT / "reports/wiki_validation_report.md").write_text(report, encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
