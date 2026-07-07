# SaLT&PepPr Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/programmablebio/saltnpeppr
- Model route: Hugging Face/model card route recorded in method card
- Version target: record Git commit, model revision, and package versions before any run

## Environment Plan
- Python environment with protein language model dependencies.
- No structural scoring dependency is required for the first interface/sequence smoke test.

## Minimal Input
- One target protein sequence.
- Optional interface or degrader-design configuration if required.
- `run.csv` row with `input_mode=seq_only_csv` and `task_id=T1_sequence_binder`.

## Expected Command Shape
```powershell
python <saltnpeppr_runner>.py --target-sequence <sequence_or_fasta> --out-dir <output_dir>
```

## Expected Output Files
- Interface/site predictions and peptide motif or candidate sequence outputs.
- Runtime log with model revision and command.

## Scoring Compatibility
- Supports `design_feasibility` if peptide candidates are emitted.
- Structural metrics are `not_applicable` unless downstream structure prediction is added.

## Pass/Fail Criteria
- Pass: produces parseable peptide/interface candidates that can map to `design_id`.
- Fail: only interface labels are produced, no peptide candidate route is available, or task fit remains degrader-only.

## Blockers
- Generic peptide binder task fit must be confirmed before first smoke run.
