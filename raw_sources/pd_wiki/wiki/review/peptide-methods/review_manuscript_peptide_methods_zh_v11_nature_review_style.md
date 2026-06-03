---
type: "publication_manuscript"
title: "AI 驱动多肽设计的证据、方法经验与成药性评价：从约束肽到宏环肽和肽抗原识别模块"
version: "v11_nature_review_style"
citation_style: "numeric_first_appearance"
generated_at: "2026-06-03T10:13:58"
sources:
  - "wiki/review/peptide-methods/review_manuscript_peptide_methods_zh_v10_evidence_expanded.md"
  - "reports/review_claim_to_reference_map_v10.csv"
  - "reports/review_key_study_examples_v10.csv"
  - "reports/review_recent_primary_research_audit_v11.csv"
  - "https://www.nature.com/articles/s44222-024-00256-4"
scope_note: "方向一：AI 驱动多肽、约束肽、D-肽、宏环肽和 pMHC/TCR-like 识别模块的领域评价文章；不启动独立 Benchmark 或候选合成计划。"
style_note: "按 Nature Reviews 式综述逻辑重建叙事：及时性、客观性、平衡性、批判性、前瞻性和可读性。"
---

# AI 驱动多肽设计的证据、方法经验与成药性评价：从约束肽到宏环肽和肽抗原识别模块

**英文题名**：Evidence, design principles and developability assessment in AI-driven peptide design: from constrained peptides to macrocycles and peptide-antigen recognition modules

**作者**：待补充

**作者单位**：待补充

**通信作者**：待补充

**基金项目**：待补充

## 摘要

多肽、约束肽、D-肽和宏环肽处在小分子药物与蛋白药物之间，既能接触较大的蛋白相互作用界面，又能通过合成化学调节构象、稳定性和组织暴露。近年生成式模型、蛋白基础模型、扩散模型和全原子建模方法进入这一领域，使多肽设计从经验筛选逐步转向条件生成和实验闭环。这个转折点使领域评价成为必要：当前问题已经不只是能否生成候选，而是候选是否具有可解释的作用位点、可复现的设计流程、清楚的实验边界和进入药物开发的证据链。

本文评价 AI 驱动的线性肽、约束肽、D-肽、宏环肽和 pMHC/TCR-like 肽抗原识别模块。我们将代表性研究按设计任务、算法能力、实验体系和成药性评价要求重新组织，而不是按发表时间罗列结果。现有证据提示，镜像展示、结构模板、宏环构象设计、pMHC 识别模块和全原子生成模型分别解决了不同层面的设计问题；这些结果不能被概括为单一的“AI 多肽设计成功”，而应根据亲和力、结构、细胞功能、动物实验、药代/药效学和 CMC 证据分层解释。

本文的核心判断是，AI 多肽设计的下一阶段应从“生成更多候选”转向“建立可评价的设计规则”。这些规则包括功能性表位定义、骨架生成与序列设计拆分、负设计前移、游离态和结合态构象共同建模、候选呈现方式选择，以及未命中候选和实验测试流程报告。读者应谨慎区分体外亲和力、实验结构、细胞功能、动物结果、药代/药效学（PK/PD）和生产工艺、质量控制与规模化制造（CMC）证据；任何一个层级都不能自动替代另一个层级。

未来的可操作里程碑包括：建立覆盖天然与非天然氨基酸的标准化数据集；报告训练集去重、同源控制、候选生成、过滤、合成和测试记录；把血清稳定性、溶解性、通透性、免疫原性和 CMC 风险纳入早期过滤；并在 pMHC/TCR-like 任务中系统处理 HLA 等位型、健康组织表达、抗原丢失和交叉反应。只有当算法、药物化学和实验验证被置于同一证据框架中，AI 多肽设计才可能从案例成功走向可复用的工程学方法。

**关键词**：AI 多肽设计；约束肽；D-肽；宏环肽；pMHC；TCR-like 模块；生成模型；药物化学；成药性评价

## Abstract

Peptides, constrained peptides, D-peptides and macrocycles occupy a design space between small molecules and protein therapeutics. Recent generative models, protein foundation models, diffusion models and full-atom modelling tools have moved peptide discovery from empirical screening towards conditional generation and experimental feedback. This Review evaluates AI-driven design of linear peptides, constrained peptides, D-peptides, macrocycles and pMHC/TCR-like peptide-antigen recognition modules. We organise the field by task, algorithmic capability, experimental evidence and developability requirement. The central message is that the next stage of AI peptide design should move from generating more candidates to establishing reproducible design principles that integrate functional epitope definition, negative design, conformational ensembles, medicinal chemistry and transparent reporting of both active and non-hit candidates.

**Keywords**: AI-driven peptide design; constrained peptide; D-peptide; macrocycle; pMHC; TCR-like module; generative model; medicinal chemistry; developability assessment

## 1 引言

