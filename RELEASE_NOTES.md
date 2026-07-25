# Release Notes

## Unreleased GitHub Homepage Documentation (`VERSION=1.2.21`) - 2026-07-25

重写 GitHub README，使方法来源、任务归类、标准输入输出、代表性 fixture 和评价标准可以从项目主页直接复核。

### Added

- 新增 `benchmark/method_sources/method_homepage_source_map_v0.35.csv`，记录 10 个纳入方法的代码仓库、固定 commit、论文、persistent ID、任务类型和 I/O 契约。
- 使用 ImageGen 生成项目图标和 protocol-first 工作流图，并保存提示词、透明背景处理和人工 QC 记录。
- 新增主页来源表、来源校验逻辑、图像属性和 README 边界测试。

### Changed

- README 改为证据分层结构，区分 T1/T2/T3、chirality/cyclization/ncAA 约束、生成与 ranking/rescoring，以及计算代理指标与生物学验证。
- 展示 v0.34 seed42 代表性输入输出，并链接 compact job、candidate、QC、runtime provenance 和 failure-only artifacts。
- 保留 `VERSION=1.2.21`、v0.35 Critical failure、schema-only `target_set_v0.csv` 和 `not_run` scoring 状态。

### Boundary

- 来源链接表和主页插图只用于导航与解释，不构成安装、可运行、完整复现、方法性能或实验验证证据。
- 本次更新未执行 clone、install、download、GPU generation、scoring、ranking、target freeze 或 wet-lab。

## Unreleased v0.35 PepGLAD Mixed-Chirality Connectivity Work Layer (`VERSION=1.2.21`) - 2026-07-14

当前计划已切换到 `ops/plans/updated_plan_v0.35.md`。本层为 PepGLAD 定义一条前瞻性连通性通道：同一候选肽可包含 L 和 D 残基，手性只做 report-only 检查，固定 seed42 baseline mismatch 只记 warning。v0.34 的 6/7 历史结果不回写。

### 实际结果

- 新增 v0.35 单行 job manifest、execution matrix、adapter、runner、parser、Harness gate 和独立 validator。
- adapter、runner、parser、治理约束和 v0.34 回归在执行前共 501 项核心测试通过；独立 focused 审查未发现 Critical/Major/Minor 问题。
- 唯一授权的 PepGLAD `attempt_001` 已执行，但 `docker run` 在容器启动前因 Docker API socket 权限不足退出：`runtime_seconds=0.026`、`exit_code=1`、`status=execution_failed`、parser/QC=`not_run`。
- host 侧 source、model 和 3EQS target 前检通过；容器内 instrumentation、pocket detection、PepGLAD inference、OpenMM/finalize、parser 和 QC 均未执行。
- `raw/` 中没有 candidate、summary 或 runtime evidence。解析器 fail closed，没有生成 `benchmark/results/pilot_pepglad_connectivity_v0.35.json`。
- 新增 `ops/audits/v035_pepglad_connectivity_audit.md` 记录本次基础设施失败和证据边界。

### 当前阻断

- 该失败不是 PepGLAD 方法失败，不能用于评价 mixed L/D policy、连通性或方法表现。
- `current.v035_bounded_connectivity` 缺少可重放的 candidate bundle，仍为 Critical `FAIL`；`current_phase` 不能签核。
- `attempt_001` 不得覆盖或自动重试。新的执行需要用户再次明确授权并先更新 execution/attempt 政策；当前不授权 `attempt_002`、seed43、scoring 或 ranking。

### Boundary

- `VERSION` 保持 `1.2.21`。
- v0.34 compact 计数和 6/7 历史结论保持不变。
- 本层没有生成候选、scoring、ranking、frozen target、wet-lab、`smoke_test_ready`、`benchmark_ready` 或完整 Benchmark 结论。

## Unreleased v0.34 Bounded Connectivity Work Layer (`VERSION=1.2.21`) - 2026-07-12

当前计划已切换到 `ops/plans/updated_plan_v0.34.md`。本工作层接入 7 种方法的真实、受限生成入口，统一记录不可覆盖 attempt、parser 输出、基础 QC 和小型证据表。原始结构与日志保留在 gitignored `benchmark_runs/v0.34/`。

### 结果

- 最新 compact merge 有 13 条 method-output manifest、12 条 candidate/QC、12 条 runtime provenance 和 14 条 run rows。6 个 seed42 primary 与对应的 6 个 eligible seed43 extensions 获得 `supported`；PepGLAD 最新候选缺席，seed43 未运行。
- 新增 `benchmark/results/pilot_failure_diagnostics_v0.34.json`，只保存 1 条 tracked failure-only diagnostic provenance。该记录绑定 `attempt_003` 的 `AWHITLLIFTH`、OpenMM 前后 SHA-256 与 L6/D5、L4/D7、固定 baseline mismatch，以及 source/model/target/observer/patch/wrapper 等 producer pins。
- PepGLAD seed42 `attempt_003` 的 target preflight 与 source/model/observer/patch/wrapper/instrumented-source pins 通过，进程退出码为 0；parser=`pepglad_seed42_replay_mismatch`，merge=`evidence_incomplete`。sequence summary 仍为 `AWHITLLIFTH`，但未晋升候选。
- OpenMM 前 B 链为 L6/D5，SHA-256 为 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`；OpenMM 后为 L4/D7，SHA-256 为 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`，不同于固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。历史 `attempt_002` 为 `AWHITLLIFTH`、L4/D7，文件 SHA-256 与 baseline 相同。
- `first_observed_chirality_failure_stage=pre_openmm_snapshot` 支持混合手性在本 attempt 的 OpenMM 前已可观察，但不证明模型根因，也不排除 OpenMM 的影响；L/D 计数从 6/5 变为 4/7。
- PepMLM 两个 seed 均生成 `WWX`，保留非标准残基 `X` 警告。D-Flow 的 3EQS fixture 有已知训练重叠，只保留连通性用途。
- RFdiffusion 保留未线程化 all-Gly backbone 与独立 ProteinMPNN FASTA handoff，当前没有 sequence-resolved structure。

### Added

- Added the v0.34 job manifest, execution matrix, seven method adapters, bounded runner, merge script and focused tests.
- Added compact execution, method-output, candidate, QC, run, runtime-provenance and merge-summary artifacts under `benchmark/deployment/` and `benchmark/results/`.
- Added one tracked failure-only diagnostic provenance record for the non-promoted PepGLAD `attempt_003`.
- Added `ops/plans/updated_plan_v0.34.md` and `ops/audits/v034_bounded_connectivity_audit.md`.

### 当前阻断

- `current.v034_bounded_connectivity` 要求 7/7 个 seed42 主运行通过；当前只有 6/7，因此该 Critical gate 为 `FAIL`。
- `current_phase` 不能签核。人工批准不能跳过 Critical failure。
- 现有官方入口没有符合当前协议的 method-native skip-relax 或 idealize 选项。按已批准的停止条件，本轮不再发起第二个诊断 attempt，也不运行 PepGLAD seed43。
- 继续执行需要用户另行批准协议/source-policy 变更，或接受 PepGLAD 在该 fixture 上失败；两种选择都不能直接进入评分。

### Boundary

- `VERSION` 保持 `1.2.21`。
- 本层没有 scoring、ranking、frozen target、wet-lab、`smoke_test_ready` 或完整 Benchmark 结论。
- 6/7 通过不能解释为方法性能比较；当前数据只说明指定 fixture 上的入口、解析与基础 QC 状态。
- 12 条 compact runtime provenance 只绑定已晋升的 12 条候选。另存的 1 条 PepGLAD failure-only diagnostic record 不计入这 12 条，也不是候选、评分或完整复现证据。

## Unreleased Harness Engineering Workflow (`VERSION=1.2.21`) - 2026-07-10

This section records the unsigned contract-driven acceptance workflow introduced against the v0.33 checkpoint. The current scientific work layer is v0.35, described above.

### Added

