# Adapter Parser Hardening Plan v0.16

## Summary

v0.16 将 v0.15 的外部 import preflight 与 Batch A minimal smoke-test 记录转化为下一轮可重复执行所需的 adapter、parser、manifest 和 target/control review queue。该层仍是 KB 控制面更新，不新增 clone、download、install、Docker build、model fetch 或 GPU run。

核心目标是让后续 Batch B 在执行前具备三类可审查接口：

1. `job_manifest.csv` 到 method-specific input 的转换边界。
2. raw method output 到 `candidate_outputs.csv` 和 `run.csv` 的 parser 边界。
3. target/control/leakage/license 审查队列，避免把 literature cases 直接写入 frozen target set。

## Adapter And Parser Priority

| method | v0.15 evidence | v0.16 decision | next gate |
|:---|:---|:---|:---|
| PepMLM | CPU-only minimal smoke test | 固化 sequence-only batch wrapper 和 generated peptide parser | adapter_contract_ready |
| ProteinMPNN | PDL1 FASTA smoke output | 固化 FASTA parser 和 fixed-chain handoff metadata | parser_contract_ready |
| RFpeptide/RFdiffusion | bundled cyclic example smoke output | 固化 PDB/TRB/trajectory manifest parser 和 receptor/contig contract | parser_contract_ready |
| RFdiffusion + ProteinMPNN handoff | v0.11 contract only | 明确 RFdiffusion output 到 ProteinMPNN input 的 handoff 字段 | handoff_contract_ready |
| DiffPepBuilder | import-level preflight only | 保留 GPU PyTorch/checkpoint/input caveat | preflight_caveat_queue |
| PepGLAD | import-level preflight with torch_scatter caveat | 修复 PyTorch extension 路线前不进入 smoke test | dependency_repair_queue |
| D-Flow / PeptideDesign | CUDA import-level preflight | 补 checkpoint manifest 和 input adapter 后再 smoke test | checkpoint_manifest_queue |
| AfCycDesign / ColabDesign cyclic peptide | import-level preflight only | 先定义 non-notebook CLI route | cli_route_queue |

## Target Review Queue

Batch B 候选只进入 review queue，不进入 `target_set_v0.csv`。优先审查：

- MDM2/p53 `3EQS`
- MHCII/HIV peptide `1SJH`
- PDL1 workbench example
- RFdiffusion pMHC panel
- PepBench/LNR panel
- PepMerge panel

每个候选必须补齐 structure chain、known binder、assay readout、license、leakage、positive/negative control 和 next action 后，才可讨论 target-set promotion。

## Output Artifacts

- `benchmark/deployment/adapter_parser_hardening_matrix_v0.16.csv`
- `benchmark/input_sets/batch_b_target_review_queue_v0.16.csv`
- `benchmark/protocols/adapter_replay_contract_v0.16.md`
- `manuscript/support/benchmark_manuscript_claim_evidence_map.csv` 的 v0.15/v0.16 claim boundary rows

## Boundaries

- v0.16 不新增任何运行证据。
- v0.16 不把任何方法提升为 `smoke_test_ready` 或 `benchmark_ready`。
- v0.16 不冻结 `target_set_v0.csv`。
- v0.16 不报告 scoring、ranking、developability、wet-lab 或 performance findings。
- 原始 logs、model cache、PDB、TRB、trajectory、weights、第三方源码和大型输出继续保留在 `/data/protein-design` 或后续外部 root。

## Verification

更新后必须运行：

```bash
PYTHONUTF8=1 python scripts/validate_benchmark_kb.py
git diff --check
git status -sb
```

