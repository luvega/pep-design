---
title: "DiffPepBuilder benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/diffpepbuilder.md"]
---

# DiffPepBuilder

## 纳入理由
explicit structural peptide binder generation

## 最小 Benchmark I/O
- 输入：target protein structure and peptide binding region
- 输出：peptide backbone/sequence candidates
- 目标类型：protein structures
- 多肽类型：linear peptide binders

## 执行前必须锁定
- 代码：https://github.com/YuzheWangPKU/DiffPepBuilder
- 权重：https://zenodo.org/records/12794439
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：DiffPepBuilder: a structure-aware diffusion model for peptide binder design
- 追踪 key：external-search-needed
