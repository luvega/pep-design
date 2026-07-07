# Benchmark Manuscript Draft Outline

## Working Title

**面向近期 AI 多肽设计方法的 Benchmark 框架：专家审查、可用性审计、任务分层、数据集 readiness 与服务器 dry-run 协议**

English working title: **A benchmark framework for recent AI peptide design methods: expert review, availability auditing, task stratification, dataset readiness and server dry-run contracts**

## Manuscript Positioning

本文定位为 Benchmark framework / protocol-first manuscript。文章核心问题不是“哪个方法当前最好”，而是“如何在任务、靶点、对照、输入输出、可运行性、可开发性和评分校准层面公平比较近期 AI 多肽设计方法”。因此，本文只陈述由本项目 KB 支持的事实：2021-06-03 至 2026-06-03 文献范围、10 个 first-wave candidate methods、三类任务协议、专家团审查、候选数据集 readiness、靶点候选矩阵、源码 pinning、link/data availability、server readiness、ARS 综合评审、generation/ranking 双轨协议和统一评分 schema。

写作风格采用中文学术初稿，保留英文方法名、模型名、论文题名、BibTeX key、Zotero item key、文件名和命令名。论证动词优先使用“提示、支持、表明、拟评估、仍需验证”；避免“证明、最佳、全面优于”等当前证据不能支持的表述。所有 performance、hit rate、experimental success 和 local reproducibility 相关结论必须保留为后续真实 Benchmark 阶段的待评估内容。

## Abstract Draft

生成式模型、蛋白基础模型和结构设计方法正在进入多肽设计领域，覆盖 linear peptide binder、cyclic peptide、D-peptide、miniprotein binder、protein-peptide interaction 和 pMHC/TCR-like recognition 等任务。然而，不同方法的输入、输出、依赖、代码、权重、手性约束和可开发性边界差异较大，直接建立统一 leaderboard 容易混淆生成能力、排序能力、工程可运行性和生物学证据。

为解决这一问题，我们基于本地 Zotero/PD-wiki 知识库整理 2021-06-03 至 2026-06-03 的近期多肽设计方法文献，并结合本地 Benchmark/评分/affinity prediction 文献建立 protocol-first 框架。该框架包含 10 个 first-wave candidate methods、三类任务、专家团审查、候选 benchmark dataset readiness、靶点候选矩阵、标准靶点集和对照集 schema、可运行性矩阵、link/data availability、server dry-run contract、generation benchmark 与 ranking/rescoring benchmark 双轨协议，以及 `run.csv -> metric CSVs -> merged_run.csv` 的统一评分数据流。

本文强调，AlphaFold-style ranking、protein-peptide affinity prediction 和 peptide developability 文献可用于设计评分与校准策略，但不能在未运行真实 benchmark 前支持方法优劣结论。当前版本提供的是可复用 Benchmark 协议和写作框架，不声明候选方法已完成本地复现，也不比较最终性能或实验成功率。

## Main Thesis

AI 多肽设计 Benchmark 应先建立任务分层、靶点/对照集、泄漏控制和工程可运行性标准，再进行模型性能排序。对于短肽、环肽、D-肽、heterochiral peptide 和 miniprotein binder，统一评价必须同时记录输入类型、输出形态、靶点类别、positive/negative controls、手性/环化约束、训练集泄漏风险、依赖版本、失败状态、药物化学可开发性代理指标和评分适用性，否则计算指标容易被误读为通用设计能力或实验可转化性。

## 1. Introduction

### Benchmark Part 1: Background And Running Example

多肽设计正在从经验筛选和结构启发优化，扩展到由 protein language models、diffusion models、full-atom generative models 和 AF2/MPNN-style pipelines 支持的条件生成。PepMLM 代表 sequence-conditioned peptide binder 方向，RFdiffusion + ProteinMPNN 和 BindCraft 代表 miniprotein/protein binder baseline，PepMirror、D-Flow 和 DexDesign 代表 D-peptide 或 chirality-aware design，AfCycDesign / ColabDesign cyclic peptide 代表 cyclic peptide structure/design 路线。建议引用：`chen_target_2025`, `bennett_improving_2023`, `pacesa_bindcraft_2024`, `yang_cross-chirality_2026`, `guerin_dexdesign_2024`, `rettie_cyclic_2023`。

Figure 1 的 running example 应展示同一 peptide-binding target 在三类路线中的差异：`PepMLM`-like sequence-conditioned route 接收 target sequence 并输出 peptide sequences；`PepMirror` 或其他 structure-conditioned peptide method 需要 target structure、binding context 与 chirality-aware handling；`RFdiffusion + ProteinMPNN` 或 `BindCraft` 依赖 target structure / hotspot 路线并输出 miniprotein/protein-binder candidates。该例子的重点不是展示哪个方法更好，而是说明输入、输出、chain convention、scoring applicability 和 failure state 不同，不能直接进入同一无分层 leaderboard。

### Benchmark Part 2: Existing-Benchmark Limitations

当前 Benchmark 的主要缺口可以压缩为三类。第一，task mismatch：sequence-only peptide output、peptide complex structure output 和 miniprotein binder output 往往不能在未分层接口下公平比较。第二，readiness mismatch：code URL、source pin、server contract 或权重路线可能被误读为已安装、已复现或已可批处理。第三，evidence mismatch：structure confidence、affinity prediction、developability proxy、negative/off-target specificity 和 biological validation 是不同证据层，不能被折叠成一个笼统分数。

