# Updated Plan v0.34

## 目标

v0.34 把 v0.33 的“未找到受支持输出”阻断，推进为 7 种方法的真实、受限生成连通性检查。每种方法先执行 seed42；只有主运行通过的方法才允许执行 seed43。本阶段不启动 scoring，不执行 ranking。

本阶段回答的是：方法入口能否在固定输入、固定随机种子和固定输出合同下产生一条可解析候选。它不回答候选质量高低，也不支持方法排名。

## 方法与输入

| 方法 | 任务 | 输入 | 主要输出约束 |
|:---|:---|:---|:---|
| PepMLM | T1 sequence binder | 固定蛋白序列 | 3 aa，seeded top-k sampling |
| DiffPepBuilder | T2 peptide binder | 3EQS | 11 aa，目标链 B、binder 链 A |
| PepGLAD | T2 peptide binder | 3EQS A/B pocket | 11 aa，目标链 A、binder 链 B |
| D-Flow / PeptideDesign | T2 D-peptide binder | 3EQS pocket fixture | 11 aa，x-mirror，D 手性 |
| PepMirror | T2 D-peptide binder | 3EQS A/B | 11 aa，镜像生成后回镜像 |
| AfCycDesign / ColabDesign | T2 cyclic peptide binder | 7ZKR A | 14 aa，cyclic offset 与末端 C-N 距离 |
| RFdiffusion + ProteinMPNN | T3 miniprotein baseline | 7ZKR A3-117 | binder B 70-100 aa，A 固定，指定 hotspots |

权威 job 合同为 `benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv`，执行矩阵为 `benchmark/deployment/pilot_execution_matrix_v0.34.csv`。

## 执行顺序

1. 对 7 个 seed42 job 生成不可覆盖的 attempt 目录，先做源码、模型、目标和命令预检。
2. 串行执行有界生成，记录 stdout、stderr、退出码、运行时间和实际输出。
3. parser 只接受 method-specific 标准路径；旧文件、空文件、路径逃逸和哈希不一致均失败。
4. 公共 QC 验证链、长度、序列/结构、目标绑定、随机种子，以及方法特有的手性、镜像、循环或 RF-to-MPNN handoff。
5. seed42 为 `passed` 且 QC 为 `pass` 或 `pass_with_warning` 时，才允许同方法 seed43。
6. 将最新 attempt 合并为仓库内 compact evidence；原始结构、日志和运行目录留在 gitignored `benchmark_runs/v0.34/`。

## 主运行验收

`current.v034_bounded_connectivity` 只有在下列条件同时满足时通过：

- 7 个主 job 均有真实进程退出码、方法输出清单、1 条解析候选和公共 QC；
- 每条主 job 状态为 `passed`，QC 为 `pass` 或 `pass_with_warning`；
- PepMirror 的四个镜像文件及 SHA 完整，D 手性检查通过；
- RFdiffusion 的 target-conditioned backbone、TRB、ProteinMPNN generated FASTA、固定 A/设计 B 和 seed 证据完整；
- 汇总表、run rows 和 merge summary 相互一致；
- 没有 scoring、ranking 或 wet-lab 状态提升。

seed43 是重复性扩展，不是主连通性 gate 的必要条件；但扩展结果不得在对应 seed42 失败时出现。

## 当前状态

最新合并包含 13 条 method-output manifest、12 条 candidate、12 条 candidate QC、12 条 compact runtime provenance 和 14 条 run rows。6 个 seed42 primary 获得 `supported`，对应的 6 个 eligible seed43 extensions 也获得 `supported`。PepGLAD 最新 seed42 诊断未晋升为候选，seed43 未运行，因此 `current.v034_bounded_connectivity` 仍为 6/7、Critical `FAIL`。

`benchmark/results/pilot_failure_diagnostics_v0.34.json` 另存 1 条 tracked failure-only diagnostic provenance。它不计入 12 条 candidate runtime provenance，不改变 candidate/QC/run 计数，也不构成候选、评分或完整复现证据。

PepGLAD seed42 `attempt_003` 的 target preflight 以及 source、model、observer、patch、wrapper 和 instrumented-source pins 均通过，进程退出码为 0。parser 返回 `pepglad_seed42_replay_mismatch`，merge 返回 `evidence_incomplete`。sequence summary 仍为 `AWHITLLIFTH`，但该输出没有进入 compact candidate/QC/provenance 表。

该 attempt 在 OpenMM 前保存的 B 链快照 SHA-256 为 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`，手性计数为 L6/D5；OpenMM 后 B 链 SHA-256 为 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`，手性计数为 L4/D7。后者不同于固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`，所以 replay fail closed。`first_observed_chirality_failure_stage=pre_openmm_snapshot` 仅支持“混合手性在本 attempt 的 OpenMM 前已可观察”；它不证明模型是根因，也不证明 OpenMM 没有影响，因为 L/D 计数从 6/5 变为 4/7。历史 `attempt_002` 的序列为 `AWHITLLIFTH`、手性为 L4/D7，文件 SHA-256 与固定 baseline 相同。

failure-only 记录把上述 `AWHITLLIFTH`、pre/post SHA-256 与 L/D、baseline mismatch 绑定到本次 producer pins，包括 source commit/entrypoint、container/conda environment、model、target、observer、patch/instrumenter、wrapper 和 instrumented source。固定这些身份有助于审计失败发生在哪一次执行，但不把失败记录升级为复现证据。

现有官方入口没有符合当前协议的 method-native skip-relax 或 idealize 选项。按已批准的停止条件，本轮不再发起第二个诊断 attempt，也不运行 PepGLAD seed43。继续执行需要用户另行批准协议或 source-policy 变更；另一项可审议选择是接受 PepGLAD 在该 fixture 和当前合同下失败。两种选择都不能直接授权评分。

## 证据边界

v0.34 允许写“该方法在指定 fixture 上产生一条通过基础 QC 的可解析候选”。即使 7 个方法全部连通，也不能写：

- 已完成正式 Benchmark；
- 已产生合格的 scoring evidence；
- 某方法表现最好或优于其他方法；
- target set 已冻结；
- 已完成实验或生物学验证。

D-Flow 的 3EQS fixture 存在已知训练集重叠，只能用于连通性检查，禁止进入后续公平评分。

## 后续阶段

下一步由用户决定是否批准 PepGLAD 协议/source-policy 变更，或接受该方法在当前 fixture 上失败。若批准新的诊断执行，必须创建不可覆盖 attempt，并仅在 seed42 primary 通过后运行 seed43。若接受失败，v0.34 gate 仍保持 6/7 Critical `FAIL`。任何路径都不能直接进入评分；只有主 gate 关闭且 target/control、license、leakage 和 provenance 审批完成后，才能另行定义独立测试集与评分资格。
