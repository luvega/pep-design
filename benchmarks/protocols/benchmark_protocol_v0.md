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

## Generation Paradigm Taxonomy

任务轴（T1/T2/T3）描述输入/输出形态；本节补充一条正交的**生成范式轴**，描述条件化与优化机制。范式标签用于方法理解与分层呈现，不得据此对方法做公平性能排名，且单一方法可同时落入多个范式。详细方法映射见 [`../method_sources/method_landscape_watchlist_v0.9.csv`](../method_sources/method_landscape_watchlist_v0.9.csv) 与 [`../../reports/review_synthesis_benchmark_framework_supplement.md`](../../reports/review_synthesis_benchmark_framework_supplement.md)。

| paradigm | conditioning core | benchmark implication |
|:---|:---|:---|
| structure_driven | 以靶点 3D 结构/口袋为条件 | 需要结构/界面指标与 pocket/chain 约定 |
| sequence_driven | 仅以靶点序列为条件（pLM 先验） | 结构指标默认 `not_applicable`，可选下游结构预测层 |
| function_property_driven | 以多属性/界面相似性为优化目标 | 支撑 developability 与 ranking/rescoring 的独立评分轴 |

## Cross-Cutting Topology And Chirality Constraints

cyclic、D-peptide、unnatural-residue 是横向约束，不是普通 linear peptide 的小变体，必须独立记录拓扑、手性与评分适用性，且不并入同一 leaderboard。

| 约束类别 | 子类 | run.csv 字段 | 评分适用性 |
|:---|:---|:---|:---|
| 环化拓扑 | head-to-tail、disulfide、side-chain crosslink、heterocyclic/ncAA 锁定 | `cyclic` + `peptide_type` + `notes` 记录环化模式 | 计入 design_feasibility/developability；结构指标视 reference 而定 |
| 手性 | L / D / mixed(heterochiral) | `chirality` + `peptide_type` | 需 stereochemistry-aware parsing；D-肽-L-靶能量评分标注 `needs_validation` |
| 非天然残基 | ncAA、N-methylation、glycosylation、lipidation、backbone modification | `peptide_type` + non-natural residue flag | 仅 metadata-level 代理；表示方案（CHUCKLES/HELM）作未来扩展 |

## Representativeness Gaps

下列内容写作 Benchmark 代表性缺口，而非已解决项：peptide-protein 复合物数据稀缺与偏置；构象不确定性（构象集合/诱导结合）；cyclic/D/ncAA 的表示与评分适用性；affinity 单指标不足需 developability 独立层。function-oriented/multi-target 设计属未来工作，不作为当前 readiness 完成证据。

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
