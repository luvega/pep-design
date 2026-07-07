# Server From-Scratch Benchmark Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task on the server. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从一台干净的 Linux CUDA 服务器开始，按可审计门控完成 Pep_design Benchmark 的服务器端 clone、download、environment setup、dry-run、smoke test、scoring 和小文件结果回写准备。

**Architecture:** 本仓库仍作为 control-plane KB，只保存协议、schema、小型 manifest、日志摘要和验证报告。第三方源码、数据、模型权重、运行结果和批量 PDB 输出必须放在服务器外部 roots，不纳入本仓库 git。执行顺序采用 gate-based workflow：preflight -> source pin -> license/download approval -> environment solve -> input contract -> dry-run -> smoke test -> scoring -> merged report。

**Tech Stack:** Linux, Bash, Git, Conda/mamba, Python, CUDA/NVIDIA driver, Hugging Face CLI, Zenodo/Dryad/API download tools, PyRosetta license where applicable, optional ColabFold/AlphaFold/Boltz/Rosetta/DockQ/PyMOL scoring modules.

---

## Scope And Non-Scope

本计划面向后续服务器端真实执行，但当前 Markdown 文件本身不是执行证据。

允许在服务器端逐步执行的内容：

- 建立外部目录结构。
- clone 并 pin 第三方方法源码。
- 在获得许可和审批后下载小型/大型数据、checkpoint、模型权重。
- 构建 Conda/mamba 环境。
- 运行 artificial input dry-run 和小规模 smoke test。
- 生成 `run.csv`、method output、metric CSV、`merged_run.csv`、runtime log 和 parser log。

仍然禁止在本 KB 仓库中保存的内容：

- 第三方源码树。
- 下载的数据集原始包。
- 模型权重或 checkpoint。
- 批量 PDB、预测结构压缩包、GPU 运行大结果。
- 未经整理的大型日志。

## Required Local KB Inputs

执行前在服务器上应先同步或 clone 当前 KB，并确认以下文件存在：

- `ops/plans/updated_plan_v0.9.md`
- `ops/plans/updated_plan_v1.3.md`
- `benchmark/deployment/server_smoke_test_contract_v0.6.md`
- `benchmark/deployment/server_readiness_checklist_v0.5.md`
- `benchmark/deployment/download_manifest_v0.8.csv`
- `benchmark/deployment/method_readiness_review_v0.8.csv`
- `benchmark/deployment/method_contracts/pepmlm_server_contract_v0.7.md`
- `benchmark/deployment/method_contracts/rfdiffusion_proteinmpnn_server_contract_v0.7.md`
- `benchmark/deployment/method_contracts/pepmirror_dependency_contract_v0.7.md`
- `benchmark/input_sets/example_run.csv`
- `benchmark/protocols/run_csv_schema.md`
- `benchmark/protocols/scoring_outputs_schema.md`
- `benchmark/scoring/scoring_protocol_v0.md`

## Server Directory Contract

默认服务器路径如下；如果服务器已有不同挂载点，应在执行日志中记录实际路径：

```bash
export PEP_ROOT=/srv/pep_design
export PEP_KB=${PEP_ROOT}/kb/Pep_design
export PEP_SRC=${PEP_ROOT}/method_sources
export PEP_DATA=${PEP_ROOT}/data
export PEP_WEIGHTS=${PEP_ROOT}/weights
export PEP_ENVS=${PEP_ROOT}/envs
export PEP_RUNS=${PEP_ROOT}/runs
export PEP_LOGS=${PEP_ROOT}/logs
export PEP_TMP=${PEP_ROOT}/tmp
```

期望目录：

```text
/srv/pep_design/
  kb/Pep_design/                 # 本 KB 仓库
  method_sources/                # 第三方方法源码，不进 git
  data/
    raw/                         # 原始下载数据，不进 git
    processed/                   # 清洗后数据，不进 git，后续仅回写小型 manifest
    target_sets/                 # 冻结前候选 target/control 文件
  weights/                       # 模型权重/checkpoint，不进 git
  envs/                          # Conda/mamba environments
  runs/
    dry_run/
    smoke_test/
    benchmark/
  logs/                          # 小型命令日志和审计日志
  tmp/
```

## Method Execution Priority

第一轮不要同时跑 10 个方法。建议按可控性分三批：

