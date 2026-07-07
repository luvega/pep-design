# Benchmark Paper Template Audit

## Material Passport

| field | value |
|:---|:---|
| material_id | `benchmark_template_audit_pep_design_v0.9` |
| project | Pep_design Benchmark KB |
| review_date | 2026-06-18 |
| skill_route | `benchmark-paper-template` main workflow |
| manuscript target | protocol-first Benchmark framework |
| evidence boundary | local artifacts only; v0.9 plan synchronization pass; no new external refresh in this pass |

## Step 1: Five-Pillar Completeness Table

| pillar | covered? | current content | improvement suggestion |
|:---|:---|:---|:---|
| Research Gap | Y | Existing peptide-design evaluation can conflate heterogeneous tasks, incompatible inputs/outputs, engineering readiness, ranking ability, developability proxies and biological evidence. Evidence: `manuscript/outlines/benchmark_manuscript_outline.md`; `benchmark/protocols/benchmark_protocol_v0.md`. | Convert the gap into a concise comparison table against existing peptide-design benchmarks and scoring studies; keep limitations to at most three. |
| Construction Pipeline | Planned | The project has a construction route for KB, candidate methods, target/control schema, dataset watchlist, run.csv, server contracts, v0.8 license/schema/input-contract review and v0.9 method landscape mapping. Evidence: `scripts/build_benchmark_kb.py`; `kb/tables/master_literature_manifest.csv`; `benchmark/input_sets/target_set_v0_schema.md`; `benchmark/deployment/server_smoke_test_contract_v0.6.md`; `ops/plans/updated_plan_v0.9.md`. | In the manuscript, describe this as protocol construction and readiness-gate construction, not as dataset construction with final benchmark samples. |
| Evaluation Framework | Y | T1/T2/T3 task split, generation versus ranking/rescoring tracks, failure states, scoring-output schemas, negative/off-target panel and leakage labels are defined. Evidence: `benchmark/protocols/benchmark_protocol_v0.md`; `benchmark/scoring/scoring_protocol_v0.md`; `benchmark/protocols/scoring_outputs_schema.md`. | Add a compact Figure/Table that maps each metric family to applicable output types and `not_applicable_reason`. |
| Empirical Findings | Planned / missing for current phase | The current manuscript can report readiness findings: literature scope, method heterogeneity, source availability, dataset readiness, target-set not frozen and dry-run gate status. It cannot report model performance. | Use "planned results" or "readiness findings" language; reserve *Finding X* performance summaries for future real runs. |
| Companion Method | NA / future optional | The project does not propose a specialized peptide-design model or judge model. | Mark as `not_applicable` in the current manuscript. Do not add a weak companion method just to satisfy the optional pillar. |

## Step 2: Introduction Six-Part Logic Chain

| part | content for this manuscript |
|:---|:---|
| 1. Background + Running Example | AI peptide design now spans PepMLM-like sequence-conditioned binders, RFdiffusion + ProteinMPNN and BindCraft miniprotein baselines, PepMirror/D-Flow/DexDesign chirality-aware or D-peptide methods, and AfCycDesign / ColabDesign cyclic peptide routes. A running example should show one target where a sequence-only method, a structure-conditioned method and a miniprotein baseline need different inputs and yield non-interchangeable outputs. |
| 2. Existing-benchmark limitations | Limitation 1: single leaderboards can hide task mismatch. Limitation 2: code/weights/source availability can be mistaken for reproducibility. Limitation 3: scoring without controls, assay context and leakage labels can be misread as biological validation. |
| 3. Research Questions | RQ1: How should recent AI peptide-design methods be stratified into task-compatible benchmark interfaces? RQ2: What metadata, target/control and leakage fields are required before generation and ranking scores become interpretable? RQ3: Which methods and datasets are ready only for metadata/source/dry-run planning versus future smoke tests? |
| 4. Design Considerations | A useful protocol-first benchmark must preserve task boundaries, separate generation from ranking/rescoring, encode failure states, record target/control provenance, keep developability at metadata level unless evidence exists, and gate server execution through source/license/weights/input-contract states. |
| 5. Our Proposal | The proposal is a local Benchmark KB and protocol framework containing a 432-record literature layer, 10 first-wave methods, T1/T2/T3 task mapping, target/control schemas, dataset watchlists, runnability/source audits, server dry-run contracts and `run.csv -> metric CSVs -> merged_run.csv` data flow. |
| 6. Contributions | C1: define a task-aware protocol for recent AI peptide-design methods (§2-§5). C2: construct evidence-backed readiness artifacts for methods, datasets, target/control schema and server gates (§3-§8, §13). C3: separate generation, ranking/rescoring, developability and leakage-aware scoring (§6-§10). C4: provide a claim-gated manuscript framework that blocks unsupported reproducibility or performance claims (§11-§12). |

## Step 3: Section Outline For §2 To §7

| section | sketch | carrying figure/table |
|:---|:---|:---|
| §2 Benchmark Lessons From Local Zotero Literature | Summarize local benchmark, scoring, affinity and developability lessons as design evidence. Clarify that these papers justify calibration and scoring boundaries, not candidate-method superiority. | Extended Data: benchmark literature lessons table. |
| §3 Literature Scope And Candidate Method Selection | Define the 2021-06-03 to 2026-06-03 evidence window, the 432-record KB, and the first-wave 10-method include set. | Table 1: candidate methods and task interfaces. |
| §4 Target Set And Control Set Design | Define target classes, positive controls, negative/decoy controls, assay evidence and leakage fields while keeping `target_set_v0.csv` schema-only. | Table 3: target/control schema. |
| §5 Task Stratification | Map methods to T1 sequence binder, T2 structure peptide binder and T3 miniprotein baseline to prevent false cross-task ranking. | Figure 2: task-method-target matrix. |
| §6 Generation Benchmark Protocol | Define parseability, validity, chain convention, chirality/cyclic flags, output completeness and failure states. | Figure 3 left track: generation benchmark. |
| §7 Ranking And Rescoring Benchmark Protocol | Define affinity, structure, interface, developability and calibration reporting separately from generation. | Figure 3 right track plus Table 4 metric applicability. |

The existing manuscript has additional sections for runnability, scoring, leakage, planned results, discussion and methods. They should remain because this project is a protocol-first manuscript, but the first seven sections should carry the core Benchmark template logic.

## Step 4: Pre-Submission Self-Check

| category | status | unresolved critical/major items |
|:---|:---|:---|
| Introduction | Major revisions needed | Running example figure and benchmark comparison table are planned but not yet drafted. |
| Benchmark section | Major revisions needed | Construction pipeline is a protocol/readiness pipeline, not a completed dataset pipeline; manuscript must avoid dataset-scale claims. |
| Experiment section | Critical for future submission, not current protocol draft | No model performance table, human baseline or Finding X results exist; current paper must label this as future Benchmark execution. |
| Structure and completeness | Major revisions needed | License, target-set freeze, data-hosting and reproducibility claims remain gated by v0.6-v0.9 contracts and readiness reviews. |

Pre-submission verdict: **NOT READY for a completed Benchmark-results venue submission; suitable for protocol-first manuscript development after the planned Introduction and claim-gate revisions.**

## Template Decision

Use `benchmark-paper-template` as the governing structure. `intro-drafter` should not be used as the primary introduction template because its own instructions route Benchmark papers back to the Benchmark template.
