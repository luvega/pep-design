# Pep Design Benchmark Knowledge Base

This repository hosts a peptide-design method knowledge base and a protocol-first benchmark design layer.

Release `1.2.21` packages a repository checkpoint for the protocol, manuscript, Harness governance, readiness evidence, v0.34 bounded connectivity history, and the v0.35 PepGLAD mixed-chirality connectivity attempt. It is not a completed Benchmark or a method ranking.

## 当前科研状态

当前计划是 [`ops/plans/updated_plan_v0.35.md`](ops/plans/updated_plan_v0.35.md)，`VERSION` 仍为 `1.2.21`。v0.35 允许同一条候选肽包含 L 和 D 残基，并把固定 baseline mismatch 记为 warning；但唯一授权的 PepGLAD `attempt_001` 在容器启动前因 Docker API socket 权限不足而失败。`exit_code=1`，parser 和 QC 均为 `not_run`，没有 raw candidate 或 v0.35 connectivity bundle。这不是 PepGLAD 方法失败，mixed L/D policy 也尚未获得实际运行验证。详见 [`ops/audits/v035_pepglad_connectivity_audit.md`](ops/audits/v035_pepglad_connectivity_audit.md)。

v0.34 历史 compact merge 保持不变：13 条 method-output manifest、12 条 candidate/QC、12 条 runtime provenance 和 14 条 run rows；6 个 seed42 primary 与对应的 6 个 eligible seed43 extensions 获得 `supported`。PepGLAD v0.34 候选缺席，seed43 未运行。

[`benchmark/results/pilot_failure_diagnostics_v0.34.json`](benchmark/results/pilot_failure_diagnostics_v0.34.json) 另存 1 条 tracked failure-only diagnostic provenance。它绑定 PepGLAD `attempt_003` 的 `AWHITLLIFTH` sequence summary、OpenMM 前后结构 SHA-256 与 L/D 计数、固定 baseline mismatch，以及 source/model/target/observer/patch/wrapper 等 producer pins。该记录不计入上述 12 条 candidate runtime provenance，也不是候选、QC、评分或完整复现证据。

PepGLAD seed42 `attempt_003` 的 target preflight 和 source/model/observer/patch/wrapper/instrumented-source pins 均通过，进程退出码为 0。parser 返回 `pepglad_seed42_replay_mismatch`，merge 返回 `evidence_incomplete`。sequence summary 仍为 `AWHITLLIFTH`，但没有晋升候选。OpenMM 前 B 链为 L6/D5，SHA-256 是 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`；OpenMM 后为 L4/D7，SHA-256 是 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`，不同于固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。历史 `attempt_002` 为 `AWHITLLIFTH`、L4/D7，文件 SHA-256 与 baseline 相同。

`first_observed_chirality_failure_stage=pre_openmm_snapshot` 只支持“混合手性在本 attempt 的 OpenMM 前已可观察”。它不证明模型是根因，也不证明 OpenMM 没有影响，因为 L/D 计数从 6/5 变为 4/7。现有官方入口没有符合当前协议的 method-native skip-relax 或 idealize 选项；按已批准的停止条件，本轮不再运行第二个诊断 attempt 或 PepGLAD seed43。

RFdiffusion 输出是未线程化的 all-Gly backbone，ProteinMPNN FASTA 是独立 handoff；当前没有 sequence-resolved structure。PepMLM 两个 seed 都生成 `WWX`，只记为 `pass_with_warning`。D-Flow 的 3EQS fixture 有已知训练重叠，只用于连通性检查。项目没有 scoring、ranking、frozen target 或 wet-lab 验证。

## Acceptance Harness

Project acceptance is governed by [`harness/contracts/project_acceptance_v1.json`](harness/contracts/project_acceptance_v1.json). The generated reader view is [`harness/PROJECT_ACCEPTANCE.md`](harness/PROJECT_ACCEPTANCE.md), the current machine/human reports are under [`ops/acceptance/`](ops/acceptance/), and the implementation plan is [`ops/plans/harness_engineering_plan_v1.0.md`](ops/plans/harness_engineering_plan_v1.0.md).

Run read-only preflight with `python scripts/run_project_acceptance.py check --profile current_phase`. 当前 active gate 是 `current.v035_bounded_connectivity`；因为 v0.35 没有可重放的 PepGLAD candidate bundle，该 gate 为 Critical `FAIL`。`current_phase` 不能签核，`VERSION` 保持 `1.2.21`。

### 对话内签核

运行 `prepare-review` 和展示审批卡前，必须停止全部 subagents 并确认其 quiescent。Agent 只能在当前受信任 Codex 会话中先展示一张未过期审批卡，再接受一条经 Unicode NFC 规范化并 trim 首尾空白后完整内容恰好为 `批准` 的回复；这是一项会话授权，不是 cryptographic identity。卡片展示后任何介入的非精确 `批准` 用户消息都会使卡失效，必须重新 prepare 并展示新卡。固定审批 bundle 同时覆盖 `governance` 与 `current_phase`，但会生成两份独立的 profile-bound `governance_owner` signoff，不能 waiver Critical/Major failure，也不批准 `release_checkpoint` 或 `full_project`。

