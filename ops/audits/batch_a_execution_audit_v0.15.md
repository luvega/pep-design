# Batch A Execution Audit v0.15

本审计记录 2026-07-07 在外部 `/data/protein-design` workbench 上完成的最小预检与
Batch A smoke-test 摘要。它是执行证据摘要，不是完整 Benchmark 结果，不冻结
`target_set_v0.csv`，也不将任何方法提升为 `smoke_test_ready` 或 `benchmark_ready`。

## Workbench And Image Evidence

- `protein-design` workbench 合入了 `pd-benchmark-methods-gpu:0.13` scaffold，并在
  本地构建出镜像 `sha256:affbdab88d8a4f017701e60a0538682b43a27e15bcd0c9f9add3dac8c4b93710`。
- 镜像大小约 `43653635007` bytes，创建时间为 `2026-07-07T16:28:27+08:00`。
- build 过程中修复了两个工程问题：`bench-dflow` 的 pip find-links 写法，以及
  `benchmark-method-env-check` heredoc/stdin 执行方式。
- 大型 Docker 层、Hugging Face cache、运行日志、PDB、TRB 和 trajectory 文件均保留在
  `/data/protein-design`，没有写入本 KB。

## Import-Level Preflight

`benchmark/deployment/run_preflight_results_v0.15.csv` 记录了五个 shared-image
环境的 import-level 结果。D-Flow / PeptideDesign 观察到 CUDA PyTorch 与
`torch_scatter` 可用；PepMLM、DiffPepBuilder 和 PepGLAD 仍显示 CPU PyTorch 或
扩展兼容性 caveat；ColabDesign/JAX 路线仅验证 import。

这些结果只支持 environment preflight 叙述。它们不支持方法已可复现、已安装无误、
已完成 checkpoint inference 或可以进入正式 Benchmark 排名。

## Batch A Minimal Smoke Tests

`benchmark/deployment/batch_a_smoke_test_results_v0.15.csv` 记录三条最小烟测：

- PepMLM：使用源码随附 `scripts/data/test.csv` 的第一条 receptor sequence，生成
  1 条 4-mer peptide；由于当前 shared image 中 PepMLM 为 CPU PyTorch，本轮记录为
  CPU-only smoke test，并观察到 `TianlaiChen/PepMLM-650M` 模型缓存在外部目录。
- ProteinMPNN：复用 `pd-foundry-gpu:latest` 和现有
  `proteinmpnn_v_48_020.pt`，在 `/data/inputs/PDL1.pdb` 上生成一个 FASTA 输出。
- RFpeptide/RFdiffusion：复用 `pd-rfpeptide-gpu:fixed` 和现有模型 mount，运行 bundled
  cyclic peptide 示例，生成一个 PDB、一个 TRB 和两个 trajectory PDB 文件。

## Boundaries And Next Actions

- 本轮没有下载或冻结 Benchmark target set；PepMLM 使用源码自带测试行，RFpeptide 和
  ProteinMPNN 使用 workbench 既有示例输入。
- 本轮没有评分、重打分、结构验证、统计分析或性能比较。
- 后续需要修复 PepMLM/DiffPepBuilder/PepGLAD 的 GPU PyTorch/extension 路线，并为
  RFdiffusion-to-ProteinMPNN handoff、PepMLM 批处理输入、target/control/leakage
  审查和 parser 输出建立可重复接口。
- 论文写作中只能表述为 `minimal smoke-test observed` 或 `readiness evidence`，
  不能表述为完整 benchmark、性能领先、实验验证或问题已解决。