AI 多肽设计已经进入需要系统评价的阶段。过去，多肽候选主要依赖展示筛选、结构启发优化和药物化学迭代；现在，语言模型、扩散模型、全原子生成和统一原子级建模正在同时改变候选分子生成、结构过滤和实验优先级排序 [13,16,18-20,32,37,41,42]。这种变化并不意味着 AI 已经解决多肽药物发现，而是说明领域已积累足够多的近期一手研究，可以比较不同任务、算法和实验体系的真实贡献。按照 Nature Reviews Bioengineering 关于综述写作的建议，一篇有价值的综述应当综合并批判性评价最重要的研究成果，明确领域状态、瓶颈和新的研究机会。

多肽设计是 AI 药物设计的高难测试场，因为它同时考验结构建模、非天然化学、药物化学和实验闭环。线性肽容易合成，却常受构象柔性、蛋白酶降解和体内暴露限制 [3,4,19,29]。约束肽和宏环肽可以降低构象自由度，但环化方式、连接子、溶解性和通透性会改变真实药物行为 [1,18,24-27]。D-肽和混合手性分子可能提高稳定性和正交性，却要求模型处理镜像结构、手性表示和异源力场问题 [2,7,38-40]。pMHC/TCR-like 识别模块则不是游离治疗性多肽，而是用于识别肽抗原-MHC 复合物的蛋白或细胞治疗组件，其风险集中在 HLA 限制、交叉反应和患者覆盖 [8-11,30,31]。

本文的评价角度是：AI 多肽设计的核心瓶颈已经从“能否提出候选”转向“能否建立可复现、可解释、可转化的设计规则”。这一角度有三个含义。第一，算法贡献必须拆成明确模块，例如序列生成、结构条件生成、全原子采样、负设计和候选过滤。第二，代表性案例应被用来提炼可复用经验，而不是被合并为笼统的成功叙述。第三，证据层级必须分开：体外结合、实验结构、细胞功能、动物或药代/药效学（PK/PD）支持以及 CMC 可行性分别回答不同问题。

## 2 领域为何进入可评价阶段

近年研究数量和证据类型已经足以支撑领域评价。v11 文献审计显示，本文 42 条参考文献中有 30 篇可计入 2023-2026 年近年一手研究核心集合，覆盖约束肽、D-肽、宏环肽、pMHC/TCR-like 识别、序列模型、扩散模型、全原子生成和统一原子级生成。这个数量满足 Nature Reviews Bioengineering 建议的“至少 30 篇近 2-3 年相关一手研究论文”的经验标准，但本文仍将 preprint、commentary 和方法背景文献单独标注，以避免把证据等级混在一起 [22,36-38]。

近期工作给出的不是单一类型的证据，而是一组互补证据。Johansen 等用 RFdiffusion、ProteinMPNN、AlphaFold2 过滤、cross-panning 和分子动力学筛选获得 NY-ESO-1/HLA-A*02:01 binder，并报告 BLI、3.8 Å cryo-EM 结构和 IMPAC-T/CAR 细胞杀伤证据 [8]。Householder 等针对同一 NY-ESO-1/HLA-A*02:01 背景设计 peptide-centric TCR mimic，提供 9.5 nM 级 SPR 结合、2.05 Å 晶体结构和 off-target 肽筛查 [9]。这两个案例说明，pMHC 识别模块已经可以进入结构和细胞功能评价；但它们也提示，候选是否可用于患者治疗仍取决于 off-target、HLA 覆盖和真实肿瘤抗原呈递。

宏环和 D-肽方向也在形成可比较的证据链。Rettie 等将深度学习用于高亲和力蛋白结合宏环设计，Bhardwaj 等把宏环设计推进到膜穿越任务，Pingitore 等报道 delocalized quinolinium-macrocyclic peptide 作为中枢神经系统穿透相关 chemotype [18,24,26]。在 D-肽方向，Chang 等通过镜像展示获得 PD-1/PD-L1 D-肽候选，Valiente 等从 ACE2-RBD 结构模板设计 SARS-CoV-2 D-肽，PepMirror 则尝试用 axial feature injection 处理跨手性生成 [2,7,38]。这些研究共同支持 D-肽和宏环肽的可计算设计正在形成可评价的方法体系，但它们的实验深度和临床前证据并不一致。

方法学研究也使领域从案例汇编转向能力评价。PepMLM 和 sequence-information design 说明靶点序列可作为肽 binder 生成条件 [29,32]；PepFlow 和 RFdiffusion3 把全原子或多模态生成推向更精细的结构表示 [37,41]；PocketXMol 将原子级提示用于小分子和肽的统一生成，并在 PD-L1-binding peptide 案例中报告细胞特异性和体内肿瘤靶向 [42]。这些方法扩展了算法空间，但其价值要通过独立靶点、未命中候选、实验命中率和可开发性指标来判断。

## 3 AI 多肽设计任务地图

多肽设计的第一步是明确输出分子类型。线性肽任务通常输出可合成序列和排序结果，主要考验序列模型、界面预测和稳定性优化 [4,16,19,29,32]。约束肽和宏环肽任务需要同时输出序列、环化方式、连接子或三维构象，因此更依赖全原子采样、构象集合和物性过滤 [1,18,24-27,41]。D-肽任务要求模型处理镜像结构和跨手性相互作用，不能把 L-肽模型的性能直接外推到 D-肽 [2,7,38-40]。pMHC/TCR-like 任务则输出识别模块、T cell engager 组件或 CAR/IMPAC-T 构型，其评价核心是 peptide-centric specificity、HLA 背景和交叉反应 [8-11,30,31]。

