# BindCraft Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/martinpacesa/BindCraft
- Weights route: AF2/MPNN/PyRosetta dependency setup
- Version target: record Git commit, config, dependency versions, and environment before any run

## Environment Plan
- Integrated BindCraft environment.
- GPU expected for AF2-related steps.
- PyRosetta dependency may require license and local installation.

## Minimal Input
- One target PDB.
- Binder design settings and optional hotspot/pocket constraints.
- `run.csv` row with `task_id=T3_miniprotein_binder_baseline`.

## Expected Command Shape
```powershell
python <bindcraft_runner>.py --settings <settings.json> --target <target.pdb> --out-dir <output_dir>
```

## Expected Output Files
- Binder sequences and predicted structures.
- Pipeline filter/score CSV if emitted.

## Scoring Compatibility
- Supports structural confidence, interface geometry, Rosetta-derived metrics if available, and design feasibility.

## Pass/Fail Criteria
- Pass: one binder design with sequence, structure, and filter record maps to `design_id`.
- Fail: dependency stack cannot be resolved, PyRosetta unavailable, or output cannot be parsed.

## Blockers
- Heavy integrated dependency stack and less direct short-peptide fit; run after RFdiffusion baseline is mapped.
