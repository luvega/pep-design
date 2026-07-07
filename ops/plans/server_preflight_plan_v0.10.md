# Server Preflight Plan v0.10

## Purpose

v0.10 将当前 KB 从 protocol/readiness 层推进到服务器端执行审批包，但本文件仍是计划产物：不 clone、不下载、不安装、不运行 GPU、不冻结 `target_set_v0.csv`，也不声明任何方法已本地复现。

## Directory Contract

后续服务器端执行必须使用仓库外部 root：

```bash
export PEP_ROOT=/srv/pep_design
export PEP_KB=${PEP_ROOT}/kb/Pep_design
export PEP_SRC=${PEP_ROOT}/method_sources
export PEP_DATA=${PEP_ROOT}/data
export PEP_WEIGHTS=${PEP_ROOT}/weights
export PEP_RUNS=${PEP_ROOT}/runs
export PEP_LOGS=${PEP_ROOT}/logs
export PEP_TMP=${PEP_ROOT}/tmp
```

这些目录不得放入本 KB git；小型 manifest、状态摘要和验证报告才可回写。

## Batch Policy

| batch | methods | v0.10 action | boundary |
|:---|:---|:---|:---|
| Batch A | PepMLM; RFdiffusion + ProteinMPNN | 准备 source/license/download/input-contract 审批 | `dry_run_ready` only |
| Batch B | PepMirror | 继续确认 PyRosetta/Vina/OpenMM/checkpoint 阻塞项 | keep dependency-blocked |
| Batch C | Other include methods | 仅保留后续 preflight 队列 | no clone/download |

PepFlow 和 BoltzDesign1 仍为 watchlist，除非后续单独批准，不进入第一轮服务器 smoke test。

## Required Approval Artifacts

- `benchmark/deployment/preflight_download_approval_v0.10.csv`
- `benchmark/deployment/method_preflight_status_v0.10.csv`
- `benchmark/input_sets/target_control_freeze_checklist_v0.10.md`
- `ops/migration/file_role_map_v0.10.csv`

## Execution Gate

只有当用户明确批准服务器执行后，才允许根据 `ops/plans/server_from_scratch_run_plan_v0.10.md` 在外部服务器 root 中 clone、下载、建环境或运行 smoke test。所有 KB 内 manifest 在执行前必须保持 `download_performed=no`。
