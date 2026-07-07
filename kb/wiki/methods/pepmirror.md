---
title: "PepMirror"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:yang_cross-chirality_2026", "applies_to:benchmark-readiness"]
---

# PepMirror

## 定位
PepMirror 属于 `latent diffusion for cross-chirality D-peptide binder design`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target PDB, receptor/ligand chains or pocket center, YAML generation config, and checkpoint

## 输出
D-peptide binder complex structures plus post-processing/ranking metrics

## 适用 peptide 类型
mirror-image D-peptide binders

## 依赖
- 代码/服务：https://github.com/YZY010418/PepMirror
- 权重/模型：https://zenodo.org/records/20095187
- 许可：MIT repository license; Zenodo checkpoint license to verify before benchmark release

## 原始论文
- 题名：Cross-Chirality Generalization by Axial Vectors for Hetero-Chiral Protein-Peptide Interaction Design
- 年份：2026
- 本地/外部 key：yang_cross-chirality_2026

## 候选评分
- 输入可标准化：4/5
- 输出可评估：5/5
- GPU 成本可控性：3/5
- 多肽任务贴合度：5/5
- 近年证据：5/5
- 总分：22/25
- 决策：include

## 复现风险
local reproducibility is untested; ranking protocol and affinity correlation still need benchmark-phase validation

## Benchmark 前置记录
record Git commit, Zenodo checkpoint, axial_type, axial_position, mirror mode, pocket definition, chain IDs, ranking thresholds, and PyRosetta/Vina/OpenMM versions
