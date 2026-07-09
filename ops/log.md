# Project Log

## [2026-07-08] release | v1.2.10 multi-case fixture pilot planning
- Bumped project version to `1.2.10`.
- Added v0.22 method-example fixture evidence, multi-case fixture target/control/job manifests, priority gate review, pilot plan and pilot audit.
- Converted v0.21 method-example adapter evidence into focused fixture pilot rows for PepMLM, DiffPepBuilder, PepGLAD, PepMirror and RFdiffusion + ProteinMPNN.
- Preserved D-Flow as `blocked_input_contract`, AfCycDesign / ColabDesign cyclic peptide as `blocked_cli_adapter`, and BindCraft as `wrapper_review_only`.
- Added validator and pytest coverage for v0.22 row counts, blocked-row invariants, target/control fixture-only boundaries and BindCraft LowConfidence output classification.
- Updated README, index, Benchmark README, input/results READMEs, AGENTS, release notes and claim-evidence map for v0.22.
- Maintained boundaries: no `target_set_v0.csv` promotion, no clone/download/install/Docker build/GPU run, no scoring, no method-ranking evidence, no complete Benchmark result, and no biological-validation claim.

## [2026-07-08] release | v1.2.9 adapter smoke and parser fixture readiness
- Bumped project version to `1.2.9`.
- Added v0.21 adapter smoke manifests, result summaries, blocker asset manifest, parser method-output/candidate/run rows, and adapter smoke audit.
- Built `pd-benchmark-methods-gpu:0.21` and `pd-pyrosetta-methods-gpu:0.21` externally under `/data/protein-design`; PyRosetta initialized in `bench-pepmirror`.
- Downloaded PepGLAD public checkpoint assets and the PepMirror Zenodo checkpoint to the external workbench only.
- Recorded bounded adapter/control evidence for PepMLM, DiffPepBuilder, PepGLAD, PepMirror, RFdiffusion + ProteinMPNN and BindCraft; RFdiffusion handoff now links RF PDB output to ProteinMPNN FASTA output.
- Recorded residual blockers: D-Flow missing PepMerge cache/input contract, SaLT&PepPr license/gated-model access, ColabDesign CLI adapter route, and OSPREY3 carry-forward-only status.
- Updated validator, README, index, Benchmark README, AGENTS, release notes and claim-evidence map for v0.21.
- Maintained boundaries: no `target_set_v0.csv` promotion, no scoring, no method-ranking evidence, no complete Benchmark result, no biological-validation claim, and no raw logs/weights/source trees/generated structures stored in the KB.

## [2026-07-08] release | v1.2.8 method unblock readiness and independent PyRosetta route
- Bumped project version to `1.2.8`.
- Added v0.20 method-unblock manifest and smoke result summaries for all 10 first-wave methods.
- Added an independent external PyRosetta image route under `/data/protein-design/images/pd-pyrosetta-methods-gpu/`, separate from BindCraft.
- Built `pd-pyrosetta-methods-gpu:0.20` from the RosettaCommons quarterly US West mirror and recorded a passing DiffPepBuilder GPU unblock smoke for one method-provided example.
- Recorded current blockers: unresolved PepMirror checkpoint manifest/download route, unresolved PepGLAD release assets, missing D-Flow input cache/data contract, SaLT&PepPr license gate, ColabDesign CLI adapter gate, and BindCraft bounded-smoke timeout.
- Updated validator, README, index, Benchmark README, AGENTS, release notes and claim-evidence map for v0.20.
- Maintained boundaries: no `target_set_v0.csv` promotion, no scoring, no method-ranking evidence, no complete Benchmark result, no biological-validation claim, and no raw logs/weights/source trees/private PyRosetta credentials or non-public Rosetta materials stored in the KB.

