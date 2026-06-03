#!/usr/bin/env python
"""Build the peptide-design benchmark background knowledge base.

The script is intentionally read-only toward Zotero, EndNote, and the existing
PD-wiki. It writes only under the current Pep_design project root.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ZOTERO_BASE = "http://127.0.0.1:23119/api/users/0"
ZOTERO_HEADERS = {"Zotero-API-Version": "3"}
BUILD_DATE = "2026-06-03"
DATE_START = "2021-06-03"
DATE_END = "2026-06-03"

ENDNOTE_ROOT = Path(r"E:\Endnote参考文献")
PD_WIKI_ROOT = ENDNOTE_ROOT / "PD-wiki"
KB_ROOT = ENDNOTE_ROOT / "_kb"

COLLECTIONS = {
    "WOJHNDDE": "AI药物设计_蛋白与多肽",
    "0T22MGK6": "PD-wiki_多肽从头设计工具方法综述",
    "WWSP0HLC": "01_Baker_IPD_2018至今",
    "YVPXPS9B": "02_本地蛋白多肽设计",
    "H075SCN7": "04_待补PDF_人工核验",
}

SEARCH_QUERIES = [
    "peptide design",
    "peptide binder design",
    "miniprotein design",
    "binder design",
    "cyclic peptide design",
    "D-peptide design",
    "macrocycle peptide design",
    "peptide mimetic",
    "protein-peptide interaction",
    "pMHC TCR mimic",
    "RFdiffusion ProteinMPNN peptide",
    "ColabDesign cyclic peptide",
    "PepMLM",
    "SaLT PepPr",
    "DiffPepBuilder",
    "PepFlow",
    "PepGLAD",
    "D-Flow peptide",
    "PepMirror",
    "DexDesign OSPREY",
    "BindCraft peptide",
    "BoltzDesign1",
]

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

CANDIDATE_METHODS: list[dict[str, Any]] = [
    {
        "method": "PepMLM",
        "slug": "pepmlm",
        "primary_title": "Target sequence-conditioned design of peptide binders using masked language modeling",
        "paper_key_hint": "U2VXH3ID",
        "year": "2025",
        "family": "sequence-conditioned peptide language model",
        "design_modality": "target-sequence conditioned sequence generation",
        "input_requirement": "target protein sequence plus design constraints",
        "output_type": "linear peptide sequences",
        "peptide_type": "linear peptide binders",
        "task": "de novo peptide binder sequence design",
        "target_type": "protein targets from sequence",
        "code_url": "https://github.com/programmablebio/pepmlm",
        "weights_url": "https://huggingface.co/ChatterjeeLab/PepMLM-650M",
        "license": "repository/model-card dependent; verify before benchmark release",
        "code_status": "public GitHub repository and Hugging Face model card to verify",
        "weights_status": "public model card to verify",
        "inputs_standardizable": "5",
        "outputs_evaluable": "4",
        "gpu_cost": "2",
        "peptide_fit": "5",
        "recency_evidence": "5",
        "total_score": "21",
        "decision": "include",
        "reported_metrics": "binding enrichment and experimental validation reported in source paper",
        "datasets": "programmable biology peptide binder datasets; verify exact benchmark split",
        "claimed_strengths": "directly targets peptide binder design from target sequence, low setup cost",
        "limitations": "sequence-only design needs downstream structure and binding validation",
        "reproducibility_notes": "lock model revision, tokenizer, sampling temperature, target sequence preprocessing",
    },
    {
        "method": "SaLT&PepPr",
        "slug": "salt-peppr",
        "primary_title": "SaLT&PepPr is an interface-predicting language model for designing peptide-guided protein degraders",
        "paper_key_hint": "2GGHXKS1",
        "year": "2023",
        "family": "interface-predicting protein language model",
        "design_modality": "sequence/interface-conditioned degrader peptide design",
        "input_requirement": "target sequence and degrader/interface design context",
        "output_type": "peptide-guided protein degrader candidates",
        "peptide_type": "linear peptide-guided binders/degraders",
        "task": "peptide-guided degrader interface design",
        "target_type": "protein targets from sequence and interface context",
        "code_url": "https://github.com/programmablebio/saltnpeppr",
        "weights_url": "https://huggingface.co/ubiquitx/saltnpeppr",
        "license": "repository/model-card dependent; verify before benchmark release",
        "code_status": "public GitHub repository and Hugging Face model card to verify",
        "weights_status": "public model card to verify",
        "inputs_standardizable": "4",
        "outputs_evaluable": "4",
        "gpu_cost": "2",
        "peptide_fit": "4",
        "recency_evidence": "4",
        "total_score": "18",
        "decision": "include",
        "reported_metrics": "interface prediction and degrader design validation reported in source paper",
        "datasets": "peptide-guided degrader/interface data; verify exact release",
        "claimed_strengths": "connects peptide design with interface prediction and degrader use cases",
        "limitations": "application focus may be narrower than general peptide binder design",
        "reproducibility_notes": "define whether benchmark scores design quality or degrader-specific interface prediction",
    },
    {
        "method": "DiffPepBuilder",
        "slug": "diffpepbuilder",
        "primary_title": "DiffPepBuilder: a structure-aware diffusion model for peptide binder design",
        "paper_key_hint": "",
        "year": "2024",
        "family": "structure-conditioned diffusion model",
        "design_modality": "backbone/sequence co-design around target structure",
        "input_requirement": "target protein structure and peptide binding region",
        "output_type": "peptide backbone/sequence candidates",
        "peptide_type": "linear peptide binders",
        "task": "structure-conditioned peptide binder generation",
        "target_type": "protein structures",
        "code_url": "https://github.com/YuzheWangPKU/DiffPepBuilder",
        "weights_url": "https://zenodo.org/records/12794439",
        "license": "repository/Zenodo dependent; verify before benchmark release",
        "code_status": "public GitHub repository to verify",
        "weights_status": "Zenodo release to verify",
        "inputs_standardizable": "4",
        "outputs_evaluable": "5",
        "gpu_cost": "3",
        "peptide_fit": "5",
        "recency_evidence": "4",
        "total_score": "21",
        "decision": "include",
        "reported_metrics": "structure recovery, binding/interface quality, and design validation to extract",
        "datasets": "protein-peptide complex datasets; verify train/test leakage policy",
        "claimed_strengths": "explicit structural peptide binder generation",
        "limitations": "requires reliable target structures and pocket/interface definition",
        "reproducibility_notes": "pin checkpoint, target chain mapping, peptide length constraints, sampling count",
    },
    {
        "method": "PepGLAD",
        "slug": "pepglad",
        "primary_title": "Full-atom peptide design with geometric latent diffusion",
        "paper_key_hint": "D5XQSGVT",
        "year": "2025",
        "family": "full-atom geometric latent diffusion",
        "design_modality": "full-atom peptide conformer/sequence generation",
        "input_requirement": "peptide design condition and optional target/interface context",
        "output_type": "full-atom peptide structures/sequences",
        "peptide_type": "linear and constrained peptide candidates",
        "task": "full-atom peptide design",
        "target_type": "peptide or protein-peptide contexts",
        "code_url": "https://github.com/THUNLP-MT/PepGLAD",
        "weights_url": "repository release; verify exact checkpoint location",
        "license": "repository dependent; verify before benchmark release",
        "code_status": "public GitHub repository to verify",
        "weights_status": "checkpoint availability needs verification",
        "inputs_standardizable": "4",
        "outputs_evaluable": "5",
        "gpu_cost": "3",
        "peptide_fit": "5",
        "recency_evidence": "5",
        "total_score": "22",
        "decision": "include",
        "reported_metrics": "full-atom geometry and validity metrics to extract",
        "datasets": "peptide structure datasets; verify release",
        "claimed_strengths": "full-atom output is directly useful for structure-level benchmark metrics",
        "limitations": "target-conditioned binder task may require adaptation",
        "reproducibility_notes": "record atom naming, stereochemistry, random seed, and relaxation steps",
    },
    {
        "method": "D-Flow / PeptideDesign",
        "slug": "d-flow-peptidedesign",
        "primary_title": "D-Flow: Multi-modality Flow Matching for D-peptide Design",
        "paper_key_hint": "arxiv:2411.10618",
        "year": "2024",
        "family": "multi-modal flow matching for D-peptide design",
        "design_modality": "full-atom receptor-conditioned D-peptide generation with mirror-image data augmentation",
        "input_requirement": "protein receptor/binding context and D-peptide generation configuration",
        "output_type": "full-atom D-peptide sequences and structures",
        "peptide_type": "D-peptides",
        "task": "de novo D-peptide binder design",
        "target_type": "protein receptor structures",
        "code_url": "https://github.com/smiles724/PeptideDesign",
        "weights_url": "repository archive dflow.zip; verify exact checkpoint provenance",
        "license": "repository dependent; verify before benchmark release",
        "code_status": "public GitHub repository to verify",
        "weights_status": "repository archive/checkpoint route needs verification",
        "inputs_standardizable": "3",
        "outputs_evaluable": "5",
        "gpu_cost": "3",
        "peptide_fit": "5",
        "recency_evidence": "5",
        "total_score": "21",
        "decision": "include",
        "reported_metrics": "chirality-aware full-atom design, sequence/structure, and interface metrics to extract",
        "datasets": "PepMerge and receptor-conditioned peptide benchmark datasets; verify release",
        "claimed_strengths": "covers D-peptide/hetero-chiral space absent from most L-peptide pipelines",
        "limitations": "benchmark tasks need explicit chirality-aware validation metrics",
        "reproducibility_notes": "record mirror-image conversion, x_mirror setting, checkpoint archive, GPU memory setting, and any L-only fallback handling",
    },
    {
        "method": "PepMirror",
        "slug": "pepmirror",
        "primary_title": "Cross-Chirality Generalization by Axial Vectors for Hetero-Chiral Protein-Peptide Interaction Design",
        "paper_key_hint": "DNKX2REN",
        "year": "2026",
        "family": "latent diffusion for cross-chirality D-peptide binder design",
        "design_modality": "target-conditioned mirror-image D-peptide binder generation with axial-feature injection",
        "input_requirement": "target PDB, receptor/ligand chains or pocket center, YAML generation config, and checkpoint",
        "output_type": "D-peptide binder complex structures plus post-processing/ranking metrics",
        "peptide_type": "mirror-image D-peptide binders",
        "task": "de novo D-peptide binder design for L-protein targets",
        "target_type": "L-protein receptor structures with pocket or reference binder context",
        "code_url": "https://github.com/YZY010418/PepMirror",
        "weights_url": "https://zenodo.org/records/20095187",
        "license": "MIT repository license; Zenodo checkpoint license to verify before benchmark release",
        "code_status": "public GitHub repository with installation, generation, mirroring, filtering, and ranking scripts to verify",
        "weights_status": "Zenodo checkpoint download route listed in repository README; exact files and checksums to verify",
        "inputs_standardizable": "4",
        "outputs_evaluable": "5",
        "gpu_cost": "3",
        "peptide_fit": "5",
        "recency_evidence": "5",
        "total_score": "22",
        "decision": "include",
        "reported_metrics": "chirality ratio, interface/ranking metrics, Vina-derived scores, and wet-lab validation evidence to extract",
        "datasets": "LNR/PepBench/ProtFrag resources and wet-lab validation cases reported in the paper; exact targets to extract",
        "claimed_strengths": "directly targets the D-peptide binder gap and provides public code plus checkpoint route",
        "limitations": "local reproducibility is untested; ranking protocol and affinity correlation still need benchmark-phase validation",
        "reproducibility_notes": "record Git commit, Zenodo checkpoint, axial_type, axial_position, mirror mode, pocket definition, chain IDs, ranking thresholds, and PyRosetta/Vina/OpenMM versions",
    },
    {
        "method": "AfCycDesign / ColabDesign cyclic peptide",
        "slug": "afcycdesign-colabdesign",
        "primary_title": "Cyclic peptide structure prediction and design using AlphaFold",
        "paper_key_hint": "HHPV1WW7",
        "year": "2023",
        "family": "AlphaFold/ColabDesign cyclic peptide design",
        "design_modality": "AlphaFold-guided cyclic peptide sequence/structure optimization",
        "input_requirement": "cyclic peptide scaffold or target/binder context",
        "output_type": "cyclic peptide sequences and predicted structures",
        "peptide_type": "cyclic peptides",
        "task": "cyclic peptide structure prediction and design",
        "target_type": "peptides and optional protein targets",
        "code_url": "https://github.com/sokrypton/ColabDesign",
        "weights_url": "AlphaFold/ColabDesign dependencies; verify local model source",
        "license": "ColabDesign and AlphaFold dependency licenses apply",
        "code_status": "public GitHub repository and notebooks to verify",
        "weights_status": "uses AlphaFold-family weights; local availability must be checked",
        "inputs_standardizable": "4",
        "outputs_evaluable": "5",
        "gpu_cost": "4",
        "peptide_fit": "5",
        "recency_evidence": "4",
        "total_score": "22",
        "decision": "include",
        "reported_metrics": "structure prediction accuracy, cyclic closure quality, and design success to extract",
        "datasets": "cyclic peptide structure/design examples",
        "claimed_strengths": "strong baseline for cyclic peptide structural design",
        "limitations": "runtime and model-weight dependencies are heavier than sequence-only methods",
        "reproducibility_notes": "pin notebook/script version, AF model preset, recycle count, and cyclic constraint encoding",
    },
    {
        "method": "DexDesign / OSPREY3",
        "slug": "dexdesign-osprey3",
        "primary_title": "DexDesign: an OSPREY-based algorithm for designing de novo D-peptide inhibitors",
        "paper_key_hint": "ULVDDJ6Z",
        "year": "2024",
        "family": "energy/search-based D-peptide design",
        "design_modality": "OSPREY-based rotamer/conformational search",
        "input_requirement": "target structure, D-peptide design site, and search configuration",
        "output_type": "D-peptide inhibitor sequences/conformations",
        "peptide_type": "D-peptides",
        "task": "de novo D-peptide inhibitor design",
        "target_type": "protein structures",
        "code_url": "https://github.com/donaldlab/OSPREY3",
        "weights_url": "not applicable",
        "license": "OSPREY3 license applies; verify before benchmark release",
        "code_status": "public OSPREY3 repository; DexDesign setup must be mapped",
        "weights_status": "not required",
        "inputs_standardizable": "3",
        "outputs_evaluable": "4",
        "gpu_cost": "1",
        "peptide_fit": "4",
        "recency_evidence": "4",
        "total_score": "16",
        "decision": "include",
        "reported_metrics": "energy and binding/design validation metrics to extract",
        "datasets": "D-peptide inhibitor case studies",
        "claimed_strengths": "non-neural baseline for D-peptide design",
        "limitations": "configuration burden may be higher than generative pipelines",
        "reproducibility_notes": "document OSPREY version, force-field settings, search budget, and target preparation",
    },
    {
        "method": "RFdiffusion + ProteinMPNN",
        "slug": "rfdiffusion-proteinmpnn",
        "primary_title": "Improving de novo protein binder design with deep learning",
        "paper_key_hint": "3AYIMQW5",
        "year": "2023",
        "family": "diffusion scaffold generation plus inverse folding sequence design",
        "design_modality": "protein/miniprotein binder backbone generation and sequence assignment",
        "input_requirement": "target structure, hotspot or motif constraints, design length",
        "output_type": "miniprotein/protein binder backbones and sequences",
        "peptide_type": "miniprotein and short protein binders",
        "task": "miniprotein/protein binder design baseline",
        "target_type": "protein structures",
        "code_url": "https://github.com/RosettaCommons/RFdiffusion; https://github.com/dauparas/ProteinMPNN",
        "weights_url": "RFdiffusion and ProteinMPNN public model releases; verify local download route",
        "license": "repository licenses apply; verify before benchmark release",
        "code_status": "public GitHub repositories to verify",
        "weights_status": "public model releases to verify",
        "inputs_standardizable": "4",
        "outputs_evaluable": "5",
        "gpu_cost": "4",
        "peptide_fit": "4",
        "recency_evidence": "4",
        "total_score": "21",
        "decision": "include",
        "reported_metrics": "AF2 confidence, interface metrics, experimental binder success in source studies",
        "datasets": "protein binder design targets and benchmark targets",
        "claimed_strengths": "established runnable baseline for miniprotein/binder design",
        "limitations": "not peptide-specific for short flexible peptides; interface definition can dominate results",
        "reproducibility_notes": "pin RFdiffusion checkpoint, ProteinMPNN version, design length ranges, and AF2 filtering",
    },
    {
        "method": "BindCraft",
        "slug": "bindcraft",
        "primary_title": "BindCraft: one-shot design of functional protein binders",
        "paper_key_hint": "QCD2DXXI",
        "year": "2024",
        "family": "AF2 backpropagation plus MPNN/PyRosetta binder pipeline",
        "design_modality": "one-shot protein/miniprotein binder design",
        "input_requirement": "target structure and binder design settings",
        "output_type": "protein/miniprotein binder sequences and structures",
        "peptide_type": "miniprotein/protein binders",
        "task": "one-shot binder design",
        "target_type": "protein structures",
        "code_url": "https://github.com/martinpacesa/BindCraft",
        "weights_url": "AlphaFold/MPNN/PyRosetta dependencies; verify local setup",
        "license": "repository and dependency licenses apply; verify before benchmark release",
        "code_status": "public GitHub repository to verify",
        "weights_status": "depends on AF2/MPNN/PyRosetta setup",
        "inputs_standardizable": "4",
        "outputs_evaluable": "5",
        "gpu_cost": "4",
        "peptide_fit": "3",
        "recency_evidence": "5",
        "total_score": "21",
        "decision": "include",
        "reported_metrics": "in silico filters and functional binder validation to extract",
        "datasets": "published binder test targets",
        "claimed_strengths": "integrated runnable pipeline with strong binder-design relevance",
        "limitations": "heavier dependencies and less direct fit to very short peptide design",
        "reproducibility_notes": "record dependency stack, AF2 parameters, PyRosetta version, filters, and design count",
    },
    {
        "method": "PepFlow",
        "slug": "pepflow",
        "primary_title": "Full-atom peptide design based on multi-modal flow matching",
        "paper_key_hint": "WA59C5TI",
        "year": "2024",
        "family": "full-atom multi-modal flow matching",
        "design_modality": "sequence/structure full-atom peptide generation",
        "input_requirement": "peptide design condition; exact benchmark I/O to verify",
        "output_type": "full-atom peptide structures/sequences",
        "peptide_type": "peptides",
        "task": "full-atom peptide generation",
        "target_type": "peptide contexts",
        "code_url": "https://huggingface.co/Irwiny/PepFlow",
        "weights_url": "https://huggingface.co/Irwiny/PepFlow",
        "license": "repository dependent; verify before benchmark release",
        "code_status": "Hugging Face route found; GitHub runnable route not confirmed",
        "weights_status": "Hugging Face route found; checkpoint use needs verification",
        "inputs_standardizable": "3",
        "outputs_evaluable": "5",
        "gpu_cost": "3",
        "peptide_fit": "5",
        "recency_evidence": "4",
        "total_score": "20",
        "decision": "watchlist",
        "reported_metrics": "full-atom design metrics to extract",
        "datasets": "peptide structure datasets; verify release",
        "claimed_strengths": "full-atom generative peptide baseline",
        "limitations": "runnable code route and target-conditioned binder fit require confirmation",
        "reproducibility_notes": "promote to include only after executable code, checkpoint use, and input schema are verified",
    },
    {
        "method": "BoltzDesign1",
        "slug": "boltzdesign1",
        "primary_title": "BoltzDesign1: Inverting All-Atom Structure Prediction Model for Generalized Biomolecular Binder Design",
        "paper_key_hint": "CRM22UDT",
        "year": "2025",
        "family": "all-atom structure-prediction inversion",
        "design_modality": "generalized biomolecular binder design",
        "input_requirement": "target complex/design specification",
        "output_type": "binder sequences/structures",
        "peptide_type": "general binders; peptide/miniprotein fit to verify",
        "task": "general binder design watchlist",
        "target_type": "protein and biomolecular targets",
        "code_url": "https://github.com/jwohlwend/boltz",
        "weights_url": "Boltz model releases; verify design-specific route",
        "license": "repository/model dependent; verify before benchmark release",
        "code_status": "public ecosystem exists; design workflow needs confirmation",
        "weights_status": "model release exists; design checkpoint/workflow to verify",
        "inputs_standardizable": "3",
        "outputs_evaluable": "4",
        "gpu_cost": "4",
        "peptide_fit": "3",
        "recency_evidence": "5",
        "total_score": "19",
        "decision": "watchlist",
        "reported_metrics": "binder design metrics to extract after workflow confirmation",
        "datasets": "general biomolecular binder targets",
        "claimed_strengths": "all-atom foundation-model route for future benchmark expansion",
        "limitations": "not first-wave unless peptide/miniprotein inputs and execution path are confirmed",
        "reproducibility_notes": "record exact design command and whether it is standalone or requires server/API",
    },
]

CONCEPTS = [
    {
        "slug": "peptide-binder-design",
        "title": "Peptide Binder Design",
        "summary": "面向蛋白靶点生成或优化短肽结合体，是本 Benchmark 的核心任务之一。",
        "methods": ["PepMLM", "SaLT&PepPr", "DiffPepBuilder", "PepMirror", "RFdiffusion + ProteinMPNN"],
    },
    {
        "slug": "cyclic-peptide-design",
        "title": "Cyclic Peptide Design",
        "summary": "环肽设计强调闭环约束、构象稳定性和全原子几何质量。",
        "methods": ["AfCycDesign / ColabDesign cyclic peptide", "PepGLAD", "PepFlow"],
    },
    {
        "slug": "d-peptide-and-chirality",
        "title": "D-peptide And Chirality-aware Design",
        "summary": "D-peptide 与异手性设计需要显式记录手性编码、结构验证和可合成性边界。",
        "methods": ["DexDesign / OSPREY3", "D-Flow / PeptideDesign", "PepMirror"],
    },
    {
        "slug": "miniprotein-and-binder-baselines",
        "title": "Miniprotein And Binder Baselines",
        "summary": "miniprotein/minibinder 方法可作为多肽设计能力的邻近基线，但不能替代短肽任务。",
        "methods": ["RFdiffusion + ProteinMPNN", "BindCraft", "BoltzDesign1"],
    },
    {
        "slug": "pmhc-tcr-mimic",
        "title": "pMHC And TCR-mimic Binders",
        "summary": "pMHC/TCR-mimic 是高特异性免疫识别相关场景，适合做应用层背景而非第一轮通用候选。",
        "methods": [],
    },
    {
        "slug": "benchmark-readiness",
        "title": "Benchmark Readiness",
        "summary": "候选方法必须有可运行证据、可批量输入、可评估输出和可记录依赖版本。",
        "methods": [method["method"] for method in CANDIDATE_METHODS if method["decision"] == "include"],
    },
]

PD_WIKI_IMPORTS = [
    "index.md",
    "AGENTS.md",
    "wiki/review/peptide-methods/review_outline_peptide_methods_zh.md",
    "wiki/review/peptide-methods/review_manuscript_peptide_methods_zh_v11_nature_review_style.md",
    "wiki/review/peptide-methods/review_v11_completion_audit.md",
    "wiki/review/peptide-methods/review_figure_table_plan_v11.md",
]


def ensure_dirs() -> None:
    dirs = [
        "raw_sources/zotero",
        "raw_sources/pd_wiki",
        "raw_sources/endnote",
        "raw_sources/external_search",
        "references",
        "wiki/literature",
        "wiki/methods",
        "wiki/concepts",
        "wiki/benchmark_candidates",
        "tables",
        "reports",
        "scripts",
    ]
    for rel in dirs:
        (PROJECT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def write_text(rel: str, text: str) -> None:
    path = PROJECT_ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(rel: str, payload: Any) -> None:
    path = PROJECT_ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(rel: str, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path = PROJECT_ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in headers})


def zotero_get(path: str, timeout: int = 30) -> tuple[Any, dict[str, str]]:
    url = ZOTERO_BASE + path
    req = urllib.request.Request(url, headers=ZOTERO_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        headers = dict(response.headers.items())
        content_type = response.headers.get("Content-Type", "")
        raw = response.read()
    if "application/json" in content_type:
        return json.loads(raw.decode("utf-8")), headers
    return raw.decode("utf-8", errors="replace"), headers


def zotero_paginated(path: str, limit: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    separator = "&" if "?" in path else "?"
    while True:
        page_path = f"{path}{separator}limit={limit}&start={start}"
        data, headers = zotero_get(page_path)
        if not isinstance(data, list):
            break
        rows.extend(data)
        total = headers.get("Total-Results")
        start += limit
        if total is not None:
            try:
                if start >= int(total):
                    break
            except ValueError:
                break
        elif len(data) < limit:
            break
    return rows


def zotero_bibtex(item_key: str) -> str:
    try:
        text, _headers = zotero_get(f"/items/{urllib.parse.quote(item_key)}?format=bibtex")
        return text if isinstance(text, str) else ""
    except Exception:
        return ""


def parse_bibtex_key(bibtex: str) -> str:
    match = re.search(r"@\w+\{([^,\s]+),", bibtex)
    return match.group(1) if match else ""


def slugify(value: str, fallback: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    value = re.sub(r"-{2,}", "-", value)
    return (value[:90].strip("-") or fallback.lower())


def normalize_title(title: str) -> str:
    return re.sub(r"\W+", "", title.casefold())


def year_from_item(data: dict[str, Any], meta: dict[str, Any]) -> str:
    candidates = [str(data.get("date") or ""), str(meta.get("parsedDate") or "")]
    for candidate in candidates:
        match = re.search(r"(20\d{2}|19\d{2})", candidate)
        if match:
            return match.group(1)
    return ""


def pmid_from_item(data: dict[str, Any]) -> str:
    fields = [str(data.get("archiveLocation") or ""), str(data.get("extra") or ""), str(data.get("url") or "")]
    for field in fields:
        match = re.search(r"PMID[:\s]*(\d+)|pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", field, flags=re.I)
        if match:
            return next(group for group in match.groups() if group)
    return ""


def arxiv_from_item(data: dict[str, Any]) -> str:
    fields = [str(data.get("DOI") or ""), str(data.get("extra") or ""), str(data.get("url") or "")]
    for field in fields:
        match = re.search(r"arxiv[:\s/]*(\d{4}\.\d{4,5}(?:v\d+)?)", field, flags=re.I)
        if match:
            return match.group(1)
    return ""


def creators_from_item(data: dict[str, Any]) -> str:
    names: list[str] = []
    for creator in data.get("creators", []) or []:
        if creator.get("name"):
            names.append(creator["name"])
        else:
            first = creator.get("firstName", "")
            last = creator.get("lastName", "")
            names.append(" ".join(part for part in [first, last] if part).strip())
    return "; ".join(name for name in names if name)


def classify_item(title: str, year: str) -> tuple[str, str, str, str, str, str, str]:
    text = title.casefold()
    family = ""
    modality = ""
    input_req = ""
    output_type = ""
    availability = "zotero metadata; runnable status not checked"
    status = "needs-manual-check"
    reason = ""

    if any(term in text for term in ["review", "evolution", "past, present", "artificial intelligence in peptide"]):
        status = "background-only"
        reason = "review or broad background source"

    if any(term in text for term in ["peptide", "miniprotein", "minibinder", "binder", "rfdiffusion", "proteinmpnn", "colabdesign", "d-peptide", "macrocycle", "cyclic", "pmhc", "tcr"]):
        if status != "background-only":
            status = "included"
        family = "peptide/protein binder design"
        input_req = "sequence or structure depending on method"
        output_type = "designed peptide/miniprotein sequence or structure"

    if "cyclic" in text or "macrocycle" in text:
        family = "cyclic/macrocyclic peptide design"
        modality = "cyclic or macrocycle structure-aware design"
    elif "d-peptide" in text or "chirality" in text:
        family = "D-peptide or chirality-aware design"
        modality = "chirality-aware design/search"
    elif "language model" in text or "masked language" in text or "contrastive" in text:
        family = "protein/peptide language model"
        modality = "sequence-conditioned generation"
    elif "diffusion" in text or "flow" in text or "generative" in text:
        family = "generative full-atom or diffusion model"
        modality = "structure/sequence generative modeling"
    elif "miniprotein" in text or "binder" in text:
        family = "miniprotein/protein binder design"
        modality = "structure or sequence conditioned binder design"

    if year and year < "2021":
        if status == "included":
            status = "background-only"
            reason = "outside primary five-year window"
    if not year:
        status = "needs-manual-check"
        reason = "missing publication year"
    if status == "needs-manual-check" and not reason:
        reason = "requires manual relevance review"
    return family, modality, input_req, output_type, availability, status, reason


def collect_zotero() -> tuple[list[dict[str, Any]], dict[str, str]]:
    collections, _ = zotero_get("/collections")
    write_json("raw_sources/zotero/collections.json", collections)

    status: dict[str, Any] = {"source": "Zotero local API", "base": ZOTERO_BASE, "build_date": BUILD_DATE}
    write_json("raw_sources/zotero/zotero_status_snapshot.json", status)

    collection_payload: dict[str, Any] = {}
    query_payload: dict[str, Any] = {}
    item_sources: dict[str, list[str]] = {}
    item_by_key: dict[str, dict[str, Any]] = {}

    for key, name in COLLECTIONS.items():
        rows = zotero_paginated(f"/collections/{urllib.parse.quote(key)}/items/top")
        collection_payload[key] = {"name": name, "count": len(rows), "items": rows}
        for row in rows:
            item_key = row.get("key", "")
            if not item_key:
                continue
            item_by_key[item_key] = row
            item_sources.setdefault(item_key, []).append(f"zotero_collection:{name}")

    for query in SEARCH_QUERIES:
        params = urllib.parse.urlencode({"q": query})
        rows = zotero_paginated(f"/items/top?{params}")
        query_payload[query] = {"count": len(rows), "items": rows}
        for row in rows:
            item_key = row.get("key", "")
            if not item_key:
                continue
            item_by_key[item_key] = row
            item_sources.setdefault(item_key, []).append(f"zotero_query:{query}")

    write_json("raw_sources/zotero/seed_items_by_collection.json", collection_payload)
    write_json("raw_sources/zotero/search_results_by_query.json", query_payload)

    rows: list[dict[str, Any]] = []
    bibtex_chunks: list[str] = []
    bibtex_key_by_zotero: dict[str, str] = {}
    seen_identity: set[str] = set()
    duplicate_rows: list[dict[str, str]] = []

    candidate_by_title = {
        normalize_title(method["primary_title"]): method for method in CANDIDATE_METHODS
    }

    for item_key, item in sorted(item_by_key.items(), key=lambda pair: pair[0]):
        data = item.get("data", {})
        meta = item.get("meta", {})
        title = str(data.get("title") or "").strip()
        if not title:
            continue
        doi = str(data.get("DOI") or "").strip()
        pmid = pmid_from_item(data)
        arxiv_id = arxiv_from_item(data)
        identity = (
            f"doi:{doi.casefold()}"
            if doi
            else f"pmid:{pmid}"
            if pmid
            else f"arxiv:{arxiv_id.casefold()}"
            if arxiv_id
            else f"title:{normalize_title(title)}"
        )
        if identity in seen_identity:
            duplicate_rows.append({"zotero_key": item_key, "identity": identity, "title": title})
            continue
        seen_identity.add(identity)

        year = year_from_item(data, meta)
        venue = str(data.get("publicationTitle") or data.get("conferenceName") or data.get("websiteTitle") or "")
        bibtex = zotero_bibtex(item_key)
        bibtex_key = parse_bibtex_key(bibtex)
        if bibtex.strip():
            bibtex_chunks.append(bibtex.strip())
        if bibtex_key:
            bibtex_key_by_zotero[item_key] = bibtex_key

        family, modality, input_req, output_type, availability, status, reason = classify_item(title, year)
        method_match = candidate_by_title.get(normalize_title(title))
        code_url = ""
        weights_url = ""
        if method_match:
            family = method_match["family"]
            modality = method_match["design_modality"]
            input_req = method_match["input_requirement"]
            output_type = method_match["output_type"]
            availability = method_match["code_status"]
            code_url = method_match["code_url"]
            weights_url = method_match["weights_url"]
            status = "included" if method_match["decision"] == "include" else "needs-manual-check"
            reason = "" if status == "included" else "candidate watchlist; runnable route not fully confirmed"

        rows.append(
            {
                "source_id": "; ".join(sorted(set(item_sources.get(item_key, [])))),
                "zotero_key": item_key,
                "bibtex_key": bibtex_key,
                "doi": doi,
                "pmid": pmid,
                "arxiv_id": arxiv_id,
                "title": title,
                "year": year,
                "venue": venue,
                "method_family": family,
                "design_modality": modality,
                "input_requirement": input_req,
                "output_type": output_type,
                "availability_status": availability,
                "code_url": code_url,
                "weights_url": weights_url,
                "pdf_status": "has Zotero children" if meta.get("numChildren") else "not checked",
                "screening_status": status,
                "exclusion_reason": reason,
                "creators": creators_from_item(data),
                "abstract": str(data.get("abstractNote") or "").strip(),
                "url": str(data.get("url") or "").strip(),
            }
        )

    write_csv("references/dedupe_report.csv", ["zotero_key", "identity", "title"], duplicate_rows)
    write_csv(
        "references/zotero-map.tsv",
        ["zotero_key", "bibtex_key", "title"],
        [
            {
                "zotero_key": row["zotero_key"],
                "bibtex_key": row["bibtex_key"],
                "title": row["title"],
            }
            for row in rows
            if row["bibtex_key"]
        ],
    )
    # Re-write the TSV with tabs after DictWriter created a comma file.
    map_path = PROJECT_ROOT / "references/zotero-map.tsv"
    with map_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["zotero_key", "bibtex_key", "title"], delimiter="\t")
        writer.writeheader()
        for row in rows:
            if row["bibtex_key"]:
                writer.writerow(
                    {
                        "zotero_key": row["zotero_key"],
                        "bibtex_key": row["bibtex_key"],
                        "title": row["title"],
                    }
                )

    write_text("references/references.bib", "\n\n".join(bibtex_chunks))
    return rows, bibtex_key_by_zotero


def import_pd_wiki_sources() -> list[dict[str, str]]:
    imported: list[dict[str, str]] = []
    if PD_WIKI_ROOT.exists():
        for rel in PD_WIKI_IMPORTS:
            src = PD_WIKI_ROOT / rel
            if src.exists():
                dst = PROJECT_ROOT / "raw_sources/pd_wiki" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                imported.append({"source": str(src), "project_copy": str(dst), "type": "selected_pd_wiki_file"})
        card_dir = PD_WIKI_ROOT / "wiki/review/peptide-methods/reference_evidence_cards_v8"
        if card_dir.exists():
            for src in sorted(card_dir.glob("*.md")):
                dst = PROJECT_ROOT / "raw_sources/pd_wiki/reference_evidence_cards_v8" / src.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                imported.append({"source": str(src), "project_copy": str(dst), "type": "reference_evidence_card"})

    legacy_project = KB_ROOT / "review_projects/03_ai_drug_design_protein_peptide_methods"
    if legacy_project.exists():
        for src in sorted(legacy_project.rglob("*")):
            if src.is_file() and src.suffix.lower() in {".md", ".csv", ".json"}:
                dst = PROJECT_ROOT / "raw_sources/pd_wiki/_kb_review_project" / src.relative_to(legacy_project)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                imported.append({"source": str(src), "project_copy": str(dst), "type": "kb_review_project"})

    write_csv("raw_sources/pd_wiki/import_manifest.csv", ["source", "project_copy", "type"], imported)
    return imported


def method_by_title_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        lookup[normalize_title(row["title"])] = row
    return lookup


def write_method_outputs(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_title = method_by_title_lookup(rows)
    evidence_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []

    for method in CANDIDATE_METHODS:
        matched_row = by_title.get(normalize_title(method["primary_title"]))
        paper_key = (
            (matched_row.get("bibtex_key") if matched_row else "")
            or (matched_row.get("zotero_key") if matched_row else "")
            or method["paper_key_hint"]
            or "external-search-needed"
        )
        evidence_rows.append(
            {
                "method": method["method"],
                "paper_key": paper_key,
                "task": method["task"],
                "target_type": method["target_type"],
                "peptide_type": method["peptide_type"],
                "input": method["input_requirement"],
                "output": method["output_type"],
                "reported_metrics": method["reported_metrics"],
                "datasets": method["datasets"],
                "claimed_strengths": method["claimed_strengths"],
                "limitations": method["limitations"],
                "reproducibility_notes": method["reproducibility_notes"],
            }
        )
        score_rows.append(
            {
                "method": method["method"],
                "primary_paper": method["primary_title"],
                "code_status": method["code_status"],
                "weights_status": method["weights_status"],
                "license": method["license"],
                "inputs_standardizable": method["inputs_standardizable"],
                "outputs_evaluable": method["outputs_evaluable"],
                "gpu_cost": method["gpu_cost"],
                "peptide_fit": method["peptide_fit"],
                "recency_evidence": method["recency_evidence"],
                "total_score": method["total_score"],
                "decision": method["decision"],
            }
        )
        write_method_card(method, paper_key)
        if method["decision"] == "include":
            write_candidate_card(method, paper_key)

    write_csv("tables/method_evidence_matrix.csv", EVIDENCE_HEADERS, evidence_rows)
    write_csv("tables/candidate_method_scorecard.csv", SCORE_HEADERS, score_rows)
    return evidence_rows, score_rows


def write_method_card(method: dict[str, Any], paper_key: str) -> None:
    status_label = "纳入候选" if method["decision"] == "include" else "观察名单"
    text = f"""---
