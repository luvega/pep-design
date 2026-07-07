# Smoke Tests

本目录记录每个 `decision=include` 方法的最小运行计划。当前阶段只写计划，不 clone、不 install、不下载权重、不运行 GPU。

v0.11 将初步测试拆为 `job_manifest.csv`、method adapter、`method_output_manifest.csv`、`candidate_outputs.csv` 和既有 metric CSV。Batch A 仅规划 PepMLM 与 RFdiffusion + ProteinMPNN；PepMirror 在 PyRosetta/Vina/OpenMM 和 stereochemistry-aware parser 未解决前保持 dependency-blocked。

v0.13 将 Docker 层烟测入口分为已有镜像复用和共享补充镜像预检。`pd-benchmark-methods-gpu:0.13` 只计划 import-level environment checks；这些检查即使后续通过，也仍需另行记录 source commit、command、input、output、runtime、logs、parser result 和 validation artifacts 后才能进入 `smoke_test_ready`。

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

| method | slug | tier | scientific_priority | engineering_readiness |
|:---|:---|:---|:---|:---|
| PepMLM | `pepmlm` | Tier 1 | high | ready |
| PepMirror | `pepmirror` | Tier 1 | high | heavy_dependency |
| RFdiffusion + ProteinMPNN | `rfdiffusion-proteinmpnn` | Tier 1 | high | needs_mapping |
| DiffPepBuilder | `diffpepbuilder` | Tier 2 | high | needs_mapping |
| PepGLAD | `pepglad` | Tier 2 | medium | needs_mapping |
| D-Flow / PeptideDesign | `d-flow-peptidedesign` | Tier 2 | high | needs_mapping |
| AfCycDesign / ColabDesign cyclic peptide | `afcycdesign-colabdesign` | Tier 2 | high | heavy_dependency |
| BindCraft | `bindcraft` | Tier 2 | medium | heavy_dependency |
| SaLT&PepPr | `salt-peppr` | Tier 3 | medium | needs_mapping |
| DexDesign / OSPREY3 | `dexdesign-osprey3` | Tier 3 | medium | heavy_dependency |

Tier is a scheduling shorthand. `scientific_priority` and `engineering_readiness` are the fields used for interpretation.
