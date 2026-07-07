# Results

当前阶段不保存真实 Benchmark 结果。

后续真实运行时，本目录只允许保存小型示例、索引或汇总表。大规模 PDB、模型输出、MSA、权重和中间结果应进入外部结果目录，并在本项目中记录路径、版本和校验信息。

v0.11 新增的 `example_method_output_manifest_v0.11.csv` 和 `example_candidate_outputs_v0.11.csv` 只用于 schema/adapter 说明，所有行均为 `not_real_benchmark` 或未运行占位记录，不是方法输出或性能证据。

v0.18 新增的 `batch_a_replay_method_output_manifest_v0.18.csv`、`batch_a_replay_candidate_outputs_v0.18.csv` 和 `batch_a_replay_run_v0.18.csv` 是从外部 v0.15 Batch A minimal smoke outputs 解析得到的小型 replay fixtures。它们用于检查 adapter/parser 字段和 `design_id` join，不是新的方法执行、scoring evidence、head-to-head result 或 Benchmark performance finding。