- Added the `harness/` contract, artifact/claim registries, read-only domain evaluators, dependency-aware profile roll-up, digest-bound signoff validation, and generated acceptance views.
- Added `scripts/run_project_acceptance.py`, focused harness tests, and `ops/plans/harness_engineering_plan_v1.0.md`.
- Preserved the full pre-harness operating rules as a digest-bound migration snapshot while reducing `AGENTS.md` to a progressive-disclosure entry map.
- 新增对话审批卡与 durable journal：运行 `prepare-review` 和展示卡片前必须停止全部 subagents 并确认其 quiescent；仅在当前受信任 Codex 会话展示未过期卡后，接受 NFC 规范化并 trim 后完整内容恰好为 `批准` 的回复，该机制不是 cryptographic identity。卡片展示后任何介入的非精确 `批准` 用户消息都会使卡失效，必须重新 prepare 并展示新卡。
- 固定 `governance` + `current_phase` bundle 生成两份 profile-bound signoff；首次签核的 `supersedes` 为 `null`，复签优先选择完整 current evaluation context 的最新前序签核。
- Source manifest 绑定 Git clean 后实际提交的 blob SHA-256；transport、staging、history、diff-check 和 clean-checkout materialization 使用受控配置/隔离 gitdir，并拒绝 hooks、filters、fsmonitor、URL rewrite、replacement refs 与 grafts。
- 仅当 source manifest 非空时创建 source checkpoint，空 manifest 复用卡片 HEAD，然后创建一个 signoff commit；通过真实 ancestry 检查与 card-bound expected-old-OID lease，以显式 refspec fast-forward push 到 `refs/heads/main`，不允许 non-fast-forward 或无条件 force-push。
- 采用 `subagent-driven-development`，将设计、red tests、编码、文档和独立 spec/quality review 分工执行。

### Pending

- `VERSION` remains `1.2.21` until digest-bound governance signoff authorizes a 1.2.22 candidate; engineering/scientific signoff must then be repeated against the final 1.2.22 digest.
- The fixed `governance` + `current_phase` approval bundle cannot proceed while `current.v035_bounded_connectivity` has a Critical failure; `full_project` remains `not_accepted`.
- 实际批准前，审批卡与 journal 仅是 generated non-evidence；production signoff 必须是 `harness/signoffs/` 下 committed、clean、非 symlink 的直接 regular file。
- Durable `local_committed_push_failed` 或 `verified` 只允许 `resume-push --card-id <card_id>` 恢复且无需重新批准。已有 final OID 时复用且不重复 commits/signoffs；仅有 source OID 时在临时 clean source checkout 中重验。若失败已留下 staged signoff，只接受与 card-derived manifest 的 path/mode/blob SHA-256 完全一致的 index，再创建或复用至多一个 signoff commit；extra/different staged 状态 fail closed。`verified` 可在 remote 已是 final OID 时协调实际成功但结果不明确的 push，而不重复 push。

### Boundary

- The harness transaction itself does not authorize clone, install, download, GPU generation, scoring, ranking, target freeze, or wet-lab work. The v0.34 bounded generation runs used separate explicit authorization.
- v0.33 remains a historical baseline with 10 method-specific blocker rows and 0 parsed/generated candidates; current evidence is recorded only in v0.34 artifacts.
- 对话 signoff 不能 waiver Critical/Major failure，也不批准 `release_checkpoint`、`full_project` 或发布。当前先解决 v0.35 基础设施执行阻断并取得可重放 candidate bundle，再重新准备审批卡。

## v1.2.21 Wave A Adapter/Parser Completion Attempt - 2026-07-10

This checkpoint adds the v0.33 adapter/parser completion attempt layer for the
10 v0.31 placeholder-failed Wave A jobs.

### Added

- Added `scripts/run_v033_wave_a_pilot.py`.
- Added `scripts/parse_v033_pilot_outputs.py`.
- Added `benchmark/deployment/pilot_execution_results_v0.33.csv`.
- Added `benchmark/results/pilot_method_output_manifest_v0.33.csv`.
- Added `benchmark/results/pilot_candidate_outputs_v0.33.csv`.
- Added `benchmark/results/pilot_run_v0.33.csv`.
- Added `benchmark/results/pilot_v033_merge_summary.json`.
- Added `ops/plans/updated_plan_v0.33.md`.
- Added `ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md`.
- Added `tests/test_v033_wave_a_adapter_completion.py`.

### Changed

- Bumped project version to `1.2.21`.
- Promoted `ops/plans/updated_plan_v0.33.md` as the current authoritative plan.
- Extended validator coverage for v0.33 compact tables and no-overclaim checks.

### Boundary

- v0.33 records 10 method-specific `no_supported_output_found` blocker rows.
- v0.33 is not Benchmark result evidence, not scoring evidence, not method-ranking evidence and not wet-lab validation evidence.

## v1.2.20 Supervisor-Skills Installation Memory - 2026-07-09

This checkpoint records installation and project-memory routing for selected
Supervisor-Skills manuscript-support skills.

### Added

- Added `ops/audits/supervisor_skills_installation_v0.32.md`.
- Added `tests/test_v032_supervisor_skills_memory.py`.

### Changed

- Bumped project version to `1.2.20`.
- Updated `AGENTS.md` with Supervisor-Skills routing for Benchmark manuscript,
  Introduction consistency check, figure planning, pre-submission review and
  idea reassessment.
- Updated `ops/audits/skill_selection.md` with source commit
  `0b77a1b98794f8341d57685a0e829a3fa175d05f`, installed skill list and
  `CC BY-NC-SA 4.0` boundary.
- Updated validator coverage for the v0.32 Supervisor-Skills memory layer.

### Notification

- Installed local skills: `benchmark-paper-template`, `intro-drafter`,
  `figure-designer`, `pre-submission-reviewer`, and `idea-evaluator`.
- Restart Codex to pick up new skills.

### Boundaries

- Supervisor-Skills entries are manuscript-support memory only.
- They are not Benchmark result, not scoring evidence, and not method-ranking
  evidence.
- No new method execution, target-set promotion, wet-lab validation or
  performance comparison was added.

## v1.2.19 Bounded Wave A Pilot Execution Parser Layer - 2026-07-09

This checkpoint executes and merges the v0.31 bounded Wave A pilot package from
the v0.30 manifests.

### Added

- Added `scripts/run_v031_wave_a_pilot.py`.
- Added `scripts/parse_v031_pilot_outputs.py`.
- Added `benchmark/deployment/pilot_execution_results_v0.31.csv`.
- Added `benchmark/results/pilot_method_output_manifest_v0.31.csv`.
- Added `benchmark/results/pilot_candidate_outputs_v0.31.csv`.
- Added `benchmark/results/pilot_run_v0.31.csv`.
- Added `benchmark/results/pilot_v031_merge_summary.json`.
- Added `ops/audits/pilot_wave_a_execution_audit_v0.31.md`.
- Added `tests/test_v031_wave_a_pilot.py`.

### Changed

- Bumped project version to `1.2.19`.
- Extended the ColabDesign bounded runner so v0.31 can keep the outer
  `command.sh` separate from the inner `colabdesign_inner_command.sh`.
- Updated validator coverage for v0.31 execution, method, candidate and run
  tables.
- Updated README, index, Benchmark README, AGENTS and project log for v0.31.

### Notification

- v0.31 represents 14 Wave A jobs from the v0.30 job manifest.
- Parsed/generated rows: 4.
- Failed placeholder rows: 10.
- Parsed methods: PepMLM and AfCycDesign / ColabDesign cyclic peptide.
- ColabDesign seed 42 and seed 43 both produced parsed 14-aa binder-chain rows
  after the wrapper fix.

### Boundaries

- No scoring or method ranking.
- No `target_set_v0.csv` promotion.
- No wet-lab synthesis, assay, or validation claim.
- The 10 failed rows are adapter placeholder failures, not algorithm-failure
  conclusions.
- No complete Benchmark result.

## v1.2.18 Pilot Benchmark Design Layer - 2026-07-09

This checkpoint converts the v0.29 bounded/parser evidence into a controlled
pilot benchmark input layer for the next bounded Wave A execution phase.

### Added

- Added `benchmark/input_sets/pilot_benchmark_target_manifest_v0.30.csv`.
- Added `benchmark/input_sets/pilot_benchmark_control_manifest_v0.30.csv`.
- Added `benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv`.
- Added `benchmark/deployment/pilot_execution_matrix_v0.30.csv`.
- Added `benchmark/input_sets/wet_lab_candidate_panel_v0.30.csv`.
- Added `ops/audits/pilot_benchmark_design_audit_v0.30.md`.
- Added `tests/test_v030_pilot_benchmark_design.py`.

