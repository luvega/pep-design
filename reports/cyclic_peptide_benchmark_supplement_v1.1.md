# v1.1 环肽、D-肽与非天然肽 Benchmark 补丁

## Purpose

本报告综合 `JMC2025_cyclic...md`、`CAS_Insights...环肽...md`、`环肽设计AI方法综述...md` 和 `王梁多肽综述草稿.md` 中可借鉴的结构、内容和思路，用于完善本项目对 cyclic peptide、D-peptide、macrocycle 和 ncAA peptide 的协议层设计。所有具体论文、数据集、药物和性能数字在正式引用前仍需 primary-source verification。

## Why This Matters

环肽和非天然肽不是 linear peptide 的简单变体。环化拓扑、手性、非天然残基和修饰会改变构象集合、合成复杂度、膜通透性、代谢稳定性、蛋白酶抗性和评分函数适用性。若只使用 `cyclic=yes` 或 `chirality=D` 这类粗粒度标签，Benchmark 难以解释不同方法输出的可比性。

## Topology-Aware Fields

建议后续在 `run.csv` 或扩展 metadata 中记录以下语义。v1.1 只定义 planned fields，不改变当前 `run.csv` 主 schema。

| field | allowed examples | use |
|:---|:---|:---|
| `cyclization_mode` | `head_to_tail`; `head_to_sidechain`; `sidechain_to_tail`; `sidechain_to_sidechain`; `disulfide`; `thioether`; `mixed`; `unknown` | 区分环化方式和 parser 需求 |
| `cycle_count` | `0`; `1`; `2`; `polycyclic`; `unknown` | 区分 monocyclic、bicyclic、多环 |
| `macrocycle_class` | `small_cyclic`; `macrocycle`; `bicyclic`; `polycyclic`; `unknown` | 支撑 target class 与 developability 分层 |
| `chirality_detail` | `L`; `D`; `mixed`; `heterochiral`; `unknown` | 支撑 D-peptide 和 PepMirror/D-Flow 类方法 |
| `modification_type` | `N_methylation`; `lipidation`; `glycosylation`; `PEGylation`; `ncAA`; `backbone_modification`; `none`; `unknown` | 支撑非天然肽和合成复杂度 |
| `representation_scheme` | `FASTA`; `HELM`; `CHUCKLES`; `PDB`; `mmCIF`; `method_specific`; `unknown` | 支撑输入输出解析和可复现记录 |

## Developability Patch

当前项目已有 `developability_metrics.csv` metadata-level 字段。结合补充资料，建议把解释边界明确为：

- 当前可记录：length、molecular weight proxy、net charge、hydrophobicity、aromaticity、cysteine/disulfide flags、cyclic flag、chirality、non-natural residue flag、aggregation-risk proxy、synthesis complexity flag。
- 后续才可记录：solubility、serum stability、protease stability、plasma protein binding、PAMPA/Caco-2、microsomal stability、hemolysis、immunogenicity、purity/yield。
- 没有实验或可靠文献数据时，later experimental-level 字段必须为空并记录 `not_available` 或 `not_measured`。

## Method-Landscape Implications

| method | v1.1 status | reason |
|:---|:---|:---|
| RFpeptides | patch_candidate | cyclic/macrocycle binder design 代表性强，但需 source/license/weights/input contract 审计 |
| CyclicMPNN | patch_candidate | cyclic peptide backbone-to-sequence optimization 线索，定位不是完整 binder pipeline |
| PPFlow | patch_candidate | target-aware torsional flow matching，与 PepFlow 不同 |
| PepMimic | patch_candidate | binding-interface mimicry，与 PepMirror 不同 |
| PocketXMol | patch_candidate | atom-level unified generation 线索，需核验 peptide task、license 和可运行路线 |
| BoltzGen | patch_candidate | all-atom cross-modal binder design 线索，需核验公开状态和 peptide input contract |
| PepINVENT | patch_candidate | ncAA/CHUCKLES 表示线索，偏 template/property optimization |
| HELM-GPT | patch_candidate | HELM macrocycle 表示和 permeability/binding 多目标线索，需核验 target-conditioning 边界 |

这些方法不进入 current include set。后续若要升级，必须先更新 `candidate_method_scorecard.csv`、runnability matrix、source pin audit 和 method contract。

## Target Direction Implications

CAS/JMC/综述资料提示的 target directions 包括 PD-1/PD-L1、Ras/SOS1、MDM2/TP53、TNF family、MCL1、Keap1、GABARAP、GPCR-like receptors 和 immune/infection contexts。它们只能作为 `target_direction_candidate`，不得直接进入 `target_set_v0.csv`。晋升条件仍是：结构来源、positive binder、negative/decoy controls、assay evidence、license、leakage 初评齐全。

## Claim Boundary

允许写：

- “补充资料提示环肽 Benchmark 需要 topology-aware 和 developability-aware 评估。”
- “RFpeptides、CyclicMPNN、PocketXMol、BoltzGen 等可作为后续方法地形审计线索。”
- “HELM/CHUCKLES 等表示方式提示非天然肽输出需要独立 parser contract。”

不得写：

- “本项目已完成环肽方法性能比较。”
- “补充资料中的 target 已进入 frozen target set。”
- “新增 patch methods 已可运行或已复现。”
