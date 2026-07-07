# 综述草稿对 Pep_design Benchmark 计划的参考价值评估

## Material Passport

| field | value |
|:---|:---|
| source draft | `G:\Downloads\Markdown笔记\王梁多肽综述草稿.md` |
| review date | 2026-06-11 |
| project | Pep_design Benchmark KB |
| evaluation focus | Benchmark 代表性、任务分类、靶点覆盖和证据边界 |
| skill route | `benchmark-paper-template` + `scientific-critical-thinking` |
| boundary | 只读评估综述草稿；不修改外部草稿、不写入 `target_set_v0.csv`、不新增性能或实验验证声明 |

## Executive Assessment

这份综述草稿对当前 protocol-first Benchmark 计划具有 **中高参考价值**，但价值主要集中在“背景框架”和“任务代表性论证”，而不是直接的数据或结果证据。

高价值部分包括 peptide discovery 背景、AI peptide design 从 prediction 到 generation 的叙事、sequence-driven / structure-driven / function-oriented 三类生成范式、数据稀缺、构象不确定性、cyclic peptide、D-peptide 和 unnatural peptide 的任务边界。这些内容可用于强化 Introduction、Task Stratification 和 Discussion。

中等价值部分是靶点类型启发，例如 MDM2/MDMX、PCSK9、PD-1、CD38、GLP-1/GPCR-like peptide contexts。这些案例可作为后续 target shortlist 的灵感来源，但必须经过结构来源、positive/negative controls、assay evidence、license 和 leakage 审计后，才可能进入计算 Benchmark 候选；若用于 prospective wet-lab validation，还需要进一步评估合成难度、检测平台和实验成本。

低价值或不可直接使用的部分包括：不能把综述草稿当作 Benchmark 数据集，不能据此说明任何方法已经本地复现、已运行或性能更优，不能替代 `target_set_v0.csv` 的 target freeze，也不能作为当前已完成湿实验验证证据。

## Table 1. 草稿章节到 Benchmark 计划的可用位置

| 草稿内容 | 对 Benchmark 的可用位置 | 可用价值 | 使用边界 |
|:---|:---|:---|:---|
| Abstract 与 Introduction 中关于 peptide flexibility、limited structural templates、chemical/topological diversity 的论述 | Introduction: Background + Running Example；Existing-benchmark limitations | 高 | 可用于说明为什么 peptide design 不能直接照搬 protein / small-molecule Benchmark；不能写成项目已经解决这些问题 |
| Figure 1 与历史叙事：SPPS、display technologies、AI-driven de novo design | Introduction 背景段；Related Work 背景 | 中 | 可用于压缩领域背景；不宜占用 Benchmark 主线篇幅 |
| Traditional computational strategies 与 wet-lab validation 路线 | Discussion: computational metrics 与 biological validation 边界 | 高 | 可支持“计算排序不能替代 SPR/BLI/ITC/cell assay”的论证；不能写成当前项目已完成实验验证 |
| Table 1: small molecule / peptide / protein / antibody generative modeling 差异 | Task Stratification；Benchmark Design Considerations | 高 | 可转化为 Benchmark 设计理由：peptide 需要 sequence-structure-topology 表示和 interface-aware constraints |
| Structure-driven generation | T2 `structure_peptide_binder` 任务说明；method family taxonomy | 高 | 可支持 T2 的存在；具体方法仍需本项目 method evidence matrix 和 runnability audit 支撑 |
| Sequence-driven generation | T1 `sequence_binder` 任务说明 | 高 | 可支持 PepMLM-like 路线的任务定义；不能推出 sequence-only 方法具有更好生物学效果 |
| Function/property-driven generation | developability / multi-objective scoring layer | 中高 | 可用于说明 developability 应独立于 binding score；实验层指标仍需真实数据或明确来源 |
| Cyclic peptide、D-peptide、other unnatural peptide 章节 | 横向约束标签：`cyclic_flag`、`chirality_flag`、`non-natural residue flag`；target class 扩展理由 | 高 | 可用于说明当前 Benchmark 覆盖缺口；不能直接把文中案例作为 independent test target |
| Conclusion and Perspectives 中关于 function-oriented design、data standardization、interpretability、computational cost 的讨论 | Discussion 与 Limitations | 中 | 可用于未来工作；不能作为 v0.8 readiness 的完成证据 |

## Table 2. 任务类型代表性评估

