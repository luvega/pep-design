# RFdiffusion + ProteinMPNN Server Contract v0.7

## Contract Status

| field | value |
|:---|:---|
| method | RFdiffusion + ProteinMPNN |
| task_id | `T3_miniprotein_binder_baseline` |
| current_gate | `input_contract_ready` |
| max_allowed_gate_in_kb | `dry_run_ready` |
| execution_status | planning_only_no_run |

This contract records the expected server-side dry-run interface for the RFdiffusion + ProteinMPNN baseline. It does not assert installation, local execution, checkpoint availability, benchmark completion, or method performance.

## Source And License

| component | repo_url | branch | commit_sha | license status |
|:---|:---|:---|:---|:---|
| RFdiffusion | `https://github.com/RosettaCommons/RFdiffusion` | `main` | `2d0c003df46b9db41d119321f15403dec3716cd9` | BSD license in local external clone; license text states code and README-referenced model weights are covered |
| ProteinMPNN | `https://github.com/dauparas/ProteinMPNN` | `main` | `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | MIT license in local external clone |

RFdiffusion README checkpoint URLs are recorded in `benchmarks/deployment/download_manifest_v0.8.csv` for future server use, but selected checkpoint sizes/checksums remain unresolved. ProteinMPNN model-weight folders are present in the pinned external clone and are tied to the commit SHA; file checksums are not yet recorded in the KB.

## Environment Notes From v0.8 Audit

| component | environment evidence | implication |
|:---|:---|:---|
| RFdiffusion | `env/SE3nv.yml` uses Python 3.9, PyTorch 1.9, `cudatoolkit=11.1`, `dgl-cuda11.1` | server should not assume modern PyTorch/CUDA without solving compatibility |
| ProteinMPNN | README example uses PyTorch with `cudatoolkit=11.3`; README maps `protein_mpnn_run.py`, `--pdb_path`, `--out_folder`, and model-weight folders | handoff can be specified, but has not been run |

## External Roots

| root | placeholder |
|:---|:---|
| source_root | `/srv/pep_design/method_sources/rfdiffusion_proteinmpnn` |
| data_root | `/srv/pep_design/data/rfdiffusion_inputs` |
| weights_root | `/srv/pep_design/weights/rfdiffusion_proteinmpnn` |
| results_root | `/srv/pep_design/results/rfdiffusion_proteinmpnn` |

All paths are future server placeholders. They are not local paths and do not indicate that files exist.

## Minimal Input Contract

| run.csv field | planned value |
|:---|:---|
| `design_id` | `rfdiffusion_mpn_T3_placeholder_pdb_001` |
| `method` | `RFdiffusion + ProteinMPNN` |
| `task_id` | `T3_miniprotein_binder_baseline` |
| `target_id` | `placeholder_pdb_target` |
| `binder_id` | same as `design_id` before generation |
| `input_mode` | `pdb_only` |
| `target_pdb` | `/srv/pep_design/data/rfdiffusion_inputs/placeholder_target.pdb` |
| `target_chains` | `B` |
| `binder_chain` | `A` |
| `peptide_type` | `miniprotein` |
| `chirality` | `L` |
| `cyclic` | `no` |
| `status` | `not_real_benchmark` |

## Command Shape

```bash
# Placeholder only. Do not run from the KB.
python <rfdiffusion_repo>/scripts/run_inference.py \
  inference.input_pdb=/srv/pep_design/data/rfdiffusion_inputs/placeholder_target.pdb \
  inference.output_prefix=/srv/pep_design/results/rfdiffusion_proteinmpnn/placeholder_run/design

python <proteinmpnn_repo>/protein_mpnn_run.py \
  --pdb_path /srv/pep_design/results/rfdiffusion_proteinmpnn/placeholder_run/design.pdb \
  --out_folder /srv/pep_design/results/rfdiffusion_proteinmpnn/placeholder_run/mpnn
```

The command shape records the planned two-stage handoff only. Checkpoints, contig syntax, hotspot syntax and actual target PDB are not defined in this KB.

## Expected Outputs

- RFdiffusion backbone PDB candidates
- ProteinMPNN sequence design files
- command log and status code
- mapping from generated file names back to `design_id`

No output file exists in the KB.

## Failure States To Record

- `checkpoint_route_unverified`
- `checkpoint_size_or_checksum_missing`
- `cuda_stack_unresolved`
- `contig_or_hotspot_contract_missing`
- `pdb_input_missing`
- `rfdiffusion_to_mpn_handoff_unvalidated`
- `output_not_evaluable`

## Next Action

HEAD selected RFdiffusion checkpoint URLs, define one minimal contig/hotspot syntax, and map RFdiffusion output filenames to ProteinMPNN `--pdb_path` / chain-design settings before server-side dry-run.