| batch | methods | purpose | gate target |
|:---|:---|:---|:---|
| Batch A | PepMLM; RFdiffusion + ProteinMPNN | 覆盖 T1 sequence-only 和 T3 miniprotein baseline；优先验证 pipeline skeleton | `smoke_test_ready` after logs exist |
| Batch B | PepMirror | 科学优先级高，但 PyRosetta/Vina/OpenMM/checkpoint 风险高；先解决 license/dependency | `dry_run_ready` before real input |
| Batch C | DiffPepBuilder; PepGLAD; D-Flow / PeptideDesign; AfCycDesign / ColabDesign cyclic peptide; BindCraft; SaLT&PepPr; DexDesign / OSPREY3 | 扩展 T2、cyclic、D-peptide、degrader/interface 和 AF/Rosetta workflows | method-specific preflight first |

PepFlow 和 BoltzDesign1 仍为 watchlist，不进入第一轮服务器 smoke test，除非用户另行批准。

## Gate Definitions

| gate | server-side evidence required |
|:---|:---|
| `metadata_ready` | KB 中有 URL、citation、task mapping、availability row |
| `source_pinned` | 服务器 clone 成功，记录 remote URL、branch、commit SHA、license file path |
| `license_checked` | 代码、数据、模型、checkpoint、PyRosetta/AF/Rosetta 条款记录完成 |
| `weights_manifested` | 下载 URL、version、size、checksum policy 和本地 weights path 记录完成 |
| `input_contract_ready` | method-specific `run.csv` row、minimal input、expected output、parser rule 明确 |
| `dry_run_ready` | 环境可创建，命令可打印 help/version 或在 artificial input 上走通非结果型流程 |
| `smoke_test_ready` | 有真实小输入、真实命令、日志、输出、parser status、runtime 和 failure status |
| `benchmark_ready` | target/control set 冻结、leakage/license/assay/control 审查完成，评分 pipeline 可重复运行 |

## Task 1: Server Inventory And KB Sync

**Files:**
- Read on server: `${PEP_KB}/AGENTS.md`
- Read on server: `${PEP_KB}/ops/plans/updated_plan_v0.9.md`
- Create on server outside git: `${PEP_LOGS}/server_inventory_YYYYMMDD.txt`
- Create on server outside git: `${PEP_LOGS}/kb_validation_YYYYMMDD.json`

- [ ] **Step 1: Create external roots**

```bash
mkdir -p "${PEP_KB}" "${PEP_SRC}" "${PEP_DATA}/raw" "${PEP_DATA}/processed" "${PEP_DATA}/target_sets" "${PEP_WEIGHTS}" "${PEP_ENVS}" "${PEP_RUNS}/dry_run" "${PEP_RUNS}/smoke_test" "${PEP_RUNS}/benchmark" "${PEP_LOGS}" "${PEP_TMP}"
```

Expected: all directories exist under `${PEP_ROOT}` and none are inside `.git`.

- [ ] **Step 2: Record server inventory**

```bash
{
  date -Iseconds
  hostname
  uname -a
  df -h "${PEP_ROOT}" || true
  free -h || true
  nvidia-smi || true
  git --version || true
  python --version || true
  conda --version || true
  mamba --version || true
} | tee "${PEP_LOGS}/server_inventory_$(date +%Y%m%d).txt"
```

Expected: inventory records OS, disk, memory, GPU and package-manager state. If `nvidia-smi` is missing, stop before any GPU method.

- [ ] **Step 3: Sync or clone KB**

Use one of the following, depending on whether the KB is copied from workstation or GitHub:

```bash
git clone https://github.com/luvega/pep-design.git "${PEP_KB}"
cd "${PEP_KB}"
git status -sb
```

Expected: KB worktree exists. If using a local copy instead of GitHub, record the copy source and commit SHA in `${PEP_LOGS}/kb_sync_YYYYMMDD.txt`.

- [ ] **Step 4: Validate KB before execution**

```bash
cd "${PEP_KB}"
PYTHONUTF8=1 python scripts/validate_benchmark_kb.py | tee "${PEP_LOGS}/kb_validation_$(date +%Y%m%d).json"
```

Expected: validator reports `status=pass`, 0 errors and 0 warnings. If validation fails, fix KB artifacts before touching external method sources.

## Task 2: License, Account And Secret Gate

