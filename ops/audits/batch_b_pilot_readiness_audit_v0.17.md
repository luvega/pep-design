# Batch B Pilot Readiness Audit v0.17

## Summary

v0.17 完成了首批 pilot gate 梳理：3EQS、1SJH、7ZKR 和本地 PDL1 example 均只作为 fixture 或 review queue，不进入 frozen target set。RCSB metadata 支持基础链/序列核对，但仍不足以支持 assay、negative control、license policy 和 training leakage 全部闭环。

## Target Gate Findings

| target gate | current decision | reason |
|:---|:---|:---|
| `mdm2_p53_3eqs_fixture` | `fixture_ready_not_frozen` | RCSB metadata 可确认 MDM2 chain A 与 peptide chain B；negative controls 与 leakage 未闭环 |
| `mhcii_hiv_1sjh_fixture` | `review_blocked_not_frozen` | peptide chain C 可确认，但 chain D superantigen context 需要先决定是否排除 |
| `gabarap_7zkr_fixture` | `fixture_ready_not_frozen` | 可作为 RFpeptide topology fixture；noncanonical `X` 与 stapled peptide policy 未闭环 |
| `pdl1_workbench_fixture` | `parser_fixture_only_not_frozen` | 本地 PDL1 输入缺少 provenance、license、chain mapping 和 controls |

## Method Gate Findings

- PepMLM、ProteinMPNN、RFpeptide/RFdiffusion 有 v0.15 minimal smoke 输出，可进入 parser replay fixture。
- RFdiffusion + ProteinMPNN handoff 只有 component smokes，仍需单次 end-to-end handoff smoke。
- DiffPepBuilder、PepGLAD、D-Flow / PeptideDesign、AfCycDesign / ColabDesign 仍在 dependency、checkpoint 或 CLI route 队列。

## No-Overclaim Boundary

本审计支持写作：当前项目已有 Batch B pilot gate 和 adapter replay 前置条件。不得写作：Batch B target set 已冻结、方法已完成 head-to-head Benchmark、某方法性能更优、或任何方法已达到 `smoke_test_ready`。
