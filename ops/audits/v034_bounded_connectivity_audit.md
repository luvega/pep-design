# v0.34 受限生成连通性审计

## 审核范围

本审计对应 `ops/plans/updated_plan_v0.34.md`。它检查 7 种方法能否从固定入口产生一条可解析候选，并通过链、长度、序列、结构、随机种子和方法专属的基础 QC。原始结构与日志位于 gitignored `benchmark_runs/v0.34/`；最新合并保存 13 条 method-output manifest、12 条 candidate、12 条 candidate QC、12 条 compact candidate runtime provenance 和 14 条 run rows。另有 1 条 tracked failure-only diagnostic provenance，不计入上述 compact candidate provenance。

本轮使用一个固定序列输入、3EQS 和 7ZKR。它没有建立正式测试集，也没有做评分。

## 运行结果

| 方法 | 输入 | seed42 主运行 | seed43 扩展 | 结论 |
|:---|:---|:---|:---|:---|
| PepMLM | 固定序列 fixture | `passed` / `pass_with_warning` | `passed` / `pass_with_warning` | 两个 seed 均生成 `WWX`；长度与种子检查通过，`X` 触发非标准残基警告 |
| DiffPepBuilder | 3EQS | `passed` / `pass` | `passed` / `pass` | 两个 seed 均产生 11 aa、链与 L 手性符合合同的候选 |
| PepGLAD | 3EQS | `exit 0` / `parse_failed` / `evidence_incomplete` | `not_run` | `attempt_003` 返回 `pepglad_seed42_replay_mismatch`；sequence summary 为 `AWHITLLIFTH`，但最新输出未晋升候选 |
| D-Flow / PeptideDesign | 3EQS | `passed` / `pass` | `passed` / `pass` | 两个 seed 均通过 x-mirror 与 D 手性检查；3EQS 有已知训练重叠，只能用于连通性检查 |
| PepMirror | 3EQS | `passed` / `pass` | `passed` / `pass` | 两个 seed 均通过镜像往返文件、哈希与 D 手性检查 |
| AfCycDesign / ColabDesign | 7ZKR | `passed` / `pass` | `passed` / `pass` | 两个 seed 均通过 14 aa、cyclic offset 与末端 C-N 距离检查 |
| RFdiffusion + ProteinMPNN | 7ZKR | `passed` / `pass` | `passed` / `pass` | target-conditioned backbone、TRB 与 ProteinMPNN FASTA handoff 可解析；backbone 为未线程化 all-Gly，当前没有 sequence-resolved structure |