## [2026-07-07] release | v1.2.7 external method install and example-smoke readiness
- Bumped project version to `1.2.7`.
- Added v0.19 method source/doc verification, install smoke manifest and smoke-test result summary tables for all 10 first-wave methods.
- Built and reused external workbench images `pd-benchmark-methods-gpu:0.19.1` and `pd-bindcraft-gpu:0.19.1`; raw logs, Docker layers, weights and generated outputs remain outside the KB.
- Recorded GPU example/preflight evidence for PepMLM, RFdiffusion + ProteinMPNN, PepGLAD and D-Flow, CPU route-probe evidence for DexDesign / OSPREY3, and blockers for DiffPepBuilder, BindCraft, SaLT&PepPr, PepMirror and ColabDesign.
- Updated validator, README, index, Benchmark README, AGENTS, release notes and claim-evidence map for v0.19.
- Maintained boundaries: no `target_set_v0.csv` promotion, no scoring, no method-ranking evidence, no complete Benchmark result, no biological-validation claim, and no raw logs/weights/source trees stored in the KB.

## [2026-07-07] release | v1.2.6 Batch B pilot gates and adapter replay fixtures
- Bumped project version to `1.2.6`.
- Added v0.17 Batch B pilot gates for target fixtures, method scope and planned fixture jobs without promoting `target_set_v0.csv`.
- Added v0.18 adapter replay fixture manifest and parser-generated small replay tables for method output manifest, candidate outputs and run rows.
- Added `scripts/parse_batch_a_replay_fixtures.py` to regenerate v0.18 replay fixture CSVs from external v0.15 Batch A smoke outputs.
- Updated claim boundaries, validator coverage, README, index, Benchmark README, AGENTS and release notes for v0.17/v0.18.
- Maintained boundaries: no new method execution, model download, data download, scoring, performance ranking, `target_set_v0.csv` promotion or `smoke_test_ready` claim.

## [2026-07-07] release | v1.2.5 adapter parser hardening and Batch B review planning
- Bumped project version to `1.2.5`.
- Added `benchmark/deployment/adapter_parser_hardening_matrix_v0.16.csv` to convert v0.15 minimal smoke evidence into adapter/parser hardening requirements and caveat queues.
- Added `benchmark/input_sets/batch_b_target_review_queue_v0.16.csv` for MDM2/p53, MHCII/HIV, PDL1, pMHC, PepBench/LNR and PepMerge review candidates without freezing `target_set_v0.csv`.
- Added `benchmark/protocols/adapter_replay_contract_v0.16.md` and `ops/plans/adapter_parser_hardening_plan_v0.16.md`.
- Added v0.15/v0.16 claim boundaries and validator coverage for v0.16 rows, required files, external path boundaries and no-overclaim rules.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no new clone/download/install/build/run, no raw logs or generated structures stored in the KB, no scoring, no performance comparison, no `target_set_v0.csv` promotion, and no `smoke_test_ready` claim.

## [2026-07-07] release | v1.2.4 external preflight and Batch A smoke evidence
- Bumped project version to `1.2.4`.
- Added `benchmark/deployment/run_preflight_results_v0.15.csv` to record import-level preflight results for PepMLM, DiffPepBuilder, PepGLAD, D-Flow / PeptideDesign and AfCycDesign / ColabDesign cyclic peptide in the externally built `pd-benchmark-methods-gpu:0.13` image.
- Added `benchmark/deployment/batch_a_smoke_test_results_v0.15.csv` with minimal smoke-test summaries for PepMLM, ProteinMPNN and RFpeptide/RFdiffusion.
- Added `ops/audits/batch_a_execution_audit_v0.15.md` to summarize image build evidence, external logs/output locations, caveats and no-overclaim boundaries.
- Updated validator, README, index, Benchmark README, release notes and AGENTS for v0.15.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no raw logs or generated structures stored in the KB, no `target_set_v0.csv` promotion, no scoring, no performance comparison, no complete Benchmark result, and no biological-validation claim.