| 任务或约束类型 | 草稿覆盖情况 | 对当前 Benchmark 的映射 | 代表性判断 | 需要补强的证据 |
|:---|:---|:---|:---|:---|
| `T1_sequence_binder` / sequence-driven generation | 覆盖较好，涉及 pLM、masked language modeling、PepMLM/EvoBind-like 路线 | T1：target sequence 输入、peptide sequence 输出 | 足以支持任务分类背景 | 仍需本项目确认方法入口、license、batch route 和输出 schema |
| `T2_structure_peptide_binder` / structure-driven generation | 覆盖较好，涉及 target-aware、binding-site-conditioned、all-atom generation | T2：target PDB、binding context、reference binder 或 pocket 输入 | 足以支持 T2 是独立任务 | 需要具体 target/control、chain convention、PDB provenance 和 assay evidence |
| `T3_miniprotein_binder_baseline` | 通过 RFdiffusion/protein design 背景间接覆盖 | T3：protein/miniprotein binder baseline | 覆盖不足但可作为对照背景 | 仍需依赖 Overath、RFdiffusion + ProteinMPNN、BindCraft 等项目内证据 |
| cyclic peptide | 覆盖较强，强调拓扑约束、macrocycle、HELM-like 表示 | 横向约束：cyclic flag；主要影响 T2，也可能影响 T1 表示 | 支持将 cyclic peptide 作为 Benchmark 覆盖缺口 | 需要 cyclic-specific data source、结构/合成可行性和评分规则 |
| D-peptide / chirality-aware design | 覆盖较强，涉及 mirror transformation、D-Flow、PepMirror、HelixDiff 等 | 横向约束：chirality flag；`d_peptide_or_chirality_aware_target` | 支持当前 target class 的必要性 | 需要 stereochemistry-aware parsing、leakage check 和 wet-lab feasibility |
| other unnatural peptide / ncAA | 覆盖中等，强调 N-methylation、glycosylation、lipidation、backbone modification | 横向约束：non-natural residue flag；developability layer | 适合作为未来扩展，不宜作为当前主任务 | 需要 representation schema、license、assay 与 synthesis complexity 审计 |
| function/property-driven generation | 覆盖中等，涉及 multi-objective optimization 和 drug-like properties | developability / ranking-rescoring 的独立证据层 | 支持“不把 binding score 等同于 developability” | 需要溶解性、稳定性、permeability、toxicity 等来源或实验数据 |
| pMHC/TCR-like recognition | 草稿覆盖不足 | 当前项目已有 `pmhc_tcr_like_recognition_target` 类 | 草稿不能补强该类代表性 | 应继续依赖 TCRTransBench、pMHC/TCR 专项文献和独立负对照设计 |

总体判断：草稿覆盖 AI peptide design 的方法学空间较好，尤其是 sequence/structure/function 三分法和 cyclic/D/unnatural peptide 约束；但对 Benchmark 所需的 target/control、dataset license/schema、train leakage 和 assay-calibrated scoring 覆盖不足。因此，它能补强“为什么要分层 Benchmark”，不能替代“怎么冻结 target set”。

## Table 3. 可补充验证靶点类型建议

| 靶点或案例类型 | 草稿中的角色 | 可作为背景靶点 | 可作为计算 Benchmark 候选 | 可作为 prospective wet-lab validation 候选 | 判断与边界 |
|:---|:---|:---:|:---:|:---:|:---|
| MDM2/MDMX peptide inhibitor context | 临床相关 peptide example，PPI inhibition | 是 | 可能 | 较适合 | 适合代表 PPI/groove-like peptide inhibition；需确认结构、known binder、negative controls、assay route 和是否与方法训练/示例重叠 |
| PCSK9 macrocyclic peptide context | macrocyclic / orally bioavailable peptide example | 是 | 可能 | 条件性适合 | 可代表 cyclic/macrocyclic translational context；但实验体系、合成成本和 IP/数据可用性需要先评估 |
| PD-1 macrocyclic D/L peptide context | target-templated macrocyclic d-/l-peptide example | 是 | 可能 | 条件性适合 | 有助于补强 immune checkpoint 与 chirality/cyclic 交叉场景；实验解释可能涉及 cell function，不适合作为低成本首选 |
| CD38 D-peptide / PepMirror context | D-peptide wet-experiment example | 是 | 谨慎 | 谨慎 | 对 D-peptide 代表性很强，但若评估 PepMirror，可能存在 source-paper overlap；更适合作为背景或 calibration，不宜直接写成 independent test |
| GLP-1 / GPCR-like peptide context | GPCR peptide / function-oriented example | 是 | 可能 | 条件性适合 | 能补强当前 GPCR peptide benchmark watchlist；但 GPCR 功能 assay 复杂，需先找到可审计 target/control table |
| VEGF/VEGFR peptide-targeting context | structure-based peptide targeting example | 是 | 可能 | 可能 | 可代表 receptor/ligand 或 PPI-like interface；需确认可用结构、已知 peptide、negative controls 和 binding assay |
| broad antimicrobial / antiviral peptide generation | broad-spectrum activity example | 是 | 不建议作为主线 | 不建议作为当前主线 | 该类任务与 target-specific binder Benchmark 不完全一致，容易引入 endpoint mismatch |

