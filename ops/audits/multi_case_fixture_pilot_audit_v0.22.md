# Multi-case Fixture Pilot Audit v0.22

## Scope

本审计记录 v0.22 multi-case fixture pilot 计划层。它把 v0.21 method-example adapter 证据转成标准化 target/control/job manifest 和 priority gate review，但不执行新 clone、download、install、GPU run、scoring 或 target-set promotion。

## Added Artifacts

- `benchmark/deployment/method_example_fixture_evidence_v0.22.csv`
- `benchmark/input_sets/multi_case_fixture_target_manifest_v0.22.csv`
- `benchmark/input_sets/multi_case_fixture_control_manifest_v0.22.csv`
- `benchmark/input_sets/multi_case_fixture_job_manifest_v0.22.csv`
- `benchmark/deployment/priority_gate_review_v0.22.csv`
- `ops/plans/multi_case_fixture_pilot_plan_v0.22.md`

## Readiness Findings

- PepMLM、DiffPepBuilder、PepGLAD、PepMirror、RFdiffusion + ProteinMPNN 进入 focused fixture pilot 的 planned rows，但这些 rows 仍是 fixture-only 计划，不是 Benchmark result。
- D-Flow 仍由 PepMerge structure directory 和 `pep_pocket_test_structure_cache.lmdb` input contract 阻塞。
- AfCycDesign / ColabDesign cyclic peptide 仍由 non-notebook CLI adapter 阻塞。
- BindCraft 只保留 wrapper-control 审查行；v0.21 LowConfidence trajectory 不得作为 accepted final design。
- `target_set_v0.csv` 仍为空，所有 target/control rows 均保持 `not_frozen`、`review_only`、`parser_qc_only` 或 `fixture_only` 边界。

## No-Overclaim Boundary

v0.22 是 planning and readiness layer，not Benchmark result。不得写成方法已完成 head-to-head comparison、已产生 performance ranking、已实验验证、已无阻塞，或已达到 `smoke_test_ready` / `benchmark_ready`。

## Next Action

在用户明确批准执行阶段后，先处理 D-Flow PepMerge/LMDB external asset contract、ColabDesign CLI wrapper smoke import、BindCraft wrapper output classifier，再生成外部 dry-run package。任何后续结果必须记录 command、input、output、runtime、environment、parser result、failure state 和 validation artifact。