批准后仅在 source manifest 非空时于当前 `main` 创建 source checkpoint；manifest 记录 Git clean 后实际进入 commit 的 blob SHA-256，空 manifest 复用卡片 HEAD，随后只创建一个 signoff commit。Transport、staging、history 与 clean-checkout materialization 均在受控 Git 配置/隔离 gitdir 中执行；重验后以显式 refspec、真实 ancestry 检查和 card-bound expected-old-OID lease 对 `git@github.com:luvega/pep-design.git` 的 `refs/heads/main` 执行 fast-forward push。该 lease 不授权 non-fast-forward 或无条件 force-push。Generated report、审批卡和 journal 是 non-evidence 控制面状态；production signoff 只有作为 `harness/signoffs/` 下 committed、clean、非 symlink 的直接 regular file 才有效。

Durable `local_committed_push_failed` 或 `verified` 只通过 `resume-push --card-id <card_id>` 恢复。已有 final OID 时直接复用且不重复 commits/signoffs；只有 source OID 时在该 source 的临时 clean checkout 中重验，再创建或复用缺失 signoff，并至多新建一个 signoff commit，且不重复 source。若失败点已留下 staged signoff，恢复只接受与卡片派生 manifest 在路径、mode 和 blob SHA-256 上完全一致的 index；任何 extra/different staged 状态均 fail closed。`verified` 可在 remote 已是 final OID 时协调不明确但实际成功的 push，仅推进 journal 而不再次 push。

该流程由不同 subagents 分别承担设计、测试、编码、文档与独立复审。对话签核流程本身不授权 clone、install、download、GPU generation、scoring 或 ranking；v0.34 的受限生成另有明确授权。当前 Critical gate 尚未通过，所以不能展示可批准的 `current_phase` 审批卡。`VERSION` 继续保持 `1.2.21`。

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
- Bounded seven-method connectivity layer: `v0.34` project-local bounded generation/QC supplement; latest merge primary 6/7 supported
- PepGLAD mixed-chirality connectivity layer: `v0.35` prospective protocol plus one infrastructure-failed attempt; no candidate bundle
- Repository checkpoint: `v1.2.21`
- Evidence/release checkpoint build date: 2026-07-09（v0.35 工作层更新于 2026-07-14）
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
- v0.34 records 14 staged jobs across 7 methods. The latest merge supports 6 seed42 primary candidates and their 6 eligible seed43 extensions. PepGLAD `attempt_003` exited 0 but failed replay verification, so no latest PepGLAD candidate or candidate-provenance row was promoted and seed43 was not run. One separate tracked failure-only diagnostic record preserves the failed attempt's sequence, pre/post-OpenMM hashes and chirality, baseline mismatch, and producer pins without treating it as candidate or scoring evidence. RFdiffusion retains an unthreaded all-Gly backbone plus a separate ProteinMPNN FASTA handoff, not a sequence-resolved structure.
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

v0.34 把 7 种方法接入同一套 job、parser 和 QC 合同。仓库保存 14 条 run rows、13 条 method-output manifest、12 条 candidate/QC 和 12 条 candidate runtime provenance；原始结构、日志和 GPU 输出仍在 gitignored `benchmark_runs/v0.34/`。PepGLAD 最新诊断的 preflight 与 pins 通过，但 replay mismatch 使其证据停留在 `evidence_incomplete`，没有进入 candidate/QC/provenance 表。另存的 1 条 `pilot_failure_diagnostics_v0.34.json` 记录只用于追踪这次失败，不改变 compact 表计数。

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

Expected validation for the current working layer covers the v0.35 plan, its fail-closed infrastructure record and the historical v0.34 bounded-connectivity artifacts, while retaining earlier planning, readiness, parser and execution layers:

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
- `pilot_benchmark_job_v034_rows`: 14
- `pilot_execution_matrix_v034_rows`: 14
- `pilot_execution_results_v034_rows`: 14
- `pilot_method_output_v034_rows`: 13
- `pilot_candidate_output_v034_rows`: 12
- `pilot_candidate_qc_v034_rows`: 12
- `pilot_run_v034_rows`: 14
- `pilot_runtime_provenance_v034_records`: 12
- `pilot_failure_diagnostics_v034_records`: 1
- `example_job_manifest_v011_rows`: 2
- `method_output_manifest_v011_rows`: 2
- `candidate_output_v011_rows`: 2
- `method_landscape_v09_rows`: 27
- `bilingual_sync_rows`: 19
- `method_classification_v1_rows`: 27
- `reference_dataset_sources_v1_rows`: 8
- `manuscript_todo_v1_rows`: 18
- `manuscript_claim_rows`: 78
- `supplementary_material_rows`: 6
- `scoring_rationale_rows`: 10
- `method_landscape_patch_v11_rows`: 8
- `grant_review_action_v13_rows`: 12
- `migration_v010_rows`: 23
- `smoke_test_readmes`: 10
- `method_cards`: 12
- `literature_cards`: 120
- `bibtex_entries`: 432
- `markdown_links_checked`: 249
- `tracked_files_checked`: 561

