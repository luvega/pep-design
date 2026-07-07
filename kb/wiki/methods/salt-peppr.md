---
title: "SaLT&PepPr"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:brixi_saltpeppr_2023", "applies_to:benchmark-readiness"]
---

# SaLT&PepPr

## 定位
SaLT&PepPr 属于 `interface-predicting protein language model`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target sequence and degrader/interface design context

## 输出
peptide-guided protein degrader candidates

## 适用 peptide 类型
linear peptide-guided binders/degraders

## 依赖
- 代码/服务：https://github.com/programmablebio/saltnpeppr
- 权重/模型：https://huggingface.co/ubiquitx/saltnpeppr
- 许可：repository/model-card dependent; verify before benchmark release

## 原始论文
- 题名：SaLT&PepPr is an interface-predicting language model for designing peptide-guided protein degraders
- 年份：2023
- 本地/外部 key：brixi_saltpeppr_2023

## 候选评分
- 输入可标准化：4/5
- 输出可评估：4/5
- GPU 成本可控性：2/5
- 多肽任务贴合度：4/5
- 近年证据：4/5
- 总分：18/25
- 决策：include

## 复现风险
application focus may be narrower than general peptide binder design

## Benchmark 前置记录
define whether benchmark scores design quality or degrader-specific interface prediction
