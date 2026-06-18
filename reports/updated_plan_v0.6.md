# Updated Plan v0.6: ARS Review, Dataset Watchlist, Server Dry-Run Contracts

## Summary

v0.6 将当前计划从 “link/data availability + source pinning” 更新为 **“ARS 综合评审 + 数据集补充 watchlist + 服务器 dry-run 合同 + manuscript claim gate”**。本阶段仍不下载数据、不 clone 第三方源码、不安装环境、不下载权重、不运行 GPU。目标是在服务器端部署前，把研究问题、证据边界、候选数据、方法输入输出合同和失败状态全部变成可验证文件。

## Key Changes

- 将 `academic-research-suite` 用作跨阶段审查框架：研究问题、文献/数据证据、manuscript positioning、peer review、experiment planning 和 integrity gate 同步审查。
- 新增 `tables/ars_review_action_items_v0.6.csv`，把 ARS 评审意见变成可裁决 action items。
- 新增 `benchmarks/input_sets/dataset_supplement_watchlist_v0.6.csv`，记录 PepBenchmark、GPCR peptide benchmark、TCRTransBench 等新增或强化来源，但不进入 frozen target set。
- 新增 `benchmarks/deployment/server_smoke_test_contract_v0.6.md`，规定后续服务器端 clone/download/install/smoke test 的 gating 顺序。
- 更新 manuscript outline 和 claim-evidence map，明确 v0.5/v0.6 是 readiness evidence，不是 performance evidence。

## Revised Execution Gates

| gate | required evidence | allowed next step |
|:---|:---|:---|
| `metadata_ready` | DOI/URL/API/HEAD/local card; license route known or pending | add to watchlist or data access manifest |
| `source_pinned` | repo URL, branch, commit SHA, license hint, README/env route | prepare external clone manifest |
| `license_checked` | repo, model, checkpoint, dataset and tool licenses recorded | prepare server download/clone command |
| `weights_manifested` | URL, version, file list, expected size, checksum plan | request server-side download approval |
| `input_contract_ready` | `run.csv` fields, input mode, chain convention, minimal test case | prepare no-weight dry-run contract |
| `dry_run_ready` | environment solve plan, command shape, expected output paths, no real model run | schedule server dry-run |
| `smoke_test_ready` | installed environment, downloaded approved weights/data, real command log | run minimal smoke test |

## Updated Dataset Policy

- Overath remains `calibration_ready_metadata_only` for T3 ranking/rescoring and scoring calibration; it is not peptide-generation performance evidence.
- PEPBI remains `pending_download_route_and_schema`; Dryad metadata is useful, but download route and schema still need confirmation.
- PepBenchmark should be tracked as `developability_property_watchlist` until binder-generation relevance and subset schemas are mapped.
- GPCR peptide benchmark should be tracked as `gpcr_t2_t3_watchlist`; its abstract strongly matches peptide design benchmarking, but external data files are not yet located.
- TCRTransBench should be tracked as `immunological_sequence_watchlist`; it is relevant to pMHC/TCR-like sequence generation but not a generic protein-target peptide binder benchmark.

## Updated Method Policy

- All 10 include methods remain `pinned_no_install`.
- PepMLM and RFdiffusion + ProteinMPNN remain first candidates for server dry-run contracts, but not for immediate GPU benchmark.
- PepMirror remains high scientific priority but high engineering dependency because PyRosetta, Vina, OpenMM and checkpoint routes must be confirmed.
- BindCraft and ColabDesign remain deferred until AF2/ProteinMPNN/PyRosetta or AlphaFold-family assets are explicitly available on the server.

## Deliverables For Next Implementation

1. Close or update ARS action items by artifact.
2. Create per-method `server_contract.md` only for methods whose source/license/weights route can be described without installation.
3. Add `example_run.csv` with 1-2 artificial metadata-only rows, not real benchmark results.
4. Build a `download_manifest_template.csv` for future server use; keep it empty or placeholder-only in the KB.
5. Refresh `reports/benchmark_manuscript_outline.md` Results and Discussion sections to include v0.5/v0.6 readiness.

## Out Of Scope

- No source clone into this repository.
- No dataset or checkpoint download.
- No conda environment creation.
- No scoring script implementation.
- No local reproducibility claims.
- No method ranking or performance comparison.
