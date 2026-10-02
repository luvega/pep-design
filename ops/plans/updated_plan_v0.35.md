# Pep Design Benchmark v0.35 计划

## 状态与目的

v0.35 是一个前瞻性的 PepGLAD 连通性补充层。它允许同一条候选肽同时包含
L 和 D 残基，并将与历史 seed42 基线的字节级差异记录为复现性提示，而不是
连通性解析失败。

本计划不改写 v0.34。v0.34 的 PepGLAD `attempt_003`、6/7 结果和失败诊断
继续作为历史事实保留。

## 唯一授权执行

- job：`v035_pepglad_3eqs_seed42`
- method：`PepGLAD`
- fixture：`3EQS`，target chain A，binder chain B
- peptide length：11
- seed：42，primary
- attempts：最多一个 `attempt_001`

不定义 seed43 或 extension job。失败后不自动重试，新的执行需要再次获得用户
授权。

## 策略

```text
chirality_constraint=unrestricted
chirality_check_mode=report_only
baseline_replay_policy=warn_on_mismatch
```

候选肽的 11 个残基必须全部可以进行几何手性判定，且
`chirality_unknown_count=0`。全 L 或全 D 记为 `chirality_status=pass`；同一候选
中同时存在 L 和 D 记为 `chirality_status=warn`。未知或不可判定手性仍然失败。

历史 seed42 baseline SHA-256 固定为
`dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。
新候选与该值不同但 candidate、official source output 和 runtime 自绑定一致时，
记为 `baseline_replay_status=warn`。不得用新 SHA 替换历史 baseline。

## 硬失败条件

- job、seed、target、chain、length 或三项策略与授权行不一致；
- required file 缺失、为空、不是 regular file、为 symlink 或逃逸 attempt；
- summary sequence 与 PDB binder sequence 不一致；
- PDB target chain 与固定输入 target 不一致；
- official source candidate、raw candidate 与 runtime post-relax SHA 不一致；
- source、model、target、container、environment、observer、instrumenter、wrapper
  或 instrumented source pin 不一致；
- runtime JSON 含重复键、非有限数、额外字段、错误类型或语义不一致；
- requested/effective seed 不是 42；
- 11 个 binder 残基未全部完成手性判定。

## 证据边界

v0.35 只支持 bounded generation connectivity。它不支持 scoring、ranking、
benchmark-completed、full reproducibility、chemical validity、biological validity、
`smoke_test_ready` 或 `benchmark_ready` 声明。项目版本保持 `1.2.21`。

## 实际执行状态

唯一授权的 `attempt_001` 已于 2026-07-14 执行。host 侧 source、model、target
前检通过，但 `docker run` 在容器启动前因无法访问
`unix:///var/run/docker.sock` 而退出：`exit_code=1`、
`runtime_seconds=0.026`、`parser_status=not_run`、`overall_qc_status=not_run`。

这是一项基础设施启动失败，不是 PepGLAD 方法失败。没有生成 raw candidate、
runtime evidence 或 v0.35 connectivity bundle，mixed L/D policy 尚未获得实际
运行验证。详细记录见 `ops/audits/v035_pepglad_connectivity_audit.md`。

不得覆盖或自动重试 `attempt_001`。新的执行需要用户再次明确授权，并先更新
执行与 attempt 政策；本计划不授权 seed43、scoring 或 ranking。

## 2026-10-02 规划补充（执行前记录）

用户已授权文档、已有证据归档和治理更新，未授权新的 PepGLAD 执行。
当前计划及原 `attempt_001` 的失败事实保持不变。

- [项目推进计划](project_progression_plan_v1.md)：证据同步、目标/对照审查与后续阶段条件。
- [PepGLAD 新执行提案](pepglad_next_execution_proposal_v1.md)：新 job/root、单次限额、前检先于 attempt 创建及授权身份迁移清单；状态为 `proposal_not_authorized`。
- [下一阶段验收接口设计](next_phase_acceptance_design_v1.md)：设计补充，尚未实现或启用。
- [SaLT&PepPr 已有推理归档](../audits/saltnpeppr_local_inference_audit_v0.36.md)：local interface inference observation，不补填 PepGLAD candidate bundle 或评分证据。

## 2026-10-02 最新决策与规则

上述“未授权”是独立新执行之前的历史状态。后续用户已授权并完成 PepGLAD fresh
单次方法验收，见 [方法级验收报告](../acceptance/pepglad_method_acceptance_v1.md)；
原 v0.35 失败与合同 gate 不变，不重跑已耗尽额度的 attempt。

用户现已明确停用 superpowers 系列工作流约束，计划与下一步工作改用 `grilling`。
旧计划中的强制技能顺序不再适用；当前正在分轮确认下一阶段成果和实施边界，
确认共同理解后再落实新计划。路线及决策状态见 [技能路线记录](../audits/skill_selection.md)。
