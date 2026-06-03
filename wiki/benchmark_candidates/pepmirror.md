---
title: "PepMirror benchmark candidate"
type: benchmark_candidate
status: include
created: 2026-06-03
wiki_role: candidate_decision
source_count: 1
last_reviewed: 2026-06-03
claims: ["selected for phase-1 shortlist because a public runnable route is available or plausibly available"]
relations: ["derived_from:../methods/pepmirror.md"]
---

# PepMirror

## 纳入理由
directly targets the D-peptide binder gap and provides public code plus checkpoint route

## 最小 Benchmark I/O
- 输入：target PDB, receptor/ligand chains or pocket center, YAML generation config, and checkpoint
- 输出：D-peptide binder complex structures plus post-processing/ranking metrics
- 目标类型：L-protein receptor structures with pocket or reference binder context
- 多肽类型：mirror-image D-peptide binders

## 执行前必须锁定
- 代码：https://github.com/YZY010418/PepMirror
- 权重：https://zenodo.org/records/20095187
- 参数：随机种子、采样数量、长度范围、过滤阈值、目标结构或序列预处理。

## 证据
- 主要论文：Cross-Chirality Generalization by Axial Vectors for Hetero-Chiral Protein-Peptide Interaction Design
- 追踪 key：yang_cross-chirality_2026