**Files:**
- Read: `${PEP_KB}/benchmark/deployment/download_manifest_v0.8.csv`
- Read: `${PEP_KB}/benchmark/deployment/method_readiness_review_v0.8.csv`
- Create outside git: `${PEP_LOGS}/license_account_gate_YYYYMMDD.md`

- [ ] **Step 1: Verify required accounts and licenses**

Record status for:

```text
Hugging Face token: required for model route checks and gated assets if any
Zenodo access: required for checkpoint/data records
Dryad access: required for PEPBI route checks
PyRosetta license: required before PepMirror or BindCraft PyRosetta-dependent steps
AlphaFold/ColabFold assets: required before AF-family scoring or ColabDesign/BindCraft
RFdiffusion checkpoint terms: required before RFdiffusion run
ProteinMPNN weights terms: required before ProteinMPNN handoff
```

Expected: each dependency is marked `approved`, `not_needed_for_batch`, or `blocked`. Do not proceed with a method if its license is `blocked`.

- [ ] **Step 2: Keep secrets outside the KB**

```bash
mkdir -p "${PEP_ROOT}/secrets"
chmod 700 "${PEP_ROOT}/secrets"
```

Expected: tokens and license files are stored outside `${PEP_KB}`. No token or license content is written into Markdown, CSV, Git commits, or shell history.

## Task 3: Source Clone And Pin Audit

**Files:**
- Read: `${PEP_KB}/benchmark/method_sources/source_pin_audit_v0.5.csv`
- Create outside git: `${PEP_LOGS}/source_pin_server_YYYYMMDD.csv`

- [ ] **Step 1: Clone Batch A sources**

Clone into `${PEP_SRC}` only:

```bash
cd "${PEP_SRC}"
git clone https://github.com/programmablebio/pepmlm PepMLM
git clone https://github.com/RosettaCommons/RFdiffusion RFdiffusion
git clone https://github.com/dauparas/ProteinMPNN ProteinMPNN
cd "${PEP_SRC}/PepMLM" && git checkout 3169c4920f8c383948e0a5d3a7c8f87e5e7d2436
cd "${PEP_SRC}/RFdiffusion" && git checkout 2d0c003df46b9db41d119321f15403dec3716cd9
cd "${PEP_SRC}/ProteinMPNN" && git checkout 8907e6671bfbfc92303b5f79c4b5e6ce47cdef57
```

These URLs and commit SHAs come from `source_pin_audit_v0.5.csv`. Record exact commands in `${PEP_LOGS}/source_clone_YYYYMMDD.sh`.

Expected: three source trees exist outside the KB.

- [ ] **Step 2: Pin commits and license files**

```bash
for repo in PepMLM RFdiffusion ProteinMPNN; do
  cd "${PEP_SRC}/${repo}"
  printf "%s,%s,%s,%s\n" "${repo}" "$(git remote get-url origin)" "$(git rev-parse HEAD)" "$(git branch --show-current)" | tee -a "${PEP_LOGS}/source_pin_server_$(date +%Y%m%d).csv"
  find . -maxdepth 2 -iname "LICENSE*" -o -iname "COPYING*" | sort | tee -a "${PEP_LOGS}/${repo}_license_files_$(date +%Y%m%d).txt"
done
```

Expected: every cloned source has remote URL, commit SHA, branch and license-file search output.

- [ ] **Step 3: Do not clone Batch B/C until Batch A passes preflight**

Expected: PepMirror, DiffPepBuilder, PepGLAD, D-Flow, AfCycDesign, BindCraft, SaLT&PepPr and DexDesign remain pending unless Batch A inventory and license gates are complete.

## Task 4: Data And Weight Download Approval

**Files:**
- Read: `${PEP_KB}/benchmark/input_sets/reference_dataset_sources_v1.csv`
- Read: `${PEP_KB}/benchmark/deployment/download_manifest_v0.8.csv`
- Create outside git: `${PEP_LOGS}/download_approval_YYYYMMDD.csv`
- Create outside git: `${PEP_LOGS}/download_performed_YYYYMMDD.csv`

- [ ] **Step 1: Build approval table before download**

For every dataset or weight, record:

```text
artifact_id,artifact_type,method_or_dataset,source_url,license_status,expected_size,checksum_policy,local_destination,approved_by,download_performed
```

Expected: all rows start with `download_performed=no`.

