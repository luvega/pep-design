# Benchmark Protocol v0

本协议冻结第一轮工程接口，不代表已经开始真实 Benchmark。所有方法在安装和最小运行前只处于 `planned` 或 `deferred` 状态。根据本地 Zotero Benchmark/评分文献的启示，本协议将 generation benchmark 与 ranking/rescoring benchmark 分开记录。

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

## Target Set And Controls

Future benchmark targets are defined by `benchmarks/input_sets/target_set_v0.csv`. Each target row must record target class, chain/structure provenance, positive control, negative or decoy controls, experimental affinity or assay evidence status, sequence/structure homology cluster and train-leakage risk.

Required target classes are:

- `protein_surface_ppi_target`
- `groove_or_pocket_peptide_binding_target`
- `pmhc_tcr_like_recognition_target`
- `d_peptide_or_chirality_aware_target`

No target should be described as an independent test until `train_leakage_risk` is reviewed and labelled `low`, `medium`, `high`, or `unknown`.

## Generation Versus Ranking Tracks

The generation benchmark asks whether a method can produce parseable, valid and task-compatible candidates from the standard inputs. The ranking/rescoring benchmark asks whether generated or pre-existing candidates can be prioritised using affinity, structure, interface and developability evidence.

`chang_ranking_2023` and `romero-molina_ppi-affinity_2022` support the need for ranking/rescoring calibration, but they do not validate de novo generation performance for the candidate methods.

## Failure States

| status | meaning |
|:---|:---|
| `not_installable` | repo or dependency installation cannot be completed |
| `weights_missing` | required model weights or checkpoint route is missing |
| `input_not_standardizable` | method input cannot be mapped to `run.csv` |
| `runs_but_no_batch` | method can run interactively but no batch route is clear |
| `output_not_evaluable` | output cannot be parsed into sequence/PDB/scoring schema |
| `deferred_dependency` | blocker is external, such as PyRosetta, AF3, AF2, Boltz, or ColabFold setup |

## Leakage And Homology Control

Every future target and reference binder should be assessed for possible overlap with method training sets, repository examples and source-paper benchmark sets. Protein targets should use sequence identity or structural similarity clusters where available. Peptide binders should use sequence similarity and motif overlap. Unknown leakage risk must remain explicit and cannot be described as an independent test.

## Evaluation Boundary

Sequence-only methods can be scored for parseability, length, motif constraints, and optional downstream structure prediction. Structural metrics are marked `not_applicable` until a structure prediction or docking layer produces model PDBs.

No method is considered locally reproducible until a later phase records environment, commit, command, input, output, runtime, and validation artifacts.