### Benchmark Part 3: Research Questions

RQ1: How can recent AI peptide-design methods be stratified into task-compatible benchmark interfaces before performance comparison? RQ2: What target/control, leakage, runnability and scoring metadata are required before generation and ranking outputs become interpretable? RQ3: Which methods and dataset sources are currently at metadata/source/dry-run readiness gates, and what evidence is required before smoke-test or performance claims?

这些 RQs 分别对应任务分层、证据/评分边界和执行 readiness。当前稿件可以回答 protocol design 和 readiness state；真实模型能力边界、top-k enrichment、failure rate、runtime 和 calibration error 必须等服务器端 smoke test 或正式 Benchmark 后再报告。

### Benchmark Part 4: Design Considerations

一个合格的 AI 多肽设计 Benchmark 协议应满足五个设计要求。G1 task compatibility：先在 T1/T2/T3 内比较，再解释跨任务差异。G2 evidence provenance：target、positive/negative controls、assay type、license 和 leakage status 必须先于 independent-test wording。G3 execution gating：方法状态应从 `metadata_ready`、`source_pinned`、`license_checked`、`weights_manifested`、`input_contract_ready`、`dry_run_ready` 到 `smoke_test_ready` 逐级推进。G4 metric applicability：sequence-only、chirality-aware、cyclic peptide 和 miniprotein 输出需要显式记录 `not_applicable_reason`。G5 claim safety：protocol readiness、server planning、local reproducibility 和 biological validation 必须保持不同 claim state。

### Benchmark Part 5: Our Proposal

本文提出一个 protocol-first Benchmark 框架：从 432 条去重文献记录中筛选 10 个 first-wave include methods，将方法映射到 T1 sequence binder、T2 structure peptide binder 和 T3 miniprotein binder baseline，建立靶点/对照集 schema、dataset watchlist、runnability/source audits、server dry-run contracts、developability proxies、negative-design panel 和 `run.csv -> metric CSVs -> merged_run.csv` 的统一数据流。该框架的贡献是为后续真实 Benchmark 提供可复用工程协议，而不是在未运行方法前给出性能排名。

### Benchmark Part 6: Contributions

1. 本文定义一个 task-aware Benchmark protocol，用于比较 recent AI peptide-design methods，同时避免把 sequence binder、structure peptide binder 和 miniprotein binder baseline 混为同一任务。
2. 本文构建 evidence-backed readiness artifacts，覆盖 method selection、dataset/watchlist governance、target/control schema、runnability audit、source pinning 和 server dry-run contracts。
3. 本文将 generation、ranking/rescoring、developability、negative-design 和 leakage-aware scoring 拆分为独立 reporting layers，并通过 `run.csv` 与 metric CSVs 连接。
4. 本文提供 claim-gated manuscript framework，明确 protocol readiness 不等于 future performance、local reproducibility 或 experimental validation。

## 2. Benchmark Lessons From Local Zotero Literature

### Paragraph Role: Evidence Layer

本项目新增 `manuscript/support/benchmark_literature_lessons.md` 和 `kb/tables/benchmark_literature_lessons.csv`，专门记录本地 Zotero 中与 Benchmark、评分、affinity prediction 和 peptide developability 相关的启示。第一批重点条目包括 `chang_ranking_2023`、`romero-molina_ppi-affinity_2022`、`jin_tpeppro_2024`、`sun_deep_2024`、`yin_leveraging_2024`、`oeller_sequence-based_2023`、`pingitore_v_delocalized_2024` 和 `rettie_accurate_2025`。

v0.4 进一步新增 `ops/audits/expert_panel_review_v0.4.md`、`kb/tables/expert_review_action_items.csv`、`dataset_readiness_scorecard.csv` 和 `target_candidate_matrix_v0.4.csv`，用于把药物化学、计算结构生物学、AI Benchmark、数据/统计和工程复现五类审查意见转化为可裁决 action items。Overath `final_dataset.csv` 的外部小文件审计显示本地扫描为 3,676 rows、312 columns、15 个非空 target_id 和 7 行 blank `target_id`；因此后续写作应同时区分“文献/数据集描述的 3,766 binders”和“本地审计 CSV 的 3,676 rows”。

### Paragraph Role: Ranking Lesson

`chang_ranking_2023` 提示 AlphaFold-style competitive modeling 可用于 peptide binder affinity ranking，但适用范围依赖 peptide/receptor structures 是否能被稳定预测。该文献更适合作为 ranking/rescoring benchmark 的设计依据，而不是直接证明 de novo generation 方法可以产生高质量候选。

### Paragraph Role: Affinity Prediction Lesson

`romero-molina_ppi-affinity_2022` 和近期 peptide-protein interaction prediction 文献提示，protein-peptide affinity scoring 不能直接套用 small-molecule scoring 或 generic PPI scoring。后续评分应记录 assay type、positive/negative controls、experimental affinity status 和 calibration set，而不是仅依赖结构置信度。

### Paragraph Role: Developability Lesson

`oeller_sequence-based_2023`、`pingitore_v_delocalized_2024` 和 `rettie_accurate_2025` 支持将 peptide developability 作为独立证据层。可计算 metadata-level proxies 可以用于初筛，但 solubility、serum stability、protease stability、permeability、hemolysis、immunogenicity、purity/yield 等实验层指标必须等真实数据或明确文献来源后再填写。

### Paragraph Role: v1.1 Supplementary-Source Boundary

