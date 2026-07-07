# Protein-Design Image Consolidation Plan v0.13

## Summary

本计划把 `/mnt/ssd4t/protein-design` 现有 Docker 镜像纳入 Benchmark
preflight control layer。核心决策是：已有镜像继续复用；缺失专用镜像的方法进入一个
新的多 conda 环境 Docker 镜像 `pd-benchmark-methods-gpu:0.13`。该镜像定义在外部
workbench 仓库，不把第三方源码、模型权重、许可证材料或 GPU 输出放入 KB。

## Image Assignment

- Reuse existing images for RFdiffusion/RFpeptide, ProteinMPNN, BindCraft,
  AF2/AF3 validation, Rosetta post-processing and PepMimic.
- Add `pd-benchmark-methods-gpu:0.13` only for PepMLM, DiffPepBuilder,
  PepGLAD, D-Flow/PeptideDesign and ColabDesign.
- Keep SaLT&PepPr license-gated until UbiquiTx/Hugging Face access is approved.
- Keep PepMirror out of the shared image until PyRosetta/license/checkpoint and
  D-peptide parser routes are resolved.
- Keep DexDesign/OSPREY3 as a future CPU/Java auxiliary route.

## Interface Changes

- The workbench Compose layer adds profile `benchmark` and method-specific
  profiles `pepmlm`, `diffpepbuilder`, `pepglad`, `dflow` and `colabdesign`.
- The shared image mounts:
  - `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark` as read-only
    source provenance.
  - `data/benchmark_models` as the external model/cache root.
  - `data/licenses` as the optional local license root.
- KB records the assignment through:
  - `benchmark/deployment/docker_image_inventory_v0.13.csv`
  - `benchmark/deployment/method_environment_assignment_v0.13.csv`

## Test Plan

- Workbench static checks:
  - parse all new environment YAML files;
  - run `bash -n scripts/smoke-test.sh examples/benchmark-methods/run-env-check.sh`;
  - run `docker compose -f compose/docker-compose.yml config --quiet`.
- KB checks:
  - extend `scripts/validate_benchmark_kb.py` to validate v0.13 headers,
    required rows and no-overclaim boundaries;
  - run `PYTHONUTF8=1 python scripts/validate_benchmark_kb.py`;
  - run `git diff --check`.

## Boundaries

本阶段记录 image/environment readiness planning and scaffold evidence only。
`pd-benchmark-methods-gpu:0.13` 的 Dockerfile 可以后续构建，但当前 KB 不声称该镜像已
构建、方法已安装、权重已下载、smoke test 已通过或 Benchmark 已执行。
