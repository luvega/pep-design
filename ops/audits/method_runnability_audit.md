# Method Runnability Audit

## Purpose

本报告把第一轮 `include` 候选方法从文献/仓库证据推进到 smoke-test 准备状态。当前判断仍是 metadata 和 repository-route 层级，不代表本地安装或复现。根据本地 Zotero Benchmark/评分文献的启示，候选方法评价不再只使用单一 Tier，而是同时记录科学优先级、工程准备度和调度 Tier。

## Priority And Readiness Definitions

| field | values | meaning |
|:---|:---|
| `scientific_priority` | high / medium / low | 与 Benchmark 科学问题的贴合度 |
| `engineering_readiness` | ready / needs_mapping / heavy_dependency | 安装、权重、batch route 和依赖复杂度 |
| `tier` | Tier 1 / Tier 2 / Tier 3 | smoke-test 调度 shorthand，不是性能或科学价值排序 |

## Tier 1

| method | scientific priority | engineering readiness | reason | next action |
|:---|:---|:---|:---|:---|
| PepMLM | high | ready | sequence-only 输入输出清晰，适合作为轻量 peptide sequence baseline | 确认 Hugging Face/model route、license 和 batch inference 命令 |
| PepMirror | high | heavy_dependency | D-peptide binder 主题高度贴合，但依赖 PyRosetta/Vina/OpenMM/Zenodo checkpoint，工程负担不轻 | 设计最小 target PDB/pocket 输入，记录 checkpoint 和依赖栈 |
| RFdiffusion + ProteinMPNN | high | needs_mapping | 成熟 binder/miniprotein 基线，batch CLI 生态明确，但仍需锁定权重、版本和过滤路线 | 固定一个小型 target/hotspot 和输出目录约定 |

## Tier 2

| method | scientific priority | engineering readiness | blocker | next action |
|:---|:---|:---|:---|:---|
| DiffPepBuilder | high | needs_mapping | checkpoint 和最小输入 schema 仍需确认 | 查明 Zenodo checkpoint 文件与示例命令 |
| PepGLAD | medium | needs_mapping | checkpoint route 和 target-conditioned binder 适配仍需确认 | 复核 repository examples 和输出格式 |
| D-Flow / PeptideDesign | high | needs_mapping | archive/checkpoint provenance 和 D/L mirror handling 需确认 | 记录 mirror conversion 与 output parser 需求 |
| AfCycDesign / ColabDesign cyclic peptide | high | heavy_dependency | notebook/AF weights/batch 化成本较高 | 明确 CLI 或 notebook execution contract |
| BindCraft | medium | heavy_dependency | 依赖重，且更偏 miniprotein/protein binder | 在 RFdiffusion baseline 映射后再设计 smoke test |

## Tier 3

| method | scientific priority | engineering readiness | reason | next action |
|:---|:---|:---|:---|:---|
| SaLT&PepPr | medium | needs_mapping | degrader/interface 任务与通用 peptide binder benchmark 不完全一致 | 保留背景价值，先映射到 T1 后再决定是否运行 |
| DexDesign / OSPREY3 | medium | heavy_dependency | OSPREY setup 和 DexDesign 最小案例需要单独梳理 | 先写环境和 workflow mapping，不作为第一批 smoke run |

## Watchlist

PepFlow 和 BoltzDesign1 保持 watchlist，不进入 v0 smoke-test 目录。若后续确认 runnable code、checkpoint 和 peptide/miniprotein 输入场景，可作为替补。

## de_novo_binder_scoring Lessons Adopted

- 用 `run.csv` 做主索引，避免每个方法自带格式直接进入分析层。
- 把输入标准化、模型输入生成、结构预测、指标抽取和 CSV 合并拆开。
- 将 PyRosetta、AF2、AF3、Boltz、ColabFold 等外部工具视为可选评分模块。
- 记录运行时间、环境、license、模型路径和输出目录，避免只保存最终分数。

## Zotero Benchmark Literature Lessons Adopted

- `chang_ranking_2023` 和 `romero-molina_ppi-affinity_2022` 支持把 ranking/rescoring 与 de novo generation 分开。
- Binding prediction 文献支持 positive/negative controls、assay labels 和 leakage checks，但不能替代实验验证。
- Developability 文献提示 binding score 不能代表 solubility、stability、membrane permeability、synthesis complexity 或 CMC 风险。

## Non-Claims

本报告不表示任何方法已在本地安装、运行或复现。所有 `Tier` 仅用于安排下一阶段 smoke-test 优先级。