title: "{method['method']}"
type: method_card
status: {method['decision']}
created: {BUILD_DATE}
wiki_role: benchmark_method
source_count: 1
last_reviewed: {BUILD_DATE}
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:{paper_key}", "applies_to:benchmark-readiness"]
---

# {method['method']}

## 定位
{method['method']} 属于 `{method['family']}`。当前状态为 **{status_label}**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
{method['input_requirement']}

## 输出
{method['output_type']}

## 适用 peptide 类型
{method['peptide_type']}

## 依赖
- 代码/服务：{method['code_url']}
- 权重/模型：{method['weights_url']}
- 许可：{method['license']}

## 原始论文
- 题名：{method['primary_title']}
- 年份：{method['year']}
- 本地/外部 key：{paper_key}

## 候选评分
- 输入可标准化：{method['inputs_standardizable']}/5
- 输出可评估：{method['outputs_evaluable']}/5
- GPU 成本可控性：{method['gpu_cost']}/5
- 多肽任务贴合度：{method['peptide_fit']}/5
- 近年证据：{method['recency_evidence']}/5
- 总分：{method['total_score']}/25
- 决策：{method['decision']}

## 复现风险
{method['limitations']}

## Benchmark 前置记录
{method['reproducibility_notes']}
"""
    write_text(f"wiki/methods/{method['slug']}.md", text)


def write_candidate_card(method: dict[str, Any], paper_key: str) -> None:
    text = f"""---
