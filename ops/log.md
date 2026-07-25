# Project Log

## [2026-07-14] execution | PepGLAD v0.35 基础设施启动失败
- 将 `ops/plans/updated_plan_v0.35.md` 设为当前计划；v0.34 保持 6/7 历史状态，`VERSION` 保持 `1.2.21`。
- 为 PepGLAD 增加 mixed L/D report-only 连通性通道、固定 baseline warning policy、唯一 seed42 job、exact-schema parser、独立 Harness/validator 和 fail-closed scoring guard。
- 设计、RED tests、编码和独立复审由不同 subagents 完成；执行前核心 v0.34/v0.35 回归为 501 passed，额外 Harness/validator focused tests、`py_compile` 与 `git diff --check` 通过。
- 唯一授权的 `attempt_001` 在容器启动前因无法访问 Docker API socket 失败：`runtime_seconds=0.026`、`exit_code=1`、parser/QC=`not_run`。host 侧 source/model/target 前检已通过，但容器内 PepGLAD、OpenMM、parser 和 QC 均未执行。
- `raw/` 中没有 candidate 或 runtime evidence，解析器拒绝发布 v0.35 connectivity bundle。该记录不支持 PepGLAD 方法失败、mixed L/D、连通性、scoring 或 ranking 结论。
- 新增 `ops/audits/v035_pepglad_connectivity_audit.md`。`attempt_001` 不得覆盖或自动重试；新的执行需要再次明确授权并更新 attempt 政策。
- 验收引擎现将尚未生成的 v0.35 条件性 bundle 交给对应 gate 判定，而不是报 Harness 程序错误；最终 `current.v035_bounded_connectivity` 为 Critical `FAIL`，项目为 `not_accepted`。全量测试 `1361 passed`，KB validator 为 0 errors、0 warnings，`git diff --check` 通过。

## [2026-07-12] evidence | PepGLAD failure-only 诊断留痕
- 新增 `benchmark/results/pilot_failure_diagnostics_v0.34.json`，只保存 PepGLAD seed42 `attempt_003` 的 1 条 tracked failure-only diagnostic provenance。原有计数保持为 13 条 method-output manifest、12 条 candidate/QC、12 条 candidate runtime provenance 和 14 条 run rows，主运行仍为 6/7。
- 该记录绑定 `AWHITLLIFTH` sequence summary、OpenMM 前 SHA-256 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b` 与 L6/D5、OpenMM 后 SHA-256 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6` 与 L4/D7、固定 baseline mismatch，以及 source/model/target/observer/patch/wrapper 等 producer pins。
- 这 1 条记录不计入 12 条 candidate runtime provenance，也不是候选、QC、评分、排名或完整复现证据。它不证明模型根因，也不排除 OpenMM 的影响。

## [2026-07-12] documentation | PepGLAD seed42 诊断与 v0.34 claim surface 校正
- 最新 compact merge 包含 13 条 method-output manifest、12 条 candidate、12 条 candidate QC、12 条 runtime provenance 和 14 条 run rows；6 个 primary 与对应的 6 个 eligible seed43 extensions 获得 `supported`。PepGLAD 最新候选缺席，seed43 未运行。
- PepGLAD seed42 `attempt_003` 的 target preflight 与 source/model/observer/patch/wrapper/instrumented-source pins 通过，进程退出码为 0；parser=`pepglad_seed42_replay_mismatch`，merge=`evidence_incomplete`。sequence summary 仍为 `AWHITLLIFTH`，但未晋升候选。
- OpenMM 前 B 链 SHA-256 为 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`、手性为 L6/D5；OpenMM 后 SHA-256 为 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`、手性为 L4/D7，且不同于固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。历史 `attempt_002` 为 `AWHITLLIFTH`、L4/D7，文件 SHA-256 与 baseline 相同。
- `first_observed_chirality_failure_stage=pre_openmm_snapshot` 支持混合手性在本 attempt 的 OpenMM 前已可观察，但不证明模型根因，也不排除 OpenMM 的影响；L/D 计数从 6/5 变为 4/7。
- 现有官方入口没有符合当前协议的 method-native skip-relax 或 idealize 选项。按已批准的停止条件，本轮不再发起第二个诊断 attempt，也不运行 PepGLAD seed43。继续执行需另行批准协议/source-policy 变更，或接受 PepGLAD 在当前 fixture 上失败；均不能直接进入评分。
- 保留 D-Flow 3EQS 训练重叠、RFdiffusion all-Gly backbone 与独立 ProteinMPNN FASTA、PepMLM `WWX`/`X` 边界。`current.v034_bounded_connectivity` 仍为 6/7 Critical `FAIL`；没有 scoring、ranking、frozen target 或 wet-lab，`VERSION` 保持 `1.2.21`。

