# 项目推进计划 v1（2026-10-02）

> 最新决策：本页工作包表保留最初规划状态。PepGLAD fresh 单次执行现已完成[方法级验收](../acceptance/pepglad_method_acceptance_v1.md)，M1 的待授权文字不再描述当前事实。用户现已将计划对齐路线改为 `grilling`，停用 superpowers 工作流约束；本页作为新一轮讨论输入，待确认共同理解后更新后续工作包。

下一阶段讨论已聚焦为“10 种方法原生任务与质量达标候选的运行验收”，详见
[待整体确认的验收计划](method_runtime_acceptance_plan_v1.md)；下文科学 Benchmark 工作包保留作后续参考。

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-10-02
- Verification Status: UNVERIFIED（未来执行尚未实施；已有记录另见审计）
- Version Label: project_progression_v1

## 当前基线与授权范围

本计划是 [v0.35 当前科学计划](updated_plan_v0.35.md) 的规划补充，不替换
`current_plan`，项目版本仍为 `1.2.21`。
用户已授权文档、证据归档与治理更新，并停用 `benchmark-paper-template` 路由。
`building-llm-wiki` 缺失时，按本次明确授权使用 `academic-research-suite` 与机器合同。

v0.34 保持 6 个 supported primary、6 个 supported seed43 extension、12 条候选/QC、
12 条 candidate runtime provenance 与 14 条 run rows。v0.35 原 `attempt_001`
为容器启动前基础设施失败，没有有效 candidate bundle，Critical gate 仍打开。
现存 SaLT&PepPr 输出另以 v0.36 归档补充记录，不晋升生成、评分或方法 readiness。

本计划只定义推进条件，不授权新 attempt、GPU generation、seed43、scoring、ranking、
target freeze、签核、commit 或 push。

## 工作包与交付物

| 工作包 | 当前状态 | 交付物 | 完成条件 |
|:---|:---|:---|:---|
| M0 证据和计划同步 | 本次整理 | 来源/观察表、归档审计、现行路由、工程计划、导航及生成报告 | 来源先于派生产物更新；validator 0 errors/0 warnings；准确保留 Critical failure |
| M1 PepGLAD 新执行准备 | proposal_not_authorized | [新执行提案](pepglad_next_execution_proposal_v1.md) | 新身份、输出根、前检、次数、超时、停止条件明确；授权身份全链迁移及测试尚须完成 |
| M2 目标与对照审查 | review_only_not_frozen | [7 项目标工作表](../../benchmark/input_sets/target_governance_worklist_v1.csv) | 逐目标关闭来源、许可、assay、controls、化学/链和 method-specific leakage 缺项 |
| M3 下一阶段验收设计 | design_only_not_implemented | [验收接口设计](next_phase_acceptance_design_v1.md) | 历史真实性与新证据检查分开；新 evaluator 能拒绝错误证据并接受合格产物 |
| M4 受控生成 | awaiting_phase_authorization | 新科学阶段的 job manifest、候选、QC、runtime provenance、失败统计 | 方法和目标资格闭环；输入、seed、候选/时间预算、失败处理先固定后执行 |
| M5 评分与分析 | awaiting_phase_authorization | 指标适用表、校准证据、metric CSV、merged_run.csv、可追溯分析 | 合法目标及对照、完整输出表示和指标验证同时满足；比较通过公平性审查 |

## 目标审查顺序

优先梳理 MDM2/3EQS 的已有正复合物、参考链/长度与缺失负对照，形成首个完整的审查模板。
这不指定 3EQS 为独立测试目标：D-Flow 已知训练重叠必须保留，其他方法的训练重叠仍需逐项审查。
计算 decoy 与 assay-backed nonbinder 使用不同标签。

7ZKR 先解决 ncAA/stapled/cyclic 表示；1SJH 先解决 chain D；本地 PDL1 先补来源、许可和链映射。
PepMLM sequence fixture、DexDesign synthetic fixture 和 BindCraft external parser control
继续保留各自 interface-only 用途。BindCraft 历史 `T4_bindcraft_peptide_smoke` 与当前 T3
任务映射作为新阶段审查项，不回写历史行。

该工作表从已有 pilot manifest/control records 派生，没有新增已批准目标、assay 值或负对照。
各项 owner_role 为审查职责，不代表已有人工签核。

## 方法输出与未来比较

T1、T2、T3 按适用任务组织比较；L/D/mixed/cyclic/ncAA 分别记录支持范围。
PepMLM 的 `WWX` 保留 `X` 警告；RFdiffusion+ProteinMPNN 的独立 FASTA handoff
在取得 sequence-resolved structure 及新 QC 前，不进入结构评分。
SaLT&PepPr 当前归档的是界面推理；DexDesign 尚需真实设计输出；BindCraft 外部示例
尚需独立的受控 job/provenance。它们各有完成条件，不能由 parser fixture 直接晋升。

M1 决策等待期间可推进 M2 与 M3 的文档和证据审查。即使后续达到 7/7 连通性覆盖，
M4/M5 仍须分别获得明确阶段授权并满足输入、表示、评分与公平性条件。

## 下一检查点

先完成 M0，随后落实 M1 的授权身份迁移设计和 M2 首个目标审查。
需要外部元数据、数据、权重或执行时，按相应阶段边界另行处理。
签核与版本推进遵循现行 digest-bound governance 流程；当前 Critical failure 不能被人工批准豁免。

验证命令与当前预期见 [Harness 工程计划](harness_engineering_plan_v1.0.md)。
SaLT&PepPr 的已有事实与缺项见 [归档审计](../audits/saltnpeppr_local_inference_audit_v0.36.md)。