### Changed

- Bumped project version to `1.2.18`.
- Updated validator coverage for v0.30 target/control/job manifests, execution
  matrix, and prospective wet-lab panel.
- Updated README, index, Benchmark README, AGENTS and project log for v0.30.

### Notification

- Wave A now has 14 planned bounded pilot jobs: seven executable methods times
  seeds `42` and `43`.
- Wave B keeps DexDesign and BindCraft as control/smoke routes.
- SaLT&PepPr remains blocked by license/gated access and has no executable job.
- The prospective wet-lab panel records MDM2, GABARAP, NCAM1 and AMHR2 as
  candidate follow-up classes only.

### Boundaries

- No v0.30 job was executed.
- No `target_set_v0.csv` promotion.
- No scoring or method-ranking evidence.
- No wet-lab synthesis, assay, or validation claim.
- No complete Benchmark result.

## v1.2.17 Bounded Generation and Parser Evidence - 2026-07-09

This checkpoint records the v0.29 bounded/parser follow-up for ColabDesign,
DexDesign and BindCraft.

### Added

- Added `scripts/run_colabdesign_bounded_generation.py`.
- Added `scripts/prepare_dexdesign_minimal_fixture.py`.
- Added `scripts/parse_bindcraft_accepted_outputs.py`.
- Added `benchmark/deployment/bounded_generation_parser_v0.29.csv`.
- Added `benchmark/results/colabdesign_bounded_method_output_manifest_v0.29.csv`.
- Added `benchmark/results/colabdesign_bounded_candidate_outputs_v0.29.csv`.
- Added `benchmark/results/bindcraft_accepted_candidate_outputs_v0.29.csv`.
- Added `ops/audits/bounded_generation_parser_audit_v0.29.md`.
- Added `tests/test_v029_bounded_generation_parser.py`.

### Changed

- Bumped project version to `1.2.17`.
- Updated validator coverage for v0.29 bounded/parser artifacts.
- Updated README, index, Benchmark README, AGENTS and project log for v0.29.

### Notification

- ColabDesign completed one bounded 7ZKR GPU generation/parser attempt in
  `benchmark_runs/v0.29/colabdesign_bounded_generation`; exit code was `0`,
  parser status was `parsed`, and the compact candidate row records sequence
  `IQTNYYVRSRTQCQ`.
- DexDesign now has a synthetic prepared D-L complex fixture with target=`z`
  and peptide=`y`; no DexDesign design job was run.
- BindCraft external CD47 accepted-final outputs were converted into four
  standard candidate rows.

### Boundaries

- No controlled multi-case Benchmark run.
- No `target_set_v0.csv` promotion.
- No multi-seed generation evidence.
- No scoring or method-ranking evidence.
- No complete Benchmark result.

## v1.2.16 External Asset Rescue - 2026-07-09

This checkpoint records external asset rescue for three previously incomplete
method gates: ColabDesign AF parameters, DexDesign input contract, and
BindCraft accepted-final output classification.

### Added

- Added `benchmark/deployment/external_asset_rescue_v0.28.csv`.
- Added `benchmark/results/bindcraft_accepted_final_classification_v0.28.csv`.
- Added `ops/audits/external_asset_rescue_audit_v0.28.md`.
- Added `tests/test_v028_external_asset_rescue.py`.

### Changed

- Bumped project version to `1.2.16`.
- Updated ColabDesign adapter defaults to use
  `/data/protein-design/data/alphafold_db/params`.
- Extended BindCraft classifier support for native `Accepted/` output layout.
- Extended DexDesign route audit with explicit D-peptide/L-protein input
  contract fields.
- Updated validator coverage for v0.28 external asset rescue rows.

### Notification

- ColabDesign asset gate now reaches `ready_for_bounded_gpu_generation` using
  `/data/protein-design/data/alphafold_db/params` and
  `7zkr_GABARAP.pdb`; no ColabDesign generation was run.
- DexDesign input contract is now explicit: first chain is L-target, second
  chain is D-peptide, recommended target=`z`, peptide=`y`; no prepared D-L
  complex fixture was found.
- BindCraft external CD47 output is classified as `accepted_final` with four
  accepted PDB files.

### Boundaries

- No controlled multi-case Benchmark run.
- No ColabDesign generated design claim.
- No DexDesign design run.
- No scoring or method-ranking evidence.
- No complete Benchmark result.

## v1.2.15 ColabDesign/DexDesign Gate Update - 2026-07-09

This checkpoint records two gate updates: a bounded ColabDesign execute asset
gate and a DexDesign-specific OSPREY3 route audit.

### Added

- Added `scripts/audit_dexdesign_route.py`.
- Added `benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv`.
- Added `ops/audits/colabdesign_dexdesign_gate_v0.27.md`.
- Added `tests/test_v027_colabdesign_dexdesign_gates.py`.

### Changed

- Bumped project version to `1.2.15`.
- Extended `scripts/prepare_colabdesign_cli_adapter.py` so `--execute` now
  writes standard failed-closed manifests when AF parameters are missing.
- Updated validator coverage for v0.27 ColabDesign and DexDesign gate rows.
- Updated README, index, Benchmark README, AGENTS and project log for v0.27.

### Notification

- ColabDesign remains blocked before generation as `blocked_af_params_missing`
  until a verified AF parameter route is supplied.
- DexDesign is restricted to the OSPREY3 `examples/ccs.D-peptide-L-protein/`
  route. Generic OSPREY examples are recorded only as
  `env_probe_only_not_dexdesign`.
- DexDesign remains `blocked_dexdesign_input_contract` until a minimal
  D-peptide/L-protein complex fixture and bounded CPU smoke route are recorded.

### Boundaries

- No ColabDesign generation result.
- No DexDesign design result.
- No `target_set_v0.csv` promotion.
- No scoring or method-ranking evidence.
- No complete Benchmark result.

## v1.2.14 D-Flow/ColabDesign/BindCraft Gate Update - 2026-07-09

This checkpoint records three readiness-gate updates: a bounded single-entry
D-Flow dry-run, a standard ColabDesign job-row CLI adapter package, and a
BindCraft accepted-final output classifier.

### Added

- Added `scripts/prepare_colabdesign_cli_adapter.py`.
- Added `scripts/classify_bindcraft_outputs.py`.
- Added `benchmark/deployment/dflow_colabdesign_bindcraft_v0.26.csv`.
- Added `benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv`.
- Added `benchmark/results/bindcraft_wrapper_classification_v0.26.csv`.
- Added `ops/audits/dflow_colabdesign_bindcraft_v0.26.md`.
- Added `tests/test_v026_colabdesign_bindcraft_adapters.py`.

### Changed

- Bumped project version to `1.2.14`.
- Updated validator coverage for v0.26 gate rows, D-Flow bounded candidate
  parsing, and BindCraft wrapper classification.
- Updated README, index, Benchmark README, AGENTS and project log for v0.26.

### Notification

- D-Flow completed a bounded one-entry run on PepMerge entry `1aze_B` with
  `num_steps=1` and `num_samples=1`; exit code was `0`, runtime was 147.67 s,
  and `sample_0.pdb`, `gt.pdb`, `outputs.csv`, and `aar.csv` were produced in
  gitignored runtime storage.
- The D-Flow sample PDB parser extracted chain B sequence `MRRRRRRRRY`.
- ColabDesign now has a standard job-row CLI adapter package for
  `v022_pilot_colabdesign_7zkr_seed42`; v0.26 packages config and manifests but
  does not run ColabDesign generation.
- BindCraft v0.21 output is classified as `low_confidence_only` with zero
  accepted PDBs and one LowConfidence trajectory PDB.

### Boundaries

- No `target_set_v0.csv` promotion.
- No scoring or method-ranking evidence.
- No ColabDesign generation run.
- No BindCraft accepted-final design claim.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No source tree, model weight, downloaded dataset archive, generated PDB,
  LMDB, or raw runtime log is tracked in git.

## v1.2.13 D-Flow Full PepMerge Download Readiness - 2026-07-09

This checkpoint resolves the D-Flow full PepMerge Google Drive blocker. It
records verified downloads for `PepMerge_release.zip` and `PepMerge_lmdb.zip`,
archive integrity checks, extracted structure coverage, official split-name
bridging, and passing `PepDataset(reset=False)` loads for the official train
and test LMDB caches.

