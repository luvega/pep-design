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
