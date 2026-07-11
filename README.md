# Pep Design Benchmark Knowledge Base

This repository hosts a peptide-design method knowledge base and a protocol-first benchmark design layer.

Release `1.2.21` packages a repository checkpoint for the protocol, manuscript, preflight control, minimal execution-evidence, adapter/parser planning, pilot-gate, parser-replay fixture, external method install/example-smoke readiness, v0.20 method-unblock readiness, v0.21 adapter-smoke/parser-fixture readiness, v0.22 controlled multi-case fixture pilot planning, v0.23 external dry-run package readiness, v0.24 D-Flow fixture-level input-contract readiness, v0.25 D-Flow full PepMerge download/load readiness, v0.26 D-Flow/ColabDesign/BindCraft gate-update layer, v0.27 ColabDesign/DexDesign gate layer, v0.28 external asset rescue layer, v0.29 bounded generation/parser layer, v0.30 pilot benchmark design layer, v0.31 bounded Wave A pilot execution/parser layer, v0.32 Supervisor-Skills installation/memory layer, and v0.33 Wave A adapter/parser completion attempt layer rather than benchmark results. It includes claim gates, source/code/image readiness audits, target/control schema design, scoring protocol design, manuscript support artifacts, external source checkouts kept outside the KB, observed Docker image inventory under `/mnt/ssd4t/protein-design`, small execution summaries from `/data/protein-design`, v0.18 replay parser artifacts, v0.19/v0.20 method runtime summaries, v0.21 bounded adapter smoke plus parser fixture summaries, v0.22 standardized target/control/job/gate manifests, v0.23 notebook CLI plus project-local D-Flow readiness evidence, a v0.24 D-Flow PepDataset LMDB fixture load test, v0.25 verified PepMerge archive/LMDB load evidence, v0.26 bounded D-Flow dry-run plus ColabDesign/BindCraft adapter evidence, v0.27 ColabDesign asset-gate plus DexDesign route-audit evidence, v0.28 ColabDesign AF parameter/target rescue, DexDesign input-contract extraction, BindCraft accepted-final classification, v0.29 ColabDesign one-case bounded generation/parser plus DexDesign/BindCraft parser-contract fixtures, v0.30 controlled pilot target/control/job manifests plus a prospective wet-lab panel, v0.31 compact Wave A execution/candidate/run parser tables, v0.32 Supervisor-Skills routing memory, and v0.33 compact adapter/parser blocker rows for the 10 v0.31 placeholder-failed jobs.

## Acceptance Harness

Project acceptance is governed by [`harness/contracts/project_acceptance_v1.json`](harness/contracts/project_acceptance_v1.json). The generated reader view is [`harness/PROJECT_ACCEPTANCE.md`](harness/PROJECT_ACCEPTANCE.md), the current machine/human reports are under [`ops/acceptance/`](ops/acceptance/), and the implementation plan is [`ops/plans/harness_engineering_plan_v1.0.md`](ops/plans/harness_engineering_plan_v1.0.md).

Run read-only preflight with `python scripts/run_project_acceptance.py check --profile current_phase`. The unsigned harness checkpoint does not change the v0.33 evidence boundary and does not promote `VERSION` beyond `1.2.21`.

### 对话内签核

运行 `prepare-review` 和展示审批卡前，必须停止全部 subagents 并确认其 quiescent。Agent 只能在当前受信任 Codex 会话中先展示一张未过期审批卡，再接受一条经 Unicode NFC 规范化并 trim 首尾空白后完整内容恰好为 `批准` 的回复；这是一项会话授权，不是 cryptographic identity。卡片展示后任何介入的非精确 `批准` 用户消息都会使卡失效，必须重新 prepare 并展示新卡。固定审批 bundle 同时覆盖 `governance` 与 `current_phase`，但会生成两份独立的 profile-bound `governance_owner` signoff，不能 waiver Critical/Major failure，也不批准 `release_checkpoint` 或 `full_project`。

批准后仅在 source manifest 非空时于当前 `main` 创建 source checkpoint；manifest 记录 Git clean 后实际进入 commit 的 blob SHA-256，空 manifest 复用卡片 HEAD，随后只创建一个 signoff commit。Transport、staging、history 与 clean-checkout materialization 均在受控 Git 配置/隔离 gitdir 中执行；重验后以显式 refspec、真实 ancestry 检查和 card-bound expected-old-OID lease 对 `git@github.com:luvega/pep-design.git` 的 `refs/heads/main` 执行 fast-forward push。该 lease 不授权 non-fast-forward 或无条件 force-push。Generated report、审批卡和 journal 是 non-evidence 控制面状态；production signoff 只有作为 `harness/signoffs/` 下 committed、clean、非 symlink 的直接 regular file 才有效。