## [2026-07-07] release | v1.2.3 academic-search target candidate planning
- Bumped project version to `1.2.3`.
- Added `benchmark/method_sources/method_paper_case_matrix_v0.14.csv` to map PepMLM, DiffPepBuilder, PepGLAD, D-Flow and RFdiffusion + ProteinMPNN pMHC literature cases to Benchmark task roles.
- Added `benchmark/input_sets/target_candidate_academic_search_v0.14.csv` with 16 candidate targets or panels, including NCAM1, AMHR2, MDM2/3EQS, MHCII/1SJH, 3CLpro/7Z4S, ALK1/6SF1, TNF/7KP7, PepBench/LNR, PepMerge, PEPBI, GPCR 124 complexes, pMHC and Chang ranking sources.
- Added `ops/plans/target_candidate_academic_search_plan_v0.14.md` and `ops/audits/target_candidate_academic_search_audit_v0.14.md`.
- Updated validator, README, index, Benchmark README, input-set README, method-source README, release notes and AGENTS for v0.14.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no PDF/data/weight download, no source clone, no install, no Docker/GPU run, no smoke-test evidence, no `target_set_v0.csv` promotion, and no local reproducibility or method-performance claim.

## [2026-07-07] release | v1.2.2 Docker image assignment scaffold
- Bumped project version to `1.2.2`.
- Added v0.13 Docker image inventory and method-environment assignment manifests for the `/mnt/ssd4t/protein-design` workbench.
- Recorded that existing RFdiffusion/RFpeptide, ProteinMPNN/Foundry, BindCraft, AF2/AF3, Rosetta, PepMimic and RFpeptide images should be reused rather than rebuilt inside the Benchmark KB.
- Added an image-consolidation plan and Docker/environment assignment audit for the shared `pd-benchmark-methods-gpu:0.13` multi-conda scaffold covering PepMLM, DiffPepBuilder, PepGLAD, D-Flow/PeptideDesign and ColabDesign.
- Updated validator, index, README, Benchmark README, AGENTS and validation report coverage for v0.13.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no model-weight download, no dataset download, no third-party source stored in the KB, no method installation evidence, no Docker/GPU benchmark run, no smoke-test-ready claim, no target-set promotion, and no local reproducibility or method-performance claim.

## [2026-07-07] release | v1.2.1 repository checkpoint and source checkout notice
- Bumped project version to `1.2.1`.
- Consolidated v0.10 structure/preflight planning, v0.11 source-I/O adapter planning, v0.12 external source-code clone auditing, and v1.3 grant-style planning into one repository checkpoint.
- Added release-note notification that first-wave include-method source code is externally checked out under `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark`.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no model-weight download, no dataset download, no environment creation, no Docker/GPU task, no smoke-test execution, no target-set promotion, and no local reproducibility or method-performance claim.

## [2026-07-07] source | v0.12 external algorithm source checkout
- Cloned the 11 GitHub repositories corresponding to the first-wave Benchmark include methods under `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark`.
- Added `benchmark/deployment/source_clone_manifest_v0.12.csv` and `ops/audits/source_code_clone_audit_v0.12.md` to record pinned commits, external paths, license/env file discovery, LFS/submodule status and clone boundary notes.
- Updated validator, index, README, Benchmark README and release notes for the v0.12 source-only checkout layer.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no model-weight download, no dataset download, no environment creation, no Docker/GPU task, no smoke-test execution, no target-set promotion, and no local reproducibility or method-performance claim.

## [2026-07-07] organization | v0.10 structure and preflight package
- Reorganized the project into `sources/`, `kb/`, `benchmark/`, `manuscript/`, and `ops/` layers without retaining old top-level compatibility directories.
- Added `ops/migration/file_role_map_v0.10.csv`, `ops/plans/server_preflight_plan_v0.10.md`, `benchmark/deployment/preflight_download_approval_v0.10.csv`, `benchmark/deployment/method_preflight_status_v0.10.csv`, and `benchmark/input_sets/target_control_freeze_checklist_v0.10.md`.
- Moved the from-scratch server runbook to `ops/plans/server_from_scratch_run_plan_v0.10.md`.
- Maintained boundaries: no source clone, no dataset download, no environment creation, no model weights, no GPU task, no target-set promotion, no smoke test, and no local reproducibility or performance claim.

