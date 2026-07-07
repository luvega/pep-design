# DiffPepBuilder Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/YuzheWangPKU/DiffPepBuilder
- Weights route: Zenodo route recorded in method card
- Version target: record Git commit, checkpoint filename/checksum, and environment before any run

## Environment Plan
- Python environment with diffusion-model dependencies.
- GPU expected for inference.

## Minimal Input
- One target PDB with receptor chain and binding context.
- Pocket or reference binder definition if required.
- `run.csv` row with `input_mode=pdb_only` or `hybrid` and `task_id=T2_structure_peptide_binder`.

## Expected Command Shape
```powershell
python <diffpepbuilder_runner>.py --target-pdb <target.pdb> --checkpoint <ckpt> --out-dir <output_dir>
```

## Expected Output Files
- Generated peptide binder PDB or equivalent structure output.
- Candidate metadata with design ID and seed.

## Scoring Compatibility
- Should support `structure_confidence`, `interface_geometry`, `structure_similarity`, and `design_feasibility` if PDB outputs are available.

## Pass/Fail Criteria
- Pass: one generated structure can be parsed and linked to `design_id`.
- Fail: checkpoint route missing, minimal input schema unclear, or no parseable structure output.

## Blockers
- Exact checkpoint files and minimal example command need verification.