- [ ] **Step 2: Approve only Batch A minimum assets**

Minimum Batch A assets:

```text
PepMLM model route or Hugging Face revision
RFdiffusion checkpoint route
ProteinMPNN weights route
One artificial input set from example_run.csv
One approved tiny smoke-test target/control candidate only if license/control/leakage fields are sufficient
```

Expected: no full benchmark dataset is downloaded before target/control governance is complete.

- [ ] **Step 3: Download only approved artifacts**

Use method-specific documented commands after approval. Every command must write to `${PEP_DATA}` or `${PEP_WEIGHTS}`, never `${PEP_KB}`.

Expected: each downloaded file has size, timestamp and checksum record in `${PEP_LOGS}/download_performed_YYYYMMDD.csv`.

## Task 5: Environment Build Strategy

**Files:**
- Read: `${PEP_KB}/benchmark/environments/environment_feasibility_matrix.csv`
- Create outside git: `${PEP_LOGS}/environment_build_YYYYMMDD.md`
- Create outside git: `${PEP_LOGS}/conda_env_export_pep_seq_hf_YYYYMMDD.yml`
- Create outside git: `${PEP_LOGS}/conda_env_export_pep_rfdiffusion_YYYYMMDD.yml`
- Create outside git: `${PEP_LOGS}/conda_env_export_pep_proteinmpnn_YYYYMMDD.yml`
- Create outside git: `${PEP_LOGS}/conda_env_export_pep_scoring_base_YYYYMMDD.yml`

- [ ] **Step 1: Create one environment per environment family**

Recommended first environments:

```text
pep_seq_hf              # PepMLM, later SaLT&PepPr
pep_rfdiffusion         # RFdiffusion
pep_proteinmpnn         # ProteinMPNN
pep_scoring_base        # CSV parsing, Biopython, pandas, numpy, optional DockQ/RMSD utilities
```

Expected: environments are isolated. Do not force all methods into one environment.

- [ ] **Step 2: Record environment solve logs**

```bash
conda env export -n pep_seq_hf > "${PEP_LOGS}/conda_env_export_pep_seq_hf_$(date +%Y%m%d).yml"
conda env export -n pep_rfdiffusion > "${PEP_LOGS}/conda_env_export_pep_rfdiffusion_$(date +%Y%m%d).yml"
conda env export -n pep_proteinmpnn > "${PEP_LOGS}/conda_env_export_pep_proteinmpnn_$(date +%Y%m%d).yml"
conda env export -n pep_scoring_base > "${PEP_LOGS}/conda_env_export_pep_scoring_base_$(date +%Y%m%d).yml"
```

Expected: each environment has an export file and a build log. If an environment fails to solve, mark the method `environment_blocked`.

## Task 6: Input Contract And Run Table

**Files:**
- Read: `${PEP_KB}/benchmark/protocols/run_csv_schema.md`
- Read: `${PEP_KB}/benchmark/input_sets/example_run.csv`
- Create outside git: `${PEP_RUNS}/dry_run/run.csv`
- Create outside git: `${PEP_RUNS}/smoke_test/run.csv`

- [ ] **Step 1: Create dry-run table from artificial inputs**

Copy `example_run.csv` to `${PEP_RUNS}/dry_run/run.csv` and keep `status=not_real_benchmark`.

Expected: dry-run table is artificial and cannot be reported as benchmark result.

- [ ] **Step 2: Create smoke-test run table only after target/control approval**

The smoke-test `run.csv` must include:

```text
design_id,method,task_id,target_id,binder_id,input_mode,target_sequence,target_pdb,target_chains,binder_chain,pocket_definition,peptide_type,chirality,cyclic,status,notes
```

Expected: every row has `status=ready_for_smoke_test` only after license, controls, assay evidence and leakage status are recorded.

## Task 7: Batch A Dry-Run

**Files:**
- Input: `${PEP_RUNS}/dry_run/run.csv`
- Create outside git: `${PEP_RUNS}/dry_run/logs/`
- Create outside git: `${PEP_RUNS}/dry_run/method_status.csv`

- [ ] **Step 1: PepMLM dry-run**

Run only help/version/import checks and artificial input parsing first:

