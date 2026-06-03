# Benchmark Manuscript Draft Outline

## Working Title

**面向近期 AI 多肽设计方法的 Benchmark 框架：任务分层、可运行性审计与统一评分协议**

English working title: **A benchmark framework for recent AI peptide design methods: task stratification, runnability auditing and unified scoring**

## Manuscript Positioning

本文定位为 Benchmark framework / protocol-first manuscript。文章的核心问题不是“哪个方法当前最好”，而是“如何在任务、输入输出、可运行性和评分层面公平比较近期 AI 多肽设计方法”。因此，本文只陈述已经由本项目 KB 支持的事实：近 5 年文献范围、候选方法筛选、三类任务协议、可运行性审计和统一评分 schema。所有性能、命中率、实验成功率和本地复现相关结论均保留为后续真实 Benchmark 阶段的待评估内容。

写作风格采用中文学术初稿，保留英文方法名、模型名、论文题名、BibTeX key、文件名和命令名。论证动词优先使用“提示、支持、表明、拟评估、仍需验证”；避免“证明、最佳、全面优于、已复现”等当前证据不能支持的表述。

## Abstract Draft

生成式模型、蛋白基础模型和结构设计方法正在进入多肽设计领域，覆盖 linear peptide binder、cyclic peptide、D-peptide、miniprotein binder 和 protein-peptide interaction 等任务。然而，不同方法的输入、输出、依赖、代码和权重状态差异较大，直接建立统一 leaderboard 容易混淆任务能力、工程可运行性和生物学证据。为解决这一问题，我们基于本地 Zotero/PD-wiki 知识库整理 2021-06-03 至 2026-06-03 的近期多肽设计方法文献，并将第一轮候选方法映射到 sequence binder、structure-conditioned peptide binder 和 miniprotein binder baseline 三类任务。

在该 protocol-first 框架中，我们建立候选方法证据表、可运行性矩阵、`run.csv` 主索引和独立评分输出 schema。该设计参考 de_novo_binder_scoring 的工程经验，将输入标准化、模型运行、结构预测、指标抽取和 CSV 合并拆分为可审计步骤。当前版本纳入 10 个 first-wave candidate methods，并将 PepMLM、PepMirror 和 RFdiffusion + ProteinMPNN 列为优先 smoke-test 设计对象。本文提供的是可复用 Benchmark 协议和写作框架，不声明任何候选方法已在本地复现，也不比较最终性能或实验成功率。

## Main Thesis

AI 多肽设计 Benchmark 应先建立任务分层和工程可运行性标准，再进行模型性能排序。对于短肽、环肽、D-肽和 miniprotein binder，统一评价必须同时记录输入类型、输出形态、手性/环化约束、依赖版本、失败状态和评分适用性，否则计算指标容易被误读为通用设计能力或实验可转化性。

## 1. Introduction

### Paragraph Role: Opening Context

多肽设计正在从经验筛选和结构启发优化，扩展到由 protein language models、diffusion models、full-atom generative models 和 AF2/MPNN-style pipelines 支持的条件生成。PepMLM 代表 sequence-conditioned peptide binder 方向，RFdiffusion + ProteinMPNN 和 BindCraft 代表 miniprotein/protein binder baseline，PepMirror、D-Flow 和 DexDesign 代表 D-peptide 或 chirality-aware design，AfCycDesign / ColabDesign cyclic peptide 则代表 cyclic peptide structure/design 路线。建议引用：`chen_target_2025`, `bennett_improving_2023`, `pacesa_bindcraft_2024`, `yang_cross-chirality_2026`, `guerin_dexdesign_2024`, `rettie_cyclic_2023`。

### Paragraph Role: Challenge

现有方法能否生成候选，不等同于候选是否可运行、可批处理、可评估或可进入实验漏斗。sequence-only 方法可能输出 peptide sequences，但需要下游结构或结合验证；structure-conditioned 方法依赖 target PDB、pocket definition 和 checkpoint；D-peptide 与 cyclic peptide 方法还需要显式处理 chirality、cycle constraint 和结构解析边界。该差异提示，一个单一分数或单一 leaderboard 难以覆盖所有多肽设计任务。

### Paragraph Role: Gap

当前 Benchmark 的主要缺口在于工程接口和证据边界。不同仓库可能使用不同输入格式、chain convention、batch route、model weights 和 scoring outputs；一些方法具备文献价值，但权重、license 或最小运行路径仍需确认。因此，Benchmark 需要首先回答“哪些方法可进入可审计运行流程”和“哪些输出可以映射到共同评分层”。

### Paragraph Role: Contribution