### Added

- Added `benchmark/deployment/dflow_full_pepmerge_download_v0.25.csv`.
- Added `ops/audits/dflow_full_pepmerge_download_audit_v0.25.md`.
- Added `tests/test_v025_dflow_full_pepmerge_download.py`.

### Changed

- Bumped project version to `1.2.13`.
- Updated validator coverage for the v0.25 full PepMerge download/load row.
- Updated README, index, Benchmark README, AGENTS and project log for v0.25.

### Notification

- The local DNS issue for `drive.google.com` was isolated; folder metadata was
  reached with a Google-IP override and downloads completed through
  `drive.usercontent.google.com`.
- `PepMerge_release.zip` is stored in gitignored
  `data/dflow/downloads/PepMerge_release.zip` with SHA256
  `eb0c9f6f81b85c399a32fe38e7f79274584805d7cafaac774a8d091792d0410c`.
- `PepMerge_lmdb.zip` is stored in gitignored
  `data/dflow/downloads/PepMerge_lmdb.zip` with SHA256
  `452240f8d60227c0959f7f3a8cf43a2f8a63e53806f4f47bdf8ccb1cb1f5ef08`.
- The extracted structure directory contains 10,348 case directories with no
  missing required `pocket.pdb`/`peptide.pdb`/`receptor.pdb`/FASTA files.
- D-Flow `PepDataset(reset=False)` loads 154 `pep_pocket_test` entries and
  9,849 `pep_pocket_train` entries from the official LMDB package.

### Boundaries

- No `target_set_v0.csv` promotion.
- No D-Flow generation run, scoring, or method-ranking evidence.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No source tree, model weight, downloaded dataset archive, generated PDB,
  LMDB, or raw runtime log is tracked in git.

## v1.2.12 D-Flow Input Contract Fixture Readiness - 2026-07-09

This checkpoint resolves the D-Flow PepMerge/LMDB blocker at fixture level. It
adds a reusable builder that prepares a PepMerge-style 3EQS input directory,
generates `pep_pocket_test_structure_cache.lmdb`, and verifies
`PepDataset(reset=False)` loading in the project-local D-Flow environment.

### Added

- Added `scripts/prepare_dflow_input_contract.py`.
- Added `benchmark/deployment/dflow_input_contract_fixture_v0.24.csv`.
- Added `ops/audits/dflow_input_contract_fixture_audit_v0.24.md`.
- Added `tests/test_v024_dflow_input_contract.py`.

### Changed

- Bumped project version to `1.2.12`.
- Updated validator coverage for the v0.24 D-Flow input-contract fixture row.
- Updated README, index, Benchmark README, AGENTS and project log for v0.24.

### Notification

- The D-Flow fixture path `data/dflow/pepmerge/mdm2_p53_3eqs_fixture` and
  LMDB cache `data/dflow/pep_cache/pep_pocket_test_structure_cache.lmdb` were
  created in gitignored runtime storage.
- `PepDataset(reset=True)` and `PepDataset(reset=False)` both passed for one
  3EQS fixture entry.
- The full PepMerge release Google Drive route remains unresolved; v0.24 does
  not claim full PepMerge dataset access.
- 3EQS chain B loads as 11 generated residues through the D-Flow parser, so
  target chain/sequence review remains required before scoring.

### Boundaries

- No `target_set_v0.csv` promotion.
- No D-Flow generation run, scoring, or method-ranking evidence.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No source tree, model weight, downloaded dataset archive, generated PDB,
  LMDB, or raw runtime log is tracked in git.

## v1.2.11 External Dry-run Package Readiness - 2026-07-09

This checkpoint adds the v0.23 execution-heavy readiness package. It records a
project-local notebook CLI tool layer and a project-local D-Flow installation
attempt while keeping datasets, weights, source trees, logs and runtime outputs
in gitignored roots.

### Added

- Added `benchmark/deployment/notebook_cli_smoke_manifest_v0.23.csv`.
- Added `benchmark/deployment/dflow_project_install_contract_v0.23.csv`.
- Added `benchmark/deployment/external_dry_run_package_manifest_v0.23.csv`.
- Added `benchmark/deployment/priority_gate_review_v0.23.csv`.
- Added `ops/plans/external_dry_run_package_plan_v0.23.md`.
- Added `ops/audits/external_dry_run_package_audit_v0.23.md`.
- Added `tests/test_v023_external_dry_run_package.py`.

### Changed

- Bumped project version to `1.2.11`.
- Updated validator coverage for v0.23 notebook CLI tooling, D-Flow
  project-local install evidence, dry-run package rows and priority gates.
- Excluded gitignored runtime environment directories from markdown link
  validation.

### Notification

- Notebook CLI tooling is installed in `.venv/benchmark-v023-conda` and a
  `papermill` smoke executed under `benchmark_runs/v0.23`.
- D-Flow / PeptideDesign is cloned into `method_sources/dflow/PeptideDesign`
  as a real project-local checkout, not a symlink.
- D-Flow has a project-local GPU Python environment at `.venv/dflow-v023`;
  `dflow.pt` is extracted under `weights/dflow/`; `PepDataset`, `PepModel`,
  DeepSpeed and `inference_pep` imports pass after the documented DeepSpeed
  `torch._six` patch.
- D-Flow remains `blocked_input_contract` because PepMerge and
  `pep_pocket_test_structure_cache.lmdb` are absent. Google Drive access to
  the README PepMerge folder timed out through both `gdown` and `curl`.
- ColabDesign has notebook CLI tooling available, but the standard job-row CLI
  adapter remains pending.
- BindCraft still requires the accepted-final output classifier before any
  accepted design claim.

### Boundaries

- No `target_set_v0.csv` promotion.
- No scoring or method-ranking evidence.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No source tree, conda environment, model weight, downloaded dataset, LMDB,
  notebook output or raw runtime log is tracked in git.

## v1.2.10 Multi-case Fixture Pilot Planning - 2026-07-08

This checkpoint adds the v0.22 controlled multi-case fixture pilot planning
layer. It converts v0.21 method-example adapter evidence into standardized
fixture target/control/job manifests and priority gates while keeping all
execution and scoring out of scope.

### Added

- Added `benchmark/deployment/method_example_fixture_evidence_v0.22.csv`.
- Added `benchmark/input_sets/multi_case_fixture_target_manifest_v0.22.csv`.
- Added `benchmark/input_sets/multi_case_fixture_control_manifest_v0.22.csv`.
- Added `benchmark/input_sets/multi_case_fixture_job_manifest_v0.22.csv`.
- Added `benchmark/deployment/priority_gate_review_v0.22.csv`.
- Added `ops/plans/multi_case_fixture_pilot_plan_v0.22.md`.
- Added `ops/audits/multi_case_fixture_pilot_audit_v0.22.md`.
- Added `tests/test_v022_multi_case_fixture_plan.py`.

### Changed

- Bumped project version to `1.2.10`.
- Updated validator coverage for v0.22 evidence rows, target/control/job
  manifests, priority gates, blocked-row invariants and no-overclaim checks.
- Updated README, index, Benchmark README, input/results READMEs, AGENTS,
  project log and claim-evidence map for v0.22.

### Notification

- PepMLM, DiffPepBuilder, PepGLAD, PepMirror and RFdiffusion + ProteinMPNN now
  have focused `planned_fixture_only` rows for a future multi-case pilot.
- D-Flow remains `blocked_input_contract` until the external PepMerge structure
  directory and `pep_pocket_test_structure_cache.lmdb` are recorded and
  loadable.
- AfCycDesign / ColabDesign cyclic peptide remains `blocked_cli_adapter` until
  a non-notebook Python CLI adapter is defined.
- BindCraft remains `wrapper_review_only`; the v0.21 LowConfidence trajectory
  is not accepted-final design evidence.

### Boundaries

- No `target_set_v0.csv` promotion.
- No clone, download, install, Docker build, GPU run or new parser output.
- No scoring or method-ranking evidence.
- No complete Benchmark result.
- No biological or experimental validation claim.

## v1.2.9 Adapter Smoke And Parser Fixture Readiness - 2026-07-08

