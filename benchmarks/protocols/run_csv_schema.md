# run.csv Schema

`run.csv` 是后续 Benchmark 的主索引，作用类似 `de_novo_binder_scoring` 的统一运行表：每个设计样本占一行，所有模型输出和评分 CSV 后续都按 `design_id` 合并。

## Required Columns

| column | required | description |
|:---|:---:|:---|
| `design_id` | yes | 全局唯一设计样本 ID，推荐 `<method_slug>_<task_id>_<target_id>_<n>` |
| `method` | yes | 方法名，必须匹配 `tables/candidate_method_scorecard.csv` |
| `task_id` | yes | `T1_sequence_binder`, `T2_structure_peptide_binder`, or `T3_miniprotein_binder_baseline` |
| `target_id` | yes | 标准靶点 ID |
| `binder_id` | yes | 方法内部候选 ID；未知时与 `design_id` 相同 |
| `input_mode` | yes | `pdb_only`, `seq_only_csv`, or `hybrid` |
| `target_sequence` | conditional | sequence-only 或 hybrid 任务需要 |
| `target_pdb` | conditional | structure 任务需要 |
| `target_chains` | conditional | structure 任务需要；多链用分号分隔 |
| `binder_chain` | conditional | structure 输出需要；默认 `A` |
| `pocket_definition` | no | hotspot residues、chain:resid list、坐标中心或参考 binder |
| `peptide_type` | yes | `linear`, `cyclic`, `D-peptide`, `heterochiral`, `miniprotein`, or `protein_binder` |
| `chirality` | yes | `L`, `D`, `mixed`, or `not_applicable` |
| `cyclic` | yes | `yes`, `no`, or `unknown` |
| `status` | yes | `planned`, `generated`, `scored`, `failed`, `not_applicable`, or `deferred` |
| `notes` | no | 简短人工说明 |

## Chain Convention

参考 `de_novo_binder_scoring` 的输入处理约定，本项目默认：

- binder chain 映射为 `A`。
- target chain 映射为 `B`。
- 多 target subchain 可用 `B,C,D...` 记录。
- 结构方法如果原始 PDB chain 不符合该约定，后续预处理脚本必须保留原始 chain 到标准 chain 的映射日志。

## Input Modes

| mode | use case |
|:---|:---|
| `pdb_only` | 从 PDB 提取 target/binder 信息，适合已有复合物或结构设计输出 |
| `seq_only_csv` | 只使用 CSV 中的 target/peptide sequence，适合 PepMLM 等 sequence-first 方法 |
| `hybrid` | PDB 提供结构上下文，CSV 覆盖 sequence、pocket 或任务字段 |

## Merge Key

所有评分输出必须包含 `design_id`。如果外部工具只能输出 `binder_id`，适配层必须先映射回 `design_id`，再参与 `merged_run.csv` 合并。
