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
- 输入：protein-peptide complex context and chirality constraints
- 输出：hetero-chiral peptide structures/sequences
- 目标类型：protein-peptide complexes
- 多肽类型：L/D and hetero-chiral peptides

## 执行前必须锁定
- 代码：https://github.com/smiles724/PeptideDesign
- 权重：repository release; verify exact checkpoint location
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：Cross-Chirality Generalization by Axial Vectors for Hetero-Chiral Protein-Peptide Interaction Design
- 追踪 key：yang_cross-chirality_2026