This checkpoint adds the v0.21 adapter-smoke and parser-fixture readiness
layer. It records bounded external adapter/control evidence and compact parser
rows while keeping all raw logs, weights, Docker layers and generated structures
outside the KB.

### Added

- Added `benchmark/deployment/adapter_smoke_manifest_v0.21.csv`.
- Added `benchmark/deployment/adapter_smoke_results_v0.21.csv`.
- Added `benchmark/deployment/blocker_asset_manifest_v0.21.csv`.
- Added `benchmark/results/adapter_method_output_manifest_v0.21.csv`.
- Added `benchmark/results/adapter_candidate_outputs_v0.21.csv`.
- Added `benchmark/results/adapter_run_rows_v0.21.csv`.
- Added `ops/audits/adapter_smoke_audit_v0.21.md`.
- Added `scripts/collect_v021_adapter_smokes.py` and
  `scripts/parse_v021_adapter_outputs.py`.
- Added external workbench files under `/data/protein-design` for
  `pd-benchmark-methods-gpu:0.21`, `pd-pyrosetta-methods-gpu:0.21`, and
  `run_v021_adapter_smokes.py`.

### Changed

- Bumped project version to `1.2.9`.
- Updated validator coverage for v0.21 adapter rows, asset pointers, parser
  rows, external path boundaries and no-overclaim checks.
- Updated README, index, Benchmark README, AGENTS, project log and claim map for
  v0.21.
- Hardened the v0.21 parser to use method-specific binder-chain selection for
  PDB outputs.

### Notification

- `pd-pyrosetta-methods-gpu:0.21` was built externally and passes PyRosetta
  initialization in `bench-pepmirror`.
- PepGLAD public checkpoint assets and the PepMirror Zenodo checkpoint are now
  present in the external workbench.
- PepMLM, DiffPepBuilder, PepGLAD, PepMirror, RFdiffusion + ProteinMPNN and
  BindCraft have bounded v0.21 adapter/control evidence on method-provided or
  synthetic examples.
- RFdiffusion + ProteinMPNN now records an explicit handoff manifest from RF PDB
  output to ProteinMPNN FASTA output.
- D-Flow remains blocked by the missing PepMerge cache/input contract.
- SaLT&PepPr remains license/gated-model blocked; ColabDesign remains blocked
  by non-notebook CLI adapter definition; OSPREY3 remains carry-forward only.

### Boundaries

- No `target_set_v0.csv` promotion.
- No scoring or method-ranking evidence.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No raw logs, Docker layers, model weights, checkpoints, third-party source
  trees, generated structures or large outputs are stored in the KB.

## v1.2.8 Method Unblock Readiness And Independent PyRosetta Route - 2026-07-08

This checkpoint adds the v0.20 method-unblock readiness layer. It prepares an
independent PyRosetta image route outside the KB, records a successful
DiffPepBuilder unblock smoke, and keeps unresolved blockers explicit before any
controlled multi-case fixture pilot.

### Added

- Added `benchmark/deployment/method_unblock_manifest_v0.20.csv`.
- Added `benchmark/deployment/method_unblock_smoke_results_v0.20.csv`.
- Added `ops/audits/method_unblock_audit_v0.20.md`.
- Added `scripts/collect_v020_method_unblock_smokes.py`.
- Added external workbench files under `/data/protein-design` for
  `pd-pyrosetta-methods-gpu:0.20` and `run_v020_unblock_smokes.py`.

### Changed

- Bumped project version to `1.2.8`.
- Updated validator coverage for v0.20 unblock rows, external path boundaries,
  timeout/blocker checks and claim gates.
- Updated index, README, Benchmark README, AGENTS and project log for v0.20.

### Notification

- The independent PyRosetta Dockerfile no longer relies on the BindCraft image.
- `pd-pyrosetta-methods-gpu:0.20` now builds from the RosettaCommons quarterly
  US West mirror and passes `pyrosetta.init("-mute all")` in both
  `bench-diffpepbuilder` and `bench-pyrosetta`.
- DiffPepBuilder v0.20 unblock smoke passed on GPU for one method-provided
  example after setting `experiment.num_loader_workers=1`.
- PepMirror is no longer blocked by the PyRosetta image route, but remains
  blocked by unresolved checkpoint manifest/download evidence.
- PepGLAD remains blocked by unresolved GitHub release asset names.
- D-Flow remains blocked by missing `test_set`/`PepMerge`/`pep_cache` inputs.
- BindCraft reached GPU trajectory execution with smoke-only settings but exited
  by timeout with code `124`; no new permission blocker was observed.

### Boundaries

- No `target_set_v0.csv` promotion.
- No scoring or method-ranking evidence.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No raw logs, Docker layers, private PyRosetta credentials or non-public Rosetta materials, model weights,
  third-party source trees, generated structures or large outputs are stored in
  the KB.

## v1.2.7 External Method Install And Example-Smoke Readiness - 2026-07-07

This checkpoint adds the v0.19 external method install/example-smoke readiness
layer. It records method-provided example or preflight outcomes for all 10
first-wave methods while keeping formal Benchmark results out of scope.

### Added

- Added `benchmark/deployment/method_source_doc_verification_v0.19.csv`.
- Added `benchmark/deployment/method_install_smoke_manifest_v0.19.csv`.
- Added `benchmark/deployment/method_smoke_test_results_v0.19.csv`.
- Added `ops/audits/method_install_smoke_audit_v0.19.md`.
- Added `scripts/collect_v019_method_smokes.py`.

### Changed

- Bumped project version to `1.2.7`.
- Updated validator coverage for v0.19 method smoke rows, external path
  boundaries, no-overclaim checks and claim gates.
- Updated index, README, Benchmark README and project log for v0.19.

### Notification

- PepMLM and RFdiffusion + ProteinMPNN have GPU example-smoke evidence, with a
  PepMLM noncanonical-output caveat and an RFdiffusion-to-ProteinMPNN handoff
  gap.
- OSPREY3 has CPU route probe evidence.
- PepGLAD and D-Flow have GPU preflight evidence but remain blocked by
  checkpoint and input-contract gaps.
- DiffPepBuilder progressed through receptor processing and ESM embedding but
  remains blocked at `pyrosetta` import.
- BindCraft received a `libgfortran5` image repair but the CD47 peptide quick
  example timed out before accepted design generation.

### Boundaries

- No `target_set_v0.csv` promotion.
- No scoring or method-ranking evidence.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No raw logs, Docker layers, model weights, ESM checkpoints, third-party source
  trees, generated structures or large outputs are stored in the KB.

## v1.2.6 Batch B Pilot Gates And Adapter Replay Fixtures - 2026-07-07

This checkpoint adds the v0.17 pilot-gate layer and v0.18 adapter replay
fixture layer. It moves the project from planning-only adapter requirements
toward repeatable parser evidence while keeping formal Benchmark results out of
scope.

### Added

- Added `benchmark/input_sets/batch_b_pilot_target_gate_v0.17.csv`.
- Added `benchmark/input_sets/batch_b_pilot_job_manifest_v0.17.csv`.
- Added `benchmark/deployment/batch_b_pilot_method_scope_v0.17.csv`.
- Added `benchmark/deployment/adapter_replay_fixture_manifest_v0.18.csv`.
- Added `benchmark/results/batch_a_replay_method_output_manifest_v0.18.csv`.
- Added `benchmark/results/batch_a_replay_candidate_outputs_v0.18.csv`.
- Added `benchmark/results/batch_a_replay_run_v0.18.csv`.
- Added `scripts/parse_batch_a_replay_fixtures.py`.
- Added v0.17/v0.18 readiness and replay audits.

### Changed

- Bumped project version to `1.2.6`.
- Updated validator coverage for v0.17 pilot gates, v0.18 replay fixtures,
  replay result rows, parser caveats and no-overclaim boundaries.
- Updated index, README, Benchmark README, AGENTS and project log for v0.17 and
  v0.18.
- Added v0.17/v0.18 claim boundaries to the manuscript claim-evidence map.

### Notification

- RCSB metadata checks were used to populate fixture-level chain and sequence
  gates for 3EQS, 1SJH and 7ZKR.
- PepMLM replay parsing retains a `partial` status because the v0.15 smoke
  output contains `X`.
- ProteinMPNN and RFpeptide/RFdiffusion v0.15 outputs can now be parsed into
  small `candidate_outputs` and `run` fixture rows.