本文提出一个 protocol-first Benchmark 框架：从 432 条去重文献记录中筛选 10 个 first-wave include methods，将方法映射到三类任务，建立 runnability audit，并定义 `run.csv -> metric CSVs -> merged_run.csv` 的统一数据流。该框架的贡献是为后续真实 Benchmark 提供可复用工程协议，而不是在未运行方法前给出性能排名。

## 2. Literature Scope And Method Selection

### Paragraph Role: Evidence Source

本研究的文献层基于本地 Zotero API、PD-wiki 历史证据层和外部 repository route 校验构建，时间窗为 2021-06-03 至 2026-06-03。当前去重后包含 432 条 Zotero-derived records，其中 125 条标记为 included，26 条作为 background-only，281 条需要后续 manual check。该设置保证候选方法来自明确来源层，同时保留 Zotero item key 与 BibTeX key 的边界。

### Paragraph Role: Selection Logic

方法筛选遵循“先可运行，再代表性”的原则。候选方法需要具备代码或服务可运行线索、可标准化输入、可评估输出和可记录版本/参数/资源需求的可能性。最终 include set 包含 PepMLM、SaLT&PepPr、DiffPepBuilder、PepGLAD、D-Flow / PeptideDesign、PepMirror、AfCycDesign / ColabDesign cyclic peptide、DexDesign / OSPREY3、RFdiffusion + ProteinMPNN 和 BindCraft；PepFlow 与 BoltzDesign1 暂列 watchlist。

### Paragraph Role: Evidence Boundary

该筛选不等同于本地复现，也不代表方法性能高低。当前纳入依据主要是 metadata、repository route、published method scope 和 scoring compatibility。对于 code status、weights status、license 和 batch inference 的判断仍需要在 smoke-test 阶段进一步核验。

## 3. Benchmark Task Stratification

### Paragraph Role: Task Design

本 Benchmark 将候选方法划分为三类任务。`T1_sequence_binder` 以 target sequence 为主要输入，输出 peptide sequence candidates；`T2_structure_peptide_binder` 以 target PDB、chain/pocket definition 或 reference binder 为输入，输出 peptide complex structure 或 peptide structure；`T3_miniprotein_binder_baseline` 以 target PDB、hotspot 或 length range 为输入，输出 binder backbone 和 sequence。

### Paragraph Role: Method Mapping

PepMLM 和 SaLT&PepPr 映射到 T1。DiffPepBuilder、PepGLAD、D-Flow / PeptideDesign、PepMirror、AfCycDesign / ColabDesign cyclic peptide 和 DexDesign / OSPREY3 映射到 T2。RFdiffusion + ProteinMPNN 和 BindCraft 映射到 T3。该映射允许同任务内比较优先进行，而跨任务比较仅限于工程可运行性、输出可评估性和资源需求。

### Paragraph Role: Rationale

任务分层的必要性来自多肽设计对象本身的异质性。linear peptide、cyclic peptide、D-peptide、heterochiral peptide 和 miniprotein binder 在构象自由度、手性表示、结构输出和实验验证路径上不同。将这些方法放入同一未分层 ranking 会掩盖任务定义带来的差异。

## 4. Engineering Design Of The Benchmark

### Paragraph Role: Pipeline Design

工程层采用统一 `run.csv` 作为主索引，每个设计样本使用 `design_id` 连接方法、任务、输入、输出和后续评分。字段包括 `method`、`task_id`、`target_id`、`input_mode`、`target_sequence`、`target_pdb`、`target_chains`、`binder_chain`、`peptide_type`、`chirality`、`cyclic`、`status` 和 `notes`。该接口参考 de_novo_binder_scoring 的输入标准化和后续 CSV 合并思路，但不把该项目作为直接依赖。

### Paragraph Role: Input Standardisation

输入标准化将 sequence/PDB preprocessing、model-specific input generation 和 method execution 拆开。结构任务默认 binder chain 为 `A`，target chain 为 `B`；多链 target 可记录为 `B,C,D...`。如果某一方法要求不同 chain convention，适配层必须记录原始 chain 到标准 chain 的映射。

### Paragraph Role: Scoring Design

评分层拆成 independent metric CSVs，包括 `confidence_metrics.csv`、`interface_metrics.csv`、`rmsd.csv`、`dockq.csv`、`rosetta_metrics.csv` 和最终 `merged_run.csv`。每个评分输出都以 `design_id` 为合并键。该设计允许 AF2、AF3、Boltz、ColabFold、DockQ、PyMOL 和 PyRosetta/Rosetta 作为可选评分模块，而不会阻塞协议层本身。

