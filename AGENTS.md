# Pep Design Benchmark KB Agent Rules

## Purpose

This project is an independent protocol-first Benchmark knowledge base for recent peptide-design methods. It supports literature evidence management, method and dataset readiness audits, Benchmark manuscript planning, and later server-side smoke-test preparation.

Current authoritative plan: `ops/plans/updated_plan_v0.9.md`.

Current version: `1.2.10`.

Next planned phase: v0.23 approved external dry-run package preparation after v0.22 multi-case fixture pilot planning. Do not start additional clone, download, install, or GPU execution unless the user explicitly requests that later phase.

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
| Benchmark manuscript structure, Introduction logic, five-pillar audit, section skeleton, pre-submission checklist | `benchmark-paper-template` |
| Chinese academic prose, hedging, overclaim control, or reader-facing report style | `academic-chinese-style` / `nature-language-style` when relevant |
| Zotero library access or BibTeX export | `zotero:Zotero` and `citation-management`; Zotero writes remain forbidden unless the user explicitly approves |
| External literature or dataset freshness checks | use web/API verification and cite authoritative sources; keep source libraries read-only |

For broad research-to-paper or multi-stage review tasks, route through `academic-research-suite` first and then use `benchmark-paper-template` for Benchmark-paper-specific structure.

## Current Artifact Roles

| artifact | role | boundary |
|:---|:---|:---|
| `ops/plans/updated_plan_v0.9.md` | current plan | planning artifact only |
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

Current v0.15-v0.22 KB artifacts support only `minimal_smoke_observed`, interface-planning, pilot-gate, parser-replay fixture, method-provided example/preflight readiness evidence, method-unblock findings, bounded adapter-smoke evidence, parser fixture rows for selected external examples, and multi-case fixture pilot planning. They do not support promotion to `smoke_test_ready` or `benchmark_ready` without controlled target governance, standardized inputs, adapter commands, multi-seed outputs, scoring artifacts, validation artifacts, and target/control governance. PepMirror and PepGLAD have v0.21 checkpoint/weight unblock evidence; D-Flow remains input-contract blocked by the missing PepMerge cache.

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
- Do not treat watchlist datasets, target candidates, review-only methods, or literature examples as frozen Benchmark targets.
- Generation ability, ranking/rescoring ability, developability proxies, structural confidence, and biological validation are separate evidence layers.

## Update Order

1. Inspect `index.md`, `ops/plans/updated_plan_v0.9.md`, and `ops/validation/wiki_validation_report.md`.
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