Durable `local_committed_push_failed` 或 `verified` 只通过 `resume-push --card-id <card_id>` 恢复。已有 final OID 时直接复用且不重复 commits/signoffs；只有 source OID 时在该 source 的临时 clean checkout 中重验，再创建或复用缺失 signoff，并至多新建一个 signoff commit，且不重复 source。若失败点已留下 staged signoff，恢复只接受与卡片派生 manifest 在路径、mode 和 blob SHA-256 上完全一致的 index；任何 extra/different staged 状态均 fail closed。`verified` 可在 remote 已是 final OID 时协调不明确但实际成功的 push，仅推进 journal 而不再次 push。

该简化流程由不同 subagents 分别承担设计、测试、编码、文档与独立复审。它没有授权 clone、install、download、GPU generation、scoring 或 ranking；v0.33 仍为 10 条 blocker rows 和 0 parsed/generated candidates，`VERSION` 继续保持 `1.2.21`，直至实际 digest 获得 governance approval 后才可准备后续 release candidate。

## Current Version

- Version: `1.2.21`
- Manuscript outline layer: `v1.0`
- Supplementary-source synthesis layer: `v1.1`
- Chinese manuscript figure/table embedding layer: `v1.2`
- Grant-style mock review layer: `v1.3` planning supplement
- Source/I/O/smoke-test interface layer: `v0.11` planning supplement
- Source-code clone audit layer: `v0.12` external checkout supplement
- Docker image/environment assignment layer: `v0.13` workbench scaffold supplement
- Academic-search target/case planning layer: `v0.14` candidate supplement
- Run preflight and Batch A evidence layer: `v0.15` external minimal smoke supplement
- Adapter/parser hardening layer: `v0.16` planning supplement
- Batch B pilot gate layer: `v0.17` planning supplement
- Adapter replay fixture layer: `v0.18` parser supplement
- Method install/example smoke layer: `v0.19` external readiness supplement
- Method unblock layer: `v0.20` external readiness supplement
- Adapter smoke/parser fixture layer: `v0.21` external readiness supplement
- Multi-case fixture pilot planning layer: `v0.22` planning supplement
- External dry-run package readiness layer: `v0.23` project-local readiness supplement
- D-Flow input-contract fixture layer: `v0.24` project-local readiness supplement
- D-Flow full PepMerge download/load layer: `v0.25` project-local readiness supplement
- D-Flow/ColabDesign/BindCraft gate update layer: `v0.26` project-local readiness supplement
- ColabDesign/DexDesign gate layer: `v0.27` project-local readiness supplement
- External asset rescue layer: `v0.28` project-local readiness supplement
- Bounded generation/parser layer: `v0.29` project-local readiness supplement
- Pilot benchmark design layer: `v0.30` planning supplement
- Bounded Wave A pilot execution/parser layer: `v0.31` project-local bounded evidence supplement
- Supervisor-Skills installation/memory layer: `v0.32` manuscript-support supplement
- Wave A adapter/parser completion attempt layer: `v0.33` project-local bounded blocker supplement
- Repository checkpoint: `v1.2.21`
- Evidence/release checkpoint build date: 2026-07-09（当前对话 harness workflow 更新于 2026-07-10）
- Literature window: 2021-06-03 to 2026-06-03
- Included first-wave candidate methods: 10
- Watchlist methods: 2

## What Is Included

