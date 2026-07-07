# Expert Panel Review v0.4

## Review Scope

本阶段为 v0.4 专家团审查，不运行 Benchmark。审查对象包括 v0.3 的任务协议、候选数据集、方法可运行性、源码路线、环境风险、评分 schema 和 manuscript claim boundaries。

允许的外部动作仅限：

- 将 Overath Zenodo `final_dataset.csv` 下载到 `E:\Codex_Projects\Pep_design_external\datasets\overath_binder_success_2025\` 并做字段级只读审计。
- 将 PepMLM、RFdiffusion、ProteinMPNN、PepMirror shallow clone 到 `E:\Codex_Projects\Pep_design_external\method_sources_v0.4\` 并做源码 pinning 审计。

未执行：未下载完整数据包、未下载权重、未安装环境、未运行 GPU、未把外部源码或数据纳入 git。

## Panel Summary

| reviewer role | main finding | required change |
|:---|:---|:---|
| 药物化学专家 | Developability 需要保持 metadata-level，与实验可开发性端点分离 | 强化 later-stage-only 边界 |
| 计算结构生物学专家 | T1/T2/T3 输出不可直接混排，DockQ/RMSD 依赖 reference complex 和 chain mapping | 保持同任务内比较优先 |
| AI Benchmark 专家 | 需要更明确 planned reporting metrics | 加入 parseability、failure-rate、top-k enrichment、calibration error |
| 数据/统计专家 | Overath `final_dataset.csv` 有 3,676 行，不是描述中的 3,766；另有 7 行 blank target | 作为 calibration candidate，先清洗再分析 |
| 工程复现专家 | source pinning 只证明源码入口和 commit，不证明可安装或可复现 | 记录 `pinned_no_install`，保留 license/weights blockers |

## Critical Findings

1. **Overath row-count discrepancy**
   外部只读扫描显示 `final_dataset.csv` 有 3,676 data rows、312 columns、15 个非空 target_id，以及 7 行 blank `target_id`。这与文献/数据集描述的 3,766 binders 不一致。后续可以继续引用“文献描述为 3,766”，但任何本地数据审计都必须写作“`final_dataset.csv` scanned rows = 3,676”，并在清洗日志中解释差异。

2. **Overath is calibration evidence, not peptide generation evidence**
   该数据集适合 T3 miniprotein/protein binder ranking/rescoring 和 scoring calibration。它不支持 short peptide、cyclic peptide、D-peptide 或 generic peptide generation 方法的性能主张。

3. **Target candidates are not frozen targets**
   `target_candidate_matrix_v0.4.csv` 只是候选矩阵。`target_set_v0.csv` 仍保持 schema-only，直到 positive control、negative/decoy plan、assay evidence、license 和 leakage 初评齐全。

4. **Source pinning is not reproducibility**
   PepMLM、RFdiffusion、ProteinMPNN 和 PepMirror 只有 shallow clone pinning 证据。没有安装、没有权重、没有输入输出、没有 runtime，因此 manuscript 不能写成 “installed”, “reproduced”, “ran locally”。

## Dataset Review

Overath 是 v0.4 唯一完成小文件字段审计的数据集。它包含 `binder_id`, `target_id`, `binder_chain`, `target_chains`, `binder`, `source`, chain sequences, AF2/ColabFold/Boltz1/AF3 confidence metrics, DockQ/RMSD, PyMOL interface metrics, Rosetta metrics, SAP/CamSol-like fields, pDockQ/ipSAE/iPAE 等列。这些字段与本项目 scoring protocol 高度相关，但需要先完成清洗、target overlap、source leakage 和 assay interpretation。

其他候选数据集仍保持 metadata-only：

- PEPBI：可能支持 T2 protein-peptide thermodynamic calibration，但 license/schema 未审计。
- PepMerge/PepBDB/Q-BioLip：适合作为 D-Flow/PepMerge leakage audit source，不应直接作为 independent test。
- PepMirror resources：适合作为 D-peptide leakage/resource audit source，需抽取 target list 和 wet-lab subset。
- Chang AF2 ranking cases：适合作为小型 peptide ranking calibration，需抽取 receptor/peptide/affinity table。
- PepBenchmark/PepBenchData：适合作为 developability/property 背景，需选择与本项目相关的子集。
- GPCR peptide benchmark：适合作为 GPCR-specific background 或 test-candidate，需全文/supplement 审计。

## Source Pinning Review

| method | pin result | blocker |
|:---|:---|:---|
| PepMLM | commit `3169c4920f8c383948e0a5d3a7c8f87e5e7d2436` | no license file and no clear CLI/env file in first-pass scan |
| RFdiffusion | commit `2d0c003df46b9db41d119321f15403dec3716cd9` | checkpoint/weights and environment still unresolved |
| ProteinMPNN | commit `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | RFdiffusion-to-MPNN handoff contract still needed |
| PepMirror | commit `41cb31f3974d91e1a2ca88f0db060405833e4a9c` | PyRosetta/Vina/OpenMM/checkpoint dependencies remain blockers |

## Required v0.5 Preparation

1. 为 Overath 建立清洗日志：解释 3,676 vs 3,766 差异、blank target rows、label distribution 和 target-level split。
2. 对 PepMLM 完成 Hugging Face model-card/license 审计，再决定是否进入 no-download smoke-test stub。
3. 对 RFdiffusion + ProteinMPNN 写最小 no-weight command contract，明确 target PDB、hotspot、chain mapping 和 output folder。
4. 对 PepMirror 完成 PyRosetta、checkpoint 和 Zenodo license 审计，再讨论安装环境。
5. 更新 manuscript 的 planned Results，把专家审查作为方法学贡献之一，而不是性能结果。

## Claim Boundaries

- 可写：v0.4 已完成专家团审查、Overath `final_dataset.csv` 字段级审计、优先源码 pinning 审计。
- 不可写：已复现、已安装、已跑通、已冻结 target set、已完成 Benchmark、Overath 证明 peptide generation 方法性能。
