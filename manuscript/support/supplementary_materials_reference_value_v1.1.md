# v1.1 补充资料对 Benchmark 框架的参考价值评估

## Material Passport

| field | value |
|:---|:---|
| project | Pep_design Benchmark KB |
| version layer | v1.1 supplementary-source synthesis |
| date | 2026-06-18 |
| source handling | 6 份 `G:\Downloads\Markdown笔记` Markdown 文件只读评估 |
| output role | source discovery / framing / protocol refinement |
| boundary | 不修改外部笔记；不替代 Zotero/BibTeX/原始论文核验；不下载数据；不 clone 源码；不升级 include 方法；不冻结 `target_set_v0.csv` |

## Executive Assessment

这 6 份补充材料整体具有较高的框架补强价值，但证据等级不同。最可直接转化为项目协议的是短肽对接评分笔记，因为它给出了“为什么不能只看 docking score”的可操作评估维度。环肽 JMC 综述和环肽 AI 方法综述对 cyclic peptide、macrocycle、D-peptide、ncAA、全原子表示和多目标 developability 的分类价值较高。CAS Insights 更适合作为药物化学背景、治疗方向和 target direction 线索。流匹配文章适合作为生成模型范式背景，不可作为具体 peptide 方法可运行证据。

本轮建议把这些材料吸收到四个层面：

1. `scoring rationale`：补充短肽姿态、方向、关键残基、构象合理性和可比性边界。
2. `cyclic / D / ncAA protocol`：补充环化类型、手性、修饰、表示方法和 developability proxy。
3. `method landscape patch`：增加 cyclic/flow/ncAA 方法线索，但维持 review-only/watchlist 状态。
4. `manuscript claim gate`：强调 source notes 是线索，不是 primary-source verified evidence。

## Source-Level Evaluation

| source | value | direct project use | evidence boundary |
|:---|:---|:---|:---|
| `蛋白-短肽对接，为什么不能只看分数.md` | 高 | 更新评分协议、写作边界、interface/pose quality checklist | 只支持 docking/scoring rationale，不支持 affinity 或稳定结合结论 |
| `王梁多肽综述草稿.md` | 高，已部分吸收 | 继续支持 structure/sequence/function 三分法与 cyclic/D/ncAA 横向约束 | 已有 v0.9 综合报告，避免重复新增相同结论 |
| `JMC2025_cyclic...md` | 高 | 补充 cyclic peptide 数据库、结构预测、template/de novo design、developability 和非天然残基边界 | 需核验原始 JMC 论文、引用和表格，不直接作为本项目结果 |
| `CAS_Insights...环肽...md` | 中 | 补充药物化学背景、环化类型、修饰、治疗方向和 target direction | 行业/数据库洞见，只作背景和候选方向，不作 benchmark 数据 |
| `从蛋白质设计到单细胞模拟，流匹配...md` | 中 | 解释 flow matching 范式，提示 PPFlow、D-Flow、PepFlow 等方法路线 | 不能作为源码可运行、权重可得或 peptide 任务适配证据 |
| `环肽设计AI方法综述...md` | 中高 | 补充 AfCycDesign、RFpeptides、CyclicMPNN、PocketXMol、BoltzGen 等线索 | 方法性能描述需降级为待核验文献线索 |

## What Should Be Borrowed

### 1. 短肽对接评分不能简化为单一分数

短肽柔性高、长度和电荷差异大，docking score 容易受到接触面积、静电项和搜索空间影响。应把评分拆成至少六个检查层：

- binding region 是否符合研究目的；
- N/C 端方向和 P/S 位点或 motif 方向是否合理；
- 关键残基是否进入对应 pocket 或 interface hotspot；
- 构象是否存在过度弯折、无锚定贴附或侧链挤压；
- 不同长度、净电荷和结构来源的 peptide 是否具备可比性；
- 若要声称稳定性，需要 MD、自由能或实验数据，不可只凭 docking pose。

### 2. 环肽需要 topology-aware evaluation

环肽不能只用 `cyclic=yes` 粗略处理。协议层需要至少记录：

