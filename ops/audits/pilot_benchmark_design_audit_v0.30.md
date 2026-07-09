# Pilot Benchmark Design Audit v0.30

日期：2026-07-09

本轮把 v0.29 的 bounded/parser evidence 转换为下一轮计算优先 pilot 的受控输入层。该层只定义 targets、controls、jobs、execution matrix 和 prospective wet-lab panel，不运行 GPU，不冻结 `target_set_v0.csv`，不产生 scoring 或方法排名。

## 计算 pilot 数据基准

| 类别 | 条目 | 用途 | 边界 |
|:---|:---|:---|:---|
| sequence-only | PepMLM sequence fixture | PepMLM 双 seed 小规模生成 | schema/adapter fixture only |
| structure | `3EQS` MDM2/p53 | DiffPepBuilder、PepGLAD、D-Flow、PepMirror | positive-complex fixture; negative controls missing |
| topology/parser | `7ZKR` GABARAP/stapled peptide | RFdiffusion+ProteinMPNN、ColabDesign | cyclic/noncanonical parser stress |
| review-only | `1SJH` MHCII/HIV | chain-D policy review | not execution input |
| reserve-only | local PDL1 | provenance review reserve | not execution input |
| wave B smoke | DexDesign synthetic D-L fixture | CPU route input-contract smoke | not biological design |
| wave B wrapper | BindCraft CD47 method example | wrapper/classifier state contract | not controlled multi-case output |

`target_set_v0.csv remains empty` for this checkpoint. None of the above rows are frozen target-set evidence. They are not Benchmark result evidence.

## Execution design

- Wave A: 14 planned jobs, seven methods x two seeds where each method receives its currently supported pilot fixture.
- Wave B: 2 planned control/smoke jobs for DexDesign and BindCraft.
- Blocked lane: SaLT&PepPr remains blocked by license/gated-model access and has no executable job.
- Output root pattern for future execution: `benchmark_runs/v0.31/<method>/<job_id>/`.

Each future execution must write method-level and candidate-level parser artifacts or a failure row. Missing outputs must not be silently dropped.

## Wet-lab planning boundary

The prospective wet-lab panel records four candidate target classes: MDM2, GABARAP, NCAM1 and AMHR2. These rows are planning-only and do not indicate synthesis, binding measurement, biological activity or experimental validation.

Recommended use in the manuscript: describe the panel as a prospective validation route after computational pilot triage. Do not write that any candidate has been experimentally validated.

## Next gate

1. Implement v0.31 runners or wrappers for Wave A jobs.
2. Execute jobs in gitignored `benchmark_runs/v0.31/`.
3. Merge standard candidate rows into `pilot_candidate_outputs_v0.31.csv`.
4. Keep scoring restricted to parser/QC until target controls and negative panels are reviewed.