## Source Boundary

This repository is the working project layer. Zotero, EndNote, and the prior PD-wiki remain upstream source systems. The files under `sources/raw_snapshots/` are local project snapshots used for provenance and should be treated as read-only.

This release excludes model weights, downloaded PDFs, EndNote libraries, third-party source trees, large datasets and raw benchmark execution outputs. v0.5 source pinning and data availability checks are metadata-only snapshots. v1.1 supplementary-source synthesis provides source discovery and framing, not primary-source verified evidence or runnability evidence. v1.2 manuscript figures and embedded Markdown tables are planning/reporting artifacts, not benchmark results. v1.3 grant-style mock review is a simulated review and preflight-planning layer, not a funding decision, execution record, code-quality confirmation, or local reproducibility claim. v0.12 source-code clone evidence records external Git checkouts only; it is not installation, environment validation, smoke-test execution, model-weight download, or local reproducibility evidence. v0.13 image/environment assignment records observed existing images and a workbench Dockerfile scaffold; it is not by itself proof that a method is runnable. v0.14 academic-search target/case matrices record literature-derived candidates only; they are not target-set promotion, data-download, assay validation, leakage clearance, or Benchmark performance evidence. v0.15 records one external shared-image import preflight layer and three minimal smoke tests only; it is not complete Benchmark evidence, target-set evidence, scoring evidence, or method-performance evidence. v0.16 records adapter/parser hardening and Batch B target review planning only; it is not a new run, target freeze, scoring result, or performance finding. v0.17 records pilot gates only; it does not freeze `target_set_v0.csv` or execute jobs. v0.18 records parser replay fixtures from v0.15 outputs only; it is not new method execution, scoring evidence or Benchmark results. v0.19 records external method install/example-smoke readiness summaries only; it is not head-to-head Benchmark evidence, scoring evidence, method-ranking evidence, or proof that every method is free of unresolved issues. v0.20 records external method-unblock readiness summaries only; it is not target-set evidence, scoring evidence, method-ranking evidence, or proof that every blocker is resolved. v0.21 records bounded adapter smoke and parser fixture rows only; it is not target-set evidence, scoring evidence, method-ranking evidence, complete reproducibility evidence, or proof that every blocker is resolved. v0.22 records multi-case fixture pilot target/control/job manifests and priority gates only; it is not frozen target-set evidence, execution evidence, scoring evidence, method-ranking evidence, or proof that D-Flow, ColabDesign or BindCraft gates are resolved. v0.23 records project-local notebook CLI and D-Flow readiness findings only; it is not target-set evidence, scoring evidence, method-ranking evidence, complete reproducibility evidence, or proof that ColabDesign or BindCraft gates are resolved. v0.24 records one D-Flow fixture-level PepDataset LMDB load test only; it is not scoring evidence, method-ranking evidence, complete reproducibility evidence, or `smoke_test_ready` promotion. v0.25 records D-Flow full PepMerge download and official LMDB load evidence only; it is not a generation run, target-set evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.26 records one D-Flow bounded dry-run, one ColabDesign CLI adapter package and one BindCraft wrapper classification only; it is not frozen target-set evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.27 records one ColabDesign bounded execute asset gate and one DexDesign route audit only; it is not generation evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.28 records external asset rescue only; it is not controlled multi-case evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.29 records one ColabDesign single-case bounded generation/parser row, one DexDesign synthetic D-L fixture, and one BindCraft external accepted candidate parser fixture only; it is not controlled multi-case evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.30 records pilot target/control/job manifests, execution routing, and prospective wet-lab candidates only; it is not execution evidence, scoring evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.31 records bounded Wave A execution/parser summaries only; it is not scoring evidence, method-ranking evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. v0.32 records Supervisor-Skills installation and routing memory only; it is not Benchmark-result evidence, scoring evidence, method-ranking evidence, or biological validation evidence. v0.33 records method-specific adapter/parser no-supported-output blocker rows only; it is not generated-candidate evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, `benchmark_ready`, or complete Benchmark evidence. Future server-side downloads and large artifacts must live outside this repository or in gitignored paths.

v0.34 只记录指定 fixture 上的生成连通性和基础 QC。最新 seed42 为 6/7 supported；PepGLAD 诊断未晋升候选，且停止条件已触发。PepMLM 保留 `X` 警告，D-Flow 3EQS 保留训练重叠限制。继续 PepGLAD 诊断需要另行批准协议/source-policy 变更，不能直接进入 scoring、ranking、frozen target、wet-lab、`smoke_test_ready`、`benchmark_ready` 或完整 Benchmark 阶段。

v0.35 的 `attempt_001` 只记录 Docker API 权限导致的容器启动前基础设施失败。它没有运行 PepGLAD、OpenMM、parser 或 QC，也没有候选肽。该 attempt 不得覆盖或自动重试；新的不可覆盖执行需要用户再次明确授权并更新 attempt 政策。
