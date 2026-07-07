---
title: "DiffPepBuilder"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:external-search-needed", "applies_to:benchmark-readiness"]
---

# DiffPepBuilder

## 定位
DiffPepBuilder 属于 `structure-conditioned diffusion model`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target protein structure and peptide binding region

## 输出
peptide backbone/sequence candidates

## 适用 peptide 类型
linear peptide binders

## 依赖
- 代码/服务：https://github.com/YuzheWangPKU/DiffPepBuilder
- 权重/模型：https://zenodo.org/records/12794439
- 许可：repository/Zenodo dependent; verify before benchmark release

## 原始论文
- 题名：DiffPepBuilder: a structure-aware diffusion model for peptide binder design
- 年份：2024
- 本地/外部 key：external-search-needed

## 候选评分
- 输入可标准化：4/5
- 输出可评估：5/5
- GPU 成本可控性：3/5
- 多肽任务贴合度：5/5
- 近年证据：4/5
- 总分：21/25
- 决策：include

## 复现风险
requires reliable target structures and pocket/interface definition

## Benchmark 前置记录
pin checkpoint, target chain mapping, peptide length constraints, sampling count