v1.1 新增 `manuscript/support/supplementary_materials_reference_value_v1.1.md`、`manuscript/support/short_peptide_scoring_rationale_v1.1.md` 和 `manuscript/support/cyclic_peptide_benchmark_supplement_v1.1.md`，把 6 份外部 Markdown 补充材料转化为 source discovery 和 protocol framing。短肽对接材料支持“docking score 不能单独解释短肽结合”的评分边界；环肽/JMC/CAS/环肽 AI 材料支持 topology-aware、chirality-aware、ncAA-aware 和 developability-aware 的协议补强；流匹配材料只支持 method paradigm 背景。新增 RFpeptides、CyclicMPNN、PPFlow、PepMimic、PocketXMol、BoltzGen、PepINVENT 和 HELM-GPT 仅为 patch candidates，不进入当前 include set，也不构成源码可运行或性能证据。

## 3. Literature Scope And Candidate Method Selection

### Paragraph Role: Evidence Source

本研究的文献层基于本地 Zotero API、PD-wiki 历史证据层和外部 repository route 校验构建，时间窗为 2021-06-03 至 2026-06-03。当前去重后包含 432 条 Zotero-derived records，其中 125 条标记为 included，26 条作为 background-only，281 条需要后续 manual check。该设置保证候选方法来自明确来源层，同时保留 Zotero item key 与 BibTeX key 的边界。

### Paragraph Role: Selection Logic

方法筛选遵循“先可运行，再代表性”的原则。候选方法需要具备代码或服务可运行线索、可标准化输入、可评估输出和可记录版本/参数/资源需求的可能性。最终 include set 包含 PepMLM、SaLT&PepPr、DiffPepBuilder、PepGLAD、D-Flow / PeptideDesign、PepMirror、AfCycDesign / ColabDesign cyclic peptide、DexDesign / OSPREY3、RFdiffusion + ProteinMPNN 和 BindCraft；PepFlow 与 BoltzDesign1 暂列 watchlist。

### Paragraph Role: Evidence Boundary

该筛选不等同于本地复现，也不代表方法性能高低。当前纳入依据主要是 metadata、repository route、published method scope 和 scoring compatibility。对于 code status、weights status、license、batch inference、training overlap 和 target-set fit 的判断仍需要在 smoke-test 和 leakage-check 阶段进一步核验。

## 4. Target Set And Control Set Design

### Paragraph Role: Target Schema

标准靶点集由 `benchmark/input_sets/target_set_v0.csv` 定义，字段包括 `target_id`、`task_id`、`target_class`、`pdb_id`、`chain_ids`、`apo_or_holo`、`known_binder`、`negative_controls`、`experimental_affinity`、`assay_type`、`sequence_identity_cluster`、`train_leakage_risk`、`license` 和 `notes`。当前文件只冻结 schema，不选择真实靶点。

### Paragraph Role: Target Classes

靶点至少覆盖四类：`protein_surface_ppi_target`、`groove_or_pocket_peptide_binding_target`、`pmhc_tcr_like_recognition_target` 和 `d_peptide_or_chirality_aware_target`。该分类避免把 PPI surface、groove/pocket-like target、pMHC/TCR-like recognition 和 chirality-aware design 混为同一任务。

### Paragraph Role: Controls

每个未来 target row 必须记录 positive control、negative or decoy control、结构来源和实验读数状态。positive control 可以是已知 binder、参考 peptide、已解析 complex 或文献报道的活性序列；negative control 可以是近邻非结合序列、同源但非预期靶标、scrambled peptide 或 decoy structure。未完成来源审计前，任何靶点都不能写成 independent test case。

### Paragraph Role: Dataset Candidate Audit

候选 benchmark dataset 与 frozen target set 必须分开。`candidate_benchmark_datasets.csv` 记录 Overath binder-success meta-analysis、PEPBI、PepMerge/PepBDB/Q-BioLip、PepMirror resource routes、Chang AF2 ranking cases、PepBenchmark/PepBenchData 和 GPCR peptide design benchmark 等候选来源。该表保留 v0.3 的 download policy 字段；v0.4 则通过 `dataset_readiness_scorecard.csv` 记录哪些数据集已经完成小文件外部审计、哪些仍停留在 metadata-only 状态。任何候选数据集都不代表已经抽样或进入最终 target set。

### Paragraph Role: Dataset Readiness And Target Candidates

v0.4 使用 `dataset_readiness_scorecard.csv` 和 `target_candidate_matrix_v0.4.csv` 区分 dataset readiness、target candidates 和 frozen target set。Overath 可作为 T3 ranking/rescoring 与 scoring calibration 的 candidate，但不是 peptide-specific generation evidence；FGFR2、EGFR、Mdm2、pMHC_NY1 和 pMHC_SILSY1 等 target candidates 只能写为 `calibration_candidate_not_frozen`。7 行 blank target rows 必须在任何定量分析前排除或修复。

## 5. Task Stratification: T1/T2/T3

### Paragraph Role: Task Design

本 Benchmark 将候选方法划分为三类任务。`T1_sequence_binder` 以 target sequence 为主要输入，输出 peptide sequence candidates；`T2_structure_peptide_binder` 以 target PDB、chain/pocket definition 或 reference binder 为输入，输出 peptide complex structure 或 peptide structure；`T3_miniprotein_binder_baseline` 以 target PDB、hotspot 或 length range 为输入，输出 binder backbone 和 sequence。

### Paragraph Role: Method Mapping

