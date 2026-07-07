# v1.3 基金评审式模拟审查：Pep_design Benchmark 项目

## Review Scope

本文件基于 `research-grants` 写作框架，对当前 Pep_design Benchmark KB 进行基金评审式模拟审查。它不是真实基金评审意见，也不是项目已获资助或已完成 Benchmark 的证据。

审查对象包括 `ops/plans/updated_plan_v0.9.md`、v0.6-v0.8 readiness artifacts、v1.0 中英文 manuscript outlines、v1.1 补充资料综合、v1.2 figure/table embedding layer、claim-evidence map、validator 和当前 `benchmark/` 协议层。

No benchmark execution was performed. No clone, no download, no install, no model weights, no GPU run, no smoke test, and no local reproducibility claim are introduced by this review.

## Overall Impact

**Overall impact: 中等偏强，建议 Major Revision Before Execution。**

项目瞄准近期 AI 多肽设计方法中真实存在的 Benchmark 缺口：任务边界不一致、输入输出不可比、代码和权重状态不透明、评分指标与实验可开发性之间存在断层。当前 KB 已经形成较完整的 protocol-first 框架，并用 claim gate 抑制过度结论，适合作为后续服务器 preflight 和 smoke test 的准备层。

主要限制是：尚未冻结 target/control set，尚未产生 server logs、真实 `run.csv`、metric CSV、parser outputs 或 runtime records，方法依赖和权重许可仍未闭环，统计分析计划和 broader impacts 仍偏弱。因此，项目在进入服务器执行前，应先完成 v0.10 preflight package 和 grant-review action closure。

## NIH-style mock review

| criterion | provisional score | assessment |
|:---|:---:|:---|
| Significance | 2 | 多肽设计 Benchmark 的任务分层、可运行性审计和证据边界具有清晰科学需求。 |
| Investigator(s) / team readiness | 5 | 当前仓库未系统说明人员分工、服务器责任人、license 管理和运行日志归档责任。 |
| Innovation | 3 | 创新点在于 protocol-first Benchmark、generation/ranking 分离、readiness gate 和 developability proxy，而不是提出新模型。 |
| Approach | 6 | 框架完整，但缺少 frozen target set、server preflight evidence、统计分析计划和真实 smoke-test 记录。 |
| Environment | 5 | 已有 server readiness checklist 和 method contracts，但 CUDA/Conda、PyRosetta、checkpoint、外部 roots 和预算尚未闭环。 |

### Major Strengths

1. **Significance 明确**：项目针对 linear peptide、cyclic peptide、D-peptide、miniprotein binder 和 ranking/rescoring 之间不可直接比较的问题，提出任务分层。
2. **Approach 边界清楚**：`run.csv -> metric CSVs -> merged_run.csv` 的工程接口清晰，并显式区分 generation benchmark 与 ranking/rescoring benchmark。
3. **证据门控较强**：claim-evidence map、validator 和 AGENTS rules 防止把 source pinning、availability check 或 figure schematic 写成复现证据。
4. **方法覆盖有层次**：10 个 first-wave include methods 与 review-only/watchlist methods 分离，避免过早扩大 Benchmark 范围。
5. **写作基础较好**：中英文大纲、图表计划、参考数据集来源表和补充资料综合已形成 protocol manuscript 的雏形。

### Major Weaknesses

1. **Approach 仍缺执行前闭环**：`target_set_v0.csv` 仍为空，target/control/license/leakage/assay evidence 尚未达到冻结标准。
2. **Preliminary data 不足**：当前没有 method-level server logs、install logs、dry-run logs、smoke-test outputs、metric CSV 或 parser outputs。
3. **统计设计不足**：尚未定义 primary endpoints、missingness handling、top-k enrichment、calibration error、failure-rate denominator 和 confidence intervals。
4. **Environment 风险较高**：PyRosetta、RFdiffusion checkpoint、ProteinMPNN handoff、PepMirror checkpoint/dependency route 和 GPU resource envelope 尚未闭环。
5. **Broader impacts 尚弱**：当前更像内部 KB 和 manuscript skeleton，尚未形成社区复用、教学、FAIR sharing、external user onboarding 和 governance plan。

