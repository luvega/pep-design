---
title: "AfCycDesign / ColabDesign cyclic peptide benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/afcycdesign-colabdesign.md"]
---

# AfCycDesign / ColabDesign cyclic peptide

## 纳入理由
strong baseline for cyclic peptide structural design

## 最小 Benchmark I/O
- 输入：cyclic peptide scaffold or target/binder context
- 输出：cyclic peptide sequences and predicted structures
- 目标类型：peptides and optional protein targets
- 多肽类型：cyclic peptides

## 执行前必须锁定
- 代码：https://github.com/sokrypton/ColabDesign
- 权重：AlphaFold/ColabDesign dependencies; verify local model source
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：Cyclic peptide structure prediction and design using AlphaFold
- 追踪 key：rettie_cyclic_2023
