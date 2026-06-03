# Method Runnability Audit

## Purpose

本报告把第一轮 `include` 候选方法从文献/仓库证据推进到 smoke-test 准备状态。当前判断仍是 metadata 和 repository-route 层级，不代表本地安装或复现。

## Tier Definitions

| tier | meaning |
|:---|:---|
| Tier 1 | 优先进入 smoke-test 设计；代码、权重/模型路线和输入输出映射相对明确 |
| Tier 2 | 保留为第一轮候选；需要先确认 checkpoint、环境、batch route 或输出解析 |
| Tier 3 | 仍在 include set 内，但第一轮 smoke test 延后；主要原因是任务适配或环境映射成本较高 |

## Tier 1

| method | reason | next action |
|:---|:---|:---|
| PepMLM | sequence-only 输入输出清晰，适合作为轻量 peptide sequence baseline | 确认 Hugging Face/model route、license 和 batch inference 命令 |
| PepMirror | D-peptide binder 主题贴合，GitHub/Zenodo route 已记录，输出可映射到结构评分 | 设计最小 target PDB/pocket 输入，记录 checkpoint 和依赖栈 |
| RFdiffusion + ProteinMPNN | 成熟 binder/miniprotein 基线，batch CLI 生态明确 | 固定一个小型 target/hotspot 和输出目录约定 |

## Tier 2

| method | blocker | next action |
|:---|:---|:---|
| DiffPepBuilder | checkpoint 和最小输入 schema 仍需确认 | 查明 Zenodo checkpoint 文件与示例命令 |
| PepGLAD | checkpoint route 和 target-conditioned binder 适配仍需确认 | 复核 repository examples 和输出格式 |
| D-Flow / PeptideDesign | archive/checkpoint provenance 和 D/L mirror handling 需确认 | 记录 mirror conversion 与 output parser 需求 |
| AfCycDesign / ColabDesign cyclic peptide | notebook/AF weights/batch 化成本较高 | 明确 CLI 或 notebook execution contract |
| BindCraft | 依赖重，且更偏 miniprotein/protein binder | 在 RFdiffusion baseline 映射后再设计 smoke test |

## Tier 3

| method | reason | next action |
|:---|:---|:---|
| SaLT&PepPr | degrader/interface 任务与通用 peptide binder benchmark 不完全一致 | 保留背景价值，先映射到 T1 后再决定是否运行 |
| DexDesign / OSPREY3 | OSPREY setup 和 DexDesign 最小案例需要单独梳理 | 先写环境和 workflow mapping，不作为第一批 smoke run |

## Watchlist

PepFlow 和 BoltzDesign1 保持 watchlist，不进入 v0 smoke-test 目录。若后续确认 runnable code、checkpoint 和 peptide/miniprotein 输入场景，可作为替补。

## de_novo_binder_scoring Lessons Adopted

- 用 `run.csv` 做主索引，避免每个方法自带格式直接进入分析层。
- 把输入标准化、模型输入生成、结构预测、指标抽取和 CSV 合并拆开。
- 将 PyRosetta、AF2、AF3、Boltz、ColabFold 等外部工具视为可选评分模块。
- 记录运行时间、环境、license、模型路径和输出目录，避免只保存最终分数。

## Non-Claims

本报告不表示任何方法已在本地安装、运行或复现。所有 `Tier` 仅用于安排下一阶段 smoke-test 优先级。
