# Pep Design Benchmark KB Agent Rules

## Purpose

This project is an independent protocol-first Benchmark knowledge base for recent peptide-design methods. It supports literature evidence management, method and dataset readiness audits, Benchmark manuscript planning, and later server-side smoke-test preparation.

Current authoritative plan: `ops/plans/updated_plan_v0.33.md`.

Current version: `1.2.21`.

Next planned phase: implement real generation entrypoints for the v0.33 method-specific no-supported-output blockers before any scoring layer is attempted. Do not start additional clone, install, large download, broad GPU execution, or scoring/ranking unless the user explicitly requests that later phase. Additional large downloads and generated outputs must remain in gitignored external/runtime roots.

## Source Boundaries

- Do not edit `E:\Endnote参考文献`, EndNote `.enl` files, Zotero items, or the upstream `PD-wiki`.
- Treat `sources/raw_snapshots/` as a local read-only mirror/snapshot layer.
- Treat `kb/references/`, `kb/tables/`, `kb/wiki/`, `manuscript/`, `ops/`, and `benchmark/` as generated project artifacts.
- Treat `benchmark/` as the Benchmark protocol, readiness-audit, smoke-test planning, and future run-result interface layer.
- Do not place third-party source trees, downloaded datasets, model weights, batch PDB outputs, large archives, or GPU run results in this repository.
- Future server-side clones, downloads, weights, and results must live outside the tracked KB or in explicitly gitignored external roots.

## Skill Routing

Use the smallest skill set that covers the task.

| task | required skill route |
|:---|:---|
| Maintain KB structure, indexes, logs, raw/kb/wiki/schema boundaries, or `AGENTS.md` | `building-llm-wiki` |
| Literature review, Zotero/BibTeX provenance, citation checks, claim-evidence review, manuscript pipeline or integrity gate | `academic-research-suite` |
| Benchmark manuscript structure, Introduction logic, five-pillar audit, section skeleton, pre-submission checklist | `benchmark-paper-template`; Supervisor-Skills `benchmark-paper-template` is the primary route |
| Benchmark Introduction consistency check after structure is fixed | Supervisor-Skills `intro-drafter` is consistency-check only; do not use it as the primary Benchmark paper template |
| Manuscript figure planning or result-figure design | Supervisor-Skills `figure-designer` plus local `academic-plotting` / `nature-figure-compliance` when publication figures are generated |
| Manuscript near-submission audit, AI-tone scan, grammar/LaTeX/figure review | Supervisor-Skills `pre-submission-reviewer` |
| Research-scope or idea-level reassessment before changing the Benchmark paper thesis | Supervisor-Skills `idea-evaluator` |
| Chinese academic prose, hedging, overclaim control, or reader-facing report style | `academic-chinese-style` / `nature-language-style` when relevant |
| Zotero library access or BibTeX export | `zotero:Zotero` and `citation-management`; Zotero writes remain forbidden unless the user explicitly approves |
| External literature or dataset freshness checks | use web/API verification and cite authoritative sources; keep source libraries read-only |

For broad research-to-paper or multi-stage review tasks, route through `academic-research-suite` first and then use `benchmark-paper-template` for Benchmark-paper-specific structure.

Supervisor-Skills `benchmark-paper-template is the primary route` for Benchmark manuscript structure. Supervisor-Skills `intro-drafter is consistency-check only` and must not replace the Benchmark-specific paper template.

## Current Artifact Roles