**图 1. 领域评价路线图。** 建议重绘为四层流程图。第一层为“候选分子生成”，包含序列条件生成、结构条件生成、全原子生成和跨手性生成。第二层为“证据分级”，区分亲和力、实验结构、细胞功能、动物或 PK/PD、CMC。第三层为“可复用方法经验”，列出表位定义、拆分设计、负设计、构象预组织化、候选呈现方式和实验测试流程。第四层为“临床前评价里程碑”，包括标准数据集、可开发性面板、HLA/抗原安全性和开放代码权重。

**图 2. AI 多肽设计任务地图。** 建议按分子类型横向排列：线性肽、约束肽、D-肽、宏环肽、pMHC/TCR-like 模块。纵向列出典型输入、输出、主要算法、必要实验和主要失败模式。该图用于帮助读者区分“生成治疗性肽”和“生成肽抗原识别模块”这两类常被混淆的任务。

**表 1. 代表性研究、证据类型和不可外推范围**

| 任务 | 代表性研究 | 输入与输出 | 关键证据 | 可支持的判断 | 不能外推的结论 |
|---|---|---|---|---|---|
| PD-1/PD-L1 D-肽 | Chang 等 [2] | 镜像 PD-L1 IgV；D-肽候选 | SPR/MST、细胞阻断、CT26 小鼠 | 镜像展示可产生免疫检查点 D-肽候选 | 不能证明所有 D-肽都有通用 PK 优势 |
| SARS-CoV-2 D-肽 | Valiente 等 [7] | ACE2-RBD 结构热点；D-肽 | BLI、Vero 中和、MD | 结构模板和构象筛选可形成 D-肽闭环 | 细胞中和不等于体内保护 |
| pMHC binder | Johansen 等 [8] | NY-ESO-1/HLA-A*02:01；识别模块 | BLI、cryo-EM、IMPAC-T/CAR 杀伤 | AI 可生成 pMHC 识别模块 | 未完成患者覆盖和体内安全性证明 |
| TCR mimic | Householder 等 [9] | NY-ESO-1/HLA-A*02:01；TCR-like 模块 | SPR、2.05 Å 结构、off-target 肽 | 结构可解释 peptide-centric specificity | off-target 面板不能穷尽健康组织风险 |
| 多靶点 pMHC-I | Liu 等 [10] | 11 个 pMHC-I 靶点；binder | BLI、Jurkat、primary T cell、CAR | 多 HLA/多抗原平台化设计可行 | HLA 泛化不是自动解决 |
| SMART MHC | White 等 [11] | MHC-I 槽结构；小型可溶 MHC | 结构、TCR 结合、Jurkat staining | 试剂工程可加速 pMHC/TCR 发现 | 不是治疗性 binder 证据 |
| 高亲和力宏环 | Rettie 等 [18] | 蛋白靶点；宏环 binder | 深度学习设计与实验结合 | 宏环可以进入 AI 生成和实验筛选流程 | 不自动说明通透性或体内暴露 |
| 全原子肽生成 | PepFlow [41] | 受体结构；全原子肽 | benchmark 任务 | 全原子多模态表示是关键算法方向 | 不能替代实验亲和力证据 |
| 跨手性 D-肽 | PepMirror [38] | CD38；D-肽候选 | 5,000 生成、12 合成、1 个 BLI 命中 | 实验测试流程可揭示模型适用范围 | 单靶点 preprint 不能作为通用成功率 |
| 统一原子级生成 | PocketXMol [42] | 原子提示；小分子和肽 | 计算任务、PD-L1 肽细胞/体内证据 | 统一生成可连接模型性能和 peptide probe | 仍需逐靶点可开发性验证 |

## 4 从代表性研究提炼可复用经验

第一条经验是功能性表位优先于靶点名称。PD-1/PD-L1 D-肽研究先把 PD-L1 IgV 结构域转化为镜像筛选靶标，使免疫检查点阻断界面成为可操作的化学靶标 [2]。Johansen 等的 pMHC binder 研究则以 NY-ESO-1 肽中暴露残基作为设计热点，再通过 cross-panning 和分子动力学过滤候选 [8]。这两个案例的共同点是，模型并不是从“PD-L1”或“NY-ESO-1”这样的靶点名称直接得到候选，而是依赖研究者对功能性界面、抗原暴露和实验可达性的定义。表位定义失败时，后续生成再多候选也难以弥补靶点假设错误。

第二条经验是骨架生成、序列设计和正交过滤应拆分报告。BindCraft 和 RFdiffusion 相关研究说明，结构条件 binder 设计通常需要先生成骨架，再进行序列设计和结构预测过滤 [13-15]。在 pMHC binder 研究中，这一流程进一步被扩展为 RFdiffusion 生成、ProteinMPNN 序列化、AlphaFold2/iPAE 过滤、cross-panning、分子动力学和细胞测试 [8]。宏环设计也显示，生成模型输出只是候选筛选流程的起点，后续还需要合成、纯化、亲和力和物性测试 [18,24]。因此，论文应分别报告每个阶段的候选数和淘汰原因，而不是只展示最终命中。