PepMLM 和 SaLT&PepPr 映射到 T1。DiffPepBuilder、PepGLAD、D-Flow / PeptideDesign、PepMirror、AfCycDesign / ColabDesign cyclic peptide 和 DexDesign / OSPREY3 映射到 T2。RFdiffusion + ProteinMPNN 和 BindCraft 映射到 T3。该映射允许同任务内比较优先进行，而跨任务比较仅限于工程可运行性、输出可评估性和资源需求。

### Paragraph Role: Rationale

任务分层的必要性来自多肽设计对象本身的异质性。linear peptide、cyclic peptide、D-peptide、heterochiral peptide 和 miniprotein binder 在构象自由度、手性表示、结构输出和实验验证路径上不同。将这些方法放入同一未分层 ranking 会掩盖任务定义带来的差异。

## 6. Generation Benchmark Protocol

### Paragraph Role: Definition

Generation benchmark 评价方法能否从标准输入产生 parseable、valid、task-compatible outputs。主要指标包括 output completeness、sequence/PDB parseability、length validity、chain validity、chirality flag、cyclic flag、non-natural residue flag、失败状态和 runtime/resource metadata。

### Paragraph Role: Input Standardisation

工程层采用统一 `run.csv` 作为主索引，每个设计样本使用 `design_id` 连接方法、任务、输入、输出和后续评分。结构任务默认 binder chain 为 `A`，target chain 为 `B`；多链 target 可记录为 `B,C,D...`。如果某一方法要求不同 chain convention，适配层必须记录原始 chain 到标准 chain 的映射。

### Paragraph Role: Failure Modes

工程失败状态被显式编码为 `not_installable`、`weights_missing`、`input_not_standardizable`、`runs_but_no_batch`、`output_not_evaluable` 和 `deferred_dependency`。这些状态用于区分方法不可运行、权重不可得、输入不能标准化和输出不能评分等不同问题，避免将工程失败误写为科学性能不足。

## 7. Ranking And Rescoring Benchmark Protocol

### Paragraph Role: Definition

Ranking/rescoring benchmark 评价已有候选或生成候选能否被 affinity、structure、interface 和 developability evidence 合理排序。该评价线与 generation benchmark 分开报告，因为一个 ranker 的表现不能说明 de novo generator 的生成能力，一个 generator 也可能产生可解析候选但缺乏校准排序能力。

### Paragraph Role: Calibration

Ranking/rescoring 需要 positive controls、negative or decoy controls、assay type、experimental affinity status 和 calibration set。`chang_ranking_2023` 和 `romero-molina_ppi-affinity_2022` 可作为评分设计证据，但不能被写成候选生成方法性能的直接验证。

### Paragraph Role: Reporting

后续真实运行时，ranking 指标应与 generation 指标分开呈现。可以报告排序相关性、top-k enrichment、known binder rank、negative control separation、calibration error 和 not-applicable reason；当前阶段只定义这些字段，不填入任何结果。

## 8. Runnability And Dependency Audit

### Paragraph Role: Priority Model

可运行性审计不再把科学价值和安装准备度混成一个分数。`method_runnability_matrix.csv` 保留 `tier` 作为 smoke-test scheduling shorthand，同时新增 `scientific_priority` 和 `engineering_readiness`。`scientific_priority` 记录方法对多肽 Benchmark 科学问题的代表性；`engineering_readiness` 记录当前最小运行路径的工程负担。

### Paragraph Role: Tier Summary

PepMLM、PepMirror 和 RFdiffusion + ProteinMPNN 仍列为 Tier 1，但解释不同：PepMLM 工程准备度较高，PepMirror 科学优先级高但依赖 PyRosetta/Vina/OpenMM/Zenodo checkpoint，RFdiffusion + ProteinMPNN 是 miniprotein baseline 的重要参照但仍需权重和版本锁定。DiffPepBuilder、PepGLAD、D-Flow、AfCycDesign 和 BindCraft 列为 Tier 2；SaLT&PepPr 与 DexDesign / OSPREY3 列为 Tier 3。

### Paragraph Role: Interpretation

Tier 不是性能判断。Tier 1 只表示当前适合优先设计 smoke-test，Tier 2 和 Tier 3 方法仍可在后续阶段进入真实运行。PepFlow 和 BoltzDesign1 保持 watchlist，用于后续替补或扩展任务。

### Paragraph Role: Source Pinning Boundary

v0.4 只对 PepMLM、RFdiffusion、ProteinMPNN 和 PepMirror 做外部 shallow clone pinning。`source_pin_audit_v0.4.csv` 记录 commit、license file、README entrypoint、environment file、batch route 和 weights policy；`audit_status=pinned_no_install` 表示只完成源码入口审计，不代表安装、运行或复现。

## 9. Scoring Framework: Structure, Interface, Similarity, Feasibility, Developability

### Paragraph Role: Metric Families

评分框架包含七类指标。`structure_confidence` 记录 pLDDT、pTM、ipTM、PAE/iPAE 和 ipSAE；`interface_geometry` 记录 contacts、interface area、H-bonds 和 clash count；`structure_similarity` 记录 DockQ、backbone RMSD 和 interface RMSD；`design_feasibility` 记录 length、chain validity、chirality flag、cyclic flag 和 output parseability；`developability` 记录 metadata-level 可开发性代理指标；`negative_design` 记录 off-target panel；`leakage_homology` 记录 target/reference overlap 风险。

### Paragraph Role: Developability Boundary

