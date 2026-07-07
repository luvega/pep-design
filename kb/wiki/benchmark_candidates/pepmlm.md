---
title: "PepMLM benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/pepmlm.md"]
---

# PepMLM

## 纳入理由
directly targets peptide binder design from target sequence, low setup cost

## 最小 Benchmark I/O
- 输入：target protein sequence plus design constraints
- 输出：linear peptide sequences
- 目标类型：protein targets from sequence
- 多肽类型：linear peptide binders

## 执行前必须锁定
- 代码：https://github.com/programmablebio/pepmlm
- 权重：https://huggingface.co/ChatterjeeLab/PepMLM-650M
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：Target sequence-conditioned design of peptide binders using masked language modeling
- 追踪 key：chen_target_2025