## [2026-07-11] engineering | v0.34 Harness evidence hardening
- 将 13 条 compact runtime provenance 绑定到原始 JSON SHA-256 和 canonical semantic SHA-256；额外、重复或未绑定 candidate 的 provenance 现在 fail closed。
- 在 merge 层把缺失的 method-specific QC status 显式归一为 `not_applicable`，保留 PepGLAD parsed-but-QC-failed 行，并用 `supported_candidate` 区分 13 条 parsed rows 与 12 条 supported rows。
- 加强 D-Flow source/checkpoint/host-environment 绑定、PepMirror source/image/checkpoint/pre-run/mirror-geometry 绑定，以及 RFdiffusion TRB 安全语义解析、source/environment/path 和未线程化 backbone-to-FASTA handoff 绑定。
- scoring guard 新增常见结构置信度、能量和亲和力字段拦截；claim surface 分开记录解析/QC、RF 结构限制、provenance 限制和 D-Flow leakage 边界。
- 未启动 scoring、ranking、frozen target 或 wet-lab；`VERSION` 保持 `1.2.21`。

## [2026-07-11] documentation | v0.34 读者事实边界校正
- 明确 7 个 seed42 primary 输出均可解析，其中 6 个通过基础 QC。PepGLAD 序列为 `AWHITLLIFTH`，手性统计为 L4/D7，因此为 `qc_failed`；PepGLAD seed43 未运行。
- 记录 6 个 eligible seed43 extensions 均通过，13 个已执行 job 均有 runtime provenance。
- 明确 RFdiffusion 输出是未线程化 all-Gly backbone，ProteinMPNN FASTA 是独立 handoff，当前没有 sequence-resolved structure。
- 明确历史 DiffPepBuilder 和 PepGLAD attempt 缺少新增 target preflight 字段，13 条 provenance 不能支持完整可复现声明。
- 保留 D-Flow 3EQS 已知 train overlap 边界；没有 scoring、ranking、frozen target 或 wet-lab 证据。
- 更新项目总览、Benchmark 结果说明、索引、release notes、v0.34 审计和 claim-evidence map；`VERSION` 保持 `1.2.21`。

## [2026-07-11] execution | v0.34 受限生成连通性
- 将 `ops/plans/updated_plan_v0.34.md` 设为当前科研与执行计划；v0.33 保留为历史 blocker 基线，`VERSION` 保持 `1.2.21`。
- 为 PepMLM、DiffPepBuilder、PepGLAD、D-Flow、PepMirror、AfCycDesign / ColabDesign 和 RFdiffusion + ProteinMPNN 接入受限生成 adapter、不可覆盖 attempt、标准 parser 与公共 QC。
- 7 个 seed42 主运行中 6 个通过。PepGLAD 输出可解析且为 11 aa，但 11 个可判定残基中有 4 个 L、7 个 D，不符合 L-peptide 合同，因此为 `qc_failed`。
- 只有 6 个主运行通过的方法进入 seed43；这 6 个扩展运行全部通过，PepGLAD seed43 未运行。
- PepMLM 两个 seed 均为 `WWX`，状态为 `pass_with_warning`。D-Flow 的 3EQS fixture 有已知训练重叠，只支持连通性检查。
- 写入 v0.34 job/execution 清单和 compact execution、method-output、candidate、QC、run、merge-summary 证据；原始结构与日志留在 gitignored `benchmark_runs/v0.34/`。
- `current.v034_bounded_connectivity` 要求主运行 7/7 通过，当前为 Critical `FAIL`，所以 `current_phase` 不能签核。人工批准不能跳过该失败。
- 下一步检查 PepGLAD 生成坐标、链映射和手性处理，修复后新建 attempt 重跑 seed42；通过后才执行 seed43。未开始 scoring、ranking、target freeze 或 wet-lab。