## [2026-07-03] planning | server from-scratch run plan v0.10
- Added `ops/plans/server_from_scratch_run_plan_v0.10.md` as the server-side from-zero execution plan.
- The plan defines external roots, license/account gates, source clone and pin audit, download approval, environment build, input contracts, Batch A dry-run, Batch A smoke-test, scoring/merge outputs, and small-artifact back-sync rules.
- Updated `index.md` to expose the new server execution plan.
- Maintained boundaries: the current workstation did not clone third-party sources, download data, create environments, fetch weights, run GPU jobs, freeze `target_set_v0.csv`, or make any reproducibility/performance claim.

## [2026-07-03] planning | v1.3 grant-style mock review update
- Applied `research-grants` framing to produce a grant-style mock review of the protocol-first Benchmark project.
- Added `ops/audits/grant_style_mock_review_v1.3.md`, `ops/plans/updated_plan_v1.3.md`, and `kb/tables/grant_review_action_items_v1.3.csv`.
- Updated `index.md`, `README.md`, manuscript TODOs, claim-evidence boundaries, and validator coverage for v1.3 action gates.
- Maintained boundaries: v1.3 is a simulated review and v0.10 preflight-planning layer only; no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no environment creation, no model weights, no GPU task, no target-set promotion, no smoke test, no funding-decision claim, and no local reproducibility or performance claim.

## [2026-06-29] manuscript | imagegen figure redesign
- Replaced the four simple manuscript PNG schematics with built-in `$imagegen` multi-panel raster figures.
- Copied the generated images from `C:\Users\xsui\.codex\generated_images\019f1192-55d8-74d1-aee7-4f077c9bc8b6` into the four existing `manuscript/assets/figures/benchmark_figure*_v1.png` paths.
- Added `manuscript/assets/figures/manuscript_figure_imagegen_qc_v2.md` and updated the prompt record, Chinese/English outline figure descriptions, figure/table plan, sync map, TODO list, claim-evidence map, README, index, and validator coverage.
- Maintained boundaries: figures remain protocol/readiness schematics only, with no benchmark execution, no source clone, no dataset or weight download, no GPU task, no target-set promotion, no performance ranking, and no local reproducibility or biological-validation claim.

## [2026-06-29] writing | review-addressed bilingual outline pass
- Updated the Chinese and English manuscript outlines with reviewer-facing claim-boundary revisions.
- Added an Introduction comparison table for existing peptide benchmark/scoring resources as a citation-planning layer only.
- Expanded Discussion limitations with missing server logs, real run/metric CSVs, parser outputs, wet-lab evidence, developability evidence, and transferability boundaries.
- Updated sync map, TODOs, reference bibliography, and claim-evidence map to keep the new comparison-table and no-download/no-performance boundaries traceable.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no environment creation, no model weights, no GPU tasks, no target-set promotion, and no local reproducibility or performance claims.

## [2026-06-18] manuscript | v1.2 Chinese figure/table embedding layer
- Bumped project version to `1.2.0`.
- Added four project-local manuscript figure assets under `manuscript/assets/figures/` and recorded image-generation intent in `imagegen_prompt_record_v1.md`.
- Embedded four conceptual figures and four CSV-derived Markdown tables into `manuscript/outlines/benchmark_manuscript_outline_zh_v1.md`.
- Updated `scripts/validate_benchmark_kb.py` to validate figure assets, embedded CSV source references, and the "not real benchmark result" boundary.
- Kept all manuscript figures and embedded tables as planning/reporting artifacts only: no benchmark execution, no performance ranking, and no local reproducibility claim.

## [2026-06-18] writing | v1.1 supplementary-source synthesis
- Added a read-only synthesis layer for six external Markdown supplementary materials from `G:\Downloads\Markdown笔记`.
- Added `manuscript/support/supplementary_materials_reference_value_v1.1.md`, `manuscript/support/short_peptide_scoring_rationale_v1.1.md`, and `manuscript/support/cyclic_peptide_benchmark_supplement_v1.1.md`.
- Added `kb/tables/supplementary_materials_action_matrix_v1.1.csv`, `kb/tables/scoring_metric_rationale_matrix_v1.1.csv`, and `kb/tables/method_landscape_patch_candidates_v1.1.csv`.
- Synchronized Chinese/English manuscript outlines, sync map, TODO list, claim-evidence map, README, and index with v1.1 boundaries.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no environment creation, no model weights, no GPU tasks, no target-set promotion, and no local reproducibility or performance claims.

