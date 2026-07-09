# Method Install Smoke Audit v0.19

## Scope

v0.19 记录外部 workbench `/data/protein-design` 上的方法安装、GPU 环境、作者示例或最小 preflight 运行情况。对应轻量摘要表为：

- `benchmark/deployment/method_source_doc_verification_v0.19.csv`
- `benchmark/deployment/method_install_smoke_manifest_v0.19.csv`
- `benchmark/deployment/method_smoke_test_results_v0.19.csv`

这些记录是 external readiness evidence，not Benchmark result。它们不支持 target-set 晋升、评分、性能排名、完整复现、方法优劣比较或生物学验证结论。

## Observed Status

| method | v0.19 status | interpretation |
|:---|:---|:---|
| PepMLM | `example_smoke_passed_gpu_noncanonical_output_caveat` | GPU 版 PyTorch 路线可用，最小生成命令完成；输出序列含 `X`，需要 parser/质量规则。 |
| RFdiffusion + ProteinMPNN | `example_smoke_passed_gpu` | 现有 RFpeptide/RFdiffusion 与 Foundry/ProteinMPNN 镜像各自示例通过；仍缺单一 handoff adapter。 |
| DexDesign / OSPREY3 | `example_smoke_passed_cpu_expected` | CPU Java/Gradle route probe 通过；还不是实际 design example。 |
| PepGLAD | `preflight_passed_blocked_weights` | GPU env 和 pocket detection preflight 通过；release checkpoint URL/下载仍未解析。 |
| D-Flow / PeptideDesign | `preflight_passed_blocked_input_contract` | GPU import preflight 通过；`pep_cache`/输入数据合同缺失。 |
| DiffPepBuilder | `failed_command` | checkpoint、receptor processing 和 ESM embedding 到达；inference 导入链卡在 `pyrosetta`，需要 PyRosetta/license route 决策。 |
| BindCraft | `failed_timeout` | `libgfortran5` 缺失已由 `pd-bindcraft-gpu:0.19.1` 修复；作者 CD47 peptide quick 示例 1800 秒内未产生 accepted design。 |
| SaLT&PepPr | `blocked_license` | UbiquiTx license 与 gated Hugging Face access 未解决。 |
| PepMirror | `blocked_license` | PyRosetta/license 与 checkpoint route 未解决。 |
| AfCycDesign / ColabDesign cyclic peptide | `deferred_notebook_route` | ColabDesign env 可导入；非 notebook CLI adapter 尚未锁定。 |

## Installation And Permission Findings

- PepMLM: Transformers 拒绝 torch `<2.6` 的 `.bin` 加载路径；已用 `pd-benchmark-methods-gpu:0.19.1` 将 `bench-pepmlm` 升级到 torch `2.6.0+cu124`。
- DiffPepBuilder: 共享镜像补齐 `pyrootutils`, `hydra-joblib-launcher`, `dm-tree`, `GPUtil`, `tmtools`, `ml-collections`, `scikit-learn`, `wandb`, `wget` 后可完成 receptor processing 和 ESM embedding；inference 仍因 `pyrosetta` 缺失失败。
- BindCraft: wrapper 已去掉 strict nounset 下 conda activate 的 `ADDR2LINE` 问题；`DAlphaBall.gcc` 缺 `libgfortran.so.5` 已通过 `pd-bindcraft-gpu:0.19.1` 修复。最终问题转为作者示例筛选/timeout，不是当前观察到的库缺失。
- RFdiffusion + ProteinMPNN: RFdiffusion 容器曾产生 root-owned 输出导致清理失败；v0.19 runner 增加 Docker root `chown` fallback。
- BindCraft timeout 后 Docker compose run 容器不会自动停止；已在 runner 中增加 best-effort timeout cleanup，并手动停止本次残留容器。
- 未观察到仍未解决的文件系统权限 blocker；剩余 blocker 主要是 license、checkpoint、input contract、PyRosetta route 和 smoke 设置可控性。

## External Artifacts

- Raw logs, command files, runtime JSON and small output manifests live under `/data/protein-design/data/outputs/benchmark_v0.19/method_smokes/`.
- Third-party source trees live under `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/`.
- DiffPepBuilder checkpoint and ESM artifacts were downloaded to external workbench paths only; no model weights are stored in this KB.
- Docker image layers remain in the external Docker/workbench environment; this KB stores only image tags and readiness summaries.

## Next Actions

1. DiffPepBuilder: decide whether to reuse an authorized PyRosetta route or patch the inference import path only if scientifically and legally appropriate; also cache ESM2 checkpoints outside per-run workdirs.
2. BindCraft: add a smoke-only advanced settings file with bounded `max_trajectories`, lower MPNN/filter workload, and explicit timeout cleanup before rerunning.
3. PepGLAD: resolve release checkpoint asset URLs/checksums without relying on rate-limited GitHub API responses.
4. D-Flow / PeptideDesign: recover or document required `pep_cache`/input dataset files before inference.
5. SaLT&PepPr and PepMirror: resolve license and gated artifact access before any executable smoke.
6. ColabDesign/AfCycDesign: choose a non-notebook adapter route or keep the method deferred.
7. RFdiffusion + ProteinMPNN: define a single handoff manifest and parser before comparative multi-case fixtures.

## No-Overclaim Boundary

v0.19 supports only method-provided example/preflight readiness findings. It does not support benchmark completion, target-set freeze, scoring, method-ranking evidence, biological validation, or claims that all methods are free of unresolved issues.