title: "{method['method']} benchmark candidate"
type: benchmark_candidate
status: include
created: {BUILD_DATE}
wiki_role: candidate_decision
source_count: 1
last_reviewed: {BUILD_DATE}
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/{method['slug']}.md"]
---

# {method['method']}

## 纳入理由
{method['claimed_strengths']}

## 最小 Benchmark I/O
- 输入：{method['input_requirement']}
- 输出：{method['output_type']}
- 目标类型：{method['target_type']}
- 多肽类型：{method['peptide_type']}

## 执行前必须锁定
- 代码：{method['code_url']}
- 权重：{method['weights_url']}
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：{method['primary_title']}
- 追踪 key：{paper_key}
"""
    write_text(f"wiki/benchmark_candidates/{method['slug']}.md", text)


def write_literature_cards(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    selected = [
        row
        for row in rows
        if row.get("screening_status") == "included"
        and row.get("year")
        and DATE_START[:4] <= row["year"] <= DATE_END[:4]
    ]
    selected = sorted(selected, key=lambda row: (row.get("year", ""), row.get("title", "")), reverse=True)[:120]
    for row in selected:
        slug = slugify(row["title"], row["zotero_key"])
        abstract = row.get("abstract") or "未抽取全文；当前卡片基于 Zotero 元数据和题名级筛选。"
        text = f"""---
