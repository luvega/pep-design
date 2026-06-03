# Smoke Tests

本目录记录每个 `decision=include` 方法的最小运行计划。当前阶段只写计划，不 clone、不 install、不下载权重、不运行 GPU。

## Required README Sections

每个方法目录的 `README.md` 必须包含：

- method source and version to verify
- environment plan
- minimal input
- expected command shape
- expected output files
- scoring compatibility
- pass/fail criteria
- blockers

## Included Methods

| method | slug | tier |
|:---|:---|:---|
| PepMLM | `pepmlm` | Tier 1 |
| PepMirror | `pepmirror` | Tier 1 |
| RFdiffusion + ProteinMPNN | `rfdiffusion-proteinmpnn` | Tier 1 |
| DiffPepBuilder | `diffpepbuilder` | Tier 2 |
| PepGLAD | `pepglad` | Tier 2 |
| D-Flow / PeptideDesign | `d-flow-peptidedesign` | Tier 2 |
| AfCycDesign / ColabDesign cyclic peptide | `afcycdesign-colabdesign` | Tier 2 |
| BindCraft | `bindcraft` | Tier 2 |
| SaLT&PepPr | `salt-peppr` | Tier 3 |
| DexDesign / OSPREY3 | `dexdesign-osprey3` | Tier 3 |
