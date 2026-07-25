# Input Sets

本目录保存小型输入合同、候选清单和 job manifest。运行时 PDB、FASTA 与大规模 benchmark targets 留在外部或 gitignored 路径。

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
| `batch_b_target_review_queue_v0.16.csv` | active | v0.16 Batch B target/control review queue；不是 frozen target set |
| `batch_b_pilot_target_gate_v0.17.csv` | active | v0.17 pilot fixture/review gate；不是 frozen target set |
| `batch_b_pilot_job_manifest_v0.17.csv` | active | v0.17 planned fixture jobs；不是运行证据 |
| `multi_case_fixture_target_manifest_v0.22.csv` | active | v0.22 multi-case fixture target manifest；不是 frozen target set |
| `multi_case_fixture_control_manifest_v0.22.csv` | active | v0.22 fixture control manifest；不是 assay validation 或 scoring evidence |
| `multi_case_fixture_job_manifest_v0.22.csv` | active | v0.22 planned/blocked fixture jobs；不是运行证据 |
| `pilot_benchmark_target_manifest_v0.30.csv` | active | v0.30 pilot target fixture 清单；不是 frozen target set |
| `pilot_benchmark_control_manifest_v0.30.csv` | active | v0.30 pilot control 清单；不是 assay 或 scoring evidence |
| `pilot_benchmark_job_manifest_v0.30.csv` | historical | v0.30 Wave A/Wave B 计划任务；运行状态由后续版本记录 |
| `pilot_benchmark_job_manifest_v0.34.csv` | historical | v0.34 七种方法的 seed42 主运行与 seed43 条件扩展合同；不是评分资格清单 |
| `pilot_pepglad_job_manifest_v0.35.csv` | current | v0.35 唯一授权的 PepGLAD seed42 mixed L/D report-only 连通性合同；不是候选或评分证据 |
| `wet_lab_candidate_panel_v0.30.csv` | prospective | 后续候选类别；不是 wet-lab 结果 |
| `dataset_supplement_schema_review_v0.7.csv` | active | v0.7 数据集补充材料 schema-review 队列，记录 license/schema/controls/leakage 的下一步审查状态 |
| `dataset_supplement_schema_review_v0.8.csv` | active | v0.8 数据源 license/schema/controls/leakage 审计结果；仍不代表 target-set promotion |
| `example_run.csv` | active | v0.7 人工 run.csv placeholder，用于服务器 dry-run 输入合同检查；不是 benchmark target 或结果 |

## Boundary

真实靶点结构、预测输出和大规模结果应在后续 Benchmark 阶段按大小和许可决定是否进入 git。v0.4 允许小型 CSV/metadata 外部审计，但不把外部数据文件放入 git，也不把候选数据集写成 frozen target set。

v0.5 继续保持 no-download 边界，只记录 API/HEAD/local metadata 检查结果。`target_set_v0.csv` 仍是 frozen target set 的唯一入口。

v0.7 的 `example_run.csv` 只允许 `status=not_real_benchmark` 的人工占位行，用于验证字段、路径约定和服务器 dry-run 合同。它不代表真实靶点集、生成输出或性能证据。

v0.8 的 `dataset_supplement_schema_review_v0.8.csv` 可以记录外部 API 或论文元数据审计结果，但不能把任何 row 写入 `target_set_v0.csv`。目标晋升仍需 license、schema、controls、assay 和 leakage 全部关闭。

v0.14 的 `target_candidate_academic_search_v0.14.csv` 只记录方法论文案例、PDB 案例和公开 panel 的 metadata-level 候选。它不能替代 `target_set_v0.csv`，也不能作为数据下载、assay 复核、leakage clearance 或 Benchmark 结果证据。

v0.17 的 `batch_b_pilot_target_gate_v0.17.csv` 和 `batch_b_pilot_job_manifest_v0.17.csv` 只记录 pilot gate 和 planned fixture jobs。它们不冻结 `target_set_v0.csv`，不证明 target/control 已闭环，也不是运行或性能证据。

v0.22 的 `multi_case_fixture_target_manifest_v0.22.csv`、`multi_case_fixture_control_manifest_v0.22.csv` 和 `multi_case_fixture_job_manifest_v0.22.csv` 只把 v0.21 method-example adapter 证据标准化为 multi-case fixture pilot 计划。它们不冻结 `target_set_v0.csv`，不代表 D-Flow、ColabDesign 或 BindCraft gate 已解决，也不是运行、scoring、ranking 或 Benchmark result。

v0.34 的 `pilot_benchmark_job_manifest_v0.34.csv` 固定 7 种方法的主运行与条件扩展合同。它只约束 fixture、链、长度、手性、拓扑、seed 和输出接口；它不把 3EQS、7ZKR 或序列 fixture 晋升为 frozen target set，也不授予 scoring 或 ranking 资格。D-Flow 3EQS 有已知训练重叠，只能用于连通性检查。Manifest 中的 target 字段不能追溯补齐历史 DiffPepBuilder/PepGLAD attempt 缺少的新增 target preflight 证据。

v0.35 的 `pilot_pepglad_job_manifest_v0.35.csv` 只授权 `v035_pepglad_3eqs_seed42` 的一个 `attempt_001`。该 attempt 因 Docker API 权限不足在容器启动前失败，没有候选或 QC。Manifest 仍是输入合同，不得据此声称 mixed L/D policy 已获得运行验证；`attempt_001` 不得覆盖或自动重试。

## Required Target Classes

- `protein_surface_ppi_target`
- `groove_or_pocket_peptide_binding_target`
- `pmhc_tcr_like_recognition_target`
- `d_peptide_or_chirality_aware_target`

## Benchmark Tracks

`target_set_v0.csv` must support both generation benchmark and ranking/rescoring benchmark. Generation tracks test whether methods produce parseable, valid and task-compatible outputs. Ranking/rescoring tracks test whether existing or generated candidates can be prioritised against affinity, structure or developability evidence.