- head-to-tail、head-to-sidechain、sidechain-to-tail、sidechain-to-sidechain、disulfide、thioether、mixed/multicyclic；
- macrocycle、bicyclic、polycyclic 与小环肽类别；
- D/L/mixed chirality；
- N-methylation、lipidation、glycosylation、PEGylation、ncAA 或 backbone modification；
- 表示方式是否可被方法和 parser 支持，例如 HELM、CHUCKLES 或 method-specific encoding。

### 3. Developability 应独立于 binding score

JMC/CAS/综述类材料一致提示，治疗性多肽尤其环肽需要关注 permeability、protease stability、metabolic stability、solubility、aggregation、hemolysis、immunogenicity 和 synthesis complexity。当前项目只能做 metadata-level proxy，不能伪造实验可开发性数据。

### 4. Flow matching 是方法范式，不是可运行性证据

流匹配资料可支持 Introduction 或 Related Work 中解释连续生成路径、采样效率和几何约束建模，但不能替代具体方法的 repo、license、weights、input contract 或 smoke-test evidence。PPFlow、D-Flow、PepFlow 等条目必须分开记录，不能因同属 flow matching 而合并。

### 5. 新方法线索只进入 patch/watchlist

RFpeptides、CyclicMPNN、PPFlow、PepMimic、PocketXMol、BoltzGen、PepINVENT、HELM-GPT 等方法可补充方法地形图，但本轮不改变 10 个 include 方法。任何升级必须后续走 source pin、license、weights、input contract、runnability 和 scorecard 更新流程。

## What Must Not Be Borrowed

- 不把公众号/笔记中的性能数字写成本项目结果。
- 不把 CAS/JMC 表格中的 target 或药物方向直接写入 `target_set_v0.csv`。
- 不把 review-only 方法写成已纳入 Benchmark。
- 不把 docking score、AF2 confidence、Rosetta score 或 developability proxy 写成实验 affinity 或 clinical developability。
- 不把 flow matching 综述写成 PPFlow、D-Flow 或 PepFlow 已可运行的证据。

## Implementation Mapping

| project layer | v1.1 update |
|:---|:---|
| scoring protocol | 增加 `short_peptide_pose_quality` 和 docking-score 限制说明 |
| test design | 在 generation/ranking track 中明确 pose plausibility 和 metric comparability |
| method landscape | 增加 patch-candidate 表，不改变 include scorecard |
| manuscript outlines | 中英文同步加入 v1.1 claim boundary |
| claim-evidence map | 增加 source notes、docking score、cyclic topology、flow matching 和 patch candidate 的边界 |
| validator | 检查 6 份来源均被记录；新增方法不得标为 `included`；新增资料不得产生复现或性能断言 |

## Claim Boundary

| claim type | allowed wording | forbidden wording |
|:---|:---|:---|
| source notes | “补充资料提示/支持本项目补强某类协议边界” | “补充资料证明某方法性能或可运行性” |
| docking score | “docking score 只能作为初筛线索，需要姿态和机制检查” | “docking score 证明短肽稳定结合或活性最强” |
| cyclic peptide | “环肽需要 topology-aware 与 developability-aware 评估” | “当前 Benchmark 已覆盖全部环肽化学空间” |
| flow matching | “流匹配是相关生成范式背景” | “流匹配方法已在本项目跑通” |
| patch methods | “新增方法为 review-only/patch candidate” | “新增方法已进入 include set 或已复现” |

## Next Actions

1. 用 `kb/tables/supplementary_materials_action_matrix_v1.1.csv` 逐条跟踪 6 份材料。
2. 用 `kb/tables/scoring_metric_rationale_matrix_v1.1.csv` 固化短肽评分和环肽可开发性指标理由。
3. 用 `kb/tables/method_landscape_patch_candidates_v1.1.csv` 记录新增方法线索，保持非 include 状态。
4. 更新中英文大纲、TODO 和 claim map，所有强结论维持 planned / needs verification。
5. 后续若要正式引用 JMC/CAS/公众号提到的具体论文或数据，必须先走 citation-management 与 primary-source verification。
