# Input Sets

本目录用于后续保存小型标准输入集合说明。当前阶段不加入真实 PDB、FASTA 或大规模 benchmark targets。

## Planned Files

| file | status | purpose |
|:---|:---|:---|
| `target_set_v0.csv` | schema-only | 记录 target_id、任务、target class、controls、assay evidence 和 leakage risk |
| `target_set_v0_schema.md` | active | 说明 target set 字段、target classes 和纳入规则 |
| `negative_design_panel_schema.md` | active | 说明 off-target/negative-control panel 字段 |
| `candidate_benchmark_datasets.csv` | active | 记录候选 benchmark/scoring/dataset 来源、许可、体量、leakage risk 和 v0.3 download policy |
| `dataset_readiness_scorecard.csv` | active | v0.4 数据集 readiness 审查，记录 license、schema、assay、controls、leakage、task fit 和 decision |
| `target_candidate_matrix_v0.4.csv` | active | v0.4 靶点候选矩阵；不是 frozen target set |
| `target_candidate_matrix_v0.5.csv` | active | v0.5 靶点候选矩阵，结合在线可用性审计更新 server-prep decision |
| `target_candidate_academic_search_v0.14.csv` | active | v0.14 academic-search 靶点/数据集/panel 候选矩阵；不是 frozen target set |
| `dataset_supplement_schema_review_v0.7.csv` | active | v0.7 数据集补充材料 schema-review 队列，记录 license/schema/controls/leakage 的下一步审查状态 |
| `dataset_supplement_schema_review_v0.8.csv` | active | v0.8 数据源 license/schema/controls/leakage 审计结果；仍不代表 target-set promotion |
| `example_run.csv` | active | v0.7 人工 run.csv placeholder，用于服务器 dry-run 输入合同检查；不是 benchmark target 或结果 |

## Boundary

真实靶点结构、预测输出和大规模结果应在后续 Benchmark 阶段按大小和许可决定是否进入 git。v0.4 允许小型 CSV/metadata 外部审计，但不把外部数据文件放入 git，也不把候选数据集写成 frozen target set。

v0.5 继续保持 no-download 边界，只记录 API/HEAD/local metadata 检查结果。`target_set_v0.csv` 仍是 frozen target set 的唯一入口。

v0.7 的 `example_run.csv` 只允许 `status=not_real_benchmark` 的人工占位行，用于验证字段、路径约定和服务器 dry-run 合同。它不代表真实靶点集、生成输出或性能证据。

v0.8 的 `dataset_supplement_schema_review_v0.8.csv` 可以记录外部 API 或论文元数据审计结果，但不能把任何 row 写入 `target_set_v0.csv`。目标晋升仍需 license、schema、controls、assay 和 leakage 全部关闭。

v0.14 的 `target_candidate_academic_search_v0.14.csv` 只记录方法论文案例、PDB 案例和公开 panel 的 metadata-level 候选。它不能替代 `target_set_v0.csv`，也不能作为数据下载、assay 复核、leakage clearance 或 Benchmark 结果证据。

## Required Target Classes

- `protein_surface_ppi_target`
- `groove_or_pocket_peptide_binding_target`
- `pmhc_tcr_like_recognition_target`
- `d_peptide_or_chirality_aware_target`

## Benchmark Tracks

`target_set_v0.csv` must support both generation benchmark and ranking/rescoring benchmark. Generation tracks test whether methods produce parseable, valid and task-compatible outputs. Ranking/rescoring tracks test whether existing or generated candidates can be prioritised against affinity, structure or developability evidence.
