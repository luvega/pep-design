# 综述综合：对 Benchmark 框架的补充与完善

## Material Passport

| field | value |
|:---|:---|
| source draft | `G:\Downloads\Markdown笔记\王梁多肽综述草稿.md` (read-only) |
| upstream assessment | [`reports/review_draft_benchmark_reference_value.md`](review_draft_benchmark_reference_value.md) |
| synthesis date | 2026-06-11 |
| project | Pep_design Benchmark KB |
| skill route | `academic-research-suite` (deep-research 综合视角) + `benchmark-paper-template` |
| deliverable | 把综述的方法学综合转成可审计的 Benchmark 框架补充：生成范式分类轴、方法覆盖图、横向约束矩阵、代表性缺口 |
| new artifact | [`benchmarks/method_sources/method_landscape_watchlist_v0.9.csv`](../benchmarks/method_sources/method_landscape_watchlist_v0.9.csv) |
| boundary | 不修改外部草稿；不写入 `target_set_v0.csv`；不新增 include 方法（仍维持 5-10）；不声称任何方法已安装/运行/复现/性能更优；不下载数据或权重 |

## 1. 综合定位

上游报告 [`review_draft_benchmark_reference_value.md`](review_draft_benchmark_reference_value.md) 已完成对该综述的只读价值评估，结论是“中高参考价值，集中在背景框架与任务代表性论证”。本报告在此基础上前进一步：把综述的方法学骨架转化为**对 Benchmark 框架的具体补充**，但严格保持在 protocol/planning 层，不触及执行层证据。

综述提供三类可直接增强本项目框架的结构化内容：

1. 一个清晰的**生成范式三分法**（structure-driven / sequence-driven / function-property-driven），本项目此前只有 T1/T2/T3 任务轴，缺少与之正交的范式轴。
2. 一份比本项目候选池更宽的**方法地形图**（约 22 个方法），可用于显式标注覆盖与缺口。
3. 对 cyclic / D-peptide / ncAA 的**横向拓扑与手性约束**讨论，可细化 `run.csv` 已有的 `cyclic`/`chirality`/`peptide_type` 字段语义与评分适用边界。

## 2. 生成范式分类轴（与任务轴正交）

综述的三类范式与本项目 T1/T2/T3 任务并不重合：任务轴描述“输入/输出形态”，范式轴描述“条件化与优化机制”。建议把范式作为方法的第二分类维度记录。

| 范式 | 条件化核心 | 综述代表方法 | 本项目对应 | 主要 Benchmark 含义 |
|:---|:---|:---|:---|:---|
| structure-driven | 以靶点 3D 结构/口袋为条件 | EvoBind, PPFlow, RFpeptides, DiffPepBuilder, PepGLAD, PepMimic | DiffPepBuilder, PepGLAD, AfCycDesign, D-Flow, PepMirror, DexDesign（T2）；RFdiffusion+ProteinMPNN, BindCraft（T3） | 需要结构/界面指标（DockQ、iRMSD、interface geometry）与 pocket/chain 约定 |
| sequence-driven | 仅以靶点序列为条件（pLM 先验） | EvoPlay, moPPIt, PepMLM, EvoBind2 | PepMLM, SaLT&PepPr（T1） | 结构指标默认 `not_applicable`，可选下游结构预测层；需警惕“结合到非功能区” |
| function/property-driven | 以多属性/界面相似性为优化目标 | EvoPlay, PepTune, PepMimic, HELM-GPT | 目前无专门 include 方法；映射到 developability / ranking-rescoring 评分层 | 支撑“binding score ≠ developability”的独立评分轴 |

边界：范式标签用于方法理解与分层呈现，不得据此对方法做公平性能排名；同一方法可同时落入多个范式（如 PepMimic 兼具 structure 与 function 视角）。

## 3. 方法覆盖图与缺口

完整覆盖映射见 [`method_landscape_watchlist_v0.9.csv`](../benchmarks/method_sources/method_landscape_watchlist_v0.9.csv)。要点如下。

### 3.1 已覆盖（在候选打分卡内）
PepMLM、SaLT&PepPr、DiffPepBuilder、PepGLAD、D-Flow、PepMirror、AfCycDesign/ColabDesign、DexDesign/OSPREY3、RFdiffusion+ProteinMPNN、BindCraft 共 10 个 include 方法，已覆盖 sequence-driven、structure-driven 与 D-peptide/cyclic 的主线。PepFlow、BoltzDesign1 维持打分卡 watchlist。

### 3.2 综述涉及但项目尚未纳入（review_only）
- **结构/序列主线补充**：PPFlow、RFpeptides、PepMimic、moPPIt、EvoBind2（及更早的 EvoBind、EvoPlay 作为背景）。
- **cyclic 专项缺口**：CpSDE（AtomSDE+ResRouter）、CP-Composer——本项目 cyclic 目前主要靠 AfCycDesign/RFpeptides 间接覆盖，缺少“模板无关、化学显式”的 cyclic 生成代表。
- **ncAA/其他非天然肽缺口**：PepINVENT、HELM-GPT、NCFlow——本项目几乎没有 ncAA 表示与生成的方法代表。
- **多目标/可成药性缺口**：PepTune、HELM-GPT——可启发 developability/多目标评分轴设计。
- **打分/重排相关**：EV-PLIG（亲和力+ATM 自由能双评分）——与 ranking-rescoring track 相关，但草稿描述含糊，需核对原始来源。

