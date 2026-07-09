# ColabDesign / DexDesign Gate Audit v0.27

## Scope

本层只处理两个未进入统一 multi-case pilot 的方法门槛：

- `AfCycDesign / ColabDesign cyclic peptide`：把 v0.26 notebook CLI adapter 从 dry-run 包推进到 bounded execute asset gate。
- `DexDesign / OSPREY3`：审查 DexDesign 专用 D-peptide/L-protein route，避免把普通 OSPREY3 example 误用为 DexDesign 证据。

## Findings

1. ColabDesign adapter 现在支持 `--execute` 门控，但该门控在缺少 AlphaFold/ColabDesign 参数目录时失败关闭，状态为 `blocked_af_params_missing`。该状态不会生成候选结构，也不会写入性能或评分结果。
2. DexDesign 审查必须以 `OSPREY3/examples/ccs.D-peptide-L-protein/` 为路线基础。`examples/1FSV` 或 `python.GMEC` 等普通 OSPREY example 只能记录为 `env_probe_only_not_dexdesign`。
3. 当前 DexDesign 仍缺最小 D-peptide/L-protein complex PDB、chain rename/preprocess 输入契约和 bounded CPU smoke 记录，因此状态保持为 `blocked_dexdesign_input_contract`。

## Evidence Files

- `benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv`
- `scripts/prepare_colabdesign_cli_adapter.py`
- `scripts/audit_dexdesign_route.py`
- Runtime outputs, if regenerated, remain under gitignored `benchmark_runs/v0.27/`.

## No-Overclaim Boundary

v0.27 是门控和路线审查层，不是 Benchmark result。它不支持 target-set freeze、scoring、method ranking、`smoke_test_ready`、`benchmark_ready` 或完整复现实验结论。

## Next Actions

1. 为 ColabDesign 提供可验证的 AF parameter route，然后在单个 fixture 上运行 bounded GPU generation。
2. 为 DexDesign 固定一个最小 D-peptide/L-protein input fixture，并记录 `Chain_Renamer.py`、`DL_preprocess.py` 和 `DL.py` 的最小 CPU smoke route。
3. 两个方法都要先产生标准 `method_output_manifest.csv`、`candidate_outputs.csv` 或 route-audit 输出，再进入 multi-case pilot。
