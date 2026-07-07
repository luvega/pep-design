# Docker Environment Assignment Audit v0.13

## Summary

本审计整理 `/mnt/ssd4t/protein-design` 当前可见的本地镜像，并将 Benchmark 第一批方法
映射到已有镜像或新的共享补充镜像。审计结论是：不能把所有方法放进一个 conda 环境；
可以把缺失专用镜像的方法放进一个 Docker 镜像，但必须使用多个隔离 conda 环境。

## Existing Images Observed

当前 Docker daemon 中已观察到以下可复用镜像：

- `pd-foundry-gpu:latest`
- `pd-rfpeptide-gpu:fixed`
- `pd-bindcraft-gpu:installed`
- `pd-af2multimer-gpu:fixed`
- `pd-af3-gpu:v3.0.2`
- `pd-rosetta-cpu-parallel:latest`
- `pd-pepmimic-gpu:latest`

这些镜像对应的 Benchmark 路线记录在
`benchmark/deployment/docker_image_inventory_v0.13.csv`。已有镜像不需要在 KB 阶段重新
建立环境。

## Conflict Findings

- PepGLAD/PepMirror 依赖 PyTorch 1.13.1 和 CUDA 11.7 生态。
- DiffPepBuilder 依赖 PyTorch 2.1 和 CUDA 11.8 生态。
- D-Flow/PeptideDesign 记录了 PyTorch 2.4.1、CUDA 12.1 和 `torch-scatter`
  兼容性需求。
- ColabDesign/AF-style routes 依赖 JAX/AlphaFold 参数路线。
- PyRosetta、SaLT&PepPr gated access、AlphaFold 参数和大 checkpoint 不能直接写入公共
  Dockerfile。

因此，单一 conda 环境不是稳妥路线；多 conda 环境共存于一个 Docker 镜像是当前的
Benchmark preflight 默认方案。

## Assignment Decision

- `pd-benchmark-methods-gpu:0.13` 作为 shared benchmark preflight image，只覆盖缺失专用镜像的方法。
- 每个方法通过 `conda run -n <env>` 调用对应环境。
- 方法输入输出仍通过后续 adapter/schema 层统一，不通过共享 Python site-packages 统一。
- 任何真实 smoke test、checkpoint 下载、模型运行、parser validation 和 runtime log 都必须在后续批准阶段另行记录。

## No-Overclaim Boundary

本审计不是 installation evidence，也不是 local reproducibility evidence。它只支持
`dockerfile_defined_not_built`、`existing_image_reuse`、`dependency_blocked` 或
`license_gated` 等 readiness findings。
