# Benchmark Protocol v0

本协议冻结第一轮工程接口，不代表已经开始真实 Benchmark。所有方法在安装和最小运行前只处于 `planned` 或 `deferred` 状态。

## Tasks

| task_id | input | output | primary methods | status |
|:---|:---|:---|:---|:---|
| `T1_sequence_binder` | target sequence and optional constraints | peptide sequence candidates | PepMLM; SaLT&PepPr | planned |
| `T2_structure_peptide_binder` | target PDB, chain/pocket definition, optional reference binder | peptide complex structure or peptide structure | DiffPepBuilder; PepGLAD; D-Flow / PeptideDesign; PepMirror; AfCycDesign / ColabDesign cyclic peptide; DexDesign / OSPREY3 | planned |
| `T3_miniprotein_binder_baseline` | target PDB, hotspot or motif, length range | binder backbone and sequence | RFdiffusion + ProteinMPNN; BindCraft | planned |

## Method Mapping

| method | task_id | benchmark role |
|:---|:---|:---|
| PepMLM | `T1_sequence_binder` | sequence-only peptide binder baseline |
| SaLT&PepPr | `T1_sequence_binder` | peptide-guided degrader/interface sequence baseline; Tier 3 until task fit is confirmed |
| DiffPepBuilder | `T2_structure_peptide_binder` | structure-conditioned peptide binder diffusion route |
| PepGLAD | `T2_structure_peptide_binder` | full-atom peptide generation route |
| D-Flow / PeptideDesign | `T2_structure_peptide_binder` | D-peptide/flow-matching route |
| PepMirror | `T2_structure_peptide_binder` | cross-chirality D-peptide binder route |
| AfCycDesign / ColabDesign cyclic peptide | `T2_structure_peptide_binder` | cyclic peptide AF/ColabDesign baseline |
| DexDesign / OSPREY3 | `T2_structure_peptide_binder` | search/energy D-peptide comparator; Tier 3 until setup is mapped |
| RFdiffusion + ProteinMPNN | `T3_miniprotein_binder_baseline` | established miniprotein/protein binder baseline |
| BindCraft | `T3_miniprotein_binder_baseline` | integrated binder-design pipeline comparator |

## Failure States

| status | meaning |
|:---|:---|
| `not_installable` | repo or dependency installation cannot be completed |
| `weights_missing` | required model weights or checkpoint route is missing |
| `input_not_standardizable` | method input cannot be mapped to `run.csv` |
| `runs_but_no_batch` | method can run interactively but no batch route is clear |
| `output_not_evaluable` | output cannot be parsed into sequence/PDB/scoring schema |
| `deferred_dependency` | blocker is external, such as PyRosetta, AF3, AF2, Boltz, or ColabFold setup |

## Evaluation Boundary

Sequence-only methods can be scored for parseability, length, motif constraints, and optional downstream structure prediction. Structural metrics are marked `not_applicable` until a structure prediction or docking layer produces model PDBs.

No method is considered locally reproducible until a later phase records environment, commit, command, input, output, runtime, and validation artifacts.
