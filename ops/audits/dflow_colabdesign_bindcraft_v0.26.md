# D-Flow, ColabDesign and BindCraft Gate Update v0.26

## Scope

This audit records three gate updates requested before controlled multi-case
execution:

- a bounded D-Flow / PeptideDesign dry-run;
- a standard job-row ColabDesign CLI adapter package;
- a BindCraft accepted-final output classifier.

The evidence is readiness and interface evidence only. It is not target-set
evidence, scoring evidence, method ranking, `smoke_test_ready`, or a complete
Benchmark result.

## D-Flow Bounded Dry-run

The D-Flow input contract from v0.25 was reduced to one official PepMerge test
entry, `1aze_B`, by copying that LMDB record into
`benchmark_runs/v0.26/dflow_bounded_lmdb/pep_pocket_test_structure_cache.lmdb`.

Command:
`benchmark_runs/v0.26/dflow_bounded_dry_run/command.sh`

Runtime evidence:

| field | value |
|:---|:---|
| exit code | `0` |
| elapsed time | `147.67` seconds |
| max RSS | `5680252` KB |
| checkpoint | `weights/dflow/dflow.pt` |
| input entry | `1aze_B` |
| output root | `benchmark_runs/v0.26/dflow_bounded_dry_run/pep_output/dflow.pt_1_1_False` |
| sample PDB | `benchmark_runs/v0.26/dflow_bounded_dry_run/pep_output/dflow.pt_1_1_False/1aze_B/sample_0.pdb` |
| outputs CSV | `benchmark_runs/v0.26/dflow_bounded_dry_run/pep_output/dflow.pt_1_1_False/outputs.csv` |

The command used `num_steps=1` and `num_samples=1`. D-Flow initialized ESM2
assets into the local Torch cache during the run. The sample PDB was parsed as
chain B sequence `MRRRRRRRRY`; this row is recorded in
`benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv`.

Note: D-Flow constructs its save path from `sample.ckpt_path`; because the
checkpoint was provided as an absolute path, the first output directory was
created under `weights/dflow/dflow.pt_1_1_False`. The generated folder was moved
into the v0.26 runtime root and the path behavior is recorded as an adapter
cleanup item.

## ColabDesign CLI Adapter

`scripts/prepare_colabdesign_cli_adapter.py` now accepts a standard job row and
writes:

- `colabdesign_adapter_config.json`;
- `command.sh`;
- `method_output_manifest.csv`;
- `candidate_outputs.csv`.

The v0.22 ColabDesign job row
`v022_pilot_colabdesign_7zkr_seed42` was packaged under
`benchmark_runs/v0.26/colabdesign_cli_adapter`. This is a CLI contract and
manifest dry-run only; v0.26 does not execute ColabDesign, run notebook code, or
claim a generated cyclic peptide.

## BindCraft Wrapper Classifier

`scripts/classify_bindcraft_outputs.py` classifies BindCraft output roots into:

- `accepted_final`;
- `low_confidence_only`;
- `timeout_only`;
- `no_output`;
- `failed`.

The existing v0.21 BindCraft output root was classified as
`low_confidence_only`: it contains one `Trajectory/LowConfidence` PDB and zero
accepted PDBs. The compact classification row is recorded in
`benchmark/results/bindcraft_wrapper_classification_v0.26.csv`.

## Boundary

These v0.26 records resolve three local gates at readiness level:

- D-Flow can complete a bounded single-entry generation command;
- ColabDesign now has a standard job-row CLI adapter package;
- BindCraft can reject LowConfidence trajectories as not accepted final.

They do not promote `target_set_v0.csv`, do not score candidates, do not rank
methods, and do not complete a head-to-head Benchmark run.
