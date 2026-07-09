# Method Unblock Audit v0.20

## Scope

v0.20 记录外部 workbench `/data/protein-design` 上的全量方法解阻检查。对应轻量摘要表为：

- `benchmark/deployment/method_unblock_manifest_v0.20.csv`
- `benchmark/deployment/method_unblock_smoke_results_v0.20.csv`

这些记录是 external readiness evidence，not Benchmark result。它们不支持 target-set 晋升、评分、方法排序、完整复现、方法优劣比较或生物学验证结论。

## Independent PyRosetta Route

- 新增外部镜像目录 `/data/protein-design/images/pd-pyrosetta-methods-gpu/`。
- 新增 compose 服务 `pd-pyrosetta-methods-gpu`，镜像 tag 为 `pd-pyrosetta-methods-gpu:0.20`。
- 该路线不复用 `pd-bindcraft-gpu` 的 PyRosetta 环境；BindCraft 镜像只作为 BindCraft 自身 smoke 环境。
- 镜像通过 RosettaCommons quarterly US West mirror 直装 PyRosetta：`pip install pyrosetta --find-links https://west.rosettacommons.org/pyrosetta/quarterly/release`。
- `bench-diffpepbuilder` 与 `bench-pyrosetta` 环境均完成 `pyrosetta.init("-mute all")` 最小导入测试。
- 当前记录的 PyRosetta build 为 `2026.03+releasequarterly.5e498f1409`；使用边界仍受 PyRosetta/RosettaCommons license terms 约束。

## Observed Status

| method | v0.20 status | interpretation |
|:---|:---|:---|
| PepMLM | `carried_forward_v019_ready` | v0.19 GPU 示例证据沿用；v0.20 未重跑。 |
| RFdiffusion + ProteinMPNN | `carried_forward_v019_ready` | v0.19 component smoke 证据沿用；仍需 handoff adapter。 |
| DexDesign / OSPREY3 | `carried_forward_v019_cpu_ready` | v0.19 CPU route probe 证据沿用；仍需选择实际 design example。 |
| DiffPepBuilder | `unblock_smoke_passed_gpu` | 独立 PyRosetta 镜像可用；示例 `alk1` 8 aa generation smoke 通过，仍需 adapter/parser 与多案例 fixture。 |
| PepMirror | `blocked_weights` | 独立 PyRosetta 镜像可用；checkpoint manifest/download 尚未验证。 |
| PepGLAD | `blocked_weights` | README 指向 GitHub release；直接猜测 asset URL 返回 404，GitHub API rate-limited。 |
| D-Flow / PeptideDesign | `blocked_input_contract` | 仅观察到 `dflow.zip`；`test_set`/`PepMerge`/`pep_cache` 合同仍未满足。 |
| BindCraft | `failed_timeout` | smoke-only 配置可进入 GPU trajectory 阶段并写出统计文件，但 542 秒后被 timeout 中止。 |
| SaLT&PepPr | `blocked_license` | UbiquiTx license 与 gated Hugging Face access 未解决。 |
| AfCycDesign / ColabDesign cyclic peptide | `deferred_cli_adapter` | 非 notebook CLI adapter 尚未锁定。 |

## Installation And Permission Findings

- PyRosetta 独立镜像：第一次构建因 `# syntax=docker/dockerfile:1.6` 触发外部 Dockerfile frontend 解析失败；已改为普通 Dockerfile。经用户确认采用 quarterly mirror 直装路线后，`pd-pyrosetta-methods-gpu:0.20` 构建成功，未观察到新的授权、网络或文件权限 blocker。
- DiffPepBuilder：第一次 v0.20 rerun 越过 PyRosetta 后在 `experiment.num_loader_workers=0` 与 PyTorch `prefetch_factor` 组合处失败；runner 调整为 `num_loader_workers=1` 后通过 GPU example smoke，生成一个 `alk1_length_8_sample_0.pdb`。
- PepMirror：PyRosetta image blocker 已解除；当前 blocker 是 checkpoint manifest/download 未验证。
- BindCraft：bounded smoke 确认 GPU 和 BindCraft 内置 PyRosetta 可用；`max_trajectories` 不是可靠硬停止，因此仍需显式 one-trajectory wrapper 或更强进程边界。
- PepGLAD：未下载 checkpoint；当前 blocker 是 release asset 名称/访问路线未解析。
- D-Flow：未下载 test/PepMerge 数据；当前 blocker 是输入合同，不是 CUDA import。
- 未观察到新的文件系统权限 blocker；v0.20 结束后未保留匹配的运行容器。

## External Artifacts

- Raw logs, command files, runtime JSON and small output manifests live under `/data/protein-design/data/outputs/benchmark_v0.20/method_unblock_smokes/`.
- Independent PyRosetta Dockerfile and runner live under `/data/protein-design`; private credentials, non-public Rosetta materials, raw logs, model weights and generated structures must remain outside KB and outside tracked files.
- This KB stores only summary CSVs and this audit.

## Next Actions

1. 将 DiffPepBuilder 的成功 example smoke 转换为统一 adapter/parser 和多案例 fixture。
2. 补齐 `PepMirror` checkpoint manifest，再运行最小 generation smoke。
3. 通过非 rate-limited 路线解析 PepGLAD release asset 名称和 checksum。
4. 为 BindCraft 写显式 one-trajectory wrapper，避免 `max_trajectories` 语义不可靠。
5. 恢复 D-Flow `test_set`/`PepMerge`/`pep_cache` 输入合同后再执行 inference smoke。

## No-Overclaim Boundary

v0.20 supports only method-unblock and readiness findings. It does not support target-set freeze, scoring, method-ranking evidence, biological validation, or claims that all methods are free of unresolved issues.
