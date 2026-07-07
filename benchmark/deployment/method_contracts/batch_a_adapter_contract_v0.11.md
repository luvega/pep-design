# Batch A Adapter Contract v0.11

## Contract Status

| field | value |
|:---|:---|
| methods | PepMLM; RFdiffusion + ProteinMPNN |
| current_gate | `input_contract_ready` |
| max_allowed_gate_in_kb | `dry_run_ready` |
| execution_status | planning_only_no_run |

This contract defines the adapter layer between `job_manifest.csv`, method-specific commands and unified output manifests. It does not assert clone, download, installation, execution, local reproducibility, or method performance.

## Shared Adapter Rules

- Input begins from `benchmark/input_sets/example_job_manifest_v0.11.csv` or later approved external `job_manifest.csv`.
- Candidate-level rows must map to `design_id` and then to `run.csv`.
- Raw method outputs, PDB files, logs, model snapshots and checkpoints remain under `/srv/pep_design` external roots.
- KB examples must keep `status=not_real_benchmark` or `parser_status=not_real_benchmark`.
- A method cannot be promoted to `smoke_test_ready` without server logs, command, environment, input, output, runtime, parser result and failure-state artifacts.

## PepMLM Adapter

| item | planned value |
|:---|:---|
| task | `T1_sequence_binder` |
| input mode | `seq_only_csv` |
| job source | `example_job_manifest_v0.11.csv` row `pepmlm_T1_placeholder_seq_job_001` |
| adapter input | target sequence, optional peptide length and number of designs if runner supports it |
| output parser | sequence table, FASTA or JSON to `candidate_outputs.csv` |
| output limitation | structural metrics remain `not_applicable` unless a downstream structure-prediction layer is added |

Required before server dry-run:

- Confirm repository entrypoint or importable API.
- Confirm Hugging Face model-card terms and selected revision.
- Write a small external wrapper that accepts `job_manifest.csv` and writes method-specific input under `${PEP_DATA}`.

## RFdiffusion + ProteinMPNN Adapter

| item | planned value |
|:---|:---|
| task | `T3_miniprotein_binder_baseline` |
| input mode | `pdb_only` or later `hybrid` |
| job source | `example_job_manifest_v0.11.csv` row `rfdiffusion_mpn_T3_placeholder_pdb_job_001` |
| adapter input | target PDB, target chain, binder chain, contig/hotspot policy |
| first-stage output | RFdiffusion backbone PDB candidates |
| second-stage output | ProteinMPNN sequence files |
| output parser | generated backbone path plus sequence assignment to `candidate_outputs.csv` |

Required before server dry-run:

- Select RFdiffusion checkpoint route and record HEAD/size/checksum policy.
- Define one minimal contig/hotspot syntax for the artificial dry-run contract.
- Define ProteinMPNN fixed-chain and designed-chain handoff policy.
- Map RFdiffusion filenames to ProteinMPNN `--pdb_path` and output parser fields.

## PepMirror Boundary

PepMirror remains outside Batch A adapter execution. No real `job_manifest.csv` row should be created until PyRosetta license/install route, Vina/OpenMM runtime, Zenodo checkpoint choice and stereochemistry-aware parser boundaries are resolved.