### Paragraph Role: Failure Modes

工程失败状态被显式编码为 `not_installable`、`weights_missing`、`input_not_standardizable`、`runs_but_no_batch`、`output_not_evaluable` 和 `deferred_dependency`。这些状态用于区分方法不可运行、权重不可得、输入不能标准化和输出不能评分等不同问题，避免将工程失败误写为科学性能不足。

## 5. Runnability Audit Of Candidate Methods

### Paragraph Role: Tier Summary

可运行性审计将 10 个 include methods 划分为三类。Tier 1 包括 PepMLM、PepMirror 和 RFdiffusion + ProteinMPNN，适合作为第一批 smoke-test 设计对象。Tier 2 包括 DiffPepBuilder、PepGLAD、D-Flow / PeptideDesign、AfCycDesign / ColabDesign cyclic peptide 和 BindCraft，主要阻塞项是 checkpoint、环境、notebook-to-batch 或 heavy dependency stack。Tier 3 包括 SaLT&PepPr 和 DexDesign / OSPREY3，主要原因是任务适配或 workflow mapping 成本较高。

### Paragraph Role: Interpretation

Tier 并非性能判断。Tier 1 只表示当前 repository route、输入输出映射和评分兼容性相对明确；Tier 2 和 Tier 3 方法仍可在后续阶段进入真实运行，但需要先解决依赖、权重、license 或最小案例映射。PepFlow 和 BoltzDesign1 保持 watchlist，用于后续替补或扩展任务。

## 6. Planned Scoring Framework

### Paragraph Role: Metric Families

评分框架包含四类指标。`structure_confidence` 记录 pLDDT、pTM、ipTM、PAE/iPAE 和 ipSAE；`interface_geometry` 记录 contacts、interface area、H-bonds 和 clash count；`structure_similarity` 记录 DockQ、backbone RMSD 和 interface RMSD；`design_feasibility` 记录 length、chain validity、chirality flag、cyclic flag 和 output parseability。

### Paragraph Role: Method-Specific Applicability

对于 sequence-only 方法，结构评分字段应保留为空，并记录 `status=not_applicable` 与 `not_applicable_reason=sequence_only_output`，除非后续添加结构预测层。对于 D-peptide 和 cyclic peptide 方法，评分必须记录 chirality、cycle constraint、chain mapping 和可解析结构。对于 miniprotein baseline，界面和结构置信度评分可作为主要计算指标，但仍不能替代实验结合或功能证据。

## 7. Anticipated Results Structure

### Paragraph Role: Planned Results

当前初稿中的 Results 部分应采用 planned results structure，而不是性能结论。第一部分报告文献和候选方法筛选结果；第二部分报告可运行性审计和 Tier 分层；第三部分报告方法到 T1/T2/T3 的任务映射；第四部分预留未来真实运行后的 parseability、runtime、output completeness、confidence/interface metrics 和 failure cases。

### Paragraph Role: Boundary

在真实 smoke test 和 Benchmark 运行前，任何“方法 A 优于方法 B”的结论都不应写入 Results、Abstract 或 Discussion。可以写“拟评估”“计划记录”“当前工程准备度提示”，但不能写“已验证”“性能最佳”或“已复现”。

## 8. Discussion

### Paragraph Role: Main Interpretation

本文的主要观点是，多肽设计 Benchmark 应先解决任务定义、工程可运行性和输出可评估性，再讨论性能排序。该观点对近期 AI peptide design 尤其重要，因为 sequence-conditioned、structure-conditioned、full-atom、chirality-aware 和 miniprotein binder 方法之间的可比性并不天然成立。

### Paragraph Role: Methodological Contribution

统一 `run.csv`、任务分层、failure states 和 independent scoring outputs 可以降低不同方法输出不可比的问题。该框架也为后续 smoke test 提供了最低信息要求：版本、命令、输入、输出、runtime、dependency、license 和 status 都必须记录。

### Paragraph Role: Scientific Boundary

计算评分只能支持候选排序和结构假设，不能替代实验亲和力、实验结构、细胞功能、PK/PD 或 CMC 证据。D-peptide、cyclic peptide 和 miniprotein binder 尤其需要区分可生成性、结构可信度、实验可合成性和生物学功能。

### Paragraph Role: Limitations And Next Steps

当前限制包括：部分候选方法权重和 license 待确认，部分方法需要 heavy dependency stack，D-peptide 和 cyclic peptide 的评分需要更明确的 chirality/constraint 检查，真实 target set 尚未冻结。下一步应完成 Tier 1 smoke test、标准 target set、版本锁定和小规模结果报告。

## 9. Methods