## [2026-07-11] governance | 对话签核安全收口（待实际批准）
- 将 source manifest 的 SHA-256 绑定到 Git clean 后实际进入 commit 的 blob；CRLF/text normalization 与 binary blob 均按提交字节验证。
- Transport、staging、history、diff-check 与 clean-checkout materialization 改用受控配置或隔离 gitdir，阻断 late hooks、clean/smudge/process filters、fsmonitor、external diff/textconv、URL rewrite、replacement refs 与 deprecated grafts。
- Push 在隔离对象图中验证真实 fast-forward ancestry，再以 card-bound expected-old-OID lease 执行 receive-time CAS，并确认远端 OID；不允许 non-fast-forward 或无条件 force-push。
- `governance` 与 `current_phase` 复签均优先 supersede 完整 current evaluation context 的最新前序签核；首次签核仍为 `null`，stale predecessor 只在没有 current predecessor 时作为审计链回退。
- Production signoff 在任何读取或 Git 检查前必须通过 `lstat` direct-regular-file 判定；FIFO、目录、symlink 或其他非普通文件均为 untrusted。
- Source-only recovery 在 source commit 的临时 clean checkout 中执行 prepare/clean 验证；若 pre-ref 失败留下 staged signoff，只接受与卡片派生 manifest 的 path/mode/blob SHA-256 完全一致的 index，extra/different staged 状态 fail closed，且恢复不重复 source/signoff。
- 保持边界：尚未生成真实审批卡，尚未提交或 push；`VERSION=1.2.21`，v0.33 仍为 10 条 blocker rows 与 0 parsed/generated candidates。

## [2026-07-10] governance | 对话签核事务（待实际批准）
- 新增当前受信任 Codex 会话内的审批卡流程：运行 `prepare-review` 和展示卡片前必须停止全部 subagents 并确认其 quiescent；只有展示未过期卡后的消息经 NFC 规范化和 trim 后完整内容恰好为 `批准` 才有效，该会话信任不是 cryptographic identity。卡片展示后任何介入的非精确 `批准` 用户消息都会使卡失效，必须重新 prepare 并展示新卡。
- 固定 bundle 同时审阅 `governance` 与 `current_phase`，并生成两份 profile-bound `governance_owner` signoff；任何签核均不能 waiver Critical/Major failure，也不批准 `release_checkpoint` 或 `full_project`。
- 事务绑定完整 evaluation/digests、source manifest、proposed tree、remote baseline 和 fixed rationales；仅当 source manifest 非空时在当前 `main` 创建 source checkpoint，空 manifest 复用卡片 HEAD，随后创建一个 signoff commit，并只向 `git@github.com:luvega/pep-design.git` 的 `refs/heads/main` 执行显式 fast-forward push。最终 receive-time CAS/隔离边界见 2026-07-11 安全收口记录。
- Generated report、审批卡和 journal 保持 non-evidence；production signoff 必须是 `harness/signoffs/` 下 committed、clean、非 symlink 的直接 regular file。Durable `local_committed_push_failed`/`verified` 只用 `resume-push` 恢复且无需重新批准：final OID 已存在时复用且不重复 commits/signoffs；只有 source OID 时先重验 source，再创建或复用缺失 signoff，并至多创建一个 signoff commit，且不重复 source；`verified` 可在 remote 已为 final OID 时协调实际成功但结果不明确的 push，不重复 push。
- 设计、测试、编码、文档及独立 spec/quality review 采用 `subagent-driven-development` 分工完成。
- 保持边界：未授权 clone、install、download、GPU generation、scoring 或 ranking；v0.33 仍为 10 条 blocker rows、0 parsed/generated candidates，`VERSION=1.2.21` 直到实际 digest 获 governance approval 后才可准备下一 release candidate。

