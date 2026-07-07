---
title: "BoltzDesign1"
type: method_card
status: watchlist
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:cho_boltzdesign1_2025", "applies_to:benchmark-readiness"]
---

# BoltzDesign1

## 定位
BoltzDesign1 属于 `all-atom structure-prediction inversion`。当前状态为 **观察名单**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target complex/design specification

## 输出
binder sequences/structures

## 适用 peptide 类型
general binders; peptide/miniprotein fit to verify

## 依赖
- 代码/服务：https://github.com/jwohlwend/boltz
- 权重/模型：Boltz model releases; verify design-specific route
- 许可：repository/model dependent; verify before benchmark release

## 原始论文
- 题名：BoltzDesign1: Inverting All-Atom Structure Prediction Model for Generalized Biomolecular Binder Design
- 年份：2025
- 本地/外部 key：cho_boltzdesign1_2025

## 候选评分
- 输入可标准化：3/5
- 输出可评估：4/5
- GPU 成本可控性：4/5
- 多肽任务贴合度：3/5
- 近年证据：5/5
- 总分：19/25
- 决策：watchlist

## 复现风险
not first-wave unless peptide/miniprotein inputs and execution path are confirmed

## Benchmark 前置记录
record exact design command and whether it is standalone or requires server/API
