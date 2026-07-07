---
title: "DexDesign / OSPREY3"
type: method_card
status: include
created: 2026-06-03
wiki_role: benchmark_method
source_count: 1
last_reviewed: 2026-06-03
claims: ["candidate readiness is based on public-code and source-paper evidence, not local benchmark execution"]
relations: ["derived_from:guerin_dexdesign_2024", "applies_to:benchmark-readiness"]
---

# DexDesign / OSPREY3

## 定位
DexDesign / OSPREY3 属于 `energy/search-based D-peptide design`。当前状态为 **纳入候选**；该判断只用于第一阶段方法筛选，不代表已经完成本地复现。

## 输入
target structure, D-peptide design site, and search configuration

## 输出
D-peptide inhibitor sequences/conformations

## 适用 peptide 类型
D-peptides

## 依赖
- 代码/服务：https://github.com/donaldlab/OSPREY3
- 权重/模型：not applicable
- 许可：OSPREY3 license applies; verify before benchmark release

## 原始论文
- 题名：DexDesign: an OSPREY-based algorithm for designing de novo D-peptide inhibitors
- 年份：2024
- 本地/外部 key：guerin_dexdesign_2024

## 候选评分
- 输入可标准化：3/5
- 输出可评估：4/5
- GPU 成本可控性：1/5
- 多肽任务贴合度：4/5
- 近年证据：4/5
- 总分：16/25
- 决策：include

## 复现风险
configuration burden may be higher than generative pipelines

## Benchmark 前置记录
document OSPREY version, force-field settings, search budget, and target preparation
