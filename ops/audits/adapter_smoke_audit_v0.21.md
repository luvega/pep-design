# Adapter Smoke Audit v0.21

## Scope

本审计记录 v0.21 adapter smoke 与 parser 输出层。外部执行、原始日志、Docker layers、第三方源码、权重、checkpoint、PDB/SDF/FASTA 和大输出仍保留在 `/data/protein-design` 与 `/mnt/ssd4t/protein-design`，KB 仅保存小型 CSV 摘要和外部路径指针。

## Added Artifacts

- `benchmark/deployment/adapter_smoke_manifest_v0.21.csv`
- `benchmark/deployment/adapter_smoke_results_v0.21.csv`
- `benchmark/deployment/blocker_asset_manifest_v0.21.csv`
- `benchmark/results/adapter_method_output_manifest_v0.21.csv`
- `benchmark/results/adapter_candidate_outputs_v0.21.csv`
- `benchmark/results/adapter_run_rows_v0.21.csv`
- `scripts/collect_v021_adapter_smokes.py`
- `scripts/parse_v021_adapter_outputs.py`

## Readiness Findings

- PepMLM, DiffPepBuilder, PepGLAD, PepMirror, and RFdiffusion + ProteinMPNN recorded bounded GPU adapter-smoke evidence on method-provided or synthetic examples.
- BindCraft recorded a bounded hard-stop control with GPU evidence and parser-readable low-confidence trajectory output.
- RFdiffusion + ProteinMPNN now records a handoff manifest linking RFdiffusion PDB output to ProteinMPNN FASTA output.
- PepGLAD public checkpoint assets and PepMirror Zenodo checkpoint were downloaded only to the external workbench and referenced through the asset manifest.
- `pd-pyrosetta-methods-gpu:0.21` was built externally with PyRosetta from the RosettaCommons quarterly mirror and used for PepMirror.
- D-Flow remains blocked by the missing PepMerge cache/input contract even though `dflow.pt` is present externally.
- SaLT&PepPr remains blocked by license/gated-model access.
- AfCycDesign / ColabDesign cyclic peptide remains blocked by the non-notebook CLI adapter decision.
- DexDesign / OSPREY3 is carried forward from earlier CPU route evidence without a new v0.21 design run.

## Parser Boundary

The parser writes compact fixture rows only. Method-specific binder-chain rules are used for PDB outputs, including BindCraft chain B, DiffPepBuilder chain A under `runs/inference`, PepGLAD chain B, and PepMirror chain H. These rows are not Benchmark result, not target-set evidence, not scoring evidence, and not method-ranking evidence.

## Next Action

Use v0.21 rows to plan a controlled multi-case fixture pilot. Before any head-to-head claim, add frozen target/control governance, standardized job manifests, multi-seed runs, scoring artifacts, parser QA, and explicit failure handling.
