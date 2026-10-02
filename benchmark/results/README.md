# 运行与候选证据索引

本目录保存真实方法任务的小型验收摘要、来源绑定和历史 parser/fixture 记录。当前运行验收为 **10/10 方法**，候选完整性质量检查为 **9/10 方法**；统一 Benchmark 评分与排名尚未开展。

| 当前文件 | 内容 | 阅读方式 |
|:---|:---|:---|
| [method_acceptance_matrix_v1.csv](method_acceptance_matrix_v1.csv) | 10 方法的运行、质量、attempt 数及完成范围 | `runtime_status` 与 `candidate_quality_status` 分开阅读 |
| [method_acceptance_execution_index_v1.json](method_acceptance_execution_index_v1.json) | 政策、范围、资源账本和完整重放结果的 SHA | 需结合本机原始证据与检查器重放 |
| [method_acceptance_existing_v1.json](method_acceptance_existing_v1.json) | 既有产物复核与复用依据 | 不等于本轮全部新增任务结果 |
| [pepglad_fresh_connectivity_v1.json](pepglad_fresh_connectivity_v1.json) | fresh PepGLAD 独立执行的紧凑候选绑定 | 保留其独立身份，旧 v0.35 失败不回写 |

逐方法说明与原始路径见[验收报告](../../ops/acceptance/method_runtime_acceptance_v1.md)及[详细 JSON](../../ops/acceptance/method_runtime_acceptance_v1.json)。D-Flow 的质量失败和 DexDesign 的单 IAS 范围均在报告中保留。

原始 PDB、MSA、权重、日志与中间结果保存在外部路径。候选摘要支持特定任务的运行与完整性核查；不同方法输入尚不可直接比较，当前没有性能排行榜。

<details>
<summary>历史示例、parser fixture 和 v0.34/v0.35 文件边界</summary>

以下记录描述对应历史阶段，最新状态以上面的当前验收文件为准。

v0.11 新增的 `example_method_output_manifest_v0.11.csv` 和 `example_candidate_outputs_v0.11.csv` 只用于 schema/adapter 说明，所有行均为 `not_real_benchmark` 或未运行占位记录，不是方法输出或性能证据。

v0.18 新增的 `batch_a_replay_method_output_manifest_v0.18.csv`、`batch_a_replay_candidate_outputs_v0.18.csv` 和 `batch_a_replay_run_v0.18.csv` 是从外部 v0.15 Batch A minimal smoke outputs 解析得到的小型 replay fixtures。它们用于检查 adapter/parser 字段和 `design_id` join，不是新的方法执行、scoring evidence、head-to-head result 或 Benchmark performance finding。

v0.21 新增的 `adapter_method_output_manifest_v0.21.csv`、`adapter_candidate_outputs_v0.21.csv` 和 `adapter_run_rows_v0.21.csv` 是 bounded adapter smoke 的 parser fixture rows，不是 scoring evidence 或 Benchmark results。v0.22 不新增结果表，只在 `benchmark/input_sets/` 和 `benchmark/deployment/` 中记录 multi-case fixture pilot planning manifests。

v0.26-v0.29 新增的小型结果表记录 D-Flow bounded dry-run、BindCraft wrapper/accepted-final parser fixture、ColabDesign 单例 bounded generation/parser 和 DexDesign/BindCraft parser-contract 证据。它们是 readiness/parser evidence，不是 scoring evidence、method ranking 或完整 Benchmark result。

v0.31 新增的 `pilot_method_output_manifest_v0.31.csv`、`pilot_candidate_outputs_v0.31.csv`、`pilot_run_v0.31.csv` 和 `pilot_v031_merge_summary.json` 汇总 14 个 Wave A bounded pilot job。当前 4 行 parsed/generated，10 行为 adapter placeholder failed。原始 PDB、日志和生成输出保留在 gitignored `benchmark_runs/v0.31/`；这些表不是 scoring evidence、method ranking、target-set promotion 或完整 Benchmark result。

