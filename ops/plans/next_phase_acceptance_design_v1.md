# 下一科学阶段验收接口设计 v1

## 状态

`design_only_not_implemented`，2026-10-02。当前权威合同仍为
[project_acceptance_v1.json](../../harness/contracts/project_acceptance_v1.json)。后续已确认的 10 方法阶段单独实现了合同 v1.2.0 的 `current.native_method_acceptance`（用户修订为运行验收 10/10，质量单列 9/10）；本文件的完整科学验收设计仍未实施，不能与该方法级门禁混为一谈。
本设计不改变现行 gate verdict，也不启用生成、target freeze 或评分。

## 已发现的实现边界

现行 `full.method_readiness` 和 `full.controlled_generation` 复用读取 v0.33 历史失败行的 evaluator。
`full.output_representation`、`full.scoring_validation` 和 `full.benchmark_pillars` 分支固定返回 fail。
它们能阻止当前不完整项目获验收，但不能据未来新产物完成正向验收。
v0.33 的 10 条 blocker rows 必须继续作为历史真实性检查，不能通过改写旧行来满足 full profile。

用户已停用稿件模板路由。机器合同中的旧 gate/claim 名称在本次保持原样；未来科学验收
应以具体产物与 evidence traceability 为依据，迁移前须同时设计合同、注册表、loader 与 evaluator。

## 建议的新阶段输入与通过条件

以下 ID 是设计名称，尚未注册为 active gates。

| 设计接口 | 必需输入 | 通过条件 | 必须拒绝 |
|:---|:---|:---|:---|
| `next.method_readiness` | 新阶段 method-target eligibility、source/license/weights/input/execute contracts | 每条获准路线具有逐级证据和适用范围；延后方法显式标记 | 用 source pin、import probe 或外部示例替代 controlled execution |
| `next.target_controls` | 目标 provenance、assay 状态、正负对照、许可和逐方法 leakage 记录 | 纳入目标逐项完成审查；计算 decoy 与 assay-backed nonbinder 分开 | 未知 leakage 解释为低风险；已知重叠作为独立公平测试 |
| `next.controlled_generation` | 批准的 jobs/attempt policies、完整 execution/runtime/candidate/QC | 身份、输入、预算、source/model/environment pins 和输出一致；失败有记录 | exit 0 单独作为成功；覆盖旧 attempt；缺少 producer 绑定 |
| `next.output_representation` | 序列/结构/链/手性/拓扑/非标准残基和 handoff 记录 | 每个接纳候选有明确可评估模态；结构指标只接收合格结构 | 将独立 FASTA 与未线程化 backbone 当作 sequence-resolved structure |
| `next.scoring_validation` | 合法目标/对照、指标适用表、工具 provenance、校准、metric CSV | 适用性可解释；design_id 合并完整；缺失/失败/不可适用分开 | 用 0 填缺失；未经验证的化学类型直接评分；已知泄漏样本混入公平比较 |
| `next.scientific_analysis` | 经验证分析输入、分析脚本、失败/资源统计、结果与 claim 对应表 | 每个结果追溯到合法产物；目标级不确定性和比较边界明确 | readiness、parser fixture 或同目标重复候选替代跨目标结果 |

## 依赖与治理迁移

目标与方法审查可以分别推进；受控生成依赖两者及明确执行授权。
输出表示依赖受控候选；评分依赖目标/对照、表示和评分阶段授权；科学分析依赖已验证评分。
发布与签核再依赖这些产物和 final digest。新 gate 不通过时仍 failure closed。

迁移时先给新增 evidence artifacts 定义用途和 forbidden uses，再调整 evaluator allowlist、
loader 的 gate/domain/severity 绑定和 profile dependencies。原历史检查和失败材料保留。
现行 `current.target_control_boundary` 要求 target set 为空；正式冻结必须进入明确的新阶段合同，
不能只往旧 CSV 添加行。移除旧模板 gate 时，科学结果的 traceability 条件应由上述产物检查承接。

## 实施前验证清单

- 完整新证据能触发正向验收，缺失、错误绑定和未授权输入能触发拒绝。
- v0.33/v0.34/v0.35 历史真实性、既有 D-Flow overlap 和 scoring guard 回归保持。
- 不可适用与未知不触发晋升；sequence-only、D/mixed/cyclic/ncAA 使用各自适用合同。
- contract/registry/loader/evaluator 的 ID、schema、dependency 和 owner role 一致。
- 生成报告与最终 digest 一致；旧 signoff 不复用。

本设计首次归档时只交付接口设计。后续方法级合同迁移见当前阶段计划；上述完整科学接口、claim surface 与 full-profile 科学检查的全面重构仍未实施。
