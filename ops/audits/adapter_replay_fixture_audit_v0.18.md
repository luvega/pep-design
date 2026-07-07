# Adapter Replay Fixture Audit v0.18

## Summary

v0.18 将 v0.15 Batch A minimal smoke outputs 解析为标准小型 replay fixtures。该层新增 parser evidence，但不新增方法运行，不下载数据，不产生 scoring 或 performance findings。

## Replay Outputs

| artifact | role |
|:---|:---|
| `benchmark/deployment/adapter_replay_fixture_manifest_v0.18.csv` | 记录 v0.15 外部输出、日志、runtime 和 parser 入口 |
| `benchmark/results/batch_a_replay_method_output_manifest_v0.18.csv` | 命令级 replay manifest |
| `benchmark/results/batch_a_replay_candidate_outputs_v0.18.csv` | 候选级 parser 输出 |
| `benchmark/results/batch_a_replay_run_v0.18.csv` | 可 join 的 `run.csv` 小型 fixture rows |
| `scripts/parse_batch_a_replay_fixtures.py` | 从外部 v0.15 小输出再生成上述三个 results CSV |

## Parser Findings

- PepMLM 输出 `RRIX`，因包含 `X`，parser 标记为 `partial`；这保留 CPU-only 与 noncanonical caveat。
- ProteinMPNN FASTA fixture 可解析为一个 `protein_binder` sequence row。
- RFpeptide/RFdiffusion PDB fixture 可解析为一个 cyclic peptide structure row，结构路径仍指向外部 output root。

## Boundary

v0.18 支持写作：已有 adapter replay fixture 可生成统一 `candidate_outputs.csv` 与 `run.csv` 小型 rows。不得写作：这些 rows 是真实 Benchmark results、scored results、target-set results、method ranking 或 biological validation。Short boundary: parser replay fixture is not Benchmark result.
