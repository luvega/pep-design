---
title: "PepMLM"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:chen_target_2025", "applies_to:benchmark-readiness"]
---

# PepMLM

## 定位
PepMLM 属于 `sequence-conditioned peptide language model`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target protein sequence plus design constraints

## 输出
linear peptide sequences

## 适用 peptide 类型
linear peptide binders

## 依赖
- 代码/服务：https://github.com/programmablebio/pepmlm
- 权重/模型：https://huggingface.co/ChatterjeeLab/PepMLM-650M
- 许可：repository/model-card dependent; verify before benchmark release

## 原始论文
- 题名：Target sequence-conditioned design of peptide binders using masked language modeling
- 年份：2025
- 本地/外部 key：chen_target_2025

## 候选评分
- 输入可标准化：5/5
- 输出可评估：4/5
- GPU 成本可控性：2/5
- 多肽任务贴合度：5/5
- 近年证据：5/5
- 总分：21/25
- 决策：include

## 复现风险
sequence-only design needs downstream structure and binding validation

## Benchmark 前置记录
lock model revision, tokenizer, sampling temperature, target sequence preprocessing