title: "{row['title'].replace('"', "'")}"
type: literature_card
status: {row['screening_status']}
created: {BUILD_DATE}
wiki_role: evidence_card
source_count: 1
last_reviewed: {BUILD_DATE}
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:{row['zotero_key']}"]
---

# {row['title']}

## Metadata
- Zotero item key: `{row['zotero_key']}`
- BibTeX key: `{row['bibtex_key']}`
- Year: {row['year']}
- Venue: {row['venue']}
- DOI: {row['doi']}
- PMID: {row['pmid']}
- arXiv: {row['arxiv_id']}

## Screening
- Status: {row['screening_status']}
- Method family: {row['method_family']}
- Design modality: {row['design_modality']}
- Input: {row['input_requirement']}
- Output: {row['output_type']}
- Availability: {row['availability_status']}

## Evidence Note
{abstract[:900]}
"""
        rel = f"wiki/literature/{slug}.md"
        write_text(rel, text)
        cards.append({"file": rel, "title": row["title"], "zotero_key": row["zotero_key"], "year": row["year"]})
    return cards


def write_concepts() -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for concept in CONCEPTS:
        method_links = []
        for method_name in concept["methods"]:
            method = next((item for item in CANDIDATE_METHODS if item["method"] == method_name), None)
            if method:
                method_links.append(f"- [{method_name}](../methods/{method['slug']}.md)")
            else:
                method_links.append(f"- {method_name}")
        text = f"""---