第三条经验是负设计和安全性面板应前移。Householder 等不仅报告 NY-ESO-1/HLA-A*02:01 TCR mimic 的高亲和力和晶体结构，还使用 HLA-A*02:01 肽库预测并验证潜在 off-target 肽 [9]。Liu 等在 11 个 pMHC-I 靶点上测试 off-target 肽、Jurkat reporter、primary T cell 和 CAR 读数，显示不同靶点的背景活化和特异性表现并不相同 [10]。这些研究说明，高亲和力不能自动证明安全窗口；相近肽、健康组织表达和 HLA allotype 背景必须在早期设计阶段进入筛选。

第四条经验是构象预组织化应同时考虑游离态和结合态。SARS-CoV-2 D-肽工作从 ACE2-RBD 结构中提取热点螺旋，利用 D-PDB 搜索和 200 ns 分子动力学筛选稳定候选，再用 BLI 和病毒中和实验验证 [7]。宏环设计同样显示，环化可以减少构象自由度，但连接子、环张力、溶剂暴露和膜通透性会改变真实结合行为 [18,24,26]。因此，构象预组织化不是简单提高亲和力的装饰步骤，而是需要在结合态、游离态和开发场景之间取舍的设计变量。

第五条经验是候选呈现方式决定实验问题和临床前解释。pMHC 识别模块在 IMPAC-T、CAR、T cell engager 或可溶试剂中会面对不同的表达、展示、细胞定位和安全性假设 [8-11,31]。Householder 等把 TCR mimic 接入 T cell engager 和 CAR 构型后，分别得到 reporter、primary T cell 和肿瘤细胞杀伤读数 [9]；peptide mask 研究则通过条件激活设计改变 binder 在不同环境下的活性 [35]。因此，把同一个结合模块换到另一种呈现方式，不是中性的包装步骤，而是会改变实验问题、药效解释和安全性评价路径的设计决策。

第六条经验是未命中候选、合成失败和测试流程是方法证据的一部分。PepMirror 在 CD38 案例中生成 5,000 个 D-肽候选，经过过滤后合成 12 个，最终只有 D-1412 给出约 10 μM 的 BLI 结合证据，其余候选多为弱响应或证据不足 [38]。DexDesign 报告了开放 OSPREY 实现和计算预测流程，但其抽取证据更适合支持算法设计和分析框架，而不是湿实验命中率 [39]。这两个案例共同说明，未命中样本不是噪声，而是判断模型适用范围、过滤策略和实验成本的必要信息。

## 5 现有算法解决了什么，尚未解决什么

现有算法已经明显扩展了候选分子生成和结构假设空间。ProteinMPNN、RFdiffusion 和 BindCraft 等流程使结构条件的骨架生成和序列设计更高效 [13-15]；PepMLM 和 sequence-information design 使靶点序列本身成为肽 binder 生成条件 [29,32]；PepFlow、RFdiffusion3 和 PocketXMol 则把全原子、多模态或统一原子级生成作为新的方向 [37,41,42]。这些方法真正解决的是“如何提出更丰富、更有条件约束的候选”，而不是直接解决“哪些候选可成药”。

算法也开始处理以往依赖专家直觉的复杂变量。DexDesign 把 OSPREY 的 ensemble-based 设计思想用于 D-肽抑制剂，PocketXMol 使用原子提示统一不同 pocket-interacting 任务，PepMirror 通过 axial feature injection 让模型对手性更敏感 [38,39,42]。这些研究提示，非天然手性、侧链构象和任务提示可以被显式建模。但其证据强度并不相同：PocketXMol 包含 PD-L1-binding peptide 的细胞特异性和体内肿瘤靶向证据 [42]，PepMirror 目前更适合说明跨手性算法探索 [38]，DexDesign 主要支持可解释算法框架和开放实现 [39]。

尚未解决的问题集中在理论表示和评价标准。第一，非天然氨基酸、D-氨基酸、N-甲基化、环化连接和混合手性仍缺乏统一的高质量训练数据和力场参数。第二，模型通常生成结合态候选，但游离态构象集合、溶液行为和膜环境仍难预测。第三，负样本和未命中样本经常缺失，使模型无法学习“不应结合什么”或“为什么合成/测试失败”。第四，计算 benchmark 和实验命中率之间仍缺乏稳定对应关系，容易把模型排序能力误读为药物发现能力。

**表 2. 算法已解决的问题与仍待解决的问题**

| 层面 | 已有进展 | 代表性证据 | 仍待解决的问题 |
|---|---|---|---|
| 条件生成 | 可基于序列、结构、热点或原子提示生成候选 | PepMLM、RFdiffusion、PocketXMol [13,32,42] | 条件定义仍依赖人工靶点和表位判断 |
| 结构与序列耦合 | 骨架生成、序列设计和结构预测可形成分阶段筛选流程 | BindCraft、pMHC binder [8,13] | 过滤分数和真实亲和力并不总一致 |
| 全原子表示 | 侧链、骨架和残基类型可联合建模 | PepFlow、RFdiffusion3 [37,41] | 溶剂效应、环化张力和非天然化学仍难统一 |
| 跨手性设计 | 镜像展示、D-PDB、axial features 可用于 D-肽或 D-protein | [2,7,38-40] | D-肽 PK、免疫学和长期安全性不能从模型外推 |
| 负设计 | pMHC 案例已开始系统筛查 off-target 肽 | [9,10,31] | 健康组织表达和患者背景仍难穷尽 |
| 可复现性 | 部分研究报告生成数、合成数和未命中候选 | PepMirror、pMHC binder [8,38] | 领域尚缺统一最低报告规范 |

