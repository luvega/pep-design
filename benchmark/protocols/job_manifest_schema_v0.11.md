# job_manifest.csv Schema v0.11

`job_manifest.csv` 是方法运行前的统一 job 表。它描述要交给 method adapter 的输入任务；`run.csv` 仍然是候选设计样本的主索引。

## Required Columns

| column | required | description |
|:---|:---:|:---|
| `job_id` | yes | 全局唯一 job ID，推荐 `<method_slug>_<task_id>_<target_id>_job_<n>` |
| `method` | yes | 方法名，必须匹配 include 或 preflight 方法名 |
| `task_id` | yes | `T1_sequence_binder`, `T2_structure_peptide_binder`, or `T3_miniprotein_binder_baseline` |
| `target_id` | yes | 标准 target ID；placeholder 行必须显式使用 placeholder ID |
| `input_mode` | yes | `pdb_only`, `seq_only_csv`, or `hybrid` |
| `target_sequence` | conditional | sequence-only 或 hybrid job 需要 |
| `target_pdb` | conditional | structure job 需要；真实运行时必须是外部 root 路径 |
| `target_chains` | conditional | structure job 需要；多链用分号分隔 |
| `binder_chain` | conditional | 结构输出约定的 binder chain，默认 `A` |
| `pocket_definition` | no | hotspot residues、chain:resid list、坐标中心或参考 binder |
| `peptide_type` | yes | `linear`, `cyclic`, `D-peptide`, `heterochiral`, `miniprotein`, or `protein_binder` |
| `chirality` | yes | `L`, `D`, `mixed`, or `not_applicable` |
| `cyclic` | yes | `yes`, `no`, or `unknown` |
| `n_designs_requested` | yes | 计划请求的候选数量；dry-run 可为 1 |
| `random_seed` | no | 可复现实验 seed；若方法不支持则留空 |
| `adapter_config` | yes | adapter 配置 ID 或短标签，不保存大 JSON |
| `status` | yes | `planned`, `approved_for_dry_run`, `dry_run_completed`, `approved_for_smoke_test`, `smoke_test_completed`, `failed`, `blocked`, or `not_real_benchmark` |
| `notes` | no | 简短人工说明 |

## Relationship To run.csv

- 一个 `job_id` 可生成多个 `design_id`。
- `run.csv` 负责候选级索引；后续真实运行时可追加 `parent_job_id`、`source_output_id`、`generation_rank`、`random_seed`、`adapter_status` 和 `status_reason`。
- `example_job_manifest_v0.11.csv` 只用于 adapter/schema 测试，不得进入真实 Benchmark 结果。

## Placeholder Boundary

`status=not_real_benchmark` 只允许用于人工示例、schema 测试和 dry-run planning。真实 smoke test 或 benchmark result 中不得出现该状态。
