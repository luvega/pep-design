---
title: "PepFlow"
type: method_card
status: watchlist
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:jiahan_li_full-atom_2024", "applies_to:benchmark-readiness"]
---

# PepFlow

## 定位
PepFlow 属于 `full-atom multi-modal flow matching`。当前状态为 **观察名单**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
peptide design condition; exact benchmark I/O to verify

## 输出
full-atom peptide structures/sequences

## 适用 peptide 类型
peptides

## 依赖
- 代码/服务：https://huggingface.co/Irwiny/PepFlow
- 权重/模型：https://huggingface.co/Irwiny/PepFlow
- 许可：repository dependent; verify before benchmark release

## 原始论文
- 题名：Full-atom peptide design based on multi-modal flow matching
- 年份：2024
- 本地/外部 key：jiahan_li_full-atom_2024

## 候选评分
- 输入可标准化：3/5
- 输出可评估：5/5
- GPU 成本可控性：3/5
- 多肽任务贴合度：5/5
- 近年证据：4/5
- 总分：20/25
- 决策：watchlist

## 复现风险
runnable code route and target-conditioned binder fit require confirmation

## Benchmark 前置记录
promote to include only after executable code, checkpoint use, and input schema are verified
