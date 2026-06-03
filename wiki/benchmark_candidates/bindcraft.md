---
title: "BindCraft benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/bindcraft.md"]
---

# BindCraft

## 纳入理由
integrated runnable pipeline with strong binder-design relevance

## 最小 Benchmark I/O
- 输入：target structure and binder design settings
- 输出：protein/miniprotein binder sequences and structures
- 目标类型：protein structures
- 多肽类型：miniprotein/protein binders

## 执行前必须锁定
- 代码：https://github.com/martinpacesa/BindCraft
- 权重：AlphaFold/MPNN/PyRosetta dependencies; verify local setup
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：BindCraft: one-shot design of functional protein binders
- 追踪 key：pacesa_bindcraft_2024