## [2026-07-10] governance | harness engineering v1.0 unsigned checkpoint
- Added a standard-library acceptance harness with four profiles, eight evidence domains, dependency-aware gates, deterministic evidence digests, and separate `harness_status` / `project_status` axes.
- Added tracked semantic derivations for D-Flow train overlap, the unconditional RFdiffusion `[12-18]` example, and the PepMirror mirror-transformation gap.
- Added read-only `check`, explicit `render`, digest-bound signoff validation, generated JSON/Markdown reports, and focused regression/adversarial tests.
- Preserved the pre-harness `AGENTS.md` as a SHA-256-bound migration snapshot and replaced the active file with a concise progressive-disclosure map.
- Kept `VERSION=1.2.21` pending human acceptance. No generation, scoring, ranking, target-set promotion, download, install, or wet-lab evidence was added.

## [2026-07-10] release | v1.2.21 Wave A adapter/parser completion attempt
- Bumped project version to `1.2.21`.
- Added v0.33 runner/parser scripts:
  `scripts/run_v033_wave_a_pilot.py` and
  `scripts/parse_v033_pilot_outputs.py`.
- Executed v0.33 dry-run and lightweight adapter/parser wrapper over the 10
  v0.31 placeholder-failed Wave A jobs.
- Added compact v0.33 tables:
  `benchmark/deployment/pilot_execution_results_v0.33.csv`,
  `benchmark/results/pilot_method_output_manifest_v0.33.csv`,
  `benchmark/results/pilot_candidate_outputs_v0.33.csv`,
  `benchmark/results/pilot_run_v0.33.csv`, and
  `benchmark/results/pilot_v033_merge_summary.json`.
- Recorded v0.33 status as 10 method-specific
  `no_supported_output_found` blocker rows and 0 parsed/generated candidates.
- Added `ops/plans/updated_plan_v0.33.md` and
  `ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md`.
- Extended validator and tests for the v0.33 adapter/parser completion layer.
- Boundary: v0.33 is not Benchmark result evidence, not scoring evidence, not
  method-ranking evidence, and not wet-lab validation evidence.

## [2026-07-09] release | v1.2.20 Supervisor-Skills installation memory
- Bumped project version to `1.2.20`.
- Installed selected Supervisor-Skills from `HKUSTDial/Supervisor-Skills` at
  source commit `0b77a1b98794f8341d57685a0e829a3fa175d05f`:
  `benchmark-paper-template`, `intro-drafter`, `figure-designer`,
  `pre-submission-reviewer`, and `idea-evaluator`.
- Added `ops/audits/supervisor_skills_installation_v0.32.md` and
  `tests/test_v032_supervisor_skills_memory.py`.
- Updated `AGENTS.md` and `ops/audits/skill_selection.md` with
  Supervisor-Skills routing, `CC BY-NC-SA 4.0` license boundary and no-overclaim
  memory.
- Extended validator coverage for the v0.32 memory layer.
- Maintained boundaries: no new method execution, no scoring, no method
  ranking, no target-set promotion, no wet-lab validation, and no complete
  Benchmark result.

