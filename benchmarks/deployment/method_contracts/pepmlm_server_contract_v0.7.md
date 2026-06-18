# PepMLM Server Contract v0.7

## Contract Status

| field | value |
|:---|:---|
| method | PepMLM |
| task_id | `T1_sequence_binder` |
| current_gate | `input_contract_ready` |
| max_allowed_gate_in_kb | `dry_run_ready` |
| execution_status | planning_only_no_run |

This contract records the expected server-side dry-run interface for PepMLM. It does not assert installation, local execution, model availability, benchmark completion, or method performance.

## Source And License

| field | value |
|:---|:---|
| repo_url | `https://github.com/programmablebio/pepmlm` |
| branch | `main` |
| commit_sha | `3169c4920f8c383948e0a5d3a7c8f87e5e7d2436` |
| source_pin_evidence | `benchmarks/method_sources/source_pin_audit_v0.5.csv` |
| repo_license_status | no license file found in v0.4 local external clone; GitHub API was rate-limited in v0.8 |
| model_route | Hugging Face model route audited in v0.8 |
| model_revision | `898fca941a9057aebdd1a6164b5ee09a1a71780e` from Hugging Face API |
| model_license_status | `mit` in Hugging Face model card API; model-card extra use-constraint fields require human decision before download/use |

## External Roots

| root | placeholder |
|:---|:---|
| source_root | `/srv/pep_design/method_sources/pepmlm` |
| data_root | `/srv/pep_design/data/pepmlm_inputs` |
| weights_root | `/srv/pep_design/weights/pepmlm` |
| results_root | `/srv/pep_design/results/pepmlm` |

All paths are future server placeholders. They are not local paths and do not indicate that files exist.

## Minimal Input Contract

| run.csv field | planned value |
|:---|:---|
| `design_id` | `pepmlm_T1_placeholder_seq_target_001` |
| `method` | `PepMLM` |
| `task_id` | `T1_sequence_binder` |
| `target_id` | `placeholder_seq_target` |
| `binder_id` | same as `design_id` before generation |
| `input_mode` | `seq_only_csv` |
| `target_sequence` | artificial placeholder sequence only |
| `peptide_type` | `linear` |
| `chirality` | `L` |
| `cyclic` | `no` |
| `status` | `not_real_benchmark` |

## Command Shape

```bash
# Placeholder only. Do not run from the KB.
python <pepmlm_entrypoint_to_verify> \
  --input_csv /srv/pep_design/data/pepmlm_inputs/example_run.csv \
  --output_dir /srv/pep_design/results/pepmlm/placeholder_run
```

The entrypoint is not yet confirmed. A future server task must inspect the repository and model card before replacing `<pepmlm_entrypoint_to_verify>`.

## Expected Outputs

- candidate peptide sequence table
- method log
- resolved model revision
- status code for each `design_id`

No output file exists in the KB.

## Failure States To Record

- `model_route_unverified`
- `repo_license_missing`
- `model_card_terms_unresolved`
- `entrypoint_unmapped`
- `batch_route_unmapped`
- `output_not_evaluable`

## Next Action

Decide the Hugging Face model-card terms, inspect the package entrypoint and write the minimal sequence-only batch wrapper before any server-side clone or model download.
