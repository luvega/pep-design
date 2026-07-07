---
title: "PepGLAD"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:kong_full-atom_2025", "applies_to:benchmark-readiness"]
---

# PepGLAD

## 定位
PepGLAD 属于 `full-atom geometric latent diffusion`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
peptide design condition and optional target/interface context

## 输出
full-atom peptide structures/sequences

## 适用 peptide 类型
linear and constrained peptide candidates

## 依赖
- 代码/服务：https://github.com/THUNLP-MT/PepGLAD
- 权重/模型：repository release; verify exact checkpoint location
- 许可：repository dependent; verify before benchmark release

## 原始论文
- 题名：Full-atom peptide design with geometric latent diffusion
- 年份：2025
- 本地/外部 key：kong_full-atom_2025

## 候选评分
- 输入可标准化：4/5
- 输出可评估：5/5
- GPU 成本可控性：3/5
- 多肽任务贴合度：5/5
- 近年证据：5/5
- 总分：22/25
- 决策：include

## 复现风险
target-conditioned binder task may require adaptation

## Benchmark 前置记录
record atom naming, stereochemistry, random seed, and relaxation steps
