# Peptide Design Benchmark Manuscript Draft Outline (English v1.0, Review-Addressed Pass)

## Title

**A Benchmark Framework for Recent AI Peptide Design Methods: Task Stratification, Runnability Auditing and Unified Scoring**

## Manuscript Positioning

This protocol-first Benchmark outline defines a fair, reproducible and auditable way to compare recent AI peptide design methods. It does not claim that the full Benchmark has been run, that any candidate method has been installed locally, or that one method outperforms another.

The evidence base combines the project KB literature window from 2021-06-03 to 2026-06-03, 10 first-wave include methods, 2 watchlist methods, the v0.9 method landscape, dataset readiness audits, server dry-run contracts, runnability matrices, the manuscript claim-evidence map and local Zotero-derived Benchmark/scoring lessons.

## Keywords

AI peptide design; benchmark; peptide binder; cyclic peptide; D-peptide; miniprotein binder; runnability audit; developability; ranking and rescoring

## Abstract

Generative models, protein foundation models and structure-based design pipelines now appear across linear peptide binders, cyclic peptides, D-peptides, heterochiral peptides, miniprotein binders and protein-peptide interaction tasks. These methods differ in inputs, outputs, dependencies, code and weight availability, stereochemical constraints and scoring applicability. A single undifferentiated leaderboard would conflate generation ability, ranking ability, engineering runnability and biological evidence.

We propose a protocol-first Benchmark framework for recent AI peptide design methods based on a local Zotero/PD-wiki knowledge base and external metadata audits. The framework defines three task interfaces, 10 first-wave include methods, 2 watchlist methods, reference dataset sources, target/control schemas, separate generation and ranking/rescoring tracks, method runnability and server dry-run gates, and a unified `run.csv -> metric CSVs -> merged_run.csv` scoring data flow. These are protocol and readiness-level artifacts, not local execution or performance results.

AlphaFold-style peptide binder ranking, protein-peptide affinity prediction and peptide developability literature can inform scoring and calibration design, but they do not support method superiority claims before a real Benchmark is executed. This release provides a reusable manuscript structure, evidence boundary, test design and execution TODO layer, not a completed performance ranking or experimental success analysis.

## 1. Introduction

### 1.1 Background and running example

Peptide design is moving from empirical screening and structure-inspired optimization toward conditional generation using protein language models, diffusion models, full-atom generative models and AF2/MPNN-style pipelines. PepMLM represents target sequence-conditioned peptide binder design. DiffPepBuilder, PepGLAD, D-Flow / PeptideDesign, PepMirror and AfCycDesign / ColabDesign cyclic peptide represent structure-conditioned peptide design. RFdiffusion + ProteinMPNN and BindCraft represent miniprotein/protein binder baseline pipelines.

Figure 1 uses a single peptide-binding target to show why task stratification matters. A sequence-only route takes a target sequence and returns peptide sequences. A structure-conditioned route requires a target PDB, pocket or reference binder and returns a peptide structure or complex. A miniprotein baseline route returns a binder backbone and sequence. The figure communicates task-interface differences, not performance differences.

### 1.2 Evaluation gap

Current comparisons face three recurring gaps. Task mismatch places sequence-only peptide outputs, structure-conditioned peptide outputs and miniprotein binder outputs in the same unstratified leaderboard. Readiness mismatch treats a code URL, source pin, server contract or download route as installation or reproducibility evidence. Evidence mismatch folds structure confidence, affinity prediction, developability proxies, negative/off-target specificity and biological validation into one score.

Existing peptide benchmark and scoring resources already address peptide property prediction, TCR/pMHC sequence translation, GPCR-targeted design, structural corpora and binder-success labels, but they do not jointly cover recent generative methods' task interfaces, source/weight/license gates, output parseability and claim-boundary separation. The full manuscript should include a comparison table in the Introduction or Related Work. The table below is a citation-planning layer only; it does not mean that these sources are already in `references.bib`, that their data have been downloaded, or that they have been promoted into the frozen target set.

| Resource or source | Main scope | Use in this manuscript | Current citation/evidence boundary |
| --- | --- | --- | --- |
| PepBenchmark / PepBenchData | Sequence/property and developability evaluation | Frames developability/property subtasks but does not replace binder-generation benchmarking | `external:pepbenchmark_2026`; `needs_bibtex_verification` |
| Peptide Property Benchmark (PPB) | Peptide property prediction benchmark | Supports separation between property prediction and developability metrics; not candidate-method performance evidence | `external:peptide_property_benchmark`; `needs_bibtex_verification` |
| TCRTransBench | pMHC/TCR-like sequence translation and cross-reactivity setting | Supports T1/pMHC boundary design and HLA/antigen-peptide metadata requirements | `external:tcrtransbench_2026`; `needs_bibtex_verification` |
| GPCR peptide design benchmark | GPCR target-class design evaluation | Frames target-class-specific benchmarking but does not promote any current target set | `junker_assessment_2026`; `needs_bibtex_verification` |
| Overath binder-success dataset | De novo binder success/failure and ranking-calibration candidate | Supports future T3 ranking/rescoring and success-label calibration | `external:overath_binder_success_2025`; `needs_bibtex_verification`; not downloaded |
| PepMerge / PepBDB / Q-BioLiP | Protein-peptide structural corpus and leakage reference | Supports structural corpus and leakage-reference planning, pending license and schema review | `arxiv:2411.10618`; `needs_bibtex_verification` |

