# DexDesign / OSPREY3 Smoke-Test Plan

## Method Source And Version To Verify
- Repository: https://github.com/donaldlab/OSPREY3
- Weights route: not required
- Version target: record OSPREY3 version, Java/runtime details, and DexDesign workflow mapping before any run

## Environment Plan
- OSPREY3-compatible Java/runtime environment.
- CPU/search workload expected.

## Minimal Input
- One target structure.
- D-peptide design site and search configuration.
- `run.csv` row with `task_id=T2_structure_peptide_binder` and `chirality=D`.

## Expected Command Shape
```powershell
<osprey_command_or_script> --config <dexdesign_config> --out-dir <output_dir>
```

## Expected Output Files
- D-peptide sequence/conformation candidates.
- Energy/search report.

## Scoring Compatibility
- Supports design feasibility after parser mapping.
- Structural/interface metrics require exported conformations or PDB models.

## Pass/Fail Criteria
- Pass: one candidate can map to `design_id` with sequence/conformation and score.
- Fail: DexDesign workflow cannot be located, OSPREY setup cannot be scripted, or output parser is unclear.

## Blockers
- Workflow setup burden is high; this remains Tier 3 until a minimal case is mapped.
