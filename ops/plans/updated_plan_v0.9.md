# Updated Plan v0.9

## Summary

v0.9 将当前项目从分散的 v0.6 ARS 评审、v0.7 服务器 dry-run 合同、v0.8 license/schema/input-contract 审计，统一同步为 **“Benchmark manuscript planning + method landscape coverage + execution-gated readiness”** 版本。

本阶段仍然不下载数据、不 clone 第三方源码、不安装环境、不下载模型权重、不运行 GPU、不冻结真实 target set、不声明任何方法已本地复现或性能更优。v0.9 的核心产物是一个当前权威计划、一个 Benchmark paper template 对齐框架，以及一个 review-driven 方法地形图，用于指导后续是否扩展候选方法和补强 cyclic/D/ncAA 代表性。

## Current Authoritative Plan Files

| role | file | status |
|:---|:---|:---|
| 当前执行计划 | `ops/plans/updated_plan_v0.9.md` | authoritative current plan |
| ARS 综合评审历史基线 | `ops/audits/academic_research_suite_review_v0.6.md` | historical review gate |
| 服务器执行门槛 | `benchmark/deployment/server_smoke_test_contract_v0.6.md` | active gate schema |
| 方法级 dry-run 合同 | `benchmark/deployment/method_contracts/` | active planning contracts |
| license/schema/input-contract 审计 | `ops/audits/license_schema_input_contract_review_v0.8.md` | active readiness evidence |
| Benchmark manuscript 主大纲 | `manuscript/outlines/benchmark_manuscript_outline.md` | active writing plan |
| Benchmark template 审计 | `manuscript/support/benchmark_template_audit.md` | active paper-structure gate |
| Introduction 六段链 | `manuscript/support/benchmark_intro_logic_chain.md` | active introduction skeleton |
| 综述驱动方法地形补充 | `manuscript/support/review_synthesis_benchmark_framework_supplement.md` | active v0.9 supplement |

旧文件 `ops/plans/updated_plan_v0.6.md` 保留为历史版本，不再作为当前计划入口。

## Skill-Derived Revisions

### Academic Research Suite

`academic-research-suite` 将本项目定位为 research-to-paper pipeline 的 pre-execution 阶段。当前可进入写作和完整性审查，但不能进入结果型 Benchmark 论文结论。v0.9 继续执行三条 ARS 边界：

1. 每条 manuscript claim 必须能映射到本地 artifact 或标为 unsupported。
2. source pin、method contract、download manifest、dataset schema review 都不是安装、下载、运行或复现证据。
3. 下一阶段如进入服务器操作，必须先通过 license、download manifest、input contract 和 no-git-large-file gate。

### Benchmark Paper Template

`benchmark-paper-template` 将稿件主轴固定为 Evaluation Gap 和 Benchmark Design Rationale，而不是技术方法论文。v0.9 采用五支柱状态：

| pillar | v0.9 status | action |
|:---|:---|:---|
| Research Gap | supported | 用 task mismatch、readiness mismatch、evidence mismatch 三个限制组织 Introduction |
| Construction Pipeline | planned/readiness | 写成 protocol/readiness pipeline，不写成已完成 dataset construction |
| Evaluation Framework | supported | 保持 T1/T2/T3、generation vs ranking、metric applicability、leakage/developability 分层 |
| Empirical Findings | planned only | 只报告 readiness findings；不写 performance findings |
| Companion Method | not_applicable / future optional | 当前不提出 specialized peptide model 或 judge model |

## v0.9 Method Landscape Policy

`benchmark/method_sources/method_landscape_watchlist_v0.9.csv` 引入 27 个方法条目，用于显示方法范式、拓扑和覆盖缺口：

- `included`: 10 个，仍为第一轮候选方法上限。
- `candidate_watchlist`: 2 个，PepFlow 与 BoltzDesign1 保持 watchlist。
- `review_only`: 15 个，只用于 related work、覆盖缺口和后续可用性审计，不进入当前 scorecard include 集合。

新增方法地形图只支持以下写法：

- 可以写：综述提示 cyclic、D-peptide、ncAA 与 function/property-driven design 是代表性缺口。
- 可以写：PepMimic 与 PepMirror、PPFlow 与 PepFlow 需要命名消歧。
- 不可写：review_only 方法已被纳入 Benchmark、已完成源码审计、已安装或已复现。

## Current Execution Gates

| gate | evidence required | current state |
|:---|:---|:---|
| `metadata_ready` | source URL, citation, task relevance | broadly available |
| `source_pinned` | repo route, commit/license metadata | available for 10 include methods at metadata level |
| `license_checked` | code/model/data license route reviewed | partial for priority methods and datasets in v0.8 |
| `weights_manifested` | file URL, expected size/checksum policy | partial future manifest only |
| `input_contract_ready` | method-specific minimum input, command shape, expected output | PepMLM/RFdiffusion + ProteinMPNN partial; PepMirror blocked |
| `dry_run_ready` | license, environment, download manifest and command dry-run plan complete | not yet reached for real execution |
| `smoke_test_ready` | server env, downloaded approved artifacts, command log, output parser | not reached |

## Next Work Package

下一步建议进入 v0.10 “server-side preflight package”，但仍需用户单独确认后才能执行任何服务器下载、clone 或环境安装。

优先级：

1. PepMLM：确认 Hugging Face model-card 使用条款、repo license 缺失边界、batch wrapper 入口。
2. RFdiffusion + ProteinMPNN：确认 RFdiffusion checkpoint HEAD/size/checksum、最小 contig/hotspot 合同、ProteinMPNN fixed-chain handoff。
3. PepMirror：确认 PyRosetta institutional license 与安装路径；未解决前保持 `source_pinned`。
4. Overath：批准服务器端下载前，先写清洗计划；下载后必须生成 row-count discrepancy 和 blank target row 清洗日志。
5. Method landscape：对 CpSDE/CP-Composer、PepINVENT/HELM-GPT/NCFlow、PepMimic/PPFlow/RFpeptides 只做 source/license metadata 审计，不进入 include 集合。
6. Manuscript：补 Figure 1 running example 和 benchmark comparison table；performance findings 保持 future placeholder。

## Claim Gate

v0.9 后所有 reader-facing 文档必须遵守：

- `target_set_v0.csv` 仍为空或 schema-only；任何 target candidate/watchlist 不等于 frozen target。
- `download_manifest_v0.8.csv` 只记录未来服务器下载路线；`download_performed=no`。
- `method_readiness_review_v0.8.csv` 不是安装或运行证据。
- `method_landscape_watchlist_v0.9.csv` 不是候选入选表。
- `review_synthesis_benchmark_framework_supplement.md` 是背景与代表性补充，不是数据集或性能证据。

## Validation

当前同步版应通过：

```powershell
$env:PYTHONUTF8='1'
python scripts/validate_benchmark_kb.py
git diff --check
```

通过后，`ops/validation/wiki_validation_report.md` 是当前机器可验证状态的权威记录。
