# Scoring Output Schema

每个评分步骤输出独立 CSV，最终按 `design_id` 合并为 `merged_run.csv`。该策略参考 `de_novo_binder_scoring` 的独立评分脚本与最终 CSV 合并流程。

## Required Tables

| file | merge key | required columns | purpose |
|:---|:---|:---|:---|
| `run.csv` | `design_id` | columns from `run_csv_schema.md` | 主索引 |
| `confidence_metrics.csv` | `design_id` | `design_id,model_source,plddt,ptm,iptm,pae,ipae,ipsae,status,not_applicable_reason` | AF2/ColabFold/Boltz/AF3 类置信度 |
| `interface_metrics.csv` | `design_id` | `design_id,interface_contacts,interface_area,hbond_count,clash_count,status,not_applicable_reason` | 界面几何 |
| `rmsd.csv` | `design_id` | `design_id,reference_id,backbone_rmsd,interface_rmsd,alignment_notes,status,not_applicable_reason` | 结构相似性 |
| `dockq.csv` | `design_id` | `design_id,reference_id,dockq,fnat,irms,lrms,status,not_applicable_reason` | DockQ 或等价指标 |
| `rosetta_metrics.csv` | `design_id` | `design_id,source,total_score,interface_delta_sasa,shape_complementarity,ddg,status,not_applicable_reason` | Rosetta/PyRosetta 指标 |
| `developability_metrics.csv` | `design_id` | `design_id,length,molecular_weight_proxy,net_charge,hydrophobicity,aromaticity,cysteine_disulfide_flags,cyclic_flag,chirality,non_natural_residue_flag,aggregation_risk_proxy,synthesis_complexity_flag,status,not_applicable_reason` | metadata-level 可开发性代理指标 |
| `negative_design_metrics.csv` | `design_id` | `design_id,off_target_id,similarity_to_target,expected_nonbinder_reason,healthy_tissue_or_related_protein_flag,scoring_result,status,not_applicable_reason` | negative/off-target panel |
| `leakage_homology_assessment.csv` | `target_id` | `target_id,method,sequence_identity_cluster,structural_cluster,motif_overlap,train_leakage_risk,status,notes` | target/reference leakage and homology checks |
| `merged_run.csv` | `design_id` | `run.csv` columns plus metric columns | 最终合并表 |

## Missing Metrics

如果某方法不能产生结构输出，结构评分列必须保留为空，并设置：

- `status=not_applicable`
- `not_applicable_reason=sequence_only_output` or another explicit reason

Developability, negative-design and leakage/homology fields may also be `not_applicable`, `not_available`, or `unknown`. Unknown leakage risk cannot be interpreted as independent validation.

## Version Fields

后续真实运行时，每个指标 CSV 应追加：

- `tool_name`
- `tool_version`
- `command`
- `runtime_seconds`
- `environment_id`

这些字段在 v0 协议中推荐但不强制，真实 Benchmark 阶段再纳入强校验。
