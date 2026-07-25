#!/usr/bin/env python
"""Validate the peptide-design benchmark knowledge base artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.engine.path_policy import is_acceptance_state_path


_GIT_CONFIG_ARGUMENTS = (
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.attributesFile=/dev/null",
)


def _sanitized_git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"LANG", "TMPDIR", "TMP", "TEMP"} or key.startswith("LC_")
    }
    environment.update(
        {
            "PATH": os.defpath,
            "HOME": os.devnull,
            "XDG_CONFIG_HOME": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


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

HOMEPAGE_METHOD_SOURCE_HEADERS = [
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

HOMEPAGE_INCLUDED_METHODS = {
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

HOMEPAGE_SOURCE_BOUNDARY = (
    "source_and_interface_navigation_only_not_runnability_or_performance"
)

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

LINK_AVAILABILITY_HEADERS = [
    "record_id",
    "artifact_type",
    "artifact_id",
    "label",
    "url",
    "check_method",
    "checked_at",
    "status",
    "http_status",
    "content_length",
    "content_type",
    "default_branch",
    "commit_sha",
    "license_or_access",
    "gated_or_auth",
    "download_performed",
    "evidence",
    "next_action",
]

DATA_ACCESS_HEADERS = [
    "dataset_id",
    "endpoint_id",
    "source_name",
    "url",
    "access_type",
    "checked_at",
    "availability_status",
    "http_status",
    "content_length",
    "license_status",
    "gated_or_auth",
    "direct_download_status",
    "download_performed",
    "recommended_use",
    "blocking_risk",
    "next_action",
]

ARS_REVIEW_ACTION_HEADERS = [
    "reviewer_role",
    "severity",
    "artifact",
    "issue",
    "recommendation",
    "decision",
    "status",
    "evidence",
    "next_action",
    "gate",
]

DATASET_SUPPLEMENT_WATCHLIST_HEADERS = [
    "candidate_id",
    "source_name",
    "source_url",
    "source_type",
    "task_relevance",
    "current_evidence",
    "readiness_decision",
    "risks",
    "next_action",
]

RUN_CSV_HEADERS = [
    "design_id",
    "method",
    "task_id",
    "target_id",
    "binder_id",
    "input_mode",
    "target_sequence",
    "target_pdb",
    "target_chains",
    "binder_chain",
    "pocket_definition",
    "peptide_type",
    "chirality",
    "cyclic",
    "status",
    "notes",
]

DOWNLOAD_MANIFEST_HEADERS = [
    "artifact_id",
    "artifact_type",
    "method_or_dataset",
    "source_url",
    "version_or_commit",
    "expected_size",
    "license_status",
    "checksum_status",
    "local_destination",
    "download_status",
    "download_performed",
    "next_action",
]

DATASET_SCHEMA_REVIEW_HEADERS = [
    "candidate_id",
    "source_name",
    "task_relevance",
    "license_status",
    "schema_status",
    "controls_status",
    "leakage_status",
    "download_route_status",
    "decision",
    "next_action",
]

DATASET_SCHEMA_REVIEW_V08_HEADERS = [
    "candidate_id",
    "source_name",
    "task_relevance",
    "license_status",
    "schema_status",
    "controls_status",
    "leakage_status",
    "download_route_status",
    "audit_evidence",
    "decision",
    "next_action",
]

METHOD_READINESS_REVIEW_HEADERS = [
    "method",
    "component",
    "current_gate",
    "license_status",
    "license_evidence",
    "input_contract_status",
    "environment_status",
    "weights_or_checkpoint_status",
    "download_manifest_status",
    "blocking_items",
    "decision",
    "next_action",
]

METHOD_LANDSCAPE_HEADERS = [
    "method",
    "representative_paper",
    "generation_paradigm",
    "peptide_topology",
    "target_conditioning",
    "mapped_task_id",
    "project_pool_status",
    "benchmark_relevance",
    "coverage_gap",
    "risks",
    "next_action",
]

BILINGUAL_SYNC_HEADERS = [
    "section_id",
    "zh_section",
    "en_section",
    "shared_artifacts",
    "claim_ids",
    "status",
    "next_action",
]

METHOD_CLASSIFICATION_HEADERS = [
    "method",
    "pool_status",
    "task_id",
    "method_family",
    "design_paradigm",
    "peptide_type",
    "input_requirement",
    "output_type",
    "code_url",
    "source_status",
    "weights_route",
    "current_gate",
    "next_action",
]

REFERENCE_DATASET_SOURCE_HEADERS = [
    "dataset_id",
    "source_name",
    "task_fit",
    "source_url",
    "license_status",
    "schema_status",
    "assay_readout",
    "positive_controls",
    "negative_controls",
    "leakage_risk",
    "download_status",
    "planned_use",
    "next_action",
]

MANUSCRIPT_TODO_HEADERS = [
    "todo_id",
    "priority",
    "artifact",
    "task",
    "status",
    "evidence",
    "next_action",
    "blocking_issue",
]

SUPPLEMENTARY_MATERIAL_HEADERS = [
    "source_id",
    "source_path",
    "material_type",
    "reference_value",
    "key_structure",
    "borrowable_content",
    "benchmark_use",
    "evidence_boundary",
    "target_artifact",
    "action",
    "priority",
    "status",
    "next_action",
]

SCORING_RATIONALE_HEADERS = [
    "metric_or_check",
    "metric_family",
    "why_needed",
    "source_support",
    "applicable_tasks",
    "applicable_outputs",
    "not_applicable_reason",
    "claim_boundary",
    "next_action",
]

METHOD_LANDSCAPE_PATCH_HEADERS = [
    "method",
    "patch_status",
    "proposed_pool_status",
    "related_task_id",
    "design_paradigm",
    "peptide_scope",
    "code_or_source_route",
    "source_materials",
    "primary_source_status",
    "evidence_boundary",
    "target_artifact",
    "next_action",
]

GRANT_REVIEW_ACTION_HEADERS = [
    "review_panel",
    "criterion",
    "score",
    "severity",
    "artifact",
    "issue",
    "recommendation",
    "decision",
    "status",
    "evidence",
    "next_action",
    "gate",
]

PREFLIGHT_DOWNLOAD_APPROVAL_HEADERS = [
    "artifact_id",
    "artifact_type",
    "method_or_dataset",
    "source_url",
    "version_or_commit",
    "license_status",
    "expected_size",
    "checksum_policy",
    "external_destination",
    "approval_required",
    "approved_by",
    "download_performed",
    "next_gate",
    "next_action",
]

METHOD_PREFLIGHT_STATUS_HEADERS = [
    "method",
    "batch",
    "current_gate",
    "max_allowed_gate",
    "preflight_status",
    "license_status",
    "source_status",
    "weights_or_checkpoint_status",
    "input_contract_status",
    "environment_status",
    "external_roots",
    "blocking_items",
    "next_action",
]

MIGRATION_FILE_ROLE_HEADERS = [
    "old_path",
    "new_path",
    "role",
    "migration_reason",
    "validator_required",
]

JOB_MANIFEST_HEADERS = [
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

METHOD_OUTPUT_MANIFEST_HEADERS = [
    "run_record_id",
    "job_id",
    "method",
    "task_id",
    "execution_stage",
    "source_commit",
    "model_revision",
    "environment_id",
    "command",
    "raw_output_root",
    "stdout_log",
    "stderr_log",
    "runtime_seconds",
    "exit_code",
    "parser_status",
    "status_reason",
    "created_at",
]

CANDIDATE_OUTPUT_HEADERS = [
    "design_id",
    "job_id",
    "method",
    "target_id",
    "binder_id",
    "source_output_id",
    "generation_rank",
    "sequence",
    "structure_path",
    "peptide_type",
    "chirality",
    "cyclic",
    "parse_status",
    "status_reason",
    "notes",
]

SOURCE_FRESHNESS_HEADERS = [
    "record_id",
    "method_or_artifact",
    "artifact_type",
    "primary_paper",
    "doi_or_identifier",
    "official_metadata_sources",
    "code_route",
    "model_or_data_route",
    "license_route",
    "freshness_check_status",
    "download_allowed",
    "next_action",
]

SOURCE_CLONE_HEADERS = [
    "method",
    "repo_name",
    "repo_url",
    "default_branch",
    "pinned_commit",
    "external_clone_path",
    "clone_performed",
    "checkout_status",
    "observed_head",
    "license_files",
    "environment_files",
    "submodule_status",
    "lfs_pointer_status",
    "next_gate",
    "notes",
]

DOCKER_IMAGE_INVENTORY_HEADERS = [
    "image_tag",
    "service_name",
    "covered_methods_or_role",
    "local_status",
    "image_id_or_build_state",
    "size_or_scope",
    "source_mount",
    "model_or_weight_mount",
    "license_boundary",
    "smoke_test_target",
    "next_action",
]

METHOD_ENVIRONMENT_ASSIGNMENT_HEADERS = [
    "method",
    "benchmark_role",
    "assigned_image",
    "assigned_conda_env",
    "assignment_status",
    "source_root",
    "model_or_weight_mount",
    "input_contract_scope",
    "license_boundary",
    "smoke_test_target",
    "next_gate",
    "next_action",
]

METHOD_PAPER_CASE_V014_HEADERS = [
    "method",
    "case_id",
    "case_scope",
    "source_paper",
    "source_identifier",
    "source_url",
    "publication_status",
    "reported_case_or_dataset",
    "target_or_dataset",
    "pdb_id_or_panel",
    "task_id",
    "peptide_scope",
    "input_requirement",
    "case_role_for_benchmark",
    "benchmark_use_decision",
    "evidence_boundary",
    "next_action",
]

TARGET_ACADEMIC_SEARCH_V014_HEADERS = [
    "candidate_id",
    "target_or_panel",
    "source_type",
    "primary_source",
    "source_identifier",
    "source_url",
    "pdb_id_or_panel_size",
    "target_class",
    "task_id",
    "peptide_design_feature",
    "method_paper_anchor",
    "benchmark_track",
    "priority",
    "readiness_decision",
    "evidence_summary",
    "required_controls_or_checks",
    "download_policy",
    "next_action",
]

ADAPTER_PREFLIGHT_HEADERS = [
    "method",
    "batch",
    "adapter_gate",
    "job_manifest_status",
    "input_adapter_status",
    "output_parser_status",
    "expected_raw_outputs",
    "allowed_test_depth",
    "blocking_items",
    "next_action",
]

RUN_PREFLIGHT_RESULTS_V015_HEADERS = [
    "target",
    "check_scope",
    "status",
    "exit_code",
    "image_tag",
    "image_id",
    "external_log_path",
    "torch_version",
    "torch_cuda",
    "torch_cuda_available",
    "import_notes",
    "evidence_boundary",
    "next_action",
]

BATCH_A_SMOKE_TEST_RESULTS_V015_HEADERS = [
    "method",
    "smoke_test_id",
    "status",
    "exit_code",
    "duration_seconds",
    "image_tag",
    "source_commit",
    "input_summary",
    "output_summary",
    "external_method_dir",
    "output_file_count",
    "output_bytes",
    "model_or_weight_event",
    "evidence_boundary",
    "next_gate",
    "next_action",
]

ADAPTER_PARSER_HARDENING_V016_HEADERS = [
    "method",
    "batch",
    "current_evidence",
    "adapter_scope",
    "input_adapter_status",
    "command_contract_status",
    "output_parser_status",
    "required_raw_outputs",
    "external_roots",
    "replay_inputs",
    "next_gate",
    "blocking_items",
    "next_action",
]

BATCH_B_TARGET_REVIEW_V016_HEADERS = [
    "candidate_id",
    "target_or_panel",
    "evidence_lane",
    "source_anchor",
    "pdb_or_panel",
    "task_id",
    "benchmark_role",
    "structure_chain_status",
    "known_binder_status",
    "assay_readout_status",
    "license_status",
    "leakage_status",
    "control_status",
    "readiness_decision",
    "next_action",
]

BATCH_B_PILOT_TARGET_GATE_V017_HEADERS = [
    "target_gate_id",
    "source_candidate_id",
    "target_or_fixture",
    "pdb_or_local_ref",
    "task_id",
    "target_class",
    "receptor_chains",
    "peptide_chains",
    "known_peptide_sequence",
    "structure_status",
    "assay_control_status",
    "license_status",
    "leakage_status",
    "pilot_decision",
    "allowed_use",
    "source_evidence",
    "next_action",
]

BATCH_B_PILOT_METHOD_SCOPE_V017_HEADERS = [
    "method",
    "pilot_track",
    "current_status",
    "image_tag",
    "source_commit_or_route",
    "adapter_status",
    "parser_status",
    "allowed_pilot_use",
    "blocking_items",
    "next_action",
]

ADAPTER_REPLAY_FIXTURE_V018_HEADERS = [
    "fixture_id",
    "method",
    "source_stage",
    "external_method_dir",
    "command_path",
    "stdout_log",
    "stderr_log",
    "runtime_json",
    "primary_output",
    "parser_name",
    "parser_version",
    "expected_candidate_outputs",
    "expected_run_csv",
    "fixture_status",
    "evidence_boundary",
    "next_action",
]

METHOD_SOURCE_DOC_VERIFICATION_V019_HEADERS = [
    "method",
    "source_dir",
    "source_commit",
    "source_route",
    "doc_route_checked",
    "example_route_checked",
    "license_access_route",
    "model_weight_route",
    "verification_status",
    "blocker",
    "next_action",
]

METHOD_INSTALL_SMOKE_MANIFEST_V019_HEADERS = [
    "method",
    "workbench_root",
    "source_dir",
    "image_tag",
    "conda_env",
    "gpu_policy",
    "smoke_entrypoint",
    "external_output_dir",
    "command_log",
    "stdout_log",
    "stderr_log",
    "runtime_json",
    "outputs_manifest",
    "manifest_status",
    "evidence_boundary",
    "next_action",
]

METHOD_SMOKE_TEST_RESULTS_V019_HEADERS = [
    "method",
    "smoke_test_id",
    "task_scope",
    "status",
    "exit_code",
    "runtime_sec",
    "image_tag",
    "conda_env",
    "source_commit",
    "gpu_required",
    "gpu_evidence",
    "output_status",
    "parser_status",
    "external_method_dir",
    "command_path",
    "stdout_log",
    "stderr_log",
    "runtime_json",
    "outputs_manifest",
    "model_or_weight_event",
    "blocker",
    "evidence_boundary",
    "next_gate",
]

METHOD_UNBLOCK_MANIFEST_V020_HEADERS = METHOD_INSTALL_SMOKE_MANIFEST_V019_HEADERS
METHOD_UNBLOCK_SMOKE_RESULTS_V020_HEADERS = METHOD_SMOKE_TEST_RESULTS_V019_HEADERS

ADAPTER_SMOKE_MANIFEST_V021_HEADERS = [
    "method",
    "workbench_root",
    "source_dir",
    "image_tag",
    "conda_env",
    "gpu_policy",
    "adapter_entrypoint",
    "external_output_dir",
    "command_log",
    "stdout_log",
    "stderr_log",
    "runtime_json",
    "outputs_manifest",
    "manifest_status",
    "evidence_boundary",
    "next_action",
]

ADAPTER_SMOKE_RESULTS_V021_HEADERS = [
    "method",
    "adapter_smoke_id",
    "task_scope",
    "status",
    "exit_code",
    "runtime_sec",
    "image_tag",
    "conda_env",
    "source_commit",
    "gpu_required",
    "gpu_evidence",
    "output_status",
    "parser_status",
    "external_method_dir",
    "command_path",
    "stdout_log",
    "stderr_log",
    "runtime_json",
    "outputs_manifest",
    "model_or_weight_event",
    "blocker",
    "evidence_boundary",
    "next_gate",
]

BLOCKER_ASSET_MANIFEST_V021_HEADERS = [
    "method",
    "asset_id",
    "source_url",
    "local_path",
    "expected_sha256",
    "observed_sha256",
    "size_bytes",
    "status",
    "notes",
]

METHOD_EXAMPLE_FIXTURE_EVIDENCE_V022_HEADERS = [
    "method",
    "v021_adapter_smoke_id",
    "v021_candidate_design_id",
    "evidence_source",
    "parsed_sequence",
    "parse_status",
    "evidence_type",
    "pilot_lane",
    "v022_decision",
    "target_binding",
    "contract_status",
    "blocker",
    "next_action",
]

MULTI_CASE_FIXTURE_TARGET_V022_HEADERS = [
    "fixture_case_id",
    "target_id",
    "source_target_gate_id",
    "task_id",
    "target_label",
    "target_sequence_or_ref",
    "target_pdb_or_ref",
    "target_chains",
    "peptide_or_binder_chain",
    "known_peptide_sequence",
    "case_role",
    "pilot_lane",
    "target_status",
    "control_status",
    "allowed_use",
    "evidence_source",
    "blocker",
    "next_action",
]

MULTI_CASE_FIXTURE_CONTROL_V022_HEADERS = [
    "control_id",
    "fixture_case_id",
    "control_type",
    "control_label",
    "control_input_ref",
    "expected_use",
    "status",
    "allowed_use",
    "blocker",
    "next_action",
]

MULTI_CASE_FIXTURE_JOB_V022_HEADERS = JOB_MANIFEST_HEADERS + [
    "fixture_case_id",
    "control_id",
    "evidence_source",
    "pilot_lane",
    "contract_status",
    "failure_policy",
]

PRIORITY_GATE_REVIEW_V022_HEADERS = [
    "gate_id",
    "method",
    "priority_area",
    "current_status",
    "required_external_asset_or_adapter",
    "required_contract_check",
    "allowed_v022_use",
    "hard_stop_or_blocker",
    "promotion_condition",
    "next_action",
]

NOTEBOOK_CLI_SMOKE_V023_HEADERS = [
    "component_id",
    "component",
    "environment_path",
    "python_version",
    "installed_packages",
    "smoke_command",
    "smoke_output",
    "status",
    "blocker",
    "evidence_boundary",
    "next_action",
]

DFLOW_PROJECT_INSTALL_V023_HEADERS = [
    "method",
    "source_dir",
    "source_commit",
    "source_mode",
    "is_symlink",
    "environment_path",
    "python_version",
    "gpu_evidence",
    "weight_path",
    "weight_sha256",
    "package_import_status",
    "model_import_status",
    "inference_import_status",
    "deepspeed_patch",
    "official_env_status",
    "input_contract_status",
    "load_test_log",
    "blocker",
    "next_gate",
    "evidence_boundary",
    "next_action",
]

EXTERNAL_DRY_RUN_PACKAGE_V023_HEADERS = [
    "package_item_id",
    "method_or_component",
    "role",
    "project_local_path",
    "runtime_evidence",
    "status",
    "blocker",
    "allowed_use",
    "next_action",
]

PRIORITY_GATE_REVIEW_V023_HEADERS = [
    "gate_id",
    "method",
    "priority_area",
    "v022_status",
    "v023_status",
    "observed_evidence",
    "remaining_blocker",
    "allowed_v023_use",
    "promotion_condition",
    "next_action",
]

DFLOW_INPUT_CONTRACT_FIXTURE_V024_HEADERS = [
    "method",
    "fixture_case_id",
    "pdb_id",
    "receptor_chains",
    "peptide_chains",
    "structure_dir",
    "case_dir",
    "dataset_dir",
    "names_file",
    "lmdb_path",
    "lmdb_size_bytes",
    "lmdb_entries",
    "entry_id_sha256",
    "pep_dataset_reset_true_status",
    "pep_dataset_reset_false_status",
    "first_total_residues",
    "first_generated_residues",
    "log_path",
    "script",
    "status",
    "evidence_boundary",
    "next_action",
]

DFLOW_FULL_PEPMERGE_DOWNLOAD_V025_HEADERS = [
    "method",
    "asset_set",
    "source_url",
    "source_file_ids",
    "download_route",
    "download_status",
    "release_zip_path",
    "release_zip_size_bytes",
    "release_zip_sha256",
    "release_zip_integrity_status",
    "release_structure_dir",
    "case_dirs",
    "structure_files",
    "required_file_missing_case_dirs",
    "lmdb_zip_path",
    "lmdb_zip_size_bytes",
    "lmdb_zip_sha256",
    "lmdb_zip_integrity_status",
    "lmdb_dir",
    "test_names",
    "train_names",
    "test_names_missing_in_release",
    "pep_dataset_test_entries",
    "pep_dataset_train_entries",
    "pep_dataset_load_status",
    "names_bridge",
    "status",
    "evidence_boundary",
    "next_action",
]

DFLOW_COLAB_BINDCRAFT_V026_HEADERS = [
    "item_id",
    "method",
    "component",
    "status",
    "execution_status",
    "exit_code",
    "runtime_sec",
    "gpu_evidence",
    "command_path",
    "raw_output_root",
    "primary_output",
    "parser_or_classifier_status",
    "observed_items",
    "blocker",
    "next_gate",
    "evidence_boundary",
    "next_action",
]

BINDCRAFT_CLASSIFICATION_V026_HEADERS = [
    "method",
    "output_root",
    "classification",
    "accepted_pdb_count",
    "low_confidence_pdb_count",
    "rejected_pdb_count",
    "trajectory_pdb_count",
    "runtime_exit_code",
    "hard_stop_status",
    "reason",
    "evidence_boundary",
]

COLABDESIGN_DEXDESIGN_GATE_V027_HEADERS = [
    "item_id",
    "method",
    "component",
    "status",
    "execution_status",
    "exit_code",
    "runtime_sec",
    "gpu_evidence",
    "command_path",
    "raw_output_root",
    "primary_output",
    "parser_or_audit_status",
    "generic_osprey_example_status",
    "observed_items",
    "blocker",
    "next_gate",
    "evidence_boundary",
    "next_action",
]

EXTERNAL_ASSET_RESCUE_V028_HEADERS = [
    "item_id",
    "method",
    "blocker",
    "search_scope",
    "status",
    "execution_status",
    "asset_or_output_status",
    "external_asset_path",
    "raw_output_root",
    "primary_output",
    "secondary_evidence",
    "observed_items",
    "blocker_remaining",
    "next_gate",
    "evidence_boundary",
    "next_action",
]

BOUNDED_GENERATION_PARSER_V029_HEADERS = [
    "item_id",
    "method",
    "artifact_type",
    "status",
    "execution_status",
    "job_or_fixture_id",
    "external_source_or_output",
    "tracked_artifact",
    "runtime_artifact",
    "exit_code",
    "parser_status",
    "candidate_count",
    "evidence_boundary",
    "next_action",
]

PILOT_BENCHMARK_TARGET_V030_HEADERS = [
    "pilot_target_id",
    "target_id",
    "task_id",
    "target_label",
    "input_ref",
    "target_sequence",
    "target_pdb",
    "target_chains",
    "binder_chain",
    "benchmark_lane",
    "allowed_methods",
    "target_status",
    "control_status",
    "leakage_status",
    "license_status",
    "wet_lab_priority",
    "allowed_use",
    "evidence_source",
    "evidence_boundary",
    "next_action",
]

PILOT_BENCHMARK_CONTROL_V030_HEADERS = [
    "control_id",
    "pilot_target_id",
    "control_type",
    "control_label",
    "control_input_ref",
    "status",
    "allowed_use",
    "blocker",
    "evidence_boundary",
    "next_action",
]

PILOT_BENCHMARK_JOB_V030_HEADERS = JOB_MANIFEST_HEADERS + [
    "pilot_target_id",
    "pilot_lane",
    "execution_wave",
    "expected_output_contract",
    "failure_policy",
    "evidence_boundary",
]

PILOT_EXECUTION_MATRIX_V030_HEADERS = [
    "execution_id",
    "job_id",
    "method",
    "target_id",
    "execution_wave",
    "runner",
    "container_or_env",
    "gpu_required",
    "max_runtime_sec",
    "output_root",
    "expected_parser",
    "status",
    "blocked_reason",
    "evidence_boundary",
    "next_action",
]

WET_LAB_CANDIDATE_PANEL_V030_HEADERS = [
    "wet_lab_candidate_id",
    "target_id",
    "target_label",
    "validation_tier",
    "recommended_assay",
    "positive_control",
    "negative_control_or_decoy",
    "expected_materials",
    "selection_trigger",
    "status",
    "evidence_source",
    "evidence_boundary",
    "next_action",
]

PILOT_EXECUTION_RESULTS_V031_HEADERS = [
    "execution_id",
    "job_id",
    "method",
    "target_id",
    "execution_wave",
    "runner",
    "container_or_env",
    "output_root",
    "status",
    "exit_code",
    "runtime_seconds",
    "parser_status",
    "candidate_count",
    "blocked_reason",
    "evidence_boundary",
    "next_action",
]

PILOT_RUN_V031_HEADERS = [
    "design_id",
    "method",
    "task_id",
    "target_id",
    "binder_id",
    "input_mode",
    "target_sequence",
    "target_pdb",
    "target_chains",
    "binder_chain",
    "pocket_definition",
    "peptide_type",
    "chirality",
    "cyclic",
    "status",
    "notes",
    "parent_job_id",
    "source_output_id",
    "generation_rank",
    "random_seed",
    "adapter_status",
    "status_reason",
]

PILOT_BENCHMARK_JOB_V034_HEADERS = PILOT_BENCHMARK_JOB_V030_HEADERS + [
    "length_min",
    "length_max",
    "expected_target_chain",
    "expected_binder_chain",
    "chirality_check_mode",
    "cyclic_check_mode",
    "noncanonical_policy",
    "seed_stage",
    "primary_job_id",
    "effective_seed_required",
    "target_pdb_path",
    "target_pdb_sha256",
    "target_binding_check_mode",
]

PILOT_EXECUTION_MATRIX_V034_HEADERS = PILOT_EXECUTION_MATRIX_V030_HEADERS + [
    "seed_stage",
    "primary_job_id",
]

PILOT_EXECUTION_RESULTS_V034_HEADERS = [
    "execution_id",
    "job_id",
    "method",
    "seed_stage",
    "random_seed",
    "attempt_id",
    "attempt_dir",
    "status",
    "overall_qc_status",
    "supported_candidate",
    "merge_status",
    "status_reason",
    "candidate_parse_status",
    "qc_status_reason",
    "chirality_evaluable",
    "chirality_l_count",
    "chirality_d_count",
    "chirality_unknown_count",
    "method_contract_status",
    "handoff_status",
]

PILOT_METHOD_OUTPUT_V034_HEADERS = [
    "run_record_id",
    "job_id",
    "method",
    "task_id",
    "execution_stage",
    "source_commit",
    "model_revision",
    "environment_id",
    "command",
    "raw_output_root",
    "stdout_log",
    "stderr_log",
    "runtime_seconds",
    "exit_code",
    "parser_status",
    "overall_qc_status",
    "status",
    "status_reason",
    "created_at",
]

PILOT_CANDIDATE_OUTPUT_V034_HEADERS = [
    "design_id",
    "job_id",
    "method",
    "target_id",
    "binder_id",
    "source_output_id",
    "generation_rank",
    "sequence",
    "structure_path",
    "source_output_path",
    "binder_chain",
    "peptide_type",
    "chirality",
    "cyclic",
    "parse_status",
    "status_reason",
    "notes",
    "supported_candidate",
]

PILOT_CANDIDATE_QC_V034_HEADERS = [
    "job_id",
    "design_id",
    "overall_qc_status",
    "status_reason",
    "backbone_to_fasta_handoff_status",
    "chain_status",
    "chirality_d_count",
    "chirality_evaluable",
    "chirality_gly_count",
    "chirality_l_count",
    "chirality_status",
    "chirality_unknown_count",
    "cyclic_status",
    "file_reason",
    "file_sha256",
    "file_size_bytes",
    "file_status",
    "handoff_status",
    "length_status",
    "method_contract_status",
    "mirror_output_atom_count",
    "mirror_output_atom_identity_status",
    "mirror_output_central_inversion_max_residual",
    "mirror_output_central_inversion_status",
    "mirror_output_central_inversion_tolerance",
    "mirror_target_atom_count",
    "mirror_target_atom_identity_status",
    "mirror_target_central_inversion_max_residual",
    "mirror_target_central_inversion_status",
    "mirror_target_central_inversion_tolerance",
    "noncanonical_residues",
    "noncanonical_status",
    "parse_status",
    "seed_status",
    "sequence_length",
    "sequence_structure_status",
    "supported_candidate",
    "target_binding_status",
    "terminal_cn_distance",
]

PILOT_RUN_V034_HEADERS = [
    "design_id",
    "job_id",
    "method",
    "task_id",
    "target_id",
    "input_mode",
    "peptide_type",
    "chirality",
    "cyclic",
    "random_seed",
    "seed_stage",
    "attempt_id",
    "status",
    "overall_qc_status",
    "supported_candidate",
    "sequence",
    "structure_path",
    "status_reason",
    "notes",
]

V034_JOB_METHODS = {
    "v034_pepmlm_sequence": "PepMLM",
    "v034_diffpepbuilder_3eqs": "DiffPepBuilder",
    "v034_pepglad_3eqs": "PepGLAD",
    "v034_dflow_3eqs": "D-Flow / PeptideDesign",
    "v034_pepmirror_3eqs": "PepMirror",
    "v034_colabdesign_7zkr": "AfCycDesign / ColabDesign cyclic peptide",
    "v034_rfdiffusion_mpnn_7zkr": "RFdiffusion + ProteinMPNN",
}

V034_RUNTIME_PAYLOAD_FIELDS = frozenset(
    {"schema_version", "evidence_boundary", "records"}
)
V034_RUNTIME_RECORD_FIELDS = frozenset(
    {
        "job_id",
        "method",
        "seed_stage",
        "random_seed",
        "attempt_id",
        "runtime_evidence_path",
        "runtime_evidence_sha256",
        "evidence_semantic_sha256",
        "evidence",
    }
)
V034_RUNTIME_EVIDENCE_FIELDS = {
    "PepMLM": frozenset(
        """conda_environment container_image effective_seed model_id model_revision
        model_weights_sha256 requested_seed sampling_strategy seed_control_status
        source_commit source_entrypoint_sha256 top_k""".split()
    ),
    "DiffPepBuilder": frozenset(
        """conda_environment container_image effective_seed filtered_receptor_sha256
        model_asset_sha256 requested_seed seed_control_status source_candidate_path
        source_commit source_entrypoint_sha256 target_context_chain target_context_mode
        target_context_path target_context_sha256""".split()
    ),
    "D-Flow / PeptideDesign": frozenset(
        """candidate_path candidate_sha256 checkpoint_path checkpoint_resolved_path
        checkpoint_sha256 containerized effective_seed execution_environment_declared
        execution_environment_type host_environment_path method python_base_prefix
        python_executable_path python_executable_realpath python_executable_sha256
        python_invocation_path python_prefix python_version requested_seed
        seed_control_status seed_patch_path seed_patch_sha256 source_checkout_path
        source_commit source_content_manifest_path source_content_manifest_sha256
        source_copy_mode source_entrypoint_patched_sha256 source_entrypoint_path
        source_entrypoint_prepatch_sha256 source_git_tracked_paths_clean
        source_tracked_file_count target_context_chain target_context_mode
        target_context_path target_context_sha256 x_mirror_applied""".split()
    ),
    "PepMirror": frozenset(
        """checkpoint_container_binding_verified checkpoint_container_path
        checkpoint_mount_mode checkpoint_path checkpoint_pin_verified
        checkpoint_revision checkpoint_sha256 checkpoint_verified_pre_run
        compose_config_command compose_config_output_sha256 compose_file_path
        compose_file_sha256 compose_file_verified_pre_run compose_image_tag
        compose_profile compose_service compose_service_verified effective_seed
        executed_source_manifest_path executed_source_manifest_sha256
        executed_source_manifest_verified_pre_run execution_environment_id
        execution_environment_verified execution_preflight_evidence_path
        execution_preflight_evidence_sha256 generate_py_post_path
        generate_py_post_sha256 generate_py_pre_path generate_py_pre_sha256
        image_id_observed_at_prepare image_id_observed_pre_run
        image_identity_stable_pre_run image_inspect_command
        image_inspect_execution_command image_inspect_execution_output_sha256
        image_inspect_execution_stage image_inspect_output_sha256 image_inspect_stage
        image_repo_tags_observed_at_prepare method mirror_commands_in_pinned_container
        mirror_input_path mirror_input_sha256 mirror_output_path mirror_output_sha256
        mirror_pdb_py_post_path mirror_pdb_py_post_sha256 mirror_pdb_py_pre_path
        mirror_pdb_py_pre_sha256 mirror_roundtrip_applied
        mirror_runtime_conda_environment mirror_runtime_scope mirrored_generated_path
        mirrored_generated_sha256 mirrored_target_path mirrored_target_sha256
        package_evidence_path package_evidence_sha256 provenance_capture_stage
        requested_seed seed_control_status seed_patch_path seed_patch_sha256
        source_commit_command source_commit_expected source_commit_observed
        source_commit_verified source_git_checkout_clean source_git_paths
        source_git_paths_clean source_root source_status_command
        source_tracked_file_count target_input_verified_pre_run target_pdb_path
        target_pdb_sha256 target_preflight_verified""".split()
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        """alphafold_model_name alphafold_params_sha256 candidate_path candidate_sha256
        container_image container_image_id cyclic_offset_applied cyclic_offset_type
        effective_seed requested_seed seed_control_status source_commit
        source_notebook_sha256 terminal_offset""".split()
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        """effective_seed mpnn_checkpoint_sha256 mpnn_container_image
        mpnn_container_image_id mpnn_designed_chain mpnn_fasta_path mpnn_fasta_sha256
        mpnn_fixed_chains mpnn_record_type mpnn_seed mpnn_selected_record_id
        mpnn_source_commit mpnn_source_entrypoint_sha256 requested_seed
        rf_backbone_path rf_backbone_sha256 rf_checkpoint_sha256 rf_container_image
        rf_container_image_id rf_contig rf_cyclic rf_design_startnum rf_deterministic
        rf_hotspots rf_source_commit rf_source_entrypoint_sha256 rf_target_conditioned
        rf_trb_path rf_trb_semantic_extract rf_trb_semantic_parser
        rf_trb_semantic_sha256 rf_trb_sha256 seed_control_status
        sequence_representation sequence_threaded_onto_backbone
        structure_representation""".split()
    ),
}
V034_RUNTIME_INT_FIELDS = {
    "PepMLM": frozenset({"requested_seed", "effective_seed", "top_k"}),
    "DiffPepBuilder": frozenset({"requested_seed", "effective_seed"}),
    "D-Flow / PeptideDesign": frozenset(
        {"requested_seed", "effective_seed", "source_tracked_file_count"}
    ),
    "PepMirror": frozenset(
        {"requested_seed", "effective_seed", "source_tracked_file_count"}
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        {"requested_seed", "effective_seed", "cyclic_offset_type", "terminal_offset"}
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {"requested_seed", "effective_seed", "rf_design_startnum", "mpnn_seed"}
    ),
}
V034_RUNTIME_BOOL_FIELDS = {
    "D-Flow / PeptideDesign": frozenset(
        {"containerized", "source_git_tracked_paths_clean", "x_mirror_applied"}
    ),
    "PepMirror": frozenset(
        """checkpoint_container_binding_verified checkpoint_pin_verified
        checkpoint_verified_pre_run compose_file_verified_pre_run
        compose_service_verified executed_source_manifest_verified_pre_run
        execution_environment_verified image_identity_stable_pre_run
        mirror_commands_in_pinned_container mirror_roundtrip_applied
        source_commit_verified source_git_checkout_clean source_git_paths_clean
        target_input_verified_pre_run target_preflight_verified""".split()
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        {"cyclic_offset_applied"}
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {
            "rf_cyclic",
            "rf_deterministic",
            "rf_target_conditioned",
            "sequence_threaded_onto_backbone",
        }
    ),
}
V034_RUNTIME_LIST_FIELDS = {
    "PepMirror": frozenset(
        {
            "compose_config_command",
            "image_inspect_command",
            "image_inspect_execution_command",
            "image_repo_tags_observed_at_prepare",
            "source_commit_command",
            "source_git_paths",
            "source_status_command",
        }
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {"mpnn_fixed_chains", "rf_hotspots"}
    ),
}
V034_DIFFPEPBUILDER_MODEL_ASSET_FIELDS = frozenset(
    {
        "diffpepbuilder_v1.pth",
        "esm2_t33_650M_UR50D.pt",
        "esm2_t33_650M_UR50D-contact-regression.pt",
    }
)
V034_RF_TRB_FIELDS = frozenset(
    {
        "input_pdb",
        "contigs",
        "cyclic",
        "design_startnum",
        "deterministic",
        "hotspot_res",
        "num_designs",
        "sampled_mask",
    }
)
V034_REPLAY_FILES = {
    "PepMLM": ("raw/pepmlm_generated.csv",),
    "DiffPepBuilder": (
        "raw/diffpepbuilder_candidate.pdb",
        "raw/diffpepbuilder_target_context.pdb",
    ),
    "D-Flow / PeptideDesign": (
        "raw/dflow_candidate.pdb",
        "raw/dflow_target_context.pdb",
    ),
    "PepMirror": (
        "raw/mirror_input.pdb",
        "raw/mirrored_target.pdb",
        "raw/mirrored_generated.pdb",
        "raw/pepmirror_candidate.pdb",
    ),
    "AfCycDesign / ColabDesign cyclic peptide": (
        "raw/afcycdesign_candidate.pdb",
    ),
    "RFdiffusion + ProteinMPNN": (
        "raw/rf/design.pdb",
        "raw/rf/design.trb",
        "raw/mpnn/design.fa",
    ),
}
V034_RUNTIME_PATHS = {
    "PepMLM": "raw/runtime_evidence.json",
    "DiffPepBuilder": "raw/runtime_evidence.json",
    "PepGLAD": "raw/runtime_evidence.json",
    "D-Flow / PeptideDesign": "runtime_evidence.json",
    "PepMirror": "runtime_evidence.json",
    "AfCycDesign / ColabDesign cyclic peptide": "raw/runtime_evidence.json",
    "RFdiffusion + ProteinMPNN": "raw/runtime_evidence.json",
}
V034_METHOD_SLUGS = {
    "PepMLM": "pepmlm",
    "DiffPepBuilder": "diffpepbuilder",
    "PepGLAD": "pepglad",
    "D-Flow / PeptideDesign": "dflow",
    "PepMirror": "pepmirror",
    "AfCycDesign / ColabDesign cyclic peptide": "colabdesign",
    "RFdiffusion + ProteinMPNN": "rfdiffusion_proteinmpnn",
}
V034_FIXED_IDENTITY_CONTRACTS = {
    "PepMLM": {
        "manifest": {
            "source_commit": "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
            "model_revision": "898fca941a9057aebdd1a6164b5ee09a1a71780e",
            "environment_id": "pd-benchmark-methods-gpu:0.21/bench-pepmlm",
        },
        "source": {
            "source_commit": "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
            "source_entrypoint_sha256": (
                "2c1844028c459e8e96d756da795b620b4ccaa65b98dd62c6f904100f0dc1e49b"
            ),
        },
        "model": {
            "model_id": "TianlaiChen/PepMLM-650M",
            "model_revision": "898fca941a9057aebdd1a6164b5ee09a1a71780e",
            "model_weights_sha256": (
                "8a3225bca1f9acd9f701ca2e46597c12bab92320e32b68f380ddf3b6d3b20770"
            ),
        },
        "environment": {
            "container_image": "pd-benchmark-methods-gpu:0.21",
            "conda_environment": "bench-pepmlm",
        },
    },
    "DiffPepBuilder": {
        "manifest": {
            "source_commit": "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
            "model_revision": "diffpepbuilder_v1.pth_external_manifest_v0.20",
            "environment_id": (
                "pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder"
            ),
        },
        "source": {
            "source_commit": "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
            "source_entrypoint_sha256": (
                "872868f48e3cf66f0ce159ada589ca2126a3b2ba98470ab3bbcb9ffc4481f7c6"
            ),
        },
        "model": {
            "model_asset_sha256": {
                "diffpepbuilder_v1.pth": (
                    "dbc4283257d27e38a1ce90c9344063b046ab7161745ebed1fd98a4b0439b992a"
                ),
                "esm2_t33_650M_UR50D.pt": (
                    "ea9d0522b335a8778dea6535a65301f10208dece28cd5865482b0b1fc446168c"
                ),
                "esm2_t33_650M_UR50D-contact-regression.pt": (
                    "8ffe6edbd4173dc8d45c2cd5cb27d43aad77ec26b4c768200c58ae1f96693575"
                ),
            }
        },
        "environment": {
            "container_image": "pd-pyrosetta-methods-gpu:0.20",
            "conda_environment": "bench-diffpepbuilder",
        },
    },
    "PepGLAD": {
        "manifest": {
            "source_commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
            "model_revision": "codesign.ckpt_external_manifest_v0.21",
            "environment_id": "pd-benchmark-methods-gpu:0.21/bench-pepglad",
        },
        "source": {
            "source_commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
            "source_entrypoint_sha256": (
                "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
            ),
            "source_entrypoint_prepatch_sha256": (
                "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
            ),
            "source_entrypoint_instrumented_sha256": (
                "c3b127e39be1b335ff6046bb2435451acfc1b323839377033bf438ccd4a32954"
            ),
            "observer_source_sha256": (
                "a0a98420dd2fd5382479abe77526fb8fc206ffb1e69a8780912fb821dded0c61"
            ),
            "observer_patch_sha256": (
                "cd9ec19f6605fd2b067824d4e02971b3a203e827b6398a4ffd1c68c64464311a"
            ),
            "seed_wrapper_sha256": (
                "6a9b4c9012205d27526e13dbccbd7d11c010eddc3c85acdb2796c2fa6668aaba"
            ),
        },
        "model": {
            "model_weights_sha256": (
                "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
            )
        },
        "environment": {
            "container_image": "pd-benchmark-methods-gpu:0.21",
            "conda_environment": "bench-pepglad",
        },
    },
    "D-Flow / PeptideDesign": {
        "manifest": {
            "source_commit": "3e3e9f501ee16db318e9bf52643513636a07699a",
            "model_revision": (
                "sha256:95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17"
            ),
            "environment_id": "host:.venv/dflow-v023",
        },
        "source": {
            "source_commit": "3e3e9f501ee16db318e9bf52643513636a07699a",
            "source_entrypoint_prepatch_sha256": (
                "6be8b50b876cc94c8a212165d7327bd46c0e906d2c85fc6c2b03a66ff9e2cd9d"
            ),
            "source_entrypoint_patched_sha256": (
                "e55db330d920d0c189a5f539ede4344219177430619228418062d0c4b4e73cad"
            ),
            "seed_patch_sha256": (
                "e55db330d920d0c189a5f539ede4344219177430619228418062d0c4b4e73cad"
            ),
            "source_content_manifest_sha256": (
                "93c91653d2184354015432316ad111e434ff6893cc5509b1cc7654c8cd841b34"
            ),
            "source_git_tracked_paths_clean": True,
            "source_tracked_file_count": 141,
        },
        "model": {
            "checkpoint_sha256": (
                "95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17"
            )
        },
        "environment": {
            "execution_environment_declared": "host:.venv/dflow-v023",
            "execution_environment_type": "host_local_python_environment",
            "containerized": False,
            "python_executable_sha256": (
                "b1220424db191e57100891b277192f24cbae078324ffdf2242c68ce526590c3d"
            ),
        },
    },
    "PepMirror": {
        "manifest": {
            "source_commit": "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            "model_revision": (
                "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"
            ),
            "environment_id": (
                "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror"
            ),
        },
        "source": {
            "source_commit_expected": "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            "source_commit_observed": "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            "generate_py_pre_sha256": (
                "452ba18b29d9647785a2a4160fcaacd97e3769af4b58e5c532fb6b3394881459"
            ),
            "generate_py_post_sha256": (
                "32cb77ec34c9f10b2223c0bb19ef09e7fad3c7d9c2c0798a5ff9e72a699e5ecb"
            ),
            "seed_patch_sha256": (
                "32cb77ec34c9f10b2223c0bb19ef09e7fad3c7d9c2c0798a5ff9e72a699e5ecb"
            ),
            "mirror_pdb_py_pre_sha256": (
                "d8438835c3c26fbf3a1971c577be037e3bfe7114338d0c6e1fb32a2a4a11a233"
            ),
            "mirror_pdb_py_post_sha256": (
                "d8438835c3c26fbf3a1971c577be037e3bfe7114338d0c6e1fb32a2a4a11a233"
            ),
        },
        "model": {
            "checkpoint_revision": (
                "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"
            ),
            "checkpoint_sha256": (
                "a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2"
            ),
        },
        "environment": {
            "compose_image_tag": "pd-pyrosetta-methods-gpu:0.21",
            "compose_file_sha256": (
                "e3a9e6e2b67d6eb13635238bf50aa519a30b70febc8cced57276c77b26831b5d"
            ),
            "compose_config_output_sha256": (
                "01c739107786aa12af5c38813fe3b578835658fef5aef51fb12c6f078e48c6f1"
            ),
            "image_id_observed_at_prepare": (
                "sha256:6b0dd1b775ad1e3e91c618f4ab245db88d9964b20faa2331f4fe9870496d2992"
            ),
            "image_id_observed_pre_run": (
                "sha256:6b0dd1b775ad1e3e91c618f4ab245db88d9964b20faa2331f4fe9870496d2992"
            ),
            "image_inspect_output_sha256": (
                "0a6541eb1bb07831e3baad628ab06db49c0c2e31c0e792ed1a49f675dfbb00bf"
            ),
            "image_inspect_execution_output_sha256": (
                "0a6541eb1bb07831e3baad628ab06db49c0c2e31c0e792ed1a49f675dfbb00bf"
            ),
            "execution_environment_id": (
                "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror"
            ),
            "mirror_runtime_conda_environment": "bench-pepmirror",
        },
    },
    "AfCycDesign / ColabDesign cyclic peptide": {
        "manifest": {
            "source_commit": "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
            "model_revision": (
                "alphafold_model_1_ptm@sha256:"
                "5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84"
            ),
            "environment_id": "pd-benchmark-methods-gpu:0.21/bench-colabdesign",
        },
        "source": {
            "source_commit": "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
            "source_notebook_sha256": (
                "ca3bd3cc14daa95e1529fd2d5c1ca18263d12341a75d2967715ec23720b129ed"
            ),
        },
        "model": {
            "alphafold_model_name": "model_1_ptm",
            "alphafold_params_sha256": (
                "5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84"
            ),
        },
        "environment": {
            "container_image": "pd-benchmark-methods-gpu:0.21",
            "container_image_id": (
                "sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2"
            ),
        },
    },
    "RFdiffusion + ProteinMPNN": {
        "manifest": {
            "source_commit": (
                "RFdiffusion@2d0c003df46b9db41d119321f15403dec3716cd9;"
                "ProteinMPNN@8907e6671bfbfc92303b5f79c4b5e6ce47cdef57"
            ),
            "model_revision": "RFdiffusion_external_models;proteinmpnn_v_48_020.pt",
            "environment_id": "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest",
        },
        "source": {
            "rf_source_commit": "2d0c003df46b9db41d119321f15403dec3716cd9",
            "rf_source_entrypoint_sha256": (
                "a22624d7d40d3d207d91e92163441da5a778c867ed6ea85aa546cc9fdbeb2105"
            ),
            "mpnn_source_commit": "8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
            "mpnn_source_entrypoint_sha256": (
                "61f2c519a7f73fa12da9eb90da97b97ec2f8d5f31d42605639c7600cbd321cbe"
            ),
        },
        "model": {
            "rf_checkpoint_sha256": (
                "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc"
            ),
            "mpnn_checkpoint_sha256": (
                "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd"
            ),
        },
        "environment": {
            "rf_container_image": "pd-rfpeptide-gpu:fixed",
            "rf_container_image_id": (
                "sha256:95e2a19e4adf4b6e8bcdd1777b609bf717472a91643dc92f0ce6aaffbc5219f1"
            ),
            "mpnn_container_image": "pd-foundry-gpu:latest",
            "mpnn_container_image_id": (
                "sha256:23f8612f4537f90078d54a5ac9669df7a6d5f436a48740e5d2884cfe856a5be4"
            ),
        },
    },
}

REQUIRED_FILES = [
    "AGENTS.md",
    "harness/contracts/project_acceptance_v1.json",
    "harness/registry/artifacts_v1.json",
    "harness/registry/claims_v1.json",
    "harness/registry/migration_parity_v1.json",
    "harness/policies/legacy_agents_v1.md",
    "harness/signoffs/README.md",
    "harness/signoffs/signoff.schema.json",
    "index.md",
    "docs/assets/readme/pep_design_icon_v1.png",
    "docs/assets/readme/pep_design_homepage_workflow_v1.png",
    "docs/assets/readme/readme_imagegen_record_v1.md",
    "ops/log.md",
    "ops/plans/harness_engineering_plan_v1.0.md",
    "scripts/run_project_acceptance.py",
    "scripts/parse_batch_a_replay_fixtures.py",
    "scripts/collect_v019_method_smokes.py",
    "scripts/collect_v020_method_unblock_smokes.py",
    "scripts/collect_v021_adapter_smokes.py",
    "scripts/parse_v021_adapter_outputs.py",
    "scripts/prepare_dflow_input_contract.py",
    "scripts/prepare_colabdesign_cli_adapter.py",
    "scripts/audit_dexdesign_route.py",
    "scripts/classify_bindcraft_outputs.py",
    "scripts/run_colabdesign_bounded_generation.py",
    "scripts/prepare_dexdesign_minimal_fixture.py",
    "scripts/parse_bindcraft_accepted_outputs.py",
    "scripts/run_v031_wave_a_pilot.py",
    "scripts/parse_v031_pilot_outputs.py",
    "scripts/run_v033_wave_a_pilot.py",
    "scripts/parse_v033_pilot_outputs.py",
    "scripts/run_v034_wave_a_generation.py",
    "scripts/parse_v034_generation_outputs.py",
    "scripts/v034_adapters/__init__.py",
    "scripts/v034_adapters/common.py",
    "scripts/v034_adapters/pepmlm.py",
    "scripts/v034_adapters/diffpepbuilder.py",
    "scripts/v034_adapters/pepglad.py",
    "scripts/v034_adapters/dflow.py",
    "scripts/v034_adapters/pepmirror.py",
    "scripts/v034_adapters/colabdesign.py",
    "scripts/v034_adapters/rfdiffusion_mpnn.py",
    "tests/test_v034_wave_a_generation.py",
    "tests/test_v034_runner.py",
    "tests/test_v034_merge.py",
    "tests/test_v034_adapters_linear.py",
    "tests/test_v034_adapters_chiral.py",
    "tests/test_v034_adapters_topology.py",
    "tests/test_v034_validator.py",
    "benchmark/README.md",
    "benchmark/availability/README.md",
    "benchmark/availability/link_availability_matrix_v0.5.csv",
    "benchmark/availability/data_access_manifest_v0.5.csv",
    "benchmark/protocols/benchmark_protocol_v0.md",
    "benchmark/protocols/run_csv_schema.md",
    "benchmark/protocols/scoring_outputs_schema.md",
    "benchmark/protocols/job_manifest_schema_v0.11.md",
    "benchmark/protocols/adapter_output_schema_v0.11.md",
    "benchmark/protocols/adapter_replay_contract_v0.16.md",
    "benchmark/scoring/scoring_protocol_v0.md",
    "benchmark/smoke_tests/README.md",
    "benchmark/input_sets/README.md",
    "benchmark/input_sets/candidate_benchmark_datasets.csv",
    "benchmark/input_sets/dataset_readiness_scorecard.csv",
    "benchmark/input_sets/target_candidate_matrix_v0.4.csv",
    "benchmark/input_sets/target_candidate_matrix_v0.5.csv",
    "benchmark/input_sets/target_candidate_academic_search_v0.14.csv",
    "benchmark/input_sets/batch_b_target_review_queue_v0.16.csv",
    "benchmark/input_sets/batch_b_pilot_target_gate_v0.17.csv",
    "benchmark/input_sets/batch_b_pilot_job_manifest_v0.17.csv",
    "benchmark/input_sets/multi_case_fixture_target_manifest_v0.22.csv",
    "benchmark/input_sets/multi_case_fixture_control_manifest_v0.22.csv",
    "benchmark/input_sets/multi_case_fixture_job_manifest_v0.22.csv",
    "benchmark/input_sets/pilot_benchmark_target_manifest_v0.30.csv",
    "benchmark/input_sets/pilot_benchmark_control_manifest_v0.30.csv",
    "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv",
    "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv",
    "benchmark/input_sets/wet_lab_candidate_panel_v0.30.csv",
    "benchmark/input_sets/dataset_supplement_watchlist_v0.6.csv",
    "benchmark/input_sets/dataset_supplement_schema_review_v0.7.csv",
    "benchmark/input_sets/dataset_supplement_schema_review_v0.8.csv",
    "benchmark/input_sets/example_run.csv",
    "benchmark/input_sets/example_job_manifest_v0.11.csv",
    "benchmark/input_sets/target_set_v0.csv",
    "benchmark/input_sets/target_set_v0_schema.md",
    "benchmark/input_sets/target_control_freeze_checklist_v0.10.md",
    "benchmark/input_sets/negative_design_panel_schema.md",
    "benchmark/method_sources/README.md",
    "benchmark/method_sources/method_source_manifest.csv",
    "benchmark/method_sources/method_homepage_source_map_v0.35.csv",
    "benchmark/method_sources/source_pin_audit_v0.4.csv",
    "benchmark/method_sources/source_pin_audit_v0.5.csv",
    "benchmark/method_sources/method_paper_case_matrix_v0.14.csv",
    "benchmark/deployment/server_readiness_checklist_v0.5.md",
    "benchmark/deployment/server_smoke_test_contract_v0.6.md",
    "benchmark/deployment/download_manifest_template_v0.7.csv",
    "benchmark/deployment/download_manifest_v0.8.csv",
    "benchmark/deployment/preflight_download_approval_v0.10.csv",
    "benchmark/deployment/source_freshness_manifest_v0.11.csv",
    "benchmark/deployment/source_clone_manifest_v0.12.csv",
    "benchmark/deployment/docker_image_inventory_v0.13.csv",
    "benchmark/deployment/method_environment_assignment_v0.13.csv",
    "benchmark/deployment/run_preflight_results_v0.15.csv",
    "benchmark/deployment/batch_a_smoke_test_results_v0.15.csv",
    "benchmark/deployment/adapter_parser_hardening_matrix_v0.16.csv",
    "benchmark/deployment/batch_b_pilot_method_scope_v0.17.csv",
    "benchmark/deployment/adapter_replay_fixture_manifest_v0.18.csv",
    "benchmark/deployment/method_source_doc_verification_v0.19.csv",
    "benchmark/deployment/method_install_smoke_manifest_v0.19.csv",
    "benchmark/deployment/method_smoke_test_results_v0.19.csv",
    "benchmark/deployment/method_unblock_manifest_v0.20.csv",
    "benchmark/deployment/method_unblock_smoke_results_v0.20.csv",
    "benchmark/deployment/adapter_smoke_manifest_v0.21.csv",
    "benchmark/deployment/adapter_smoke_results_v0.21.csv",
    "benchmark/deployment/blocker_asset_manifest_v0.21.csv",
    "benchmark/deployment/method_example_fixture_evidence_v0.22.csv",
    "benchmark/deployment/priority_gate_review_v0.22.csv",
    "benchmark/deployment/notebook_cli_smoke_manifest_v0.23.csv",
    "benchmark/deployment/dflow_project_install_contract_v0.23.csv",
    "benchmark/deployment/external_dry_run_package_manifest_v0.23.csv",
    "benchmark/deployment/priority_gate_review_v0.23.csv",
    "benchmark/deployment/dflow_input_contract_fixture_v0.24.csv",
    "benchmark/deployment/dflow_full_pepmerge_download_v0.25.csv",
    "benchmark/deployment/dflow_colabdesign_bindcraft_v0.26.csv",
    "benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv",
    "benchmark/deployment/external_asset_rescue_v0.28.csv",
    "benchmark/deployment/bounded_generation_parser_v0.29.csv",
    "benchmark/deployment/pilot_execution_matrix_v0.30.csv",
    "benchmark/deployment/pilot_execution_results_v0.31.csv",
    "benchmark/deployment/pilot_execution_results_v0.33.csv",
    "benchmark/deployment/pilot_execution_matrix_v0.34.csv",
    "benchmark/deployment/pilot_execution_results_v0.34.csv",
    "benchmark/deployment/method_readiness_review_v0.8.csv",
    "benchmark/deployment/method_preflight_status_v0.10.csv",
    "benchmark/deployment/adapter_preflight_status_v0.11.csv",
    "benchmark/deployment/method_contracts/pepmlm_server_contract_v0.7.md",
    "benchmark/deployment/method_contracts/rfdiffusion_proteinmpnn_server_contract_v0.7.md",
    "benchmark/deployment/method_contracts/pepmirror_dependency_contract_v0.7.md",
    "benchmark/deployment/method_contracts/batch_a_adapter_contract_v0.11.md",
    "benchmark/environments/README.md",
    "benchmark/environments/environment_feasibility_matrix.csv",
    "benchmark/results/README.md",
    "benchmark/results/example_method_output_manifest_v0.11.csv",
    "benchmark/results/example_candidate_outputs_v0.11.csv",
    "benchmark/results/batch_a_replay_method_output_manifest_v0.18.csv",
    "benchmark/results/batch_a_replay_candidate_outputs_v0.18.csv",
    "benchmark/results/batch_a_replay_run_v0.18.csv",
    "benchmark/results/adapter_method_output_manifest_v0.21.csv",
    "benchmark/results/adapter_candidate_outputs_v0.21.csv",
    "benchmark/results/adapter_run_rows_v0.21.csv",
    "benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv",
    "benchmark/results/bindcraft_wrapper_classification_v0.26.csv",
    "benchmark/results/bindcraft_accepted_final_classification_v0.28.csv",
    "benchmark/results/colabdesign_bounded_method_output_manifest_v0.29.csv",
    "benchmark/results/colabdesign_bounded_candidate_outputs_v0.29.csv",
    "benchmark/results/bindcraft_accepted_candidate_outputs_v0.29.csv",
    "benchmark/results/pilot_method_output_manifest_v0.31.csv",
    "benchmark/results/pilot_candidate_outputs_v0.31.csv",
    "benchmark/results/pilot_run_v0.31.csv",
    "benchmark/results/pilot_v031_merge_summary.json",
    "benchmark/results/pilot_method_output_manifest_v0.33.csv",
    "benchmark/results/pilot_candidate_outputs_v0.33.csv",
    "benchmark/results/pilot_run_v0.33.csv",
    "benchmark/results/pilot_v033_merge_summary.json",
    "benchmark/results/pilot_method_output_manifest_v0.34.csv",
    "benchmark/results/pilot_candidate_outputs_v0.34.csv",
    "benchmark/results/pilot_candidate_qc_v0.34.csv",
    "benchmark/results/pilot_run_v0.34.csv",
    "benchmark/results/pilot_v034_merge_summary.json",
    "benchmark/results/pilot_runtime_provenance_v0.34.json",
    "benchmark/results/pilot_failure_diagnostics_v0.34.json",
    "sources/raw_snapshots/_index.md",
    "kb/references/references.bib",
    "kb/references/zotero-map.tsv",
    "kb/references/search_log.md",
    "kb/references/dedupe_report.csv",
    "kb/tables/master_literature_manifest.csv",
    "kb/tables/method_evidence_matrix.csv",
    "kb/tables/candidate_method_scorecard.csv",
    "kb/tables/method_runnability_matrix.csv",
    "kb/tables/benchmark_literature_lessons.csv",
    "kb/tables/expert_review_action_items.csv",
    "kb/tables/ars_review_action_items_v0.6.csv",
    "ops/audits/skill_selection.md",
    "manuscript/support/literature_scope_report.md",
    "manuscript/support/candidate_methods_shortlist.md",
    "ops/audits/method_runnability_audit.md",
    "ops/audits/dataset_candidate_audit.md",
    "ops/audits/method_source_audit.md",
    "ops/audits/environment_feasibility_audit.md",
    "ops/audits/expert_panel_review_v0.4.md",
    "ops/audits/link_and_data_availability_audit_v0.5.md",
    "ops/audits/academic_research_suite_review_v0.6.md",
    "ops/audits/source_code_clone_audit_v0.12.md",
    "ops/audits/docker_environment_assignment_audit_v0.13.md",
    "ops/audits/target_candidate_academic_search_audit_v0.14.md",
    "ops/audits/batch_a_execution_audit_v0.15.md",
    "ops/audits/batch_b_pilot_readiness_audit_v0.17.md",
    "ops/audits/adapter_replay_fixture_audit_v0.18.md",
    "ops/audits/method_install_smoke_audit_v0.19.md",
    "ops/audits/method_unblock_audit_v0.20.md",
    "ops/audits/adapter_smoke_audit_v0.21.md",
    "ops/audits/multi_case_fixture_pilot_audit_v0.22.md",
    "ops/audits/external_dry_run_package_audit_v0.23.md",
    "ops/audits/dflow_input_contract_fixture_audit_v0.24.md",
    "ops/audits/dflow_full_pepmerge_download_audit_v0.25.md",
    "ops/audits/dflow_colabdesign_bindcraft_v0.26.md",
    "ops/audits/colabdesign_dexdesign_gate_v0.27.md",
    "ops/audits/external_asset_rescue_audit_v0.28.md",
    "ops/audits/bounded_generation_parser_audit_v0.29.md",
    "ops/audits/pilot_benchmark_design_audit_v0.30.md",
    "ops/audits/pilot_wave_a_execution_audit_v0.31.md",
    "ops/audits/supervisor_skills_installation_v0.32.md",
    "ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md",
    "ops/audits/v034_bounded_connectivity_audit.md",
    "ops/plans/updated_plan_v0.6.md",
    "ops/plans/updated_plan_v0.9.md",
    "ops/plans/updated_plan_v0.33.md",
    "ops/plans/updated_plan_v0.34.md",
    "ops/plans/updated_plan_v1.3.md",
    "ops/plans/server_preflight_plan_v0.10.md",
    "ops/plans/server_from_scratch_run_plan_v0.10.md",
    "ops/plans/source_io_smoke_test_plan_v0.11.md",
    "ops/plans/protein_design_image_consolidation_plan_v0.13.md",
    "ops/plans/target_candidate_academic_search_plan_v0.14.md",
    "ops/plans/adapter_parser_hardening_plan_v0.16.md",
    "ops/plans/batch_b_pilot_execution_plan_v0.17.md",
    "ops/plans/multi_case_fixture_pilot_plan_v0.22.md",
    "ops/plans/external_dry_run_package_plan_v0.23.md",
    "ops/migration/file_role_map_v0.10.csv",
    "ops/audits/license_schema_input_contract_review_v0.8.md",
    "ops/audits/supervisor_skills_idea_evaluation.md",
    "manuscript/support/benchmark_template_audit.md",
    "manuscript/support/benchmark_intro_logic_chain.md",
    "manuscript/support/review_draft_benchmark_reference_value.md",
    "manuscript/support/review_synthesis_benchmark_framework_supplement.md",
    "ops/audits/grant_style_mock_review_v1.3.md",
    "manuscript/support/benchmark_literature_lessons.md",
    "manuscript/outlines/benchmark_manuscript_outline.md",
    "manuscript/outlines/benchmark_manuscript_outline_zh_v1.md",
    "manuscript/outlines/benchmark_manuscript_outline_en_v1.md",
    "manuscript/assets/figures/benchmark_figure1_overview_v1.png",
    "manuscript/assets/figures/benchmark_figure2_task_method_matrix_v1.png",
    "manuscript/assets/figures/benchmark_figure3_dual_track_v1.png",
    "manuscript/assets/figures/benchmark_figure4_scoring_architecture_v1.png",
    "manuscript/assets/figures/imagegen_prompt_record_v1.md",
    "manuscript/assets/figures/manuscript_figure_imagegen_qc_v2.md",
    "manuscript/support/benchmark_manuscript_sync_map_v1.csv",
    "manuscript/support/benchmark_test_design_v1.md",
    "manuscript/support/benchmark_reference_bibliography_v1.md",
    "manuscript/support/benchmark_manuscript_todo_v1.csv",
    "manuscript/support/benchmark_manuscript_claim_evidence_map.csv",
    "manuscript/support/benchmark_manuscript_figure_table_plan.md",
    "manuscript/support/supplementary_materials_reference_value_v1.1.md",
    "manuscript/support/short_peptide_scoring_rationale_v1.1.md",
    "manuscript/support/cyclic_peptide_benchmark_supplement_v1.1.md",
    "kb/tables/candidate_method_classification_v1.csv",
    "kb/tables/supplementary_materials_action_matrix_v1.1.csv",
    "kb/tables/scoring_metric_rationale_matrix_v1.1.csv",
    "kb/tables/method_landscape_patch_candidates_v1.1.csv",
    "kb/tables/grant_review_action_items_v1.3.csv",
    "benchmark/input_sets/reference_dataset_sources_v1.csv",
    "benchmark/method_sources/method_landscape_watchlist_v0.9.csv",
    "kb/wiki/literature/_index.md",
    "kb/wiki/methods/_index.md",
    "kb/wiki/concepts/_index.md",
    "kb/wiki/benchmark_candidates/_index.md",
    "tests/test_v030_pilot_benchmark_design.py",
    "tests/test_v031_wave_a_pilot.py",
    "tests/test_v032_supervisor_skills_memory.py",
    "tests/test_v033_wave_a_adapter_completion.py",
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
    "job_manifest.csv",
    "method_output_manifest.csv",
    "candidate_outputs.csv",
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
    "sources/raw_snapshots/zotero/seed_items_by_collection.json",
}

RUNTIME_MARKDOWN_SKIP_DIRS = {
    ".venv",
    "benchmark_runs",
    "data",
    "logs",
    "method_sources",
    "weights",
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


def check_homepage_method_sources(errors: list[str]) -> int:
    rel = "benchmark/method_sources/method_homepage_source_map_v0.35.csv"
    rows = check_headers(errors, rel, HOMEPAGE_METHOD_SOURCE_HEADERS)
    by_method: dict[str, dict[str, str]] = {}
    for row in rows:
        method = row.get("method", "")
        if not method:
            errors.append(
                "method_homepage_source_map_v0.35.csv row missing method"
            )
            continue
        if method in by_method:
            errors.append(
                "method_homepage_source_map_v0.35.csv duplicate method: "
                + method
            )
        by_method[method] = row

    missing = sorted(HOMEPAGE_INCLUDED_METHODS - set(by_method))
    if missing:
        errors.append(
            "method_homepage_source_map_v0.35.csv missing included methods: "
            + ", ".join(missing)
        )
    unexpected = sorted(set(by_method) - HOMEPAGE_INCLUDED_METHODS)
    if unexpected:
        errors.append(
            "method_homepage_source_map_v0.35.csv has unexpected methods: "
            + ", ".join(unexpected)
        )

    for method, row in by_method.items():
        for field in (
            "method_family",
            "input_contract",
            "output_contract",
            "publication_title",
            "persistent_id",
            "publication_status",
        ):
            if not row.get(field):
                errors.append(
                    f"{method}: homepage source map missing {field}"
                )

        task_id = row.get("task_id", "")
        if task_id not in REQUIRED_PROTOCOL_TASKS:
            errors.append(
                f"{method}: homepage source map has invalid task_id {task_id}"
            )

        repo_urls = [
            value.strip()
            for value in row.get("repo_url", "").split(";")
            if value.strip()
        ]
        if not repo_urls or any(
            not value.startswith("https://github.com/")
            for value in repo_urls
        ):
            errors.append(
                f"{method}: homepage source map repo_url must use GitHub HTTPS routes"
            )

        pins = [
            value.strip()
            for value in row.get("pinned_commit", "").split(";")
            if value.strip()
        ]
        if not pins:
            errors.append(
                f"{method}: homepage source map missing pinned_commit"
            )
        elif any(not re.fullmatch(r"[0-9a-f]{40}", value) for value in pins):
            errors.append(
                f"{method}: homepage source map pinned_commit must use 40-character lowercase Git SHAs"
            )

        publication_urls = [
            value.strip()
            for value in row.get("publication_url", "").split(";")
            if value.strip()
        ]
        if not publication_urls or any(
            not value.startswith("https://") for value in publication_urls
        ):
            errors.append(
                f"{method}: homepage source map publication_url must use HTTPS"
            )

        verified_on = row.get("verified_on", "")
        try:
            datetime.strptime(verified_on, "%Y-%m-%d")
        except ValueError:
            errors.append(
                f"{method}: homepage source map verified_on must be YYYY-MM-DD"
            )

        if row.get("evidence_boundary") != HOMEPAGE_SOURCE_BOUNDARY:
            errors.append(
                f"{method}: homepage source map has invalid evidence_boundary"
            )

    return len(rows)


def _v034_rows_by_job(
    errors: list[str], artifact_name: str, rows: list[dict[str, str]]
) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        job_id = row.get("job_id", "")
        if not job_id:
            errors.append(f"{artifact_name}: row missing job_id")
            continue
        if job_id in indexed:
            errors.append(f"{artifact_name}: duplicate job_id {job_id}")
        indexed[job_id] = row
    return indexed


def _v034_unique_json_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _v034_json_object(
    errors: list[str], path: Path, artifact_name: str
) -> dict[str, object]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_v034_unique_json_object,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"{artifact_name} is not valid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{artifact_name} must contain a JSON object")
        return {}
    return value


def _v034_validate_exact_json_contract(
    errors: list[str],
    artifact_name: str,
    observed: object,
    expected: object,
    path: str = "",
) -> None:
    location = f"{artifact_name} {path}".strip()
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            errors.append(f"{location} must be a JSON object")
            return
        expected_keys = set(expected)
        observed_keys = set(observed)
        if observed_keys != expected_keys:
            errors.append(
                f"{location} keys mismatch; "
                f"missing={sorted(expected_keys - observed_keys)}, "
                f"extra={sorted(observed_keys - expected_keys)}"
            )
        for key, expected_value in expected.items():
            if key in observed:
                child_path = f"{path}.{key}" if path else key
                _v034_validate_exact_json_contract(
                    errors,
                    artifact_name,
                    observed[key],
                    expected_value,
                    child_path,
                )
        return
    if isinstance(expected, list):
        if not isinstance(observed, list):
            errors.append(f"{location} must be a JSON array")
            return
        if len(observed) != len(expected):
            item_label = "item" if len(expected) == 1 else "items"
            errors.append(
                f"{location} must contain exactly {len(expected)} {item_label}"
            )
            return
        for index, expected_value in enumerate(expected):
            _v034_validate_exact_json_contract(
                errors,
                artifact_name,
                observed[index],
                expected_value,
                f"{path}[{index}]",
            )
        return
    if type(observed) is not type(expected) or observed != expected:
        errors.append(f"{location} must be {expected!r}")


def _v034_runtime_value_is_finite(value: object) -> bool:
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _v034_runtime_value_is_finite(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return all(_v034_runtime_value_is_finite(item) for item in value)
    return True


def _v034_string_list(value: object) -> bool:
    return isinstance(value, list) and all(type(item) is str for item in value)


def _v034_runtime_evidence_exact_schema(
    method: object, evidence: object
) -> bool:
    if type(method) is not str or not isinstance(evidence, dict):
        return False
    expected = V034_RUNTIME_EVIDENCE_FIELDS.get(method)
    if expected is None or set(evidence) != expected:
        return False
    int_fields = V034_RUNTIME_INT_FIELDS.get(method, frozenset())
    bool_fields = V034_RUNTIME_BOOL_FIELDS.get(method, frozenset())
    list_fields = V034_RUNTIME_LIST_FIELDS.get(method, frozenset())
    nested_fields = (
        frozenset({"model_asset_sha256"})
        if method == "DiffPepBuilder"
        else frozenset({"rf_trb_semantic_extract"})
        if method == "RFdiffusion + ProteinMPNN"
        else frozenset()
    )
    if any(type(evidence.get(field)) is not int for field in int_fields):
        return False
    if any(type(evidence.get(field)) is not bool for field in bool_fields):
        return False
    if any(not _v034_string_list(evidence.get(field)) for field in list_fields):
        return False
    string_fields = expected - int_fields - bool_fields - list_fields - nested_fields
    if any(type(evidence.get(field)) is not str for field in string_fields):
        return False
    if method == "DiffPepBuilder":
        assets = evidence.get("model_asset_sha256")
        if not (
            isinstance(assets, dict)
            and set(assets) == V034_DIFFPEPBUILDER_MODEL_ASSET_FIELDS
            and all(
                type(value) is str
                and re.fullmatch(r"[0-9a-f]{64}", value) is not None
                for value in assets.values()
            )
        ):
            return False
    if method == "RFdiffusion + ProteinMPNN":
        semantics = evidence.get("rf_trb_semantic_extract")
        if not (
            isinstance(semantics, dict)
            and set(semantics) == V034_RF_TRB_FIELDS
            and type(semantics.get("input_pdb")) is str
            and _v034_string_list(semantics.get("contigs"))
            and type(semantics.get("cyclic")) is bool
            and type(semantics.get("design_startnum")) is int
            and type(semantics.get("deterministic")) is bool
            and _v034_string_list(semantics.get("hotspot_res"))
            and type(semantics.get("num_designs")) is int
            and _v034_string_list(semantics.get("sampled_mask"))
        ):
            return False
    return _v034_runtime_value_is_finite(evidence)


def _v034_runtime_provenance_exact_schema(provenance: object) -> bool:
    if not isinstance(provenance, dict) or set(provenance) != V034_RUNTIME_PAYLOAD_FIELDS:
        return False
    records = provenance.get("records")
    if not isinstance(records, list):
        return False
    sha256_pattern = re.compile(r"[0-9a-f]{64}")
    for record in records:
        if not isinstance(record, dict) or set(record) != V034_RUNTIME_RECORD_FIELDS:
            return False
        if not all(
            (
                type(record.get("job_id")) is str,
                type(record.get("method")) is str,
                type(record.get("seed_stage")) is str,
                type(record.get("random_seed")) is int,
                type(record.get("attempt_id")) is str,
                type(record.get("runtime_evidence_path")) is str,
                type(record.get("runtime_evidence_sha256")) is str,
                sha256_pattern.fullmatch(record.get("runtime_evidence_sha256", ""))
                is not None,
                type(record.get("evidence_semantic_sha256")) is str,
                sha256_pattern.fullmatch(record.get("evidence_semantic_sha256", ""))
                is not None,
                _v034_runtime_evidence_exact_schema(
                    record.get("method"), record.get("evidence")
                ),
            )
        ):
            return False
    return True


def _v034_attempt_directory(
    job: dict[str, str], execution: dict[str, str]
) -> Path | None:
    method = job.get("method", "")
    slug = V034_METHOD_SLUGS.get(method)
    job_id = job.get("job_id", "")
    attempt_id = execution.get("attempt_id", "")
    path_text = execution.get("attempt_dir", "")
    if (
        slug is None
        or not job_id
        or not attempt_id
        or Path(attempt_id).name != attempt_id
        or not path_text
        or not Path(path_text).is_absolute()
    ):
        return None
    path = Path(path_text)
    code_root = Path(__file__).resolve().parents[1]
    allowed_roots = {
        ROOT / "benchmark_runs/v0.34",
        code_root / "benchmark_runs/v0.34",
    }
    for run_root in allowed_roots:
        expected = run_root / slug / job_id / attempt_id
        try:
            if path != expected or path.is_symlink():
                continue
            resolved_root = run_root.resolve(strict=True)
            resolved = path.resolve(strict=True)
            if resolved != expected.resolve(strict=True) or not resolved.is_dir():
                continue
            current = run_root
            if current.is_symlink():
                continue
            valid = True
            for part in (slug, job_id, attempt_id, "raw"):
                current /= part
                if current.is_symlink():
                    valid = False
                    break
            if valid and current.is_dir():
                return resolved
        except (OSError, RuntimeError, ValueError):
            continue
    return None


def _v034_parse_captured_json(path: Path) -> dict[str, object] | None:
    def reject_constant(value: str) -> object:
        raise ValueError(f"non-finite JSON constant: {value}")

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_v034_unique_json_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _v034_replay_path_matches(
    replay_root: Path, replay_text: str, attempt: Path, compact_text: str
) -> bool:
    if not replay_text or not compact_text:
        return replay_text == compact_text
    try:
        replay_relative = Path(os.path.abspath(replay_text)).relative_to(replay_root)
        compact_path = Path(compact_text)
        compact_absolute = (
            compact_path if compact_path.is_absolute() else attempt / compact_path
        )
        compact_relative = Path(os.path.abspath(compact_absolute)).relative_to(attempt)
    except ValueError:
        return False
    return replay_relative == compact_relative


def _v034_fixed_identity_mismatches(
    job: dict[str, str],
    execution: dict[str, str],
    compact_manifest: dict[str, str],
    compact_provenance: dict[str, object] | None,
) -> set[str]:
    from scripts import parse_v034_generation_outputs as merge

    categories = {"source", "model", "environment"}
    method = job.get("method", "")
    contract = V034_FIXED_IDENTITY_CONTRACTS.get(method)
    attempt = _v034_attempt_directory(job, execution)
    runtime_relative = V034_RUNTIME_PATHS.get(method)
    if contract is None or attempt is None or runtime_relative is None:
        return categories
    runtime_capture = merge._bound_relative_attempt_file(attempt, runtime_relative)
    manifest_capture = merge._bound_relative_attempt_file(
        attempt, "method_output_manifest.csv"
    )
    if runtime_capture is None or manifest_capture is None:
        return categories
    runtime = _v034_parse_captured_json(runtime_capture)
    manifest_rows = merge._strict_csv_rows(manifest_capture)
    if runtime is None or manifest_rows is None or len(manifest_rows) != 1:
        return categories
    attempt_manifest = manifest_rows[0]
    mismatches: set[str] = set()
    manifest_contract = contract["manifest"]
    manifest_fields = {
        "source": "source_commit",
        "model": "model_revision",
        "environment": "environment_id",
    }
    for category in categories:
        expected_runtime = contract[category]
        if not isinstance(expected_runtime, dict) or any(
            runtime.get(field) != expected
            for field, expected in expected_runtime.items()
        ):
            mismatches.add(category)
        manifest_field = manifest_fields[category]
        expected_manifest = manifest_contract[manifest_field]
        if (
            attempt_manifest.get(manifest_field) != expected_manifest
            or compact_manifest.get(manifest_field) != expected_manifest
            or attempt_manifest.get(manifest_field)
            != compact_manifest.get(manifest_field)
        ):
            mismatches.add(category)

    compact_evidence = (
        compact_provenance.get("evidence")
        if isinstance(compact_provenance, dict)
        else None
    )
    if compact_provenance is not None and compact_evidence != runtime:
        mismatches.update(categories)

    derived_manifest: dict[str, str]
    if method == "PepMLM":
        derived_manifest = {
            "source_commit": str(runtime.get("source_commit", "")),
            "model_revision": str(runtime.get("model_revision", "")),
            "environment_id": (
                f"{runtime.get('container_image', '')}/"
                f"{runtime.get('conda_environment', '')}"
            ),
        }
    elif method == "DiffPepBuilder":
        derived_manifest = {
            "source_commit": str(runtime.get("source_commit", "")),
            "model_revision": str(manifest_contract["model_revision"]),
            "environment_id": (
                f"{runtime.get('container_image', '')}/"
                f"{runtime.get('conda_environment', '')}"
            ),
        }
    elif method == "PepGLAD":
        derived_manifest = {
            "source_commit": str(runtime.get("source_commit", "")),
            "model_revision": str(manifest_contract["model_revision"]),
            "environment_id": (
                f"{runtime.get('container_image', '')}/"
                f"{runtime.get('conda_environment', '')}"
            ),
        }
    elif method == "D-Flow / PeptideDesign":
        derived_manifest = {
            "source_commit": str(runtime.get("source_commit", "")),
            "model_revision": f"sha256:{runtime.get('checkpoint_sha256', '')}",
            "environment_id": str(
                runtime.get("execution_environment_declared", "")
            ),
        }
    elif method == "PepMirror":
        derived_manifest = {
            "source_commit": str(runtime.get("source_commit_observed", "")),
            "model_revision": str(runtime.get("checkpoint_revision", "")),
            "environment_id": str(runtime.get("execution_environment_id", "")),
        }
    elif method == "AfCycDesign / ColabDesign cyclic peptide":
        derived_manifest = {
            "source_commit": str(runtime.get("source_commit", "")),
            "model_revision": (
                f"alphafold_{runtime.get('alphafold_model_name', '')}@sha256:"
                f"{runtime.get('alphafold_params_sha256', '')}"
            ),
            "environment_id": (
                f"{runtime.get('container_image', '')}/bench-colabdesign"
            ),
        }
    elif method == "RFdiffusion + ProteinMPNN":
        derived_manifest = {
            "source_commit": (
                f"RFdiffusion@{runtime.get('rf_source_commit', '')};"
                f"ProteinMPNN@{runtime.get('mpnn_source_commit', '')}"
            ),
            "model_revision": str(manifest_contract["model_revision"]),
            "environment_id": (
                f"{runtime.get('rf_container_image', '')} + "
                f"{runtime.get('mpnn_container_image', '')}"
            ),
        }
    else:
        return categories
    for category, manifest_field in manifest_fields.items():
        if derived_manifest[manifest_field] != attempt_manifest.get(manifest_field):
            mismatches.add(category)
    return mismatches


def _v034_stable_raw_replay(
    job: dict[str, str],
    execution: dict[str, str],
    method_row: dict[str, str],
    candidate: dict[str, str],
    qc: dict[str, str],
    run: dict[str, str],
    provenance: dict[str, object],
) -> bool:
    from scripts import parse_v034_generation_outputs as merge
    from scripts.run_v034_wave_a_generation import CANDIDATE_HEADERS, _candidate_row
    from scripts.v034_adapters.common import evaluate_candidate_qc

    attempt = _v034_attempt_directory(job, execution)
    evidence = provenance.get("evidence")
    method = job.get("method", "")
    replay_files = V034_REPLAY_FILES.get(method)
    runtime_relative = V034_RUNTIME_PATHS.get(method)
    if (
        attempt is None
        or not isinstance(evidence, dict)
        or replay_files is None
        or runtime_relative is None
        or provenance.get("runtime_evidence_path") != runtime_relative
    ):
        return False
    store = merge._ACTIVE_CAPTURE_STORE
    if store is None:
        return False
    runtime_capture = merge._bound_relative_attempt_file(
        attempt,
        runtime_relative,
        provenance.get("runtime_evidence_sha256"),
    )
    if runtime_capture is None:
        return False
    raw_evidence = _v034_parse_captured_json(runtime_capture)
    if raw_evidence != evidence:
        return False
    replay = store.root / "validator-replay" / job["job_id"] / attempt.name
    try:
        replay.mkdir(parents=True, exist_ok=False)
        for relative_text in replay_files:
            if merge._copy_captured_relative_file(attempt, replay, relative_text) is None:
                return False
        source = attempt.resolve(strict=True)
        destination = replay.resolve(strict=True)
        if method == "PepMirror":
            replay_evidence = merge._prepare_pepmirror_replay(
                attempt, replay, raw_evidence
            )
            if replay_evidence is None:
                return False
        else:
            rewritten = merge._rewrite_attempt_paths(
                raw_evidence, source, destination
            )
            if not isinstance(rewritten, dict):
                return False
            replay_evidence = rewritten
        merge._write_replay_json(replay / runtime_relative, replay_evidence)

        adapter = importlib.import_module(
            {
                "PepMLM": "scripts.v034_adapters.pepmlm",
                "DiffPepBuilder": "scripts.v034_adapters.diffpepbuilder",
                "D-Flow / PeptideDesign": "scripts.v034_adapters.dflow",
                "PepMirror": "scripts.v034_adapters.pepmirror",
                "AfCycDesign / ColabDesign cyclic peptide": (
                    "scripts.v034_adapters.colabdesign"
                ),
                "RFdiffusion + ProteinMPNN": (
                    "scripts.v034_adapters.rfdiffusion_mpnn"
                ),
            }[method]
        )
        replay_value, replay_runtime = adapter.parse(job, replay)
        replay_candidate = _candidate_row(job, replay_value)
        if set(replay_candidate) != set(CANDIDATE_HEADERS):
            return False
        for field in set(CANDIDATE_HEADERS) - {
            "structure_path",
            "source_output_path",
        }:
            if str(replay_candidate.get(field, "")) != candidate.get(field, ""):
                return False
        for field in ("structure_path", "source_output_path"):
            if not _v034_replay_path_matches(
                destination,
                str(replay_candidate.get(field, "")),
                source,
                candidate.get(field, ""),
            ):
                return False

        normalized_runtime = merge._rewrite_attempt_paths(
            replay_runtime, destination, source
        )
        if not isinstance(normalized_runtime, dict):
            return False
        if method == "PepMirror":
            normalized_runtime["package_evidence_sha256"] = raw_evidence.get(
                "package_evidence_sha256"
            )
            normalized_runtime["execution_preflight_evidence_sha256"] = (
                raw_evidence.get("execution_preflight_evidence_sha256")
            )
        if normalized_runtime != raw_evidence:
            return False

        job_snapshot = dict(job)
        if job.get("target_pdb_path"):
            target = merge._hash_bound_job_target(job)
            if target is None:
                return False
            job_snapshot["target_pdb_path"] = str(target)
        observed_qc = evaluate_candidate_qc(
            job_snapshot, replay_candidate, replay_runtime, replay / "raw"
        )
        expected_qc = {
            field: (
                job["job_id"]
                if field == "job_id"
                else candidate.get("design_id", "")
                if field == "design_id"
                else "yes"
                if field == "supported_candidate"
                else "not_applicable"
                if field
                in {
                    "backbone_to_fasta_handoff_status",
                    "mirror_target_atom_identity_status",
                    "mirror_target_central_inversion_status",
                    "mirror_output_atom_identity_status",
                    "mirror_output_central_inversion_status",
                }
                and field not in observed_qc
                else str(observed_qc.get(field, ""))
            )
            for field in PILOT_CANDIDATE_QC_V034_HEADERS
        }
        if qc != expected_qc:
            return False

        manifest_capture = merge._bound_relative_attempt_file(
            attempt, "method_output_manifest.csv"
        )
        result_capture = merge._bound_relative_attempt_file(attempt, "run_result.json")
        if manifest_capture is None or result_capture is None:
            return False
        manifest_rows = merge._strict_csv_rows(manifest_capture)
        result = _v034_parse_captured_json(result_capture)
        if manifest_rows is None or len(manifest_rows) != 1 or result is None:
            return False
        if manifest_rows[0] != method_row:
            return False

        expected_execution = {
            "execution_id": f"exec_{job['job_id']}",
            "job_id": job["job_id"],
            "method": method,
            "seed_stage": job.get("seed_stage", ""),
            "random_seed": job.get("random_seed", ""),
            "attempt_id": attempt.name,
            "attempt_dir": str(attempt),
            "status": str(result.get("status", "")),
            "overall_qc_status": str(result.get("overall_qc_status", "")),
            "supported_candidate": "yes",
            "merge_status": "supported",
            "status_reason": str(result.get("status_reason", "")),
            "candidate_parse_status": str(result.get("parser_status", "")),
            "qc_status_reason": str(observed_qc.get("status_reason", "")),
            "chirality_evaluable": str(observed_qc.get("chirality_evaluable", "")),
            "chirality_l_count": str(observed_qc.get("chirality_l_count", "")),
            "chirality_d_count": str(observed_qc.get("chirality_d_count", "")),
            "chirality_unknown_count": str(
                observed_qc.get("chirality_unknown_count", "")
            ),
            "method_contract_status": str(
                observed_qc.get("method_contract_status", "")
            ),
            "handoff_status": str(observed_qc.get("handoff_status", "")),
        }
        if execution != expected_execution:
            return False
        expected_run = {
            "design_id": candidate.get("design_id", ""),
            "job_id": job["job_id"],
            "method": method,
            "task_id": job.get("task_id", ""),
            "target_id": job.get("target_id", ""),
            "input_mode": job.get("input_mode", ""),
            "peptide_type": job.get("peptide_type", ""),
            "chirality": job.get("chirality", ""),
            "cyclic": job.get("cyclic", ""),
            "random_seed": job.get("random_seed", ""),
            "seed_stage": job.get("seed_stage", ""),
            "attempt_id": attempt.name,
            "status": str(result.get("status", "")),
            "overall_qc_status": str(result.get("overall_qc_status", "")),
            "supported_candidate": "yes",
            "sequence": candidate.get("sequence", ""),
            "structure_path": candidate.get("structure_path", ""),
            "status_reason": str(result.get("status_reason", "")),
            "notes": (
                "Bounded connectivity evidence only; not scoring, ranking, or "
                "Benchmark result"
            ),
        }
        return run == expected_run
    except (
        csv.Error,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RuntimeError,
        KeyError,
    ):
        return False


_V035_HISTORICAL_NAMES = frozenset(
    {
        "pilot_benchmark_job_manifest_v0.34.csv",
        "pilot_execution_matrix_v0.34.csv",
        "pilot_execution_results_v0.34.csv",
        "pilot_method_output_manifest_v0.34.csv",
        "pilot_candidate_outputs_v0.34.csv",
        "pilot_candidate_qc_v0.34.csv",
        "pilot_run_v0.34.csv",
        "pilot_runtime_provenance_v0.34.json",
        "pilot_failure_diagnostics_v0.34.json",
        "pilot_v034_merge_summary.json",
    }
)
_V035_HISTORICAL_PATHS = (
    "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv",
    "benchmark/deployment/pilot_execution_matrix_v0.34.csv",
    "benchmark/deployment/pilot_execution_results_v0.34.csv",
    "benchmark/results/pilot_method_output_manifest_v0.34.csv",
    "benchmark/results/pilot_candidate_outputs_v0.34.csv",
    "benchmark/results/pilot_candidate_qc_v0.34.csv",
    "benchmark/results/pilot_run_v0.34.csv",
    "benchmark/results/pilot_runtime_provenance_v0.34.json",
    "benchmark/results/pilot_failure_diagnostics_v0.34.json",
    "benchmark/results/pilot_v034_merge_summary.json",
)
_V035_PUBLIC_FILES = frozenset(
    {
        "raw/pepglad_candidate.pdb",
        "raw/pepglad_pre_relax.pdb",
        "raw/pepglad_summary.jsonl",
        "raw/runtime_evidence.json",
        "work/codesign/3EQS_0.pdb",
    }
)
_V035_REPLAY_FILES = _V035_PUBLIC_FILES | frozenset(
    {
        "execution.json",
        "job.json",
        "observer_patch_evidence.json",
        "pepglad_instrument_source.py",
        "pepglad_observer.py",
        "pepglad_seeded_entry.py",
        "run_result.json",
        "work/api/run.py",
    }
)
_V035_RUN_RESULT_FIELDS = frozenset(
    {
        "attempt_dir",
        "created_at",
        "design_id",
        "exit_code",
        "job_id",
        "method",
        "overall_qc_status",
        "parser_status",
        "runtime_seconds",
        "status",
        "status_reason",
    }
)
_V035_BUNDLE_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_boundary",
        "historical_v034_bindings",
        "job",
        "execution",
        "candidate",
        "qc",
        "runtime_provenance",
    }
)
_V035_HISTORICAL_FIELDS = frozenset(
    {"primary_supported", "pepglad_status", "artifacts"}
)
_V035_JOB_FIELDS = frozenset(
    {
        "job_id",
        "method",
        "random_seed",
        "seed_stage",
        "target_sha256",
        "target_chain",
        "binder_chain",
        "length",
        "chirality_constraint",
        "chirality_check_mode",
        "baseline_replay_policy",
    }
)
_V035_EXECUTION_FIELDS = frozenset(
    {"attempt_id", "attempt_dir", "exit_code", "status", "supported_candidate"}
)
_V035_CANDIDATE_FIELDS = frozenset(
    {
        "design_id",
        "sequence",
        "structure_path",
        "file_sha256",
        "binder_chain",
        "parse_status",
        "chirality",
    }
)
_V035_QC_FIELDS = frozenset(
    {
        "observed_chirality_class",
        "chirality_status",
        "chirality_evaluable",
        "chirality_l_count",
        "chirality_d_count",
        "chirality_unknown_count",
        "baseline_replay_status",
        "overall_qc_status",
    }
)
_V035_RUNTIME_FIELDS = frozenset(
    {
        "attempt_id",
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "runtime_evidence_path",
        "runtime_evidence_sha256",
        "runtime_semantic_sha256",
        "baseline_expected_sha256",
        "baseline_observed_sha256",
        "files",
        "producer_bindings",
    }
)
_V035_PRODUCER_FIELDS = frozenset(
    {
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "target_input_sha256",
        "container_image",
        "conda_environment",
        "observer_source_sha256",
        "observer_patch_sha256",
        "seed_wrapper_sha256",
        "source_entrypoint_instrumented_sha256",
    }
)
_V035_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)
_V035_FORBIDDEN_RESULT = re.compile(
    r"(?<![a-z0-9])(?:score|scoring|rank|ranking|leaderboard|"
    r"benchmark[_ -]?result|seed[_ -]?43|best[_ -]?performing)(?![a-z0-9])",
    re.IGNORECASE,
)


def _v035_sha256(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _v035_forbidden_result_content(
    value: object, path: tuple[str, ...] = ()
) -> bool:
    if type(value) is dict:
        return any(
            _V035_FORBIDDEN_RESULT.search(key) is not None
            or _v035_forbidden_result_content(item, path + (key,))
            for key, item in value.items()
        )
    if type(value) is list:
        return any(
            _v035_forbidden_result_content(item, path + (str(index),))
            for index, item in enumerate(value)
        )
    if type(value) is str:
        if (
            path == ("evidence_boundary",)
            and value == "bounded_connectivity_only_not_scoring_or_ranking"
        ):
            return False
        return _V035_FORBIDDEN_RESULT.search(value) is not None
    return False


def _v035_bundle_schema_valid(bundle: object) -> bool:
    if (
        type(bundle) is not dict
        or set(bundle) != _V035_BUNDLE_FIELDS
        or _v035_forbidden_result_content(bundle)
    ):
        return False
    historical = bundle.get("historical_v034_bindings")
    job = bundle.get("job")
    execution = bundle.get("execution")
    candidate = bundle.get("candidate")
    qc = bundle.get("qc")
    runtime = bundle.get("runtime_provenance")
    if not all(
        type(value) is dict
        for value in (historical, job, execution, candidate, qc, runtime)
    ):
        return False
    files = runtime.get("files")
    producer = runtime.get("producer_bindings")
    artifacts = historical.get("artifacts")
    if not all(type(value) is dict for value in (files, producer, artifacts)):
        return False
    if not all(
        (
            set(historical) == _V035_HISTORICAL_FIELDS,
            set(job) == _V035_JOB_FIELDS,
            set(execution) == _V035_EXECUTION_FIELDS,
            set(candidate) == _V035_CANDIDATE_FIELDS,
            set(qc) == _V035_QC_FIELDS,
            set(runtime) == _V035_RUNTIME_FIELDS,
            set(files) == _V035_PUBLIC_FILES,
            set(producer) == _V035_PRODUCER_FIELDS,
            set(artifacts) == _V035_HISTORICAL_NAMES,
            all(_v035_sha256(value) for value in artifacts.values()),
            all(_v035_sha256(value) for value in files.values()),
        )
    ):
        return False
    if not all(
        (
            bundle.get("schema_version") == "v0.35",
            bundle.get("evidence_boundary")
            == "bounded_connectivity_only_not_scoring_or_ranking",
            type(historical.get("primary_supported")) is int,
            historical.get("primary_supported") == 6,
            historical.get("pepglad_status")
            == "historical_failure_not_promoted",
            job.get("job_id") == "v035_pepglad_3eqs_seed42",
            job.get("method") == "PepGLAD",
            type(job.get("random_seed")) is int,
            job.get("random_seed") == 42,
            job.get("seed_stage") == "primary",
            _v035_sha256(job.get("target_sha256")),
            job.get("target_chain") == "A",
            job.get("binder_chain") == "B",
            type(job.get("length")) is int,
            job.get("length") == 11,
            job.get("chirality_constraint") == "unrestricted",
            job.get("chirality_check_mode") == "report_only",
            job.get("baseline_replay_policy") == "warn_on_mismatch",
        )
    ):
        return False
    attempt_dir = execution.get("attempt_dir")
    if not all(
        (
            execution.get("attempt_id") == "attempt_001",
            type(attempt_dir) is str,
            Path(attempt_dir).is_absolute() if type(attempt_dir) is str else False,
            Path(attempt_dir).name == "attempt_001"
            if type(attempt_dir) is str
            else False,
            Path(attempt_dir).parent.name == "v035_pepglad_3eqs_seed42"
            if type(attempt_dir) is str
            else False,
            Path(attempt_dir).parent.parent.name == "pepglad"
            if type(attempt_dir) is str
            else False,
            type(execution.get("exit_code")) is int,
            execution.get("exit_code") == 0,
            execution.get("status") == "passed",
            type(execution.get("supported_candidate")) is bool,
            execution.get("supported_candidate") is True,
        )
    ):
        return False
    sequence = candidate.get("sequence")
    if not all(
        (
            candidate.get("design_id")
            == "v035_pepglad_3eqs_seed42_candidate_1",
            type(sequence) is str,
            re.fullmatch(r"[A-Z]{11}", sequence) is not None
            if type(sequence) is str
            else False,
            candidate.get("structure_path") == "raw/pepglad_candidate.pdb",
            _v035_sha256(candidate.get("file_sha256")),
            candidate.get("binder_chain") == "B",
            candidate.get("parse_status") == "parsed",
            candidate.get("chirality") in {"L", "D", "mixed"},
        )
    ):
        return False
    count_fields = (
        "chirality_evaluable",
        "chirality_l_count",
        "chirality_d_count",
        "chirality_unknown_count",
    )
    if any(type(qc.get(field)) is not int or qc[field] < 0 for field in count_fields):
        return False
    observed = qc.get("observed_chirality_class")
    l_count = qc.get("chirality_l_count")
    d_count = qc.get("chirality_d_count")
    if observed == "mixed":
        class_valid = l_count > 0 and d_count > 0
        chirality_status = "warn"
    elif observed == "L":
        class_valid = l_count == 11 and d_count == 0
        chirality_status = "pass"
    elif observed == "D":
        class_valid = l_count == 0 and d_count == 11
        chirality_status = "pass"
    else:
        return False
    if not all(
        (
            qc.get("chirality_evaluable") == 11,
            l_count + d_count == 11,
            qc.get("chirality_unknown_count") == 0,
            observed == candidate.get("chirality"),
            class_valid,
            qc.get("chirality_status") == chirality_status,
        )
    ):
        return False
    if not all(
        (
            runtime.get("attempt_id") == execution.get("attempt_id"),
            type(runtime.get("requested_seed")) is int,
            runtime.get("requested_seed") == 42,
            type(runtime.get("effective_seed")) is int,
            runtime.get("effective_seed") == 42,
            runtime.get("seed_control_status") == "honored",
            runtime.get("runtime_evidence_path") == "raw/runtime_evidence.json",
            _v035_sha256(runtime.get("runtime_evidence_sha256")),
            _v035_sha256(runtime.get("runtime_semantic_sha256")),
            runtime.get("baseline_expected_sha256") == _V035_BASELINE_SHA256,
            runtime.get("baseline_observed_sha256")
            == candidate.get("file_sha256"),
            files.get("raw/pepglad_candidate.pdb")
            == candidate.get("file_sha256"),
            files.get("work/codesign/3EQS_0.pdb")
            == candidate.get("file_sha256"),
            files.get("raw/runtime_evidence.json")
            == runtime.get("runtime_evidence_sha256"),
            type(producer.get("source_commit")) is str,
            re.fullmatch(r"[0-9a-f]{40}", producer.get("source_commit", ""))
            is not None,
            producer.get("target_input_sha256") == job.get("target_sha256"),
            all(
                _v035_sha256(producer.get(field))
                for field in _V035_PRODUCER_FIELDS
                - {"source_commit", "container_image", "conda_environment"}
            ),
            all(
                type(producer.get(field)) is str and bool(producer.get(field))
                for field in ("container_image", "conda_environment")
            ),
        )
    ):
        return False
    baseline_status = (
        "pass"
        if runtime.get("baseline_observed_sha256") == _V035_BASELINE_SHA256
        else "warn"
    )
    overall_status = (
        "pass_with_warning"
        if "warn" in {chirality_status, baseline_status}
        else "pass"
    )
    return all(
        (
            qc.get("baseline_replay_status") == baseline_status,
            qc.get("overall_qc_status") == overall_status,
        )
    )


def _v035_stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mode,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _v035_directory_identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_mode, value.st_dev, value.st_ino)


def _v035_directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _v035_close_descriptors(descriptors: list[int]) -> None:
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except OSError:
            pass


def _v035_open_directory_chain(
    directory: Path,
) -> tuple[list[int], list[os.stat_result]] | None:
    logical = Path(directory)
    if not logical.is_absolute() or Path(os.path.abspath(logical)) != logical:
        return None
    descriptors: list[int] = []
    identities: list[os.stat_result] = []
    try:
        current = os.open(logical.anchor, _v035_directory_flags())
        descriptors.append(current)
        opened = os.fstat(current)
        if not stat.S_ISDIR(opened.st_mode):
            _v035_close_descriptors(descriptors)
            return None
        identities.append(opened)
        for part in logical.parts[1:]:
            child = os.open(part, _v035_directory_flags(), dir_fd=current)
            descriptors.append(child)
            opened = os.fstat(child)
            if not stat.S_ISDIR(opened.st_mode):
                _v035_close_descriptors(descriptors)
                return None
            identities.append(opened)
            current = child
    except (OSError, ValueError):
        _v035_close_descriptors(descriptors)
        return None
    return descriptors, identities


def _v035_directory_chain_stable(
    directory: Path,
    descriptors: list[int],
    identities: list[os.stat_result],
) -> bool:
    parts = Path(directory).parts
    if len(descriptors) != len(parts) or len(identities) != len(parts):
        return False
    try:
        for descriptor, expected in zip(descriptors, identities):
            current = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(current.st_mode)
                or _v035_directory_identity(current)
                != _v035_directory_identity(expected)
            ):
                return False
        for index, part in enumerate(parts[1:], start=1):
            current = os.stat(
                part,
                dir_fd=descriptors[index - 1],
                follow_symlinks=False,
            )
            if (
                not stat.S_ISDIR(current.st_mode)
                or _v035_directory_identity(current)
                != _v035_directory_identity(identities[index])
            ):
                return False
        current_path = os.lstat(directory)
    except OSError:
        return False
    return (
        stat.S_ISDIR(current_path.st_mode)
        and _v035_directory_identity(current_path)
        == _v035_directory_identity(identities[-1])
    )


def _v035_stable_file(
    path: Path, *, confined_root: Path | None = None
) -> tuple[Path, bytes, str, tuple[int, ...]] | None:
    logical = Path(path)
    if not logical.is_absolute() or Path(os.path.abspath(logical)) != logical:
        return None
    root = Path(confined_root) if confined_root is not None else None
    try:
        if root is not None:
            if not root.is_absolute() or Path(os.path.abspath(root)) != root:
                return None
            logical.relative_to(root)
    except ValueError:
        return None
    opened = _v035_open_directory_chain(logical.parent)
    if opened is None:
        return None
    descriptors, directory_stats = opened
    file_descriptor: int | None = None
    try:
        file_flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        file_descriptor = os.open(
            logical.name,
            file_flags,
            dir_fd=descriptors[-1],
        )
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size <= 0:
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(file_descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(file_descriptor)
        current_file = os.stat(
            logical.name,
            dir_fd=descriptors[-1],
            follow_symlinks=False,
        )
        identity = _v035_stat_identity(before)
        payload = b"".join(chunks)
        if not all(
            (
                identity == _v035_stat_identity(after),
                identity == _v035_stat_identity(current_file),
                len(payload) == before.st_size,
                _v035_directory_chain_stable(
                    logical.parent,
                    descriptors,
                    directory_stats,
                ),
            )
        ):
            return None
        return logical, payload, hashlib.sha256(payload).hexdigest(), identity
    except (OSError, RuntimeError, ValueError):
        return None
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        _v035_close_descriptors(descriptors)


def _v035_strict_json_bytes(payload: bytes) -> dict[str, object] | None:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_v034_unique_json_object,
            parse_constant=reject_constant,
        )
    except (UnicodeError, ValueError):
        return None
    return value if type(value) is dict else None


def _v035_run_result_valid(
    result: object,
    *,
    attempt: Path,
    job: dict[str, object],
    execution: dict[str, object],
    candidate: dict[str, object],
    qc: dict[str, object],
    replay_candidate: dict[str, object],
    replay_qc: dict[str, object],
) -> bool:
    if type(result) is not dict or set(result) != _V035_RUN_RESULT_FIELDS:
        return False
    string_fields = _V035_RUN_RESULT_FIELDS - {"exit_code"}
    if any(type(result.get(field)) is not str for field in string_fields):
        return False
    if type(result.get("exit_code")) is not int:
        return False
    try:
        runtime_seconds = float(result["runtime_seconds"])
        created_at = datetime.fromisoformat(
            result["created_at"].replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return False
    if (
        not math.isfinite(runtime_seconds)
        or runtime_seconds <= 0
        or created_at.tzinfo is None
        or created_at.utcoffset() is None
    ):
        return False
    expected = {
        "attempt_dir": str(attempt),
        "design_id": candidate.get("design_id"),
        "exit_code": execution.get("exit_code"),
        "job_id": job.get("job_id"),
        "method": job.get("method"),
        "overall_qc_status": qc.get("overall_qc_status"),
        "parser_status": candidate.get("parse_status"),
        "status": execution.get("status"),
        "status_reason": "bounded_connectivity_candidate_qc_passed",
    }
    if any(result.get(field) != value for field, value in expected.items()):
        return False
    return all(
        (
            result["design_id"]
            == "v035_pepglad_3eqs_seed42_candidate_1",
            replay_candidate.get("parse_status") == result["parser_status"],
            replay_qc.get("overall_qc_status") == result["overall_qc_status"],
            result["exit_code"] == 0,
            result["status"] == "passed",
            bool(result["status_reason"]),
        )
    )


def _v035_authorized_attempt_is_unique(attempt: Path) -> bool:
    logical = Path(attempt)
    if (
        not logical.is_absolute()
        or Path(os.path.abspath(logical)) != logical
        or logical.name != "attempt_001"
        or logical.parent.name != "v035_pepglad_3eqs_seed42"
        or logical.parent.parent.name != "pepglad"
    ):
        return False
    run_root = logical.parents[2]
    opened = _v035_open_directory_chain(run_root)
    if opened is None:
        return False
    descriptors, directory_stats = opened
    attempts: list[Path] = []

    def scan(directory_fd: int, directory: Path) -> bool:
        try:
            before = os.fstat(directory_fd)
            names = tuple(sorted(os.listdir(directory_fd)))
            for name in names:
                entry = os.stat(
                    name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
                if stat.S_ISLNK(entry.st_mode):
                    return False
                is_attempt = re.fullmatch(r"attempt_[0-9]{3}", name) is not None
                if is_attempt and not stat.S_ISDIR(entry.st_mode):
                    return False
                if not stat.S_ISDIR(entry.st_mode):
                    continue
                child_fd = os.open(
                    name,
                    _v035_directory_flags(),
                    dir_fd=directory_fd,
                )
                try:
                    child = os.fstat(child_fd)
                    if _v035_directory_identity(child) != _v035_directory_identity(
                        entry
                    ):
                        return False
                    if is_attempt:
                        attempts.append(directory / name)
                    elif not scan(child_fd, directory / name):
                        return False
                    current_child = os.fstat(child_fd)
                    current_entry = os.stat(
                        name,
                        dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                    if not all(
                        _v035_directory_identity(value)
                        == _v035_directory_identity(entry)
                        for value in (current_child, current_entry)
                    ):
                        return False
                finally:
                    os.close(child_fd)
            after = os.fstat(directory_fd)
            return all(
                (
                    _v035_directory_identity(after)
                    == _v035_directory_identity(before),
                    tuple(sorted(os.listdir(directory_fd))) == names,
                )
            )
        except (OSError, ValueError):
            return False

    try:
        topology_stable = scan(descriptors[-1], run_root)
        chain_stable = _v035_directory_chain_stable(
            run_root,
            descriptors,
            directory_stats,
        )
        return topology_stable and chain_stable and attempts == [logical]
    finally:
        _v035_close_descriptors(descriptors)


def _v035_capture_attempt(
    attempt: Path,
) -> dict[str, tuple[Path, bytes, str, tuple[int, ...]]] | None:
    if (
        not attempt.is_absolute()
        or Path(os.path.abspath(attempt)) != attempt
        or attempt.name != "attempt_001"
        or attempt.parent.name != "v035_pepglad_3eqs_seed42"
        or attempt.parent.parent.name != "pepglad"
    ):
        return None
    try:
        attempt_lstat = os.lstat(attempt)
        if stat.S_ISLNK(attempt_lstat.st_mode) or not stat.S_ISDIR(
            attempt_lstat.st_mode
        ):
            return None
    except OSError:
        return None
    captured: dict[str, tuple[Path, bytes, str, tuple[int, ...]]] = {}
    for relative in _V035_REPLAY_FILES:
        value = _v035_stable_file(attempt / relative, confined_root=attempt)
        if value is None:
            return None
        captured[relative] = value
    return captured


def _v035_raw_replay_valid(bundle: object) -> bool:
    if not _v035_bundle_schema_valid(bundle):
        return False
    from scripts.run_v035_pepglad_connectivity import (
        AUTHORIZED_EXECUTION,
        AUTHORIZED_JOB,
    )
    from scripts.v035_adapters import pepglad

    execution = bundle["execution"]
    candidate = bundle["candidate"]
    qc = bundle["qc"]
    provenance = bundle["runtime_provenance"]
    job_summary = bundle["job"]
    attempt = Path(execution["attempt_dir"])
    if not _v035_authorized_attempt_is_unique(attempt):
        return False
    captured = _v035_capture_attempt(attempt)
    if captured is None:
        return False
    captured_job = _v035_strict_json_bytes(captured["job.json"][1])
    captured_execution = _v035_strict_json_bytes(captured["execution.json"][1])
    run_result = _v035_strict_json_bytes(captured["run_result.json"][1])
    if not all(
        (
            captured_job == dict(AUTHORIZED_JOB),
            captured_execution == dict(AUTHORIZED_EXECUTION),
            run_result is not None,
        )
    ):
        return False
    expected_bindings = pepglad.expected_runtime_bindings()
    files = provenance["files"]
    if not all(
        (
            provenance["producer_bindings"] == expected_bindings,
            job_summary["target_sha256"]
            == expected_bindings["target_input_sha256"],
            all(files[relative] == captured[relative][2] for relative in files),
            captured["raw/pepglad_candidate.pdb"][1]
            == captured["work/codesign/3EQS_0.pdb"][1],
            captured["raw/pepglad_candidate.pdb"][2]
            == candidate["file_sha256"],
        )
    ):
        return False
    runtime_capture = captured["raw/runtime_evidence.json"]
    runtime = _v035_strict_json_bytes(runtime_capture[1])
    if runtime is None:
        return False
    try:
        semantic = json.dumps(
            runtime, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    if not all(
        (
            runtime_capture[2] == provenance["runtime_evidence_sha256"],
            hashlib.sha256(semantic).hexdigest()
            == provenance["runtime_semantic_sha256"],
            all(runtime.get(field) == value for field, value in expected_bindings.items()),
            runtime.get("requested_seed") == 42,
            type(runtime.get("requested_seed")) is int,
            runtime.get("effective_seed") == 42,
            type(runtime.get("effective_seed")) is int,
            runtime.get("seed_control_status") == "honored",
            runtime.get("baseline_replay_expected_sha256")
            == _V035_BASELINE_SHA256,
            runtime.get("baseline_replay_observed_sha256")
            == candidate["file_sha256"],
            runtime.get("post_relax_sha256") == candidate["file_sha256"],
        )
    ):
        return False
    job = dict(AUTHORIZED_JOB)
    if not all(
        (
            job_summary["job_id"] == job["job_id"],
            job_summary["method"] == job["method"],
            str(job_summary["random_seed"]) == job["random_seed"],
            job_summary["seed_stage"] == job["seed_stage"],
            job_summary["target_sha256"] == job["target_pdb_sha256"],
            job_summary["target_chain"] == job["expected_target_chain"],
            job_summary["binder_chain"] == job["expected_binder_chain"],
            str(job_summary["length"]) == job["length_min"] == job["length_max"],
            job_summary["chirality_constraint"] == job["chirality_constraint"],
            job_summary["chirality_check_mode"] == job["chirality_check_mode"],
            job_summary["baseline_replay_policy"]
            == job["baseline_replay_policy"],
        )
    ):
        return False
    target_path = Path(job["target_pdb_path"])
    if not target_path.is_absolute():
        target_path = ROOT / target_path
    target_capture = _v035_stable_file(target_path, confined_root=ROOT)
    if (
        target_capture is None
        or target_capture[2] != expected_bindings["target_input_sha256"]
    ):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="v035-validator-replay-") as temporary:
            snapshot = (
                Path(temporary)
                / "pepglad"
                / "v035_pepglad_3eqs_seed42"
                / "attempt_001"
            )
            snapshot.mkdir(parents=True)
            for relative, value in captured.items():
                destination = snapshot / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(value[1])
            snapshot_target = Path(temporary) / "target" / "3EQS.pdb"
            snapshot_target.parent.mkdir()
            snapshot_target.write_bytes(target_capture[1])
            replay_job = {**job, "target_pdb_path": str(snapshot_target)}
            replay_candidate, replay_runtime = pepglad.parse(replay_job, snapshot)
            replay_qc = pepglad.evaluate_candidate(
                replay_job, replay_candidate, replay_runtime, snapshot / "raw"
            )
            structure = Path(replay_candidate.get("structure_path", ""))
            structure_relative = structure.resolve(strict=True).relative_to(
                snapshot.resolve(strict=True)
            )
            if structure_relative.as_posix() != candidate["structure_path"]:
                return False
            candidate_checks = {
                "sequence": replay_candidate.get("sequence"),
                "binder_chain": replay_candidate.get("binder_chain"),
                "parse_status": replay_candidate.get("parse_status"),
                "chirality": replay_candidate.get("chirality"),
            }
            if any(
                candidate_checks[field] != candidate[field]
                for field in candidate_checks
            ):
                return False
            if replay_runtime != runtime:
                return False
            if any(replay_qc.get(field) != qc[field] for field in _V035_QC_FIELDS):
                return False
            if not _v035_run_result_valid(
                run_result,
                attempt=attempt,
                job=job_summary,
                execution=execution,
                candidate=candidate,
                qc=qc,
                replay_candidate=replay_candidate,
                replay_qc=replay_qc,
            ):
                return False
    except (
        KeyError,
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        return False
    repeated = _v035_capture_attempt(attempt)
    repeated_target = _v035_stable_file(target_path, confined_root=ROOT)
    return all(
        (
            repeated == captured,
            repeated_target == target_capture,
            _v035_authorized_attempt_is_unique(attempt),
        )
    )


def _v035_historical_bindings_valid(
    bundle: object, *, artifact_paths: list[Path] | tuple[Path, ...] | None = None
) -> bool:
    if type(bundle) is not dict:
        return False
    historical = bundle.get("historical_v034_bindings")
    if type(historical) is not dict or set(historical) != _V035_HISTORICAL_FIELDS:
        return False
    artifacts = historical.get("artifacts")
    if not all(
        (
            type(historical.get("primary_supported")) is int,
            historical.get("primary_supported") == 6,
            historical.get("pepglad_status")
            == "historical_failure_not_promoted",
            type(artifacts) is dict,
            set(artifacts) == _V035_HISTORICAL_NAMES
            if type(artifacts) is dict
            else False,
        )
    ):
        return False
    paths = (
        tuple(ROOT / relative for relative in _V035_HISTORICAL_PATHS)
        if artifact_paths is None
        else tuple(Path(path) for path in artifact_paths)
    )
    if len(paths) != 10 or len({path.name for path in paths}) != 10:
        return False
    by_name: dict[str, tuple[Path, bytes, str, tuple[int, ...]]] = {}
    for path in paths:
        capture = _v035_stable_file(Path(os.path.abspath(path)))
        if capture is None:
            return False
        by_name[path.name] = capture
    if set(by_name) != _V035_HISTORICAL_NAMES or any(
        artifacts[name] != capture[2] for name, capture in by_name.items()
    ):
        return False
    repeated = {
        name: _v035_stable_file(capture[0]) for name, capture in by_name.items()
    }
    return all(repeated[name] == capture for name, capture in by_name.items())


def validate_v035_pepglad_bundle(
    errors: list[str],
    warnings: list[str],
    *,
    bundle: object | None = None,
) -> None:
    del warnings
    selected = bundle
    if selected is None:
        path = ROOT / "benchmark/results/pilot_pepglad_connectivity_v0.35.json"
        capture = _v035_stable_file(path)
        selected = _v035_strict_json_bytes(capture[1]) if capture is not None else None
    schema_valid = _v035_bundle_schema_valid(selected)
    raw_valid = _v035_raw_replay_valid(selected)
    historical_valid = _v035_historical_bindings_valid(selected)
    if not schema_valid:
        errors.append("v0.35 bundle schema or scoring boundary is invalid")
    if not raw_valid:
        errors.append("v0.35 raw replay is invalid or stale")
    if not historical_valid:
        errors.append("v0.35 historical bindings are invalid or stale")


def _v034_positive_int(
    errors: list[str], job_id: str, field: str, value: str
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        errors.append(f"{job_id}: {field} must be an integer")
        return -1
    if parsed <= 0:
        errors.append(f"{job_id}: {field} must be positive")
    return parsed


def check_v034_bounded_connectivity(errors: list[str]) -> dict[str, int]:
    """Validate the truthful, currently incomplete v0.34 connectivity snapshot."""

    job_rows = check_headers(
        errors,
        "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv",
        PILOT_BENCHMARK_JOB_V034_HEADERS,
    )
    matrix_rows = check_headers(
        errors,
        "benchmark/deployment/pilot_execution_matrix_v0.34.csv",
        PILOT_EXECUTION_MATRIX_V034_HEADERS,
    )
    execution_rows = check_headers(
        errors,
        "benchmark/deployment/pilot_execution_results_v0.34.csv",
        PILOT_EXECUTION_RESULTS_V034_HEADERS,
    )
    method_rows = check_headers(
        errors,
        "benchmark/results/pilot_method_output_manifest_v0.34.csv",
        PILOT_METHOD_OUTPUT_V034_HEADERS,
    )
    candidate_rows = check_headers(
        errors,
        "benchmark/results/pilot_candidate_outputs_v0.34.csv",
        PILOT_CANDIDATE_OUTPUT_V034_HEADERS,
    )
    qc_rows = check_headers(
        errors,
        "benchmark/results/pilot_candidate_qc_v0.34.csv",
        PILOT_CANDIDATE_QC_V034_HEADERS,
    )
    run_rows = check_headers(
        errors,
        "benchmark/results/pilot_run_v0.34.csv",
        PILOT_RUN_V034_HEADERS,
    )

    expected_specs: dict[str, tuple[str, str, str, str]] = {}
    for job_base, method in V034_JOB_METHODS.items():
        primary_job_id = f"{job_base}_seed42"
        expected_specs[primary_job_id] = (method, "primary", "42", "")
        expected_specs[f"{job_base}_seed43"] = (
            method,
            "extension",
            "43",
            primary_job_id,
        )
    expected_job_ids = set(expected_specs)
    pepglad_primary = "v034_pepglad_3eqs_seed42"
    pepglad_extension = "v034_pepglad_3eqs_seed43"
    expected_supported = expected_job_ids - {pepglad_primary, pepglad_extension}
    expected_method_jobs = expected_supported | {pepglad_primary}

    table_rows = {
        "pilot_benchmark_job_manifest_v0.34.csv": job_rows,
        "pilot_execution_matrix_v0.34.csv": matrix_rows,
        "pilot_execution_results_v0.34.csv": execution_rows,
        "pilot_method_output_manifest_v0.34.csv": method_rows,
        "pilot_candidate_outputs_v0.34.csv": candidate_rows,
        "pilot_candidate_qc_v0.34.csv": qc_rows,
        "pilot_run_v0.34.csv": run_rows,
    }
    indexed = {
        name: _v034_rows_by_job(errors, name, rows)
        for name, rows in table_rows.items()
    }
    jobs_by_id = indexed["pilot_benchmark_job_manifest_v0.34.csv"]
    matrix_by_id = indexed["pilot_execution_matrix_v0.34.csv"]
    execution_by_id = indexed["pilot_execution_results_v0.34.csv"]
    method_by_id = indexed["pilot_method_output_manifest_v0.34.csv"]
    candidate_by_id = indexed["pilot_candidate_outputs_v0.34.csv"]
    qc_by_id = indexed["pilot_candidate_qc_v0.34.csv"]
    run_by_id = indexed["pilot_run_v0.34.csv"]

    expected_sets = {
        "pilot_benchmark_job_manifest_v0.34.csv": expected_job_ids,
        "pilot_execution_matrix_v0.34.csv": expected_job_ids,
        "pilot_execution_results_v0.34.csv": expected_job_ids,
        "pilot_method_output_manifest_v0.34.csv": expected_method_jobs,
        "pilot_candidate_outputs_v0.34.csv": expected_supported,
        "pilot_candidate_qc_v0.34.csv": expected_supported,
        "pilot_run_v0.34.csv": expected_job_ids,
    }
    for artifact_name, expected_ids in expected_sets.items():
        observed_ids = set(indexed[artifact_name])
        if observed_ids != expected_ids:
            errors.append(
                f"{artifact_name}: v0.34 job set mismatch; "
                f"missing={sorted(expected_ids - observed_ids)}, "
                f"extra={sorted(observed_ids - expected_ids)}"
            )

    expected_lengths = {
        "pilot_benchmark_job_manifest_v0.34.csv": 14,
        "pilot_execution_matrix_v0.34.csv": 14,
        "pilot_execution_results_v0.34.csv": 14,
        "pilot_method_output_manifest_v0.34.csv": 13,
        "pilot_candidate_outputs_v0.34.csv": 12,
        "pilot_candidate_qc_v0.34.csv": 12,
        "pilot_run_v0.34.csv": 14,
    }
    for artifact_name, expected_length in expected_lengths.items():
        observed_length = len(table_rows[artifact_name])
        if observed_length != expected_length:
            errors.append(
                f"{artifact_name}: expected {expected_length} v0.34 rows, "
                f"found {observed_length}"
            )

    for job_id, (method, stage, seed, primary_job_id) in expected_specs.items():
        job = jobs_by_id.get(job_id, {})
        matrix = matrix_by_id.get(job_id, {})
        execution = execution_by_id.get(job_id, {})
        run = run_by_id.get(job_id, {})
        for artifact_name, row in [
            ("job manifest", job),
            ("execution matrix", matrix),
            ("execution results", execution),
            ("run table", run),
        ]:
            if row and row.get("method") != method:
                errors.append(f"{job_id}: {artifact_name} method must be {method}")
            if row and row.get("seed_stage") != stage:
                errors.append(f"{job_id}: {artifact_name} seed_stage must be {stage}")
        for artifact_name, row in [
            ("job manifest", job),
            ("execution results", execution),
            ("run table", run),
        ]:
            if row and row.get("random_seed") != seed:
                errors.append(f"{job_id}: {artifact_name} random_seed must be {seed}")
        for artifact_name, row in [("job manifest", job), ("execution matrix", matrix)]:
            if row and row.get("primary_job_id") != primary_job_id:
                errors.append(
                    f"{job_id}: {artifact_name} primary_job_id must be {primary_job_id!r}"
                )
        if job:
            if job.get("n_designs_requested") != "1":
                errors.append(f"{job_id}: n_designs_requested must be 1")
            if job.get("status") != "planned_bounded_generation":
                errors.append(f"{job_id}: job status must remain planned_bounded_generation")
            if "not Benchmark result" not in job.get("evidence_boundary", ""):
                errors.append(f"{job_id}: job manifest missing bounded evidence boundary")
        if matrix:
            if matrix.get("execution_id") != f"exec_{job_id}":
                errors.append(f"{job_id}: execution_id must be exec_{job_id}")
            if matrix.get("status") != "planned_bounded_generation":
                errors.append(f"{job_id}: matrix status must remain planned_bounded_generation")
            if "not Benchmark result" not in matrix.get("evidence_boundary", ""):
                errors.append(f"{job_id}: execution matrix missing bounded evidence boundary")

    supported_execution_ids = {
        job_id
        for job_id, row in execution_by_id.items()
        if row.get("supported_candidate") == "yes"
        and row.get("merge_status") == "supported"
        and row.get("status") == "passed"
    }
    if supported_execution_ids != expected_supported:
        errors.append(
            "pilot_execution_results_v0.34.csv must contain exactly 12 supported "
            "rows (6 primary + 6 extension)"
        )
    for artifact_name, rows_by_id in [
        ("pilot_candidate_outputs_v0.34.csv", candidate_by_id),
        ("pilot_candidate_qc_v0.34.csv", qc_by_id),
    ]:
        if {pepglad_primary, pepglad_extension} & set(rows_by_id):
            errors.append(f"{artifact_name} must not contain PepGLAD rows")
        supported_ids = {
            job_id
            for job_id, row in rows_by_id.items()
            if row.get("supported_candidate") == "yes"
        }
        if supported_ids != expected_supported:
            errors.append(
                f"{artifact_name} must contain exactly 12 supported rows "
                "(6 primary + 6 extension)"
            )

    for job_id in expected_supported:
        execution = execution_by_id.get(job_id, {})
        method_row = method_by_id.get(job_id, {})
        candidate = candidate_by_id.get(job_id, {})
        qc = qc_by_id.get(job_id, {})
        run = run_by_id.get(job_id, {})
        if execution.get("overall_qc_status") not in {"pass", "pass_with_warning"}:
            errors.append(f"{job_id}: supported execution must have passing QC")
        if execution.get("method_contract_status") != "pass":
            errors.append(f"{job_id}: supported execution method_contract_status must be pass")
        if method_row.get("status") != "passed":
            errors.append(f"{job_id}: method output status must be passed")
        if method_row.get("overall_qc_status") not in {"pass", "pass_with_warning"}:
            errors.append(f"{job_id}: method output must have passing QC")
        if not candidate.get("design_id") or candidate.get("generation_rank") != "1":
            errors.append(f"{job_id}: supported candidate must have one rank-1 design")
        if candidate.get("supported_candidate") != "yes":
            errors.append(f"{job_id}: candidate row must be marked supported")
        if qc.get("overall_qc_status") not in {"pass", "pass_with_warning"}:
            errors.append(f"{job_id}: candidate QC must pass or pass_with_warning")
        if qc.get("method_contract_status") != "pass":
            errors.append(f"{job_id}: candidate QC method_contract_status must be pass")
        if qc.get("supported_candidate") != "yes":
            errors.append(f"{job_id}: candidate QC row must be marked supported")
        if run.get("status") != "passed" or run.get("supported_candidate") != "yes":
            errors.append(f"{job_id}: run row must record a supported passed candidate")
        if run.get("overall_qc_status") not in {"pass", "pass_with_warning"}:
            errors.append(f"{job_id}: run row must have passing QC")
        if "not scoring" not in run.get("notes", "") or "Benchmark result" not in run.get("notes", ""):
            errors.append(f"{job_id}: run row missing no-scoring/no-Benchmark boundary")
        candidate_boundary = candidate.get("notes", "")
        if (
            "not Benchmark result" not in candidate_boundary
            or "scoring evidence" not in candidate_boundary
        ):
            errors.append(f"{job_id}: candidate row missing bounded evidence boundary")

    pepglad_primary_execution = execution_by_id.get(pepglad_primary, {})
    if (
        pepglad_primary_execution.get("status") != "parse_failed"
        or pepglad_primary_execution.get("overall_qc_status") != "fail"
        or pepglad_primary_execution.get("supported_candidate") != "no"
        or pepglad_primary_execution.get("merge_status") != "evidence_incomplete"
        or pepglad_primary_execution.get("candidate_parse_status") != "failed"
        or pepglad_primary_execution.get("method_contract_status") != "pass"
    ):
        errors.append(
            "PepGLAD execution must remain parse_failed/evidence_incomplete and unsupported"
        )
    if (
        pepglad_primary_execution.get("attempt_id") != "attempt_003"
        or Path(pepglad_primary_execution.get("attempt_dir", "")).name
        != "attempt_003"
    ):
        errors.append("PepGLAD execution must bind attempt_003")
    if (
        pepglad_primary_execution.get("status_reason")
        != "pepglad_seed42_replay_mismatch"
    ):
        errors.append(
            "PepGLAD execution status_reason must be pepglad_seed42_replay_mismatch"
        )
    if any(
        pepglad_primary_execution.get(field)
        for field in [
            "chirality_evaluable",
            "chirality_l_count",
            "chirality_d_count",
            "chirality_unknown_count",
        ]
    ):
        errors.append("PepGLAD execution must not promote replay diagnostics to candidate QC")

    pepglad_primary_method = method_by_id.get(pepglad_primary, {})
    if (
        pepglad_primary_method.get("status") != "parse_failed"
        or pepglad_primary_method.get("overall_qc_status") != "fail"
        or pepglad_primary_method.get("parser_status") != "failed"
        or pepglad_primary_method.get("exit_code") != "0"
    ):
        errors.append("PepGLAD method manifest must remain parse_failed")
    if (
        pepglad_primary_method.get("run_record_id")
        != "v034_pepglad_3eqs_seed42_attempt_003"
        or Path(pepglad_primary_method.get("raw_output_root", "")).parent.name
        != "attempt_003"
        or Path(pepglad_primary_method.get("stdout_log", "")).parent.name
        != "attempt_003"
        or Path(pepglad_primary_method.get("stderr_log", "")).parent.name
        != "attempt_003"
        or "/attempt_003/command.sh"
        not in pepglad_primary_method.get("command", "")
    ):
        errors.append("PepGLAD method manifest must bind attempt_003")
    if (
        pepglad_primary_method.get("status_reason")
        != "pepglad_seed42_replay_mismatch"
    ):
        errors.append(
            "PepGLAD method manifest status_reason must be "
            "pepglad_seed42_replay_mismatch"
        )

    pepglad_primary_run = run_by_id.get(pepglad_primary, {})
    if (
        pepglad_primary_run.get("status") != "parse_failed"
        or pepglad_primary_run.get("overall_qc_status") != "fail"
        or pepglad_primary_run.get("supported_candidate") != "no"
    ):
        errors.append("PepGLAD run row must remain parse_failed and unsupported")
    if pepglad_primary_run.get("attempt_id") != "attempt_003":
        errors.append("PepGLAD run row must bind attempt_003")
    if (
        pepglad_primary_run.get("status_reason")
        != "pepglad_seed42_replay_mismatch"
    ):
        errors.append(
            "PepGLAD run row status_reason must be pepglad_seed42_replay_mismatch"
        )
    if any(
        pepglad_primary_run.get(field)
        for field in ["design_id", "sequence", "structure_path"]
    ):
        errors.append("PepGLAD run row must not contain a promoted candidate")
    if (
        "not scoring" not in pepglad_primary_run.get("notes", "")
        or "Benchmark result" not in pepglad_primary_run.get("notes", "")
    ):
        errors.append("PepGLAD run row missing no-scoring/no-Benchmark boundary")

    pepglad_extension_execution = execution_by_id.get(pepglad_extension, {})
    if (
        pepglad_extension_execution.get("status") != "not_run"
        or pepglad_extension_execution.get("overall_qc_status") != "not_run"
        or pepglad_extension_execution.get("supported_candidate") != "no"
        or pepglad_extension_execution.get("merge_status") != "not_run"
        or pepglad_extension_execution.get("attempt_id")
        or pepglad_extension_execution.get("status_reason") != "no_attempt_recorded"
    ):
        errors.append("PepGLAD extension must remain not_run after failed primary")
    pepglad_extension_run = run_by_id.get(pepglad_extension, {})
    if (
        pepglad_extension_run.get("status") != "not_run"
        or pepglad_extension_run.get("overall_qc_status") != "not_run"
        or pepglad_extension_run.get("supported_candidate") != "no"
        or pepglad_extension_run.get("attempt_id")
        or pepglad_extension_run.get("design_id")
        or pepglad_extension_run.get("sequence")
        or pepglad_extension_run.get("structure_path")
        or pepglad_extension_run.get("status_reason") != "no_attempt_recorded"
    ):
        errors.append("PepGLAD extension run row must remain not_run without a candidate")

    for job_id in ["v034_pepmlm_sequence_seed42", "v034_pepmlm_sequence_seed43"]:
        candidate = candidate_by_id.get(job_id, {})
        qc = qc_by_id.get(job_id, {})
        execution = execution_by_id.get(job_id, {})
        if (
            "X" not in candidate.get("sequence", "")
            or candidate.get("parse_status") != "partial"
            or "X" not in qc.get("noncanonical_residues", "")
            or qc.get("noncanonical_status") != "warn"
            or qc.get("overall_qc_status") != "pass_with_warning"
            or execution.get("candidate_parse_status") != "partial"
            or execution.get("overall_qc_status") != "pass_with_warning"
        ):
            errors.append(f"{job_id}: PepMLM partial-X warning evidence is incomplete")

    for job_id in [
        "v034_rfdiffusion_mpnn_7zkr_seed42",
        "v034_rfdiffusion_mpnn_7zkr_seed43",
    ]:
        if qc_by_id.get(job_id, {}).get("handoff_status") != "pass":
            errors.append(f"{job_id}: RF handoff_status must be pass")
        if execution_by_id.get(job_id, {}).get("handoff_status") != "pass":
            errors.append(f"{job_id}: RF execution handoff_status must be pass")

    for job_base, method in [
        ("v034_dflow_3eqs", "D-Flow / PeptideDesign"),
        ("v034_pepmirror_3eqs", "PepMirror"),
    ]:
        for seed in (42, 43):
            job_id = f"{job_base}_seed{seed}"
            candidate = candidate_by_id.get(job_id, {})
            qc = qc_by_id.get(job_id, {})
            execution = execution_by_id.get(job_id, {})
            if candidate.get("chirality") != "D":
                errors.append(f"{job_id}: {method} candidate chirality must be D")
            if qc.get("chirality_status") != "pass":
                errors.append(f"{job_id}: {method} chirality_status must be pass")
            _v034_positive_int(errors, job_id, "chirality_d_count", qc.get("chirality_d_count", ""))
            if qc.get("chirality_l_count") != "0" or qc.get("chirality_unknown_count") != "0":
                errors.append(f"{job_id}: {method} QC must contain no L or unknown residues")
            if execution.get("chirality_l_count") != "0" or execution.get("chirality_unknown_count") != "0":
                errors.append(f"{job_id}: {method} execution must contain no L or unknown residues")

    for job_id in ["v034_colabdesign_7zkr_seed42", "v034_colabdesign_7zkr_seed43"]:
        candidate = candidate_by_id.get(job_id, {})
        qc = qc_by_id.get(job_id, {})
        if candidate.get("cyclic") != "yes" or candidate.get("peptide_type") != "cyclic":
            errors.append(f"{job_id}: ColabDesign candidate must remain cyclic")
        if qc.get("cyclic_status") != "pass":
            errors.append(f"{job_id}: ColabDesign cyclic_status must be pass")
        try:
            terminal_distance = float(qc.get("terminal_cn_distance", ""))
        except (TypeError, ValueError):
            errors.append(f"{job_id}: ColabDesign terminal C-N distance must be numeric")
        else:
            if not 0.9 <= terminal_distance <= 2.0:
                errors.append(f"{job_id}: ColabDesign terminal C-N distance is out of range")

    provenance_path = ROOT / "benchmark/results/pilot_runtime_provenance_v0.34.json"
    provenance = _v034_json_object(
        errors,
        provenance_path,
        "pilot_runtime_provenance_v0.34.json",
    )
    if not _v034_runtime_provenance_exact_schema(provenance):
        errors.append(
            "pilot_runtime_provenance_v0.34.json runtime provenance exact schema "
            "must contain only the registered finite fields and strict value types"
        )
    if provenance.get("schema_version") != "v0.34":
        errors.append("pilot_runtime_provenance_v0.34.json schema_version must be v0.34")
    if provenance.get("evidence_boundary") != "bounded_connectivity_only_not_scoring_or_ranking":
        errors.append("pilot_runtime_provenance_v0.34.json has an invalid evidence boundary")
    provenance_records_value = provenance.get("records", [])
    if not isinstance(provenance_records_value, list):
        errors.append("pilot_runtime_provenance_v0.34.json records must be a list")
        provenance_records: list[dict[str, object]] = []
    else:
        provenance_records = []
        for index, record in enumerate(provenance_records_value):
            if not isinstance(record, dict):
                errors.append(f"runtime provenance record {index} must be an object")
                continue
            provenance_records.append(record)
    if len(provenance_records) != 12:
        errors.append(
            "pilot_runtime_provenance_v0.34.json must contain 12 supported-job records"
        )
    provenance_by_id: dict[str, dict[str, object]] = {}
    for record in provenance_records:
        job_id = record.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            errors.append("runtime provenance record missing job_id")
            continue
        if job_id in provenance_by_id:
            errors.append(f"runtime provenance contains duplicate job_id {job_id}")
        provenance_by_id[job_id] = record
    if set(provenance_by_id) != expected_supported:
        errors.append(
            "pilot_runtime_provenance_v0.34.json runtime provenance job set must "
            "match the 12 supported jobs"
        )

    sha256_pattern = re.compile(r"[0-9a-f]{64}")
    for job_id in expected_supported:
        record = provenance_by_id.get(job_id, {})
        method, stage, seed_text, _ = expected_specs[job_id]
        seed = int(seed_text)
        execution = execution_by_id.get(job_id, {})
        run = run_by_id.get(job_id, {})
        candidate = candidate_by_id.get(job_id, {})
        qc = qc_by_id.get(job_id, {})
        if record.get("method") != method:
            errors.append(f"{job_id}: runtime provenance method must be {method}")
        if record.get("seed_stage") != stage or record.get("random_seed") != seed:
            errors.append(f"{job_id}: runtime provenance seed/stage binding is invalid")
        attempt_id = record.get("attempt_id")
        if (
            not isinstance(attempt_id, str)
            or attempt_id != execution.get("attempt_id")
            or attempt_id != run.get("attempt_id")
            or Path(execution.get("attempt_dir", "")).name != attempt_id
        ):
            errors.append(f"{job_id}: runtime provenance attempt_id is not bound to compact rows")
        if record.get("runtime_evidence_path") not in {
            "runtime_evidence.json",
            "raw/runtime_evidence.json",
        }:
            errors.append(f"{job_id}: runtime_evidence_path is not an allowed attempt-relative path")
        raw_sha = record.get("runtime_evidence_sha256")
        if not isinstance(raw_sha, str) or sha256_pattern.fullmatch(raw_sha) is None:
            errors.append(f"{job_id}: runtime_evidence_sha256 must be a lowercase SHA-256")
        evidence = record.get("evidence")
        if not isinstance(evidence, dict) or not evidence:
            errors.append(f"{job_id}: runtime provenance evidence must be a non-empty object")
            evidence = {}
        try:
            semantic_payload = json.dumps(
                evidence,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError):
            semantic_payload = b""
            errors.append(
                f"{job_id}: runtime provenance exact schema requires finite "
                "JSON semantic values"
            )
        expected_semantic_sha = hashlib.sha256(semantic_payload).hexdigest()
        semantic_sha = record.get("evidence_semantic_sha256")
        if (
            not isinstance(semantic_sha, str)
            or sha256_pattern.fullmatch(semantic_sha) is None
        ):
            errors.append(
                f"{job_id}: evidence_semantic_sha256 must be a lowercase SHA-256"
            )
        elif semantic_sha != expected_semantic_sha:
            errors.append(f"{job_id}: evidence_semantic_sha256 mismatch")
        if not all(
            (
                evidence.get("requested_seed") == seed,
                evidence.get("effective_seed") == seed,
                evidence.get("seed_control_status") == "honored",
            )
        ):
            errors.append(f"{job_id}: runtime evidence seed binding must be honored")

        if method == "PepMirror":
            for path_field, sha_field in [
                ("mirror_input_path", "mirror_input_sha256"),
                ("mirrored_target_path", "mirrored_target_sha256"),
                ("mirrored_generated_path", "mirrored_generated_sha256"),
                ("mirror_output_path", "mirror_output_sha256"),
                ("seed_patch_path", "seed_patch_sha256"),
            ]:
                if not evidence.get(path_field):
                    errors.append(f"{job_id}: PepMirror provenance missing {path_field}")
                value = evidence.get(sha_field)
                if not isinstance(value, str) or sha256_pattern.fullmatch(value) is None:
                    errors.append(f"{job_id}: PepMirror provenance missing {sha_field}")
            if not evidence.get("checkpoint_path") or not str(
                evidence.get("checkpoint_revision", "")
            ).startswith("sha256:"):
                errors.append(f"{job_id}: PepMirror provenance missing checkpoint binding")
            if evidence.get("mirror_roundtrip_applied") is not True:
                errors.append(f"{job_id}: PepMirror provenance must record mirror roundtrip")
            if evidence.get("mirror_input_sha256") != jobs_by_id.get(job_id, {}).get(
                "target_pdb_sha256"
            ):
                errors.append(f"{job_id}: PepMirror input SHA is not target-bound")
            if evidence.get("mirror_input_sha256") == evidence.get(
                "mirrored_target_sha256"
            ):
                errors.append(f"{job_id}: PepMirror mirrored target must differ from input")
            if (
                evidence.get("mirror_output_sha256") != qc.get("file_sha256")
                or evidence.get("mirror_output_path") != candidate.get("structure_path")
                or evidence.get("mirror_output_path")
                != candidate.get("source_output_path")
            ):
                errors.append(f"{job_id}: PepMirror output provenance is not candidate-bound")

        if method == "RFdiffusion + ProteinMPNN":
            for path_field, sha_field in [
                ("rf_backbone_path", "rf_backbone_sha256"),
                ("rf_trb_path", "rf_trb_sha256"),
                ("mpnn_fasta_path", "mpnn_fasta_sha256"),
            ]:
                if not evidence.get(path_field):
                    errors.append(f"{job_id}: RF provenance missing {path_field}")
                value = evidence.get(sha_field)
                if not isinstance(value, str) or sha256_pattern.fullmatch(value) is None:
                    errors.append(f"{job_id}: RF provenance missing {sha_field}")
            rf_contract = all(
                (
                    evidence.get("rf_target_conditioned") is True,
                    evidence.get("rf_contig") == "[A3-117/0 70-100]",
                    set(evidence.get("rf_hotspots", []))
                    == {"A48", "A50", "A51", "A52", "A62", "A65"},
                    evidence.get("rf_cyclic") is False,
                    evidence.get("rf_deterministic") is True,
                    evidence.get("rf_design_startnum") == seed,
                    evidence.get("mpnn_seed") == seed,
                    evidence.get("mpnn_designed_chain") == "B",
                    set(evidence.get("mpnn_fixed_chains", [])) == {"A"},
                    evidence.get("mpnn_record_type") == "generated_sample",
                    bool(evidence.get("mpnn_selected_record_id")),
                )
            )
            if not rf_contract:
                errors.append(f"{job_id}: RF-to-MPNN provenance contract is incomplete")
            if (
                evidence.get("rf_backbone_sha256") != qc.get("file_sha256")
                or evidence.get("rf_backbone_path") != candidate.get("structure_path")
                or evidence.get("mpnn_fasta_path")
                != candidate.get("source_output_path")
            ):
                errors.append(f"{job_id}: RF provenance is not candidate/handoff-bound")

    from scripts import parse_v034_generation_outputs as v034_merge

    if v034_merge._ACTIVE_CAPTURE_STORE is not None:
        for job_id in expected_method_jobs:
            for category in ("source", "model", "environment"):
                errors.append(
                    f"{job_id}: fixed identity/pin mismatch ({category})"
                )
        for job_id in expected_supported:
            errors.append(f"{job_id}: stable raw replay mismatch")
    else:
        capture_store = v034_merge._CaptureStore()
        v034_merge._ACTIVE_CAPTURE_STORE = capture_store
        try:
            for job_id in expected_method_jobs:
                mismatches = _v034_fixed_identity_mismatches(
                    jobs_by_id.get(job_id, {}),
                    execution_by_id.get(job_id, {}),
                    method_by_id.get(job_id, {}),
                    provenance_by_id.get(job_id),
                )
                for category in sorted(mismatches):
                    errors.append(
                        f"{job_id}: fixed identity/pin mismatch ({category})"
                    )
            for job_id in expected_supported:
                replay_ok = _v034_stable_raw_replay(
                    jobs_by_id.get(job_id, {}),
                    execution_by_id.get(job_id, {}),
                    method_by_id.get(job_id, {}),
                    candidate_by_id.get(job_id, {}),
                    qc_by_id.get(job_id, {}),
                    run_by_id.get(job_id, {}),
                    provenance_by_id.get(job_id, {}),
                )
                if not replay_ok:
                    errors.append(f"{job_id}: stable raw replay mismatch")
        finally:
            v034_merge._ACTIVE_CAPTURE_STORE = None
            capture_store.close()

    summary_path = ROOT / "benchmark/results/pilot_v034_merge_summary.json"
    summary = _v034_json_object(
        errors,
        summary_path,
        "pilot_v034_merge_summary.json",
    )
    for key, expected in {
        "schema_version": "v0.34",
        "primary_total": 7,
        "primary_passed": 6,
        "primary_complete": False,
        "extension_total": 7,
        "extension_passed": 6,
        "extension_complete": False,
        "parsed_candidate_rows": 12,
        "qc_failed_rows": 0,
        "runtime_provenance_rows": 12,
        "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
    }.items():
        if summary.get(key) != expected:
            expected_text = str(expected).lower() if isinstance(expected, bool) else expected
            errors.append(f"pilot_v034_merge_summary.json {key} must be {expected_text}")
    expected_summary_status = {
        job_id: (
            "evidence_incomplete"
            if job_id == pepglad_primary
            else "not_run"
            if job_id == pepglad_extension
            else "supported"
        )
        for job_id in expected_job_ids
    }
    if summary.get("job_status") != expected_summary_status:
        errors.append(
            "pilot_v034_merge_summary.json job_status must match the replay-failure snapshot"
        )

    failure_diagnostic_name = "pilot_failure_diagnostics_v0.34.json"
    failure_diagnostic_path = ROOT / f"benchmark/results/{failure_diagnostic_name}"
    failure_diagnostics = _v034_json_object(
        errors,
        failure_diagnostic_path,
        failure_diagnostic_name,
    )
    failure_diagnostic_attempt_dir = pepglad_primary_execution.get(
        "attempt_dir", ""
    )
    expected_failure_diagnostic = {
        "schema_version": "v0.34",
        "evidence_boundary": "failure_diagnostic_only_not_candidate_or_scoring",
        "records": [
            {
                "job_id": pepglad_primary,
                "method": "PepGLAD",
                "seed_stage": "primary",
                "random_seed": 42,
                "attempt_id": "attempt_003",
                "attempt_dir": failure_diagnostic_attempt_dir,
                "candidate_eligible": False,
                "seed43_status": "not_run",
                "process": {"exit_code": 0},
                "parser": {
                    "status": "failed",
                    "status_reason": "pepglad_seed42_replay_mismatch",
                },
                "merge": {"status": "evidence_incomplete"},
                "runtime_evidence": {
                    "path": "raw/runtime_evidence.json",
                    "sha256": (
                        "06d65928279969e0289038c2f0d1801459a698ceccf1cc87b6a0474a68eb3e85"
                    ),
                    "semantic_sha256": (
                        "e0db9a3380984fb8232ce36e5dae7bc4cea91612a0f6529c3e950dfe58e92fae"
                    ),
                },
                "summary": {
                    "path": "raw/pepglad_summary.jsonl",
                    "sha256": (
                        "2f6fdc775c44e0ab525fbe26f9baf7d44760fcedc041a302a86d6529b634b76c"
                    ),
                    "sequence": "AWHITLLIFTH",
                },
                "pre_openmm": {
                    "path": "raw/pepglad_pre_relax.pdb",
                    "sha256": (
                        "b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b"
                    ),
                    "chirality": {
                        "chain": "B",
                        "calculation_status": "pass",
                        "evaluable": 11,
                        "l_count": 6,
                        "d_count": 5,
                        "gly_count": 0,
                        "unknown_count": 0,
                    },
                },
                "post_openmm": {
                    "path": "raw/pepglad_candidate.pdb",
                    "sha256": (
                        "e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6"
                    ),
                    "chirality": {
                        "chain": "B",
                        "calculation_status": "pass",
                        "evaluable": 11,
                        "l_count": 4,
                        "d_count": 7,
                        "gly_count": 0,
                        "unknown_count": 0,
                    },
                },
                "baseline": {
                    "expected_sha256": (
                        "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
                    ),
                    "observed_sha256": (
                        "e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6"
                    ),
                    "status": "mismatch",
                    "failure_stage": "pre_openmm_snapshot",
                },
                "producer_bindings": {
                    "target": {
                        "path": "/data/input/3EQS.pdb",
                        "sha256": (
                            "7086cf2bc4723ccbb4be5ff7f86a50d9db59bc307f4fbb0395a3c6ce3569827d"
                        ),
                        "preflight_verified": True,
                    },
                    "source": {
                        "commit": "bad015ca50c312a89482adb5220c3d907f13df5c",
                        "entrypoint_sha256": (
                            "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
                        ),
                    },
                    "model": {
                        "weights_sha256": (
                            "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe"
                        )
                    },
                    "container": {"image": "pd-benchmark-methods-gpu:0.21"},
                    "environment": {"conda_environment": "bench-pepglad"},
                    "observer": {
                        "path": "pepglad_observer.py",
                        "sha256": (
                            "a0a98420dd2fd5382479abe77526fb8fc206ffb1e69a8780912fb821dded0c61"
                        ),
                    },
                    "patch": {
                        "evidence_path": "observer_patch_evidence.json",
                        "evidence_sha256": (
                            "0342297b2094fe43fe2e7bf49d720e58eccdc3103b0a02e943c0861ca160a9aa"
                        ),
                        "instrumenter_path": "pepglad_instrument_source.py",
                        "instrumenter_sha256": (
                            "cd9ec19f6605fd2b067824d4e02971b3a203e827b6398a4ffd1c68c64464311a"
                        ),
                        "injection_status": "applied",
                        "source_copy_mode": "attempt_local_copy",
                    },
                    "wrapper": {
                        "path": "pepglad_seeded_entry.py",
                        "sha256": (
                            "6a9b4c9012205d27526e13dbccbd7d11c010eddc3c85acdb2796c2fa6668aaba"
                        ),
                    },
                    "instrumented_source": {
                        "path": "work/api/run.py",
                        "prepatch_sha256": (
                            "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
                        ),
                        "sha256": (
                            "c3b127e39be1b335ff6046bb2435451acfc1b323839377033bf438ccd4a32954"
                        ),
                    },
                },
            }
        ],
    }
    _v034_validate_exact_json_contract(
        errors,
        failure_diagnostic_name,
        failure_diagnostics,
        expected_failure_diagnostic,
    )
    failure_diagnostic_records_value = failure_diagnostics.get("records", [])
    failure_diagnostic_records = (
        failure_diagnostic_records_value
        if isinstance(failure_diagnostic_records_value, list)
        else []
    )
    failure_diagnostic_record = (
        failure_diagnostic_records[0]
        if len(failure_diagnostic_records) == 1
        and isinstance(failure_diagnostic_records[0], dict)
        else {}
    )
    manifest_raw_root = pepglad_primary_method.get("raw_output_root", "")
    manifest_attempt_dir = (
        str(Path(manifest_raw_root).parent) if manifest_raw_root else ""
    )
    expected_attempt_suffix = (
        "benchmark_runs/v0.34/pepglad/"
        "v034_pepglad_3eqs_seed42/attempt_003"
    )
    summary_job_status = summary.get("job_status", {})
    if not isinstance(summary_job_status, dict):
        summary_job_status = {}
    if failure_diagnostic_record and not all(
        (
            failure_diagnostic_record.get("attempt_id")
            == pepglad_primary_execution.get("attempt_id")
            == pepglad_primary_run.get("attempt_id")
            == "attempt_003",
            failure_diagnostic_record.get("attempt_dir")
            == pepglad_primary_execution.get("attempt_dir")
            == manifest_attempt_dir,
            isinstance(failure_diagnostic_record.get("attempt_dir"), str),
            str(failure_diagnostic_record.get("attempt_dir", "")).replace(
                "\\", "/"
            ).endswith(expected_attempt_suffix),
            pepglad_primary_method.get("run_record_id")
            == "v034_pepglad_3eqs_seed42_attempt_003",
            pepglad_primary_method.get("exit_code") == "0",
            pepglad_primary_method.get("status_reason")
            == "pepglad_seed42_replay_mismatch",
            summary_job_status.get(pepglad_primary) == "evidence_incomplete",
            summary_job_status.get(pepglad_extension) == "not_run",
        )
    ):
        errors.append(
            f"{failure_diagnostic_name} record is not cross-bound to the "
            "PepGLAD attempt_003 failure rows"
        )
    if (
        pepglad_primary in candidate_by_id
        or pepglad_primary in qc_by_id
        or pepglad_primary in provenance_by_id
    ):
        errors.append(
            f"{failure_diagnostic_name} requires PepGLAD to remain absent from "
            "candidate, QC, and runtime provenance artifacts"
        )

    for artifact_name, rows in table_rows.items():
        for row in rows:
            text = " ".join(str(value) for value in row.values()).lower()
            for forbidden in [
                "benchmark_completed",
                "benchmark_ready",
                "best_performing",
                "performance_ranking",
                "scoring_passed",
                "ranking_passed",
                "scored_candidate",
                "ranked_candidate",
                "wet_lab_validated",
            ]:
                if forbidden in text:
                    errors.append(
                        f"{artifact_name}: {row.get('job_id', 'unknown')} overclaims {forbidden}"
                    )

    replay_diagnostic_tokens = [
        "attempt_003",
        "L6/D5",
        "L4/D7",
        "b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b",
        "e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6",
        "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26",
        "pre_openmm_snapshot",
    ]
    plan_text = (ROOT / "ops/plans/updated_plan_v0.34.md").read_text(encoding="utf-8")
    for token in [
        "Updated Plan v0.34",
        "7 种方法",
        "seed42",
        "seed43",
        "current.v034_bounded_connectivity",
        "不支持方法排名",
        "本阶段不启动 scoring",
        "不执行 ranking",
        "D-Flow",
        "PepGLAD seed43",
        *replay_diagnostic_tokens,
    ]:
        if token not in plan_text:
            errors.append(f"updated_plan_v0.34.md missing required token {token}")
    audit_text = (ROOT / "ops/audits/v034_bounded_connectivity_audit.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "v0.34 受限生成连通性审计",
        "7 种方法",
        "12 条 compact runtime provenance",
        "没有 scoring、ranking",
        "target_set_v0.csv",
        "1.2.21",
        "PepGLAD seed43",
        "not_run",
        *replay_diagnostic_tokens,
    ]:
        if token not in audit_text:
            errors.append(f"v034_bounded_connectivity_audit.md missing required token {token}")

    return {
        "jobs": len(job_rows),
        "execution_rows": len(execution_rows),
        "method_rows": len(method_rows),
        "candidate_rows": len(candidate_rows),
        "qc_rows": len(qc_rows),
        "run_rows": len(run_rows),
        "runtime_provenance_records": len(provenance_records),
        "failure_diagnostic_records": len(failure_diagnostic_records),
        "primary_supported": sum(
            1
            for job_id in supported_execution_ids
            if expected_specs.get(job_id, ("", "", "", ""))[1] == "primary"
        ),
        "extension_supported": sum(
            1
            for job_id in supported_execution_ids
            if expected_specs.get(job_id, ("", "", "", ""))[1] == "extension"
        ),
    }


def check_markdown_links(errors: list[str]) -> int:
    checked = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        rel_path = path.relative_to(ROOT)
        if is_acceptance_state_path(rel_path):
            continue
        if rel_path.parts and rel_path.parts[0] in RUNTIME_MARKDOWN_SKIP_DIRS:
            continue
        if len(rel_path.parts) >= 2 and rel_path.parts[:2] == ("sources", "raw_snapshots"):
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
                target_relative = target_path.relative_to(ROOT.resolve())
            except ValueError:
                continue
            if is_acceptance_state_path(target_relative):
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
        if any(
            marker in line
            for marker in [
                "避免",
                "不",
                "不能",
                "不得",
                "未",
                "尚未",
                "forbidden",
                "not",
                "does not",
                "no ",
            ]
        ):
            continue
        return True
    return False


def check_tracked_large_or_forbidden_files(errors: list[str]) -> int:
    completed = subprocess.run(
        [
            "git",
            *_GIT_CONFIG_ARGUMENTS,
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env=_sanitized_git_environment(),
    )
    checked = 0
    for rel in completed.stdout.splitlines():
        if is_acceptance_state_path(rel):
            continue
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-write-report",
        action="store_true",
        help="Run all checks and print JSON without updating the tracked report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    if errors:
        result = {"status": "fail", "errors": errors, "warnings": warnings}
        if not args.no_write_report:
            (ROOT / "ops/validation/wiki_validation_report.md").write_text(
                "# Wiki Validation Report\n\n```json\n"
                + json.dumps(result, ensure_ascii=False, indent=2)
                + "\n```\n",
                encoding="utf-8",
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for token in [
        "ops/plans/updated_plan_v0.9.md",
        "Skill Routing",
        "building-llm-wiki",
        "academic-research-suite",
        "benchmark-paper-template",
        "Supervisor-Skills",
        "benchmark-paper-template is the primary route",
        "intro-drafter is consistency-check only",
        "Execution Gates",
        "download_performed=no",
        "not_real_benchmark",
        "PYTHONUTF8",
        "scripts/validate_benchmark_kb.py",
    ]:
        if token not in agents_text:
            errors.append(f"AGENTS.md missing required local operating token {token}")

    master_rows = check_headers(errors, "kb/tables/master_literature_manifest.csv", MASTER_HEADERS)
    evidence_rows = check_headers(errors, "kb/tables/method_evidence_matrix.csv", EVIDENCE_HEADERS)
    score_rows = check_headers(errors, "kb/tables/candidate_method_scorecard.csv", SCORE_HEADERS)
    runnability_rows = check_headers(errors, "kb/tables/method_runnability_matrix.csv", RUNNABILITY_HEADERS)
    benchmark_lesson_rows = check_headers(
        errors,
        "kb/tables/benchmark_literature_lessons.csv",
        BENCHMARK_LITERATURE_HEADERS,
    )
    target_set_rows = check_headers(errors, "benchmark/input_sets/target_set_v0.csv", TARGET_SET_HEADERS)
    dataset_candidate_rows = check_headers(
        errors,
        "benchmark/input_sets/candidate_benchmark_datasets.csv",
        DATASET_CANDIDATE_HEADERS,
    )
    method_source_rows = check_headers(
        errors,
        "benchmark/method_sources/method_source_manifest.csv",
        METHOD_SOURCE_HEADERS,
    )
    homepage_method_source_count = check_homepage_method_sources(errors)
    environment_rows = check_headers(
        errors,
        "benchmark/environments/environment_feasibility_matrix.csv",
        ENVIRONMENT_HEADERS,
    )
    expert_review_rows = check_headers(errors, "kb/tables/expert_review_action_items.csv", EXPERT_REVIEW_HEADERS)
    dataset_readiness_rows = check_headers(
        errors,
        "benchmark/input_sets/dataset_readiness_scorecard.csv",
        DATASET_READINESS_HEADERS,
    )
    target_candidate_rows = check_headers(
        errors,
        "benchmark/input_sets/target_candidate_matrix_v0.4.csv",
        TARGET_CANDIDATE_HEADERS,
    )
    target_candidate_v05_rows = check_headers(
        errors,
        "benchmark/input_sets/target_candidate_matrix_v0.5.csv",
        TARGET_CANDIDATE_HEADERS,
    )
    source_pin_rows = check_headers(
        errors,
        "benchmark/method_sources/source_pin_audit_v0.4.csv",
        SOURCE_PIN_HEADERS,
    )
    source_pin_v05_rows = check_headers(
        errors,
        "benchmark/method_sources/source_pin_audit_v0.5.csv",
        SOURCE_PIN_HEADERS,
    )
    link_availability_rows = check_headers(
        errors,
        "benchmark/availability/link_availability_matrix_v0.5.csv",
        LINK_AVAILABILITY_HEADERS,
    )
    data_access_rows = check_headers(
        errors,
        "benchmark/availability/data_access_manifest_v0.5.csv",
        DATA_ACCESS_HEADERS,
    )
    ars_action_rows = check_headers(
        errors,
        "kb/tables/ars_review_action_items_v0.6.csv",
        ARS_REVIEW_ACTION_HEADERS,
    )
    dataset_watchlist_rows = check_headers(
        errors,
        "benchmark/input_sets/dataset_supplement_watchlist_v0.6.csv",
        DATASET_SUPPLEMENT_WATCHLIST_HEADERS,
    )
    example_run_rows = check_headers(
        errors,
        "benchmark/input_sets/example_run.csv",
        RUN_CSV_HEADERS,
    )
    example_job_manifest_rows = check_headers(
        errors,
        "benchmark/input_sets/example_job_manifest_v0.11.csv",
        JOB_MANIFEST_HEADERS,
    )
    download_manifest_rows = check_headers(
        errors,
        "benchmark/deployment/download_manifest_template_v0.7.csv",
        DOWNLOAD_MANIFEST_HEADERS,
    )
    dataset_schema_review_rows = check_headers(
        errors,
        "benchmark/input_sets/dataset_supplement_schema_review_v0.7.csv",
        DATASET_SCHEMA_REVIEW_HEADERS,
    )
    dataset_schema_review_v08_rows = check_headers(
        errors,
        "benchmark/input_sets/dataset_supplement_schema_review_v0.8.csv",
        DATASET_SCHEMA_REVIEW_V08_HEADERS,
    )
    download_manifest_v08_rows = check_headers(
        errors,
        "benchmark/deployment/download_manifest_v0.8.csv",
        DOWNLOAD_MANIFEST_HEADERS,
    )
    preflight_download_rows = check_headers(
        errors,
        "benchmark/deployment/preflight_download_approval_v0.10.csv",
        PREFLIGHT_DOWNLOAD_APPROVAL_HEADERS,
    )
    source_freshness_rows = check_headers(
        errors,
        "benchmark/deployment/source_freshness_manifest_v0.11.csv",
        SOURCE_FRESHNESS_HEADERS,
    )
    source_clone_rows = check_headers(
        errors,
        "benchmark/deployment/source_clone_manifest_v0.12.csv",
        SOURCE_CLONE_HEADERS,
    )
    docker_image_inventory_rows = check_headers(
        errors,
        "benchmark/deployment/docker_image_inventory_v0.13.csv",
        DOCKER_IMAGE_INVENTORY_HEADERS,
    )
    method_environment_assignment_rows = check_headers(
        errors,
        "benchmark/deployment/method_environment_assignment_v0.13.csv",
        METHOD_ENVIRONMENT_ASSIGNMENT_HEADERS,
    )
    method_paper_case_v014_rows = check_headers(
        errors,
        "benchmark/method_sources/method_paper_case_matrix_v0.14.csv",
        METHOD_PAPER_CASE_V014_HEADERS,
    )
    target_academic_search_v014_rows = check_headers(
        errors,
        "benchmark/input_sets/target_candidate_academic_search_v0.14.csv",
        TARGET_ACADEMIC_SEARCH_V014_HEADERS,
    )
    run_preflight_v015_rows = check_headers(
        errors,
        "benchmark/deployment/run_preflight_results_v0.15.csv",
        RUN_PREFLIGHT_RESULTS_V015_HEADERS,
    )
    batch_a_smoke_test_v015_rows = check_headers(
        errors,
        "benchmark/deployment/batch_a_smoke_test_results_v0.15.csv",
        BATCH_A_SMOKE_TEST_RESULTS_V015_HEADERS,
    )
    adapter_parser_hardening_v016_rows = check_headers(
        errors,
        "benchmark/deployment/adapter_parser_hardening_matrix_v0.16.csv",
        ADAPTER_PARSER_HARDENING_V016_HEADERS,
    )
    batch_b_target_review_v016_rows = check_headers(
        errors,
        "benchmark/input_sets/batch_b_target_review_queue_v0.16.csv",
        BATCH_B_TARGET_REVIEW_V016_HEADERS,
    )
    batch_b_pilot_target_gate_v017_rows = check_headers(
        errors,
        "benchmark/input_sets/batch_b_pilot_target_gate_v0.17.csv",
        BATCH_B_PILOT_TARGET_GATE_V017_HEADERS,
    )
    batch_b_pilot_method_scope_v017_rows = check_headers(
        errors,
        "benchmark/deployment/batch_b_pilot_method_scope_v0.17.csv",
        BATCH_B_PILOT_METHOD_SCOPE_V017_HEADERS,
    )
    batch_b_pilot_job_manifest_v017_rows = check_headers(
        errors,
        "benchmark/input_sets/batch_b_pilot_job_manifest_v0.17.csv",
        JOB_MANIFEST_HEADERS,
    )
    adapter_replay_fixture_v018_rows = check_headers(
        errors,
        "benchmark/deployment/adapter_replay_fixture_manifest_v0.18.csv",
        ADAPTER_REPLAY_FIXTURE_V018_HEADERS,
    )
    batch_a_replay_method_output_v018_rows = check_headers(
        errors,
        "benchmark/results/batch_a_replay_method_output_manifest_v0.18.csv",
        METHOD_OUTPUT_MANIFEST_HEADERS,
    )
    batch_a_replay_candidate_v018_rows = check_headers(
        errors,
        "benchmark/results/batch_a_replay_candidate_outputs_v0.18.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    batch_a_replay_run_v018_rows = check_headers(
        errors,
        "benchmark/results/batch_a_replay_run_v0.18.csv",
        RUN_CSV_HEADERS,
    )
    method_source_doc_v019_rows = check_headers(
        errors,
        "benchmark/deployment/method_source_doc_verification_v0.19.csv",
        METHOD_SOURCE_DOC_VERIFICATION_V019_HEADERS,
    )
    method_install_smoke_manifest_v019_rows = check_headers(
        errors,
        "benchmark/deployment/method_install_smoke_manifest_v0.19.csv",
        METHOD_INSTALL_SMOKE_MANIFEST_V019_HEADERS,
    )
    method_smoke_test_v019_rows = check_headers(
        errors,
        "benchmark/deployment/method_smoke_test_results_v0.19.csv",
        METHOD_SMOKE_TEST_RESULTS_V019_HEADERS,
    )
    method_unblock_manifest_v020_rows = check_headers(
        errors,
        "benchmark/deployment/method_unblock_manifest_v0.20.csv",
        METHOD_UNBLOCK_MANIFEST_V020_HEADERS,
    )
    method_unblock_smoke_v020_rows = check_headers(
        errors,
        "benchmark/deployment/method_unblock_smoke_results_v0.20.csv",
        METHOD_UNBLOCK_SMOKE_RESULTS_V020_HEADERS,
    )
    adapter_smoke_manifest_v021_rows = check_headers(
        errors,
        "benchmark/deployment/adapter_smoke_manifest_v0.21.csv",
        ADAPTER_SMOKE_MANIFEST_V021_HEADERS,
    )
    adapter_smoke_results_v021_rows = check_headers(
        errors,
        "benchmark/deployment/adapter_smoke_results_v0.21.csv",
        ADAPTER_SMOKE_RESULTS_V021_HEADERS,
    )
    blocker_asset_manifest_v021_rows = check_headers(
        errors,
        "benchmark/deployment/blocker_asset_manifest_v0.21.csv",
        BLOCKER_ASSET_MANIFEST_V021_HEADERS,
    )
    method_example_fixture_v022_rows = check_headers(
        errors,
        "benchmark/deployment/method_example_fixture_evidence_v0.22.csv",
        METHOD_EXAMPLE_FIXTURE_EVIDENCE_V022_HEADERS,
    )
    multi_case_fixture_target_v022_rows = check_headers(
        errors,
        "benchmark/input_sets/multi_case_fixture_target_manifest_v0.22.csv",
        MULTI_CASE_FIXTURE_TARGET_V022_HEADERS,
    )
    multi_case_fixture_control_v022_rows = check_headers(
        errors,
        "benchmark/input_sets/multi_case_fixture_control_manifest_v0.22.csv",
        MULTI_CASE_FIXTURE_CONTROL_V022_HEADERS,
    )
    multi_case_fixture_job_v022_rows = check_headers(
        errors,
        "benchmark/input_sets/multi_case_fixture_job_manifest_v0.22.csv",
        MULTI_CASE_FIXTURE_JOB_V022_HEADERS,
    )
    priority_gate_review_v022_rows = check_headers(
        errors,
        "benchmark/deployment/priority_gate_review_v0.22.csv",
        PRIORITY_GATE_REVIEW_V022_HEADERS,
    )
    notebook_cli_smoke_v023_rows = check_headers(
        errors,
        "benchmark/deployment/notebook_cli_smoke_manifest_v0.23.csv",
        NOTEBOOK_CLI_SMOKE_V023_HEADERS,
    )
    dflow_project_install_v023_rows = check_headers(
        errors,
        "benchmark/deployment/dflow_project_install_contract_v0.23.csv",
        DFLOW_PROJECT_INSTALL_V023_HEADERS,
    )
    external_dry_run_package_v023_rows = check_headers(
        errors,
        "benchmark/deployment/external_dry_run_package_manifest_v0.23.csv",
        EXTERNAL_DRY_RUN_PACKAGE_V023_HEADERS,
    )
    priority_gate_review_v023_rows = check_headers(
        errors,
        "benchmark/deployment/priority_gate_review_v0.23.csv",
        PRIORITY_GATE_REVIEW_V023_HEADERS,
    )
    dflow_input_contract_fixture_v024_rows = check_headers(
        errors,
        "benchmark/deployment/dflow_input_contract_fixture_v0.24.csv",
        DFLOW_INPUT_CONTRACT_FIXTURE_V024_HEADERS,
    )
    dflow_full_pepmerge_download_v025_rows = check_headers(
        errors,
        "benchmark/deployment/dflow_full_pepmerge_download_v0.25.csv",
        DFLOW_FULL_PEPMERGE_DOWNLOAD_V025_HEADERS,
    )
    dflow_colab_bindcraft_v026_rows = check_headers(
        errors,
        "benchmark/deployment/dflow_colabdesign_bindcraft_v0.26.csv",
        DFLOW_COLAB_BINDCRAFT_V026_HEADERS,
    )
    colabdesign_dexdesign_gate_v027_rows = check_headers(
        errors,
        "benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv",
        COLABDESIGN_DEXDESIGN_GATE_V027_HEADERS,
    )
    external_asset_rescue_v028_rows = check_headers(
        errors,
        "benchmark/deployment/external_asset_rescue_v0.28.csv",
        EXTERNAL_ASSET_RESCUE_V028_HEADERS,
    )
    bounded_generation_parser_v029_rows = check_headers(
        errors,
        "benchmark/deployment/bounded_generation_parser_v0.29.csv",
        BOUNDED_GENERATION_PARSER_V029_HEADERS,
    )
    pilot_benchmark_target_v030_rows = check_headers(
        errors,
        "benchmark/input_sets/pilot_benchmark_target_manifest_v0.30.csv",
        PILOT_BENCHMARK_TARGET_V030_HEADERS,
    )
    pilot_benchmark_control_v030_rows = check_headers(
        errors,
        "benchmark/input_sets/pilot_benchmark_control_manifest_v0.30.csv",
        PILOT_BENCHMARK_CONTROL_V030_HEADERS,
    )
    pilot_benchmark_job_v030_rows = check_headers(
        errors,
        "benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv",
        PILOT_BENCHMARK_JOB_V030_HEADERS,
    )
    pilot_execution_matrix_v030_rows = check_headers(
        errors,
        "benchmark/deployment/pilot_execution_matrix_v0.30.csv",
        PILOT_EXECUTION_MATRIX_V030_HEADERS,
    )
    wet_lab_candidate_panel_v030_rows = check_headers(
        errors,
        "benchmark/input_sets/wet_lab_candidate_panel_v0.30.csv",
        WET_LAB_CANDIDATE_PANEL_V030_HEADERS,
    )
    pilot_execution_results_v031_rows = check_headers(
        errors,
        "benchmark/deployment/pilot_execution_results_v0.31.csv",
        PILOT_EXECUTION_RESULTS_V031_HEADERS,
    )
    pilot_execution_results_v033_rows = check_headers(
        errors,
        "benchmark/deployment/pilot_execution_results_v0.33.csv",
        PILOT_EXECUTION_RESULTS_V031_HEADERS,
    )
    method_readiness_v08_rows = check_headers(
        errors,
        "benchmark/deployment/method_readiness_review_v0.8.csv",
        METHOD_READINESS_REVIEW_HEADERS,
    )
    method_preflight_rows = check_headers(
        errors,
        "benchmark/deployment/method_preflight_status_v0.10.csv",
        METHOD_PREFLIGHT_STATUS_HEADERS,
    )
    adapter_preflight_rows = check_headers(
        errors,
        "benchmark/deployment/adapter_preflight_status_v0.11.csv",
        ADAPTER_PREFLIGHT_HEADERS,
    )
    method_landscape_rows = check_headers(
        errors,
        "benchmark/method_sources/method_landscape_watchlist_v0.9.csv",
        METHOD_LANDSCAPE_HEADERS,
    )
    manuscript_sync_rows = check_headers(
        errors,
        "manuscript/support/benchmark_manuscript_sync_map_v1.csv",
        BILINGUAL_SYNC_HEADERS,
    )
    method_classification_rows = check_headers(
        errors,
        "kb/tables/candidate_method_classification_v1.csv",
        METHOD_CLASSIFICATION_HEADERS,
    )
    reference_dataset_source_rows = check_headers(
        errors,
        "benchmark/input_sets/reference_dataset_sources_v1.csv",
        REFERENCE_DATASET_SOURCE_HEADERS,
    )
    manuscript_todo_rows = check_headers(
        errors,
        "manuscript/support/benchmark_manuscript_todo_v1.csv",
        MANUSCRIPT_TODO_HEADERS,
    )
    manuscript_claim_rows = check_headers(
        errors,
        "manuscript/support/benchmark_manuscript_claim_evidence_map.csv",
        MANUSCRIPT_CLAIM_HEADERS,
    )
    supplementary_material_rows = check_headers(
        errors,
        "kb/tables/supplementary_materials_action_matrix_v1.1.csv",
        SUPPLEMENTARY_MATERIAL_HEADERS,
    )
    scoring_rationale_rows = check_headers(
        errors,
        "kb/tables/scoring_metric_rationale_matrix_v1.1.csv",
        SCORING_RATIONALE_HEADERS,
    )
    method_landscape_patch_rows = check_headers(
        errors,
        "kb/tables/method_landscape_patch_candidates_v1.1.csv",
        METHOD_LANDSCAPE_PATCH_HEADERS,
    )
    grant_review_action_rows = check_headers(
        errors,
        "kb/tables/grant_review_action_items_v1.3.csv",
        GRANT_REVIEW_ACTION_HEADERS,
    )
    migration_rows = check_headers(
        errors,
        "ops/migration/file_role_map_v0.10.csv",
        MIGRATION_FILE_ROLE_HEADERS,
    )
    method_output_manifest_rows = check_headers(
        errors,
        "benchmark/results/example_method_output_manifest_v0.11.csv",
        METHOD_OUTPUT_MANIFEST_HEADERS,
    )
    candidate_output_rows = check_headers(
        errors,
        "benchmark/results/example_candidate_outputs_v0.11.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    adapter_method_output_v021_rows = check_headers(
        errors,
        "benchmark/results/adapter_method_output_manifest_v0.21.csv",
        METHOD_OUTPUT_MANIFEST_HEADERS,
    )
    adapter_candidate_output_v021_rows = check_headers(
        errors,
        "benchmark/results/adapter_candidate_outputs_v0.21.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    adapter_run_rows_v021_rows = check_headers(
        errors,
        "benchmark/results/adapter_run_rows_v0.21.csv",
        RUN_CSV_HEADERS,
    )
    dflow_bounded_candidate_v026_rows = check_headers(
        errors,
        "benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    bindcraft_classification_v026_rows = check_headers(
        errors,
        "benchmark/results/bindcraft_wrapper_classification_v0.26.csv",
        BINDCRAFT_CLASSIFICATION_V026_HEADERS,
    )
    bindcraft_accepted_final_v028_rows = check_headers(
        errors,
        "benchmark/results/bindcraft_accepted_final_classification_v0.28.csv",
        BINDCRAFT_CLASSIFICATION_V026_HEADERS,
    )
    colabdesign_bounded_method_v029_rows = check_headers(
        errors,
        "benchmark/results/colabdesign_bounded_method_output_manifest_v0.29.csv",
        METHOD_OUTPUT_MANIFEST_HEADERS,
    )
    colabdesign_bounded_candidate_v029_rows = check_headers(
        errors,
        "benchmark/results/colabdesign_bounded_candidate_outputs_v0.29.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    bindcraft_accepted_candidate_v029_rows = check_headers(
        errors,
        "benchmark/results/bindcraft_accepted_candidate_outputs_v0.29.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    pilot_method_output_v031_rows = check_headers(
        errors,
        "benchmark/results/pilot_method_output_manifest_v0.31.csv",
        METHOD_OUTPUT_MANIFEST_HEADERS,
    )
    pilot_candidate_output_v031_rows = check_headers(
        errors,
        "benchmark/results/pilot_candidate_outputs_v0.31.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    pilot_run_v031_rows = check_headers(
        errors,
        "benchmark/results/pilot_run_v0.31.csv",
        PILOT_RUN_V031_HEADERS,
    )
    pilot_method_output_v033_rows = check_headers(
        errors,
        "benchmark/results/pilot_method_output_manifest_v0.33.csv",
        METHOD_OUTPUT_MANIFEST_HEADERS,
    )
    pilot_candidate_output_v033_rows = check_headers(
        errors,
        "benchmark/results/pilot_candidate_outputs_v0.33.csv",
        CANDIDATE_OUTPUT_HEADERS,
    )
    pilot_run_v033_rows = check_headers(
        errors,
        "benchmark/results/pilot_run_v0.33.csv",
        PILOT_RUN_V031_HEADERS,
    )
    v034_counts = check_v034_bounded_connectivity(errors)
    v035_bundle_path = (
        ROOT / "benchmark/results/pilot_pepglad_connectivity_v0.35.json"
    )
    if v035_bundle_path.is_file():
        validate_v035_pepglad_bundle(errors, warnings)
    _map_rows = check_headers(errors, "kb/references/zotero-map.tsv", ["zotero_key", "bibtex_key", "title"], delimiter="\t")

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

        smoke_path = ROOT / "benchmark/smoke_tests" / method_slug(method) / "README.md"
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

    if len(link_availability_rows) < 18:
        errors.append(
            "link_availability_matrix_v0.5.csv should contain method and dataset endpoint rows"
        )
    allowed_link_status = {"ok", "blocked", "metadata_only"}
    method_link_methods = {
        row.get("artifact_id", "")
        for row in link_availability_rows
        if row.get("artifact_type") == "method_repo" and row.get("status") in allowed_link_status
    }
    for method in included_method_names:
        if method not in method_link_methods:
            errors.append(f"{method}: missing v0.5 method repo link availability row")
    for row in link_availability_rows:
        if row.get("download_performed") != "no":
            errors.append(f"{row.get('record_id')}: v0.5 link audit must not download data or artifacts")
        if row.get("status") not in allowed_link_status:
            errors.append(f"{row.get('record_id')}: invalid link availability status {row.get('status')}")
        for required_field in ["record_id", "artifact_type", "artifact_id", "url", "check_method", "checked_at", "evidence", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('record_id')}: link availability row missing {required_field}")
        for field in ["status", "evidence", "next_action"]:
            value = row.get(field, "").lower()
            if "installed" in value or "reproduced" in value or "ran_locally" in value:
                errors.append(f"{row.get('record_id')}: link availability row overclaims {field}")

    source_pin_v05_by_method = {row.get("method", ""): row for row in source_pin_v05_rows}
    allowed_v05_pin_status = {"reachable_unpinned", "pinned_no_install", "blocked_metadata_only"}
    for method in included_method_names:
        row = source_pin_v05_by_method.get(method)
        if not row:
            errors.append(f"{method}: missing source_pin_audit_v0.5 row")
            continue
        if row.get("audit_status") not in allowed_v05_pin_status:
            errors.append(f"{method}: invalid v0.5 source pin status {row.get('audit_status')}")
        for required_field in ["repo_url", "default_branch", "commit_sha", "readme_entrypoint", "weights_policy", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{method}: source_pin_audit_v0.5 row missing {required_field}")
        for field in ["audit_status", "weights_policy", "batch_route", "next_action"]:
            value = row.get(field, "").lower()
            if "installed" in value or "reproduced" in value or "ran_locally" in value:
                errors.append(f"{method}: source_pin_audit_v0.5 row overclaims {field}")
    if len(source_pin_v05_rows) < len(included_method_names):
        errors.append(
            f"source_pin_audit_v0.5.csv should cover all include methods, found {len(source_pin_v05_rows)}"
        )

    if len(data_access_rows) < len(dataset_candidate_rows):
        errors.append(
            f"data_access_manifest_v0.5.csv should cover candidate datasets, found {len(data_access_rows)}"
        )
    data_access_by_dataset = {row.get("dataset_id", ""): row for row in data_access_rows}
    for dataset_id in dataset_by_id:
        if dataset_id not in data_access_by_dataset:
            errors.append(f"{dataset_id}: missing v0.5 data access manifest row")
    for row in data_access_rows:
        if row.get("download_performed") != "no":
            errors.append(f"{row.get('dataset_id')}: v0.5 data access row must not download data")
        for required_field in [
            "dataset_id",
            "endpoint_id",
            "url",
            "access_type",
            "checked_at",
            "availability_status",
            "direct_download_status",
            "recommended_use",
            "blocking_risk",
            "next_action",
        ]:
            if not row.get(required_field):
                errors.append(f"{row.get('dataset_id')}: data access row missing {required_field}")
    overath_data_access = data_access_by_dataset.get("overath_binder_success_2025", {})
    if overath_data_access:
        if "81981455" not in overath_data_access.get("content_length", ""):
            errors.append("Overath v0.5 data access must record final_dataset.csv byte size")
        recommended_use = overath_data_access.get("recommended_use", "").lower()
        if "generation" in recommended_use and "not_generation" not in recommended_use:
            errors.append("Overath v0.5 data access must not recommend peptide generation performance use")
    pepbi_data_access = data_access_by_dataset.get("pepbi_dryad_2025", {})
    if pepbi_data_access and "401" not in pepbi_data_access.get("direct_download_status", ""):
        errors.append("PEPBI v0.5 data access must record Dryad download HEAD 401 blocker")
    gpcr_data_access = data_access_by_dataset.get("gpcr_peptide_design_benchmark_2026", {})
    if gpcr_data_access and "no_external_data_route" not in gpcr_data_access.get("direct_download_status", ""):
        errors.append("GPCR v0.5 data access must remain pending external data route")

    if len(target_candidate_v05_rows) < len(target_candidate_rows):
        errors.append(
            "target_candidate_matrix_v0.5.csv should preserve at least the v0.4 candidate coverage"
        )
    for row in target_candidate_v05_rows:
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{row.get('candidate_id')}: invalid v0.5 target candidate task_id {row.get('task_id')}")
        if not row.get("decision"):
            errors.append(f"{row.get('candidate_id')}: missing v0.5 target candidate decision")

    deployment_text = (ROOT / "benchmark/deployment/server_readiness_checklist_v0.5.md").read_text(
        encoding="utf-8"
    )
    for token in ["Linux CUDA Conda", "External source root", "External data root", "PyRosetta", "不下载数据", "不得纳入本仓库 git"]:
        if token not in deployment_text:
            errors.append(f"server_readiness_checklist_v0.5.md missing required token {token}")

    if len(ars_action_rows) < 8:
        errors.append("ars_review_action_items_v0.6.csv should contain multi-role ARS action items")
    ars_roles = {row.get("reviewer_role", "") for row in ars_action_rows}
    for role in [
        "editor_in_chief",
        "methodology_reviewer",
        "domain_reviewer",
        "engineering_reproducibility",
        "devils_advocate",
        "data_statistics",
        "writing_claims",
    ]:
        if role not in ars_roles:
            errors.append(f"ars_review_action_items_v0.6.csv missing reviewer role {role}")
    allowed_ars_status = {"open", "done", "defer"}
    required_gates = {
        "metadata_ready",
        "source_pinned",
        "license_checked",
        "weights_manifested",
        "input_contract_ready",
        "dry_run_ready",
        "smoke_test_ready",
        "claim_gate",
    }
    observed_gates = set()
    for row in ars_action_rows:
        if row.get("severity") not in {"critical", "major", "minor"}:
            errors.append(f"ARS action has invalid severity: {row.get('issue')}")
        if row.get("status") not in allowed_ars_status:
            errors.append(f"ARS action has invalid status: {row.get('issue')}")
        observed_gates.add(row.get("gate", ""))
        for required_field in ["artifact", "issue", "recommendation", "decision", "evidence", "next_action", "gate"]:
            if not row.get(required_field):
                errors.append(f"ARS action row missing {required_field}: {row.get('issue')}")
    if "claim_gate" not in observed_gates or "dry_run_ready" not in observed_gates:
        errors.append("ARS action items must include claim_gate and dry_run_ready gates")

    if len(dataset_watchlist_rows) < 5:
        errors.append("dataset_supplement_watchlist_v0.6.csv should contain supplemental dataset candidates")
    watchlist_ids = {row.get("candidate_id", "") for row in dataset_watchlist_rows}
    for candidate_id in ["gpcr_peptide_benchmark_2026", "pepbenchmark_2026", "tcrtransbench_2026"]:
        if candidate_id not in watchlist_ids:
            errors.append(f"dataset_supplement_watchlist_v0.6.csv missing {candidate_id}")
    for row in dataset_watchlist_rows:
        for required_field in ["source_name", "source_url", "task_relevance", "readiness_decision", "risks", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('candidate_id')}: dataset watchlist row missing {required_field}")
        decision = row.get("readiness_decision", "").lower()
        if "frozen" in decision or "ready_for_benchmark" in decision:
            errors.append(f"{row.get('candidate_id')}: watchlist decision must not imply frozen benchmark readiness")

    server_contract = (ROOT / "benchmark/deployment/server_smoke_test_contract_v0.6.md").read_text(
        encoding="utf-8"
    )
    for token in required_gates:
        if token not in server_contract:
            errors.append(f"server_smoke_test_contract_v0.6.md missing gate {token}")
    for forbidden in ["code confirmed problem-free", "benchmark completed", "method A outperforms method B"]:
        if forbidden not in server_contract:
            errors.append(f"server_smoke_test_contract_v0.6.md missing forbidden wording guard {forbidden}")

    ars_review_text = (ROOT / "ops/audits/academic_research_suite_review_v0.6.md").read_text(
        encoding="utf-8"
    )
    for token in ["Material Passport", "Major Revision Before Execution", "Devil's Advocate Review", "Web Refresh Notes"]:
        if token not in ars_review_text:
            errors.append(f"academic_research_suite_review_v0.6.md missing required section {token}")
    updated_plan_text = (ROOT / "ops/plans/updated_plan_v0.6.md").read_text(encoding="utf-8")
    for token in ["Revised Execution Gates", "Updated Dataset Policy", "Updated Method Policy", "Out Of Scope"]:
        if token not in updated_plan_text:
            errors.append(f"updated_plan_v0.6.md missing required section {token}")

    if len(example_run_rows) < 2:
        errors.append("example_run.csv should contain placeholder rows for PepMLM and RFdiffusion + ProteinMPNN")
    for row in example_run_rows:
        if row.get("status") != "not_real_benchmark":
            errors.append(f"{row.get('design_id')}: example_run status must be not_real_benchmark")
        if row.get("method") not in {"PepMLM", "RFdiffusion + ProteinMPNN"}:
            errors.append(f"{row.get('design_id')}: example_run should only cover v0.7 priority methods")
        if "placeholder" not in row.get("target_id", "").lower():
            errors.append(f"{row.get('design_id')}: example_run target_id must remain placeholder")
        if "not a benchmark" not in row.get("notes", "").lower() and "not_real" not in row.get("notes", "").lower():
            errors.append(f"{row.get('design_id')}: example_run notes must state it is not benchmark evidence")

    if len(example_job_manifest_rows) < 2:
        errors.append("example_job_manifest_v0.11.csv should contain placeholder jobs for Batch A")
    for row in example_job_manifest_rows:
        if row.get("status") != "not_real_benchmark":
            errors.append(f"{row.get('job_id')}: example job manifest status must be not_real_benchmark")
        if row.get("method") not in {"PepMLM", "RFdiffusion + ProteinMPNN"}:
            errors.append(f"{row.get('job_id')}: example job manifest should only cover Batch A methods")
        if row.get("task_id") not in {"T1_sequence_binder", "T3_miniprotein_binder_baseline"}:
            errors.append(f"{row.get('job_id')}: invalid Batch A task_id {row.get('task_id')}")
        if "placeholder" not in row.get("target_id", "").lower():
            errors.append(f"{row.get('job_id')}: example job target_id must remain placeholder")
        if "not a benchmark" not in row.get("notes", "").lower() and "placeholder" not in row.get("notes", "").lower():
            errors.append(f"{row.get('job_id')}: example job notes must state placeholder/non-benchmark status")

    if not download_manifest_rows:
        errors.append("download_manifest_template_v0.7.csv should contain a placeholder row")
    for row in download_manifest_rows:
        if row.get("download_performed") != "no":
            errors.append(f"{row.get('artifact_id')}: download manifest must not record downloads")
        if row.get("local_destination") != "server_path_placeholder":
            errors.append(f"{row.get('artifact_id')}: download manifest local_destination must remain placeholder")
        if row.get("source_url").startswith("http"):
            errors.append(f"{row.get('artifact_id')}: v0.7 download manifest must not contain actionable download URLs")

    if len(dataset_schema_review_rows) < 6:
        errors.append("dataset_supplement_schema_review_v0.7.csv should review all v0.6 watchlist entries")
    schema_review_ids = {row.get("candidate_id", "") for row in dataset_schema_review_rows}
    for candidate_id in ["overath_binder_success_2025", "pepbi_dryad_2025", "pepbenchmark_2026", "gpcr_peptide_benchmark_2026", "tcrtransbench_2026", "chang_af2_ranking_cases_2023"]:
        if candidate_id not in schema_review_ids:
            errors.append(f"dataset_supplement_schema_review_v0.7.csv missing {candidate_id}")
    for row in dataset_schema_review_rows:
        decision = row.get("decision", "").lower()
        if "frozen" in decision or "ready_for_target_set" in decision:
            errors.append(f"{row.get('candidate_id')}: schema review must not imply target-set promotion")
        for required_field in ["license_status", "schema_status", "controls_status", "leakage_status", "download_route_status", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('candidate_id')}: schema review row missing {required_field}")

    if len(dataset_schema_review_v08_rows) < 6:
        errors.append("dataset_supplement_schema_review_v0.8.csv should review all v0.6 watchlist entries")
    schema_review_v08_ids = {row.get("candidate_id", "") for row in dataset_schema_review_v08_rows}
    for candidate_id in [
        "overath_binder_success_2025",
        "pepbi_dryad_2025",
        "pepbenchmark_2026",
        "gpcr_peptide_benchmark_2026",
        "tcrtransbench_2026",
        "chang_af2_ranking_cases_2023",
    ]:
        if candidate_id not in schema_review_v08_ids:
            errors.append(f"dataset_supplement_schema_review_v0.8.csv missing {candidate_id}")
    for row in dataset_schema_review_v08_rows:
        decision = row.get("decision", "").lower()
        if "frozen" in decision or "ready_for_target_set" in decision:
            errors.append(f"{row.get('candidate_id')}: v0.8 schema review must not imply target-set promotion")
        if not row.get("audit_evidence", "").startswith("http"):
            errors.append(f"{row.get('candidate_id')}: v0.8 schema review must cite external audit evidence URL")
        for required_field in ["license_status", "schema_status", "controls_status", "leakage_status", "download_route_status", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('candidate_id')}: v0.8 schema review row missing {required_field}")

    if len(download_manifest_v08_rows) < 5:
        errors.append("download_manifest_v0.8.csv should record future routes for datasets and priority method weights")
    for row in download_manifest_v08_rows:
        if row.get("download_performed") != "no":
            errors.append(f"{row.get('artifact_id')}: v0.8 download manifest must not record completed downloads")
        if not row.get("local_destination", "").startswith("/srv/pep_design/"):
            errors.append(f"{row.get('artifact_id')}: v0.8 download destination should be an external /srv/pep_design path")
        if not row.get("source_url", "").startswith("http"):
            errors.append(f"{row.get('artifact_id')}: v0.8 download manifest rows should cite an HTTP source route")

    method_readiness_keys = {(row.get("method", ""), row.get("component", "")) for row in method_readiness_v08_rows}
    for method in ["PepMLM", "RFdiffusion", "ProteinMPNN", "PepMirror"]:
        if not any(key[0] == method for key in method_readiness_keys):
            errors.append(f"method_readiness_review_v0.8.csv missing {method}")
    for row in method_readiness_v08_rows:
        gate = row.get("current_gate", "")
        if gate == "smoke_test_ready":
            errors.append(f"{row.get('method')}: v0.8 method readiness must not mark smoke_test_ready")
        for required_field in ["license_status", "license_evidence", "input_contract_status", "environment_status", "blocking_items", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('method')}: v0.8 method readiness row missing {required_field}")

    if len(method_landscape_rows) < 25:
        errors.append("method_landscape_watchlist_v0.9.csv should contain the review-derived method landscape")
    allowed_pool_status = {"included", "candidate_watchlist", "review_only"}
    allowed_paradigms = {"sequence_driven", "structure_driven", "function_property_driven"}
    allowed_landscape_tasks = set(REQUIRED_PROTOCOL_TASKS) | {"ranking_developability", "ranking_rescoring"}
    landscape_by_method = {row.get("method", ""): row for row in method_landscape_rows}
    for method in included_method_names:
        row = landscape_by_method.get(method)
        if not row:
            errors.append(f"method_landscape_watchlist_v0.9.csv missing included method {method}")
        elif row.get("project_pool_status") != "included":
            errors.append(f"{method}: v0.9 method landscape must keep included methods labelled included")
    for method in ["PepFlow", "BoltzDesign1"]:
        if landscape_by_method.get(method, {}).get("project_pool_status") != "candidate_watchlist":
            errors.append(f"{method}: v0.9 method landscape must keep scorecard watchlist methods as candidate_watchlist")
    for method in ["PepMimic", "PPFlow", "CpSDE", "CP-Composer", "PepINVENT", "HELM-GPT", "NCFlow"]:
        if landscape_by_method.get(method, {}).get("project_pool_status") != "review_only":
            errors.append(f"{method}: v0.9 landscape additions must remain review_only")
    for row in method_landscape_rows:
        if row.get("project_pool_status") not in allowed_pool_status:
            errors.append(f"{row.get('method')}: invalid v0.9 project_pool_status {row.get('project_pool_status')}")
        if row.get("generation_paradigm") not in allowed_paradigms:
            errors.append(f"{row.get('method')}: invalid generation_paradigm {row.get('generation_paradigm')}")
        if row.get("mapped_task_id") not in allowed_landscape_tasks:
            errors.append(f"{row.get('method')}: invalid mapped_task_id {row.get('mapped_task_id')}")
        for required_field in ["representative_paper", "peptide_topology", "target_conditioning", "benchmark_relevance", "risks", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('method')}: v0.9 method landscape row missing {required_field}")

    current_plan_text = (ROOT / "ops/plans/updated_plan_v0.33.md").read_text(encoding="utf-8")
    for token in [
        "Updated Plan v0.33",
        "Current Position",
        "v0.33 Work Package",
        "Execution Boundary",
        "Next Work Package",
        "Claim Gate",
    ]:
        if token not in current_plan_text:
            errors.append(f"updated_plan_v0.33.md missing required section {token}")
    for forbidden in ["download_performed=yes", "smoke_test_ready | reached", "target_set_v0.csv 已冻结"]:
        if forbidden in current_plan_text:
            errors.append(f"updated_plan_v0.33.md contains overclaim boundary violation: {forbidden}")

    benchmark_template_text = (ROOT / "manuscript/support/benchmark_template_audit.md").read_text(encoding="utf-8")
    for token in ["Five-Pillar Completeness Table", "Introduction Six-Part Logic Chain", "Pre-Submission Self-Check", "NOT READY"]:
        if token not in benchmark_template_text:
            errors.append(f"benchmark_template_audit.md missing Benchmark template token {token}")
    intro_logic_text = (ROOT / "manuscript/support/benchmark_intro_logic_chain.md").read_text(encoding="utf-8")
    for token in ["Background + Running Example", "Existing-Benchmark Limitations", "Research Questions", "Design Considerations", "Our Proposal", "Contributions"]:
        if token not in intro_logic_text:
            errors.append(f"benchmark_intro_logic_chain.md missing six-part Introduction token {token}")
    review_synthesis_text = (ROOT / "manuscript/support/review_synthesis_benchmark_framework_supplement.md").read_text(
        encoding="utf-8"
    )
    for token in ["生成范式分类轴", "方法覆盖图与缺口", "PepMimic ≠ PepMirror", "PPFlow ≠ PepFlow", "Claim Boundary"]:
        if token not in review_synthesis_text:
            errors.append(f"review_synthesis_benchmark_framework_supplement.md missing v0.9 synthesis token {token}")
    supplementary_text = (ROOT / "manuscript/support/supplementary_materials_reference_value_v1.1.md").read_text(
        encoding="utf-8"
    )
    for token in ["source discovery", "docking score", "topology-aware", "Flow matching", "patch candidate"]:
        if token not in supplementary_text:
            errors.append(f"supplementary_materials_reference_value_v1.1.md missing v1.1 token {token}")
    short_scoring_text = (ROOT / "manuscript/support/short_peptide_scoring_rationale_v1.1.md").read_text(encoding="utf-8")
    for token in ["binding region", "N/C orientation", "key residue", "comparability", "不得写"]:
        if token not in short_scoring_text:
            errors.append(f"short_peptide_scoring_rationale_v1.1.md missing v1.1 scoring token {token}")
    cyclic_supplement_text = (ROOT / "manuscript/support/cyclic_peptide_benchmark_supplement_v1.1.md").read_text(
        encoding="utf-8"
    )
    for token in ["Topology-Aware Fields", "cyclization_mode", "chirality_detail", "HELM", "CHUCKLES", "patch_candidate"]:
        if token not in cyclic_supplement_text:
            errors.append(f"cyclic_peptide_benchmark_supplement_v1.1.md missing v1.1 cyclic token {token}")

    server_contract_paths = [
        ROOT / "benchmark/deployment/method_contracts/pepmlm_server_contract_v0.7.md",
        ROOT / "benchmark/deployment/method_contracts/rfdiffusion_proteinmpnn_server_contract_v0.7.md",
    ]
    for path in server_contract_paths:
        text = path.read_text(encoding="utf-8")
        for token in ["current_gate", "repo", "External Roots", "Failure States", "planning_only"]:
            if token not in text:
                errors.append(f"{path.relative_to(ROOT)} missing method contract token {token}")
        if "smoke_test_ready" in text and "max_allowed_gate_in_kb | `dry_run_ready`" not in text:
            errors.append(f"{path.relative_to(ROOT)} must not promote a method to smoke_test_ready")
    pepmirror_contract = (ROOT / "benchmark/deployment/method_contracts/pepmirror_dependency_contract_v0.7.md").read_text(
        encoding="utf-8"
    )
    if "current_gate | `source_pinned`" not in pepmirror_contract:
        errors.append("PepMirror dependency contract must remain source_pinned")
    for token in ["Blocking Dependencies", "PyRosetta", "Zenodo checkpoint", "dependency_contract_only_no_run"]:
        if token not in pepmirror_contract:
            errors.append(f"pepmirror_dependency_contract_v0.7.md missing dependency token {token}")

    protocol_text = (ROOT / "benchmark/protocols/benchmark_protocol_v0.md").read_text(encoding="utf-8")
    for task in REQUIRED_PROTOCOL_TASKS:
        if task not in protocol_text:
            errors.append(f"benchmark_protocol_v0.md missing task {task}")
    for token in ["Generation Versus Ranking Tracks", "Target Set And Controls", "Leakage And Homology Control"]:
        if token not in protocol_text:
            errors.append(f"benchmark_protocol_v0.md missing required section {token}")

    scoring_schema = (ROOT / "benchmark/protocols/scoring_outputs_schema.md").read_text(encoding="utf-8")
    for filename in REQUIRED_SCORING_OUTPUTS:
        if filename not in scoring_schema:
            errors.append(f"scoring_outputs_schema.md missing output table {filename}")
    scoring_protocol = (ROOT / "benchmark/scoring/scoring_protocol_v0.md").read_text(encoding="utf-8")
    for family in ["developability", "negative_design", "leakage_homology"]:
        if family not in scoring_protocol:
            errors.append(f"scoring_protocol_v0.md missing metric family {family}")

    manuscript_outline = (ROOT / "manuscript/outlines/benchmark_manuscript_outline.md").read_text(encoding="utf-8")
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

    zh_outline = (ROOT / "manuscript/outlines/benchmark_manuscript_outline_zh_v1.md").read_text(encoding="utf-8")
    en_outline = (ROOT / "manuscript/outlines/benchmark_manuscript_outline_en_v1.md").read_text(encoding="utf-8")
    zh_required = ["题名", "摘要", "候选方法分类与代码位置", "参考数据集来源与靶点集计划", "待办清单", "参考文献与引用边界"]
    en_required = ["Title", "Abstract", "Candidate Method Taxonomy and Code Routes", "Reference Dataset Sources and Target-Set Planning", "TODO List", "References and Citation Boundary"]
    for token in zh_required:
        if token not in zh_outline:
            errors.append(f"benchmark_manuscript_outline_zh_v1.md missing token {token}")
    for token in en_required:
        if token not in en_outline:
            errors.append(f"benchmark_manuscript_outline_en_v1.md missing token {token}")
    for token in ["v1.1 补充资料驱动的评分边界", "对接评分", "拓扑感知评价", "补丁候选"]:
        if token not in zh_outline:
            errors.append(f"benchmark_manuscript_outline_zh_v1.md missing v1.1 token {token}")
    for token in [
        "图表草稿与嵌入表格",
        "assets/figures/benchmark_figure1_overview_v1.png",
        "assets/figures/benchmark_figure2_task_method_matrix_v1.png",
        "assets/figures/benchmark_figure3_dual_track_v1.png",
        "assets/figures/benchmark_figure4_scoring_architecture_v1.png",
        "kb/tables/candidate_method_classification_v1.csv",
        "benchmark/input_sets/reference_dataset_sources_v1.csv",
        "kb/tables/scoring_metric_rationale_matrix_v1.1.csv",
        "benchmark/deployment/method_readiness_review_v0.8.csv",
        "不代表真实 benchmark 结果",
    ]:
        if token not in zh_outline:
            errors.append(f"benchmark_manuscript_outline_zh_v1.md missing embedded figure/table token {token}")
    for token in ["v1.1 Supplementary-source scoring boundary", "docking score", "topology-aware", "patch candidates"]:
        if token not in en_outline:
            errors.append(f"benchmark_manuscript_outline_en_v1.md missing v1.1 token {token}")
    for forbidden in ["性能最佳", "已复现", "已经完成性能排名"]:
        if has_unqualified_forbidden_wording(zh_outline, forbidden):
            errors.append(f"benchmark_manuscript_outline_zh_v1.md contains unsupported claim wording: {forbidden}")
    for forbidden in ["outperforms", "locally reproduced", "benchmark has been completed"]:
        if has_unqualified_forbidden_wording(en_outline, forbidden):
            errors.append(f"benchmark_manuscript_outline_en_v1.md contains unsupported claim wording: {forbidden}")

    sync_ids = [row.get("section_id", "") for row in manuscript_sync_rows]
    if len(sync_ids) < 15:
        errors.append("benchmark_manuscript_sync_map_v1.csv should cover the full bilingual outline")
    if "S10A" not in sync_ids:
        errors.append("benchmark_manuscript_sync_map_v1.csv missing v1.1 supplementary scoring section S10A")
    if len(sync_ids) != len(set(sync_ids)):
        errors.append("benchmark_manuscript_sync_map_v1.csv contains duplicate section_id values")
    for row in manuscript_sync_rows:
        if row.get("status") != "aligned":
            errors.append(f"{row.get('section_id')}: bilingual sync row must be aligned")
        for required_field in ["zh_section", "en_section", "shared_artifacts", "claim_ids", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('section_id')}: bilingual sync row missing {required_field}")

    classification_by_method = {row.get("method", ""): row for row in method_classification_rows}
    if len(method_classification_rows) < len(method_landscape_rows):
        errors.append("candidate_method_classification_v1.csv should cover all v0.9 landscape methods")
    for method in included_method_names:
        row = classification_by_method.get(method)
        if not row:
            errors.append(f"candidate_method_classification_v1.csv missing included method {method}")
        elif row.get("pool_status") != "included":
            errors.append(f"{method}: candidate classification must mark included methods as included")
    for method in ["PepFlow", "BoltzDesign1"]:
        row = classification_by_method.get(method)
        if not row:
            errors.append(f"candidate_method_classification_v1.csv missing watchlist method {method}")
        elif row.get("pool_status") != "candidate_watchlist":
            errors.append(f"{method}: candidate classification must keep watchlist status")
    for row in method_classification_rows:
        if row.get("pool_status") not in {"included", "candidate_watchlist", "review_only"}:
            errors.append(f"{row.get('method')}: invalid pool_status {row.get('pool_status')}")
        for required_field in ["task_id", "method_family", "design_paradigm", "peptide_type", "input_requirement", "output_type", "code_url", "source_status", "current_gate", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('method')}: candidate classification row missing {required_field}")
        if row.get("pool_status") in {"included", "candidate_watchlist"} and row.get("code_url") == "pending_source_audit":
            errors.append(f"{row.get('method')}: include/watchlist method must have a concrete code route or explicit pending public route")
        if "installed" in row.get("source_status", "").lower() or "reproduced" in row.get("source_status", "").lower():
            errors.append(f"{row.get('method')}: classification source_status must not imply installation or reproduction")

    expected_supplementary_sources = {
        "short_peptide_docking_score_note",
        "wang_liang_peptide_review_draft",
        "jmc2025_cyclic_peptide_review",
        "cas_insights_cyclic_peptide_trends",
        "flow_matching_life_science_note",
        "cyclic_ai_methods_review_note",
    }
    observed_supplementary_sources = {row.get("source_id", "") for row in supplementary_material_rows}
    missing_sources = sorted(expected_supplementary_sources - observed_supplementary_sources)
    if missing_sources:
        errors.append("supplementary_materials_action_matrix_v1.1.csv missing sources: " + ", ".join(missing_sources))
    if len(supplementary_material_rows) < 6:
        errors.append("supplementary_materials_action_matrix_v1.1.csv should cover all six supplementary materials")
    for row in supplementary_material_rows:
        if not row.get("source_path", "").startswith("G:\\Downloads\\Markdown笔记\\"):
            errors.append(f"{row.get('source_id')}: supplementary source_path must remain an external read-only note path")
        if row.get("priority") not in {"high", "medium", "low"}:
            errors.append(f"{row.get('source_id')}: invalid supplementary priority {row.get('priority')}")
        if row.get("status") not in {"integrated_v1.1", "integrated_existing_plus_v1.1", "pending"}:
            errors.append(f"{row.get('source_id')}: invalid supplementary status {row.get('status')}")
        if (
            "primary_source" not in row.get("evidence_boundary", "")
            and "framing" not in row.get("evidence_boundary", "")
            and "not_benchmark" not in row.get("evidence_boundary", "")
            and "background" not in row.get("evidence_boundary", "")
        ):
            errors.append(f"{row.get('source_id')}: supplementary evidence boundary should state source/framing/non-benchmark limits")

    scoring_checks = {row.get("metric_or_check", "") for row in scoring_rationale_rows}
    for metric in [
        "binding_region_correctness",
        "terminal_orientation_status",
        "key_residue_match_status",
        "conformational_plausibility",
        "score_comparability_group",
        "cyclization_mode",
        "chirality_detail",
        "non_natural_residue_representation",
        "metadata_level_developability",
        "flow_matching_paradigm_label",
    ]:
        if metric not in scoring_checks:
            errors.append(f"scoring_metric_rationale_matrix_v1.1.csv missing metric/check {metric}")
    for row in scoring_rationale_rows:
        if row.get("metric_family") not in {
            "interface_geometry",
            "design_feasibility",
            "structure_similarity",
            "ranking_rescoring",
            "developability",
            "method_landscape",
        }:
            errors.append(f"{row.get('metric_or_check')}: invalid v1.1 metric_family {row.get('metric_family')}")
        for required_field in ["why_needed", "source_support", "claim_boundary", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('metric_or_check')}: scoring rationale row missing {required_field}")

    expected_patch_methods = {
        "RFpeptides",
        "CyclicMPNN",
        "PPFlow",
        "PepMimic",
        "PocketXMol",
        "BoltzGen",
        "PepINVENT",
        "HELM-GPT",
    }
    observed_patch_methods = {row.get("method", "") for row in method_landscape_patch_rows}
    missing_patch_methods = sorted(expected_patch_methods - observed_patch_methods)
    if missing_patch_methods:
        errors.append("method_landscape_patch_candidates_v1.1.csv missing methods: " + ", ".join(missing_patch_methods))
    for row in method_landscape_patch_rows:
        if row.get("patch_status") != "patch_candidate":
            errors.append(f"{row.get('method')}: v1.1 method patch status must remain patch_candidate")
        if row.get("proposed_pool_status") == "included":
            errors.append(f"{row.get('method')}: v1.1 patch candidates must not be promoted to included")
        if row.get("primary_source_status") != "needs_primary_source_verification":
            errors.append(f"{row.get('method')}: v1.1 patch candidate must require primary-source verification")
        if row.get("related_task_id") not in {"T1_sequence_binder", "T2_structure_peptide_binder", "T3_miniprotein_binder_baseline", "method_landscape_only"}:
            errors.append(f"{row.get('method')}: invalid v1.1 related_task_id {row.get('related_task_id')}")

    grant_review_text = (ROOT / "ops/audits/grant_style_mock_review_v1.3.md").read_text(encoding="utf-8")
    for token in [
        "NIH-style mock review",
        "NSF-style mock review",
        "Overall Impact",
        "Significance",
        "Approach",
        "Broader impacts",
        "No benchmark execution",
        "Major Revision Before Execution",
    ]:
        if token not in grant_review_text:
            errors.append(f"grant_style_mock_review_v1.3.md missing token {token}")
    updated_plan_v13 = (ROOT / "ops/plans/updated_plan_v1.3.md").read_text(encoding="utf-8")
    for token in [
        "v0.10 Preflight Package",
        "Specific Aim 1",
        "Specific Aim 2",
        "Specific Aim 3",
        "No clone",
        "No download",
        "No GPU",
        "updated_plan_v0.9.md",
    ]:
        if token not in updated_plan_v13:
            errors.append(f"updated_plan_v1.3.md missing token {token}")
    if len(grant_review_action_rows) < 10:
        errors.append("grant_review_action_items_v1.3.csv should contain at least 10 action rows")
    observed_review_panels = {row.get("review_panel", "") for row in grant_review_action_rows}
    for panel in ["NIH", "NSF", "Data_Sharing", "Risk", "Budget"]:
        if panel not in observed_review_panels:
            errors.append(f"grant_review_action_items_v1.3.csv missing review panel {panel}")
    observed_gates = {row.get("gate", "") for row in grant_review_action_rows}
    for gate in ["target_gate", "execution_gate", "scoring_gate", "dissemination_gate"]:
        if gate not in observed_gates:
            errors.append(f"grant_review_action_items_v1.3.csv missing gate {gate}")
    if not any(row.get("severity") == "critical" for row in grant_review_action_rows):
        errors.append("grant_review_action_items_v1.3.csv should include at least one critical item")
    for row in grant_review_action_rows:
        if row.get("severity") not in {"critical", "major", "minor"}:
            errors.append(f"{row.get('criterion')}: invalid grant review severity {row.get('severity')}")
        if row.get("status") not in {"open", "done", "deferred"}:
            errors.append(f"{row.get('criterion')}: invalid grant review status {row.get('status')}")
        for required_field in ["artifact", "issue", "recommendation", "decision", "evidence", "next_action", "gate"]:
            if not row.get(required_field):
                errors.append(f"{row.get('criterion')}: grant review row missing {required_field}")
        if row.get("status") == "done":
            errors.append(f"{row.get('criterion')}: v1.3 grant review action rows should not imply completed execution")

    server_preflight_text = (ROOT / "ops/plans/server_preflight_plan_v0.10.md").read_text(encoding="utf-8")
    for token in [
        "不 clone",
        "不下载",
        "Batch A",
        "dry_run_ready",
        "download_performed=no",
        "/srv/pep_design",
    ]:
        if token not in server_preflight_text:
            errors.append(f"server_preflight_plan_v0.10.md missing token {token}")

    target_freeze_text = (ROOT / "benchmark/input_sets/target_control_freeze_checklist_v0.10.md").read_text(
        encoding="utf-8"
    )
    for token in ["schema-only", "license", "assay", "positive control", "negative control", "leakage", "No row"]:
        if token not in target_freeze_text:
            errors.append(f"target_control_freeze_checklist_v0.10.md missing token {token}")

    preflight_artifact_ids = {row.get("artifact_id", "") for row in preflight_download_rows}
    for artifact_id in [
        "pepmlm_hf_model_snapshot",
        "rfdiffusion_base_ckpt",
        "proteinmpnn_repo_weights",
        "pepmirror_cross_both_v1_ckpt",
        "overath_final_dataset_csv",
    ]:
        if artifact_id not in preflight_artifact_ids:
            errors.append(f"preflight_download_approval_v0.10.csv missing {artifact_id}")
    for row in preflight_download_rows:
        if row.get("download_performed") != "no":
            errors.append(f"{row.get('artifact_id')}: v0.10 preflight rows must keep download_performed=no")
        if row.get("approved_by") != "pending":
            errors.append(f"{row.get('artifact_id')}: v0.10 preflight approval must remain pending")
        for required_field in ["source_url", "license_status", "external_destination", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('artifact_id')}: preflight download row missing {required_field}")

    preflight_methods = {row.get("method", ""): row for row in method_preflight_rows}
    for method in ["PepMLM", "RFdiffusion + ProteinMPNN", "PepMirror"]:
        if method not in preflight_methods:
            errors.append(f"method_preflight_status_v0.10.csv missing {method}")
    for row in method_preflight_rows:
        if row.get("max_allowed_gate") not in {"dry_run_ready", "input_contract_ready", "source_pinned"}:
            errors.append(f"{row.get('method')}: invalid v0.10 max_allowed_gate {row.get('max_allowed_gate')}")
        text = " ".join(row.values()).lower()
        for forbidden in ["installed", "reproduced", "smoke_test_ready", "benchmark_ready"]:
            if forbidden in text:
                errors.append(f"{row.get('method')}: v0.10 method preflight must not imply {forbidden}")
        if "/srv/pep_design" not in row.get("external_roots", ""):
            errors.append(f"{row.get('method')}: v0.10 method preflight must keep external roots outside KB")

    source_freshness_methods = {row.get("method_or_artifact", ""): row for row in source_freshness_rows}
    for method in ["PepMLM", "RFdiffusion", "ProteinMPNN", "PepMirror"]:
        if method not in source_freshness_methods:
            errors.append(f"source_freshness_manifest_v0.11.csv missing {method}")
    for row in source_freshness_rows:
        if row.get("freshness_check_status") not in {"needs_external_refresh", "blocked_dependency", "planned_not_refreshed"}:
            errors.append(f"{row.get('record_id')}: invalid v0.11 freshness status {row.get('freshness_check_status')}")
        if row.get("download_allowed") != "no_until_approved":
            errors.append(f"{row.get('record_id')}: v0.11 source freshness must keep download_allowed=no_until_approved")
        for required_field in ["primary_paper", "official_metadata_sources", "code_route", "license_route", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('record_id')}: source freshness row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in ["download_performed=yes", "installed", "reproduced", "smoke_test_ready"]:
            if forbidden in text:
                errors.append(f"{row.get('record_id')}: source freshness row overclaims {forbidden}")

    expected_source_clones = {
        "pepmlm": "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
        "saltnpeppr": "fba9d029f34638fe87277f69b5d6a5797273c5a5",
        "DiffPepBuilder": "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
        "PepGLAD": "bad015ca50c312a89482adb5220c3d907f13df5c",
        "PeptideDesign": "3e3e9f501ee16db318e9bf52643513636a07699a",
        "PepMirror": "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
        "ColabDesign": "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
        "OSPREY3": "3d53244851f0388db9e01b288bbd330145935aa7",
        "RFdiffusion": "2d0c003df46b9db41d119321f15403dec3716cd9",
        "ProteinMPNN": "8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
        "BindCraft": "b971db42ba6e091afab63ccb30ae02215150a990",
    }
    source_clone_by_repo = {row.get("repo_name", ""): row for row in source_clone_rows}
    for repo_name, commit in expected_source_clones.items():
        row = source_clone_by_repo.get(repo_name)
        if not row:
            errors.append(f"source_clone_manifest_v0.12.csv missing {repo_name}")
            continue
        if row.get("pinned_commit") != commit:
            errors.append(f"{repo_name}: v0.12 source clone pinned commit mismatch")
        if row.get("observed_head") != commit:
            errors.append(f"{repo_name}: v0.12 source clone observed head mismatch")
    if len(source_clone_rows) != len(expected_source_clones):
        errors.append(
            f"source_clone_manifest_v0.12.csv should contain {len(expected_source_clones)} rows, found {len(source_clone_rows)}"
        )
    allowed_clone_status = {"checkout_verified", "checkout_verified_network_warning"}
    for row in source_clone_rows:
        repo_name = row.get("repo_name", "")
        if row.get("clone_performed") != "yes":
            errors.append(f"{repo_name}: v0.12 source clone row must record clone_performed=yes")
        if row.get("checkout_status") not in allowed_clone_status:
            errors.append(f"{repo_name}: invalid v0.12 checkout_status {row.get('checkout_status')}")
        if not row.get("external_clone_path", "").startswith(
            "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/"
        ):
            errors.append(f"{repo_name}: source clone path must remain outside the KB repository")
        for required_field in ["method", "repo_url", "default_branch", "license_files", "environment_files", "next_gate"]:
            if not row.get(required_field):
                errors.append(f"{repo_name}: source clone row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in ["installed", "reproduced", "smoke_test_ready", "benchmark_ready", "gpu_run", "weights_downloaded"]:
            if forbidden in text:
                errors.append(f"{repo_name}: source clone row overclaims {forbidden}")

    expected_image_tags = {
        "pd-foundry-gpu:latest",
        "pd-rfpeptide-gpu:fixed",
        "pd-bindcraft-gpu:installed",
        "pd-af2multimer-gpu:fixed",
        "pd-af3-gpu:v3.0.2",
        "pd-rosetta-cpu-parallel:latest",
        "pd-pepmimic-gpu:latest",
        "pd-benchmark-methods-gpu:0.13",
    }
    image_by_tag = {row.get("image_tag", ""): row for row in docker_image_inventory_rows}
    for image_tag in expected_image_tags:
        if image_tag not in image_by_tag:
            errors.append(f"docker_image_inventory_v0.13.csv missing {image_tag}")
    if len(docker_image_inventory_rows) != len(expected_image_tags):
        errors.append(
            f"docker_image_inventory_v0.13.csv should contain {len(expected_image_tags)} rows, "
            f"found {len(docker_image_inventory_rows)}"
        )
    allowed_image_status = {"existing_docker_image_observed", "workbench_dockerfile_defined_not_built"}
    for row in docker_image_inventory_rows:
        image_tag = row.get("image_tag", "")
        if row.get("local_status") not in allowed_image_status:
            errors.append(f"{image_tag}: invalid v0.13 local_status {row.get('local_status')}")
        for required_field in ["service_name", "covered_methods_or_role", "license_boundary", "smoke_test_target", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{image_tag}: docker image inventory row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in ["benchmark_completed", "best_performing", "experimentally_validated", "weights_baked"]:
            if forbidden in text:
                errors.append(f"{image_tag}: docker image inventory row overclaims {forbidden}")

    expected_environment_methods = {
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
    environment_by_method = {row.get("method", ""): row for row in method_environment_assignment_rows}
    for method in expected_environment_methods:
        if method not in environment_by_method:
            errors.append(f"method_environment_assignment_v0.13.csv missing {method}")
    if len(method_environment_assignment_rows) != len(expected_environment_methods):
        errors.append(
            f"method_environment_assignment_v0.13.csv should contain {len(expected_environment_methods)} rows, "
            f"found {len(method_environment_assignment_rows)}"
        )
    allowed_assignment_status = {
        "dockerfile_defined_not_built",
        "existing_images_reuse",
        "existing_image_reuse",
        "license_gated_placeholder",
        "dependency_blocked",
        "cpu_java_route_planned",
    }
    for row in method_environment_assignment_rows:
        method = row.get("method", "")
        if row.get("assignment_status") not in allowed_assignment_status:
            errors.append(f"{method}: invalid v0.13 assignment_status {row.get('assignment_status')}")
        if row.get("assigned_image") != "not_assigned_license_gated" and not row.get("source_root", "").startswith(
            "/mnt/ssd4t/protein-design/data/src/pep_design_benchmark"
        ):
            errors.append(f"{method}: v0.13 source root must remain outside the KB repository")
        for required_field in ["benchmark_role", "assigned_image", "license_boundary", "next_gate", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{method}: method environment assignment row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in ["benchmark_completed", "best_performing", "experimentally_validated", "smoke_test_ready"]:
            if forbidden in text:
                errors.append(f"{method}: method environment assignment row overclaims {forbidden}")

    expected_v014_case_ids = {
        "pepmlm_ncam1_binding",
        "pepmlm_amhr2_binding",
        "pepmlm_intracellular_degradation_targets",
        "pepmlm_viral_phosphoproteins",
        "diffpepbuilder_mhcii_1sjh",
        "diffpepbuilder_ogt_6ma3",
        "diffpepbuilder_mdm2_3eqs",
        "diffpepbuilder_3clpro_7z4s",
        "diffpepbuilder_alk1_6sf1",
        "diffpepbuilder_tnf_7kp7",
        "pepglad_pepbench_lnr_panel",
        "dflow_pepmerge_panel",
        "rfdiffusion_pmhci_specificity_panel",
    }
    observed_v014_case_ids = {row.get("case_id", "") for row in method_paper_case_v014_rows}
    missing_v014_cases = sorted(expected_v014_case_ids - observed_v014_case_ids)
    if missing_v014_cases:
        errors.append("method_paper_case_matrix_v0.14.csv missing cases: " + ", ".join(missing_v014_cases))
    if len(method_paper_case_v014_rows) < len(expected_v014_case_ids):
        errors.append(
            f"method_paper_case_matrix_v0.14.csv should contain at least {len(expected_v014_case_ids)} rows, "
            f"found {len(method_paper_case_v014_rows)}"
        )
    allowed_v014_case_decisions = {
        "candidate_reference_not_frozen",
        "related_work_reference_not_frozen",
        "panel_reference_not_downloaded",
    }
    allowed_v014_case_scopes = {"wet_case", "regeneration_case", "de_novo_case", "benchmark_dataset_case", "method_extension_case"}
    for row in method_paper_case_v014_rows:
        case_id = row.get("case_id", "")
        if row.get("case_scope") not in allowed_v014_case_scopes:
            errors.append(f"{case_id}: invalid v0.14 case_scope {row.get('case_scope')}")
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{case_id}: invalid v0.14 task_id {row.get('task_id')}")
        if row.get("benchmark_use_decision") not in allowed_v014_case_decisions:
            errors.append(f"{case_id}: invalid v0.14 benchmark_use_decision {row.get('benchmark_use_decision')}")
        if not row.get("source_url", "").startswith("http"):
            errors.append(f"{case_id}: v0.14 method paper case must cite an HTTP source URL")
        for required_field in [
            "method",
            "source_paper",
            "source_identifier",
            "publication_status",
            "reported_case_or_dataset",
            "target_or_dataset",
            "peptide_scope",
            "input_requirement",
            "evidence_boundary",
            "next_action",
        ]:
            if not row.get(required_field):
                errors.append(f"{case_id}: v0.14 method paper case row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "download_performed=yes",
            "ready_for_target_set",
            "smoke_test_ready",
            "benchmark_completed",
            "best_performing",
            "installed",
            "reproduced",
            "ran_locally",
        ]:
            if forbidden in text:
                errors.append(f"{case_id}: v0.14 method paper case row overclaims {forbidden}")

    expected_v014_target_ids = {
        "diff_mdm2_p53_3eqs_v014",
        "diff_mhcii_hiv_1sjh_v014",
        "diff_ogt_hcf1_6ma3_v014",
        "diff_3clpro_7z4s_v014",
        "diff_alk1_bmp10_6sf1_v014",
        "diff_tnf_tnfr1_7kp7_v014",
        "pepmlm_ncam1_v014",
        "pepmlm_amhr2_v014",
        "pepmlm_degradation_targets_v014",
        "pepmlm_viral_phosphoproteins_v014",
        "rfdiffusion_pmhci_11_targets_v014",
        "pepglad_pepbench_lnr_v014",
        "dflow_pepmerge_v014",
        "pepbi_329_panel_v014",
        "gpcr_124_panel_v014",
        "chang_af2_six_receptors_v014",
    }
    observed_v014_target_ids = {row.get("candidate_id", "") for row in target_academic_search_v014_rows}
    missing_v014_targets = sorted(expected_v014_target_ids - observed_v014_target_ids)
    if missing_v014_targets:
        errors.append(
            "target_candidate_academic_search_v0.14.csv missing candidates: " + ", ".join(missing_v014_targets)
        )
    if len(target_academic_search_v014_rows) < 12:
        errors.append(
            "target_candidate_academic_search_v0.14.csv should contain at least 12 academic-search candidates"
        )
    allowed_v014_priorities = {"high", "medium", "low"}
    allowed_v014_target_decisions = {"candidate_not_frozen", "panel_candidate_not_frozen", "related_work_not_frozen"}
    for row in target_academic_search_v014_rows:
        candidate_id = row.get("candidate_id", "")
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{candidate_id}: invalid v0.14 target task_id {row.get('task_id')}")
        if row.get("priority") not in allowed_v014_priorities:
            errors.append(f"{candidate_id}: invalid v0.14 priority {row.get('priority')}")
        if row.get("readiness_decision") not in allowed_v014_target_decisions:
            errors.append(f"{candidate_id}: invalid v0.14 readiness_decision {row.get('readiness_decision')}")
        if "metadata_only" not in row.get("download_policy", ""):
            errors.append(f"{candidate_id}: v0.14 download_policy must remain metadata_only/no-download")
        if not row.get("source_url", "").startswith("http"):
            errors.append(f"{candidate_id}: v0.14 target candidate must cite an HTTP source URL")
        for required_field in [
            "target_or_panel",
            "source_type",
            "primary_source",
            "source_identifier",
            "pdb_id_or_panel_size",
            "target_class",
            "peptide_design_feature",
            "method_paper_anchor",
            "benchmark_track",
            "evidence_summary",
            "required_controls_or_checks",
            "next_action",
        ]:
            if not row.get(required_field):
                errors.append(f"{candidate_id}: v0.14 target candidate row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "download_performed=yes",
            "ready_for_target_set",
            "smoke_test_ready",
            "benchmark_completed",
            "best_performing",
            "installed",
            "reproduced",
            "ran_locally",
        ]:
            if forbidden in text:
                errors.append(f"{candidate_id}: v0.14 target candidate row overclaims {forbidden}")

    target_search_plan_text = (ROOT / "ops/plans/target_candidate_academic_search_plan_v0.14.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "academic-search driven",
        "method_paper_case_matrix_v0.14.csv",
        "target_candidate_academic_search_v0.14.csv",
        "NCAM1",
        "MDM2",
        "PepMerge",
        "PEPBI",
        "GPCR 124",
        "metadata_only_no_download",
        "does not freeze",
    ]:
        if token not in target_search_plan_text:
            errors.append(f"target_candidate_academic_search_plan_v0.14.md missing token {token}")
    for forbidden in ["download_performed=yes", "smoke_test_ready | reached", "target_set_v0.csv 已冻结"]:
        if forbidden in target_search_plan_text:
            errors.append(f"target_candidate_academic_search_plan_v0.14.md contains overclaim token {forbidden}")

    target_search_audit_text = (ROOT / "ops/audits/target_candidate_academic_search_audit_v0.14.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "Search Evidence",
        "PepMLM",
        "DiffPepBuilder",
        "RCSB PDB API",
        "PepBench",
        "D-Flow",
        "RFdiffusion",
        "PEPBI",
        "GPCR",
        "Chang AlphaFold",
        "No-Overclaim Boundary",
    ]:
        if token not in target_search_audit_text:
            errors.append(f"target_candidate_academic_search_audit_v0.14.md missing token {token}")

    expected_v015_preflight_targets = {
        "PepMLM",
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "AfCycDesign / ColabDesign cyclic peptide",
    }
    observed_v015_preflight_targets = {row.get("target", "") for row in run_preflight_v015_rows}
    missing_v015_preflight_targets = sorted(expected_v015_preflight_targets - observed_v015_preflight_targets)
    if missing_v015_preflight_targets:
        errors.append(
            "run_preflight_results_v0.15.csv missing targets: " + ", ".join(missing_v015_preflight_targets)
        )
    if len(run_preflight_v015_rows) != len(expected_v015_preflight_targets):
        errors.append(
            f"run_preflight_results_v0.15.csv should contain {len(expected_v015_preflight_targets)} rows, "
            f"found {len(run_preflight_v015_rows)}"
        )
    allowed_v015_run_status = {"passed", "failed", "blocked"}
    for row in run_preflight_v015_rows:
        target = row.get("target", "")
        if row.get("status") not in allowed_v015_run_status:
            errors.append(f"{target}: invalid v0.15 preflight status {row.get('status')}")
        try:
            int(row.get("exit_code", ""))
        except ValueError:
            errors.append(f"{target}: v0.15 preflight exit_code must be integer-like")
        if row.get("image_tag") != "pd-benchmark-methods-gpu:0.13":
            errors.append(f"{target}: v0.15 preflight image_tag must be pd-benchmark-methods-gpu:0.13")
        if not row.get("image_id", "").startswith("sha256:"):
            errors.append(f"{target}: v0.15 preflight image_id must start with sha256:")
        if not row.get("external_log_path", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.15/preflight/"
        ):
            errors.append(f"{target}: v0.15 preflight log path must remain under external workbench outputs")
        for required_field in RUN_PREFLIGHT_RESULTS_V015_HEADERS:
            if not row.get(required_field):
                errors.append(f"{target}: v0.15 preflight row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark_completed",
            "best_performing",
            "experimentally_validated",
            "problem-free",
            "smoke_test_ready",
            "benchmark_ready",
            "ready_for_target_set",
            "download_performed=yes",
        ]:
            if forbidden in text:
                errors.append(f"{target}: v0.15 preflight row overclaims {forbidden}")

    expected_v015_batch_methods = {"PepMLM", "ProteinMPNN", "RFpeptide/RFdiffusion"}
    observed_v015_batch_methods = {row.get("method", "") for row in batch_a_smoke_test_v015_rows}
    missing_v015_batch_methods = sorted(expected_v015_batch_methods - observed_v015_batch_methods)
    if missing_v015_batch_methods:
        errors.append(
            "batch_a_smoke_test_results_v0.15.csv missing methods: " + ", ".join(missing_v015_batch_methods)
        )
    if len(batch_a_smoke_test_v015_rows) != len(expected_v015_batch_methods):
        errors.append(
            f"batch_a_smoke_test_results_v0.15.csv should contain {len(expected_v015_batch_methods)} rows, "
            f"found {len(batch_a_smoke_test_v015_rows)}"
        )
    allowed_v015_batch_status = {"passed", "failed", "blocked"}
    allowed_v015_next_gates = {"minimal_smoke_observed", "minimal_smoke_observed_with_cpu_caveat"}
    for row in batch_a_smoke_test_v015_rows:
        method = row.get("method", "")
        if row.get("status") not in allowed_v015_batch_status:
            errors.append(f"{method}: invalid v0.15 Batch A status {row.get('status')}")
        try:
            int(row.get("exit_code", ""))
            duration_seconds = int(row.get("duration_seconds", ""))
            output_file_count = int(row.get("output_file_count", ""))
            output_bytes = int(row.get("output_bytes", ""))
        except ValueError:
            errors.append(f"{method}: v0.15 Batch A numeric fields must be integer-like")
            duration_seconds = 0
            output_file_count = 0
            output_bytes = 0
        if row.get("status") == "passed" and (duration_seconds <= 0 or output_file_count <= 0 or output_bytes <= 0):
            errors.append(f"{method}: passed v0.15 Batch A row must record positive runtime and output size")
        if not row.get("external_method_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.15/batch_a/"
        ):
            errors.append(f"{method}: v0.15 Batch A output path must remain under external workbench outputs")
        if not re.fullmatch(r"[0-9a-f]{40}", row.get("source_commit", "")):
            errors.append(f"{method}: v0.15 Batch A source_commit must be a 40-character git SHA")
        if row.get("next_gate") not in allowed_v015_next_gates:
            errors.append(f"{method}: invalid v0.15 Batch A next_gate {row.get('next_gate')}")
        if method == "PepMLM" and "cpu" not in " ".join(row.values()).lower():
            errors.append("PepMLM v0.15 Batch A row must retain the CPU-only caveat")
        for required_field in BATCH_A_SMOKE_TEST_RESULTS_V015_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.15 Batch A row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark_completed",
            "best_performing",
            "experimentally_validated",
            "problem-free",
            "smoke_test_ready",
            "benchmark_ready",
            "ready_for_target_set",
            "download_performed=yes",
        ]:
            if forbidden in text:
                errors.append(f"{method}: v0.15 Batch A row overclaims {forbidden}")

    batch_a_audit_text = (ROOT / "ops/audits/batch_a_execution_audit_v0.15.md").read_text(encoding="utf-8")
    for token in [
        "Batch A Execution Audit v0.15",
        "pd-benchmark-methods-gpu:0.13",
        "run_preflight_results_v0.15.csv",
        "batch_a_smoke_test_results_v0.15.csv",
        "CPU-only smoke test",
        "Boundaries And Next Actions",
        "minimal smoke-test observed",
        "/data/protein-design",
    ]:
        if token not in batch_a_audit_text:
            errors.append(f"batch_a_execution_audit_v0.15.md missing token {token}")
    batch_a_audit_lower = batch_a_audit_text.lower()
    for forbidden_phrase in [
        "benchmark completed",
        "best-performing",
        "experimentally validated",
        "problem-free",
        "smoke_test_ready",
        "benchmark_ready",
    ]:
        if has_unqualified_forbidden_wording(batch_a_audit_lower, forbidden_phrase):
            errors.append(f"batch_a_execution_audit_v0.15.md contains overclaim phrase {forbidden_phrase}")

    expected_v016_adapter_methods = {
        "PepMLM",
        "ProteinMPNN",
        "RFpeptide/RFdiffusion",
        "RFdiffusion + ProteinMPNN handoff",
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "AfCycDesign / ColabDesign cyclic peptide",
    }
    observed_v016_adapter_methods = {row.get("method", "") for row in adapter_parser_hardening_v016_rows}
    missing_v016_adapter_methods = sorted(expected_v016_adapter_methods - observed_v016_adapter_methods)
    if missing_v016_adapter_methods:
        errors.append(
            "adapter_parser_hardening_matrix_v0.16.csv missing methods: "
            + ", ".join(missing_v016_adapter_methods)
        )
    if len(adapter_parser_hardening_v016_rows) != len(expected_v016_adapter_methods):
        errors.append(
            f"adapter_parser_hardening_matrix_v0.16.csv should contain "
            f"{len(expected_v016_adapter_methods)} rows, found {len(adapter_parser_hardening_v016_rows)}"
        )
    allowed_v016_next_gates = {
        "adapter_contract_ready",
        "parser_contract_ready",
        "handoff_contract_ready",
        "preflight_caveat_queue",
        "dependency_repair_queue",
        "checkpoint_manifest_queue",
        "cli_route_queue",
    }
    for row in adapter_parser_hardening_v016_rows:
        method = row.get("method", "")
        if row.get("next_gate") not in allowed_v016_next_gates:
            errors.append(f"{method}: invalid v0.16 adapter next_gate {row.get('next_gate')}")
        if "/data/protein-design/" not in row.get("external_roots", ""):
            errors.append(f"{method}: v0.16 adapter external_roots must remain under /data/protein-design")
        for required_field in ADAPTER_PARSER_HARDENING_V016_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.16 adapter row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark_completed",
            "best_performing",
            "experimentally_validated",
            "problem-free",
            "smoke_test_ready",
            "benchmark_ready",
            "ready_for_target_set",
            "download_performed=yes",
            "performance_ranking",
        ]:
            if forbidden in text:
                errors.append(f"{method}: v0.16 adapter row overclaims {forbidden}")

    expected_v016_target_ids = {
        "mdm2_p53_3eqs_batch_b_review",
        "mhcii_hiv_1sjh_batch_b_review",
        "pdl1_workbench_example_batch_b_review",
        "rfdiffusion_pmhc_panel_batch_b_review",
        "pepbench_lnr_panel_batch_b_review",
        "pepmerge_panel_batch_b_review",
    }
    observed_v016_target_ids = {row.get("candidate_id", "") for row in batch_b_target_review_v016_rows}
    missing_v016_target_ids = sorted(expected_v016_target_ids - observed_v016_target_ids)
    if missing_v016_target_ids:
        errors.append(
            "batch_b_target_review_queue_v0.16.csv missing candidates: "
            + ", ".join(missing_v016_target_ids)
        )
    if len(batch_b_target_review_v016_rows) != len(expected_v016_target_ids):
        errors.append(
            f"batch_b_target_review_queue_v0.16.csv should contain {len(expected_v016_target_ids)} rows, "
            f"found {len(batch_b_target_review_v016_rows)}"
        )
    allowed_v016_lanes = {
        "protein_structure_and_mechanism",
        "literature_and_dataset_discovery",
    }
    for row in batch_b_target_review_v016_rows:
        candidate_id = row.get("candidate_id", "")
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{candidate_id}: invalid v0.16 target task_id {row.get('task_id')}")
        if row.get("evidence_lane") not in allowed_v016_lanes:
            errors.append(f"{candidate_id}: invalid v0.16 evidence_lane {row.get('evidence_lane')}")
        if row.get("readiness_decision") != "review_queue_not_frozen":
            errors.append(f"{candidate_id}: v0.16 readiness_decision must be review_queue_not_frozen")
        for required_field in BATCH_B_TARGET_REVIEW_V016_HEADERS:
            if not row.get(required_field):
                errors.append(f"{candidate_id}: v0.16 target review row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "download_performed=yes",
            "ready_for_target_set",
            "smoke_test_ready",
            "benchmark_completed",
            "best_performing",
            "installed",
            "reproduced",
            "ran_locally",
            "target_set_v0.csv 已冻结",
        ]:
            if forbidden in text:
                errors.append(f"{candidate_id}: v0.16 target review row overclaims {forbidden}")

    adapter_plan_text = (ROOT / "ops/plans/adapter_parser_hardening_plan_v0.16.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "Adapter Parser Hardening Plan v0.16",
        "adapter",
        "parser",
        "Batch B",
        "target/control",
        "PepMLM",
        "ProteinMPNN",
        "RFpeptide/RFdiffusion",
        "target_set_v0.csv",
        "不新增任何运行证据",
    ]:
        if token not in adapter_plan_text:
            errors.append(f"adapter_parser_hardening_plan_v0.16.md missing token {token}")
    adapter_replay_contract_text = (ROOT / "benchmark/protocols/adapter_replay_contract_v0.16.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "Adapter Replay Contract v0.16",
        "Required Replay Fields",
        "Parser Contract",
        "Batch B Gate",
        "candidate_outputs.csv",
        "run.csv",
        "smoke_test_ready",
    ]:
        if token not in adapter_replay_contract_text:
            errors.append(f"adapter_replay_contract_v0.16.md missing token {token}")
    for text_name, text_value in [
        ("adapter_parser_hardening_plan_v0.16.md", adapter_plan_text.lower()),
        ("adapter_replay_contract_v0.16.md", adapter_replay_contract_text.lower()),
    ]:
        for forbidden_phrase in [
            "benchmark completed",
            "best-performing",
            "experimentally validated",
            "problem-free",
            "benchmark_ready | reached",
            "smoke_test_ready | reached",
        ]:
            if has_unqualified_forbidden_wording(text_value, forbidden_phrase):
                errors.append(f"{text_name} contains overclaim phrase {forbidden_phrase}")

    expected_v017_target_gate_ids = {
        "mdm2_p53_3eqs_fixture",
        "mhcii_hiv_1sjh_fixture",
        "gabarap_7zkr_fixture",
        "pdl1_workbench_fixture",
    }
    observed_v017_target_gate_ids = {row.get("target_gate_id", "") for row in batch_b_pilot_target_gate_v017_rows}
    missing_v017_target_gate_ids = sorted(expected_v017_target_gate_ids - observed_v017_target_gate_ids)
    if missing_v017_target_gate_ids:
        errors.append(
            "batch_b_pilot_target_gate_v0.17.csv missing target gates: "
            + ", ".join(missing_v017_target_gate_ids)
        )
    if len(batch_b_pilot_target_gate_v017_rows) != len(expected_v017_target_gate_ids):
        errors.append(
            f"batch_b_pilot_target_gate_v0.17.csv should contain {len(expected_v017_target_gate_ids)} rows, "
            f"found {len(batch_b_pilot_target_gate_v017_rows)}"
        )
    allowed_v017_pilot_decisions = {
        "fixture_ready_not_frozen",
        "review_blocked_not_frozen",
        "parser_fixture_only_not_frozen",
    }
    for row in batch_b_pilot_target_gate_v017_rows:
        target_gate_id = row.get("target_gate_id", "")
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{target_gate_id}: invalid v0.17 target task_id {row.get('task_id')}")
        if row.get("pilot_decision") not in allowed_v017_pilot_decisions:
            errors.append(f"{target_gate_id}: invalid v0.17 pilot decision {row.get('pilot_decision')}")
        if "not_frozen" not in row.get("pilot_decision", ""):
            errors.append(f"{target_gate_id}: v0.17 target gate must retain not_frozen boundary")
        for required_field in BATCH_B_PILOT_TARGET_GATE_V017_HEADERS:
            if not row.get(required_field):
                errors.append(f"{target_gate_id}: v0.17 target gate row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "download_performed=yes",
            "ready_for_target_set",
            "smoke_test_ready",
            "benchmark_completed",
            "best_performing",
            "reproduced",
            "target_set_v0.csv 已冻结",
            "performance_ranking",
        ]:
            if forbidden in text:
                errors.append(f"{target_gate_id}: v0.17 target gate row overclaims {forbidden}")

    expected_v017_method_scope = expected_v016_adapter_methods
    observed_v017_method_scope = {row.get("method", "") for row in batch_b_pilot_method_scope_v017_rows}
    missing_v017_method_scope = sorted(expected_v017_method_scope - observed_v017_method_scope)
    if missing_v017_method_scope:
        errors.append(
            "batch_b_pilot_method_scope_v0.17.csv missing methods: "
            + ", ".join(missing_v017_method_scope)
        )
    if len(batch_b_pilot_method_scope_v017_rows) != len(expected_v017_method_scope):
        errors.append(
            f"batch_b_pilot_method_scope_v0.17.csv should contain {len(expected_v017_method_scope)} rows, "
            f"found {len(batch_b_pilot_method_scope_v017_rows)}"
        )
    allowed_v017_allowed_use = {"fixture_parser_only", "deferred"}
    for row in batch_b_pilot_method_scope_v017_rows:
        method = row.get("method", "")
        if row.get("allowed_pilot_use") not in allowed_v017_allowed_use:
            errors.append(f"{method}: invalid v0.17 allowed_pilot_use {row.get('allowed_pilot_use')}")
        for required_field in BATCH_B_PILOT_METHOD_SCOPE_V017_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.17 method scope row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark_completed",
            "best_performing",
            "experimentally_validated",
            "problem-free",
            "smoke_test_ready",
            "benchmark_ready",
            "ready_for_target_set",
            "performance_ranking",
        ]:
            if forbidden in text:
                errors.append(f"{method}: v0.17 method scope row overclaims {forbidden}")

    expected_v017_job_ids = {
        "batch_b_pilot_pepmlm_seq_fixture_seed101",
        "batch_b_pilot_rfpeptide_7zkr_fixture_seed101",
        "batch_b_pilot_proteinmpnn_pdl1_fixture_seed101",
        "batch_b_pilot_handoff_7zkr_fixture_seed101",
        "batch_b_pilot_diffpepbuilder_3eqs_seed101",
    }
    observed_v017_job_ids = {row.get("job_id", "") for row in batch_b_pilot_job_manifest_v017_rows}
    missing_v017_job_ids = sorted(expected_v017_job_ids - observed_v017_job_ids)
    if missing_v017_job_ids:
        errors.append(
            "batch_b_pilot_job_manifest_v0.17.csv missing job ids: " + ", ".join(missing_v017_job_ids)
        )
    if len(batch_b_pilot_job_manifest_v017_rows) != len(expected_v017_job_ids):
        errors.append(
            f"batch_b_pilot_job_manifest_v0.17.csv should contain {len(expected_v017_job_ids)} rows, "
            f"found {len(batch_b_pilot_job_manifest_v017_rows)}"
        )
    for row in batch_b_pilot_job_manifest_v017_rows:
        job_id = row.get("job_id", "")
        if row.get("status") not in {"planned_fixture_only", "deferred"}:
            errors.append(f"{job_id}: invalid v0.17 pilot job status {row.get('status')}")
        if row.get("n_designs_requested") != "5" or row.get("random_seed") != "101":
            errors.append(f"{job_id}: v0.17 pilot job must use n_designs=5 and seed=101")
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{job_id}: invalid v0.17 pilot job task_id {row.get('task_id')}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "generated",
            "scored",
            "smoke_test_ready",
            "benchmark_completed",
            "best_performing",
            "target_set_v0.csv 已冻结",
        ]:
            if forbidden in text:
                errors.append(f"{job_id}: v0.17 pilot job row overclaims {forbidden}")

    expected_v018_fixture_ids = {
        "batch_a_pepmlm_cpu_smoke_replay",
        "batch_a_proteinmpnn_pdl1_replay",
        "batch_a_rfpeptide_macrocycle_replay",
    }
    observed_v018_fixture_ids = {row.get("fixture_id", "") for row in adapter_replay_fixture_v018_rows}
    missing_v018_fixture_ids = sorted(expected_v018_fixture_ids - observed_v018_fixture_ids)
    if missing_v018_fixture_ids:
        errors.append(
            "adapter_replay_fixture_manifest_v0.18.csv missing fixtures: "
            + ", ".join(missing_v018_fixture_ids)
        )
    if len(adapter_replay_fixture_v018_rows) != len(expected_v018_fixture_ids):
        errors.append(
            f"adapter_replay_fixture_manifest_v0.18.csv should contain {len(expected_v018_fixture_ids)} rows, "
            f"found {len(adapter_replay_fixture_v018_rows)}"
        )
    for row in adapter_replay_fixture_v018_rows:
        fixture_id = row.get("fixture_id", "")
        if not row.get("external_method_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.15/batch_a/"
        ):
            errors.append(f"{fixture_id}: v0.18 fixture external_method_dir must remain under external Batch A root")
        if row.get("parser_name") != "parse_batch_a_replay_fixtures.py":
            errors.append(f"{fixture_id}: v0.18 fixture parser_name must be parse_batch_a_replay_fixtures.py")
        if row.get("parser_version") != "v0.18":
            errors.append(f"{fixture_id}: v0.18 fixture parser_version must be v0.18")
        for required_field in ADAPTER_REPLAY_FIXTURE_V018_HEADERS:
            if not row.get(required_field):
                errors.append(f"{fixture_id}: v0.18 adapter replay fixture row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark_completed",
            "best_performing",
            "experimentally_validated",
            "problem-free",
            "smoke_test_ready",
            "benchmark_ready",
            "performance_ranking",
        ]:
            if forbidden in text:
                errors.append(f"{fixture_id}: v0.18 adapter replay fixture row overclaims {forbidden}")

    if len(batch_a_replay_method_output_v018_rows) != len(expected_v018_fixture_ids):
        errors.append(
            "batch_a_replay_method_output_manifest_v0.18.csv should contain "
            f"{len(expected_v018_fixture_ids)} rows, found {len(batch_a_replay_method_output_v018_rows)}"
        )
    if len(batch_a_replay_candidate_v018_rows) != len(expected_v018_fixture_ids):
        errors.append(
            "batch_a_replay_candidate_outputs_v0.18.csv should contain "
            f"{len(expected_v018_fixture_ids)} rows, found {len(batch_a_replay_candidate_v018_rows)}"
        )
    if len(batch_a_replay_run_v018_rows) != len(expected_v018_fixture_ids):
        errors.append(
            "batch_a_replay_run_v0.18.csv should contain "
            f"{len(expected_v018_fixture_ids)} rows, found {len(batch_a_replay_run_v018_rows)}"
        )
    allowed_v018_parse_status = {"parsed", "partial", "failed", "not_applicable"}
    for row in batch_a_replay_method_output_v018_rows:
        run_record_id = row.get("run_record_id", "")
        if row.get("execution_stage") != "v0.15_minimal_smoke_replay_fixture":
            errors.append(f"{run_record_id}: v0.18 method output execution_stage must remain replay fixture")
        if row.get("parser_status") not in allowed_v018_parse_status:
            errors.append(f"{run_record_id}: invalid v0.18 parser_status {row.get('parser_status')}")
        if not row.get("raw_output_root", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.15/batch_a/"
        ):
            errors.append(f"{run_record_id}: v0.18 raw_output_root must remain external")
        try:
            int(row.get("runtime_seconds", ""))
            int(row.get("exit_code", ""))
        except ValueError:
            errors.append(f"{run_record_id}: v0.18 runtime_seconds and exit_code must be integer-like")
    candidate_by_design = {row.get("design_id", ""): row for row in batch_a_replay_candidate_v018_rows}
    run_by_design = {row.get("design_id", ""): row for row in batch_a_replay_run_v018_rows}
    if set(candidate_by_design) != set(run_by_design):
        errors.append("v0.18 candidate_outputs and run fixture design_id sets must match")
    for row in batch_a_replay_candidate_v018_rows:
        design_id = row.get("design_id", "")
        if row.get("parse_status") not in allowed_v018_parse_status:
            errors.append(f"{design_id}: invalid v0.18 candidate parse_status {row.get('parse_status')}")
        if row.get("method") == "PepMLM" and row.get("parse_status") != "partial":
            errors.append("PepMLM v0.18 replay fixture must retain partial parser caveat")
        if row.get("method") == "RFpeptide/RFdiffusion" and not row.get("structure_path", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.15/batch_a/"
        ):
            errors.append("RFpeptide/RFdiffusion v0.18 structure_path must remain external")
    for row in batch_a_replay_run_v018_rows:
        design_id = row.get("design_id", "")
        if row.get("status") != "not_real_benchmark":
            errors.append(f"{design_id}: v0.18 replay run rows must remain not_real_benchmark")
        if row.get("task_id") not in REQUIRED_PROTOCOL_TASKS:
            errors.append(f"{design_id}: invalid v0.18 replay run task_id {row.get('task_id')}")

    expected_v019_methods = {
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
    allowed_v019_statuses = {
        "example_smoke_passed_gpu",
        "example_smoke_passed_cpu_expected",
        "example_smoke_passed_gpu_noncanonical_output_caveat",
        "example_smoke_passed_gpu_low_confidence_caveat",
        "preflight_passed_blocked_weights",
        "preflight_passed_blocked_input_contract",
        "blocked_license",
        "deferred_notebook_route",
        "failed_command",
        "failed_timeout",
        "failed_no_gpu_evidence",
        "missing_runtime",
    }
    v019_doc_methods = {row.get("method", "") for row in method_source_doc_v019_rows}
    v019_manifest_methods = {row.get("method", "") for row in method_install_smoke_manifest_v019_rows}
    v019_result_methods = {row.get("method", "") for row in method_smoke_test_v019_rows}
    for label, observed in [
        ("method_source_doc_verification_v0.19.csv", v019_doc_methods),
        ("method_install_smoke_manifest_v0.19.csv", v019_manifest_methods),
        ("method_smoke_test_results_v0.19.csv", v019_result_methods),
    ]:
        missing = sorted(expected_v019_methods - observed)
        extra = sorted(observed - expected_v019_methods)
        if missing:
            errors.append(f"{label} missing v0.19 methods: {', '.join(missing)}")
        if extra:
            errors.append(f"{label} has unexpected v0.19 methods: {', '.join(extra)}")
        if len(observed) != len(expected_v019_methods):
            errors.append(f"{label} should contain {len(expected_v019_methods)} method rows")

    for row in method_source_doc_v019_rows:
        method = row.get("method", "")
        if not row.get("source_dir", "").startswith("/mnt/ssd4t/protein-design/"):
            errors.append(f"{method}: v0.19 source_dir must point to the external source root")
        if row.get("verification_status") not in allowed_v019_statuses:
            errors.append(f"{method}: invalid v0.19 verification_status {row.get('verification_status')}")
        for required_field in METHOD_SOURCE_DOC_VERIFICATION_V019_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.19 source/doc row missing {required_field}")

    for row in method_install_smoke_manifest_v019_rows:
        method = row.get("method", "")
        if row.get("workbench_root") != "/data/protein-design":
            errors.append(f"{method}: v0.19 workbench_root must remain /data/protein-design")
        if not row.get("source_dir", "").startswith("/mnt/ssd4t/protein-design/"):
            errors.append(f"{method}: v0.19 manifest source_dir must point to the external source root")
        if not row.get("external_output_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.19/method_smokes/"
        ):
            errors.append(f"{method}: v0.19 external_output_dir must remain under the external workbench")
        if row.get("manifest_status") not in allowed_v019_statuses:
            errors.append(f"{method}: invalid v0.19 manifest_status {row.get('manifest_status')}")
        for required_field in METHOD_INSTALL_SMOKE_MANIFEST_V019_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.19 manifest row missing {required_field}")

    for row in method_smoke_test_v019_rows:
        method = row.get("method", "")
        status = row.get("status", "")
        if status not in allowed_v019_statuses:
            errors.append(f"{method}: invalid v0.19 smoke status {status}")
        if not row.get("external_method_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.19/method_smokes/"
        ):
            errors.append(f"{method}: v0.19 external_method_dir must remain under the external workbench")
        if row.get("next_gate") == "smoke_test_ready":
            errors.append(f"{method}: v0.19 must not mark a method smoke_test_ready")
        if status.startswith("example_smoke_passed") and row.get("gpu_required") == "yes":
            if row.get("gpu_evidence") == "not_observed":
                errors.append(f"{method}: v0.19 GPU smoke pass must include GPU evidence")
        if ("blocked" in status or status.startswith("failed")) and not row.get("blocker"):
            errors.append(f"{method}: v0.19 blocked/failed row must include blocker text")
        if row.get("exit_code") != "NA":
            try:
                int(str(row.get("exit_code", "")))
                float(str(row.get("runtime_sec", "")))
            except ValueError:
                errors.append(f"{method}: v0.19 exit_code/runtime_sec should be numeric or NA")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark completed",
            "best-performing",
            "experimentally validated",
            "problem-free",
            "benchmark_ready",
            "performance ranking",
            "full benchmark result achieved",
        ]:
            if forbidden in text:
                errors.append(f"{method}: v0.19 smoke row overclaims {forbidden}")

    expected_v020_methods = expected_v019_methods
    allowed_v020_statuses = {
        "carried_forward_v019_ready",
        "carried_forward_v019_cpu_ready",
        "blocked_license",
        "blocked_input_contract",
        "blocked_pyrosetta_wheel_missing",
        "blocked_pyrosetta_image_missing",
        "blocked_weights",
        "deferred_cli_adapter",
        "unblock_smoke_passed_gpu",
        "failed_command",
        "failed_timeout",
        "failed_no_gpu_evidence",
        "missing_runtime",
    }
    v020_manifest_methods = {row.get("method", "") for row in method_unblock_manifest_v020_rows}
    v020_result_methods = {row.get("method", "") for row in method_unblock_smoke_v020_rows}
    for label, observed in [
        ("method_unblock_manifest_v0.20.csv", v020_manifest_methods),
        ("method_unblock_smoke_results_v0.20.csv", v020_result_methods),
    ]:
        missing = sorted(expected_v020_methods - observed)
        extra = sorted(observed - expected_v020_methods)
        if missing:
            errors.append(f"{label} missing v0.20 methods: {', '.join(missing)}")
        if extra:
            errors.append(f"{label} has unexpected v0.20 methods: {', '.join(extra)}")
        if len(observed) != len(expected_v020_methods):
            errors.append(f"{label} should contain {len(expected_v020_methods)} method rows")

    for row in method_unblock_manifest_v020_rows:
        method = row.get("method", "")
        if row.get("workbench_root") != "/data/protein-design":
            errors.append(f"{method}: v0.20 workbench_root must remain /data/protein-design")
        if not row.get("source_dir", "").startswith("/mnt/ssd4t/protein-design/"):
            errors.append(f"{method}: v0.20 manifest source_dir must point to the external source root")
        if not row.get("external_output_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.20/method_unblock_smokes/"
        ):
            errors.append(f"{method}: v0.20 external_output_dir must remain under the external workbench")
        if row.get("manifest_status") not in allowed_v020_statuses:
            errors.append(f"{method}: invalid v0.20 manifest_status {row.get('manifest_status')}")
        for required_field in METHOD_UNBLOCK_MANIFEST_V020_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.20 manifest row missing {required_field}")

    for row in method_unblock_smoke_v020_rows:
        method = row.get("method", "")
        status = row.get("status", "")
        if status not in allowed_v020_statuses:
            errors.append(f"{method}: invalid v0.20 unblock status {status}")
        if not row.get("external_method_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.20/method_unblock_smokes/"
        ):
            errors.append(f"{method}: v0.20 external_method_dir must remain under the external workbench")
        if row.get("next_gate") == "smoke_test_ready":
            errors.append(f"{method}: v0.20 must not mark a method smoke_test_ready")
        if status in {"unblock_smoke_passed_gpu", "carried_forward_v019_ready"} and row.get("gpu_required") == "yes":
            if row.get("gpu_evidence") == "not_observed":
                errors.append(f"{method}: v0.20 GPU-ready status must include GPU evidence")
        if (
            status.startswith("blocked")
            or status.startswith("failed")
            or status.startswith("deferred")
        ) and not row.get("blocker"):
            errors.append(f"{method}: v0.20 blocked/failed/deferred row must include blocker text")
        if row.get("exit_code") != "NA":
            try:
                int(str(row.get("exit_code", "")))
                float(str(row.get("runtime_sec", "")))
            except ValueError:
                errors.append(f"{method}: v0.20 exit_code/runtime_sec should be numeric or NA")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark completed",
            "best-performing",
            "experimentally validated",
            "problem-free",
            "benchmark_ready",
            "performance ranking",
            "full benchmark result achieved",
            "smoke_test_ready",
        ]:
            if forbidden in text:
                errors.append(f"{method}: v0.20 unblock row overclaims {forbidden}")

    expected_v021_methods = expected_v019_methods
    allowed_v021_statuses = {
        "adapter_smoke_passed_gpu",
        "bounded_execution_control_passed",
        "carried_forward_v020_ready",
        "blocked_license",
        "blocked_weights",
        "blocked_input_contract",
        "blocked_cli_adapter",
        "failed_command",
        "failed_timeout",
        "failed_no_gpu_evidence",
        "missing_runtime",
    }
    v021_manifest_methods = {row.get("method", "") for row in adapter_smoke_manifest_v021_rows}
    v021_result_methods = {row.get("method", "") for row in adapter_smoke_results_v021_rows}
    for label, observed in [
        ("adapter_smoke_manifest_v0.21.csv", v021_manifest_methods),
        ("adapter_smoke_results_v0.21.csv", v021_result_methods),
    ]:
        missing = sorted(expected_v021_methods - observed)
        extra = sorted(observed - expected_v021_methods)
        if missing:
            errors.append(f"{label} missing v0.21 methods: {', '.join(missing)}")
        if extra:
            errors.append(f"{label} has unexpected v0.21 methods: {', '.join(extra)}")
        if len(observed) != len(expected_v021_methods):
            errors.append(f"{label} should contain {len(expected_v021_methods)} method rows")

    for row in adapter_smoke_manifest_v021_rows:
        method = row.get("method", "")
        if row.get("workbench_root") != "/data/protein-design":
            errors.append(f"{method}: v0.21 workbench_root must remain /data/protein-design")
        if not row.get("source_dir", "").startswith("/mnt/ssd4t/protein-design/"):
            errors.append(f"{method}: v0.21 manifest source_dir must point to the external source root")
        if not row.get("external_output_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.21/adapter_smokes/"
        ):
            errors.append(f"{method}: v0.21 external_output_dir must remain under the external workbench")
        if row.get("manifest_status") not in allowed_v021_statuses:
            errors.append(f"{method}: invalid v0.21 manifest_status {row.get('manifest_status')}")
        for required_field in ADAPTER_SMOKE_MANIFEST_V021_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.21 manifest row missing {required_field}")

    for row in adapter_smoke_results_v021_rows:
        method = row.get("method", "")
        status = row.get("status", "")
        if status not in allowed_v021_statuses:
            errors.append(f"{method}: invalid v0.21 adapter status {status}")
        if not row.get("external_method_dir", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.21/adapter_smokes/"
        ):
            errors.append(f"{method}: v0.21 external_method_dir must remain under the external workbench")
        if row.get("next_gate") == "smoke_test_ready":
            errors.append(f"{method}: v0.21 must not mark a method smoke_test_ready")
        if status in {"adapter_smoke_passed_gpu", "bounded_execution_control_passed"} and row.get("gpu_required") == "yes":
            if row.get("gpu_evidence") == "not_observed":
                errors.append(f"{method}: v0.21 GPU adapter pass must include GPU evidence")
        if (
            status.startswith("blocked")
            or status.startswith("failed")
        ) and not row.get("blocker"):
            errors.append(f"{method}: v0.21 blocked/failed row must include blocker text")
        if row.get("exit_code") != "NA":
            try:
                int(str(row.get("exit_code", "")))
                float(str(row.get("runtime_sec", "")))
            except ValueError:
                errors.append(f"{method}: v0.21 exit_code/runtime_sec should be numeric or NA")
        for required_field in ADAPTER_SMOKE_RESULTS_V021_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.21 result row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark completed",
            "best-performing",
            "experimentally validated",
            "problem-free",
            "benchmark_ready",
            "performance ranking",
            "full benchmark result achieved",
            "smoke_test_ready",
        ]:
            if forbidden in text:
                errors.append(f"{method}: v0.21 adapter row overclaims {forbidden}")

    expected_v021_assets = {
        "pepmirror_commutator_both_v1",
        "pepglad_checkpoints_zip",
        "dflow_source_local_weight",
        "dflow_pepmerge_cache",
    }
    observed_v021_assets = {row.get("asset_id", "") for row in blocker_asset_manifest_v021_rows}
    missing_v021_assets = sorted(expected_v021_assets - observed_v021_assets)
    if missing_v021_assets:
        errors.append("blocker_asset_manifest_v0.21.csv missing assets: " + ", ".join(missing_v021_assets))
    for row in blocker_asset_manifest_v021_rows:
        asset_id = row.get("asset_id", "")
        if row.get("status") not in {"present", "missing"}:
            errors.append(f"{asset_id}: invalid v0.21 asset status {row.get('status')}")
        if not row.get("local_path", "").startswith("/data/protein-design/data/"):
            errors.append(f"{asset_id}: v0.21 asset local_path must remain outside the KB")
        if row.get("status") == "present":
            try:
                if int(row.get("size_bytes", "0")) <= 0:
                    errors.append(f"{asset_id}: present v0.21 asset must record a positive size")
            except ValueError:
                errors.append(f"{asset_id}: v0.21 asset size_bytes should be integer-like")

    allowed_v021_parse_status = {"parsed", "partial", "failed", "not_applicable"}
    if len(adapter_method_output_v021_rows) != len(expected_v021_methods):
        errors.append(
            "adapter_method_output_manifest_v0.21.csv should contain "
            f"{len(expected_v021_methods)} method rows, found {len(adapter_method_output_v021_rows)}"
        )
    for row in adapter_method_output_v021_rows:
        run_record_id = row.get("run_record_id", "")
        if row.get("execution_stage") != "v0.21_adapter_smoke_fixture":
            errors.append(f"{run_record_id}: v0.21 method output execution_stage must remain adapter smoke fixture")
        if row.get("parser_status") not in allowed_v021_parse_status:
            errors.append(f"{run_record_id}: invalid v0.21 parser_status {row.get('parser_status')}")
        if not row.get("raw_output_root", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.21/adapter_smokes/"
        ):
            errors.append(f"{run_record_id}: v0.21 raw_output_root must remain external")
        if row.get("exit_code") != "NA":
            try:
                int(str(row.get("exit_code", "")))
                float(str(row.get("runtime_seconds", "")))
            except ValueError:
                errors.append(f"{run_record_id}: v0.21 runtime_seconds and exit_code should be numeric or NA")
        for forbidden in ["benchmark completed", "best-performing", "experimentally validated", "benchmark_ready"]:
            if forbidden in " ".join(row.values()).lower():
                errors.append(f"{run_record_id}: v0.21 method output row overclaims {forbidden}")

    v021_candidate_by_design = {row.get("design_id", ""): row for row in adapter_candidate_output_v021_rows}
    v021_run_by_design = {row.get("design_id", ""): row for row in adapter_run_rows_v021_rows}
    if set(v021_candidate_by_design) != set(v021_run_by_design):
        errors.append("v0.21 candidate_outputs and run rows design_id sets must match")
    for row in adapter_candidate_output_v021_rows:
        design_id = row.get("design_id", "")
        if row.get("parse_status") not in allowed_v021_parse_status:
            errors.append(f"{design_id}: invalid v0.21 candidate parse_status {row.get('parse_status')}")
        if row.get("structure_path") and not row.get("structure_path", "").startswith(
            "/data/protein-design/data/outputs/benchmark_v0.21/adapter_smokes/"
        ):
            errors.append(f"{design_id}: v0.21 structure_path must remain external")
    for row in adapter_run_rows_v021_rows:
        design_id = row.get("design_id", "")
        if row.get("status") != "not_real_benchmark":
            errors.append(f"{design_id}: v0.21 adapter run rows must remain not_real_benchmark")

    expected_v022_methods = expected_v021_methods
    observed_v022_methods = {row.get("method", "") for row in method_example_fixture_v022_rows}
    missing_v022_methods = sorted(expected_v022_methods - observed_v022_methods)
    extra_v022_methods = sorted(observed_v022_methods - expected_v022_methods)
    if missing_v022_methods:
        errors.append("method_example_fixture_evidence_v0.22.csv missing methods: " + ", ".join(missing_v022_methods))
    if extra_v022_methods:
        errors.append("method_example_fixture_evidence_v0.22.csv has unexpected methods: " + ", ".join(extra_v022_methods))
    if len(method_example_fixture_v022_rows) != len(expected_v022_methods):
        errors.append(
            "method_example_fixture_evidence_v0.22.csv should contain "
            f"{len(expected_v022_methods)} method rows, found {len(method_example_fixture_v022_rows)}"
        )
    allowed_v022_parse_status = {"parsed", "partial", "failed", "not_applicable"}
    allowed_v022_decisions = {
        "scheduled_adapter_multi_case_fixture",
        "blocked_input_contract_prep",
        "blocked_cli_adapter_prep",
        "wrapper_control_review_only",
        "license_blocked_carry_forward",
        "deferred_cpu_carry_forward",
    }
    for row in method_example_fixture_v022_rows:
        method = row.get("method", "")
        if row.get("evidence_type") != "method_example_adapter_smoke":
            errors.append(f"{method}: v0.22 evidence_type must remain method_example_adapter_smoke")
        if row.get("parse_status") not in allowed_v022_parse_status:
            errors.append(f"{method}: invalid v0.22 parse_status {row.get('parse_status')}")
        if row.get("v022_decision") not in allowed_v022_decisions:
            errors.append(f"{method}: invalid v0.22 decision {row.get('v022_decision')}")
        if row.get("v021_adapter_smoke_id") and not row.get("v021_adapter_smoke_id", "").startswith("v021_"):
            errors.append(f"{method}: v0.22 evidence row must reference v0.21 adapter smoke id")
        if method == "PepMLM" and row.get("parse_status") != "partial":
            errors.append("PepMLM v0.22 evidence must retain partial parser caveat")
        if method == "D-Flow / PeptideDesign" and row.get("v022_decision") != "blocked_input_contract_prep":
            errors.append("D-Flow v0.22 evidence must remain blocked_input_contract_prep")
        if method == "AfCycDesign / ColabDesign cyclic peptide" and row.get("v022_decision") != "blocked_cli_adapter_prep":
            errors.append("ColabDesign v0.22 evidence must remain blocked_cli_adapter_prep")
        if method == "BindCraft" and row.get("v022_decision") != "wrapper_control_review_only":
            errors.append("BindCraft v0.22 evidence must remain wrapper_control_review_only")
        for required_field in METHOD_EXAMPLE_FIXTURE_EVIDENCE_V022_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.22 evidence row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "benchmark_completed",
            "best_performing",
            "experimentally_validated",
            "problem-free",
            "smoke_test_ready",
            "benchmark_ready",
            "performance_ranking",
        ]:
            if forbidden in text:
                errors.append(f"{method}: v0.22 evidence row overclaims {forbidden}")

    expected_v022_fixture_ids = {
        "pepmlm_sequence_contract_fixture",
        "mdm2_p53_3eqs_fixture",
        "gabarap_7zkr_fixture",
        "mhcii_hiv_1sjh_fixture",
        "pdl1_workbench_fixture",
    }
    observed_v022_fixture_ids = {row.get("fixture_case_id", "") for row in multi_case_fixture_target_v022_rows}
    missing_v022_fixture_ids = sorted(expected_v022_fixture_ids - observed_v022_fixture_ids)
    if missing_v022_fixture_ids:
        errors.append("multi_case_fixture_target_manifest_v0.22.csv missing fixtures: " + ", ".join(missing_v022_fixture_ids))
    if len(multi_case_fixture_target_v022_rows) != len(expected_v022_fixture_ids):
        errors.append(
            f"multi_case_fixture_target_manifest_v0.22.csv should contain {len(expected_v022_fixture_ids)} rows, "
            f"found {len(multi_case_fixture_target_v022_rows)}"
        )
    allowed_v022_target_statuses = {
        "fixture_ready_not_frozen",
        "review_blocked_not_frozen",
        "parser_fixture_only_not_frozen",
    }
    v022_allowed_tasks = set(REQUIRED_PROTOCOL_TASKS) | {"T4_bindcraft_peptide_smoke"}
    for row in multi_case_fixture_target_v022_rows:
        fixture_case_id = row.get("fixture_case_id", "")
        if row.get("task_id") not in v022_allowed_tasks:
            errors.append(f"{fixture_case_id}: invalid v0.22 fixture task_id {row.get('task_id')}")
        if row.get("target_status") not in allowed_v022_target_statuses:
            errors.append(f"{fixture_case_id}: invalid v0.22 target_status {row.get('target_status')}")
        if "not_frozen" not in row.get("target_status", ""):
            errors.append(f"{fixture_case_id}: v0.22 target manifest must retain not_frozen status")
        for required_field in MULTI_CASE_FIXTURE_TARGET_V022_HEADERS:
            if not row.get(required_field):
                errors.append(f"{fixture_case_id}: v0.22 target row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "ready_for_target_set",
            "target_set_v0.csv 已冻结",
            "benchmark_completed",
            "best_performing",
            "performance_ranking",
            "smoke_test_ready",
            "benchmark_ready",
        ]:
            if forbidden in text:
                errors.append(f"{fixture_case_id}: v0.22 target row overclaims {forbidden}")

    expected_v022_control_ids = {
        "pepmlm_sequence_noncanonical_parser_control",
        "mdm2_positive_complex_chain_control",
        "mdm2_negative_control_placeholder",
        "gabarap_noncanonical_parser_control",
        "mhcii_chain_d_confounder_control",
        "pdl1_local_provenance_control",
        "bindcraft_low_confidence_output_control",
    }
    observed_v022_control_ids = {row.get("control_id", "") for row in multi_case_fixture_control_v022_rows}
    missing_v022_control_ids = sorted(expected_v022_control_ids - observed_v022_control_ids)
    if missing_v022_control_ids:
        errors.append("multi_case_fixture_control_manifest_v0.22.csv missing controls: " + ", ".join(missing_v022_control_ids))
    if len(multi_case_fixture_control_v022_rows) != len(expected_v022_control_ids):
        errors.append(
            f"multi_case_fixture_control_manifest_v0.22.csv should contain {len(expected_v022_control_ids)} rows, "
            f"found {len(multi_case_fixture_control_v022_rows)}"
        )
    allowed_v022_control_statuses = {"available_metadata_only", "missing", "blocked", "wrapper_review_required"}
    for row in multi_case_fixture_control_v022_rows:
        control_id = row.get("control_id", "")
        fixture_case_id = row.get("fixture_case_id", "")
        if fixture_case_id not in expected_v022_fixture_ids and fixture_case_id != "bindcraft_cd47_method_example_control":
            errors.append(f"{control_id}: v0.22 control references unknown fixture_case_id {fixture_case_id}")
        if row.get("status") not in allowed_v022_control_statuses:
            errors.append(f"{control_id}: invalid v0.22 control status {row.get('status')}")
        if control_id == "bindcraft_low_confidence_output_control":
            control_text = " ".join(row.values()).lower()
            if "lowconfidence" not in control_text or "not accepted final" not in control_text:
                errors.append("BindCraft v0.22 control must explicitly reject LowConfidence as accepted final")
        for required_field in MULTI_CASE_FIXTURE_CONTROL_V022_HEADERS:
            if not row.get(required_field):
                errors.append(f"{control_id}: v0.22 control row missing {required_field}")

    expected_v022_job_ids = {
        "v022_pilot_pepmlm_sequence_seed42",
        "v022_pilot_diffpepbuilder_3eqs_seed42",
        "v022_pilot_pepglad_3eqs_seed42",
        "v022_pilot_pepmirror_3eqs_seed42",
        "v022_pilot_rfdiffusion_mpnn_7zkr_seed42",
        "v022_pilot_dflow_3eqs_seed42",
        "v022_pilot_colabdesign_7zkr_seed42",
        "v022_pilot_bindcraft_cd47_wrapper_seed42",
    }
    observed_v022_job_ids = {row.get("job_id", "") for row in multi_case_fixture_job_v022_rows}
    missing_v022_job_ids = sorted(expected_v022_job_ids - observed_v022_job_ids)
    if missing_v022_job_ids:
        errors.append("multi_case_fixture_job_manifest_v0.22.csv missing job ids: " + ", ".join(missing_v022_job_ids))
    if len(multi_case_fixture_job_v022_rows) != len(expected_v022_job_ids):
        errors.append(
            f"multi_case_fixture_job_manifest_v0.22.csv should contain {len(expected_v022_job_ids)} rows, "
            f"found {len(multi_case_fixture_job_v022_rows)}"
        )
    allowed_v022_job_statuses = {
        "planned_fixture_only",
        "blocked_input_contract",
        "blocked_cli_adapter",
        "wrapper_review_only",
    }
    planned_v022_methods = {
        "PepMLM",
        "DiffPepBuilder",
        "PepGLAD",
        "PepMirror",
        "RFdiffusion + ProteinMPNN",
    }
    job_methods = {row.get("method", ""): row for row in multi_case_fixture_job_v022_rows}
    for row in multi_case_fixture_job_v022_rows:
        job_id = row.get("job_id", "")
        fixture_case_id = row.get("fixture_case_id", "")
        control_id = row.get("control_id", "")
        method = row.get("method", "")
        status = row.get("status", "")
        if status not in allowed_v022_job_statuses:
            errors.append(f"{job_id}: invalid v0.22 pilot job status {status}")
        if row.get("n_designs_requested") != "1" or row.get("random_seed") != "42":
            errors.append(f"{job_id}: v0.22 pilot job must use n_designs=1 and seed=42")
        if row.get("task_id") not in v022_allowed_tasks:
            errors.append(f"{job_id}: invalid v0.22 pilot job task_id {row.get('task_id')}")
        if fixture_case_id not in expected_v022_fixture_ids and fixture_case_id != "bindcraft_cd47_method_example_control":
            errors.append(f"{job_id}: v0.22 pilot job references unknown fixture_case_id {fixture_case_id}")
        if control_id not in expected_v022_control_ids:
            errors.append(f"{job_id}: v0.22 pilot job references unknown control_id {control_id}")
        if method in planned_v022_methods and status != "planned_fixture_only":
            errors.append(f"{job_id}: v0.22 first-lane method should be planned_fixture_only")
        if method == "D-Flow / PeptideDesign" and status != "blocked_input_contract":
            errors.append("D-Flow v0.22 job must remain blocked_input_contract")
        if method == "AfCycDesign / ColabDesign cyclic peptide" and status != "blocked_cli_adapter":
            errors.append("ColabDesign v0.22 job must remain blocked_cli_adapter")
        if method == "BindCraft":
            if status != "wrapper_review_only":
                errors.append("BindCraft v0.22 job must remain wrapper_review_only")
            if "low_confidence_only" not in row.get("failure_policy", ""):
                errors.append("BindCraft v0.22 job failure_policy must include low_confidence_only")
        text = " ".join(row.values()).lower()
        for forbidden in [
            "generated_output",
            "scored",
            "benchmark_completed",
            "best_performing",
            "performance_ranking",
            "smoke_test_ready",
            "benchmark_ready",
        ]:
            if forbidden in text:
                errors.append(f"{job_id}: v0.22 pilot job row overclaims {forbidden}")
    if job_methods.get("D-Flow / PeptideDesign", {}).get("contract_status") != "blocked_missing_pepmerge_lmdb":
        errors.append("D-Flow v0.22 contract_status must be blocked_missing_pepmerge_lmdb")
    if job_methods.get("AfCycDesign / ColabDesign cyclic peptide", {}).get("contract_status") != "blocked_cli_adapter":
        errors.append("ColabDesign v0.22 contract_status must be blocked_cli_adapter")
    if job_methods.get("BindCraft", {}).get("contract_status") != "wrapper_review_required":
        errors.append("BindCraft v0.22 contract_status must be wrapper_review_required")

    expected_v022_gate_ids = {
        "v022_dflow_input_contract",
        "v022_colabdesign_cli_adapter",
        "v022_bindcraft_wrapper_review",
        "v022_formal_manifest_gate",
    }
    observed_v022_gate_ids = {row.get("gate_id", "") for row in priority_gate_review_v022_rows}
    missing_v022_gate_ids = sorted(expected_v022_gate_ids - observed_v022_gate_ids)
    if missing_v022_gate_ids:
        errors.append("priority_gate_review_v0.22.csv missing gates: " + ", ".join(missing_v022_gate_ids))
    if len(priority_gate_review_v022_rows) != len(expected_v022_gate_ids):
        errors.append(
            f"priority_gate_review_v0.22.csv should contain {len(expected_v022_gate_ids)} rows, "
            f"found {len(priority_gate_review_v022_rows)}"
        )
    for row in priority_gate_review_v022_rows:
        gate_id = row.get("gate_id", "")
        for required_field in PRIORITY_GATE_REVIEW_V022_HEADERS:
            if not row.get(required_field):
                errors.append(f"{gate_id}: v0.22 priority gate row missing {required_field}")
        text = " ".join(row.values()).lower()
        if gate_id == "v022_dflow_input_contract":
            if "pep_pocket_test_structure_cache.lmdb missing" not in text:
                errors.append("D-Flow v0.22 gate must retain missing LMDB blocker")
            if row.get("allowed_v022_use") != "blocked_contract_row_only":
                errors.append("D-Flow v0.22 gate must remain blocked_contract_row_only")
        if gate_id == "v022_colabdesign_cli_adapter":
            if row.get("allowed_v022_use") != "blocked_cli_row_only":
                errors.append("ColabDesign v0.22 gate must remain blocked_cli_row_only")
        if gate_id == "v022_bindcraft_wrapper_review":
            if row.get("allowed_v022_use") != "wrapper_control_only":
                errors.append("BindCraft v0.22 gate must remain wrapper_control_only")
            for token in ["accepted_final", "low_confidence_only", "timeout_only", "no_output", "failed"]:
                if token not in text:
                    errors.append(f"BindCraft v0.22 gate missing output class token {token}")
        for forbidden in [
            "benchmark_completed",
            "best_performing",
            "performance_ranking",
            "smoke_test_ready",
            "benchmark_ready",
        ]:
            if forbidden in text:
                errors.append(f"{gate_id}: v0.22 priority gate row overclaims {forbidden}")

    if len(notebook_cli_smoke_v023_rows) != 1:
        errors.append(
            f"notebook_cli_smoke_manifest_v0.23.csv should contain 1 row, found {len(notebook_cli_smoke_v023_rows)}"
        )
    for row in notebook_cli_smoke_v023_rows:
        component_id = row.get("component_id", "")
        for required_field in NOTEBOOK_CLI_SMOKE_V023_HEADERS:
            if not row.get(required_field):
                errors.append(f"{component_id}: v0.23 notebook CLI row missing {required_field}")
        if row.get("status") != "smoke_passed":
            errors.append("v0.23 notebook CLI smoke must record smoke_passed")
        if "papermill" not in row.get("installed_packages", ""):
            errors.append("v0.23 notebook CLI smoke must include papermill")
        if "not method output" not in row.get("evidence_boundary", ""):
            errors.append("v0.23 notebook CLI evidence boundary must say not method output")

    if len(dflow_project_install_v023_rows) != 1:
        errors.append(
            f"dflow_project_install_contract_v0.23.csv should contain 1 row, found {len(dflow_project_install_v023_rows)}"
        )
    for row in dflow_project_install_v023_rows:
        method = row.get("method", "")
        for required_field in DFLOW_PROJECT_INSTALL_V023_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.23 D-Flow install row missing {required_field}")
        if row.get("source_mode") != "project_internal_git_clone_not_symlink":
            errors.append("D-Flow v0.23 source_mode must be project_internal_git_clone_not_symlink")
        if row.get("is_symlink") != "no":
            errors.append("D-Flow v0.23 source must not be recorded as a symlink")
        if row.get("input_contract_status") != "blocked_input_contract":
            errors.append("D-Flow v0.23 must remain blocked_input_contract until PepMerge LMDB loads")
        for token in ["PepDataset", "PepModel_import_ok", "inference_pep_import_ok", "Google Drive"]:
            if token not in " ".join(row.values()):
                errors.append(f"D-Flow v0.23 install row missing token {token}")
        for forbidden in ["smoke_test_ready", "benchmark_ready", "benchmark_completed", "best_performing"]:
            if forbidden in " ".join(row.values()).lower():
                errors.append(f"D-Flow v0.23 install row overclaims {forbidden}")

    expected_v023_package_ids = {
        "v023_notebook_cli",
        "v023_dflow_project_install",
        "v023_colabdesign_adapter",
        "v023_bindcraft_classifier",
        "v023_alphafold_target_qc",
    }
    observed_v023_package_ids = {row.get("package_item_id", "") for row in external_dry_run_package_v023_rows}
    missing_v023_package_ids = sorted(expected_v023_package_ids - observed_v023_package_ids)
    if missing_v023_package_ids:
        errors.append(
            "external_dry_run_package_manifest_v0.23.csv missing package ids: "
            + ", ".join(missing_v023_package_ids)
        )
    if len(external_dry_run_package_v023_rows) != len(expected_v023_package_ids):
        errors.append(
            f"external_dry_run_package_manifest_v0.23.csv should contain {len(expected_v023_package_ids)} rows, "
            f"found {len(external_dry_run_package_v023_rows)}"
        )
    for row in external_dry_run_package_v023_rows:
        package_item_id = row.get("package_item_id", "")
        for required_field in EXTERNAL_DRY_RUN_PACKAGE_V023_HEADERS:
            if not row.get(required_field):
                errors.append(f"{package_item_id}: v0.23 package row missing {required_field}")
        if package_item_id == "v023_alphafold_target_qc" and row.get("allowed_use") != "target_qc_only_not_scoring":
            errors.append("AlphaFold v0.23 package row must remain target_qc_only_not_scoring")

    expected_v023_gate_ids = {
        "v023_dflow_project_install",
        "v023_dflow_input_contract",
        "v023_colabdesign_notebook_cli",
        "v023_bindcraft_wrapper_classifier",
        "v023_formal_manifest_gate",
    }
    observed_v023_gate_ids = {row.get("gate_id", "") for row in priority_gate_review_v023_rows}
    missing_v023_gate_ids = sorted(expected_v023_gate_ids - observed_v023_gate_ids)
    if missing_v023_gate_ids:
        errors.append("priority_gate_review_v0.23.csv missing gates: " + ", ".join(missing_v023_gate_ids))
    if len(priority_gate_review_v023_rows) != len(expected_v023_gate_ids):
        errors.append(
            f"priority_gate_review_v0.23.csv should contain {len(expected_v023_gate_ids)} rows, "
            f"found {len(priority_gate_review_v023_rows)}"
        )
    for row in priority_gate_review_v023_rows:
        gate_id = row.get("gate_id", "")
        text = " ".join(row.values()).lower()
        for required_field in PRIORITY_GATE_REVIEW_V023_HEADERS:
            if not row.get(required_field):
                errors.append(f"{gate_id}: v0.23 priority gate row missing {required_field}")
        if gate_id == "v023_dflow_input_contract":
            if row.get("allowed_v023_use") != "blocked_contract_row_only":
                errors.append("D-Flow v0.23 input gate must remain blocked_contract_row_only")
            for token in ["google drive", "pep_pocket_test_structure_cache.lmdb"]:
                if token not in text:
                    errors.append(f"D-Flow v0.23 input gate missing token {token}")
        if gate_id == "v023_colabdesign_notebook_cli" and row.get("allowed_v023_use") != "cli_tooling_only":
            errors.append("ColabDesign v0.23 gate must remain cli_tooling_only")
        if gate_id == "v023_bindcraft_wrapper_classifier":
            for token in ["accepted_final", "low_confidence_only", "timeout_only", "no_output", "failed"]:
                if token not in text:
                    errors.append(f"BindCraft v0.23 gate missing output class token {token}")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "smoke_test_ready", "benchmark_ready"]:
            if forbidden in text:
                errors.append(f"{gate_id}: v0.23 priority gate row overclaims {forbidden}")

    if len(dflow_input_contract_fixture_v024_rows) != 1:
        errors.append(
            "dflow_input_contract_fixture_v0.24.csv should contain 1 row, "
            f"found {len(dflow_input_contract_fixture_v024_rows)}"
        )
    for row in dflow_input_contract_fixture_v024_rows:
        method = row.get("method", "")
        text = " ".join(row.values())
        lower_text = text.lower()
        for required_field in DFLOW_INPUT_CONTRACT_FIXTURE_V024_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.24 D-Flow input-contract row missing {required_field}")
        if method != "D-Flow / PeptideDesign":
            errors.append("D-Flow v0.24 input-contract row must be for D-Flow / PeptideDesign")
        if row.get("status") != "input_contract_ready_fixture":
            errors.append("D-Flow v0.24 fixture status must be input_contract_ready_fixture")
        if row.get("pep_dataset_reset_true_status") != "passed":
            errors.append("D-Flow v0.24 PepDataset reset=True status must be passed")
        if row.get("pep_dataset_reset_false_status") != "passed":
            errors.append("D-Flow v0.24 PepDataset reset=False status must be passed")
        if row.get("lmdb_entries") != "1":
            errors.append("D-Flow v0.24 fixture must record exactly 1 LMDB entry")
        for token in ["pep_pocket_test_structure_cache.lmdb", "scripts/prepare_dflow_input_contract.py"]:
            if token not in text:
                errors.append(f"D-Flow v0.24 input-contract row missing token {token}")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append("D-Flow v0.24 evidence boundary must say not Benchmark result")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "smoke_test_ready", "benchmark_ready"]:
            if forbidden in lower_text:
                errors.append(f"D-Flow v0.24 input-contract row overclaims {forbidden}")

    if len(dflow_full_pepmerge_download_v025_rows) != 1:
        errors.append(
            "dflow_full_pepmerge_download_v0.25.csv should contain 1 row, "
            f"found {len(dflow_full_pepmerge_download_v025_rows)}"
        )
    for row in dflow_full_pepmerge_download_v025_rows:
        method = row.get("method", "")
        text = " ".join(row.values())
        lower_text = text.lower()
        for required_field in DFLOW_FULL_PEPMERGE_DOWNLOAD_V025_HEADERS:
            if not row.get(required_field):
                errors.append(f"{method}: v0.25 D-Flow full PepMerge row missing {required_field}")
        if method != "D-Flow / PeptideDesign":
            errors.append("D-Flow v0.25 full PepMerge row must be for D-Flow / PeptideDesign")
        if row.get("download_status") != "downloaded_verified":
            errors.append("D-Flow v0.25 full PepMerge download status must be downloaded_verified")
        if row.get("release_zip_integrity_status") != "unzip_test_passed":
            errors.append("D-Flow v0.25 release zip integrity status must be unzip_test_passed")
        if row.get("lmdb_zip_integrity_status") != "unzip_test_passed":
            errors.append("D-Flow v0.25 LMDB zip integrity status must be unzip_test_passed")
        expected_values = {
            "case_dirs": "10348",
            "required_file_missing_case_dirs": "0",
            "test_names": "154",
            "train_names": "9849",
            "test_names_missing_in_release": "0",
            "pep_dataset_test_entries": "154",
            "pep_dataset_train_entries": "9849",
        }
        for key, expected in expected_values.items():
            if row.get(key) != expected:
                errors.append(f"D-Flow v0.25 {key} must be {expected}")
        if row.get("pep_dataset_load_status") != "passed":
            errors.append("D-Flow v0.25 PepDataset load status must be passed")
        if row.get("status") != "input_contract_ready_full_pepmerge":
            errors.append("D-Flow v0.25 status must be input_contract_ready_full_pepmerge")
        for token in ["PepMerge_release.zip", "PepMerge_lmdb.zip", "drive.usercontent.google.com"]:
            if token not in text:
                errors.append(f"D-Flow v0.25 full PepMerge row missing token {token}")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append("D-Flow v0.25 evidence boundary must say not Benchmark result")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "smoke_test_ready", "benchmark_ready"]:
            if forbidden in lower_text and f"not {forbidden}" not in lower_text:
                errors.append(f"D-Flow v0.25 full PepMerge row overclaims {forbidden}")

    expected_v026_ids = {
        "v026_dflow_bounded_dry_run",
        "v026_colabdesign_cli_adapter",
        "v026_bindcraft_wrapper_classifier",
    }
    observed_v026_ids = {row.get("item_id", "") for row in dflow_colab_bindcraft_v026_rows}
    missing_v026_ids = sorted(expected_v026_ids - observed_v026_ids)
    if missing_v026_ids:
        errors.append("dflow_colabdesign_bindcraft_v0.26.csv missing items: " + ", ".join(missing_v026_ids))
    if len(dflow_colab_bindcraft_v026_rows) != len(expected_v026_ids):
        errors.append(
            f"dflow_colabdesign_bindcraft_v0.26.csv should contain {len(expected_v026_ids)} rows, "
            f"found {len(dflow_colab_bindcraft_v026_rows)}"
        )
    for row in dflow_colab_bindcraft_v026_rows:
        item_id = row.get("item_id", "")
        text = " ".join(row.values()).lower()
        for required_field in DFLOW_COLAB_BINDCRAFT_V026_HEADERS:
            if not row.get(required_field):
                errors.append(f"{item_id}: v0.26 gate row missing {required_field}")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{item_id}: v0.26 gate evidence boundary must say not Benchmark result")
        if item_id == "v026_dflow_bounded_dry_run":
            if row.get("status") != "bounded_dry_run_passed":
                errors.append("D-Flow v0.26 bounded dry-run status must be bounded_dry_run_passed")
            if row.get("exit_code") != "0":
                errors.append("D-Flow v0.26 bounded dry-run exit_code must be 0")
            for token in ["sample_0.pdb", "outputs_csv", "parsed"]:
                if token not in text:
                    errors.append(f"D-Flow v0.26 bounded dry-run row missing token {token}")
        if item_id == "v026_colabdesign_cli_adapter":
            if row.get("status") != "cli_adapter_defined":
                errors.append("ColabDesign v0.26 status must be cli_adapter_defined")
            if row.get("execution_status") != "dry_run_package_only":
                errors.append("ColabDesign v0.26 execution_status must be dry_run_package_only")
            if "no gpu design run" not in text:
                errors.append("ColabDesign v0.26 row must preserve no GPU design run boundary")
        if item_id == "v026_bindcraft_wrapper_classifier":
            if row.get("parser_or_classifier_status") != "low_confidence_only":
                errors.append("BindCraft v0.26 classifier status must be low_confidence_only")
            if "accepted_final" not in text:
                errors.append("BindCraft v0.26 classifier row must mention accepted_final")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready"]:
            if forbidden in text:
                errors.append(f"{item_id}: v0.26 gate row overclaims {forbidden}")

    expected_v027_ids = {
        "v027_colabdesign_bounded_execute_gate",
        "v027_dexdesign_route_audit",
    }
    observed_v027_ids = {row.get("item_id", "") for row in colabdesign_dexdesign_gate_v027_rows}
    missing_v027_ids = sorted(expected_v027_ids - observed_v027_ids)
    if missing_v027_ids:
        errors.append("colabdesign_dexdesign_gate_v0.27.csv missing items: " + ", ".join(missing_v027_ids))
    if len(colabdesign_dexdesign_gate_v027_rows) != len(expected_v027_ids):
        errors.append(
            f"colabdesign_dexdesign_gate_v0.27.csv should contain {len(expected_v027_ids)} rows, "
            f"found {len(colabdesign_dexdesign_gate_v027_rows)}"
        )
    for row in colabdesign_dexdesign_gate_v027_rows:
        item_id = row.get("item_id", "")
        text = " ".join(row.values()).lower()
        for required_field in COLABDESIGN_DEXDESIGN_GATE_V027_HEADERS:
            if not row.get(required_field):
                errors.append(f"{item_id}: v0.27 gate row missing {required_field}")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{item_id}: v0.27 gate evidence boundary must say not Benchmark result")
        if item_id == "v027_colabdesign_bounded_execute_gate":
            if row.get("method") != "AfCycDesign / ColabDesign cyclic peptide":
                errors.append("ColabDesign v0.27 row has wrong method")
            if row.get("status") not in {"blocked_af_params_missing", "bounded_gpu_generation_passed"}:
                errors.append("ColabDesign v0.27 status must be blocked_af_params_missing or bounded_gpu_generation_passed")
            if row.get("status") == "blocked_af_params_missing" and "af" not in row.get("blocker", "").lower():
                errors.append("ColabDesign v0.27 blocked row must mention AF parameter blocker")
            if row.get("status") == "blocked_af_params_missing" and row.get("exit_code") != "not_run":
                errors.append("ColabDesign v0.27 blocked row exit_code must be not_run")
            if row.get("status") == "blocked_af_params_missing" and "no_gpu_generation" not in row.get("gpu_evidence", ""):
                errors.append("ColabDesign v0.27 blocked row must preserve no GPU generation evidence")
        if item_id == "v027_dexdesign_route_audit":
            if row.get("method") != "DexDesign / OSPREY3":
                errors.append("DexDesign v0.27 row has wrong method")
            if row.get("generic_osprey_example_status") != "env_probe_only_not_dexdesign":
                errors.append("DexDesign v0.27 generic OSPREY example status must be env_probe_only_not_dexdesign")
            if row.get("status") != "blocked_dexdesign_input_contract":
                errors.append("DexDesign v0.27 status must remain blocked_dexdesign_input_contract")
            if "ccs.d-peptide-l-protein" not in text:
                errors.append("DexDesign v0.27 row must mention ccs.D-peptide-L-protein route")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready"]:
            if forbidden in text:
                errors.append(f"{item_id}: v0.27 gate row overclaims {forbidden}")

    expected_v028_ids = {
        "v028_colabdesign_af_params_target_gate",
        "v028_dexdesign_input_contract",
        "v028_bindcraft_accepted_final",
    }
    observed_v028_ids = {row.get("item_id", "") for row in external_asset_rescue_v028_rows}
    missing_v028_ids = sorted(expected_v028_ids - observed_v028_ids)
    if missing_v028_ids:
        errors.append("external_asset_rescue_v0.28.csv missing items: " + ", ".join(missing_v028_ids))
    if len(external_asset_rescue_v028_rows) != len(expected_v028_ids):
        errors.append(
            f"external_asset_rescue_v0.28.csv should contain {len(expected_v028_ids)} rows, "
            f"found {len(external_asset_rescue_v028_rows)}"
        )
    for row in external_asset_rescue_v028_rows:
        item_id = row.get("item_id", "")
        text = " ".join(row.values()).lower()
        for required_field in EXTERNAL_ASSET_RESCUE_V028_HEADERS:
            if not row.get(required_field):
                errors.append(f"{item_id}: v0.28 rescue row missing {required_field}")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{item_id}: v0.28 evidence boundary must say not Benchmark result")
        if item_id == "v028_colabdesign_af_params_target_gate":
            if row.get("status") != "asset_gate_ready_no_generation":
                errors.append("ColabDesign v0.28 rescue status must be asset_gate_ready_no_generation")
            for token in ["alphafold_db/params", "7zkr_GABARAP.pdb", "no generated design"]:
                if token.lower() not in text:
                    errors.append(f"ColabDesign v0.28 row missing token {token}")
        if item_id == "v028_dexdesign_input_contract":
            if row.get("status") != "input_contract_defined_fixture_missing":
                errors.append("DexDesign v0.28 status must be input_contract_defined_fixture_missing")
            for token in ["l-target first chain", "d-peptide second chain", "target=z", "peptide=y"]:
                if token not in text:
                    errors.append(f"DexDesign v0.28 row missing token {token}")
        if item_id == "v028_bindcraft_accepted_final":
            if row.get("status") != "accepted_final_found":
                errors.append("BindCraft v0.28 status must be accepted_final_found")
            for token in ["accepted_final_count_4", "4 accepted pdb"]:
                if token not in text:
                    errors.append(f"BindCraft v0.28 row missing token {token}")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready"]:
            if forbidden in text:
                errors.append(f"{item_id}: v0.28 rescue row overclaims {forbidden}")

    expected_v029_ids = {
        "v029_colabdesign_bounded_generation",
        "v029_dexdesign_minimal_fixture",
        "v029_bindcraft_candidate_parser",
    }
    observed_v029_ids = {row.get("item_id", "") for row in bounded_generation_parser_v029_rows}
    missing_v029_ids = sorted(expected_v029_ids - observed_v029_ids)
    if missing_v029_ids:
        errors.append("bounded_generation_parser_v0.29.csv missing items: " + ", ".join(missing_v029_ids))
    if len(bounded_generation_parser_v029_rows) != len(expected_v029_ids):
        errors.append(
            f"bounded_generation_parser_v0.29.csv should contain {len(expected_v029_ids)} rows, "
            f"found {len(bounded_generation_parser_v029_rows)}"
        )
    for row in bounded_generation_parser_v029_rows:
        item_id = row.get("item_id", "")
        text = " ".join(row.values()).lower()
        for required_field in BOUNDED_GENERATION_PARSER_V029_HEADERS:
            if not row.get(required_field):
                errors.append(f"{item_id}: v0.29 row missing {required_field}")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{item_id}: v0.29 evidence boundary must say not Benchmark result")
        if item_id == "v029_colabdesign_bounded_generation":
            if row.get("method") != "AfCycDesign / ColabDesign cyclic peptide":
                errors.append("ColabDesign v0.29 row has wrong method")
            if row.get("status") != "bounded_gpu_generation_passed":
                errors.append("ColabDesign v0.29 status must be bounded_gpu_generation_passed")
            if row.get("exit_code") != "0":
                errors.append("ColabDesign v0.29 exit_code must be 0")
            if row.get("parser_status") != "parsed":
                errors.append("ColabDesign v0.29 parser_status must be parsed")
            if row.get("candidate_count") != "1":
                errors.append("ColabDesign v0.29 candidate_count must be 1")
            for token in ["7zkr_gabarap.pdb", "alphafold_db/params", "single_seed_single_model_ultra_smoke"]:
                if token not in text:
                    errors.append(f"ColabDesign v0.29 row missing token {token}")
        if item_id == "v029_dexdesign_minimal_fixture":
            if row.get("method") != "DexDesign / OSPREY3":
                errors.append("DexDesign v0.29 row has wrong method")
            if row.get("status") != "dexdesign_input_contract_ready_fixture_created":
                errors.append("DexDesign v0.29 status must be dexdesign_input_contract_ready_fixture_created")
            if row.get("parser_status") != "not_applicable":
                errors.append("DexDesign v0.29 parser_status must be not_applicable")
            if row.get("candidate_count") != "0":
                errors.append("DexDesign v0.29 candidate_count must be 0")
            for token in ["prepared d-l complex", "target=z", "peptide=y"]:
                if token not in text:
                    errors.append(f"DexDesign v0.29 row missing token {token}")
        if item_id == "v029_bindcraft_candidate_parser":
            if row.get("method") != "BindCraft":
                errors.append("BindCraft v0.29 row has wrong method")
            if row.get("status") != "accepted_candidate_parser_passed":
                errors.append("BindCraft v0.29 status must be accepted_candidate_parser_passed")
            if row.get("parser_status") != "parsed":
                errors.append("BindCraft v0.29 parser_status must be parsed")
            if row.get("candidate_count") != "4":
                errors.append("BindCraft v0.29 candidate_count must be 4")
            for token in ["accepted", "final_design_stats.csv", "external accepted-final parser fixture"]:
                if token not in text:
                    errors.append(f"BindCraft v0.29 row missing token {token}")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready"]:
            if forbidden in text:
                errors.append(f"{item_id}: v0.29 row overclaims {forbidden}")

    expected_v030_target_ids = {
        "pepmlm_sequence_contract_fixture",
        "mdm2_p53_3eqs_fixture",
        "gabarap_7zkr_fixture",
        "mhcii_hiv_1sjh_fixture",
        "pdl1_workbench_fixture",
        "dexdesign_synthetic_d_l_fixture",
        "bindcraft_cd47_method_example_control",
    }
    observed_v030_target_ids = {row.get("pilot_target_id", "") for row in pilot_benchmark_target_v030_rows}
    missing_v030_target_ids = sorted(expected_v030_target_ids - observed_v030_target_ids)
    if missing_v030_target_ids:
        errors.append(
            "pilot_benchmark_target_manifest_v0.30.csv missing targets: "
            + ", ".join(missing_v030_target_ids)
        )
    if len(pilot_benchmark_target_v030_rows) != len(expected_v030_target_ids):
        errors.append(
            "pilot_benchmark_target_manifest_v0.30.csv should contain "
            f"{len(expected_v030_target_ids)} rows, found {len(pilot_benchmark_target_v030_rows)}"
        )
    if target_set_rows:
        errors.append("target_set_v0.csv must remain empty before v0.30 target/control freeze review")
    expected_v030_lanes = {
        "pepmlm_sequence_contract_fixture": "wave_a_sequence_generation",
        "mdm2_p53_3eqs_fixture": "wave_a_structure_generation",
        "gabarap_7zkr_fixture": "wave_a_topology_parser",
        "mhcii_hiv_1sjh_fixture": "review_only",
        "pdl1_workbench_fixture": "reserve_only",
        "dexdesign_synthetic_d_l_fixture": "wave_b_input_contract_smoke",
        "bindcraft_cd47_method_example_control": "wave_b_wrapper_control",
    }
    for row in pilot_benchmark_target_v030_rows:
        pilot_target_id = row.get("pilot_target_id", "")
        text = " ".join(row.values()).lower()
        for required_field in PILOT_BENCHMARK_TARGET_V030_HEADERS:
            if not row.get(required_field):
                errors.append(f"{pilot_target_id}: v0.30 target row missing {required_field}")
        if row.get("benchmark_lane") != expected_v030_lanes.get(pilot_target_id):
            errors.append(f"{pilot_target_id}: unexpected v0.30 benchmark_lane {row.get('benchmark_lane')}")
        if row.get("target_status") == "frozen_target_set":
            errors.append(f"{pilot_target_id}: v0.30 target row must not be frozen_target_set")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{pilot_target_id}: v0.30 target evidence boundary must say not Benchmark result")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready", "wet_lab_validated"]:
            if forbidden in text:
                errors.append(f"{pilot_target_id}: v0.30 target row overclaims {forbidden}")

    expected_v030_control_ids = {
        "pepmlm_sequence_noncanonical_parser_control",
        "mdm2_positive_complex_chain_control",
        "mdm2_negative_control_placeholder",
        "gabarap_noncanonical_parser_control",
        "mhcii_chain_d_confounder_control",
        "pdl1_local_provenance_control",
        "dexdesign_synthetic_chain_contract_control",
        "bindcraft_accepted_final_parser_control",
    }
    observed_v030_control_ids = {row.get("control_id", "") for row in pilot_benchmark_control_v030_rows}
    missing_v030_control_ids = sorted(expected_v030_control_ids - observed_v030_control_ids)
    if missing_v030_control_ids:
        errors.append(
            "pilot_benchmark_control_manifest_v0.30.csv missing controls: "
            + ", ".join(missing_v030_control_ids)
        )
    if len(pilot_benchmark_control_v030_rows) != len(expected_v030_control_ids):
        errors.append(
            "pilot_benchmark_control_manifest_v0.30.csv should contain "
            f"{len(expected_v030_control_ids)} rows, found {len(pilot_benchmark_control_v030_rows)}"
        )
    for row in pilot_benchmark_control_v030_rows:
        control_id = row.get("control_id", "")
        text = " ".join(row.values()).lower()
        for required_field in PILOT_BENCHMARK_CONTROL_V030_HEADERS:
            if not row.get(required_field):
                errors.append(f"{control_id}: v0.30 control row missing {required_field}")
        if row.get("pilot_target_id") not in observed_v030_target_ids:
            errors.append(f"{control_id}: v0.30 control references unknown pilot_target_id")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{control_id}: v0.30 control evidence boundary must say not Benchmark result")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready", "wet_lab_validated"]:
            if forbidden in text:
                errors.append(f"{control_id}: v0.30 control row overclaims {forbidden}")

    wave_a_v030_jobs = [row for row in pilot_benchmark_job_v030_rows if row.get("execution_wave") == "wave_a"]
    wave_b_v030_jobs = [row for row in pilot_benchmark_job_v030_rows if row.get("execution_wave") == "wave_b"]
    blocked_v030_jobs = [row for row in pilot_benchmark_job_v030_rows if row.get("execution_wave") == "blocked"]
    if len(wave_a_v030_jobs) != 14:
        errors.append(f"pilot_benchmark_job_manifest_v0.30.csv should contain 14 Wave A jobs, found {len(wave_a_v030_jobs)}")
    if len(wave_b_v030_jobs) != 2:
        errors.append(f"pilot_benchmark_job_manifest_v0.30.csv should contain 2 Wave B jobs, found {len(wave_b_v030_jobs)}")
    if len(blocked_v030_jobs) != 1:
        errors.append(f"pilot_benchmark_job_manifest_v0.30.csv should contain 1 blocked job, found {len(blocked_v030_jobs)}")
    expected_v030_wave_a_methods = {
        "PepMLM",
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "PepMirror",
        "RFdiffusion + ProteinMPNN",
        "AfCycDesign / ColabDesign cyclic peptide",
    }
    observed_v030_wave_a_methods = {row.get("method", "") for row in wave_a_v030_jobs}
    if observed_v030_wave_a_methods != expected_v030_wave_a_methods:
        errors.append("pilot_benchmark_job_manifest_v0.30.csv Wave A methods do not match expected set")
    if {row.get("random_seed", "") for row in wave_a_v030_jobs} != {"42", "43"}:
        errors.append("pilot_benchmark_job_manifest_v0.30.csv Wave A jobs must use seeds 42 and 43")
    job_ids_v030 = {row.get("job_id", "") for row in pilot_benchmark_job_v030_rows}
    for row in pilot_benchmark_job_v030_rows:
        job_id = row.get("job_id", "")
        text = " ".join(row.values()).lower()
        for required_field in PILOT_BENCHMARK_JOB_V030_HEADERS:
            optional_v030_job_fields = {"target_sequence", "target_pdb", "pocket_definition"}
            if row.get("execution_wave") == "blocked":
                optional_v030_job_fields.update({"random_seed"})
            if not row.get(required_field) and required_field not in optional_v030_job_fields:
                errors.append(f"{job_id}: v0.30 job row missing {required_field}")
        if row.get("execution_wave") != "blocked" and row.get("pilot_target_id") not in observed_v030_target_ids:
            errors.append(f"{job_id}: v0.30 job references unknown pilot_target_id")
        if row.get("execution_wave") == "wave_a" and row.get("status") != "planned_pilot":
            errors.append(f"{job_id}: v0.30 Wave A job status must be planned_pilot")
        if row.get("execution_wave") == "blocked":
            if row.get("method") != "SaLT&PepPr" or row.get("status") != "blocked_license":
                errors.append(f"{job_id}: v0.30 blocked lane must be SaLT&PepPr blocked_license")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{job_id}: v0.30 job evidence boundary must say not Benchmark result")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready", "wet_lab_validated"]:
            if forbidden in text:
                errors.append(f"{job_id}: v0.30 job row overclaims {forbidden}")

    matrix_job_ids_v030 = {row.get("job_id", "") for row in pilot_execution_matrix_v030_rows}
    if matrix_job_ids_v030 != job_ids_v030:
        errors.append("pilot_execution_matrix_v0.30.csv job_id set must match pilot_benchmark_job_manifest_v0.30.csv")
    if len(pilot_execution_matrix_v030_rows) != len(pilot_benchmark_job_v030_rows):
        errors.append(
            "pilot_execution_matrix_v0.30.csv row count must match pilot_benchmark_job_manifest_v0.30.csv"
        )
    for row in pilot_execution_matrix_v030_rows:
        execution_id = row.get("execution_id", "")
        text = " ".join(row.values()).lower()
        for required_field in PILOT_EXECUTION_MATRIX_V030_HEADERS:
            if not row.get(required_field):
                errors.append(f"{execution_id}: v0.30 execution row missing {required_field}")
        output_root = row.get("output_root", "")
        if not (output_root.startswith("benchmark_runs/v0.31/") or output_root == "not_applicable"):
            errors.append(f"{execution_id}: v0.30 output_root must point to benchmark_runs/v0.31 or not_applicable")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append(f"{execution_id}: v0.30 execution evidence boundary must say not Benchmark result")
        for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready", "wet_lab_validated"]:
            if forbidden in text:
                errors.append(f"{execution_id}: v0.30 execution row overclaims {forbidden}")

    expected_v030_wet_lab_ids = {
        "wetlab_mdm2_p53",
        "wetlab_gabarap_stapled",
        "wetlab_ncam1_sequence",
        "wetlab_amhr2_sequence",
    }
    observed_v030_wet_lab_ids = {row.get("wet_lab_candidate_id", "") for row in wet_lab_candidate_panel_v030_rows}
    missing_v030_wet_lab_ids = sorted(expected_v030_wet_lab_ids - observed_v030_wet_lab_ids)
    if missing_v030_wet_lab_ids:
        errors.append(
            "wet_lab_candidate_panel_v0.30.csv missing candidates: "
            + ", ".join(missing_v030_wet_lab_ids)
        )
    if len(wet_lab_candidate_panel_v030_rows) != len(expected_v030_wet_lab_ids):
        errors.append(
            f"wet_lab_candidate_panel_v0.30.csv should contain {len(expected_v030_wet_lab_ids)} rows, "
            f"found {len(wet_lab_candidate_panel_v030_rows)}"
        )
    for row in wet_lab_candidate_panel_v030_rows:
        wet_lab_candidate_id = row.get("wet_lab_candidate_id", "")
        text = " ".join(row.values()).lower()
        for required_field in WET_LAB_CANDIDATE_PANEL_V030_HEADERS:
            if not row.get(required_field):
                errors.append(f"{wet_lab_candidate_id}: v0.30 wet-lab candidate row missing {required_field}")
        if row.get("status") != "prospective_not_run":
            errors.append(f"{wet_lab_candidate_id}: v0.30 wet-lab status must be prospective_not_run")
        if "not wet-lab validated" not in row.get("evidence_boundary", ""):
            errors.append(f"{wet_lab_candidate_id}: v0.30 wet-lab boundary must say not wet-lab validated")
        if "not benchmark result" not in text:
            errors.append(f"{wet_lab_candidate_id}: v0.30 wet-lab row must preserve not Benchmark result boundary")
        for forbidden in ["wet_lab_validated", "benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready"]:
            if forbidden in text:
                errors.append(f"{wet_lab_candidate_id}: v0.30 wet-lab row overclaims {forbidden}")

    pilot_benchmark_design_audit_v030_text = (
        ROOT / "ops/audits/pilot_benchmark_design_audit_v0.30.md"
    ).read_text(encoding="utf-8")
    for token in [
        "Pilot Benchmark Design Audit v0.30",
        "target_set_v0.csv remains empty",
        "Wave A: 14 planned jobs",
        "Wave B: 2 planned control/smoke jobs",
        "SaLT&PepPr remains blocked",
        "not Benchmark result",
    ]:
        if token not in pilot_benchmark_design_audit_v030_text:
            errors.append(f"pilot_benchmark_design_audit_v0.30.md missing token {token}")

    wave_a_job_ids_v030 = {row.get("job_id", "") for row in wave_a_v030_jobs}
    v031_table_sets = {
        "pilot_execution_results_v0.31.csv": {row.get("job_id", "") for row in pilot_execution_results_v031_rows},
        "pilot_method_output_manifest_v0.31.csv": {row.get("job_id", "") for row in pilot_method_output_v031_rows},
        "pilot_candidate_outputs_v0.31.csv": {row.get("job_id", "") for row in pilot_candidate_output_v031_rows},
        "pilot_run_v0.31.csv": {row.get("parent_job_id", "") for row in pilot_run_v031_rows},
    }
    for artifact_name, observed_job_ids in v031_table_sets.items():
        if observed_job_ids != wave_a_job_ids_v030:
            errors.append(f"{artifact_name} job set must exactly match v0.30 Wave A jobs")
    for artifact_name, rows in [
        ("pilot_execution_results_v0.31.csv", pilot_execution_results_v031_rows),
        ("pilot_method_output_manifest_v0.31.csv", pilot_method_output_v031_rows),
        ("pilot_candidate_outputs_v0.31.csv", pilot_candidate_output_v031_rows),
        ("pilot_run_v0.31.csv", pilot_run_v031_rows),
    ]:
        if len(rows) != 14:
            errors.append(f"{artifact_name} should contain 14 Wave A rows, found {len(rows)}")
        for row in rows:
            text = " ".join(row.values()).lower()
            if "not benchmark result" not in text:
                errors.append(f"{artifact_name}: {row.get('job_id') or row.get('parent_job_id') or row.get('design_id')} missing not Benchmark result boundary")
            for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready", "wet_lab_validated"]:
                if forbidden in text:
                    errors.append(
                        f"{artifact_name}: {row.get('job_id') or row.get('parent_job_id') or row.get('design_id')} overclaims {forbidden}"
                    )
    if sum(1 for row in pilot_execution_results_v031_rows if row.get("status") == "parsed") != 4:
        errors.append("pilot_execution_results_v0.31.csv should contain 4 parsed rows")
    if sum(1 for row in pilot_execution_results_v031_rows if row.get("status") == "failed") != 10:
        errors.append("pilot_execution_results_v0.31.csv should contain 10 failed rows")
    if sum(1 for row in pilot_method_output_v031_rows if row.get("parser_status") == "parsed") != 4:
        errors.append("pilot_method_output_manifest_v0.31.csv should contain 4 parsed rows")
    if sum(1 for row in pilot_method_output_v031_rows if row.get("parser_status") == "failed") != 10:
        errors.append("pilot_method_output_manifest_v0.31.csv should contain 10 failed rows")
    if sum(1 for row in pilot_candidate_output_v031_rows if row.get("parse_status") == "parsed") != 4:
        errors.append("pilot_candidate_outputs_v0.31.csv should contain 4 parsed rows")
    if sum(1 for row in pilot_candidate_output_v031_rows if row.get("parse_status") == "failed") != 10:
        errors.append("pilot_candidate_outputs_v0.31.csv should contain 10 failed rows")
    if sum(1 for row in pilot_run_v031_rows if row.get("status") == "generated") != 4:
        errors.append("pilot_run_v0.31.csv should contain 4 generated rows")
    if sum(1 for row in pilot_run_v031_rows if row.get("status") == "failed") != 10:
        errors.append("pilot_run_v0.31.csv should contain 10 failed rows")
    parsed_methods_v031 = {
        row.get("method", "")
        for row in pilot_candidate_output_v031_rows
        if row.get("parse_status") == "parsed"
    }
    if parsed_methods_v031 != {"PepMLM", "AfCycDesign / ColabDesign cyclic peptide"}:
        errors.append("pilot_candidate_outputs_v0.31.csv parsed methods must be PepMLM and ColabDesign only")
    failed_reasons_v031 = {
        row.get("status_reason", "")
        for row in pilot_candidate_output_v031_rows
        if row.get("parse_status") == "failed"
    }
    if failed_reasons_v031 != {"adapter_execution_failed_or_not_implemented_exit_86"}:
        errors.append("pilot_candidate_outputs_v0.31.csv failed rows must use the exit_86 adapter placeholder reason")
    for row in pilot_candidate_output_v031_rows:
        if row.get("parse_status") == "parsed" and row.get("method") == "PepMLM":
            if not row.get("sequence") or row.get("structure_path"):
                errors.append(f"{row.get('design_id')}: PepMLM v0.31 row must have sequence and no structure_path")
        if row.get("parse_status") == "parsed" and row.get("method") == "AfCycDesign / ColabDesign cyclic peptide":
            if len(row.get("sequence", "")) != 14:
                errors.append(f"{row.get('design_id')}: ColabDesign v0.31 sequence length must be 14")
            if "benchmark_runs/v0.31/colabdesign" not in row.get("structure_path", ""):
                errors.append(f"{row.get('design_id')}: ColabDesign v0.31 structure_path must point to gitignored v0.31 runtime root")
    for row in pilot_method_output_v031_rows:
        if row.get("method") == "AfCycDesign / ColabDesign cyclic peptide" and row.get("parser_status") == "parsed":
            if not row.get("command", "").endswith("colabdesign_inner_command.sh"):
                errors.append(f"{row.get('job_id')}: ColabDesign v0.31 method row must record inner command path")
    summary_v031_path = ROOT / "benchmark/results/pilot_v031_merge_summary.json"
    try:
        summary_v031 = json.loads(summary_v031_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"pilot_v031_merge_summary.json is not valid JSON: {exc}")
        summary_v031 = {}
    for key, expected in {
        "wave_a_jobs": 14,
        "method_rows": 14,
        "candidate_rows": 14,
        "run_rows": 14,
        "execution_rows": 14,
    }.items():
        if summary_v031.get(key) != expected:
            errors.append(f"pilot_v031_merge_summary.json {key} should be {expected}")
    if "not Benchmark result" not in summary_v031.get("evidence_boundary", ""):
        errors.append("pilot_v031_merge_summary.json must preserve not Benchmark result boundary")

    pilot_wave_a_execution_audit_v031_text = (
        ROOT / "ops/audits/pilot_wave_a_execution_audit_v0.31.md"
    ).read_text(encoding="utf-8")
    for token in [
        "Pilot Wave A Execution Audit v0.31",
        "14 Wave A jobs",
        "4 parsed",
        "10 failed",
        "PepMLM",
        "ColabDesign",
        "target_set_v0.csv remains empty",
        "not Benchmark result",
    ]:
        if token not in pilot_wave_a_execution_audit_v031_text:
            errors.append(f"pilot_wave_a_execution_audit_v0.31.md missing token {token}")

    v031_placeholder_job_ids = {
        row.get("job_id", "")
        for row in pilot_candidate_output_v031_rows
        if row.get("parse_status") == "failed"
        and row.get("status_reason") == "adapter_execution_failed_or_not_implemented_exit_86"
    }
    v033_table_sets = {
        "pilot_execution_results_v0.33.csv": {row.get("job_id", "") for row in pilot_execution_results_v033_rows},
        "pilot_method_output_manifest_v0.33.csv": {row.get("job_id", "") for row in pilot_method_output_v033_rows},
        "pilot_candidate_outputs_v0.33.csv": {row.get("job_id", "") for row in pilot_candidate_output_v033_rows},
        "pilot_run_v0.33.csv": {row.get("parent_job_id", "") for row in pilot_run_v033_rows},
    }
    for artifact_name, observed_job_ids in v033_table_sets.items():
        if observed_job_ids != v031_placeholder_job_ids:
            errors.append(f"{artifact_name} job set must exactly match v0.31 placeholder-failed Wave A jobs")
    for artifact_name, rows in [
        ("pilot_execution_results_v0.33.csv", pilot_execution_results_v033_rows),
        ("pilot_method_output_manifest_v0.33.csv", pilot_method_output_v033_rows),
        ("pilot_candidate_outputs_v0.33.csv", pilot_candidate_output_v033_rows),
        ("pilot_run_v0.33.csv", pilot_run_v033_rows),
    ]:
        if len(rows) != 10:
            errors.append(f"{artifact_name} should contain 10 v0.33 adapter completion rows, found {len(rows)}")
        for row in rows:
            text = " ".join(row.values()).lower()
            if "not benchmark result" not in text or "not scoring evidence" not in text:
                errors.append(f"{artifact_name}: {row.get('job_id') or row.get('parent_job_id') or row.get('design_id')} missing evidence boundary")
            for forbidden in ["benchmark_completed", "best_performing", "performance_ranking", "benchmark_ready", "smoke_test_ready", "wet_lab_validated"]:
                if forbidden in text:
                    errors.append(
                        f"{artifact_name}: {row.get('job_id') or row.get('parent_job_id') or row.get('design_id')} overclaims {forbidden}"
                    )
    if sum(1 for row in pilot_execution_results_v033_rows if row.get("status") == "failed") != 10:
        errors.append("pilot_execution_results_v0.33.csv should contain 10 failed rows")
    if sum(1 for row in pilot_method_output_v033_rows if row.get("parser_status") == "failed") != 10:
        errors.append("pilot_method_output_manifest_v0.33.csv should contain 10 failed parser rows")
    if sum(1 for row in pilot_candidate_output_v033_rows if row.get("parse_status") == "failed") != 10:
        errors.append("pilot_candidate_outputs_v0.33.csv should contain 10 failed candidate rows")
    if sum(1 for row in pilot_run_v033_rows if row.get("status") == "failed") != 10:
        errors.append("pilot_run_v0.33.csv should contain 10 failed run rows")
    v033_failed_methods = {
        row.get("method", "")
        for row in pilot_candidate_output_v033_rows
        if row.get("parse_status") == "failed"
    }
    if v033_failed_methods != {"DiffPepBuilder", "PepGLAD", "D-Flow / PeptideDesign", "PepMirror", "RFdiffusion + ProteinMPNN"}:
        errors.append("pilot_candidate_outputs_v0.33.csv failed methods must be the five v0.31 placeholder methods")
    for row in pilot_candidate_output_v033_rows:
        reason = row.get("status_reason", "")
        if reason == "adapter_execution_failed_or_not_implemented_exit_86":
            errors.append(f"{row.get('design_id')}: v0.33 rows must not reuse v0.31 placeholder exit_86 reason")
        if not reason.endswith("_adapter_attempt_no_supported_output_found"):
            errors.append(f"{row.get('design_id')}: v0.33 status_reason must record method-specific no-supported-output blocker")
    for row in pilot_method_output_v033_rows:
        if row.get("execution_stage") != "bounded_wave_a_adapter_completion_v0.33":
            errors.append(f"{row.get('job_id')}: v0.33 method row has wrong execution_stage")
    summary_v033_path = ROOT / "benchmark/results/pilot_v033_merge_summary.json"
    try:
        summary_v033 = json.loads(summary_v033_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"pilot_v033_merge_summary.json is not valid JSON: {exc}")
        summary_v033 = {}
    for key, expected in {
        "wave_a_jobs": 10,
        "method_rows": 10,
        "candidate_rows": 10,
        "run_rows": 10,
        "execution_rows": 10,
    }.items():
        if summary_v033.get(key) != expected:
            errors.append(f"pilot_v033_merge_summary.json {key} should be {expected}")
    if "not Benchmark result" not in summary_v033.get("evidence_boundary", ""):
        errors.append("pilot_v033_merge_summary.json must preserve not Benchmark result boundary")

    wave_a_adapter_parser_completion_audit_v033_text = (
        ROOT / "ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md"
    ).read_text(encoding="utf-8")
    for token in [
        "Wave A Adapter/Parser Completion Audit v0.33",
        "10 v0.31 placeholder-failed jobs",
        "10 failed",
        "no_supported_output_found",
        "not Benchmark result",
        "not scoring evidence",
    ]:
        if token not in wave_a_adapter_parser_completion_audit_v033_text:
            errors.append(f"wave_a_adapter_parser_completion_audit_v0.33.md missing token {token}")

    supervisor_skills_installation_v032_text = (
        ROOT / "ops/audits/supervisor_skills_installation_v0.32.md"
    ).read_text(encoding="utf-8")
    skill_selection_text = (ROOT / "ops/audits/skill_selection.md").read_text(encoding="utf-8")
    supervisor_memory_text = "\n".join(
        [agents_text, skill_selection_text, supervisor_skills_installation_v032_text]
    )
    for token in [
        "Supervisor-Skills",
        "HKUSTDial/Supervisor-Skills",
        "0b77a1b98794f8341d57685a0e829a3fa175d05f",
        "CC BY-NC-SA 4.0",
        "benchmark-paper-template",
        "intro-drafter",
        "figure-designer",
        "pre-submission-reviewer",
        "idea-evaluator",
        "not Benchmark result",
        "not scoring evidence",
        "not method-ranking evidence",
    ]:
        if token not in supervisor_memory_text:
            errors.append(f"Supervisor-Skills memory missing token {token}")
    if "benchmark-paper-template is the primary route" not in agents_text:
        errors.append("AGENTS.md must record Supervisor-Skills benchmark-paper-template primary route")
    if "intro-drafter is consistency-check only" not in agents_text:
        errors.append("AGENTS.md must record Supervisor-Skills intro-drafter consistency-check boundary")
    if "Restart Codex to pick up new skills" not in supervisor_skills_installation_v032_text:
        errors.append("supervisor_skills_installation_v0.32.md must remind to restart Codex")

    if len(dflow_bounded_candidate_v026_rows) != 1:
        errors.append(
            "dflow_bounded_candidate_outputs_v0.26.csv should contain 1 row, "
            f"found {len(dflow_bounded_candidate_v026_rows)}"
        )
    for row in dflow_bounded_candidate_v026_rows:
        if row.get("method") != "D-Flow / PeptideDesign":
            errors.append("D-Flow v0.26 candidate row must be for D-Flow / PeptideDesign")
        if row.get("parse_status") != "parsed":
            errors.append("D-Flow v0.26 candidate row parse_status must be parsed")
        if row.get("sequence") != "MRRRRRRRRY":
            errors.append("D-Flow v0.26 candidate row sequence must be MRRRRRRRRY")
        if "not target-set evidence" not in row.get("notes", ""):
            errors.append("D-Flow v0.26 candidate row must preserve target-set boundary")

    if len(bindcraft_classification_v026_rows) != 1:
        errors.append(
            "bindcraft_wrapper_classification_v0.26.csv should contain 1 row, "
            f"found {len(bindcraft_classification_v026_rows)}"
        )
    for row in bindcraft_classification_v026_rows:
        if row.get("method") != "BindCraft":
            errors.append("BindCraft v0.26 classification row must be for BindCraft")
        if row.get("classification") != "low_confidence_only":
            errors.append("BindCraft v0.26 classification must be low_confidence_only")
        if row.get("accepted_pdb_count") != "0":
            errors.append("BindCraft v0.26 accepted_pdb_count must be 0")
        if row.get("low_confidence_pdb_count") != "1":
            errors.append("BindCraft v0.26 low_confidence_pdb_count must be 1")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append("BindCraft v0.26 evidence boundary must say not Benchmark result")

    if len(bindcraft_accepted_final_v028_rows) != 1:
        errors.append(
            "bindcraft_accepted_final_classification_v0.28.csv should contain 1 row, "
            f"found {len(bindcraft_accepted_final_v028_rows)}"
        )
    for row in bindcraft_accepted_final_v028_rows:
        if row.get("method") != "BindCraft":
            errors.append("BindCraft v0.28 classification row must be for BindCraft")
        if row.get("classification") != "accepted_final":
            errors.append("BindCraft v0.28 classification must be accepted_final")
        if row.get("accepted_pdb_count") != "4":
            errors.append("BindCraft v0.28 accepted_pdb_count must be 4")
        if "not Benchmark result" not in row.get("evidence_boundary", ""):
            errors.append("BindCraft v0.28 evidence boundary must say not Benchmark result")

    if len(colabdesign_bounded_method_v029_rows) != 1:
        errors.append(
            "colabdesign_bounded_method_output_manifest_v0.29.csv should contain 1 row, "
            f"found {len(colabdesign_bounded_method_v029_rows)}"
        )
    for row in colabdesign_bounded_method_v029_rows:
        if row.get("method") != "AfCycDesign / ColabDesign cyclic peptide":
            errors.append("ColabDesign v0.29 method manifest row has wrong method")
        if row.get("execution_stage") != "bounded_gpu_generation":
            errors.append("ColabDesign v0.29 method manifest execution_stage must be bounded_gpu_generation")
        if row.get("exit_code") != "0":
            errors.append("ColabDesign v0.29 method manifest exit_code must be 0")
        if row.get("parser_status") != "parsed":
            errors.append("ColabDesign v0.29 method manifest parser_status must be parsed")
        if "not Benchmark result" not in row.get("status_reason", ""):
            errors.append("ColabDesign v0.29 method manifest must preserve not Benchmark result boundary")

    if len(colabdesign_bounded_candidate_v029_rows) != 1:
        errors.append(
            "colabdesign_bounded_candidate_outputs_v0.29.csv should contain 1 row, "
            f"found {len(colabdesign_bounded_candidate_v029_rows)}"
        )
    for row in colabdesign_bounded_candidate_v029_rows:
        if row.get("method") != "AfCycDesign / ColabDesign cyclic peptide":
            errors.append("ColabDesign v0.29 candidate row has wrong method")
        if row.get("parse_status") != "parsed":
            errors.append("ColabDesign v0.29 candidate parse_status must be parsed")
        if len(row.get("sequence", "")) != 14:
            errors.append("ColabDesign v0.29 candidate sequence length must be 14 for the bounded fixture")
        if "benchmark_runs/v0.29/colabdesign_bounded_generation" not in row.get("structure_path", ""):
            errors.append("ColabDesign v0.29 candidate structure_path must point to gitignored runtime root")
        if "not Benchmark result" not in row.get("notes", ""):
            errors.append("ColabDesign v0.29 candidate notes must preserve not Benchmark result boundary")

    if len(bindcraft_accepted_candidate_v029_rows) != 4:
        errors.append(
            "bindcraft_accepted_candidate_outputs_v0.29.csv should contain 4 rows, "
            f"found {len(bindcraft_accepted_candidate_v029_rows)}"
        )
    expected_bindcraft_sequences_v029 = {
        "SPKEEWRKRLAE",
        "APTGKELWRKRLAE",
        "PPTGKELWRKRLAE",
        "SPKEEWKARLRARR",
    }
    observed_bindcraft_sequences_v029 = {row.get("sequence", "") for row in bindcraft_accepted_candidate_v029_rows}
    if observed_bindcraft_sequences_v029 != expected_bindcraft_sequences_v029:
        errors.append("BindCraft v0.29 candidate sequences do not match accepted-final parser fixture")
    for row in bindcraft_accepted_candidate_v029_rows:
        if row.get("method") != "BindCraft":
            errors.append("BindCraft v0.29 candidate row has wrong method")
        if row.get("parse_status") != "parsed":
            errors.append("BindCraft v0.29 candidate parse_status must be parsed")
        if "Accepted" not in row.get("structure_path", ""):
            errors.append("BindCraft v0.29 candidate structure_path must point to Accepted output")
        if "not Benchmark result" not in row.get("notes", ""):
            errors.append("BindCraft v0.29 candidate notes must preserve not Benchmark result boundary")

    pilot_plan_text = (ROOT / "ops/plans/batch_b_pilot_execution_plan_v0.17.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "Batch B Pilot Execution Plan v0.17",
        "target_set_v0.csv",
        "batch_b_pilot_target_gate_v0.17.csv",
        "batch_b_pilot_job_manifest_v0.17.csv",
        "不新增 GPU run",
    ]:
        if token not in pilot_plan_text:
            errors.append(f"batch_b_pilot_execution_plan_v0.17.md missing token {token}")
    pilot_audit_text = (ROOT / "ops/audits/batch_b_pilot_readiness_audit_v0.17.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "Batch B Pilot Readiness Audit v0.17",
        "3EQS",
        "1SJH",
        "7ZKR",
        "pdl1_workbench_fixture",
        "No-Overclaim Boundary",
    ]:
        if token not in pilot_audit_text:
            errors.append(f"batch_b_pilot_readiness_audit_v0.17.md missing token {token}")
    replay_audit_text = (ROOT / "ops/audits/adapter_replay_fixture_audit_v0.18.md").read_text(
        encoding="utf-8"
    )
    method_install_smoke_audit_text = (ROOT / "ops/audits/method_install_smoke_audit_v0.19.md").read_text(
        encoding="utf-8"
    )
    method_unblock_audit_text = (ROOT / "ops/audits/method_unblock_audit_v0.20.md").read_text(
        encoding="utf-8"
    )
    adapter_smoke_audit_text = (ROOT / "ops/audits/adapter_smoke_audit_v0.21.md").read_text(
        encoding="utf-8"
    )
    multi_case_fixture_plan_text = (ROOT / "ops/plans/multi_case_fixture_pilot_plan_v0.22.md").read_text(
        encoding="utf-8"
    )
    multi_case_fixture_audit_text = (ROOT / "ops/audits/multi_case_fixture_pilot_audit_v0.22.md").read_text(
        encoding="utf-8"
    )
    external_dry_run_plan_text = (ROOT / "ops/plans/external_dry_run_package_plan_v0.23.md").read_text(
        encoding="utf-8"
    )
    external_dry_run_audit_text = (ROOT / "ops/audits/external_dry_run_package_audit_v0.23.md").read_text(
        encoding="utf-8"
    )
    for token in [
        "Adapter Replay Fixture Audit v0.18",
        "adapter_replay_fixture_manifest_v0.18.csv",
        "batch_a_replay_candidate_outputs_v0.18.csv",
        "parse_batch_a_replay_fixtures.py",
        "not Benchmark result",
    ]:
        if token not in replay_audit_text:
            errors.append(f"adapter_replay_fixture_audit_v0.18.md missing token {token}")
    for token in [
        "Method Install Smoke Audit v0.19",
        "method_source_doc_verification_v0.19.csv",
        "method_install_smoke_manifest_v0.19.csv",
        "method_smoke_test_results_v0.19.csv",
        "not Benchmark result",
    ]:
        if token not in method_install_smoke_audit_text:
            errors.append(f"method_install_smoke_audit_v0.19.md missing token {token}")
    for token in [
        "Method Unblock Audit v0.20",
        "method_unblock_manifest_v0.20.csv",
        "method_unblock_smoke_results_v0.20.csv",
        "not Benchmark result",
    ]:
        if token not in method_unblock_audit_text:
            errors.append(f"method_unblock_audit_v0.20.md missing token {token}")
    for token in [
        "Adapter Smoke Audit v0.21",
        "adapter_smoke_manifest_v0.21.csv",
        "adapter_smoke_results_v0.21.csv",
        "adapter_method_output_manifest_v0.21.csv",
        "not Benchmark result",
    ]:
        if token not in adapter_smoke_audit_text:
            errors.append(f"adapter_smoke_audit_v0.21.md missing token {token}")
    for token in [
        "Multi-case Fixture Pilot Plan v0.22",
        "method_example_fixture_evidence_v0.22.csv",
        "multi_case_fixture_target_manifest_v0.22.csv",
        "priority_gate_review_v0.22.csv",
        "D-Flow",
        "ColabDesign",
        "BindCraft",
    ]:
        if token not in multi_case_fixture_plan_text:
            errors.append(f"multi_case_fixture_pilot_plan_v0.22.md missing token {token}")
    for token in [
        "Multi-case Fixture Pilot Audit v0.22",
        "method_example_fixture_evidence_v0.22.csv",
        "multi_case_fixture_job_manifest_v0.22.csv",
        "priority_gate_review_v0.22.csv",
        "not Benchmark result",
        "No-Overclaim Boundary",
    ]:
        if token not in multi_case_fixture_audit_text:
            errors.append(f"multi_case_fixture_pilot_audit_v0.22.md missing token {token}")
    for token in [
        "External Dry-run Package Plan v0.23",
        "notebook_cli_smoke_manifest_v0.23.csv",
        "dflow_project_install_contract_v0.23.csv",
        "D-Flow",
        "ColabDesign",
        "BindCraft",
        "AlphaFold DB",
        "No-Overclaim Boundary",
    ]:
        if token not in external_dry_run_plan_text:
            errors.append(f"external_dry_run_package_plan_v0.23.md missing token {token}")
    for token in [
        "External Dry-run Package Audit v0.23",
        "external_dry_run_package_manifest_v0.23.csv",
        "priority_gate_review_v0.23.csv",
        "FileNotFoundError",
        "Google Drive",
        "not Benchmark result",
        "No-Overclaim Boundary",
    ]:
        if token not in external_dry_run_audit_text:
            errors.append(f"external_dry_run_package_audit_v0.23.md missing token {token}")
    for text_name, text_value in [
        ("batch_b_pilot_execution_plan_v0.17.md", pilot_plan_text.lower()),
        ("batch_b_pilot_readiness_audit_v0.17.md", pilot_audit_text.lower()),
        ("adapter_replay_fixture_audit_v0.18.md", replay_audit_text.lower()),
        ("method_install_smoke_audit_v0.19.md", method_install_smoke_audit_text.lower()),
        ("method_unblock_audit_v0.20.md", method_unblock_audit_text.lower()),
        ("adapter_smoke_audit_v0.21.md", adapter_smoke_audit_text.lower()),
        ("multi_case_fixture_pilot_plan_v0.22.md", multi_case_fixture_plan_text.lower()),
        ("multi_case_fixture_pilot_audit_v0.22.md", multi_case_fixture_audit_text.lower()),
        ("external_dry_run_package_plan_v0.23.md", external_dry_run_plan_text.lower()),
        ("external_dry_run_package_audit_v0.23.md", external_dry_run_audit_text.lower()),
    ]:
        for forbidden_phrase in [
            "benchmark completed",
            "best-performing",
            "experimentally validated",
            "problem-free",
            "benchmark_ready | reached",
            "smoke_test_ready | reached",
        ]:
            if has_unqualified_forbidden_wording(text_value, forbidden_phrase):
                errors.append(f"{text_name} contains overclaim phrase {forbidden_phrase}")

    adapter_methods = {row.get("method", ""): row for row in adapter_preflight_rows}
    for method in ["PepMLM", "RFdiffusion + ProteinMPNN", "PepMirror"]:
        if method not in adapter_methods:
            errors.append(f"adapter_preflight_status_v0.11.csv missing {method}")
    for method in ["PepMLM", "RFdiffusion + ProteinMPNN"]:
        row = adapter_methods.get(method, {})
        if row.get("batch") != "Batch_A":
            errors.append(f"{method}: v0.11 adapter row must remain Batch_A")
        if "artificial_dry_run" not in row.get("allowed_test_depth", ""):
            errors.append(f"{method}: v0.11 adapter must start with artificial dry-run planning")
    pepmirror_adapter = adapter_methods.get("PepMirror", {})
    if pepmirror_adapter and pepmirror_adapter.get("allowed_test_depth") != "none_dependency_blocked":
        errors.append("PepMirror v0.11 adapter row must remain dependency-blocked")
    for row in adapter_preflight_rows:
        for required_field in ["adapter_gate", "job_manifest_status", "input_adapter_status", "output_parser_status", "blocking_items", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('method')}: adapter preflight row missing {required_field}")
        text = " ".join(row.values()).lower()
        for forbidden in ["installed", "reproduced", "benchmark_ready"]:
            if forbidden in text:
                errors.append(f"{row.get('method')}: adapter preflight row overclaims {forbidden}")

    for row in method_output_manifest_rows:
        if row.get("parser_status") != "not_real_benchmark":
            errors.append(f"{row.get('run_record_id')}: example method output parser_status must be not_real_benchmark")
        if row.get("source_commit") != "not_cloned":
            errors.append(f"{row.get('run_record_id')}: example method output source_commit must be not_cloned")
        if row.get("command") != "placeholder_only_do_not_run":
            errors.append(f"{row.get('run_record_id')}: example method output command must remain placeholder_only_do_not_run")
        if not row.get("raw_output_root", "").startswith("/srv/pep_design/"):
            errors.append(f"{row.get('run_record_id')}: raw output root must be an external /srv/pep_design path")

    for row in candidate_output_rows:
        if row.get("parse_status") != "not_real_benchmark":
            errors.append(f"{row.get('design_id')}: example candidate output parse_status must be not_real_benchmark")
        if row.get("source_output_id") != "not_generated":
            errors.append(f"{row.get('design_id')}: example candidate output must not imply generated output")
        if row.get("method") not in {"PepMLM", "RFdiffusion + ProteinMPNN"}:
            errors.append(f"{row.get('design_id')}: example candidate output should only cover Batch A")

    source_io_plan_text = (ROOT / "ops/plans/source_io_smoke_test_plan_v0.11.md").read_text(encoding="utf-8")
    for token in [
        "不 clone",
        "不下载",
        "不安装",
        "不运行 GPU",
        "job_manifest.csv",
        "method_output_manifest.csv",
        "candidate_outputs.csv",
        "Batch A",
        "PepMirror",
        "download_performed=no",
    ]:
        if token not in source_io_plan_text:
            errors.append(f"source_io_smoke_test_plan_v0.11.md missing token {token}")

    adapter_contract_text = (
        ROOT / "benchmark/deployment/method_contracts/batch_a_adapter_contract_v0.11.md"
    ).read_text(encoding="utf-8")
    for token in ["planning_only_no_run", "PepMLM Adapter", "RFdiffusion + ProteinMPNN Adapter", "PepMirror Boundary"]:
        if token not in adapter_contract_text:
            errors.append(f"batch_a_adapter_contract_v0.11.md missing token {token}")

    if len(migration_rows) < 10:
        errors.append("file_role_map_v0.10.csv should record the major path migrations")
    for row in migration_rows:
        for required_field in MIGRATION_FILE_ROLE_HEADERS:
            if not row.get(required_field):
                errors.append(f"migration row missing {required_field}: {row}")
        if row.get("validator_required") not in {"yes", "no"}:
            errors.append(f"{row.get('old_path')}: migration validator_required must be yes or no")

    dataset_source_ids = {row.get("dataset_id", "") for row in reference_dataset_source_rows}
    for dataset_id in ["overath_binder_success_2025", "pepbi_dryad_2025", "pepbenchmark_2026", "gpcr_peptide_benchmark_2026", "tcrtransbench_2026", "chang_af2_ranking_cases_2023"]:
        if dataset_id not in dataset_source_ids:
            errors.append(f"reference_dataset_sources_v1.csv missing {dataset_id}")
    if len(reference_dataset_source_rows) < 7:
        errors.append("reference_dataset_sources_v1.csv should include at least seven reference dataset sources")
    for row in reference_dataset_source_rows:
        for required_field in ["source_name", "task_fit", "source_url", "license_status", "schema_status", "assay_readout", "positive_controls", "negative_controls", "leakage_risk", "download_status", "planned_use", "next_action"]:
            if not row.get(required_field):
                errors.append(f"{row.get('dataset_id')}: reference dataset source row missing {required_field}")
        download_status = row.get("download_status", "").lower()
        if "download_performed" not in download_status and "pending" not in download_status:
            errors.append(f"{row.get('dataset_id')}: download_status must record no-download or pending status")
        if "frozen" in row.get("planned_use", "").lower():
            errors.append(f"{row.get('dataset_id')}: reference dataset planned_use must not imply frozen target promotion")

    test_design_text = (ROOT / "manuscript/support/benchmark_test_design_v1.md").read_text(encoding="utf-8")
    for token in [
        "Generation Benchmark",
        "Ranking / Rescoring Benchmark",
        "T1_sequence_binder",
        "T2_structure_peptide_binder",
        "T3_miniprotein_binder_baseline",
        "No performance values",
        "v1.1 Supplementary Scoring Rationale",
        "binding region",
        "cyclization mode",
    ]:
        if token not in test_design_text:
            errors.append(f"benchmark_test_design_v1.md missing token {token}")

    todo_ids = {row.get("todo_id", "") for row in manuscript_todo_rows}
    if len(todo_ids) < 10:
        errors.append("benchmark_manuscript_todo_v1.csv should contain manuscript and readiness TODO items")
    for row in manuscript_todo_rows:
        if row.get("priority") not in {"high", "medium", "low"}:
            errors.append(f"{row.get('todo_id')}: invalid TODO priority {row.get('priority')}")
        if row.get("status") not in {"open", "done", "deferred"}:
            errors.append(f"{row.get('todo_id')}: invalid TODO status {row.get('status')}")
        for required_field in ["artifact", "task", "evidence", "next_action", "blocking_issue"]:
            if not row.get(required_field):
                errors.append(f"{row.get('todo_id')}: TODO row missing {required_field}")

    bibliography_text = (ROOT / "manuscript/support/benchmark_reference_bibliography_v1.md").read_text(encoding="utf-8")
    for token in ["Core Method References", "Benchmark, Ranking and Scoring References", "Dataset and Benchmark Source References", "needs_bibtex_verification", "Citation Safety Rules"]:
        if token not in bibliography_text:
            errors.append(f"benchmark_reference_bibliography_v1.md missing token {token}")

    claim_texts = {row.get("claim", "") for row in manuscript_claim_rows}
    for claim in [
        "v1.0 中英文分稿是 manuscript outline artifacts 不是完整论文",
        "v1.0 候选方法分类表记录代码路线但不是安装证明",
        "v1.0 参考数据集来源表是 no-download 数据源计划",
        "v1.0 测试设计只定义 generation 与 ranking/rescoring 协议",
        "v1.0 参考文献计划包含待校验外部条目",
        "v1.1 补充资料综合是 source discovery 和 framing 不是 primary-source verified evidence",
        "短肽 docking score 不足以单独支持稳定结合或方法优劣结论",
        "环肽和非天然肽补充资料支持 topology-aware evaluation 但不支持 target-set 晋升",
        "flow matching 补充资料是方法范式背景不是源码可运行性证据",
        "v1.1 method landscape patch candidates 不是 include scorecard",
        "v1.3 grant-style mock review 是模拟评审和更新计划不是资助决定或执行证据",
        "v1.3 行动项表支持 v0.10 preflight planning 但不支持本地安装复现或代码无问题",
        "v0.15 外部预检和 Batch A 只支持 minimal smoke-test observed readiness evidence",
        "v0.16 adapter/parser hardening 是接口计划层不是新增运行证据",
        "v0.16 Batch B target review queue 不是 frozen target set",
        "v0.17 Batch B pilot gate 不是 frozen target set 或正式运行结果",
        "v0.18 adapter replay fixtures 是 parser evidence 不是 Benchmark results",
        "v0.19 方法安装与示例 smoke 是 external readiness evidence 不是 Benchmark results",
        "v0.20 方法解阻 smoke 是 external readiness evidence 不是 Benchmark results",
        "v0.21 adapter smoke 与 parser 输出是 external readiness evidence 不是 Benchmark results",
        "v0.22 multi-case fixture pilot 是标准化计划层不是 Benchmark results",
    ]:
        if claim not in claim_texts:
            errors.append(f"benchmark_manuscript_claim_evidence_map.csv missing claim boundary: {claim}")

    method_files = sorted((ROOT / "kb/wiki/methods").glob("*.md"))
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

    bibtex = (ROOT / "kb/references/references.bib").read_text(encoding="utf-8")
    bib_entries = len(re.findall(r"@\w+\{", bibtex))
    if bib_entries == 0:
        errors.append("references.bib has no BibTeX entries")

    link_count = check_markdown_links(errors)
    tracked_file_count = check_tracked_large_or_forbidden_files(errors)

    literature_cards = [path for path in (ROOT / "kb/wiki/literature").glob("*.md") if path.name != "_index.md"]
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
            "homepage_method_source_rows": homepage_method_source_count,
            "environment_rows": len(environment_rows),
            "expert_review_rows": len(expert_review_rows),
            "dataset_readiness_rows": len(dataset_readiness_rows),
            "target_candidate_rows": len(target_candidate_rows),
            "target_candidate_v05_rows": len(target_candidate_v05_rows),
            "source_pin_rows": len(source_pin_rows),
            "source_pin_v05_rows": len(source_pin_v05_rows),
            "link_availability_rows": len(link_availability_rows),
            "data_access_rows": len(data_access_rows),
            "ars_review_action_rows": len(ars_action_rows),
            "dataset_watchlist_v06_rows": len(dataset_watchlist_rows),
            "example_run_rows": len(example_run_rows),
            "example_job_manifest_v011_rows": len(example_job_manifest_rows),
            "download_manifest_rows": len(download_manifest_rows),
            "dataset_schema_review_v07_rows": len(dataset_schema_review_rows),
            "dataset_schema_review_v08_rows": len(dataset_schema_review_v08_rows),
            "download_manifest_v08_rows": len(download_manifest_v08_rows),
            "preflight_download_v010_rows": len(preflight_download_rows),
            "source_freshness_v011_rows": len(source_freshness_rows),
            "source_clone_v012_rows": len(source_clone_rows),
            "docker_image_inventory_v013_rows": len(docker_image_inventory_rows),
            "method_environment_assignment_v013_rows": len(method_environment_assignment_rows),
            "method_paper_case_v014_rows": len(method_paper_case_v014_rows),
            "target_academic_search_v014_rows": len(target_academic_search_v014_rows),
            "run_preflight_v015_rows": len(run_preflight_v015_rows),
            "batch_a_smoke_test_v015_rows": len(batch_a_smoke_test_v015_rows),
            "adapter_parser_hardening_v016_rows": len(adapter_parser_hardening_v016_rows),
            "batch_b_target_review_v016_rows": len(batch_b_target_review_v016_rows),
            "batch_b_pilot_target_gate_v017_rows": len(batch_b_pilot_target_gate_v017_rows),
            "batch_b_pilot_method_scope_v017_rows": len(batch_b_pilot_method_scope_v017_rows),
            "batch_b_pilot_job_manifest_v017_rows": len(batch_b_pilot_job_manifest_v017_rows),
            "adapter_replay_fixture_v018_rows": len(adapter_replay_fixture_v018_rows),
            "batch_a_replay_method_output_v018_rows": len(batch_a_replay_method_output_v018_rows),
            "batch_a_replay_candidate_v018_rows": len(batch_a_replay_candidate_v018_rows),
            "batch_a_replay_run_v018_rows": len(batch_a_replay_run_v018_rows),
            "method_source_doc_v019_rows": len(method_source_doc_v019_rows),
            "method_install_smoke_manifest_v019_rows": len(method_install_smoke_manifest_v019_rows),
            "method_smoke_test_v019_rows": len(method_smoke_test_v019_rows),
            "method_unblock_manifest_v020_rows": len(method_unblock_manifest_v020_rows),
            "method_unblock_smoke_v020_rows": len(method_unblock_smoke_v020_rows),
            "adapter_smoke_manifest_v021_rows": len(adapter_smoke_manifest_v021_rows),
            "adapter_smoke_results_v021_rows": len(adapter_smoke_results_v021_rows),
            "blocker_asset_manifest_v021_rows": len(blocker_asset_manifest_v021_rows),
            "adapter_method_output_v021_rows": len(adapter_method_output_v021_rows),
            "adapter_candidate_output_v021_rows": len(adapter_candidate_output_v021_rows),
            "adapter_run_rows_v021_rows": len(adapter_run_rows_v021_rows),
            "dflow_bounded_candidate_v026_rows": len(dflow_bounded_candidate_v026_rows),
            "bindcraft_classification_v026_rows": len(bindcraft_classification_v026_rows),
            "bindcraft_accepted_final_v028_rows": len(bindcraft_accepted_final_v028_rows),
            "colabdesign_bounded_method_v029_rows": len(colabdesign_bounded_method_v029_rows),
            "colabdesign_bounded_candidate_v029_rows": len(colabdesign_bounded_candidate_v029_rows),
            "bindcraft_accepted_candidate_v029_rows": len(bindcraft_accepted_candidate_v029_rows),
            "method_example_fixture_v022_rows": len(method_example_fixture_v022_rows),
            "multi_case_fixture_target_v022_rows": len(multi_case_fixture_target_v022_rows),
            "multi_case_fixture_control_v022_rows": len(multi_case_fixture_control_v022_rows),
            "multi_case_fixture_job_v022_rows": len(multi_case_fixture_job_v022_rows),
            "priority_gate_review_v022_rows": len(priority_gate_review_v022_rows),
            "notebook_cli_smoke_v023_rows": len(notebook_cli_smoke_v023_rows),
            "dflow_project_install_v023_rows": len(dflow_project_install_v023_rows),
            "external_dry_run_package_v023_rows": len(external_dry_run_package_v023_rows),
            "priority_gate_review_v023_rows": len(priority_gate_review_v023_rows),
            "dflow_input_contract_fixture_v024_rows": len(dflow_input_contract_fixture_v024_rows),
            "dflow_full_pepmerge_download_v025_rows": len(dflow_full_pepmerge_download_v025_rows),
            "dflow_colab_bindcraft_v026_rows": len(dflow_colab_bindcraft_v026_rows),
            "colabdesign_dexdesign_gate_v027_rows": len(colabdesign_dexdesign_gate_v027_rows),
            "external_asset_rescue_v028_rows": len(external_asset_rescue_v028_rows),
            "bounded_generation_parser_v029_rows": len(bounded_generation_parser_v029_rows),
            "pilot_benchmark_target_v030_rows": len(pilot_benchmark_target_v030_rows),
            "pilot_benchmark_control_v030_rows": len(pilot_benchmark_control_v030_rows),
            "pilot_benchmark_job_v030_rows": len(pilot_benchmark_job_v030_rows),
            "pilot_execution_matrix_v030_rows": len(pilot_execution_matrix_v030_rows),
            "wet_lab_candidate_panel_v030_rows": len(wet_lab_candidate_panel_v030_rows),
            "pilot_execution_results_v031_rows": len(pilot_execution_results_v031_rows),
            "pilot_method_output_v031_rows": len(pilot_method_output_v031_rows),
            "pilot_candidate_output_v031_rows": len(pilot_candidate_output_v031_rows),
            "pilot_run_v031_rows": len(pilot_run_v031_rows),
            "supervisor_skills_installation_v032_files": 1,
            "pilot_execution_results_v033_rows": len(pilot_execution_results_v033_rows),
            "pilot_method_output_v033_rows": len(pilot_method_output_v033_rows),
            "pilot_candidate_output_v033_rows": len(pilot_candidate_output_v033_rows),
            "pilot_run_v033_rows": len(pilot_run_v033_rows),
            "pilot_job_v034_rows": v034_counts["jobs"],
            "pilot_execution_results_v034_rows": v034_counts["execution_rows"],
            "pilot_method_output_v034_rows": v034_counts["method_rows"],
            "pilot_candidate_output_v034_rows": v034_counts["candidate_rows"],
            "pilot_candidate_qc_v034_rows": v034_counts["qc_rows"],
            "pilot_run_v034_rows": v034_counts["run_rows"],
            "pilot_runtime_provenance_v034_records": v034_counts[
                "runtime_provenance_records"
            ],
            "pilot_failure_diagnostics_v034_records": v034_counts[
                "failure_diagnostic_records"
            ],
            "pilot_primary_supported_v034_rows": v034_counts["primary_supported"],
            "pilot_extension_supported_v034_rows": v034_counts["extension_supported"],
            "method_readiness_v08_rows": len(method_readiness_v08_rows),
            "method_preflight_v010_rows": len(method_preflight_rows),
            "adapter_preflight_v011_rows": len(adapter_preflight_rows),
            "method_output_manifest_v011_rows": len(method_output_manifest_rows),
            "candidate_output_v011_rows": len(candidate_output_rows),
            "method_landscape_v09_rows": len(method_landscape_rows),
            "bilingual_sync_rows": len(manuscript_sync_rows),
            "method_classification_v1_rows": len(method_classification_rows),
            "reference_dataset_sources_v1_rows": len(reference_dataset_source_rows),
            "manuscript_todo_v1_rows": len(manuscript_todo_rows),
            "manuscript_claim_rows": len(manuscript_claim_rows),
            "supplementary_material_rows": len(supplementary_material_rows),
            "scoring_rationale_rows": len(scoring_rationale_rows),
            "method_landscape_patch_v11_rows": len(method_landscape_patch_rows),
            "grant_review_action_v13_rows": len(grant_review_action_rows),
            "migration_v010_rows": len(migration_rows),
            "smoke_test_readmes": len(
                [path for path in (ROOT / "benchmark/smoke_tests").glob("*/README.md")]
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
    if not args.no_write_report:
        (ROOT / "ops/validation/wiki_validation_report.md").write_text(
            report, encoding="utf-8"
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