## 6 证据等级、药物化学和临床前评价

体外亲和力、实验结构、细胞功能和动物结果必须分层解释。Chang 等的 [D]PPA-1 包含结合、细胞阻断和小鼠肿瘤模型证据，因此可作为 D-肽免疫检查点阻断的多层案例 [2]。Valiente 等的 SARS-CoV-2 D-肽提供结构模板、分子动力学、BLI 和 Vero 细胞中和证据，但细胞中和不能替代体内保护或临床安全性 [7]。PepMirror 的 D-1412 目前主要支持跨手性生成和候选测试流程，不应被写成成熟药物候选 [38]。这种分层语言可以防止把“有结合”误写成“具备临床前开发价值”。

结构证据尤其需要严格区分。Householder 等的 2.05 Å 晶体结构可以直接支持 peptide-centric TCR mimic 与 NY-ESO-1/HLA-A*02:01 的具体接触模式 [9]；Johansen 等的 3.8 Å cryo-EM 结构可以支持 NY1-B04 与 pMHC 复合物的结合构象 [8]。相反，Shen 等双靶向 D-肽的强证据主要来自细胞和动物免疫功能，而不是高分辨率结构 [5]。预测结构、对接模型和分子动力学可解释设计假设，但不能替代实验结构。

药物化学可开发性是 AI 多肽设计常被低估的评价维度。血清稳定性（serum stability）说明体液中降解风险；血浆蛋白结合（plasma protein binding）影响游离暴露；溶解性（solubility）和聚集（aggregation）决定配制和体外测试可靠性；平行人工膜通透性实验（PAMPA）和 Caco-2 细胞通透性实验（Caco-2）用于早期通透性判断；微粒体稳定性（microsomal stability）提示代谢风险；溶血（hemolysis）和免疫原性（immunogenicity）关系到安全性；药代/药效学（PK/PD）和生产工艺、质量控制与规模化制造（CMC）决定候选能否进入开发路径 [18,24,26,42]。这些指标目前很少被统一纳入生成模型目标函数。

**图 3. 从计算模型到药物候选的证据阶梯。** 建议重绘为阶梯图。每一级写明问题：计算生成回答“能否提出候选”；亲和力回答“是否结合”；实验结构回答“如何结合”；细胞功能回答“在给定模型中是否产生作用”；动物或 PK/PD 回答“是否有体内暴露和功能”；CMC 回答“是否可稳定、可控、可规模化生产”。箭头旁标注“不可跳级”。

**Box 1. AI 多肽设计论文最低报告规范**

| 项目 | 建议报告内容 |
|---|---|
| 训练数据 | 数据来源、时间范围、去重策略、同源控制 |
| 任务定义 | 靶点、表位、输入类型、输出分子类型、候选呈现方式 |
| 候选流转记录 | 生成数、过滤数、合成数、测试数、命中数 |
| 过滤规则 | 结构预测、界面分数、负设计、物性阈值和人工筛选标准 |
| 实验结果 | 亲和力、结构、细胞、动物、PK/PD 或 CMC 分层报告 |
| 失败信息 | 合成失败、纯化失败、无结合、off-target、细胞毒性 |
| 可复现性 | 代码、模型权重、随机种子、命令、版本和数据划分 |

**Box 2. 药物化学读者需要关注的多肽可开发性指标**

| 中文指标 | 英文术语 | 主要问题 |
|---|---|---|
| 血清稳定性 | serum stability | 多肽是否被血清或蛋白酶快速降解 |
| 血浆蛋白结合 | plasma protein binding | 游离药物暴露和组织分布是否可解释 |
| 溶解性 | solubility | 配制、纯化和体外测试是否可靠 |
| 聚集 | aggregation | 是否影响读数、免疫原性或制剂稳定性 |
| 平行人工膜通透性实验 | PAMPA | 是否具备早期被动通透性线索 |
| Caco-2 细胞通透性实验 | Caco-2 | 是否具备细胞层面通透性和外排线索 |
| 微粒体稳定性 | microsomal stability | 是否存在快速代谢风险 |
| 溶血 | hemolysis | 是否有红细胞膜损伤风险 |
| 免疫原性 | immunogenicity | 是否可能诱发不希望的免疫反应 |
| 药代/药效学 | PK/PD | 体内暴露和功能是否匹配 |
| 生产工艺、质量控制与规模化制造 | CMC | 合成、纯化、放大和质量属性是否可控 |

## 7 pMHC/TCR-like 识别模块作为临床前评价案例