- `kb/references/`: BibTeX export, Zotero-to-BibTeX key map, search log, dedupe report.
- `kb/tables/`: master literature manifest, method evidence matrix, candidate method scorecard, expert review action items, v1.0 candidate method classification, v1.1 supplementary-material action matrix, scoring rationale matrix, method-landscape patch candidates, and v1.3 grant review action items.
- `kb/wiki/`: literature cards, method cards, concept pages, benchmark candidate pages.
- `benchmark/`: protocol, run.csv schema, target/control schema, scoring schema, dataset readiness scorecard, target candidate matrix, v1.0 reference dataset sources, method source routes, source pin audits, availability audits, server readiness checklist, server smoke-test contract, method contracts, artificial example run table, download manifest template, environment feasibility matrix, and smoke-test planning layer.
- v0.11 adds `job_manifest.csv` and adapter-output schemas plus artificial Batch A example manifests for PepMLM and RFdiffusion + ProteinMPNN.
- v0.12 adds `benchmark/deployment/source_clone_manifest_v0.12.csv` and `ops/audits/source_code_clone_audit_v0.12.md` to record external source checkouts for 11 first-wave method repositories.
- v0.13 adds Docker image inventory and method-environment assignment manifests for reusing existing `/mnt/ssd4t/protein-design` images and defining a shared multi-conda benchmark image scaffold.
- v0.14 adds method-paper case and academic-search target candidate matrices for NCAM1, AMHR2, DiffPepBuilder PDB cases, pMHC, PepBench/LNR, PepMerge, PEPBI, GPCR and Chang ranking sources.
- v0.15 adds import-level shared-image preflight results and three external minimal Batch A smoke-test summaries for PepMLM, ProteinMPNN and RFpeptide/RFdiffusion.
- v0.16 adds adapter/parser hardening and Batch B target-control review planning through an adapter matrix, replay contract and target review queue.
- v0.17 adds controlled Batch B pilot target gates, method scope and planned fixture job manifest without target-set promotion.
- v0.18 adds a parser replay script and three small replay fixture result tables parsed from v0.15 Batch A outputs.
- v0.19 adds source/doc verification, install smoke manifests and method smoke-test result summaries for the 10 first-wave methods using external `/data/protein-design` workbench logs.
- v0.20 adds method-unblock manifests and result summaries for the 10 first-wave methods, including an independent PyRosetta image route and unresolved blockers.
- v0.21 adds adapter-smoke manifests, blocker asset status, parser output manifests, candidate rows and run rows for the 10 first-wave methods using bounded external workbench examples.
- v0.22 converts v0.21 method-example adapter evidence into focused multi-case fixture target/control/job manifests and priority gate reviews for D-Flow, ColabDesign and BindCraft without execution or scoring.
- v0.23 records project-local notebook CLI tooling, D-Flow source/env/weight/import readiness evidence, and updated dry-run gates while keeping PepMerge/LMDB unresolved.
- v0.24 adds a D-Flow PepMerge-style fixture builder and records a passing `PepDataset(reset=False)` LMDB load test for one 3EQS fixture.
- v0.25 records verified full PepMerge archive download, extraction, official LMDB extraction and `PepDataset(reset=False)` loading for D-Flow train/test splits while keeping all large assets gitignored.
- v0.26 records one bounded D-Flow dry-run, a standard ColabDesign job-row CLI adapter package and a BindCraft accepted-final classifier while keeping runtime outputs gitignored.
- v0.27 records a ColabDesign bounded execute asset gate and a DexDesign D-peptide/L-protein route audit while keeping outputs gitignored.
- v0.28 records ColabDesign AF parameter/target PDB route discovery, DexDesign input-contract extraction and BindCraft accepted-final classification from external outputs while keeping runtime outputs gitignored.
- v0.29 records one ColabDesign bounded GPU generation/parser row, a DexDesign synthetic prepared D-L input-contract fixture and a BindCraft accepted-final standard candidate parser fixture while keeping raw PDB outputs and logs gitignored.
- v0.30 records controlled pilot target/control/job manifests, an execution matrix for Wave A/Wave B/blocked lanes, and a prospective wet-lab candidate panel while keeping `target_set_v0.csv` empty and runtime outputs gitignored.
- v0.31 records bounded Wave A pilot execution/parser summaries for 14 Wave A jobs, with 4 parsed/generated rows and 10 placeholder-failed adapter rows, while keeping raw outputs and generated PDB files gitignored.
- v0.32 records installation and project-memory routing for selected Supervisor-Skills manuscript-support skills while preserving the boundary that these skills are not Benchmark-result or scoring evidence.
- v0.33 records method-specific adapter/parser completion attempts for the 10 v0.31 placeholder-failed Wave A jobs, with 10 no-supported-output blocker rows and no generated candidates.
- `sources/raw_snapshots/`: read-only local snapshots copied into the project for provenance.
- `manuscript/`: Benchmark outlines, claim map, figure/table plan, bibliography planning, manuscript figures, and manuscript-facing support reports.
- `ops/`: current and historical plans, audits, validation report, build summary, migration records, and project log.
- `scripts/`: reproducible build and validation scripts.

