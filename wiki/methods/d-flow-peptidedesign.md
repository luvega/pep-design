---
title: "D-Flow / PeptideDesign"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:yang_cross-chirality_2026", "applies_to:benchmark-readiness"]
---

# D-Flow / PeptideDesign

## 定位
D-Flow / PeptideDesign 属于 `flow matching for hetero-chiral peptide design`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
protein-peptide complex context and chirality constraints

## 输出
hetero-chiral peptide structures/sequences

## 适用 peptide 类型
L/D and hetero-chiral peptides

## 依赖
- 代码/服务：https://github.com/smiles724/PeptideDesign
- 权重/模型：repository release; verify exact checkpoint location
- 许可：repository dependent; verify before benchmark release

## 原始论文
- 题名：Cross-Chirality Generalization by Axial Vectors for Hetero-Chiral Protein-Peptide Interaction Design
- 年份：2026
- 本地/外部 key：yang_cross-chirality_2026

## 候选评分
- 输入可标准化：3/5
- 输出可评估：5/5
- GPU 成本可控性：3/5
- 多肽任务贴合度：5/5
- 近年证据：5/5
- 总分：21/25
- 决策：include

## 复现风险
benchmark tasks need explicit chirality-aware validation metrics

## Benchmark 前置记录
record stereochemistry encoding and any L-only fallback handling
