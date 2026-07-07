# Batch B Pilot Execution Plan v0.17

## Purpose

v0.17 将 v0.16 的 Batch B target review queue 转化为可执行前的 pilot gate。该层仍不把任何候选写入 `target_set_v0.csv`，也不报告 performance ranking。目标是在真实 Batch B 之前固定三件事：target fixture 边界、method pilot scope、job manifest 字段。

## Inputs

- `benchmark/input_sets/batch_b_pilot_target_gate_v0.17.csv`
- `benchmark/deployment/batch_b_pilot_method_scope_v0.17.csv`
- `benchmark/input_sets/batch_b_pilot_job_manifest_v0.17.csv`
- `benchmark/protocols/adapter_replay_contract_v0.16.md`

## Execution Order

1. 先使用 v0.18 parser replay fixture 解析 v0.15 Batch A 输出，确认 `candidate_outputs.csv` 与 `run.csv` join key 可用。
2. 只允许 `fixture_ready_not_frozen` 或 `parser_fixture_only_not_frozen` 的行进入外部 fixture pilot；`review_blocked_not_frozen` 只做审计，不运行。
3. 对同一 track 的真实 head-to-head 比较，至少需要两个方法共享同一个通过审计的 target 和统一 `n_designs_requested`、seed、输入 contract。
4. 未解决 GPU、checkpoint、CLI 或 chain policy 的方法保持 `deferred`，只报告 readiness findings。

## Gate Boundary

- v0.17 不新增 GPU run。
- v0.17 不下载 PDB、数据集、模型权重或第三方源码。
- v0.17 不冻结 `target_set_v0.csv`。
- v0.17 的 job manifest 是 planned fixture manifest，不是 Benchmark result。

## Next Action

进入 v0.18 adapter replay fixture，先从已有 `/data/protein-design/data/outputs/benchmark_v0.15/batch_a` 小输出生成标准 manifest、candidate_outputs 和 run rows。之后再决定是否启动 v0.19 外部 multi-seed pilot。