### 1.3 Research questions

RQ1: How can recent AI peptide design methods be mapped to task-compatible Benchmark interfaces before performance comparison?

RQ2: Which target, control, leakage, runnability and scoring metadata are required before generated or ranked outputs become interpretable?

RQ3: Which methods and dataset sources currently sit at metadata, source or dry-run readiness gates, and what evidence is still required before server-side smoke tests?

### 1.4 Design principles

The Benchmark follows five design principles. G1 task compatibility: compare methods within T1/T2/T3 before discussing cross-task differences. G2 evidence provenance: target, control, assay, license and leakage fields must be traceable. G3 execution gating: method state should progress from metadata_ready to smoke_test_ready through explicit gates. G4 metric applicability: unsupported metrics must carry a `not_applicable_reason`. G5 claim safety: protocol readiness, server planning, local reproducibility and biological validation must remain distinct.

### 1.5 Contributions

The contribution is limited to the protocol and readiness layer: (1) a task-aware Benchmark protocol separating T1/T2/T3 peptide-design interfaces; (2) a first-wave method classification with external code routes and readiness gates, without treating source pins as execution evidence; (3) reference dataset source and target/control schemas with no-download boundaries; and (4) a split generation and ranking/rescoring test design plus synchronized Chinese and English outlines, TODOs and claim gates. The manuscript does not propose a new peptide-generation model, companion method, performance ranking or experimental validation.

## 2. Benchmark Lessons From Local Zotero Literature

Local Benchmark and scoring literature indicates that generation, ranking, developability and experimental validation should be reported as separate evidence layers. `chang_ranking_2023` supports AlphaFold-style competitive modeling as a design reference for peptide binder ranking, but not as direct evidence for de novo generation performance. `romero-molina_ppi-affinity_2022` and protein-peptide affinity prediction studies indicate that peptide-aware scoring should not be replaced by small-molecule or generic PPI scoring. `oeller_sequence-based_2023`, `pingitore_v_delocalized_2024` and `rettie_accurate_2025` support developability as an independent scoring family, but the current phase only records metadata-level proxies.

## 3. Literature Scope and Candidate Method Selection

The literature window is fixed at 2021-06-03 to 2026-06-03. The current KB contains 432 deduplicated Zotero-derived records, including 125 included literature records. The first-wave include methods are PepMLM, SaLT&PepPr, DiffPepBuilder, PepGLAD, D-Flow / PeptideDesign, PepMirror, AfCycDesign / ColabDesign cyclic peptide, DexDesign / OSPREY3, RFdiffusion + ProteinMPNN and BindCraft. PepFlow and BoltzDesign1 remain watchlist methods.

Inclusion requires a public code or service route, batchable inputs and outputs, mapping to at least one unified task, and the possibility of recording versions, parameters and resource requirements. Methods are deferred when task fit is weak, weights are unavailable, batch routes are unclear, outputs are not evaluable, or license constraints remain unresolved.

## 4. Candidate Method Taxonomy and Code Routes

Table 1 comes from `kb/tables/candidate_method_classification_v1.csv`. Methods are grouped into three pools:

- `included`: 10 first-wave candidate methods used in the current protocol and smoke-test planning.
- `candidate_watchlist`: PepFlow and BoltzDesign1, retained for later replacement or task expansion.
- `review_only`: related methods from the v0.9 method landscape, used for Related Work, coverage-gap analysis and future source/license audits.

Code routes are external repository, Hugging Face, Zenodo or pending routes. They are not local clone paths. Source pinning and code-route availability do not imply installation, reproduction or problem-free execution.

## 5. Reference Dataset Sources and Target-Set Planning

Table 2 comes from `benchmark/input_sets/reference_dataset_sources_v1.csv`. Candidate sources include the Overath binder-success dataset, PEPBI, PepMerge/PepBDB/Q-BioLip, PepMirror resources, Chang AF2 ranking cases, PepBenchmark/PepBenchData, a GPCR peptide design benchmark and TCRTransBench.

These sources support target-candidate discovery, ranking calibration, schema design or Related Work. `target_set_v0.csv` remains schema-only. No dataset source or target candidate is a frozen Benchmark target. All dataset entries retain no-download or pending-verification status.