## [2026-06-18] writing | v1.0 bilingual manuscript outline layer
- Added separate Chinese and English Benchmark manuscript draft outlines in `manuscript/outlines/benchmark_manuscript_outline_zh_v1.md` and `manuscript/outlines/benchmark_manuscript_outline_en_v1.md`.
- Added `manuscript/support/benchmark_manuscript_sync_map_v1.csv` to keep bilingual section IDs, shared evidence artifacts, claim IDs, and next actions aligned.
- Added shared v1.0 support artifacts: `kb/tables/candidate_method_classification_v1.csv`, `manuscript/support/benchmark_test_design_v1.md`, `benchmark/input_sets/reference_dataset_sources_v1.csv`, `manuscript/support/benchmark_reference_bibliography_v1.md`, and `manuscript/support/benchmark_manuscript_todo_v1.csv`.
- Extended the claim-evidence map and validator to guard bilingual-outline, code-route, no-download dataset, test-design, and citation-verification boundaries.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no environment creation, no model weights, no GPU tasks, no target-set promotion, and no local reproducibility or performance claims.

## [2026-06-18] schema | local AGENTS contract initialization
- Reinitialized `AGENTS.md` as the local agent operating contract for the v0.9 Pep_design Benchmark KB.
- Added skill routing for `building-llm-wiki`, `academic-research-suite`, `benchmark-paper-template`, Chinese academic style skills, Zotero, citation management, and external evidence verification.
- Added current-plan routing to `ops/plans/updated_plan_v0.9.md`, artifact roles, execution gates, claim boundaries, update order, validation commands, and git safety rules.
- Extended `scripts/validate_benchmark_kb.py` to verify the local AGENTS contract contains required plan, skill-routing, gate, and validation tokens.

## [2026-06-18] release | v0.9.0 plan and manuscript synchronization
- Bumped project version to `0.9.0`.
- Added `ops/plans/updated_plan_v0.9.md` as the current authoritative plan, consolidating ARS review, Benchmark paper template alignment, v0.8 readiness evidence, and v0.9 review-driven method landscape coverage.
- Updated `README.md`, `index.md`, `RELEASE_NOTES.md`, manuscript outline, claim-evidence map, and validator checks so the project no longer points to v0.7/v0.8 as the current plan.
- Kept `method_landscape_watchlist_v0.9.csv` as a landscape/watchlist artifact only: no new include methods, no target-set promotion, no server execution, and no performance or reproducibility claims.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no environment creation, no model weights, no GPU tasks, and no local reproducibility claims.

## [2026-06-11] synthesis | review-driven benchmark framework supplement
- Synthesized the read-only draft `G:\Downloads\Markdown笔记\王梁多肽综述草稿.md` into additive Benchmark framework supplements, building on `manuscript/support/review_draft_benchmark_reference_value.md`.
- Added `manuscript/support/review_synthesis_benchmark_framework_supplement.md` and `benchmark/method_sources/method_landscape_watchlist_v0.9.csv` (paradigm/topology coverage map for ~22 review methods vs the 10 include methods).
- Added a generation paradigm taxonomy axis (structure/sequence/function-property), cross-cutting cyclic/chirality/ncAA constraint matrix, and a representativeness-gaps section to `benchmark_protocol_v0.md`.
- Flagged naming disambiguations: PepMimic vs PepMirror and PPFlow vs PepFlow; surfaced cyclic (CpSDE/CP-Composer) and ncAA (PepINVENT/HELM-GPT/NCFlow) as method-coverage gaps in review_only status.
- Maintained boundaries: no external draft edits, no new include methods (kept 5-10), no `target_set_v0.csv` promotion, no Zotero/EndNote/PD-wiki writes, no source clone, no dataset/weights download, no GPU tasks, and no local reproducibility/performance claims.

