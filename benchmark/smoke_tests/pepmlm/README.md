# PepMLM Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/programmablebio/pepmlm
- Model route: Hugging Face PepMLM model card route recorded in method card
- Version target: record Git commit, model revision, and package versions before any run

## Environment Plan
- Python environment with PyTorch and Hugging Face dependencies.
- No structure-prediction dependency is required for the first sequence-only smoke test.

## Minimal Input
- One target protein sequence.
- Optional peptide length or design constraint if supported by the runner.
- `run.csv` row with `input_mode=seq_only_csv` and `task_id=T1_sequence_binder`.

## Expected Command Shape
```powershell
python <pepmlm_runner>.py --target-sequence <sequence_or_fasta> --num-designs 5 --out-dir <output_dir>
```

## Expected Output Files
- Peptide sequence candidates in CSV, FASTA, or JSON.
- Runtime log with model revision and command.

## Scoring Compatibility
- Directly supports `design_feasibility` metrics.
- Structural metrics are `not_applicable` unless downstream structure prediction is added.

## Pass/Fail Criteria
- Pass: produces at least one parseable peptide sequence with target/design IDs.
- Fail: model route unavailable, command cannot batch inputs, or output cannot map to `design_id`.

## Blockers
- Exact CLI/API route and model license still need verification.