## 6. Benchmark Task Stratification

T1 `sequence_binder`: target sequence -> peptide sequence. Methods: PepMLM and SaLT&PepPr.

T2 `structure_peptide_binder`: target PDB, pocket or reference binder -> peptide complex or peptide structure. Methods: DiffPepBuilder, PepGLAD, D-Flow / PeptideDesign, PepMirror, AfCycDesign / ColabDesign cyclic peptide and DexDesign / OSPREY3.

T3 `miniprotein_binder_baseline`: target PDB, hotspot or length constraint -> binder backbone and sequence. Methods: RFdiffusion + ProteinMPNN and BindCraft.

Cross-task comparisons should be restricted to engineering runnability, output evaluability, resource requirements and failure states, not biological success rates.

## 7. Generation Benchmark Protocol

The generation benchmark records whether a method can produce parseable, valid and task-compatible outputs from standardized inputs. Core fields include output completeness, sequence/PDB parseability, length validity, chain validity, chirality flags, cyclic flags, non-natural residue flags, failure state, runtime and resource metadata.

The primary index is `run.csv`. For structure tasks, binder chain defaults to `A` and target chain defaults to `B`; multi-chain targets are recorded as `B,C,D...`. Method-specific chain conventions must be preserved through an adapter mapping from original chains to standard chains.

## 8. Ranking and Rescoring Benchmark Protocol

The ranking/rescoring benchmark records whether affinity, structure, interface and developability evidence can prioritize existing or generated candidates. This track is reported separately from generation because a ranker does not demonstrate de novo generation ability, and a generator may produce parseable candidates without calibrated ranking.

Planned metrics include known binder rank, negative control separation, top-k enrichment, calibration error and not-applicable reasons. No performance values are filled in at the current phase.

## 9. Unified Scoring Framework

The scoring families are:

- `structure_confidence`: pLDDT, pTM, ipTM, PAE/iPAE and ipSAE.
- `interface_geometry`: contacts, interface area, hydrogen bonds and clash count.
- `structure_similarity`: DockQ, backbone RMSD and interface RMSD.
- `design_feasibility`: length, chain validity, chirality flag, cyclic flag and output parseability.
- `developability`: net charge, hydrophobicity, aromaticity, cysteine/disulfide flags, aggregation-risk proxy and synthesis-complexity flag.
- `negative_design` and `leakage_homology`: off-target panels, sequence/structure clusters and training leakage risk.

For sequence-only methods, structural metrics require downstream structure prediction or must be marked not applicable. For D-peptide, cyclic peptide and ncAA methods, chirality, cycle constraints, residue representation and structure parsing boundaries must be explicit.

### 9.1 v1.1 Supplementary-source scoring boundary

The supplementary short-peptide docking material indicates that peptide docking or rescoring should not be interpreted from docking score alone. Future scoring contracts should record whether the binding region is correct, whether N/C-terminal orientation is meaningful and plausible, whether key peptide residues align with target pockets or hotspots, whether the pose is conformationally plausible, whether different peptides are comparable in length, charge, structure source and parameters, and whether MD, free-energy or experimental validation exists. In v1.1 these are planned parser-contract and writing-boundary items only; no docking or MD result is reported.

Cyclic and non-natural peptides also require topology-aware records. `cyclic=yes` is not sufficient to represent head-to-tail, side-chain, disulfide, thioether, mixed or multi-cyclic constraints. D/L/mixed chirality, N-methylation, lipidation, glycosylation, ncAA use and HELM/CHUCKLES-like representation should be future metadata fields. RFpeptides, CyclicMPNN, PPFlow, PepMimic, PocketXMol, BoltzGen, PepINVENT and HELM-GPT are added only as patch candidates or review-only leads; they do not alter the current 10-method include set.

## 10. Runnability, Dependencies and Server Gates

The readiness gates are metadata_ready, source_pinned, license_checked, weights_manifested, input_contract_ready, dry_run_ready and smoke_test_ready. PepMLM and RFdiffusion + ProteinMPNN have v0.7 server contracts and v0.8 input-contract readiness evidence. PepMirror remains at dependency-contract level because PyRosetta, Vina, OpenMM and checkpoint routes still require resolution.

These gates schedule later server-side preflight and governance work. They do not prove local reproducibility. Future server execution must use external clone, data and weight roots, and must not place third-party source code, datasets, weights or GPU results inside the KB.

## 11. Data Leakage, Homology Control and Target Novelty

Every target and reference binder must carry a training-leakage risk field. Protein targets should be clustered by sequence identity or structural similarity. Peptide binders should be checked for sequence similarity and motif overlap. Before verification, the only valid leakage state is `unknown`; it cannot support independent-test wording. pMHC/TCR-like tasks additionally require HLA allele, peptide antigen, near-neighbour peptide panel and cross-reactivity risk fields.

