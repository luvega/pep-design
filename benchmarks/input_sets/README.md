# Input Sets

本目录用于后续保存小型标准输入集合说明。当前阶段不加入真实 PDB、FASTA 或大规模 benchmark targets。

## Planned Files

| file | status | purpose |
|:---|:---|:---|
| `target_set_v0.csv` | schema-only | 记录 target_id、任务、target class、controls、assay evidence 和 leakage risk |
| `target_set_v0_schema.md` | active | 说明 target set 字段、target classes 和纳入规则 |
| `negative_design_panel_schema.md` | active | 说明 off-target/negative-control panel 字段 |
| `example_run.csv` | planned | 最小 schema 示例，后续用于 validator 和 smoke-test 演示 |

## Boundary

真实靶点结构、预测输出和大规模结果应在后续 Benchmark 阶段按大小和许可决定是否进入 git。

## Required Target Classes

- `protein_surface_ppi_target`
- `groove_or_pocket_peptide_binding_target`
- `pmhc_tcr_like_recognition_target`
- `d_peptide_or_chirality_aware_target`

## Benchmark Tracks

`target_set_v0.csv` must support both generation benchmark and ranking/rescoring benchmark. Generation tracks test whether methods produce parseable, valid and task-compatible outputs. Ranking/rescoring tracks test whether existing or generated candidates can be prioritised against affinity, structure or developability evidence.