pMHC/TCR-like 方向最能说明“算法命中”和“治疗窗口”之间的距离。Johansen 等表明 de novo pMHC binder 可以被接入 IMPAC-T/CAR 构型并诱导 NY-ESO-1 阳性黑色素瘤细胞杀伤 [8]。Householder 等显示 peptide-centric TCR mimic 可以获得结构解释和 off-target 肽筛查 [9]。Liu 等进一步把任务扩展到 11 个 pMHC-I 复合物和多个 HLA 背景 [10]。这些结果共同支持 pMHC 识别模块进入可设计阶段，但不能说明所有肿瘤抗原都适合 AI binder 开发。

这个方向的主要难点不是生成一个能结合 pMHC 的模块，而是证明它在患者背景下安全有效。Kacen 等的免疫肽组研究显示，翻译后修饰可重塑 HLA-I 肽库，并改变锚定位点或 TCR 识别区域 [30]。Du 等的 TRACeR-I 平台则强调 HLA-A、HLA-B 和 HLA-C 多类 allotype 背景下的患者覆盖问题 [31]。这些研究说明，设计者必须同时处理 HLA 等位型、真实抗原加工呈递、健康组织表达、相近肽、抗原丢失和 off-target alloreactivity。

细胞读数也不能合并为笼统的“细胞验证”。Jurkat reporter 主要回答人工报告系统能否被触发；primary T cell 更接近效应细胞功能；CAR 或 IMPAC-T 组件测试识别模块在特定细胞治疗呈现方式中能否工作；肿瘤细胞杀伤模型进一步加入靶抗原表达、HLA 呈递和效应细胞功能的组合变量 [8-10,31]。因此，pMHC/TCR-like 论文应明确每个读数回答的问题，而不是用一个细胞结果代表全部转化风险。

## 8 工程化和临床转化里程碑

下一阶段算法开发应首先解决数据和表示问题。领域需要覆盖天然氨基酸、D-氨基酸、N-甲基化、环化连接、混合手性和肽-蛋白复合物的标准化数据集。训练集应报告去重、同源控制和与测试靶点的结构相似性，避免把同源泄漏误读为泛化能力。全原子模型需要明确处理侧链、溶剂、环化张力和非天然修饰；跨手性模型则需要解释哪些几何特征真正决定 D/L 相互作用 [38-41]。

工程化评价应从模型输出延伸到实验测试流程。每篇方法论文至少应报告生成数、过滤数、合成数、测试数、命中数和未命中候选。PepMirror 和 pMHC binder 案例显示，这些流程信息可以帮助读者判断模型命中率和筛选损耗 [8,38]。PocketXMol 的统一原子级生成显示模型可连接多种 pocket-interacting 任务，但它也提示，统一模型必须通过具体靶点和具体实验体系验证其适用性 [42]。

转化里程碑应按分子类型制定。线性肽需要优先解决稳定性、暴露和选择性；宏环肽需要同时验证构象、通透性、溶解性和合成放大；D-肽需要独立评估结合模式、代谢、免疫学和长期安全性；pMHC/TCR-like 模块需要建立 HLA 覆盖、健康组织表达、相近肽和抗原丢失面板 [2,7,18,24,30,31,40,42]。这些里程碑不是独立 Benchmark 项目，而是综述评价中用于判断证据强度的共同语言。

临床应用还需要明确场景。免疫检查点调节可借鉴 PD-1/PD-L1、LAG-3 和 CD24/Siglec-10 案例，但必须区分体外阻断、动物模型和人体治疗窗口 [1-6]。感染阻断可借鉴 SARS-CoV-2 D-肽，但病毒变异、给药途径和体内暴露仍需独立验证 [7]。细胞内蛋白互作、酶抑制和肿瘤抗原识别分别需要不同的递送、选择性和安全性标准 [12,25,30,31]。

## 9 结论

AI 多肽设计正在从候选分子生成走向系统评价。近年研究表明，生成模型和结构设计流程可以在特定任务中产生可测结合、结构解释、细胞功能甚至部分动物或体内靶向证据 [2,7-10,18,31,42]。但这些证据不能合并为“AI 多肽设计已经成熟”的单一结论。不同分子类型、候选呈现方式和实验体系回答不同问题，任何跨任务外推都需要谨慎。

本文将当前领域状态概括为三点。第一，算法已经明显扩展了候选分子生成和结构假设空间。第二，可靠设计仍依赖人工定义表位、选择候选呈现方式、设计负样本面板和解释未命中样本。第三，药物化学和临床前评价要求尚未被充分纳入模型训练和评价。下一阶段真正有价值的工作，应当把 AI 技术、专业知识和实验反馈整合成可复现的设计规则，而不是只追求更多模型或更多个例。

## 利益冲突

作者声明无已知利益冲突。正式投稿前应根据目标期刊要求补充完整声明。

## 作者贡献

待补充。建议按构思、文献检索、证据抽取、写作、图表设计和最终审阅分项列出。

## 数据和代码可获得性

本文为综述文章。文献清单、证据审计表、图表计划和修订日志保存在 PD-wiki 项目中；正式投稿前应根据期刊要求决定是否公开这些辅助材料。

## 参考文献

[1] Rodriguez I.; Kocik-Krol J.; Skalniak L., et al. Structural and biological characterization of pAC65, a macrocyclic peptide that blocks PD-L1 with equivalent potency to the FDA-approved antibodies[J]. Molecular Cancer, 2023. DOI: 10.1186/s12943-023-01853-4.