## [2026-07-07] planning | source I/O and initial smoke-test interface v0.11
- Added `ops/plans/source_io_smoke_test_plan_v0.11.md` to turn the source download, unified input, unified output and initial smoke-test plan into a KB control-plane package.
- Added `job_manifest` and adapter-output schemas plus artificial Batch A example manifests for PepMLM and RFdiffusion + ProteinMPNN.
- Added v0.11 source freshness and adapter preflight manifests, keeping all future download/use decisions at no-until-approved status.
- Added `benchmark/deployment/method_contracts/batch_a_adapter_contract_v0.11.md` to specify PepMLM and RFdiffusion + ProteinMPNN adapter boundaries while keeping PepMirror dependency-blocked.
- Updated validator, index, README and release notes for v0.11 artifacts.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no environment creation, no model weights, no GPU tasks, no smoke-test execution, no target-set promotion, and no local reproducibility or method-performance claims.

## [2026-06-11] review | benchmark reference value of peptide review draft
- Added `manuscript/support/review_draft_benchmark_reference_value.md` to evaluate the read-only draft `G:\Downloads\Markdown笔记\王梁多肽综述草稿.md` for Benchmark representativeness, task taxonomy, target coverage, and claim boundaries.
- Classified the draft's value as high for peptide-discovery background, AI generation paradigms, data scarcity, conformational uncertainty, and cyclic/D/unnatural peptide task boundaries; medium for target-type inspiration; and not usable as dataset, performance, target-freeze, or wet-lab validation evidence.
- Kept boundaries: no edits to the external review draft, no `target_set_v0.csv` promotion, no Zotero/EndNote/PD-wiki writes, no method installation, no model run, and no local reproducibility, performance, or experimental-validation claims.

## [2026-06-09] readiness | license schema input-contract audit v0.8
- Advanced priority data sources and methods from recorded/pinned status to auditable license/schema/input-contract readiness.
- Added `dataset_supplement_schema_review_v0.8.csv`, `method_readiness_review_v0.8.csv`, `download_manifest_v0.8.csv`, and `ops/audits/license_schema_input_contract_review_v0.8.md`.
- Updated PepMLM, RFdiffusion + ProteinMPNN, and PepMirror contracts with v0.8 license, environment, checkpoint, and blocking-dependency evidence.
- Updated validator coverage for v0.8 artifacts and kept all `download_performed` values as `no`.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no environment creation, no model weights, no GPU tasks, no local reproducibility claims, and no target-set promotion.

## [2026-06-09] writing | Supervisor-Skills benchmark evaluation
- Applied Supervisor-Skills to the protocol-first Benchmark manuscript plan.
- Added `ops/audits/supervisor_skills_idea_evaluation.md`, `manuscript/support/benchmark_template_audit.md`, and `manuscript/support/benchmark_intro_logic_chain.md`.
- Updated the manuscript outline Introduction to follow the Benchmark six-part chain, while keeping `intro-drafter` as a consistency check only.
- Updated the claim-evidence map and skill-selection report with skill routing, planned/readiness finding boundaries, and `Companion Method = not_applicable / future optional`.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no source clone, no dataset download, no method install, no model weights, no GPU tasks, and no local reproducibility or performance claims.

## [2026-06-06] release | v0.7.0
- Bumped project version to `0.7.0`.
- Added method-level server contracts for PepMLM and RFdiffusion + ProteinMPNN plus a dependency-only PepMirror contract.
- Added artificial `example_run.csv`, empty download manifest template, and dataset supplement schema-review table.
- Updated `run.csv` schema, manuscript outline, claim-evidence map, ARS action items, and validator checks for v0.7 dry-run planning.
- Maintained boundaries: no source clone, no dataset download, no environment creation, no model weights, no GPU tasks, and no local reproducibility claims.

## [2026-06-06] release | v0.6.0
- Bumped project version to `0.6.0`.
- Applied `academic-research-suite` as a research-to-paper pipeline review framework for the Benchmark plan.
- Added ARS comprehensive review, updated v0.6 plan, ARS action items, dataset supplement watchlist, and server smoke-test contract.
- Updated manuscript outline and claim-evidence map with v0.6 readiness and no-execution boundaries.
- Maintained boundaries: no Zotero/EndNote/PD-wiki writes, no third-party clone, no dataset download, no environment creation, no model weights, no GPU tasks, and no local reproducibility claims.