| artifact | role | boundary |
|:---|:---|:---|
| `ops/plans/updated_plan_v0.9.md` | historical current-plan baseline | planning artifact only |
| `ops/plans/updated_plan_v0.33.md` | current plan | planning artifact only |
| `ops/plans/updated_plan_v0.6.md` | historical ARS baseline | not the current plan |
| `ops/audits/license_schema_input_contract_review_v0.8.md` | readiness evidence | not download/install/run evidence |
| `benchmark/deployment/download_manifest_v0.8.csv` | future server download route | all rows must keep `download_performed=no` until approved server execution |
| `benchmark/deployment/preflight_download_approval_v0.10.csv` | future download approval table | all rows must keep `download_performed=no` and `approved_by=pending` until approved server execution |
| `benchmark/deployment/method_preflight_status_v0.10.csv` | priority method preflight state | planning-only; no clone/install/run evidence |
| `benchmark/deployment/source_clone_manifest_v0.12.csv` | external source checkout evidence | source-only clone evidence; not install/run/weight evidence |
| `benchmark/deployment/docker_image_inventory_v0.13.csv` | local Docker image reuse inventory | image assignment evidence only; not build/run evidence |
| `benchmark/deployment/method_environment_assignment_v0.13.csv` | method-to-image/environment assignment | scaffold/readiness evidence only; not installation or smoke-test evidence |
| `benchmark/deployment/run_preflight_results_v0.15.csv` | external shared-image import preflight results | import-level evidence only; not checkpoint inference or method reproducibility evidence |
| `benchmark/deployment/batch_a_smoke_test_results_v0.15.csv` | Batch A minimal smoke-test summary | minimal example execution evidence only; not target-set, scoring, performance, or benchmark-completion evidence |
| `benchmark/deployment/adapter_parser_hardening_matrix_v0.16.csv` | adapter/parser hardening matrix | interface planning only; not new execution evidence |
| `benchmark/input_sets/batch_b_target_review_queue_v0.16.csv` | Batch B target/control review queue | review queue only; not frozen target set |
| `benchmark/protocols/adapter_replay_contract_v0.16.md` | adapter replay metadata contract | future replay contract only; not a run log |
| `benchmark/input_sets/batch_b_pilot_target_gate_v0.17.csv` | Batch B pilot target gate | fixture/review gate only; not frozen target set |
| `benchmark/input_sets/batch_b_pilot_job_manifest_v0.17.csv` | Batch B pilot planned job manifest | planned fixture jobs only; not execution evidence |
| `benchmark/deployment/batch_b_pilot_method_scope_v0.17.csv` | Batch B pilot method scope | method gating only; not performance evidence |
| `benchmark/deployment/adapter_replay_fixture_manifest_v0.18.csv` | adapter replay fixture manifest | parser replay fixture only; not new method execution |
| `benchmark/results/batch_a_replay_*_v0.18.csv` | small adapter replay fixture outputs | parsed v0.15 minimal smoke fixtures only; not Benchmark results |
| `benchmark/deployment/method_source_doc_verification_v0.19.csv` | method source/doc verification summary | external readiness evidence only; not Benchmark results |
| `benchmark/deployment/method_install_smoke_manifest_v0.19.csv` | method install/example-smoke manifest | external command/log pointer summary only; raw logs and outputs stay outside KB |
| `benchmark/deployment/method_smoke_test_results_v0.19.csv` | method smoke-test result summary | method-provided example/preflight evidence only; not scoring, ranking, or full reproducibility evidence |
| `ops/audits/method_install_smoke_audit_v0.19.md` | v0.19 install/smoke audit | readiness findings and blockers only |
| `benchmark/deployment/method_unblock_manifest_v0.20.csv` | method unblock manifest | external command/log pointer summary only; raw logs and outputs stay outside KB |
| `benchmark/deployment/method_unblock_smoke_results_v0.20.csv` | method unblock result summary | external unblock/readiness evidence only; not Benchmark results |
| `ops/audits/method_unblock_audit_v0.20.md` | v0.20 unblock audit | readiness findings and blockers only |
| `benchmark/deployment/adapter_smoke_manifest_v0.21.csv` | v0.21 adapter smoke manifest | external command/log pointer summary only; raw logs and outputs stay outside KB |
| `benchmark/deployment/adapter_smoke_results_v0.21.csv` | v0.21 adapter smoke result summary | bounded external adapter/readiness evidence only; not Benchmark results |
| `benchmark/deployment/blocker_asset_manifest_v0.21.csv` | v0.21 blocker asset manifest | external asset status pointers only; weights/checkpoints stay outside KB |
| `benchmark/results/adapter_*_v0.21.csv` | v0.21 parser fixture outputs | compact parser rows only; not scoring or Benchmark results |
| `ops/audits/adapter_smoke_audit_v0.21.md` | v0.21 adapter smoke audit | readiness findings, parser boundaries and blockers only |
| `benchmark/deployment/method_example_fixture_evidence_v0.22.csv` | v0.22 evidence-to-fixture map | method-example adapter evidence only; not target-set, scoring, or performance evidence |
| `benchmark/input_sets/multi_case_fixture_*_v0.22.csv` | v0.22 target/control/job fixture manifests | fixture planning only; not frozen target set or run evidence |
| `benchmark/deployment/priority_gate_review_v0.22.csv` | v0.22 D-Flow/ColabDesign/BindCraft gate review | blocked/planning gate only; not execution evidence |
| `ops/plans/multi_case_fixture_pilot_plan_v0.22.md` | v0.22 pilot plan | planning artifact only |
| `ops/audits/multi_case_fixture_pilot_audit_v0.22.md` | v0.22 pilot audit | readiness findings and no-overclaim boundary only |
| `benchmark/deployment/notebook_cli_smoke_manifest_v0.23.csv` | project-local notebook CLI smoke summary | tooling readiness only; not method output or Benchmark evidence |
| `benchmark/deployment/dflow_project_install_contract_v0.23.csv` | D-Flow project-local install/input-contract evidence | readiness findings only; D-Flow remains input-contract blocked |
| `benchmark/deployment/external_dry_run_package_manifest_v0.23.csv` | v0.23 dry-run package index | package readiness only; large assets stay in gitignored roots |
| `benchmark/deployment/priority_gate_review_v0.23.csv` | v0.23 D-Flow/ColabDesign/BindCraft gate review | readiness gate only; not scoring or target-set evidence |
| `ops/plans/external_dry_run_package_plan_v0.23.md` | v0.23 dry-run package plan | planning/readiness artifact only |
| `ops/audits/external_dry_run_package_audit_v0.23.md` | v0.23 dry-run package audit | readiness findings and blocker record only |
| `benchmark/deployment/dflow_input_contract_fixture_v0.24.csv` | D-Flow PepDataset fixture-level LMDB load evidence | one fixture input-contract readiness only; not full PepMerge access, scoring, or smoke-test-ready evidence |
| `ops/audits/dflow_input_contract_fixture_audit_v0.24.md` | v0.24 D-Flow input-contract audit | root-cause and fixture-load evidence only; not Benchmark result |
| `benchmark/deployment/dflow_full_pepmerge_download_v0.25.csv` | D-Flow full PepMerge download/load evidence | full PepMerge input-contract readiness only; large assets stay gitignored; not scoring or smoke-test-ready evidence |
| `ops/audits/dflow_full_pepmerge_download_audit_v0.25.md` | v0.25 D-Flow full PepMerge audit | download integrity and PepDataset load evidence only; not Benchmark result |
| `benchmark/deployment/dflow_colabdesign_bindcraft_v0.26.csv` | v0.26 D-Flow/ColabDesign/BindCraft gate evidence | bounded readiness/interface evidence only; not scoring or Benchmark result |
| `benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv` | D-Flow single-entry parsed candidate row | bounded dry-run parser evidence only; not target-set or scoring evidence |
| `benchmark/results/bindcraft_wrapper_classification_v0.26.csv` | BindCraft wrapper output class row | classifier evidence only; `low_confidence_only` is not accepted final |
| `ops/audits/dflow_colabdesign_bindcraft_v0.26.md` | v0.26 gate audit | readiness findings and no-overclaim boundary only |
| `benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv` | v0.27 ColabDesign/DexDesign gate evidence | bounded gate/route-audit evidence only; not scoring or Benchmark result |
| `ops/audits/colabdesign_dexdesign_gate_v0.27.md` | v0.27 ColabDesign/DexDesign gate audit | blocker findings only; not run or ranking evidence |
| `benchmark/deployment/external_asset_rescue_v0.28.csv` | v0.28 ColabDesign/DexDesign/BindCraft asset rescue | external asset and contract evidence only; not scoring or Benchmark result |
| `benchmark/results/bindcraft_accepted_final_classification_v0.28.csv` | BindCraft accepted-final classification | wrapper classifier evidence only; not controlled multi-case output |
| `ops/audits/external_asset_rescue_audit_v0.28.md` | v0.28 external asset rescue audit | readiness findings only; not run or ranking evidence |
| `benchmark/deployment/bounded_generation_parser_v0.29.csv` | v0.29 ColabDesign/DexDesign/BindCraft bounded/parser evidence | single-case or parser-fixture evidence only; not controlled multi-case output |
| `benchmark/results/colabdesign_bounded_*_v0.29.csv` | ColabDesign one-case bounded GPU generation parser rows | ultra-smoke evidence only; raw PDB stays gitignored; not scoring or method ranking |
| `benchmark/results/bindcraft_accepted_candidate_outputs_v0.29.csv` | BindCraft accepted-final standard candidate parser fixture | external CD47 parser fixture only; not controlled benchmark output |
| `ops/audits/bounded_generation_parser_audit_v0.29.md` | v0.29 bounded generation/parser audit | readiness findings only; not Benchmark result |
| `benchmark/input_sets/pilot_benchmark_target_manifest_v0.30.csv` | v0.30 pilot target fixture manifest | controlled pilot input design only; not frozen target set |
| `benchmark/input_sets/pilot_benchmark_control_manifest_v0.30.csv` | v0.30 pilot control manifest | parser/control governance only; not biological validation |
| `benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv` | v0.30 pilot job manifest | planned Wave A/Wave B jobs only; not execution evidence |
| `benchmark/deployment/pilot_execution_matrix_v0.30.csv` | v0.30 runner/environment matrix | planned execution routing only; output roots stay gitignored |
| `benchmark/input_sets/wet_lab_candidate_panel_v0.30.csv` | v0.30 prospective wet-lab candidate panel | planning-only; not synthesis, assay, or wet-lab validation evidence |
| `ops/audits/pilot_benchmark_design_audit_v0.30.md` | v0.30 pilot design audit | target/control/job planning boundary only; not Benchmark result |
| `benchmark/deployment/pilot_execution_results_v0.31.csv` | v0.31 bounded Wave A execution summary | bounded pilot/parser evidence only; not scoring or Benchmark result |
| `benchmark/results/pilot_*_v0.31.*` | v0.31 merged method/candidate/run parser rows | compact parser rows only; raw outputs stay gitignored; not method ranking |
| `ops/audits/pilot_wave_a_execution_audit_v0.31.md` | v0.31 Wave A execution audit | bounded execution/parser boundary only; not Benchmark result |
| `ops/audits/supervisor_skills_installation_v0.32.md` | Supervisor-Skills installation and memory record | writing-skill routing evidence only; not Benchmark result |
| `benchmark/deployment/pilot_execution_results_v0.33.csv` | v0.33 Wave A adapter/parser completion attempt summary | method-specific no-supported-output blocker evidence only; not scoring or Benchmark result |
| `benchmark/results/pilot_*_v0.33.*` | v0.33 merged method/candidate/run adapter-parser rows | compact failed rows only; raw outputs stay gitignored; not method ranking |
| `ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md` | v0.33 Wave A adapter/parser completion audit | blocker findings only; not generation success or Benchmark result |
| `ops/audits/skill_selection.md` | active skill-routing memory | includes HKUSTDial/Supervisor-Skills commit/license notes; not scoring evidence |
| `ops/plans/protein_design_image_consolidation_plan_v0.13.md` | image consolidation plan | planning artifact only |
| `ops/plans/adapter_parser_hardening_plan_v0.16.md` | adapter/parser hardening plan | planning artifact only |
| `ops/audits/docker_environment_assignment_audit_v0.13.md` | Docker/environment assignment audit | readiness finding only; not local reproducibility evidence |
| `ops/audits/batch_a_execution_audit_v0.15.md` | external preflight and Batch A execution audit | small evidence summary only; large logs, caches and generated structures stay outside the KB |
| `benchmark/method_sources/method_paper_case_matrix_v0.14.csv` | method-paper case matrix | literature case evidence only; not target freeze or run evidence |
| `benchmark/input_sets/target_candidate_academic_search_v0.14.csv` | academic-search target candidate matrix | candidate/panel planning only; not frozen target set |
| `ops/plans/target_candidate_academic_search_plan_v0.14.md` | target academic-search plan | planning artifact only |
| `ops/audits/target_candidate_academic_search_audit_v0.14.md` | target academic-search audit | metadata-level evidence only; no data download |
| `benchmark/deployment/method_readiness_review_v0.8.csv` | method license/env/checkpoint/input-contract audit | not local reproducibility evidence |
| `benchmark/method_sources/method_landscape_watchlist_v0.9.csv` | method landscape and Related Work coverage | not an include scorecard or source pin audit |
| `benchmark/input_sets/target_set_v0.csv` | frozen target interface | remains schema-only until controls, assay, license, leakage, and provenance are complete |
| `benchmark/input_sets/target_control_freeze_checklist_v0.10.md` | target/control freeze gate | checklist only; not target promotion |
| `benchmark/input_sets/example_run.csv` | artificial input-contract example | rows must remain `status=not_real_benchmark` |
| `manuscript/support/benchmark_manuscript_claim_evidence_map.csv` | claim gate | unsupported claims must stay unsupported |
| `ops/validation/wiki_validation_report.md` | latest machine validation result | regenerate through validator, do not hand-edit counts |