title: "{concept['title']}"
type: concept
status: active
created: {BUILD_DATE}
wiki_role: concept_map
source_count: {len(concept['methods'])}
last_reviewed: {BUILD_DATE}
claims: ["concept page summarizes routing logic rather than adding new literature claims"]
relations: []
---

# {concept['title']}

{concept['summary']}

## 相关方法
{chr(10).join(method_links) if method_links else "- 当前作为背景主题，不纳入第一轮可运行方法清单。"}
"""
        rel = f"wiki/concepts/{concept['slug']}.md"
        write_text(rel, text)
        cards.append({"file": rel, "title": concept["title"], "type": "concept"})
    return cards


def write_indexes(literature_cards: list[dict[str, str]]) -> None:
    method_rows = [
        {
            "file": f"{method['slug']}.md",
            "type": "method",
            "description": method["family"],
            "status": method["decision"],
        }
        for method in CANDIDATE_METHODS
    ]
    candidate_rows = [
        {
            "file": f"{method['slug']}.md",
            "type": "candidate",
            "description": method["task"],
            "status": method["decision"],
        }
        for method in CANDIDATE_METHODS
        if method["decision"] == "include"
    ]
    concept_rows = [
        {"file": f"{concept['slug']}.md", "type": "concept", "description": concept["summary"], "status": "active"}
        for concept in CONCEPTS
    ]

    def table(rows: list[dict[str, str]]) -> str:
        lines = ["| file | type | description | status |", "|:---|:---|:---|:---|"]
        for row in rows:
            lines.append(f"| `{row['file']}` | {row['type']} | {row['description']} | {row['status']} |")
        return "\n".join(lines)

    literature_rows = [
        {
            "file": Path(card["file"]).name,
            "type": "literature",
            "description": f"{card['year']} {card['title']}",
            "status": "included",
        }
        for card in literature_cards
    ]

    write_text("wiki/methods/_index.md", "# Method Cards\n\n" + table(method_rows))
    write_text("wiki/benchmark_candidates/_index.md", "# Benchmark Candidates\n\n" + table(candidate_rows))
    write_text("wiki/concepts/_index.md", "# Concepts\n\n" + table(concept_rows))
    write_text("wiki/literature/_index.md", "# Literature Cards\n\n" + table(literature_rows))
    write_text(
        "raw_sources/_index.md",
        """# Raw Sources

