# Skill Selection

## 当前路线（2026-10-02）

- `grilling is the primary route`：按用户最新决定，用 `/home/a/.codex/skills/grilling/SKILL.md` 落实项目计划与下一步工作。将决策组织为依赖树，每轮集中提出前提已明确的问题、逐项给出建议，收到回答后再展开下一轮；最终共同理解经用户确认后实施新计划。
- `superpowers workflow constraints are disabled`：停止由 `using-superpowers`、`brainstorming`、`writing-plans`、`executing-plans`、`subagent-driven-development` 及该系列其他技能强制施加的流程、worktree、TDD、复审和分支收尾顺序。具体测试、审查、工具和分工按任务需要选择。
- `docs/superpowers/`、旧计划中的 `REQUIRED SUB-SKILL` 和其他历史引用不再构成当前执行指令；保留历史文件及其证据绑定，不删除安装目录或修改全局技能。旧 `scripts/build_benchmark_kb.py` 在已有 AGENTS 或验收合同的项目中于副作用前拒绝 bootstrap，直接调用根文档生成函数也受保护，避免旧模板覆盖现行规则。
- 文件、工具与证据能够确认的事实由 agent 查明，可分派 subagent；研究取舍交给用户决定。既有明确授权继续有效，不重复询问已定事项。本次规则切换已获明确授权；本轮 10 方法计划随后经用户整体确认，方法级合同迁移已在该授权内实施。
- `benchmark-paper-template is disabled`：继续停用其结构和五支柱规划规则。`academic-research-suite` 改为按需研究支持，不再是强制规划主路线。
- 本机未找到 `building-llm-wiki`；用户先前允许的 `academic-research-suite` 与机器合同替代路线保留为 KB 支持选项，不要求安装技能。
- `intro-drafter is consistency-check only`；Supervisor-Skills 历史论文支持与 superpowers 工作流分开记录，均不提供执行或科学结果证据。
- 机器合同、证据边界、数据来源保护、执行预算与 Git 授权继续有效；新计划不自动获得新 GPU 执行或评分授权。PepGLAD fresh 单次方法验收已完成；后续合同 v1.1.0 已将活动门禁迁至 current.native_method_acceptance，v0.35 历史失败和 evaluator 保留。

## 历史采用记录（不构成当前路线）
- Zotero：只读导出本地文献元数据、BibTeX 和 item-key 映射。
- building-llm-wiki：按 raw sources / wiki / schema 三层结构建设项目知识库。
- literature-review 与 citation-management：用于检索块、去重、元数据完整性和 references.bib 管理。
- academic-chinese-style / nature-language-style：用于中文报告的证据边界、克制表达和 overclaim 控制。
- academic-research-suite：用于 v0.6-v0.9 的 research-to-paper pipeline 审查、完整性 gate、claim boundary、计划同步和后续 manuscript 阶段管理。
- idea-evaluator：用于评估 protocol-first Benchmark idea 的 fatal flaws、五维评分、feasibility 和继续推进 verdict。
- benchmark-paper-template：作为 manuscript skeleton、Introduction 六段链和 v0.9 当前计划同步的主模板，用于五支柱审计、§2-§7 骨架、pre-submission gate 和 Benchmark-vs-technical-paper 边界。
- intro-drafter：仅作为二次一致性检查，确认背景、gap、RQs、design considerations、proposal 和 contributions 连续；不作为 Benchmark paper 的主模板。

## Supervisor-Skills 历史安装记忆

- Source: `HKUSTDial/Supervisor-Skills`
- Installed source commit: `0b77a1b98794f8341d57685a0e829a3fa175d05f`
- Installed local skills: `benchmark-paper-template`, `intro-drafter`, `figure-designer`, `pre-submission-reviewer`, `idea-evaluator`
- License boundary: `CC BY-NC-SA 4.0`; keep use in this academic, non-commercial Benchmark KB context with attribution.
- 历史记录曾将 `benchmark-paper-template` 设为 primary route；该路线已按上述用户指令停用。
- `intro-drafter` is consistency-check only because Benchmark papers use a different Introduction flow from technical papers.
- `figure-designer` is for manuscript figure planning and QC; it does not create Benchmark result evidence.
- `pre-submission-reviewer` is for final manuscript audit; it is not scoring evidence.
- `idea-evaluator` is for scope reassessment; it does not prove method readiness.
- Boundary: Supervisor-Skills records are not Benchmark result, not scoring evidence, and not method-ranking evidence.

