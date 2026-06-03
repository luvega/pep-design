---
title: "BindCraft"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:pacesa_bindcraft_2024", "applies_to:benchmark-readiness"]
---

# BindCraft

## 定位
BindCraft 属于 `AF2 backpropagation plus MPNN/PyRosetta binder pipeline`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target structure and binder design settings

## 输出
protein/miniprotein binder sequences and structures

## 适用 peptide 类型
miniprotein/protein binders

## 依赖
- 代码/服务：https://github.com/martinpacesa/BindCraft
- 权重/模型：AlphaFold/MPNN/PyRosetta dependencies; verify local setup
- 许可：repository and dependency licenses apply; verify before benchmark release

## 原始论文
- 题名：BindCraft: one-shot design of functional protein binders
- 年份：2024
- 本地/外部 key：pacesa_bindcraft_2024

## 候选评分
- 输入可标准化：4/5
- 输出可评估：5/5
- GPU 成本可控性：4/5
- 多肽任务贴合度：3/5
- 近年证据：5/5
- 总分：21/25
- 决策：include

## 复现风险
heavier dependencies and less direct fit to very short peptide design

## Benchmark 前置记录
record dependency stack, AF2 parameters, PyRosetta version, filters, and design count
