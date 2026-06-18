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