### 3.3 需要消歧的命名风险
- **PepMimic ≠ PepMirror**：本项目候选池含 PepMirror（D-peptide，AFI/E(3) 手性感知），综述同时讨论 PepMimic（Kong 等，界面拟态 latent diffusion）。两者不同，不可混用。
- **PPFlow ≠ PepFlow**：打分卡 watchlist 的 PepFlow（multi-modal flow matching）与综述的 PPFlow（torsional flow matching）是不同方法，需分别记录。

边界：上述 review_only 方法均维持 `review_only` 状态，不进入 `candidate_method_scorecard.csv` 的 include 集合（受 5-10 上限与既有 runnability/source/license 证据约束）；纳入与否仍以本项目 scorecard、runnability audit 与 source/license 证据为准。

## 4. 横向拓扑与手性约束矩阵

综述把 cyclic / D-peptide / ncAA 处理为需要独立建模的拓扑约束。建议在 `run.csv`（已含 `peptide_type`/`chirality`/`cyclic`）与 scoring 层显式记录以下子类与评分适用性。

| 约束类别 | 子类（综述依据） | run.csv 字段 | 评分适用性 | 缺口/风险 |
|:---|:---|:---|:---|:---|
| 环化拓扑 | head-to-tail、disulfide bridging、side-chain crosslinking、heterocyclic/ncAA 锁定 | `cyclic=yes` + `peptide_type=cyclic` + notes 记录环化模式 | cyclic flag 计入 design_feasibility/developability；环化模式影响合成复杂度代理 | 现有 schema 未区分环化模式；缺 cyclic-specific 数据源 |
| 手性 | L / D / 混合（heterochiral）；E(3) 等变模型的手性感知误差 | `chirality` + `peptide_type` | 需 stereochemistry-aware parsing；Rosetta/能量评分对 D-靶系统需验证 | L 系打分函数迁移到 D-肽-L-靶可能失真 |
| 非天然残基 | ncAA、N-methylation、glycosylation、lipidation、backbone modification | `peptide_type` + non-natural residue flag（developability） | 仅作 metadata-level 代理；表示方案（CHUCKLES/HELM）需明确 | 缺 ncAA 表示 schema 与 license/assay 审计；实验数据稀缺 |

实施建议（均为 schema/协议层，不涉及执行）：
1. 在 `run.csv` 的 `notes` 或后续扩展列记录环化模式（head_to_tail/disulfide/sidechain/heterocyclic）。
2. 在 scoring_protocol 的 `developability` 与 `design_feasibility` 家族明确：手性与环化 flag 必填，结构/能量指标对 D 与 ncAA 系统标注 `needs_validation`。
3. ncAA 表示（CHUCKLES/HELM）作为未来扩展记录，不在当前主任务排名中混入。

## 5. 代表性缺口（综述支持的 Benchmark 设计理由）

综述 Table 1（small molecule / peptide / protein / antibody 生成建模差异）与“挑战”章节，支持把以下写成本项目的代表性缺口，而非已解决项：

- **数据稀缺与偏置**：peptide-protein 复合物结构远少于 PPI，且偏向 AMP/短信号肽——影响 target/control 代表性与 leakage 评估。
- **构象不确定性**：peptide 多为构象集合、结合时诱导构象——单一静态结构预测可靠性受限，支撑“生成 vs 排序分轨”。
- **拓扑/手性/化学空间**：cyclic、D-peptide、ncAA 需独立的表示、解析与评分适用性，不能并入同一 leaderboard。
- **多目标可成药性**：affinity 单指标不足，需 developability 独立证据层（与 PepTune/HELM-GPT 的多目标观点一致）。
- **目标导向（未来）**：综述展望 function-oriented、multi-target 设计——属未来工作，不作为当前 readiness 完成证据。

## 6. Claim Boundary

| claim type | allowed wording | forbidden wording |
|:---|:---|:---|
| 范式分类 | “综述支持把 structure/sequence/function 三类范式作为与任务轴正交的分类维度” | “范式分类证明三类方法可公平排名” |
| 方法覆盖 | “综述提示 PPFlow/CpSDE/PepINVENT 等可作为覆盖缺口候选” | “这些方法已被本项目纳入/已运行/已复现” |
| 命名消歧 | “PepMimic 与 PepMirror、PPFlow 与 PepFlow 是不同方法” | 把两者当作同一条目处理 |
| 横向约束 | “cyclic/D/ncAA 需要独立记录拓扑、手性与评分适用性” | “本项目已完成 cyclic/D/ncAA 全面评测” |
| 代表性 | “综述支持把数据稀缺/构象不确定/拓扑约束写成代表性缺口” | “综述证明本 Benchmark 已覆盖全部代表性空间” |

## 7. Recommended Next Steps

1. 在 `benchmark_protocol_v0.md` 增加“生成范式分类轴”“横向拓扑与手性约束”“代表性缺口”三节（本轮已做，纯增量）。
2. 后续若评估 review_only 方法，先走 source pin → license → runnability → input contract 流程，再考虑是否调整 scorecard（受 5-10 上限约束，可能需替换而非新增）。
3. 优先补强 cyclic（CpSDE/CP-Composer）与 ncAA（PepINVENT/HELM-GPT/NCFlow）两个方法地形缺口的可用性审计，但不下载任何权重。
4. developability/多目标评分轴可参考 PepTune 的属性集合（permeability、hemolysis、solubility、non-fouling），但实验层指标仍需真实数据或明确来源。
5. 维持上游报告的靶点边界：综述案例（MDM2/MDMX、PCSK9、PD-1、CD38、GLP-1）仍只作候选方向，不进入 frozen target set。