## Execution Gates

Method and dataset readiness must move through explicit gates:

1. `metadata_ready`
2. `source_pinned`
3. `license_checked`
4. `weights_manifested`
5. `input_contract_ready`
6. `dry_run_ready`
7. `smoke_test_ready`

Current v0.15-v0.33 KB artifacts support only `minimal_smoke_observed`, interface-planning, pilot-gate, parser-replay fixture, method-provided example/preflight readiness evidence, method-unblock findings, bounded adapter-smoke evidence, parser fixture rows for selected external examples, multi-case fixture pilot planning, v0.23 dry-run package readiness findings, one D-Flow fixture-level PepDataset LMDB load test, D-Flow full PepMerge download/load readiness, one bounded D-Flow dry-run, one ColabDesign CLI adapter package, one BindCraft wrapper classification, a ColabDesign bounded execute asset gate, a DexDesign route audit, v0.28 external asset rescue findings, one ColabDesign single-case bounded GPU generation parser row, one DexDesign synthetic D-L input-contract fixture, one BindCraft external accepted-final standard candidate parser fixture, v0.30 controlled pilot target/control/job planning, v0.31 bounded Wave A pilot/parser rows, and v0.33 method-specific no-supported-output adapter/parser blocker rows. They do not support promotion to `smoke_test_ready` or `benchmark_ready` without controlled execution records, standardized multi-case outputs, scoring artifacts, validation artifacts, and target/control governance.