## 12. Anticipated Results Structure

The current Results section can only contain planned and readiness findings:

1. Literature and candidate method screening.
2. Candidate method taxonomy and code routes.
3. Reference dataset sources and no-download readiness.
4. T1/T2/T3 task mapping.
5. Generation and ranking/rescoring scoring design.
6. Dependency, license, weights/checkpoint and server-gate status.
7. Empty slots for future parseability, failure rate, runtime, top-k enrichment and calibration error.

These items should be written as readiness findings or planned result slots, not as results-paper *Finding X* statements. No method superiority, hit rate, experimental success rate or local reproducibility claim should be written before real server-side execution.

## 13. Discussion

The main claim is that peptide design Benchmarking should first solve task definition, target/control governance, leakage control, engineering runnability and metric applicability before performance ranking. Computational scores can support candidate prioritization and structural hypotheses, but they do not replace experimental affinity, experimental structures, cellular function, PK/PD or CMC evidence. A binding score also cannot substitute for medicinal chemistry developability evidence.

Key missing measurements include real server execution logs, commits and environment records, real `run.csv`, metric CSVs, `merged_run.csv`, parser outputs, failure rates, runtime, resource use, target/control freeze, wet-lab affinity/function, off-target specificity, developability experiments, chirality/topology validation for D-peptide/cyclic/ncAA outputs, and leakage/homology checks. Adding these measurements could strengthen the task stratification and scoring design; if real runs show that some methods cannot batch, produce unparseable outputs, or require non-applicable metrics, then stronger comparability claims must be weakened.

The transfer range is also limited. Task stratification, claim gates, not-applicable metrics and source/license/readiness gates can transfer to other peptide-design benchmark projects. Performance, runnability, biological success, target novelty and developability conclusions cannot be transferred to new target classes, assays, chemistries, chirality/cyclization representations or server environments. GPCR, TCR/pMHC, PPI interfaces, cyclic peptides, D-peptides and non-natural amino acid peptides may each change output evaluability, control design and scoring applicability.

Current limitations include that `target_set_v0.csv` still has zero frozen rows, unresolved license/schema/control/leakage fields for some datasets, unresolved weights or dependencies for some methods, the need for stereochemistry-aware validation of D-peptide, cyclic peptide and ncAA outputs, and the absence of real smoke-test and performance reports. The next phase should prepare a server-side preflight package, not a performance-results manuscript.

## 14. Methods

Literature search and deduplication use Zotero item keys, BibTeX keys, DOI, PMID, arXiv ID and normalized title. Candidate method selection uses `candidate_method_scorecard.csv` and `method_landscape_watchlist_v0.9.csv`. Dataset source tracking uses `candidate_benchmark_datasets.csv`, `dataset_supplement_schema_review_v0.8.csv` and the v1.0 reference dataset table. Test design uses `run_csv_schema.md`, `benchmark_protocol_v0.md` and `scoring_outputs_schema.md`. Project integrity is checked by `scripts/validate_benchmark_kb.py`.

## 15. Figures and Tables

- Figure 1: Benchmark running example, protocol pipeline and claim gate.
- Figure 2: Task-method-target evidence matrix.
- Figure 3: Generation versus ranking/rescoring tracks plus missing-measurement layer.
- Figure 4: Scoring architecture, metric CSV modules and merged reporting boundary.
- Table 0: Existing peptide benchmark / scoring resource comparison and citation-planning boundary.
- Table 1: Candidate method taxonomy, tasks, inputs/outputs and code routes.
- Table 2: Reference dataset sources, intended use and license/schema/control/leakage status.
- Table 3: Test design and metric applicability.
- Table 4: Readiness gates and execution boundaries.

The current figure assets are generated with built-in `$imagegen` and reviewed in `manuscript/assets/figures/manuscript_figure_imagegen_qc_v2.md`. They are protocol/readiness figures, not benchmark-result or performance figures.

## 16. TODO List

The detailed TODO list is in `manuscript/support/benchmark_manuscript_todo_v1.csv`. Highest-priority remaining items are to manually review Tables 1 and 2, validate citation keys with citation-management, and close server-side license/checkpoint/input-contract items for PepMLM, RFdiffusion + ProteinMPNN and PepMirror before execution.

## 17. References and Citation Boundary

The reference plan is in `manuscript/support/benchmark_reference_bibliography_v1.md`. The manuscript should cite existing BibTeX keys whenever possible. External sources such as Overath, PepBenchmark, TCRTransBench and the GPCR benchmark must remain marked `needs_bibtex_verification` until they are added to `references.bib` or otherwise verified. No untraceable reference should be introduced.
