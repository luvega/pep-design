---
type: "review_outline"
title: "AI驱动的多肽从头设计工具与方法研究进展"
sources:
  - "reports/review_peptide_methods_corpus.csv"
  - "reports/review_peptide_methods_evidence_table.csv"
---

# AI驱动的多肽从头设计工具与方法研究进展：详细中文提纲

Generated: 2026-05-30T21:47:38

## 写作边界

- 本综述聚焦线性肽、约束肽、D-肽、宏环肽、肽结合模块和pMHC/TCR-like识别模块的从头设计工具与方法。
- RFdiffusion、BindCraft、ProteinMPNN、LigandMPNN等蛋白设计工具只作为方法来源或对照，不扩展为泛protein binder应用综述。
- Benchmark和候选合成只在方法评价与展望中讨论，不作为本阶段独立研究计划。

## 章节设计

### 1. 引言

核心论点：多肽和肽样分子位于小分子与蛋白药物之间，AI从头设计的价值在于把构象采样、靶点界面约束和实验筛选闭环整合起来。
关键引用：@rodriguez_structural_2023; @wu_k_novo_2023; @chang_blocking_2015; @yin_rational_2021; @tseng_structure-guided_2024; @rettie_accurate_2025; @chen_design_2024; @shen_discovery_2023; @bhardwaj_g_accurate_2022; @kong_full-atom_2025; @hanna_s_novo_2026; @zhai_blocking_2021; @valiente_computational_2021; @pingitore_v_delocalized_2024; @brixi_saltpeppr_2023; @hosseinzadeh_p_anchor_2021; @hu_design_2023; @mulligan_vk_computationally_2021; @yao_s_novo_2022; @junker_assessment_2026; @li_design_2025; @gupta_design_2022
待核验事实：多肽药物优势和限制应引用原始研究或权威综述；本文核心事实必须优先回到Core60原始论文。

### 2. 对象与任务定义

核心论点：多肽从头设计不是单一任务，应区分序列生成、结构条件生成、靶点条件binder设计、宏环/手性/二硫键约束设计以及pMHC识别设计。
关键引用：@johansen_novo-designed_2025; @householder_novo_2025; @rodriguez_structural_2023; @wu_k_novo_2023; @liu_design_2025; @chang_blocking_2015; @white_wl_design_2026; @zhai_novel_2020; @rettie_accurate_2025; @chen_design_2024; @shen_discovery_2023; @bhardwaj_g_accurate_2022; @kong_full-atom_2025; @hanna_s_novo_2026; @zhai_blocking_2021; @valiente_computational_2021; @pingitore_v_delocalized_2024; @brixi_saltpeppr_2023; @du_targeting_2025; @hosseinzadeh_p_anchor_2021; @kacen_post-translational_2023; @mulligan_vk_computationally_2021; @yao_s_novo_2022; @junker_assessment_2026; @li_design_2025; @gupta_design_2022; @pacesa_one-shot_2025; @bennett_improving_2023; @minibinders_minibinders_machine_learning_mpnn_library_selection_sappington_i_improved_2026; @bhat_novo_2025; @peptides_machine_learning_vazquez_torres_s_novo_2024; @chen_target_2025; @dauparas_robust_2022; @watson_novo_2023; @dauparas_atomic_2025
表格建议：表1列出任务类型、输入、输出、代表方法、验证方式。

### 3. 早期结构指导和物理模型方法

核心论文：
- 2021 | Rational Design of Potent Peptide Inhibitors of the PD-1:PD-L1 Interaction for Cancer Immunotherapy | Journal of the American Chemical Society | `yin_rational_2021` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。
- 2024 | Structure-Guided Discovery of PD-1/PD-L1 Interaction Inhibitors: Peptide Design, Screening, and Optimization via Computation-Aided Phage Display Engineering | Journal of Chemical Information and Modeling | `tseng_structure-guided_2024` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。
- 2023 | Design of a novel chimeric peptide via dual blockade of CD47/SIRPα and PD-1/PD-L1 for cancer immunotherapy | Sci China Life Sci | `hu_design_2023` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。

本节写作重点：
- 从方法问题出发组织文献，而不是按年份罗列。
- 每个实验证据需要区分亲和力、结构、细胞功能、动物模型和代码/数据开放性。
- 对preprint或仅有计算验证的工作要降低证据等级。

### 4. 深度学习和生成式模型方法