最新合并有 6 个 primary 候选通过基础 QC，且对应的 6 个 eligible seed43 extensions 全部通过。PepGLAD 最新 primary 诊断没有进入 compact candidate/QC/provenance 表，也没有执行 seed43。历史 `attempt_002` 曾解析序列 `AWHITLLIFTH`，其 B 链手性为 L4/D7，文件 SHA-256 为固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`；该历史失败不等同于最新候选。

这里的 `pass` 只表示入口、解析和基础 QC 连通。它不说明哪种方法设计得更好。PepGLAD 的当前状态只说明最新诊断证据不满足 replay 和候选晋升合同，不能据此判定算法整体较差。

## PepGLAD 诊断

- `benchmark/results/pilot_failure_diagnostics_v0.34.json` 只含 `attempt_003` 的 1 条 failure-only 记录。它绑定 sequence summary `AWHITLLIFTH`、pre/post SHA-256 与 L6/D5、L4/D7、固定 baseline mismatch，以及 producer pins。该文件不是候选、QC、评分或完整复现证据。
- `attempt_003` 的 target preflight 以及 source、model、observer、patch、wrapper 和 instrumented-source pins 均通过，进程退出码为 0。
- OpenMM 前的 B 链快照 SHA-256 为 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`，11 个可判定残基为 L6/D5。OpenMM 后 B 链 SHA-256 为 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`，手性为 L4/D7。
- OpenMM 后 SHA-256 不同于固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。parser 因此返回 `pepglad_seed42_replay_mismatch`，merge 将该 job 记为 `evidence_incomplete`；sequence summary 虽仍为 `AWHITLLIFTH`，但输出没有晋升候选。
- `first_observed_chirality_failure_stage=pre_openmm_snapshot` 支持“混合手性在本 attempt 的 OpenMM 前已可观察”。它不证明模型是根因，也不证明 OpenMM 没有影响；OpenMM 前后 L/D 计数从 6/5 变为 4/7。

## 证据完整性

- `pilot_runtime_provenance_v0.34.json` 含 12 条记录，对应 6 个 supported primary 与 6 个 supported seed43 extensions。PepGLAD 最新诊断因 replay mismatch 未纳入，PepGLAD extension 未运行。
- `pilot_failure_diagnostics_v0.34.json` 的 1 条记录独立于上述 12 条 candidate provenance。其 `producer_bindings` 固定 source commit `bad015ca50c312a89482adb5220c3d907f13df5c`、entrypoint SHA-256 `af888f4e441cf2b051cfa52df60920fdb55cb89c25bb319d08ccdf10dd073dac`、image `pd-benchmark-methods-gpu:0.21`、conda environment `bench-pepglad`、model SHA-256 `5f05dc0f678ed7a75c2ce8fc19f63cc145bd4568f75cbfc7f15aeacdddbd3cfe`、target SHA-256 `7086cf2bc4723ccbb4be5ff7f86a50d9db59bc307f4fbb0395a3c6ce3569827d`，以及 observer、patch/instrumenter、wrapper 和 instrumented-source SHA-256。
- PepGLAD `attempt_003` 的 preflight 与各项 pin 通过，不抵消 replay mismatch，也不构成完整可复现声明。
- RFdiffusion backbone 与 ProteinMPNN FASTA 是两个 handoff artifacts。ProteinMPNN 序列尚未 thread 回 all-Gly backbone，当前记录不构成 sequence-resolved structure。
- D-Flow 的 3EQS fixture 存在已知 train overlap；相关行不具备公平 scoring 资格。

## Harness 结论

`current.v034_bounded_connectivity` 要求 7 个 seed42 主运行全部通过。当前结果只有 6 个通过，所以该 Critical gate 为 `FAIL`，`current_phase` 不能签核。对话中的人工批准不能跳过这个失败。

## 下一步

诊断已把混合手性的首次可观察位置收窄到本 attempt 的 OpenMM 前，但没有定位模型根因，也没有排除 OpenMM 的影响。现有官方入口没有符合当前协议的 method-native skip-relax 或 idealize 选项。按已批准的停止条件，本轮不发起第二个诊断 attempt，也不运行 PepGLAD seed43。

继续执行需要用户另行批准协议或 source-policy 变更，或由用户接受 PepGLAD 在该 fixture 和当前合同下失败。前一种路径必须使用新的不可覆盖 attempt，且 seed42 通过后才能运行 seed43；后一种路径保留 6/7 Critical `FAIL`。两种路径都不能直接进入评分。即使后续达到 7/7，也要先补齐 target/control、license、leakage 和 provenance 审批，再定义独立测试集。

## 固定边界

- 这些结果只支持“指定 fixture 上的受限生成连通性和基础 QC”。
- D-Flow 的 3EQS 训练重叠行不能进入公平评分。
- PepMLM 的相同 `WWX` 与 `X` 警告不能解释为候选质量或重复性优势。
- 12 条 compact runtime provenance 只绑定已晋升的 12 条候选；另存的 1 条 PepGLAD failure-only diagnostic provenance 不计入候选 provenance，也不证明完整可复现。
- RFdiffusion 的 all-Gly backbone 和独立 ProteinMPNN FASTA 不应写成 sequence-resolved structure。
- `target_set_v0.csv` 继续保持 schema-only。
- 没有 scoring、ranking、frozen target、wet-lab 或生物学验证。
- `VERSION` 保持 `1.2.21`。
