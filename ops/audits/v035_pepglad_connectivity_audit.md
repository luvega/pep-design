# PepGLAD v0.35 连通性执行审计

## 结论

v0.35 的唯一授权作业 `v035_pepglad_3eqs_seed42` 已创建
`attempt_001`，但在启动容器前因宿主机 Docker API socket 权限不足而失败。
这是一项基础设施启动失败，不是 PepGLAD 方法失败，也不是生成或连通性失败。

本次没有候选结构、runtime evidence、parser 输出或 QC 结果，因此不能生成
`benchmark/results/pilot_pepglad_connectivity_v0.35.json`。v0.34 的 6/7 历史结果
保持不变，`current.v035_bounded_connectivity` 仍为 Critical `FAIL`。

## 授权与前检

- job：`v035_pepglad_3eqs_seed42`
- attempt：`attempt_001`
- fixture：`3EQS`，target chain A，binder chain B
- seed：42，primary
- policy：`chirality_constraint=unrestricted`
- policy：`chirality_check_mode=report_only`
- policy：`baseline_replay_policy=warn_on_mismatch`
- Docker image/environment：`pd-benchmark-methods-gpu:0.21/bench-pepglad`
- runtime limit：900 s

执行前，v0.35 adapter、runner、parser、validator 和相关 v0.34 回归共 501 项测试
通过；额外 Harness/validator focused tests、`py_compile` 和 `git diff --check`
也通过。host 侧前检确认 PepGLAD source commit、source entrypoint、模型权重和
3EQS 输入与固定 SHA-256 一致，dry-run 只返回 `status=validated`，没有创建
attempt。

## 实际执行

`run_result.json` 与 `method_output_manifest.csv` 一致记录：

| field | value |
|:---|:---|
| `created_at` | `2026-07-14T12:19:52+00:00` |
| `runtime_seconds` | `0.026` |
| `exit_code` | `1` |
| `status` | `execution_failed` |
| `status_reason` | `process_exit_1` |
| `parser_status` | `not_run` |
| `overall_qc_status` | `not_run` |

`stderr.log` 记录 Docker API 连接被拒绝：当前受限执行环境无权访问
`unix:///var/run/docker.sock`。`stdout.log` 为空。容器没有启动，因此容器内的
source instrumentation、pocket detection、PepGLAD inference、OpenMM/finalize、
parser 和 QC 均未执行。

## 证据边界

本次证据只支持“授权 attempt 因 Docker API 权限不足而在容器启动前失败”。
它不支持以下结论：

- PepGLAD 方法或模型在 3EQS 上失败；
- PepGLAD 已生成候选肽；
- mixed L/D policy 已获得实际运行验证；
- baseline replay、手性、结构或连接性 QC 已执行；
- 任意 scoring、ranking、方法表现、完整复现或生物学结论。

`raw/` 中没有 `pepglad_candidate.pdb`、runtime evidence 或 summary。解析器已
fail closed，未发布 v0.35 connectivity bundle。

## 下一步

`attempt_001` 必须保留且不得覆盖。当前授权禁止自动重试、`attempt_002`、
seed43、scoring 和 ranking。再次执行需要用户新的明确授权，并先更新执行与
attempt 政策；否则接受本次基础设施失败并保持 Critical gate 打开。

## 项目验收

最终全量测试为 `1361 passed`。KB validator 为 0 errors、0 warnings，
`git diff --check` 通过。Harness evaluation 正常完成，项目状态为
`not_accepted`；`current.v035_bounded_connectivity` 因没有有效 bundle 而保持
Critical `FAIL`，后续 scoring 和 manuscript gate 保持 `pending`。
