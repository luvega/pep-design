# Source, I/O And Initial Smoke-Test Plan v0.11

## Purpose

v0.11 将 v0.10 server-side preflight package 进一步细化为源码下载准备、统一输入格式、统一输出格式和初步运行测试设计。本文件仍是 KB 控制面计划：不 clone、不下载、不安装、不运行 GPU、不冻结 `target_set_v0.csv`，也不声明任何方法已本地复现。

## Execution Boundary

后续真实服务器操作必须继续使用仓库外部 root：

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

KB 内只保存小型 schema、manifest、状态摘要和验证报告。第三方源码树、数据集、model weights、checkpoint、PDB 批量输出和 GPU 结果不得进入本仓库 git。

## Source Freshness Gate

源码下载前先使用 `academic-search` 风格的元数据核对，而不是直接 clone：

1. 以本地 `kb/tables/master_literature_manifest.csv`、`kb/tables/method_evidence_matrix.csv`、`benchmark/method_sources/source_pin_audit_v0.5.csv` 和 `benchmark/deployment/download_manifest_v0.8.csv` 为起点。
2. 对每个 Batch A 方法核对 primary paper、DOI 或 `to_verify` 标识、官方 repo、model/checkpoint/weights route、license route 和 `fetched_at`。
3. 只记录公开元数据和官方 route；不自动下载非 OA PDF，不绕过付费墙，不修改 Zotero、EndNote 或上游 PD-wiki。
4. 若 GitHub/Hugging Face/Zenodo 等官方 route 与 KB 记录不一致，先更新 source freshness manifest，再决定是否修改下载审批表。

对应状态表为 `benchmark/deployment/source_freshness_manifest_v0.11.csv`。
所有下载审批表在服务器执行获批前必须保持 `download_performed=no`。

## Unified Input Flow

v0.11 使用两层输入：

- `job_manifest.csv`：预运行 job 表，一行表示一个 method-target-configuration job，用于描述目标、输入模式、数量、seed 和 adapter 配置。
- `run.csv`：生成后主索引，一行表示一个候选设计样本，继续以 `design_id` 作为所有评分表 merge key。

最小流程：

```text
target/control governance -> job_manifest.csv -> method adapter input -> raw method output
raw method output -> candidate_outputs.csv -> run.csv -> metric CSVs -> merged_run.csv
```

`benchmark/input_sets/example_job_manifest_v0.11.csv` 只含 artificial placeholder rows，所有行必须保持 `status=not_real_benchmark`，不得作为真实 target 或性能证据。

## Unified Output Flow

v0.11 输出分为三层：

- `method_output_manifest.csv`：记录 job、method、stage、source commit、model revision、environment、command、external output root、runtime、exit code 和 parser status。
- `candidate_outputs.csv`：记录候选级 `design_id`、`job_id`、sequence、structure path、rank、parse status 和 failure reason。
- metric CSVs：沿用 `benchmark/protocols/scoring_outputs_schema.md`，最终生成 `merged_run.csv`。

大文件只保留外部路径，不复制进 KB。若某方法不能产生结构输出，结构指标保持 `status=not_applicable` 并写明原因。

## Batch A Initial Test Policy

首轮只覆盖 Batch A：

| method | test depth | required before dry-run | required before real smoke test |
|:---|:---|:---|:---|
| PepMLM | help/version plus artificial sequence job | repo route, HF model-card terms, batch wrapper route | approved T1 target row and external model snapshot |
| RFdiffusion + ProteinMPNN | help/version plus artificial PDB job | RFdiffusion checkpoint HEAD/checksum plan, contig/hotspot syntax, ProteinMPNN handoff policy | approved T3 target PDB, checkpoint, weights and GPU environment |
| PepMirror | no run in Batch A | PyRosetta/Vina/OpenMM/license route remains blocked | only after dependency blockers are resolved |

真实最小 smoke test 必须记录 command、input、output、runtime、environment、parser result 和 failure state。没有这些证据时，不得写 `smoke_test_ready`、已安装、已复现或方法性能结论。

## Implementation Artifacts

- `benchmark/protocols/job_manifest_schema_v0.11.md`
- `benchmark/protocols/adapter_output_schema_v0.11.md`
- `benchmark/input_sets/example_job_manifest_v0.11.csv`
- `benchmark/results/example_method_output_manifest_v0.11.csv`
- `benchmark/results/example_candidate_outputs_v0.11.csv`
- `benchmark/deployment/source_freshness_manifest_v0.11.csv`
- `benchmark/deployment/adapter_preflight_status_v0.11.csv`
- `benchmark/deployment/method_contracts/batch_a_adapter_contract_v0.11.md`

## Validation

回写 KB 后必须运行：

```bash
PYTHONUTF8=1 python scripts/validate_benchmark_kb.py
git diff --check
git status -sb
```

`git diff --check` 可能报告 CRLF-to-LF normalization warning；真正的 whitespace error 必须修复。