## Language And Claim Rules

- Reader-facing prose is Chinese by default.
- Preserve English method names, software commands, paper titles, Zotero item keys, BibTeX keys, URLs, model names, and dataset names.
- Prefer `提示`, `支持`, `表明`, `拟评估`, `仍需验证`, `metadata-level`, and `readiness findings`.
- Do not write that a method is installed, reproduced, runnable, benchmark-completed, problem-free, best-performing, or experimentally validated unless a later phase records environment, commit, command, input, output, runtime, logs, parser result, and validation artifacts.
- Do not treat source pinning, source checkouts, method contracts, availability checks, download manifests, or schema reviews as installation, smoke-test, Benchmark-result, or local-reproducibility evidence.
- Do not treat v0.15 minimal smoke tests as complete benchmark runs, target-set evidence, scoring evidence, performance ranking, or proof that broader method environments are problem-free.
- Do not treat v0.16 adapter/parser hardening or Batch B target review queue rows as new run evidence, frozen targets, scoring evidence, or performance findings.
- Do not treat v0.17 pilot gates as frozen targets, completed runs, or head-to-head evidence.
- Do not treat v0.18 replay fixtures as new execution, scoring results, method ranking, or Benchmark results.
- Do not treat v0.20 method-unblock rows as target-set evidence, scoring evidence, method ranking, or Benchmark results.
- Do not treat v0.21 adapter-smoke or parser rows as target-set evidence, scoring evidence, method ranking, full reproducibility evidence, or Benchmark results.
- Do not treat v0.22 multi-case fixture target/control/job manifests or priority gates as frozen target-set evidence, execution evidence, scoring evidence, method ranking, full reproducibility evidence, or Benchmark results.
- Do not treat v0.23 notebook CLI tooling or D-Flow project-local install/import evidence as target-set evidence, scoring evidence, method ranking, full reproducibility evidence, or Benchmark results.
- Do not treat v0.24 D-Flow fixture-level LMDB load evidence as full PepMerge dataset access, scoring evidence, method ranking, `smoke_test_ready`, or complete Benchmark evidence.
- Do not treat v0.25 D-Flow full PepMerge download/load evidence as a generation run, target-set evidence, scoring evidence, method ranking, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat v0.26 D-Flow bounded dry-run, ColabDesign CLI adapter package, or BindCraft wrapper classification as frozen target-set evidence, scoring evidence, method ranking, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat v0.27 ColabDesign asset-gate or DexDesign route-audit rows as generation evidence, scoring evidence, method ranking, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat v0.28 external asset rescue, ColabDesign asset gate readiness, DexDesign input-contract extraction, or BindCraft accepted-final external output classification as controlled multi-case Benchmark evidence, scoring evidence, method ranking, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat v0.29 ColabDesign single-case bounded GPU output, DexDesign synthetic prepared D-L fixture, or BindCraft external accepted candidate parser rows as controlled multi-case Benchmark evidence, scoring evidence, method ranking, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat v0.30 pilot target/control/job manifests, execution matrix, or prospective wet-lab panel as execution evidence, scoring evidence, frozen target-set evidence, method ranking, wet-lab validation, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat v0.31 bounded Wave A execution/parser rows as scoring evidence, method-ranking evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat v0.33 adapter/parser completion rows as generated candidates, scoring evidence, method-ranking evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence.
- Do not treat Supervisor-Skills idea, benchmark, figure, or submission-review guidance as Benchmark execution, scoring evidence, method-ranking evidence, or biological validation evidence.
- Do not treat watchlist datasets, target candidates, review-only methods, or literature examples as frozen Benchmark targets.
- Generation ability, ranking/rescoring ability, developability proxies, structural confidence, and biological validation are separate evidence layers.