| folder | source | rule |
|:---|:---|:---|
| `zotero/` | Zotero local API snapshots | read-only source metadata |
| `pd_wiki/` | mirrored selected files from `E:\\Endnote参考文献\\PD-wiki` and `_kb` | project-local copy; do not edit upstream source |
| `endnote/` | source-library routing notes | source of truth remains EndNote/Zotero |
| `external_search/` | query logs and manually curated method URLs | used for查漏 and runnable-status validation |
""",
    )


def write_external_search_log() -> None:
    source_rows = []
    for method in CANDIDATE_METHODS:
        source_rows.append(
            {
                "method": method["method"],
                "primary_paper": method["primary_title"],
                "code_url": method["code_url"],
                "weights_url": method["weights_url"],
                "status": method["decision"],
            }
        )
    write_csv(
        "raw_sources/external_search/method_repository_routes.csv",
        ["method", "primary_paper", "code_url", "weights_url", "status"],
        source_rows,
    )
    query_lines = [
        "# External Search Log",
        "",
        f"- Date: {BUILD_DATE}",
        "- Role: 查漏、校验最新状态、确认 public code/model/Zenodo/Hugging Face route。",
        "- Boundary: 这些外部 URL 是第一阶段可运行性证据线索；正式 Benchmark 前必须逐一打开仓库、锁定版本、检查 license。",
        "",
        "## Query Blocks",
    ]
    for query in SEARCH_QUERIES:
        query_lines.append(f"- `{query}`")
    query_lines.extend(
        [
            "",
            "## Source Prioritization",
            "- Zotero 本地库和 `E:\\Endnote参考文献\\PD-wiki` 是主证据入口。",
            "- PubMed/Semantic Scholar/OpenAlex/Crossref/arXiv/bioRxiv/PMC 用于元数据查漏。",
            "- GitHub/Hugging Face/Zenodo 用于 runnable route 查证。",
        ]
    )
    write_text("references/search_log.md", "\n".join(query_lines))
    write_text("raw_sources/external_search/search_log.md", "\n".join(query_lines))


def check_url_status(url: str) -> tuple[str, str]:
    if not url or url == "not applicable" or "verify" in url or "release;" in url:
        return "", "not_checked"
    if ";" in url:
        parts = [part.strip() for part in url.split(";") if part.strip()]
        statuses = [check_url_status(part) for part in parts]
        code = "; ".join(item[0] for item in statuses if item[0])
        status = "; ".join(item[1] for item in statuses)
        return code, status
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "Codex-Pep-design-KB/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return str(response.status), "reachable"
    except Exception:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Codex-Pep-design-KB/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                return str(response.status), "reachable_get"
        except Exception as exc:
            return "", f"unreachable:{type(exc).__name__}"


def write_url_status() -> None:
    rows: list[dict[str, str]] = []
    for method in CANDIDATE_METHODS:
        for field in ["code_url", "weights_url"]:
            url = method[field]
            status_code, status = check_url_status(url)
            rows.append(
                {
                    "method": method["method"],
                    "field": field,
                    "url": url,
                    "http_status": status_code,
                    "check_status": status,
                }
            )
    write_csv(
        "raw_sources/external_search/url_status.csv",
        ["method", "field", "url", "http_status", "check_status"],
        rows,
    )


def write_reports(rows: list[dict[str, Any]], evidence_rows: list[dict[str, Any]], score_rows: list[dict[str, Any]], imported: list[dict[str, str]]) -> None:
    status_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["screening_status"]] = status_counts.get(row["screening_status"], 0) + 1
        family = row["method_family"] or "unclassified"
        family_counts[family] = family_counts.get(family, 0) + 1
    include_count = sum(1 for row in score_rows if row["decision"] == "include")

    write_text(
        "reports/skill_selection.md",
        f"""# Skill Selection

