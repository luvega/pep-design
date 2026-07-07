---
title: "RFdiffusion + ProteinMPNN benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/rfdiffusion-proteinmpnn.md"]
---

# RFdiffusion + ProteinMPNN

## 纳入理由
established runnable baseline for miniprotein/binder design

## 最小 Benchmark I/O
- 输入：target structure, hotspot or motif constraints, design length
- 输出：miniprotein/protein binder backbones and sequences
- 目标类型：protein structures
- 多肽类型：miniprotein and short protein binders

## 执行前必须锁定
- 代码：https://github.com/RosettaCommons/RFdiffusion; https://github.com/dauparas/ProteinMPNN
- 权重：RFdiffusion and ProteinMPNN public model releases; verify local download route
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：Improving de novo protein binder design with deep learning
- 追踪 key：bennett_improving_2023