[2] Chang H.; Liu B.; Qi Y., et al. Blocking of the PD-1/PD-L1 Interaction by a D-Peptide Antagonist for Cancer Immunotherapy[J]. Angewandte Chemie International Edition, 2015. DOI: 10.1002/anie.201506225.

[3] Yin H.; Zhou X.; Huang Y., et al. Rational Design of Potent Peptide Inhibitors of the PD-1:PD-L1 Interaction for Cancer Immunotherapy[J]. Journal of the American Chemical Society, 2021. DOI: 10.1021/jacs.1c08132.

[4] Tseng T.; Lee C.; Chen P., et al. Structure-Guided Discovery of PD-1/PD-L1 Interaction Inhibitors: Peptide Design, Screening, and Optimization via Computation-Aided Phage Display Engineering[J]. Journal of Chemical Information and Modeling, 2024. DOI: 10.1021/acs.jcim.3c01500.

[5] Shen W.; Shi P.; Dong Q., et al. Discovery of a novel dual-targeting D-peptide to block CD24/Siglec-10 and PD-1/PD-L1 interaction and synergize with radiotherapy for cancer immunotherapy[J]. Journal for ImmunoTherapy of Cancer, 2023. DOI: 10.1136/jitc-2023-007068.

[6] Zhai W.; Zhou X.; Wang H., et al. A novel cyclic peptide targeting LAG-3 for cancer immunotherapy by activating antigen-specific CD8+ T cell responses[J]. Acta Pharmaceutica Sinica B, 2020. DOI: 10.1016/j.apsb.2020.01.005.

[7] Valiente P. A.; Wen H.; Nim S., et al. Computational Design of Potent D-Peptide Inhibitors of SARS-CoV-2[J]. Journal of Medicinal Chemistry, 2021. DOI: 10.1021/acs.jmedchem.1c00655.

[8] Johansen K. H.; Wolff D. S.; Scapolo B., et al. De novo-designed pMHC binders facilitate T cell–mediated cytotoxicity toward cancer cells[J]. Science, 2025. DOI: 10.1126/science.adv0422.

[9] Householder K. D.; Xiang X.; Jude K. M., et al. De novo design and structure of a peptide–centric TCR mimic binding module[J]. Science, 2025. DOI: 10.1126/science.adv3813.

[10] Liu B.; Greenwood N. F.; Bonzanini J. E., et al. Design of high-specificity binders for peptide–MHC-I complexes[J]. Science, 2025. DOI: 10.1126/science.adv0185.

[11] White WL; Bai H; Kim CJ, et al. Design of solubly expressed miniaturized SMART MHCs[J]. Proc Natl Acad Sci U S A, 2026. DOI: 10.1073/pnas.2505932123.

[12] Hosseinzadeh P; Watson PR; Craven TW, et al. Anchor extension: a structure-guided approach to design cyclic peptides targeting enzyme active sites[J]. Nat Commun, 2021. DOI: 10.1038/s41467-021-23609-8.

[13] Pacesa M.; Nickel L.; Schellhaas C., et al. One-shot design of functional protein binders with BindCraft[J]. Nature, 2025. DOI: 10.1038/s41586-025-09429-6.

[14] Bennett N. R.; Coventry B.; Goreshnik I., et al. Improving de novo protein binder design with deep learning[J]. Nature Communications, 2023. DOI: 10.1038/s41467-023-38328-5.

[15] Minibinders Minibinders Machine Learning MPNN Library Selection Sappington I; Toul M; Lee DS, et al. Improved protein binder design using β-pairing targeted RFdiffusion[J]. Nat Commun, 2026. DOI: 10.1038/s41467-025-67866-3.

[16] Bhat S.; Palepu K.; Hong L., et al. De novo design of peptide binders to conformationally diverse targets with contrastive language modeling[J]. Science Advances, 2025. DOI: 10.1126/sciadv.adr8638.

[17] Peptides Machine Learning Vázquez Torres S; Leung PJY; Venkatesh P, et al. De novo design of high-affinity binders of bioactive helical peptides[J]. Nature, 2024. DOI: 10.1038/s41586-023-06953-1.

[18] Rettie S. A.; Juergens D.; Adebomi V., et al. Accurate de novo design of high-affinity protein-binding macrocycles using deep learning[J]. Nature Chemical Biology, 2025. DOI: 10.1038/s41589-025-01929-w.

[19] Chen S.; Lin T.; Basu R., et al. Design of target specific peptide inhibitors using generative deep learning and molecular dynamics simulations[J]. Nature Communications, 2024. DOI: 10.1038/s41467-024-45766-2.

[20] Kong X.; Jia Y.; Huang W., et al. Full-atom peptide design with geometric latent diffusion[J]. Advances in Neural Information Processing Systems, 2025.

[21] Brixi G.; Ye T.; Hong L., et al. SaLT&PepPr is an interface-predicting language model for designing peptide-guided protein degraders[J]. Communications Biology, 2023. DOI: 10.1038/s42003-023-05464-z.