## Current Directory Architecture

- `sources/raw_snapshots/`: read-only source snapshots only.
- `kb/`: generated references, structured tables, and wiki cards.
- `benchmark/`: protocol, schemas, input-set governance, method-source readiness, deployment manifests, and smoke-test planning interfaces.
- `manuscript/`: paper outlines, figures, claim gates, citation planning, and manuscript-facing support.
- `ops/`: plans, audits, migration records, validation outputs, build summaries, and the project log.

v0.10/v0.11 preflight planning adds approval/status/source-freshness/adapter files for future server execution, v0.12 records source-only external checkouts, v0.13 records Docker image/environment assignment, v0.14 records academic-search target/case candidates, v0.15 records small external preflight/smoke-test summaries, v0.16 records adapter/parser plus target-control review planning, v0.17 records pilot gates, v0.18 records parser replay fixtures, v0.19 records external method install/example-smoke readiness summaries, v0.20 records method-unblock readiness summaries, v0.21 records bounded adapter-smoke/parser fixture summaries, v0.22 records controlled multi-case fixture pilot planning, v0.23 records external dry-run package readiness, v0.24 records D-Flow fixture-level LMDB input-contract readiness, v0.25 records D-Flow full PepMerge download/load readiness, v0.26 records D-Flow/ColabDesign/BindCraft gate updates, v0.27 records ColabDesign/DexDesign gate updates, v0.28 records external asset rescue updates, v0.29 records bounded generation/parser-contract updates, v0.30 records controlled pilot input/job planning, v0.31 records bounded Wave A execution/parser summaries, v0.32 records Supervisor-Skills manuscript-support memory, and v0.33 records method-specific no-supported-output adapter/parser blockers for the v0.31 placeholder-failed jobs. Model weights, datasets, installations, built image layers, raw logs, generated structures, GPU outputs and large run artifacts remain outside tracked KB files.

## First-Wave Candidate Methods

The `include` set is:

- PepMLM
- SaLT&PepPr
- DiffPepBuilder
- PepGLAD
- D-Flow / PeptideDesign
- PepMirror
- AfCycDesign / ColabDesign cyclic peptide
- DexDesign / OSPREY3
- RFdiffusion + ProteinMPNN
- BindCraft

PepFlow and BoltzDesign1 are retained as watchlist methods until their executable route, checkpoint use, and peptide/miniprotein task fit are confirmed.

## Rebuild And Validate

Run from the repository root on Windows PowerShell:

```powershell
$env:PYTHONUTF8='1'
python scripts/build_benchmark_kb.py
python scripts/validate_benchmark_kb.py
```

Expected validation for the current working layer covers the v0.33 current plan, v1.0 manuscript-outline layer, v1.1 supplementary-source synthesis layer, v1.2 Chinese manuscript figure/table embedding layer, v1.3 grant-style mock review planning layer, v0.11 source/I-O/smoke-test interface planning layer, v0.13 image/environment assignment layer, v0.14 academic-search target/case planning layer, v0.15 external preflight plus Batch A minimal smoke-test evidence layer, v0.16 adapter/parser hardening plus Batch B target review planning layer, v0.17 pilot gate layer, v0.18 adapter replay fixture layer, v0.19 external method install/example-smoke readiness layer, v0.20 external method-unblock readiness layer, v0.21 external adapter-smoke/parser fixture layer, v0.22 multi-case fixture pilot planning layer, v0.23 external dry-run package readiness layer, v0.24 D-Flow input-contract fixture layer, v0.25 D-Flow full PepMerge download/load layer, v0.26 D-Flow/ColabDesign/BindCraft gate-update layer, v0.27 ColabDesign/DexDesign gate layer, v0.28 external asset rescue layer, v0.29 bounded generation/parser layer, v0.30 pilot benchmark design layer, v0.31 bounded Wave A execution/parser layer, and v0.33 adapter/parser completion attempt layer:

- `status`: `pass`
- `master_rows`: 432
- `included_methods`: 10
- `runnability_rows`: 10
- `benchmark_literature_rows`: 8
- `candidate_dataset_rows`: 7
- `method_source_rows`: 10
- `environment_rows`: 10
- `expert_review_rows`: 15
- `dataset_readiness_rows`: 7
- `target_candidate_rows`: 9
- `target_candidate_v05_rows`: 9
- `source_pin_rows`: 4
- `source_pin_v05_rows`: 10
- `link_availability_rows`: 23
- `data_access_rows`: 7
- `ars_review_action_rows`: 11
- `dataset_watchlist_v06_rows`: 6
- `example_run_rows`: 2
- `download_manifest_rows`: 1
- `dataset_schema_review_v07_rows`: 6
- `dataset_schema_review_v08_rows`: 6
- `download_manifest_v08_rows`: 8
- `preflight_download_v010_rows`: 8
- `source_freshness_v011_rows`: 4
- `method_readiness_v08_rows`: 4
- `method_preflight_v010_rows`: 3
- `adapter_preflight_v011_rows`: 3
- `source_clone_v012_rows`: 11
- `docker_image_inventory_v013_rows`: 8
- `method_environment_assignment_v013_rows`: 10
- `method_paper_case_v014_rows`: 13
- `target_academic_search_v014_rows`: 16
- `run_preflight_v015_rows`: 5
- `batch_a_smoke_test_v015_rows`: 3
- `adapter_parser_hardening_v016_rows`: 8
- `batch_b_target_review_v016_rows`: 6
- `batch_b_pilot_target_gate_v017_rows`: 4
- `batch_b_pilot_method_scope_v017_rows`: 8
- `batch_b_pilot_job_manifest_v017_rows`: 5
- `adapter_replay_fixture_v018_rows`: 3
- `batch_a_replay_method_output_v018_rows`: 3
- `batch_a_replay_candidate_v018_rows`: 3
- `batch_a_replay_run_v018_rows`: 3
- `method_source_doc_v019_rows`: 10
- `method_install_smoke_manifest_v019_rows`: 10
- `method_smoke_test_v019_rows`: 10
- `method_unblock_manifest_v020_rows`: 10
- `method_unblock_smoke_v020_rows`: 10
- `adapter_smoke_manifest_v021_rows`: 10
- `adapter_smoke_results_v021_rows`: 10
- `blocker_asset_manifest_v021_rows`: 4
- `adapter_method_output_v021_rows`: 10
- `adapter_candidate_output_v021_rows`: 6
- `adapter_run_rows_v021_rows`: 6
- `dflow_bounded_candidate_v026_rows`: 1
- `bindcraft_classification_v026_rows`: 1
- `bindcraft_accepted_final_v028_rows`: 1
- `method_example_fixture_v022_rows`: 10
- `multi_case_fixture_target_v022_rows`: 5
- `multi_case_fixture_control_v022_rows`: 7
- `multi_case_fixture_job_v022_rows`: 8
- `priority_gate_review_v022_rows`: 4
- `notebook_cli_smoke_v023_rows`: 1
- `dflow_project_install_v023_rows`: 1
- `external_dry_run_package_v023_rows`: 5
- `priority_gate_review_v023_rows`: 5
- `dflow_input_contract_fixture_v024_rows`: 1
- `dflow_full_pepmerge_download_v025_rows`: 1
- `dflow_colab_bindcraft_v026_rows`: 3
- `colabdesign_dexdesign_gate_v027_rows`: 2
- `external_asset_rescue_v028_rows`: 3
- `bounded_generation_parser_v029_rows`: 3
- `pilot_benchmark_target_v030_rows`: 7
- `pilot_benchmark_control_v030_rows`: 8
- `pilot_benchmark_job_v030_rows`: 17
- `pilot_execution_matrix_v030_rows`: 17
- `wet_lab_candidate_panel_v030_rows`: 4
- `pilot_execution_results_v031_rows`: 14
- `pilot_method_output_v031_rows`: 14
- `pilot_candidate_output_v031_rows`: 14
- `pilot_run_v031_rows`: 14
- `supervisor_skills_installation_v032_files`: 1
- `pilot_execution_results_v033_rows`: 10
- `pilot_method_output_v033_rows`: 10
- `pilot_candidate_output_v033_rows`: 10
- `pilot_run_v033_rows`: 10
- `example_job_manifest_v011_rows`: 2
- `method_output_manifest_v011_rows`: 2
- `candidate_output_v011_rows`: 2
- `method_landscape_v09_rows`: 27
- `bilingual_sync_rows`: 19
- `method_classification_v1_rows`: 27
- `reference_dataset_sources_v1_rows`: 8
- `manuscript_todo_v1_rows`: 18
- `manuscript_claim_rows`: 73
- `supplementary_material_rows`: 6
- `scoring_rationale_rows`: 10
- `method_landscape_patch_v11_rows`: 8
- `grant_review_action_v13_rows`: 12
- `migration_v010_rows`: 23
- `smoke_test_readmes`: 10
- `method_cards`: 12
- `literature_cards`: 120
- `bibtex_entries`: 432
- `markdown_links_checked`: 219
- `tracked_files_checked`: 463