建议：后续若要做真正的干湿结合验证，不应从综述草稿直接选定靶点，而应先建立一个 `prospective validation shortlist`。首轮可优先考虑 2-3 个互补靶点类型：一个 PPI/groove-like peptide target，一个 GPCR-like 或 receptor peptide target，一个 chirality/cyclic 约束 target。每个靶点必须先完成结构来源、known binder、negative/scrambled controls、assay type、license 和 leakage 审计，再决定是否合成 8-12 条候选 peptide。

## 分级可用性结论

### 高价值：可直接进入 Benchmark 代表性论证

- Peptide 相比 small molecule、protein 和 antibody 的独特性：柔性高、构象集合显著、结构模板有限、拓扑和化学修饰复杂。
- AI peptide design 的三类路线：structure-driven、sequence-driven、function/property-driven generation。
- cyclic peptide、D-peptide 和 unnatural peptide 不是普通 linear peptide 的小变体，而是需要独立记录 topology、chirality、representation 和 scoring applicability 的横向约束。
- 数据稀缺、结构不确定性、target conditioning 和 interface modeling 是 Benchmark 的核心评估缺口。

### 中等价值：可作为候选引用或靶点启发

- MDM2/MDMX、PCSK9、PD-1、CD38、GLP-1/GPCR-like contexts 可作为 target-selection 的候选方向。
- SPR、BLI、ITC、fluorescence-based assay、cellular assay、toxicity、enzymatic degradation 和 stability tests 可作为 wet-lab validation 层的 assay vocabulary。
- PepINVENT、HELM-GPT、D-Flow、PepMirror、HelixDiff 等方法描述可帮助完善 Related Work 或 citation bank，但方法纳入仍应以本项目 `candidate_method_scorecard.csv`、runnability audit 和 source/license evidence 为准。

### 低价值或不可用：不能作为当前 Benchmark 证据

- 不能作为 dataset download、schema audit 或 license audit 的替代证据。
- 不能证明任何候选方法已本地安装、已运行、已复现或性能更优。
- 不能替代 `target_set_v0.csv` 的 target freeze。
- 不能作为 wet-lab validation 已完成的证据。
- 不能将文中临床或实验案例直接转写为本项目的 independent Benchmark target。

## 对当前 Benchmark 计划的具体影响

1. Introduction 可以更明确地把 Benchmark 缺口写成：peptide design 的评估难点不是单纯缺 leaderboard，而是 sequence、structure、topology、chirality、developability 和 biological validation 的证据层不一致。
2. Task Stratification 仍应保持 T1/T2/T3，但需要把 cyclic、D-peptide、unnatural residue 作为横向约束标签，而不是单独混入同一 leaderboard。
3. Dataset 代表性目前仍不全面。现有候选数据源足以支撑 protocol/readiness 和部分 retrospective calibration，但还不能代表 cyclic/D/unnatural peptide、GPCR peptide、pMHC/TCR-like recognition 和 developability 的完整空间。
4. 若后续需要“真正的干湿结合验证”，应自选少量代表性靶点做 prospective validation，而不是直接依赖现有数据集或综述案例。湿实验验证应被写作未来 add-on，不是当前 v0.8 的完成项。
5. 综述草稿提示当前 Benchmark 可以增加一个“代表性缺口”小节：现有计划覆盖 method heterogeneity 和 readiness gate 较强，但对 cyclic/D/unnatural peptide 的数据源、assay route 和 stereochemistry-aware metrics 仍需补强。

## Claim Boundary

| claim type | allowed wording | forbidden wording |
|:---|:---|:---|
| 草稿价值 | “该综述草稿支持/提示/可作为背景说明...” | “该综述证明本 Benchmark 已经全面覆盖...” |
| 任务分类 | “草稿支持将 sequence-driven、structure-driven 和 function-oriented generation 区分讨论” | “草稿证明三类任务已经可公平排名” |
| 靶点案例 | “MDM2/MDMX、PCSK9、PD-1、CD38、GLP-1 等可作为候选靶点方向” | “这些靶点已进入 frozen target set” |
| 数据集证据 | “草稿可提示数据稀缺和代表性缺口” | “草稿可替代 dataset schema/license 审计” |
| 方法性能 | “草稿可作为方法背景或 Related Work 候选来源” | “草稿证明某方法性能最佳/已复现/已运行” |
| 湿实验 | “后续可设计 prospective wet-lab validation” | “当前 Benchmark 已完成实验验证” |

## Recommended Next Steps

1. 暂不修改 `target_set_v0.csv`。先把综述草稿中的靶点案例整理为候选方向，而不是 target rows。
2. 后续可新增一份 `prospective_validation_shortlist`，字段至少包括 target class、known binder、negative controls、structure provenance、assay route、synthesis risk、license 和 leakage risk。
3. 在 manuscript Introduction 或 Discussion 中引用该草稿的思想时，应优先使用“背景/挑战/分类”层面，而不是“结果/性能/验证”层面。
4. 对 cyclic、D-peptide 和 unnatural peptide 的 Benchmark 补强应从 representation、schema、metric applicability 和 wet-lab feasibility 四个维度推进。
