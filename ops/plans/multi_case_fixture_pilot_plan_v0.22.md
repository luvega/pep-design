# Multi-case Fixture Pilot Plan v0.22

## Material Passport

- Origin Skill: academic-research-suite experiment-agent
- Origin Mode: code experiment plan
- Origin Date: 2026-07-08
- Verification Status: UNVERIFIED until validator and tests pass
- Version Label: v0.22 planning layer

## Objective

v0.22 converts v0.21 method-example adapter smoke evidence into a controlled multi-case fixture pilot plan. It does not download assets, install methods, run GPU jobs, score candidates, freeze targets, or create Benchmark results.

## Planned Artifacts

- `benchmark/deployment/method_example_fixture_evidence_v0.22.csv`
- `benchmark/input_sets/multi_case_fixture_target_manifest_v0.22.csv`
- `benchmark/input_sets/multi_case_fixture_control_manifest_v0.22.csv`
- `benchmark/input_sets/multi_case_fixture_job_manifest_v0.22.csv`
- `benchmark/deployment/priority_gate_review_v0.22.csv`
- `ops/audits/multi_case_fixture_pilot_audit_v0.22.md`

## Pilot Design

The first pilot lane is focused rather than all-method execution. PepMLM, DiffPepBuilder, PepGLAD, PepMirror, and RFdiffusion + ProteinMPNN receive planned fixture rows with `n_designs_requested=1` and `random_seed=42`. D-Flow, ColabDesign, and BindCraft receive explicit gate rows rather than performance-comparison rows.

Target/control governance remains fixture-level:

- `pepmlm_sequence_contract_fixture` is a sequence adapter fixture only.
- `mdm2_p53_3eqs_fixture` is the primary structure fixture but lacks negative controls and leakage review.
- `gabarap_7zkr_fixture` is a topology and noncanonical parser/QC fixture.
- `mhcii_hiv_1sjh_fixture` is a chain-policy control until chain D handling is resolved.
- `pdl1_workbench_fixture` remains a local reserve fixture until provenance, license, chain mapping, and controls are reviewed.

## Priority Gates

- D-Flow must remain `blocked_input_contract` until external PepMerge structure data and `pep_pocket_test_structure_cache.lmdb` are present, checksum-recorded, and loadable through the method dataset path with `reset=False`.
- ColabDesign must remain `blocked_cli_adapter` until a non-notebook Python CLI adapter accepts the standard job row and emits the unified output manifests.
- BindCraft remains `wrapper_control_only` until the wrapper distinguishes `accepted_final`, `low_confidence_only`, `timeout_only`, `no_output`, and `failed`; v0.21 LowConfidence trajectory output is not accepted final design evidence.

## Execution Contract

No v0.22 row is `smoke_test_ready`, `benchmark_ready`, scored, ranked, or promoted into `target_set_v0.csv`. A later external dry-run package may use these rows only after user approval and after the validator confirms the blocked-row and fixture-only boundaries.

## Analysis Plan

The v0.22 success criterion is artifact consistency: method evidence maps to target/control/job rows, blocked methods stay blocked, wrapper controls are not overclaimed, and claim boundaries are updated. Candidate quality, method ranking, biological validation, and performance statistics are out of scope.
