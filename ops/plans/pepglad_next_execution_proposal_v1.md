# PepGLAD 新执行提案 v1（待授权、待身份迁移）

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-10-02
- Verification Status: UNVERIFIED
- Version Label: pepglad_fresh_execution_proposal_v1

## 目的与身份

目标是取得一个满足 bounded connectivity 合同的 PepGLAD 候选，保留
[原 v0.35 attempt 的基础设施失败](../audits/v035_pepglad_connectivity_audit.md)。
提案状态为 `proposal_not_authorized`，没有新增 active job、runtime 目录或 candidate。
下列身份属于提案命名空间，现有 runner/parser/Harness 尚未支持，不能直接执行。

| 项目 | 提案值 |
|:---|:---|
| proposal_id | `pepglad_fresh_execution_v1` |
| proposed_job_id | `pepglad_fresh_v1_3eqs_seed42` |
| proposed_output_root | `benchmark_runs/pepglad_fresh_v1/pepglad/pepglad_fresh_v1_3eqs_seed42` |
| proposed_attempt_id | `attempt_001`，仅属于上述新 job/root；原 v0.35 `attempt_001` 不变 |
| method / fixture | PepGLAD / 3EQS |
| target / binder chain | A / B |
| input SHA-256 | `7086cf2bc4723ccbb4be5ff7f86a50d9db59bc307f4fbb0395a3c6ce3569827d` |
| peptide length / seed | 11 / 42（primary） |
| image / environment | `pd-benchmark-methods-gpu:0.21` / `bench-pepglad`；实际 image ID 与 source/model pins 须通过既有固定点核对 |
| chirality_constraint | `unrestricted` |
| chirality_check_mode | `report_only` |
| baseline_replay_policy | `warn_on_mismatch` |
| 允许执行次数 / runtime limit | 最多 1 个新 attempt / 900 s |
| extensions / scoring / ranking | 未纳入此提案 |

历史 baseline SHA-256 仍为
`dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。
不得以新结果替换该 baseline，也不得用新授权解释为重试或覆盖旧 attempt。

## 前检先于 attempt 创建

在最终实际执行身份与权限上下文中，先验证 Docker client/server API 可达性，
目标 image ID、环境、GPU 资源、输出父目录，以及 source/model/target 固定点。
核查所选入口、observer、instrumenter、wrapper 和 instrumented source 的完整绑定。
这些前检只读取状态；容器启动与推理属于获授权后的执行步骤。

前检失败时不创建 attempt、不启动容器，记录 `preflight_blocked` 并停止。
成功前检与正式启动应处于同一执行身份，启动前再次确认关键身份未变化。
本次文档更新没有查询 Docker API 或启动容器，不能声称权限问题已修复。

## 先完成授权身份迁移

现有 v0.35 manifest、runner、parser、独立 validator、Harness protocol binding 和回归测试
使用固定的 `v035_pepglad_3eqs_seed42` 身份。后续需要明确的新执行授权和更新后的 attempt
政策，并在真正执行前完成以下实现及检查：

1. 将新 job/root/attempt 身份一致地接入 producer、parser、validator 和验收接口。
2. 保留原 job/root、失败记录和 v0.34 bindings；旧身份仍按原合同解释。
3. 在新的参数化或 versioned policy 中检查源、模型、target、image、seed 和输出路径，
   防止仅改 job ID 却沿用不一致的授权字段。
4. 验证旧路径覆盖拒绝、未授权身份拒绝、前检失败不创建 attempt、次数耗尽停止，
   以及新的有效证据包能被独立重放检查。
5. 明确新的 candidate bundle 如何纳入 current-phase gate，更新相关合同/注册表和计划后再执行。

以上是实现清单，不是本次已完成的代码能力。归档 SaLT&PepPr 不承担该迁移的任何完成条件。

## 输出与停止条件

成功输出应具有 official source candidate、raw candidate、summary、runtime、method manifest、
candidate outputs、candidate QC 和独立 connectivity bundle；大型结构和日志留在 gitignored 根。
bundle 绑定原 v0.34 小型产物 hash，不回写其 6/7 历史状态。

11 个 binder 残基必须全部完成手性判定，unknown count 为 0；mixed L/D 与 baseline mismatch
按既有前瞻性政策记 warning。序列、目标链、长度、源/模型/环境 pins、runtime schema 或
official/raw/runtime SHA 绑定不一致时失败关闭。

运行或解析失败后停止，保留全部失败记录；不自动再建 attempt、运行 seed43、扩大超时、
跳过 relax、理想化结构或进入 scoring/ranking。exit 0 本身不构成候选接纳依据。

若不授权新执行，继续接受现存基础设施失败事实并保持当前 Critical gate 打开。
此提案不能产生 signoff，不能豁免目标、对照、许可、leakage 或后续评分门禁。
