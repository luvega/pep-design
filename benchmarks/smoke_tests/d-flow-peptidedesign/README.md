# D-Flow / PeptideDesign Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/smiles724/PeptideDesign
- Weights route: repository archive/checkpoint route to verify
- Version target: record Git commit, archive/checkpoint checksum, and environment before any run

## Environment Plan
- Python environment with D-peptide/full-atom generation dependencies.
- GPU expected for inference.

## Minimal Input
- One receptor or receptor-peptide context.
- Chirality/mirror configuration recorded in `run.csv`.
- `run.csv` row with `input_mode=pdb_only` or `hybrid` and `task_id=T2_structure_peptide_binder`.

## Expected Command Shape
```powershell
python <peptidedesign_runner>.py --config <config.yml> --checkpoint <ckpt> --out-dir <output_dir>
```

## Expected Output Files
- D-peptide structure/sequence output.
- Mirror/chirality setting log.

## Scoring Compatibility
- Supports structural metrics if complex PDB output is produced.
- Chirality-specific checks must be logged under `design_feasibility`.

## Pass/Fail Criteria
- Pass: output records sequence, structure, chirality mode, and `design_id`.
- Fail: checkpoint provenance unclear, mirror conversion not reproducible, or output cannot be parsed.

## Blockers
- Archive provenance and stereochemistry handling need explicit mapping.
