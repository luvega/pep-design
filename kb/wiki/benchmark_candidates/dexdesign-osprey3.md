---
title: "DexDesign / OSPREY3 benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/dexdesign-osprey3.md"]
---

# DexDesign / OSPREY3

## 纳入理由
non-neural baseline for D-peptide design

## 最小 Benchmark I/O
- 输入：target structure, D-peptide design site, and search configuration
- 输出：D-peptide inhibitor sequences/conformations
- 目标类型：protein structures
- 多肽类型：D-peptides

## 执行前必须锁定
- 代码：https://github.com/donaldlab/OSPREY3
- 权重：not applicable
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：DexDesign: an OSPREY-based algorithm for designing de novo D-peptide inhibitors
- 追踪 key：guerin_dexdesign_2024
