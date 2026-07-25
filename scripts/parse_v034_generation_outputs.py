#!/usr/bin/env python3
"""Merge latest immutable v0.34 attempts into compact tracked evidence tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import io
import json
import math
import os
import shlex
import stat
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_v034_wave_a_generation import (
    ADAPTER_MODULES,
    CANDIDATE_HEADERS,
    DEFAULT_JOB_MANIFEST,
    DEFAULT_RUN_ROOT,
    METHOD_OUTPUT_HEADERS,
    METHOD_SLUGS,
    _candidate_row,
)
from scripts.v034_adapters.common import (
    _fasta_records,
    _is_ordered_subsequence,
    _source_file_matches,
    chirality_stats,
    evaluate_candidate_qc,
    parse_pdb_chain_sequences,
    validate_output_file,
)


DEFAULT_RESULTS_ROOT = ROOT / "benchmark/results"
DEFAULT_DEPLOYMENT_PATH = (
    ROOT / "benchmark/deployment/pilot_execution_results_v0.34.csv"
)

DEPLOYMENT_HEADERS = (
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
)

RUN_HEADERS = (
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
)

METHOD_SPECIFIC_QC_STATUS_FIELDS = (
    "backbone_to_fasta_handoff_status",
    "mirror_target_atom_identity_status",
    "mirror_target_central_inversion_status",
    "mirror_output_atom_identity_status",
    "mirror_output_central_inversion_status",
)

PASS_STATUSES = {"pass", "pass_with_warning"}

METHOD_PROVENANCE_CONTRACTS = {
    "PepMLM": (
        "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
        "898fca941a9057aebdd1a6164b5ee09a1a71780e",
        "pd-benchmark-methods-gpu:0.21/bench-pepmlm",
    ),
    "DiffPepBuilder": (
        "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
        "diffpepbuilder_v1.pth_external_manifest_v0.20",
        "pd-pyrosetta-methods-gpu:0.20/bench-diffpepbuilder",
    ),
    "PepGLAD": (
        "bad015ca50c312a89482adb5220c3d907f13df5c",
        "codesign.ckpt_external_manifest_v0.21",
        "pd-benchmark-methods-gpu:0.21/bench-pepglad",
    ),
    "D-Flow / PeptideDesign": (
        "3e3e9f501ee16db318e9bf52643513636a07699a",
        "sha256:95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17",
        "host:.venv/dflow-v023",
    ),
    "PepMirror": (
        "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
        "sha256:a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2",
        "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror",
    ),
    "AfCycDesign / ColabDesign cyclic peptide": (
        "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
        "alphafold_model_1_ptm@sha256:5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84",
        "pd-benchmark-methods-gpu:0.21/bench-colabdesign",
    ),
    "RFdiffusion + ProteinMPNN": (
        "RFdiffusion@2d0c003df46b9db41d119321f15403dec3716cd9;"
        "ProteinMPNN@8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
        "RFdiffusion_external_models;proteinmpnn_v_48_020.pt",
        "pd-rfpeptide-gpu:fixed + pd-foundry-gpu:latest",
    ),
}

RF_HOTSPOTS = ["A48", "A50", "A51", "A52", "A62", "A65"]

CANONICAL_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")

EXPECTED_JOB_TOPOLOGY = {
    "PepMLM": (
        "v034_pepmlm_sequence_seed42",
        "v034_pepmlm_sequence_seed43",
    ),
    "DiffPepBuilder": (
        "v034_diffpepbuilder_3eqs_seed42",
        "v034_diffpepbuilder_3eqs_seed43",
    ),
    "PepGLAD": (
        "v034_pepglad_3eqs_seed42",
        "v034_pepglad_3eqs_seed43",
    ),
    "D-Flow / PeptideDesign": (
        "v034_dflow_3eqs_seed42",
        "v034_dflow_3eqs_seed43",
    ),
    "PepMirror": (
        "v034_pepmirror_3eqs_seed42",
        "v034_pepmirror_3eqs_seed43",
    ),
    "AfCycDesign / ColabDesign cyclic peptide": (
        "v034_colabdesign_7zkr_seed42",
        "v034_colabdesign_7zkr_seed43",
    ),
    "RFdiffusion + ProteinMPNN": (
        "v034_rfdiffusion_mpnn_7zkr_seed42",
        "v034_rfdiffusion_mpnn_7zkr_seed43",
    ),
}

EXPECTED_SOURCE_OUTPUT_IDS = {
    "PepMLM": "pepmlm_generated.csv",
    "DiffPepBuilder": "diffpepbuilder_candidate.pdb",
    "PepGLAD": "pepglad_candidate.pdb",
    "D-Flow / PeptideDesign": "dflow_candidate.pdb",
    "PepMirror": "pepmirror_candidate.pdb",
    "AfCycDesign / ColabDesign cyclic peptide": "afcycdesign_candidate.pdb",
    "RFdiffusion + ProteinMPNN": "design.fa:T=0.1",
}

ADAPTER_REPLAY_FILES = {
    "PepMLM": ("raw/pepmlm_generated.csv",),
    "DiffPepBuilder": (
        "raw/diffpepbuilder_candidate.pdb",
        "raw/diffpepbuilder_target_context.pdb",
    ),
    "PepGLAD": (
        "raw/pepglad_candidate.pdb",
        "raw/pepglad_summary.jsonl",
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
        "package_evidence.json",
        "execution_preflight_evidence.json",
        "executed_source_manifest.json",
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

ADAPTER_RUNTIME_PATHS = {
    "PepMLM": "raw/runtime_evidence.json",
    "DiffPepBuilder": "raw/runtime_evidence.json",
    "PepGLAD": "raw/runtime_evidence.json",
    "D-Flow / PeptideDesign": "runtime_evidence.json",
    "PepMirror": "runtime_evidence.json",
    "AfCycDesign / ColabDesign cyclic peptide": "raw/runtime_evidence.json",
    "RFdiffusion + ProteinMPNN": "raw/runtime_evidence.json",
}

RUNTIME_TARGET_CONTEXT_METHODS = frozenset(
    {"DiffPepBuilder", "D-Flow / PeptideDesign"}
)
JOB_TARGET_PDB_METHODS = frozenset(
    {
        "PepGLAD",
        "PepMirror",
        "AfCycDesign / ColabDesign cyclic peptide",
        "RFdiffusion + ProteinMPNN",
    }
)
EXACT_RUNTIME_TARGET_CONTEXTS = {
    "DiffPepBuilder": "TLLYTMKEVLFYLGQYIMTKRLYDEKQQHIVYCSFSVKEHRKIYTMI",
    "D-Flow / PeptideDesign": "TVLLLTMKEVLFYLGQYIMTKRLYDEKQQHIVYCLLFFSVKEHRKIYTMIY",
}

SEMANTIC_RUNTIME_FILE_FIELDS = (
    ("target_context_path", "target_context_sha256"),
    ("mirror_input_path", "mirror_input_sha256"),
    ("mirrored_target_path", "mirrored_target_sha256"),
    ("mirrored_generated_path", "mirrored_generated_sha256"),
    ("mirror_output_path", "mirror_output_sha256"),
    ("rf_backbone_path", "rf_backbone_sha256"),
    ("rf_trb_path", "rf_trb_sha256"),
    ("mpnn_fasta_path", "mpnn_fasta_sha256"),
)

RUNTIME_PROVENANCE_PAYLOAD_FIELDS = frozenset(
    {"schema_version", "evidence_boundary", "records"}
)
RUNTIME_PROVENANCE_RECORD_FIELDS = frozenset(
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

NON_PEPGLAD_RUNTIME_EVIDENCE_FIELDS = {
    "PepMLM": frozenset(
        {
            "conda_environment",
            "container_image",
            "effective_seed",
            "model_id",
            "model_revision",
            "model_weights_sha256",
            "requested_seed",
            "sampling_strategy",
            "seed_control_status",
            "source_commit",
            "source_entrypoint_sha256",
            "top_k",
        }
    ),
    "DiffPepBuilder": frozenset(
        {
            "conda_environment",
            "container_image",
            "effective_seed",
            "filtered_receptor_sha256",
            "model_asset_sha256",
            "requested_seed",
            "seed_control_status",
            "source_candidate_path",
            "source_commit",
            "source_entrypoint_sha256",
            "target_context_chain",
            "target_context_mode",
            "target_context_path",
            "target_context_sha256",
        }
    ),
    "D-Flow / PeptideDesign": frozenset(
        {
            "candidate_path",
            "candidate_sha256",
            "checkpoint_path",
            "checkpoint_resolved_path",
            "checkpoint_sha256",
            "containerized",
            "effective_seed",
            "execution_environment_declared",
            "execution_environment_type",
            "host_environment_path",
            "method",
            "python_base_prefix",
            "python_executable_path",
            "python_executable_realpath",
            "python_executable_sha256",
            "python_invocation_path",
            "python_prefix",
            "python_version",
            "requested_seed",
            "seed_control_status",
            "seed_patch_path",
            "seed_patch_sha256",
            "source_checkout_path",
            "source_commit",
            "source_content_manifest_path",
            "source_content_manifest_sha256",
            "source_copy_mode",
            "source_entrypoint_patched_sha256",
            "source_entrypoint_path",
            "source_entrypoint_prepatch_sha256",
            "source_git_tracked_paths_clean",
            "source_tracked_file_count",
            "target_context_chain",
            "target_context_mode",
            "target_context_path",
            "target_context_sha256",
            "x_mirror_applied",
        }
    ),
    "PepMirror": frozenset(
        {
            "checkpoint_container_binding_verified",
            "checkpoint_container_path",
            "checkpoint_mount_mode",
            "checkpoint_path",
            "checkpoint_pin_verified",
            "checkpoint_revision",
            "checkpoint_sha256",
            "checkpoint_verified_pre_run",
            "compose_config_command",
            "compose_config_output_sha256",
            "compose_file_path",
            "compose_file_sha256",
            "compose_file_verified_pre_run",
            "compose_image_tag",
            "compose_profile",
            "compose_service",
            "compose_service_verified",
            "effective_seed",
            "executed_source_manifest_path",
            "executed_source_manifest_sha256",
            "executed_source_manifest_verified_pre_run",
            "execution_environment_id",
            "execution_environment_verified",
            "execution_preflight_evidence_path",
            "execution_preflight_evidence_sha256",
            "generate_py_post_path",
            "generate_py_post_sha256",
            "generate_py_pre_path",
            "generate_py_pre_sha256",
            "image_id_observed_at_prepare",
            "image_id_observed_pre_run",
            "image_identity_stable_pre_run",
            "image_inspect_command",
            "image_inspect_execution_command",
            "image_inspect_execution_output_sha256",
            "image_inspect_execution_stage",
            "image_inspect_output_sha256",
            "image_inspect_stage",
            "image_repo_tags_observed_at_prepare",
            "method",
            "mirror_commands_in_pinned_container",
            "mirror_input_path",
            "mirror_input_sha256",
            "mirror_output_path",
            "mirror_output_sha256",
            "mirror_pdb_py_post_path",
            "mirror_pdb_py_post_sha256",
            "mirror_pdb_py_pre_path",
            "mirror_pdb_py_pre_sha256",
            "mirror_roundtrip_applied",
            "mirror_runtime_conda_environment",
            "mirror_runtime_scope",
            "mirrored_generated_path",
            "mirrored_generated_sha256",
            "mirrored_target_path",
            "mirrored_target_sha256",
            "package_evidence_path",
            "package_evidence_sha256",
            "provenance_capture_stage",
            "requested_seed",
            "seed_control_status",
            "seed_patch_path",
            "seed_patch_sha256",
            "source_commit_command",
            "source_commit_expected",
            "source_commit_observed",
            "source_commit_verified",
            "source_git_checkout_clean",
            "source_git_paths",
            "source_git_paths_clean",
            "source_root",
            "source_status_command",
            "source_tracked_file_count",
            "target_input_verified_pre_run",
            "target_pdb_path",
            "target_pdb_sha256",
            "target_preflight_verified",
        }
    ),
    "AfCycDesign / ColabDesign cyclic peptide": frozenset(
        {
            "alphafold_model_name",
            "alphafold_params_sha256",
            "candidate_path",
            "candidate_sha256",
            "container_image",
            "container_image_id",
            "cyclic_offset_applied",
            "cyclic_offset_type",
            "effective_seed",
            "requested_seed",
            "seed_control_status",
            "source_commit",
            "source_notebook_sha256",
            "terminal_offset",
        }
    ),
    "RFdiffusion + ProteinMPNN": frozenset(
        {
            "effective_seed",
            "mpnn_checkpoint_sha256",
            "mpnn_container_image",
            "mpnn_container_image_id",
            "mpnn_designed_chain",
            "mpnn_fasta_path",
            "mpnn_fasta_sha256",
            "mpnn_fixed_chains",
            "mpnn_record_type",
            "mpnn_seed",
            "mpnn_selected_record_id",
            "mpnn_source_commit",
            "mpnn_source_entrypoint_sha256",
            "requested_seed",
            "rf_backbone_path",
            "rf_backbone_sha256",
            "rf_checkpoint_sha256",
            "rf_container_image",
            "rf_container_image_id",
            "rf_contig",
            "rf_cyclic",
            "rf_design_startnum",
            "rf_deterministic",
            "rf_hotspots",
            "rf_source_commit",
            "rf_source_entrypoint_sha256",
            "rf_target_conditioned",
            "rf_trb_path",
            "rf_trb_semantic_extract",
            "rf_trb_semantic_parser",
            "rf_trb_semantic_sha256",
            "rf_trb_sha256",
            "seed_control_status",
            "sequence_representation",
            "sequence_threaded_onto_backbone",
            "structure_representation",
        }
    ),
}

NON_PEPGLAD_RUNTIME_INT_FIELDS = {
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

NON_PEPGLAD_RUNTIME_BOOL_FIELDS = {
    "D-Flow / PeptideDesign": frozenset(
        {"containerized", "source_git_tracked_paths_clean", "x_mirror_applied"}
    ),
    "PepMirror": frozenset(
        {
            "checkpoint_container_binding_verified",
            "checkpoint_pin_verified",
            "checkpoint_verified_pre_run",
            "compose_file_verified_pre_run",
            "compose_service_verified",
            "executed_source_manifest_verified_pre_run",
            "execution_environment_verified",
            "image_identity_stable_pre_run",
            "mirror_commands_in_pinned_container",
            "mirror_roundtrip_applied",
            "source_commit_verified",
            "source_git_checkout_clean",
            "source_git_paths_clean",
            "target_input_verified_pre_run",
            "target_preflight_verified",
        }
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

NON_PEPGLAD_RUNTIME_LIST_FIELDS = {
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

RF_TRB_SEMANTIC_FIELDS = frozenset(
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

RESULT_REQUIRED_FIELDS = frozenset(
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

QC_REQUIRED_FIELDS = frozenset(
    {
        "job_id",
        "design_id",
        "file_status",
        "file_reason",
        "file_sha256",
        "file_size_bytes",
        "parse_status",
        "chain_status",
        "target_binding_status",
        "length_status",
        "sequence_length",
        "sequence_structure_status",
        "chirality_status",
        "cyclic_status",
        "noncanonical_status",
        "noncanonical_residues",
        "seed_status",
        "method_contract_status",
        "handoff_status",
        "overall_qc_status",
        "status_reason",
    }
)

QC_ALLOWED_FIELDS = QC_REQUIRED_FIELDS | frozenset(
    {
        "chirality_evaluable",
        "chirality_l_count",
        "chirality_d_count",
        "chirality_gly_count",
        "chirality_unknown_count",
        "terminal_cn_distance",
        "backbone_to_fasta_handoff_status",
        "mirror_target_atom_identity_status",
        "mirror_target_central_inversion_status",
        "mirror_target_atom_count",
        "mirror_target_central_inversion_max_residual",
        "mirror_target_central_inversion_tolerance",
        "mirror_output_atom_identity_status",
        "mirror_output_central_inversion_status",
        "mirror_output_atom_count",
        "mirror_output_central_inversion_max_residual",
        "mirror_output_central_inversion_tolerance",
    }
)

DIFFPEPBUILDER_MODEL_ASSETS = {
    "diffpepbuilder_v1.pth": "dbc4283257d27e38a1ce90c9344063b046ab7161745ebed1fd98a4b0439b992a",
    "esm2_t33_650M_UR50D.pt": "ea9d0522b335a8778dea6535a65301f10208dece28cd5865482b0b1fc446168c",
    "esm2_t33_650M_UR50D-contact-regression.pt": (
        "8ffe6edbd4173dc8d45c2cd5cb27d43aad77ec26b4c768200c58ae1f96693575"
    ),
}

RF_RUNTIME_PROVENANCE = {
    "rf_source_entrypoint_sha256": "a22624d7d40d3d207d91e92163441da5a778c867ed6ea85aa546cc9fdbeb2105",
    "rf_checkpoint_sha256": "76e4e260aefee3b582bd76b77ab95d2592e64f00c51bf344968ab9239f3250bc",
    "mpnn_source_entrypoint_sha256": "61f2c519a7f73fa12da9eb90da97b97ec2f8d5f31d42605639c7600cbd321cbe",
    "mpnn_checkpoint_sha256": "c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd",
    "rf_container_image_id": "sha256:95e2a19e4adf4b6e8bcdd1777b609bf717472a91643dc92f0ce6aaffbc5219f1",
    "mpnn_container_image_id": "sha256:23f8612f4537f90078d54a5ac9669df7a6d5f436a48740e5d2884cfe856a5be4",
}

PEPGLAD_RECOVERY_MODE = "instrumented_official_pipeline"
PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256 = (
    "dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26"
)
PEPGLAD_SOURCE_ENTRYPOINT_SHA256 = (
    "af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac"
)
PEPGLAD_OBSERVER_SCRIPT_SHA256 = (
    "a0a98420dd2fd5382479abe77526fb8fc206ffb1e69a8780912fb821dded0c61"
)
PEPGLAD_INSTRUMENTER_SCRIPT_SHA256 = (
    "cd9ec19f6605fd2b067824d4e02971b3a203e827b6398a4ffd1c68c64464311a"
)
PEPGLAD_SEED_WRAPPER_SCRIPT_SHA256 = (
    "6a9b4c9012205d27526e13dbccbd7d11c010eddc3c85acdb2796c2fa6668aaba"
)
PEPGLAD_SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256 = (
    "c3b127e39be1b335ff6046bb2435451acfc1b323839377033bf438ccd4a32954"
)
PEPGLAD_LEGACY_RUNTIME_FIELDS = frozenset(
    {
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "source_candidate_path",
        "container_image",
        "conda_environment",
    }
)
PEPGLAD_INSTRUMENTED_RUNTIME_FIELDS = frozenset(
    {
        "requested_seed",
        "effective_seed",
        "seed_control_status",
        "recovery_mode",
        "source_candidate_path",
        "pre_relax_path",
        "pre_relax_sha256",
        "post_relax_path",
        "post_relax_sha256",
        "official_candidate_stage",
        "pre_relax_role",
        "binder_chain",
        "expected_chirality",
        "pre_relax_binder_chirality",
        "post_relax_binder_chirality",
        "first_observed_chirality_failure_stage",
        "baseline_replay_expected_sha256",
        "baseline_replay_observed_sha256",
        "baseline_replay_status",
        "observer_patch_evidence_path",
        "observer_patch_evidence_sha256",
        "observer_patch_path",
        "observer_patch_sha256",
        "observer_source_path",
        "observer_source_sha256",
        "seed_wrapper_path",
        "seed_wrapper_sha256",
        "instrumented_source_path",
        "source_entrypoint_prepatch_sha256",
        "source_entrypoint_instrumented_sha256",
        "target_input_sha256",
        "target_preflight_verified",
        "source_commit",
        "source_entrypoint_sha256",
        "model_weights_sha256",
        "container_image",
        "conda_environment",
    }
)
PEPGLAD_PATCH_EVIDENCE_FIELDS = frozenset(
    {
        "observer_injection_status",
        "observer_patch_path",
        "observer_patch_sha256",
        "observer_source_path",
        "observer_source_sha256",
        "source_entrypoint_path",
        "source_entrypoint_prepatch_sha256",
        "source_entrypoint_instrumented_sha256",
        "source_copy_mode",
        "target_input_path",
        "target_input_sha256",
        "target_preflight_verified",
    }
)
PEPGLAD_FAILURE_QC_FIELDS = frozenset(
    {
        "job_id",
        "design_id",
        "file_status",
        "file_reason",
        "file_sha256",
        "file_size_bytes",
        "parse_status",
        "chain_status",
        "target_binding_status",
        "length_status",
        "sequence_length",
        "sequence_structure_status",
        "chirality_status",
        "cyclic_status",
        "noncanonical_status",
        "noncanonical_residues",
        "seed_status",
        "method_contract_status",
        "backbone_to_fasta_handoff_status",
        "handoff_status",
        "overall_qc_status",
        "status_reason",
    }
)
PEPGLAD_REPLAY_MISMATCH_REASON = "pepglad_seed42_replay_mismatch"
PEPGLAD_FAILURE_DIAGNOSTIC_BOUNDARY = (
    "failure_diagnostic_only_not_candidate_or_scoring"
)

_NO_SHA256_CHECK = object()


class _CapturedFile:
    def __init__(self, *, path: Path, opened_path: Path, digest: str, size: int) -> None:
        self.path = path
        self.opened_path = opened_path
        self.digest = digest
        self.size = size


class _CaptureStore:
    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="v034-merge-snapshots-")
        self.root = Path(self._temporary.name)
        self._cache: dict[str, _CapturedFile] = {}

    def close(self) -> None:
        self._temporary.cleanup()

    def capture(self, path: Path) -> _CapturedFile | None:
        logical = Path(os.path.abspath(path))
        key = os.fspath(logical)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(logical, flags)
        except OSError:
            return None
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                return None
            opened_link = os.readlink(f"/proc/self/fd/{descriptor}")
            if opened_link.endswith(" (deleted)"):
                return None
            opened_path = Path(opened_link)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
            stable_metadata = (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) == (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            payload = b"".join(chunks)
            if not stable_metadata or len(payload) != before.st_size:
                return None
        finally:
            os.close(descriptor)

        suffix = logical.suffix if logical.suffix else ".bin"
        snapshot_fd, snapshot_name = tempfile.mkstemp(
            prefix="captured-", suffix=suffix, dir=self.root
        )
        snapshot = Path(snapshot_name)
        try:
            with os.fdopen(snapshot_fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            snapshot.unlink(missing_ok=True)
            raise
        captured = _CapturedFile(
            path=snapshot,
            opened_path=opened_path,
            digest=hashlib.sha256(payload).hexdigest(),
            size=len(payload),
        )
        self._cache[key] = captured
        return captured


_ACTIVE_CAPTURE_STORE: _CaptureStore | None = None


def _strict_csv_rows(path: Path) -> list[dict[str, str]] | None:
    try:
        payload = path.read_bytes().decode("utf-8")
        parsed = list(csv.reader(io.StringIO(payload, newline=""), strict=True))
    except (OSError, UnicodeError, csv.Error):
        return None
    if not parsed:
        return None
    headers, *rows = parsed
    if not headers or len(headers) != len(set(headers)):
        return None
    if any(
        not cell
        or "\x00" in cell
        or "\n" in cell
        or "\r" in cell
        for cell in headers
    ):
        return None
    if any(
        len(row) != len(headers)
        or any("\x00" in cell or "\n" in cell or "\r" in cell for cell in row)
        for row in rows
    ):
        return None
    return [dict(zip(headers, row)) for row in rows]


def load_jobs(path: Path = DEFAULT_JOB_MANIFEST) -> list[dict[str, str]]:
    rows = _strict_csv_rows(path)
    if rows is None:
        raise ValueError("v0.34 job manifest must be strict UTF-8 CSV")
    if len(rows) != 14:
        raise ValueError("v0.34 job topology must contain exactly fourteen jobs")
    job_ids = [row.get("job_id", "") for row in rows]
    if any(not job_id for job_id in job_ids) or len(set(job_ids)) != len(job_ids):
        raise ValueError("v0.34 job IDs must be nonempty and unique")
    if set(row.get("method", "") for row in rows) != set(EXPECTED_JOB_TOPOLOGY):
        raise ValueError("v0.34 job topology must contain the exact seven-method set")

    by_method: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_method.setdefault(row["method"], []).append(row)
    for method, (primary_id, extension_id) in EXPECTED_JOB_TOPOLOGY.items():
        method_rows = by_method.get(method, [])
        primary = [row for row in method_rows if row.get("seed_stage") == "primary"]
        extension = [row for row in method_rows if row.get("seed_stage") == "extension"]
        if len(method_rows) != 2 or len(primary) != 1 or len(extension) != 1:
            raise ValueError(
                f"v0.34 {method} job topology must be one primary plus one extension"
            )
        if not all(
            (
                primary[0].get("job_id") == primary_id,
                primary[0].get("random_seed") == "42",
                not primary[0].get("primary_job_id"),
                extension[0].get("job_id") == extension_id,
                extension[0].get("random_seed") == "43",
                extension[0].get("primary_job_id") == primary_id,
            )
        ):
            raise ValueError(f"v0.34 {method} primary/extension topology is invalid")
        pair_variant_fields = {
            "job_id",
            "random_seed",
            "notes",
            "seed_stage",
            "primary_job_id",
        }
        if method == "RFdiffusion + ProteinMPNN":
            pair_variant_fields.add("pilot_target_id")
        if any(
            primary[0].get(field) != extension[0].get(field)
            for field in primary[0]
            if field not in pair_variant_fields
        ):
            raise ValueError(f"v0.34 {method} paired job topology is inconsistent")
    return rows


def _latest_attempt(job_root: Path, run_root: Path) -> Path | None:
    try:
        resolved_root = run_root.resolve(strict=True)
        for ancestor in (job_root.parent, job_root):
            if ancestor.is_symlink() or not ancestor.is_dir():
                return None
            ancestor.resolve(strict=True).relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        return None
    attempts = sorted(
        path
        for path in job_root.glob("attempt_[0-9][0-9][0-9]")
        if path.is_dir()
        and not path.is_symlink()
        and path.resolve().is_relative_to(resolved_root)
    )
    return attempts[-1] if attempts else None


def _one_csv_row(path: Path) -> dict[str, str] | None:
    rows = _strict_csv_rows(path)
    return rows[0] if rows is not None and len(rows) == 1 else None


def _unique_json_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _json_numbers_are_finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_json_numbers_are_finite(item) for item in value)
    if isinstance(value, dict):
        return all(_json_numbers_are_finite(item) for item in value.values())
    return True


def _json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_nonfinite_json_constant,
        )
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) and _json_numbers_are_finite(value) else None


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(type(item) is str for item in value)


def _rf_trb_semantic_schema(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != RF_TRB_SEMANTIC_FIELDS:
        return False
    return all(
        (
            type(value.get("input_pdb")) is str,
            _string_list(value.get("contigs")),
            type(value.get("cyclic")) is bool,
            type(value.get("design_startnum")) is int,
            type(value.get("deterministic")) is bool,
            _string_list(value.get("hotspot_res")),
            type(value.get("num_designs")) is int,
            _string_list(value.get("sampled_mask")),
        )
    )


def _non_pepglad_runtime_schema(
    method: str, evidence: Mapping[str, Any]
) -> bool:
    expected = NON_PEPGLAD_RUNTIME_EVIDENCE_FIELDS.get(method)
    if expected is None or set(evidence) != expected:
        return False
    int_fields = NON_PEPGLAD_RUNTIME_INT_FIELDS.get(method, frozenset())
    bool_fields = NON_PEPGLAD_RUNTIME_BOOL_FIELDS.get(method, frozenset())
    list_fields = NON_PEPGLAD_RUNTIME_LIST_FIELDS.get(method, frozenset())
    dict_fields = (
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
    if any(not _string_list(evidence.get(field)) for field in list_fields):
        return False
    string_fields = expected - int_fields - bool_fields - list_fields - dict_fields
    if any(type(evidence.get(field)) is not str for field in string_fields):
        return False
    if method == "DiffPepBuilder":
        assets = evidence.get("model_asset_sha256")
        if not (
            isinstance(assets, dict)
            and set(assets) == set(DIFFPEPBUILDER_MODEL_ASSETS)
            and all(type(value) is str for value in assets.values())
        ):
            return False
    if method == "RFdiffusion + ProteinMPNN" and not _rf_trb_semantic_schema(
        evidence.get("rf_trb_semantic_extract")
    ):
        return False
    return True


def _runtime_provenance_record_contract(record: Mapping[str, Any]) -> bool:
    return all(
        (
            set(record) == RUNTIME_PROVENANCE_RECORD_FIELDS,
            type(record.get("job_id")) is str,
            type(record.get("method")) is str,
            type(record.get("seed_stage")) is str,
            type(record.get("random_seed")) is int,
            type(record.get("attempt_id")) is str,
            type(record.get("runtime_evidence_path")) is str,
            _is_sha256(record.get("runtime_evidence_sha256")),
            _is_sha256(record.get("evidence_semantic_sha256")),
            isinstance(record.get("evidence"), dict),
        )
    )


def _runtime_provenance_payload_contract(payload: Mapping[str, Any]) -> bool:
    records = payload.get("records")
    return all(
        (
            set(payload) == RUNTIME_PROVENANCE_PAYLOAD_FIELDS,
            payload.get("schema_version") == "v0.34",
            payload.get("evidence_boundary")
            == "bounded_connectivity_only_not_scoring_or_ranking",
            isinstance(records, list),
            all(
                isinstance(record, dict)
                and _runtime_provenance_record_contract(record)
                for record in records or []
            ),
        )
    )


def _headers(preferred: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> list[str]:
    ordered = list(preferred)
    seen = set(ordered)
    extras = sorted({key for row in rows for key in row if key not in seen})
    return ordered + extras


def _csv_payload(
    headers: Iterable[str], rows: Iterable[Mapping[str, Any]]
) -> bytes:
    fieldnames = list(headers)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=fieldnames,
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _read_existing_bytes(path: Path) -> bytes | None:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OSError(f"output path is not a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise OSError(f"output changed while capturing prior bytes: {path}")
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise OSError(f"short read while capturing prior output: {path}")
        return payload
    finally:
        os.close(descriptor)


def _stage_payload(path: Path, payload: bytes) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class _StagedArtifact:
    def __init__(self, *, path: Path, temporary: Path, prior: bytes | None) -> None:
        self.path = path
        self.temporary = temporary
        self.prior = prior


def _publish_bundle(artifacts: Iterable[tuple[Path, bytes]]) -> None:
    staged: list[_StagedArtifact] = []
    published: list[_StagedArtifact] = []
    directories: set[Path] = set()
    try:
        for path, payload in artifacts:
            path.parent.mkdir(parents=True, exist_ok=True)
            directories.add(path.parent)
            prior = _read_existing_bytes(path)
            temporary = _stage_payload(path, payload)
            staged.append(
                _StagedArtifact(
                    path=path,
                    temporary=temporary,
                    prior=prior,
                )
            )
        try:
            for artifact in staged:
                os.replace(artifact.temporary, artifact.path)
                published.append(artifact)
            for directory in directories:
                _fsync_directory(directory)
        except Exception as publish_error:
            rollback_error: Exception | None = None
            for artifact in reversed(published):
                try:
                    if artifact.prior is None:
                        artifact.path.unlink(missing_ok=True)
                    else:
                        rollback = _stage_payload(artifact.path, artifact.prior)
                        try:
                            os.replace(rollback, artifact.path)
                        finally:
                            rollback.unlink(missing_ok=True)
                except Exception as error:
                    rollback_error = rollback_error or error
            for directory in directories:
                try:
                    _fsync_directory(directory)
                except OSError as error:
                    rollback_error = rollback_error or error
            if rollback_error is not None:
                raise RuntimeError("output bundle rollback failed") from rollback_error
            raise publish_error
    finally:
        for artifact in staged:
            artifact.temporary.unlink(missing_ok=True)


def _parsed_candidate(
    job: Mapping[str, str],
    result: Mapping[str, Any],
    candidate: Mapping[str, str] | None,
    qc: Mapping[str, str] | None,
) -> bool:
    if (
        result.get("status") not in {"passed", "qc_failed"}
        or candidate is None
        or qc is None
    ):
        return False
    design_id = str(result.get("design_id", ""))
    return all(
        (
            candidate.get("job_id") == job["job_id"],
            candidate.get("design_id") == design_id,
            candidate.get("parse_status") in {"parsed", "partial"},
            bool(candidate.get("sequence", "")),
            qc.get("job_id") == job["job_id"],
            qc.get("design_id") == design_id,
        )
    )


def _runtime_provenance(
    job: Mapping[str, str], attempt: Path | None
) -> dict[str, Any] | None:
    if attempt is None:
        return None
    present_paths = [
        path
        for path in (
            attempt / "runtime_evidence.json",
            attempt / "raw/runtime_evidence.json",
        )
        if path.exists() or path.is_symlink()
    ]
    if len(present_paths) != 1:
        return None
    path = present_paths[0]
    resolved = _bound_attempt_file(attempt, str(path))
    if resolved is None:
        return None
    evidence = _json_object(resolved)
    if evidence is None:
        return None
    semantic_payload = json.dumps(
        evidence, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return {
        "job_id": job["job_id"],
        "method": job["method"],
        "seed_stage": job["seed_stage"],
        "random_seed": int(job["random_seed"]),
        "attempt_id": attempt.name,
        "runtime_evidence_path": path.relative_to(attempt).as_posix(),
        "runtime_evidence_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
        "evidence_semantic_sha256": hashlib.sha256(semantic_payload).hexdigest(),
        "evidence": evidence,
    }


def _pepglad_failure_summary(path: Path) -> dict[str, Any] | None:
    try:
        payload = path.read_bytes().decode("utf-8")
        lines = payload.splitlines()
        if len(lines) != 1 or not lines[0]:
            return None
        value = json.loads(
            lines[0],
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != {
        "id",
        "rec_chains",
        "pep_chain",
        "pep_seq",
    }:
        return None
    if not all(
        (
            value.get("id") == "3EQS_0",
            value.get("rec_chains") == ["A"],
            value.get("pep_chain") == "B",
            isinstance(value.get("pep_seq"), str),
            len(value.get("pep_seq", "")) == 11,
            value.get("pep_seq", "").isascii(),
            value.get("pep_seq", "").isalpha(),
            value.get("pep_seq", "").isupper(),
        )
    ):
        return None
    return value


def _pepglad_failure_execution_contract(
    job: Mapping[str, str],
    attempt: Path,
    result: Mapping[str, Any],
    manifest: Mapping[str, str],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    if (
        set(result) != RESULT_REQUIRED_FIELDS
        or set(manifest) != set(METHOD_OUTPUT_HEADERS)
        or set(candidate) != set(CANDIDATE_HEADERS)
        or set(qc) != PEPGLAD_FAILURE_QC_FIELDS
    ):
        return False
    raw_root = _bound_attempt_directory(attempt, manifest.get("raw_output_root"))
    stdout_log = _bound_attempt_file(attempt, manifest.get("stdout_log"))
    stderr_log = _bound_attempt_file(attempt, manifest.get("stderr_log"))
    result_attempt = _bound_attempt_directory(attempt, result.get("attempt_dir"))
    try:
        command_parts = shlex.split(manifest.get("command", ""))
        expected_attempt = attempt.resolve(strict=True)
        expected_raw = (attempt / "raw").resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    command_file = (
        _bound_attempt_file(attempt, command_parts[1])
        if len(command_parts) == 2 and command_parts[0] == "bash"
        else None
    )
    expected_stdout = _bound_attempt_file(attempt, str(attempt / "stdout.log"))
    expected_stderr = _bound_attempt_file(attempt, str(attempt / "stderr.log"))
    expected_command = _bound_attempt_file(attempt, str(attempt / "command.sh"))
    manifest_runtime = _positive_finite_float(manifest.get("runtime_seconds"))
    result_runtime = _positive_finite_float(result.get("runtime_seconds"))
    manifest_created_at = _timezone_aware_timestamp(manifest.get("created_at"))
    result_created_at = _timezone_aware_timestamp(result.get("created_at"))
    design_id = f"{job['job_id']}_candidate_1"
    expected_qc_reason = (
        "file_status;parse_status;target_binding_status;length_status;"
        "chirality_status;overall_qc_status"
    )
    return all(
        (
            job.get("job_id") == "v034_pepglad_3eqs_seed42",
            job.get("method") == "PepGLAD",
            job.get("seed_stage") == "primary",
            job.get("random_seed") == "42",
            not job.get("primary_job_id"),
            attempt.name == "attempt_003",
            result.get("job_id") == manifest.get("job_id") == job["job_id"],
            result.get("method") == manifest.get("method") == "PepGLAD",
            result.get("design_id")
            == candidate.get("design_id")
            == qc.get("design_id")
            == design_id,
            manifest.get("run_record_id") == f"{job['job_id']}_attempt_003",
            manifest.get("task_id") == job.get("task_id"),
            manifest.get("execution_stage") == "primary",
            manifest.get("source_commit")
            == METHOD_PROVENANCE_CONTRACTS["PepGLAD"][0],
            manifest.get("model_revision")
            == METHOD_PROVENANCE_CONTRACTS["PepGLAD"][1],
            manifest.get("environment_id")
            == METHOD_PROVENANCE_CONTRACTS["PepGLAD"][2],
            result.get("status") == manifest.get("status") == "parse_failed",
            result.get("parser_status")
            == manifest.get("parser_status")
            == candidate.get("parse_status")
            == "failed",
            result.get("overall_qc_status")
            == manifest.get("overall_qc_status")
            == qc.get("overall_qc_status")
            == "fail",
            result.get("status_reason")
            == manifest.get("status_reason")
            == candidate.get("status_reason")
            == PEPGLAD_REPLAY_MISMATCH_REASON,
            _is_exact_int(result.get("exit_code"), 0),
            _parse_int(manifest.get("exit_code")) == 0,
            manifest_runtime is not None,
            result_runtime is not None,
            manifest_runtime == result_runtime,
            manifest_created_at is not None,
            result_created_at is not None,
            manifest_created_at == result_created_at,
            result_attempt == expected_attempt,
            raw_root == expected_raw,
            stdout_log == expected_stdout,
            stderr_log == expected_stderr,
            command_file == expected_command,
            candidate.get("job_id") == qc.get("job_id") == job["job_id"],
            candidate.get("method") == "PepGLAD",
            candidate.get("target_id") == job.get("target_id"),
            candidate.get("binder_id") == f"{job['job_id']}_binder_1",
            candidate.get("generation_rank") == "1",
            candidate.get("binder_chain") == "B",
            candidate.get("peptide_type") == "linear",
            candidate.get("chirality") == "L",
            candidate.get("cyclic") == "no",
            not candidate.get("source_output_id"),
            not candidate.get("sequence"),
            not candidate.get("structure_path"),
            not candidate.get("source_output_path"),
            qc.get("file_status") == "fail",
            qc.get("file_reason") == "missing_output_file",
            not qc.get("file_sha256"),
            qc.get("file_size_bytes") == "0",
            qc.get("parse_status") == "fail",
            qc.get("chain_status") == "not_applicable",
            qc.get("target_binding_status") == "fail",
            qc.get("length_status") == "fail",
            qc.get("sequence_length") == "0",
            qc.get("sequence_structure_status") == "not_applicable",
            qc.get("chirality_status") == "fail",
            qc.get("cyclic_status") == "not_applicable",
            qc.get("noncanonical_status") == "pass",
            not qc.get("noncanonical_residues"),
            qc.get("seed_status") == "pass",
            qc.get("method_contract_status") == "pass",
            qc.get("backbone_to_fasta_handoff_status") == "not_applicable",
            qc.get("handoff_status") == "not_applicable",
            qc.get("status_reason") == expected_qc_reason,
        )
    )


def _pepglad_failure_diagnostic(
    job: Mapping[str, str],
    attempt: Path | None,
    result: Mapping[str, Any],
    manifest: Mapping[str, str] | None,
    candidate: Mapping[str, str] | None,
    qc: Mapping[str, str] | None,
    runtime_provenance: Mapping[str, Any] | None,
    *,
    merge_status: str,
    candidate_tracked: bool,
    runtime_provenance_tracked: bool,
    seed43_status: str,
) -> dict[str, Any] | None:
    if not all(
        (
            attempt is not None,
            manifest is not None,
            candidate is not None,
            qc is not None,
            runtime_provenance is not None,
            merge_status == "evidence_incomplete",
            not candidate_tracked,
            not runtime_provenance_tracked,
            seed43_status == "not_run",
        )
    ):
        return None
    assert attempt is not None
    assert manifest is not None
    assert candidate is not None
    assert qc is not None
    assert runtime_provenance is not None
    if not _pepglad_failure_execution_contract(
        job, attempt, result, manifest, candidate, qc
    ):
        return None
    evidence = runtime_provenance.get("evidence")
    if (
        not isinstance(evidence, dict)
        or set(evidence) != PEPGLAD_INSTRUMENTED_RUNTIME_FIELDS
        or runtime_provenance.get("runtime_evidence_path")
        != "raw/runtime_evidence.json"
    ):
        return None

    source_candidate = _bound_relative_attempt_file(
        attempt, evidence.get("source_candidate_path")
    )
    pre_relax = _bound_relative_attempt_file(
        attempt, evidence.get("pre_relax_path"), evidence.get("pre_relax_sha256")
    )
    post_relax = _bound_relative_attempt_file(
        attempt, evidence.get("post_relax_path"), evidence.get("post_relax_sha256")
    )
    patch_evidence_path = _bound_relative_attempt_file(
        attempt,
        evidence.get("observer_patch_evidence_path"),
        evidence.get("observer_patch_evidence_sha256"),
    )
    observer_patch = _bound_relative_attempt_file(
        attempt,
        evidence.get("observer_patch_path"),
        evidence.get("observer_patch_sha256"),
    )
    observer_source = _bound_relative_attempt_file(
        attempt,
        evidence.get("observer_source_path"),
        evidence.get("observer_source_sha256"),
    )
    seed_wrapper = _bound_relative_attempt_file(
        attempt,
        evidence.get("seed_wrapper_path"),
        evidence.get("seed_wrapper_sha256"),
    )
    instrumented_source = _bound_relative_attempt_file(
        attempt,
        evidence.get("instrumented_source_path"),
        evidence.get("source_entrypoint_instrumented_sha256"),
    )
    runtime_evidence_file = _bound_relative_attempt_file(
        attempt,
        "raw/runtime_evidence.json",
        runtime_provenance.get("runtime_evidence_sha256"),
    )
    summary_path = _bound_relative_attempt_file(
        attempt, "raw/pepglad_summary.jsonl"
    )
    if any(
        path is None
        for path in (
            source_candidate,
            pre_relax,
            post_relax,
            patch_evidence_path,
            observer_patch,
            observer_source,
            seed_wrapper,
            instrumented_source,
            runtime_evidence_file,
            summary_path,
        )
    ):
        return None
    assert source_candidate is not None
    assert pre_relax is not None
    assert post_relax is not None
    assert patch_evidence_path is not None
    assert observer_patch is not None
    assert observer_source is not None
    assert seed_wrapper is not None
    assert instrumented_source is not None
    assert runtime_evidence_file is not None
    assert summary_path is not None

    patch_evidence = _json_object(patch_evidence_path)
    summary = _pepglad_failure_summary(summary_path)
    target = _hash_bound_job_target(job)
    if (
        patch_evidence is None
        or set(patch_evidence) != PEPGLAD_PATCH_EVIDENCE_FIELDS
        or summary is None
        or target is None
    ):
        return None
    try:
        runtime_payload = json.dumps(
            evidence, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        source_payload = source_candidate.read_bytes()
        pre_payload = pre_relax.read_bytes()
        post_payload = post_relax.read_bytes()
        summary_payload = summary_path.read_bytes()
        pre_stats = {"chain": "B", **chirality_stats(pre_relax, "B")}
        post_stats = {"chain": "B", **chirality_stats(post_relax, "B")}
        pre_sequence = parse_pdb_chain_sequences(pre_relax).get("B", "")
        post_sequence = parse_pdb_chain_sequences(post_relax).get("B", "")
        source_sequence = parse_pdb_chain_sequences(source_candidate).get("B", "")
        observer_patch_digest = hashlib.sha256(observer_patch.read_bytes()).hexdigest()
        observer_source_digest = hashlib.sha256(observer_source.read_bytes()).hexdigest()
        seed_wrapper_digest = hashlib.sha256(seed_wrapper.read_bytes()).hexdigest()
        instrumented_source_digest = hashlib.sha256(
            instrumented_source.read_bytes()
        ).hexdigest()
        patch_evidence_digest = hashlib.sha256(
            patch_evidence_path.read_bytes()
        ).hexdigest()
    except (OSError, UnicodeError, TypeError, ValueError):
        return None

    pre_expected = {
        "chain": "B",
        "status": "pass",
        "evaluable": 11,
        "l_count": 6,
        "d_count": 5,
        "gly_count": 0,
        "unknown_count": 0,
    }
    post_expected = {
        "chain": "B",
        "status": "pass",
        "evaluable": 11,
        "l_count": 4,
        "d_count": 7,
        "gly_count": 0,
        "unknown_count": 0,
    }
    post_digest = hashlib.sha256(post_payload).hexdigest()
    runtime_digest = hashlib.sha256(runtime_evidence_file.read_bytes()).hexdigest()
    runtime_semantic_digest = hashlib.sha256(runtime_payload).hexdigest()
    if not all(
        (
            _pepglad_identity_contract(evidence),
            evidence.get("requested_seed") == 42,
            evidence.get("effective_seed") == 42,
            evidence.get("seed_control_status") == "honored",
            evidence.get("recovery_mode") == PEPGLAD_RECOVERY_MODE,
            evidence.get("source_candidate_path") == "work/codesign/3EQS_0.pdb",
            evidence.get("pre_relax_path") == "raw/pepglad_pre_relax.pdb",
            evidence.get("post_relax_path") == "raw/pepglad_candidate.pdb",
            evidence.get("official_candidate_stage") == "post_openmm_relaxation",
            evidence.get("pre_relax_role") == "diagnostic_evidence_only",
            evidence.get("binder_chain") == "B",
            evidence.get("expected_chirality") == "L",
            pre_stats == evidence.get("pre_relax_binder_chirality") == pre_expected,
            post_stats == evidence.get("post_relax_binder_chirality") == post_expected,
            evidence.get("first_observed_chirality_failure_stage")
            == "pre_openmm_snapshot",
            hashlib.sha256(pre_payload).hexdigest()
            == evidence.get("pre_relax_sha256"),
            post_digest
            == evidence.get("post_relax_sha256")
            == evidence.get("baseline_replay_observed_sha256"),
            source_payload == post_payload,
            pre_sequence
            == post_sequence
            == source_sequence
            == summary.get("pep_seq"),
            evidence.get("baseline_replay_expected_sha256")
            == PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
            post_digest != PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
            evidence.get("baseline_replay_status") == "mismatch",
            evidence.get("target_input_sha256") == job.get("target_pdb_sha256"),
            evidence.get("target_preflight_verified") is True,
            runtime_digest == runtime_provenance.get("runtime_evidence_sha256"),
            runtime_semantic_digest
            == runtime_provenance.get("evidence_semantic_sha256"),
            patch_evidence.get("observer_injection_status") == "applied",
            patch_evidence.get("source_copy_mode") == "attempt_local_copy",
            patch_evidence.get("target_input_path") == "/data/input/3EQS.pdb",
            patch_evidence.get("target_input_sha256")
            == evidence.get("target_input_sha256"),
            patch_evidence.get("target_preflight_verified") is True,
            patch_evidence.get("observer_patch_path")
            == evidence.get("observer_patch_path")
            == "pepglad_instrument_source.py",
            observer_patch_digest
            == patch_evidence.get("observer_patch_sha256")
            == evidence.get("observer_patch_sha256")
            == PEPGLAD_INSTRUMENTER_SCRIPT_SHA256,
            patch_evidence.get("observer_source_path")
            == evidence.get("observer_source_path")
            == "pepglad_observer.py",
            observer_source_digest
            == patch_evidence.get("observer_source_sha256")
            == evidence.get("observer_source_sha256")
            == PEPGLAD_OBSERVER_SCRIPT_SHA256,
            evidence.get("seed_wrapper_path") == "pepglad_seeded_entry.py",
            seed_wrapper_digest
            == evidence.get("seed_wrapper_sha256")
            == PEPGLAD_SEED_WRAPPER_SCRIPT_SHA256,
            patch_evidence.get("source_entrypoint_path")
            == evidence.get("instrumented_source_path")
            == "work/api/run.py",
            patch_evidence.get("source_entrypoint_prepatch_sha256")
            == evidence.get("source_entrypoint_prepatch_sha256")
            == PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            instrumented_source_digest
            == patch_evidence.get("source_entrypoint_instrumented_sha256")
            == evidence.get("source_entrypoint_instrumented_sha256")
            == PEPGLAD_SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256,
            patch_evidence_digest
            == evidence.get("observer_patch_evidence_sha256"),
        )
    ):
        return None

    return {
        "job_id": job["job_id"],
        "method": job["method"],
        "seed_stage": job["seed_stage"],
        "random_seed": 42,
        "attempt_id": attempt.name,
        "attempt_dir": result["attempt_dir"],
        "candidate_eligible": False,
        "seed43_status": "not_run",
        "process": {"exit_code": 0},
        "parser": {
            "status": "failed",
            "status_reason": PEPGLAD_REPLAY_MISMATCH_REASON,
        },
        "merge": {"status": "evidence_incomplete"},
        "runtime_evidence": {
            "path": "raw/runtime_evidence.json",
            "sha256": runtime_digest,
            "semantic_sha256": runtime_semantic_digest,
        },
        "summary": {
            "path": "raw/pepglad_summary.jsonl",
            "sha256": hashlib.sha256(summary_payload).hexdigest(),
            "sequence": summary["pep_seq"],
        },
        "pre_openmm": {
            "path": evidence["pre_relax_path"],
            "sha256": evidence["pre_relax_sha256"],
            "chirality": {
                "chain": pre_stats["chain"],
                "calculation_status": pre_stats["status"],
                "evaluable": pre_stats["evaluable"],
                "l_count": pre_stats["l_count"],
                "d_count": pre_stats["d_count"],
                "gly_count": pre_stats["gly_count"],
                "unknown_count": pre_stats["unknown_count"],
            },
        },
        "post_openmm": {
            "path": evidence["post_relax_path"],
            "sha256": evidence["post_relax_sha256"],
            "chirality": {
                "chain": post_stats["chain"],
                "calculation_status": post_stats["status"],
                "evaluable": post_stats["evaluable"],
                "l_count": post_stats["l_count"],
                "d_count": post_stats["d_count"],
                "gly_count": post_stats["gly_count"],
                "unknown_count": post_stats["unknown_count"],
            },
        },
        "baseline": {
            "expected_sha256": PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
            "observed_sha256": post_digest,
            "status": "mismatch",
            "failure_stage": "pre_openmm_snapshot",
        },
        "producer_bindings": {
            "target": {
                "path": patch_evidence["target_input_path"],
                "sha256": evidence["target_input_sha256"],
                "preflight_verified": True,
            },
            "source": {
                "commit": evidence["source_commit"],
                "entrypoint_sha256": evidence["source_entrypoint_sha256"],
            },
            "model": {"weights_sha256": evidence["model_weights_sha256"]},
            "container": {"image": evidence["container_image"]},
            "environment": {
                "conda_environment": evidence["conda_environment"]
            },
            "observer": {
                "path": evidence["observer_source_path"],
                "sha256": observer_source_digest,
            },
            "patch": {
                "evidence_path": evidence["observer_patch_evidence_path"],
                "evidence_sha256": patch_evidence_digest,
                "instrumenter_path": evidence["observer_patch_path"],
                "instrumenter_sha256": observer_patch_digest,
                "injection_status": patch_evidence["observer_injection_status"],
                "source_copy_mode": patch_evidence["source_copy_mode"],
            },
            "wrapper": {
                "path": evidence["seed_wrapper_path"],
                "sha256": seed_wrapper_digest,
            },
            "instrumented_source": {
                "path": evidence["instrumented_source_path"],
                "prepatch_sha256": evidence["source_entrypoint_prepatch_sha256"],
                "sha256": instrumented_source_digest,
            },
        },
    }


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _is_exact_int(value: Any, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _parse_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if str(value).strip() == str(parsed) else None


def _parse_finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def _positive_finite_float(value: Any) -> float | None:
    parsed = _parse_finite_float(value)
    return parsed if parsed is not None and parsed > 0 else None


def _timezone_aware_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _canonical_status_reason(value: Any) -> bool:
    allowed = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
    return (
        isinstance(value, str)
        and bool(value)
        and value.isascii()
        and all(character in allowed for character in value)
    )


def _bound_attempt_file(
    attempt: Path, path_value: Any, expected_sha256: Any = _NO_SHA256_CHECK
) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    raw_path = Path(path_value)
    candidates = (
        [raw_path] if raw_path.is_absolute() else [raw_path, attempt / raw_path]
    )
    for path in candidates:
        try:
            if path.is_symlink():
                continue
            attempt_root = attempt.resolve(strict=True)
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(attempt_root) or not resolved.is_file():
                continue
            store = _ACTIVE_CAPTURE_STORE
            if store is None:
                return None
            captured = store.capture(path)
            if (
                captured is None
                or not captured.opened_path.is_relative_to(attempt_root)
            ):
                continue
            if expected_sha256 is not _NO_SHA256_CHECK:
                if not _is_sha256(expected_sha256):
                    return None
                if captured.digest != expected_sha256:
                    return None
            return captured.path
        except (OSError, RuntimeError, ValueError):
            continue
    return None


def _bound_relative_attempt_file(
    attempt: Path, path_value: Any, expected_sha256: Any = _NO_SHA256_CHECK
) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    relative = Path(path_value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() != path_value
    ):
        return None
    try:
        current = attempt
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                return None
    except OSError:
        return None
    return _bound_attempt_file(attempt, path_value, expected_sha256)


def _bound_attempt_directory(attempt: Path, path_value: Any) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    raw_path = Path(path_value)
    candidates = (
        [raw_path] if raw_path.is_absolute() else [raw_path, attempt / raw_path]
    )
    for path in candidates:
        try:
            if path.is_symlink():
                continue
            attempt_root = attempt.resolve(strict=True)
            resolved = path.resolve(strict=True)
            if resolved.is_relative_to(attempt_root) and resolved.is_dir():
                return resolved
        except (OSError, RuntimeError, ValueError):
            continue
    return None


def _canonical_attempt_input(attempt: Path, filename: str) -> Path | None:
    path = attempt / filename
    try:
        expected = path.resolve(strict=True)
        if expected != attempt.resolve(strict=True) / filename:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return _bound_attempt_file(attempt, str(path))


def _manifest_contract(job: Mapping[str, str], manifest: Mapping[str, str]) -> bool:
    if set(manifest) != set(METHOD_OUTPUT_HEADERS):
        return False
    if any(not str(manifest.get(field, "")).strip() for field in METHOD_OUTPUT_HEADERS):
        return False
    expected = METHOD_PROVENANCE_CONTRACTS.get(job["method"])
    if expected is None:
        return False
    source_commit, model_revision, environment_id = expected
    return all(
        (
            manifest.get("job_id") == job["job_id"],
            manifest.get("method") == job["method"],
            manifest.get("task_id") == job["task_id"],
            manifest.get("source_commit") == source_commit,
            manifest.get("model_revision") == model_revision,
            manifest.get("environment_id") == environment_id,
            manifest.get("parser_status") in {"parsed", "partial"},
            manifest.get("overall_qc_status") in PASS_STATUSES,
            manifest.get("status") == "passed",
            manifest.get("status_reason") == "bounded_connectivity_candidate_qc_passed",
            _timezone_aware_timestamp(manifest.get("created_at")) is not None,
        )
    )


def _execution_evidence_contract(
    job: Mapping[str, str],
    attempt: Path,
    result: Mapping[str, Any],
    manifest: Mapping[str, str],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    if set(result) != RESULT_REQUIRED_FIELDS:
        return False
    raw_root = _bound_attempt_directory(attempt, manifest.get("raw_output_root"))
    stdout_log = _bound_attempt_file(attempt, manifest.get("stdout_log"))
    stderr_log = _bound_attempt_file(attempt, manifest.get("stderr_log"))
    result_attempt = _bound_attempt_directory(attempt, result.get("attempt_dir"))
    try:
        command_parts = shlex.split(manifest.get("command", ""))
    except (TypeError, ValueError):
        command_parts = []
    command_file = (
        _bound_attempt_file(attempt, command_parts[1])
        if len(command_parts) == 2 and command_parts[0] == "bash"
        else None
    )
    manifest_runtime = _positive_finite_float(manifest.get("runtime_seconds"))
    result_runtime = _positive_finite_float(result.get("runtime_seconds"))
    manifest_created_at = _timezone_aware_timestamp(manifest.get("created_at"))
    result_created_at = _timezone_aware_timestamp(result.get("created_at"))
    try:
        expected_attempt = attempt.resolve(strict=True)
        expected_raw = (attempt / "raw").resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return False
    expected_stdout = _bound_attempt_file(attempt, str(attempt / "stdout.log"))
    expected_stderr = _bound_attempt_file(attempt, str(attempt / "stderr.log"))
    expected_command = _bound_attempt_file(attempt, str(attempt / "command.sh"))
    return all(
        (
            manifest.get("run_record_id") == f"{job['job_id']}_{attempt.name}",
            manifest.get("execution_stage") == job["seed_stage"],
            manifest.get("status") == result.get("status") == "passed",
            result.get("status_reason")
            == manifest.get("status_reason")
            == "bounded_connectivity_candidate_qc_passed",
            manifest.get("parser_status")
            == result.get("parser_status")
            == candidate.get("parse_status"),
            manifest.get("overall_qc_status")
            == result.get("overall_qc_status")
            == qc.get("overall_qc_status"),
            result.get("design_id")
            == candidate.get("design_id")
            == qc.get("design_id"),
            result_attempt == expected_attempt,
            raw_root == expected_raw,
            stdout_log == expected_stdout,
            stderr_log == expected_stderr,
            command_file == expected_command,
            manifest_runtime is not None,
            result_runtime is not None,
            manifest_runtime == result_runtime,
            manifest_created_at is not None,
            result_created_at is not None,
            manifest_created_at == result_created_at,
            _parse_int(manifest.get("exit_code")) == 0,
            _is_exact_int(result.get("exit_code"), 0),
        )
    )


def _candidate_path_contract(
    job: Mapping[str, str],
    attempt: Path,
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    method = job["method"]
    if set(candidate) != set(CANDIDATE_HEADERS):
        return False
    if not all(
        (
            candidate.get("job_id") == job["job_id"],
            candidate.get("method") == method,
            candidate.get("target_id") == job["target_id"],
            candidate.get("binder_id") == f"{job['job_id']}_binder_1",
            candidate.get("source_output_id") == EXPECTED_SOURCE_OUTPUT_IDS.get(method),
            candidate.get("generation_rank") == "1",
            candidate.get("binder_chain") == job["expected_binder_chain"],
            candidate.get("peptide_type") == job["peptide_type"],
            candidate.get("chirality") == job["chirality"],
            candidate.get("cyclic") == job["cyclic"],
            candidate.get("parse_status") in {"parsed", "partial"},
            bool(candidate.get("sequence", "")),
            _canonical_status_reason(candidate.get("status_reason")),
            "Bounded connectivity evidence only; not Benchmark result or scoring evidence"
            in candidate.get("notes", ""),
        )
    ):
        return False

    source_output = _bound_attempt_file(attempt, candidate.get("source_output_path"))
    if source_output is None:
        return False
    if method == "PepMLM":
        primary = _bound_attempt_file(
            attempt,
            candidate.get("source_output_path"),
            qc.get("file_sha256"),
        )
        if candidate.get("structure_path") or primary is None:
            return False
    else:
        primary = _bound_attempt_file(
            attempt, candidate.get("structure_path"), qc.get("file_sha256")
        )
        if primary is None:
            return False
        if method != "RFdiffusion + ProteinMPNN" and source_output != primary:
            return False

    sequence = candidate.get("sequence", "")
    sequence_length = _parse_int(qc.get("sequence_length"))
    file_size = _parse_int(qc.get("file_size_bytes"))
    length_min = _parse_int(job.get("length_min"))
    length_max = _parse_int(job.get("length_max"))
    noncanonical = "".join(
        sorted({residue for residue in sequence if residue not in CANONICAL_AA})
    )
    expected_noncanonical_status = "warn" if noncanonical else "pass"
    expected_overall = "pass_with_warning" if noncanonical else "pass"
    expected_qc_reason = (
        "noncanonical_status" if noncanonical else "all_required_checks_passed"
    )
    try:
        artifact_size = primary.stat().st_size
        if method == "PepMLM":
            source_row = _one_csv_row(primary)
            artifact_content_ok = source_row is not None and all(
                (
                    set(source_row)
                    == {"job_id", "generated_binder", "binder_rank", "target_id"},
                    source_row.get("job_id") == job["job_id"],
                    source_row.get("generated_binder") == sequence,
                    source_row.get("binder_rank") == "1",
                    source_row.get("target_id") == job["target_id"],
                )
            )
        else:
            chains = parse_pdb_chain_sequences(primary)
            target_sequence = chains.get(job["expected_target_chain"], "")
            binder_sequence = chains.get(job["expected_binder_chain"], "")
            artifact_content_ok = bool(target_sequence) and (
                len(binder_sequence) == len(sequence)
                if method == "RFdiffusion + ProteinMPNN"
                else binder_sequence == sequence
            )
    except (OSError, UnicodeError, ValueError):
        return False
    if not all(
        (
            sequence.isascii(),
            all("A" <= residue <= "Z" for residue in sequence),
            sequence_length == len(sequence),
            length_min is not None,
            length_max is not None,
            length_min <= len(sequence) <= length_max,
            artifact_size > 0,
            file_size == artifact_size,
            artifact_content_ok,
            qc.get("noncanonical_status") == expected_noncanonical_status,
            qc.get("noncanonical_residues") == noncanonical,
            qc.get("overall_qc_status") == expected_overall,
            qc.get("file_reason") == "validated",
            qc.get("status_reason") == expected_qc_reason,
        )
    ):
        return False
    return True


def _pdb_chain_sequence(path: Path | None, chain: Any) -> str | None:
    if path is None or not isinstance(chain, str) or not chain:
        return None
    try:
        sequence = parse_pdb_chain_sequences(path).get(chain, "")
    except (OSError, UnicodeError, ValueError):
        return None
    return sequence or None


def _hash_bound_job_target(job: Mapping[str, str]) -> Path | None:
    path_value = job.get("target_pdb_path")
    expected_sha256 = job.get("target_pdb_sha256")
    if (
        not isinstance(path_value, str)
        or not path_value
        or not _is_sha256(expected_sha256)
    ):
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    store = _ACTIVE_CAPTURE_STORE
    captured = store.capture(path) if store is not None else None
    if captured is None:
        return None
    matched, matched_path = _source_file_matches(
        str(captured.path), expected_sha256
    )
    if not matched or matched_path is None:
        return None
    try:
        resolved = matched_path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def _job_input_target_chain(job: Mapping[str, str]) -> str | None:
    value = job.get("target_chains")
    if not isinstance(value, str):
        return None
    chain = value.replace(",", ";").split(";", 1)[0].strip()
    return chain or None


def _rewrite_attempt_paths(value: Any, source: Path, destination: Path) -> Any:
    source_text = os.fspath(source)
    destination_text = os.fspath(destination)
    if isinstance(value, str):
        if value == source_text:
            return destination_text
        prefix = source_text + os.sep
        if value.startswith(prefix):
            return destination_text + os.sep + value[len(prefix) :]
        return value
    if isinstance(value, list):
        return [
            _rewrite_attempt_paths(item, source, destination) for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _rewrite_attempt_paths(item, source, destination)
            for key, item in value.items()
        }
    return value


def _copy_captured_relative_file(
    attempt: Path, replay: Path, relative_text: str
) -> Path | None:
    relative = Path(relative_text)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() != relative_text
    ):
        return None
    captured = _bound_relative_attempt_file(attempt, relative_text)
    if captured is None:
        return None
    destination = replay / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(captured.read_bytes())
    return destination


def _logical_attempt_relative_path(root: Path, path_text: str) -> Path | None:
    path = Path(path_text)
    candidates = (path,) if path.is_absolute() else (path, root / path)
    for candidate in candidates:
        try:
            return Path(os.path.abspath(candidate)).relative_to(root)
        except ValueError:
            continue
    return None


def _write_replay_json(path: Path, value: Mapping[str, Any]) -> str:
    payload = (
        json.dumps(
            dict(value),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _prepare_pepmirror_replay(
    attempt: Path,
    replay: Path,
    evidence: Mapping[str, Any],
) -> dict[str, Any] | None:
    source = attempt.resolve(strict=True)
    destination = replay.resolve(strict=True)
    manifest_capture = _bound_relative_attempt_file(
        attempt, "executed_source_manifest.json"
    )
    package_capture = _bound_relative_attempt_file(attempt, "package_evidence.json")
    preflight_capture = _bound_relative_attempt_file(
        attempt, "execution_preflight_evidence.json"
    )
    if any(
        path is None
        for path in (manifest_capture, package_capture, preflight_capture)
    ):
        return None
    assert manifest_capture is not None
    assert package_capture is not None
    assert preflight_capture is not None
    manifest = _json_object(manifest_capture)
    package = _json_object(package_capture)
    preflight = _json_object(preflight_capture)
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if (
        package is None
        or preflight is None
        or not isinstance(files, dict)
        or not all(type(key) is str and _is_sha256(value) for key, value in files.items())
    ):
        return None
    for relative_text in files:
        relative = Path(relative_text)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != relative_text
            or _copy_captured_relative_file(
                attempt, replay, f"work/PepMirror/{relative_text}"
            )
            is None
        ):
            return None

    manifest_path = replay / "executed_source_manifest.json"
    manifest_path.write_bytes(manifest_capture.read_bytes())
    rewritten_package = _rewrite_attempt_paths(package, source, destination)
    rewritten_preflight = _rewrite_attempt_paths(preflight, source, destination)
    if not isinstance(rewritten_package, dict) or not isinstance(
        rewritten_preflight, dict
    ):
        return None
    package_sha256 = _write_replay_json(
        replay / "package_evidence.json", rewritten_package
    )
    preflight_sha256 = _write_replay_json(
        replay / "execution_preflight_evidence.json", rewritten_preflight
    )
    rewritten = _rewrite_attempt_paths(dict(evidence), source, destination)
    if not isinstance(rewritten, dict):
        return None
    rewritten.update(rewritten_package)
    rewritten.update(rewritten_preflight)
    rewritten.update(
        package_evidence_path=str(replay / "package_evidence.json"),
        package_evidence_sha256=package_sha256,
        execution_preflight_evidence_path=str(
            replay / "execution_preflight_evidence.json"
        ),
        execution_preflight_evidence_sha256=preflight_sha256,
    )
    return rewritten


def _stable_adapter_replay_contract(
    job: Mapping[str, str],
    attempt: Path,
    provenance: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    store = _ACTIVE_CAPTURE_STORE
    evidence = provenance.get("evidence")
    if store is None or not isinstance(evidence, dict):
        return False
    module_name = ADAPTER_MODULES.get(job["method"])
    replay_files = ADAPTER_REPLAY_FILES.get(job["method"])
    if module_name is None or replay_files is None:
        return False
    replay = store.root / "adapter-replay" / job["job_id"] / attempt.name
    try:
        replay.mkdir(parents=True, exist_ok=False)
        for relative_text in replay_files:
            if relative_text.endswith(".json") and job["method"] == "PepMirror":
                continue
            if _copy_captured_relative_file(attempt, replay, relative_text) is None:
                return False

        source = attempt.resolve(strict=True)
        destination = replay.resolve(strict=True)
        replay_evidence: dict[str, Any]
        if job["method"] == "PepMirror":
            prepared = _prepare_pepmirror_replay(
                attempt, replay, evidence
            )
            if prepared is None:
                return False
            replay_evidence = prepared
        else:
            rewritten = _rewrite_attempt_paths(
                dict(evidence), source, destination
            )
            if not isinstance(rewritten, dict):
                return False
            replay_evidence = rewritten

        runtime_relative = provenance.get("runtime_evidence_path")
        if (
            not isinstance(runtime_relative, str)
            or runtime_relative not in {
                "runtime_evidence.json",
                "raw/runtime_evidence.json",
            }
        ):
            return False
        adapter_runtime_relative = ADAPTER_RUNTIME_PATHS.get(job["method"])
        if adapter_runtime_relative is None:
            return False
        _write_replay_json(replay / adapter_runtime_relative, replay_evidence)

        adapter = importlib.import_module(module_name)
        pepglad_baseline = None
        if job["method"] == "PepGLAD":
            pepglad_baseline = adapter.SEED42_POST_RELAX_BASELINE_SHA256
            adapter.SEED42_POST_RELAX_BASELINE_SHA256 = (
                PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256
            )
        try:
            replay_value, replay_runtime = adapter.parse(job, replay)
        finally:
            if pepglad_baseline is not None:
                adapter.SEED42_POST_RELAX_BASELINE_SHA256 = pepglad_baseline
        replay_candidate = _candidate_row(job, replay_value)
        if set(replay_candidate) != set(CANDIDATE_HEADERS):
            return False

        path_fields = {"structure_path", "source_output_path"}
        for field in set(CANDIDATE_HEADERS) - path_fields:
            if str(replay_candidate.get(field, "")) != candidate.get(field, ""):
                return False
        for field in path_fields:
            replay_text = str(replay_candidate.get(field, ""))
            candidate_text = candidate.get(field, "")
            if not replay_text or not candidate_text:
                if replay_text != candidate_text:
                    return False
                continue
            replay_relative = Path(os.path.abspath(replay_text)).relative_to(destination)
            candidate_relative = _logical_attempt_relative_path(
                source, candidate_text
            )
            if candidate_relative is None:
                return False
            if replay_relative != candidate_relative:
                return False

        normalized_runtime = _rewrite_attempt_paths(
            replay_runtime, destination, source
        )
        if not isinstance(normalized_runtime, dict):
            return False
        if job["method"] == "PepMirror":
            normalized_runtime["package_evidence_sha256"] = evidence.get(
                "package_evidence_sha256"
            )
            normalized_runtime["execution_preflight_evidence_sha256"] = evidence.get(
                "execution_preflight_evidence_sha256"
            )
        if normalized_runtime != evidence:
            return False

        job_snapshot = dict(job)
        if job.get("target_pdb_path"):
            target = _hash_bound_job_target(job)
            if target is None:
                return False
            job_snapshot["target_pdb_path"] = str(target)
        observed = evaluate_candidate_qc(
            job_snapshot,
            replay_candidate,
            replay_runtime,
            replay / "raw",
        )
        for field, value in observed.items():
            reported = qc.get(field)
            if reported is None and value == "not_applicable":
                continue
            if reported != str(value):
                return False
        return all(
            (
                qc.get("file_sha256") == observed.get("file_sha256"),
                qc.get("file_size_bytes") == str(observed.get("file_size_bytes")),
                qc.get("parse_status") == str(observed.get("parse_status")),
                qc.get("overall_qc_status")
                == str(observed.get("overall_qc_status")),
                qc.get("status_reason") == str(observed.get("status_reason")),
            )
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RuntimeError,
        KeyError,
    ):
        return False


def _target_content_contract(
    job: Mapping[str, str],
    attempt: Path,
    provenance: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    method = job["method"]
    if method == "PepMLM":
        return True
    candidate_path = _bound_attempt_file(
        attempt, candidate.get("structure_path"), qc.get("file_sha256")
    )
    target_chain = job.get("expected_target_chain")
    candidate_target_sequence = _pdb_chain_sequence(candidate_path, target_chain)
    if candidate_target_sequence is None:
        return False

    if method in RUNTIME_TARGET_CONTEXT_METHODS:
        evidence = provenance.get("evidence")
        if not isinstance(evidence, dict):
            return False
        context_chain = evidence.get("target_context_chain")
        context_path = _bound_attempt_file(
            attempt,
            evidence.get("target_context_path"),
            evidence.get("target_context_sha256"),
        )
        trusted_target_sequence = _pdb_chain_sequence(context_path, context_chain)
        job_target_sequence = _pdb_chain_sequence(
            _hash_bound_job_target(job), _job_input_target_chain(job)
        )
        return (
            job.get("target_binding_check_mode")
            == "pocket_subsequence_and_sha256"
            and evidence.get("target_context_mode") == "ordered_subsequence"
            and context_chain == target_chain
            and trusted_target_sequence is not None
            and job_target_sequence is not None
            and trusted_target_sequence == EXACT_RUNTIME_TARGET_CONTEXTS.get(method)
            and candidate_target_sequence == trusted_target_sequence
            and _is_ordered_subsequence(
                trusted_target_sequence, job_target_sequence
            )
        )

    if method in JOB_TARGET_PDB_METHODS:
        trusted_target_sequence = _pdb_chain_sequence(
            _hash_bound_job_target(job), _job_input_target_chain(job)
        )
        return (
            trusted_target_sequence is not None
            and candidate_target_sequence == trusted_target_sequence
        )

    return False


def _semantic_qc_contract(
    job: Mapping[str, str],
    attempt: Path,
    provenance: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    store = _ACTIVE_CAPTURE_STORE
    evidence = provenance.get("evidence")
    if store is None or not isinstance(evidence, dict):
        return False
    candidate_snapshot = dict(candidate)
    for field in ("structure_path", "source_output_path"):
        path_value = candidate.get(field)
        if not path_value:
            continue
        bound = _bound_attempt_file(attempt, path_value)
        if bound is None:
            return False
        candidate_snapshot[field] = str(bound)

    evidence_snapshot = dict(evidence)
    for path_field, digest_field in SEMANTIC_RUNTIME_FILE_FIELDS:
        if not evidence.get(path_field):
            continue
        bound = _bound_attempt_file(
            attempt, evidence.get(path_field), evidence.get(digest_field)
        )
        if bound is None:
            return False
        evidence_snapshot[path_field] = str(bound)

    job_snapshot = dict(job)
    if job.get("target_pdb_path"):
        target = _hash_bound_job_target(job)
        if target is None:
            return False
        job_snapshot["target_pdb_path"] = str(target)

    output_text = candidate_snapshot.get("structure_path") or candidate_snapshot.get(
        "source_output_path"
    )
    if not output_text:
        return False
    try:
        file_result = validate_output_file(Path(output_text), store.root)
        observed = evaluate_candidate_qc(
            job_snapshot, candidate_snapshot, evidence_snapshot, store.root
        )
    except (OSError, UnicodeError, ValueError, TypeError, RuntimeError):
        return False
    if not all(
        (
            str(file_result.get("status", "")) == qc.get("file_status"),
            str(file_result.get("reason", "")) == qc.get("file_reason"),
            str(file_result.get("sha256", "")) == qc.get("file_sha256"),
            str(file_result.get("size_bytes", "")) == qc.get("file_size_bytes"),
        )
    ):
        return False
    for field, value in observed.items():
        reported = qc.get(field)
        if reported is None and value == "not_applicable":
            continue
        if reported != str(value):
            return False
    return True


def _chirality_numeric_contract(
    job: Mapping[str, str], qc: Mapping[str, str], sequence: str
) -> bool:
    counts = {
        key: _parse_int(qc.get(f"chirality_{key}"))
        for key in (
            "evaluable",
            "l_count",
            "d_count",
            "gly_count",
            "unknown_count",
        )
    }
    if any(value is None or value < 0 for value in counts.values()):
        return False
    evaluable = counts["evaluable"]
    l_count = counts["l_count"]
    d_count = counts["d_count"]
    gly_count = counts["gly_count"]
    unknown_count = counts["unknown_count"]
    expected_count = l_count if job["chirality"] == "L" else d_count
    opposite_count = d_count if job["chirality"] == "L" else l_count
    return all(
        (
            evaluable > 0,
            l_count + d_count == evaluable,
            expected_count == evaluable,
            opposite_count == 0,
            gly_count == sequence.count("G"),
            unknown_count == 0,
            evaluable + gly_count + unknown_count == len(sequence),
        )
    )


def _mirror_numeric_qc_contract(qc: Mapping[str, str]) -> bool:
    for prefix in ("mirror_target", "mirror_output"):
        atom_count = _parse_int(qc.get(f"{prefix}_atom_count"))
        residual = _parse_finite_float(
            qc.get(f"{prefix}_central_inversion_max_residual")
        )
        tolerance = _positive_finite_float(
            qc.get(f"{prefix}_central_inversion_tolerance")
        )
        if (
            atom_count is None
            or atom_count <= 0
            or residual is None
            or residual < 0
            or tolerance is None
            or tolerance != 0.002
            or residual > tolerance
        ):
            return False
    return True


def _qc_contract(
    job: Mapping[str, str], qc: Mapping[str, str], candidate: Mapping[str, str]
) -> bool:
    if not QC_REQUIRED_FIELDS.issubset(qc) or not set(qc).issubset(QC_ALLOWED_FIELDS):
        return False
    method = job["method"]
    required_pass = (
        "file_status",
        "parse_status",
        "length_status",
        "seed_status",
        "method_contract_status",
    )
    if any(qc.get(field) != "pass" for field in required_pass):
        return False
    if qc.get("overall_qc_status") not in PASS_STATUSES:
        return False

    expected_chain = "not_applicable" if method == "PepMLM" else "pass"
    expected_sequence_structure = (
        "not_applicable"
        if method in {"PepMLM", "RFdiffusion + ProteinMPNN"}
        else "pass"
    )
    expected_target = (
        "not_applicable"
        if job.get("target_binding_check_mode") == "not_applicable"
        else "pass"
    )
    expected_chirality = (
        "pass" if job.get("chirality_check_mode") == "geometry" else "not_applicable"
    )
    expected_cyclic = (
        "not_applicable" if job.get("cyclic_check_mode") == "not_applicable" else "pass"
    )
    expected_handoff = (
        "pass" if method == "RFdiffusion + ProteinMPNN" else "not_applicable"
    )
    if not all(
        (
            qc.get("chain_status") == expected_chain,
            qc.get("sequence_structure_status") == expected_sequence_structure,
            qc.get("target_binding_status") == expected_target,
            qc.get("chirality_status") == expected_chirality,
            qc.get("cyclic_status") == expected_cyclic,
            qc.get("handoff_status") == expected_handoff,
        )
    ):
        return False

    if job.get(
        "chirality_check_mode"
    ) == "geometry" and not _chirality_numeric_contract(
        job, qc, candidate.get("sequence", "")
    ):
        return False
    if job.get("cyclic_check_mode") != "not_applicable":
        terminal_distance = _parse_finite_float(qc.get("terminal_cn_distance"))
        if terminal_distance is None or not 0.9 <= terminal_distance <= 2.0:
            return False
    if (
        method == "RFdiffusion + ProteinMPNN"
        and qc.get("backbone_to_fasta_handoff_status") != "pass"
    ):
        return False
    if method == "PepMirror":
        if not all(
            qc.get(field) == "pass"
            for field in (
                "mirror_target_atom_identity_status",
                "mirror_target_central_inversion_status",
                "mirror_output_atom_identity_status",
                "mirror_output_central_inversion_status",
            )
        ):
            return False
        if not _mirror_numeric_qc_contract(qc):
            return False
    return True


def _common_runtime_contract(
    job: Mapping[str, str], evidence: Mapping[str, Any]
) -> bool:
    seed = int(job["random_seed"])
    return all(
        (
            _is_exact_int(evidence.get("requested_seed"), seed),
            _is_exact_int(evidence.get("effective_seed"), seed),
            evidence.get("seed_control_status") == "honored",
        )
    )


def _pepmlm_runtime_contract(evidence: Mapping[str, Any]) -> bool:
    return all(
        (
            evidence.get("source_commit") == "3169c4920f8c383948e0a5d3a7c8f87e5e7d2436",
            evidence.get("source_entrypoint_sha256")
            == "2c1844028c459e8e96d756da795b620b4ccaa65b98dd62c6f904100f0dc1e49b",
            evidence.get("model_id") == "TianlaiChen/PepMLM-650M",
            evidence.get("model_revision")
            == "898fca941a9057aebdd1a6164b5ee09a1a71780e",
            evidence.get("model_weights_sha256")
            == "8a3225bca1f9acd9f701ca2e46597c12bab92320e32b68f380ddf3b6d3b20770",
            evidence.get("container_image") == "pd-benchmark-methods-gpu:0.21",
            evidence.get("conda_environment") == "bench-pepmlm",
            evidence.get("sampling_strategy") == "top_k_categorical",
            _is_exact_int(evidence.get("top_k"), 3),
        )
    )


def _diffpepbuilder_runtime_contract(
    job: Mapping[str, str], attempt: Path, evidence: Mapping[str, Any]
) -> bool:
    target = _bound_attempt_file(
        attempt,
        evidence.get("target_context_path"),
        evidence.get("target_context_sha256"),
    )
    return all(
        (
            evidence.get("source_commit") == "c19eb4f0cd2419d3bcc116184c0868243b6c4169",
            evidence.get("source_entrypoint_sha256")
            == "872868f48e3cf66f0ce159ada589ca2126a3b2ba98470ab3bbcb9ffc4481f7c6",
            evidence.get("model_asset_sha256") == DIFFPEPBUILDER_MODEL_ASSETS,
            _is_sha256(evidence.get("filtered_receptor_sha256")),
            isinstance(evidence.get("source_candidate_path"), str),
            bool(evidence.get("source_candidate_path")),
            evidence.get("container_image") == "pd-pyrosetta-methods-gpu:0.20",
            evidence.get("conda_environment") == "bench-diffpepbuilder",
            evidence.get("target_context_chain") == job["expected_target_chain"],
            evidence.get("target_context_mode") == "ordered_subsequence",
            target is not None,
        )
    )


def _pepglad_identity_contract(evidence: Mapping[str, Any]) -> bool:
    return all(
        (
            evidence.get("source_commit") == "bad015ca50c312a89482adb5220c3d907f13df5c",
            evidence.get("source_entrypoint_sha256")
            == PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            evidence.get("model_weights_sha256")
            == "5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe",
            evidence.get("container_image") == "pd-benchmark-methods-gpu:0.21",
            evidence.get("conda_environment") == "bench-pepglad",
        )
    )


def _pepglad_chirality_passes(
    stats: Mapping[str, Any], expected_chirality: str
) -> bool:
    expected_key = "l_count" if expected_chirality == "L" else "d_count"
    return all(
        (
            stats.get("status") == "pass",
            _is_positive_int(stats.get("evaluable")),
            stats.get(expected_key) == stats.get("evaluable"),
        )
    )


def _pepglad_instrumented_runtime_contract(
    job: Mapping[str, str],
    attempt: Path,
    evidence: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    if set(evidence) != PEPGLAD_INSTRUMENTED_RUNTIME_FIELDS:
        return False
    source_candidate = _bound_relative_attempt_file(
        attempt, evidence.get("source_candidate_path")
    )
    pre_relax = _bound_relative_attempt_file(
        attempt, evidence.get("pre_relax_path"), evidence.get("pre_relax_sha256")
    )
    post_relax = _bound_relative_attempt_file(
        attempt, evidence.get("post_relax_path"), evidence.get("post_relax_sha256")
    )
    patch_evidence_path = _bound_relative_attempt_file(
        attempt,
        evidence.get("observer_patch_evidence_path"),
        evidence.get("observer_patch_evidence_sha256"),
    )
    observer_patch = _bound_relative_attempt_file(
        attempt,
        evidence.get("observer_patch_path"),
        evidence.get("observer_patch_sha256"),
    )
    observer_source = _bound_relative_attempt_file(
        attempt,
        evidence.get("observer_source_path"),
        evidence.get("observer_source_sha256"),
    )
    seed_wrapper = _bound_relative_attempt_file(
        attempt,
        evidence.get("seed_wrapper_path"),
        evidence.get("seed_wrapper_sha256"),
    )
    instrumented_source = _bound_relative_attempt_file(
        attempt,
        evidence.get("instrumented_source_path"),
        evidence.get("source_entrypoint_instrumented_sha256"),
    )
    candidate_structure = _bound_attempt_file(
        attempt, candidate.get("structure_path"), qc.get("file_sha256")
    )
    candidate_source = _bound_attempt_file(
        attempt, candidate.get("source_output_path"), qc.get("file_sha256")
    )
    bound_files = (
        source_candidate,
        pre_relax,
        post_relax,
        patch_evidence_path,
        observer_patch,
        observer_source,
        seed_wrapper,
        instrumented_source,
        candidate_structure,
        candidate_source,
    )
    if any(path is None for path in bound_files):
        return False
    assert source_candidate is not None
    assert pre_relax is not None
    assert post_relax is not None
    assert patch_evidence_path is not None
    assert observer_patch is not None
    assert observer_source is not None
    assert seed_wrapper is not None
    assert instrumented_source is not None
    assert candidate_structure is not None
    assert candidate_source is not None

    patch_evidence = _json_object(patch_evidence_path)
    if (
        patch_evidence is None
        or set(patch_evidence) != PEPGLAD_PATCH_EVIDENCE_FIELDS
    ):
        return False
    target = _hash_bound_job_target(job)
    if target is None:
        return False

    binder_chain = evidence.get("binder_chain")
    expected_chirality = evidence.get("expected_chirality")
    if binder_chain != "B" or expected_chirality != "L":
        return False
    try:
        pre_stats = {"chain": binder_chain, **chirality_stats(pre_relax, binder_chain)}
        post_stats = {
            "chain": binder_chain,
            **chirality_stats(post_relax, binder_chain),
        }
        source_candidate_payload = source_candidate.read_bytes()
        post_payload = post_relax.read_bytes()
        observer_patch_digest = hashlib.sha256(
            observer_patch.read_bytes()
        ).hexdigest()
        observer_source_digest = hashlib.sha256(
            observer_source.read_bytes()
        ).hexdigest()
        seed_wrapper_digest = hashlib.sha256(seed_wrapper.read_bytes()).hexdigest()
        instrumented_source_digest = hashlib.sha256(
            instrumented_source.read_bytes()
        ).hexdigest()
    except (OSError, UnicodeError, ValueError, TypeError):
        return False
    if not _pepglad_chirality_passes(pre_stats, expected_chirality):
        expected_failure_stage = "pre_openmm_snapshot"
    elif not _pepglad_chirality_passes(post_stats, expected_chirality):
        expected_failure_stage = "post_openmm_relaxation"
    else:
        expected_failure_stage = "none_observed"

    post_digest = hashlib.sha256(post_payload).hexdigest()
    source_candidate_digest = hashlib.sha256(source_candidate_payload).hexdigest()
    post_qc_counts_match = all(
        qc.get(f"chirality_{field}") == str(post_stats[field])
        for field in (
            "evaluable",
            "l_count",
            "d_count",
            "gly_count",
            "unknown_count",
        )
    )
    seed = int(job["random_seed"])
    if seed == 42:
        baseline_contract = all(
            (
                evidence.get("baseline_replay_expected_sha256")
                == PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
                post_digest == PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
                evidence.get("baseline_replay_observed_sha256") == post_digest,
                evidence.get("baseline_replay_status") == "match",
            )
        )
    else:
        baseline_contract = all(
            (
                seed == 43,
                evidence.get("baseline_replay_expected_sha256") == "",
                evidence.get("baseline_replay_observed_sha256") == post_digest,
                evidence.get("baseline_replay_status") == "not_applicable",
            )
        )

    return all(
        (
            _pepglad_identity_contract(evidence),
            evidence.get("recovery_mode") == PEPGLAD_RECOVERY_MODE,
            evidence.get("official_candidate_stage") == "post_openmm_relaxation",
            evidence.get("pre_relax_role") == "diagnostic_evidence_only",
            job.get("expected_binder_chain") == binder_chain,
            job.get("chirality") == expected_chirality,
            evidence.get("pre_relax_binder_chirality") == pre_stats,
            evidence.get("post_relax_binder_chirality") == post_stats,
            evidence.get("first_observed_chirality_failure_stage")
            == expected_failure_stage,
            post_qc_counts_match,
            post_relax == candidate_structure == candidate_source,
            pre_relax != candidate_structure,
            evidence.get("post_relax_sha256") == qc.get("file_sha256") == post_digest,
            source_candidate_payload == post_payload,
            source_candidate_digest == post_digest,
            baseline_contract,
            evidence.get("target_input_sha256") == job.get("target_pdb_sha256"),
            evidence.get("target_preflight_verified") is True,
            evidence.get("source_entrypoint_prepatch_sha256")
            == PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            patch_evidence.get("observer_injection_status") == "applied",
            patch_evidence.get("source_copy_mode") == "attempt_local_copy",
            observer_patch_digest
            == evidence.get("observer_patch_sha256")
            == patch_evidence.get("observer_patch_sha256")
            == PEPGLAD_INSTRUMENTER_SCRIPT_SHA256,
            observer_source_digest
            == evidence.get("observer_source_sha256")
            == patch_evidence.get("observer_source_sha256")
            == PEPGLAD_OBSERVER_SCRIPT_SHA256,
            seed_wrapper_digest
            == evidence.get("seed_wrapper_sha256")
            == PEPGLAD_SEED_WRAPPER_SCRIPT_SHA256,
            instrumented_source_digest
            == evidence.get("source_entrypoint_instrumented_sha256")
            == patch_evidence.get("source_entrypoint_instrumented_sha256")
            == PEPGLAD_SOURCE_ENTRYPOINT_INSTRUMENTED_SHA256,
            patch_evidence.get("observer_patch_path")
            == evidence.get("observer_patch_path"),
            patch_evidence.get("observer_patch_sha256")
            == evidence.get("observer_patch_sha256"),
            patch_evidence.get("observer_source_path")
            == evidence.get("observer_source_path"),
            patch_evidence.get("observer_source_sha256")
            == evidence.get("observer_source_sha256"),
            patch_evidence.get("source_entrypoint_path")
            == evidence.get("instrumented_source_path"),
            patch_evidence.get("source_entrypoint_prepatch_sha256")
            == evidence.get("source_entrypoint_prepatch_sha256")
            == PEPGLAD_SOURCE_ENTRYPOINT_SHA256,
            patch_evidence.get("source_entrypoint_instrumented_sha256")
            == evidence.get("source_entrypoint_instrumented_sha256"),
            patch_evidence.get("target_input_path") == "/data/input/3EQS.pdb",
            patch_evidence.get("target_input_sha256")
            == evidence.get("target_input_sha256")
            == job.get("target_pdb_sha256"),
            patch_evidence.get("target_preflight_verified") is True,
        )
    )


def _pepglad_runtime_contract(
    job: Mapping[str, str],
    attempt: Path,
    evidence: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    recovery_mode = evidence.get("recovery_mode")
    if recovery_mode is not None:
        if recovery_mode != PEPGLAD_RECOVERY_MODE:
            return False
        return _pepglad_instrumented_runtime_contract(
            job, attempt, evidence, candidate, qc
        )
    candidate_structure = _bound_attempt_file(
        attempt,
        candidate.get("structure_path"),
        PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
    )
    candidate_source = _bound_attempt_file(
        attempt,
        candidate.get("source_output_path"),
        PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
    )
    return all(
        (
            job.get("job_id") == "v034_pepglad_3eqs_seed42",
            job.get("seed_stage") == "primary",
            job.get("random_seed") == "42",
            not job.get("primary_job_id"),
            set(evidence) == PEPGLAD_LEGACY_RUNTIME_FIELDS,
            _pepglad_identity_contract(evidence),
            evidence.get("source_candidate_path")
            == "/data/attempt/work/codesign/3EQS_0.pdb",
            qc.get("file_sha256") == PEPGLAD_SEED42_POST_RELAX_BASELINE_SHA256,
            candidate_structure is not None,
            candidate_source is not None,
        )
    )


def _dflow_source_manifest_contract(
    path: Path | None, evidence: Mapping[str, Any]
) -> bool:
    if path is None:
        return False
    manifest = _json_object(path)
    if manifest is None or not isinstance(manifest.get("files"), list):
        return False
    files = manifest["files"]
    if len(files) != evidence.get("source_tracked_file_count"):
        return False
    if not all(
        isinstance(entry, dict)
        and isinstance(entry.get("path"), str)
        and bool(entry.get("path"))
        and _is_sha256(entry.get("sha256"))
        and _is_nonnegative_int(entry.get("size_bytes"))
        for entry in files
    ):
        return False
    entrypoints = [
        entry
        for entry in files
        if str(entry.get("path", "")).endswith("dflow/experiments/inference_pep.py")
    ]
    return all(
        (
            manifest.get("schema_version") == "v034_dflow_source_content_v1",
            manifest.get("source_commit") == evidence.get("source_commit"),
            manifest.get("source_copy_mode") == evidence.get("source_copy_mode"),
            manifest.get("source_entrypoint_prepatch_sha256")
            == evidence.get("source_entrypoint_prepatch_sha256"),
            manifest.get("source_entrypoint_patched_sha256")
            == evidence.get("source_entrypoint_patched_sha256"),
            len(entrypoints) == 1,
            (
                entrypoints[0].get("sha256")
                == evidence.get("source_entrypoint_patched_sha256")
                if entrypoints
                else False
            ),
        )
    )


def _dflow_runtime_contract(
    job: Mapping[str, str],
    attempt: Path,
    evidence: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    source_manifest = _bound_attempt_file(
        attempt,
        evidence.get("source_content_manifest_path"),
        evidence.get("source_content_manifest_sha256"),
    )
    entrypoint = _bound_attempt_file(
        attempt,
        evidence.get("source_entrypoint_path"),
        evidence.get("source_entrypoint_patched_sha256"),
    )
    runtime_candidate = _bound_attempt_file(
        attempt, evidence.get("candidate_path"), evidence.get("candidate_sha256")
    )
    candidate_path = _bound_attempt_file(
        attempt, candidate.get("structure_path"), qc.get("file_sha256")
    )
    target = _bound_attempt_file(
        attempt,
        evidence.get("target_context_path"),
        evidence.get("target_context_sha256"),
    )
    return all(
        (
            evidence.get("method") == job["method"],
            evidence.get("source_commit") == "3e3e9f501ee16db318e9bf52643513636a07699a",
            evidence.get("source_copy_mode") == "git_tracked_files_only",
            evidence.get("source_git_tracked_paths_clean") is True,
            _is_positive_int(evidence.get("source_tracked_file_count")),
            _dflow_source_manifest_contract(source_manifest, evidence),
            entrypoint is not None,
            evidence.get("source_entrypoint_prepatch_sha256")
            == "6be8b50b876cc94c8a212165d7327bd46c0e906d2c85fc6c2b03a66ff9e2cd9d",
            evidence.get("checkpoint_sha256")
            == "95020b5a25ff66df78a563c127c4f6958f8e10a6c472729634cdd8322e9cef17",
            isinstance(evidence.get("checkpoint_path"), str),
            bool(evidence.get("checkpoint_path")),
            isinstance(evidence.get("checkpoint_resolved_path"), str),
            bool(evidence.get("checkpoint_resolved_path")),
            evidence.get("execution_environment_declared") == "host:.venv/dflow-v023",
            evidence.get("execution_environment_type")
            == "host_local_python_environment",
            runtime_candidate is not None,
            runtime_candidate == candidate_path,
            evidence.get("candidate_sha256") == qc.get("file_sha256"),
            target is not None,
            evidence.get("target_context_chain") == job["expected_target_chain"],
            evidence.get("target_context_mode") == "ordered_subsequence",
            evidence.get("x_mirror_applied") is True,
        )
    )


def _pepmirror_runtime_contract(
    job: Mapping[str, str],
    attempt: Path,
    evidence: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    bound_paths = {
        name: _bound_attempt_file(
            attempt, evidence.get(f"{name}_path"), evidence.get(f"{name}_sha256")
        )
        for name in (
            "package_evidence",
            "execution_preflight_evidence",
            "mirror_input",
            "mirrored_target",
            "mirrored_generated",
            "mirror_output",
        )
    }
    candidate_path = _bound_attempt_file(
        attempt, candidate.get("structure_path"), qc.get("file_sha256")
    )
    return all(
        (
            evidence.get("method") == job["method"],
            evidence.get("source_commit_expected")
            == "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            evidence.get("source_commit_observed")
            == "41cb31f3974d91e1a2ca88f0db060405833e4a9c",
            evidence.get("source_commit_verified") is True,
            evidence.get("source_git_checkout_clean") is True,
            evidence.get("source_git_paths_clean") is True,
            evidence.get("generate_py_pre_sha256")
            == "452ba18b29d9647785a2a4160fcaacd97e3769af4b58e5c532fb6b3394881459",
            evidence.get("generate_py_post_sha256")
            == "32cb77ec34c9f10b2223c0bb19ef09e7fad3c7d9c2c0798a5ff9e72a699e5ecb",
            evidence.get("mirror_pdb_py_pre_sha256")
            == "d8438835c3c26fbf3a1971c577be037e3bfe7114338d0c6e1fb32a2a4a11a233",
            evidence.get("mirror_pdb_py_post_sha256")
            == "d8438835c3c26fbf3a1971c577be037e3bfe7114338d0c6e1fb32a2a4a11a233",
            evidence.get("checkpoint_sha256")
            == "a86aac3ea26509282f89ee99a9d42028fc4dd3ad404617b3754a1dea4c1867f2",
            evidence.get("checkpoint_pin_verified") is True,
            evidence.get("checkpoint_container_binding_verified") is True,
            bound_paths["package_evidence"] is not None,
            bound_paths["execution_preflight_evidence"] is not None,
            evidence.get("execution_environment_id")
            == "pd-pyrosetta-methods-gpu:0.21/bench-pepmirror",
            evidence.get("execution_environment_verified") is True,
            evidence.get("image_identity_stable_pre_run") is True,
            bound_paths["mirror_input"] is not None,
            evidence.get("mirror_input_sha256") == job["target_pdb_sha256"],
            bound_paths["mirrored_target"] is not None,
            bound_paths["mirrored_generated"] is not None,
            bound_paths["mirror_output"] is not None,
            bound_paths["mirror_output"] == candidate_path,
            evidence.get("mirror_output_sha256") == qc.get("file_sha256"),
            evidence.get("mirror_roundtrip_applied") is True,
            evidence.get("target_pdb_sha256") == job["target_pdb_sha256"],
            evidence.get("target_preflight_verified") is True,
            evidence.get("mirror_runtime_scope") == "pinned_compose_conda_environment",
            evidence.get("mirror_runtime_conda_environment") == "bench-pepmirror",
            evidence.get("mirror_commands_in_pinned_container") is True,
        )
    )


def _colabdesign_runtime_contract(
    attempt: Path,
    evidence: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    runtime_candidate = _bound_attempt_file(
        attempt, evidence.get("candidate_path"), evidence.get("candidate_sha256")
    )
    candidate_path = _bound_attempt_file(
        attempt, candidate.get("structure_path"), qc.get("file_sha256")
    )
    return all(
        (
            evidence.get("source_commit") == "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
            evidence.get("source_notebook_sha256")
            == "ca3bd3cc14daa95e1529fd2d5c1ca18263d12341a75d2967715ec23720b129ed",
            evidence.get("alphafold_model_name") == "model_1_ptm",
            evidence.get("alphafold_params_sha256")
            == "5e564f79af5bcd54ccef6e2a6bb0ff01015d01650ebc41d4575e35f0de9ecc84",
            evidence.get("container_image") == "pd-benchmark-methods-gpu:0.21",
            evidence.get("container_image_id")
            == "sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2",
            runtime_candidate is not None,
            runtime_candidate == candidate_path,
            evidence.get("candidate_sha256") == qc.get("file_sha256"),
            evidence.get("cyclic_offset_applied") is True,
            _is_exact_int(evidence.get("cyclic_offset_type"), 2),
            _is_exact_int(evidence.get("terminal_offset"), 1),
        )
    )


def _rf_runtime_contract(
    job: Mapping[str, str],
    attempt: Path,
    evidence: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    backbone = _bound_attempt_file(
        attempt, evidence.get("rf_backbone_path"), evidence.get("rf_backbone_sha256")
    )
    trb = _bound_attempt_file(
        attempt, evidence.get("rf_trb_path"), evidence.get("rf_trb_sha256")
    )
    fasta = _bound_attempt_file(
        attempt, evidence.get("mpnn_fasta_path"), evidence.get("mpnn_fasta_sha256")
    )
    candidate_backbone = _bound_attempt_file(
        attempt, candidate.get("structure_path"), qc.get("file_sha256")
    )
    candidate_fasta = _bound_attempt_file(attempt, candidate.get("source_output_path"))
    fasta_sequence_ok = False
    if fasta is not None and fasta.stat().st_size > 0:
        try:
            selected_id = str(evidence.get("mpnn_selected_record_id", ""))
            matching_sequences = [
                sequence
                for header, sequence in _fasta_records(fasta)
                if header.split(",", 1)[0].split()[0] == selected_id
            ]
            fasta_sequence_ok = matching_sequences == [candidate.get("sequence", "")]
        except (OSError, UnicodeError, ValueError):
            fasta_sequence_ok = False
    semantics = evidence.get("rf_trb_semantic_extract")
    semantic_sha = None
    if isinstance(semantics, dict):
        semantic_sha = hashlib.sha256(
            json.dumps(
                semantics,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    seed = int(job["random_seed"])
    return all(
        (
            evidence.get("rf_source_commit")
            == "2d0c003df46b9db41d119321f15403dec3716cd9",
            evidence.get("mpnn_source_commit")
            == "8907e6671bfbfc92303b5f79c4b5e6ce47cdef57",
            all(
                evidence.get(key) == value
                for key, value in RF_RUNTIME_PROVENANCE.items()
            ),
            evidence.get("rf_container_image") == "pd-rfpeptide-gpu:fixed",
            evidence.get("mpnn_container_image") == "pd-foundry-gpu:latest",
            backbone is not None,
            backbone == candidate_backbone,
            evidence.get("rf_backbone_sha256") == qc.get("file_sha256"),
            trb is not None,
            fasta is not None,
            fasta == candidate_fasta,
            fasta_sequence_ok,
            isinstance(semantics, dict),
            evidence.get("rf_trb_semantic_parser") == "pickletools_literal_scan_v1",
            evidence.get("rf_trb_semantic_sha256") == semantic_sha,
            (
                semantics.get("contigs") == ["A3-117/0 70-100"]
                if isinstance(semantics, dict)
                else False
            ),
            semantics.get("cyclic") is False if isinstance(semantics, dict) else False,
            (
                _is_exact_int(semantics.get("design_startnum"), seed)
                if isinstance(semantics, dict)
                else False
            ),
            (
                semantics.get("deterministic") is True
                if isinstance(semantics, dict)
                else False
            ),
            (
                semantics.get("hotspot_res") == RF_HOTSPOTS
                if isinstance(semantics, dict)
                else False
            ),
            (
                _is_exact_int(semantics.get("num_designs"), 1)
                if isinstance(semantics, dict)
                else False
            ),
            evidence.get("rf_target_conditioned") is True,
            evidence.get("rf_contig") == "[A3-117/0 70-100]",
            evidence.get("rf_hotspots") == RF_HOTSPOTS,
            evidence.get("rf_cyclic") is False,
            _is_exact_int(evidence.get("rf_design_startnum"), seed),
            evidence.get("rf_deterministic") is True,
            _is_exact_int(evidence.get("mpnn_seed"), seed),
            evidence.get("mpnn_designed_chain") == "B",
            evidence.get("mpnn_fixed_chains") == ["A"],
            evidence.get("mpnn_record_type") == "generated_sample",
            isinstance(evidence.get("mpnn_selected_record_id"), str),
            bool(evidence.get("mpnn_selected_record_id")),
            evidence.get("structure_representation") == "unthreaded_rf_backbone",
            evidence.get("sequence_representation") == "proteinmpnn_generated_fasta",
            evidence.get("sequence_threaded_onto_backbone") is False,
        )
    )


def _runtime_contract(
    job: Mapping[str, str],
    attempt: Path,
    provenance: Mapping[str, Any],
    candidate: Mapping[str, str],
    qc: Mapping[str, str],
) -> bool:
    evidence = provenance.get("evidence")
    if not isinstance(evidence, dict) or not _common_runtime_contract(job, evidence):
        return False
    method = job["method"]
    if method != "PepGLAD" and not _non_pepglad_runtime_schema(method, evidence):
        return False
    if method == "PepMLM":
        return _pepmlm_runtime_contract(evidence)
    if method == "DiffPepBuilder":
        return _diffpepbuilder_runtime_contract(job, attempt, evidence)
    if method == "PepGLAD":
        return _pepglad_runtime_contract(job, attempt, evidence, candidate, qc)
    if method == "D-Flow / PeptideDesign":
        return _dflow_runtime_contract(job, attempt, evidence, candidate, qc)
    if method == "PepMirror":
        return _pepmirror_runtime_contract(job, attempt, evidence, candidate, qc)
    if method == "AfCycDesign / ColabDesign cyclic peptide":
        return _colabdesign_runtime_contract(attempt, evidence, candidate, qc)
    if method == "RFdiffusion + ProteinMPNN":
        return _rf_runtime_contract(job, attempt, evidence, candidate, qc)
    return False


def _supported(
    job: Mapping[str, str],
    attempt: Path | None,
    result: Mapping[str, Any],
    manifest: Mapping[str, str] | None,
    candidate: Mapping[str, str] | None,
    qc: Mapping[str, str] | None,
    runtime_provenance: Mapping[str, Any] | None,
) -> bool:
    if result.get("status") != "passed" or result.get("overall_qc_status") not in {
        "pass",
        "pass_with_warning",
    }:
        return False
    if (
        attempt is None
        or manifest is None
        or candidate is None
        or qc is None
        or runtime_provenance is None
    ):
        return False
    design_id = str(result.get("design_id", ""))
    return all(
        (
            result.get("job_id") == job["job_id"],
            result.get("method") == job["method"],
            _manifest_contract(job, manifest),
            _execution_evidence_contract(job, attempt, result, manifest, candidate, qc),
            candidate.get("job_id") == job["job_id"],
            candidate.get("design_id") == design_id,
            candidate.get("parse_status") in {"parsed", "partial"},
            bool(candidate.get("sequence", "")),
            qc.get("job_id") == job["job_id"],
            qc.get("design_id") == design_id,
            qc.get("overall_qc_status") in PASS_STATUSES,
            _candidate_path_contract(job, attempt, candidate, qc),
            _target_content_contract(
                job, attempt, runtime_provenance, candidate, qc
            ),
            _qc_contract(job, qc, candidate),
            _runtime_provenance_record_contract(runtime_provenance),
            _runtime_contract(job, attempt, runtime_provenance, candidate, qc),
            _semantic_qc_contract(
                job, attempt, runtime_provenance, candidate, qc
            ),
            _stable_adapter_replay_contract(
                job, attempt, runtime_provenance, candidate, qc
            ),
        )
    )


def _merge_outputs(
    *,
    run_root: Path = DEFAULT_RUN_ROOT,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    deployment_path: Path = DEFAULT_DEPLOYMENT_PATH,
    job_manifest: Path = DEFAULT_JOB_MANIFEST,
) -> dict[str, Any]:
    jobs = load_jobs(job_manifest)
    run_root = Path(run_root).resolve()
    results_root = Path(results_root)
    deployment_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, str]] = []
    candidate_rows: list[dict[str, str]] = []
    qc_rows: list[dict[str, str]] = []
    run_rows: list[dict[str, Any]] = []
    runtime_provenance_rows: list[dict[str, Any]] = []
    failure_diagnostic_rows: list[dict[str, Any]] = []
    supported_by_job: dict[str, bool] = {}
    pepglad_extension = next(
        job
        for job in jobs
        if job["method"] == "PepGLAD" and job["seed_stage"] == "extension"
    )
    pepglad_extension_root = (
        run_root
        / METHOD_SLUGS[pepglad_extension["method"]]
        / pepglad_extension["job_id"]
    )
    pepglad_seed43_status = (
        "not_run"
        if _latest_attempt(pepglad_extension_root, run_root) is None
        else "attempt_recorded"
    )

    for job in jobs:
        job_root = run_root / METHOD_SLUGS[job["method"]] / job["job_id"]
        attempt = _latest_attempt(job_root, run_root)
        result_path = (
            _canonical_attempt_input(attempt, "run_result.json")
            if attempt is not None
            else None
        )
        manifest_path = (
            _canonical_attempt_input(attempt, "method_output_manifest.csv")
            if attempt is not None
            else None
        )
        candidate_path = (
            _canonical_attempt_input(attempt, "candidate_outputs.csv")
            if attempt is not None
            else None
        )
        qc_path = (
            _canonical_attempt_input(attempt, "candidate_qc.csv")
            if attempt is not None
            else None
        )
        result = _json_object(result_path) if result_path is not None else None
        manifest = _one_csv_row(manifest_path) if manifest_path is not None else None
        candidate = _one_csv_row(candidate_path) if candidate_path is not None else None
        qc = _one_csv_row(qc_path) if qc_path is not None else None
        result = result or {}
        runtime_provenance = _runtime_provenance(job, attempt)
        runtime_evidence = (
            runtime_provenance.get("evidence")
            if runtime_provenance is not None
            else None
        )
        pepglad_recovery_claimed = (
            job["method"] == "PepGLAD"
            and isinstance(runtime_evidence, dict)
            and set(runtime_evidence) != PEPGLAD_LEGACY_RUNTIME_FIELDS
        )
        pepglad_recovery_valid = not pepglad_recovery_claimed or all(
            (
                attempt is not None,
                candidate is not None,
                qc is not None,
                runtime_provenance is not None,
            )
        )
        if pepglad_recovery_claimed and pepglad_recovery_valid:
            assert attempt is not None
            assert candidate is not None
            assert qc is not None
            assert runtime_provenance is not None
            pepglad_recovery_valid = _runtime_contract(
                job, attempt, runtime_provenance, candidate, qc
            )
        is_supported = _supported(
            job,
            attempt,
            result,
            manifest,
            candidate,
            qc,
            runtime_provenance,
        )
        is_parsed = _parsed_candidate(
            job, result, candidate, qc
        ) and pepglad_recovery_valid
        supported_by_job[job["job_id"]] = is_supported
        if manifest is not None:
            manifest_rows.append(manifest)
        if is_parsed and candidate is not None and qc is not None:
            tracked_candidate = dict(candidate)
            tracked_candidate["supported_candidate"] = "yes" if is_supported else "no"
            tracked_qc = dict(qc)
            for field in METHOD_SPECIFIC_QC_STATUS_FIELDS:
                if not tracked_qc.get(field):
                    tracked_qc[field] = "not_applicable"
            tracked_qc["supported_candidate"] = "yes" if is_supported else "no"
            candidate_rows.append(tracked_candidate)
            qc_rows.append(tracked_qc)
        runtime_provenance_tracked = (
            runtime_provenance is not None
            and pepglad_recovery_valid
            and is_supported
        )
        if runtime_provenance_tracked:
            runtime_provenance_rows.append(runtime_provenance)

        status = str(result.get("status", "not_run"))
        merge_status = (
            "supported"
            if is_supported
            else (
                "evidence_incomplete"
                if status == "passed" or not pepglad_recovery_valid
                else status
            )
        )
        if job["method"] == "PepGLAD" and job["seed_stage"] == "primary":
            diagnostic = _pepglad_failure_diagnostic(
                job,
                attempt,
                result,
                manifest,
                candidate,
                qc,
                runtime_provenance,
                merge_status=merge_status,
                candidate_tracked=is_parsed,
                runtime_provenance_tracked=runtime_provenance_tracked,
                seed43_status=pepglad_seed43_status,
            )
            if diagnostic is not None:
                failure_diagnostic_rows.append(diagnostic)
        deployment_rows.append(
            {
                "execution_id": f"exec_{job['job_id']}",
                "job_id": job["job_id"],
                "method": job["method"],
                "seed_stage": job["seed_stage"],
                "random_seed": job["random_seed"],
                "attempt_id": attempt.name if attempt is not None else "",
                "attempt_dir": str(attempt) if attempt is not None else "",
                "status": status,
                "overall_qc_status": result.get("overall_qc_status", "not_run"),
                "supported_candidate": "yes" if is_supported else "no",
                "merge_status": merge_status,
                "status_reason": result.get("status_reason", "no_attempt_recorded"),
                "candidate_parse_status": (
                    candidate.get("parse_status", "") if candidate else ""
                ),
                "qc_status_reason": qc.get("status_reason", "") if qc else "",
                "chirality_evaluable": qc.get("chirality_evaluable", "") if qc else "",
                "chirality_l_count": qc.get("chirality_l_count", "") if qc else "",
                "chirality_d_count": qc.get("chirality_d_count", "") if qc else "",
                "chirality_unknown_count": (
                    qc.get("chirality_unknown_count", "") if qc else ""
                ),
                "method_contract_status": (
                    qc.get("method_contract_status", "") if qc else ""
                ),
                "handoff_status": qc.get("handoff_status", "") if qc else "",
            }
        )
        run_rows.append(
            {
                "design_id": (
                    candidate.get("design_id", "") if is_parsed and candidate else ""
                ),
                "job_id": job["job_id"],
                "method": job["method"],
                "task_id": job.get("task_id", ""),
                "target_id": job.get("target_id", ""),
                "input_mode": job.get("input_mode", ""),
                "peptide_type": job.get("peptide_type", ""),
                "chirality": job.get("chirality", ""),
                "cyclic": job.get("cyclic", ""),
                "random_seed": job.get("random_seed", ""),
                "seed_stage": job.get("seed_stage", ""),
                "attempt_id": attempt.name if attempt is not None else "",
                "status": status,
                "overall_qc_status": result.get("overall_qc_status", "not_run"),
                "supported_candidate": "yes" if is_supported else "no",
                "sequence": (
                    candidate.get("sequence", "") if is_parsed and candidate else ""
                ),
                "structure_path": (
                    candidate.get("structure_path", "")
                    if is_parsed and candidate
                    else ""
                ),
                "status_reason": result.get("status_reason", "no_attempt_recorded"),
                "notes": "Bounded connectivity evidence only; not scoring, ranking, or Benchmark result",
            }
        )

    for job in jobs:
        if (
            job["seed_stage"] != "extension"
            or not supported_by_job[job["job_id"]]
            or supported_by_job.get(job["primary_job_id"], False)
        ):
            continue
        supported_by_job[job["job_id"]] = False
        for row in deployment_rows:
            if row["job_id"] == job["job_id"]:
                row["supported_candidate"] = "no"
                row["merge_status"] = "primary_not_supported"
        for rows in (candidate_rows, qc_rows, run_rows):
            for row in rows:
                if row["job_id"] == job["job_id"]:
                    row["supported_candidate"] = "no"

    runtime_provenance_rows = [
        row
        for row in runtime_provenance_rows
        if supported_by_job.get(str(row.get("job_id")), False)
    ]

    primary = [job for job in jobs if job["seed_stage"] == "primary"]
    extension = [job for job in jobs if job["seed_stage"] == "extension"]
    primary_passed = sum(supported_by_job[job["job_id"]] for job in primary)
    extension_passed = sum(supported_by_job[job["job_id"]] for job in extension)
    summary: dict[str, Any] = {
        "schema_version": "v0.34",
        "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
        "primary_total": len(primary),
        "primary_passed": primary_passed,
        "primary_complete": primary_passed == len(primary),
        "extension_total": len(extension),
        "extension_passed": extension_passed,
        "extension_complete": extension_passed == len(extension),
        "parsed_candidate_rows": len(candidate_rows),
        "qc_failed_rows": sum(
            row.get("status") == "qc_failed" for row in deployment_rows
        ),
        "runtime_provenance_rows": len(runtime_provenance_rows),
        "job_status": {row["job_id"]: row["merge_status"] for row in deployment_rows},
    }

    manifest_headers = _headers(METHOD_OUTPUT_HEADERS, manifest_rows)
    candidate_headers = _headers(CANDIDATE_HEADERS, candidate_rows)
    qc_headers = _headers(
        ("job_id", "design_id", "overall_qc_status", "status_reason"), qc_rows
    )
    runtime_document = {
        "schema_version": "v0.34",
        "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
        "records": runtime_provenance_rows,
    }
    if not _runtime_provenance_payload_contract(runtime_document):
        raise RuntimeError("runtime provenance output violates its exact schema")
    runtime_payload = (
        json.dumps(
            runtime_document,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    failure_diagnostic_payload = (
        json.dumps(
            {
                "schema_version": "v0.34",
                "evidence_boundary": PEPGLAD_FAILURE_DIAGNOSTIC_BOUNDARY,
                "records": failure_diagnostic_rows,
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    summary_payload = (
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )

    _publish_bundle(
        (
            (
                deployment_path,
                _csv_payload(DEPLOYMENT_HEADERS, deployment_rows),
            ),
            (
                results_root / "pilot_method_output_manifest_v0.34.csv",
                _csv_payload(manifest_headers, manifest_rows),
            ),
            (
                results_root / "pilot_candidate_outputs_v0.34.csv",
                _csv_payload(candidate_headers, candidate_rows),
            ),
            (
                results_root / "pilot_candidate_qc_v0.34.csv",
                _csv_payload(qc_headers, qc_rows),
            ),
            (
                results_root / "pilot_run_v0.34.csv",
                _csv_payload(RUN_HEADERS, run_rows),
            ),
            (
                results_root / "pilot_runtime_provenance_v0.34.json",
                runtime_payload.encode("utf-8"),
            ),
            (
                results_root / "pilot_failure_diagnostics_v0.34.json",
                failure_diagnostic_payload.encode("utf-8"),
            ),
            (
                results_root / "pilot_v034_merge_summary.json",
                summary_payload.encode("utf-8"),
            ),
        )
    )
    return summary


def merge_outputs(
    *,
    run_root: Path = DEFAULT_RUN_ROOT,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    deployment_path: Path = DEFAULT_DEPLOYMENT_PATH,
    job_manifest: Path = DEFAULT_JOB_MANIFEST,
) -> dict[str, Any]:
    global _ACTIVE_CAPTURE_STORE
    if _ACTIVE_CAPTURE_STORE is not None:
        raise RuntimeError("nested v0.34 merge capture sessions are not supported")
    store = _CaptureStore()
    _ACTIVE_CAPTURE_STORE = store
    try:
        return _merge_outputs(
            run_root=run_root,
            results_root=results_root,
            deployment_path=deployment_path,
            job_manifest=job_manifest,
        )
    finally:
        _ACTIVE_CAPTURE_STORE = None
        store.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--deployment-path", type=Path, default=DEFAULT_DEPLOYMENT_PATH)
    args = parser.parse_args()
    summary = merge_outputs(
        run_root=args.run_root,
        results_root=args.results_root,
        deployment_path=args.deployment_path,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["primary_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
