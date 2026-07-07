# Updated Plan v1.3: Grant-Style Mock Review Closure And v0.10 Preflight Package

## Summary

v1.3 是对 `research-grants` 模拟评审意见的计划性响应。它不取代 `ops/plans/updated_plan_v0.9.md` 作为当前权威计划，而是在 v0.9、v1.0、v1.1 和 v1.2 的基础上增加一个 grant-review closure layer，用于准备下一阶段 v0.10 server-side preflight package。

本阶段继续不下载数据、不 clone 第三方源码、不安装环境、不下载模型权重、不运行 GPU、不冻结 `target_set_v0.csv`、不声明任何候选方法已本地复现或代码无问题。

## Review-Derived Rationale

基金评审式审查认为当前项目的 Significance 和 Innovation 较强，但 Approach、Environment、statistical analysis plan 和 Broader impacts 仍需补齐。主要原因是当前证据仍停留在 protocol/readiness 层，尚无 server logs、真实 `run.csv`、metric CSV、parser outputs、runtime records 或 smoke-test outputs。

v1.3 的目标是把这些开放项转成可验证的下一步工作包，而不是跳过门控直接执行 Benchmark。

## Specific Aim 1: Target and Control Governance

目标：建立 target/control candidate freeze criteria，为后续 `target_set_v0.csv` 的正式冻结提供判定规则。

计划动作：

1. 为每个 candidate target 记录 license、assay readout、positive control、negative or decoy control、task mapping、leakage risk、sequence/structure homology status 和 provenance。
2. 将 Overath、PEPBI、PepBenchmark、GPCR peptide benchmark、TCRTransBench、Chang AF2 ranking cases 等资源继续作为 candidate/reference sources，而不是 frozen targets。
3. 建立 target-freeze checklist，只有 controls、assay、license、leakage 和 provenance 全部闭环后，才允许写入 `benchmark/input_sets/target_set_v0.csv`。

交付物建议：

- `benchmark/input_sets/target_control_freeze_checklist_v0.10.md`
- `benchmark/input_sets/target_candidate_decision_matrix_v0.10.csv`

## Specific Aim 2: Server-side Preflight Package

目标：在不执行下载或安装的前提下，为 v0.10 服务器端操作准备可审批包。

优先方法：

1. PepMLM：Hugging Face model route、repository license boundary、batch CSV input wrapper、sequence-only scoring handoff。
2. RFdiffusion + ProteinMPNN：RFdiffusion checkpoint route、ProteinMPNN handoff、contig/hotspot input contract、fixed-chain policy。
3. PepMirror：PyRosetta/Vina/OpenMM/Zenodo checkpoint blockers、license route、dependency feasibility boundary。

计划动作：

1. 定义 external clone root、data root、weights root、results root 和 no-git-large-file policy。
2. 将每个 method contract 升级为 preflight package，不超过 `dry_run_ready` gate。
3. 为每个下载或 checkpoint route 建立 approval row，所有行保持 `download_performed=no`，直到用户批准服务器执行。

交付物建议：

- `benchmark/deployment/server_preflight_package_v0.10.md`
- `benchmark/deployment/preflight_download_approval_v0.10.csv`
- `benchmark/deployment/method_preflight_status_v0.10.csv`

## Specific Aim 3: Statistical And Scoring Analysis Plan

目标：在真实运行前定义 primary endpoints、统计口径和缺失值处理，避免后验选择指标。

计划指标：

1. Generation benchmark: parseability、valid output rate、task-compatible output rate、failure rate、runtime、GPU memory、output completeness。
2. Ranking/rescoring benchmark: top-k enrichment、rank correlation、calibration error、score separation、confidence interval、method-level denominator。
3. Structure/interface scoring: pLDDT、pTM、ipTM、PAE/iPAE、ipSAE、contacts、interface area、H-bonds、clash count、DockQ、RMSD。
4. Developability metadata: length、charge、hydrophobicity、aromaticity、cysteine/disulfide flag、cyclic flag、D/L/mixed chirality、non-natural residue flag、aggregation-risk proxy、synthesis complexity flag。

交付物建议：

- `benchmark/scoring/statistical_analysis_plan_v0.10.md`
- `benchmark/scoring/metric_applicability_matrix_v0.10.csv`

## Specific Aim 4: Broader Impacts And Reuse Plan

目标：把当前 KB 转化为可复用的 Benchmark protocol package。

计划动作：

1. 建立 external user onboarding：如何理解 `run.csv`、method contract、score CSV 和 claim gate。
2. 建立 community contribution policy：如何新增方法、数据集或 target candidate，而不破坏 source boundaries。
3. 建立 tutorial and training plan：用人工 placeholder 示例展示 pipeline，不使用真实 Benchmark 输出冒充结果。
4. 建立 FAIR sharing policy：说明哪些 artifacts 可共享、哪些外部数据/权重/源码不能纳入仓库。

交付物建议：

- `manuscript/support/broader_impacts_and_reuse_plan_v1.3.md`
- `manuscript/support/benchmark_user_onboarding_outline_v1.3.md`

## Acceptance Criteria

v1.3/v0.10 前置更新完成时应满足：

1. `kb/tables/grant_review_action_items_v1.3.csv` 至少包含 10 条行动项，并覆盖 NIH-style mock review、NSF-style mock review、data sharing、risk mitigation 和 budget/resource feasibility。
2. 关键行动项必须标注 severity、decision、status、evidence、next_action 和 gate。
3. 所有 reader-facing 文档继续说明：source pinning、download manifest、availability check、method contract、figure schematic 和 planning table 都不是执行证据。
4. `target_set_v0.csv` 继续可以为空；若有条目，必须满足 controls、assay、license、leakage 和 provenance 字段。
5. `scripts/validate_benchmark_kb.py` 检查 v1.3 评审层并生成 `ops/validation/wiki_validation_report.md`。

## Explicit Non-Actions

- No clone.
- No download.
- No install.
- No model weights.
- No GPU run.
- No server execution.
- No target-set freeze.
- No method superiority claim.
- No local reproducibility claim.

## Relationship To Current Plan

`ops/plans/updated_plan_v0.9.md` 仍是当前权威计划。v1.3 是一层 grant-review-driven update plan，用于帮助决定 v0.10 server-side preflight package 的具体范围。只有在用户明确批准后，后续才可进入服务器端 clone、download、environment setup 或 smoke-test 执行。
