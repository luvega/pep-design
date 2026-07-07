---
title: "D-Flow / PeptideDesign benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/d-flow-peptidedesign.md"]
---

# D-Flow / PeptideDesign

## 纳入理由
covers D-peptide/hetero-chiral space absent from most L-peptide pipelines

## 最小 Benchmark I/O
- 输入：protein receptor/binding context and D-peptide generation configuration
- 输出：full-atom D-peptide sequences and structures
- 目标类型：protein receptor structures
- 多肽类型：D-peptides

## 执行前必须锁定
- 代码：https://github.com/smiles724/PeptideDesign
- 权重：repository archive dflow.zip; verify exact checkpoint provenance
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：D-Flow: Multi-modality Flow Matching for D-peptide Design
- 追踪 key：arxiv:2411.10618
