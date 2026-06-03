---
title: "RFdiffusion + ProteinMPNN"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:bennett_improving_2023", "applies_to:benchmark-readiness"]
---

# RFdiffusion + ProteinMPNN

## 定位
RFdiffusion + ProteinMPNN 属于 `diffusion scaffold generation plus inverse folding sequence design`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target structure, hotspot or motif constraints, design length

## 输出
miniprotein/protein binder backbones and sequences

## 适用 peptide 类型
miniprotein and short protein binders

## 依赖
- 代码/服务：https://github.com/RosettaCommons/RFdiffusion; https://github.com/dauparas/ProteinMPNN
- 权重/模型：RFdiffusion and ProteinMPNN public model releases; verify local download route
- 许可：repository licenses apply; verify before benchmark release

## 原始论文
- 题名：Improving de novo protein binder design with deep learning
- 年份：2023
- 本地/外部 key：bennett_improving_2023

## 候选评分
- 输入可标准化：4/5
- 输出可评估：5/5
- GPU 成本可控性：4/5
- 多肽任务贴合度：4/5
- 近年证据：4/5
- 总分：21/25
- 决策：include

## 复现风险
not peptide-specific for short flexible peptides; interface definition can dominate results

## Benchmark 前置记录
pin RFdiffusion checkpoint, ProteinMPNN version, design length ranges, and AF2 filtering
