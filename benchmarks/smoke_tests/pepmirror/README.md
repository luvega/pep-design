# PepMirror Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/YZY010418/PepMirror
- Weights route: https://zenodo.org/records/20095187
- Version target: record Git commit, Zenodo checkpoint filename/checksum, and environment before any run

## Environment Plan
- Python environment following repository instructions.
- Expected dependencies include structure generation and post-processing/ranking tools such as PyRosetta, Vina, or OpenMM if required by the selected route.
- GPU expected for generation; CPU scoring dependencies may also be required.

## Minimal Input
- One small target PDB.
- Receptor/ligand chain definition or pocket center.
- `run.csv` row with `input_mode=pdb_only` or `hybrid`, `task_id=T2_structure_peptide_binder`, and `chirality=D`.

## Expected Command Shape
```powershell
python <pepmirror_generation_runner>.py --config <config.yml> --checkpoint <ckpt> --out-dir <output_dir>
python <pepmirror_ranking_runner>.py --input-dir <output_dir> --out-csv <metrics.csv>
```

## Expected Output Files
- D-peptide binder complex PDBs.
- Ranking or filtering CSV.
- Generation config and seed log.

## Scoring Compatibility
- Supports `structure_confidence`, `interface_geometry`, `structure_similarity` when a reference exists, and `design_feasibility`.

## Pass/Fail Criteria
- Pass: one D-peptide complex PDB and ranking record can map to `design_id`.
- Fail: checkpoint unavailable, dependency stack cannot be resolved, or output lacks chain/chirality metadata.

## Blockers
- Local installation and scoring dependency availability remain untested.