## [2026-07-09] release | v1.2.19 bounded Wave A pilot execution/parser layer
- Bumped project version to `1.2.19`.
- Added `scripts/run_v031_wave_a_pilot.py` and
  `scripts/parse_v031_pilot_outputs.py` to package, execute and merge the
  v0.31 bounded Wave A pilot rows from the v0.30 manifests.
- Ran the v0.31 Wave A pilot over 14 jobs and merged compact execution,
  method, candidate and run rows into
  `benchmark/deployment/pilot_execution_results_v0.31.csv`,
  `benchmark/results/pilot_method_output_manifest_v0.31.csv`,
  `benchmark/results/pilot_candidate_outputs_v0.31.csv`,
  `benchmark/results/pilot_run_v0.31.csv`, and
  `benchmark/results/pilot_v031_merge_summary.json`.
- Fixed the ColabDesign bounded runner so the v0.31 outer `command.sh` is not
  overwritten by the inner Docker command record; the inner command is stored
  as `colabdesign_inner_command.sh`.
- Recorded v0.31 status as 4 parsed/generated rows and 10 failed placeholder
  rows. Parsed methods are PepMLM and AfCycDesign / ColabDesign cyclic peptide.
- Added `ops/audits/pilot_wave_a_execution_audit_v0.31.md` and
  `tests/test_v031_wave_a_pilot.py`; extended validator checks for v0.31
  headers, row counts, Wave A job alignment, parser counts and no-overclaim
  boundaries.
- Maintained boundaries: no scoring, no method ranking, no target-set
  promotion, no wet-lab validation, and no complete Benchmark result.

## [2026-07-09] release | v1.2.18 pilot benchmark design layer
- Bumped project version to `1.2.18`.
- Added v0.30 pilot target, control and job manifests for the next bounded
  Wave A/Wave B execution phase:
  `benchmark/input_sets/pilot_benchmark_target_manifest_v0.30.csv`,
  `benchmark/input_sets/pilot_benchmark_control_manifest_v0.30.csv`, and
  `benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv`.
- Added `benchmark/deployment/pilot_execution_matrix_v0.30.csv` with 17 planned
  execution records: 14 Wave A jobs, 2 Wave B control/smoke jobs and 1 blocked
  SaLT&PepPr access record.
- Added `benchmark/input_sets/wet_lab_candidate_panel_v0.30.csv` with four
  prospective follow-up target classes: MDM2, GABARAP, NCAM1 and AMHR2.
- Added `ops/audits/pilot_benchmark_design_audit_v0.30.md` and
  `tests/test_v030_pilot_benchmark_design.py`; extended the validator to check
  v0.30 headers, row counts, job/matrix alignment, blocked-license handling,
  empty `target_set_v0.csv`, and wet-lab prospective-only boundaries.
- Maintained boundaries: no v0.30 job execution, no target-set promotion, no
  scoring, no method ranking, no wet-lab validation, and no complete Benchmark
  result.

## [2026-07-09] release | v1.2.17 bounded generation and parser evidence
- Bumped project version to `1.2.17`.
- Added `scripts/run_colabdesign_bounded_generation.py` and ran one bounded
  ColabDesign 7ZKR GPU generation/parser attempt in gitignored
  `benchmark_runs/v0.29/colabdesign_bounded_generation`; exit code was `0`,
  parser status was `parsed`, and the compact candidate row records sequence
  `IQTNYYVRSRTQCQ`.
- Added `scripts/prepare_dexdesign_minimal_fixture.py` and created a synthetic
  prepared D-L complex fixture with target=`z` and peptide=`y`; the DexDesign
  route audit now reports `dexdesign_input_contract_ready` for that fixture.
- Added `scripts/parse_bindcraft_accepted_outputs.py` and converted four
  external CD47 BindCraft accepted-final PDBs into standard candidate rows.