当前阶段 developability 只包含 metadata-level proxies：length、molecular weight proxy、net charge、hydrophobicity、aromaticity、cysteine/disulfide flags、cyclic flag、D/L/mixed chirality、non-natural residue flag、aggregation-risk proxy 和 synthesis complexity flag。later experimental-level 字段包括 solubility、serum stability、protease stability、plasma protein binding、PAMPA/Caco-2、microsomal stability、hemolysis、immunogenicity、purity/yield；未有数据时必须留空或标记 `not_available`。

### Paragraph Role: Method-Specific Applicability

对于 sequence-only 方法，结构评分字段应保留为空，并记录 `status=not_applicable` 与 `not_applicable_reason=sequence_only_output`，除非后续添加结构预测层。对于 D-peptide 和 cyclic peptide 方法，评分必须记录 chirality、cycle constraint、chain mapping 和可解析结构。对于 miniprotein baseline，界面和结构置信度评分可作为主要计算指标，但仍不能替代实验结合或功能证据。

## 10. Data Leakage, Homology Control And Target Novelty

### Paragraph Role: Leakage Definition

每个 target 和 reference binder 需要记录是否可能出现在方法训练集、repository examples 或 source-paper benchmark set 中。对 protein target 使用 sequence identity 或 structural similarity cluster；对 peptide binder 使用 sequence similarity、motif overlap 和 known binder overlap。

### Paragraph Role: Risk Labels

所有泄漏风险先标为 `unknown`、`low`、`medium` 或 `high`。未核实的 `unknown` 不能写成 independent test。若某一 target 与方法论文示例、公开训练数据或同源 benchmark target 高度重叠，只能作为 calibration/background case，而不能作为泛化性能证据。

### Paragraph Role: Negative Design

对 peptide binder、pMHC/TCR-like 和 degrader/interface 方法，新增 negative/off-target panel 计划。字段包括 `off_target_id`、`similarity_to_target`、`expected_nonbinder_reason`、`healthy_tissue_or_related_protein_flag`、`scoring_result` 和 `status`。pMHC/TCR-like 任务还应记录 HLA allele、peptide antigen、near-neighbour peptide panel 和 cross-reactivity risk。

## 11. Anticipated Results And Reporting Standards

### Paragraph Role: Planned Results

当前初稿中的 Results 部分应采用 planned results structure，而不是性能结论。第一部分报告文献和候选方法筛选结果；第二部分报告本地 Zotero benchmark lessons；第三部分报告专家团审查和 action items；第四部分报告 candidate benchmark dataset readiness 和 Overath `final_dataset.csv` 字段级审计；第五部分报告 target candidate matrix 与 target_set_v0 仍未冻结；第六部分报告方法到 T1/T2/T3 的任务映射；第七部分报告 runnability audit、source pin audit、environment feasibility audit 和 priority/readiness 分层；第八部分预留未来真实运行后的 parseability、failure_rate、runtime、output completeness、top-k enrichment、calibration error、interface metrics、developability proxies 和 failure cases。

### Paragraph Role: Boundary

在真实 smoke test 和 Benchmark 运行前，任何“方法 A 优于方法 B”的结论都不应写入 Results、Abstract 或 Discussion。可以写“拟评估”“计划记录”“当前工程准备度提示”“metadata-level proxy”，但不能写“已验证”“性能最佳”或“全面优于”。

### Paragraph Role: ARS Review And v0.6 Readiness

v0.6 新增 `ops/audits/academic_research_suite_review_v0.6.md`、`ops/plans/updated_plan_v0.6.md`、`kb/tables/ars_review_action_items_v0.6.csv`、`dataset_supplement_watchlist_v0.6.csv` 和 `server_smoke_test_contract_v0.6.md`。这些材料应写入 planned Results 或 Methods 的 readiness 部分，用于说明本文如何进行研究完整性审查、外部数据 watchlist 管理和服务器执行门槛设计。它们不应写成实验结果、性能排序或复现证据。

### Paragraph Role: v0.7 Dry-Run Contracts

v0.7 进一步将 ARS 评审意见落实为服务器 dry-run 输入合同。PepMLM 与 RFdiffusion + ProteinMPNN 获得方法级 server contract，用于记录 repo pin、外部路径占位、最小 `run.csv` 字段、命令形状、预期输出和 failure states；PepMirror 仅保留 dependency contract，因为 PyRosetta、Vina、OpenMM 和 Zenodo checkpoint 仍未解决。`example_run.csv` 只包含人工 placeholder rows，`download_manifest_template_v0.7.csv` 只包含模板或 placeholder；二者都不得写作真实输入、真实下载或真实结果。

### Paragraph Role: Supervisor-Skills Audit

本轮新增 `ops/audits/supervisor_skills_idea_evaluation.md`、`manuscript/support/benchmark_template_audit.md` 和 `manuscript/support/benchmark_intro_logic_chain.md`。这些材料应写作 manuscript-planning evidence：`idea-evaluator` 给出 Accept with Revisions，指出主要风险是 unverifiable claim 和 scope creep；`benchmark-paper-template` 确认 Research Gap、Evaluation Framework 和 protocol construction 已具备基础，但 Empirical Findings 仍只能写为 planned/readiness findings；`intro-drafter` 仅用于检查 Introduction 逻辑连续性，不替代 Benchmark 六段链。

### Paragraph Role: v0.8 License / Schema / Input-Contract Readiness