### Boundaries

- No new method execution.
- No new model, data or checkpoint download.
- No `target_set_v0.csv` promotion.
- No scoring, performance ranking or complete Benchmark result.
- No method promotion to `smoke_test_ready` or `benchmark_ready`.

## v1.2.5 Adapter Parser Hardening And Batch B Review Planning - 2026-07-07

This checkpoint adds the v0.16 planning layer that turns v0.15 minimal
smoke-test evidence into adapter/parser hardening requirements and a controlled
Batch B target review queue. It is an interface and governance update only.

### Added

- Added `benchmark/deployment/adapter_parser_hardening_matrix_v0.16.csv`.
- Added `benchmark/input_sets/batch_b_target_review_queue_v0.16.csv`.
- Added `benchmark/protocols/adapter_replay_contract_v0.16.md`.
- Added `ops/plans/adapter_parser_hardening_plan_v0.16.md`.

### Changed

- Bumped project version to `1.2.5`.
- Added v0.15/v0.16 claim boundaries to
  `manuscript/support/benchmark_manuscript_claim_evidence_map.csv`.
- Updated validator coverage for v0.16 adapter/parser rows, target review rows,
  required plan/contract files and no-overclaim boundaries.
- Updated index, README, Benchmark README, AGENTS and project log for v0.16.

### Notification

- v0.16 prioritizes PepMLM, ProteinMPNN, RFpeptide/RFdiffusion and the
  RFdiffusion-to-ProteinMPNN handoff for adapter/parser hardening.
- DiffPepBuilder, PepGLAD, D-Flow / PeptideDesign and AfCycDesign /
  ColabDesign remain in preflight caveat queues until dependency, checkpoint or
  CLI-route blockers are resolved.
- Batch B target candidates are now represented as a review queue, not as
  frozen targets.

### Boundaries

- No new method execution.
- No new model, data or checkpoint download.
- No `target_set_v0.csv` promotion.
- No scoring, performance ranking or complete Benchmark result.
- No method promotion to `smoke_test_ready` or `benchmark_ready`.

## v1.2.4 External Preflight And Batch A Minimal Smoke Evidence - 2026-07-07

This checkpoint adds the v0.15 execution-evidence layer for the external
`/data/protein-design` workbench. It records one built shared benchmark image,
five import-level preflight checks and three minimal Batch A smoke tests as
readiness evidence only.

### Added

- Added `benchmark/deployment/run_preflight_results_v0.15.csv`.
- Added `benchmark/deployment/batch_a_smoke_test_results_v0.15.csv`.
- Added `ops/audits/batch_a_execution_audit_v0.15.md`.

### Changed

- Bumped project version to `1.2.4`.
- Updated validator coverage for v0.15 preflight and Batch A smoke-test
  summaries.
- Updated index, README, Benchmark README, AGENTS and project log for the
  external minimal execution-evidence layer.

### Notification

- `pd-benchmark-methods-gpu:0.13` was built externally as
  `sha256:affbdab88d8a4f017701e60a0538682b43a27e15bcd0c9f9add3dac8c4b93710`.
- Import-level checks passed for PepMLM, DiffPepBuilder, PepGLAD,
  D-Flow / PeptideDesign and AfCycDesign / ColabDesign cyclic peptide, with
  CPU or extension caveats retained where observed.
- Minimal Batch A smoke tests passed for PepMLM, ProteinMPNN and
  RFpeptide/RFdiffusion using external workbench inputs and caches.

### Boundaries

- No `target_set_v0.csv` promotion.
- No scoring or performance ranking.
- No complete Benchmark result.
- No biological or experimental validation claim.
- No raw logs, model caches, Docker layers, PDB/TRB/trajectory files, weights,
  third-party source trees or large outputs are stored in the KB.

## v1.2.3 Academic-Search Target Candidate And Method Case Planning - 2026-07-07

This checkpoint adds the v0.14 academic-search layer for candidate peptide
targets, method-paper cases and dataset/panel references. It records literature
examples and candidate panels for later schema review; it is not a target-set
freeze or execution layer.

### Added

- Added `benchmark/method_sources/method_paper_case_matrix_v0.14.csv`.
- Added `benchmark/input_sets/target_candidate_academic_search_v0.14.csv`.
- Added `ops/plans/target_candidate_academic_search_plan_v0.14.md`.
- Added `ops/audits/target_candidate_academic_search_audit_v0.14.md`.

### Changed

- Bumped project version to `1.2.3`.
- Updated validator coverage for v0.14 method-paper cases and academic-search
  target candidates.
- Updated index, README, Benchmark README, input-set README, method-source
  README, AGENTS and project log for the academic-search target/case layer.

### Notification

- Candidate targets now include method-paper cases and panels such as NCAM1,
  AMHR2, MDM2/3EQS, MHCII/1SJH, 3CLpro/7Z4S, ALK1/6SF1, TNF/7KP7,
  PepBench/LNR, PepMerge, PEPBI, GPCR 124 complexes, pMHC targets and Chang
  ranking cases.
- The next review queue should focus on exact chain/sequence extraction,
  controls, assay evidence, license, data route and leakage checks before any
  target-set promotion.

### Boundaries

- No target-set freeze.
- No data download.
- No model weights.
- No method installation.
- No Docker/GPU benchmark run.
- No smoke-test evidence.
- No local reproducibility or method-performance claim.

## v1.2.2 Docker Image Assignment And Benchmark Environment Scaffold - 2026-07-07

This checkpoint adds the v0.13 Docker image/environment assignment layer. It
records which `/mnt/ssd4t/protein-design` images should be reused and defines a
shared multi-conda benchmark image scaffold for first-wave methods that do not
already have dedicated local images.

### Added

- Added `benchmark/deployment/docker_image_inventory_v0.13.csv`.
- Added `benchmark/deployment/method_environment_assignment_v0.13.csv`.
- Added `ops/plans/protein_design_image_consolidation_plan_v0.13.md`.
- Added `ops/audits/docker_environment_assignment_audit_v0.13.md`.

### Changed

- Bumped project version to `1.2.2`.
- Updated validator coverage for v0.13 image inventory and method-environment
  assignment rows.
- Updated index, README, Benchmark README, AGENTS and project log for the
  image/environment scaffold layer.

### Notification

- Existing RFdiffusion/RFpeptide, ProteinMPNN/Foundry, BindCraft, AF2/AF3,
  Rosetta, PepMimic and RFpeptide images under `/mnt/ssd4t/protein-design` are
  assigned for reuse.
- The external workbench now contains a `pd-benchmark-methods-gpu:0.13`
  Dockerfile scaffold with separate conda environments for PepMLM,
  DiffPepBuilder, PepGLAD, D-Flow/PeptideDesign and ColabDesign.

### Boundaries

- No new image build was recorded in the KB.
- No model weights.
- No dataset download.
- No third-party source stored in the KB.
- No method installation evidence.
- No Docker/GPU benchmark run.
- No target-set freeze.
- No local reproducibility or method-performance claim.

## v1.2.1 Repository Checkpoint, Preflight Interfaces, And Source Clone Audit - 2026-07-07

This checkpoint collects the v0.10 structure/preflight layer, v0.11 source-I/O adapter planning layer, v0.12 external source-code clone audit, and v1.3 grant-style planning supplement into one repository commit. It remains a protocol/readiness release, not a benchmark-result release.

### Added

- Added v0.10 structure and server preflight planning artifacts.
- Added v0.11 job/adapter interface schemas and artificial example manifests.
- Added v0.12 source clone manifest and source-code clone audit.
- Added v1.3 grant-style mock review planning artifacts.

### Changed

- Bumped project version to `1.2.1`.
- Reorganized repository paths into `sources/`, `kb/`, `benchmark/`, `manuscript/`, and `ops/`.
- Updated validator coverage for v0.10/v0.11/v0.12/v1.3 control-plane artifacts.
- Updated index, README, Benchmark README, AGENTS and project log for the checkpoint.

### Notification

- The first-wave include-method source code is now externally checked out under `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark`.
- The KB records source checkout provenance only; third-party source trees remain outside the tracked repository.
- RFdiffusion and ProteinMPNN Docker assets under `/data/protein-design` remain separate from source provenance.

### Boundaries