- Recorded v0.29 evidence in
  `benchmark/deployment/bounded_generation_parser_v0.29.csv`,
  `benchmark/results/colabdesign_bounded_method_output_manifest_v0.29.csv`,
  `benchmark/results/colabdesign_bounded_candidate_outputs_v0.29.csv`,
  `benchmark/results/bindcraft_accepted_candidate_outputs_v0.29.csv`, and
  `ops/audits/bounded_generation_parser_audit_v0.29.md`.
- Maintained boundaries: no controlled multi-case run, no target-set
  promotion, no multi-seed evidence, no scoring, no method ranking, and no
  complete Benchmark result.

## [2026-07-09] release | v1.2.16 external asset rescue
- Bumped project version to `1.2.16`.
- Found ColabDesign/AlphaFold parameters under
  `/data/protein-design/data/alphafold_db/params` and a reusable fixture target
  PDB at
  `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion/examples/input_pdbs/7zkr_GABARAP.pdb`.
- Reran the ColabDesign bounded asset gate in gitignored
  `benchmark_runs/v0.28/colabdesign_asset_gate`; status is
  `ready_for_bounded_gpu_generation`, with no generation run.
- Extracted the DexDesign D-peptide/L-protein input contract from the OSPREY3
  `examples/ccs.D-peptide-L-protein/` route and recorded the remaining missing
  prepared D-L complex fixture.
- Extended the BindCraft classifier to support native `Accepted/` layouts and
  classified `/data/protein-design/data/outputs/bindcraft/CD47` as
  `accepted_final` with four accepted PDB files.
- Recorded v0.28 evidence in
  `benchmark/deployment/external_asset_rescue_v0.28.csv`,
  `benchmark/results/bindcraft_accepted_final_classification_v0.28.csv`, and
  `ops/audits/external_asset_rescue_audit_v0.28.md`.
- Maintained boundaries: no controlled multi-case run, no ColabDesign
  generation claim, no DexDesign design claim, no scoring, no method ranking,
  and no complete Benchmark result.

## [2026-07-09] release | v1.2.15 ColabDesign/DexDesign gate update
- Bumped project version to `1.2.15`.
- Extended `scripts/prepare_colabdesign_cli_adapter.py` with a bounded
  execute asset gate that writes standard manifests and fails closed when
  AlphaFold/ColabDesign parameters are missing.
- Added `scripts/audit_dexdesign_route.py` to audit the DexDesign-specific
  OSPREY3 `examples/ccs.D-peptide-L-protein/` route.
- Recorded the compact gate summary in
  `benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv` and audit notes
  in `ops/audits/colabdesign_dexdesign_gate_v0.27.md`.
- Maintained boundaries: generic OSPREY examples are environment probes only,
  ColabDesign is blocked before generation without AF parameters, DexDesign is
  blocked until a D-peptide/L-protein input contract and bounded CPU smoke are
  recorded, and there is no scoring or complete Benchmark result.

## [2026-07-09] release | v1.2.14 D-Flow/ColabDesign/BindCraft gate update
- Bumped project version to `1.2.14`.
- Ran a bounded D-Flow / PeptideDesign dry-run on one official PepMerge entry
  (`1aze_B`) with `num_steps=1` and `num_samples=1`; exit code was `0` and the
  output includes `sample_0.pdb`, `gt.pdb`, `outputs.csv`, and `aar.csv` under
  gitignored `benchmark_runs/v0.26`.
- Parsed the D-Flow sample PDB into a compact candidate row with chain B
  sequence `MRRRRRRRRY` in
  `benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv`.
- Added `scripts/prepare_colabdesign_cli_adapter.py` and generated a standard
  ColabDesign job-row adapter package for `v022_pilot_colabdesign_7zkr_seed42`
  without running notebook or GPU generation code.
- Added `scripts/classify_bindcraft_outputs.py`; classified the v0.21 BindCraft
  output as `low_confidence_only` with zero accepted PDBs.