v0.8 新增 `benchmark/input_sets/dataset_supplement_schema_review_v0.8.csv`、`benchmark/deployment/method_readiness_review_v0.8.csv`、`benchmark/deployment/download_manifest_v0.8.csv` 和 `ops/audits/license_schema_input_contract_review_v0.8.md`。这些材料可写作 readiness findings：Overath、PEPBI、PepBenchmark、GPCR peptide benchmark、TCRTransBench 和 Chang AF2 ranking cases 已完成不同程度的 license/schema/input-route metadata 审计；PepMLM、RFdiffusion、ProteinMPNN 和 PepMirror 已完成优先级方法的 license/env/checkpoint/input-contract 审计。它们仍不代表数据下载、方法安装、服务器运行、target-set 晋升或性能结果。

### Paragraph Role: v0.9 Plan And Method Landscape Synchronization

v0.9 新增 `ops/plans/updated_plan_v0.9.md` 作为当前权威计划，并将 `manuscript/support/review_draft_benchmark_reference_value.md`、`manuscript/support/review_synthesis_benchmark_framework_supplement.md` 和 `benchmark/method_sources/method_landscape_watchlist_v0.9.csv` 纳入 manuscript-planning evidence。该层用于说明：本稿的 Benchmark 逻辑应同时包含 T1/T2/T3 任务轴和 structure/sequence/function-property 生成范式轴；cyclic、D-peptide 与 ncAA 是横向拓扑/手性/化学约束；review_only 方法只能作为 coverage gap、Related Work 或后续 source/license 审计候选，不能写作新增 include 方法或已运行方法。

## 12. Discussion

### Paragraph Role: Main Interpretation

本文的主要观点是，多肽设计 Benchmark 应先解决任务定义、靶点/对照集、工程可运行性、输出可评估性和评分校准，再讨论性能排序。该观点对近期 AI peptide design 尤其重要，因为 sequence-conditioned、structure-conditioned、full-atom、chirality-aware、cyclic peptide 和 miniprotein binder 方法之间的可比性并不天然成立。

### Paragraph Role: Methodological Contribution

统一 `run.csv`、target set schema、任务分层、failure states 和 independent scoring outputs 可以降低不同方法输出不可比的问题。该框架也为后续 smoke test 提供了最低信息要求：版本、命令、输入、输出、runtime、dependency、license、controls、leakage risk 和 status 都必须记录。

### Paragraph Role: Scientific Boundary

计算评分只能支持候选排序和结构假设，不能替代实验亲和力、实验结构、细胞功能、PK/PD 或 CMC 证据。药物化学可开发性也不能被 binding score 代替；sequence-level proxies 只适合作为 metadata-level 初筛。D-peptide、cyclic peptide 和 miniprotein binder 尤其需要区分可生成性、结构可信度、手性/环化约束、实验可合成性和生物学功能。

### Paragraph Role: Skill-Gated Writing Boundary

Supervisor-Skills 的本轮评估支持继续推进 protocol-first manuscript，但不支持把稿件升级为 completed Benchmark-results paper。`benchmark-paper-template` 要求的 Running Example、Benchmark Comparison Table、pipeline figure 和 Finding-style performance summaries 仍需分阶段处理：前两者可在写作阶段补齐，performance findings 必须等真实服务器运行和结果表存在后再写入。

### Paragraph Role: Limitations And Next Steps

当前限制包括：真实 target set 尚未冻结，候选 benchmark dataset 只有 Overath 完成小文件字段级审计，Overath 行数差异和 blank target rows 需要清洗日志，部分候选方法权重和 license 待确认，部分方法需要 heavy dependency stack，D-peptide 和 cyclic peptide 的评分需要更明确的 stereochemistry-aware validation，affinity/ranking 指标仍需 assay-aware calibration。v0.6 ARS 综合评审进一步指出，新增 GPCR peptide benchmark、PepBenchmark 和 TCRTransBench 等来源只能先进入 watchlist，不能直接补入 frozen target set。v0.7 已建立 server dry-run contracts、artificial example_run 和 download manifest template，但这些仍是 execution planning artifacts，不是方法运行结果。v0.8 完成 license/schema/input-contract readiness 审计，v0.9 完成当前计划与方法地形图同步；二者仍不等同于数据下载、方法安装、target freeze 或 performance findings。下一步应进入 v0.10 server-side preflight package：关闭 PepMLM model-card/license 与 batch wrapper、RFdiffusion + ProteinMPNN checkpoint/contig/handoff、PepMirror PyRosetta license、Overath 清洗计划和 cyclic/ncAA review_only 方法 source/license metadata 审计。

## 13. Methods

### Paragraph Role: Literature Workflow

文献检索与去重基于 Zotero item key、BibTeX key、DOI、PMID、arXiv ID 和 normalized title。Zotero、EndNote 和 upstream PD-wiki 作为 source layer，不直接修改；`E:\Codex_Projects\Pep_design` 作为项目工作层。

### Paragraph Role: Candidate Scoring

候选方法筛选使用 `candidate_method_scorecard.csv`，维度包括 `code_status`、`weights_status`、`inputs_standardizable`、`outputs_evaluable`、`gpu_cost`、`peptide_fit` 和 `recency_evidence`。进入 include set 的方法必须可映射到至少一个 Benchmark task。

### Paragraph Role: Target Set Construction

靶点集使用 `target_set_v0.csv`，每个 target 必须记录 target class、PDB/structure provenance、chain IDs、known binder、negative controls、experimental affinity status、assay type、homology cluster、train leakage risk 和 license。真实 target 冻结前不进入性能声明。

### Paragraph Role: Dataset Candidate Audit