## Source Boundary

This repository is the working project layer. Zotero, EndNote, and the prior PD-wiki remain upstream source systems. The files under `sources/raw_snapshots/` are local project snapshots used for provenance and should be treated as read-only.

This release excludes model weights, downloaded PDFs, EndNote libraries, third-party source trees, large datasets and raw benchmark execution outputs. v0.5 source pinning and data availability checks are metadata-only snapshots. v1.1 supplementary-source synthesis provides source discovery and framing, not primary-source verified evidence or runnability evidence. v1.2 manuscript figures and embedded Markdown tables are planning/reporting artifacts, not benchmark results. v1.3 grant-style mock review is a simulated review and preflight-planning layer, not a funding decision, execution record, code-quality confirmation, or local reproducibility claim. v0.12 source-code clone evidence records external Git checkouts only; it is not installation, environment validation, smoke-test execution, model-weight download, or local reproducibility evidence. v0.13 image/environment assignment records observed existing images and a workbench Dockerfile scaffold; it is not by itself proof that a method is runnable. v0.14 academic-search target/case matrices record literature-derived candidates only; they are not target-set promotion, data-download, assay validation, leakage clearance, or Benchmark performance evidence. v0.15 records one external shared-image import preflight layer and three minimal smoke tests only; it is not complete Benchmark evidence, target-set evidence, scoring evidence, or method-performance evidence. v0.16 records adapter/parser hardening and Batch B target review planning only; it is not a new run, target freeze, scoring result, or performance finding. v0.17 records pilot gates only; it does not freeze `target_set_v0.csv` or execute jobs. v0.18 records parser replay fixtures from v0.15 outputs only; it is not new method execution, scoring evidence or Benchmark results. v0.19 records external method install/example-smoke readiness summaries only; it is not head-to-head Benchmark evidence, scoring evidence, method-ranking evidence, or proof that every method is free of unresolved issues. v0.20 records external method-unblock readiness summaries only; it is not target-set evidence, scoring evidence, method-ranking evidence, or proof that every blocker is resolved. v0.21 records bounded adapter smoke and parser fixture rows only; it is not target-set evidence, scoring evidence, method-ranking evidence, complete reproducibility evidence, or proof that every blocker is resolved. v0.22 records multi-case fixture pilot target/control/job manifests and priority gates only; it is not frozen target-set evidence, execution evidence, scoring evidence, method-ranking evidence, or proof that D-Flow, ColabDesign or BindCraft gates are resolved. v0.23 records project-local notebook CLI and D-Flow readiness findings only; it is not target-set evidence, scoring evidence, method-ranking evidence, complete reproducibility evidence, or proof that ColabDesign or BindCraft gates are resolved. v0.24 records one D-Flow fixture-level PepDataset LMDB load test only; it is not scoring evidence, method-ranking evidence, complete reproducibility evidence, or `smoke_test_ready` promotion. v0.25 records D-Flow full PepMerge download and official LMDB load evidence only; it is not a generation run, target-set evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.26 records one D-Flow bounded dry-run, one ColabDesign CLI adapter package and one BindCraft wrapper classification only; it is not frozen target-set evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.27 records one ColabDesign bounded execute asset gate and one DexDesign route audit only; it is not generation evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.28 records external asset rescue only; it is not controlled multi-case evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.29 records one ColabDesign single-case bounded generation/parser row, one DexDesign synthetic D-L fixture, and one BindCraft external accepted candidate parser fixture only; it is not controlled multi-case evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.30 records pilot target/control/job manifests, execution routing, and prospective wet-lab candidates only; it is not execution evidence, scoring evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.31 records bounded Wave A execution/parser summaries only; it is not scoring evidence, method-ranking evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.32 records Supervisor-Skills installation and routing memory only; it is not Benchmark-result evidence, scoring evidence, method-ranking evidence, or biological validation evidence. v0.33 records method-specific adapter/parser no-supported-output blocker rows only; it is not generated-candidate evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. Future server-side downloads and large artifacts must live outside this repository or in gitignored paths.
