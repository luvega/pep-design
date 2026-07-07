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

REQUIRED_FILES = [
    "AGENTS.md",
    "index.md",
    "ops/log.md",
    "scripts/parse_batch_a_replay_fixtures.py",
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
    for token in [
        "Adapter Replay Fixture Audit v0.18",
        "adapter_replay_fixture_manifest_v0.18.csv",
        "batch_a_replay_candidate_outputs_v0.18.csv",
        "parse_batch_a_replay_fixtures.py",
        "not Benchmark result",
    ]:
        if token not in replay_audit_text:
            errors.append(f"adapter_replay_fixture_audit_v0.18.md missing token {token}")
    for text_name, text_value in [
        ("batch_b_pilot_execution_plan_v0.17.md", pilot_plan_text.lower()),
        ("batch_b_pilot_readiness_audit_v0.17.md", pilot_audit_text.lower()),
        ("adapter_replay_fixture_audit_v0.18.md", replay_audit_text.lower()),
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
