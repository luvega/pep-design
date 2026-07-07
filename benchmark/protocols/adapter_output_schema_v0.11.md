# Adapter Output Schema v0.11

本 schema 定义 method adapter 到统一评分层之间的输出接口。它不替代现有 metric CSV；它只记录方法原始输出如何被解析成候选级索引。

## method_output_manifest.csv

| column | required | description |
|:---|:---:|:---|
| `run_record_id` | yes | 单次命令记录 ID |
| `job_id` | yes | 对应 `job_manifest.csv` 的 job |
| `method` | yes | 方法名 |
| `task_id` | yes | 标准 task ID |
| `execution_stage` | yes | `source_check`, `dry_run_plan`, `dry_run`, `smoke_test`, or `benchmark` |
| `source_commit` | yes | 代码 commit；未 clone 时写 `not_cloned` |
| `model_revision` | yes | model/checkpoint revision；未下载时写 `not_downloaded` 或 `not_applicable` |
| `environment_id` | yes | 环境 ID；未创建时写 `not_created` |
| `command` | yes | 真实命令或 `placeholder_only_do_not_run` |
| `raw_output_root` | yes | 外部 output root；不得指向 KB 内大文件目录 |
| `stdout_log` | no | 外部 stdout log 路径或 `not_run` |
| `stderr_log` | no | 外部 stderr log 路径或 `not_run` |
| `runtime_seconds` | no | 真实运行耗时；未运行时写 `not_run` |
| `exit_code` | no | 真实 exit code；未运行时写 `not_run` |
| `parser_status` | yes | `not_real_benchmark`, `not_run`, `parsed`, `partial`, `failed`, or `not_applicable` |
| `status_reason` | yes | 失败、跳过或 placeholder 原因 |
| `created_at` | yes | ISO date |

## candidate_outputs.csv

| column | required | description |
|:---|:---:|:---|
| `design_id` | yes | 候选级 ID，必须能合并到 `run.csv` |
| `job_id` | yes | 上游 job |
| `method` | yes | 方法名 |
| `target_id` | yes | target ID |
| `binder_id` | yes | 方法内部候选 ID；未知时与 `design_id` 相同 |
| `source_output_id` | yes | 原始文件名、record ID 或 `not_generated` |
| `generation_rank` | no | 方法原始 rank；无 rank 时留空 |
| `sequence` | conditional | sequence 输出；结构-only 失败行可留空 |
| `structure_path` | conditional | 外部 PDB 或结构路径；sequence-only 可留空 |
| `peptide_type` | yes | 同 `run.csv` |
| `chirality` | yes | 同 `run.csv` |
| `cyclic` | yes | 同 `run.csv` |
| `parse_status` | yes | `not_real_benchmark`, `parsed`, `partial`, `failed`, or `not_applicable` |
| `status_reason` | yes | parser 或输出状态说明 |
| `notes` | no | 简短说明 |

## Merge Rule

1. `method_output_manifest.csv` 记录命令级证据。
2. `candidate_outputs.csv` 记录候选级解析结果。
3. `run.csv` 通过 `design_id` 合并候选级输出。
4. 评分 CSV 和 `merged_run.csv` 继续按 `design_id` 合并。

没有 `command`、`input`、`output`、`runtime`、`environment`、`parser_status` 和 failure state 的记录不得作为 `smoke_test_ready` 证据。