## Update Order

1. Inspect `index.md`, `ops/plans/updated_plan_v0.33.md`, and `ops/validation/wiki_validation_report.md`.
2. Refresh source metadata only when the user requests it or the task depends on current external state.
3. Update `kb/references/` and `kb/tables/` before regenerating wiki, manuscript, or ops artifacts.
4. Regenerate or update `kb/wiki/` cards and `_index.md` files when source tables change.
5. Update `benchmark/` protocol, input-set, deployment, method-source, scoring, or availability artifacts.
6. Update `manuscript/`, `ops/`, `index.md`, `README.md`, `RELEASE_NOTES.md`, and append `ops/log.md`.
7. Run validation before claiming completion:

```powershell
$env:PYTHONUTF8='1'
python scripts/validate_benchmark_kb.py
git diff --check
git status -sb
```

## Validation Rules

- Windows commands that read or write Chinese text should set `PYTHONUTF8=1`.
- `scripts/validate_benchmark_kb.py` is the project validator and must pass with 0 errors and 0 warnings before a release-style update is considered complete.
- `ops/validation/wiki_validation_report.md` is generated by the validator.
- `git diff --check` may report CRLF-to-LF normalization warnings; whitespace errors still need fixing.
- If validator and documentation disagree, update the source artifact or validator expectation, then rerun validation.

## Git And Safety

- The worktree may contain staged or unstaged protocol/manuscript artifacts from v0.6-v1.2. Do not revert unrelated user or prior-agent changes.
- Do not run destructive commands such as `git reset --hard` or `git checkout --` unless explicitly requested.
- Do not commit or push unless the user asks.
- Keep edits scoped to the requested phase and maintain source-library boundaries.