### Paragraph Role: Literature Workflow

文献检索与去重基于 Zotero item key、BibTeX key、DOI、PMID、arXiv ID 和 normalized title。Zotero、EndNote 和 upstream PD-wiki 作为 source layer，不直接修改；`E:\Codex_Projects\Pep_design` 作为项目工作层。

### Paragraph Role: Candidate Scoring

候选方法筛选使用 `candidate_method_scorecard.csv`，维度包括 `code_status`、`weights_status`、`inputs_standardizable`、`outputs_evaluable`、`gpu_cost`、`peptide_fit` 和 `recency_evidence`。进入 include set 的方法必须可映射到至少一个 Benchmark task。

### Paragraph Role: Runnability And Protocol Validation

可运行性审计使用 `method_runnability_matrix.csv`，字段覆盖 repo route、license、weights、install route、batch inference、expected inputs/outputs、scoring compatibility、hardware notes、blocking risks 和 next action。项目验证由 `scripts/validate_benchmark_kb.py` 执行，检查 KB、候选方法、runnability rows、smoke-test README、Markdown links 和协议文件。

## 10. Figures And Tables

Figure 1 should show the full Benchmark design overview: literature KB, candidate shortlist, runnability audit, task mapping, `run.csv`, method execution, metric CSVs, `merged_run.csv`, and report generation. Figure 2 should show a task-method matrix, with method families on one axis and task/input/output/peptide type on the other. Figure 3 should show scoring architecture, with independent confidence, interface, RMSD/DockQ, Rosetta and design-feasibility metrics converging into `merged_run.csv`.

Table 1 should summarise the 10 include methods, their primary task, input, output, peptide type and current code/weights status. Table 2 should compress `method_runnability_matrix.csv` into Tier, blocker and next action. Table 3 should define metric families, applicable tasks and not-applicable reasons. Extended Data should include search query blocks, screening status counts, watchlist methods and validator output.

## Reverse Outline

| section | single message | evidence source |
|:---|:---|:---|
| Abstract | This is a protocol-first Benchmark framework, not a performance ranking | `reports/wiki_validation_report.md`; `benchmarks/protocols/benchmark_protocol_v0.md` |
| Introduction | Peptide-design methods are heterogeneous and require task-aware benchmarking | `tables/method_evidence_matrix.csv`; candidate literature cards |
| Literature scope | The KB defines the evidence base and first-wave candidate set | `reports/literature_scope_report.md`; `reports/candidate_methods_shortlist.md` |
| Task stratification | T1/T2/T3 prevent false comparisons across unlike outputs | `benchmarks/protocols/benchmark_protocol_v0.md` |
| Engineering design | `run.csv` and independent metric CSVs make the benchmark auditable | `benchmarks/protocols/run_csv_schema.md`; `benchmarks/protocols/scoring_outputs_schema.md` |
| Runnability audit | Tiering schedules smoke tests but does not rank performance | `reports/method_runnability_audit.md` |
| Scoring framework | Metrics must be applied only when output type supports them | `benchmarks/scoring/scoring_protocol_v0.md` |
| Discussion | Computational metrics do not replace experimental validation | writing guardrails and method limitations |

## Candidate Citation Bank

| role | suggested citation keys |
|:---|:---|
| sequence peptide design | `chen_target_2025`, `brixi_saltpeppr_2023` |
| structure/miniprotein binder design | `bennett_improving_2023`, `dauparas_robust_2022`, `pacesa_bindcraft_2024`, `pacesa_one-shot_2025` |
| D-peptide and chirality-aware design | `yang_cross-chirality_2026`, `guerin_dexdesign_2024`, `valiente_computational_2021`, `shen_discovery_2023` |
| cyclic/macrocyclic peptide design | `rettie_cyclic_2023`, `watson_pr_macrocyclic_2023`, `pingitore_v_delocalized_2024` |
| pMHC/TCR-like and application boundary | `johansen_novo-designed_2025`, `householder_novo_2025`, `white_wl_design_2026` |
| scoring and engineering reference | de_novo_binder_scoring project README and example workflow |

## Self-Review Checklist

| dimension | current status | action before full manuscript |
|:---|:---|:---|
| contribution | Framework contribution is clear | Keep title and abstract protocol-first |
| writing clarity | Section roles are explicit | Convert outline to paragraph prose in next drafting phase |
| experimental strength | No experimental results claimed | Add real smoke-test results only after running methods |
| evaluation completeness | Scoring categories and failure states defined | Add target set and environment after smoke-test planning |
| method design soundness | Interfaces align with project schemas | Keep validator updated when manuscript files change |
