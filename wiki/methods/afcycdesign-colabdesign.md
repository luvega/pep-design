---
title: "AfCycDesign / ColabDesign cyclic peptide"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:rettie_cyclic_2023", "applies_to:benchmark-readiness"]
---

# AfCycDesign / ColabDesign cyclic peptide

## 定位
AfCycDesign / ColabDesign cyclic peptide 属于 `AlphaFold/ColabDesign cyclic peptide design`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
cyclic peptide scaffold or target/binder context

## 输出
cyclic peptide sequences and predicted structures

## 适用 peptide 类型
cyclic peptides

## 依赖
- 代码/服务：https://github.com/sokrypton/ColabDesign
- 权重/模型：AlphaFold/ColabDesign dependencies; verify local model source
- 许可：ColabDesign and AlphaFold dependency licenses apply

## 原始论文
- 题名：Cyclic peptide structure prediction and design using AlphaFold
- 年份：2023
- 本地/外部 key：rettie_cyclic_2023

## 候选评分
- 输入可标准化：4/5
- 输出可评估：5/5
- GPU 成本可控性：4/5
- 多肽任务贴合度：5/5
- 近年证据：4/5
- 总分：22/25
- 决策：include

## 复现风险
runtime and model-weight dependencies are heavier than sequence-only methods

## Benchmark 前置记录
pin notebook/script version, AF model preset, recycle count, and cyclic constraint encoding