[22] Junker H.; Schoeder C. T.. Assessment of Generative De Novo Peptide Design Methods for G Protein-Coupled Receptors[J]. bioRxiv, 2026. DOI: 10.64898/2026.02.26.708415.

[23] Wu K; Bai H; Chang YT, et al. De novo design of modular peptide-binding proteins by superhelical matching[J]. Nature, 2023. DOI: 10.1038/s41586-023-05909-9.

[24] Bhardwaj G; O'Connor J; Rettie S, et al. Accurate de novo design of membrane-traversing macrocycles[J]. Cell, 2022. DOI: 10.1016/j.cell.2022.07.019.

[25] Mulligan VK; Workman S; Sun T, et al. Computationally designed peptide macrocycle inhibitors of New Delhi metallo-β-lactamase 1[J]. Proc Natl Acad Sci U S A, 2021. DOI: 10.1073/pnas.2012800118.

[26] Pingitore V; Pancholi J; Hornsby TW, et al. Delocalized quinolinium-macrocyclic peptides, an atypical chemotype for CNS penetration[J]. Sci Adv, 2024. DOI: 10.1126/sciadv.ado3501.

[27] Hanna S; Salveson PJ; Wicky B, et al. De novo design of a macrocycle-induced dimerization system for cellular control[J]. Nat Commun, 2026. DOI: 10.1038/s41467-026-71345-8.

[28] Yao S; Moyer A; Zheng Y, et al. De novo design and directed folding of disulfide-bridged peptide heterodimers[J]. Nat Commun, 2022. DOI: 10.1038/s41467-022-29210-x.

[29] Li Q.; Vlachos E. N.; Bryant P.. Design of linear and cyclic peptide binders from protein sequence information[J]. Communications Chemistry, 2025. DOI: 10.1038/s42004-025-01601-3.

[30] Kacen A.; Javitt A.; Kramer M. P., et al. Post-translational modifications reshape the antigenic landscape of the MHC I immunopeptidome in tumors[J]. Nature Biotechnology, 2023. DOI: 10.1038/s41587-022-01464-2.

[31] Du H.; Mallik L.; Hwang D., et al. Targeting peptide antigens using a multiallelic MHC I-binding system[J]. Nature Biotechnology, 2025. DOI: 10.1038/s41587-024-02505-8.

[32] Chen L. T.; Quinn Z.; Dumas M., et al. Target sequence-conditioned design of peptide binders using masked language modeling[J]. Nature Biotechnology, 2025. DOI: 10.1038/s41587-025-02761-2.

[33] Muratspahic E.; Kim D.; Feldman D., et al. De novo design of miniproteins targeting GPCRs[J]. Nature, 2026. DOI: 10.1038/s41586-026-10656-8.

[34] Liu C.; Wu K.; Choi H., et al. Diffusing protein binders to intrinsically disordered proteins[J]. Nature, 2025. DOI: 10.1038/s41586-025-09248-9.

[35] Escobar-Rosales M.; Montaner C.; Expòsit M., et al. Design of Peptide Masks Enables Rapid Generation of Conditionally-Active Miniprotein Binders[J]. Journal of the American Chemical Society, 2025. DOI: 10.1021/jacs.5c16108.

[36] Liu H. Designing de novo D-protein binders[J]. Cell Research, 2024. DOI: 10.1038/s41422-024-01029-9.

[37] Butcher J.; Krishna R.; Mitra R., et al. De novo Design of All-atom Biomolecular Interactions with RFdiffusion3[J]. bioRxiv, 2025. DOI: 10.1101/2025.09.18.676967.

[38] Yang Z.; Tian Z.; Jia Y., et al. Cross-Chirality Generalization by Axial Vectors for Hetero-Chiral Protein-Peptide Interaction Design[J/OL]. arXiv, 2026. DOI: 10.48550/arXiv.2602.20176.

[39] Guerin N.; Childs H.; Zhou P.; Donald B. R. DexDesign: an OSPREY-based algorithm for designing de novo D-peptide inhibitors[J]. Protein Engineering, Design and Selection, 2024. DOI: 10.1093/protein/gzae007.

[40] Sun K.; Li S.; Zheng B.; Zhu Y.; Wang T.; Liang M.; Yao Y.; Zhang K.; Zhang J.; Li H.; Han D.; Zheng J.; Coventry B.; Cao L.; Baker D.; Liu L.; Lu P. Accurate de novo design of heterochiral protein-protein interactions[J]. Cell Research, 2024. DOI: 10.1038/s41422-024-01014-2.

[41] Li J.; Cheng C.; Wu Z.; Guo R.; Luo S.; Ren Z.; Peng J.; Ma J. Full-atom peptide design based on multi-modal flow matching[J]. Proceedings of the 41st International Conference on Machine Learning, 2024. DOI/PMID: 待补充；已由 PD-wiki PDF/Markdown 记录追踪.

[42] Peng X.; Guo R.; Guo F.; Wang Z.; Sun J.; Guan J.; Jia Y.; Xu Y.; Huang Y.; Zhang M.; Peng J.; Wang X.; Han C.; Wang Z.; Ma J. Unified modeling of 3D molecular generation via atomic interactions with PocketXMol[J]. Cell, 2026. DOI: 10.1016/j.cell.2026.01.003.
