# AfCycDesign / ColabDesign Cyclic Peptide Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/sokrypton/ColabDesign
- Weights route: AlphaFold-family weights or ColabDesign runtime setup
- Version target: record Git commit/notebook revision, AF model source, and environment before any run

## Environment Plan
- ColabDesign/AlphaFold-compatible Python environment.
- GPU expected.
- Notebook route must be converted into a reproducible command or documented notebook execution contract.

## Minimal Input
- One cyclic peptide design setting or target/binder context.
- `run.csv` row with `task_id=T2_structure_peptide_binder` and `cyclic=yes`.

## Expected Command Shape
```powershell
python <colabdesign_runner>.py --config <config.yml> --out-dir <output_dir>
```

## Expected Output Files
- Cyclic peptide sequence and predicted structure.
- AF/ColabDesign confidence outputs if available.

## Scoring Compatibility
- Supports structural confidence and design feasibility if PDB outputs are exported.
- Interface metrics apply only when target complex output is available.

## Pass/Fail Criteria
- Pass: one cyclic peptide sequence/structure can map to `design_id`.
- Fail: no batch route, AF weights unavailable, or cyclic constraint encoding is not logged.

## Blockers
- Notebook-to-batch conversion and AF dependency setup are the main blockers.
