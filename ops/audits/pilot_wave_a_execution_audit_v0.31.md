# Pilot Wave A Execution Audit v0.31

Date: 2026-07-09

## Scope

This audit records the bounded Wave A pilot execution and parser merge from the
v0.30 target/control/job manifests. It covers 14 Wave A jobs only. DexDesign and
BindCraft remain Wave B/control routes, and SaLT&PepPr remains blocked by
license/gated access.

Runtime outputs, raw PDB files, logs and generated structures remain in
gitignored `benchmark_runs/v0.31/`. The tracked KB stores only compact execution
and parser tables.

## Commands Recorded

- `python scripts/run_v031_wave_a_pilot.py --dry-run`
- `python scripts/run_v031_wave_a_pilot.py --execute`
- `python scripts/run_v031_wave_a_pilot.py --execute --jobs v030_colabdesign_7zkr_seed42 v030_colabdesign_7zkr_seed43`
- `python scripts/parse_v031_pilot_outputs.py`

The targeted ColabDesign rerun followed a wrapper fix that separates the outer
`command.sh` from the inner `colabdesign_inner_command.sh` Docker command
record. This prevents the bounded runner from overwriting a bash script while it
is being read.

## Tracked Outputs

- `benchmark/deployment/pilot_execution_results_v0.31.csv`
- `benchmark/results/pilot_method_output_manifest_v0.31.csv`
- `benchmark/results/pilot_candidate_outputs_v0.31.csv`
- `benchmark/results/pilot_run_v0.31.csv`
- `benchmark/results/pilot_v031_merge_summary.json`

## Status Summary

- 14 Wave A jobs are represented in every v0.31 tracked table.
- 4 parsed/generated rows are present.
- 10 failed rows are present.
- Parsed methods: PepMLM and AfCycDesign / ColabDesign cyclic peptide.
- PepMLM has two bounded sequence rows.
- ColabDesign has two bounded 7ZKR parser rows with 14-aa binder chains.
- DiffPepBuilder, PepGLAD, D-Flow / PeptideDesign, PepMirror and
  RFdiffusion + ProteinMPNN currently have `exit_86` placeholder rows in the
  v0.31 runner. This records missing method-specific Wave A adapters in this
  pilot package; it is not an algorithm-failure conclusion.

## Boundary

This is bounded pilot execution/parser evidence only; it is not Benchmark result
evidence. It does not support scoring, method ranking, target-set
promotion, wet-lab synthesis, assay validation, `smoke_test_ready`,
`benchmark_ready`, or a complete Benchmark claim.

`target_set_v0.csv remains empty`. The prospective wet-lab panel from v0.30 is
unchanged and remains planning-only.

## Next Action

The next phase should implement real Wave A adapters/parsers for the 10 failed
placeholder rows before any scoring layer is attempted. Priority order:
D-Flow, PepGLAD, PepMirror, DiffPepBuilder, and RFdiffusion + ProteinMPNN.