核心论文：
- 2023 | De novo design of modular peptide-binding proteins by superhelical matching | Nature | `wu_k_novo_2023` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。
- 2024 | Design of target specific peptide inhibitors using generative deep learning and molecular dynamics simulations | Nature Communications | `chen_design_2024` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。
- 2025 | Full-atom peptide design with geometric latent diffusion | Advances in Neural Information Processing Systems | `kong_full-atom_2025` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。
- 2023 | SaLT&PepPr is an interface-predicting language model for designing peptide-guided protein degraders | Communications Biology | `brixi_saltpeppr_2023` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。
- 2026 | Assessment of Generative <em>De Novo</em> Peptide Design Methods for G Protein-Coupled Receptors | bioRxiv | `junker_assessment_2026` | Core60 A层主题核心：Linear and constrained peptide design；用于综述正文主证据。
- 2025 | One-shot design of functional protein binders with BindCraft | Nature | `pacesa_one-shot_2025` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2023 | Improving de novo protein binder design with deep learning. | Nat Commun | `bennett_improving_2023` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2026 | Improved protein binder design using β-pairing targeted RFdiffusion | Nat Commun | `minibinders_minibinders_machine_learning_mpnn_library_selection_sappington_i_improved_2026` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2025 | De novo design of peptide binders to conformationally diverse targets with contrastive language modeling | Science Advances | `bhat_novo_2025` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2024 | De novo design of high-affinity binders of bioactive helical peptides | Nature | `peptides_machine_learning_vazquez_torres_s_novo_2024` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2025 | Target sequence-conditioned design of peptide binders using masked language modeling | Nature Biotechnology | `chen_target_2025` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2022 | Robust deep learning-based protein sequence design using ProteinMPNN | Science | `dauparas_robust_2022` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2023 | De novo design of protein structure and function with RFdiffusion | Nature | `watson_novo_2023` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。
- 2025 | Atomic context-conditioned protein sequence design using LigandMPNN | Nat Methods | `dauparas_atomic_2025` | B层方法背景：用于解释生成式蛋白/多肽设计模型来源或作为方法对照。

本节写作重点：
- 从方法问题出发组织文献，而不是按年份罗列。
- 每个实验证据需要区分亲和力、结构、细胞功能、动物模型和代码/数据开放性。
- 对preprint或仅有计算验证的工作要降低证据等级。

### 5. 宏环肽、D-肽与非天然约束设计

核心论文：
- 2023 | Structural and biological characterization of pAC65, a macrocyclic peptide that blocks PD-L1 with equivalent potency to the FDA-approved antibodies | Molecular Cancer | `rodriguez_structural_2023` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2015 | Blocking of the PD-1/PD-L1 Interaction by a D-Peptide Antagonist for Cancer Immunotherapy | Angewandte Chemie International Edition | `chang_blocking_2015` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2025 | Accurate de novo design of high-affinity protein-binding macrocycles using deep learning. | Nat Chem Biol | `rettie_accurate_2025` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2023 | Discovery of a novel dual-targeting D-peptide to block CD24/Siglec-10 and PD-1/PD-L1 interaction and synergize with radiotherapy for cancer immunotherapy | Journal for ImmunoTherapy of Cancer | `shen_discovery_2023` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2022 | Accurate de novo design of membrane-traversing macrocycles. | Cell | `bhardwaj_g_accurate_2022` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2026 | De novo design of a macrocycle-induced dimerization system for cellular control. | Nat Commun | `hanna_s_novo_2026` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2021 | Blocking of the PD-1/PD-L1 interaction by a novel cyclic peptide inhibitor for cancer immunotherapy | Science China Life Sciences | `zhai_blocking_2021` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2021 | Computational Design of Potent D-Peptide Inhibitors of SARS-CoV-2 | Journal of Medicinal Chemistry | `valiente_computational_2021` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2024 | Delocalized quinolinium-macrocyclic peptides, an atypical chemotype for CNS penetration. | Sci Adv | `pingitore_v_delocalized_2024` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2021 | Anchor extension: a structure-guided approach to design cyclic peptides targeting enzyme active sites | Nat Commun | `hosseinzadeh_p_anchor_2021` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2021 | Computationally designed peptide macrocycle inhibitors of New Delhi metallo-β-lactamase 1 | Proc Natl Acad Sci U S A | `mulligan_vk_computationally_2021` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2022 | De novo design and directed folding of disulfide-bridged peptide heterodimers. | Nat Commun | `yao_s_novo_2022` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2025 | Design of linear and cyclic peptide binders from protein sequence information | Communications Chemistry | `li_design_2025` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。
- 2022 | Design of Protein Segments and Peptides for Binding to Protein Targets | BioDesign Research | `gupta_design_2022` | Core60 A层主题核心：Macrocycle and D-peptide design；用于综述正文主证据。