## NSF-style mock review

### Intellectual Merit

项目的 Intellectual Merit 较强。它不把多肽设计方法混合成单一 leaderboard，而是将任务、输入合同、输出可解析性、结构评分、ranking/rescoring、developability proxy 和 leakage control 分层。这种设计有利于解释为什么 sequence-only 方法、structure-conditioned peptide binder、D-peptide/cyclic peptide 方法和 miniprotein baseline 不应被强行放入同一个性能排名。

需要补强的是：当前 framework transferability 仍停留在 protocol principles，尚不能外推到 performance、runnability 或 biological success。下一步必须用 preflight package 证明至少部分方法和数据接口可以进入服务器端执行准备。

### Broader impacts

Broader impacts 目前不足。项目可以发展为多肽设计 Benchmark 教程、开放 schema、方法 readiness checklist、数据集选择规范和 manuscript template，但当前尚未系统描述目标用户、外部复用路径、培训材料、开放许可、引用规范和结果共享策略。

建议在 v0.10 前补充 open-science and training plan，包括：如何让其他实验室复用 `run.csv` schema、如何提交新的 method contract、如何标注 failed runs、如何报告 no-result evidence、如何避免把 computational proxy 写成 medicinal chemistry endpoint。

## Panel Decision

**模拟 panel decision: Revise before execution。**

项目可以继续推进，但下一轮不应直接进入大规模 Benchmark。建议先完成 v1.3 action closure 和 v0.10 server-side preflight package，再由用户单独批准是否进行 clone、download、environment setup 或 smoke test。

## Required Next Update

### Specific Aim 1: Target and Control Governance

目标是建立 target/control candidate freeze criteria，而不是立即冻结 `target_set_v0.csv`。每个候选靶点至少需要 license、assay readout、positive control、negative/decoy plan、leakage risk、sequence/structure homology status 和 task mapping。

### Specific Aim 2: Server-side Preflight Package

目标是为 PepMLM、RFdiffusion + ProteinMPNN 和 PepMirror 准备服务器端 preflight inputs。产物应包括 external clone root、data root、weights root、download approval manifest、license decision table、environment family、expected command shape 和 no-git-large-file gate。

### Specific Aim 3: Statistical and Scoring Analysis Plan

目标是补齐统计设计。至少定义 parseability、task-compatible output rate、runtime/resource use、failure rate、top-k enrichment、calibration error、ranking agreement、missingness handling、method-level denominator 和 metric applicability rules。

### Specific Aim 4: Broader Impacts and Reuse Plan

目标是将当前 KB 转化为可复用 Benchmark protocol package。应补充 community onboarding、tutorial notebook plan、schema documentation、FAIR sharing policy、citation policy 和 benchmark-report template。

## Recommended Milestones

| milestone | expected artifact | gate |
|:---|:---|:---|
| M1 | target/control freeze checklist | target_gate |
| M2 | server root and license decision table | environment_gate |
| M3 | method preflight package for priority methods | execution_gate |
| M4 | statistical analysis plan | scoring_gate |
| M5 | broader impacts and reuse plan | dissemination_gate |
| M6 | updated validator checks for v1.3/v0.10 readiness | validation_gate |

## Claim Boundary

本审查只支持以下表述：当前项目具有较强 protocol-first Benchmark 设计基础，但在进入真实 Benchmark 执行前仍需完成 target/control governance、server preflight、statistical analysis plan 和 broader impacts plan。

本审查不支持以下表述：候选方法已经本地安装、已复现、代码无问题、数据已下载、target set 已冻结、Benchmark 已完成、某方法优于其他方法、计算评分可替代实验可开发性或药物化学终点。
