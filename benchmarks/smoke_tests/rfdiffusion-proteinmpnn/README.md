# RFdiffusion + ProteinMPNN Smoke-Test Plan

## Method Source And Version To Verify
- Repositories: https://github.com/RosettaCommons/RFdiffusion and https://github.com/dauparas/ProteinMPNN
- Weights route: public model releases to verify and pin
- Version target: record both Git commits, checkpoint files, and environment before any run

## Environment Plan
- RFdiffusion environment for backbone generation.
- ProteinMPNN environment for sequence assignment.
- GPU expected for RFdiffusion and downstream structure prediction.

## Minimal Input
- One target PDB.
- Hotspot or motif/length constraints.
- `run.csv` row with `input_mode=pdb_only` or `hybrid` and `task_id=T3_miniprotein_binder_baseline`.

## Expected Command Shape
```powershell
python <rfdiffusion_runner>.py inference.input_pdb=<target.pdb> inference.output_prefix=<out_prefix>
python <proteinmpnn_runner>.py --pdb_path <generated_backbone.pdb> --out_folder <output_dir>
```

## Expected Output Files
- Binder backbone PDB.
- ProteinMPNN-designed sequences.
- Generation and sequence-design logs.

## Scoring Compatibility
- Supports structural confidence, interface geometry, optional DockQ/RMSD, and design feasibility.

## Pass/Fail Criteria
- Pass: one backbone and sequence can map to `design_id`.
- Fail: checkpoint unavailable, target/hotspot input cannot be standardized, or sequence assignment cannot run in batch.

## Blockers
- Version pinning, checkpoint location, and AF2/structure-prediction filter route need mapping.