候选数据集审计使用 `candidate_benchmark_datasets.csv`，每个 dataset row 必须记录 source name、DOI/URL、access route、version、record count、data volume、task fit、benchmark track、structure/affinity/control status、license、leakage risk、download policy、recommended use 和 next action。`overath_binder_success_2025` 可在后续作为 ranking/rescoring 与 scoring calibration 的高优先级候选，但在未审计 `final_dataset.csv` 字段、license 和 target overlap 前不能写成已使用 Benchmark 数据。

### Paragraph Role: Expert Panel And Source Pinning

专家团审查使用 `expert_review_action_items.csv`，每条意见必须记录 reviewer role、severity、artifact、issue、recommendation、decision、status、evidence 和 next action。源码 pinning 使用 `source_pin_audit_v0.4.csv`，只记录外部 shallow clone 的 commit 和入口线索；任何 `pinned_no_install` 行都不能写作已安装或已复现。

### Paragraph Role: Server Contract Methods

服务器 dry-run 合同使用 `server_smoke_test_contract_v0.6.md` 和 `benchmark/deployment/method_contracts/`。每个方法合同必须记录 method、task_id、current gate、repo pin、license blocker、外部 source/data/weights/results root 占位、最小输入、命令形状、预期输出和 failure states。合同中的 `current_gate` 不能超过现有证据：PepMLM 与 RFdiffusion + ProteinMPNN 仅可作为 input contract / dry-run planning；PepMirror 仍停留在 dependency/source-pinned 层。

### Paragraph Role: License / Schema / Input-Contract Audit

v0.8 审计使用公开 API、论文 metadata 和既有本地外部 shallow clone 的只读文件，记录数据源 license/schema/controls/leakage/download-route 状态以及方法 license/environment/weights-or-checkpoint/input-contract 状态。`download_manifest_v0.8.csv` 可以包含未来服务器 URL 和 checksum plan，但所有行必须保持 `download_performed=no`，直到服务器端批准下载并生成日志。

### Paragraph Role: Method Landscape And Review-Driven Coverage Audit

v0.9 方法地形图使用 `method_landscape_watchlist_v0.9.csv` 将 include、candidate_watchlist 和 review_only 方法分开记录，并增加 structure/sequence/function-property 生成范式、peptide topology、target conditioning 和 coverage gap 字段。该表用于 Related Work、代表性缺口和后续 source/license 审计优先级，不用于替代 `candidate_method_scorecard.csv`，也不改变 10 个 first-wave include 方法。

### Paragraph Role: Positive And Negative Controls

Positive controls 用于确认评分和 ranking 能否识别已知 binder；negative or decoy controls 用于评估 specificity 和 false-positive 风险。pMHC/TCR-like 任务需要额外记录 HLA allele、peptide antigen、near-neighbour peptide panel 和 cross-reactivity risk。

### Paragraph Role: Leakage And Homology Checks

Protein targets 使用 sequence identity 或 structural similarity cluster，peptide binders 使用 sequence similarity 和 motif overlap。所有 target/reference binder 先记录 `train_leakage_risk=unknown`，只有完成来源核验后才能降为 `low` 或标记为 `medium/high`。

### Paragraph Role: Developability Scoring

Developability 评分当前只记录 metadata-level proxies，包括 length、molecular weight proxy、net charge、hydrophobicity、aromaticity、cysteine/disulfide flags、chirality、cyclic flag、non-natural residue flag、aggregation-risk proxy 和 synthesis complexity flag。实验层可开发性指标留待后续真实数据或文献抽取。

### Paragraph Role: Runnability And Protocol Validation

可运行性审计使用 `method_runnability_matrix.csv`，字段覆盖 repo route、license、weights、install route、batch inference、expected inputs/outputs、scoring compatibility、hardware notes、blocking risks、scientific priority、engineering readiness 和 next action。v0.4 进一步使用 `source_pin_audit_v0.4.csv` 记录源码 pinning，使用 `environment_feasibility_matrix.csv` 记录环境族、关键依赖、许可阻塞和安装风险。项目验证由 `scripts/validate_benchmark_kb.py` 执行，检查 KB、候选方法、expert review rows、dataset readiness rows、target candidate rows、source pin rows、runnability rows、method source rows、environment rows、candidate dataset rows、smoke-test README、Markdown links、target set schema、benchmark lessons 和协议文件。

## 14. Figures And Tables

Figure 1 should show the full Benchmark design overview: literature KB, local Zotero benchmark lessons, expert-panel review, candidate dataset readiness, target candidate matrix, candidate shortlist, target/control design, task mapping, runnability audit, source/environment audit, `run.csv`, method execution, metric CSVs, `merged_run.csv`, and report generation. Figure 2 should show a task-method-target matrix, with method families, target classes, input/output types, chirality/cyclic flags and controls. Figure 3 should show generation versus ranking/rescoring tracks. Figure 4 should show scoring architecture, including confidence, interface, similarity, feasibility, developability, negative design and leakage/homology layers.

Table 1 should summarise the 10 include methods, their primary task, input, output, peptide type and current code/weights status. Table 2 should compress `method_runnability_matrix.csv` into Tier, scientific priority, engineering readiness, blocker and next action. Table 3 should define target classes, positive controls, negative controls, assay evidence and leakage fields. Table 4 should define metric families, applicable tasks and not-applicable reasons. Table 5 should summarise candidate benchmark datasets and readiness decisions. Table 6 should summarise source pinning for PepMLM, RFdiffusion, ProteinMPNN and PepMirror. Extended Data should include expert action items, search query blocks, screening status counts, benchmark literature lessons, target candidates, watchlist methods, method source routes, environment feasibility, and validator output.