## 已采用
- Zotero：只读导出本地文献元数据、BibTeX 和 item-key 映射。
- building-llm-wiki：按 raw sources / wiki / schema 三层结构建设项目知识库。
- literature-review 与 citation-management：用于检索块、去重、元数据完整性和 references.bib 管理。
- academic-chinese-style / nature-language-style：用于中文报告的证据边界、克制表达和 overclaim 控制。

## 替代说明
`biomedical-research-framework` 未在本机 skill 目录中发现；本阶段用固定 CSV schema、method card 的证据字段、以及 overclaim/hedging 规则替代其产物。

## 后续暂不启用
- office-academic-skill：留到 PPT/Word 报告阶段。
- scientific-toolkit-skill：留到实际 Benchmark 统计和图表阶段。
""",
    )

    family_lines = "\n".join(f"- {family}: {count}" for family, count in sorted(family_counts.items()))
    status_lines = "\n".join(f"- {status}: {count}" for status, count in sorted(status_counts.items()))
    write_text(
        "reports/literature_scope_report.md",
        f"""# Literature Scope Report

## Scope
- Time window: {DATE_START} to {DATE_END}
- Primary source: Zotero local API collections and targeted query blocks.
- Source layer reused: `E:\\Endnote参考文献\\PD-wiki` and `_kb\\review_projects\\03_ai_drug_design_protein_peptide_methods`.
- Project layer: `E:\\Codex_Projects\\Pep_design`.

