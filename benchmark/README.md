# Benchmark Workspace

本目录是 Pep_design 后续 Benchmark 的工作层。当前阶段只定义协议、schema、审计表和 smoke-test 计划，不下载大模型权重、不运行 GPU 设计任务、不声称本地复现。

## Directory Map

| path | purpose |
|:---|:---|
| `protocols/` | run.csv、任务协议和评分输出 schema |
| `smoke_tests/` | 每个候选方法的最小运行计划 |
| `input_sets/` | 后续标准输入集合说明和小型示例 |
| `availability/` | 方法仓库和数据入口的 metadata/API/HEAD 可用性审计 |
| `deployment/` | 后续服务器部署、外部目录、许可证准备清单、download manifest template 和方法级 server contract |
| `scoring/` | 评分协议和后续评分脚本位置 |
| `results/` | 后续小型示例输出或结果索引；真实大结果不进入 git |

## Source Boundary

`de_novo_binder_scoring` 只作为评分管线经验来源，不作为本项目依赖。后续如需使用其脚本，应另行记录版本、license、输入输出适配和引用。

v0.5 availability audits only record reachability and metadata. They do not imply that code is installed, datasets are downloaded, or methods are locally reproduced.

v0.7 method contracts and `download_manifest_template_v0.7.csv` are server dry-run planning artifacts. They define expected inputs, external roots, blockers and download bookkeeping fields, but they do not record clone, install, checkpoint fetch, data download or benchmark execution.

v0.8 license/schema/input-contract review adds auditable metadata for priority data sources and methods. `download_manifest_v0.8.csv` may include future server URLs, sizes or checksums where known, but every row must keep `download_performed=no` until an approved server-side download is actually executed outside this repository.

v0.9 synchronizes the current plan and manuscript structure. `method_landscape_watchlist_v0.9.csv` is a coverage and Related Work artifact; it does not expand the include method set, freeze targets, install methods, or create benchmark results.

v0.10 adds server-side preflight approval/status artifacts for future execution. All approval rows remain pending, and no clone/download/install/run evidence is stored in the KB.

v0.11 adds the job/adapter interface layer: `job_manifest.csv` schema, adapter-output schema, artificial Batch A example manifests, source freshness planning and adapter preflight status. These artifacts prepare PepMLM and RFdiffusion + ProteinMPNN for later approved dry-run/smoke-test work, while PepMirror remains dependency-blocked.

v0.12 records source-only external Git checkouts for the 11 repositories corresponding to the first-wave include methods. The source trees live under `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark`; the KB stores only the small manifest and audit report, not third-party source, weights, datasets, install artifacts, GPU outputs, or benchmark results.

v0.13 records local Docker image reuse and the shared benchmark environment scaffold. Existing `/mnt/ssd4t/protein-design` images are reused for RFdiffusion/ProteinMPNN, BindCraft, AF2/AF3, Rosetta, PepMimic and RFpeptide routes. `pd-benchmark-methods-gpu:0.13` is a workbench Dockerfile scaffold with separate conda environments for PepMLM, DiffPepBuilder, PepGLAD, D-Flow/PeptideDesign and ColabDesign; the v0.13 layer alone is not method installation, smoke-test result, or benchmark-run evidence.

v0.14 adds academic-search target/case candidate planning through `method_paper_case_matrix_v0.14.csv` and `target_candidate_academic_search_v0.14.csv`. These files record literature examples and candidate panels only. They do not download data, freeze targets, validate assays, clear leakage, install methods, or create Benchmark results.

v0.15 records external `/data/protein-design` preflight and minimal Batch A smoke-test summaries through `deployment/run_preflight_results_v0.15.csv`, `deployment/batch_a_smoke_test_results_v0.15.csv`, and `ops/audits/batch_a_execution_audit_v0.15.md`. Raw logs, model caches, Docker layers, PDB/TRB/trajectory outputs and future large run artifacts remain outside this KB. The v0.15 records support `minimal_smoke_observed` evidence only; they do not support target-set promotion, scoring, performance ranking, complete Benchmark claims, or `smoke_test_ready` promotion.