本节写作重点：
- 从方法问题出发组织文献，而不是按年份罗列。
- 每个实验证据需要区分亲和力、结构、细胞功能、动物模型和代码/数据开放性。
- 对preprint或仅有计算验证的工作要降低证据等级。

### 6. 肽抗原、pMHC和TCR-like识别模块设计

核心论文：
- 2025 | De novo-designed pMHC binders facilitate T cell–mediated cytotoxicity toward cancer cells | Science | `johansen_novo-designed_2025` | Core60 A层主题核心：Peptide-MHC and TCR-like recognition；用于综述正文主证据。
- 2025 | De novo design and structure of a peptide–centric TCR mimic binding module | Science | `householder_novo_2025` | Core60 A层主题核心：Peptide-MHC and TCR-like recognition；用于综述正文主证据。
- 2025 | Design of high-specificity binders for peptide-MHC-I complexes | Science | `liu_design_2025` | Core60 A层主题核心：Peptide-MHC and TCR-like recognition；用于综述正文主证据。
- 2026 | Design of solubly expressed miniaturized SMART MHCs | Proc Natl Acad Sci U S A | `white_wl_design_2026` | Core60 A层主题核心：Peptide-MHC and TCR-like recognition；用于综述正文主证据。
- 2020 | A novel cyclic peptide targeting LAG-3 for cancer immunotherapy by activating antigen-specific CD8(+) T cell responses | Acta Pharm Sin B | `zhai_novel_2020` | Core60 A层主题核心：Peptide-MHC and TCR-like recognition；用于综述正文主证据。
- 2025 | Targeting peptide antigens using a multiallelic MHC I-binding system | Nature Biotechnology | `du_targeting_2025` | Core60 A层主题核心：Peptide-MHC and TCR-like recognition；用于综述正文主证据。
- 2023 | Post-translational modifications reshape the antigenic landscape of the MHC I immunopeptidome in tumors | Nature Biotechnology | `kacen_post-translational_2023` | Core60 A层主题核心：Peptide-MHC and TCR-like recognition；用于综述正文主证据。

本节写作重点：
- 从方法问题出发组织文献，而不是按年份罗列。
- 每个实验证据需要区分亲和力、结构、细胞功能、动物模型和代码/数据开放性。
- 对preprint或仅有计算验证的工作要降低证据等级。

### 7. 实验验证标准与证据强度

核心论点：本节用于综合前文证据，提出仍需解决的方法学问题。
关键引用：@pacesa_one-shot_2025; @bennett_improving_2023; @minibinders_minibinders_machine_learning_mpnn_library_selection_sappington_i_improved_2026; @bhat_novo_2025; @peptides_machine_learning_vazquez_torres_s_novo_2024; @chen_target_2025; @dauparas_robust_2022; @watson_novo_2023; @dauparas_atomic_2025
待核验事实：挑战与展望必须从前文证据推出，不引入未核验的新方向。

### 8. 挑战与展望

核心论点：本节用于综合前文证据，提出仍需解决的方法学问题。
关键引用：@pacesa_one-shot_2025; @bennett_improving_2023; @minibinders_minibinders_machine_learning_mpnn_library_selection_sappington_i_improved_2026; @bhat_novo_2025; @peptides_machine_learning_vazquez_torres_s_novo_2024; @chen_target_2025; @dauparas_robust_2022; @watson_novo_2023; @dauparas_atomic_2025
待核验事实：挑战与展望必须从前文证据推出，不引入未核验的新方向。

## 图表计划

- 图1：多肽从头设计任务谱系，从sequence-only到target-conditioned和macrocycle/full-atom design。
- 图2：方法谱系图，展示Rosetta/结构指导、语言模型、扩散模型、全原子生成和实验筛选闭环。
- 表1：核心文献证据矩阵，对应 `review_peptide_methods_evidence_table.csv`。
- 表2：实验验证标准，包括亲和力、结构、细胞、动物、代码/数据可用性。

## 待人工复核

- 缺少DOI/PMID的文献需要正式投稿前补齐。
- 所有亲和力数值、PDB/EMDB编号和动物实验结论需从原文或数据库逐项核验。
- Zotero未运行时生成的BibTeX条目需打开Zotero后刷新。