v0.33 的小型结果表把 10 个 placeholder failure 改写为方法级 `no_supported_output_found` blocker。它们是历史 blocker evidence，不是生成成功。

v0.34 的 `pilot_method_output_manifest_v0.34.csv`、`pilot_candidate_outputs_v0.34.csv`、`pilot_candidate_qc_v0.34.csv`、`pilot_run_v0.34.csv`、`pilot_runtime_provenance_v0.34.json`、`pilot_failure_diagnostics_v0.34.json` 和 `pilot_v034_merge_summary.json` 汇总受限生成连通性。最新 compact 表有 13 条 method-output manifest、12 条 candidate、12 条 candidate QC、12 条 candidate runtime provenance 和 14 条 run rows。6 个 seed42 primary 与对应的 6 个 eligible seed43 extensions 获得 `supported`；PepGLAD 最新候选缺席，seed43 未运行。

[`pilot_failure_diagnostics_v0.34.json`](pilot_failure_diagnostics_v0.34.json) 只含 1 条 tracked failure-only diagnostic provenance。它绑定 `attempt_003` 的 `AWHITLLIFTH` sequence summary、OpenMM 前 L6/D5 与 SHA-256 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`、OpenMM 后 L4/D7 与 SHA-256 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`、固定 baseline mismatch，以及 source/model/target/observer/patch/wrapper 等 producer pins。它不进入 12 条 candidate runtime provenance，不是候选、QC、评分或完整复现证据。

PepGLAD seed42 `attempt_003` 的 target preflight 与 source/model/observer/patch/wrapper/instrumented-source pins 均通过，进程退出码为 0。parser 返回 `pepglad_seed42_replay_mismatch`，merge 返回 `evidence_incomplete`。sequence summary 仍为 `AWHITLLIFTH`，但该输出没有晋升候选。OpenMM 前 B 链快照为 L6/D5，SHA-256 是 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`；OpenMM 后为 L4/D7，SHA-256 是 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`，与固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26` 不同。历史 `attempt_002` 为 `AWHITLLIFTH`、L4/D7，文件 SHA-256 与 baseline 相同。

`first_observed_chirality_failure_stage=pre_openmm_snapshot` 支持混合手性在本 attempt 的 OpenMM 前已可观察，但不证明模型根因，也不证明 OpenMM 没有影响，因为 L/D 计数从 6/5 变为 4/7。RFdiffusion 的结构输出仍是未线程化 all-Gly backbone，ProteinMPNN FASTA 是独立 handoff；PepMLM 保留 `WWX`/`X` 边界，D-Flow 3EQS 保留已知训练重叠边界。

原始结构和日志留在 gitignored `benchmark_runs/v0.34/`。现有官方入口没有符合当前协议的 method-native skip-relax 或 idealize 选项；按停止条件，本轮不再运行第二个 PepGLAD 诊断 attempt 或 seed43。继续执行需要另行批准协议/source-policy 变更，或接受该 fixture 失败。两种选择都不授权 scoring、ranking、frozen target、wet-lab 或完整 Benchmark 结论。

v0.35 预留的 `pilot_pepglad_connectivity_v0.35.json` 只接受通过 exact-schema、raw replay 和历史 SHA 绑定的候选 bundle。唯一授权的 PepGLAD `attempt_001` 在容器启动前因 Docker API socket 权限不足失败：`exit_code=1`、parser/QC=`not_run`，`raw/` 中没有 candidate 或 runtime evidence。解析器已 fail closed，因此本目录没有该 bundle。该状态只支持基础设施失败记录，不支持 PepGLAD 方法失败、mixed L/D、连通性、scoring 或 ranking 结论。审计见 [`../../ops/audits/v035_pepglad_connectivity_audit.md`](../../ops/audits/v035_pepglad_connectivity_audit.md)。

</details>
