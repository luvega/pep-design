# PepGLAD Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/THUNLP-MT/PepGLAD
- Weights route: repository/checkpoint location to verify
- Version target: record Git commit, checkpoint filename/checksum, and environment before any run

## Environment Plan
- Python environment with geometric diffusion dependencies.
- GPU expected for inference.

## Minimal Input
- One peptide or target-conditioned design context, depending on supported examples.
- `run.csv` row with `task_id=T2_structure_peptide_binder`.

## Expected Command Shape
```powershell
python <pepglad_runner>.py --config <config.yml> --out-dir <output_dir>
```

## Expected Output Files
- Full-atom peptide structures and sequence metadata.
- Seed/config log.

## Scoring Compatibility
- Supports structure parsing if PDB/full-atom outputs are emitted.
- Target-interface metrics are only applicable if a target complex is generated.

## Pass/Fail Criteria
- Pass: one output structure and sequence can map to `design_id`.
- Fail: no public checkpoint route, no target-conditioned input path, or output lacks parseable structure.

## Blockers
- Checkpoint availability and binder-task fit require verification.