- No model weights.
- No dataset download.
- No environment install.
- No Docker or GPU run.
- No target-set freeze.
- No smoke-test execution.
- No local reproducibility or method-performance claim.

## v0.12 Source Code Clone Audit - 2026-07-07

### Added

- Added `benchmark/deployment/source_clone_manifest_v0.12.csv`.
- Added `ops/audits/source_code_clone_audit_v0.12.md`.
- Cloned and checked out 11 first-wave method source repositories under `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark`.

### Changed

- Updated validator coverage for v0.12 source clone rows and no-overclaim boundaries.
- Updated index, README, Benchmark README and project log for the source-only external checkout layer.

### Boundaries

- Source clone only.
- No model weights.
- No dataset download.
- No environment install.
- No Docker or GPU run.
- No target-set freeze.
- No smoke-test execution.
- No local reproducibility or method-performance claim.

## v0.11 Source/I-O And Initial Smoke-Test Planning - 2026-07-07

### Added

- Added `ops/plans/source_io_smoke_test_plan_v0.11.md`.
- Added `benchmark/protocols/job_manifest_schema_v0.11.md`.
- Added `benchmark/protocols/adapter_output_schema_v0.11.md`.
- Added `benchmark/input_sets/example_job_manifest_v0.11.csv`.
- Added `benchmark/results/example_method_output_manifest_v0.11.csv`.
- Added `benchmark/results/example_candidate_outputs_v0.11.csv`.
- Added `benchmark/deployment/source_freshness_manifest_v0.11.csv`.
- Added `benchmark/deployment/adapter_preflight_status_v0.11.csv`.
- Added `benchmark/deployment/method_contracts/batch_a_adapter_contract_v0.11.md`.

### Changed

- Extended `run.csv` and scoring-output protocol docs with a non-breaking v0.11 adapter layer.
- Updated validator coverage for v0.11 schemas, manifests, placeholder rows and no-execution boundaries.
- Updated index and README navigation for the new source/I-O/smoke-test planning artifacts.

### Boundaries

- No clone.
- No download.
- No install.
- No model weights.
- No GPU run.
- No target-set freeze.
- No smoke-test execution.
- No local reproducibility or method-performance claim.

## v0.10 Structure And Preflight Planning - 2026-07-07

### Added

- Added `ops/plans/server_preflight_plan_v0.10.md`.
- Added `benchmark/deployment/preflight_download_approval_v0.10.csv`.
- Added `benchmark/deployment/method_preflight_status_v0.10.csv`.
- Added `benchmark/input_sets/target_control_freeze_checklist_v0.10.md`.
- Added `ops/migration/file_role_map_v0.10.csv`.

### Changed

- Reorganized top-level artifacts into `sources/`, `kb/`, `benchmark/`, `manuscript/`, and `ops/`.
- Moved current and historical plans, audits, validation output, build summary, and project log under `ops/`.
- Moved manuscript outlines, figures, claim gates, reference planning, and paper support reports under `manuscript/`.
- Updated scripts, index, README, AGENTS, and validator expectations for the new paths.

### Boundaries

- No clone.
- No download.
- No install.
- No model weights.
- No GPU run.
- No target-set freeze.
- No smoke-test execution.
- No local reproducibility or method-performance claim.

## v1.2.0 Chinese Manuscript Figure/Table Embedding Layer - 2026-06-18

This release adds a manuscript presentation layer on top of the v0.9.0 current plan, v1.0 bilingual outlines and v1.1 supplementary-source synthesis.

### Added

- Added four project-local manuscript figure assets under `manuscript/assets/figures/`.
- Added `manuscript/assets/figures/imagegen_prompt_record_v1.md` to record figure-generation intent and claim boundaries.
- Embedded four conceptual figures into `manuscript/outlines/benchmark_manuscript_outline_zh_v1.md`.
- Embedded four CSV-derived Markdown tables into the Chinese manuscript outline:
  - `kb/tables/candidate_method_classification_v1.csv`
  - `benchmark/input_sets/reference_dataset_sources_v1.csv`
  - `kb/tables/scoring_metric_rationale_matrix_v1.1.csv`
  - `benchmark/deployment/method_readiness_review_v0.8.csv`

### Changed

- Updated the Chinese manuscript outline from a figure/table plan list to a reader-facing draft section with figure captions, CSV provenance notes, and translated table display fields.
- Updated validator coverage for manuscript figure assets, figure prompt record, embedded table source references, and the "not real benchmark result" boundary.
- Bumped project version to `1.2.0`.

### Boundaries

- No benchmark execution.
- No new include methods.
- No data download, source clone, environment install, model-weight fetch, or GPU task.
- Figure assets are conceptual manuscript schematics, not experimental results or local reproducibility evidence.
- Embedded tables come from existing project CSV artifacts; the source CSV files remain the complete evidence records.

## v1.1 Supplementary-Source Synthesis Layer - 2026-06-18

Supplementary-source synthesis update on top of the v0.9.0 plan and v1.0 bilingual manuscript-outline layer.

### Added

- Added `manuscript/support/supplementary_materials_reference_value_v1.1.md`.
- Added `manuscript/support/short_peptide_scoring_rationale_v1.1.md`.
- Added `manuscript/support/cyclic_peptide_benchmark_supplement_v1.1.md`.
- Added `kb/tables/supplementary_materials_action_matrix_v1.1.csv`.
- Added `kb/tables/scoring_metric_rationale_matrix_v1.1.csv`.
- Added `kb/tables/method_landscape_patch_candidates_v1.1.csv`.

### Changed

- Updated Chinese and English manuscript outlines with v1.1 supplementary-source scoring boundaries.
- Updated sync map, TODO list, claim-evidence map, README, index, and validator expectations.

### Boundaries

- No include-method changes.
- No target-set promotion.
- No data download, source clone, environment install, model-weight fetch, GPU task, or Benchmark result.

## v0.9.0 - 2026-06-18

Plan and Benchmark manuscript synchronization release.

### Added

- Added `ops/plans/updated_plan_v0.9.md` as the current authoritative plan.
- Added validator coverage for v0.9 plan, Benchmark template artifacts, review synthesis artifacts, and method landscape watchlist.
- Added claim boundaries for review-driven method landscape mapping and manuscript planning.

### Changed

- Synchronized `VERSION`, `README.md`, `index.md`, `ops/log.md`, manuscript outline, claim-evidence map, and validation report with v0.9.
- Promoted `ops/plans/updated_plan_v0.9.md` as the current plan entry point while preserving `ops/plans/updated_plan_v0.6.md` as historical context.
- Kept `benchmark/method_sources/method_landscape_watchlist_v0.9.csv` as a landscape/watchlist artifact, not an include-method scorecard.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 27 method landscape rows
- 6 v0.8 dataset schema review rows
- 8 v0.8 download manifest rows
- 4 v0.8 method readiness rows
- 46 manuscript claim rows
- 0 validation errors
- 0 validation warnings

### Not Included

- No dataset downloads.
- No third-party source clones.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No frozen target set promotion.
- No claim of local reproducibility or method performance.

## v0.8.0 - 2026-06-09

License, schema, and input-contract readiness release.

### Added

- Added `benchmark/input_sets/dataset_supplement_schema_review_v0.8.csv`.
- Added `benchmark/deployment/method_readiness_review_v0.8.csv`.
- Added `benchmark/deployment/download_manifest_v0.8.csv`.
- Added `ops/audits/license_schema_input_contract_review_v0.8.md`.

### Changed

- Updated priority method contracts with v0.8 license, environment, checkpoint, and blocker evidence.
- Updated validator coverage for v0.8 readiness artifacts.
- Kept all future download rows at `download_performed=no`.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 6 v0.8 dataset schema review rows
- 8 v0.8 download manifest rows
- 4 v0.8 method readiness rows
- 0 validation errors
- 0 validation warnings

### Not Included

- No dataset downloads.
- No third-party source clones.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No target-set promotion.
- No claim of local reproducibility.

## v0.7.0 - 2026-06-06

Server dry-run contract and placeholder input release.

### Added

- Added method-level contracts for PepMLM and RFdiffusion + ProteinMPNN.
- Added a dependency-only PepMirror contract.
- Added artificial `benchmark/input_sets/example_run.csv` rows with `status=not_real_benchmark`.
- Added `benchmark/deployment/download_manifest_template_v0.7.csv`.
- Added `benchmark/input_sets/dataset_supplement_schema_review_v0.7.csv`.