## [2026-06-03] release | v0.5.0
- Bumped project version to `0.5.0`.
- Added v0.5 link availability and data access manifests for candidate method repositories and benchmark dataset routes.
- Expanded source pin audit to all 10 include methods using GitHub API and `git ls-remote` metadata only.
- Added target candidate matrix v0.5 and Linux CUDA Conda server readiness checklist.
- Maintained boundaries: no third-party source clone, no dataset download, no environment creation, no model weights, no GPU tasks, and no local reproducibility claims.

## [2026-06-03] release | v0.4.0
- Bumped project version to `0.4.0`.
- Added expert-panel review, expert action items, dataset readiness scorecard, target candidate matrix, and source pin audit.
- Audited Overath `final_dataset.csv` externally and recorded the 3,676-row scanned dataset boundary, including blank target rows.
- Shallow-cloned PepMLM, RFdiffusion, ProteinMPNN, and PepMirror outside the repository for source pinning only.
- Maintained boundaries: no third-party source trees in git, no large data in git, no environment creation, no model weights, no GPU tasks, and no local reproducibility claims.

## [2026-06-03] release | v0.3.0
- Bumped project version to `0.3.0`.
- Added dataset candidate audit, method source route audit, and environment feasibility audit for the v0.3 readiness layer.
- Added `overath_binder_success_2025` from bioRxiv/Zenodo as a high-priority scoring calibration and ranking/rescoring candidate dataset.
- Maintained boundaries: no dataset download, no source clone, no environment creation, no model weights, no GPU tasks, and no local reproducibility claims.

## [2026-06-03] release | v0.2.0
- Bumped project version to `0.2.0`.
- Documented the protocol-readiness release in `RELEASE_NOTES.md` and `README.md`.
- Release scope: Benchmark protocol, target/control schemas, runnability audit, local Zotero benchmark lessons, manuscript outline, and validator coverage.
- Exclusions remain unchanged: no method installation, no model weights, no GPU runs, and no local reproducibility claims.

## [2026-06-03] protocol | Zotero benchmark literature revision
- Added local Zotero benchmark/scoring/developability lessons in `manuscript/support/benchmark_literature_lessons.md` and `kb/tables/benchmark_literature_lessons.csv`.
- Added target/control schema, negative-design panel schema, developability metrics, leakage/homology placeholders, and generation versus ranking/rescoring split.
- Split candidate interpretation into `scientific_priority` and `engineering_readiness` while keeping `tier` only as a smoke-test scheduling shorthand.
- Did not write Zotero items, modify EndNote/PD-wiki source layers, install methods, download weights, or run GPU tasks.

## [2026-06-03] protocol | benchmark v0.2 readiness layer
- Added Benchmark protocol, run.csv schema, scoring-output schema, runnability audit, and smoke-test planning layer.
- Followed `de_novo_binder_scoring` as a scoring-pipeline reference for standard inputs, independent metrics, and merged CSV outputs.
- Did not download model weights, install candidate methods, run GPU tasks, or claim local reproducibility.

## [2026-06-03] writing | benchmark manuscript outline
- Drafted the protocol-first Benchmark manuscript outline, claim-evidence map, and figure/table plan.
- Framed the article as Benchmark framework/design rather than completed performance ranking.
- Preserved claim boundaries: no method is described as locally reproduced or superior before smoke tests.

## [2026-06-03] bootstrap | peptide design benchmark KB
- Built independent raw/kb/wiki/schema project structure under `E:\Codex_Projects\Pep_design`.
- Read Zotero through local API only; no Zotero writes were performed.
- Mirrored selected `PD-wiki` and `_kb` evidence files into `sources/raw_snapshots/pd_wiki`.
- Generated literature manifest, method evidence matrix, candidate scorecard, method cards, concept pages, and reports.