## Counts
- Unique Zotero-derived records after DOI/PMID/arXiv/title dedupe: {len(rows)}
- Imported PD-wiki/_kb source files: {len(imported)}
- Method evidence rows: {len(evidence_rows)}
- First-wave included benchmark methods: {include_count}

## Screening Status
{status_lines}

## Method Family Counts
{family_lines}

## Notes
- Rows marked `needs-manual-check` are not rejected; they need full-text or repository verification.
- Rows marked `background-only` can support Benchmark article background but do not count toward method candidates.
""",
    )

    table_lines = ["| method | score | decision | runnable evidence |", "|:---|:---:|:---|:---|"]
    for row in score_rows:
        method = next(item for item in CANDIDATE_METHODS if item["method"] == row["method"])
        table_lines.append(f"| {row['method']} | {row['total_score']} | {row['decision']} | {method['code_url']} |")
    write_text(
        "reports/candidate_methods_shortlist.md",
        f"""# Candidate Methods Shortlist

第一轮选择遵循“先可运行，再代表性”的规则。`include` 表示进入 Benchmark 方案设计阶段；`watchlist` 表示保留但需要进一步确认执行路线。

{chr(10).join(table_lines)}

## Include Set
纳入数量为 {include_count}，满足 5-10 个候选方法的第一阶段要求。

## Watchlist
PepFlow 和 BoltzDesign1 目前保留为观察名单，主要原因是可运行路线、权重位置或 peptide/miniprotein 任务适配度仍需二次确认。
""",
    )


def write_root_docs(rows: list[dict[str, Any]], score_rows: list[dict[str, Any]]) -> None:
    include_count = sum(1 for row in score_rows if row["decision"] == "include")
    write_text(
        "AGENTS.md",
        f"""# Pep Design Benchmark KB Operating Rules

## Purpose
This project is an independent Benchmark background knowledge base for recent peptide-design methods.

## Source Boundaries
- Do not edit `E:\\Endnote参考文献`, EndNote `.enl` files, Zotero items, or the upstream `PD-wiki`.
- Treat `raw_sources/` as a local read-only mirror/snapshot layer.
- Treat `wiki/`, `tables/`, `references/`, and `reports/` as generated project artifacts.
- Treat `benchmarks/` as the Benchmark protocol, smoke-test planning, and future run-result interface layer.

## Language And Claims
- Reader-facing prose is Chinese by default.
- Preserve English method names, paper titles, Zotero item keys, BibTeX keys, URLs, model names, and command names.
- Do not claim local reproducibility until a method has been installed and run in a later Benchmark phase.
- Use `提示/支持/表明/仍需验证` rather than overclaiming when evidence is only metadata-level.

## Update Order
1. Refresh Zotero/API snapshots.
2. Update `references/` and `tables/`.
3. Regenerate `wiki/` cards and `_index.md` files.
4. Update `reports/` and append `log.md`.
5. Run `python scripts/validate_benchmark_kb.py`.
""",
    )
    write_text(
        "index.md",
        f"""# 多肽设计方法 Benchmark 知识库

## Current Status
- Build date: {BUILD_DATE}
- Time window: {DATE_START} to {DATE_END}
- Unique Zotero-derived records after dedupe: {len(rows)}
- First-wave included methods: {include_count}
- Project boundary: this folder is the working KB; Zotero/EndNote/PD-wiki remain source systems.

## Navigation
- [Raw source snapshots](raw_sources/_index.md)
- [References and search log](references/search_log.md)
- [Literature cards](wiki/literature/_index.md)
- [Method cards](wiki/methods/_index.md)
- [Concept map](wiki/concepts/_index.md)
- [Benchmark candidates](wiki/benchmark_candidates/_index.md)
- [Candidate shortlist](reports/candidate_methods_shortlist.md)
- [Literature scope report](reports/literature_scope_report.md)
- [Benchmark protocol v0](benchmarks/protocols/benchmark_protocol_v0.md)
- [run.csv schema](benchmarks/protocols/run_csv_schema.md)
- [Scoring protocol v0](benchmarks/scoring/scoring_protocol_v0.md)
- [Method runnability audit](reports/method_runnability_audit.md)

## Next Phase
The current next phase is smoke-test readiness: freeze target/input schemas, verify method install routes, and prepare minimal run plans without downloading large weights or running GPU benchmark tasks.
""",
    )
    write_text(
        "log.md",
        f"""# Project Log

## [{BUILD_DATE}] protocol | benchmark v0.2 readiness layer
- Added Benchmark protocol, run.csv schema, scoring-output schema, runnability audit, and smoke-test planning layer.
- Followed `de_novo_binder_scoring` as a scoring-pipeline reference for standard inputs, independent metrics, and merged CSV outputs.
- Did not download model weights, install candidate methods, run GPU tasks, or claim local reproducibility.

## [{BUILD_DATE}] bootstrap | peptide design benchmark KB
- Built independent raw/wiki/schema project structure under `E:\\Codex_Projects\\Pep_design`.
- Read Zotero through local API only; no Zotero writes were performed.
- Mirrored selected `PD-wiki` and `_kb` evidence files into `raw_sources/pd_wiki`.
- Generated literature manifest, method evidence matrix, candidate scorecard, method cards, concept pages, and reports.
""",
    )


def write_source_paths() -> None:
    text = f"""# Source Paths

## Active Project Layer
- `E:\\Codex_Projects\\Pep_design`

## Raw Literature Systems
- EndNote/Zotero source workspace: `E:\\Endnote参考文献`
- EndNote source libraries include `.enl` plus `.Data\\sdb\\*.eni` where present.
- Existing generated literature wiki: `E:\\Endnote参考文献\\PD-wiki`
- Existing EndNote/Zotero KB layer: `E:\\Endnote参考文献\\_kb`

## Rule
This project stores snapshots and derived notes only. Do not move, delete, or rewrite raw EndNote/Zotero/PD-wiki files from this project workflow.
"""
    write_text("raw_sources/endnote/source_paths.md", text)


def main() -> None:
    ensure_dirs()
    rows, _bibtex_map = collect_zotero()
    imported = import_pd_wiki_sources()
    write_source_paths()
    write_external_search_log()
    write_url_status()
    write_csv("tables/master_literature_manifest.csv", MASTER_HEADERS, rows)
    literature_cards = write_literature_cards(rows)
    write_concepts()
    evidence_rows, score_rows = write_method_outputs(rows)
    write_indexes(literature_cards)
    write_reports(rows, evidence_rows, score_rows, imported)
    write_root_docs(rows, score_rows)
    summary = {
        "build_date": BUILD_DATE,
        "project_root": str(PROJECT_ROOT),
        "zotero_unique_records": len(rows),
        "literature_cards": len(literature_cards),
        "method_cards": len(CANDIDATE_METHODS),
        "included_candidates": sum(1 for row in score_rows if row["decision"] == "include"),
        "pd_wiki_imported_files": len(imported),
    }
    write_json("reports/build_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