- Recorded the compact gate summary in
  `benchmark/deployment/dflow_colabdesign_bindcraft_v0.26.csv` and audit notes
  in `ops/audits/dflow_colabdesign_bindcraft_v0.26.md`.
- Maintained boundaries: no `target_set_v0.csv` promotion, no scoring, no
  method-ranking evidence, no ColabDesign generation claim, no BindCraft
  accepted-final claim, no complete Benchmark result, and no biological-
  validation claim.

## [2026-07-09] release | v1.2.13 D-Flow full PepMerge download readiness
- Bumped project version to `1.2.13`.
- Resolved the D-Flow full PepMerge Google Drive blocker by using a working
  Google IP for folder metadata and `drive.usercontent.google.com` confirmed
  download URLs.
- Downloaded and verified gitignored `PepMerge_release.zip` and
  `PepMerge_lmdb.zip`; both archives passed `unzip -t` and SHA256 recording.
- Extracted 10,348 PepMerge structure case directories and confirmed no case is
  missing required `pocket.pdb`, `peptide.pdb`, `receptor.pdb`,
  `receptor.fasta`, or `peptide.fasta`.
- Verified `PepDataset(reset=False)` loads 154 official `pep_pocket_test`
  entries and 9,849 official `pep_pocket_train` entries from the extracted LMDB
  package; recorded the summary in
  `benchmark/deployment/dflow_full_pepmerge_download_v0.25.csv`.
- Maintained boundaries: no `target_set_v0.csv` promotion, no D-Flow generation
  run, no scoring, no method-ranking evidence, no complete Benchmark result,
  and no biological-validation claim.

## [2026-07-09] release | v1.2.12 D-Flow input-contract fixture readiness
- Bumped project version to `1.2.12`.
- Added `scripts/prepare_dflow_input_contract.py` to build a D-Flow PepMerge-style fixture from a benchmark PDB case and verify `PepDataset` LMDB loading.
- Created a gitignored 3EQS D-Flow fixture under `data/dflow/pepmerge/mdm2_p53_3eqs_fixture` and generated `data/dflow/pep_cache/pep_pocket_test_structure_cache.lmdb`.
- Verified `PepDataset(reset=True)` and `PepDataset(reset=False)` load one fixture entry in the project-local D-Flow environment; recorded the compact summary in `benchmark/deployment/dflow_input_contract_fixture_v0.24.csv`.
- Added `ops/audits/dflow_input_contract_fixture_audit_v0.24.md` and pytest/validator coverage.
- Maintained boundaries: no full PepMerge release download, no `target_set_v0.csv` promotion, no D-Flow generation run, no scoring, no method-ranking evidence, no complete Benchmark result, and no biological-validation claim.

## [2026-07-09] release | v1.2.11 external dry-run package readiness
- Bumped project version to `1.2.11`.
- Added v0.23 notebook CLI smoke, D-Flow project install contract, external dry-run package manifest, priority gate review, plan, audit and pytest coverage.
- Installed notebook CLI tooling in the project-local `.venv/benchmark-v023-conda` environment and verified a `papermill` notebook execution smoke under `benchmark_runs/v0.23`.
- Cloned D-Flow / PeptideDesign into `method_sources/dflow/PeptideDesign` as a real project-local checkout at commit `3e3e9f501ee16db318e9bf52643513636a07699a`, not a symlink.
- Built a project-local D-Flow GPU environment under `.venv/dflow-v023`, extracted `dflow.pt` under `weights/dflow/`, patched the documented DeepSpeed `torch._six` issue, and verified `PepDataset`, `PepModel` and `inference_pep` imports.
- Recorded D-Flow blocker: PepMerge and `pep_pocket_test_structure_cache.lmdb` are absent; Google Drive access to the README PepMerge folder timed out through `gdown` and `curl`.
- Maintained boundaries: no `target_set_v0.csv` promotion, no scoring, no method-ranking evidence, no complete Benchmark result, and no biological-validation claim.

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
