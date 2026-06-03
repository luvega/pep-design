---
title: "PepGLAD benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/pepglad.md"]
---

# PepGLAD

## 纳入理由
full-atom output is directly useful for structure-level benchmark metrics

## 最小 Benchmark I/O
- 输入：peptide design condition and optional target/interface context
- 输出：full-atom peptide structures/sequences
- 目标类型：peptide or protein-peptide contexts
- 多肽类型：linear and constrained peptide candidates

## 执行前必须锁定
- 代码：https://github.com/THUNLP-MT/PepGLAD
- 权重：repository release; verify exact checkpoint location
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：Full-atom peptide design with geometric latent diffusion
- 追踪 key：kong_full-atom_2025
