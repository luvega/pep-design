# Wave A Adapter/Parser Completion Audit v0.33

Date: 2026-07-10

## Scope

This audit records the v0.33 bounded adapter/parser completion attempt for the
10 v0.31 placeholder-failed jobs. It covers D-Flow / PeptideDesign,
DiffPepBuilder, PepGLAD, PepMirror and RFdiffusion + ProteinMPNN, two seeds per
method.

The scope is deliberately narrower than full generation. v0.33 replaces the
v0.31 placeholder exit 86 package with method-specific adapter/parser wrappers
and compact result rows. It does not run scoring, method ranking, target-set
promotion, wet-lab synthesis or assay validation.

## Commands Recorded

- `python scripts/run_v033_wave_a_pilot.py --dry-run`
- `python scripts/run_v033_wave_a_pilot.py --execute`
- `python scripts/parse_v033_pilot_outputs.py`

Runtime outputs, command packages and logs remain in gitignored
`benchmark_runs/v0.33/`. The tracked KB stores only compact execution and parser
tables.

## Tracked Outputs

- `benchmark/deployment/pilot_execution_results_v0.33.csv`
- `benchmark/results/pilot_method_output_manifest_v0.33.csv`
- `benchmark/results/pilot_candidate_outputs_v0.33.csv`
- `benchmark/results/pilot_run_v0.33.csv`
- `benchmark/results/pilot_v033_merge_summary.json`

## Status Summary

- 10 v0.31 placeholder-failed jobs are represented in every v0.33 tracked table.
- 10 failed rows are present.
- 0 parsed/generated candidate rows are present.
- All v0.33 failed rows now use method-specific `no_supported_output_found`
  blocker reasons.
- v0.33 rows no longer use the v0.31
  `adapter_execution_failed_or_not_implemented_exit_86` placeholder reason as
  their active candidate status.

Current method-specific blockers:

- D-Flow / PeptideDesign: `dflow_adapter_attempt_no_supported_output_found`
- DiffPepBuilder: `diffpepbuilder_adapter_attempt_no_supported_output_found`
- PepGLAD: `pepglad_adapter_attempt_no_supported_output_found`
- PepMirror: `pepmirror_adapter_attempt_no_supported_output_found`
- RFdiffusion + ProteinMPNN:
  `rfdiffusion_proteinmpnn_adapter_attempt_no_supported_output_found`

## Boundary

This is bounded adapter/parser completion evidence only; it is not Benchmark result
evidence and not scoring evidence. It does not support method ranking,
`smoke_test_ready`, `benchmark_ready`, frozen target-set promotion, wet-lab
validation or any claim that an algorithm failed scientifically.

`target_set_v0.csv` remains empty. The v0.30 prospective wet-lab panel remains
planning-only.

## Next Action

The next phase should implement real generation entrypoints for these five
methods, beginning with D-Flow, then PepGLAD, PepMirror, DiffPepBuilder and
RFdiffusion + ProteinMPNN. Only after parseable candidates exist should the
project start scoring or ranking layers.
