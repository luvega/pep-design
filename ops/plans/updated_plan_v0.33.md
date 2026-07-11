# Updated Plan v0.33

## Summary

v0.33 将当前项目从 v0.31 的 placeholder-failed Wave A pilot 推进到
**method-specific adapter/parser completion attempt**。本阶段只处理 v0.31
中 10 条 `adapter_execution_failed_or_not_implemented_exit_86` 行，不扩展
target set，不执行 scoring，不写方法排名。

## Current Position

当前仓库版本推进到 `1.2.21`。v0.31 已记录 14 个 Wave A jobs，其中 PepMLM
和 ColabDesign 各 2 个 seed 有 bounded parser rows，另外 5 个方法的 10 个
seed 仍是 placeholder adapter 失败。v0.33 的目标是替换这些 placeholder
失败状态，记录每个方法的 method-specific adapter/parser wrapper 尝试结果。

`target_set_v0.csv` 仍为空。v0.30 prospective wet-lab panel 仍是规划层，不是
合成、assay 或 wet-lab validation evidence。

## v0.33 Work Package

本轮新增：

- `scripts/run_v033_wave_a_pilot.py`
- `scripts/parse_v033_pilot_outputs.py`
- `benchmark/deployment/pilot_execution_results_v0.33.csv`
- `benchmark/results/pilot_method_output_manifest_v0.33.csv`
- `benchmark/results/pilot_candidate_outputs_v0.33.csv`
- `benchmark/results/pilot_run_v0.33.csv`
- `benchmark/results/pilot_v033_merge_summary.json`
- `ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md`
- `tests/test_v033_wave_a_adapter_completion.py`

v0.33 只选择以下方法的 v0.31 placeholder-failed rows：

- D-Flow / PeptideDesign
- DiffPepBuilder
- PepGLAD
- PepMirror
- RFdiffusion + ProteinMPNN

每个 job 都写入标准 runtime contract：`input_manifest.json`、`command.sh`、
`method_specific_adapter.py`、`stdout.log`、`stderr.log`、
`method_output_manifest.csv` 和 `candidate_outputs.csv`。runtime outputs 留在
gitignored `benchmark_runs/v0.33/`。

## Execution Boundary

v0.33 已执行轻量 method-specific adapter/parser wrapper，并合并 10 条 compact
rows。当前 10 条均为 `failed`，原因均为 method-specific
`*_adapter_attempt_no_supported_output_found`。这说明 placeholder exit 86 已被
替换为方法级 adapter/parser blocker，但尚未产生可解析候选。

该层不支持以下表述：

- 方法已完成正式 Benchmark。
- 方法已达到 `smoke_test_ready` 或 `benchmark_ready`。
- 任何方法优于其他方法。
- 当前失败可解释为算法科学失败。
- 当前计算证据可替代 wet-lab validation。

## Next Work Package

下一步应进入 v0.34 real-generation adapter implementation：

1. 对 D-Flow 优先接入已验证的 PepMerge/LMDB input contract，并让 wrapper 调用
   实际 bounded generation entrypoint。
2. 对 PepGLAD、PepMirror 和 DiffPepBuilder 分别审查 source tree 中的最小
   inference/example command，把输出路径固定到 `benchmark_runs/v0.34/`。
3. 对 RFdiffusion + ProteinMPNN 固化 RFdiffusion backbone 输出到 ProteinMPNN
   sequence design 的 handoff contract。
4. 每个方法先跑 1 个 seed，只有产生标准 `candidate_outputs.csv` 后再补第二个
   seed。
5. 在至少两个结构方法产生可解析候选之前，不启动 scoring layer。

## Claim Gate

v0.33 只能写为 bounded adapter/parser completion attempt。它不是 scoring
evidence，不是 method-ranking evidence，不是 frozen target-set evidence，不是
wet-lab validation evidence，也不是完整 Benchmark result。

所有大文件、模型权重、第三方源码、日志和生成结构继续留在外部或 gitignored
runtime roots。