## 替代说明
`biomedical-research-framework` 未在本机 skill 目录中发现；本阶段用固定 CSV schema、method card 的证据字段、以及 overclaim/hedging 规则替代其产物。

`tech-paper-template` 本轮不启用，因为本文定位为 Benchmark framework / protocol-first manuscript，不提出新的 peptide-design algorithm 或 technical mechanism。

## 后续暂不启用
- office-academic-skill：留到 PPT/Word 报告阶段。
- scientific-toolkit-skill：留到实际 Benchmark 统计和图表阶段。

## 本轮决策树（D1–D8 已确认，阶段执行已授权）

| 决策 | 状态 | 下一层依赖 |
|:---|:---|:---|
| D0 停用 superpowers 强制流程，改用 grilling 对齐计划 | 用户已明确决定，本次落实 | 无需再次批准规则切换 |
| D1 下一阶段首要交付 | 用户选择：先补齐全部 10 种方法的运行验收 | 方法级验收标准与证据复用 |
| D2 阶段目标和边界确认后的自主实施程度 | 用户选择：阶段内自主执行，关键变化再讨论 | 范围、预算、停止条件改变时返回用户 |
| D3 运行验收标准 | 用户选择：按各方法自身任务做真实端到端验收 | 各方法验收项与执行范围 |
| D4 已有证据使用 | 用户选择：复用合格证据，只补缺项 | 缺项清单与所需预算 |
| D5 每方法通过标准 | 用户选择：必须产出质量达标候选才算该方法通过 | 原生 QC 和过滤结果纳入验收 |
| D6 新增执行资源预算 | 用户选择：采用第三轮阶段预算 | 安装/下载/计算额度与停止条件 |
| D7 手性范围 | 用户选择：按方法声明允许不同手性，分别做质量检查 | mixed 本身不失败，未知或不满足适用 QC 的候选不能通过 |

D1–D7 已由用户明确回答。已选预算为 GPU 累计 24 小时；CPU 密集任务累计
墙钟 24 小时、最多 24 线程/256 GiB RAM；新增下载 50 GiB、磁盘 200 GiB；
每方法最多 3 次新尝试。方法原生终点和机器容量已经只读核查。

整体理解汇总见 [10 方法运行与候选质量验收计划](../plans/method_runtime_acceptance_plan_v1.md)。
D8：用户最终回复“确认，按此计划执行”。共同理解与阶段执行已确认；按验收计划的预算、质量标准和停止条件自主实施。

阶段执行已达到约定停止条件：9/10 通过，D-Flow 的 3 次新尝试共 17 个候选均未满足质量检查。按 D2/D6 停止追加生成；新的 attempt、外部后处理或验收标准变化必须另作用户决策，不能由推荐选项推定批准。详见阶段验收报告。

## 2026-10-02：初期验收范围修订 D9

用户明确“我初步只需要跑通代码和环境，后续再大量比较”。本决定替代 D5 的初期质量通过前提：运行验收需真实原生终点及完整执行证据；候选质量另列。现有证据支持运行 10/10、候选完整性质量 9/10。D-Flow 质量失败与 DexDesign 单 IAS 范围保留；原政策、预算、阈值、账本及 attempt 不变。修订前计划/合同/质量报告已独立归档并记录 SHA，见 `benchmark/deployment/method_runtime_scope_v2.json`。不启动额外 D-Flow 诊断或新模型运行，大量比较延期。合同更新为 v1.2.0，项目 VERSION 保持 1.2.21，不签核、commit/push 或发布。