```bash
conda activate pep_seq_hf
cd "${PEP_SRC}/PepMLM"
python - <<'PY' | tee "${PEP_RUNS}/dry_run/logs/pepmlm_entrypoint_discovery_$(date +%Y%m%d).log"
import sys
from pathlib import Path
print(sys.version)
root = Path(".").resolve()
print("repo", root)
print("candidate_files")
for pattern in ["*.py", "*/**/*.py", "README*", "requirements*", "environment*"]:
    for path in sorted(root.glob(pattern))[:40]:
        print(path)
PY
```

Expected: the log records Python version and candidate entrypoint files. This is repository discovery, not a model run.

- [ ] **Step 2: RFdiffusion dry-run**

Run repository help/config validation without generating benchmark outputs:

```bash
conda activate pep_rfdiffusion
cd "${PEP_SRC}/RFdiffusion"
python - <<'PY' | tee "${PEP_RUNS}/dry_run/logs/rfdiffusion_entrypoint_discovery_$(date +%Y%m%d).log"
import sys
from pathlib import Path
print(sys.version)
root = Path(".").resolve()
print("repo", root)
for path in [
    Path("scripts/run_inference.py"),
    Path("configs/inference/base.yml"),
    Path("env/SE3nv.yml"),
    Path("setup.py"),
]:
    print(path, "exists=", path.exists())
PY
```

Expected: script route and config dependency status are recorded.

- [ ] **Step 3: ProteinMPNN dry-run**

```bash
conda activate pep_proteinmpnn
cd "${PEP_SRC}/ProteinMPNN"
python - <<'PY' | tee "${PEP_RUNS}/dry_run/logs/proteinmpnn_entrypoint_discovery_$(date +%Y%m%d).log"
import sys
from pathlib import Path
print(sys.version)
root = Path(".").resolve()
print("repo", root)
for path in [
    Path("protein_mpnn_run.py"),
    Path("helper_scripts"),
    Path("examples"),
    Path("README.md"),
]:
    print(path, "exists=", path.exists())
PY
```

Expected: script route and handoff dependency status are recorded.

## Task 8: Batch A Smoke Test

**Files:**
- Input: `${PEP_RUNS}/smoke_test/run.csv`
- Output root: `${PEP_RUNS}/smoke_test/outputs/`
- Logs: `${PEP_RUNS}/smoke_test/logs/`
- Create outside git: `${PEP_RUNS}/smoke_test/method_run_log.csv`

- [ ] **Step 1: Run PepMLM on one approved T1 row**

Expected output record:

```text
design_id,method,command,commit_sha,environment,started_at,finished_at,exit_code,output_path,parser_status,error_message
```

Expected: one sequence-output file or a recorded failure. Do not interpret performance.

- [ ] **Step 2: Run RFdiffusion + ProteinMPNN on one approved T3 row**

Expected output record:

```text
design_id,method,rf_command,mpnn_command,rf_commit_sha,mpnn_commit_sha,environment,started_at,finished_at,exit_code,output_path,parser_status,error_message
```

Expected: one backbone/sequence-output directory or a recorded failure. Do not interpret performance.

- [ ] **Step 3: Decide whether PepMirror can enter smoke test**

PepMirror may enter smoke test only if PyRosetta license, Vina, OpenMM and checkpoint routes are complete.

Expected: if any dependency remains blocked, record `deferred_dependency` and do not run PepMirror.

## Task 9: Scoring And Merged Outputs

**Files:**
- Read: `${PEP_KB}/benchmark/protocols/scoring_outputs_schema.md`
- Read: `${PEP_KB}/benchmark/scoring/scoring_protocol_v0.md`
- Create outside git: `${PEP_RUNS}/smoke_test/scoring/confidence_metrics.csv`
- Create outside git: `${PEP_RUNS}/smoke_test/scoring/interface_metrics.csv`
- Create outside git: `${PEP_RUNS}/smoke_test/scoring/rmsd.csv`
- Create outside git: `${PEP_RUNS}/smoke_test/scoring/dockq.csv`
- Create outside git: `${PEP_RUNS}/smoke_test/scoring/developability_metrics.csv`
- Create outside git: `${PEP_RUNS}/smoke_test/merged_run.csv`

- [ ] **Step 1: Score parseability first**

Every design gets:

```text
design_id,method,status,output_exists,output_parseable,chain_valid,length_valid,not_applicable_reason
```

Expected: failed runs still produce a parseability row.

- [ ] **Step 2: Apply metric families only when applicable**

Rules:

```text
sequence-only output: developability metadata allowed; structure metrics empty with not_applicable_reason
complex structure output: confidence/interface/similarity/developability allowed
D-peptide output: chirality flag required before geometry interpretation
cyclic peptide output: cyclic/topology flag required before validity interpretation
```

Expected: no metric family is forced onto an incompatible output.

- [ ] **Step 3: Merge by design_id**

```bash
conda activate pep_scoring_base
python - <<'PY'
from pathlib import Path
import os
import pandas as pd

run_root = Path(os.environ["PEP_RUNS"]) / "smoke_test"
run_csv = run_root / "run.csv"
scoring_root = run_root / "scoring"
out = run_root / "merged_run.csv"
frames = []

if run_csv.exists():
    frames.append(pd.read_csv(run_csv))

for name in [
    "confidence_metrics.csv",
    "interface_metrics.csv",
    "rmsd.csv",
    "dockq.csv",
    "developability_metrics.csv",
]:
    path = scoring_root / name
    if path.exists():
        frame = pd.read_csv(path)
        if "design_id" not in frame.columns:
            raise SystemExit(f"{path} missing design_id")
        frames.append(frame)

if not frames:
    raise SystemExit("no run or scoring CSV files found")

merged = frames[0]
for frame in frames[1:]:
    merged = merged.merge(frame, on="design_id", how="outer", suffixes=("", "_dup"))

out.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(out, index=False)
print(f"wrote {out} rows={len(merged)} columns={len(merged.columns)}")
PY
```

Expected: `merged_run.csv` exists or a merge failure log exists. The merged file is still a smoke-test artifact, not a performance benchmark.

## Task 10: Back-Sync Small Artifacts To KB

**Files:**
- Create in KB only after execution: `benchmark/results/server_smoke_test_manifest_v0.10.csv`
- Create in KB only after execution: `ops/audits/server_smoke_test_summary_v0.10.md`
- Modify after execution: `manuscript/support/benchmark_manuscript_claim_evidence_map.csv`
- Modify after execution: `ops/validation/wiki_validation_report.md`

- [ ] **Step 1: Copy only small summaries into KB**

Allowed:

```text
CSV manifests
environment export summaries
command log summaries
parser status summaries
small merged smoke-test table
failure taxonomy
checksums and external paths
```

Forbidden:

```text
third-party source trees
raw datasets
weights/checkpoints
bulk PDB outputs
large prediction archives
full unfiltered logs containing secrets
```

- [ ] **Step 2: Update claim-evidence map**

After real smoke tests, add claims only at the level supported by logs:

```text
supported: method X reached smoke_test_ready on server with one approved input
unsupported: method X is generally reproduced
unsupported: method X outperforms method Y
unsupported: code is problem-free
```

Expected: claim map distinguishes dry-run, smoke-test readiness and benchmark performance.

- [ ] **Step 3: Run KB validation after back-sync**

```bash
cd "${PEP_KB}"
PYTHONUTF8=1 python scripts/validate_benchmark_kb.py
git diff --check
git status -sb
```

Expected: validator passes before any commit or manuscript claim update.

## Go / No-Go Criteria

Proceed from dry-run to smoke test only if:

- KB validator passes.
- Server inventory records GPU/driver/disk/memory.
- Required source commits are pinned.
- License and account blockers are resolved for the specific method.
- Download approval rows exist before downloading data or weights.
- Environment exports exist.
- `run.csv` rows are valid under schema.
- Output parser and failure-state recording exist.

Stop and revise if:

- Any license is unclear for a method or dataset.
- Any command writes data, weights or source trees into `${PEP_KB}`.
- A method requires unrecorded manual notebook intervention.
- A metric cannot be mapped to `design_id`.
- A result cannot be parsed into the scoring schema.
- The plan would require claiming performance before smoke-test outputs exist.

## Recommended First Server Session

The first server session should stop after Task 4 unless all licenses, roots and approval rows are clean. A practical first milestone is:

1. KB cloned or copied to server.
2. Server inventory captured.
3. KB validator pass captured.
4. Batch A source repositories cloned outside KB and commit-pinned.
5. License/account gate recorded.
6. Download approval table drafted with `download_performed=no`.

This milestone is enough to upgrade selected methods from metadata-only readiness to server preflight evidence, but it is still not local reproducibility, smoke-test success or benchmark performance.
