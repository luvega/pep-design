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

REQUIRED_FILES = [
    "AGENTS.md",
    "index.md",
    "ops/log.md",
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
    "ops/plans/updated_plan_v0.6.md",
    "ops/plans/updated_plan_v0.9.md",
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


def check_markdown_links(errors: list[str]) -> int:
    checked = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        rel_path = path.relative_to(ROOT)
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

    current_plan_text = (ROOT / "ops/plans/updated_plan_v0.9.md").read_text(encoding="utf-8")
    for token in ["Current Authoritative Plan Files", "Benchmark Paper Template", "v0.9 Method Landscape Policy", "Next Work Package", "Claim Gate"]:
        if token not in current_plan_text:
            errors.append(f"updated_plan_v0.9.md missing required section {token}")
    for forbidden in ["download_performed=yes", "smoke_test_ready | reached", "target_set_v0.csv 已冻结"]:
        if forbidden in current_plan_text:
            errors.append(f"updated_plan_v0.9.md contains overclaim boundary violation: {forbidden}")

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
    (ROOT / "ops/validation/wiki_validation_report.md").write_text(report, encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
