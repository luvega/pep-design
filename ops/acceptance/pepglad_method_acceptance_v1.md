# PepGLAD 方法级执行验收 v1

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-02
- Verification Status: ANALYZED（历史基线未字节复现；本次 bounded connectivity 已独立验证）
- Version Label: pepglad_method_acceptance_v1

## 结论与范围

PepGLAD 新作业 `pepglad_fresh_v1_3eqs_seed42` 的单次执行通过 bounded connectivity 验收，
QC 为 `pass_with_warning`。本次验证源码、权重、环境、GPU 推理、OpenMM 输出、
parser、QC 和原始证据绑定。它不提升 `smoke_test_ready` 或 `benchmark_ready`，
不代表完整复现、化学有效性、生物学有效性、评分、排名或整个项目的生产签收。

用户 2026-10-02 指示“先完成验收再考虑更新说明、REAMME、运行脚本案例和整个项目”，
据此完成既有提案的一个新 job/root、seed42、最多一个 attempt、900 s 限额。
许可范围和停止条件绑定在 [attempt policy](../../benchmark/deployment/pepglad_fresh_attempt_policy_v1.json)，
不覆盖或重试原 v0.35 `attempt_001`。本次执行次数已耗尽，入口拒绝后续执行。

## 实际执行

| 项目 | 结果 |
|:---|:---|
| 新 attempt | `benchmark_runs/pepglad_fresh_v1/pepglad/pepglad_fresh_v1_3eqs_seed42/attempt_001` |
| target / chain / length / seed | 3EQS / A、B / 11 / 42 |
| exit code / runtime | 0 / 25.119 s |
| sequence | `AWHITLLIFTH` |
| parser / QC | `parsed` / `pass_with_warning` |
| GPU | NVIDIA GeForce RTX 4090 |
| PyTorch / CUDA / torch_scatter | 1.13.1+cu117 / 11.7 / 2.1.1+pt113cu117 |
| OpenMM / Ray | 8.0 / 2.51.2 |
| image | `pd-benchmark-methods-gpu:0.21`，命令使用固定 image ID |
| image ID | `sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2` |

生成前在相同宿主身份完成两次固定点及 CUDA 前检。源码 checkout、入口、codesign 权重、
3EQS 输入和 instrumentation 与既有 pins 一致。未安装依赖、下载资产或修改上游源码。
前检曾发现检查项中误列的 `torch_geometric` 并非 PepGLAD 源码依赖；按实际入口移除该项，
没有补装该库。随后修正 NVIDIA 容器 banner 的前检 JSON 读取；以上均发生在 attempt 创建前。

## 独立验收与提示

五项验收全部通过：独立 schema、独立 raw replay、历史 v0.34 artifact 绑定、
固定 image ID 的启动命令、哈希绑定的单次 attempt policy。official source PDB、raw PDB、
runtime post-relax SHA 一致，summary 序列与 PDB 一致；11 个残基均可判定，unknown 为 0。

OpenMM 前为 L6/D5，最终为 L5/D6，因此记录 mixed chirality 提示。
候选 SHA 与历史 seed42 baseline 不同，因此按既定 `warn_on_mismatch` 记录复现性提示；
没有替换历史 baseline。该观察不能归因于模型，也不能排除 OpenMM 的影响。
运行日志另有 pkg_resources 弃用和 Ray 环境变量行为提示，未导致执行失败。

相关回归 **632 passed**；最终入口 focused tests **17 passed**。
6 个内存副本反例（seed、unknown chirality、source commit、candidate SHA、旧 job 身份、score 字段）
全部被独立 replay 拒绝；没有修改已接纳的实际文件。原 v0.35 与相关 v0.34 的
18 个受保护文件 SHA 保持一致。

## 证据与项目边界

- [机器验收报告](pepglad_method_acceptance_v1.json)
- [候选连通性证据包](../../benchmark/results/pepglad_fresh_connectivity_v1.json)
- [单次执行矩阵](../../benchmark/deployment/pepglad_fresh_execution_matrix_v1.csv)
- [输入合同](../../benchmark/input_sets/pepglad_fresh_job_manifest_v1.csv)

运行结构和原始日志留在 gitignored `benchmark_runs/pepglad_fresh_v1/`。
`python scripts/run_pepglad_fresh_acceptance.py --verify` 只重新检查已有证据，不生成新候选。

`current_phase` 仍绑定旧 v0.35 作业；本报告不替换 `current.v035_bounded_connectivity`，
也不豁免 Critical failure。其与新证据的门禁迁移属于后续整个项目更新范围。
本轮不再改 README、说明首页、发布说明或运行案例；版本保持 `1.2.21`。