## Reverse Outline

| section | single message | evidence source |
|:---|:---|:---|
| Abstract | This is a protocol-first Benchmark framework, not a performance ranking | `ops/validation/wiki_validation_report.md`; `benchmark/protocols/benchmark_protocol_v0.md` |
| Introduction | Peptide-design methods are heterogeneous and require task-aware benchmarking | `kb/tables/method_evidence_matrix.csv`; candidate literature cards |
| Benchmark lessons | Local Zotero scoring and developability papers define calibration boundaries | `manuscript/support/benchmark_literature_lessons.md`; `kb/tables/benchmark_literature_lessons.csv` |
| Expert review | Five expert roles turn protocol weaknesses into action items | `ops/audits/expert_panel_review_v0.4.md`; `kb/tables/expert_review_action_items.csv` |
| Dataset audit | Candidate datasets can support calibration planning but are not frozen target sets | `benchmark/input_sets/candidate_benchmark_datasets.csv`; `ops/audits/dataset_candidate_audit.md` |
| Dataset readiness | Overath is calibration-ready only after cleaning; other datasets remain pending | `benchmark/input_sets/dataset_readiness_scorecard.csv`; `benchmark/input_sets/target_candidate_matrix_v0.4.csv` |
| Literature scope | The KB defines the evidence base and first-wave candidate set | `manuscript/support/literature_scope_report.md`; `manuscript/support/candidate_methods_shortlist.md` |
| Target/control set | Target class, controls, assay evidence and leakage labels are required before performance claims | `benchmark/input_sets/target_set_v0_schema.md`; `benchmark/input_sets/negative_design_panel_schema.md` |
| Task stratification | T1/T2/T3 prevent false comparisons across unlike outputs | `benchmark/protocols/benchmark_protocol_v0.md` |
| Generation protocol | Generation evaluates parseability and task compatibility | `benchmark/protocols/run_csv_schema.md`; `benchmark/protocols/benchmark_protocol_v0.md` |
| Ranking protocol | Ranking/rescoring evaluates prioritisation and calibration, not generation ability | `manuscript/support/benchmark_literature_lessons.md`; `benchmark/scoring/scoring_protocol_v0.md` |
| Runnability audit | Tiering schedules smoke tests while priority/readiness separates science and engineering | `ops/audits/method_runnability_audit.md`; `kb/tables/method_runnability_matrix.csv` |
| Source pinning | Source pins record commit and route only, not installation or reproducibility | `benchmark/method_sources/source_pin_audit_v0.4.csv` |
| Scoring framework | Metrics must be applied only when output type supports them | `benchmark/scoring/scoring_protocol_v0.md`; `benchmark/protocols/scoring_outputs_schema.md` |
| Leakage control | Unknown leakage risk cannot support independent-test wording | `benchmark/protocols/benchmark_protocol_v0.md`; `benchmark/input_sets/target_set_v0_schema.md` |
| Discussion | Computational metrics and metadata proxies do not replace experimental validation | claim-evidence map and scoring boundaries |

## Candidate Citation Bank

| role | suggested citation keys |
|:---|:---|
| sequence peptide design | `chen_target_2025`, `brixi_saltpeppr_2023` |
| structure/miniprotein binder design | `bennett_improving_2023`, `dauparas_robust_2022`, `pacesa_bindcraft_2024`, `pacesa_one-shot_2025` |
| D-peptide and chirality-aware design | `yang_cross-chirality_2026`, `guerin_dexdesign_2024`, `valiente_computational_2021`, `shen_discovery_2023` |
| cyclic/macrocyclic peptide design | `rettie_cyclic_2023`, `watson_pr_macrocyclic_2023`, `pingitore_v_delocalized_2024`, `rettie_accurate_2025` |
| pMHC/TCR-like and application boundary | `johansen_novo-designed_2025`, `householder_novo_2025`, `white_wl_design_2026` |
| ranking and affinity prediction | `chang_ranking_2023`, `romero-molina_ppi-affinity_2022`, `jin_tpeppro_2024`, `sun_deep_2024`, `yin_leveraging_2024` |
| developability and macrocycle boundary | `oeller_sequence-based_2023`, `pingitore_v_delocalized_2024`, `rettie_accurate_2025` |
| scoring and engineering reference | de_novo_binder_scoring project README and example workflow |
| dataset and scoring calibration candidates | `overath_binder_success_2025`, `junker_assessment_2026`, `chang_ranking_2023`, `romero-molina_ppi-affinity_2022` |

## Self-Review Checklist

| dimension | current status | action before full manuscript |
|:---|:---|:---|
| contribution | Framework contribution is clear | Keep title and abstract protocol-first |
| writing clarity | Section roles are explicit | Convert outline to paragraph prose in next drafting phase |
| experimental strength | No experimental results claimed | Add real smoke-test results only after running methods |
| target-set strength | Target/control schema exists, but real targets are not frozen | Select targets only after provenance, assay and leakage checks |
| ranking/generation split | Protocol separates generation and ranking/rescoring | Keep metrics separated in future Results |
| developability | Metadata-level proxies are defined | Do not add experimental developability values without source data |
| evaluation completeness | Scoring categories, failure states and leakage fields are defined | Add environment and version metadata after smoke-test planning |
| method design soundness | Interfaces align with project schemas | Keep validator updated when manuscript files change |