### Changed

- Updated `run_csv_schema.md` to allow `not_real_benchmark` for placeholder rows only.
- Updated manuscript outline and claim-evidence map with v0.7 dry-run contract boundaries.
- Updated ARS action-item statuses for outline, claim-gate, and example-run work.
- Updated validator, project version, index, log, and README for v0.7.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 2 example run rows
- 1 download manifest placeholder row
- 6 dataset schema review rows
- 11 ARS action rows
- 33 manuscript claim rows
- 0 validation errors
- 0 validation warnings

### Not Included

- No dataset downloads.
- No third-party source clones.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.

## v0.6.0 - 2026-06-06

Academic Research Suite review and server dry-run planning release.

### Added

- Added `ops/audits/academic_research_suite_review_v0.6.md`.
- Added `ops/plans/updated_plan_v0.6.md`.
- Added `kb/tables/ars_review_action_items_v0.6.csv`.
- Added `benchmark/input_sets/dataset_supplement_watchlist_v0.6.csv`.
- Added `benchmark/deployment/server_smoke_test_contract_v0.6.md`.

### Changed

- Updated manuscript outline and claim-evidence map with v0.6 ARS review, dataset watchlist, and server dry-run boundaries.
- Updated validator to check ARS action items, dataset supplement watchlist, server gate contract, and v0.6 review/plan sections.
- Updated project version, index, log, and README for v0.6.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 10 ARS review action rows
- 6 dataset supplement watchlist rows
- 29 manuscript claim rows
- 0 validation errors
- 0 validation warnings

### Not Included

- No dataset downloads.
- No third-party source clones.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.

## v0.5.0 - 2026-06-03

Availability and server-readiness audit release for the peptide-design Benchmark KB.

### Added

- Added `benchmark/availability/link_availability_matrix_v0.5.csv` and `data_access_manifest_v0.5.csv`.
- Added `ops/audits/link_and_data_availability_audit_v0.5.md`.
- Added `benchmark/method_sources/source_pin_audit_v0.5.csv` covering all 10 include methods.
- Added `benchmark/input_sets/target_candidate_matrix_v0.5.csv`.
- Added `benchmark/deployment/server_readiness_checklist_v0.5.md` for Linux CUDA Conda/mamba deployment planning.

### Changed

- Updated validator to check v0.5 availability, data access, source pin, target candidate, and server readiness artifacts.
- Updated project version, index, log, and README for v0.5.
- Kept Overath as ranking/rescoring and scoring-calibration evidence, not peptide-generation performance evidence.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 10 v0.5 source pin rows
- 23 v0.5 link availability rows
- 7 v0.5 data access rows
- 9 v0.5 target candidate rows
- 0 validation errors
- 0 validation warnings

### Not Included

- No dataset downloads.
- No third-party source clones.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.

## v0.4.0 - 2026-06-03

Expert-panel and small-file audit release for the peptide-design Benchmark KB.

### Added

- Added `ops/audits/expert_panel_review_v0.4.md` and `kb/tables/expert_review_action_items.csv`.
- Added `benchmark/input_sets/dataset_readiness_scorecard.csv` and `target_candidate_matrix_v0.4.csv`.
- Added `benchmark/method_sources/source_pin_audit_v0.4.csv`.
- Performed external-only audit of Overath `final_dataset.csv` and priority source pins for PepMLM, RFdiffusion, ProteinMPNN, and PepMirror.

### Changed

- Updated manuscript outline and claim-evidence map with expert-panel, dataset readiness, target-candidate, and source-pinning boundaries.
- Updated validator to check v0.4 tables, expert-role coverage, source pinning status, Overath non-generation boundary, and large-file protection.
- Updated project version, index, log, and README for v0.4.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 15 expert review action rows
- 7 dataset readiness rows
- 9 target candidate rows
- 4 source pin rows
- 0 validation errors
- 0 validation warnings

### Not Included

- No full dataset downloads into git.
- No third-party source trees in git.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.

## v0.3.0 - 2026-06-03

Dataset/source/environment audit release for the peptide-design Benchmark KB.

### Added

- Added `benchmark/input_sets/candidate_benchmark_datasets.csv` and `ops/audits/dataset_candidate_audit.md`.
- Added the bioRxiv/Zenodo candidate dataset `overath_binder_success_2025` for ranking/rescoring and scoring calibration planning.
- Added `benchmark/method_sources/README.md`, `benchmark/method_sources/method_source_manifest.csv`, and `ops/audits/method_source_audit.md`.
- Added `benchmark/environments/README.md`, `benchmark/environments/environment_feasibility_matrix.csv`, and `ops/audits/environment_feasibility_audit.md`.

### Changed

- Updated the validator to require candidate dataset, method source, and environment feasibility coverage.
- Updated index, README, manuscript outline, claim-evidence map, and input-set documentation for v0.3.
- Kept Overath binder-success data as metadata-only in v0.3; it is treated as scoring calibration/ranking evidence, not as peptide-specific generation benchmark evidence.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 7 candidate dataset rows
- 10 method source rows
- 10 environment feasibility rows
- 10 included benchmark methods
- 10 smoke-test README files
- 0 validation errors

### Not Included

- No dataset downloads.
- No method source clones.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.

## v0.2.0 - 2026-06-03

Protocol-readiness release for the peptide-design Benchmark KB.

### Added

- Added Benchmark protocol layer with `benchmark/protocols/benchmark_protocol_v0.md`, `run_csv_schema.md`, and `scoring_outputs_schema.md`.
- Added `benchmark/smoke_tests/` planning READMEs for all 10 included methods.
- Added PepMirror as a first-wave include method and created the corresponding method/candidate evidence layer.
- Added `kb/tables/method_runnability_matrix.csv` and `ops/audits/method_runnability_audit.md`.
- Added local Zotero Benchmark/scoring/developability lesson layer with `kb/tables/benchmark_literature_lessons.csv` and `manuscript/support/benchmark_literature_lessons.md`.
- Added target/control planning schemas: `target_set_v0.csv`, `target_set_v0_schema.md`, and `negative_design_panel_schema.md`.
- Added Benchmark manuscript outline, claim-evidence map, and figure/table plan for a protocol-first manuscript.

### Changed

- Split candidate interpretation into `scientific_priority` and `engineering_readiness`, while keeping `tier` only as smoke-test scheduling shorthand.
- Split generation benchmark from ranking/rescoring benchmark in protocol and manuscript framing.
- Expanded scoring schema with `developability`, `negative_design`, and `leakage_homology` metric families.
- Updated project index, log, README, and validator to reflect the v0.2 protocol/calibration layer.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` passes with:

- 432 master manifest rows
- 125 included literature rows
- 10 included benchmark methods
- 10 runnability rows
- 8 benchmark literature lesson rows
- 17 manuscript claim-evidence rows
- 10 smoke-test README files
- 12 method cards
- 120 literature cards
- 432 BibTeX entries
- 0 validation errors
- 0 validation warnings

### Not Included

- No actual benchmark runs.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.
- No Zotero, EndNote, or upstream PD-wiki writes.

## v0.1.0 - 2026-06-03

Initial repository version for the peptide-design method benchmark background knowledge base.

### Added

- Bootstrapped AI-native knowledge-base structure with `sources/raw_snapshots/`, `kb/references/`, `kb/tables/`, `kb/wiki/`, `reports/`, and `scripts/`.
- Exported and deduplicated Zotero-derived metadata into `kb/tables/master_literature_manifest.csv`.
- Generated 120 literature cards, 11 method cards, 9 benchmark candidate cards, and concept pages.
- Generated first-wave candidate shortlist with 9 included methods and 2 watchlist methods.
- Added URL status evidence for method repositories, Hugging Face pages, and Zenodo routes.
- Added reproducible build and validation scripts.

### Validation

`python scripts/validate_benchmark_kb.py` passes with:

- 432 master manifest rows
- 125 included literature rows
- 11 method evidence rows
- 9 included benchmark methods
- 432 BibTeX entries
- 0 validation errors
- 0 validation warnings

### Not Included

- No actual benchmark runs.
- No downloaded model weights.
- No downloaded PDFs.
- No EndNote source libraries.
