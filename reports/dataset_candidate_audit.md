# Dataset Candidate Audit

## Purpose

v0.3 进入“数据集候选审计”阶段。本报告只记录可用于后续 Benchmark 的候选数据集、访问路线、许可状态、体量、任务适配和泄漏风险；不下载数据、不冻结真实 target set，也不声明任何方法已完成复现。

候选数据集记录在 `benchmarks/input_sets/candidate_benchmark_datasets.csv`。`target_set_v0.csv` 仍保持 schema-only，后续只有在完成来源、许可、assay、positive/negative controls 和 leakage/homology 审计后，才会写入真实 target rows。

## High-Priority Additions

### `overath_binder_success_2025`

`Predicting Experimental Success in De Novo Binder Design: A Meta-Analysis of 3,766 Experimentally Characterised Binders` 是 v0.3 新增的高优先级数据集候选。当前记录的来源包括 bioRxiv preprint 与 Zenodo dataset：

- Article DOI: `10.1101/2025.08.14.670059`
- Dataset DOI: `10.5281/zenodo.15722219`
- Article version: bioRxiv v2, 2025-09-17
- Zenodo version: v1.0.0, 2025-08-14
- Scope: 3,766 experimentally characterised binders across 15 structurally diverse targets
- Data volume: approximately 9.3 GB total on Zenodo; `final_dataset.csv` is about 82 MB
- License note: article `cc_by_nc_nd`; Zenodo dataset `cc-by-4.0`

该数据集更适合支持 `ranking_rescoring` 和 `scoring_calibration`，尤其是 T3 miniprotein/protein binder baseline 的评分校准、成功/失败特征抽取和 structure-confidence/ranking feature 对照。它不能直接作为 short peptide、D-peptide 或 cyclic peptide generation benchmark 的性能证据。

v0.3 的下载策略固定为 `metadata_only_in_v0.3`。下一步如进入 v0.4，可先只审计 `final_dataset.csv` 的字段和 license，再决定是否采样小型校准子集；不得在未确认许可和存储策略前下载完整预测输出归档。

## Candidate Dataset Summary

| dataset_id | planned role | fit | v0.3 decision |
|:---|:---|:---|:---|
| `overath_binder_success_2025` | scoring calibration and ranking/rescoring | T3 binder success meta-analysis | metadata-only, high priority |
| `pepbi_dryad_2025` | protein-peptide thermodynamic calibration | T2 protein-peptide affinity context | metadata-only, verify schema/license |
| `pepmerge_pepbdb_qbiolip` | source/leakage audit for D-Flow and D-peptide tasks | T2 receptor-conditioned peptide design | metadata-only, map access route |
| `pepmirror_pepbench_protfrag` | PepMirror and D-peptide leakage/resource audit | T2 D-peptide binder design | metadata-only, extract resource list |
| `chang_af2_ranking_cases_2023` | small peptide binder ranking cases | T1/T2 ranking calibration | literature extraction only |
| `pepbenchmark_2026` | peptide property/developability background | developability and property tasks | metadata-only, subset selection later |
| `gpcr_peptide_design_benchmark_2026` | GPCR peptide design benchmark background | T2/T3 GPCR-specific generation/scoring | Zotero/KB extraction later |

## Design Consequences

- Generation benchmark 和 ranking/rescoring benchmark 必须分开。`overath_binder_success_2025` 支持 scoring/ranking 设计，不支持“生成方法优于其他方法”的结论。
- 所有 dataset rows 先记录 `leakage_risk`。来源可能与候选方法训练集、论文 benchmark 或示例 target 重叠时，只能作为 calibration/background case。
- 对 protein-peptide 或 binder success 数据集，必须记录 assay/readout 类型。没有实验读数或标签定义时，不能作为 ranking gold standard。
- 对 D-peptide、cyclic peptide 和 GPCR peptide 任务，必须额外检查 chirality、cycle constraint、chain mapping 和 structure parseability。

## Next Actions

1. 对 `overath_binder_success_2025` 只做 `final_dataset.csv` 字段级审计计划，暂不下载完整 9.3 GB 预测输出。
2. 对 `pepbi_dryad_2025` 核验 Dryad license、字段和 thermodynamic labels。
3. 对 `pepmerge_pepbdb_qbiolip` 与 `pepmirror_pepbench_protfrag` 抽取 train/test split、示例 target、checkpoint 和数据许可。
4. 对 `chang_af2_ranking_cases_2023` 抽取 receptor、peptide、affinity labels 和结构可预测性限制。
5. 对 `gpcr_peptide_design_benchmark_2026` 从 Zotero/KB 卡片进入全文或 supplement 抽取，判断是否能成为 peptide-specific target/control 候选。

## Boundaries

- 本报告不是 dataset download log。
- 本报告不是 frozen target set。
- 当前没有生成 `merged_run.csv`，也没有任何 ranking 或 success prediction 结果。
- 未完成 license、leakage、assay 和 schema 检查前，所有数据集只能写作“候选”或“计划用于”。
