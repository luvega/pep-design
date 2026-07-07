---
title: "SaLT&PepPr benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/salt-peppr.md"]
---

# SaLT&PepPr

## 纳入理由
connects peptide design with interface prediction and degrader use cases

## 最小 Benchmark I/O
- 输入：target sequence and degrader/interface design context
- 输出：peptide-guided protein degrader candidates
- 目标类型：protein targets from sequence and interface context
- 多肽类型：linear peptide-guided binders/degraders

## 执行前必须锁定
- 代码：https://github.com/programmablebio/saltnpeppr
- 权重：https://huggingface.co/ubiquitx/saltnpeppr
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：SaLT&PepPr is an interface-predicting language model for designing peptide-guided protein degraders
- 追踪 key：brixi_saltpeppr_2023
